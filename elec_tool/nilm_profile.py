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

import copy
import json
import math
import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

PROFILE_SCHEMA = "nilm_profile/1"
# v0.99.26：新增第 8 维 d_ih＝**谐波电流增量**（2~13 次谐波电流有效值的合量，事件后窗中位数 − 前窗中位数，A）。
#   动机（第 171/172 轮实测）：整流/变频类设备在总线上贡献约 +15 A 谐波电流（THD_I×I 从 16~18 A 升到 31~33 A），
#   而同功率的线性负荷（电阻/电机）几乎为 0——这是把"本设备"与"幅值相近的他负荷"分开的最强维度
#   （第 171 轮构造的"同功率 35 A/−23 kW 完全线性仿冒"在 7 维下 D²=0、置信度 1.0（必然误报）；加 d_ih 后 D²≈29、
#    置信度 0.16 < min_confidence 0.3 ⇒ 拒识。见 tests/test_r173_harmonic_multi_profile.py）。
#   新维度统一追加在末尾：旧画像（7 维）的 μ/σ 下标不变，加载后自动按"缺少的特征跳过"处理（见 profile_feature_names）。
FEATURES = ["d_ia", "d_ib", "d_ic", "d_p", "d_q", "peak_ratio", "dur_cycles", "d_ih"]
LEGACY_FEATURES = FEATURES[:7]                 # v0.99.26：v0.99.25 及更早生成的画像（无谐波维度）
FEATURE_NAMES = {"d_ia": "ΔIa (A)", "d_ib": "ΔIb (A)", "d_ic": "ΔIc (A)", "d_p": "ΔP (W)", "d_q": "ΔQ (var)",
                 "peak_ratio": "启动峰值比", "dur_cycles": "持续周波数", "d_ih": "Δ谐波电流 (A)"}
TEMPLATE_POINTS = 16
# σ 收缩下限：相对中心的比例（单次事件也能给出合理容差）与绝对下限（电流 A / 功率 W / 比值 / 周波）
_REL_FLOOR = {"d_ia": 0.15, "d_ib": 0.15, "d_ic": 0.15, "d_p": 0.15, "d_q": 0.25, "peak_ratio": 0.3, "dur_cycles": 0.5,
              "d_ih": 0.15}
# v0.92.5：dur_cycles 下限 2→5 周波（在线终点估计对噪声敏感，单样本画像 σ=2 时 10 周波偏差就贡献 25）
# v0.99.26：d_ih 相对下限 15%（与 ΔI 同口径；实测设备在运/停机谐波电流 30~33 A vs 16~18 A，事件间波动 ±15%）、
#   绝对下限 2 A（母线谐波电流测量的噪声量级，实测同站稳态 1 s 中位数抖动 < 1 A；低于 2 A 的差别不作为证据）
_ABS_FLOOR = {"d_ia": 0.02, "d_ib": 0.02, "d_ic": 0.02, "d_p": 5.0, "d_q": 5.0, "peak_ratio": 0.1, "dur_cycles": 5.0,
              "d_ih": 2.0}


class ProfileError(ValueError):
    pass


# ------------------------------------------------------------------ 事件特征
def _median(a: np.ndarray, fallback: float = 0.0) -> float:
    return float(np.median(a)) if a.size else float(fallback)


def event_features(p4: np.ndarray, q4: np.ndarray, i4: np.ndarray, onset: int, end: int,
                   pre_n: int, post_n: int, pre_lo: Optional[int] = None, post_hi: Optional[int] = None,
                   ih4: Optional[np.ndarray] = None) -> Dict[str, Any]:
    """候选事件（窗内索引 onset→end）的特征向量与归一化轨迹。p4/q4/i4：(4, L)，顺序 total, A, B, C。

    ``ih4``：v0.99.26 谐波电流（4, L，同顺序，单位 A，2~13 次谐波电流有效值合量）；为空时 d_ih 记 0
    （旧调用方 / 旧测试不带谐波数据，画像里该维的 μ 也是 0，贡献为 0）。

    * ΔIa/ΔIb/ΔIc/ΔP/ΔQ ＝ 事件后窗 [end, end+post_n) 中位数 − 事件前窗 [onset−pre_n, onset) 中位数（§5.4）；
    * ΔIh ＝ 同上口径的谐波电流变化（A，正＝事件后谐波电流更大）；
    * peak_ratio ＝ 事件窗内三相电流合成量相对事件前基线的最大偏移 / 稳态偏移（≥1；1＝无启动冲击）；
    * dur_cycles ＝ end − onset；
    * template ＝ [onset, end+post_n) 内合成电流相对事件前基线的变化 / 稳态变化，重采样到 TEMPLATE_POINTS 点。
    """
    L = p4.shape[1]
    a0, a1 = max(0, onset - pre_n), onset
    b0, b1 = min(end, L), min(end + post_n, L)
    # v0.99.24：前后窗被相邻变点截断（总线侧其它负荷在 pre/post 窗内投切时，窗取到别的台阶）；截断后长度不足则不截
    if pre_lo is not None and a0 < int(pre_lo) < a1 and (a1 - int(pre_lo)) >= max(10, pre_n // 10):
        a0 = int(pre_lo)
    _fl = max(10, post_n // 20)
    if post_hi is not None and b0 < int(post_hi) < b1 and (int(post_hi) - b0) >= _fl:
        b1 = int(post_hi)
    elif post_hi is not None and int(post_hi) <= b0 + _fl and int(post_hi) - onset >= _fl:
        # v0.99.25：相邻他负荷紧贴终点，[end, post_hi) 没有干净段 ⇒ 改取 post_hi 之前的最后 _fl 周波（宁可短，也不跨过他负荷）
        b0 = int(post_hi) - _fl; b1 = int(post_hi)
    if b0 >= b1:
        b0, b1 = min(end, L - 1), L
    pre = {"p": _median(p4[0, a0:a1], p4[0, max(0, onset - 1)]), "q": _median(q4[0, a0:a1], q4[0, max(0, onset - 1)]),
           "ia": _median(i4[1, a0:a1], i4[1, max(0, onset - 1)]), "ib": _median(i4[2, a0:a1], i4[2, max(0, onset - 1)]),
           "ic": _median(i4[3, a0:a1], i4[3, max(0, onset - 1)]), "it": _median(i4[0, a0:a1], i4[0, max(0, onset - 1)])}
    post = {"p": _median(p4[0, b0:b1]), "q": _median(q4[0, b0:b1]), "ia": _median(i4[1, b0:b1]), "ib": _median(i4[2, b0:b1]),
            "ic": _median(i4[3, b0:b1]), "it": _median(i4[0, b0:b1])}
    d_it = post["it"] - pre["it"]
    # v0.99.26：谐波电流增量（2~13 次合量）——设备是不是"谐波源"的直接证据，线性负荷约为 0
    d_ih = 0.0
    if ih4 is not None and getattr(ih4, "shape", (0, 0))[1] == L:
        h_pre = _median(ih4[0, a0:a1], float(ih4[0, max(0, onset - 1)]) if ih4.shape[1] else 0.0)
        h_post = _median(ih4[0, b0:b1], h_pre)
        d_ih = float(h_post - h_pre)
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
           "d_p": post["p"] - pre["p"], "d_q": post["q"] - pre["q"], "peak_ratio": peak_ratio, "dur_cycles": float(end - onset),
           "d_ih": float(d_ih)}
    thd_delta = float(d_ih / abs(d_it)) if abs(d_it) > 1e-12 else 0.0      # 增量 THD（诊断用，不参与 D²）
    return {"vec": vec, "template": [float(x) for x in template], "pre": pre, "post": post, "d_it": float(d_it),
            "d_ih": float(d_ih), "thd_delta": thd_delta}


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
            "template": [float(v) for v in tmpl], "template_spread": max(tspread, 0.25),   # v0.99.19：样本少时模板散布下限 0.25
            "dur_cycles": {"min": float(dur.min()), "max": float(dur.max()), "mean": float(dur.mean())},
            "events": [{"t_start": s.get("t_start"), "t_start_local": s.get("t_start_local"), "onset": s.get("onset"),
                        "end": s.get("end"), "vec": {k: float(v) for k, v in s["vec"].items()}, "source": s.get("source", "")}
                       for s in samples]}


