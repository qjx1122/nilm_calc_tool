#!/usr/bin/env python
"""生成负荷辨识演示样例 data/nilm_steps.csv（第 12 轮）。

三相 57.74 V 二次侧，P 总 1000 W → 2.0 s 投入 +500 W → 4.4 s 切除 −300 W，3.0 s 处一个周波 +400 W 尖峰，
PF=0.9 感性，电流叠加 2 mA 高斯噪声，fs=6400，时长 6 s。用法：.venv/bin/python tools/gen_nilm_sample.py [输出路径]
"""
import csv
import os
import sys

import numpy as np

fs, dur = 6400, 6.0
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "data", "nilm_steps.csv")
n = int(fs * dur); t = np.arange(n) / fs; w = 2 * np.pi * 50 * t
P = np.full(n, 1000.0); P[t >= 2.0] += 500; P[t >= 4.4] -= 300
P[int(3.0 * fs):int(3.0 * fs) + 128] += 400
U, ang = 57.74, np.arccos(0.9)
cols = []
for ph, phase in enumerate((0, -2 * np.pi / 3, 2 * np.pi / 3)):
    cols.append(U * np.sqrt(2) * np.sin(w + phase))
    cols.append((P / 3) / (U * 0.9) * np.sqrt(2) * np.sin(w + phase - ang) + np.random.default_rng(ph).normal(0, 0.002, n))
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
with open(out, "w", newline="", encoding="utf-8") as fh:
    wr = csv.writer(fh)
    wr.writerow(["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
    base = 1791878400.0
    for k in range(n):
        wr.writerow([f"{base + t[k]:.6f}"] + [f"{c[k]:.5f}" for c in cols])
print(f"已生成 {out}（{n} 行；事件：2.0 s ↑500 W，4.4 s ↓300 W；3.0 s 单周波尖峰）")
