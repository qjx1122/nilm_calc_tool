"""v0.61：数据处理页「波形预览」——离线波形 CSV 的文件信息 / 原始波形加载 / 逐周波有效值曲线。

三个纯函数，都在**配置副本**上操作（PT/CT、列映射、时标解释取自给定的基准配置），不改运行配置、不启动引擎、不落盘：

- :func:`file_info`      通道数（表头映射到的 Ua/Ub/Uc/Ia/Ib/Ic）、采样率（由时标推算，推算不出时用配置值）、行数、时长、起止时间
- :func:`load_waveform`  按 起点时刻 + 终点时刻 / 点数、重采样率、通道 读一段原始采样（一次侧口径，与界面其它曲线一致）
- :func:`rms_curve`      一段时间内的逐周波有效值（Ua/Ub/Uc/Ia/Ib/Ic），点数过多时自动合并相邻周波

时间文本写法与播放时间段相同（``2026-10-13 08:00:02.5`` / ``08:00:02.5`` / epoch 秒）。
"""
from __future__ import annotations

import csv as _csv
import math
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .config import AppConfig, ConfigError, parse_play_start, parse_time_text

CHANNELS: Tuple[str, ...] = ("Ua", "Ub", "Uc", "Ia", "Ib", "Ic")
_FIELD_OF = {"Ua": "ua", "Ub": "ub", "Uc": "uc", "Ia": "ia", "Ib": "ib", "Ic": "ic"}
MAX_POINTS_DEFAULT = 1_000_000       # 单次返回的最多采样点（每通道）
MAX_RMS_POINTS_DEFAULT = 200_000     # 有效值曲线最多点数，超过则合并相邻周波
RESAMPLE_METHODS: Tuple[str, ...] = ("linear", "nearest", "fft")   # v0.62：与「重采样」功能同一组方法
DEFAULT_CYCLES = 300                 # v0.62：默认加载 / 周波窗的周波数


class WaveError(ValueError):
    pass


def _prep_cfg(base: AppConfig, path: str, t_start: str = "", t_end: str = "") -> AppConfig:
    cfg = AppConfig.from_dict(base.to_dict())
    cfg.source.kind = "csv_file"; cfg.source.path = path
    cfg.source.file_speed = 0.0; cfg.source.play_window = False; cfg.source.play_end_time = ""
    cfg.source.play_start_mode = "begin"; cfg.source.play_start_value = ""
    ts_txt, te_txt = str(t_start or "").strip(), str(t_end or "").strip()
    if ts_txt:
        parse_play_start("time", ts_txt)
        cfg.source.play_start_mode = "time"; cfg.source.play_start_value = ts_txt
    if te_txt:
        parse_play_start("time", te_txt)
        cfg.source.play_end_time = te_txt
    if ts_txt and te_txt:
        a, b = parse_play_start("time", ts_txt), parse_play_start("time", te_txt)
        if a[0] == b[0] and b[1] <= a[1]:
            raise WaveError(f"结束时间必须晚于起始时间（{ts_txt} → {te_txt}）")
    cfg.validate()
    return cfg


def _parse_t(text: str) -> Optional[float]:
    s = str(text or "").strip()
    return float(parse_time_text(s)) if s else None


def _count_rows(p: str, has_header: bool) -> int:
    n = 0
    with open(p, "rb") as fh:
        last = b""
        while True:
            buf = fh.read(1 << 20)
            if not buf:
                break
            n += buf.count(b"\n"); last = buf[-1:]
        if last and last != b"\n":
            n += 1
    return max(0, n - (1 if has_header else 0))


