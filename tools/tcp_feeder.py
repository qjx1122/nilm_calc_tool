#!/usr/bin/env python3
"""TCP 数据源联调喂数器 —— 无需真实采集装置即可验证 `source.kind="tcp"` 全链路。

它扮演「采集装置/前置机」：监听一个端口，把合成的三相电压电流瞬时值按帧发给客户端
（本工具的 `TcpStreamSource`）。信号模型与 `elec_tool.sources.simulator` 完全一致
（二次侧 U1=100/√3 V、I1=5 A、电流滞后 30°、含 3/5/7/11/13 次谐波与 0.2% 噪声），
因此收到数据后算出的 U/I/P/Q/PF/THD 可与 `cli.py selftest` 的解析解期望值对账。

用法（在仓库根目录）：
  # 文本帧（每行一条 CSV，列序＝用户给定格式），实时速率
  python tools/tcp_feeder.py --port 9000 --mode text_csv

  # 文本帧 + 首行发中文表头（验证 columns.has_header 与列名映射）
  python tools/tcp_feeder.py --port 9000 --mode text_csv --header

  # 二进制帧（默认 <7d ＝ 7 个 double 小端：t,ua,ia,ub,ib,uc,ic），4 倍速灌数
  python tools/tcp_feeder.py --port 9000 --mode binary --rate 4

  # 自定义工况与自动停止
  python tools/tcp_feeder.py --port 9000 --mode binary --fs 6400 --freq 50 --duration 30

配套客户端命令（另开一个终端）：
  python cli.py live --source tcp --host 127.0.0.1 --port 9000
  # 二进制帧需让工具的帧格式与喂数器一致（默认即 <7d / t,ua,ia,ub,ib,uc,ic）：
  #   在 configs/runtime.json 或 --config 指定的配置里设 source.frame="binary"
  #   （界面路径：数据源与控制 → TCP 帧格式 → binary）

说明：
  * 单客户端串行服务（一个客户端断开后接受下一个），够联调用；
  * --rate 1.0 ＝ 按真实时间发（6400 点/s），>1 加速（压测/快速验证），<1 减速；
  * Ctrl+C 停止；--duration N 秒后自动停止。
"""

from __future__ import annotations

import argparse
import os
import socket
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elec_tool.config import AppConfig                      # noqa: E402
from elec_tool.sources.simulator import SimulatorSource      # noqa: E402

HEADER_CN = "时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流\n"


def build_sim(args: argparse.Namespace) -> SimulatorSource:
    """按命令行工况构造合成源（不做实时节流，节流由本喂数器自己控制）。"""
    cfg = AppConfig()
    cfg.sampling.fs = float(args.fs)
    cfg.sampling.f_nom = float(args.freq)
    cfg.source.block_samples = int(args.block)
    cfg.validate()
    return SimulatorSource(cfg, f=float(args.freq), realtime_pace=False,
                           block_samples=int(args.block))


def serialize(block, mode: str, fmt: str = "<7d") -> bytes:
    """把一个 SampleBlock 序列化成 wire 字节（列序＝t,ua,ia,ub,ib,uc,ic）。"""
    if mode == "binary":
        out = bytearray()
        for k in range(block.n):
            out += struct.pack(fmt, float(block.t[k]),
                               float(block.u[0, k]), float(block.i[0, k]),
                               float(block.u[1, k]), float(block.i[1, k]),
                               float(block.u[2, k]), float(block.i[2, k]))
        return bytes(out)
    lines = []
    for k in range(block.n):
        lines.append(f"{block.t[k]:.9f},{block.u[0, k]:.6f},{block.i[0, k]:.6f},"
                     f"{block.u[1, k]:.6f},{block.i[1, k]:.6f},"
                     f"{block.u[2, k]:.6f},{block.i[2, k]:.6f}\n")
    return "".join(lines).encode("utf-8")


