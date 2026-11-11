"""v0.99.52（第 212 轮）：设备画像**自动定位**漏掉停止事件——启停交替校验 + 起点精修。

用户实录（搅拌机，约每 123 s 运行 31 s，不给标签）：9 次启动全部找到，10 次停止只找到 4 次，其中 1 次的起点早了 55 个周波。
原因：自动定位的两种方法（稳态分段、双滑窗）都要求**动作之前**的电平平稳。启动之前是停机（很平）⇒ 都能找到；
停止之前是运行，这台设备运行时逐周波有效值上下摆几安（电流里约三成不是工频分量）⇒ 稳态分段的事件前稳态段被打断，
双滑窗的门槛被前窗的波动抬到比台阶还高，两边都漏。

覆盖
- ``auto_locate_events``（逐周波序列进、事件表出）：
  · 运行电平波动 ⇒ 漏掉的停止由启停交替校验补出（``auto:alternation``），起点误差 ≤ 2 周波，没有多出来的事件；
    文件开头就在运行、文件结尾仍在运行、只有一次运行、启动的台阶被冲击抬高几倍、某一次启动的冲击特别大、
    逐周波有效值深度脉动、运行中途掉电十几个周波、量纲放大 1000 倍（功率口径） 都一样；
  · 稳态分段给的起点偏早（事件前的波动只出现在停止前几十个周波）⇒ 起点精修挪到突变处；停止落在周波中间也挪得到；
  · 启停顺序本来就交替的序列（分级带载、多档位、星三角、带冲击的干净启停、两段式停止）⇒ 与只用稳态分段 + 双滑窗的
    结果**完全相同**；
  · 缓慢漂移切出来的碎片 ⇒ 不误报；软停（斜坡）⇒ 不编造事件，只在 ``alternation_unresolved`` 里报出来；
- ``_alternation_check``（直接给事件表）：补出的起点准到周波（停止前正处在波动的下行段、停止拖了三个周波）；
  软停降到三成再切断的那一下不补；贴着文件头尾、前窗 / 后窗放不下的不补；返回值按起点排好；空事件表；
- ``_onset_scores``：抽成函数后与原先 ``_locate_near`` 里的写法逐值相同（标签模式不受影响）；
- ``build_profile``（采样波形 CSV，口径 / 窗长与用户那次提取相同）：3 次启动 + 3 次停止，停止全部来自交替校验，
  notes 里有「启停交替校验补出」；起点精修的波形给出「起点做了精修」；软停波形给出「还有动作没能补出来」的提示。
"""
from __future__ import annotations

import numpy as np
import pytest

from elec_tool.config import AppConfig
from elec_tool.nilm import detect_steps
from elec_tool.nilm_auto import auto_params
from elec_tool.nilm_profile import (SRC_ALTERNATION, _alternation_check, _onset_scores, _state_onset, auto_locate_events,
                                    build_profile, transition_end)

PRE, POST = 10, 50                                  # 与用户那次提取相同的前窗 / 后窗（周波）
R3 = ((1000, 2500), (4000, 5500), (7000, 8200))     # 三次运行（启动周波, 停止周波）
HEAD_RUN = ((-500, 900), (2500, 4000), (5500, 7000))   # 文件开头就在运行
TAIL_RUN = ((1000, 2500), (4000, 5500), (7000, 9500))  # 文件结尾仍在运行
STARTS3 = [(st, st + 49) for st, _sp in R3]         # 只有 R3 三次启动的事件表 (起点, 终点)


# ---------------------------------------------------------------- 逐周波序列
def _series(L, runs, *, base=1.0, level=10.0, levels=None, fluct=3.0, period=6.6, noise=0.02, inrush=None, seed=12, scale=1.0):
    """停机＝base（平稳）；运行＝base+level（levels 给出每次运行各自的电平），再叠加幅度 fluct、周期 period 周波的波动（转矩脉动）。
    runs 里的启动可以是负数（文件开头就在运行）、停止可以超过 L（文件结尾仍在运行）。"""
    rng = np.random.default_rng(seed)
    x = np.full(L, float(base))
    for i, (st, sp) in enumerate(runs):
        a, b = max(st, 0), min(sp, L); k = np.arange(b - a) + (a - st)
        lv = np.full(b - a, float(levels[i] if levels else level))
        if inrush is not None and st >= 0:
            lv = lv + inrush(k)
        x[a:b] += lv + fluct * np.sin(2 * np.pi * k / period + rng.uniform(0, 6.28))
    return (x + rng.normal(0, noise, L)) * scale


def _steps(L, events, *, base=1.0, noise=0.02, seed=11):
    """干净的台阶序列：events＝[(周波, 变化量)]。"""
    rng = np.random.default_rng(seed)
    x = np.full(L, float(base))
    for k, d in events:
        x[k:] += d
    return x + rng.normal(0, noise, L)


def _inrush(k):
    """启动冲击：+40 起、时间常数 15 周波。"""
    return 40.0 * np.exp(-k / 15.0)


def _big_inrush(k):
    """大的启动冲击：+60 起、时间常数 40 周波——后窗（50 周波）整个落在冲击里，启动量出来的台阶是运行电平的 3 倍。"""
    return 60.0 * np.exp(-k / 40.0)


