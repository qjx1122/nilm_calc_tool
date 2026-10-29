"""负荷辨识 · 设备画像（v0.90，按《设备画像提取与总线侧负荷辨识事件检测算法方案.md》基础版实现）。

两个阶段，算法核心只依赖 numpy：

1. **设备侧画像构建** ``build_profile``：对设备侧（分路侧）含启停过程的周波录波回放逐周波特征（P/Q/三相 I），
   用启停标签（真值表「时间,动作」）或变化点检测定位每次启动 / 停止事件，提取事件特征向量
   ``FEATURES``（事件前后稳态差：ΔIa/ΔIb/ΔIc/ΔP/ΔQ，启动峰值比，持续周波数）与归一化动态轨迹模板
   （事件窗内三相电流合成量相对事件前基线的变化，时间归一化到 ``TEMPLATE_POINTS`` 点），分别对启动 / 停止做
   多次事件统计（中心 μ、对角 σ，带相对 / 绝对下限的收缩，方案 §3.4），写成单个 JSON 画像文件（§3.5 的 JSON+NPZ
   在本工具里合并为一个 JSON，数组内联，便于配置页填路径与随配置一起复制）。

2. **总线侧匹配检测** ``detect_profile``：在周波窗上用稳健双滑窗变化点产生候选（§5.2/5.4，前后窗长取画像的
   pre/post），对每个候选提取同一特征向量，与启动 / 停止画像分别算对角马氏距离 ``D²``（§5.5，Σ+λI 收缩），
   取最小者为方向；轨迹模板用归一化 L2 距离作为动态证据（基础版不做 DTW，§11 增强版再加）；
   置信度 ``confidence = exp(−D²/(2·d))``（d＝特征维数；D²=d 即平均 1σ 偏差 → 0.61）；再按 ``d2_max``
   （每维平均允许的 D² 上限）、``min_confidence``、最优 / 次优区分度 ``margin`` 与设备状态机（OFF→START /
   ON→STOP 合理，否则降置信度并打 ``state_mismatch`` 标记）过滤。输出带 ``device_id / confidence / d2 /
   profile_direction(START|STOP) / status(confirmed|low_confidence) / quality_flags`` 的事件；
   ``observed_delta_p`` ＝总线侧观测 ΔP，``estimated_device_delta_p`` 恒为 None（无同步校准数据时不估计，§7）。

限制（方案 §1/§4）：设备侧电流 ≠ 总线侧电流增量；画像只能做候选检测与相似性匹配，特征相似的设备之间不保证唯一辨识。
"""
from __future__ import annotations

import json
import math
import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

PROFILE_SCHEMA = "nilm_profile/1"
FEATURES = ["d_ia", "d_ib", "d_ic", "d_p", "d_q", "peak_ratio", "dur_cycles"]
FEATURE_NAMES = {"d_ia": "ΔIa (A)", "d_ib": "ΔIb (A)", "d_ic": "ΔIc (A)", "d_p": "ΔP (W)", "d_q": "ΔQ (var)",
                 "peak_ratio": "启动峰值比", "dur_cycles": "持续周波数"}
TEMPLATE_POINTS = 16
# σ 收缩下限：相对中心的比例（单次事件也能给出合理容差）与绝对下限（电流 A / 功率 W / 比值 / 周波）
_REL_FLOOR = {"d_ia": 0.15, "d_ib": 0.15, "d_ic": 0.15, "d_p": 0.15, "d_q": 0.25, "peak_ratio": 0.3, "dur_cycles": 0.5}
# v0.92.5：dur_cycles 下限 2→5 周波（在线终点估计对噪声敏感，单样本画像 σ=2 时 10 周波偏差就贡献 25）
_ABS_FLOOR = {"d_ia": 0.02, "d_ib": 0.02, "d_ic": 0.02, "d_p": 5.0, "d_q": 5.0, "peak_ratio": 0.1, "dur_cycles": 5.0}


class ProfileError(ValueError):
    pass


# ------------------------------------------------------------------ 事件特征
def _median(a: np.ndarray, fallback: float = 0.0) -> float:
    return float(np.median(a)) if a.size else float(fallback)


