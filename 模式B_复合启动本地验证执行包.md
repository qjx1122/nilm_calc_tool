# 模式 B：复合启动待决本地验证执行包

## 先读：本版的明确范围

此版只为集合联合归因的固定档位、单相纯电流强冲击 START 增加保守的待决观测：待起点后 4 秒的波形范围可核验，记录较早基线和后续电平；即便检测到稳定上升，也只输出带候选证据的 `unknown`，不确认搅拌机、不推进设备状态。它**并未实现本例启动的确定归因**；不能用于自动控制或保护。4 秒是波形证据范围，不是实际输出延迟上限，已有联合候选等待、块处理与调度也会增加延迟。详细说明、短运行 / 邻近并发、尾部和数据不足限制见指南 H.38。

从当前分支获取本次修订；不要切换分支、重置工作区或覆盖历史运行输出。

## 1. 核对代码和回归

在 Windows 原来的 `test_gpu` PowerShell 中：

```powershell
cd 'D:\Work\testPython\NILM_Test2026\nilm_calc_tool_261114'
git branch --show-current
git status --short
git rev-parse HEAD
python -c "import sys,numpy; print('Python:', sys.executable, 'numpy:', numpy.__version__)"
```

预期分支 `arena/51b63974-nilm-calc-tool`。若尚未取得本次修订，请先报告 `git status --short`；有未提交修改时不要强制更新。确认工作区改动安全后，用 `git fetch origin arena/51b63974-nilm-calc-tool` 和 `git merge --ff-only FETCH_HEAD` 获取当前分支最新版本。合并失败请保留现状并报告，不要 reset。记录新 HEAD；确保 `tests/test_joint_composite_start.py` 和 `tests/test_joint_composite_start_tail.py` 均存在。

为避开此前 Tavern 插件兼容问题，仅在当前命令范围临时禁用自动加载，结束后恢复原值：

```powershell
$oldPytestAutoload = $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD
try {
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
    python -m pytest -q tests/test_joint_composite_start.py tests/test_joint_composite_start_tail.py tests/test_joint_stop_recovery.py tests/test_joint_profile_detection.py tests/test_profile_truncated_template.py tests/test_r226_single_phase_scope.py
    $testExit = $LASTEXITCODE
} finally {
    if ($null -eq $oldPytestAutoload) { Remove-Item Env:PYTEST_DISABLE_PLUGIN_AUTOLOAD -ErrorAction SilentlyContinue }
    else { $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = $oldPytestAutoload }
}
if ($testExit -ne 0) { throw "Regression failed; report output. Exit: $testExit" }
```

请回传分支、HEAD、状态和完整测试输出；不要只回传最后一行。沙盒 Linux 独立定向测试通过不等同于 Windows 环境通过。

## 2. 用户本地原始 CSV 播放

1. 在播放前保留上一次运行的输出和已有 `tmp/`，配置新的运行输出位置或备份到全新目录；不覆盖源 CSV、画像、已有事件 CSV / NPZ。记录本次输出保存目录。
2. 重启软件，确认加载的确为新代码、现有同一个两设备联合画像集合，以及新源 `…1号搅拌机-1-启动1.csv`。确认采样 10000 Hz / 50 Hz、第 1 列时间、第 4 列 A 相搅拌机电流及当前配置；播放整份文件。用户真值是 2020-12-24 12:00:25～12:00:27 左右唯一启动。
3. 回传新运行 `run_info.json`、`config_branch.json`、`nilm_events_*.csv`、`nilm_profile_candidates_*.csv` 和控制台 / 界面的错误提示（有则完整保留）；放在全新 `tmp/` 子目录或直接上传，不覆盖以前的文件。若可以，记录启动事件首次显示的墙钟时间、播放速度及是否完整播放至文件尾。若能获得逐时设备状态，连同输出回传；否则不能把代码推断当成状态实测。
4. 核对该时段 `profile` 事件是否为 `unknown`，是否含 `composite_start_settled_unattributed` 或其他复合启动标记、`candidate_devices` 中原候选状态和 `composite_metrics`；后续负向观测不应误当作真实停止。原始候选 CSV 可能先保存初次拒绝，不能把它当作最终未知事件的完整证据。观测数、时间、标记和状态均需根据实录核对，**不要预设结果必然一致**。
5. 另须覆盖数据尾部、短运行和真实相邻 / 并发动作的独立录波；单次样本、合成回归、原始 CSV 播放均不单独等于现场准确率或保护逻辑验收。
