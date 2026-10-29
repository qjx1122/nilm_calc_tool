# REPORT_TEST.md — 专题报告台账（nilm_calc_tool）

> 台账文件（BOOTSTRAP.md v2.2）：**只追加、按专题分节、不新建文件**。所有「用户专题 / 实验专题 / 验证专题」报告统一沉淀于此。
> 纪律（ROLE.md v1.2/v1.3）：每条专题必须含**用户执行命令（含实录路径）+ 输出 + 判读**三件套；模式 B 下**未获用户真实回报前不得下结论**；结论区分「已复现」与「经验推测」。
> 状态标注：✅已确认（有实录）｜🔶待确认（等回报）｜❌已废弃（不删行，只翻状态）

## 条目模板（追加专题时复制此块，勿改本模板）

```markdown
## [YYYY-MM-DD] 专题：<专题名>
- 类型：用户专题 / 实验专题 / 验证专题
- 目标与假设：
- 方法 / 数据 / 参数：
- 用户执行命令（含实录路径；本节无用户命令则注明）：
- 结果 / 结论：
- 是否进入 REPORT.md（稳定结论）：是 / 否
- 遗留问题：
```

## 专题索引

| 编号 | 日期 | 专题名 | 类型 | 执行模式 | 状态 | 是否升格 REPORT.md |
| --- | --- | --- | --- | --- | --- | --- |
| T-001 | 2026-10-10 | 环境与数据基线核对（台账回填前置采集） | 验证专题 | B（用户本地执行） | 🔶待用户回报 | 待定 |
| T-002 | 2026-10-10 | 电气量计算工具实现自验证 + 本地部署与真实数据验收执行包 | 验证专题 | 混合（沙盒 A 已实录 / 用户侧 B 待回报） | 🔶待用户回报（沙盒侧已✅实录） | 部分已升格 |
| T-003 | 2026-10-10 | 四种数据源的配置·运行·验证（csv_file/csv_tail/tcp/simulator × CLI/Web/库） | 验证专题 | 混合（沙盒 A 已实录 / 用户侧 S·D 组待回报） | 🔶待用户回报（沙盒侧已✅实录，含 F-01~F-10 修复） | 是（四源等价性等 5 条） |
| T-004 | 2026-10-12 | 第 6 轮四功能：用户时标格式 / 24h 曲线 / 逐曲线保存开关 / 自定义播放时间 | 用户专题（实现＋验证） | 混合（沙盒 A 已实录 / 用户侧 U6 组待回报） | 🔶待用户回报（沙盒侧已✅实录） | 是（C-14：按数据时间保留＋峰谷抽稀；C-15：无日期时标处理规则） |
| T-005 | 2026-10-12 | 第 7 轮三功能：曲线实时落盘 / 离线播放起点 / 曲线悬停取值 | 用户专题（实现＋验证） | 混合（沙盒 A 已实录 / 用户侧 U7 组待回报） | 🔶待用户回报（沙盒侧已✅实录） | 是（C-16：实时落盘与曲线/保存共用提取规则＋按数据日期分文件；C-17：播放起点四种定位的代价与语义） |
| T-006 | 2026-10-12 | 第 8 轮：数据处理子界面——离线波形 CSV 重采样（文件名 原名_re_fs） | 用户专题（实现＋验证） | 混合（沙盒 A 已实录 / 用户侧 U8 组待回报） | 🔶待用户回报（沙盒侧已✅实录） | 是（C-18：重采样时间轴按等间隔重建＋按源写法重生成时标；fft 周期语义） |
| T-007 | 2026-10-13 | 第 9 轮：间谐波 / 直流偏置 电气量子界面 + 事件子界面（6 类事件） | 用户专题（实现＋验证） | 混合（沙盒 A 已实录 / 用户侧 U9 组待回报） | 🔶待用户回报（沙盒侧已✅实录） | 是（C-19：间谐波 IEC 分组口径与分辨率前提；C-20：事件状态机的滞回/热改阈值/数据时间/折算规则） |

---

## [2026-10-10] 专题 T-001：环境与数据基线核对（台账回填前置采集）

- **类型**：验证专题
- **执行模式**：模式 B（用户 2026-10-10 显式指定）——Agent 只产出执行包，**只基于用户回报的真实结果继续**
- **目标与假设**：
  - 目标：为 `README.md`（安装/运行/数据目录/配置/产物）、`NILM_DATA_DICT.md`（8 章节字段与口径）采集真实依据，把 🔶待确认 条目逐条翻 ✅ 或 ❌
  - 假设：本仓库为空壳（仅协议文件），真实代码与数据在用户本地或另一仓库；若不成立（代码其实在本仓库某处），B 组命令会直接暴露
- **方法 / 数据 / 参数**：只读命令采集，不改文件、不装依赖、不跑训练；分 4 组（A 环境工具链 / B 代码仓库现场 / C 数据现场 / D KPI 口径问答）

### 用户执行命令（含实录路径）

> 🔶 **实录路径：待用户回报**（必填项——BOOTSTRAP v2.2 修复「命令持久化链条三层皆断」的关键字段）
> 建议实录文件名：`nilm_baseline_20261010.log`（PowerShell 用 `Start-Transcript` 落盘，bash 用 `script` 或 `tee` 落盘）

**E-0 环境说明**
- 在**你本地的项目环境**执行（Windows PowerShell 或 Linux/macOS bash 均可，下面每组给两种写法）
- 全部为**只读命令**：不修改文件、不安装依赖、不启动训练；预计总耗时 **< 3 分钟**
- 输出可整段贴回对话；同时请**保存日志并回报绝对路径**（该路径会写入本专题，保证档案可复现）
- 若某命令不存在/报错，**照实贴报错**即可，不要跳过（报错本身就是判读依据）

**实录落盘（先执行这一条，最后执行 Stop）**
```powershell
# PowerShell
Start-Transcript -Path "$HOME\nilm_baseline_20261010.log"
# … 执行 A/B/C 组命令 …
Stop-Transcript
```
```bash
# bash（方式一：script 全程录制）
script -q "$HOME/nilm_baseline_20261010.log"
# … 执行 A/B/C 组命令 … 然后 exit 结束录制
# bash（方式二：当前 shell 重定向）
exec > >(tee "$HOME/nilm_baseline_20261010.log") 2>&1
```

**A 组｜环境与工具链**
```powershell
# A1 Python 与位置
python -V; where.exe python
# A2 Conda 环境（若用 conda）
conda env list
# A3 关键依赖版本
pip list | Select-String -Pattern "torch|pandas|numpy|scikit-learn|xgboost|lightgbm|matplotlib"
# A4 GPU 可用性
nvidia-smi
python -c "import torch;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),torch.cuda.device_count())"
# A5 机器资源（核数 / 内存）
Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors
Get-CimInstance Win32_OperatingSystem | Select-Object @{n='FreeGB';e={[math]::Round($_.FreePhysicalMemory/1MB,1)}},@{n='TotalGB';e={[math]::Round($_.TotalVisibleMemorySize/1MB,1)}}
# A6 版本控制工具
git --version; gh auth status
```
```bash
# A1
python -V; which -a python
# A2
conda env list
# A3
pip list | grep -Ei 'torch|pandas|numpy|scikit-learn|xgboost|lightgbm|matplotlib'
# A4
nvidia-smi
python -c "import torch;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),torch.cuda.device_count())"
# A5
nproc; free -g; df -h .
# A6
git --version; gh auth status
```

**B 组｜代码与仓库现场**（在**真实代码所在目录**执行；若代码不在本仓库，请一并回答 B5）
```powershell
# B1 git 现场
git log -5 --oneline; git status --short --branch; git branch -a
# B2 已入库文件清单
git ls-files
# B3 Python 入口盘点
Get-ChildItem -Recurse -Depth 3 -Filter *.py | Select-Object -First 50 FullName
# B4 依赖声明文件是否存在
Get-ChildItem -Name requirements*.txt,environment.yml,pyproject.toml,setup.py,setup.sh -ErrorAction SilentlyContinue
# B5 双标定环境变量在代码中的引用
Get-ChildItem -Recurse -Filter *.py | Select-String -Pattern "NILM_DUAL_SCALER" | Select-Object -First 20
```
```bash
# B1
git log -5 --oneline; git status --short --branch; git branch -a
# B2
git ls-files
# B3
find . -maxdepth 3 -name "*.py" -not -path "./.git/*" | head -50
# B4
ls -1 requirements*.txt environment.yml pyproject.toml setup.py setup.sh 2>/dev/null
# B5
grep -rn "NILM_DUAL_SCALER" --include=*.py . | head -20
```
- **B6（文字回答）**：NILM 计算工具的代码现在在哪？（本机绝对路径 / 另一个 GitHub 仓库地址+分支 / 尚未编写只有需求）

**C 组｜数据现场**（把 `<DATA_ROOT>` 换成真实数据根目录）
```powershell
# C1 目录树（2 层，最多 60 行）
Get-ChildItem <DATA_ROOT> -Recurse -Depth 2 | Select-Object -First 60 FullName
# C2 样本文件表头与前 3 行（换成真实文件名）
Get-Content <DATA_ROOT>\<样本文件>.csv -TotalCount 3
# C3 文件数与体量
(Get-ChildItem <DATA_ROOT> -Recurse -Filter *.csv).Count
"{0:N2} GB" -f ((Get-ChildItem <DATA_ROOT> -Recurse | Measure-Object Length -Sum).Sum/1GB)
# C4 双标定环境变量当前取值
"NILM_DUAL_SCALER=$env:NILM_DUAL_SCALER"
# C5 数据是否被 git 忽略
Get-Content .gitignore -ErrorAction SilentlyContinue
```
```bash
# C1
find <DATA_ROOT> -maxdepth 2 | head -60
# C2
head -3 <DATA_ROOT>/<样本文件>.csv
# C3
find <DATA_ROOT> -name "*.csv" | wc -l; du -sh <DATA_ROOT>
# C4
echo "NILM_DUAL_SCALER=$NILM_DUAL_SCALER"
# C5
cat .gitignore 2>/dev/null; git check-ignore -v <DATA_ROOT> 2>/dev/null
```
- **C6（文字回答）**：数据是否涉密/是否允许入库？若不允许，外部存储位置与访问方式是什么？

**D 组｜KPI 口径问答（纯文字回答，无需命令）**
| 编号 | 问题 | 你的回答 |
| --- | --- | --- |
| D1 | 主验收指标（MAE / RMSE / R²）与合格阈值 | |
| D2 | 统计粒度（终端 / 用户 / 两者） | |
| D3 | 功率类型与单位（有功 W？kW？含 Q/S？） | |
| D4 | 采样间隔与滑窗长度、步长 | |
| D5 | 数据划分方式（按时间/用户/终端）与随机种子 | |
| D6 | 是否剔除零负荷段与缺测段 | |
| D7 | `NILM_DUAL_SCALER` 双标定的确切含义（两级分别标定什么） | |

### 预期输出样例（⚠️ 示例格式，**非实录**，仅用于对照）

```
A1  Python 3.10.13
A3  numpy 1.26.4 / pandas 2.2.1 / torch 2.2.2 / scikit-learn 1.4.1.post1 / xgboost 2.0.3
A4  NVIDIA-SMI 550.xx  Driver Version: 550.xx  CUDA Version: 12.4  |  torch 2.2.2 cuda True 1
A5  NumberOfCores 8 / NumberOfLogicalProcessors 16 / FreeGB 12.3 / TotalGB 32.0
B2  README.md  src/preprocess.py  src/train_tcn.py  requirements.txt
C2  ts,user_id,P,Q,U,I
    2026-03-01 00:00:00,U1001,312.4,58.1,228.6,1.42
C4  NILM_DUAL_SCALER=device_user
```

### 判读要点（回报后 Agent 按此对账，🔶全部待实录激活）

| 编号 | 观察 | 判读与后续动作 |
| --- | --- | --- |
| J-A4 | `cuda True` 且核数 ≥8、内存 ≥16GB | 训练类任务**可考虑模式 A**（仍需预估单命令耗时，>30min 则回 B） |
| J-A4' | 无 GPU，或 ≤2 核 / ≤3GB 内存 | **维持模式 B**（对齐 ROLE.md v1.3 沙盒实证：2 核 transformer 单训 23min、内存 3GB） |
| J-A3 | `pip list` 缺 torch/pandas 等 | 环境未就绪 → 先补 `README.md` 第 2 节安装命令，再谈实验 |
| J-B4 | 无 `requirements.txt` 等声明文件 | 需由 A3 反推生成依赖清单（列为下一任务）；README 第 2 节保持 🔶 |
| J-B6 | 代码在另一仓库/本机 | 决定是否迁入本仓库或改为「引用外部路径」；影响任务边界 |
| J-C2 | 表头为中文/乱码 | 编码非 UTF-8（疑 GBK）→ `NILM_DATA_DICT.md` 第 4 节编码字段需明确，否则批量合并会踩坑 |
| J-C3 | 体量 >1GB 或 C6 答涉密 | 数据**不入库** → `.gitignore` 排除 + README 第 4 节登记外部路径 |
| J-C4 | `NILM_DUAL_SCALER` 为空且 B5 无引用 | 说明该机制尚未在本项目实现（仅存在于 ROLE.md 背景描述）→ 数据字典 P-03 行翻 ❌ 或标「未实现」 |
| J-D1~D7 | 用户给出明确口径 | 回填 `NILM_DATA_DICT.md` 第 3/6/8 节与 `REPORT.md` 3.2，并翻 ✅（注明来源＝用户确认 + 日期） |

> ⚠️ **J-\* 阈值性质声明**：表中「≥8 核 / ≥16GB / >1GB / >30min」等数值为**经验判据**，非本项目实测；来源为 `ROLE.md` v1.3 沙盒实证（2 核 / 3GB 内存 / transformer 单训 23min / torch 源受阻）外推，属「经验推测」档。用户回报 A5/C3 实际值后按实测对账，必要时修订阈值并记入变更记录。

### 结果回收格式（请按此贴回，便于逐条落盘）

```
实录路径：<绝对路径，必填>
执行环境：<Windows PowerShell / bash>，执行日期：<YYYY-MM-DD>

| 编号 | 实际执行命令 | 输出（关键片段，可截断） | 你的备注 |
| --- | --- | --- | --- |
| A1 |  |  |  |
| A3 |  |  |  |
| … |  |  |  |

文字回答：
B6 代码位置：
C6 数据是否入库：
D1~D7：
```

- **结果 / 结论**：🔶**待用户回报**（模式 B 纪律：未获实录前不下任何结论；本节将在收到回报后填「命令+输出+判读」三件套，并逐条对账 J-* 判读项）
- **是否进入 REPORT.md（稳定结论）**：待定 —— 仅当 D 组口径确认后，KPI 口径部分升格至 `REPORT.md` 3.2；环境/数据事实回填 `README.md` 与 `NILM_DATA_DICT.md`（不属稳定结论，不进 REPORT.md）
- **遗留问题**：
  1. `TUNING_GUIDE.md` 未创建（无稳定方法论可对账，见 `STATUS.md` 决策记录）
  2. 代码与数据归属未定（B6/C6 未回报），故无法评估是否需要迁入本仓库、是否需要 `.gitignore`
  3. 依赖声明文件缺失，`README.md` 第 2 节安装命令无法给出
  4. 本 session 沙盒侧仅完成**文件级验证**（存在/非空/结构/无编造事实），未做任何运行时验证——已在 `README.md` 第 9 节明示

---

## [2026-10-10] 专题 T-002：电气量计算工具实现自验证 + 本地部署与真实数据验收执行包

- **类型**：验证专题（含实现记录）
- **执行模式**：**混合**——① 沙盒侧（模式 A）写码 + 合成信号解析解自验证 + live preview 实跑，**已有实录**；② 用户侧（模式 B）真实数据/Windows 部署/生产常驻，**只产出执行包，未获实录前不下结论**。（用户本轮跳过澄清提问，按 STATUS.md 决策记录采用混合模式）
- **目标与假设**：
  - 目标：交付「电力系统各类电气量计算工具」，满足 6 条验收标准（总体工具 / 各量分子界面 / 导航条切换 / 实时+离线两种输入 / 七类电气量含 2–50 次谐波与频谱 / 各量分别配置时间段），并给出用户本地可复现的部署与验收路径
  - 假设：用户环境为 Windows + 真实采集 CSV（6400 Hz、7 列、PT=100、CT=15）；UI 形态选 Web（沙盒可当场验收），Qt 桌面壳延后；谐波口径取额定 50 Hz 整周期矩形窗 FFT + 可选自适应估频，IEC 61000-4-7 分组延后
- **方法 / 数据 / 参数**：合成信号（`elec_tool/selftest.py:build_signal`，解析解 `expected_values()`）+ 沙盒实跑（模拟器实时源、`gen-sample` 生成的 5 s/32000 行 CSV）；工况 fs=6400 Hz、f=50 Hz、PT=100、CT=15、窗长 1 s（谐波/基波 0.2 s）

### 沙盒侧实录（三件套：命令 + 输出 + 判读）✅

| # | 命令（沙盒实录，Linux 6.1.158+ / CPython 3.11.2 / numpy 2.4.6） | 输出关键片段 | 判读 |
| --- | --- | --- | --- |
| A1 | `./.venv/bin/python cli.py selftest` | `自检项 44 个：通过 44，失败 0，通过率 100.0%，最差相对误差 1.508e-05，耗时 0.32s` | 七类量计算口径与解析解一致；worst 1.5e-5 来自 S7 非额定频率工况，额定工况中位误差 1.1e-15（浮点级） |
| A2 | `./.venv/bin/python -m pytest tests/ -q` | `141 passed, 1 skipped in 54.95s` | 唯一 skip＝`tests/test_cli.py:43`（60 Hz 下 50 次=3000 Hz 逼近 Nyquist 3200 Hz，另行测试）；142 项覆盖解析/调度/CLI/Web 四层 |
| A3 | `cli.py compute --file data/sample_6400hz.csv --format table --every 5` | `✓ 完成：输出 26 次；读入样本 32000（5.00s 数据），块 25，缓冲 10880/10880`；`各量输出次数：{'fundamental': 26, 'harmonic': 26, 'voltage': 6, …, 'spectrum': 6}` | 需求⑥成立：同一份数据里 0.2 s 窗出 26 次、1 s 窗出 6 次，各量独立调度 |
| A4 | `cli.py compute --file … --set-window voltage=5` | `缓冲 32000/49280`；`'voltage': 2` | 改窗长即时生效且缓冲自动扩容（容量公式 `ceil(最长窗×fs×1.5)+max(块,64)`） |
| A5 | `cli.py sources --file data/sample_6400hz.csv` | `编码：utf-8-sig`；`列映射：{'timestamp':0,'ua':1,'ia':2,'ub':3,'ib':4,'uc':5,'ic':6}`；`时间戳模式：s 推算采样率：6399.9943 Hz` | 用户给定列格式被正确识别；时间戳反推 fs 与配置偏差 0.0001% |
| A6 | `cli.py serve --host 127.0.0.1 --port 8001 --pt 100 --ct 15 --set-window voltage=2` + `curl /api/state` | `serve 生效配置: PT=100.0 CT=15.0 fs=6400.0 | voltage 窗=2.0s | source=simulator`；`running: False` | CLI 覆盖参数确实传到 Web 会话；未设 `ELEC_TOOL_AUTOSTART` 时不自动跑引擎（需界面点启动） |
| A7 | Web 实时链路（`ELEC_TOOL_AUTOSTART=1`，模拟器 `sim_speed=1`） | `速率 6398–6400 点/s`；`emits {'fundamental': 258, 'harmonic': 258, 'voltage': 51, …}`；`voltage 请求1.0s → 实际1.0s 6400点/50周期 f_used=49.999992 泄漏=False` | 实时摄入达额定速率；窗长口径**精确**等于请求值；WebSocket 推送为「分量子集」，前端 `mergeResult()` 按键合并 |
| A8 | 离线安装（内网场景）：`pip download -r requirements.txt -d wheels` → 新 venv `pip install --no-index --find-links wheels -r requirements.txt` | Linux：29 包/28 MB，装完 `selftest 44/44`、`pytest 140 passed`（当时值） | 完全无网可部署；Windows 目标须显式列包（见 A9） |
| A9 | `pip download --platform win_amd64 --python-version 3.11 --implementation cp --abi cp311 --only-binary=:all: numpy fastapi uvicorn websockets pytest httpx -d wheels_win` | 24 包/18 MB，含 `numpy-2.4.6-cp311-cp311-win_amd64.whl` | ✅下载侧通过；⚠️ 用 `-r requirements.txt` 跨平台下载会 `ResolutionImpossible`（`uvicorn[standard]`→uvloop 无 Windows wheel），已在 requirements.txt 用 PEP 508 平台标记分流 + README §2.4(c) 给出显式列包命令 |
| A10 | `ast.parse(feature_version=(3,9)/(3,10))` 扫描 31 个 `.py` | `3.9/3.10 语法不兼容项：无`；且无 `match`/`itertools.pairwise`/`KW_ONLY`/`tomllib` 等 3.10+ 专属用法 | 语法层面兼容 3.9+；**运行时未逐版实测**（🔶） |

**本轮修复的两个真 bug（均由新增测试暴露，已加回归测试锁死）**

| # | 现象（实测） | 根因 | 修法与回归测试 |
| --- | --- | --- | --- |
| B1 | 32000 行的 CSV 跑出 `samples_in=32640`；等满 1.2 s 数据却只算出 6272 点 | `EngineRunner.start()` **持锁** join 旧线程，旧线程正卡在「写结果要拿同一把锁」→ 互等到 2 s 超时后旧线程存活；旧线程每轮重读 `self.engine`，于是继续轮询**被替换的新引擎** → 同批数据双重摄入 | 锁外 join + 每轮全新 `threading.Event` + 线程只持有本轮私有 `engine/stop_event` + 每轮自检「被取代即退场」；回归：`tests/test_server.py::test_offline_window_length_changes_output_count`（断言 `samples_in == 文件行数`） |
| B2 | 用户配 **1 s** 窗，实际只算 **0.98 s / 49 周期**，频谱分辨率变 1.0204 Hz，并持续打印「整周期截断」告警 | `plan_window` 用**绝对**容差 `floor(cyc_req + 1e-9)` 判整周期；估频 `f_used=49.999987`（相对误差 2.6e-7）时 `cyc_req=49.999987` 直接掉到 49 周期 | 改相对容差 `max(1e-9, 1e-5·|cyc_req|)`；真·非整数周期（49.85 Hz→49 周期）行为不变；回归：`tests/test_analysis.py::test_plan_window_estimated_freq_near_integer_keeps_all_cycles` |

> 附带修正：未知导出格式返回 400（原静默走 JSON 分支）；重启引擎清空历史（一次运行＝一个数据集）；界面配置写 `configs/runtime.json`，出厂模板 `configs/default.json` 不再被污染；自检报告如实显示运行环境（Python/OS/numpy）；csv_tail 的 `tail_from_end`/`watch_dir_newest` 补上 CLI 开关与界面勾选框（此前只能改配置文件）。