def _some_big_inrush(runs, which):
    """三次运行（运行时波动），只有 which 里的那几次启动带大冲击。"""
    x = _series(9000, runs)
    for i in which:
        x[runs[i][0]:runs[i][0] + 200] += _big_inrush(np.arange(200))
    return x


def _dropout(n):
    """三次运行（运行时波动），每次运行到第 700 个周波时掉到停机电平 n 个周波又恢复。"""
    x = _series(9000, R3)
    for st, _sp in R3:
        x[st + 700:st + 700 + n] = 1.0
    return x


def _fluct_runs(phase, fall=(), seed=11):
    """R3 三次运行，运行电平 10±3（周期 6.6 周波），波动的相位按**停止时刻**对齐（phase）；fall 给出停止时拖的几个半截周波
    （各自还剩运行电平的几成）。"""
    rng = np.random.default_rng(seed)
    x = np.full(9000, 1.0)
    for st, sp in R3:
        x[st:sp] += 10.0 + 3.0 * np.sin(2 * np.pi * (np.arange(st, sp) - sp) / 6.6 + phase)
        for j, f in enumerate(fall):
            x[sp + j] += 10.0 * f
    return x + rng.normal(0, 0.02, 9000)


def _burst_before_stop(n_burst, *, calm=0.0, burst=1.5, period=6.6, partial=0.0, seed=11):
    """运行大部分时间平稳（波动 ±calm），只在每次停止前 n_burst 个周波里波动加大到 ±burst；partial>0 时停止落在周波中间
    （停止的那个周波还剩运行电平的 partial）。"""
    rng = np.random.default_rng(seed)
    x = np.full(9000, 1.0)
    for st, sp in R3:
        n = sp - st
        a = np.full(n, float(calm)); a[n - n_burst:] = burst
        x[st:sp] += 10.0 + a * np.sin(2 * np.pi * np.arange(n) / period + rng.uniform(0, 6.28))
        x[sp] += 10.0 * partial
    return x + rng.normal(0, 0.02, 9000)


def _two_stage_stop(L, runs, *, inrush=None, levels=None, n_slow=15, frac=0.6, n_pre=0, seed=11):
    """干净的启停（运行时不波动）；n_slow>0 时停止分两段：先在 n_slow 个周波里缓降 frac，再突降到停机电平；
    n_pre>0 时缓降之前还有 n_pre 个周波的波动（±1.5）。levels 给出每次运行的负荷（默认都是 10）。"""
    rng = np.random.default_rng(seed)
    x = np.full(L, 1.0)
    for (st, sp), lev in zip(runs, levels or [10.0] * len(runs)):
        n = sp - st
        lv = np.full(n, float(lev))
        if inrush is not None:
            lv = lv + inrush(np.arange(n))
        if n_pre:
            lv[n - n_slow - n_pre:n - n_slow] += 1.5 * np.sin(2 * np.pi * np.arange(n_pre) / 6.6 + rng.uniform(0, 6.28))
        if n_slow:
            lv[-n_slow:] -= lev * frac * (np.arange(n_slow) + 1) / n_slow
        x[st:sp] += lv
    return x + rng.normal(0, 0.02, L)


def _staged_with_decay(seed=11):
    """分级带载，第一级带缓慢衰减的冲击：+5（+6 起、时间常数 100 周波的衰减）→ 750 周波后升到 +10 → 停。"""
    rng = np.random.default_rng(seed)
    x = np.full(8000, 1.0)
    for a in (1000, 4500):
        x[a:a + 750] += 5 + 6 * np.exp(-np.arange(750) / 100.0); x[a + 750:a + 2000] += 10
    return x + rng.normal(0, 0.02, 8000)


def _soft_start_in_the_middle(n_ramp=250, seed=12):
    """R3 三次运行（运行时波动，停止都是突降），第二次是软启动：在 n_ramp 个周波里线性升上来。"""
    rng = np.random.default_rng(seed)
    x = np.full(9000, 1.0)
    for i, (st, sp) in enumerate(R3):
        lv = np.full(sp - st, 10.0)
        if i == 1:
            lv[:n_ramp] = 10.0 * (np.arange(n_ramp) + 1) / n_ramp
        x[st:sp] += lv + 3.0 * (lv / 10.0) ** 0.5 * np.sin(2 * np.pi * np.arange(sp - st) / 6.6 + rng.uniform(0, 6.28))
    return x + rng.normal(0, 0.02, 9000)


def _ramp_stop(n_ramp, *, to=0.0, runs=R3, seed=12):
    """运行时波动（±3）；停止不是突降：在 n_ramp 个周波里线性降到「停机电平 + to」，to>0 时最后再突降 to（软停到一定转速后切断）。
    runs 里的启动可以是负数（文件开头就在运行）。"""
    rng = np.random.default_rng(seed)
    x = np.full(9000, 1.0)
    for st, sp in runs:
        n = sp - st + n_ramp
        lv = np.full(n, 10.0); lv[sp - st:] = 10.0 - (10.0 - to) * (np.arange(n_ramp) + 1) / n_ramp
        y = lv + 3.0 * (lv / 10.0) ** 0.5 * np.sin(2 * np.pi * np.arange(n) / 6.6 + rng.uniform(0, 6.28))
        x[max(st, 0):st + n] += y[max(-st, 0):]
    return x + rng.normal(0, 0.02, 9000)


