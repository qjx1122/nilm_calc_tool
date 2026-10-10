"""实时数据源③：TCP 客户端流。

⚠️ 帧格式属**待用户确认项**（NILM_DATA_DICT 🔶）：本项目暂未提供采集装置的通信协议，
故实现两种通用格式，真实协议确认后按需扩展 parse_frame：
  frame="text_csv"：每行一条记录，格式同离线 CSV（可带表头），如
                    `1760000000.000000,57.73,5.01,57.70,4.98,57.75,5.03`
  frame="binary"  ：定长二进制帧，按 source.struct_fmt（默认 `<7d`＝7 个 double，小端）解包，
                    字段顺序由 source.struct_fields 指定（默认 `t,ua,ia,ub,ib,uc,ic`）
"""

from __future__ import annotations

import csv
import io
import re
import socket
import struct
import time
from typing import Any, Dict, List, Optional

import numpy as np

from ..blocks import SampleBlock
from ..config import AppConfig
from .base import DataSource, note_key
from .parsing import ParseError, parse_timestamps


class TcpStreamSource(DataSource):
    kind = "tcp"

    def __init__(self, cfg: AppConfig, host: Optional[str] = None, port: Optional[int] = None,
                 frame: Optional[str] = None, timeout_s: float = 2.0,
                 block_samples: Optional[int] = None, reconnect_s: float = 2.0,
                 tz_offset_h: float = 0.0):
        self.cfg = cfg
        self.host = host or cfg.source.host
        self.port = int(port or cfg.source.port)
        self.frame = frame or cfg.source.frame
        self.timeout_s = float(timeout_s)
        self.reconnect_s = float(reconnect_s)
        self.block_samples = int(block_samples or cfg.source.block_samples or 640)
        self.tz_offset_h = tz_offset_h
        self._sock: Optional[socket.socket] = None
        self._buf = b""
        self._pending: List[List[float]] = []
        self._pending_t: List[Any] = []
        self._colmap_resolved: Optional[Dict[str, int]] = None
        self._header_seen = False
        self._n_blocks = 0
        self._n_samples = 0
        self._seq = 0
        self._connected_at: Optional[float] = None
        self._last_recv_at: Optional[float] = None
        self._reconnects = 0
        self._t_next: Optional[float] = None
        self._notes: List[str] = []
        self._frame_size = struct.calcsize(cfg.source.struct_fmt) if self.frame == "binary" else 0
        self._fields = [f.strip() for f in getattr(cfg.source, "struct_fields", "t,ua,ia,ub,ib,uc,ic").split(",")]

    def _note(self, msg: str) -> None:
        """追加告警并**去重**：同一问题每个数据块都会触发，重复 20 条会淹没真正的新信息。

        去重口径见 base.note_key（中文骨架，去数字与 ASCII），只比对最近 5 条。
        """
        # 为什么要归一化：同一问题的告警每块都带不同数值/单位模式名（s、ms、us、ns），
        # 按原文去重无效——实测帧格式不匹配时刷出 6 条几乎相同的告警
        key = note_key(msg)
        if any(note_key(n) == key for n in self._notes[-5:]):
            return
        self._notes.append(msg)          # 注意：此处必须直接 append，调 _note 会无限递归
        if len(self._notes) > 20:
            self._notes = self._notes[-20:]

    # ---------- 生命周期 ----------
    def open(self) -> None:
        self._connect()

    def _connect(self) -> None:
        try:
            self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout_s)
            self._sock.settimeout(self.timeout_s)
            self._connected_at = time.time()
            self._note(f"已连接 {self.host}:{self.port}（frame={self.frame}）")
        except OSError as exc:
            self._sock = None
            raise ParseError(
                f"TCP 连接失败 {self.host}:{self.port} —— {exc}。"
                f"排查：① 采集服务是否已启动并监听该端口 ② 防火墙/网段 ③ 配置 source.host/port 是否正确"
            ) from exc

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None
        self._pending = []
        self._pending_t = []

    @property
    def exhausted(self) -> bool:
        return False

    # ---------- 读取 ----------
    def read(self) -> Optional[SampleBlock]:
        if self._sock is None:
            self._connect()
        try:
            chunk = self._sock.recv(1 << 16) if self._sock else b""
        except (socket.timeout, TimeoutError):
            return None
        except OSError as exc:
            self._note(f"接收异常：{exc}；{self.reconnect_s}s 后重连")
            self.close()
            time.sleep(self.reconnect_s)
            self._reconnects += 1
            try:
                self._connect()
            except ParseError as exc2:
                self._note(str(exc2))
                return None
            return None
        if chunk == b"":
            self._note("对端关闭连接，准备重连")
            self.close()
            time.sleep(self.reconnect_s)
            self._reconnects += 1
            try:
                self._connect()
            except ParseError as exc:
                self._note(str(exc))
            return None
        self._last_recv_at = time.time()
        self._buf += chunk
        if self.frame == "binary":
            self._parse_binary()
        else:
            self._parse_text()
        if len(self._pending) >= self.block_samples:
            return self._flush_block(self.block_samples)
        return None

    def _parse_binary(self) -> None:
        fs_size = self._frame_size
        if fs_size <= 0:
            raise ParseError(f"binary 帧格式非法：source.struct_fmt={self.cfg.source.struct_fmt!r}")
        n_frames = len(self._buf) // fs_size
        if n_frames == 0:
            return
        raw = self._buf[: n_frames * fs_size]
        self._buf = self._buf[n_frames * fs_size:]
        fmt = self.cfg.source.struct_fmt
        unpacked = [struct.unpack(fmt, raw[k * fs_size:(k + 1) * fs_size]) for k in range(n_frames)]
        for frame in unpacked:
            rec = dict(zip(self._fields, [float(v) for v in frame]))
            self._append_record(rec)

    def _parse_text(self) -> None:
        if b"\n" not in self._buf:
            return
        *lines, rest = self._buf.split(b"\n")
        self._buf = rest
        text = b"\n".join(lines).decode("utf-8", errors="replace")
        for row in csv.reader(io.StringIO(text), delimiter=self.cfg.columns.delimiter):
            if not row or all(not str(c).strip() for c in row):
                continue
            cells = [c.strip() for c in row]
            if not self._header_seen and self.cfg.columns.has_header:
                try:
                    float(cells[0])
                except ValueError:
                    # 首行是表头 → 解析列映射
                    try:
                        self._colmap_resolved = self.cfg.columns.resolve(cells)
                        self._header_seen = True
                        self._note(f"识别到表头：{cells} → 映射 {self._colmap_resolved}")
                        continue
                    except Exception:
                        pass
            if self._colmap_resolved:
                rec = {}
                for key, idx in self._colmap_resolved.items():
                    if idx < len(cells):
                        rec[key] = cells[idx]
                self._append_record(rec, str_timestamp=True)
            else:
                # 无表头：按用户给定列序 t,ua,ia,ub,ib,uc,ic
                if len(cells) < 7:
                    self._note(f"跳过字段不足的行（{len(cells)}<7）：{cells[:3]}…")
                    continue
                self._append_record({"t": cells[0], "ua": cells[1], "ia": cells[2], "ub": cells[3],
                                     "ib": cells[4], "uc": cells[5], "ic": cells[6]}, str_timestamp=True)

    def _append_record(self, rec: Dict[str, Any], str_timestamp: bool = False) -> None:
        try:
            vals = [float(rec.get(k, np.nan)) for k in ("ua", "ia", "ub", "ib", "uc", "ic")]
        except (TypeError, ValueError):
            self._note(f"记录含非数值字段，已跳过：{rec}")
            return
        self._pending.append(vals)
        self._pending_t.append(rec.get("t"))
        if len(self._notes) > 20:
            self._notes = self._notes[-20:]

    def _flush_block(self, n: int) -> SampleBlock:
        rows = self._pending[:n]
        ts_raw = self._pending_t[:n]
        self._pending = self._pending[n:]
        self._pending_t = self._pending_t[n:]
        arr = np.asarray(rows, dtype=np.float64)           # (n,6) → ua,ia,ub,ib,uc,ic
        u = np.vstack([arr[:, 0], arr[:, 2], arr[:, 4]])
        i = np.vstack([arr[:, 1], arr[:, 3], arr[:, 5]])
        # 时间戳：有则解析，无则按 fs 续接
        t: np.ndarray
        if all(v is not None for v in ts_raw) and ts_raw:
            try:
                info = parse_timestamps([str(v) for v in ts_raw], self.cfg.columns.timestamp_unit,
                                        self.tz_offset_h)
                t = info.t
                for n in info.notes:          # 解析层告警必须冒泡，否则用户看不到时间轴已退化
                    self._note(n)
                if t.size != arr.shape[0] or not np.all(np.isfinite(t)):
                    raise ValueError("时间戳解析结果与样本数不一致")
            except Exception as exc:
                self._note(f"时间戳解析失败（{exc}），改用 fs 合成时间轴")
                t = self._synthetic_t(arr.shape[0])
        else:
            t = self._synthetic_t(arr.shape[0])
        block = SampleBlock(t=t, u=u, i=i, scaled=False, source=f"tcp:{self.host}:{self.port}", seq=self._seq)
        self._seq += 1
        self._n_blocks += 1
        self._n_samples += block.n
        return block

    def _synthetic_t(self, n: int) -> np.ndarray:
        """无时标时按配置 fs 生成连续时间轴（起点＝连接时刻），保证块间时间单调不重叠。"""
        fs = float(self.cfg.sampling.fs)
        if self._t_next is None:
            self._t_next = self._connected_at or time.time()
        t = self._t_next + np.arange(n, dtype=np.float64) / fs
        if n:
            self._t_next = float(t[-1] + 1.0 / fs)
        return t

    def info(self) -> Dict[str, Any]:
        return {
            "kind": self.kind, "host": self.host, "port": self.port, "frame": self.frame,
            "connected": self._sock is not None, "connected_at": self._connected_at,
            "last_recv_at": self._last_recv_at, "reconnects": self._reconnects,
            "buffer_bytes": len(self._buf), "pending_rows": len(self._pending),
            "block_samples": self.block_samples, "blocks_read": self._n_blocks,
            "samples_read": self._n_samples, "struct_fmt": self.cfg.source.struct_fmt,
            "struct_fields": self._fields, "colmap": self._colmap_resolved,
            "notes": list(self._notes),
            "protocol_status": "🔶待确认：真实采集协议（帧头/字节序/时标格式）需用户提供后校准",
        }