def profile_feature_names(profile: Dict[str, Any]) -> List[str]:
    """画像实际包含的特征名（v0.99.26）。

    新画像 8 维（含 d_ih）；v0.99.25 及更早的画像只有前 7 维——旧画像必须**照旧可用**，
    因此维数以 μ 的长度为准，缺的特征在匹配时跳过（等价于该维不参与 D²），
    而不是把旧画像判为"特征定义不一致"拒绝加载（方案 §3.5 的版本检查改为"必须是当前 FEATURES 的前缀"）。
    """
    declared = profile.get("features")
    n_dec = len(declared) if isinstance(declared, (list, tuple)) and declared else 0
    # 以 μ 的实际长度为准：7 维旧画像（v0.99.25 及更早）即便头部声明的 features 被新版本改写成 8 项，
    #   也按 7 维解释；两者不一致时取较小者（多出来的维度没有 μ/σ，本来也无法参与计算）
    n_mu = 0
    for k in ("startup", "shutdown"):
        g = profile.get(k) or {}
        n_mu = max(n_mu, len(g.get("mu") or []))
    cands = [n for n in (n_dec, n_mu) if 1 <= n <= len(FEATURES)]
    if cands:
        return list(FEATURES[:min(cands)])
    return list(FEATURES)


# v0.99.27：无功序列「单独造候选」的画像无功份额下限 |ΔQ| / √(ΔP²+ΔQ²)。
#   低于它（纯电阻设备，ΔQ≈0）只把无功阶跃当**变点**用于截断前后窗，不造候选——否则任何电容投切都会越过 |ΔQ|/2 的门槛、
#   被当成这台设备的启停（误报）。1 个画像一条规则适用两侧，不跟 PT/CT、不跟检测量口径（P/I）绑定。
Q_CANDIDATE_SHARE_MIN = 0.1

# v0.99.27：每方向建议的最少启停样本数（σ 由样本估计；<3 个时只能取经验下限，界面 / CLI 统一提示）
MIN_EVENTS_PER_DIR = 3


def sample_size_notes(doc: Dict[str, Any]) -> List[str]:
    """v0.99.27：**样本量提示**（界面 / CLI 共用）。

    每方向建议 ≥ ``MIN_EVENTS_PER_DIR`` 次独立启停：
      * 1 个样本 ⇒ 标准差为 0，σ 完全靠 ``_REL_FLOOR`` / ``_ABS_FLOOR`` 托底（容差固定为 15 %/25 % …）；
      * 2 个样本 ⇒ σ 只有 1 个自由度，偶然一次差异会被放大成"很宽"或"很窄"的容差；
      * ≥3 个才有稳定的重复性估计（实测设备通常落到 2~5 %）。

    返回**给用户看的提示文本**（已含方向名），不满足时逐方向一条；两个方向都够则返回空列表。
    只读 ``doc["startup"/"shutdown"]["n"]``，因此**旧画像（7 维、v0.99.25 及更早）同样适用**。
    """
    out: List[str] = []
    for key, name in (("startup", "启动"), ("shutdown", "停止")):
        g = doc.get(key) or {}
        try:
            n = int(g.get("n") or 0)
        except (TypeError, ValueError):
            n = 0
        if n >= MIN_EVENTS_PER_DIR:
            continue
        if n <= 0:
            out.append(f"没有{name}事件样本（建议每方向 ≥{MIN_EVENTS_PER_DIR} 次启停）：画像只含另一方向，总线侧只能辨识该方向")
        else:
            out.append(f"{name}画像只有 {n} 次事件（建议每方向 ≥{MIN_EVENTS_PER_DIR} 次启停）：σ 取经验下限（ΔI/ΔP/ΔIh 15 %、ΔQ 25 % 与绝对下限），"
                       f"容差偏紧 ⇒ 现场噪声容易判成不匹配、幅值相近的他负荷也更容易被误认成同一设备"
                       f"（第 167 轮实录：单样本画像把他负荷两级下跌判成 STOP 0.46）；请补录不同日期 / 工况的启停后重新提取（方案 §3.4）")
    return out