def _two_methods(x, pre_n=PRE, post_n=POST):
    """v0.99.51 及以前的自动定位：稳态分段 + 双滑窗补充，终点按 transition_end（照抄旧逻辑，用来确认「不该动的一个不变」）。"""
    ap = auto_params(x, 50.0)
    prm = ap["algorithms"]["steady_state"]
    steps = [(int(a), int(b), "auto:steady_state") for a, b, *_r in detect_steps("steady_state", x, prm)]
    guard = max(post_n, int(prm.get("max_transient_cycles", post_n)))
    for a, b, *_r in detect_steps("two_window", x, ap["algorithms"]["two_window"]):
        if all(abs(int(a) - s[0]) > guard for s in steps):
            steps.append((int(a), int(b), "auto:two_window"))
    steps.sort(key=lambda s: s[0])
    out = []
    for onset, end, src in steps:
        if onset + 2 <= x.size:
            tgt = float(np.median(x[onset:onset + post_n])); dl = tgt - float(np.median(x[max(0, onset - pre_n):onset]))
            end = transition_end(x, onset, post_n, tgt, abs(dl))
        out.append((onset, int(end), src))
    return out


def _split(x, ev):
    """事件表 → (上升事件 [(起点, 来源)], 下降事件 [(起点, 来源)])；方向按事件前后电平之差。"""
    up, dn = [], []
    for o, e, s in ev:
        d = float(np.median(x[e:e + POST]) - np.median(x[max(0, o - PRE):o]))
        (up if d >= 0 else dn).append((o, s))
    return up, dn


def _near(got, truth, tol=2):
    return len(got) == len(truth) and all(abs(o - k) <= tol for (o, _s), k in zip(got, truth))


# ---------------------------------------------------------------- auto_locate_events：启停交替校验
@pytest.mark.parametrize("name,x,ups,downs", [
    ("三次运行", _series(9000, R3), [1000, 4000, 7000], [2500, 5500, 8200]),
    ("文件开头就在运行", _series(9000, HEAD_RUN), [2500, 5500], [900, 4000, 7000]),
    ("文件结尾仍在运行", _series(9000, TAIL_RUN), [1000, 4000, 7000], [2500, 5500]),
    ("只有一次运行", _series(6000, ((2000, 3200),)), [2000], [3200]),
    # 启动量出来的台阶是运行电平的 3 倍：「这一段的运行电平」要从段里量（冲击时间短，压不过运行那一段），不能直接用台阶；
    # 文件开头那一段也要拿量到的运行电平去比，不能拿台阶比
    ("启动的台阶被冲击抬高到 3 倍，文件开头就在运行", _series(9000, HEAD_RUN, inrush=_big_inrush), [2500, 5500], [900, 4000, 7000]),
    # 只有一次启动的台阶特别大：典型台阶不能被它带偏，否则另外两次启动算不上主要动作，第一次停止就查不到
    ("只有第二次启动带大冲击", _some_big_inrush(R3, (1,)), [1000, 4000, 7000], [2500, 5500, 8200]),
    # 第一次启动算不上主要动作，文件开头又是停机：开头那一段照样按电平状态核对，第一次停止才找得回来
    ("只有后两次启动带大冲击（文件开头停机）", _some_big_inrush(R3, (1, 2)), [1000, 4000, 7000], [2500, 5500, 8200]),
    # 最后一次启动算不上主要动作，文件结尾仍在运行：结尾那一段照样核对，第二次停止才找得回来
    ("只有前两次启动带大冲击（文件结尾仍在运行）", _some_big_inrush(TAIL_RUN, (0, 1)), [1000, 4000, 7000], [2500, 5500]),
    # 逐周波有效值在 3.5～18.5 之间摆（单个周波会掉到判定线以下）：电平状态要在中值平滑后的序列上看
    ("逐周波有效值深度脉动，文件开头就在运行", _series(9000, HEAD_RUN, fluct=7.5), [2500, 5500], [900, 4000, 7000]),
    # 运行中途掉到停机电平 16 个周波又恢复：状态没保持住，不算一次停止 + 启动
    ("运行中途掉电 16 个周波", _dropout(16), [1000, 4000, 7000], [2500, 5500, 8200]),
])
def test_alternation_adds_stops_missed_when_run_level_fluctuates(name, x, ups, downs):
    ev, info = auto_locate_events(x, 50.0, PRE, POST)
    up, dn = _split(x, ev)
    assert _near(up, ups), (name, up)
    assert _near(dn, downs), (name, dn)                                   # 停止一个不漏、一个不多，起点误差 ≤ 2 周波
    assert all(s == SRC_ALTERNATION for _o, s in dn), (name, dn)          # 稳态分段和双滑窗都没找到它们（夹具确实踩到了缺陷）
    assert all(s != SRC_ALTERNATION for _o, s in up), (name, up)
    assert info["n_alternation"] == len(downs) and info["alternation_unresolved"] == [], (name, info)
    assert [o for o, _e, _s in ev] == sorted(o for o, _e, _s in ev)       # 按起点排好