# ------------------------------------------------------------------ ① 文件信息
def file_info(base: AppConfig, path: str) -> Dict[str, Any]:
    """通道 / 采样率 / 行数 / 时长 / 起止时间。采样率优先由前 3000 行时标推算（``fs_est``），推算不出时用配置 ``sampling.fs``。"""
    from .sources.parsing import file_tz_offset_h, parse_timestamps, read_header
    if not path or not os.path.isfile(path):
        raise WaveError(f"文件不存在：{path}")
    cfg = AppConfig.from_dict(base.to_dict())
    header, enc = read_header(path, cfg.columns.encoding, cfg.columns.delimiter)
    has_header = cfg.columns.looks_like_header(header)
    idx = cfg.columns.layout(header if has_header else None)
    ts_c = idx.get("timestamp")
    chans = [c for c in CHANNELS if idx.get(_FIELD_OF[c]) is not None]
    n_rows = _count_rows(path, has_header)
    if n_rows == 0:
        raise WaveError(f"文件没有数据行：{path}")
    size = os.path.getsize(path)
    first_ts: List[str] = []
    with open(path, "r", encoding=enc, newline="") as fh:
        rdr = _csv.reader(fh, delimiter=cfg.columns.delimiter)
        if has_header:
            next(rdr, None)
        for k, row in enumerate(rdr):
            if ts_c is not None and len(row) > ts_c:
                first_ts.append(row[ts_c])
            if k >= 3000:
                break
    # 末尾几行（从文件尾 64 KB 取；尾块首行可能被截断）
    last_ts: List[str] = []
    if ts_c is not None:
        with open(path, "rb") as fh:
            fh.seek(max(0, size - 65536))
            tail = fh.read().decode(enc, errors="replace").splitlines()
        rows = []
        for ln in (tail[1:] if size > 65536 else tail):
            if not ln.strip():
                continue
            try:
                r = next(_csv.reader([ln], delimiter=cfg.columns.delimiter))
            except Exception:
                continue
            if len(r) > ts_c and not (has_header and r[ts_c] == header[ts_c]):
                rows.append(r)
        last_ts = [r[ts_c] for r in rows[-3:]]
    tz_h = file_tz_offset_h(cfg)
    fs_cfg = float(cfg.sampling.fs)
    fs_est: Optional[float] = None
    t0: Optional[float] = None; t1: Optional[float] = None
    notes: List[str] = []
    ts_mode = None
    if ts_c is not None and first_ts:
        info = parse_timestamps(first_ts, cfg.columns.timestamp_unit, tz_h)
        ts_mode = info.mode
        notes += list(info.notes or [])
        if info.t.size:
            t0 = float(info.t[0])
        if info.fs_est == info.fs_est and info.fs_est > 0:    # 非 NaN
            fs_est = float(info.fs_est)
        if last_ts:
            i1 = parse_timestamps(last_ts, cfg.columns.timestamp_unit, tz_h)
            if i1.t.size:
                t1 = float(i1.t[-1])
    # 时标 0.1 ms 量化会让推算值带小数尾巴（6400.011…）：与配置值相差 <0.5% 时按配置值；否则取推算值（保留 1 位小数）
    fs = fs_cfg if (fs_est is None or abs(fs_est - fs_cfg) / fs_cfg < 0.005) else round(fs_est, 1)
    if cfg.source.custom_time:
        txt = str(cfg.source.custom_time_start or "").strip()
        if txt:
            t0 = float(parse_time_text(txt))
        t1 = (t0 if t0 is not None else 0.0) + (n_rows - 1) / fs
        notes.append("基准配置启用了自定义播放时间：时间轴＝起始时间 + 行号 / fs")
    elif t0 is None:
        notes.append("文件没有时间列或时标无法解析：时间轴按 行号 / fs 计")
        t0 = 0.0; t1 = (n_rows - 1) / fs
    # v0.62：时长与结束时间按 采样率 × 数据点数 计算（结束时间＝起始 + (行数−1)/fs）；时标里的末行时间另记，差异大时提示
    t_end_ts = t1
    duration = (n_rows / fs) if fs > 0 else 0.0
    t1 = t0 + (n_rows - 1) / fs
    if t_end_ts is not None and abs(t_end_ts - t1) > max(1.0 / fs, 1e-3) * 2:
        notes.append(f"按时标末行的结束时间 {t_end_ts:.3f} 与按 采样率×点数 计算的 {t1:.3f} 相差 {t_end_ts - t1:+.3f} s（文件内有缺口或时标不均匀）")
    if fs_est and abs(fs_est - fs_cfg) / fs_cfg > 0.02:
        notes.append(f"时标推算采样率 {fs_est:.1f} Hz 与基准配置 sampling.fs={fs_cfg:g} Hz 相差 >2%，波形加载按推算值解释")
    return {"ok": True, "path": path, "size_mb": round(size / 1024 / 1024, 3), "encoding": enc, "has_header": has_header,
            "header": header if has_header else None, "n_channels": len(chans), "channels": chans,
            "columns": {c: idx.get(_FIELD_OF[c]) for c in chans}, "rows": n_rows,
            "fs": fs, "fs_est": fs_est, "fs_configured": fs_cfg, "f_nom": float(cfg.sampling.f_nom),
            "samples_per_cycle": int(round(fs / float(cfg.sampling.f_nom))),
            "duration_s": duration, "t_start": t0, "t_end": t1, "t_end_by_timestamp": t_end_ts, "ts_mode": ts_mode, "custom_time": bool(cfg.source.custom_time),
            "pt_ct": {"enabled": bool(cfg.transform.enabled), "pt_ratio": cfg.transform.pt_ratio, "ct_ratio": cfg.transform.ct_ratio},
            "notes": notes}


