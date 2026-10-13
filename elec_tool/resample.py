"""离线波形 CSV 重采样（数据处理子界面 / CLI ``resample`` 的算法核心，只依赖 numpy）。

输入：与播放用同一格式的波形 CSV（``时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流``，
      可有/无表头、任意编码、时间戳可为 epoch 数值 / ``0/00/00 HH:MM:SS.ffff`` / ISO 字符串）。
输出：``<out_dir>/<原文件名>_re_<fs_new>.csv``，表头与列顺序原样保留，时间戳按原格式重新生成。

时间轴约定（重要）
  * 原始数据按**等间隔** ``fs_src`` 处理：第 i 行位于 ``t0 + i/fs_src``。``fs_src`` 默认由时间戳列前
    20000 行线性拟合推算（与播放探查同一算法），也可显式指定。**不**逐行使用原时间戳，因为采集器
    常见 0.1 ms 量化 / 重复时标，逐行插值会把量化抖动放大成波形失真。
  * 输出第 k 行位于 ``t0 + k/fs_new``，k 从 0 到 ``floor((N-1)·fs_new/fs_src)``，不外推。
  * 时间戳文本：epoch 数值 → 同单位数值（小数位按 1/fs_new 分辨率自动加足）；
    ``Y/M/D HH:MM:SS.f`` → 保留原日期段写法（``0/00/00`` 原样）、小数位 = max(原位数, 覆盖 1/fs_new 所需位数)；
    其它日期字符串 → ``YYYY-MM-DD HH:MM:SS.ffffff``。

插值方法
  linear   线性插值，流式分块处理，内存 O(块)。降采样时**无抗混叠**（高次谐波可能折叠），升采样安全。
  nearest  最近邻（保持原始量化值，用于整数倍抽取时等价于直接抽样）。流式。
  fft      频域重采样（等价 scipy.signal.resample：rfft → 截断/补零 → irfft）。降采样自带理想低通抗混叠，
           但需**整文件载入内存**且对非整周期信号两端有吉布斯振铃；适合实验室对比，不建议用于超大文件。
"""
from __future__ import annotations

import csv
import math
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

from .config import AppConfig, ColumnMap, ConfigError
from .sources.parsing import (ParseError, _RE_SLASH_CLOCK, detect_encoding, parse_timestamps,
                              read_header)

METHODS = ("linear", "nearest", "fft")
_PRESCAN_ROWS = 20000
_CHUNK_ROWS = 65536


class ResampleError(ValueError):
    """参数/数据问题导致的重采样失败（给界面与 CLI 的可读信息）。"""


def output_name(src_path: str, fs_new: float) -> str:
    """``波形_农业排灌_大水泵_80_1.csv`` + 6400 → ``波形_农业排灌_大水泵_80_1_re_6400.csv``。"""
    stem, ext = os.path.splitext(os.path.basename(src_path))
    fs_txt = str(int(round(fs_new))) if abs(fs_new - round(fs_new)) < 1e-9 else repr(float(fs_new)).replace(".", "p")
    return f"{stem}_re_{fs_txt}{ext or '.csv'}"


@dataclass
class ResampleJob:
    """进度/取消句柄（Web 后台线程用；CLI 可忽略）。"""
    progress: float = 0.0            # 0~1，按已读字节
    rows_in: int = 0
    rows_out: int = 0
    stage: str = "idle"
    cancel: threading.Event = field(default_factory=threading.Event)
    on_progress: Optional[Callable[["ResampleJob"], None]] = None

    def tick(self, progress: float, stage: Optional[str] = None) -> None:
        self.progress = max(0.0, min(1.0, progress))
        if stage:
            self.stage = stage
        if self.on_progress:
            self.on_progress(self)
        if self.cancel.is_set():
            raise ResampleError("已取消")


# ------------------------------------------------------------------ 时间戳写回