def test_alternation_is_scale_free_and_handles_start_inrush():
    # 功率口径（数值大 1000 倍）：结果与电流口径逐个相同
    x = _series(9000, R3); xk = _series(9000, R3, scale=1000.0)
    ev, _ = auto_locate_events(x, 50.0, PRE, POST); evk, _ = auto_locate_events(xk, 50.0, PRE, POST)
    assert evk == ev
    # 启动带 5 倍冲击（时间常数 15 周波）：启动量出来的台阶比停止大得多，停止照样补得出来
    xi = _series(9000, R3, inrush=_inrush)
    evi, info = auto_locate_events(xi, 50.0, PRE, POST)
    up, dn = _split(xi, evi)
    assert _near(up, [1000, 4000, 7000]) and _near(dn, [2500, 5500, 8200]), (up, dn)
    assert all(s == SRC_ALTERNATION for _o, s in dn) and info["alternation_unresolved"] == []


def test_alternation_recovers_a_short_run_missed_by_both_methods():
    """文件开头有一次只转了 30 个周波的运行（稳态分段和双滑窗都没报），后面是一次正常的启停：开头那一段按电平状态核对时，
    这次短运行的启动和停止都补得出来；其余事件与旧逻辑相同。"""
    x = _steps(6000, [(1000, 10), (1030, -10), (3000, 10), (4500, -10)])
    old = _two_methods(x)
    assert not any(abs(o - k) <= 5 for o, _e, _s in old for k in (1000, 1030))        # 旧逻辑：短运行的两个动作都没有
    ev, info = auto_locate_events(x, 50.0, PRE, POST)
    assert [v for v in ev if v[2] != SRC_ALTERNATION] == old
    assert [(o, e - o <= 1) for o, e, s in ev if s == SRC_ALTERNATION] == [(1000, True), (1030, True)]
    assert info["n_alternation"] == 2 and info["alternation_unresolved"] == []


# ---------------------------------------------------------------- auto_locate_events：起点精修
def test_refine_moves_early_onset_to_the_step():
    """运行大部分时间很平，只在每次停止前 55 个周波里波动：稳态分段能找到停止，但起点记在波动开始的地方（早 55 周波）。"""
    x = _burst_before_stop(55)
    old_dn = sorted(o for o, _e, _s in _two_methods(x) if o not in (1000, 4000, 7000))
    assert len(old_dn) == 3 and all(50 <= sp - o <= 56 for o, (_st, sp) in zip(old_dn, R3)), old_dn   # 旧逻辑：三次停止都早 55 个周波左右
    ev, info = auto_locate_events(x, 50.0, PRE, POST)
    up, dn = _split(x, ev)
    assert _near(up, [1000, 4000, 7000], tol=0) and _near(dn, [2500, 5500, 8200], tol=1), (up, dn)
    assert info["n_refined"] == 3 and 50 <= info["refine_max_shift"] <= 56 and info["n_alternation"] == 0
    assert all(s == "auto:steady_state" for _o, s in up + dn)                               # 来源不变，只是起点挪了
    stops = [v for v in ev if v[0] not in (1000, 4000, 7000)]
    assert len(stops) == 3 and all(e - o <= 2 for o, e, _s in stops)                        # 持续周波数不再把波动算进去


def test_refine_reaches_past_a_partial_cycle():
    """运行电平一直有波动（±1），停止前 60 个周波加大到 ±3，停止落在周波中间（那个周波还剩三成）。稳态分段的容差跟着波动变宽，
    事件后稳态段从那个半截周波就开始了——精修要再往后一个周波才找得到落稳的地方，不然起点还留在 60 个周波之前。"""
    x = _burst_before_stop(60, calm=1.0, burst=3.0, period=3.3, partial=0.3, seed=12)
    old_dn = sorted(o for o, _e, _s in _two_methods(x) if o not in (1000, 4000, 7000))
    assert len(old_dn) == 3 and all(55 <= sp - o <= 62 for o, (_st, sp) in zip(old_dn, R3)), old_dn
    ev, info = auto_locate_events(x, 50.0, PRE, POST)
    up, dn = _split(x, ev)
    assert _near(up, [1000, 4000, 7000], tol=0) and _near(dn, [2500, 5500, 8200], tol=1), (up, dn)
    assert info["n_refined"] == 3 and info["n_alternation"] == 0 and info["alternation_unresolved"] == []


