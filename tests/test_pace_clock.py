"""v0.15.1 节拍钟：绝对限速 + 两侧互锁（不死锁、先播完一侧不拖累另一侧）。"""
import threading
import time

from elec_tool.pace import PaceClock


def test_absolute_pace_and_sync():
    clk = PaceClock(10.0)                      # 10 倍速：1 s 数据 = 0.1 s 墙钟
    out = {}

    def side(name, t0, n, blk):
        clk.anchor(name, t0)
        t = t0
        for _ in range(n):
            clk.wait_until(name, t + blk, t_block_start=t)
            clk.advance(name, t + blk)
            t += blk
        out[name] = time.monotonic()
        clk.finish(name)

    w0 = time.monotonic()
    a = threading.Thread(target=side, args=("bus", 100.0, 20, 0.1))     # 2 s 数据，块 0.1 s（fs 6400）
    b = threading.Thread(target=side, args=("branch", 500.0, 10, 0.2))  # 2 s 数据，块 0.2 s（fs 3200）
    a.start(); b.start(); a.join(5); b.join(5)
    assert not a.is_alive() and not b.is_alive(), "互锁死锁"
    assert abs((out["bus"] - w0) - 0.2) < 0.08 and abs((out["branch"] - w0) - 0.2) < 0.08
    assert abs(out["bus"] - out["branch"]) < 0.05


def test_first_block_never_blocked_and_finished_side_releases_peer():
    clk = PaceClock(0.0)                       # 不限速：只剩互锁
    clk.anchor("bus", 0.0); clk.anchor("branch", 0.0)
    assert not clk._blocked_by_peer("bus", 0.0) and not clk._blocked_by_peer("branch", 0.0)
    assert clk.wait_until("bus", 0.3146, t_block_start=0.0) == 0      # 第一块很大也放行
    clk.advance("bus", 0.3146)
    assert clk._blocked_by_peer("bus", 0.3146)                         # 第二块：领先分路 > 容差 → 等
    clk.finish("branch")
    assert not clk._blocked_by_peer("bus", 0.3146)                     # 分路播完 → 不再等


def test_pause_resume_shifts_schedule():
    clk = PaceClock(1.0)
    clk.anchor("bus", 0.0)
    clk.pause(); time.sleep(0.15); clk.resume()
    assert clk.target_wall("bus", 0.0) - clk.wall0 >= 0.14
    assert clk.info()["paused_total_s"] >= 0.14