class _TsWriter:
    """按首个原始时间戳的写法生成输出时间戳文本。"""

    def __init__(self, first_raw: str, mode: str, t0: float, fs_new: float, tz_offset_h: float):
        self.kind = "numeric"
        self.fmt_digits = 0
        self.t0 = float(t0)
        self.tz = tz_offset_h * 3600.0
        need_digits = max(0, int(math.ceil(math.log10(fs_new))) if fs_new > 1 else 0)
        s = first_raw.strip()
        m = _RE_SLASH_CLOCK.match(s)
        if mode in ("s", "ms", "us", "ns", "relative_s"):
            self.unit = {"s": 1.0, "ms": 1e3, "us": 1e6, "ns": 1e9, "relative_s": 1.0}[mode]
            self.base_raw = float(s)
            ip, _, fp = s.partition(".")
            self.base_int = int(ip)
            self.base_frac = float("0." + fp) if fp else 0.0
            orig_digits = len(s.split(".")[1]) if "." in s else 0
            step_unit = self.unit / fs_new                           # 一步在该单位下的大小
            need = max(0, int(math.ceil(-math.log10(step_unit))) + 1) if step_unit < 1 else 0
            self.fmt_digits = min(9, max(orig_digits, need))
            self.kind = "numeric"
        elif m:
            a, b, c, hh, mm, ss, frac = m.groups()
            self.kind = "slash"
            self.no_date = (int(a) == 0 or int(b) == 0 or int(c) == 0)
            self.date_text = s.split(" ")[0] if " " in s else s.split("T")[0]
            self.sep = "T" if "T" in s and " " not in s else " "
            self.fmt_digits = max(len(frac or ""), need_digits)
            # 有日期：原样式为 Y/M/D 或 D/M/Y，按与解析一致的规则判断分隔符与顺序
            self.date_sep = "/" if "/" in self.date_text else "-"
            self.ymd_first = not (int(a) <= 31 and int(c) > 31)
        else:
            self.kind = "iso"
            self.fmt_digits = max(6, need_digits)

    def text(self, k: int, fs_new: float) -> str:
        if self.kind == "numeric":
            # 整数部分与小数偏移分开算：epoch 毫秒/纳秒量级（1e12~1e18）直接做 float 加法会丢掉亚毫秒精度
            off = self.base_frac + k * self.unit / fs_new
            if not self.fmt_digits:
                return str(self.base_int + int(round(off)))
            off = round(off, self.fmt_digits)
            carry = math.floor(off)
            dec = off - carry
            return f"{self.base_int + carry}{f'{dec:.{self.fmt_digits}f}'[1:]}"
        d = self.fmt_digits
        t = round(self.t0 + k / fs_new + self.tz, d)          # 先按输出位数取整，再拆时分秒，避免 59.99995→60.0000
        if self.kind == "slash" and self.no_date:
            tod = t % 86400.0
            return f"{self.date_text}{self.sep}{self._hms(tod, d)}"
        day = math.floor(t / 86400.0)
        tod = t - day * 86400.0
        dt = datetime.fromtimestamp(day * 86400.0, tz=timezone.utc)
        if self.kind == "slash":
            ymd = [f"{dt.year:04d}", f"{dt.month:02d}", f"{dt.day:02d}"]
            if not self.ymd_first:
                ymd = ymd[::-1]
            return f"{self.date_sep.join(ymd)}{self.sep}{self._hms(tod, d)}"
        return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d} {self._hms(tod, d)}"

    @staticmethod
    def _hms(tod: float, d: int) -> str:
        # tod 已按 d 位取整；用整数运算拆分，杜绝浮点误差
        scale = 10 ** d
        total = int(round(tod * scale))
        hh, rem = divmod(total, 3600 * scale)
        mm, rem = divmod(rem, 60 * scale)
        ss, frac = divmod(rem, scale)
        hh %= 24
        return f"{hh:02d}:{mm:02d}:{ss:02d}" + (f".{frac:0{d}d}" if d else "")


# ------------------------------------------------------------------ 主流程

def _prescan(path: str, enc: str, delimiter: str, colmap: ColumnMap, has_header: bool,
             tz_offset_h: float) -> Dict[str, Any]:
    header: Optional[List[str]] = None
    with open(path, "r", encoding=enc, newline="") as fh:
        rdr = csv.reader(fh, delimiter=delimiter)
        first = next(rdr, None)
        if first is None:
            raise ResampleError(f"{path} 为空文件")
        idx: Optional[Dict[str, int]] = None
        rows: List[List[str]] = []
        if has_header:
            try:
                idx = colmap.resolve([h.strip() for h in first])
                header = first
            except ConfigError:
                idx = None
        if header is None:
            rows.append(first)
        if idx is None:
            idx = {k: i for i, k in enumerate(("timestamp", "ua", "ia", "ub", "ib", "uc", "ic"))}
        for row in rdr:
            if row and any(str(c).strip() for c in row):
                rows.append(row)
            if len(rows) >= _PRESCAN_ROWS:
                break
    if not rows:
        raise ResampleError(f"{path} 没有数据行")
    ti = idx["timestamp"]
    info = parse_timestamps([r[ti] for r in rows], colmap.timestamp_unit, tz_offset_h)
    return {"header": header, "idx": idx, "ts_mode": info.mode, "fs_est": info.fs_est,
            "t0": float(info.t[0]), "first_raw": rows[0][ti], "ncols": len(rows[0]),
            "ts_notes": info.notes}


