# 模式 B：多设备联合识别本地诊断执行包

## 目标和边界

由用户在原始录波所在 Windows 机器本地执行。先以现有运行配置导出**连续逐周波诊断数据**，供分析 12:51:23 启动过渡、12:51:25 歧义、12:51:45 额外停止及两次真实停止；不改算法、运行配置、画像或已有输出，不重新播放，也不更改 Git 分支。**这是特征提取诊断，不是实时播放端到端复验，也不能单独证明现场识别准确率。**

原始瞬时波形可以留在本机；导出的文件仍含电流时序、时间和可能的设备运行信息，仅在确认可以共享时回传。预估须读取约 714 MB 文件两次计算哈希，另读取一次计算逐周波数据，可能需要数分钟、数百 MB 可用内存；实际耗时取决于机器。请确认磁盘至少有数十 MB 可用空间，不在正在写入的原始文件上操作。可以中止；下次重新执行时必须换新输出目录名。**尚未在用户 Windows 机器试运行**。

## A. 先确认设备和运行真值（不需要运行程序）

请先核对：

1. 播放源 `化工行业-天云龙涂料厂-dev-4号研磨机-1-启停2.csv` 的**第 4 列**实际接的是哪台设备？表头和传感器接线是什么？画像中的 `1号搅拌机` 是否是该通道的正确名称？
2. 气泵画像来源 `化工行业-天云龙涂料厂-dev-1号搅拌机-1-停止1.csv` 的**第 3 列**实际接的是哪台设备？这份画像是否正确标为 `气泵`？仅凭文件名无法作结论。
3. 12:49:42.848～12:52:22.228 内，1 号搅拌机是否仅有用户提供的三次启停？特别是 **12:51:25 和 12:51:45 附近**有没有真实停机、分档、短时负载或其他设备动作？该通道是否包含其他设备？未知可以写「未知」。

## B. 本地导出：PowerShell 完整命令

1. 在 PowerShell 进入**实际运行项目的根目录**，保持包含 `tmp/config_branch.json` 和 `tmp/profile_1号搅拌机_20261114_170805.json` 的现有文件不变。例如（仅在路径确实相同时使用）：

   ```powershell
   cd 'D:\Work\testPython\NILM_Test2026\nilm_calc_tool_261114'
   git branch --show-current
   git rev-parse HEAD
   git status --short
   ```

   预期分支为 `arena/51b63974-nilm-calc-tool`，HEAD 应为包含上次数据提交 `8eefae0` 的版本。若有未提交修改不要覆盖；若代码版本不同，先回报版本与状态，不要强制重置或切换分支。

2. 确认 Python 与 numpy：有项目虚拟环境时优先用它，否则用已安装项目依赖的 `python`。下面命令自动选 `.venv`，并且没有安装依赖、没有拉取代码。然后整段复制到 PowerShell 执行：

   ```powershell
   $ErrorActionPreference = 'Stop'
   $env:PYTHONUTF8 = '1'
   $OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
   $py = if (Test-Path '.\.venv\Scripts\python.exe') { '.\.venv\Scripts\python.exe' } else { 'python' }
   & $py -c "import sys,numpy; print('Python:',sys.executable,'numpy:',numpy.__version__)"
   if ($LASTEXITCODE -ne 0) { throw 'Python or numpy unavailable; stop and report.' }

   @'
import hashlib, json, os, sys
import numpy as np
from elec_tool.config import AppConfig
from elec_tool.nilm_profile import load_cycles, event_features, _single_phase_arrays

cfg_file = os.path.join('tmp', 'config_branch.json')
# Avoid relying on terminal encoding when finding the supplied profile.
profiles = [p for p in os.listdir('tmp') if p.startswith('profile_') and p.endswith('_20261114_170805.json')]
if len(profiles) != 1:
    raise SystemExit('STOP: expected exactly one mixer profile in tmp')
with open(os.path.join('tmp', profiles[0]), encoding='utf-8-sig') as f:
    prof = json.load(f)
cfg = AppConfig.load(cfg_file)
source = os.path.abspath(cfg.source.path)
if not os.path.isfile(source):
    raise SystemExit('STOP: recorded CSV not found on this machine: ' + source)
if float(cfg.sampling.fs) != 10000 or float(cfg.sampling.f_nom) != 50:
    raise SystemExit('STOP: sampling configuration differs from recorded run')
if not cfg.columns.mapping_enabled or str(cfg.columns.mapping.get('timestamp')) != '1' or str(cfg.columns.mapping.get('ia')) != '4':
    raise SystemExit('STOP: timestamp/Ia column mapping differs from recorded run')
if prof.get('single_phase', {}).get('mode') != 'current' or prof.get('single_phase', {}).get('branch_phase') != 'A':
    raise SystemExit('STOP: profile scope differs from recorded run')
expected = prof['source_files'][0]['sha256']
def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()
print('Source:', source, flush=True)
st0 = os.stat(source)
digest = sha(source)
print('Source bytes:', st0.st_size, 'SHA256:', digest, flush=True)
print('Profile training SHA256:', expected, flush=True)
if digest != expected:
    raise SystemExit('STOP: source bytes differ from profile training source; report this instead of exporting')
print('Extracting continuous per-cycle features; please wait...', flush=True)
c, feat, t, p4, q4, i4, ih4, _ = load_cycles(cfg, source, max_cycles=60001, _check_continuity=True)
st1 = os.stat(source)
if (st0.st_size, st0.st_mtime_ns) != (st1.st_size, st1.st_mtime_ns) or sha(source) != digest:
    raise SystemExit('STOP: source changed during reading; no diagnostic saved')
if len(t) != 60000 or abs(float(t[0])-float(prof['t_first'])) > 0.003 or abs(float(t[-1])-float(prof['t_last'])) > 0.003:
    raise SystemExit('STOP: cycle count or first/last timestamp differs from profile; no diagnostic saved')
if not (np.isfinite(t).all() and np.isfinite(i4[1]).all() and np.isfinite(ih4[1]).all() and (np.diff(t) > 0).all()):
    raise SystemExit('STOP: non-finite values or non-increasing timestamps; no diagnostic saved')
print('Cycles:', len(t), 'first epoch:', float(t[0]), 'last epoch:', float(t[-1]), flush=True)
print('Quality:', json.dumps(feat.source_quality, ensure_ascii=True), flush=True)
# Match profile extraction: project actual A-phase to total and A rows.
pp, qq, ii, hh = _single_phase_arrays(p4, q4, i4, ih4, 'A', 'A', True)
for group in ('startup', 'shutdown'):
    for e in prof[group]['events']:
        f = event_features(pp, qq, ii, int(e['onset']), int(e['end']), 10, 50, ih4=hh)
        print('Profile event:', e['t_start_local'], group,
              'Ia current/profile:', round(float(f['vec']['d_ia']), 6), round(float(e['vec']['d_ia']), 6),
              'Ih current/profile:', round(float(f['vec']['d_ih']), 6), round(float(e['vec']['d_ih']), 6), flush=True)
# New directory and exclusive file: never overwrite an earlier result.
outdir = 'diagnostic_joint_20261116_01'
try:
    os.mkdir(outdir)
except FileExistsError:
    raise SystemExit('STOP: output directory already exists; change outdir to a NEW name and rerun')
out = os.path.join(outdir, 'profile_cycles.npz')
with open(out, 'xb') as f:
    np.savez_compressed(f, t=t, ia=i4[1], ih_a=ih4[1])
print('Saved:', os.path.abspath(out), 'bytes:', os.path.getsize(out), 'SHA256:', sha(out), flush=True)
print('DONE: diagnostic only; original CSV and run output not modified.', flush=True)
'@ | & $py -
   if ($LASTEXITCODE -ne 0) { Write-Host 'Diagnostic stopped. Please report the STOP/error text; do not overwrite existing data.' }
   ```

   If the recorded CSV has been moved, the command will stop rather than guess a path. Report its location; do not edit the original configuration snapshot. If the source hash differs, report both hashes; do not treat it as the same training file. If extraction is interrupted after creating the new directory, leave that partial directory in place and use a different `outdir` on the next run.

