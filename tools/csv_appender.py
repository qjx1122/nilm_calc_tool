#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CSV 追加喂数器：模拟「采集器边采边写文件」，用于验证 csv_tail 数据源（无需真实硬件）。

用户的实时落地方式（见 NILM_DATA_DICT.md）＝采集器把二次侧三相电压电流写成 CSV，
列格式 `时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流`，fs=6400Hz。
本工具按同样的列格式追加，信号模型复用 SimulatorSource（与 `cli.py selftest` 的解析解同源，
因此 csv_tail 的结果可以直接和 tcp / simulator 两个源对账）。

四种典型验证（另开终端跑计算侧）：

    # ① 文件 + 从头读（含历史）
    python tools/csv_appender.py --out data/tail_live.csv --rate 4
    python cli.py live --source csv_tail --path data/tail_live.csv

    # ② 文件 + 只读启动之后的新增（真实运行常用，避免算历史）
    python cli.py live --source csv_tail --path data/tail_live.csv --from-end

    # ③ 目录 + 跟最新文件（采集器按时间分片写多个文件）
    python tools/csv_appender.py --out data/tail_dir --rotate-every 20 --rate 4
    python cli.py live --source csv_tail --path data/tail_dir --watch-newest

    # ④ 轮转/截断：--rotate-every N 每 N 块换新文件；旧文件保留，csv_tail 靠 inode 变化感知
退出码：0 正常结束（含 --duration 到时）、130 Ctrl+C。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from elec_tool.config import AppConfig                      # noqa: E402
from elec_tool.sources.simulator import SimulatorSource      # noqa: E402

HEADER = "时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流"


def build_sim(args: argparse.Namespace) -> SimulatorSource:
    """按命令行工况构造合成源（实时节流交给 SimulatorSource 的 realtime_pace/speed）。"""
    cfg = AppConfig()
    cfg.sampling.fs = float(args.fs)
    cfg.sampling.f_nom = float(args.freq)
    cfg.source.block_samples = int(args.block)
    cfg.validate()
    return SimulatorSource(cfg, f=float(args.freq), realtime_pace=True,
                           speed=float(args.rate), block_samples=int(args.block))


def target_path(args: argparse.Namespace, part: int) -> Path:
    """--out 无扩展名（视为目录）或给了 --rotate-every → 写 part_NNN.csv；否则就是该文件本身。"""
    out = Path(args.out)
    if args.rotate_every > 0 or out.suffix == "":
        out.mkdir(parents=True, exist_ok=True)
        return out / f"part_{part:03d}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def open_writer(path: Path, header: bool):
    fh = path.open("w", encoding="utf-8", newline="")
    if header:
        fh.write(HEADER + "\n")
    fh.flush()
    return fh


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CSV 追加喂数器（模拟采集器写文件，验证 csv_tail）")
    ap.add_argument("--out", required=True,
                    help="目标 CSV 文件；无扩展名或给了 --rotate-every 时视为目录，写 part_NNN.csv")
    ap.add_argument("--fs", type=float, default=6400.0, help="采样率 Hz（默认 6400）")
    ap.add_argument("--freq", type=float, default=50.0, help="基波频率 Hz（默认 50）")
    ap.add_argument("--block", type=int, default=640, help="每次追加的样本点数（默认 640＝0.1s@6400Hz）")
    ap.add_argument("--rate", type=float, default=1.0, help="实时速率倍数：1＝真实速度，4＝四倍速（默认 1）")
    ap.add_argument("--duration", type=float, default=0.0, help="持续秒数，0＝不限（默认 0，Ctrl+C 停）")
    ap.add_argument("--rotate-every", type=int, default=0, help="每写 N 个块换新文件（0＝不换，默认 0）")
    ap.add_argument("--no-header", action="store_true", help="不写表头行（验证无表头解析路径）")
    ap.add_argument("--pt", type=float, default=100.0, help="PT 变比（默认 100，仅用于日志显示）")
    ap.add_argument("--ct", type=float, default=15.0, help="CT 变比（默认 15，仅用于日志显示）")
    args = ap.parse_args(argv)

    src = build_sim(args)
    part = 0
    path = target_path(args, part)
    fh = open_writer(path, not args.no_header)

    print(f"● CSV 追加喂数器：{path}")
    print(f"  fs={args.fs}Hz  f={args.freq}Hz  块={args.block}点  速率倍数={args.rate}  "
          f"时长限制={args.duration or '不限'}  "
          f"轮转={'每 %d 块' % args.rotate_every if args.rotate_every else '关'}  "
          f"表头={'无' if args.no_header else HEADER.split(',')[0] + ' 等 7 列'}")
    print(f"  信号：二次侧三相 U/I（PT={args.pt} CT={args.ct}），含 3/5/7/11/13 次谐波与 0.2% 噪声")
    print(f"  计算侧示例：python cli.py live --source csv_tail --path {args.out} --from-end")

    t0 = time.time()
    n_blocks = n_rows = 0
    try:
        src.open()
        while True:
            if args.duration and (time.time() - t0) >= args.duration:
                break
            blk = src.read()
            if blk is None or blk.is_empty():
                continue
            t, u, i = blk.t, blk.u, blk.i
            # 二次侧原始值直接落盘：与真实采集器一致，变比换算由计算侧 transform 负责
            rows = "".join(
                "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n" % (t[k], u[0, k], i[0, k], u[1, k], i[1, k],
                                                           u[2, k], i[2, k])
                for k in range(t.size))
            fh.write(rows)
            fh.flush()          # 必须 flush：csv_tail 靠文件长度变化发现新数据
            n_blocks += 1
            n_rows += int(t.size)
            if args.rotate_every and n_blocks % args.rotate_every == 0:
                fh.close()
                part += 1
                path = target_path(args, part)
                fh = open_writer(path, not args.no_header)
                print(f"  ↻ 轮转到新文件：{path}")
    except KeyboardInterrupt:
        print("\n● 收到 Ctrl+C，停止追加")
        return 130
    finally:
        try:
            fh.close()
        except Exception:
            pass
        src.close()
    el = max(1e-9, time.time() - t0)
    print(f"✓ 结束：追加 {n_rows} 行 / {n_blocks} 块，用时 {el:.1f}s（{n_rows / el:.0f} 行/s），文件 {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