def resample_csv(src_path: str, fs_new: float, out_dir: str = "data", *,
                 cfg: Optional[AppConfig] = None, fs_src: Optional[float] = None,
                 method: str = "linear", overwrite: bool = False, decimals: int = 6,
                 job: Optional[ResampleJob] = None, root: Optional[str] = None) -> Dict[str, Any]:
    """重采样一个 CSV 文件，返回结果字典（out_path / rows_in / rows_out / fs_src / notes …）。"""
    t_start = time.time()
    job = job or ResampleJob()
    cfg = cfg or AppConfig()
    colmap = cfg.columns
    if method not in METHODS:
        raise ResampleError(f"method 必须是 {METHODS} 之一，收到 {method!r}")
    try:
        fs_new = float(fs_new)
    except (TypeError, ValueError):
        raise ResampleError(f"目标采样率不是数字：{fs_new!r}") from None
    if not (fs_new > 0) or not math.isfinite(fs_new):
        raise ResampleError(f"目标采样率必须 > 0，收到 {fs_new}")
    root = root or os.getcwd()
    src = src_path if os.path.isabs(src_path) else os.path.join(root, src_path)
    if not os.path.isfile(src):
        raise ResampleError(f"文件不存在：{src_path}")
    out_dir_abs = out_dir if os.path.isabs(out_dir) else os.path.join(root, out_dir)
    os.makedirs(out_dir_abs, exist_ok=True)
    out_path = os.path.join(out_dir_abs, output_name(src, fs_new))
    if os.path.abspath(out_path) == os.path.abspath(src):
        raise ResampleError("输出文件与输入文件同名，拒绝覆盖输入")
    if os.path.exists(out_path) and not overwrite:
        raise ResampleError(f"输出文件已存在：{os.path.relpath(out_path, root)}（勾选「覆盖」或改目标采样率）")

    enc = colmap.encoding if colmap.encoding != "auto" else detect_encoding(src)
    # 输出编码与输入一致；utf-8-sig 只在源文件真的带 BOM 时才写 BOM（探测器对纯 UTF-8 也会报 utf-8-sig）
    with open(src, "rb") as _fh:
        _has_bom = _fh.read(3) == b"\xef\xbb\xbf"
    enc_out = "utf-8-sig" if (enc.lower().replace("_", "-") in ("utf-8", "utf-8-sig", "utf8") and _has_bom) \
        else ("utf-8" if enc.lower().replace("_", "-") == "utf-8-sig" else enc)
    delim = colmap.delimiter
    notes: List[str] = []
    job.tick(0.0, "prescan")
    tz_h = float(getattr(colmap, "tz_offset_h", 0.0) or 0.0)
    pre = _prescan(src, enc, delim, colmap, colmap.has_header, tz_h)
    if fs_src is None or not fs_src:
        fs_src_used = float(pre["fs_est"])
        if not math.isfinite(fs_src_used) or fs_src_used <= 0:
            fs_src_used = float(cfg.sampling.fs)
            notes.append(f"时间戳无法推算原采样率（{pre['ts_mode']}），回退为配置 sampling.fs={fs_src_used:g}")
        else:
            notes.append(f"原采样率由时间戳前 {_PRESCAN_ROWS} 行线性拟合推算：{fs_src_used:.4f} Hz")
            # 贴近常见整数采样率则取整（避免 6399.98 之类的量化残差造成输出行数差 1）
            rounded = round(fs_src_used)
            if rounded > 0 and abs(fs_src_used - rounded) / rounded < 2e-3:
                fs_src_used = float(rounded)
                notes.append(f"与整数采样率 {rounded} 偏差 <0.2%，按 {rounded} Hz 处理")
        fs_src_source = "estimated"
    else:
        fs_src_used = float(fs_src)
        fs_src_source = "user"
        if fs_src_used <= 0:
            raise ResampleError("原采样率必须 > 0")
        if math.isfinite(pre["fs_est"]) and abs(pre["fs_est"] - fs_src_used) / fs_src_used > 0.05:
            notes.append(f"⚠ 指定原采样率 {fs_src_used:g} 与时间戳推算 {pre['fs_est']:.2f} 偏差 >5%，以指定值为准")
    if abs(fs_new - fs_src_used) < 1e-9:
        notes.append("目标采样率与原采样率相同：输出为按等间隔重写时间戳的副本")
    if fs_new < fs_src_used and method == "linear":
        notes.append(f"⚠ 线性插值降采样无抗混叠：高于 {fs_new / 2:g} Hz 的成分会折叠；"
                     f"需要严格结果请用 fft 方法")
    ratio = fs_src_used / fs_new                                  # 输出一步对应的输入索引步长
    ts_writer = _TsWriter(pre["first_raw"], pre["ts_mode"], pre["t0"], fs_new, tz_h)
    for n in pre["ts_notes"]:
        notes.append("源时间戳：" + n)

    header, idx = pre["header"], pre["idx"]
    ti = idx["timestamp"]
    ncols = pre["ncols"]
    size = max(1, os.path.getsize(src))

    rows_in = 0
    rows_out = 0
    tmp_path = out_path + ".part"
    try:
        rows_in, rows_out = _run_resample(src, tmp_path, enc, enc_out, delim, header, idx, ncols, size, method,
                                          ratio, fs_new, fs_src_used, ts_writer, decimals, job, notes)
    except BaseException:
        try:
            os.remove(tmp_path)                      # 失败/取消不留半成品
        except OSError:
            pass
        raise
    os.replace(tmp_path, out_path)
    job.tick(1.0, "done")
    job.rows_in, job.rows_out = rows_in, rows_out
    dur_in = (rows_in - 1) / fs_src_used if rows_in > 1 else 0.0
    return {
        "ok": True, "src_path": os.path.relpath(src, root) if src.startswith(root) else src,
        "out_path": os.path.relpath(out_path, root), "out_name": os.path.basename(out_path),
        "out_size_mb": round(os.path.getsize(out_path) / 1024 / 1024, 3),
        "rows_in": rows_in, "rows_out": rows_out, "fs_src": fs_src_used, "fs_src_source": fs_src_source,
        "fs_src_estimated": pre["fs_est"], "fs_new": fs_new, "method": method,
        "duration_s": dur_in, "ts_mode": pre["ts_mode"], "ts_first_in": pre["first_raw"],
        "ts_first_out": ts_writer.text(0, fs_new), "ts_last_out": ts_writer.text(max(rows_out - 1, 0), fs_new),
        "header_kept": header is not None, "encoding": enc, "encoding_out": enc_out, "elapsed_s": round(time.time() - t_start, 3),
        "notes": notes,
    }