def event_features(p4: np.ndarray, q4: np.ndarray, i4: np.ndarray, onset: int, end: int,
                   pre_n: int, post_n: int) -> Dict[str, Any]:
    """候选事件（窗内索引 onset→end）的特征向量与归一化轨迹。p4/q4/i4：(4, L)，顺序 total, A, B, C。

    * ΔIa/ΔIb/ΔIc/ΔP/ΔQ ＝ 事件后窗 [end, end+post_n) 中位数 − 事件前窗 [onset−pre_n, onset) 中位数（§5.4）；
    * peak_ratio ＝ 事件窗内三相电流合成量相对事件前基线的最大偏移 / 稳态偏移（≥1；1＝无启动冲击）；
    * dur_cycles ＝ end − onset；
    * template ＝ [onset, end+post_n) 内合成电流相对事件前基线的变化 / 稳态变化，重采样到 TEMPLATE_POINTS 点。
    """
    L = p4.shape[1]
    a0, a1 = max(0, onset - pre_n), onset
    b0, b1 = min(end, L), min(end + post_n, L)
    if b0 >= b1:
        b0, b1 = min(end, L - 1), L
    pre = {"p": _median(p4[0, a0:a1], p4[0, max(0, onset - 1)]), "q": _median(q4[0, a0:a1], q4[0, max(0, onset - 1)]),
           "ia": _median(i4[1, a0:a1], i4[1, max(0, onset - 1)]), "ib": _median(i4[2, a0:a1], i4[2, max(0, onset - 1)]),
           "ic": _median(i4[3, a0:a1], i4[3, max(0, onset - 1)]), "it": _median(i4[0, a0:a1], i4[0, max(0, onset - 1)])}
    post = {"p": _median(p4[0, b0:b1]), "q": _median(q4[0, b0:b1]), "ia": _median(i4[1, b0:b1]), "ib": _median(i4[2, b0:b1]),
            "ic": _median(i4[3, b0:b1]), "it": _median(i4[0, b0:b1])}
    d_it = post["it"] - pre["it"]
    seg = i4[0, onset:b1] - pre["it"]
    if seg.size == 0:
        seg = np.zeros(1)
    denom = abs(d_it) if abs(d_it) > 1e-12 else max(float(np.max(np.abs(seg))), 1e-12)
    peak_ratio = float(np.max(np.abs(seg)) / denom) if seg.size else 1.0
    peak_ratio = max(1.0, min(peak_ratio, 50.0))
    # 轨迹：按 Δ 的符号归一化（启动→正向 0→1，停止→0→1 同样方向），时间归一化
    sgn = 1.0 if d_it >= 0 else -1.0
    traj = sgn * seg / denom
    xs = np.linspace(0, max(seg.size - 1, 1), TEMPLATE_POINTS)
    template = np.interp(xs, np.arange(seg.size), traj) if seg.size > 1 else np.full(TEMPLATE_POINTS, float(traj[0]))
    vec = {"d_ia": post["ia"] - pre["ia"], "d_ib": post["ib"] - pre["ib"], "d_ic": post["ic"] - pre["ic"],
           "d_p": post["p"] - pre["p"], "d_q": post["q"] - pre["q"], "peak_ratio": peak_ratio, "dur_cycles": float(end - onset)}
    return {"vec": vec, "template": [float(x) for x in template], "pre": pre, "post": post, "d_it": float(d_it)}


def _vec_array(vec: Dict[str, float]) -> np.ndarray:
    return np.array([float(vec[k]) for k in FEATURES], dtype=np.float64)