# ------------------------------------------------------------------ 读块
def _iter_blocks(cfg: AppConfig):
    from .scaling import scale_block
    from .sources import create_source
    from .sources.parsing import ParseError
    try:
        with create_source(cfg) as src:
            while True:
                blk = src.read()
                if blk is None:
                    if src.exhausted:
                        break
                    continue
                if blk.n:
                    yield scale_block(blk, cfg.transform)
    except ParseError as exc:                    # 起点超出文件范围 / 时标解析失败 → 带说明的 WaveError（界面直接显示）
        raise WaveError(str(exc)) from exc


def _norm_channels(channels: Optional[Sequence[str]], available: Optional[Sequence[str]] = None) -> List[str]:
    if not channels:
        chans = list(CHANNELS)
    else:
        chans = []
        for c in channels:
            c = str(c).strip()
            if not c:
                continue
            m = {k.lower(): k for k in CHANNELS}.get(c.lower())
            if m is None:
                raise WaveError(f"未知通道 {c!r}（可选 {', '.join(CHANNELS)}）")
            if m not in chans:
                chans.append(m)
        if not chans:
            chans = list(CHANNELS)
    if available is not None:
        chans = [c for c in chans if c in available] or chans
    return chans


def _pick(blk, ch: str) -> np.ndarray:
    k = "ABC".index(ch[1].upper())
    return blk.u[k] if ch[0].upper() == "U" else blk.i[k]