def serve(args: argparse.Namespace) -> int:
    sim = build_sim(args)
    frame_bytes = struct.calcsize(args.struct_fmt) if args.mode == "binary" else 0
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen(1)
    print(f"● TCP 喂数器已监听 {args.host}:{args.port}  mode={args.mode}"
          f"{'（帧长 %d 字节）' % frame_bytes if frame_bytes else '（每行一条 CSV）'}")
    print(f"  fs={args.fs}Hz  f={args.freq}Hz  块={args.block}点  速率倍数={args.rate}"
          f"  时长限制={args.duration or '无'}s")
    print("  信号：二次侧 U1=57.735V(相) I1=5.000A φ=30° 谐波 3/5/7/11/13 次 噪声 0.2%")
    print("  等待客户端连接…（Ctrl+C 停止）", flush=True)

    t_start = time.time()
    sent_total = 0
    try:
        while True:
            if args.duration and (time.time() - t_start) > args.duration:
                print(f"✓ 达到时长限制 {args.duration}s，停止；共发送 {sent_total} 样本")
                return 0
            conn, addr = srv.accept()
            print(f"● 客户端已连接：{addr[0]}:{addr[1]}", flush=True)
            if args.mode == "text_csv" and args.header:
                conn.sendall(HEADER_CN.encode("utf-8"))
            try:
                with conn:
                    while True:
                        if args.duration and (time.time() - t_start) > args.duration:
                            break
                        block = sim.read()
                        if block is None or block.is_empty():
                            time.sleep(0.01)
                            continue
                        # 节流：让累计发送样本数跟随 rate × fs × 墙钟时间
                        if args.rate > 0:
                            target = (time.time() - t_start) * args.fs * args.rate
                            if sent_total + block.n > target:
                                time.sleep(min((sent_total + block.n - target) /
                                               max(args.fs * args.rate, 1.0), 1.0))
                        conn.sendall(serialize(block, args.mode, args.struct_fmt))
                        sent_total += block.n
                        if sent_total % (int(args.fs) * 5) < block.n:      # 每 ~5s 报一次
                            print(f"  已发送 {sent_total} 样本（{sent_total / args.fs:.1f}s 数据）",
                                  flush=True)
            except (BrokenPipeError, ConnectionResetError, OSError) as exc:
                print(f"· 客户端断开（{type(exc).__name__}），等待下一个连接…", flush=True)
    except KeyboardInterrupt:
        print(f"\n● 收到中断，停止；共发送 {sent_total} 样本（{sent_total / args.fs:.2f}s 数据）")
        return 0
    finally:
        srv.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="TCP 数据源联调喂数器（合成三相电压电流）")
    ap.add_argument("--host", default="0.0.0.0", help="监听地址（默认 0.0.0.0，便于跨机联调）")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--mode", choices=["text_csv", "binary"], default="text_csv",
                    help="帧格式：text_csv＝每行一条 CSV；binary＝struct 定长帧（默认 <7d）")
    ap.add_argument("--header", action="store_true", help="text_csv 模式下首行发送中文表头")
    ap.add_argument("--fs", type=float, default=6400.0, help="采样频率 Hz")
    ap.add_argument("--freq", type=float, default=50.0, help="基波频率 Hz")
    ap.add_argument("--block", type=int, default=640, help="每次发送的样本数")
    ap.add_argument("--struct-fmt", dest="struct_fmt", default="<7d",
                    help='binary 帧的 struct 格式串（默认 "<7d"＝7 个 double 小端；'
                         '可试 ">7d" 大端、"<7f" 单精度以验证客户端帧格式可配）')
    ap.add_argument("--rate", type=float, default=1.0,
                    help="速率倍数：1.0＝实时(6400点/s)，>1 加速，<1 减速")
    ap.add_argument("--duration", type=float, default=0.0, help="运行多少秒后自动停止（0＝不限）")
    args = ap.parse_args(argv)
    return serve(args)


if __name__ == "__main__":
    raise SystemExit(main())