### 用户执行命令（模式 B 执行包，🔶待回报）

> 回收要求：每条命令贴**原样输出**（可截断到关键行）；不确定的写「不确定」，**不要猜**。Windows 命令均在仓库根目录、激活 venv 后执行（`.venv\Scripts\activate`）。

**W 组：Windows 本地部署（对应 README §2）**

```powershell
# W1 环境与取码
py -3.11 -V
git clone -b arena/82e34fb8-nilm-calc-tool https://github.com/qjx1122/nilm_calc_tool.git
cd nilm_calc_tool

# W2 建环境装依赖（联网）
py -3.11 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip list | findstr /I "numpy fastapi uvicorn websockets pytest httpx"

# W3 三层验证（期望：44/44 通过；141 passed, 1 skipped）
.venv\Scripts\python cli.py selftest
.venv\Scripts\python -m pytest tests/ -q

# W4 起 Web 界面并打开浏览器
.venv\Scripts\python cli.py serve
#   → 浏览器访问 http://127.0.0.1:8000 ；「数据源与控制」→ 模拟器 → 启动数据源
#   → 局域网另一台机器访问 http://<本机IP>:8000（若不通，请贴防火墙放行前后的现象）

# W5（内网机才需要）离线安装：把联网机上 wheels_win\ 拷来后
.venv\Scripts\pip install --no-index --find-links .\wheels_win numpy fastapi uvicorn websockets pytest httpx
```

判读要点：**J-W1** `selftest` 必须 44/44（若非全绿，贴出失败项的 `id/expected/actual/rel_err`）；**J-W2** `pytest` 若出现 `test_server.py` 全 skip，说明缺 httpx；**J-W3** 界面若显示「推送断开 → 已降级为轮询」，说明 WebSocket 被拦（功能仍可用，实时性 1.5 s）；**J-W4** 中文若乱码，贴出 `cli.py sources --file <你的csv>` 的编码行。

**R 组：真实数据对账（对应 README §4，核心验收）**

```powershell
# R1 数据体检（只看，不算）
.venv\Scripts\python cli.py sources --file data\<你的真实数据>.csv

# R2 离线批算并导出
.venv\Scripts\python cli.py compute --file data\<你的真实数据>.csv --format csv --out output\对账.csv

# R3 按业务窗长重算（例：电压有效值 5 s，谐波 0.2 s）
.venv\Scripts\python cli.py compute --file data\<你的真实数据>.csv --set-window voltage=5 --set-window harmonic=0.2 --format table --every 5

# R4 实时链路（采集器边写边算）
.venv\Scripts\python cli.py live --source csv_tail --path data\<采集器正在写的文件>.csv
#   只算启动后的新数据：加 --from-end ；路径给目录跟最新文件：加 --watch-newest

# R5 二次值对账（排除变比因素，与现场表计直接比数）
.venv\Scripts\python cli.py compute --file data\<你的真实数据>.csv --no-scale --format table --every 5
```

判读要点：**J-R1** R1 输出里「列映射」必须覆盖 timestamp/ua/ia/ub/ib/uc/ic 七项，「推算采样率」应≈6400（偏差 >1% 请贴出，可能是时间戳精度不足）；**J-R2** R2/R5 的 U、I、P、PF、THD 与现场表计或既有系统对比，请填下表并注明比对对象与时段；**J-R3** 若出现「缺测/NaN 已线性插值」且带「>5%」字样，该段数据不可用于验收；**J-R4** 若电压是**线电压**而非相电压，需把 `transform.voltage_input` 改为 `line` 后重算（这条目前是 🔶待确认）。

| 量 | 本工具输出 | 对比对象（表计/系统）读数 | 相对偏差 | 备注 |
| --- | --- | --- | --- | --- |
| U（A/B/C） |  |  |  |  |
| I（A/B/C） |  |  |  |  |
| P / Q / PF |  |  |  |  |
| THD_U / THD_I |  |  |  |  |

**P 组：生产常驻（对应 README §9，可选）**

```powershell
# P1 后台常驻（二选一）
#   方式A：任务计划程序 → 开机触发 → 操作填 .venv\Scripts\python.exe cli.py serve，起始于填仓库目录
#   方式B：NSSM 注册为 Windows 服务（nssm install ElecTool）
# P2 自启动即跑引擎：在服务的环境变量里加 ELEC_TOOL_AUTOSTART=1
# P3 日志留存：把 stdout/stderr 重定向到 logs\serve.log（任务计划/NSSM 均可配）
```

判读要点：**J-P1** 重启机器后服务是否自动恢复；**J-P2** 长时间运行（>1 h）内存是否稳定（环形缓冲与历史都是定长队列，理论上不涨；若涨请贴任务管理器数值与运行时长）。

### 结果回收格式（复制到回报里即可）

```
W1~W5：命令 + 原样输出（关键行）
R1~R5：命令 + 原样输出（关键行）+ 对账表
P1~P3：做法 + 现象
文字回答：
 1) 你的采集 CSV 实际编码 / 时间戳格式（epoch 秒？ISO？毫秒？）：
 2) 电压列是相电压还是线电压：
 3) PT/CT 实际值是否与 100/15 一致：
 4) 实时数据落地方式（采集器写文件？TCP？协议文档能否提供）：
 5) 部署形态（单机浏览器 / 局域网多人 / 需要常驻服务）：
 6) 是否需要 Qt 桌面壳（当前为 Web 版）：
```

- **结果 / 结论**：
  - 沙盒侧 ✅**已复现**：6 条验收标准全部有代码与测试对应（README §1 对照表）；算法口径与解析解一致（44/44）；实时与离线两条链路实跑通过；内网离线安装路径实测可用
  - 用户侧 🔶**待回报**：Windows 部署、真实数据对账、生产常驻三组尚无实录，**不下结论**
- **是否进入 REPORT.md（稳定结论）**：**部分已升格** —— 电气量计算口径（整周期矩形窗 FFT、相量/THD/序分量/功率定义、变比与一次二次口径、窗调度与降级规则）属稳定方法论，已写入 `REPORT.md`；本地部署事实属环境事实，回填 `README.md` §2/§3/§4 与 `NILM_DATA_DICT.md`，不进 REPORT.md
- **遗留问题**：
  1. IEC 61000-4-7 谐波分组（10/15 分钟评估、分组平方和）未实现——当前为整周期矩形窗口径，若验收方要求 IEC 口径需另立专题
  2. TCP 实时源帧格式（字节序/字段顺序/缩放/帧头尾）未取得，`source.frame/struct_fmt` 为可配置占位 🔶
  3. Qt 桌面壳延后（本轮决策 Web 优先，理由见 `STATUS.md`）
  4. 用户/权限、历史入库（数据库）、报警推送未实现，当前为单机工具形态
  5. T-001 的 B6/C6/D1~D7 仍未回报；本轮用户已实质回答其中的 fs=6400 Hz、CSV 列格式、PT=100/CT=15（来源：用户 2026-10-10 需求描述），已在 `NILM_DATA_DICT.md` 翻 ✅
  6. `TUNING_GUIDE.md` 仍未创建（窗长/口径选择的调参教学可在此沉淀，待用户真实数据回报后再写才有依据）

---

## [2026-10-10] 专题 T-003：四种数据源的配置 · 运行 · 验证（csv_file / csv_tail / tcp / simulator）

- **类型**：验证专题（含实现记录与缺陷修复）
- **执行模式**：**混合**——① 沙盒侧（模式 A）四种源 × 三条入口（CLI / Web+REST / Python 库）全部实跑取证，**已有实录**；② 用户侧（模式 B）真实采集装置与真实 TCP 协议，**只产出执行包，未获实录前不下结论**。
- **目标与假设**：
  - 目标：把验收④「输入支持实时采集与离线文件」拆成 4 种源，逐源交付「完整配置字段（含默认值与约束）＋ 三种运行方式 ＋ **真实验证测试**」，并让用户在**没有采集硬件**的条件下也能自行复现全部验证。
  - 假设：用户实时落地＝采集器写 CSV（✅已确认，见 `NILM_DATA_DICT.md` v0.2）或 TCP 推送（协议未定 🔶）；列格式 `时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流`、fs=6400 Hz、PT=100、CT=15。
- **方法 / 数据 / 参数**：
  - **采集侧扮演工具（本轮新增，`tools/`）**：`tcp_feeder.py`（TCP 服务端，`text_csv`/`binary` 两种帧，可指定 `--struct-fmt`）、`csv_appender.py`（按用户列格式持续追加写文件，可 `--rotate-every` 分片轮转）。两者与内置 `simulator` **共用同一信号模型**，因此四源结果可互相对账，也可与 `cli.py selftest` 的解析解对账。
  - 信号模型：二次侧 U1=100/√3 V、I1=5 A、φ=30°、谐波 3/5/7/11/13 次＝8%/6%/3%/1.5%/1%、噪声 0.2%、不平衡 2%、fs=6400 Hz、f=50 Hz。
  - **解析解**（一次侧，PT=100/CT=15）：U1=5773.503 V、I1=75.0 A、P₁=3·U1·I1·cos30°=**1125.000 kW**、THDu=**10.595%**。
  - 判定容差（写在 `tools/verify_sources.py::judge`）：U1 用**三相均值**对账（合成信号含 2% 不平衡，单相值本就偏离）容差 5‱；P 对 P₁ 容差 0.5%（谐波功率应使其略高）；THDu 容差 0.05 百分点；**出现数据缺口直接 FAIL**。
  - 环境：Linux 6.1.158+ / CPython 3.11.2 / numpy 2.4.6 / 2 核 3 GB，2026-10-10。Web/REST 用例跑在**第二个实例**（端口 8002，`ELEC_TOOL_AUTOSTART=0 ELEC_TOOL_PERSIST_CONFIG=0`），不动 8000 的预览实例、不污染入库配置。

### 沙盒侧实录（三件套：命令 + 输出 + 判读）✅

| # | 命令（沙盒实录） | 输出关键片段 | 判读 |
| --- | --- | --- | --- |
| S1 | `python tools/verify_sources.py` | `✓ 结果：PASS 5 / SKIP 0 / FAIL 0（共 5 例）` | 五种配置（4 源，tcp 含文本/二进制两帧）在**库层**全部通过解析解对账；工具会自动拉起喂数器/追加器并在结束时清理 |
| S2 | 同上 → `csv_file` 例 | `[PASS] U1均=5773.60V 偏差 0.17‱；P=1140.644kW；THDu 偏差 0.003 百分点`；`U(A/B/C)=[5805.9,5805.9,5806.0]V I1=[75.005,74.999,74.998]A PF=0.8637 不平衡=0.0016% 缺口 0`；`窗长(实际s,周期数)：{'voltage': (1.0, 50), 'harmonic': (0.2, 10)}` | 离线链路正确；样例文件由 `gen-sample`（三相平衡、谐波电流相角 40°）生成，故 P 比实时源高 1.1%＝**数据差异不是算法误差**；窗长「请求＝实际」（1s→50 周期、0.2s→10 周期） |
| S3 | `cli.py live --source csv_tail --path data/tail_live.csv --from-end --duration 6` | `✓ 结束：输出 78 次，样本 100480，数据时长 15.70s，实时速率 16749 样本/s`；`U=5805.9/5921.8/5689.5V P=1127.76kW Q=660.31kvar THDu=10.60%`；`· tail_from_end=True：只读打开之后的新增内容`；`· 源：采样率校验通过：时间戳推算 6399.998Hz ≈ 配置 6400.0Hz（偏差 0.0000%）` | 追加读取正常；4 倍速下 16749 样本/s（≈4×6400×0.7 有效摄入）；追加器时间戳写 `%.6f`（µs 级）仍能推出 fs 偏差 0.0000% ⇒ 最长连续段线性拟合生效 |
| S4 | `cli.py live --source csv_tail --path data/tail_dir --watch-newest --duration 10`（追加器 `--rotate-every 20`） | 修复前：`⚠ 检测到 8 处数据时间跳变`，示例 `gap_s=0.10015606880187988, missing_samples=639.9988`，时刻间隔恰 2.000s；修复后：`✓ 结束：输出 125 次，样本 160640，数据时长 25.10s`、**无缺口告警**、`· 源：目录中出现更新的文件，切换监视对象：part_092.csv（旧文件补读 640 行）`；期间产生 93 个分片 | 目录分片模式可用；修复前每次切换丢**正好一整块**（640 点＝100.2ms），形成与轮转周期同频的假缺口；修复后缺口 0 且告警自证补读行数（见 F-01） |
| S5 | `cli.py live --source tcp --host 127.0.0.1 --port 9000 --duration 6`（喂数器 `--mode text_csv --header`） | `✓ 结束：输出 42 次，样本 54400，数据时长 8.50s，实时速率 18134 样本/s`；`U=5805.8/5921.7/5689.5V P=1127.72kW Q=660.38kvar f=50.000Hz THDu=10.60%`；喂数器日志：`识别到表头 → 映射 {'timestamp':0,'ua':1,'ia':2,'ub':3,'ib':4,'uc':5,'ic':6}`、3 次客户端连接、`BrokenPipeError`/`ConnectionResetError` 后继续服务 | 文本帧链路正确；中文表头自动识别；客户端断开不影响服务端（可反复启停引擎） |
| S6 | `cli.py live --source tcp --port 9001 --frame binary --struct-fmt ">7f" --duration 6`（喂数器同格式，28 字节/帧） | `✓ 结束：输出 3 次，样本 60800，数据时长 9.50s，实时速率 10201 样本/s`；`U=5805.9/5922.0/5689.6V P=1127.80kW Q=660.30kvar THDu=10.60%` | 大端 float32 二进制帧数值与文本帧一致 ⇒ **字节序/类型可配且解析无损**（但时标量化见 F-04） |
| S7 | Web/REST 五例：`POST /api/engine/start`（8002 实例）＋`GET /api/state`＋`GET /api/result`；`GET /api/probe?path=data/sample_6400hz.csv` | probe：`{"ok":true,"encoding":"utf-8-sig","header":[7 列中文],"fs_est":6399.99,"ts_mode":"s"}`；csv_file `U=[5805.8,5805.7,5805.7] P=1140.63kW PF=0.8637 THDu=10.589% 缺口0`；csv_tail `U=[5806.3,5922.1,5690.1] P=1127.87kW 不平衡=3.997% 缺口0`；tcp text `P=1127.81kW THDu=10.607%`；tcp binary `<7d` `U=[5805.7,5922.2,5689.6] P=1127.74kW THDu=10.596% 缺口0`；simulator `P=1127.73kW THDu=10.594% 缺口0` | **Web 入口与 CLI/库入口数值一致**（同源四路 P 极差 0.013%）；`/api/probe` 能在启动前把编码/表头/fs 判对，是现场排错第一站 |
| S8 | 帧格式不匹配：喂数器 `>7f`，客户端用默认 `<7d` | 修复前：`✗ 执行失败：OverflowError: timestamp out of range for platform time_t`；修复后：不再崩，收尾打印一条去重后的源告警 `时间戳解析失败（时间戳换算后不合理（模式=s，最大绝对值 1.37806e+308 秒…）。排查：① TCP 二进制帧请核对 source.struct_fmt（字节序/类型…）与 struct_fields 字段顺序…② CSV 请核对 columns 列映射与 timestamp_unit…③ 若协议用 float32 存 epoch 秒…），改用 fs 合成时间轴` | 坏帧格式从「崩在显示层」变成「可诊断降级」：电气量仍按样本序＋配置 fs 计算，时间轴退回合成并显式告警（F-02、F-03） |
| S9 | 帧格式匹配但用 float32 存 epoch（`>7f`） | `· 源：时间戳整块无递增（全部相同）：时标精度远粗于采样间隔，或用 float32 存 epoch 秒导致量化（float32 在 1.7e9 秒处步长约 128s）。电气量仍按样本序与配置 fs 计算，但时间轴与缺口检测不可信；建议协议改用 double 或整数毫秒时标`；同期显示时刻比真实早约 2 分钟 | 精度陷阱被显式暴露，不会静默产出错误时间轴（F-04）；协议侧应改用 double 或整数毫秒 |
| S10 | 端口未监听：`cli.py live --source tcp --port 9001`（喂数器已退出） | `✗ 执行失败：ParseError: TCP 连接失败 127.0.0.1:9001 —— [Errno 111] Connection refused。排查：① 采集服务是否已启动并监听该端口 ② 防火墙/网段 ③ 配置 source.host/port 是否正确` | 连接失败给出可操作排查清单，不是裸 socket 异常 |
| S11 | `python -m pytest tests/ -q` | `147 passed, 1 skipped in 59.35s`（唯一 skip＝`tests/test_cli.py:43`，60Hz×50 次逼近 Nyquist） | 全量回归通过；本轮新增 6 项（1 项 csv_tail 丢块回归 + 5 项工具防腐） |
| S12 | `python cli.py selftest` | `44/44`，`worst_rel_err=1.508e-05` | 算法层解析解自证未受本轮改动影响 |
| S13 | `python tools/verify_sources.py --kinds tcp_text --external-feeders --tcp-port-text 9999` | `[SKIP] tcp_text　没有可连的喂数器；先跑 python tools/tcp_feeder.py --port <端口> 或去掉 --external-feeders 让本工具自动拉起`，退出码 0 | 无采集侧时是 SKIP＋提示（退出码 0），参数错误 2、验证失败 1 ⇒ 可编入脚本/CI |
| S14 | `JSDOM_DIR=/tmp/uitest node tools/ui_dropdown_check.cjs http://127.0.0.1:8000`（jsdom 加载**真实** `index.html`+`app.js`，打**真实**服务端；脚本自动在 9000 端口拉起 TCP 喂数器） | `=== 结果：PASS 74 / FAIL 0 ===`；`#src-kind` 4 项逐个：`✓ 可选中`＋`✓ 无关字段已联动禁用`＋`✓ 载荷只含该源相关字段`＋`✓ 载荷无空值/0 覆盖服务端配置`＋`✓ 服务端确实以该源运行`；载荷实录 csv_tail `{"kind":"csv_tail","path":"data/sample_6400hz.csv","tail_from_end":false,"watch_dir_newest":false,"block_samples":640}`、tcp `{"kind":"tcp","host":"127.0.0.1","port":9000,"frame":"text_csv","block_samples":640}`、simulator `{"kind":"simulator","sim_speed":4,"block_samples":640}`；服务端状态 csv_file `running=false finished=true samples_in=32000`，csv_tail/tcp/simulator `running=true samples_in=32000/39040/44800` | **「数据源输入方式」4 种输入方式都能正常选中并分别配置**，且服务端真的按所选 kind 摄入（csv_file 是离线源，读满即 finished 属预期）；载荷不再夹带无关字段/空值 |
| S15 | 同上 → A2/A3 段 | `✓ frame=text_csv 时 struct 两项禁用`、`✓ 选 binary 后 struct 格式/字段顺序放开`、binary 载荷含 `"frame":"binary","struct_fmt":">7f","struct_fields":"t,ua,ia,ub,ib,uc,ic"`、切回 text_csv 后载荷**不含** struct 两项；脏值保护：经真实 WS `onmessage` 推入一条 `config.source.kind='simulator'` 的 state 后 `✓ #src-kind 仍是用户选的 csv_tail`、`✓ 正在输入的路径未被清空`（`data/我正在输入的一半路径`）、`✓ 给出「已暂停自动回填」的明确提示`；点「刷新」后 `✓ 丢弃修改并重新回填`（`formDirty=false`，kind 回到服务端值 tcp） | 「帧格式」下拉框与 binary 专属字段联动正确；F-09（推送覆盖用户输入）已消除，且「刷新」语义明确＝丢弃未保存修改 |
| S16 | 同上 → B 段（口径三下拉框，逐个值点「保存配置（热更新）」）＋修复前 `/tmp/uitest/probe.cjs` 实录 | 修复前：全新加载 3 s 后 `cfg-pt/cfg-ct/cfg-fs/cfg-fnom/cfg-hmax/src-path/src-host` **全为空**；只改 `cfg-uin=line` 点保存 → `PUT /api/config` **HTTP 400**，body 含 `fs:0, pt_ratio:0, order_max:0`，报「sampling.fs 必须 > 0（当前 0）」，服务端仍 `phase/6400/100`。修复后：`cfg-uin` line/phase、`cfg-apparent` vector/arithmetic、`cfg-reactive` quadrature/harmonic_sum **6 组全部** `✓ PUT 已发出且未被 400 拒（HTTP 200）`＋`✓ 服务端配置已生效（回显一致）`＋`✓ 载荷不含 0 值` | F-08 已消除：空数字框不再被当 0 送出；口径下拉框选中即生效并可被 `GET /api/config` 复核 |
| S17 | 空值语义 REST 实录：`PUT /api/config {"source":{"path":""}}`；`PUT {"source":{"host":""}}`；`POST /api/engine/start {"kind":"csv_file"}`（不带 path） | ① `HTTP 400 {"ok":false,"error":"source.kind=csv_file 需要 source.path（文件或目录路径）"}`；② `HTTP 200`（空 host **被存下**）；③ `HTTP 200 ok=true`，服务端沿用已存路径，2 s 后 `/api/state`：`running=false finished=true samples_in=32000`，源告警「采样率校验通过：时间戳推算 6399.962Hz ≈ 配置 6400Hz」 | 语义确证：**载荷里省略某键＝沿用服务端已存值**（深合并），而**送空串**要么被 400 拒（path）要么被静默存空（host）⇒ 前端必须按「非空才送」裁剪，这正是 F-07 的修法依据 |
| S18 | `pytest tests/test_web_ui.py -q`；把 `app/static/app.js` 换回修复前版本再跑同一命令；`pytest tests/ -q` | 修复后 `14 passed in 0.05s`；换回旧版 `7 failed, 7 passed`（失败项＝两个下拉框 change 监听、脏值保护与联动函数、载荷裁剪、空值跳过、启动不夹带配置、SRC_HINT 覆盖 4 源）；还原后 `14 passed`；全量 `161 passed, 1 skipped in 59.28s` | 前端契约测试**撤销修复必 FAIL** 已验证（不是空跑绿）；全量回归 147→161 通过 |

### 四源横向对账（同一信号模型，三条入口）