# ------------------------------------------------------------------ ② 原始波形
def load_waveform(base: AppConfig, path: str, *, t_start: str = "", t_end: str = "", n_points: Optional[int] = None,
                  n_cycles: Optional[int] = None, fs_out: Optional[float] = None, method: str = "linear",
                  channels: Optional[Sequence[str]] = None, max_points: int = MAX_POINTS_DEFAULT) -> Dict[str, Any]:
    """读一段原始采样并（可选）重采样。

    - ``t_start`` 空＝文件起点；``t_end`` 空＝文件末尾；点数上限＝``n_points``（输出点数，按 ``fs_out`` 计）或
      ``n_cycles``（周波数 × 每周波点数，v0.62 默认 300 周波）；两者都为空＝整个时间段（受 ``max_points`` 限制，超出截断并提示）。
      时间段与点数同时给出时取先到者。
    - ``fs_out`` 空或等于原采样率＝原始点；否则按 ``method`` 重采样到 起点 + k/fs_out 等间隔网格：
      ``linear`` 线性插值 / ``nearest`` 最近邻 / ``fft`` 频域（与「重采样」功能同一组方法；fft 自带理想低通抗混叠，
      输出点数取整后实际采样率略有偏差时记入 notes）。
    - 返回：t（epoch 秒）、channels{Ua:[…]…}、units、fs、fs_src、n、truncated、源信息。值为一次侧口径（随基准配置 PT/CT）。
    """
    if not path or not os.path.isfile(path):
        raise WaveError(f"文件不存在：{path}")
    cfg = _prep_cfg(base, path, t_start, t_end)
    info = file_info(base, path)
    fs_src = float(info["fs"])
    chans = _norm_channels(channels, info["channels"])
    fs_o = float(fs_out) if fs_out else fs_src
    if not (fs_o > 0):
        raise WaveError(f"重采样率必须 > 0（当前 {fs_out}）")
    resample = abs(fs_o - fs_src) > 1e-9 * max(fs_o, fs_src)
    method = str(method or "linear").strip().lower()
    if method not in RESAMPLE_METHODS:
        raise WaveError(f"重采样方式必须是 {'/'.join(RESAMPLE_METHODS)} 之一（当前 {method!r}）")
    te = _parse_t(t_end)
    n_req: Optional[int] = None
    if n_points is not None and str(n_points) != "":
        n_req = int(n_points)
        if n_req <= 0:
            raise WaveError(f"点数必须 > 0（当前 {n_points}）")
    elif n_cycles is not None and str(n_cycles) != "":
        nc = int(n_cycles)
        if nc <= 0:
            raise WaveError(f"周波数必须 > 0（当前 {n_cycles}）")
        n_req = nc * max(1, int(round(fs_o / float(cfg.sampling.f_nom))))
    max_points = max(1, int(max_points))
    want_out = min(n_req, max_points) if n_req is not None else max_points
    # 需要读入的原始点数（重采样时按比例多读 1 个周波做插值边界）
    want_src = int(math.ceil(want_out * fs_src / fs_o)) + (int(fs_src / float(cfg.sampling.f_nom)) + 2 if resample else 0)
    ts: List[np.ndarray] = []; data: Dict[str, List[np.ndarray]] = {c: [] for c in chans}
    got = 0; eof = True
    for blk in _iter_blocks(cfg):
        ts.append(blk.t)
        for c in chans:
            data[c].append(_pick(blk, c))
        got += int(blk.n)
        if got >= want_src:
            eof = False
            break
    if not ts:
        raise WaveError("指定时间段内没有读到数据（时刻超出文件范围或文件为空）")
    t = np.concatenate(ts)
    arr = {c: np.concatenate(data[c]) for c in chans}
    truncated = False
    fs_eff: Optional[float] = None
    if resample:
        t0 = float(t[0]); t_last = float(t[-1])
        n_grid = int(math.floor((t_last - t0) * fs_o)) + 1
        if n_req is not None:
            n_grid = min(n_grid, n_req)
        if n_grid > max_points:
            n_grid = max_points; truncated = True
        tg = t0 + np.arange(n_grid) / fs_o
        if method == "nearest":
            idx = np.clip(np.rint((tg - t0) * fs_src).astype(np.int64), 0, t.size - 1)
            out = {c: arr[c][idx] for c in chans}
        elif method == "fft":
            # 与 resample.py 同一实现（周期语义）：n_in 点 → n_out = round(n_in·fs_o/fs_src) 点覆盖同一时长
            n_in = int(t.size); n_out = max(2, int(round(n_in * fs_o / fs_src)))
            fs_eff = n_out * fs_src / n_in
            m_out = n_out // 2 + 1
            out = {}
            for c in chans:
                spec = np.fft.rfft(arr[c]); keep = min(spec.size, m_out)
                ns = np.zeros(m_out, dtype=np.complex128); ns[:keep] = spec[:keep]
                if n_out % 2 == 0 and keep == m_out and m_out <= spec.size:
                    ns[-1] = ns[-1].real
                out[c] = (np.fft.irfft(ns, n=n_out) * (n_out / n_in))[:n_grid]
            if out[chans[0]].size < n_grid:          # 取整后比网格短：网格按实际输出长度裁剪
                n_grid = int(out[chans[0]].size); tg = tg[:n_grid]
        else:
            out = {c: np.interp(tg, t, arr[c]) for c in chans}
        t_out = tg
    else:
        n_keep = t.size
        if n_req is not None:
            n_keep = min(n_keep, n_req)
        if n_keep > max_points:
            n_keep = max_points; truncated = True
        t_out = t[:n_keep]; out = {c: arr[c][:n_keep] for c in chans}
    if n_req is None and te is None and not eof:
        truncated = True
    notes: List[str] = list(info.get("notes") or [])
    if truncated:
        notes.append(f"点数超过单次上限 {max_points}，只返回前 {t_out.size} 点；可缩小时间段 / 指定点数 / 降低重采样率")
    if resample and fs_o < fs_src and method != "fft":
        notes.append(f"降采样方式 {method} 无抗混叠低通（高于新 Nyquist 的谐波会折叠到低频），仅作预览；要保真降采样请选 fft")
    if fs_eff is not None and abs(fs_eff - fs_o) / fs_o > 1e-9:
        notes.append(f"fft 方法输出点数取整后实际采样率 {fs_eff:.6f} Hz（目标 {fs_o:g}，偏差 {abs(fs_eff - fs_o) / fs_o * 100:.4f}%）；时间轴仍按目标采样率")
    rnd = 6
    return {"ok": True, "path": path, "fs": fs_o, "fs_src": fs_src, "resampled": resample, "method": (method if resample else None),
            "fs_effective": fs_eff, "samples_per_cycle": max(1, int(round(fs_o / float(cfg.sampling.f_nom)))), "channels_loaded": chans,
            "n": int(t_out.size), "t": [float(x) for x in t_out],
            "channels": {c: [float(round(float(v), rnd)) if math.isfinite(v) else None for v in out[c]] for c in chans},
            "units": {c: ("V" if c[0] == "U" else "A") for c in chans},
            "t_first": float(t_out[0]) if t_out.size else None, "t_last": float(t_out[-1]) if t_out.size else None,
            "request": {"t_start": str(t_start or ""), "t_end": str(t_end or ""), "n_points": n_req, "n_cycles": n_cycles, "fs_out": fs_out,
                        "method": method, "channels": list(channels) if channels else None},
            "truncated": truncated, "eof": eof, "notes": notes}


