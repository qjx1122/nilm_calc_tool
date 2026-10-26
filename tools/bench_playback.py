"""v0.82：离线 CSV 播放吞吐基准（库路径，不经服务端）。用法：
    python tools/bench_playback.py --file data/nilm_bus_mixed.csv [--config configs/default.json] [--block 640] [--profile]
输出：数据时长 / 墙钟 / 倍数（相对实时）；--profile 打印 cProfile 前 25 项。服务端路径的倍数见 README v0.82 记录。"""
from __future__ import annotations

import argparse
import cProfile
import os
import pstats
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from elec_tool.config import AppConfig           # noqa: E402
from elec_tool.engine import LiveEngine          # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--config", default=os.path.join(ROOT, "configs", "default.json"))
    ap.add_argument("--block", type=int, default=640)
    ap.add_argument("--profile", action="store_true")
    a = ap.parse_args()
    cfg = AppConfig.load(a.config)
    cfg.source.kind = "csv_file"; cfg.source.path = a.file; cfg.source.file_speed = 0.0
    cfg.source.block_samples = int(a.block); cfg.source.play_start_mode = "begin"; cfg.source.play_end_time = ""
    eng = LiveEngine(cfg, output_root=ROOT)
    pr = cProfile.Profile() if a.profile else None
    t0 = time.perf_counter()
    if pr:
        pr.enable()
    n = 0
    for _ in eng.run():
        n += 1
    if pr:
        pr.disable()
    dt = time.perf_counter() - t0
    data_s = eng.state.samples_in / float(cfg.sampling.fs)
    print(f"{a.file}: {eng.state.samples_in} 样本 = {data_s:.1f} s 数据，墙钟 {dt:.2f} s → {data_s / dt:.2f}× 实时；结果 {n} 次；块 {a.block}")
    if pr:
        pstats.Stats(pr).sort_stats("tottime").print_stats(25)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