| 源 / 入口 | U(A/B/C) V | U1均偏差 | P kW | Q kvar | PF | THDu % | 缺口 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `csv_file`（库） | 5805.9 / 5805.9 / 5806.0 | 0.17‱ | 1140.644 | 662.658 | 0.8637 | 10.589 | 0 |
| `csv_tail`（CLI `--from-end`） | 5805.9 / 5921.8 / 5689.5 | — | 1127.76 | 660.31 | — | 10.60 | 0 |
| `csv_tail`（Web/REST） | 5806.3 / 5922.1 / 5690.1 | — | 1127.87 | 660.32 | 0.8584 | 10.580 | 0 |
| `csv_tail`（库） | — | 0.70‱ | 1127.747 | 660.362 | 0.8584 | 10.589 | 0 |
| `tcp text_csv`（CLI） | 5805.8 / 5921.7 / 5689.5 | — | 1127.72 | 660.38 | — | 10.60 | 0 |
| `tcp text_csv`（Web/REST） | 5806.2 / 5921.7 / 5689.8 | — | 1127.81 | 660.30 | 0.8584 | 10.607 | 0 |
| `tcp binary >7f`（CLI） | 5805.9 / 5922.0 / 5689.6 | — | 1127.80 | 660.30 | — | 10.60 | 0 |
| `tcp binary <7d`（Web/REST） | 5805.7 / 5922.2 / 5689.6 | — | 1127.74 | 660.38 | 0.8584 | 10.596 | 0 |
| `tcp binary <7d`（库） | — | 0.42‱ | 1127.751 | 660.384 | 0.8584 | 10.593 | 0 |
| `simulator`（Web/REST） | 5805.6 / 5922.4 / 5689.5 | — | 1127.73 | 660.38 | 0.8584 | 10.594 | 0 |
| `simulator`（库） | — | 0.42‱ | 1127.727 | 660.376 | 0.8584 | 10.593 | 0 |
| **解析解** | U1=5773.503 V | 0 | **P₁=1125.000** | — | cos30°=0.8660 | **10.595** | — |

**判读**：四种实时源在三条入口下 P 落在 1127.727～1127.87 kW（极差 **0.013%**）、U1 偏差 ≤0.70‱、THDu 偏差 ≤0.005 百分点、缺口全 0 ⇒ **源类型与入口都不影响算法结果**；P 比 P₁ 高 0.24%＝谐波功率贡献（预期）。`csv_file` 的 P 高 1.1% 属数据实现差异（平衡＋谐波电流相角 40°），其 U1/THDu 仍吻合解析解。

### 本轮修复的缺陷（全部由实测发现，均已加回归测试或实录）

| 编号（F＝本轮修复；与 T-001 的 B 组命令编号、REPORT.md 的 C-0x 结论编号各自独立） | 现象（实测） | 根因 | 修法 | 回归证据 | 状态 |
| --- | --- | --- | --- | --- | --- |
| F-01 | `csv_tail` 目录模式每切换分片丢 640 点（100.2ms），8s 内 8 处「疑似丢点」假缺口，间隔恰 2.000s | `_rotate_if_needed()` 检测到更新文件就直接 `_reopen()`，旧分片在上次轮询后新写入的数据未读走即被关闭 | 切换前 `_drain_current()` 补读旧文件（inode 变化分支同样处理；截断分支不 drain，因数据已被覆盖），告警写明「旧文件补读 N 行」 | `tests/test_sources.py::test_csv_tail_dir_switch_drains_old_file`；撤销修复则断言 `1280 != 1920` 失败；实录 S4 修复后缺口 0 | ✅已修 |
| F-02 | 帧格式不匹配时 CLI 崩 `OverflowError: timestamp out of range for platform time_t` | 坏时标一路传到显示层 `time.localtime`；`np.isfinite` 挡不住「超大但有限」的值 | ① `parse_timestamps` 加合理性闸门（非有限或 max\|t\|>1e11 秒 → 可诊断 `ParseError`，文案指向 struct_fmt/struct_fields/列映射/timestamp_unit/float32 精度）② `cli.py::_fmt_clock()` 兜住 OverflowError/OSError/ValueError ③ 源捕获后退回 fs 合成时间轴 | 实录 S8（修复前/后对比） | ✅已修 |
| F-03 | 实时源告警刷屏：3s 内 8 条只差小数位的「采样率校验通过」、6 条几乎相同的解析告警，关键信息被淹没；且 `cli.py live` 收尾**完全不打印**源告警 | 同类告警每块重发且文本含变化数值/模式名，按原文去重无效；live 收尾只打引擎状态 | `sources/base.py::note_key()` 按中文骨架（去数字与 ASCII）去重，tcp/csv_tail 共用；`cli.py::_print_diagnostics()` 让 compute/live 收尾统一打印「缺口 + 引擎告警 + 源告警」并截断 170 字 | 实录 S8/S9（同一问题只剩 1 条）、S3/S4（源告警可见） | ✅已修 |
| F-04 | float32 存 epoch 秒 → 时标量化步长 ~128s，显示时刻比真实早约 2 分钟，却无任何告警 | 协议侧精度问题，解析层未检测「整块无递增/存在回退」 | `_flag_degenerate_clock()`：整块无递增或出现回退时显式告警，并说明电气量仍按样本序＋配置 fs 计算、时间轴与缺口检测不可信 | 实录 S9 | ✅已修 |
| F-05 | `app/static/app.js::collectSourcePayload` 存在死代码：`return` 在前、后续「删空值」语句引用未定义的 `payload` | 上一轮 patch 时把 `return {…}` 直接后接新逻辑 | 改为 `const payload = {…}` → 删空值 → `return payload` | `node --check` 通过 ＋ 另做「`return` 之后残留语句数＝0」静态检查（**教训：`node --check` 只验语法不验逻辑**） | ✅已修 |
| F-06 | 「数据源输入方式」与「帧格式」两个下拉框**选了界面毫无变化**：4 种源的字段全部平铺常驻、都能编辑，填了不生效也不提示；无逐源填写说明 | `app.js::bind()` 只给频谱 3 个下拉框注册了 change，`#src-kind`/`#src-frame` **没有任何监听**；`renderSource()` 只做回填不做联动 | 新增 `syncSourceForm()`：按 kind/frame 决定 10 个字段的 `disabled`，并写 `#src-hint` 逐源说明（`SRC_HINT` 单一事实来源）；两个下拉框注册 change；`style.css` 加 `label.off{opacity:.45}` 与 `:disabled{cursor:not-allowed}` 让置灰可见 | S14（4×「无关字段已联动禁用」全 ✓）、S15（binary 才放开 struct 两项）、`tests/test_web_ui.py::test_source_selects_have_change_listener`（换回旧 app.js 即 FAIL） | ✅已修 |
| F-07 | 启动/保存载荷**无条件发送全部字段**：选 simulator 仍带 `path/host/port/frame`，TCP 切回 `text_csv` 仍带旧 `struct_fmt`；空 `path` 被服务端 400 拒，空 `host` 被静默存成 `''`（下次连不上且看不出原因） | `collectSourcePayload()` 是「全字段平铺」写法，上一轮只为 struct 两项做了删空 | 改为**按 kind 裁剪**＋「非空/有效才送」：`if (path) p.path = path`、`if (host) p.host = host`、`struct_*` 仅在 `frame==='binary'` 时送、`sim_speed/block_samples/port` 走 `Number.isFinite` 闸门 | S14（4×「载荷只含该源相关字段」「载荷无空值/0」）、S17（空值语义 REST 实录）、`test_source_payload_omits_irrelevant_and_empty_fields` | ✅已修 |
| F-08 | **全新加载页面直接点「保存配置（热更新）」必失败**：`PUT /api/config` 400「sampling.fs 必须 > 0（当前 0）」，服务端配置不变，界面只提示「保存失败」，用户不知道是哪个框的问题 | 空输入框经 `+$('#cfg-fs').value` 变成 `0` 一并送出；`PUT` 是深合并，`0` 会真的覆盖 fs/PT/CT/order_max。根因是 `renderSource()` 只在源视图打开时回填（见 F-09 的另一面），未进过该页时表单停在 HTML 默认（空） | `collectConfigPayload()` 改为返回 `{payload, skipped}`：只送**有限且 >0** 的数字，`order_max` 再 `Math.round` 且 ≥2；被跳过的字段名写进成功提示（「PT 变比、采样率 fs 为空 → 保留服务端原值」），不静默 | S16（6 组口径 PUT 全 200 且回显生效、载荷无 0 值）、`test_config_payload_skips_empty_numbers` | ✅已修 |
| F-09 | 停在「数据源与控制」页且引擎在跑时，**刚选的下拉框每 0.2 s 被改回服务端的 kind、输入一半的路径被清空**（本轮最隐蔽缺陷） | 快量推送 → `connectWS()` 收到 `result`/`state` 即 `render()` → `renderSource()` **无条件**把服务端配置写回表单 | 拆出 `fillSourceForm(cfg)`；`renderSource()` 仅在 `!S.formDirty` 时回填，否则显示 `#src-formnote`「⚠ 界面有未保存的修改…」；`#view-source` 全部 input/select 绑 `input`+`change` 置脏；「刷新」＝清脏并重新回填，保存/启动成功后也清脏 | S15（经真实 WS `onmessage` 推送后 kind 与半截路径均不变、提示出现、刷新后恢复）、`test_form_has_dirty_guard_and_sync` | ✅已修 |
| F-10 | 改完 PT/CT 或功率口径后点「启动数据源」，用户以为生效，实际**被服务端静默忽略** | `startEngine()` 把 `collectConfigPayload()` 一起 POST，而 `/api/engine/start` 只取 source 白名单键＋`windows`，`transform/sampling/harmonic/power` 被丢弃 | 启动载荷只送 source（＋可选 windows）；若口径类字段有未保存修改，成功提示追加「（提示：口径/变比的修改请点「保存配置（热更新）」）」 | S14/S16（口径生效路径＝PUT，服务端回显一致）、`test_start_engine_does_not_smuggle_ignored_config` | ✅已修 |

### 能力补齐（本轮新增，均由实测驱动）

- `cli.py live` 增加 `--frame {text_csv,binary}` / `--struct-fmt` / `--struct-fields`：此前二进制帧格式只能改配置文件，现场无法快速试帧。
- Web「数据源与控制」TCP 面板增加 `struct_fmt` / `struct_fields` 两个输入框；`POST /api/engine/start` 的 source 覆盖白名单同步加这两键（否则界面填了也不生效）。
- `tools/tcp_feeder.py`、`tools/csv_appender.py`、`tools/verify_sources.py` ＋ `tests/test_tools.py`（5 项防腐测试）：**没有采集硬件也能完整验证四种源**，这是本专题可交付给用户复现的关键。
- `parse_timestamps` 的退化时标检测与 TCP 解析告警冒泡（原先 `info.notes` 被源丢弃，用户看不到时间轴已退化）。
- 界面自解释能力（本轮 S14~S18 驱动）：`#src-hint` 逐源填写说明、`#src-formnote` 未保存提示、`label.off`/`:disabled` 置灰视觉——让「选了哪种源、该填什么、哪些框填了不生效、有没有白改」都在界面上直接可见。
- `tools/ui_dropdown_check.cjs`：jsdom 驱动**真实页面**打**真实服务端**的界面端到端检查（自动拉起 TCP 喂数器、捕获 PUT/POST 载荷原文、以 canvas 绘制调用计数验证重绘、结束把预览恢复为 simulator）。界面行为从此**可自动化回归**，不靠手点。
- `tests/test_web_ui.py`（14 项前端契约，随 `pytest tests/` 一起跑，不需 node/浏览器）：下拉框选项 ↔ 后端枚举集合相等、app.js 引用的元素 id 全部存在、两个源下拉框已注册 change、载荷裁剪/空值跳过/脏值保护/不夹带配置四道闸门在位。

### 用户执行命令（模式 B 执行包，🔶待回报）

**S 组：无硬件即可复现四源验证（Windows / Linux 通用，路径用仓库根）**

```bash
S-W1  python tools/verify_sources.py                                  # 期望：PASS 5 / SKIP 0 / FAIL 0
S-W2  python -m pytest tests/ -q                                      # 期望：161 passed, 1 skipped
S-W3  python cli.py selftest                                          # 期望：44/44，worst_rel_err≈1.5e-05
S-W4  # 终端1：python tools/tcp_feeder.py --port 9000 --mode text_csv --header --rate 4
      # 终端2：python cli.py live --source tcp --port 9000 --duration 10
      #                                              期望：U≈5806/5922/5690V、P≈1127.7kW、缺口 0
S-W5  # 终端1：python tools/csv_appender.py --out data/tail_dir --rotate-every 20 --rate 4
      # 终端2：python cli.py live --source csv_tail --path data/tail_dir --watch-newest --duration 20
      #                                              期望：缺口 0，且源告警含「旧文件补读 N 行」
S-W6  python tools/csv_appender.py --out data/tail_live.csv --rate 4 --duration 20   # 然后按 S-W5 终端2 换成该文件
```

**U 组：Web 界面下拉框点检（浏览器手点，无需 node；对应 S14~S16 的用户侧复核）**

```text
先 python cli.py serve，浏览器打开 http://127.0.0.1:8000

U-1  点左侧「🔌 数据源与控制」      期望：PT=100 / CT=15 / fs=6400 / 主机=127.0.0.1 等**均已回填**（不是空框）
U-2  「数据源输入方式」依次选 4 项   期望：每次切换后**无关字段置灰**，下拉框下方说明文字随之变化
U-3  选 tcp → 帧格式选 binary      期望：struct 格式/字段顺序两框由灰变可编辑；切回 text_csv 又变灰
U-4  选 simulator → 速率填 4 → 点「启动数据源」
                                    期望：右上状态变运行中、提示「已启动数据源：simulator」、总览面板开始出数
U-5  在 CSV 路径框打半截字后**不点任何按钮**，等 2~3 s
                                    期望：半截字不被清掉、下拉框不被改回，并出现「⚠ 界面有未保存的修改…」；
                                          再点「刷新」→ 恢复成服务端配置
U-6  电压输入口径改「线电压」→ 点「保存配置（热更新）」
                                    期望：提示保存成功；F5 刷新后仍是「线电压」
                                          （或 curl http://127.0.0.1:8000/api/config 看 transform.voltage_input=line）
U-7  （可选，需 node ≥18）npm install jsdom --prefix /tmp/uitest
     JSDOM_DIR=/tmp/uitest node tools/ui_dropdown_check.cjs http://127.0.0.1:8000
                                    期望：PASS 74 / FAIL 0
```

**D 组：接真实采集装置（需现场数据/协议，🔶）**

```bash
D-1  python cli.py sources --file <你的真实CSV>        # 回报 encoding / header / fs_est / ts_mode / notes
D-2  python cli.py compute --file <你的真实CSV> --format table
     #  回报 U/I/P/Q/PF/THDu 与现场表计或既有系统的读数对照（差多少、什么口径）
D-3  python cli.py live --source csv_tail --path <采集器正在写的文件> --from-end --duration 30
     #  回报 实时速率 / 缺口数 / 源告警原文
D-4  TCP 联调前先回报协议：帧头帧尾、长度字段、字段顺序、字节序、每字段类型（float32/float64/int）、
     时标类型（epoch 秒/毫秒/相对秒）、是否已乘变比、有无心跳/确认帧 → 据此定 struct_fmt/struct_fields
D-5  若采集器按时间分片写多个文件：回报分片命名规则、单文件时长、是否保留旧文件
     （用于确认 watch_dir_newest 是否够用，或需要改成按文件名排序）
```

### 判读要点（回报后 Agent 按此对账）

- **J-S1**：S-W1 若出现 FAIL，先看 `why` 字段——「未取到 U1_abc/P_kW」＝跑得太短（加大 `--duration`）；「U1 偏差 >5‱」＝变比或列映射不对；「缺口 ≠0」＝采集侧丢数或时标退化。
- **J-S2**：S-W2 在 Windows 上若有失败，重点看是否 `tests/test_tools.py`（子进程路径/编码差异）与 `tests/test_web.py`（端口占用）；沙盒侧 Linux 全绿。
- **J-S3**：S-W4/S-W5 的数值应与本专题 S5/S4 一致到小数点后 1 位（同一信号模型、同一 seed）；不一致先查是否有人改过 `configs/runtime.json`。
- **J-U1**：U-1 若为空框，说明 `/api/state` 没取到 config（按 F12 看控制台是否有 `/api/state` 失败）；修复后进入该页即回填，空框属回归（对应 F-08 的根因面）。
- **J-U2**：U-5 是本轮最隐蔽的缺陷（F-09）：若半截字被清掉或下拉框自己跳回，说明脏值保护失效——**它只在「停在数据源页 + 引擎在跑」时出现，每 0.2 s 一次**，静态读代码或只点一次都发现不了。
- **J-U3**：U-6 若提示「保存失败：sampling.fs 必须 > 0（当前 0）」，说明 F-08 回归（空数字框被当 0 送出）；正确行为是跳过该字段，并在成功提示里列出被跳过的字段名。
- **J-U4**：U-4 若提示成功但总览不出数，先看「运行状态与告警」里的源告警原文（csv_file 读满即 `finished`，属预期，不是故障）。
- **J-D1**：`fs_est` 与配置 fs 偏差应 <0.01%；偏差大说明时间戳精度不足（ms 级）或存在丢点，按 §4.2 注意事项处理。
- **J-D2**：与现场表计对账时注意三点口径——① 本工具默认输出**一次值**（`transform.enabled=true`）② 电压默认按**相电压**解释（若现场给线电压需改 `transform.voltage_input=line`）③ 谐波口径为 50Hz 整周期矩形窗 FFT，未做 IEC 61000-4-7 分组，与电能表的谐波子组读数会有差异。
- **J-D3**：`缺口 >0` 时先看告警里的 `gap_s` 是否等于整数个块（＝采集侧或分片切换丢数），还是随机值（＝传输丢包）。
- **J-D4**：真实协议若是「帧头＋长度＋校验」结构，`struct_fmt` 不足以描述，需要在 `elec_tool/sources/tcp_stream.py::_flush_block` 加拆帧（`DataSource` 接口不变，上层零改动）——这属于**新工作项**，需先拿到协议文档再评估工作量。

### 结果回收格式（复制到回报里即可）

```
S-W1 verify_sources：PASS __ / SKIP __ / FAIL __；FAIL 的 why 原文：______
S-W2 pytest：__ passed, __ skipped, __ failed；失败用例名：______
S-W3 selftest：__/44，worst_rel_err=______
S-W4 tcp text_csv：U=__/__/__V  P=____kW  缺口=__  源告警：______
S-W5 csv_tail 目录：输出__次  样本__  缺口=__  是否出现「旧文件补读」：是/否
S-W6 csv_tail 单文件：输出__次  样本__  缺口=__
U-1 进入数据源页是否已回填：是/否（若否，空的字段名=______）
U-2 4 种源是否都联动置灰＋说明变化：是/否（异常的源=______）
U-3 binary 帧两框是否随之放开/收回：是/否
U-4 simulator 速率4 启动是否成功出数：是/否（提示原文=______）
U-5 半截输入是否被推送清掉：是/否；未保存提示是否出现：是/否；点刷新是否恢复：是/否
U-6 口径改「线电压」保存是否成功且刷新后保留：是/否（失败提示原文=______）
U-7 （若跑了）ui_dropdown_check：PASS __ / FAIL __；失败项=______
浏览器与 OS=______
D-1 sources 体检：encoding=__ header=__ fs_est=__ ts_mode=__ notes=______
D-2 compute 与表计对照：U=______ I=______ P=______ 表计读数=______ 差=______
D-3 live 真实追加文件：速率=__样本/s 缺口=__ 告警原文=______
D-4 TCP 协议要点：帧头=__ 长度字段=__ 字段顺序=__ 字节序=__ 类型=__ 时标=__ 是否已乘变比=__
D-5 分片规则：命名=__ 单文件时长=__ 是否保留旧文件=__
环境：OS=__ Python=__ numpy=__  CPU/内存=__
```

### 结果 / 结论

- **沙盒侧（✅已复现）**：四种数据源在 CLI、Web/REST、Python 库三条入口下**全部实跑通过**，同源四路 P 极差 0.013%、U1 偏差 ≤0.70‱、THDu 偏差 ≤0.005 百分点、缺口 0 ⇒ 输入方式与入口不影响算法结果；`tools/verify_sources.py` 实测 PASS 5 / FAIL 0，`pytest` 147 passed / 1 skipped，`selftest` 44/44。
- **实测发现并修复 5 个问题**（F-01~F-05），其中 **F-01（目录分片切换丢一整块）属现场必踩**：采集器按段换文件时会出现与轮转周期同频的假缺口，容易被误判成「现场丢点」。
- **界面层（✅已复现，S14~S18）**：「数据源输入方式」下拉框的 **4 种输入方式都能正常选中并分别配置**，服务端确实按所选 kind 摄入（csv_file 读满 32000 样本后 finished；csv_tail/tcp/simulator running=true，samples_in 32000/39040/44800）；「帧格式」下拉框选 binary 才放开 struct 两项、切回 text_csv 载荷不再夹带；口径三下拉框（电压输入/视在/无功）6 组取值 PUT 后服务端回显全部生效；频谱三下拉框（通道/比例/频段上限）8 组取值 change 均触发重绘（234~1245 次绘制调用）。`tools/ui_dropdown_check.cjs` 实测 **PASS 74 / FAIL 0**（修复前同脚本 PASS 37 / **FAIL 10**）。
- **本轮又修 5 个界面缺陷（F-06~F-10）**，其中 **F-09（实时推送覆盖用户正在编辑的表单）最隐蔽**：只有「停在数据源页 + 引擎在跑」时才出现，每 0.2 s 一次，表现为「下拉框自己跳回去、路径打一半被清空」；F-08 则让**全新加载页面后第一次点「保存配置」必 400**。
- **用户侧（🔶未获实录，不下结论）**：真实采集 CSV 的编码/时标/相线口径、真实 TCP 协议帧格式、Windows 环境下的 S 组结果，均待回报。
- **是否进入 REPORT.md（稳定结论）**：**是**——① 四源等价性（同源四路 P 极差 0.013%）② F-01 教训（切换监视对象前必须 drain 旧文件）③ 「float32 不可存 epoch 秒」的协议约束 ④ 无硬件验证路径（`tools/` 三件套）⑤ **界面层验证方法与空值语义**（C-13：真实 DOM＋真实服务端才能验界面；深合并接口下「留空＝沿用、送 0＝被拒/被覆盖」，前端必须裁剪载荷）。
- **遗留问题**：
  1. TCP 的 `timeout_s` / `reconnect_s`（各默认 2.0 s）只是构造参数，未暴露到配置文件与界面；
  2. 真实协议若含帧头/长度/校验，需要在 `_flush_block` 加拆帧逻辑（待协议文档）；
  3. 喂数器/追加器是**联调工具**，不替代真实装置的背压、断连、乱序行为验证；
  4. Windows 侧 S 组未实测（子进程与路径分隔符可能有差异）；
  5. `csv_tail` 目录模式按 mtime 选最新文件，若现场分片命名与 mtime 不一致（如补写旧分片），需要改成按文件名排序——待 D-5 回报后决定。
  6. 界面检查在 **jsdom** 中运行，无真实浏览器渲染：置灰以 `disabled` 属性断言代替视觉核对，canvas 以绘制调用计数代替像素比对；真实浏览器（尤其 Windows/Edge）下的视觉、输入法与焦点行为未实测——由 U 组回报补齐。
  7. 引擎启动后服务端把 `source.path` 解析为**绝对路径**并经 `/api/config` 回显到表单（`_persist` 写盘时仍还原为相对路径），属外观问题，未修。
  8. U 组（浏览器手点 7 步）与 S 组、D 组一样**尚未获用户实录**，界面在真实浏览器下的表现不下结论。

## [2026-10-12] 专题 T-004：第 6 轮四功能（用户时标格式 / 24h 曲线 / 逐曲线保存开关 / 自定义播放时间）