# ------------------------------------------------------------------ ③ 逐周波有效值
def rms_curve(base: AppConfig, path: str, *, t_start: str = "", t_end: str = "", duration_s: Optional[float] = None,
              channels: Optional[Sequence[str]] = None, agg_cycles: int = 1,
              max_points: int = MAX_RMS_POINTS_DEFAULT, max_cycles: int = 5_000_000) -> Dict[str, Any]:
    """指定时间段内各通道的逐周波有效值曲线（每 ``agg_cycles`` 个周波一个点；点数超过 ``max_points`` 时自动加大合并数）。

    每周波样本数 n = round(fs / f_nom)，按时间连续切整周波（跨块结转零头，时间缺口处丢弃零头）。
    """
    if not path or not os.path.isfile(path):
        raise WaveError(f"文件不存在：{path}")
    cfg = _prep_cfg(base, path, t_start, t_end)
    info = file_info(base, path)
    fs = float(info["fs"]); f_nom = float(cfg.sampling.f_nom)
    n_cyc = max(4, int(round(fs / f_nom)))
    chans = _norm_channels(channels, info["channels"])
    agg = max(1, int(agg_cycles or 1))
    if duration_s is not None:
        duration_s = float(duration_s)
        if not (duration_s > 0):
            raise WaveError(f"时长必须 > 0 秒（当前 {duration_s}）")
    carry_t: Optional[np.ndarray] = None; carry: Dict[str, np.ndarray] = {}
    sq: Dict[str, List[np.ndarray]] = {c: [] for c in chans}; tt: List[np.ndarray] = []
    t_first: Optional[float] = None; total = 0; stop = False
    for blk in _iter_blocks(cfg):
        t = blk.t; cur = {c: _pick(blk, c) for c in chans}
        if carry_t is not None and carry_t.size:
            if (t[0] - carry_t[-1]) > 1.5 / fs:
                carry_t = None; carry = {}
            else:
                t = np.concatenate([carry_t, t]); cur = {c: np.concatenate([carry[c], cur[c]]) for c in chans}
        m = t.size // n_cyc; rest = t.size - m * n_cyc
        carry_t = t[m * n_cyc:] if rest else None; carry = {c: cur[c][m * n_cyc:] for c in chans} if rest else {}
        if m == 0:
            continue
        tc = t[: m * n_cyc: n_cyc]
        if t_first is None:
            t_first = float(tc[0])
        if duration_s is not None:
            keep = tc < t_first + duration_s - 1e-9          # [起点, 起点 + 时长)：3 s → 150 个周波
            if not keep.all():
                m = int(keep.sum()); stop = True
                if m == 0:
                    break
                tc = tc[:m]
        tt.append(tc)
        for c in chans:
            x = cur[c][: m * n_cyc].reshape(m, n_cyc)
            sq[c].append(np.mean(x * x, axis=1))
        total += m
        if stop or total >= max_cycles:
            break
    if not tt:
        raise WaveError("指定时间段内没有读到整周波数据（时刻超出文件范围或文件为空）")
    t_all = np.concatenate(tt); ms = {c: np.concatenate(sq[c]) for c in chans}
    n = t_all.size
    notes: List[str] = list(info.get("notes") or [])
    k = agg
    if math.ceil(n / k) > max_points:
        k = int(math.ceil(n / max_points))
        notes.append(f"周波数 {n} 超过曲线点数上限 {max_points}，已自动按每 {k} 个周波合并为一个点")
    if k > 1:
        m2 = n // k
        if m2 == 0:
            k = n; m2 = 1
        t_all = t_all[: m2 * k: k]
        ms = {c: np.mean(ms[c][: m2 * k].reshape(m2, k), axis=1) for c in chans}
    rms = {c: np.sqrt(ms[c]) for c in chans}
    return {"ok": True, "path": path, "fs": fs, "f_nom": f_nom, "samples_per_cycle": n_cyc, "agg_cycles": k,
            "n": int(t_all.size), "cycles_total": int(n), "t": [float(x) for x in t_all],
            "channels": {c: [float(round(float(v), 6)) for v in rms[c]] for c in chans},
            "units": {c: ("V" if c[0] == "U" else "A") for c in chans},
            "t_first": float(t_all[0]), "t_last": float(t_all[-1]),
            "request": {"t_start": str(t_start or ""), "t_end": str(t_end or ""), "duration_s": duration_s, "agg_cycles": agg,
                        "channels": list(channels) if channels else None},
            "notes": notes}