# ---------------------------------------------------------------- auto_locate_events：不该动的一个不变
@pytest.mark.parametrize("name,x", [
    ("分级带载 +5 +5 −10", _steps(8000, [(1000, 5), (1800, 5), (3000, -10), (5000, 5), (5800, 5), (7000, -10)])),
    ("多档位 0-5-10-5-0", _steps(9000, [(800, 5), (1600, 5), (2400, -5), (3200, -5), (5000, 5), (5800, 5), (6600, -5), (7400, -5)])),
    ("星三角 +30（100 周波）→ +10", _steps(9000, [(k + d, v) for k, _sp in R3 for d, v in ((0, 30), (100, -20))] + [(sp, -10) for _k, sp in R3])),
    ("星三角，另一组噪声", _steps(9000, [(k + d, v) for k, _sp in R3 for d, v in ((0, 30), (100, -20))] + [(sp, -10) for _k, sp in R3], seed=14)),
    ("带冲击的干净启停", _series(9000, R3, fluct=0.0, inrush=_inrush, seed=11)),
    ("带冲击的干净启停，另一组噪声", _series(9000, R3, fluct=0.0, inrush=_inrush, seed=14)),
    # 第一级的后窗落在衰减里，量出来比第二级大：两级仍是「接着往上走」，不能当成「同方向、中间缺一次停止」
    ("第一级带缓慢衰减的分级带载", _staged_with_decay()),
    # 先缓降六成、再突降：稳态分段的起点在缓降开始处，这不是「起点偏早」，不精修
    ("两段式停止（先缓降、再突降）", _two_stage_stop(9000, R3)),
    ("带冲击的启动 + 两段式停止", _two_stage_stop(9000, R3, inrush=_inrush)),
    # 启动的台阶被抬高到 3 倍，只有启动算得上主要动作，相邻两次启动之间要查。查到的翻转在突降处，已有的停止事件
    # 起点在缓降开始处（早 15 个周波）、终点在突降之后——翻转落在这个事件里，就是它，不能在突降处再补一个
    ("启动的台阶被冲击抬高到 3 倍 + 两段式停止", _two_stage_stop(9000, R3, inrush=_big_inrush)),
    # 停止前先波动 60 个周波，再缓降八成，最后突降两成：最后那一下只是个小尾巴，不是「起点偏早」，不精修
    ("停止前波动一阵、缓降八成、再突降", _two_stage_stop(9000, R3, frac=0.8, n_pre=60)),
    # 第三次运行只带四成负荷：它的停止（−4）不到典型台阶的一半，但已经在事件表里，不能再补一遍
    ("有一次运行只带四成负荷", _two_stage_stop(12000, ((1000, 2500), (4000, 5500), (7000, 8500), (10000, 11200)), inrush=_inrush,
                                levels=[10.0, 10.0, 4.0, 10.0], n_slow=0)),
])
def test_sequences_that_already_alternate_are_untouched(name, x):
    ev, info = auto_locate_events(x, 50.0, PRE, POST)
    assert ev == _two_methods(x), name
    assert info["n_refined"] == 0 and info["n_alternation"] == 0 and info["alternation_unresolved"] == [], (name, info)


def test_drift_fragments_raise_no_false_alarm():
    """整条序列缓慢漂移（±0.6，周期 4000 周波）：稳态分段把漂移切成几十个小片段，其中有的终点落在后一次真动作之后。
    这些片段不能被当成「同方向的大动作」而报「缺一次反方向的动作」，更不能补事件。"""
    for seed in (12, 13, 14):
        x = _series(9000, R3, fluct=0.0, seed=seed) + 0.6 * np.sin(2 * np.pi * np.arange(9000) / 4000.0)
        ev, info = auto_locate_events(x, 50.0, PRE, POST)
        assert info["n_alternation"] == 0 and info["alternation_unresolved"] == [], (seed, info)
        assert not any(s == SRC_ALTERNATION for _o, _e, s in ev)
        assert {1000, 2500, 4000, 5500, 7000, 8200} <= {o for o, _e, _s in ev}, seed          # 六次真动作都在，起点准


def test_soft_stop_is_reported_not_invented():
    """软停：电流在 250 个周波里线性降下来。没有突变台阶可补——事件表与旧逻辑相同，只把这三段报出来。"""
    rng = np.random.default_rng(11)
    x = np.full(9000, 1.0)
    for st, sp in R3:
        x[st:sp] += 10.0
        x[sp:sp + 250] += 10.0 * (1.0 - np.arange(250) / 250.0)
    x = x + rng.normal(0, 0.02, 9000)
    ev, info = auto_locate_events(x, 50.0, PRE, POST)
    assert ev == _two_methods(x)
    assert info["n_alternation"] == 0 and len(info["alternation_unresolved"]) == 3
    assert all(0 <= g0 < g1 <= 9000 for g0, g1 in info["alternation_unresolved"])


def test_ramp_stop_after_fluctuating_run_is_not_invented():
    """运行时波动、停止是 30 个周波的斜坡：两种方法都找不到停止；电平确实回到了停机值、幅值也够，但不是突变——
    交替校验只把这三段报出来，不编造事件。"""
    x = _ramp_stop(30)
    ev, info = auto_locate_events(x, 50.0, PRE, POST)
    assert ev == _two_methods(x) and len(ev) == 3                      # 只有三次启动
    assert info["n_alternation"] == 0 and len(info["alternation_unresolved"]) == 3


# ---------------------------------------------------------------- _alternation_check：直接给事件表
def test_alternation_check_rejects_a_small_final_cut():
    """软停降到三成后切断：最后那一下是突变，但只有运行电平的三成——不能把它当成这次停止补进去。
    直接给 ``_alternation_check`` 一份只有三次启动的事件表（不依赖稳态分段碰巧找不找得到那一下）。"""
    found, unresolved = _alternation_check(_ramp_stop(250, to=3.0), STARTS3, PRE, POST)
    assert found == [] and len(unresolved) == 3
    # 对照：同一份事件表，停止是突降 ⇒ 三次都补出来，幅值是整个运行电平
    found, unresolved = _alternation_check(_series(9000, R3), STARTS3, PRE, POST)
    assert unresolved == [] and len(found) == 3
    assert all(abs(o - sp) <= 2 and e - o <= 2 and -12.5 < d < -7.5 for (o, e, d), (_st, sp) in zip(found, R3)), found