- 类型：用户专题（功能实现 + 验证测试）
- 执行模式：混合——沙盒侧实录（✅）＋ 用户侧浏览器点检 U6 组（🔶待回报）
- 本专题角色：工程实现工程师（默认资深电力算法专家负责口径复核）
- 目标与假设：
  1. 离线 CSV 支持 `0/00/00 00:12:40.0000,290.175751,…` 格式（用户原样给出三行：日期段全 0、只有当天时刻、小数 4 位＝0.1 ms、**无表头**）；
  2. 界面所有趋势曲线＝最新 24 小时数据，不足则全部；
  3. 每条曲线可分别配置是否保存，保存曲线数据时未勾选项不保存；
  4. 离线播放可选「自定义时间」：启用则时间轴＝起始时间＋样本序号/采样率，起始默认文件第 1 条数据时间；否则按文件内时间播放；
  5. 完成后验证各功能。
  **假设**（用户未说明、按工程默认处理并在 README 标注）：「24 小时」按**数据时间**计（离线回放同样成立）；「曲线」指 6 条时间趋势（波形/频谱是单窗瞬时量）；「保存曲线数据」＝服务端写 `output/curves_<ts>/<曲线>.csv` ＋ 浏览器下载合并 CSV 两个入口；自定义起始时间文本按**本地时间**解释。
- 方法 / 数据 / 参数：
  - 数据：用户三行原样样例（单元测试直接引用）＋ 按同一写法合成的 3 s / 19200 行文件（`tests/conftest.py` 新增 `ts_mode="clock"`；`tools/ui_r6_check.cjs` 自动生成 `/tmp/ui_r6_user_fmt.csv`）
  - 工具：`pytest tests/test_r6_features.py`（25 项，每项写明「撤销修复会怎样 FAIL」）、`tools/ui_r6_check.cjs`（jsdom 真实 DOM 打真实服务端，30 项）、旧 `tools/ui_dropdown_check.cjs` 复跑防回退、`curl` REST 取证

### 沙盒侧实录（三件套：命令 + 输出 + 判读）✅

**S1 修复前基线（证明问题真实存在）**
```
$ python cli.py compute --file /tmp/f1/user_fmt.csv
✗ 执行失败：ParseError: 时间戳 '0/00/00 00:12:40.0000' 无法解析；已尝试格式 (...) 与 ISO8601
$ curl "/api/probe?path=/tmp/f1/user_fmt.csv"
{"ok":false,"error":"ConfigError: CSV 表头无法识别字段 [...]；表头=['0/00/00 00:12:40.0000', '0.000000', ...]"}
```
判读：两处失败——时间戳格式不认识；无表头文件在 `/api/probe` 被当成表头解析失败（`iter_csv_blocks` 本就能回退，probe 没有同样的回退）。

**S2 修复后：解析器单元取证**
```
parse_timestamps(用户三行) → mode=clock_time  t=[760. 760.0001 760.0003]  (00:12:40 → 760 s)
  notes: 时间戳格式识别为 'Y/M/D HH:MM:SS.f(无日期=0/00/00)'；时间戳只有时刻、无日期…按 1970-01-01 + 当天时刻处理，跨午夜自动展开…
["0/00/00 23:59:59.9999","0/00/00 00:00:00.0001"] → diff=+0.0002（跨午夜不判回退）
["2026/1/5 8:03:07.5", …] → mode=datetime（不补零写法顺带支持；与 strptime 路径结果一致）
```

**S3 修复后：CLI 端到端（3 s 合成文件，同一写法）**
```
$ python cli.py compute --file /tmp/f1/user_fmt.csv --quantities voltage,fundamental --format table
✓ 完成：输出 16 次；读入样本 19200（3.00s 数据），块 15
  · 源：时间戳格式识别为 'Y/M/D HH:MM:SS.f(无日期=0/00/00)'
  · 源：采样率校验通过：时间戳推算 6400.008Hz ≈ 配置 6400.0Hz（偏差 0.0001%）
$ python cli.py compute --file … --custom-time-start "2026-10-12 08:00:00" --limit 2
数据时刻 2026-10-12 08:00:00 … · 源：自定义播放时间已启用：时间轴 = 起始时间(配置起始时间) + 样本序号/fs
```
判读：0.1 ms 截断下逐点差分在 0.1/0.2 ms 间跳动，`_infer_fs` 的最长段线性拟合仍给出 6400.008 Hz（偏差 1e-6 量级）。修复前该文件还会刷「1280 个单元格非数值（行0列0='0/00/00 …'）」——无表头路径把时间戳列当数值解析，已改为跳过第 0 列。

**S4 源层：自定义时间三态（`CsvFileSource` 直读两块）**
```
custom=False start=''                     t0=760.0000 b2.t0=761.000000 dt_uniform=0.640  → 1970-01-01 00:12:40
custom=True  start=''                     t0=760.0000 b2.t0=761.000000 dt_uniform=1.000  → 文件第 1 条数据时间
custom=True  start='2026-10-12 08:00:00'  t0=1791792000.0000 b2.t0=1791792001.0  dt_uniform=0.999  → 配置起始时间
```
判读：`dt_uniform`＝相邻样本差×fs；关自定义时为 0.64（文件时标被 0.1 ms 量化），开自定义后恒为 1（跨块连续，不重置）。

**S5 REST：probe / start / state / history**
```
GET /api/probe?path=…user_fmt.csv → ok=True has_header=False rows=19200 ts_mode=clock_time fs_est=6400.003 t_first_text='0/00/00 00:12:40.0000'
POST /api/engine/start {"kind":"csv_file","path":…,"custom_time":true,"custom_time_start":"2026-10-12 08:00:00"} → ok=True（回显 custom_time=true：白名单已放行）
GET /api/state → finished=True samples=19200 | source.custom_time=True 起始来源=配置起始时间 2026-10-12 08:00:00 | file_first_t=760.0
GET /api/history/voltage?max_points=1500 → {count:4,count_total:4,hours:24.0,decimated:False,span_s:2.0} t_first=2026-10-12 08:00:00
```

**S6 History 24h 保留与性能（合成 30 h@1 pt/s、24 h@0.2 s）**
```
30h@1pt/s push 108000 → 保留 count=87000 dropped=21000 span=24.17h（懒修剪 ≤5% 余量；get(hours=24) 精确 86401 点）
24h@0.2s ×2 快量：push 864k 条 3.7 s；内存 38.5 MB；count=432000 span=24.00h
get(24h, max_points=1500) → 1000 点  40 ms（numpy 分桶前的纯 Python 版为 757 ms，24h 时 6 曲线/3 s 轮询会把 2 核吃满 → 已改）
并发：引擎线程 push 2 万条 + Web 线程 get 200 次 → 0 异常（加了 History 锁；numpy 拷贝不保留 buffer 导出，否则 array 扩容会 BufferError）
```

**S7 保存曲线：勾选过滤（REST）**
```
PUT /api/config {"output":{"curve_save":{"current":false,"harmonic":false}}} → 200；GET /api/config 回显 current/harmonic=false，其余 true
热更新后 GET /api/history/voltage count_total=4（不变）；GET /api/result 200（不变）
POST /api/curves/save {} → ok dir=output/curves_20261012_113236 files=[voltage 4, power 4, power_factor 4, fundamental 16] skipped=[current, harmonic]
voltage.csv 表头：t_epoch_s,time_local,quantity,window_s,Ua,Ub,Uc,Uab,Ubc,Uca,unbalance_pct,U1（UTF-8-BOM）
GET /api/curves/export?quantity=current → 403；?quantity=voltage → 200 text/csv；合并下载只含 fundamental/power/power_factor/voltage
全部取消 → POST /api/curves/save → 400「没有勾选任何要保存的曲线」
```
判读：**修复前**热更新后 `count_total=0`、`/api/result` 409——`EngineRunner.set_cfg()` 对「已结束」的离线引擎整个重建，勾一下保存框就把 24h 曲线和结果清空；改为任何已有引擎都走 `update_config()`，并让 `LiveEngine.update_config()` 搬运 `history`。另修 `time_local` 小数部分四舍五入进位（760.9998 → 「:40.000」）为截断。

**S8 界面端到端（jsdom 真实 DOM + 真实服务端）**
```
$ JSDOM_DIR=/tmp/uitest node tools/ui_r6_check.cjs http://127.0.0.1:8000
=== D1 自定义播放时间 ===  simulator 下勾选框禁用 ✓ / csv_file 下可用、起始框未勾选时禁用 ✓ / 勾选后放开 ✓
  未勾选载荷 {"kind":"csv_file","path":…,"custom_time":false,"custom_time_start":"","block_samples":640} ✓ → 服务端跑完 samples_in=19200 ✓ t_last=762.9998（文件时标）✓
  勾选+起始 → 载荷 custom_time=true ✓ → source.custom_time=true 起始来源=配置起始时间 ✓ 曲线 t_first-t0=1.000 t_last-t0=3.000 ✓ 摘要显示「自定义播放时间」✓
  起始留空 → 起始来源=文件第 1 条数据时间 t0=760 ✓ / 起始填「昨天」→ 400 ✓ + toast 含可接受写法 ✓
=== D3 曲线请求 ===  6 条请求均 max_points=1500、无 n= ✓ / 概览「最近 24 小时」说明 ✓ / 面板标题「最近 2.0s · 4 点（保留窗 24h）」✓ / history 元数据 ✓
=== D2 保存曲线 ===  6 面板各 1 勾选框 ✓ 初始全选 ✓ 取消 current → PUT output.curve_save.current=false 200 ✓ 回显 ✓ render 后不翻回 ✓
  PF 页勾选框 ✓ → power_factor=false ✓ / 导出页 6 项同步 ✓ 文案「4/6」✓ / 点保存 → POST 200 ✓ 列出 4 文件 +「三相电流：未勾选，已跳过」✓ / 导出页重勾 current → 概览同步 ✓ 服务端 true ✓
=== 结果：PASS 30 / FAIL 0 ===
$ node tools/ui_dropdown_check.cjs → PASS 74 / FAIL 0（上一轮 harness 复跑；唯一改动：允许 custom_time_start 为空串——空＝「用文件第 1 条」是有效语义）
```

**S9 全量回归**
```
$ pytest tests/ -q → 186 passed, 1 skipped（61 s）   （161 → 186，新增 tests/test_r6_features.py 25 项）
$ python cli.py selftest → 44/44，最差相对误差 1.508e-05
```

### 本轮修复的缺陷（全部由实测发现）

| 编号 | 现象 | 根因 | 修法 | 回归 |
| --- | --- | --- | --- | --- |
| F-11 | 用户时标 `0/00/00 00:12:40.0000` → `ParseError` | `TS_FORMATS` 全是 strptime，月/日为 0 必失败 | `_parse_slash_clock` 正则骨架：日期段任一为 0 → 当天时刻（1970-01-01 基准，mode=`clock_time`），`_unwrap_midnight` 跨日展开，小数按位数换算 | `test_user_clock_format_*`、`test_clock_format_unwraps_midnight` |
| F-12 | 无表头文件 `/api/probe` 报「表头无法识别」 | probe 没有 `iter_csv_blocks` 的「首行不像表头→当数据」回退 | 同一规则；返回 `has_header/first_row/t_first_text` | `test_web_probe_accepts_headerless_clock_file` |
| F-13 | 无表头文件每块刷「1280 个单元格非数值（行0列0=时间戳）」 | `parse_rows` 把第 0 列也按数值解析 | 跳过第 0 列 | `test_headerless_user_file_runs_through_csv_source` |
| F-14 | 趋势曲线只有最后 600/400 点（`History(maxlen=600)`＋前端 `n=400`） | 定长 deque、无时间语义 | 按数据时间修剪的紧凑列存储＋`hours/max_points`＋峰谷抽稀 | `test_history_keeps_only_last_24h_by_data_time` 等 4 项 |
| F-15 | 任何热更新（含勾选保存框）后已结束离线引擎的历史与结果清空 | `set_cfg` 对非存活线程重建 `LiveEngine`；`update_config` 重建 `MetricsCalculator` 丢 history | 已有引擎一律 `update_config`；`update_config` 搬运 history 并按新配置更新保留参数 | `test_engine_hot_update_preserves_history`、`test_web_curve_save_toggle_persists_and_keeps_history` |
| F-16 | （自测发现）`History.get` 纯 Python 抽稀 43 万点 757 ms；无锁下引擎线程 `del` 切片与 Web 线程读取竞争 | — | numpy 分桶（40 ms）＋`threading.Lock`＋拷贝不保留 buffer 导出 | S6 并发实录 |

### 用户执行命令（U6 组：浏览器手点，🔶待回报）

```
U6-1 数据源页选「离线文件」→ 出现「csv_file：自定义播放时间」勾选框与「自定义起始时间」输入框；选其它源时两者置灰
U6-2 路径填你的真实 CSV（0/00/00 写法）→「探查数据」→ 期望 has_header=false、ts_mode=clock_time、fs_est≈6400、无红色错误
U6-3 不勾自定义 →「启动数据源」→ 概览出数；曲线横轴显示 00:12:40 一类时刻（日期为 1970，属预期）
U6-4 勾自定义、起始留空 → 启动 → 数据源状态摘要含「自定义播放时间：起始 文件第 1 条数据时间」
U6-5 勾自定义、起始填 2026-10-12 08:00:00 → 启动 → 摘要含「配置起始时间」，曲线横轴从 08:00:00 起；起始填「昨天」→ 红色 toast 含可接受写法
U6-6 概览任一曲线面板右上角取消「保存曲线」→ toast「已排除出保存项」→ F5 后仍未勾选；「导出与日志」列表同步、点「保存曲线数据到 output/」→ 列表含「…：未勾选，已跳过」，output/curves_<时间>/ 下无该曲线文件
U6-7 让模拟器连续跑 ≥10 分钟 → 概览曲线面板标题显示「最近 10.x min · N 点」，横轴不显示毫秒；（可选）跑过夜后标题显示「最近 24.00h」且内存稳定
U6-8（可选，有 node）npm install jsdom --prefix /tmp/uitest && JSDOM_DIR=/tmp/uitest node tools/ui_r6_check.cjs http://127.0.0.1:8000 → 期望 PASS 30 / FAIL 0
```

### 判读要点
- J-U6a：U6-2 若 `fs_est` 明显偏离 6400（>1%），说明真实文件时标截断方式与样例不同（例如只写到 ms），把 probe 输出贴回即可，不影响电气量计算（计算只按样本序与配置 fs）；
- J-U6b：U6-5 自定义起始时间按**你电脑的本地时区**解释；若现场要求 UTC，请回报，我们加 `tz` 字段；
- J-U6c：U6-7 若 24 h 后内存持续增长，回报 `/api/state` 里 `history.*.count/dropped`，用于判断是修剪没生效还是别处泄漏。

### 结果回收格式
```
T-004 回报  日期=____  浏览器=____  OS=____
U6-1 ☐通过 ☐异常：____    U6-2 has_header=__ ts_mode=__ fs_est=__    U6-3 ☐通过
U6-4 摘要文字=____          U6-5 ☐通过（起始=____）  非法文本提示=____
U6-6 ☐通过（跳过的曲线=____；output 目录文件=____）
U6-7 标题文字=____  内存（任务管理器）=____    U6-8 PASS __ / FAIL __
```

### 结果 / 结论
- **沙盒侧（✅已复现）**：四项功能全部实现并通过三层验证——25 项 pytest（撤销修复必 FAIL）、30 项 jsdom 端到端、旧 74 项 harness 无回退；全量 **186 passed, 1 skipped**，selftest 44/44。用户给出的三行样例被单元测试原样引用并解析正确。
- **实测发现并修复 6 个问题（F-11~F-16）**，其中 **F-15（热更新清空 24h 曲线）**若不修，功能③的勾选框每点一次就把功能②的曲线清空，两项功能互相打架；**F-16** 若不修，24 h 曲线在 2 核机器上会把 CPU 吃满。
- **用户侧（🔶未获实录，不下结论）**：真实采集文件的时标截断方式、时区语义、真实浏览器下的勾选/曲线表现、过夜内存，待 U6 组回报。
- **是否进入 REPORT.md（稳定结论）**：**是**——C-14「趋势历史按数据时间保留＋传输前峰谷抽稀」；C-15「无日期时标的处理规则（当天时刻→1970 基准、跨午夜展开、真实日期由自定义起始时间给）」。
- **遗留问题**：
  1. 自定义播放时间只对 `csv_file` 生效；`csv_tail` 实时追加按定义使用文件时标（若现场 tail 的文件也是 0/00/00 写法，曲线日期会是 1970——需要时可扩展）；
  2. 开自定义时间后文件内缺口不再被检测（时间轴合成）；
  3. 趋势历史随「重新启动数据源」清空（一次运行＝一个数据集的既有决策）；跨运行/跨进程的 24 h 需要落盘（SQLite/CSV 滚动文件），本轮未做；
  4. `history_hours` / `history_max_points` 只能在配置文件改，未上界面；
  5. 曲线 x 轴跨午夜时只显示时:分:秒不显示日期（24 h 内最多跨一次午夜，可从面板标题的跨度判断）。

---

## [2026-10-12] 专题 T-005：第 7 轮三功能（曲线实时落盘 / 离线文件指定位置播放 / 曲线悬停取值）
- 类型：用户专题（实现＋验证）
- 目标与假设：用户原话「1. 计算的曲线数据实时保存到 output/realtime 目录下 CSV 文件中；2. 离线文件可指定位置进行播放；3. 鼠标移动到曲线上时显示鼠标指示位置的数据」。假设（用户未说明，已按最合理语义实现并在 README §3.1 标注）：① 「曲线数据」＝6 条趋势曲线的标量点（与第 6 轮「保存曲线」同一口径），实时＝**每算出一点就追加一行并 flush**，按**数据日期**分文件（跨午夜换文件），并受「保存曲线」勾选过滤（未勾选＝不落盘，与手工保存一致）；② 「指定位置」给四种定位方式（第 N 行 / 跳过 N 秒 / 文件 N% / 指定时刻）＋从头，起点之前的数据不参与计算；③ 悬停取值对所有 canvas 曲线（趋势/波形/频谱）生效，吸附到最近数据点而不是插值。
- 方法 / 数据 / 参数：代码改前先探查 `History`/`_curve_rows`/`iter_csv_blocks`/`drawLine`；实现后三层验证——pytest（每项写明撤销修复如何 FAIL）、jsdom 驱动真实页面打真实服务端（`tools/ui_r7_check.cjs`）、CLI 实跑；旧 harness（r6 30 项 / 下拉框 74 项）复跑防回退。数据：`data/sample_6400hz.csv`（32000 行 / 5 s）、合成 `0/00/00` 无表头文件（4 s / 25600 行）。
- 执行模式：混合——沙盒侧（A）✅已实录；用户侧（B）＝U7 组浏览器点检 🔶待回报。

### 沙盒侧实录（三件套：命令 + 输出 + 判读）✅

**S1 源层：播放起点五种模式（库级）**
- 命令：Python 直接构造 `CsvFileSource`，对 `data/sample_6400hz.csv`（32000 行）逐一设置 `play_start_mode/value`
- 输出：`begin → 32000 点 t0=1791802088.19`；`row 6401 → 25600 点 t0=…089.19 play_seek={'mode':'row','skipped_rows':6400}`；`seconds 1 → 25600 点`（同 row）；`percent 50 → 16000 点 start_byte=1307411/2614757`；`time "2026-10-12 10:48:10" → 20413 点 skipped_rows=11587 start_t=1791802090.0001`；`time "10:48:11" → 14013 点`；`time "2099-01-01" → skipped 32000 reached_eof=True`；用户 0/00/00 文件 `time "00:12:41" → skipped 6400 start_t=761.0`
- 判读：row/seconds 精确到行；percent 按字节对齐行首后样本数恰为一半；time 的绝对/只填时刻两种写法都命中；超范围时 `reached_eof=True` → 第一次 `read()` 抛 `ParseError: 播放起点超出文件范围…`（修前静默 0 样本，F-17）

**S2 CLI**
- 命令：`python cli.py compute --file data/sample_6400hz.csv --play-from sec:2 --realtime-dir /tmp/rt_test --format table --limit 2`
- 输出：`✓ 完成：输出 2 次；读入样本 2560 … · 实时落盘：/tmp/rt_test（本次写入 4 行，2 个文件） · 源：播放起点：跳过开头 2 s（≈12800 行）…实际跳过 12800 行`；`/tmp/rt_test/fundamental_20261012.csv` 首行 `t_epoch_s,time_local,window_s,f,U1,I1,unbalance_pct,phiA_deg`，带 BOM
- 命令：`--play-from time:23:59:59` → `✗ 执行失败：ParseError: 播放起点超出文件范围：time='23:59:59'，文件共 32000 条数据行（没有时标 ≥ 该时刻的数据；…）`
- 判读：CLI 三件（`--play-from` / `--realtime-save` / `--realtime-dir`）可用，收尾诊断打印落盘行数与跳过行数

**S3 pytest 回归**
- 命令：`.venv/bin/python -m pytest tests/test_r7_features.py -q` → **18 passed**；`pytest tests/ -q` → **204 passed, 1 skipped**（约 69 s）
- 关键断言：实时落盘文件行数 == `History.get()` 点数 == `writer.rows_written`（6 曲线逐条）；文件值 == 历史值；未勾选曲线无文件；`realtime_save=False` 零文件；同一天二次运行续写且 BOM/表头各 1 份；相差 1 天的两条记录 → `power_20261012.csv`+`power_20261013.csv`；热更新关开关后旧 writer 不再写；`parse_play_start` 合法/非法 12 组；row/seconds/percent/time/只填时刻/0/00/00 文件/超 EOF/与自定义时间组合；REST 白名单放行＋`play_seek` 回显＋400＋超范围错误可见；`/api/realtime`；前端契约（下拉框 5 项 == `PLAY_START_MODES`、面板元素齐全、`drawLine` 末尾 `drawHover`、`fmtTip` 6 处）
- 判读：全绿；撤销任一实现对应用例 FAIL（用例 docstring 标明）