# ------------------------------------------------------------------ v0.62：独立的基准配置（不与总线 / 分路侧运行配置关联）
BASE_FIELDS: Tuple[str, ...] = ("fs", "f_nom", "pt_ct_enabled", "pt_ratio", "ct_ratio", "file_time_utc")


def base_defaults(cfg: AppConfig) -> Dict[str, Any]:
    """界面「基准配置」的初始值（来自出厂配置 configs/default.json）。"""
    return {"fs": float(cfg.sampling.fs), "f_nom": float(cfg.sampling.f_nom), "pt_ct_enabled": bool(cfg.transform.enabled),
            "pt_ratio": float(cfg.transform.pt_ratio), "ct_ratio": float(cfg.transform.ct_ratio),
            "file_time_utc": bool(cfg.source.file_time_utc)}


def make_base(default_cfg: AppConfig, **overrides: Any) -> AppConfig:
    """出厂配置副本 + 界面给的几项（采样率 / 额定频率 / PT·CT 启用与变比 / 时标 UTC）→ 预览用基准配置。
    None / 空串＝沿用出厂值；非法值抛 WaveError。"""
    cfg = AppConfig.from_dict(default_cfg.to_dict())
    cfg.source.kind = "csv_file"; cfg.source.custom_time = False; cfg.source.play_window = False
    def _f(name: str, lo: float) -> Optional[float]:
        v = overrides.get(name)
        if v is None or str(v).strip() == "":
            return None
        try:
            x = float(v)
        except (TypeError, ValueError):
            raise WaveError(f"基准配置 {name} 不是数字：{v!r}") from None
        if not (x > lo):
            raise WaveError(f"基准配置 {name} 必须 > {lo:g}（当前 {x:g}）")
        return x
    def _b(name: str) -> Optional[bool]:
        v = overrides.get(name)
        if v is None or str(v).strip() == "":
            return None
        return str(v).strip().lower() in ("1", "true", "on", "yes")
    fs = _f("fs", 0); fn = _f("f_nom", 0); pt = _f("pt_ratio", 0); ct = _f("ct_ratio", 0)
    en = _b("pt_ct_enabled"); utc = _b("file_time_utc")
    if fs is not None:
        cfg.sampling.fs = fs
    if fn is not None:
        cfg.sampling.f_nom = fn
    if pt is not None:
        cfg.transform.pt_ratio = pt
    if ct is not None:
        cfg.transform.ct_ratio = ct
    if en is not None:
        cfg.transform.enabled = en
    if utc is not None:
        cfg.source.file_time_utc = utc
    cfg.source.path = "x.csv"                     # 只为通过校验；实际路径由各函数填
    try:
        cfg.validate()
    except ConfigError as exc:
        raise WaveError(f"基准配置无效：{exc}") from None
    return cfg