def validate_profile(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(doc, dict) or doc.get("schema") != PROFILE_SCHEMA:
        raise ProfileError(f"画像文件 schema 不是 {PROFILE_SCHEMA}（当前 {doc.get('schema') if isinstance(doc, dict) else type(doc).__name__!r}）")
    if not doc.get("startup") and not doc.get("shutdown"):
        raise ProfileError("画像里既没有启动画像也没有停止画像")
    feats = doc.get("features")
    if feats is not None:
        if not isinstance(feats, (list, tuple)) or not all(isinstance(x, str) for x in feats) \
                or list(feats) != FEATURES[:len(feats)] or not (len(LEGACY_FEATURES) <= len(feats) <= len(FEATURES)):
            raise ProfileError(f"画像特征定义与本版本不一致：{feats}（本版本为 {FEATURES}；仅接受它的前缀，"
                               f"即 {len(LEGACY_FEATURES)} 维旧画像或 {len(FEATURES)} 维新画像）")
    names = profile_feature_names(doc)
    if len(names) < len(LEGACY_FEATURES):        # 少于 7 维：无法与任何版本对上
        raise ProfileError(f"画像特征数 {len(names)} 少于最低要求 {len(LEGACY_FEATURES)}（{LEGACY_FEATURES}）")
    for key in ("startup", "shutdown"):
        g = doc.get(key)
        if not g:
            continue
        if len(g.get("mu", [])) != len(names) or len(g.get("sigma", [])) != len(names):
            raise ProfileError(f"画像 {key}.mu/sigma 维数不对（{len(g.get('mu', []))}/{len(g.get('sigma', []))}，"
                               f"应为 {len(names)}＝{names}）")
        if any((not math.isfinite(float(v))) or float(v) <= 0 for v in g["sigma"]):
            raise ProfileError(f"画像 {key}.sigma 必须全为正有限数")
    doc["_features"] = list(names)          # 归一化后的实际维度（下划线键不进 save_profile）
    return doc


def load_profile(path: str, root: Optional[str] = None) -> Dict[str, Any]:
    p = path if os.path.isabs(path) else os.path.join(root or os.getcwd(), path)
    doc = _load_profile_raw(p)
    names = doc.get("_features") or profile_feature_names(doc)
    jd = names.index("dur_cycles") if "dur_cycles" in names else None
    for k in ("startup", "shutdown"):          # v0.92.5：旧画像的 σ 按当前绝对下限抬升
        g = doc.get(k)
        if g and jd is not None and len(g.get("sigma", [])) > jd:
            g["sigma"][jd] = max(float(g["sigma"][jd]), _ABS_FLOOR["dur_cycles"])
    pc = doc.get("pt_ct")
    if isinstance(pc, dict) and not bool(pc.get("enabled", True)):     # v0.99.23：旧画像「PT/CT 关闭」＝未换算 ⇒ PT=CT=1
        doc["pt_ct"] = {"enabled": True, "pt_ratio": 1.0, "ct_ratio": 1.0}
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
                     skip: Sequence[str] = (), feats: Optional[Sequence[str]] = None) -> Tuple[float, List[float]]:
    """对角马氏距离 D² 与各维贡献；Σ_λ = diag(σ²) + λ·median(σ²)·I（§5.5 收缩）。``skip``：不参与的特征名（v0.93：三相三线无 B 相电流时跳过 d_ib）。
    ``feats``：μ/σ 对应的特征名（v0.99.26：旧画像 7 维没有 d_ih，按下标与 FEATURES 前缀对齐）。"""
    names = list(feats) if feats else list(FEATURES)
    x = np.array([float(vec[k]) for k in names], dtype=np.float64)
    m = np.asarray(mu, dtype=np.float64); s = np.asarray(sigma, dtype=np.float64)
    var = s * s
    var = var + float(lam_rel) * float(np.median(var))
    contrib = (x - m) ** 2 / var
    for k in skip:
        if k in names:
            contrib[names.index(k)] = 0.0
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
    feats = profile_feature_names(profile)          # v0.99.26：旧画像 7 维、新画像 8 维（含 d_ih）
    skip = [k for k in skip if k in feats]
    d = max(1, len(feats) - len(skip))
    res: Dict[str, Any] = {}
    for key, name in (("startup", "START"), ("shutdown", "STOP")):
        g = profile.get(key)
        if not g:
            continue
        d2, contrib = mahalanobis_diag(vec, g["mu"], g["sigma"], lam_rel, skip, feats)
        td = template_distance(feat["template"], g["template"])
        res[name] = {"d2": d2, "contrib": contrib, "template_dist": td, "template_spread": float(g.get("template_spread", 0.3))}
    if not res:
        raise ProfileError("画像为空")
    best = min(res, key=lambda k: res[k]["d2"])
    other = [k for k in res if k != best]
    d2 = res[best]["d2"]
    conf = math.exp(-d2 / (2.0 * d))
    # 动态轨迹证据：轨迹 RMS 距离超过模板散布 3 倍时打折（基础版：L2，不做 DTW）
    td, sp = res[best]["template_dist"], max(res[best]["template_spread"], 0.25)   # v0.99.19：下限 0.1→0.25（见 build 注释）
    traj_penalty = 1.0 if td <= 3.0 * sp else max(0.3, 3.0 * sp / td)
    margin = (res[other[0]]["d2"] / d2) if (other and d2 > 0) else float("inf")
    return {"direction": best, "d2": d2, "d2_per_dim": d2 / d, "confidence": conf * traj_penalty, "margin": margin,
            "phase_map": mapping, "phase_map_auto": False,
            "template_dist": td, "traj_penalty": traj_penalty, "contrib": dict(zip(feats, res[best]["contrib"])),
            "d2_start": res.get("START", {}).get("d2"), "d2_stop": res.get("STOP", {}).get("d2")}