def test_alternation_onset_is_located_to_the_cycle():
    """补出来的停止，起点要准到周波。波动的相位按停止时刻对齐，直接给只有三次启动的事件表。"""
    # ① 停止前两个周波正处在波动的下行段（每周波降 2～3，但还在波动范围以内）：起点就是突降的那个周波，不往前多算
    found, unresolved = _alternation_check(_fluct_runs(np.pi + 2 * np.pi * 1.5 / 6.6), STARTS3, PRE, POST)
    assert unresolved == [] and [o for o, _e, _d in found] == [2500, 5500, 8200], found
    assert all(e - o <= 1 for o, e, _d in found), found
    # ② 停止拖了三个周波（还剩 65 %、35 %、0）：起点取第一个半截周波（误差 ≤ 1），不取落稳的那个周波
    for phase in (np.pi / 2 + 2 * np.pi / 6.6, -np.pi / 2 + 2 * np.pi / 6.6):      # 停止前一个周波在波峰 / 在波谷
        found, unresolved = _alternation_check(_fluct_runs(phase, fall=(0.65, 0.35)), STARTS3, PRE, POST)
        assert unresolved == [] and len(found) == 3, (phase, found, unresolved)
        assert all(0 <= o - sp <= 1 for (o, _e, _d), (_st, sp) in zip(found, R3)), (phase, found)


def test_alternation_check_at_the_file_edges_and_ordering():
    starts = [(2500, 2549), (5500, 5549)]
    # 文件开头就在运行：先查两次启动之间、再查文件头尾，返回的事件仍按起点排好
    found, unresolved = _alternation_check(_series(9000, HEAD_RUN), starts, PRE, POST)
    assert unresolved == [] and [o for o, _e, _d in found] == sorted(o for o, _e, _d in found) and len(found) == 3
    assert all(abs(o - k) <= 2 for (o, _e, _d), k in zip(found, (900, 4000, 7000))), found
    # 三次停止都是 30 个周波的斜坡：三段都报出来，也按起点排好（第一段从文件开头起）
    found, unresolved = _alternation_check(_ramp_stop(30, runs=HEAD_RUN), starts, PRE, POST)
    assert found == [] and [g0 for g0, _g1 in unresolved] == [0, 2549, 5549] and [g1 for _g0, g1 in unresolved] == [2500, 5500, 9000]
    # 第一次停止在第 40 个周波：前窗取 50 个周波时放不下 ⇒ 不补，把这一段报出来；前窗取 10 个周波时照补
    x = _series(9000, ((-500, 40), (2500, 4000), (5500, 7000)))
    found, unresolved = _alternation_check(x, starts, 50, POST)
    assert [o for o, _e, _d in found] == [4000, 7000] and unresolved == [(0, 2500)]
    found, unresolved = _alternation_check(x, starts, PRE, POST)
    assert [o for o, _e, _d in found] == [40, 4000, 7000] and unresolved == []
    # 最后一次停止离文件结尾只有 30 个周波：后窗（50 个周波）放不下 ⇒ 不补，把这一段报出来
    x = _series(6000, ((1000, 2500), (4000, 5970)))
    found, unresolved = _alternation_check(x, [(1000, 1049), (4000, 4049)], PRE, POST)
    assert [o for o, _e, _d in found] == [2500] and unresolved == [(4049, 6000)]
    # 空事件表：没有可参照的动作，什么也不做
    assert _alternation_check(x, [], PRE, POST) == ([], [])


def test_alternation_check_reports_what_it_cannot_add():
    # 两次启动之间夹着一次软启动的运行（事件表里没有它的启动）：两次突降的停止补得出来，软启动补不出来 ⇒ 这一段要报出来
    found, unresolved = _alternation_check(_soft_start_in_the_middle(), [STARTS3[0], STARTS3[2]], PRE, POST)
    assert [o for o, _e, _d in found] == [2500, 5500, 8200] and unresolved == [(1049, 7000)]
    # 停机只有 15 个周波就又启动了：两次启动同方向，中间的电平状态没保持住，一次翻转都看不到 ⇒ 也要报出来
    x = _series(6000, ((1000, 2500), (2515, 4000)))
    found, unresolved = _alternation_check(x, [(1000, 1049), (2515, 2564)], PRE, POST)
    assert [o for o, _e, _d in found] == [4000] and unresolved == [(1049, 2515)]


def test_alternation_check_typical_step_and_main_events():
    # 第二次运行的电平是另外两次的 3 倍（事件表里只有三次启动）：典型台阶不能被这一个大台阶带偏，
    # 否则另外两次启动算不上主要动作，它们的停止一个补不出来、一个被当成「幅值不够」
    x = _series(9000, R3, levels=[10.0, 30.0, 10.0])
    found, unresolved = _alternation_check(x, [(1000, 1049), (4000, 4001), (7000, 7049)], PRE, POST)
    assert unresolved == [] and [o for o, _e, _d in found] == [2500, 5500, 8200]
    assert [round(d / 10.0) for _o, _e, d in found] == [-1, -3, -1]
    # 事件表里除了一次启动，还有两个幅值恰好为 0 的事件（停机时电平是量化值、一点不动，双滑窗在那里报的事件 Δ＝0）：
    # 它们不参与定典型台阶，启动仍是唯一的主要动作，它后面漏掉的停止照补
    x = _series(6000, ((2000, 3200),), noise=0.0)
    found, unresolved = _alternation_check(x, [(2000, 2049), (4000, 4001), (4500, 4501)], PRE, POST)
    assert unresolved == [] and [o for o, _e, _d in found] == [3200]
    # 头两个主要动作互相重叠（前一个的终点在后一个的起点之后）：量不出「第一个主要动作之后那一段」的运行电平，文件开头
    # 那一段没有可比的东西 ⇒ 不查（开头的电平在缓慢漂移，查的话漂移会被当成一串动作），也不出错
    x = _steps(4000, [(2000, 5), (2030, 8), (3000, -13)])
    x[:1900] += 0.3 * np.sin(2 * np.pi * np.arange(1900) / 380.0)
    assert _alternation_check(x, [(2000, 2049), (2030, 2079), (3000, 3001)], PRE, POST) == ([], [])


