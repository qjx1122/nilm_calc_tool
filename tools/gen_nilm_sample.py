#!/usr/bin/env python
"""生成负荷辨识演示样例 data/nilm_steps.csv（第 12 轮）。

三相 57.74 V 二次侧，P 总 1000 W → 2.0 s 投入 +500 W → 4.4 s 切除 −300 W，3.0 s 处一个周波 +400 W 尖峰，
PF=0.9 感性，电流叠加 2 mA 高斯噪声，fs=6400，时长 6 s。用法：.venv/bin/python tools/gen_nilm_sample.py [输出路径]

v0.36 加 ``--current-only``：只写三相电流列（表头 ``时间戳,A相电流,B相电流,C相电流``，无电压）→ data/nilm_steps_i.csv，
    用于验证「数据源只有电流」时按电流有效值检测（nilm.quantity=auto/i）；事件时刻与 nilm_steps 相同。

v0.22.1 加 ``--bus``：生成「总线上多台设备混合」样例 data/nilm_bus_mixed.csv（10 s）：
    待检设备 2.0 s 开 +500 W / 6.0 s 关 −500 W；其它设备：3.5 s +1500 W、8.0 s −1500 W（大设备）、5.0 s +120 W（小设备）。
"""
import csv
import os
import sys

import numpy as np

args = [a for a in sys.argv[1:] if not a.startswith("--")]
BUS = "--bus" in sys.argv
IONLY = "--current-only" in sys.argv
fs, dur = 6400, (10.0 if BUS else 6.0)
default_name = "nilm_bus_mixed.csv" if BUS else ("nilm_steps_i.csv" if IONLY else "nilm_steps.csv")
out = args[0] if args else os.path.join(os.path.dirname(__file__), "..", "data", default_name)
n = int(fs * dur); t = np.arange(n) / fs; w = 2 * np.pi * 50 * t
P = np.full(n, 1000.0)
if BUS:
    P[t >= 2.0] += 500; P[t >= 6.0] -= 500              # 待检设备 开/关
    P[t >= 3.5] += 1500; P[t >= 8.0] -= 1500            # 其它大设备
    P[t >= 5.0] += 120                                  # 其它小设备
    desc = "待检 2.0 s ↑500 / 6.0 s ↓500；其它 3.5 s ↑1500、8.0 s ↓1500、5.0 s ↑120 W"
else:
    P[t >= 2.0] += 500; P[t >= 4.4] -= 300
    P[int(3.0 * fs):int(3.0 * fs) + 128] += 400
    desc = "2.0 s ↑500 W，4.4 s ↓300 W；3.0 s 单周波尖峰"
U, ang = 57.74, np.arccos(0.9)
cols = []
for ph, phase in enumerate((0, -2 * np.pi / 3, 2 * np.pi / 3)):
    cols.append(U * np.sqrt(2) * np.sin(w + phase))
    cols.append((P / 3) / (U * 0.9) * np.sqrt(2) * np.sin(w + phase - ang) + np.random.default_rng(ph).normal(0, 0.002, n))
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
with open(out, "w", newline="", encoding="utf-8") as fh:
    wr = csv.writer(fh)
    if IONLY:
        cols = cols[1::2]                                   # 只保留三相电流
        wr.writerow(["时间戳", "A相电流", "B相电流", "C相电流"])
    else:
        wr.writerow(["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
    base = 1791878400.0
    for k in range(n):
        wr.writerow([f"{base + t[k]:.6f}"] + [f"{c[k]:.5f}" for c in cols])
print(f"已生成 {out}（{n} 行；事件：{desc}）")