**S4 jsdom 端到端（真实页面 + 真实服务端 8000）**
- 命令：`JSDOM_DIR=/tmp/uitest node tools/ui_r7_check.cjs` → **PASS 39 / FAIL 0**（连跑 3 次稳定）
- E1 实时落盘：面板 4 元素齐全、回填服务端配置；离线文件跑完 → 目录 6 个 `<曲线>_19700101.csv`（0/00/00 文件的数据日期＝1970-01-01，符合第 6 轮 C-15 规则）；`voltage` 文件 5 行 == `rows_written` == `count_total`；表头 `\uFEFFt_epoch_s,time_local,window_s,Ua,Ub,Uc…`；取消 current 勾选再跑 → `{before:{v:5,c:5}, after:{v:10,c:5}}`（current 不增、voltage 续写）；点「应用」关闭 → `PUT {output:{realtime_save:false,…}}` 200 → 再跑行数不变 → `/api/realtime enabled=false, dir_files=6`
- E2 播放起点：simulator 下两控件禁用；csv_file 下下拉可用、begin 时取值框禁用；选项 `begin,row,seconds,percent,time`；row=6401 载荷 `{…,"play_start_mode":"row","play_start_value":"6401"}` → `samples_in=19200`（25600−6400），摘要含「跳过 6400 行」；seconds=2 → 12800；percent=50 → 12799；time=00:12:43 → 6400 且 `t_first=763.9998`；time=23:59:00 → `error: ParseError: 播放起点超出文件范围…`；row=abc → 400 ＋ toast「播放起点「第 N 行」必须是整数」；选回 begin → 25600 全量
- E3 悬停：`ov-u` 已挂 `__chart`（3 条曲线）＋`crosshair`；mousemove 到最后一点像素 → `__hoverInfo` 3 项且 `Ua/Ub/Uc` 与 `S.histCache.voltage[-1]` 完全相等（`21213.2034…`）；x 文本 `00:12:43.999`（含毫秒）；靠近首点吸附 idx=0；`render()` 重绘后悬停仍在；mouseleave 清除；刻度区不显示；频谱图悬停 50 Hz 给出 `50.00 Hz`
- 旧 harness 复跑：`ui_r6_check.cjs` **PASS 30 / FAIL 0**、`ui_dropdown_check.cjs` **PASS 74 / FAIL 0**
- 判读：三项功能在真实 DOM＋真实服务端下可用，且与第 5/6 轮功能无回退

### 本轮修复/发现的问题
| 编号 | 现象 | 修法 | 状态 |
| --- | --- | --- | --- |
| F-17 | 播放起点超出文件范围时源静默读出 0 样本，引擎「已结束」无任何提示 | `CsvFileSource.read()` 首次即 EOF 且 `reached_eof` → 抛可诊断 `ParseError`（含模式/取值/文件总行数/0/00/00 提示） | ✅已修＋回归 |
| F-18 | 默认开启实时落盘后，所有测试/工具跑一次就往仓库 `output/realtime/` 写文件 | 环境变量 `ELEC_TOOL_REALTIME_DIR` 优先；`tests/conftest.py` autouse 夹具把它指到 `tmp_path` | ✅已修 |
| F-19 | r6/r7 Web 测试与 jsdom 脚本在 `finished=true` 后立刻数行/数点，而运行线程还要 `flush_all` 一次（收尾强算＋入历史＋落盘）→ 偶发 `assert 4 == 3`（全量跑时复现、单跑不复现） | `_wait_finished` 在 finished 后再等 0.3~0.6 s 并重读状态 | ✅已修（测试侧） |
| F-20 | jsdom 脚本在预览进程常驻模拟器时把落盘目录切到临时目录 → 模拟器把「今天日期」的文件写进测试目录，污染「6 个文件」断言 | 脚本开头先 `POST /api/engine/stop` 再改目录（真实部署无此问题：切目录＝有意为之） | ✅已修（测试侧） |
| F-21 | 首版载荷在 `begin` 模式也送 `play_start_value:""`，违反第 5 轮「载荷无空值」纪律（`ui_dropdown_check` FAIL 1） | 只在非 begin 时送取值 | ✅已修 |
| F-22 | **用户回报**：本机 `127.0.0.1` 正常，用局域网 IP `192.168.0.167` 访问时每次界面刷新纵向滚动条变长、页面一直拉伸 | 根因＝`prep()` 每次重绘回读 `getAttribute('height')`，而 `cv.height = h*dpr` 会同步改写该属性 → `devicePixelRatio≠1` 时高度按 dpr 复利放大（沙盒复现 dpr=1.25：200→250→312→390→487）；与 IP 无关，差异来自浏览器**按主机名记忆的缩放级别**（或另一台机器的 Windows 125%/150% 缩放）使 dpr≠1。修法＝逻辑高度首次读取后缓存在 `data-h`，不再回读；修后 dpr=1.25 下 CSS 高度恒 200px、位图 250px（高分屏仍清晰）；回归 `test_canvas_prep_does_not_reread_scaled_height_attribute` | ✅已修＋回归（`fc5c688`） |
| F-23 | **用户回报**：离线文件播放时顶栏「样本」与「数据源状态」汇总不自动更新、需手动刷新 | 根因＝`/ws` 只在队列**空闲 1s** 时才发 `state`（samples_in/数据时长/缓冲/输出次数都只在 state 里）；离线播放 result 连续不断、队列永不空闲 → state 永不下发（模拟器 0.2s 一帧亦偶发）。修法＝按单调时钟每 `WS_STATE_INTERVAL_S=1.0s` 必发一次 state，与 result 流量无关。实测 3s 播放：result 26 条、state 4 条、samples_in 17280→32000；旧代码同场景 state=0。回归 `test_ws_pushes_state_periodically_during_continuous_playback`（旧代码 `assert 0 >= 2` 失败） | ✅已修＋回归（`e20869a`） |

### 用户执行命令（U7 组：浏览器手点，🔶待回报）
- U7-1 `python cli.py serve` → 浏览器「导出与日志」→「实时落盘」：开关勾选、目录 `output/realtime` → 「数据源与控制」启动模拟器 → 等 10 s → 回到导出页点「刷新状态」。**期望**：列出 6 个 `<曲线>_<今天>.csv` 与「本次会话已写 N 行」，N 随时间增长；资源管理器里 `output/realtime/` 有 6 个文件，Excel 打开 `voltage_<今天>.csv` 列为 `t_epoch_s,time_local,window_s,Ua,Ub,Uc,Uab,Ubc,Uca,unbalance_pct,U1`
- U7-2 概览页取消「三相电流」的「保存曲线」→ 等 5 s → 导出页刷新状态。**期望**：面板出现「三相电流：未勾选「保存曲线」，不落盘」，`current_<今天>.csv` 行数不再增长；其它文件继续增长
- U7-3 导出页取消「启用实时落盘」→ 点「应用」→ toast「实时落盘已关闭（已写入配置）」→ 等 5 s → 刷新状态。**期望**：状态「未启用」，所有文件行数不变；重新勾选并应用 → 继续追加到同一文件（不出现第二个表头）
- U7-4 用**真实采集文件**：数据源页选 csv_file、填路径、「播放起点」选「跳过开头 N 秒」填 `60` → 启动。**期望**：摘要「已摄入」= 总行数 − 60×fs，告警「播放起点：跳过开头 60 s（≈384000 行）…实际跳过 384000 行」；曲线第一个点时刻＝文件第 1 条时刻 + 60 s
- U7-5 同一文件「播放起点」选「指定时刻」只填 `HH:MM:SS`（取文件中段某一时刻）→ 启动。**期望**：曲线从该时刻开始；填一个文件里没有的时刻（如 `23:59:59`）→ 状态「✗ 播放起点超出文件范围…」
- U7-6 「播放起点」选「文件 N% 处」填 `90` → 启动。**期望**：数秒内跑完最后 10%（大文件也不需要先读前 90%），摘要显示「（字节 X/Y）」
- U7-7 概览页鼠标在「三相电压趋势」上左右移动。**期望**：竖虚线吸附到最近点、三色圆点、浮框 `HH:MM:SS.mmm / Ua: … V / Ub / Uc`；移到最右侧浮框翻到左边；曲线每 0.2 s 刷新时浮框不消失；移出图表浮框消失；电压页「波形」上浮框 x 为秒、频谱页为 Hz
- U7-8（可选，过夜）实时落盘开着跑过 00:00。**期望**：`output/realtime/` 出现次日日期的新文件，旧文件停止增长

### 判读要点
- J-U7a：`voltage_<日期>.csv` 行数应 == 概览电压曲线面板标题处的「N 点」（同一提取规则、同一时刻写入）；若文件行数**持续落后**，说明磁盘写入阻塞（看面板 `errors`）
- J-U7b：播放起点的「实际跳过行数」应与自算一致：row 模式＝N−1；seconds 模式＝round(秒×fs)；若不一致，先核对配置 `sampling.fs`
- J-U7c：时刻模式下若报超范围但你确认文件里有该时刻 → 核对文件时标是「当天时刻（0/00/00）」还是带日期；带日期的文件请填完整 `YYYY-MM-DD HH:MM:SS`；时区按本机本地时间解释

### 结果回收格式
```
U7-1 文件清单：…  voltage 行数(刷新两次)：… / …   列头：…
U7-2 current 行数(前/后)：… / …   voltage 行数(前/后)：… / …
U7-3 关闭后行数：…  重开后是否有第二个表头：是/否
U7-4 文件总行数：…  已摄入：…  告警原文：…
U7-5 时刻：…  曲线首点时刻：…  超范围提示原文：…
U7-6 用时：… s  摘要字节：…
U7-7 浮框内容截图或抄录：…  刷新时是否消失：是/否
U7-8（可选）次日文件名：…
```

### 结果 / 结论
- **沙盒侧（✅已复现）**：三项功能全部实现并通过三层验证——18 项 pytest、39 项 jsdom 端到端、旧 104 项 harness 无回退；全量 **204 passed, 1 skipped**。
- **用户侧（🔶未获实录，不下结论）**：真实大文件下 percent/time 定位耗时、Windows 下文件句柄与 Excel 同时打开时的追加行为、真实浏览器的悬停视觉，待 U7 组回报。
- **是否进入 REPORT.md（稳定结论）**：**是**——C-16（实时落盘必须与曲线/手工保存共用同一提取规则、按数据日期分文件、受同一勾选过滤，否则三处数字对不上）；C-17（播放起点四种定位的代价与语义：row/seconds O(N) 跳行、percent O(1) 字节定位但跳过行数未知、time 顺序扫描时标列；超范围必须可诊断）。
- **遗留问题**：
  1. 实时落盘为**单进程追加写**，不做轮转大小限制：0.2 s 快量一天约 43 万行/文件（≈40 MB），长期运行需外部清理或后续加「按大小/天数清理」；
  2. `percent` 模式跳过的行数未知（只报字节），`time` 模式对**非单调**时标（除跨午夜外）只取第一次 ≥ 目标的位置；
  3. 播放起点只对 `csv_file` 生效（`csv_tail` 已有 `tail_from_end` 语义）；
  4. 悬停浮框固定吸附最近点，不做线性插值；多条曲线 x 不对齐时（各量独立窗长）各自取最近点，同一浮框内各项时刻可能相差一个步长（已按首条曲线的时刻显示）；
  5. 实时落盘目录与「保存曲线」勾选共用一份配置：想「不落盘但手工保存」目前只能关总开关。

---

## [2026-10-12] 专题 T-006：第 8 轮 数据处理子界面——离线波形 CSV 重采样
- 类型：用户专题（实现＋验证）
- 目标与假设：用户原话「增加数据处理子界面：支持对指定路径的离线波形 CSV 文件按指定采样频率进行重采样，重采样后的文件保存到 data 目录下，文件名为原始文件名+re+采样率，如 `波形_农业排灌_大水泵_80_1.csv` → `波形_农业排灌_大水泵_80_1_re_6400.csv`」。假设（用户未说明，已按最合理语义实现并在 README §3.1 标注）：① 原采样率默认由时间戳推算、可手填；② 时间轴按等间隔重建而不逐行用原时标（采集器 0.1 ms 量化）；③ 默认 linear（流式、大文件安全），fft 作为抗混叠选项；④ 表头/列序/编码/BOM/时标写法原样保留；⑤ 输出已存在默认拒绝、需勾选覆盖。
- 方法 / 数据 / 参数：先探查 `parsing.py`（时标解析/格式/fs 推算）复用其规则；实现 `elec_tool/resample.py`（numpy only）→ REST 后台任务 → CLI → UI；三层验证：pytest 16 项、jsdom 端到端 29 项（真实页面打真实服务端，用用户命名的样例文件）、CLI 实跑；旧 harness r7/r6/dropdown 复跑防回退。数据：合成 3200 Hz `0/00/00 12:40:00.ffff` 文件（用户命名）、`data/sample_6400hz.csv`、epoch 秒 / 整数毫秒 / ISO / GBK / 无表头 / 带 BOM 变体。
- 执行模式：混合——沙盒侧（A）✅已实录；用户侧（B）＝U8 组浏览器点检 🔶待回报。

### 沙盒侧实录（三件套：命令 + 输出 + 判读）✅

**S1 算法层：3200→6400 升采样（用户命名文件、GBK、0/00/00 时标）**
- 命令：`resample_csv("/tmp/rs/波形_农业排灌_大水泵_80_1.csv", 6400, method=m)`，m ∈ linear/fft/nearest；对比解析 `100·sin(2π50t)`
- 输出：三种方法输出名均 `波形_农业排灌_大水泵_80_1_re_6400.csv`；`32000 → 63999`（linear/nearest）/ `64000`（fft 周期语义）；`fs_src 3200.0`（推算）；首/末时标 `0/00/00 12:40:00.0000` / `12:40:09.9997`；Ua 最大误差 linear **0.1203**、fft **1e-06**、nearest 4.9（半样本偏移，预期）；耗时 0.6~0.7 s
- 判读：文件名符合用户规格；时标写法与小数位保持；linear 误差＝50 Hz 在 1/3200 步长下线性插值理论上限（0.12），fft 在整周期信号上精确

**S2 fft 降采样抗混叠（6400→800，Ia 含 1250 Hz 分量）**
- 输出：`rows_out 8000`，Ia 与纯 50 Hz 解析解最大误差 <1e-4（1250 Hz 被理想低通滤掉）；同场景 linear 的 notes 含「⚠ 线性插值降采样无抗混叠」
- 判读：与 README 的方法说明一致

**S3 时标写法 × 编码 × 表头矩阵**（`test_timestamp_styles_encodings_header`）
- 输出：epoch 秒 → `1791861203.000000`、第 2 行 +1/6400；整数毫秒 → 自动加 2 位小数 `1791861203000.00 / +0.16 / 64 步=10.00`（整数部分与小数偏移分开算，无 1e12 量级 float 精度丢失）；ISO → `2026-10-12 08:00:00.000313`；GBK 原样；无表头输出无表头；源带 BOM 才写 BOM；输出再经 `parse_timestamps` 推算 fs ＝ 6400 ±0.2%
- 判读：输出可被播放链路直接读取

**S4 流式正确性与取消**：块大小强制 1000 行、非整数比 3200→7000，流式结果与整文件 `np.interp` 逐点 <1e-6；76800 行文件在 `resample` 阶段取消 → `ResampleError: 已取消`、目录无 `.csv` 也无 `.part`

**S5 REST 后台任务**（`test_api_resample_roundtrip` + jsdom E3/E4/E6）：preview 给出正确 out_name/exists；POST → 轮询 `running→result`，`progress 1.0`，`rows_out 2N-1`；未勾覆盖再跑 → `error 输出文件已存在…`；覆盖 + fft → `rows_out 2N`；fs_new ≤0 / 非数 / method 非法 / out_dir 越界 / 路径不存在 / 缺 path → 均 `ok:false` 带中文原因

**S6 jsdom 端到端 `tools/ui_r8_check.cjs`**：**PASS 29 / FAIL 0**（导航项、下拉填充与选中填路径、输出名预览、探查显示 9600 行与 3200.001 Hz、POST 载荷无空值、进度条 100%/done、文件真实写入 data/、表头原样、时标 `0/00/00 12:40:00.0000/0002`、插值中点值 4.900857、下拉自动刷新、已存在提示、覆盖保护失败标红、fft 覆盖成功、用作播放源切页填值、非法参数提示）；旧 harness 复跑 r7 39/0、r6 30/0、dropdown 74/0；全量 **222 passed, 1 skipped**

**S7 CLI**：`cli.py resample "<用户文件名>" --fs 6400 --method fft` → `✓ 已写出 …_re_6400.csv（5.055 MB）行数 32000 → 64000 …`；输出已存在未加 `--overwrite` → 退出码 2 + `✗ 重采样失败：输出文件已存在`

### 本轮修复/发现的问题
| 编号 | 现象 | 处理 | 状态 |
| --- | --- | --- | --- |
| F-24 | fft 首版按 `(N-1)·fs_new/fs_src+1` 取输出点数，与频域重采样的**周期语义**不符，整周期信号误差 4.9 | 改为 `round(N·fs_new/fs_src)`，比例非整时实际采样率写入 notes；误差降到 1e-6 | ✅ |
| F-25 | 整数毫秒 epoch（1.8e12）直接 float 加 0.15625 丢精度（得 0.1599） | 时标整数部分与小数偏移分开累加 | ✅ |
| F-26 | `detect_encoding` 对纯 UTF-8 报 `utf-8-sig`，输出被加上源文件没有的 BOM（jsdom 表头断言失败） | 只有源文件真的以 BOM 开头才写 BOM | ✅ |
| F-27 | 失败/取消后残留 `<out>.csv.part` | 统一 `try/except BaseException` 删除半成品 | ✅ |
| F-28 | jsdom 轮询拿到**上一任务**的终态（竞争） | 以 `started_at` 变化判定本次任务终态 | ✅（测试侧） |

### 用户执行命令（U8 组：浏览器手点，🔶待回报）
1. 左侧「🧮 数据处理」→ 下拉选一个真实采集文件（或手填绝对路径）→ 「探查源文件」：记录行数、首个时间戳、推算采样率
2. 目标采样率填 6400 → 「开始重采样」：记录进度条是否前进、耗时、结果区行数 N→M、输出文件名是否为 `原名_re_6400.csv`
3. 用 Excel/记事本打开输出文件：表头是否与原文件一致、时间戳写法是否一致、第 2 行时间戳与第 1 行差是否 ≈ 1/6400 s
4. 再点一次「开始」→ 应提示「已存在」；勾「覆盖」选 `fft` → 应成功（大文件注意内存：fft 整文件载入，约 文件行数×7×8 字节 ×3）
5. 「用重采样文件作为离线播放源 →」→ 数据源页把「配置采样率 fs」改为 6400 → 启动 → 顶栏频率 ≈50 Hz、电压电流有效值与原文件播放时一致
6. （可选）真实大文件（≥30 min）linear 重采样：记录耗时与内存（任务管理器）
7. （可选）CLI：`python cli.py resample "<文件>" --fs 6400 --format json`

### 判读要点
- 行数：linear/nearest 为 `floor((N-1)·fs_new/fs_src)+1`，fft 为 `round(N·fs_new/fs_src)`
- 输出再播放时电气量应与源文件播放一致（RMS 偏差 <0.1%，fft 方法 THD 一致；linear 升采样 THD 略低属正常——线性插值是低通）
- 任何「⚠」notes 都应能解释（降采样无抗混叠 / 指定原采样率与推算偏差 / fft 比例非整）

### 结果回收格式
```
U8-1 探查：行数=____ 首时标=____ 推算fs=____
U8-2 重采样：耗时=____s N→M=____→____ 输出名=____
U8-3 文件：表头一致 Y/N 时标写法一致 Y/N 相邻差=____
U8-4 覆盖保护：已存在提示 Y/N；fft 覆盖成功 Y/N 内存峰值=____
U8-5 播放：fs=6400 后频率=____ Ua_rms=____（原文件=____）
U8-6/7（可选）：____
```

### 结果 / 结论
- **沙盒侧（✅已复现）**：功能实现并通过三层验证——16 项 pytest、29 项 jsdom 端到端、旧 143 项 harness 无回退；全量 **222 passed, 1 skipped**。
- **用户侧（🔶未获实录，不下结论）**：真实采集文件（真实时标抖动/缺口/编码）、大文件耗时与内存、Windows 路径与中文文件名。
- **是否进入 REPORT.md（稳定结论）**：**是**——C-18（重采样时间轴按等间隔原采样率重建、时标按源写法重生成；fft 周期语义与 linear 的抗混叠边界）。
- **遗留问题**：
  1. 原始文件若有**缺口**（时标跳变），等间隔假设会把缺口「压掉」（输出按行数连续）；需要保缺口请先按缺口切分；
  2. `fft` 整文件载入，内存约 `行数×7×8 B×3`；超大文件请用 linear 或后续加分段重叠 FFT；
  3. 只支持单文件；目录批量可用 CLI 循环；
  4. 重采样不改配置 `sampling.fs`，播放前需手动改为目标值（「用作播放源」按钮已提示）。

---

## [2026-10-13] 专题 T-007：第 9 轮 间谐波 / 直流偏置 / 事件 子界面
- 类型：用户专题（实现＋验证）
- 目标与假设：用户原话「1.增加计算的间谐波电气量子界面 2.增加计算的事件子界面(包含基波相量超限事件、谐波相量超限事件、间谐波相量超限事件、频率超限事件、频率变化率超限事件和功率振荡事件) 3.增加计算直流偏置电气量」。用户跳过澄清 → 按推荐路线实现并把**假设与可配置项**写入 README §3.1「间谐波 / 直流偏置 / 事件」：间谐波＝IEC 61000-4-7 分组（10 周波窗、组/中心子组/主导相量/TIHD）；直流＝整周期窗均值；事件阈值全部 `events.*` 可配置，默认 110%/90% U_nom、6 A、HR 5/10%、THD 5/10%、IH 1/2%、49.5–50.5 Hz、1 Hz/s、功率振荡 0.1–2.5 Hz 峰峰 5%。
- 方法 / 数据 / 参数：沿既有扩展点（`QUANTITY_KEYS`→窗→`_compute_quantity`→`_EXTRACTORS`→前端）加两量；新建 `elec_tool/events.py`（状态机 + CSV）挂在引擎 `_write_realtime` 之后；三层验证：pytest 13 项（解析解）、jsdom 28 项（真实页面打真实服务端 + 样例 CSV）、旧 harness 复跑。
- 执行模式：混合——沙盒侧（A）✅已实录；用户侧（B）＝U9 组浏览器点检 🔶待回报。

### 沙盒侧实录（三件套：命令 + 输出 + 判读）✅

**S1 间谐波解析解（`interharmonic_analysis`，0.2 s=10 周波，fs 6400）**
- 命令：`x = 100√2 sin(2π50t) + 2√2 cos(2π175t+0.3) + 1.5`，`interharmonic_analysis(x, 6400, 50, 50, n_cycles=10)`
- 输出：`Δf=5.0 Hz`、每组 9 bin、50 组；第 3 组（150~200 Hz）`rms=1.9999999999999967`、`subgroup_rms` 同、`dom_freq_hz=175.0`、`dom_angle_deg=17.18873385392433`（=0.3 rad）、`pct=2.0`；`TIHD=2.0%`；其余组 <1e-9；1 周波窗 → 全 0 + 提示「窗长仅 1 个周波…」
- 判读：组有效值/相量/TIHD 与注入值一致到 1e-14 量级；去直流后 0 组不受 1.5 V 偏置污染

**S2 直流偏置解析解（`dc_analysis` 与 `_q_dc`）**
- 输出：`x=57.7√2 sin + 0.3√2 sin(5ω) + 1.25` → `dc=1.25`、`dc_pct=2.1664%`、50 个周期均值 std<1e-9；三相 `dc_u=(0.3,−0.2,0.1)`、`dc_i=(0.1,0.2,0.3)` → `u_dc` 逐相精确、`in_dc=0.6`
- 判读：整周期均值即直流，无偏；中性线直流＝三相之和