def test_alternation_check_matches_flips_to_located_events():
    # 第三次启动已经在事件表里，只是起点记晚了 2 个周波：翻转落在它前面一点，认得出是同一次动作，不再补一个
    x = _some_big_inrush(TAIL_RUN, (0, 1))
    found, unresolved = _alternation_check(x, [(1000, 1016), (4000, 4018), (7002, 7051)], PRE, POST)
    assert unresolved == [] and [o for o, _e, _d in found] == [2500, 5500]
    # 停止前几个周波里电流几次掉到停机值又回来（接触器抖动）：中值平滑后的翻转比真正停下来的周波早 4 个周波，
    # 精定位要在翻转前后半个平滑窗里找，起点仍是真正停下来的那个周波
    x = _fluct_runs(0.0)
    for _st, sp in R3:
        x[[sp - 8, sp - 6, sp - 4, sp - 2]] = 1.0
    found, unresolved = _alternation_check(x, STARTS3, PRE, POST)
    assert unresolved == [] and [o for o, _e, _d in found] == [2500, 5500, 8200]


def test_state_onset_needs_some_history_to_walk_back():
    """``_state_onset`` 往前回看要先量出翻转前的波动范围；翻转前可用的历史不足 m 个周波时不回看，起点＝落稳的第一个周波。"""
    fall = [7.5, 4.5] + [1.0] * 20                       # 停止拖了两个半截周波
    x = np.array([11.0] * 30 + fall)
    assert _state_onset(x, x < 3.0, 0, 20, 40, -1.0, 5, 0) == (30, 32)          # 历史够：起点回到第一个半截周波
    x = np.array([11.0] * 5 + fall)
    assert _state_onset(x, x < 3.0, 0, 0, 15, -1.0, 5, 0) == (7, 7)             # 落稳前只有 2 个周波可以量波动范围：不回看
    assert _state_onset(x, x < 3.0, 0, 0, 4, -1.0, 5, 0) is None                # 搜索范围里没有落稳的地方


def test_onset_scores_same_as_previous_inline_rule():
    """``_locate_near`` 的打分抽成 ``_onset_scores`` 后逐值相同（sign=0）；sign≠0 只留这个方向的得分。"""
    rng = np.random.default_rng(3)
    x = np.cumsum(rng.normal(0, 1, 400)); m = 5
    old = []
    for k in range(20, 380):
        dev = x[k:k + m] - float(np.median(x[k - 10:k]))
        old.append(float(np.min(np.abs(dev))) if (np.all(dev > 0) or np.all(dev < 0)) else 0.0)
    assert _onset_scores(x, 20, 379, 10, m) == old
    up, dn = _onset_scores(x, 20, 379, 10, m, 1.0), _onset_scores(x, 20, 379, 10, m, -1.0)
    assert [max(a, b) for a, b in zip(up, dn)] == old and all(min(a, b) == 0.0 for a, b in zip(up, dn))
    assert any(v > 0 for v in up) and any(v > 0 for v in dn)


# ---------------------------------------------------------------- 采样波形 → build_profile
FS_W, T0 = 1600.0, 1.79e9
RUNS_S = ((20.0, 50.0), (70.0, 100.0), (115.0, 140.0))       # 150 s 的文件里运行三次（启动秒, 停止秒）


def _mixer_wave(dur_s, runs, *, i_off=0.88, i_run=10.0, inrush=8.0, inrush_s=0.34, m=0.30, f_mod=7.6, mod_tail_s=0.0, soft_stop_s=0.0,
                noise=0.02, seed=1):
    """搅拌机一类设备的 A 相电流采样波形：停机时小而平稳；运行时 50 Hz 电流的幅值按 f_mod（几赫兹）脉动（转矩脉动 ⇒ 间谐波，
    逐周波有效值上下摆几安）；直接启动，冲击 inrush 倍、持续 inrush_s 秒；mod_tail_s>0 时只在每次停止前这么多秒里脉动；
    soft_stop_s>0 时停止不是突降而是线性降下来。"""
    rng = np.random.default_rng(seed)
    n = int(round(FS_W * dur_s)); t = np.arange(n) / FS_W
    amp = np.full(n, i_off); mod = np.zeros(n)
    for a, b in runs:
        sel = (t >= a) & (t < b); tau = t[sel] - a
        amp[sel] = i_run + (inrush - 1.0) * i_run / (1.0 + np.exp(np.clip((tau - inrush_s) / 0.04, -50, 50)))
        if mod_tail_s > 0:
            mod[sel] = m * (tau >= (b - a) - mod_tail_s)
        else:
            mod[sel] = m * np.clip((tau - inrush_s - 0.1) / 0.5, 0.0, 1.0)      # 转速上来之后才开始脉动
        if soft_stop_s > 0:
            dn = (t >= b) & (t < b + soft_stop_s)
            amp[dn] = i_run - (i_run - i_off) * (t[dn] - b) / soft_stop_s
    env = amp * (1.0 + mod * np.cos(2 * np.pi * f_mod * t + rng.uniform(0, 6.28)))
    return T0 + t, np.sqrt(2) * env * np.sin(2 * np.pi * 50.0 * t + 0.3) + rng.normal(0, noise, n)