def transition_end(x: np.ndarray, onset: int, post_n: int, tgt: float, dlt: float, hi: Optional[int] = None) -> int:
    """v0.99.23：过渡结束点（统一规则，在线候选 / 标签定位 / 自动定位三处共用）。

    在 onset 之后的 post_n 周波上，先做长度 w 的滑动中值平滑（w≈post_n/20，3～25 周波），终点＝平滑轨迹**首次进入**
    事件后电平 ±20 %·|Δ| 带内并**连续保持 hold 周波**（hold≈post_n/10，3～250 周波）的那个周波（+1）；从未保持过则退回
    「最后一次越带的下一周波」。封顶 onset+post_n−1。

    背景：v0.92.2 的「最后一次越带」规则在总线侧对噪声极敏感——目标设备 35 A 停机的 20 % 带只有 7 A，其它负荷在 60 s 后窗里
    随便一次 ±7 A 的抖动就把终点推到几十秒之后（实录 dur 2161 周波 vs 画像 256，D² 贡献 221；后窗整体后移还把 ΔQ 量错，贡献 110），
    真停机因此被拒。平滑 + 保持能同时抵御冲击尖峰（会离开带、保持失败）与孤立抖动（被中值吸收）。"""
    L = x.size
    stop = onset + post_n if hi is None else min(onset + post_n, int(hi))   # v0.99.24：可被下一变点截断
    seg = x[onset:max(stop, onset + 2)]
    n = seg.size
    if n <= 1:
        return min(onset + 1, L - 1)
    band = 0.2 * abs(float(dlt))
    w = max(1, min(25, post_n // 20))
    if w > 1 and n >= w:
        from numpy.lib.stride_tricks import sliding_window_view
        sm = np.median(sliding_window_view(seg, w), axis=1)             # 长度 n−w+1，sm[k] 对应 seg[k:k+w]
    else:
        sm = seg
    inside = np.abs(sm - float(tgt)) <= band
    hold = max(3, min(250, post_n // 10))
    end = None
    if inside.size >= hold:
        # 连续 hold 个 True 的首个起点
        c = np.convolve(inside.astype(np.int32), np.ones(hold, dtype=np.int32), mode="valid")
        hit = np.nonzero(c >= hold)[0]
        if hit.size:
            end = onset + int(hit[0]) + 1
    if end is None:
        exc = np.nonzero(np.abs(seg - float(tgt)) > band)[0]
        end = onset + (int(exc[-1]) + 1 if exc.size else 1)
    end = min(end, onset + post_n - 1)
    return max(onset + 1, min(end, L - 1))


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
        sgn0 = delta[k0] >= 0
        while j < idx.size and exceed[j] and (delta[j] >= 0) == sgn0:   # v0.99.25：同向才算一段
            j += 1
        if j >= idx.size and (delta.size == 0 or (delta[-1] >= 0) == sgn0):
            break          # v0.92.5：超限游程顶到右边界＝后窗还没装满，峰值位置未定（在线会随新数据右移），等下一块再评估
        # v0.99.25：符号变了就从这里切开——先发生的同向过渡照样出候选（原来是 |Δ| 游程，后一个更大的反号事件会把前一个吞掉）
        pk = k0 + int(np.argmax(np.abs(delta[k0:j])))
        onset = int(idx[pk])
        # 终点：onset 之后「相对事件后电平的偏差 > 稳态偏差 20%」的最后一个周波的下一周波（过渡结束处），封顶 post_n
        #   v0.92.2：原为"首个进入 20% 带的周波"——斜坡 / 冲击型启动会在过渡中途就判终点，事件后窗落在过渡里，
        #   ΔP/ΔQ/ΔI 与画像（设备侧按稳态分段取过渡结束后）系统性不一致
        #   v0.99.23：改为 transition_end（平滑 + 首次进带并保持），三处共用，见其说明
        end = transition_end(x, onset, post_n, float(m_post[pk]), abs(float(delta[pk])))
        out.append((onset, min(end, L - 1), float(delta[pk])))
    return out


def change_points(x: np.ndarray, pre_n: int, post_n: int, min_d: float, k_sig: float) -> List[Tuple[int, float]]:
    """v0.99.24：窗内「其它变化」的位置与带符号幅值（用于截断候选的前后特征窗）。短双滑窗（w≈post/20，10～150 周波）、
    门槛＝max(¼ 候选门槛, k·σ)。"""
    w = max(10, min(150, post_n // 20))
    return [(o, d) for o, _e, d in _two_window_candidates(x, w, w, 0.25 * min_d, k_sig)]


def window_bounds(cps: Sequence[Tuple[int, float]], onset: int, end: int, pre_n: int, post_n: int,
                  delta: float = 0.0, dur_max: int = 0, peak_max: float = 1.0,
                  foreign: Sequence[int] = ()) -> Tuple[Optional[int], Optional[int]]:
    """候选 (onset,end) 的前窗下界 / 后窗上界：前一个变点（含其过渡）之后、下一个变点之前。

    后窗：onset 之后 1.5×dur_max（画像最长持续）以内的变点，若与候选**同号**且幅值不超过候选自身的 1.5 倍（慢斜坡 / 分级启动被
    短窗切成多个同向变点），或反号但幅值不超过 1.25×max(peak_max−1, 0.25)×|Δ|（启动冲击峰的回落、过冲的回摆——peak_max＝画像峰值比
    均值），视为候选自身过渡的一部分，不截断；其余变点（幅值更大的同号台阶、反号且幅值大、或超出该范围）都截断。前窗：任何变点都截断。
    v0.99.25：后窗边界以 **onset** 为基准判断（原来的 end 可能已经被污染的后窗中位数拉到下一个事件上，边界跟着失效）。
    v0.99.27：``foreign``＝**别的量**上的变点位置（如 I 口径下的 |ΔQ| 阶跃＝电容投切）。它们的幅值与候选不同量纲，
    不能参与"同号 / 幅值不超过 1.5 倍"这套比较（var 与 A 无法比大小）⇒ 只按时间判：超出候选自身过渡窗就截断。"""
    w = max(10, min(150, post_n // 20))
    fset = {int(c) for c in foreign}
    before = [c for c, _d in cps if c < onset - w]
    own_until = onset + int(1.5 * max(dur_max, 0)) + w
    # v0.99.27：别的量（无功）上的变点只按"短窗内"算同一次动作——候选自身的无功摆动（电机励磁涌流）只有几周波~几秒，
    #   不能沿用 dur_max（慢启停设备的 dur 可达 1200+ 周波≈25 s，会把 25 s 内的电容投切全当成"自己"的而不截断）。
    own_until_f = onset + w
    decay_lim = 1.25 * max(float(peak_max) - 1.0, 0.25) * abs(float(delta))

    cap = max(1.5 * abs(float(delta)), decay_lim)      # v0.99.25：同号但幅值远大于候选自身过渡 ⇒ 别的设备，照截

    def _own(c: int, d: float) -> bool:
        if c in fset:
            return c <= own_until_f                   # v0.99.27：无功变点只看短窗（见 own_until_f）
        if c > own_until:
            return False
        if abs(d) <= decay_lim:
            return True                               # 启动冲击峰回落 / 过冲回摆
        return ((d >= 0) == (delta >= 0)) and abs(d) <= cap
    after = [c for c, d in cps if c > onset + w and not _own(c, d)]   # v0.99.25：只看 onset 之后（终点本身可能是被污染的目标）
    pre_lo = (max(before) + w) if before else None
    post_hi = (min(after) - w) if after else None
    return pre_lo, post_hi


def detect_profile(p4: np.ndarray, q4: np.ndarray, i4: np.ndarray, profile: Dict[str, Any], prm: Dict[str, Any],
                   use_p: bool, device_state: str = "unknown", skip: Sequence[str] = (),
                   ih4: Optional[np.ndarray] = None) -> List[Dict[str, Any]]:
    """窗上运行一次画像匹配检测。返回按 onset 排序的候选结果列表（每项含 onset/end/pre/post/match/flags/accepted）。

    ``skip``：不参与匹配的特征名；三相三线两表法（transform.wiring=3p3w）本侧无 B 相电流，引擎传 ("d_ib",)，
    此时 ΔI 合成幅值也只按 A/C 两相计算。

    prm：``d2_max``（每维平均 D² 上限）、``min_confidence``、``k_sigma``（候选门槛的噪声倍数）、``margin``（最优 / 次优 D² 比下限）、
    ``lambda_rel``（协方差收缩）、``state_check``（1/0）、``max_scale``（v0.99.15：多尺度候选搜索的最大倍数，1＝只用画像 pre/post 单尺度）。
    候选的最小幅值＝画像里 |ΔP|（或 |ΔI 合成|）最小值的一半。

    多尺度（v0.99.15，v0.99.19 修正）：慢斜坡停机（如变频器减速 3 s 快降 + 25 s 指数尾）在 pre/post=10/50 周波的双滑窗里 1 s 内
    只能看到全幅的一小部分，达不到「画像幅值一半」门槛 ⇒ 没有候选。现在依次用 ×1、×2、×4 … ×max_scale 的前后窗各搜一遍，
    **多尺度只用于找候选**；同一事件在多个尺度命中时合并为一个候选，onset/end 取**最细命中尺度**的结果，特征一律按画像自身的
    pre/post 窗量——画像是用同样的 pre/post 在设备侧提取的，特征窗口几何必须一致才可比（v0.99.15 曾按最大尺度 post 窗量特征：
    慢停机在设备侧提取时 post=50 只量到快降段的部分幅值、σ 又只有 10 % 下限，总线侧按 ×8 窗量到接近全幅反而 D² 爆掉被拒）。
    返回项附 ``scale``（取几何的尺度；1＝原单尺度行为）、``scales_hit``。
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
    # v0.99.24：细尺度（÷2、÷4 … 到 min_scale）——画像前后窗很长（慢启停设备 pre/post=3000）时，总线上相邻 60 s 内其它负荷的
    #   投切会和目标事件落进同一个「超限游程」，只留一个峰（幅值最大的那个），目标事件根本成不了候选（实录：+60 A 他负荷
    #   58 s 后设备 +35 A 斜坡启动、16 s 后 −70 A 他负荷，整段只报了 +60 A 那个）。细尺度窗短，相邻事件各自成游程。
    min_scale = float(prm.get("min_scale", 0.25))
    scales: List[float] = []
    sc = 1.0
    while sc >= min_scale and max(pre_n, post_n) * sc >= 10:
        scales.insert(0, sc); sc /= 2.0
    sc = 2.0
    while sc <= max_scale:
        scales.append(sc); sc *= 2.0
    merged: List[Dict[str, Any]] = []            # {onset, end, delta, scale}
    for sc in scales:
        wp, wq = max(5, int(round(pre_n * sc))), max(5, int(round(post_n * sc)))
        for onset, end, delta in _two_window_candidates(x, wp, wq, min_d, k_sig):
            hit = None
            for g in merged:                      # 与已有候选重叠 ⇒ 同一事件；容差按**已有（更细）候选**的尺度，粗尺度游程不吞并相邻细候选
                if (delta >= 0) != (g["delta"] >= 0):
                    continue                      # v0.99.25：反号＝两次方向相反的动作，绝不能并成一个候选
                tol = int(post_n * min(sc, g["scale"]))
                if g["onset"] - tol <= onset <= g["end"] + tol:
                    hit = g; break
            if hit is None:
                merged.append({"onset": onset, "end": end, "delta": delta, "scale": sc, "scales_hit": [sc]})
            else:                                 # 尺度升序扫描：先命中的（更细）保留几何与幅值
                hit["scales_hit"].append(sc)      # v0.99.25：幅值不再被更粗尺度覆盖（粗尺度后窗可能已经吃进下一个反号事件，符号会把整段几何带偏）
    # ------------------------------------------------------------------ v0.99.27：无功序列（纯无功阶跃）
    # **问题**（第 172 轮实录）：`detect_profile` 只对检测量那一条序列（P 口径＝p4[0]、I 口径＝i4[0]）跑候选与 change_points，
    #   而电容组投切 / SVG 动作是**纯无功阶跃**——它在 P 上几乎不动、在三相合成电流上也只动一点点。后果两条：
    #   ① 它不成候选 ⇒ 一个无功型设备（电容器、SVG、空压机卸载）的启停在 I 口径下根本看不见；
    #   ② 它不成"变点"⇒ 候选的前后窗把它整个吃进去（干净窗 ΔQ −0.33 kvar，实际取到 −25.8 kvar，画像 d_q 彻底对不上）。
    # **改法**：把 q4[0] 作为**第二条搜索序列**并联进来——
    #   * 变点：Q 上的变点进 `change_points` 结果，参与截断前后窗（与 x 上的变点按时间合并，同位置视为同一次动作）；
    #   * 候选：Q 上也能出候选（不与 x 候选重叠时），几何按 Q 序列自己的 `transition_end` 定；
    #   * 两条序列单位不同（W 或 A vs var），**幅值绝不可比**：`window_bounds` 里把它们互为 `foreign`，只按时间截断。
    #   * 只有画像本身有可观的无功份额（|ΔQ| / √(ΔP²+ΔQ²) ≥ 10 %）才允许 Q 单独造候选——纯电阻设备 ΔQ≈0 时，
    #     任何电容投切都会越过它 |ΔQ|/2 的门槛，全被当成它的启停，那是误报。
    iq = FEATURES.index("d_q"); ip_ = FEATURES.index("d_p")
    p_amp = [abs(float(g["mu"][ip_])) for g in groups if g.get("mu") and len(g["mu"]) > ip_]
    q_amp = [abs(float(g["mu"][iq])) for g in groups if g.get("mu") and len(g["mu"]) > iq]
    q_sig: Optional[np.ndarray] = None
    q_cps: List[Tuple[int, float]] = []
    min_d_q = _ABS_FLOOR["d_q"]
    q_use = False
    if q4 is not None and q4.shape[1] == x.size and float(np.ptp(q4[0])) > 0.0 and q_amp:
        q_sig = q4[0]
        # 门槛＝画像 |ΔQ| 的一半；但**不能为 0**：q 很干净时局部方差 → 0，thr=0 会把"零变化"的窗口也判成变点
        #   （合成例：台阶后第一段平台的 delta 恰为 0，照样 >= 0 ⇒ 冒出一个假变点把候选后窗截短）。用 _ABS_FLOOR 托底。
        min_d_q = max(0.5 * min(q_amp), _ABS_FLOOR["d_q"])
        q_cps = change_points(q_sig, pre_n, post_n, min_d_q, k_sig)
        q_share = max(q_amp) / max(1e-12, math.hypot(max(p_amp) if p_amp else 0.0, max(q_amp)))
        q_use = q_share >= Q_CANDIDATE_SHARE_MIN     # 无功份额不足 ⇒ 只当"变点"用，不单独造候选
        if q_use:
            for sc in scales:
                wp, wq = max(5, int(round(pre_n * sc))), max(5, int(round(post_n * sc)))
                for onset, end, delta_q in _two_window_candidates(q_sig, wp, wq, min_d_q, k_sig):
                    hit = None
                    for g in merged:                 # 与 x 上的候选重叠 ⇒ 同一次动作：沿用 x 候选（幅值 / 量纲以检测量为准）
                        tol = int(post_n * min(sc, g["scale"]))
                        if g["onset"] - tol <= onset <= g["end"] + tol:
                            hit = g; break
                    if hit is None:
                        merged.append({"onset": onset, "end": end, "delta": delta_q, "scale": sc, "scales_hit": [sc], "from_q": True})
    merged.sort(key=lambda g: g["onset"])
    cands = [(g["onset"], g["end"], g["delta"], g["scale"], g["scales_hit"], bool(g.get("from_q"))) for g in merged]
    cps = change_points(x, pre_n, post_n, min_d, k_sig)                     # v0.99.24：相邻变点截断特征窗
    # 两套量纲的变点各自成"主"列表，另一套的位置作为 foreign（只按时间截断，见 window_bounds）
    w_cp = max(10, min(150, post_n // 20))
    x_pos = [c for c, _d in cps]
    q_pos = [c for c, _d in q_cps]
    q_only = [int(o) for o in q_pos if not any(abs(o - c) <= w_cp for c in x_pos)]
    x_only = [int(c) for c in x_pos if not any(abs(o - c) <= w_cp for o in q_pos)]
    fused_x = sorted(list(cps) + [(o, 0.0) for o in q_only], key=lambda t: t[0])
    fused_q = sorted(list(q_cps) + [(o, 0.0) for o in x_only], key=lambda t: t[0])
    dur_max = max([int((g.get("dur_cycles") or {}).get("max", 0) or 0) for g in groups] + [0])
    _pk = FEATURES.index("peak_ratio")
    peak_max = max([float(g["mu"][_pk]) for g in groups if g.get("mu")] + [1.0])
    d2_max = float(prm.get("d2_max", 9.0)); min_conf = float(prm.get("min_confidence", 0.3))
    margin_min = float(prm.get("margin", 1.5)); lam = float(prm.get("lambda_rel", 0.1))
    state_check = int(float(prm.get("state_check", 1))) != 0
    pmap = phase_map_code(prm.get("phase_map", 1))                      # v0.99.6：总线 / 设备侧相序映射
    out: List[Dict[str, Any]] = []
    state = device_state
    for onset, end, delta, sc, hits, from_q in cands:
        xs = (q_sig if q_sig is not None else x) if from_q else x
        if from_q and q_sig is not None:
            pre_lo, post_hi = window_bounds(fused_q, onset, end, pre_n, post_n, delta, dur_max, peak_max, x_only)
        else:
            pre_lo, post_hi = window_bounds(fused_x, onset, end, pre_n, post_n, delta, dur_max, peak_max, q_only)
        if sc < 1:
            # v0.99.24：细尺度找到的候选，其终点是按短后窗（post·sc）定的——慢斜坡在短窗里的「目标电平」是坡中值，终点会定在坡的前段；
            #   这里按画像自身 post 几何（并受下一变点截断）重算终点，使 dur / 后窗与画像提取时同一规则
            a0 = max(0, onset - pre_n) if pre_lo is None else max(0, onset - pre_n, int(pre_lo))
            b1 = onset + post_n if post_hi is None else min(onset + post_n, int(post_hi))
            if b1 - onset >= 2 and onset - a0 >= 1:
                tgt = float(np.median(xs[onset:b1])); dl = tgt - float(np.median(xs[a0:onset]))
                end = transition_end(xs, onset, post_n, tgt, abs(dl), hi=post_hi)
        floor_post = max(10, post_n // 20)
        gap_post = (int(post_hi) - int(end)) if post_hi is not None else post_n
        crowded = post_hi is not None and gap_post < floor_post                       # 干净后窗偏短：记标志并改用 post_hi 前 floor_post 周波（v0.99.25）
        feat = event_features(p4, q4, i4, onset, end, pre_n, post_n, pre_lo, post_hi, ih4)   # v0.99.19：特征窗口与画像提取一致；v0.99.24：相邻变点截断；v0.99.26：谐波电流
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
        # v0.99.25：量出来的 Δ 与搜索到的 Δ 反号。v0.99.27：Q 序列上的候选只能跟 **ΔQ** 比符号（var vs A/W 不可比）
        d_meas = (float(feat["vec"]["d_q"]) if from_q else (float(feat["vec"]["d_p"]) if use_p else float(feat["d_it"])))
        if abs(float(delta)) > 1e-9 and abs(d_meas) > 1e-9 and (float(delta) > 0) != (d_meas > 0):
            flags.append("sign_flip")                 # ＝前后窗取错了（跨过了相邻的另一次动作），不是本设备的动作
        if crowded:
            flags.append("window_crowded")            # 相邻他负荷紧贴终点：后窗只能取很短的一段（仍按这一段量，D²/置信度照常把关）
        accepted = ("d2_exceeds" not in flags) and ("sign_flip" not in flags) and conf >= min_conf
        status = "confirmed" if accepted and not flags else ("low_confidence" if accepted else "rejected")
        if accepted:
            state = "on" if m["direction"] == "START" else "off"
        out.append({"onset": onset, "end": end, "delta": delta, "feat": feat, "match": m, "confidence": conf, "source": "q" if from_q else "x",
                    "flags": flags, "accepted": accepted, "status": status, "scale": (int(sc) if sc >= 1 else float(sc)),
                    "scales_hit": [(int(x) if x >= 1 else float(x)) for x in hits],
                    "post_wait": int(post_n), "pre_lo": pre_lo, "post_hi": post_hi})
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
    end = transition_end(x, best, post_n, float(np.median(x[best:best + post_n])), abs(delta))   # v0.99.23：与在线候选同一规则
    return best, end, delta


def load_cycles(cfg, file: str, *, max_cycles: int = 400000, t_start: str = "", t_end: str = "", custom_time: bool = False,
                custom_time_start: str = "", custom_time_end: str = ""):
    """读取设备侧文件为逐周波序列。返回 (c, feat, t, p4, q4, i4, ih4, u_nonzero)；``cfg`` 不被修改。
    v0.99.26：新增 ih4（4, N）＝逐周波谐波电流（2~13 次合量，A）。旧调用方按 7 元组解包需同步（tools 里已改）。"""
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
    ts, ps, qs, is_, hs = [], [], [], [], []          # v0.99.26：hs＝逐周波谐波电流
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
                ts.append(f["t"]); ps.append(f["p"]); qs.append(f["q"]); is_.append(f["i"])
                hs.append(f["ih"] if f.get("ih") is not None else np.zeros((4, f["t"].size))); n += int(f["t"].size)
            if n >= max_cycles:
                break
    if not ts:
        raise ProfileError("没有读到整周波数据")
    t = np.concatenate(ts)[:max_cycles]; p4 = np.concatenate(ps, axis=1)[:, :max_cycles]
    q4 = np.concatenate(qs, axis=1)[:, :max_cycles]; i4 = np.concatenate(is_, axis=1)[:, :max_cycles]
    ih4 = np.concatenate(hs, axis=1)[:, :max_cycles]          # v0.99.26：逐周波谐波电流（画像第 8 维 d_ih 的来源）
    return c, feat, t, p4, q4, i4, ih4, u_nonzero


def build_profile(cfg, file: str, *, device_id: str = "device", labels: Optional[str] = None, label_tol_s: float = 2.0,
                  pre_cycles: int = 10, post_cycles: int = 50, max_cycles: int = 400000, quantity: Optional[str] = None,
                  t_start: str = "", t_end: str = "", custom_time: bool = False, custom_time_start: str = "",
                  custom_time_end: str = "", merge_gap_s: float = 10.0) -> Dict[str, Any]:
    """从设备侧文件构建画像。``merge_gap_s``（v0.92，仅自动定位模式）：同方向、中间没有反向事件、起点间隔 ≤ 该秒数的
    相邻事件视为同一次动作被稳态分段切碎（或启动后的分级带载 / 反复重启），只保留 |ΔI| 最大的一个；0＝不合并。``cfg``＝基准配置（PT/CT、fs、列映射，不被修改）。``labels``＝标签文本（空＝自动用稳态分段 +
    自适应参数找启停事件：幅值为正＝启动、为负＝停止）。返回画像文档（含 ``events`` 明细与 ``notes``）。"""
    c, feat, t, p4, q4, i4, ih4, u_nonzero = load_cycles(cfg, file, max_cycles=max_cycles, t_start=t_start, t_end=t_end, custom_time=custom_time,
                                                   custom_time_start=custom_time_start, custom_time_end=custom_time_end)
    from .nilm import HARM_ORDERS, detect_steps
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
            ef = event_features(p4, q4, i4, onset, end, pre_n, post_n, ih4=ih4)
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
            # v0.99.23：终点不再沿用 steady_state / two_window 各自的终点定义，统一按 transition_end（与总线侧在线候选同一规则），
            #   否则 dur_cycles 在两侧按不同规则量出、不可比
            onset = int(onset)
            if onset + 2 <= x.size:
                tgt_ = float(np.median(x[onset:onset + post_n])); dl_ = tgt_ - float(np.median(x[max(0, onset - pre_n):onset]))
                end = transition_end(x, onset, post_n, tgt_, abs(dl_))
            ef = event_features(p4, q4, i4, int(onset), int(end), pre_n, post_n, ih4=ih4)
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
    # v0.99.27：样本量提示集中到 sample_size_notes()（提取结果 / 画像加载 / 界面 / CLI 用同一段文字）
    notes.extend(sample_size_notes({"startup": startup, "shutdown": shutdown}))
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
           "harmonic": {"orders": [int(k) for k in HARM_ORDERS], "unit": "A", "feature": "d_ih",
                        "note": "2~13 次谐波电流有效值合量（ΣI_k² 开方，A）；特征是事件前后之差（三相平均＝每相口径，线性可加）；设备是不是谐波源的指纹，线性负荷≈0"},
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
    names = profile_feature_names(doc)          # v0.99.26：旧画像 7 维 / 新画像 8 维
    def g(key):
        x = doc.get(key)
        return None if not x else {"n": x["n"], "mu": dict(zip(names, x["mu"])), "sigma": dict(zip(names, x["sigma"])),
                                   "dur_cycles": x.get("dur_cycles")}
    return {"device_id": doc.get("device_id"), "version": doc.get("version"), "created": doc.get("created"), "quantity": doc.get("quantity"),
            "unit": doc.get("unit"), "pre_cycles": doc.get("pre_cycles"), "post_cycles": doc.get("post_cycles"),
            "startup": g("startup"), "shutdown": g("shutdown"), "path": doc.get("_path"), "label_mode": doc.get("label_mode"),
            "source_file": doc.get("source_file"), "notes": list(doc.get("notes") or []),
            "features": list(names), "has_harmonic": "d_ih" in names,
            # v0.99.27：每方向 <3 个样本时给出界面提示（提取结果 与 画像匹配状态行都用这一份）
            "min_events": MIN_EVENTS_PER_DIR, "sample_notes": sample_size_notes(doc),
            "harmonic": dict(doc.get("harmonic") or {}) if "d_ih" in names else {},
            "stage": dict(doc.get("stage") or {})}


# ------------------------------------------------------------------ 档位（多档位 / 变频设备的画像补救）
# v0.99.28（第 179 轮）：**多档位设备只录到部分档位时怎么办**。三个后果都来自"画像只代表被录到的那一档"：
#   ① 候选门槛 `min_d = 0.5·min(|ΔP| 或 |ΔI合成|)` 取自画像幅值 ⇒ **低于 0.5× 录制档位的档位连候选都不生成**（静默漏报）；
#   ② 0.5~0.7× 能成候选但被 `min_confidence` 拒（实测单档画像的可接受区间是 **0.70~1.30×**，见 `stage_window`）；
#   ③ 把不同档位的事件混进同一份画像最糟：μ 落在两档之间（一个不存在的档位）、σ 涨到 40~60 %，
#      接受区间被拉成 0.1~1.4×，"同幅值纯线性假负荷"会被判成确认（实测 conf 0.43）。
# 补救：**派生档位画像**——把已录档位的画像按倍数 k 同比缩放出一组"假设画像"（JSON 里写 `stage` 说明来源与假设），
#   用 `nilm.profile_path` 的 `;` 列表一起加载。窗口 0.70~1.30× ⇒ 网格间距 1.30/0.70 = 1.857 时正好
#   "无缝且不重叠"（同一事件不会被两份画像重复报出）。派生只缩放幅度量纲维，`peak_ratio`（比值）保持，
#   `dur_cycles` 默认保持（σ 已有 50 % 下限：实测按 k 缩与不缩，D²/维 只差 0.1~0.4）。
STAGE_GRID_RATIO = 1.857                         # 1.30/0.70：档位窗口"无缝且不重叠"的唯一间距
STAGE_AMP_FEATURES = ("d_ia", "d_ib", "d_ic", "d_p", "d_q", "d_ih")   # 随档位同比缩放的维


def _stage_amp(group: Dict[str, Any], names: Sequence[str], use_p: bool) -> float:
    """画像幅值（与 `detect_profile` 的候选门槛同口径）：P 口径取 |ΔP|，I 口径取三相 ΔI 合成。"""
    mu = group.get("mu") or []
    if use_p:
        j = names.index("d_p") if "d_p" in names else None
        return abs(float(mu[j])) if j is not None and len(mu) > j else 0.0
    return float(math.sqrt(sum(float(mu[names.index(k)]) ** 2 for k in ("d_ia", "d_ib", "d_ic") if k in names and len(mu) > names.index(k))))


def _stage_vec(group: Dict[str, Any], names: Sequence[str], k: float, q_mode: str = "scale", ih_exp: float = 1.0,
               dur_exp: float = 0.0) -> Dict[str, float]:
    """把一份画像的 μ 按档位倍数 k 缩放成"合成事件"特征向量（peak 不动）。"""
    mu = list(group.get("mu") or [])
    out: Dict[str, float] = {}
    for i, f in enumerate(names):
        m = float(mu[i])
        if f in ("d_ia", "d_ib", "d_ic", "d_p"):
            out[f] = m * k
        elif f == "d_q":
            out[f] = m if str(q_mode) == "const" else m * k
        elif f == "d_ih":
            out[f] = m * (k ** float(ih_exp))
        elif f == "dur_cycles":
            out[f] = m * (k ** float(dur_exp))
        else:
            out[f] = m
    return out


def stage_window(doc: Dict[str, Any], *, lam_rel: float = 0.1, d2_max: float = 9.0, min_confidence: float = 0.3,
                 k_min: float = 0.05, k_max: float = 3.0, step: float = 0.01, q_mode: str = "scale",
                 ih_exp: float = 1.0, dur_exp: float = 0.0) -> Dict[str, Any]:
    """该画像能接受的**档位倍数区间**（相对画像里录到的档位）＋候选门槛对应的档位。

    把画像自己的 μ 按 k 同比缩放成合成事件，走真实 ``match_event`` 判接受 —— 与线上判定完全同口径
    （含 σ 收缩 λ、``d2_max``、``min_confidence``、相序），所以是"这份画像到底认几档"的实测值，不是经验值。

    返回 ``{k_lo, k_hi, k_gate, min_d, amp, unit, probes}``：
      * ``k_lo~k_hi``：特征空间能接受的档位区间（本机 8 维、I 口径实测 **0.70~1.30**）；
      * ``k_gate``：低于它**连候选都不会生成**（``min_d`` 门槛）——静默漏报区；
      * ``k_lo~k_gate`` 之间：能成候选但会被拒（诊断 CSV 里能看到 `d2_exceeds`）。
    """
    names = profile_feature_names(doc)
    use_p = str(doc.get("quantity") or "i").strip().lower() == "p"
    amps = [a for a in (_stage_amp(doc[key], names, use_p) for key in ("startup", "shutdown") if doc.get(key)) if a > 0]
    amp = max(amps) if amps else 0.0
    min_d = 0.5 * min(amps) if amps else 0.0
    lo = hi = None
    n = int(round((k_max - k_min) / step)) + 1
    for j in range(n):
        k = round(k_min + j * step, 6)
        best = None
        for key in ("startup", "shutdown"):
            g = doc.get(key)
            if not g:
                continue
            vec = _stage_vec(g, names, k, q_mode, ih_exp, dur_exp)
            r = match_event(doc, {"vec": vec, "template": list(g.get("template") or [])}, lam_rel, (), 1)
            if best is None or r["d2"] < best["d2"]:
                best = r
        if best is None:
            continue
        ok = (best["d2_per_dim"] <= float(d2_max)) and (best["confidence"] >= float(min_confidence))
        if ok and lo is None:
            lo = k
        if ok:
            hi = k
    return {"k_lo": lo, "k_hi": hi, "k_gate": (round(min_d / amp, 3) if amp > 0 else None), "min_d": round(min_d, 4),
            "amp": round(amp, 4), "unit": str(doc.get("unit") or ("W" if use_p else "A")), "probes": n}


def derive_stage_profile(doc: Dict[str, Any], scale: float, *, q_mode: str = "scale", ih_exp: float = 1.0,
                         dur_exp: float = 0.0, device_id: Optional[str] = None) -> Dict[str, Any]:
    """按档位倍数 ``scale`` 派生一份**假设**画像（该档位没有实录，用已录档位同比缩放）。

    * μ/σ 的幅度维（ΔIa/ΔIb/ΔIc/ΔP/ΔQ/ΔIh）同乘 ``scale``（``q_mode="const"`` 时 ΔQ 不动；
      ``ih_exp`` 可把谐波维改成 ``k**ih_exp``，轻载 THD 升高时取 0.7~0.9 更接近实际）；
    * σ 再按 ``_REL_FLOOR`` / ``_ABS_FLOOR`` 抬回下限（低档位时绝对下限会接管，容差不会过窄）；
    * ``peak_ratio`` 保持（比值，与档位无关）；``dur_cycles`` 默认保持（σ 有 50 % 下限兜底，``dur_exp`` 可改）；
    * 原始事件的 ``events`` 明细**丢弃**（它记录的是被录档位的事件，缩放后会引起误会），只留 ``n``；
    * 写 ``stage`` 字段说明"派生自哪份画像、哪个倍数、什么假设"——**不是实测**，界面 / 报告里要显式提示。
    """
    k = float(scale)
    if not (0.05 <= k <= 20.0):
        raise ProfileError(f"档位倍数不合理：{k:g}（应在 0.05~20 之间，相对**画像里录到的那一档**）")
    names = profile_feature_names(doc)
    out = copy.deepcopy(doc)
    base = str(doc.get("device_id") or "device")
    out["device_id"] = str(device_id or f"{base}@{round(k * 100):g}%")
    for key in ("startup", "shutdown"):
        g = out.get(key)
        if not g:
            continue
        mu = [float(v) for v in g.get("mu") or []]
        sg = [float(v) for v in g.get("sigma") or []]
        vec = _stage_vec(g, names, k, q_mode, ih_exp, dur_exp)
        mu2 = [float(vec[f]) for f in names]
        sg2 = []
        for i, f in enumerate(names):
            ratio = (mu2[i] / mu[i]) if abs(mu[i]) > 1e-12 else 1.0
            s2 = max(abs(sg[i]) * abs(ratio), _REL_FLOOR[f] * abs(mu2[i]), _ABS_FLOOR[f])
            sg2.append(float(s2))
        g["mu"] = mu2
        g["sigma"] = sg2
        if dur_exp and isinstance(g.get("dur_cycles"), dict):
            g["dur_cycles"] = {kk: float(vv) * (k ** float(dur_exp)) for kk, vv in g["dur_cycles"].items()}
        g.pop("events", None)                       # 原始事件明细属于被录档位，缩放后不再成立
    notes = list(out.get("notes") or [])
    notes.append(f"档位派生（v0.99.28）：按 k={k:g}×（相对画像 {base} 录到的档位）缩放，"
                 f"q_mode={q_mode}、ih_exp={ih_exp:g}、dur_exp={dur_exp:g}。**该档位没有实录**，"
                 f"μ/σ 是按倍数外推的假设值；上总线前请用该档的真实启停复核 `nilm_profile_diag`/候选 CSV 的 `c_*`。")
    out["notes"] = notes
    out["stage"] = {"derived_from": base, "scale": k, "q_mode": str(q_mode), "ih_exp": float(ih_exp),
                    "dur_exp": float(dur_exp), "basis": "image",
                    "note": "由已录档位画像按倍数派生的假设画像，无该档实录；混档提取（多档事件进同一份画像）会把 μ 拉到两档之间、σ 放大，禁止"}
    return validate_profile(out)


def stage_grid_ratio(doc: Dict[str, Any], **kw: Any) -> float:
    """该画像的"无缝且不重叠"网格间距 ＝ **实测**接受窗口 ``k_hi / k_lo``（不是常数）。

    本机实测量：真实 8 维画像 0.70~1.30 ⇒ 1.857；小样本 / 高噪声画像窗口更窄（如 0.73~1.27 ⇒ 1.74），
    用固定 1.857 会留缝 —— 所以网格间距一律按调用方画像的实测窗口算。
    """
    w = stage_window(doc, **kw)
    lo, hi = w.get("k_lo"), w.get("k_hi")
    if not lo or not hi or float(hi) <= float(lo):
        return float(STAGE_GRID_RATIO)
    return float(hi) / float(lo)


def derive_stage_profiles(doc: Dict[str, Any], scales: Optional[Sequence[float]] = None, *, count: int = 5,
                          center: float = 1.0, ratio: Optional[float] = None, **kw: Any) -> List[Dict[str, Any]]:
    """派生一组档位画像。``scales`` 给定则照它派生；否则按"阶梯"生成 ``count`` 份（见 ``derive_stage_ladder``）。

    ``ratio`` 给定时退化为等比网格（间距 ``ratio``，用于"我就要固定间距"的场合）；不给则用阶梯——
    因为**每份派生画像自己的窗口宽度不一样**（低档位的 σ 会被绝对下限接管，窗口更宽），固定间距会重叠或留缝。
    """
    if scales is not None:
        return [derive_stage_profile(doc, float(k), **kw) for k in scales]
    if ratio:
        c = int(max(1, count)); half = (c - 1) / 2.0
        return [derive_stage_profile(doc, float(center) * (float(ratio) ** (j - half)), **kw) for j in range(c)]
    return derive_stage_ladder(doc, count=count, center=center, **kw)


def _window_ratio(w: Dict[str, Any]) -> float:
    """窗口上下界之比＝"无缝且不重叠"的档位间距（窗口 0.70~1.30 ⇒ 1.857）。"""
    lo, hi = w.get("k_lo"), w.get("k_hi")
    if not lo or not hi or float(hi) <= float(lo):
        return float(STAGE_GRID_RATIO)
    return float(hi) / float(lo)


def derive_stage_ladder(doc: Dict[str, Any], *, count: int = 5, center: float = 1.0, **kw: Any) -> List[Dict[str, Any]]:
    """从 ``center`` 档出发，按**每份派生画像实测的接受窗口**向两侧接力铺开 ``count`` 份。

    摆放规则（向上为例）：新档位 ``k_new`` 使"新画像窗口的下界"正好落在"上一份画像窗口的上界"上 ——
    ``k_new · k_lo(k_new) = k_prev · k_hi(prev)``。因为窗口宽度随档位变化（低档位的 σ 被绝对下限接管、窗口更宽），
    这里对 ``k_new`` 做 3 次不动点迭代收敛。结果：相邻两份的接受区间**首尾相接**，既不漏档、也不重复报。
    """
    c = int(max(1, count))
    half = (c - 1) // 2
    wkw = {k: v for k, v in kw.items() if k in ("lam_rel", "d2_max", "min_confidence", "q_mode", "ih_exp", "dur_exp")}
    base = derive_stage_profile(doc, float(center), **kw)
    out: List[Dict[str, Any]] = [base]

    def _place(cur: Dict[str, Any], up: bool) -> Dict[str, Any]:
        w_cur = stage_window(cur, **wkw)
        if not w_cur.get("k_lo") or not w_cur.get("k_hi"):
            k = float(cur["stage"]["scale"]) * (float(STAGE_GRID_RATIO) if up else 1.0 / float(STAGE_GRID_RATIO))
            return derive_stage_profile(doc, k, **kw)
        edge = float(cur["stage"]["scale"]) * (float(w_cur["k_hi"]) if up else float(w_cur["k_lo"]))
        k = float(cur["stage"]["scale"]) * (_window_ratio(w_cur) if up else 1.0 / _window_ratio(w_cur))   # 初值：按上一份的窗口比
        sub = derive_stage_profile(doc, k, **kw)
        for _ in range(3):                              # 不动点：让新画像自己的窗口贴住上一份的边界
            w = stage_window(sub, **wkw)
            if not w.get("k_lo") or not w.get("k_hi"):
                break
            k2 = edge / (float(w["k_lo"]) if up else float(w["k_hi"]))
            if abs(k2 - k) <= 1e-6:
                break
            k = k2
            sub = derive_stage_profile(doc, k, **kw)
        return sub

    cur = base
    for _ in range(half):                                         # 向上（更大档位）
        cur = _place(cur, True); out.append(cur)
    cur = base
    for _ in range(c - 1 - half):                                 # 向下（更小档位）
        cur = _place(cur, False); out.append(cur)
    return sorted(out, key=lambda g: float((g.get("stage") or {}).get("scale") or 0.0))