**S3 事件状态机（`EventDetector`，合成 4 块 1 s）**
- 输入：正常 → (U1=70 V、175 Hz 2 V、I 5 次 0.6 A) → (U1=72) → 正常
- 输出：开始 `fund_phasor U1-{A,B,C}-high`（limit 63.514）、`harm_phasor THD_I-*/HR_I-*-h5`（12% > 10%）、`interharm IH_U-*-g3`（2.857% > 1%，detail 含「主导 175.0 Hz」）；第 3 块峰值更新到 72；第 4 块全部 `ended`，`duration_s=2.000`；CSV `events_20261009.csv` 2×N 行（start/end），UTF-8-BOM
- 频率：50→50.8→52→50：`freq f-high` 开始于 50.8（>50.5），`rocof` 开始于 1.2 Hz/s、峰值 2.0、复归；频率滞回带 0.05 Hz（绝对带）
- 判读：6 类中 5 类命中；见 F-29/F-30 两处首版缺陷

**S4 功率振荡**
- 输入：P 以 0.5 Hz、±10% 调制，power 窗 0.5 s，评估窗 6 s
- 输出：`dom_freq_hz=0.4615`（6 s 窗分辨率 0.167 Hz）、`amp_pp_pct=19.4`（理论 20）、事件 `power_osc P active`；调制消失后 `ended`
- 判读：hann 窗 + 短评估窗下频率/幅度在容差内；默认 power 步长 1 s 时 Nyquist 0.5 Hz（README 已写明如何提高）

**S5 PT/CT 折算**
- 输出：`transform.enabled=true`（PT 100 / CT 15）时 `effective_limits = {u1_high 6351.4 V, u1_low 5196.6 V, i1_high 90 A}`；二次 57.7 V/5 A 的正常信号不报；6.5 A（一次 97.5 A）→ `I1-*-high`
- 判读：首版未折算 → 真实样例一开机就 6 条基波超限（F-29）

**S6 Web/REST/WS（live preview 8000 + `data/sample_6400hz.csv`）**
- 输出：`/api/config.windows` 含 9 键；`/api/result` 新量 ok；`/api/events` 摘要 `counts={harm_phasor:12}`（样例 8% 3 次 / 6% 5 次 → THD_U/HR_U-h3/HR_U-h5 ×3 + THD_I ×3，与 `harmonic` 页 THD 10.6% 一致）；`PUT /api/config {events:{thd_u_limit_pct:20,…}}` 后 3 s 内 12 条全部 ended（F-30 修复后）；`POST /api/events/clear` → `removed=12`；`/api/history/dc` 有点
- jsdom `tools/ui_r9_check.cjs`：**PASS 28 / FAIL 0**（N1 三子界面卡片/表/趋势请求、N2 窗口页两行 FFT 类且 dc 不去直流、N3 事件页 6 类卡片/折算卡片/历史与活动表/徽标/类型过滤、N4 表单回填→改阈值→PUT 载荷→热更新→复归、N5 清空）

**S7 回归**
- `pytest tests -q`：**235 passed, 1 skipped**（含新 13 项；旧测试按 7→9 量、6→8 曲线更新：conftest/selftest 用 `QUANTITY_KEYS`、test_server 计数、test_r6 保存集合、test_r7 文件数与 fmtTip 计数）
- `cli.py selftest`：44/44，最差 1.508e-05（不变）
- 旧 harness：dropdown **74/74**、r6 **30/30**（6→8 曲线断言已更新）、r8 **29/29**、r7 **38/39**——失败项「摘要显示『播放起点』与跳过行数」在 `git stash` 回到改动前的前端下同样失败，属 jsdom 桩掉 WebSocket 后 `src-summary` 不再被 state 推送刷新的时序问题，与本轮改动无关，留作 F-31 观察

### 本轮修复/发现的问题
| 编号 | 现象 | 处理 | 状态 |
| --- | --- | --- | --- |
| F-29 | 基波阈值按二次侧默认值（57.74 V / 6 A）直接与**一次值**结果比较 → 真实样例一开机 6 条基波超限 | `EventConfig.limits_secondary`（默认 true）：启用 PT/CT 时阈值自动 ×PT/×CT；摘要回传 `effective_limits/limit_scale`，界面卡片显示 | ✅ |
| F-30 | 复归按**事件记录的旧阈值**判，用户把阈值抬高后旧事件永远挂着 | `_release(limit=当前阈值)`；并把频率滞回从「limit×0.95」改为绝对带 `(1−h)×(f_high−f_low)`（否则 50.5×0.95=47.98 永不复归） | ✅ |
| F-31 | `ui_r7_check` 1 项（播放起点摘要）在 jsdom 下失败，改动前后一致 | 判为测试时序（WS 桩），未改产品代码 | 🔶观察 |
| F-32 | （用户回报 2026-10-13）开启事件检测、事件很多时，每条事件都在右下角弹 toast，界面被刷屏 | `app.js onEventPush` 去掉逐条 toast；事件到达只更新导航徽标（活动数）并刷新「事件」页表格；回归断言加入 `test_frontend_has_new_views_and_wiring`；`ui_r9_check` 复跑 28/28 | ✅ |
| — | `sampling.adaptive_freq=false` 时频率恒为额定 → 频率/ROCOF 事件永不触发，且偏频下谐波/间谐波泄漏虚高 | 事件摘要 `notes` 给出提示（出厂 `configs/default.json` 为 true） | ✅ |

### 用户执行命令（U9 组：浏览器手点，🔶待回报）
1. 启动离线样例 `data/sample_6400hz.csv` → 「🚨 事件」：活动事件是否为 12 条谐波相量超限、导航徽标数字=12、基波相量 0 条；「基波有效阈值」卡片是否显示 `5.197 kV ~ 6.351 kV / I1 ≤ 90 A（×100/×15）`
2. 阈值表单：THD_U/HR_U/THD_I 上限改 50 → 「保存阈值」→ 2 s 内活动表清空、历史表状态「已结束」且有持续时长；改回 5/5/10
3. 「🎚 间谐波」：TIHD 三相 ≈0.24%、柱状图可切换「含有率/组有效值」、相量表每相 10 行；窗口配置页 `interharmonic` 0.2 s
4. 「➖ 直流偏置」：三相 |DC| 与中性线值、逐周期曲线平直；趋势 U/I 切换
5. 真实采集文件播放：记录事件类型分布与数量；若基波大量超限，核对 PT/CT 与 `u_nom`（线电压口径请把 `u_nom` 改 100）
6. （可选）`output/events/events_<日期>.csv` 用 Excel 打开：start/end 成对、时间为数据时间

### 判读要点
- 样例文件应**只**出谐波相量事件；出现基波事件＝PT/CT 或 `u_nom` 口径不符；出现频率事件＝`adaptive_freq` 下估频异常或数据真偏频
- 间谐波含有率 >1% 持续出现＝真有间谐波源（变频负荷）或窗内有暂态/缺口（看 `harmonic`/`voltage` 页 notes）

### 结果回收格式
```
U9-1 事件：活动=____ 类型=____ 徽标=____ 有效阈值=____
U9-2 热改阈值：复归用时=____s 历史状态=____
U9-3 间谐波：TIHD_U=____ 最大组=____
U9-4 直流：Ua_dc=____ In_dc=____
U9-5 真实文件：事件分布=____
```

### 结果 / 结论
- **沙盒侧（✅已复现）**：三项功能实现并通过三层验证——13 项 pytest（解析解到 1e-9）、28 项 jsdom 端到端、旧 harness 无回退（1 项时序观察）；全量 **235 passed, 1 skipped**。
- **用户侧（🔶未获实录，不下结论）**：真实数据下的事件分布、阈值合理性、一次/二次口径。
- **是否进入 REPORT.md（稳定结论）**：**是**——C-19、C-20。
- **遗留问题**：
  1. 事件为单级固定阈值，无持续时间门槛/分级/动态阈值；
  2. 功率振荡只看 P 总，频率上限受 power 步长限制（1 s → 0.5 Hz）；
  3. ROCOF 时间分辨率＝fundamental 步长（出厂 0.2 s），数据缺口跨越时会出现虚假 ROCOF（已用数据时间差做分母，缺口越大值越小，不会误放大）；
  4. IEC 61000-4-7 的 10/15 min 聚合未做。

---

## [2026-10-13] 专题 T-010：第 12 轮 负荷辨识子界面（逐周波事件检测）
- 类型：用户专题（实现＋验证）
- 目标与假设：用户原话「增加负荷辨识子界面：1.尽量多的事件检测算法实时检测窗口内周波数据；2.事件含发生时刻、方向和幅度；3.各算法参数可配置；4.事件保存到 CSV（算法类型、起止时间、方向、幅值）」。假设：事件对象＝逐周波有功 P（total/A/B/C 可选），方向＝ΔP 符号，幅值＝稳态差；不做负荷分类。
- 方法 / 数据 / 参数：`elec_tool/nilm.py`：`CycleFeatures`（128 点周波、跨块结转、基波单频 DFT Q）→ 滚动窗 → 6 算法纯函数 `detect_steps()` → 去重/确认 → `NilmWriter`。合成样例 `tools/gen_nilm_sample.py`（1000 W → +500 W@2.0 s → −300 W@4.4 s，3.0 s 单周波尖峰）。
- 执行模式：混合——沙盒侧（A）✅已实录；用户侧（B）＝U12 组 🔶待回报。

### 沙盒侧实录（三件套：命令 + 输出 + 判读）✅
| # | 命令 | 输出（节选） | 判读 |
|---|---|---|---|
| S1 | 算法层：300 周波合成序列（+500/−300 阶跃、σ=2 噪声、单点 +400 尖峰）跑 6 算法 | threshold (100,101,999,1500) (220,221,1501,1200)；two_window (100,110) (220,230)；cusum (100,100) (220,220)；glr (100,105) (220,225)；steady_state (100,100) (220,220)；median_diff (100,101) (220,221) | 6 种算法起点全部命中 100/220，幅值 ±1%，尖峰均未成事件 ✅ |
| S2 | 引擎端到端 `data/nilm_steps.csv`（PT/CT 默认） | 6 算法 × 2 事件：`08:00:02.000 up 750 kW`、`08:00:04.400 down 450 kW`（ΔQ +363 kvar / −218 kvar，ΔI +83.3 A / −50 A）；two_window 另报 3.0 s 尖峰 60 kW | 时刻精确到周波、方向/幅值正确；双滑窗尖峰特性已在 README 说明 ✅ |
| S3 | `cat output/nilm/nilm_events_20261013.csv` | 表头 `id,algorithm,algorithm_name,channel,t_start,t_start_local,t_end,t_end_local,duration_s,cycles,direction,magnitude_w,delta_p_w,delta_q_var,delta_i_a,pre_p_w,post_p_w,score`，13 行 | 需求 4 四要素（算法类型/起止时间/方向/幅值）齐全 ✅ |
| S4 | `.venv/bin/python -m pytest tests/test_r12_nilm.py -q` | `8 passed` | 算法层 / 相对门槛 / 周波特征精度（P 1e-3、Q 感性为正）/ 引擎+CSV / 跨块去重与禁用 / 配置校验与往返 / REST（热更新深合并、400、播放、过滤、cycles、clear）/ 前端接线 ✅ |
| S5 | `.venv/bin/python -m pytest tests -q` ×4 | `257 passed, 1 skipped` ×3；1 次出现 1 项失败（未捕获到用例名，复跑 3 次未再现） | 无回归；偶发项记 F-39 观察 🔶 |
| S6 | `JSDOM_DIR=/tmp/uitest node tools/ui_r12_check.cjs` | `结果：16 通过 / 0 失败` | 导航/6 算法表单回填/播放后事件表含 6 算法与 ↑↓ 方向与 kW 幅值/周波窗 300 点/算法过滤/PUT 载荷 `nilm.algorithms.glr.threshold=40` 生效/清空与徽标 ✅ |

### 本轮修复/发现的问题
| 编号 | 现象 | 处理 | 状态 |
|---|---|---|---|
| F-38 | 绝对 W 门槛在一次侧（MW 级）失效：threshold/steady_state 的 20/30 W 容差小于 1.5 MW 的周波噪声 → 0 事件；CUSUM 起点因 k=10 W 过小提前 13 周波；噪声触发的起点被「粘」到后面的阶跃 | 新增 `rel_tol_pct`（默认 1%）/`min_delta_pct`（默认 0）按窗内 \|P\| 中位数折算；阈值差分触发量取 max(min_delta/2, 容差)，起点精修到越过 Δ/2 的周波 | ✅ |
| F-39 | 全量测试 4 次中 1 次 1 项失败，未捕获用例名，复跑未再现 | 观察；下轮全量加 `-rf` 输出 | 🔶 |
| F-42 | （用户回报 2026-10-14）离线文件方式下界面「暂停播放」没有生效 | 服务端日志实录：用户每次 `POST /api/engine/pause` 都是 **400**——离线文件此前**不限速**（沙盒实测 16.5k 样本/s ≈ 2.6× 实时），5 s 样例 2 s 就播完，按钮还亮着、点下去已是「已播放完毕」；加上前端看门狗只在「本地认为运行中」时才校对、静态资源无 Cache-Control 可能拿到旧 app.js。修：① `source.file_speed`（csv_file 播放倍速，1＝真实速率、0＝不限速；配置默认 0 保持 CLI/测试行为，**界面默认 1×**），限速按相邻两块间隔计、暂停后恢复不突发追赶；② 看门狗无条件 2 s 校对 `/api/state`；点击置灰原因 toast；③ `/` 注入资源版本号 `?v=<内容哈希>` + `Cache-Control: no-store`，`/static/*` no-cache。验证：`tests/test_r13b_file_speed.py` 4 项（倍速计时 / 恢复不追赶 / 校验与透传 / 版本号与缓存头）、`tools/ui_r13_check.cjs` 12/12（jsdom 走真实界面：选文件 → 启动 → 点暂停样本与数据时刻冻结 → 点恢复继续）；全量 270 passed | ✅ |
| F-41 | （用户回报 2026-10-14）离线文件播放完，界面运行状态不自动更新，需手动刷新 | 根因：引擎线程的终态 `state` 推送发生在 `engine.stop()` **之前**（此时 `engine.running` 仍 True、线程仍 alive），界面收到的终态是「运行中」；之后只靠 WS 1 s 定时 state 兜底，推送链路一旦异常（state() 抛错会让 WS 循环静默退出）就停在旧状态。修：① 终态广播移到 `finally` 的 `engine.stop()` 之后，并以 `_thread_done` 标志让 `state().running` 立即为 False；② WS 定时 state 的 `state()` 异常改为发 `error` 消息而不断开；`state()` 内 `to_dict()`/`history.stats()` 单项失败不拖垮整体；③ 前端增加 2 s 状态看门狗 `startStateWatch()`（运行/暂停期间校对 `/api/state`，到终态弹「离线文件播放完毕」），WS 与轮询两种模式都覆盖。回归 `test_r13_pause.py::test_final_state_broadcast_after_playback_reports_not_running`（旧代码失败：第一条 finished 的 state 带 running=True）；全量 266 passed | ✅ |
| F-40 | （用户回报 2026-10-13，Windows）离线文件（自定义时间）启动后 `GET /api/nilm/events` 500：`time.localtime(t)` → `OSError: [Errno 22] Invalid argument` | 根因：无日期时标 `0/00/00 HH:MM:SS` 基准为 1970-01-01，v0.10 起按本地时间解释（UTC+8 减 8 h）→ **负 epoch**；Linux 的 localtime 接受负值而 Windows CRT 直接报错，沙盒因此没暴露。修法：① `_NO_DATE_BASE` 改 1970-01-02（任何时区偏移后仍为正）；② 新增 `elec_tool/timefmt.py`（`fmt_local/local_day/local_tod_s`：localtime 失败时用 datetime 手工换算），nilm / events / realtime_writer / server 导出与 probe / cli / `_tod_of` 全部出口改走它；③ `tests/test_f40_negative_epoch.py` 3 项用 monkeypatch 模拟 Windows localtime（负值抛 OSError）+ 东八区复现并回归；全量 **260 passed**（UTC 与 Asia/Shanghai） | ✅ |
| — | `test_r7` 的 `fmtTip` 计数硬编码 8 → 9 | 已改 | ✅ |

### 用户执行命令（U12 组：浏览器手点，🔶待回报）
1. `.venv/bin/python tools/gen_nilm_sample.py` → 数据源页播放 `data/nilm_steps.csv` → 「🧩 负荷辨识」：事件表应有 6 算法 × 2 条（2.000 s ↑750 kW、4.400 s ↓450 kW）+ 双滑窗 1 条 60 kW 尖峰
2. 周波窗曲线：对象切 A 相 / 量切 Q、I，竖线落在阶跃处；标注算法下拉只留一种
3. 参数：`min_delta_pct` 填 5 → 保存 → 清空 → 重播：尖峰小事件消失
4. 真实采集文件播放：记录各算法事件数、是否有明显误报/漏报，以及合适的 `min_delta_w`（W，一次侧）
5. `output/nilm/nilm_events_<日期>.csv` 用 Excel 打开核对四要素

### 结果回收格式
```
U12-1 事件数：阈值__ 双滑窗__ CUSUM__ GLR__ 稳态__ 中值__   U12-3 尖峰消失：__
U12-4 真实文件：误报__ 漏报__ 建议 min_delta_w=__
```

### 结果 / 结论
- **沙盒侧（✅已复现）**：6 算法并行、事件四要素齐全、参数全可配、CSV 落盘；pytest 8 项 + jsdom 16 项 + 全量 257。
- **用户侧（🔶未获实录，不下结论）**：真实负荷的噪声水平与合适门槛。
- **是否进入 REPORT.md**：**是**——C-23。
- **遗留问题**：① 只做事件检测（特征＋事件库），无负荷类型分类/聚类；② 周波按额定频率定长切分；③ 双滑窗/CUSUM 的尖峰特性；④ 事件不跨进程持久化（CSV 为准）；⑤ F-39 偶发项待抓。

---

## [2026-10-13] 专题 T-009：第 11 轮 离线文件时标 UTC 开关
- 类型：用户专题（实现＋验证）
- 目标与假设：用户原话「离线文件当使用不启用自定义时间时，增加是否使用UTC时间配置。当不使用UTC时间时，则曲线上数据时间保持和文件中的数据时间一致」。根因：此前文本时标一律当 UTC 解析（`tz_offset_h=0`），界面按浏览器本地时间显示 → 北京时间下曲线比文件多 8 h。假设：默认不按 UTC（与文件一致）；浏览器与服务端同时区；偏移按本机当前时区取。
- 方法 / 数据 / 参数：`source.file_time_utc`（默认 false）→ `parsing.file_tz_offset_h(cfg)`（false＝`local_utc_offset_h()`，true＝0）→ `create_source/LiveEngine` 默认推导；`_parse_slash_clock` 无日期写法同样减偏移、`_seek_time`/`_tod_of` 当天时刻按偏移还原；probe/start/CLI/界面透传。沙盒 TZ 为 UTC，测试用 `TZ=Asia/Shanghai` + `tzset()` 复现 8 h 偏差。
- 执行模式：混合——沙盒侧（A）✅已实录；用户侧（B）＝U11 组 🔶待回报。

### 沙盒侧实录（三件套：命令 + 输出 + 判读）✅
| # | 命令 | 输出（节选） | 判读 |
|---|---|---|---|
| S1 | `.venv/bin/python -m pytest tests/test_r11_file_time.py -q` | `6 passed` | 东八区下 `2026-10-12 08:00:00` 本地显示 08:00:00（false）/ 16:00:00（true）；`0/00/00 00:12:40` → 00:12:40；epoch 两种设置一致；`create_source` 偏移 8/0/显式 3；REST 探查 `t_first_local` 与启动透传 ✅ |
| S2 | `TZ=Asia/Shanghai .venv/bin/python -m pytest tests -q` 与 默认 UTC | `249 passed, 1 skipped` ×2 | 旧用例 `test_r6/r7` 三处把无日期时标当 UTC 的断言改为按本机偏移，双时区全绿 ✅ |
| S3 | 服务端 `TZ=Asia/Shanghai` 起 8000；`curl /api/probe?path=data/clock_0000.csv` | false：`t_first_local 1970-01-01 00:12:40, tz_offset_h 8`；true：`08:12:40, tz_offset_h 0` | 文件 `0/00/00 00:12:40.0000` 不按 UTC 时显示与文件一致 ✅ |
| S4 | `JSDOM_DIR=/tmp/uitest node tools/ui_r11_check.cjs` | `结果：11 通过 / 0 失败` | 勾选框回填/联动（自定义时间开启则灰显）；start 载荷 `file_time_utc` 透传；状态 `tz_offset_h` 8/0；两次 `t_start` 相差 28800 s；摘要显示「与文件一致」✅ |

### 本轮修复/发现的问题
| 编号 | 现象 | 处理 | 状态 |
|---|---|---|---|
| F-36 | `0/00/00` 无日期写法首版未减偏移（仍 08:12:40） | `_parse_slash_clock` 无日期分支同样 `− tz_offset_h×3600`，`_seek_time`/`_tod_of` 的当天时刻按偏移还原 | ✅ |
| F-37 | 旧用例三处隐含「沙盒＝UTC」假设，换时区即失败 | 期望值改为 `tod − tm_gmtoff` | ✅ |

### 用户执行命令（U11 组：浏览器手点，🔶待回报）
1. 「数据源」页：csv_file、不勾选「自定义播放时间」→「文件时标按 UTC 解释」可用且默认不勾选
2. 播放真实文件（时标 `0/00/00 00:12:40.0000` 或带日期）→ 曲线悬停 / 顶栏数据时间 / `output/realtime` CSV `time_local` 与文件时间一致（不再 +8 h）
3. 勾选 UTC → 重新启动 → 时间 +8 h（旧表现）
4. 勾选「自定义播放时间」→ UTC 勾选框灰显
5. 播放起点 `time:00:13:00` → 从文件时标 00:13:00 开始

### 结果回收格式
```
U11-2 文件时标=____ 界面时间=____ realtime CSV time_local=____
U11-3 勾选 UTC 后界面时间=____
```

### 结果 / 结论
- **沙盒侧（✅已复现）**：pytest 6 项 + 双时区全量 249 + jsdom 11 项 + REST 实录。
- **用户侧（🔶未获实录，不下结论）**：用户 Windows 机器时区与浏览器时区是否一致。
- **是否进入 REPORT.md**：**是**——C-22。
- **遗留问题**：① 浏览器与服务端不同时区时界面仍按浏览器时区显示；② 偏移按当前时刻取，跨夏令时的历史文件可能差 1 h（中国无夏令时）；③ 默认值由「当 UTC」改为「当本地」，已部署用户若依赖旧表现需勾选 UTC。

---

