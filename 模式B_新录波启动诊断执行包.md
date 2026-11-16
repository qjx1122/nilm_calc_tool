# 模式 B：新录波启动诊断执行包

## 对象和初步结论

本执行包专用于用户提供的 2020-12-24 新录波、上传提交 `57bd72a` 的 `tmp` 运行快照和既有两设备集合。用户确认第 1 列时间、第 4 列 1 号搅拌机电流，10000 Hz / 50 Hz，全文件只有 12:00:25～12:00:27 附近一次真实启动。源文件 SHA-256 为 `8b23e5b35c7496d01b781654fe6bfbb198093a41df8bd3fb8fadcd17c6254333`，不同于旧画像训练源。不同不代表错误，旧脚本本来就是针对旧训练源的，不能直接删除旧哈希限制继续用。

用户运行 `run_id=1794810344531`，分路配置和用户描述一致，使用旧搅拌机与气泵集合的快照 SHA-256 `0d2ee61abc4bcf770e47b5e0f594d1f2790191e44a9381e06fc650339ff95870`。画像算法输出三条 unknown（12:00:25.506、12:00:26.105、12:00:27.065），没有确认搅拌机启动。第一条候选中搅拌机 START 为 rejected，带 `trajectory_deviates`，confidence 0.1150、ΔIa 8.7211 A、14 周波；这些只是候选的当前窗口结果，不等于真实完整启动幅度或已证明的根因。另有 47 行来自其他六个独立算法，不是 47 个设备画像确认事件。1 秒交流监测值从启动前约 0.21 A 上升至 67.47 A，后降到约 7 A，提示可能存在较长启动过渡，但其去直流口径和逐周波画像口径不同，不能直接等同比较。

新文件 SHA 不同于旧训练源，支持这不是完全相同的字节文件；但仅靠哈希不同不能证明工况完全独立。`run_info` 未记录播放文件内容哈希或运行进程代码 SHA，用户提供的 SHA / HEAD 是本地事后记录，不是运行时独立证明。真值是用户提供的范围，暂不能确定精确启动时刻。

## Windows 本地提取

1. 先检查 Git 状态，在不覆盖本地修改的前提下拉取当前分支的修订版（`c15ed4f` 上的脚本是旧版），将项目根目录的 `diagnose_new_mixer_start.py` 复制为 `diagnose_new_mixer_start_fixed.py`；或从本会话下载修订版并另存为该名称。若目标文件已存在，先保留，换一个新名字并同步修改下面两处命令。不要覆盖 `run_diagnose.ps1`、旧结果或源 CSV。
2. 在原来的 `test_gpu` PowerShell 中，从项目根目录依次执行：

```powershell
cd 'D:\Work\testPython\NILM_Test2026\nilm_calc_tool_261114'
git branch --show-current
git rev-parse HEAD
git status --short
python -c "import sys,numpy; print('Python:', sys.executable, 'numpy:', numpy.__version__)"
if ($LASTEXITCODE -ne 0) { throw 'Python or numpy unavailable; stop' }
$expected = '72343f252fc2adbf3e58ff1651258325479bf2992c41b2be5404a57088cf6d2d'
$actual = & python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read().replace(b'\r\n',b'\n')).hexdigest())" '.\diagnose_new_mixer_start_fixed.py'
if ($LASTEXITCODE -ne 0) { throw 'Cannot read script; stop' }
Write-Host "Script LF-normalized SHA256: $actual"
if ($actual -ne $expected) {
    Write-Host 'Script mismatch; STOP. Do not execute it; report the hash.'
} else {
    & python .\diagnose_new_mixer_start_fixed.py
    if ($LASTEXITCODE -ne 0) { Write-Host 'Diagnostic stopped; report the full output and error.' }
}
```

脚本对新录波核对原始字节哈希；对仓库中的 `tmp/config_branch.json` 和集合文本快照，仅将 CRLF 归一为 LF 后与仓库基准哈希比较，并分别打印原始和归一化哈希；不会修改文件。归一化一致不能证明当前工作区文件原始字节与运行时加载的字节一致。脚本还核对事件 CSV 的 run_id 与时间，然后从源文件起始读取逐周波 Ia / A 相谐波，核验源文件读取前后无变化、周波时间递增以及覆盖目标时段。它不会把训练画像的事件索引用到新文件；它最多读取 100001 周波，达到上限即停止，不将截短数据当作完整数据保存。粗略连续性检查不能代替完整的缺失样本审计，非零质量计数应报告。请不要在源 CSV 正被写入时运行；需足够内存和磁盘空间，可能需数分钟。沙盒缺少该 CSV，本脚本尚未在用户 Windows 上执行，可能需要依据实录调整。

成功时新建 `diagnostic_joint_new_mixer_01/cycles_new_mixer.npz` 并显示 SHA-256。若目录已存在或一次中断留下目录，先保留它，在脚本中仅将 `OUTDIR` 改为一个未使用的目录名再运行；改后脚本哈希会变，原哈希检查不再适用，须明确说明。不要覆盖任何文件。该 NPZ 含逐周波电流时序、时标与少量来源元数据，可能包含设备运行信息；仅在同意共享时回传。也可先只回传完整终端输出 / STOP 信息及脚本版本。

导出是离线特征提取，不是在线端到端重放或状态轨迹。回传 NPZ 后再分析启动完整过渡和候选窗口；未经独立验证不得修改阈值来强行匹配，也不能用于自动控制或保护。