# ------------------------------------------------------------------ 画像统计
def fit_group(samples: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """对同一方向的多次事件做统计：μ、σ（对角，带收缩下限）、轨迹模板均值 / 散布、持续时间分布。"""
    if not samples:
        return None
    X = np.vstack([_vec_array(s["vec"]) for s in samples])
    mu = X.mean(axis=0)
    sd = X.std(axis=0, ddof=1) if X.shape[0] > 1 else np.zeros(X.shape[1])
    sigma = np.array([max(float(sd[j]), _REL_FLOOR[k] * abs(float(mu[j])), _ABS_FLOOR[k]) for j, k in enumerate(FEATURES)])
    T = np.vstack([np.asarray(s["template"], dtype=np.float64) for s in samples])
    tmpl = T.mean(axis=0)
    tspread = float(np.sqrt(np.mean((T - tmpl) ** 2))) if T.shape[0] > 1 else 0.0
    dur = X[:, FEATURES.index("dur_cycles")]
    return {"n": int(X.shape[0]), "mu": [float(v) for v in mu], "sigma": [float(v) for v in sigma],
            "template": [float(v) for v in tmpl], "template_spread": max(tspread, 0.1),
            "dur_cycles": {"min": float(dur.min()), "max": float(dur.max()), "mean": float(dur.mean())},
            "events": [{"t_start": s.get("t_start"), "t_start_local": s.get("t_start_local"), "onset": s.get("onset"),
                        "end": s.get("end"), "vec": {k: float(v) for k, v in s["vec"].items()}, "source": s.get("source", "")}
                       for s in samples]}


def validate_profile(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(doc, dict) or doc.get("schema") != PROFILE_SCHEMA:
        raise ProfileError(f"画像文件 schema 不是 {PROFILE_SCHEMA}（当前 {doc.get('schema') if isinstance(doc, dict) else type(doc).__name__!r}）")
    if list(doc.get("features") or []) != FEATURES:
        raise ProfileError(f"画像特征定义与本版本不一致：{doc.get('features')} ≠ {FEATURES}（特征定义版本不一致时拒绝加载，方案 §3.5）")
    if not doc.get("startup") and not doc.get("shutdown"):
        raise ProfileError("画像里既没有启动画像也没有停止画像")
    for key in ("startup", "shutdown"):
        g = doc.get(key)
        if not g:
            continue
        if len(g.get("mu", [])) != len(FEATURES) or len(g.get("sigma", [])) != len(FEATURES):
            raise ProfileError(f"画像 {key}.mu/sigma 维数不对")
        if any((not math.isfinite(float(v))) or float(v) <= 0 for v in g["sigma"]):
            raise ProfileError(f"画像 {key}.sigma 必须全为正有限数")
    return doc


def load_profile(path: str, root: Optional[str] = None) -> Dict[str, Any]:
    p = path if os.path.isabs(path) else os.path.join(root or os.getcwd(), path)
    doc = _load_profile_raw(p)
    jd = FEATURES.index("dur_cycles")
    for k in ("startup", "shutdown"):          # v0.92.5：旧画像的 σ 按当前绝对下限抬升
        g = doc.get(k)
        if g and len(g.get("sigma", [])) > jd:
            g["sigma"][jd] = max(float(g["sigma"][jd]), _ABS_FLOOR["dur_cycles"])
    return doc


def _load_profile_raw(p: str) -> Dict[str, Any]:
    if not os.path.isfile(p):
        raise ProfileError(f"画像文件不存在：{p}")
    with open(p, encoding="utf-8") as fh:
        doc = json.load(fh)
    doc = validate_profile(doc)
    doc["_path"] = p
    return doc


# ------------------------------------------------------------------ 匹配
def mahalanobis_diag(vec: Dict[str, float], mu: Sequence[float], sigma: Sequence[float], lam_rel: float = 0.1,
                     skip: Sequence[str] = ()) -> Tuple[float, List[float]]:
    """对角马氏距离 D² 与各维贡献；Σ_λ = diag(σ²) + λ·median(σ²)·I（§5.5 收缩）。``skip``：不参与的特征名（v0.93：三相三线无 B 相电流时跳过 d_ib）。"""
    x = _vec_array(vec); m = np.asarray(mu, dtype=np.float64); s = np.asarray(sigma, dtype=np.float64)
    var = s * s
    var = var + float(lam_rel) * float(np.median(var))
    contrib = (x - m) ** 2 / var
    for k in skip:
        if k in FEATURES:
            contrib[FEATURES.index(k)] = 0.0
    return float(np.sum(contrib)), [float(c) for c in contrib]


def template_distance(template: Sequence[float], ref: Sequence[float]) -> float:
    a = np.asarray(template, dtype=np.float64); b = np.asarray(ref, dtype=np.float64)
    n = min(a.size, b.size)
    if n == 0:
        return 0.0
    return float(np.sqrt(np.mean((a[:n] - b[:n]) ** 2)))


# v0.99.6：相序映射——总线侧与设备侧接线 / 相别标注可能不一致（设备 A 相接在总线 B 相等），ΔIa/ΔIb/ΔIc 三个分相特征需要
#   按映射重排后再与画像比较（ΔP/ΔQ/峰值比/持续周波是三相合成量，不受相序影响）。编码（配置 nilm.algorithms.profile.phase_map 为数值）：
#   1 ABC（默认，不重排）2 ACB  3 BAC  4 BCA  5 CAB  6 CBA  0 自动（6 种全试，取 D² 最小者并在结果里报告）。
#   字符串含义：第 i 位＝总线侧第 i 相（A,B,C）上接的是设备侧哪一相。
PHASE_MAPS = {1: "ABC", 2: "ACB", 3: "BAC", 4: "BCA", 5: "CAB", 6: "CBA"}


def phase_map_code(v: Any) -> int:
    """配置值 → 编码（0 自动 / 1..6）；字符串 "ABC"/"auto" 也接受。"""
    if isinstance(v, str):
        t = v.strip().upper()
        if t in ("", "AUTO", "0"):
            return 0
        for k, m in PHASE_MAPS.items():
            if t == m:
                return k
        try:
            v = float(t)
        except ValueError:
            raise ProfileError(f"phase_map 不认识：{v!r}（可写 0 自动 / 1..6 / ABC…CBA）")
    code = int(float(v or 1))
    if code not in PHASE_MAPS and code != 0:
        raise ProfileError(f"phase_map 必须是 0（自动）或 1..6（当前 {v!r}）")
    return code


def remap_phases(vec: Dict[str, float], mapping: str) -> Dict[str, float]:
    """按相序映射把总线侧分相特征重排为设备侧相序：mapping[i] 是总线第 i 相上的设备相。"""
    if mapping == "ABC":
        return dict(vec)
    bus = {"A": vec["d_ia"], "B": vec["d_ib"], "C": vec["d_ic"]}
    dev = {mapping[i]: bus[ph] for i, ph in enumerate("ABC")}
    out = dict(vec)
    out["d_ia"], out["d_ib"], out["d_ic"] = dev["A"], dev["B"], dev["C"]
    return out


def match_event(profile: Dict[str, Any], feat: Dict[str, Any], lam_rel: float = 0.1, skip: Sequence[str] = (),
                phase_map: int = 1) -> Dict[str, Any]:
    """候选特征与启动 / 停止画像分别匹配；返回最优方向、D²、置信度、区分度与轨迹距离。``skip``：不参与匹配的特征（见 mahalanobis_diag）。
    ``phase_map``：相序映射编码（见 PHASE_MAPS；0＝自动试 6 种取 D² 最小）。"""
    if phase_map == 0:
        best = None
        for code, m in PHASE_MAPS.items():
            r = match_event(profile, feat, lam_rel, skip, code)
            if best is None or r["d2"] < best["d2"]:
                best = r
        best["phase_map_auto"] = True
        return best
    mapping = PHASE_MAPS[int(phase_map)]
    vec = remap_phases(feat["vec"], mapping)
    skip = [k for k in skip if k in FEATURES]
    d = max(1, len(FEATURES) - len(skip))
    res: Dict[str, Any] = {}
    for key, name in (("startup", "START"), ("shutdown", "STOP")):
        g = profile.get(key)
        if not g:
            continue
        d2, contrib = mahalanobis_diag(vec, g["mu"], g["sigma"], lam_rel, skip)
        td = template_distance(feat["template"], g["template"])
        res[name] = {"d2": d2, "contrib": contrib, "template_dist": td, "template_spread": float(g.get("template_spread", 0.3))}
    if not res:
        raise ProfileError("画像为空")
    best = min(res, key=lambda k: res[k]["d2"])
    other = [k for k in res if k != best]
    d2 = res[best]["d2"]
    conf = math.exp(-d2 / (2.0 * d))
    # 动态轨迹证据：轨迹 RMS 距离超过模板散布 3 倍时打折（基础版：L2，不做 DTW）
    td, sp = res[best]["template_dist"], max(res[best]["template_spread"], 0.1)
    traj_penalty = 1.0 if td <= 3.0 * sp else max(0.3, 3.0 * sp / td)
    margin = (res[other[0]]["d2"] / d2) if (other and d2 > 0) else float("inf")
    return {"direction": best, "d2": d2, "d2_per_dim": d2 / d, "confidence": conf * traj_penalty, "margin": margin,
            "phase_map": mapping, "phase_map_auto": False,
            "template_dist": td, "traj_penalty": traj_penalty, "contrib": dict(zip(FEATURES, res[best]["contrib"])),
            "d2_start": res.get("START", {}).get("d2"), "d2_stop": res.get("STOP", {}).get("d2")}


# ------------------------------------------------------------------ 总线侧检测
def _two_window_candidates(x: np.ndarray, pre_n: int, post_n: int, min_d: float, k_sig: float) -> List[Tuple[int, int, float]]:
    """稳健双滑窗候选：|median(后) − median(前)| 局部极大值 ≥ max(min_d, k·MAD 尺度)。返回 (onset, end, delta)。"""
    L = x.size
    if L < pre_n + post_n + 2:
        return []
    cs = np.concatenate([[0.0], np.cumsum(x)]); cs2 = np.concatenate([[0.0], np.cumsum(x * x)])
    idx = np.arange(pre_n, L - post_n + 1)
    m_pre = (cs[idx] - cs[idx - pre_n]) / pre_n
    m_post = (cs[idx + post_n] - cs[idx]) / post_n
    v_pre = np.maximum((cs2[idx] - cs2[idx - pre_n]) / pre_n - m_pre ** 2, 0.0)
    delta = m_post - m_pre
    thr = np.maximum(min_d, k_sig * np.sqrt(v_pre))
    exceed = np.abs(delta) >= thr
    out: List[Tuple[int, int, float]] = []
    j = 0
    while j < idx.size:
        if not exceed[j]:
            j += 1; continue
        k0 = j
        while j < idx.size and exceed[j]:
            j += 1
        if j >= idx.size:
            break          # v0.92.5：超限游程顶到右边界＝后窗还没装满，峰值位置未定（在线会随新数据右移），等下一块再评估
        pk = k0 + int(np.argmax(np.abs(delta[k0:j])))
        onset = int(idx[pk])
        # 终点：onset 之后「相对事件后电平的偏差 > 稳态偏差 20%」的最后一个周波的下一周波（过渡结束处），封顶 post_n
        #   v0.92.2：原为"首个进入 20% 带的周波"——斜坡 / 冲击型启动会在过渡中途就判终点，事件后窗落在过渡里，
        #   ΔP/ΔQ/ΔI 与画像（设备侧按稳态分段取过渡结束后）系统性不一致
        seg = x[onset:onset + post_n]
        tgt = float(m_post[pk]); dlt = abs(float(delta[pk]))
        exc = np.nonzero(np.abs(seg - tgt) > 0.2 * dlt)[0]
        end = onset + (int(exc[-1]) + 1 if exc.size else 1)
        end = min(end, onset + post_n - 1)
        out.append((onset, min(end, L - 1), float(delta[pk])))
    return out


def detect_profile(p4: np.ndarray, q4: np.ndarray, i4: np.ndarray, profile: Dict[str, Any], prm: Dict[str, Any],
                   use_p: bool, device_state: str = "unknown", skip: Sequence[str] = ()) -> List[Dict[str, Any]]:
    """窗上运行一次画像匹配检测。返回按 onset 排序的候选结果列表（每项含 onset/end/pre/post/match/flags/accepted）。

    ``skip``：不参与匹配的特征名；三相三线两表法（transform.wiring=3p3w）本侧无 B 相电流，引擎传 ("d_ib",)，
    此时 ΔI 合成幅值也只按 A/C 两相计算。

    prm：``d2_max``（每维平均 D² 上限）、``min_confidence``、``k_sigma``（候选门槛的噪声倍数）、``margin``（最优 / 次优 D² 比下限）、
    ``lambda_rel``（协方差收缩）、``state_check``（1/0）、``max_scale``（v0.99.15：多尺度候选搜索的最大倍数，1＝只用画像 pre/post 单尺度）。
    候选的最小幅值＝画像里 |ΔP|（或 |ΔI 合成|）最小值的一半。

    多尺度（v0.99.15）：慢斜坡停机（如变频器减速 3 s 快降 + 25 s 指数尾）在 pre/post=10/50 周波的双滑窗里 1 s 内只能看到全幅的
    一小部分，达不到「画像幅值一半」门槛 ⇒ 没有候选。现在依次用 ×1、×2、×4 … ×max_scale 的前后窗各搜一遍；同一事件在多个尺度
    命中时合并为一个候选：onset 取最早（细尺度定位准）、end 取最晚、特征按最大尺度的 post 窗量（事件后窗落在过渡结束后，ΔI/ΔP 接近全幅）。
    返回项附 ``scale``（命中的最大倍数，1＝原单尺度行为）。
    """
    pre_n = int(profile.get("pre_cycles", 10)); post_n = int(profile.get("post_cycles", 50))
    groups = [profile[k] for k in ("startup", "shutdown") if profile.get(k)]
    ip = FEATURES.index("d_p")
    if use_p:
        x = p4[0]
        amp = [abs(g["mu"][ip]) for g in groups]
    else:
        x = i4[0]
        amp = [math.sqrt(sum(g["mu"][FEATURES.index(k)] ** 2 for k in ("d_ia", "d_ib", "d_ic") if k not in skip)) for g in groups]
    min_d = 0.5 * min(amp) if amp else 0.0
    k_sig = float(prm.get("k_sigma", 4.0))
    max_scale = max(1, int(float(prm.get("max_scale", 8))))
    scales = [1]
    while scales[-1] * 2 <= max_scale:
        scales.append(scales[-1] * 2)
    merged: List[Dict[str, Any]] = []            # {onset, end, delta, scale}
    for sc in scales:
        for onset, end, delta in _two_window_candidates(x, pre_n * sc, post_n * sc, min_d, k_sig):
            hit = None
            for g in merged:                      # 与已有候选重叠（onset 落在其 [onset − post·sc, end + post·sc]）⇒ 同一事件
                if g["onset"] - post_n * sc <= onset <= g["end"] + post_n * sc:
                    hit = g; break
            if hit is None:
                merged.append({"onset": onset, "end": end, "delta": delta, "scale": sc})
            else:
                hit["onset"] = min(hit["onset"], onset); hit["end"] = max(hit["end"], end); hit["scale"] = max(hit["scale"], sc)
                if abs(delta) > abs(hit["delta"]):
                    hit["delta"] = delta
    merged.sort(key=lambda g: g["onset"])
    cands = [(g["onset"], g["end"], g["delta"], g["scale"]) for g in merged]
    d2_max = float(prm.get("d2_max", 9.0)); min_conf = float(prm.get("min_confidence", 0.3))
    margin_min = float(prm.get("margin", 1.5)); lam = float(prm.get("lambda_rel", 0.1))
    state_check = int(float(prm.get("state_check", 1))) != 0
    pmap = phase_map_code(prm.get("phase_map", 1))                      # v0.99.6：总线 / 设备侧相序映射
    out: List[Dict[str, Any]] = []
    state = device_state
    for onset, end, delta, sc in cands:
        feat = event_features(p4, q4, i4, onset, end, pre_n, post_n * sc)
        m = match_event(profile, feat, lam, skip, pmap)
        flags: List[str] = []
        if m.get("phase_map_auto") and m.get("phase_map") != "ABC":
            flags.append("phase_map_" + str(m.get("phase_map")))       # 自动相序：记录实际采用的映射（非 ABC 时提示）
        conf = m["confidence"]
        if m["d2_per_dim"] > d2_max:
            flags.append("d2_exceeds")
        if math.isfinite(m["margin"]) and m["margin"] < margin_min:
            flags.append("ambiguous_direction")
        if state_check and state != "unknown":
            if (m["direction"] == "START" and state == "on") or (m["direction"] == "STOP" and state == "off"):
                flags.append("state_mismatch"); conf *= 0.5
        if m["traj_penalty"] < 1.0:
            flags.append("trajectory_deviates")
        accepted = ("d2_exceeds" not in flags) and conf >= min_conf
        status = "confirmed" if accepted and not flags else ("low_confidence" if accepted else "rejected")
        if accepted:
            state = "on" if m["direction"] == "START" else "off"
        out.append({"onset": onset, "end": end, "delta": delta, "feat": feat, "match": m, "confidence": conf,
                    "flags": flags, "accepted": accepted, "status": status, "scale": int(sc), "post_wait": int(post_n * sc)})
    return out


# ------------------------------------------------------------------ 画像构建（设备侧离线）
_UP = {"开", "开机", "启动", "起动", "投入", "on", "start", "up", "1", "true"}
_DN = {"关", "关机", "停止", "停机", "切除", "off", "stop", "down", "0", "false"}


def parse_labels(text: str, day_hint: Optional[float] = None) -> List[Dict[str, Any]]:
    """解析启停标签文本（每行「时间,动作[,备注]」；时间写法同真值表：完整日期时间 / epoch 秒 / HH:MM:SS[.fff]）。"""
    from .config import parse_time_text
    from datetime import datetime
    rows: List[Dict[str, Any]] = []
    lines = [ln.strip() for ln in str(text or "").replace("\t", ",").splitlines() if ln.strip() and not ln.strip().startswith("#")]
    for ln in lines:
        parts = [c.strip() for c in ln.replace("，", ",").split(",")]
        if len(parts) < 2:
            raise ProfileError(f"标签行至少要「时间,动作」两列：{ln!r}")
        txt, act = parts[0], parts[1].lower()
        if not txt or not txt[0].isdigit():
            if rows or len(lines) == 1:
                raise ProfileError(f"标签行时间无法解析：{ln!r}")
            continue                                            # 表头
        if act in _UP:
            d = "START"
        elif act in _DN:
            d = "STOP"
        else:
            raise ProfileError(f"标签「动作」不认识：{parts[1]!r}（可写 开/关、启动/停止、on/off、start/stop）")
        if ":" in txt and "-" not in txt and "/" not in txt and " " not in txt:
            if day_hint is None:
                raise ProfileError("标签只写了时刻（HH:MM:SS）但文件没有日期信息；请写完整日期时间")
            hh, mm, *rest = txt.split(":")
            base = datetime.fromtimestamp(day_hint).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            t = base + int(hh) * 3600 + int(mm) * 60 + (float(rest[0]) if rest else 0.0)
        else:
            t = parse_time_text(txt)
        rows.append({"t": float(t), "direction": d, "note": parts[2] if len(parts) > 2 else "", "text": txt})
    return rows


def _locate_near(x: np.ndarray, k_center: int, half: int, pre_n: int, post_n: int) -> Tuple[int, int, float]:
    """标签时刻附近 ±half 周波内找双滑窗 |Δ| 最大的变化点；返回 (onset, end, delta)。"""
    L = x.size
    lo, hi = max(pre_n, k_center - half), min(L - post_n - 1, k_center + half)
    if hi <= lo:
        raise ProfileError("标签时刻太靠近文件边界，前后窗放不下")
    # 变化点用「前窗中位数 vs 紧随其后 m 周波中位数」的短窗得分定位（长后窗中位数对启动冲击不敏感，会把 onset 提前到冲击之前的任意位置）
    #   得分＝紧随其后 m 周波相对前窗中位数的**最小**偏离（m 个周波都偏离才算真正起点，单个尖峰 / 起点前的周波得分为 0）；
    #   取第一个得分 ≥ 0.5×最大得分的周波为 onset（台阶：恰为起点；斜坡：起点附近而非坡顶）
    m = max(2, min(5, post_n))
    ks = list(range(lo, hi + 1)); sc = []
    for k in ks:
        pre_med = float(np.median(x[k - pre_n:k]))
        dev = x[k:k + m] - pre_med
        sc.append(float(np.min(np.abs(dev))) if (np.all(dev > 0) or np.all(dev < 0)) else 0.0)
    bd = max(sc)
    best = ks[next(i for i, v in enumerate(sc) if v >= 0.5 * bd)] if bd > 0 else lo
    delta = float(np.median(x[best:best + post_n]) - np.median(x[best - pre_n:best]))
    seg = x[best:best + post_n]; tgt = float(np.median(seg))
    exc = np.nonzero(np.abs(seg - tgt) > 0.2 * abs(delta))[0]          # v0.92.2：终点＝过渡结束处（与在线候选同一规则）
    end = min(best + (int(exc[-1]) + 1 if exc.size else 1), best + post_n - 1)
    return best, end, delta


def load_cycles(cfg, file: str, *, max_cycles: int = 400000, t_start: str = "", t_end: str = "", custom_time: bool = False,
                custom_time_start: str = "", custom_time_end: str = ""):
    """读取设备侧文件为逐周波序列。返回 (c, feat, t, p4, q4, i4, u_nonzero)；``cfg`` 不被修改。"""
    from .config import AppConfig, parse_play_start
    from .nilm import CycleFeatures, detect_steps
    from .nilm_auto import auto_params
    from .scaling import scale_block
    from .sources import create_source
    from .timefmt import fmt_local
    c = AppConfig.from_dict(cfg.to_dict())
    if custom_time:
        from .wave_preview import WaveError, _prep_cfg, file_info, make_base
        try:
            b2 = make_base(cfg, custom_time="1", custom_time_start=str(custom_time_start or ""), custom_time_end=str(custom_time_end or ""))
            info = file_info(b2, file); c = _prep_cfg(b2, file, t_start, t_end, info)
        except WaveError as exc:
            raise ProfileError(str(exc)) from None
    else:
        c.source.kind = "csv_file"; c.source.path = file; c.source.file_speed = 0.0; c.source.play_window = False
        c.source.play_end_time = ""; c.source.play_start_mode = "begin"; c.source.play_start_value = ""
        if t_start:
            parse_play_start("time", t_start); c.source.play_start_mode = "time"; c.source.play_start_value = t_start
        if t_end:
            parse_play_start("time", t_end); c.source.play_end_time = t_end
        c.validate()
    feat = CycleFeatures(c.sampling.fs, c.sampling.f_nom)
    ts, ps, qs, is_ = [], [], [], []
    u_nonzero = False; n = 0
    with create_source(c) as src:
        while True:
            blk = src.read()
            if blk is None:
                if src.exhausted:
                    break
                continue
            if not u_nonzero and np.any(np.abs(blk.u) > 0):
                u_nonzero = True
            f = feat.push(scale_block(blk, c.transform))
            if f["t"].size:
                ts.append(f["t"]); ps.append(f["p"]); qs.append(f["q"]); is_.append(f["i"]); n += int(f["t"].size)
            if n >= max_cycles:
                break
    if not ts:
        raise ProfileError("没有读到整周波数据")
    t = np.concatenate(ts)[:max_cycles]; p4 = np.concatenate(ps, axis=1)[:, :max_cycles]
    q4 = np.concatenate(qs, axis=1)[:, :max_cycles]; i4 = np.concatenate(is_, axis=1)[:, :max_cycles]
    return c, feat, t, p4, q4, i4, u_nonzero


def build_profile(cfg, file: str, *, device_id: str = "device", labels: Optional[str] = None, label_tol_s: float = 2.0,
                  pre_cycles: int = 10, post_cycles: int = 50, max_cycles: int = 400000, quantity: Optional[str] = None,
                  t_start: str = "", t_end: str = "", custom_time: bool = False, custom_time_start: str = "",
                  custom_time_end: str = "", merge_gap_s: float = 10.0) -> Dict[str, Any]:
    """从设备侧文件构建画像。``merge_gap_s``（v0.92，仅自动定位模式）：同方向、中间没有反向事件、起点间隔 ≤ 该秒数的
    相邻事件视为同一次动作被稳态分段切碎（或启动后的分级带载 / 反复重启），只保留 |ΔI| 最大的一个；0＝不合并。``cfg``＝基准配置（PT/CT、fs、列映射，不被修改）。``labels``＝标签文本（空＝自动用稳态分段 +
    自适应参数找启停事件：幅值为正＝启动、为负＝停止）。返回画像文档（含 ``events`` 明细与 ``notes``）。"""
    c, feat, t, p4, q4, i4, u_nonzero = load_cycles(cfg, file, max_cycles=max_cycles, t_start=t_start, t_end=t_end, custom_time=custom_time,
                                                   custom_time_start=custom_time_start, custom_time_end=custom_time_end)
    from .nilm import detect_steps
    from .nilm_auto import auto_params
    from .timefmt import fmt_local
    q_req = quantity or str(getattr(c.nilm, "quantity", "auto") or "auto")
    use_p = (q_req == "p") or (q_req == "auto" and u_nonzero)
    if use_p and not u_nonzero:
        raise ProfileError("数据源没有电压：有功恒为 0，请用 quantity=i（或 auto）")
    x = p4[0] if use_p else i4[0]
    notes: List[str] = []
    samples: List[Dict[str, Any]] = []
    pre_n, post_n = int(pre_cycles), int(post_cycles)
    cps = float(c.sampling.f_nom)
    if labels and str(labels).strip():
        lab = parse_labels(labels, day_hint=float(t[0]))
        half = max(5, int(round(float(label_tol_s) * cps)))
        for lb in lab:
            k = int(np.searchsorted(t, lb["t"]))
            if k <= 0 or k >= t.size:
                notes.append(f"标签 {lb['text']} 不在文件时间范围内，忽略"); continue
            try:
                onset, end, delta = _locate_near(x, k, half, pre_n, post_n)
            except ProfileError as exc:
                notes.append(f"标签 {lb['text']}：{exc}"); continue
            d = "START" if delta >= 0 else "STOP"
            if d != lb["direction"]:
                notes.append(f"标签 {lb['text']} 为 {lb['direction']}，但附近最大变化为 {'正' if delta >= 0 else '负'}向（Δ={delta:.4g}），按标签方向归类，请复核")
            ef = event_features(p4, q4, i4, onset, end, pre_n, post_n)
            samples.append({**ef, "direction": lb["direction"], "onset": int(onset), "end": int(end), "t_start": float(t[onset]),
                            "t_start_local": fmt_local(float(t[onset])), "source": f"label:{lb['text']}"})
        mode = "labels"
    else:
        ap = auto_params(x, cps)
        if ap is None:
            raise ProfileError("文件太短（不足 60 个有效周波），无法自动定位启停事件；请给启停标签")
        prm = ap["algorithms"]["steady_state"]
        steps = [(int(a_), int(b_), pr_, po_, sc_, "auto:steady_state") for a_, b_, pr_, po_, sc_ in detect_steps("steady_state", x, prm)]
        # v0.92.1：稳态分段要求过渡在 max_transient 周波内收敛到稳态——电机启动电流（I 口径尤甚）常衰减数秒，整个事件被丢掉；
        #          用双滑窗补充：其 onset 与已找到事件相距 > max(post_n, max_transient) 周波的才加入（同一次动作不重复）
        prm2 = ap["algorithms"]["two_window"]
        guard = max(post_n, int(prm.get("max_transient_cycles", post_n)))
        for a_, b_, pr_, po_, sc_ in detect_steps("two_window", x, prm2):
            if all(abs(int(a_) - s0[0]) > guard for s0 in steps):
                steps.append((int(a_), int(b_), pr_, po_, sc_, "auto:two_window"))
        steps.sort(key=lambda s0: s0[0])
        for onset, end, pre, post, score, src in steps:
            ef = event_features(p4, q4, i4, int(onset), int(end), pre_n, post_n)
            # v0.91.2：方向按合成电流有效值的变化判（RMS 恒正，启动必升、停止必降），不再按 P 判——P 的符号受 CT 极性 / 相别配对影响
            samples.append({**ef, "direction": "START" if ef["d_it"] >= 0 else "STOP", "onset": int(onset), "end": int(end),
                            "t_start": float(t[onset]), "t_start_local": fmt_local(float(t[onset])), "source": src})
        n_tw = sum(1 for s0 in steps if s0[5] == "auto:two_window")
        if n_tw:
            notes.append(f"自动定位：稳态分段漏掉的 {n_tw} 个事件由双滑窗补充（source=auto:two_window）——多为过渡过程长于 max_transient 的启动；其后窗若仍在过渡中，ΔI/ΔP 会偏大，建议加大 post 或给标签")
        mode = "auto"
        # v0.92：合并被稳态分段切碎的同一次动作（同方向连续出现、间隔 ≤ merge_gap_s；设备不可能不停就再启）
        if merge_gap_s and float(merge_gap_s) > 0 and len(samples) > 1:
            samples.sort(key=lambda s_: s_["onset"])
            kept: List[Dict[str, Any]] = []; merged = 0; last_t = None
            for s_ in samples:
                k_ = kept[-1] if kept else None
                if k_ is not None and k_["direction"] == s_["direction"] and (s_["t_start"] - last_t) <= float(merge_gap_s):
                    merged += 1; last_t = s_["t_start"]   # 以最后一段起点续算间隔（一串切片整体合并）
                    if abs(s_["d_it"]) > abs(k_["d_it"]):
                        kept[-1] = s_                     # 一组里保留 |ΔI| 最大的那次（小前导波动 / 分级带载的小级不代表设备）
                    continue
                kept.append(s_); last_t = s_["t_start"]
            if merged:
                samples = kept
                notes.append(f"自动定位：有 {merged} 个事件与前一事件同方向、间隔 ≤{float(merge_gap_s):g} s 且中间无反向事件，判为同一次动作被切碎 / 分级带载 / 反复重启，只保留 |ΔI| 最大的一个，已合并（merge_gap_s=0 可关闭）")
        notes.append(f"未提供启停标签：用稳态分段 + 自适应参数自动定位到 {len(samples)} 个事件（合并后）（幅值为正＝启动、为负＝停止），请核对事件明细")
    if not samples:
        raise ProfileError("没有定位到任何启停事件：请检查标签时刻 / 文件内容")
    # v0.91.2：一致性检查——方向与 ΔI 符号相反（标签时刻偏差 / 前后窗跨事件）、ΔP 与 ΔI 异号（P 极性可疑）
    n_dir = sum(1 for s_ in samples if (s_["d_it"] >= 0) != (s_["direction"] == "START") and abs(s_["d_it"]) > 1e-9)
    if n_dir:
        notes.append(f"{n_dir}/{len(samples)} 个事件的电流变化方向与归类方向相反（启动 ΔI<0 或停止 ΔI>0）：标签时刻偏差超过容差、或前后窗跨过了相邻事件，请复核标签 / 减小 post 窗")
    n_pol = sum(1 for s_ in samples if s_["vec"]["d_p"] * s_["d_it"] < 0 and abs(s_["vec"]["d_p"]) > 1e-6)
    if n_pol:
        notes.append(f"{n_pol}/{len(samples)} 个事件的 ΔP 与 ΔI 异号（有功为负）：CT 极性接反或电压/电流相别未配对（列映射），画像 ΔP/ΔQ 的符号与总线侧不一致将匹配不上；请核对接线 / 列映射，或改用 quantity=i")
    startup = fit_group([s for s in samples if s["direction"] == "START"])
    shutdown = fit_group([s for s in samples if s["direction"] == "STOP"])
    for name, g in (("启动", startup), ("停止", shutdown)):
        if g is None:
            notes.append(f"没有{name}事件样本：画像只含另一方向，总线侧只能辨识该方向")
        elif g["n"] < 3:
            notes.append(f"{name}画像只有 {g['n']} 次事件：σ 按相对下限（{int(_REL_FLOOR['d_p'] * 100)}% 中心值）给出，建议采集不同日期 / 工况的 ≥3 次独立启停（方案 §3.4）")
    # 稳态电平（设备 OFF / ON 时本侧 P 或 I）
    lv_off = float(np.median(x[:pre_n])) if x.size >= pre_n else float(x[0])
    doc = {"schema": PROFILE_SCHEMA, "device_id": str(device_id or "device"), "version": "1.0",
           "created": time.strftime("%Y-%m-%d %H:%M:%S"), "source_file": file, "label_mode": mode,
           "quantity": "p" if use_p else "i", "unit": "W" if use_p else "A", "fs": float(c.sampling.fs), "f_nom": cps,
           "n_cycle": int(feat.n_cycle), "pt_ct": {"enabled": bool(c.transform.enabled), "pt_ratio": float(c.transform.pt_ratio),
                                                   "ct_ratio": float(c.transform.ct_ratio)},
           "wiring": {"wiring": str(getattr(c.transform, "wiring", "3p4w")), "reconstruct_3w": bool(getattr(c.transform, "reconstruct_3w", False)),
                      "invert_current": bool(getattr(c.transform, "invert_current", False)), "invert_phases": str(getattr(c.transform, "invert_phases", "") or "")},   # v0.95
           "pre_cycles": pre_n, "post_cycles": post_n, "features": list(FEATURES), "feature_names": dict(FEATURE_NAMES),
           "template_points": TEMPLATE_POINTS, "cycles": int(t.size), "t_first": float(t[0]), "t_last": float(t[-1]),
           "steady": {"level_first_window": lv_off}, "startup": startup, "shutdown": shutdown, "notes": notes,
           "calibration": {"bus_mapping": None, "note": "无同步总线侧校准数据：总线侧只输出观测幅值，不估计设备贡献幅值（方案 §4/§7）"}}
    return validate_profile(doc)


def save_profile(doc: Dict[str, Any], path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    out = {k: v for k, v in doc.items() if not k.startswith("_")}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1); fh.write("\n")
    return path


def profile_summary(doc: Dict[str, Any]) -> Dict[str, Any]:
    """给界面 / summary 用的精简信息。"""
    def g(key):
        x = doc.get(key)
        return None if not x else {"n": x["n"], "mu": dict(zip(FEATURES, x["mu"])), "sigma": dict(zip(FEATURES, x["sigma"])),
                                   "dur_cycles": x.get("dur_cycles")}
    return {"device_id": doc.get("device_id"), "version": doc.get("version"), "created": doc.get("created"), "quantity": doc.get("quantity"),
            "unit": doc.get("unit"), "pre_cycles": doc.get("pre_cycles"), "post_cycles": doc.get("post_cycles"),
            "startup": g("startup"), "shutdown": g("shutdown"), "path": doc.get("_path"), "label_mode": doc.get("label_mode"),
            "source_file": doc.get("source_file"), "notes": list(doc.get("notes") or [])}