def _write_csv(path, t, ia):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("时间戳,A相电压,A相电流\n")
        np.savetxt(fh, np.column_stack([t, np.zeros_like(ia), ia]), fmt=["%.6f", "%.1f", "%.5f"], delimiter=",")


def _cfg():
    cfg = AppConfig()
    cfg.sampling.fs, cfg.sampling.f_nom = FS_W, 50.0
    cfg.transform.pt_ratio = cfg.transform.ct_ratio = 1.0
    cfg.harmonic.order_max = 15                                  # 1600 Hz 采样：Nyquist 800 Hz，谐波上限降到 15 次
    cfg.columns.mapping_enabled = True                           # 与用户那次相同：只映射时间列和 A 相电流列
    cfg.columns.mapping = {"timestamp": "1", "ua": "", "ia": "3", "ub": "", "ib": "", "uc": "", "ic": ""}
    cfg.validate()
    return cfg


def _profile(path):
    return build_profile(_cfg(), path, device_id="周期运行设备", labels=None, pre_cycles=PRE, post_cycles=POST,
                         merge_gap_s=10.0, quantity="i", phases="A")


@pytest.fixture(scope="module")
def mixer_csv(tmp_path_factory):
    p = str(tmp_path_factory.mktemp("r212") / "mixer.csv")
    _write_csv(p, *_mixer_wave(150.0, RUNS_S))
    return p


def test_build_profile_auto_finds_every_stop_of_a_fluctuating_load(mixer_csv):
    doc = _profile(mixer_csv)
    assert doc["label_mode"] == "auto" and doc["phases"] == "A"
    st, sp = doc["startup"], doc["shutdown"]
    assert st["n"] == 3 and sp is not None and sp["n"] == 3                  # v0.99.51：启动 3 次、停止 0 次（shutdown 为 None）
    for e, (a, _b) in zip(st["events"], RUNS_S):
        assert abs(e["t_start"] - (T0 + a)) <= 0.041 and e["source"] != SRC_ALTERNATION
    for e, (_a, b) in zip(sp["events"], RUNS_S):
        assert abs(e["t_start"] - (T0 + b)) <= 0.041, e["t_start"] - T0     # 起点误差 ≤ 2 周波
        assert e["source"] == SRC_ALTERNATION
        assert -10.5 < e["vec"]["d_ia"] < -7.5 and e["vec"]["dur_cycles"] <= 3   # 真台阶 −9.1 A（运行 10 A → 停机 0.88 A），突降
    notes = "\n".join(doc["notes"])
    assert "启停交替校验补出 3 个事件（启动 0 个、停止 3 个，source=auto:alternation" in notes
    assert "还有动作没能补出来" not in notes and "起点做了精修" not in notes
    assert "自动定位到 6 个事件" in notes


def test_build_profile_refines_an_onset_recorded_too_early(tmp_path):
    """运行时电流很平，只在每次停止前 1.1 s（55 个周波）里脉动：v0.99.51 把三次停止的起点都记在脉动开始处
    （早 1.1 s，持续 49 个周波）。"""
    p = str(tmp_path / "burst.csv")
    _write_csv(p, *_mixer_wave(150.0, RUNS_S, m=0.15, mod_tail_s=1.1))
    doc = _profile(p)
    sp = doc["shutdown"]
    assert doc["startup"]["n"] == 3 and sp is not None and sp["n"] == 3
    for e, (_a, b) in zip(sp["events"], RUNS_S):
        assert abs(e["t_start"] - (T0 + b)) <= 0.041, e["t_start"] - T0
        assert e["source"] == "auto:steady_state" and e["vec"]["dur_cycles"] <= 3 and -10.5 < e["vec"]["d_ia"] < -7.5
    notes = "\n".join(doc["notes"])
    assert "自动定位：3 个事件的起点做了精修（v0.99.52）" in notes and "最多挪了 55 个周波" in notes
    assert "启停交替校验补出" not in notes and "还有动作没能补出来" not in notes


def test_build_profile_soft_stop_gives_a_hint(tmp_path):
    p = str(tmp_path / "soft.csv")
    _write_csv(p, *_mixer_wave(150.0, RUNS_S, m=0.0, soft_stop_s=5.0))
    doc = _profile(p)
    notes = "\n".join(doc["notes"])
    assert "有 3 段里还有动作没能补出来" in notes and "没有明确的突变台阶" in notes and "建议给启停标签" in notes
    assert "启停交替校验补出" not in notes
    assert not any(e["source"] == SRC_ALTERNATION for g in ("startup", "shutdown") for e in (doc[g] or {}).get("events", []))