def _run_resample(src: str, tmp_path: str, enc: str, enc_out: str, delim: str, header: Optional[List[str]],
                  idx: Dict[str, int], ncols: int, size: int, method: str, ratio: float, fs_new: float,
                  fs_src_used: float, ts_writer: _TsWriter, decimals: int, job: ResampleJob,
                  notes: List[str]) -> "tuple[int, int]":
    ti = idx["timestamp"]
    rows_in = 0
    rows_out = 0
    with open(src, "r", encoding=enc, newline="") as fh, \
            open(tmp_path, "w", encoding=enc_out, newline="") as fo:
        rdr = csv.reader(fh, delimiter=delim)
        wr = csv.writer(fo, delimiter=delim)
        if header is not None:
            next(rdr, None)
            wr.writerow(header)
        num_cols = [c for c in range(ncols) if c != ti]
        fmt = f"{{:.{int(decimals)}f}}"

        def emit(local: np.ndarray, base_index: int, k_from: int, k_to: int) -> int:
            """local 覆盖输入索引 [base_index, base_index+len)；输出 k ∈ [k_from, k_to)。"""
            if k_to <= k_from:
                return k_from
            ks = np.arange(k_from, k_to)
            pos = ks * ratio - base_index
            if method == "nearest":
                src_i = np.clip(np.rint(pos).astype(np.int64), 0, local.shape[0] - 1)
                vals = local[src_i]
            else:
                xi = np.arange(local.shape[0], dtype=np.float64)
                vals = np.column_stack([np.interp(pos, xi, local[:, j]) for j in range(local.shape[1])])
            out_rows = []
            for r, k in enumerate(ks):
                row = [""] * ncols
                row[ti] = ts_writer.text(int(k), fs_new)
                for j, c in enumerate(num_cols):
                    row[c] = fmt.format(vals[r, j])
                out_rows.append(row)
            wr.writerows(out_rows)
            return k_to

        if method == "fft":
            all_rows: List[List[str]] = []
            for row in rdr:
                if row and any(str(c).strip() for c in row):
                    all_rows.append(row)
            rows_in = len(all_rows)
            if rows_in < 2:
                raise ResampleError("数据行不足 2 行，无法重采样")
            job.tick(0.5, "fft")
            try:
                data = np.array([[r[c] for c in num_cols] for r in all_rows], dtype=np.float64)
            except (ValueError, IndexError) as exc:
                raise ResampleError(f"数据列含非数值或列数不一致：{exc}") from None
            del all_rows
            n_in = data.shape[0]
            # 频域重采样是**周期**语义：n_in 点覆盖时长 n_in/fs_src（含回绕到下一周期的隐含点），
            # 输出 n_out = round(n_in·fs_new/fs_src) 点覆盖同一时长；比例非整时实际输出采样率略有偏差，记入 notes
            n_out = max(2, int(round(n_in * fs_new / fs_src_used)))
            fs_eff = n_out * fs_src_used / n_in
            if abs(fs_eff - fs_new) / fs_new > 1e-9:
                notes.append(f"⚠ fft 方法输出点数取整后实际采样率 {fs_eff:.6f} Hz（目标 {fs_new:g}；"
                             f"时间戳仍按目标采样率写出，偏差 {abs(fs_eff - fs_new) / fs_new * 100:.4f}%）")
            spec = np.fft.rfft(data, axis=0)
            m_in = spec.shape[0]
            m_out = n_out // 2 + 1
            new_spec = np.zeros((m_out, spec.shape[1]), dtype=np.complex128)
            keep = min(m_in, m_out)
            new_spec[:keep] = spec[:keep]
            if n_out % 2 == 0 and keep == m_out and m_out <= m_in:
                new_spec[-1] = new_spec[-1].real              # Nyquist 频点取实部
            vals = np.fft.irfft(new_spec, n=n_out, axis=0) * (n_out / n_in)
            job.tick(0.75, "write")
            out_rows = []
            for k in range(n_out):
                row = [""] * ncols
                row[ti] = ts_writer.text(k, fs_new)
                for j, c in enumerate(num_cols):
                    row[c] = fmt.format(vals[k, j])
                out_rows.append(row)
                if len(out_rows) >= _CHUNK_ROWS:
                    wr.writerows(out_rows); out_rows = []
                    job.tick(0.75 + 0.25 * k / n_out, "write")
            wr.writerows(out_rows)
            rows_out = n_out
            notes.append("fft 方法：整文件频域重采样（理想低通抗混叠；非整周期信号两端可能有振铃）")
        else:
            carry: Optional[np.ndarray] = None               # 上一块最后一行（输入索引 rows_in-1）
            k_next = 0
            chunk: List[List[str]] = []

            def flush(final: bool) -> None:
                nonlocal carry, rows_in, k_next
                if not chunk:
                    return
                try:
                    arr = np.array([[r[c] for c in num_cols] for r in chunk], dtype=np.float64)
                except (ValueError, IndexError) as exc:
                    raise ResampleError(f"第 {rows_in + 1}~{rows_in + len(chunk)} 行数据列含非数值或列数不一致：{exc}") from None
                base = rows_in - (1 if carry is not None else 0)
                local = np.vstack([carry, arr]) if carry is not None else arr
                rows_in += arr.shape[0]
                last_index = rows_in - 1                     # 目前已知的最大输入索引
                # 可输出的 k：k*ratio ≤ last_index（最后一行之前的所有点；最后一行本身也可取）
                k_max = int(math.floor(last_index / ratio + 1e-9)) + 1
                k_next = emit(local, base, k_next, k_max)
                carry = arr[-1:].copy()
                chunk.clear()

            for row in rdr:
                if not row or not any(str(c).strip() for c in row):
                    continue
                chunk.append(row)
                if len(chunk) >= _CHUNK_ROWS:
                    flush(False)
                    job.tick(fh.buffer.tell() / size if hasattr(fh, "buffer") else 0.5, "resample")
            flush(True)
            rows_out = k_next
            if rows_in < 2:
                raise ResampleError("数据行不足 2 行，无法重采样")
    return rows_in, rows_out