## [2026-10-13] 专题 T-008：第 10 轮 离线文件列映射开关
- 类型：用户专题（实现＋验证）
- 目标与假设：用户原话「修改代码，增加是否启用离线文件数据映射关系配置功能。如果没有启用，默认依次为时间,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流；否则，只播放有有映射关系的列数据」。假设（用户未另行澄清）：未映射通道按 0 播放而非剔除；未启用时可识别表头仍按表头（兼容既有文件）；时间戳未映射按 fs 合成时间轴；TCP 源不在范围。
- 方法 / 数据 / 参数：`ColumnMap` 新增 `mapping_enabled/mapping` + `layout()/looks_like_header()/validate()/unmapped()`，`parsing._rows_to_block/_assemble/iter_csv_blocks/_seek_time`、`server /api/probe`、`cli sources --file`、`resample._prescan` 全部改走 `layout()`；前端「数据源」页新面板。合成 CSV（U 57.7 V，I 5/6/7 A 区分三相）做解析解断言。
- 执行模式：混合——沙盒侧（A）✅已实录；用户侧（B）＝U10 组浏览器点检 🔶待回报。

### 沙盒侧实录（三件套：命令 + 输出 + 判读）✅
| # | 命令 | 输出（节选） | 判读 |
|---|---|---|---|
| S1 | `.venv/bin/python -m pytest tests/test_r10_colmap.py -q` | `8 passed` | 默认列序 / 表头乱序按表头 / 列号+列名混填 / 未映射置 0（`max|u_b|==0`）/ 无时间戳 3 块时间轴 `diff==1/6400` 连续 / 表头判定 / 校验 4 类报错 / REST 端到端 `rms A=5770 B=0 C=0` ✅ |
| S2 | `.venv/bin/python -m pytest tests -q` | `243 passed, 1 skipped` | 旧 235 项无回退（`test_config` 的 `resolve` 用例保持不变）✅ |
| S3 | `JSDOM_DIR=/tmp/uitest node tools/ui_r10_check.cjs` | `结果：15 通过 / 0 失败` | M1 回填与禁用态；M2 启用/默认列序/按探查表头填入（`ua=A相电压`）/探查输出 `[1] 时间戳`；M3 PUT 载荷 `columns.mapping_enabled=true, ub=''` 且服务端生效；M4 探查显示「启用 columns.mapping」「未映射不播放：B相电压…」；M5 播放样例 notes 含「未映射」、`rms {A:5805.7,B:0,C:0}`、刷新后表单保持 ✅ |
| S4 | `curl PUT /api/config {"columns":{"mapping_enabled":true,"mapping":{"ub":"","ib":"","uc":"","ic":""}}}` → `GET /api/probe?path=data/sample_6400hz.csv` | `"columns":{"timestamp":0,"ua":1,"ia":2,"ub":null,…},"mapping_enabled":true,"unmapped":["B相电压","B相电流","C相电压","C相电流"]` | 探查接口回显映射与未映射字段 ✅ |

### 本轮修复/发现的问题
| 编号 | 现象 | 处理 | 状态 |
|---|---|---|---|
| F-33 | 时间戳未映射时每块时间轴都从 0 起（`iter_csv_blocks` 分块调用 `_rows_to_block`，首版只在尾块传了行偏移） | 增加 `row_offset` 跨块累计，t = 行号/fs；S1 用例断言 3 块 `diff` 恒等 1/fs | ✅ |
| F-34 | 未启用映射时，表头列名识别不出（如 `ts,Ia,Ua,junk`）会把表头当成一行坏数据（v0.8 既有行为） | `looks_like_header()`：识别不出名字但第 2~7 列有非数值 → 仍判表头跳过 | ✅ |
| F-35 | `app.js` 拼接 id `'#cfg-map-' + k` 触发 `test_appjs_only_references_existing_element_ids`（既有陷阱） | 改 `` getElementById(`cfg-map-${k}`) `` | ✅ |

### 用户执行命令（U10 组：浏览器手点，🔶待回报）
1. 「数据源」页 → 「离线文件列映射」面板：默认不勾选、7 个输入灰显并显示 1~7
2. 不启用：播放真实采集文件（表头 `时间戳,A相电压,…`）→ 结果与 v0.8 一致
3. 勾选启用 → 「探查数据」→ 「按探查表头填入」→ 清空 B/C 四项 → 「保存配置」→ 再「探查数据」应显示「未映射不播放：B相电压、B相电流、C相电压、C相电流」
4. 启动播放 → 电压/电流页 B、C 相为 0，数据源状态 notes 有「列映射：未映射字段 …」
5. 列号写法：7 个字段填 `1,4,5,2,3,6,7`（把 B 相数据当 A 相）→ 播放后 A 相电流应≈原 B 相
6. 时间戳留空 → 保存 → 播放：时间轴从 0 起按 6400 Hz 递增；「数据处理」页重采样应报「需要时间戳列」

### 判读要点
- 启用映射后仍有 B/C 相数值 ＝ 配置未保存或播放未重启（映射对下次启动生效）
- 保存时 400「columns.mapping …」＝校验失败，看提示（列号 <1 / 重复 / 无通道 / 列名不在表头）

### 结果回收格式
```
U10-1 默认面板：____    U10-3 探查提示：____
U10-4 B/C 相为 0：____  U10-5 列号交换：Ia≈____  U10-6 无时间戳：____
```

### 结果 / 结论
- **沙盒侧（✅已复现）**：开关与映射规则按用户口径实现；pytest 8 项 + jsdom 15 项 + REST 实录；全量 **243 passed, 1 skipped**。
- **用户侧（🔶未获实录，不下结论）**：真实文件的列名/列序是否需要映射。
- **是否进入 REPORT.md（稳定结论）**：**是**——C-21。
- **遗留问题**：① 未映射通道按 0（非剔除），三相派生量会把该相当 0 参与；② 映射对运行中的源不热切换（需重启数据源）；③ TCP 源字段顺序仍走 `struct_fields`；④ `csv_tail` 按位置用 `parse_rows`→`layout(None)`，表头名映射在追加模式下不解析表头（只认列号）。

---

## 🗒 变更记录
- v0.79（2026-10-23）：`ui_r76_check.cjs`：瞬时波形图例 `P Q S Pa Qa Sa Pb Qb Sb Pc Qc Sc` 与趋势图图例集合相同、卡片含 A/B/C 相 P/Q/S、默认 3 条、勾 Pa / 去 Q 后 series_hidden 同步，ALL PASS；全量 pytest 首跑 1 项偶发失败（环境重建后首跑，重跑两次均 381 passed）。
- v0.78（2026-10-23）：`ui_r76_check.cjs` 复跑：瞬时波形图例 12 复选框（趋势图亦 12）、默认勾总 P/Q/S 画 3 条、勾 A 相 P / 去总 Q 后隐藏集合与 `output.series_hidden[p-wave]` 同步、A 相 s≥|p| 逐点、说明段 `display:block`；ALL PASS。注意：实录会把勾选状态写进配置，脚本开头已清 `series_hidden[p-wave]`。
- v0.77（2026-10-23）：联动面板重排后回归 `ui_r70_check.cjs`（按保存值填充 / 取消勾选不保存直接启动 / 预览按界面值 / 分路侧配置不被改写）8/8 ALL PASS；pytest r14 / r17 分路相关 20 passed。
- v0.76（2026-10-23）：电气量页实录（8035，`data/nilm_bus_mixed.csv` 播放后、内存造 1 个负荷辨识事件）：三页趋势图 3 条 × marks=0、周波窗（有效值）装载后 3 条 × marks=0、标题无「右键 / 竖线」字样、周波窗两列同 grid2 等宽；功率页 `#p-wave-ph` 已移除、12 勾选框默认总 P/Q/S 画 3 条、勾 A 相 P / 去总 Q 后 3 条且点数一致、A 相有功均值 559.6 kW < 总 1680.0 kW、A 相 s(t) ≥ |p(t)| 逐点成立、全取消空态。pytest `test_v76_instantaneous_q_s_series`（6400 Hz、φ=60°：lag=32 点，mean p≈UIcosφ、mean q≈UIsinφ 误差 <1 W/var）。
- v0.75（2026-10-23）：「保存配置只改变化项」实录（8034 临时服务，`ELEC_TOOL_CONFIG_PATH=/tmp/cfg75/runtime.json`、`ELEC_TOOL_BRANCH_CONFIG_PATH=/tmp/cfg75/branch_runtime.json`，两文件由 default.json + `my_custom_note` 生成、4 空格缩进）：修前第一轮 18 项失败（不改值点 btn-src-save 补写 columns.mapping.*、btn-ev-save 补写全部 events.*、btn-nilm-save 补写 nilm.algorithms.*、btn-save-cfgfile 补写 branch.* / events_dir / nilm_dir 等、btn-save-win 把 step_s null→数字、btn-rt-save-br / btn-save-cfgfile-br 写 output.source_id）；修后 17 按钮 ALL PASS，最终文件只多 `transform.pt_ratio/ct_ratio`、`columns.mapping.ua`、`events.u1_high_pct`、`nilm.rel_tol_pct`、`branch.time_offset_s` 等被改项，自定义键与缩进原样。pytest `tests/test_r63_persist.py` 8 passed。
- v0.74（2026-10-23）：保存配置文件完整性检查实录（TestClient + 8033 UI）：修前 `source.path=x.csv`、`nilm.channels=[total]`（选的是 C）、`source.custom_time=false`（已启用）、`_tuning` 无 min_load；修后 `source.path=data/nilm_bus_mixed.csv`、`channels=[C]`、`custom_time=true/2026-01-01 00:00:00`、`_tuning.params.min_load_used=2.5`，`AppConfig.load` 可加载，等价命令 `--config nilm_tune_base.json … --apply --out` 复现；全量 378 passed / 1 skipped。
- v0.73（2026-10-23）：`ui_r72_check.cjs` 追加自定义时间 7 项：勾选显示自定义起止、占位改写；自定义起始 2026-01-01 00:00:00 + 起止全空 → `whole_file`、64000 点 / 6400 Hz ＝ 10.000 s、`file_t_start`＝自定义起始；`00:00:01→00:00:03` ＝ 100 周波；`zz` → 400；命令含 `--custom-time --custom-time-start`；沿用某侧时基准分组整体禁用显示该侧值、切回还原，**ALL PASS**；CLI `tools/nilm_tune.py --custom-time …` 100 周波 / 10.0 s 与界面一致；全量 377 passed / 1 skipped。
- v0.72.2（2026-10-23）：`ui_r72_check.cjs` 追加 5 项（分路侧运行配置设 p / B）：独立基准下检测量 / 检测对象可编辑并按 i / C 计算；沿用分路侧 → 两项禁用、显示 p / B、请求 quantity/channel 为 null、结果 p / B；切回独立基准还原 i / C，**ALL PASS**；pytest 新增 running 模式忽略请求 quantity/channel、I+total 退回 A；全量 375 passed / 1 skipped。
- v0.72（2026-10-23）：第 93 轮沙盒侧实录——`tools/ui_r72_check.cjs`（jsdom 打 8033，`ELEC_TOOL_CONFIG_PATH=/tmp/cfg72/runtime.json`、`ELEC_TOOL_NILM_DIR=/tmp/out72/nilm`）**ALL PASS**：独立基准初值＝出厂（PT 100 / CT 15 / fs 6400）而非总线侧 PT 123；改 PT=77 + 关 PT/CT → 请求 `base_mode=custom`、结果 `scaled=false`、`--config …/nilm_tune_base.json`、两侧运行配置不变；填入总线侧 / 分路侧值、恢复出厂；沿用分路侧 → `/api/branch/process/nilm_tune`、`base.ct_ratio=5`；独立基准 + 套用目标分路侧 → 分路侧 nilm 更新、CT 仍 5。CLI `tools/nilm_tune.py --config output/nilm/nilm_tune_base.json` 与界面 level=1155001.2003 / sigma_cycle=22.3624 完全一致。全量 374 passed / 1 skipped。用户侧：浏览器手点独立基准配置 → 调参 → 套用，**🔶待回报**。
- v0.71（2026-10-23）：第 92 轮沙盒侧实录——`tools/ui_r71_check.cjs`（jsdom 驱动真实页面打 8032 服务端，csv_file 源 `data/nilm_bus_mixed.csv`）**ALL PASS**：三视图趋势 3 条 × 11 点、右键菜单键序 `copy-image,save-image,open-image,show-window,show-window2,zoom-reset,native!`、周波窗（有效值）`/api/elec/cycles_file?n=300&t=中心` 3 条 × 300、周波窗（瞬时值）`/api/nilm/wave_file` 3（6）通道 × 38400 点、两图同段、清除 / 手动装载（空＝起点起 50 周波）、模拟器源两项灰显 + 装载禁用、分路侧右列独立装载 40 周波；pytest 新增 `test_elec_cycles_file_matches_nilm_cycles`；全量 373 passed / 1 skipped。用户侧：浏览器手点三子界面右键 → 周波窗，**🔶待回报**。
- v0.11.1（2026-10-13）：T-010 追加 **F-40**（用户 Windows 回报：无日期时标按本地解释后为负 epoch → localtime OSError → 负荷辨识接口 500；基准改 1970-01-02 + 统一安全格式化出口 `timefmt`；全量 260 passed）。
- v0.11（2026-10-13）：追加专题 **T-010**（第 12 轮：负荷辨识子界面·逐周波事件检测）：S1~S6 实录、F-38~F-39、U12 组执行包。
- v0.10（2026-10-13）：追加专题 **T-009**（第 11 轮：离线文件时标 UTC 开关）：S1~S4 实录、F-36~F-37、U11 组执行包。
- v0.9（2026-10-13）：追加专题 **T-008**（第 10 轮：离线文件列映射开关）：沙盒侧 S1~S4 实录、F-33~F-35、U10 组执行包。
- v0.8（2026-10-13）：追加专题 **T-007**（第 9 轮：间谐波 / 直流偏置 / 事件 子界面）：沙盒侧 S1~S7 实录、F-29~F-31、U9 组执行包。
- v0.7（2026-10-12）：追加专题 **T-006**（第 8 轮：数据处理子界面——离线波形 CSV 重采样）：沙盒侧 S1~S7 实录、F-24~F-28、U8 组执行包。
- v0.6.2（2026-10-12）：T-005 追加 **F-23**（用户回报：离线播放时顶栏样本汇总不自动刷新＝WS state 只在队列空闲时下发；已修＋回归，全量 206 passed）。
- v0.6.1（2026-10-12）：T-005 追加 **F-22**（用户回报：IP 访问时页面纵向无限拉伸＝画布高度按 devicePixelRatio 复利放大，已修＋回归；全量 205 passed）。
- v0.6（2026-10-12）：追加专题 **T-005**（第 7 轮三功能：曲线实时落盘 / 离线文件指定位置播放 / 曲线悬停取值）：沙盒侧 S1~S4 实录三件套（源层五种定位、CLI、18 项 pytest、39 项 jsdom＋旧 harness 复跑）、问题 **F-17~F-21**、用户侧 **U7 组**（浏览器手点 8 步）＋判读 J-U7a~c＋回收格式。索引新增 T-005 行。
- v0.5（2026-10-12）：追加专题 **T-004**（第 6 轮四功能：用户时标格式 `0/00/00 00:12:40.0000` / 24h 趋势曲线 / 逐曲线「保存曲线」开关 / 离线自定义播放时间）：沙盒侧 S1~S9 实录三件套（修复前基线、解析器取证、CLI/源层/REST/界面端到端、History 24h 性能与并发、全量回归 186 passed）、缺陷 **F-11~F-16**、用户侧 **U6 组**（浏览器手点 8 步）＋判读 J-U6a~c＋回收格式。索引新增 T-004 行。
- v0.4（2026-10-10）：T-003 追加 **Web 界面下拉框专项检查**：沙盒侧实录 S14~S18（jsdom 驱动真实页面打真实服务端 `PASS 74 / FAIL 0`、帧格式联动与脏值保护、口径三下拉框 PUT 回显、空值语义 REST 实录、前端契约测试「撤销修复必 FAIL」验证）、缺陷 **F-06~F-10**（两个源下拉框无联动／载荷无条件发送空值／空数字框导致保存必 400／实时推送覆盖用户正在编辑的表单／启动按钮夹带被服务端忽略的配置段）、能力补齐（`#src-hint`+`#src-formnote`+置灰视觉、`tools/ui_dropdown_check.cjs`、`tests/test_web_ui.py` 14 项）、用户侧 **U 组**（浏览器手点 7 步）＋判读 J-U1~J-U4＋回收格式。测试 147→**161 passed, 1 skipped**；S-W2 期望值同步更新。索引行升格为「F-01~F-10」「5 条稳定结论」
- v0.3（2026-10-10）：追加专题 **T-003**（四种数据源的配置·运行·验证）：沙盒侧 S1~S13 实录三件套、四源横向对账表（同源四路 P 极差 0.013%、U1 偏差 ≤0.70‱、THDu 偏差 ≤0.005 百分点、缺口 0）、本轮实测发现并修复的 **F-01~F-05**（目录分片切换丢一整块／坏帧格式崩 OverflowError／告警刷屏且 live 收尾不打印源告警／float32 存 epoch 秒无告警／前端 collectSourcePayload 死代码）、能力补齐（`cli.py live --frame/--struct-fmt/--struct-fields`、界面 TCP 两字段、`tools/` 三件套＋5 项防腐测试）、用户侧 **S 组（无硬件可复现）与 D 组（真实装置/协议）** 执行包＋J-* 判读＋回收格式。测试 141→**147 passed, 1 skipped**。T-001/T-002 状态不变（仍待回报）
- v0.2（2026-10-10）：追加专题 **T-002**（电气量计算工具实现自验证 + 本地部署与真实数据验收执行包）：沙盒侧 A1~A10 实录三件套、本轮修复的两个真 bug（B1 引擎线程换代竞争导致双重摄入、B2 整周期窗少算一个周期）、用户侧 W/R/P 三组模式 B 执行包与 J-* 判读要点、结果回收格式；专题索引与 T-001 状态保持不变（仍待回报）
- v0.1（2026-10-10）：创建台账骨架 + 条目模板 + 专题索引；登记待归档专题 T-001（模式 B 执行包：E-0 环境说明 / A~D 四组只读命令 / 预期输出样例 / J-* 判读要点 / 结果回收格式）。⚠️ 本条**尚无结果**，等用户实录回报后追加三件套，不新建文件
- v0.80（2026-10-23）：`test_r12_nilm.py::test_estimate_min_load_splits_primary_and_secondary_steps`（7.5↔26.5 A + 0.6 A 二级波动 → split、primary≈19、reliable=False；无二级波动 → 不分簇仍可靠；三档 300k/450k 不分簇；`detect_repetition` 60 s 模板 ×5 → suspected/period 60、真实噪声与过短序列不告警）、`::test_run_tune_reports_repetition_and_estimate_fields`（结果含 `repetition`；2 s 波形复制 3 次的 CSV → period 2.0 + notes 告警）；`tools/ui_r80_check.cjs` 实录：分簇文案 / 下拉默认主负荷 / 三种填入 / 拼接提示 ALL PASS；全量 383 passed / 1 skipped。
- v0.81（2026-10-23）：`tests/test_r81_cfg_load.py` 6 项（`/api/config/file` 两侧默认路径；加载 other.json → PT=123 热更新、source_id 仍 0、文件未改、分路侧不受影响；persist=true 只写差异 `transform.ct_ratio`，sampling/columns/source/windows/harmonic/power 不变；分路侧空路径＝branch.json、source_id=1、总线侧不受影响；不存在 / 非 JSON / 非对象 / fs=0 均 400 且运行配置不变；界面元素与 JS 引用）；`tools/ui_r81_check.cjs` 实录 7 项 ALL PASS；全量首跑 1 失败（`test_appjs_only_references_existing_element_ids`：动态拼接 `'#btn-' + pre` 被扫成不存在的 id，改为显式两个 id 后通过）→ 389 passed / 1 skipped。
- v0.82（2026-10-23）：`tests/test_r82_playback_perf.py` 3 项（按列快路径与逐单元结果相等、坏单元/空单元/短行回退计数不变；`_parse_slash_clock_block` 与逐值解析一致（带日期逐位、无日期 <1e-9）、混入非骨架/数值/小数段非数字返回 None、跨午夜展开；`engine.run` 64000 样本 <6 s）；旧实现对比脚本：interharmonic（nc=1/3/10/50）、spectrum（抽稀/不抽稀）、rms_per_cycle（f=50/49.85/50.2）、_jsonable（14 种类型组合）输出相同；服务端 cProfile：引擎线程 4.94 s → 2.39 s（to_dict 2.36 s → 0.6 s → 再到 ~0.3 s）。基准：库 10 s 数据 5.48 s → 0.81 s；服务端 120 s 文件 21.1 s → 13.2 s；两侧同播 6.5 s → 2.6 s（10 s 数据）。全量 392 passed / 1 skipped。
- v0.83（2026-10-26）：`tests/test_r83_repeated_cycles.py` 5 项（周波复制序列 repeat_frac>0.95 / run=50 / sigma_raw<1e-6 / σ∈(0.003,0.02)；真实白噪声序列 sigma_method=diff_mad 且与 sigma_raw 相等；`longest_transient(run_cycles=50)` 量到 1800–2600 周波且大于不折算结果；`suggest` 的 steady_state 参数经 `detect_steps` 检出 ≥+1.2 A 起动与 ≤−1.2 A 停机；`estimate_min_load(run_cycles)` 稳态段 ≤12、最大台阶≈1.4 A）；CLI `tools/nilm_tune.py --file`（6400 Hz 模板复制 CSV，75 s）打印周波复制告警并给出 window_cycles=1900。全量 397 passed / 1 skipped。
- v0.83.1（2026-10-26）：`test_measure_blocky_with_in_second_jitter`（秒内 6e-7 抖动 / 35% 逐位相等：repeat_frac<0.5 仍判 block、run=50、σ_1<2e-6、σ∈(0.003,0.02)、suggest 的 steady_state 检出 ±1.2 A 以上起停、稳态段 ≤12）；白噪声序列 sigma_lags 1…100 全部 ≈0.01、method=diff_mad。全量 398 passed / 1 skipped。
- v0.83.2（2026-10-26）：`test_ramp_plateau_not_taken_as_steady_anchor`（含 6 s 回落平台的 46 s 斜坡：暂态 ≥2300、max_transient ≥3400、window ≥ max_tr+2×min_steady、steady_state 检出 ±1.2 A 以上起停；用户第 108 轮参数 max_tr=2000/window=2500 在同一序列为 0 事件）。全量 399 passed / 1 skipped。
- v0.84（2026-10-26）：`tools/ui_r84_check.cjs` 8 项（总线侧列出可点击 CSV、两侧项数文本一致、只含 .csv、显示 MB、点击填入 #src-path / #br-path、S.formDirty&srcDirty、BR.dirty）ALL PASS；pytest test_frontend_contract / test_r12_nilm 通过。
- v0.87（2026-10-27）：`tests/test_r87_nilm_auto.py` 6 项（window_stats 白噪声 σ≈80/hold=1/transient 覆盖 20 周波斜坡、6 算法各 2 事件 0 虚警、threshold/steady/median 幅值 ±12 kW、<60 周波返回 None；秒值×50 模拟 hold=50、σ∈(0.006,0.012)、steady_state 仅 ±1.4；NilmDetector 自适应 vs 手填荒谬值 vs 分路侧 vs 算法停用；配置往返；run_tune 含 auto_params；API PUT 两侧 + summary；前端接线）；`tools/ui_r87_check.cjs` 11 项 ALL PASS。全量 411 passed / 1 skipped。备注：双窗/GLR/CUSUM 的 score 口径与稳态差不同，斜坡事件只断言起点与计数。
- v0.88（2026-10-27）：`tests/test_r87_nilm_auto.py` 改为两侧用例（分路侧 source_id=1 + 自适应 ⇒ 6 算法事件集合/数量与总线侧一致、notes 含「自适应算法参数已启用（分路侧）」；`/api/branch/config` PUT auto_params=true ⇒ summary.auto_params_effective=True；前端源码不含 `p.auto_params = false` 与分路侧隐藏逻辑）；`tools/ui_r87_check.cjs` 12 项（分路侧勾选可见、分路侧载荷随勾选 true/false）ALL PASS；全量 411 passed / 1 skipped。
- v0.88.1（2026-10-27）：`tools/ui_r87_check.cjs` 17 项（新增：总线/分路侧勾选后数值项 input/select 全部 disabled 且数量一致、算法启停勾选不 disabled、分路侧推导面板等待文案、取消勾选恢复可编辑）ALL PASS；`tests/test_r87_nilm_auto.py` + `tests/test_server.py` 通过。
- v0.89（2026-10-27）：`tests/test_r89_nilm_mark_all.py` 2 项（API limit=0/1/1000/999999 均 200、limit 解析源码断言；前端接线）；`tools/ui_r89_check.cjs` 10 项 ALL PASS；全量 413 passed / 1 skipped。
- v0.86（2026-10-27）：`tests/test_r86_process_colmap.py` 4 项（`apply_col_map`/`make_base` 解析、缺字段补默认、非数字 / 坏 JSON 报错；2↔3 列互换 + 不可识别表头文件：`wave/rms` 不启用 Ua≈5 A·Ia≈57.7 V（取反）、启用 ua=3/ia=2 后正确、info/load 通过、非法列号 400；`nilm_tune` 不启用 level≈57.7、启用≈5.0、`nilm_tune_base.json.columns.mapping.ia=2`、running 模式亦回显、重复列号 400；时间在第 2 列文件：重采样 timestamp=2 → rows_out 6400、`params` 回显、重复列号拒绝）；`tools/ui_r86_check.cjs` 18 项（三处块存在 / 默认不启用 / 列号行隐藏 / 默认 1..7 / 文案、三种载荷默认值、勾选后展开、载荷含列映射、调参与预览本地保存）ALL PASS；全量 405 passed / 1 skipped。备注：重采样「不启用映射且第 1 列不是时间」的反例用例耗时 >30 s（把电流值当时间戳），已移除以免拖慢套件。
- v0.85（2026-10-26）：`tests/test_r85_branch_speed.py` 2 项（默认 follow=True / 0→False / to_dict 含键；联动启动：默认同一 PaceClock speed=2 且分路侧配置 file_speed=5 不改写，follow=false 后各自 PaceClock 分路 5 / 总线 2，总线侧 follow 不受影响）；`test_r14_branch::test_r15_common_window` 断言更新（synced_pace=True、file_speed 有效值 0、配置仍 5）；`tools/ui_r85_check.cjs` 8 项（默认勾选、禁用/启用切换、提示显示、payload 字段、总线侧不含该键、保存落盘、总线侧非文件时勾选禁用）ALL PASS。全量 401 passed / 1 skipped。
- v0.89.1（2026-10-28）：**自适应算法参数 vs 调参工具参数 对照核查**（`tools/verify_auto_vs_tune.py`，样例 `data/nilm_steps.csv` 300 周波 / `nilm_bus_mixed.csv` 500 周波 / `nilm_softstart.csv` 1000 周波，P 口径三相总，默认 PT=100/CT=15 折算后基荷 1.8–4.1 MW，运行窗 300 周波）。
  - 一致项：σ 三者完全相同（27.92 / 27.62 / 9391 W，噪声统计口径一致：差分 MAD×1.4826/√2）；修复后 settle_cycles 5=5；steady_state.tol 与 threshold.settle_tol 为同量级（A/T 0.85–0.9）；GLR noise 1.00。
  - 结构性差异（设计口径不同，非错误）：**min_delta** 调参=max(6σ, 2%×基荷 或 最小关心负荷/2)=37 000 W（2% 基荷主导），自适应=max(1.5kσ√(2/min_steady), 4σ)=111.7 W（纯噪声口径，k=5.53）→ 相差 330×；自适应没有「最小关心负荷」业务下限，MW 级总线上百瓦级扰动只要超过 5.5σ 即报事件。two_window 窗 10→16–32（Allan 拐点）、k_sigma 3→5.53；GLR window 15→16–32、threshold 25→15.3（k²/2）；CUSUM drift/h 取法不同（min_delta/4 与 2(min_delta−k) vs min_delta/2 与 Siegmund 反解）；median_cycles 5→5（奇数化 settle）。
  - 回放结果：steps / bus_mixed 两文件 6 算法 ×3 套参数事件起点与幅值全部一致（2 / 5 个事件，无虚警，含 1 周波尖峰被 two_window 三套都报）；整段推导 A 与运行时末窗 R 的参数在 steps 完全相同、bus_mixed 仅 min_steady 32 vs 16（窗长不同、Allan 拐点不同）且事件一致。softstart（半数周波是斜坡）三者都把 σ 量成斜坡斜率（9391 W），属已知局限：MAD 在事件占比 ≥50% 时失效，调参侧 steady_state 靠 `longest_transient` 仍给出 max_transient=650 / min_steady=33，自适应侧 transient 只到 80（超限游程口径，斜坡每周波增量 9390≈σ 不算超限）→ 自适应 steady_state 漏报斜坡事件，仅 two_window/GLR 报 3 个；这是自适应相对调参工具的真实短板（慢斜坡）。
  - 发现并修复的缺陷：① `_corr_time` 台阶下 τ 恒 20（settle/min_steady/transient 顶满，修复前 v0.87 全部推导表受影响）；② 长斜坡 / 密集台阶被判采样保持或分段恒定（自适应整段 None、调参 σ=1.57e6 W）。
  - 验证：`tests/test_r87_nilm_auto.py` 9 项、`tests/test_r83_repeated_cycles.py`、`tests/test_nilm_tune_tool.py` 通过；全量 416 passed / 1 skipped。