### Expected output — example, not an actual run

- `Source bytes: ... SHA256: ...` followed by the same value for `Profile training SHA256`.
- `Cycles: 60000`; epoch first / last approximately `1608784937.0882` / `1608786137.0682`.
- Three `Profile event` rows. The current and profile ΔIa / ΔIh numbers should be close when data, processing and extraction geometry agree; discrepancies are evidence to investigate, not a pass/fail decision based on an arbitrary tolerance.
- `Saved: ...\diagnostic_joint_20261116_01\profile_cycles.npz ... SHA256: ...`, then `DONE`.

The continuity check only detects obvious timestamp jumps and is not a complete missing-sample audit. A successful export is not proof of exact reproduction of the online processing sequence; matching first / last times alone is not proof either. The recorded source SHA-256 comparison checks against the **training** file, not an independently recorded runtime source hash.

## C. 回传与后续判断

请回传：

1. 第 A 节的两列设备 / 接线核对和三个特殊时刻的现场真值，无法确认写「未知」。
2. `git branch --show-current`、`git rev-parse HEAD`，以及上面诊断命令的完整输出或完整报错；注意路径可能包含敏感信息，可在保留文件名和路径对应关系的情况下脱敏。
3. 若同意共享设备数据，提交或上传新生成的 `diagnostic_joint_20261116_01/profile_cycles.npz`，并给出输出的 SHA-256。**不要覆盖现有 `tmp/` 输出**；如需提交到当前远程分支，可将该文件作为新增文件放入 `tmp/`，但不要删除或替换现有文件。也可以直接上传此文件。若不愿共享，可先回传文本结果，再讨论在本机输出有限时间窗口的替代方案。

收到后将只读校验哈希、长度、时标与画像特征；再检查三次真值及 12:51:25 / 12:51:45 前后逐周波电平、持续性、谐波和候选窗口，并对照诊断 CSV。必要时可在隔离环境用这些逐周波数据做**明确标记为近似离线**的候选 / 状态分析；这不等同于原始 CSV 以现场实际数据块和实时播放端到端重放。最终修复方案和阈值须覆盖独立设备、短运行、分档及并发事件，不能只调到本例通过。

**更正上次分析的口径提醒**：`tmp/realtime/current_20261116.csv` 是 1 秒监测输出，监测 Ia 使用去直流交流 RMS；画像逐周波 Ia 使用含直流 RMS。两者不应直接进行数值等同或用监测电平推断画像 ΔIa；之前引用 1 秒数值只能作为粗略趋势线索，不能作为停机或瞬态形态的定论。

**更正（已收到用户回传后）**：初版命令打印对比时把未投影的三相平均谐波行传入 `event_features`，而画像先将 A 相投影到总行，故当时打印的 ΔIh 恰为画像的三分之一。导出的 `ih_a` 是 A 相数据，本次回传文件无需重导；上述命令已修正比较口径。