- v0.90（2026-10-28）：**设备画像匹配算法（基础版）** `tests/test_r90_nilm_profile.py` 14 项。合成数据（fs 6400、PT/CT 关、pf 0.9、电流噪声 2 mA）：设备侧基荷 100 W + 500 W 设备三次启停（启动 0.3 s 内 +300 W 冲击）；总线侧基荷 3000 W + 该设备 3.0→9.0 s + 他设备 1500 W 5.0→12.0 s + 120 W 6.5 s 起。
  - 画像：标签方式 μ(ΔP)=500.0、μ(ΔQ)=242.2、μ(ΔIa/b/c)=3.207 A、峰值比 1.60、启动持续 15.7 周波、停止 1 周波；3 个启动起点与标签时刻偏差 ≤1 周波（修复前「长后窗中位数」定位把起点提前 2–11 周波）；无标签自动定位同样 3/3。
  - 总线侧检测：START@3.00 s（D²=0.01，置信 0.999）、STOP@9.00 s（D²≈0，置信 1.0），他设备 −1500 W 候选 D²/d=103.8（ΔI 三维各贡献 162、ΔP 178）→ `rejected[d2_exceeds, state_mismatch]`，+1500 / +120 W 候选同样被拒；`nilm_replay` 同一文件 6 标量算法各报 5–6 事件（120～1500 W），profile 恰 2 事件 500 W。
  - 状态机：ON 状态下第二次「启动」→ `state_mismatch`、非 confirmed；`state_check=0` → 两次均 confirmed。画像缺失 → `summary.profile.error`＋notes；路径空＋勾选 → notes 提示。
  - 落盘 / 读回：`nilm_events_*.csv` 末 6 列 `device_id,confidence,d2,profile_direction,status,quality_flags`；旧表头（含 unit/run_id 无 device_id）改名 `.pre-v090.csv`；`load_nilm_events` 读回并 `load_events` 装回 device_id。
  - API：`POST /api/process/nilm_profile`（总线 / 分路路由、标签文本 / 自动两种、坏标签 400、文件不存在 400）；CLI `tools/nilm_profile.py` 写出含 `command` 的画像。UI：`tools/ui_r90_check.cjs` 13/13（jsdom 打 8033 实服务）。
  - 回归：r12 / r18 / r87 中「全部算法」断言改 `NILM_SCALAR_ALGOS`；CSV 列断言改按列名定位。全量 **444 passed / 1 skipped**（约 128 s）。
  - 未覆盖：真实设备录波（无样本）；同幅值同 pf 的孪生设备（方法局限，必然高置信误配）；I 口径画像端到端（仅单元层路径）；DTW / 幅值校准未实现。
- v0.91（2026-10-28）：**周波窗定位提速** `tests/test_r91_line_index.py` 5 项 + 402 MB 实测基线 / 优化后对照（bench：`_wave_window_from_file` / `cycle_values` / `load_cycles_from_file`，定位第 600 s，n=300，页缓存热）：
- v0.91.1（2026-10-28，文档）：NILM_TUNING_GUIDE 画像算法章节；文中三条命令（nilm_profile → nilm_replay --set nilm.profile_path/profile.enabled → nilm_check）用合成数据实跑通过（profile 行 2 真值/2 命中/0 误报）。发现并修复 nilm_replay `--set nilm.profile_path=` 被转成 bool。tests/test_tools + test_r90 19 passed。
- v0.91.2（2026-10-28）：合成数据电流取反（P<0）复现"启动 ΔI<0 / 停止 ΔI>0"：原因＝自动模式方向按 ΔP 符号；改按 d_it 后方向正确并给出"6/6 事件 ΔP 与 ΔI 异号"提示。test_r90 + test_tools 19 passed。
- v0.92（2026-10-28）：`tests/test_r92_profile_polarity_merge.py` 3 项——极性反转在 PT/CT 启用/未启用下均生效；CT 接反的合成数据勾选反转后 ΔP/ΔI 同号、启动 μ 为正；分级带载（3 级 +5 %）自动定位 4 个启动 → merge_gap 10 s 合并为 1 个。API `/api/process/nilm_profile` 带 merge_gap_s 实测合并 3 个，command 含 `--merge-gap 10`。
- v0.92.1（2026-10-28）：电机型合成波（P 0.5 s 衰减、无功启动电流 3 s 衰减）：改前 P/I 两口径稳态分段都漏掉启动（前后稳态段间隔 161/503 周波 > max_transient 80），I 口径还把 −0.08 A 的前导波动当成停止；改后 P/I 各得 1 启 + 1 停且停止为真实大台阶（`test_r92` 第 4 项）。test_r90/r92/tools 22 passed。
- v0.92.2（2026-10-28）：用用户给的画像 JSON + 合成"设备1"（fs 10000、P<0、23.6 kW/36 A、启动 82 周波斜坡、7 A 小负荷）按用户分路侧 nilm 配置回放：画像/数据一致时 2/2 命中（STOP D²/维 0.07，START 1.5）；ΔQ 符号与画像不一致时全部 `d2_exceeds`（d_q 贡献 112/274）；PT/CT 不一致时给出错误。test_r92 第 5 项覆盖首 gap 与 PT/CT；全量 439 passed。
- v0.92.3（2026-10-28）：用户回放输出（口径一次侧、6 算法全开、profile 关、profile_path 空）与其配置文件矛盾 ⇒ 路径 `config/branch_runtime.json` 不存在被静默回退。修复后 `--config config/zz.json` 退出码 2 并提示 `configs/zz.json`。test_tools/config/r9x 65 passed。
- v0.92.4（2026-10-28）：用户回放"全程没有候选"根因＝画像前后窗 3000/3000 > window_cycles 300（`_two_window_candidates` 需 L ≥ pre+post+2）。修复后提示「需要约 9092 周波的检测窗…已自动缓存」。
- v0.99.8（2026-10-29）：出厂 PT/CT 改为不启用后 14 个按一次侧口径断言的测试改用 `copy_default_ptct_on` 夹具；全量 452 passed。
- v0.99.6（2026-10-29）：新增 4 项测试（相序重排/自动、配置校验、自动相序下检测不变、一次侧变比不同不误判 + 一侧关闭拒绝）；全量 452 passed。
- v0.99.2（2026-10-29）：TestClient 复核 `/api/process/wave/rms` 对 1 A 二次电流：pt_ct 关 → 1.0；`pt_ct_enabled=1,pt_ratio=1,ct_ratio=40` → 39.99999；server/ct_estimate 测试通过。
- v0.99（2026-10-29）：HTML 自动转换 190 处标签，id 集合与 label 配对数前后一致；JS 语法校验；全量 pytest 448 passed。
- v0.98（2026-10-29）：仅前端 HTML/CSS/JS；控件 id 全部保留（npPayload 不变），JS 语法校验通过，server / profile 测试通过。
- v0.97（2026-10-29）：事件时间段口径：停机 5.5→6.5 s、N=50：总线 CT 估计 39.98（真值 40）、n_pre/n_post=50/50；两侧都勾（42/15）→ 互估 40.0 / 15.76 并给偏差 4.8%/5.1%；都不勾 → 仅比值 2.665；事件类型填反 → 「方向不符」提示；N=20 生效；曲线 GET /wave/rms 带 3p3w+A 反返回 600 周波正确幅值；CLI --json；全量 pytest 448 passed。界面未做浏览器截图（沙箱无浏览器），布局沿用现有 label.f 网格样式。
- v0.96（2026-10-29）：合成：设备一次 36 A 停机 + 总线 120 A 背景，分路 CT 15 四线、总线 CT 40 三相三线 A 相 CT 反；A/C 相、B 相（重构）估计总线 CT 39.97~39.99（真值 40）、反向估分路 15.0；台阶时刻精确到周波；HH:MM:SS 写法、超范围 / 坏参数 / 3p3w+B 未重构报错；API 200/400、等价命令、CLI --json；live 服务 POST 返回 39.997；全量 pytest 448 passed。
- v0.95（2026-10-29）：两表法合成文件经 `/api/process/wave/load`：默认 Ib≡0、Ua 为线电压幅值；基准配置 3p3w+重构+A 反后 Ib 回到相电流幅值、Ua 回到相电压；非法 wiring/invert_phases → 400；`/api/process/nilm_tune` 返回 base 含四项且 `nilm_tune_base.json` 落盘；CLI `nilm_profile.py --wiring 3p3w --invert-phases A --reconstruct-3w` 提取画像 ΔIb=−35.7（重构）；全量 pytest 446 passed。
- v0.94（2026-10-29）：不对称电流（36/38/40 A）+ 对称电压合成：重构后分相 P/I 与四线逐相一致（rtol 1e-6）；用户画像 + 合成 3p3w 总线：重构后 STOP 命中、d_ib 参与 7 维匹配（D²/维 0.30、置信 0.86）；阈值算法检测对象 B 相重构后检出 8204 W 台阶（未重构恒 0）；全量 pytest 445 passed。
- v0.93（2026-10-29）：合成三相三线两表法总线（A/C 电压列=Uab/Ucb、B 无 CT、A 相 CT 接反、36 A 停机）：原样 0 候选+体检提示；`wiring=3p3w` 仍 0 候选（符号不一致提示，B 缺相提示消失）；`wiring=3p3w + invert_phases=A` 停机 STOP 精确到秒、置信 0.908；测试用 600 W 台阶 3 次停机全部命中；全量 pytest 443 passed。
- v0.92.6（2026-10-28）：合成总线侧（B 相 I=0、A 相极性反、6 s 停机 36 A）复现用户「零候选」；体检提示恰出现 1 次且含两类原因；全量 pytest 通过。
- v0.92.5（2026-10-28）：用户回放显示同一次停机产生 80+ 个起点逐块右移的候选、首个被接受的时刻偏早 15 s、STOP 组因 dur σ=2 被 dur 维（贡献 32）压住。200 s 合成长文件 + 用户画像（3000/3000）：修后停止只出 1 个候选、时刻精确到秒；10/50 画像停止/启动各 1 次命中。全量 440 passed。
  - 基线：瞬时值 817 ms、有效值 816 ms、负荷辨识周波窗 273 ms、自定义时间 910 / 286 ms；cProfile：`_count_rows`×2 0.52 s + `_count_newlines` 0.19 s + JSON 逐元素 round 0.17 s，占 1.1 s 中的 0.88 s。
  - 优化后：104 / 112 / 95 / 103 / 118 ms；HTTP 端到端（含 2.3 MB JSON 传输）`/api/nilm/wave_file` 0.32 s、`/api/elec/cycles_file` 0.10 s、`/api/nilm/cycles_file` 0.09 s。
  - 正确性：索引三接口 vs 暴力计数（随机 / 定长跨边界 / 边界对齐）逐位一致；time / row / seconds 定位 `skipped_rows` 与首块 t 在顺序扫 vs 索引路径一致；三条周波窗端点 + 自定义时间两路径结果逐位一致。
  - 发现并修的实现坑：检查点 `cum[k]==target` 时目标行首可能在边界之前（行跨边界），须从上一个检查点扫（改为严格小于）。
  - 未覆盖：冷页缓存 / 机械盘上的绝对耗时（只能按「读整文件 → 读 ≤1 MiB」推断）；多进程部署下索引不共享。

## 专题：tmp/ 实录（海湾化工 bus-停止 / dev1，2026-10-29 18:20 播放）总线侧误报多、画像匹配无事件的根因分析（第 156 轮）

**数据事实（tmp/realtime、tmp/nilm、tmp/config_*.json）**
- 总线侧：3p3w + 重构 + 反相 A，CT=250、**PT=1**，Ua≈60 V（Uab≈104 V ⇒ 明显是 PT 二次侧 100 V 级电压，PT 未设）；Ia 50～106 A；P≈−16 kW（三相均为负）。quantity=i、channels=[A]、**auto_params=true**、min_gap=500 周波、profile 启用。
- 分路侧：CT=1、PT=1，Ua≈239 V（真实 380 V 低压侧），Ia/Ib/Ic≈37/32.5/43.6 A，P≈−24 kW（三相均为负）。
- 设备停机（分路侧 14:39:29→14:39:55）：2 s 软降（37→31 A）→ 1 s 快降（31→17.7 A）→ **约 25 s 指数尾（17.7→0.6 A）**。总线侧对应台阶出现在 **14:38:15→14:38:41**（94→69 A 用 3 s，再 69→56 A 用 25 s），三相各降约 34/35/33 A，与设备 37/32/44 A 同量级 ⇒ 同一事件，但**两文件时钟相差约 75 s**。总线 ΔP≈+6.3 kW，×4 ≈ 设备 ΔP 24 kW ⇒ 总线 PT 实际≈4（如 400 V/100 V），配置 PT=1 使总线 P/Q 小 4 倍。
- 事件文件：200 条全部 source_id=0，6 种算法各 31～36 条，**相邻事件间隔最小 10.1 s、中位 10.5～11.7 s ＝ min_gap_cycles 500 周波**，|ΔI| 分位数 3.6/5.0/5.6/6.6/9.0 A，up 139 / down 61，不随真实负荷变化；真实停机处（14:38:15）各算法只报出 −5～−7 A。

**结论 1：6 种算法"误报多"＝自适应参数在总线背景波动下门槛过低，被 min_gap 限速后的饱和输出。**
- auto_params 的 σ 来自逐周波一阶差分 MAD（周波尺度白噪声），min_delta=max(k·σ·√(2/min_steady)·1.5, 4σ)；总线其它 60 % 负荷造成的**秒级漂移**（1 s RMS 相邻差常见 2～6 A，如 97.97→92.04）不在该 σ 里，于是 3～9 A 的背景涨落被全部算法持续判为台阶，每 10 s（gap）放行一条 ⇒ 每算法约 35 条/7 min，正是观察到的数量与间隔。
- 真实停机是 3 s + 25 s 的慢斜坡，自适应的 settle/max_rise/transient 由周波尺度统计推得（通常几十周波），斜坡被切成多个小台阶，幅值只剩 −5～−7 A。
- 处置：总线侧**关闭自适应**，用数据处理·调参两步法——第 ① 步用 dev1 文件估最小关心负荷（≈30 A/相，可取 15～20 A 作门槛）、第 ② 步用总线稳态背景段量噪声（σ 会体现秒级漂移）、max_rise/max_transient 放大到覆盖 25 s 尾（≥1500 周波）或只要求捕捉快降段；代码层可改进 auto：min_delta 用 min_steady 尺度的 Allan 偏差而非周波 σ（待用户确认后实现）。

**结论 2：画像匹配无事件＝候选阶段就没过门槛（不是匹配被拒）。**
- 画像候选用双滑窗（pre=画像 pre_cycles≈10、post≈50 周波＝0.2 s/1 s 中位数差）在三相合成电流 √(Ia²+Ib²+Ic²) 上找，门槛 min_d=0.5×画像 |ΔI 合成| ≈ 0.5×√(37²+32.5²+43.6²)=33 A。总线侧最陡处 1 s 内每相只降 ≈11.5 A（合成 ≈20 A）<33 A ⇒ **无候选**，profile_last 为空，自然无事件（也无 rejected 诊断）。
- 即使有候选也会被拒：候选终点封顶 post_n−1 周波，总线 ΔI 只量到快降段（≈−25 A/相）而画像是全幅 −37 A；总线 PT=1 使 ΔP 为画像的 1/4；两侧 P 全为负（CT 极性/方向约定两侧都反），d_p/d_q 维度 D² 必然超 d2_max。
- 处置：总线 PT 填真实变比（≈4，需核对铭牌）；画像提取 post_cycles 覆盖慢尾（或候选搜索改为多尺度/稳态分段，与设备侧提取同口径——建议的代码改进）；检查两侧 CT 极性；若用到两侧对齐（估计 CT、同步对账）注意 75 s 时钟偏差。

**未能核实**：画像文件 output/nilm/profile_设备1_20261028_165536.json 与原始 CSV 不在 tmp/，pre/post_cycles、dur、sigma 与周波级 σ 为推断值。

- v0.99.15（2026-10-29）：针对上节两条根因的代码改进已实现——auto `sigma_block/sigma_eff/drift_ratio`，画像 `max_scale`；合成实验：随机游走背景（周波 σ 0.42，50 周波漂移 ≈2.8）下 min_delta 由 1.55 → 8.9（drift_ratio 5.7）；3 s 快降 + τ=6 s 尾的 −34 A/相慢停机，单尺度 0 候选、×8 尺度 1 候选（ΔIa −27 A，STOP）。全量 pytest 456 passed。

- v0.99.17（2026-10-29）：性能剖析（cProfile，config_bus.json 参数，10 kHz，640 样本/块）：优化前 `_evaluate` 占 98%，其中 detect_steps 67%（cusum/steady/threshold 纯 Python 循环遍历整窗）、window_stats 27%（多滞后 MAD median）；优化后单块 1.3 ms，评估次数 1/3，全量 pytest 459 passed。
