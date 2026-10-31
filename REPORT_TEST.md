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

## 专题：tmp/ 第二次实录（PT=4、min_gap=1000、window=3000、自适应、画像 profile_device_20261029_212837）复盘（第 161 轮）

**数据事实**：总线 Ia 1 s RMS 相邻差 MAD-σ 1.69 A、10 s 块均值差 σ 3.9 A；每 30 s 窗内 Ia 极差 10～20 A，14:48 后 20～30 A（如 59.6→87.4 A、73.3→99.1 A）——这是**其它负荷真实投切**，不是噪声。总线 6 种算法 155 条事件，各算法相邻间隔最小 20.0～20.2 s ＝ min_gap 1000 周波（限速饱和），|ΔI| 中位 8.9 A、最大 40.9 A。分路侧 7 条（含 profile 1 条 low_confidence/trajectory_deviates，ΔI 合成 −37.3 A，dur 99 周波）。

**结论 1（6 种算法"误报"）**：阈值类算法在总线上检测的是**全部负荷**的台阶；本条总线其它设备每分钟多次 10～30 A 的投切，与目标设备 34 A/相的停机同量级，任何门槛（含自适应 Allan 口径）都无法只留目标设备——要么都报、要么连目标也丢。这不是算法缺陷而是口径：总线侧 6 种算法＝总线事件记录器，设备归属只能靠画像匹配。建议总线侧把 6 种算法当"总线事件日志"或关闭，只看 profile；或把 min_gap 调大并以 |ΔI| ≥ 25 A 过滤。

**结论 2（画像仍未识别）**：用 tmp/ 1 s RMS 插值重建周波序列 + 以设备侧同法构造画像做仿真：v0.99.15 的多尺度在停止处产生候选但按 ×8 窗量特征（ΔIa −28、dur 399）与画像（按 post=50 提取：ΔIa −14、dur 99、σ 10 % 下限）不一致 ⇒ d2/dim 33.8 → rejected（界面只在 profile_last 诊断里能看到，事件文件里为空）。修正特征几何后同一候选 confirmed（conf 0.80，d2/dim 0.4），邻近另一设备 +10 A 事件 rejected（d2/dim 54.7）。PT=4 后 ΔP 两侧已一致（10.4 k vs 10.5 k）。另：分路侧自匹配 trajectory_deviates 说明模板散布下限 0.1 过严，已放宽至 0.25。

**未能核实**：画像 JSON 与原始 CSV 仍不在 tmp/；仿真用 1 s RMS 线性插值（无周波级细节），结论为机理级而非逐值复现。建议下次把 `output/nilm/profile_*.json` 与负荷辨识页「画像匹配诊断（最近候选）」一并放入 tmp/。


## 第 164 轮专题：总线侧画像匹配未运行（PT/CT 标志位硬拒绝）

| 项 | 结果 |
|---|---|
| 复现方式 | `tmp/realtime/current_*.csv`+`power_*.csv`（source_id=0）1 s RMS 线性插值为 20 ms 周波序列，经 stub `CycleFeatures.push` 喂给 `NilmDetector(AppConfig.from_dict(tmp/config_bus.json))` |
| 修复前 | profile 事件 0，`profile_hist` 0，errors 含「一次 / 二次侧口径不一致 … 画像匹配不会命中」 |
| 修复后 | 14:38:17 STOP **confirmed** conf 0.830 d²/维 0.373（ΔIa/b/c −36.0/−38.3/−39.3 A，ΔP +25604 W，持续 271 周波）；14:39:45 与 14:48:22 候选 rejected（d²/维 135.6 / 131.9，state_mismatch） |
| 候选 CSV | `run/nilm_profile_candidates_{日}.csv` 3 行 |
| 回归 | 466 passed, 1 skipped |


## 第 165 轮专题：候选被拒的维度分解与终点规则修复

| 候选（总线侧） | 状态 | D²/维 | 贡献最大维 | 说明 |
|---|---|---|---|---|
| 14:38:16 STOP（修复前，实录） | rejected | 48.1 | dur 221、ΔQ 110 | ΔI/ΔP 贡献 ≤2.6，终点被噪声推到 2161 周波 |
| 14:38:16 STOP（修复后，仿真 σ=0/2/4 A） | confirmed | 0.35/0.47/0.60 | — | conf 0.84/0.79/0.74 |
| 14:39:45 / 14:48:22（他负荷） | rejected | 69–82 | ΔI/ΔP/dur | 正确拒绝 |

回归：469 passed, 1 skipped。


## 第 166 轮：v0.99.23 实录结果（总线侧 confirmed）

| 侧 | 时刻 | 结论 | conf | D²/维 | margin | 最大贡献维 |
|---|---|---|---|---|---|---|
| 总线 | 14:38:16.9 | STOP confirmed | 0.748 | 0.58 | 178.6 | ΔIb 1.56 |
| 分路 | 14:39:31.6 | STOP confirmed | 0.983 | 0.03 | 3041 | dur 0.24 |
| 总线 | 14:48:22.5 | START rejected | 0.044 | 6.24 | 10.7 | ΔQ 22.5 |

## 第 167 轮：启动段实录（总线侧设备启动无候选 → v0.99.24 confirmed）

| 时刻（总线） | 事件 | 改前 | v0.99.24 | D²/维 | 备注 |
|---|---|---|---|---|---|
| 14:55:33 | 他负荷 −28 A（两级） | 无候选 | STOP confirmed 0.46 | 1.54 | **误报**，单样本 σ 下限所致 |
| 14:59:08 | 他负荷 +60 A | START rejected | START rejected | 29.8 | 正确 |
| 15:00:08 | 设备启动 +35 A 斜坡 18 s | **无候选** | START confirmed 0.789 | 0.47 | ΔI 34/36/40、ΔP −25.6 kW、dur 580 |
| 15:00:40 | 他负荷 −70 A | 无候选 | 并入上一候选间隔内 / rejected 424 | — | 正确 |

回放脚本：真实 `NilmDetector` 读 tmp/config_bus.json + 画像 020116 + tmp/realtime current/power（source 0）。全量 pytest 473 passed。

## 第 168 轮专题：设备启动「有候选但特征反号」——window 被相邻他负荷污染

运行目录：`output/20261030_120818/`（`tmp/` 副本）。画像 `profile_bus_profile_device_20261030_120634.json`（pre/post=3000，启动 μ=+35.9/+31.2/+42.5 A、ΔP −23.9 kW、dur 1271；停机 μ=−36.3/−31.5/−42.2 A、dur 305）。

| 时刻（总线） | 候选 | d_ia/d_ib/d_ic (A) | ΔP (kW) | ΔQ (kvar) | dur | D²/维 | 判定 |
|---|---|---|---|---|---|---|---|
| 14:55:32 | STOP | −21.5/−17.7/−17.9 | +15.8 | −0.25 | 187 | 5.92 | rejected（他负荷两级 −28 A） |
| 14:59:08 | START | +62.7/+64.5/+57.4 | −48.6 | −1.04 | 1 | 27.8 | rejected `d2_exceeds`（他负荷 +60 A）✓ |
| **15:00:08** | **STOP** | **−39.2/−38.8/−30.5** | **+33.5** | **−15.2** | **1356** | **544.7** | **rejected `trajectory_deviates`（设备启动被量反）** |
| 15:00:39 | STOP | −71.2/−73.4/−67.6 | +57.9 | −16.0 | 5 | 621.3 | rejected（他负荷 −70 A）✓ |
| 分路 15:01:22 | START | +34.4/+29.3/+40.5 | −23.1 | +0.95 | 175 | 0.49 | **confirmed 0.782** ✓ |

**数字对账（证明后窗跨过了 15:00:39）**：15:00:08 行的 ΔP +33.5 ≈ +57.9（他负荷切除）− 25.6（设备本身）；ΔQ −15.2 ≈ −16.0 + 0.9；ΔI −39 ≈ (+62 +35 −71) − 62。前窗起点落在 14:59:08 之后、后窗起点落在 15:00:39 之后，两端都不是设备自己的过渡。

**代码链**：`_two_window_candidates` 的 |Δ| 游程不分符号；多尺度合并 `abs(delta) > abs(hit["delta"])` 让后窗更长（已含下一个反号事件）的粗尺度覆盖细尺度幅值 ⇒ 候选 Δ 变负；`window_bounds` 的「同号＝自身过渡」豁免把 −70 A 台阶放行（无幅值上限，且边界以 `end` 为基准，`end` 又被污染的中位数拉到 15:00:35）⇒ `post_hi=None` ⇒ 60 s 后窗整段落在事件之后。

**v0.99.25 修复与验证**：同号才合并、幅值取最细尺度；同号豁免加 ≤1.5|Δ| 上限；后窗边界以 onset 为基准；干净后窗不足 `post/20` 时取 `post_hi` 前 `post/20` 周波并记 `window_crowded`；`sign_flip` 直接拒。合成回归（drop 距斜坡终点 100 周波）：旧 Δ=−91.7、d_ia=−34.0；新 Δ=+33.5、d_ia=+28.3（`window_crowded`）。实录数据回放：总线 15:00:08 `START confirmed 0.789`（dur 580），分路 15:01:22 `confirmed 0.776`。全量 pytest 476 passed / 1 skipped。

## 第 169 轮专题：bus-启动-1.csv（15:45–16:05）为什么零 `profile` 事件

运行目录 `output/20261030_143226/`。总线 20 min（15:45:03–16:05:02），分路 dev1.csv 14:35:57–15:05:56 —— **两段不重叠**，本次没有设备侧对照。画像 `..._084954`（pre/post 3000，启动 +35.95/+31.20/+42.49 A、−23.9 kW、+0.9 kvar、峰值比 1.59、dur 1271）。

**(a) 段内负荷动作清单**（40 s 前后中位数对比）

| 时刻 | 动作 | ΔP (kW) | ΔQ (kvar) | ΔIa / ΔIb / ΔIc (A) | 持续 | 形状 |
|---|---|---|---|---|---|---|
| 15:46:43~15:48:13 | 波动负荷投入→退出 | −11.9 | −0.4 | +20.9 / +21.0 / +20.0 | ≈ 85 s | 分段/抖动 |
| 15:50:34 | 负荷切除 | +11.3 | −0.3 | −16.6 / −17.3 / −16.5 | 保持 | 台阶 |
| 15:51:03 | 大负荷投入 | −47.4 | −0.2 | +63.3 / +63.1 / +60.4 | ≈ 70 s | 6~8 s 两级上升，峰值比 1.08 |
| 15:52:13 | 同一大负荷切除 | +47.6 | +0.3 | −63.4 / −61.2 / −61.8 | — | 3 s 下降 |
| 16:00:45 | 电容投切 + 电机投入 | −73.5 | ±30 摆动 | +95.4 / +99.8 / +93.2 | 到文件末 | 峰值比 1.13、Q 多次跳变 |

**与画像的差别**：画像的三相是 C 相最大（+34.4/+36.5/+40.3 A，C−A≈+6 A）、25 s 单调斜坡、峰值比 1.59、ΔQ +0.9 kvar；上表五次动作 C−A 在 −2.9~+1.6 A（三相平衡）、上升 3~8 s、峰值比 1.08~1.13、ΔQ≈0。幅值分别是设备（−24 kW / 37 A）的 0.5×、1.9×、2.9×。

**(b) 设备状态：本段一开始就在运行**

| 状态 | P (kW) | Q (kvar) | I (A) | THD_I | 谐波电流 THD×I |
|---|---|---|---|---|---|
| 设备停机（旧文件 14:53–14:58，无电容） | −47.8 | −7.7 | 64.6 / 73.2 / 70.0 | 25 % | 16.1 / 18.3 / 17.0 A |
| **设备运行 + 电容投入（旧文件 15:01:10–15:05:50）** | **−57.2** | **−23.9** | **84.7 / 93.8 / 95.4** | **37 %** | **31.5 / 33.3 / 32.3 A** |
| 本段 15:45:05–15:46:40 | −55.6 | −16.6 | 80.4 / 90.0 / 88.2 | 39 % | 31.4 / 33.4 / 31.9 A |
| 本段 15:48:20–15:50:30 | −57.1 | −16.7 | 83.6 / 89.9 / 91.5 | 39 % | 32.4 / 34.2 / 32.8 A |
| 本段 15:52:20–15:58:50 | −52.2 | −17.1 | 76.3 / 85.1 / 82.5 | 37 % | 28.4 / 30.3 / 28.9 A |
| 本段 15:59:20–16:00:40 | −55.7 | −21.0 | 82.4 / 91.1 / 89.4 | 37 % | 30.3 / 31.5 / 30.5 A |

本段稳态与"设备运行+电容投入"参照几乎重合，谐波电流（28~34 A）远离停机参照（16~18 A）；每次大负荷事件退出后 THD 都回到 36~38 %。⇒ 设备在上一段 15:01 启动后一直运行到本段结束，20 min 内**没有启动、也没有停机**，所以没有事件可报。

**(c) 探针：把画像签名的启动注入本段 15:55:00**（+35.9/31.2/42.5 A、25 s 斜坡、峰值比 1.59、−23.9 kW、+0.9 kvar）

```
detect_profile(...) → 15:55:04 START confirmed conf=0.891 D²/维=0.23 scale=0.5 hits=[0.5,1] dur=721
```
说明现行 v0.99.25 流程在本段数据上仍然灵敏，零事件不是漏检。

**(d) 候选 CSV（总线 5 条，全部 rejected）**

| 时刻 | scale | D²/维 | conf | flags | 实际是什么 |
|---|---|---|---|---|---|
| 15:50:14 | 2.0 | 47.4 | 0.000 | sign_flip, window_crowded | 15:50:34 切除 + 15:51:03 投入被 120 s 窗混在一起 |
| 15:51:03 | 0.25 | 11.9 | 0.003 | d2_exceeds | 45 kW 大负荷（1.9× 设备） |
| 15:52:13 | 0.25 | 14.7 | 0.001 | d2_exceeds | 同一大负荷切除 |
| 16:00:01 | 1.0 | 82.5 | 0.000 | d2_exceeds, ambiguous, trajectory, crowded | 电容投切暂态 |
| 16:00:48 | 0.25 | 71.2 | 0.000 | d2_exceeds | 电机 +90 A 投入 |

**建议**：① 验证该设备启动时，总线与设备侧录波必须覆盖同一时段（本次 15:45–16:05 vs 14:35–15:06 错开）；② 若只想确认"设备是否在运"，可用 THD_I×I（本次 16~18 A / 31~33 A 分得很开）作为设备状态判据。

## 第 170 轮专题：bus-启动-1.csv（15:45:03–16:05:02）到底有没有启停——五条独立证据

**数据身份**：`tmp/` 仍是 14:32:26 那次运行的输出（`run_info.json` `created_local=2026-10-30 14:32:26`，总线源 `化工行业-海湾化工-bus-启动-1.csv`，窗口 15:45:03–16:05:02，1174 个 1 s 点；分路源 `化工行业-海湾化工-dev1.csv`，窗口 14:35:57–15:05:56）。两侧时间**不重叠**（相差 39 min），本轮没有办法用设备侧数据直接对账。

**结论：这段 20 min 内没有这台设备的启动，也没有停机——录制开始时设备已经在运行，到文件结束仍在运行。** 工具报 0 条 `profile` 事件是正确的。下面五条证据互相独立。

### 证据 A（最有力）：谐波电流指纹 —— 设备是谐波源，它的"在不在"会在 THD_I×I 上留下台阶

设备侧（dev1）自身 THD_I 50~60 %，是整流/变频类负荷；上一段（14:53–15:06）设备启停已知，可用来标定"开关一次这个设备，总线谐波电流变多少"：

| 时段 | 状态 | I (A) | THD_I | 谐波电流 THD×I (A，均值) |
|---|---|---|---|---|
| 14:53:19–14:58:59（上一段） | **设备停** | 60.7–82.5 / 69.7–87.1 / 66.3–85.1 | 20.6–26.3 % | **16.3 ~ 18.5** |
| 14:59:28（上一段，+60 A 他负荷已投） | 设备仍停 | 127.2 / 135.8 / 131.9 | 13.2–14.0 % | 17.8（被稀释，绝对量不变） |
| 15:00:29–15:05:37（上一段） | **设备运行** | 85–88 / 94–97 / 96–97 | 34.5–40.2 % | **30.4 ~ 33.4** |

⇒ 这台设备在总线上贡献约 **+15 A 的谐波电流**（16.8 → 32.5），而它只是把基波电流抬高约 25 A。

本段 20 min 每 60 s 一格的谐波电流均值：

| 时刻 | 15:45 | 15:46 | 15:47 | 15:48 | 15:49 | 15:50 | 15:51 | 15:52 | 15:53 | 15:54 |
|---|---|---|---|---|---|---|---|---|---|---|
| 谐波电流 (A) | 32.4 | 31.5 | **46.0** | 32.9 | 33.1 | 30.1 | 29.1 | 29.3 | 30.7 | 28.2 |

| 时刻 | 15:55 | 15:56 | 15:57 | 15:58 | 15:59 | 16:00 | 16:01 | 16:02 | 16:03 | 16:04 |
|---|---|---|---|---|---|---|---|---|---|---|
| 谐波电流 (A) | 29.0 | 29.1 | 29.8 | 32.0 | 30.9 | 31.1 | 27.1 | 32.4 | 28.7 | 29.5 |

整段**从未**掉到"设备停"的 16~18 A，包括最后一个采样点（16:04:29，I 已升到 176/190/181 A，谐波电流仍有 29.5 A）。如果设备在段内任何时刻启动，这个量会从 ~17 A 跳到 ~32 A；如果停机，会反向跳一次。都没有 ⇒ 设备全程在运。唯一超过 33 A 的 15:47 那格（46 A）是一个**临时的谐波负荷**（THD 46 %、+18 A、持续约 85 s 后退出），见证据 B。

### 证据 B：段内全部台阶，与设备签名逐项比对

设备画像签名（总线侧实测，12:08 运行 15:00:08 confirmed）：ΔIa/ΔIb/ΔIc **+35.9/+31.2/+42.5 A**、**ΔP −23.9 kW**、ΔQ +0.9 kvar、**25.4 s 斜坡**、峰值比 1.59。用五维向量做最小二乘分解 `y ≈ α·设备`（α＝相当于几台该设备，残差＝形状偏离）：

| 时刻 | ΔP (kW) | ΔQ (kvar) | ΔIa / ΔIb / ΔIc (A) | C−A | **α** | 残差 | 实际是什么 |
|---|---|---|---|---|---|---|---|
| 15:46:43~15:48:13 | −10.1 | −0.1 | +17.8 / +18.0 / +16.9 | −0.9 | +0.18 | 0.07 | 谐波型负荷（THD 46 %）临时投入 ~85 s 后退出 |
| 15:50:34 | +8.4 | +0.0 | −12.8 / −12.7 / −13.8 | −1.0 | −0.35 | 0.04 | 小负荷切除，保持 |
| **15:51:03** | **−45.7** | −0.3 | **+61.4 / +60.2 / +58.6** | −2.8 | **+1.91** | 0.04 | 大负荷投入（约 70 s 后切除）；三相平衡、**不带来任何谐波电流** |
| 15:52:13 | +47.1 | −0.1 | −61.5 / −61.3 / −60.1 | +1.4 | −1.96 | 0.04 | 上述大负荷切除 |
| **16:00:45** | **−69.3** | −1.4 | **+90.3 / +95.1 / +89.1** | −1.2 | **+2.89** | 0.06 | 电容器组投切（Q 在 ±30 kvar 之间反复跳）+ 电机投入，持续到文件末 |

- α 是**幅值比**：最接近设备的 15:51:03 也相当于 **1.9 台**该设备，16:00:45 相当于 **2.9 台**；
- 15:51:03 / 16:00:45 的残差只有 4 %~6 %，说明它们的**相别/功率因数形状**与设备相近——单看三相电流会误判，所以必须叠加证据 A（谐波）：设备投切必然带来 +15 A 谐波电流，这两次动作的谐波电流分别是 29.1 A / 31.1 A，与动作前的 30.1 / 30.9 A **持平**，说明它们是干净负荷，不是这台设备。

### 证据 C：形状

| | 上升时间 | 峰值比 | 之后 |
|---|---|---|---|
| 设备画像 | **25.4 s 单调斜坡**（1271 周波） | **1.59** | 保持运行 |
| 15:51:03 大负荷 | 6~8 s 两级 | 1.06 | 70 s 后切除（15:52:13） |
| 16:00:45 电机+电容 | ~4 s 带振荡 | 1.36 | 保持到文件末 |

### 证据 D：用真实引擎回放这段数据

`NilmDetector` + `tmp/config_bus.json` + 画像 `profile_bus_..._084954`，按 10 周波/块（≈640 样本 @50 Hz 等价节奏）喂 `tmp/realtime` 的总线序列：

```
profile 事件 0 条；候选 5 条，全部 rejected
  15:47:17  START  D²/维 11.9   （15:46~15:48 的谐波型临时负荷）
  15:50:15  START  D²/维 43.1   sign_flip + window_crowded（被夹在两次动作之间）
  15:51:04  START  D²/维 18.1   （−45.7 kW 大负荷，ΔIa 61）
  15:52:13  STOP   D²/维 19.4   （上面那台切除）
  16:00:48  START  D²/维 80.2   （电机 + 电容，ΔIa 90）
引擎 errors 只有 3 条提示（画像 PT/CT 与本侧不同、画像 3p4w 本侧 3p3w、前后窗需求大于 window_cycles），device_state 终态 unknown
```
（运行目录 CSV 里的 5 条候选为 15:50:14 / 15:51:03 / 15:52:13 / 16:00:01 / 16:00:48，与本回放 4 条相同，差异来自回放每块 10 周波的节拍。）

D² 上限 9，实际 11.9~80.2 ⇒ 全部正确拒绝，没有"该报没报"。

### 证据 E：反证——把设备启动"注入"这段数据

在同一段数据上把画像签名的启动叠加到 15:55:00（+35.9/31.2/42.5 A、25.4 s 斜坡、峰值比 1.59、−23.9 kW、+0.9 kvar），同一套引擎、同一份配置：

```
profile 事件 1 条：2021-05-25 15:55:04  START  conf=0.892  D²=1.6  ΔP=−24987 W  ΔI=66.1 A  dur=14.4 s
最终 device_state = on
```

说明：门限、窗长、画像、状态机都没有把这类动作挡住。**零事件是因为数据里没有这个动作。**

### 结论与建议

1. 这段总线数据里只有三组**他负荷**：临时谐波负荷（15:46~15:48，+18 A / −10 kW）、大线性负荷（15:51:03~15:52:13，+61 A / −46 kW）、电机 + 电容组（16:00:45 起，+90 A / −69 kW，电容 Q 在 ±30 kvar 反复投切）；**没有本设备的启停**。
2. 设备状态：录制起点（15:45:03）就在运行，终点（16:05:02）仍在运行——依据是谐波电流全程 27~33 A（设备停时为 16~18 A）。
3. 若要记录这台设备的启停，总线与设备侧录波必须**覆盖同一时段**（本段 15:45–16:05 与 dev1.csv 的 14:36–15:06 错开 39 min）；或用 12:08 那轮（14:53–15:06）这种两侧同段的文件。
4. 若您认为 15:51:03 或 16:00:45 就是这台设备，那说明画像与现场已不是同一台/同一容量：幅值相差 1.9× / 2.9×，且它们**不产生谐波电流**而设备会带来 +15 A。这种情况下需要从该设备分路的同期录波**重新提取画像**（≥3 个启停样本），不要用旧画像。
5. 现在的状态机只能从"已确认的启停事件"推设备状态；本段是"中途开始录制"，状态只能是 `unknown`。若后续要在这类"半路开始"的文件上直接给出设备状态，可考虑用谐波电流水平做一次初始状态判定（本轮已证明该判据在现场数据上是可分的：16~18 A vs 27~33 A）。

## 第 171 轮专题：基于设备画像的负荷辨识算法能否用于其它设备（代码级分析 + 可移植性实验）

**被测版本**：v0.99.25（`elec_tool/nilm_profile.py` + `elec_tool/nilm.py::_evaluate_profile`，commit `009832f`）。

**一句话结论**：**算法框架是设备无关的通用模板匹配器，可以用于其它设备；但"一份画像只对应一台设备的一个工况"，每换一台设备/一种工况都必须重新提取画像**，并满足 5 个前提（独立画像、画像窗覆盖其过渡、启动+停机双向、PT/CT 与接线量纲一致、样本≥3 或幅值足够大）。不满足时不是"精度下降"，而是**静默无候选或误报**。

---

### 一、算法到底用了什么信息（决定它能推广到哪类设备）

| 环节 | 代码位置 | 内容 | 是否设备无关 |
|---|---|---|---|
| 逐周波特征 | `nilm.py::CycleFeatures` | 每周波 ΣP / ΣQ / 三相电流均方根（基波 DFT + 时域 RMS） | ✅ 通用 |
| 候选搜索 | `nilm_profile.py::_two_window_candidates` + `detect_profile` | 双滑窗中位数差，多尺度 ×0.25…×8，超限游程（同向才成段） | ✅ 通用 |
| 特征窗几何 | `change_points` / `window_bounds` / `transition_end`（v0.99.23~25） | 前窗被上一变点截断、后窗被下一变点截断；过渡终点＝平滑后首次进 ±20 %·\|Δ\| 带并保持 | ✅ 通用（这正是总线侧多设备场景需要的） |
| 特征向量 | `FEATURES` 7 维 | ΔIa/ΔIb/ΔIc/ΔP/ΔQ/peak_ratio/dur_cycles | ⚠️ 只含**稳态量**，不含谐波、波形、闪变 |
| 相似度 | `mahalanobis_diag` + `match_event` | 对角马氏距离 + λ·median(σ²) 收缩；轨迹模板 16 点 L2；`conf = exp(−D²/2d)·轨迹折扣` | ⚠️ 对角（各维独立），设备间相关性被忽略 |
| 状态机 | `_evaluate_profile` | unknown/on/off；`state_mismatch` 折半 | ⚠️ 仅二态，无多档位 |
| 画像管理 | `NilmConfig.profile_path`（单个字符串）、`NilmDetector._profile`（单个 dict） | **一次只加载一份画像** | ❌ 一画像一设备 |
| 量纲 | `transform.pt_ratio/ct_ratio/wiring/invert_phases`、`profile.pt_ct`、`phase_map` | 跨侧换算 + 相序映射 + 3p3w 跳 ΔIb | ✅ 通用（v0.99.6/0.99.23 已验证） |

`nilm.quantity`（i 或 p）必须与画像 `quantity` 一致，否则 `_evaluate_profile` **直接不运行**并写 errors——这是第一道硬门槛。

---

### 二、可移植性实验（合成 6 类设备，全部走真实 `detect_profile`）

实验条件：总线背景 80/90/88 A、白噪声 1 A/周波、慢漂移 2 A；每类设备用**自己的画像**（设备侧 3 个样本、幅值 ±2 % 抖动）在其总线上注入一次动作。

**表 1 自画像识别（可移植性）**

| 设备 | 画像窗（pre/post 周波） | 结果 | conf | D²/维 |
|---|---|---|---|---|
| A 整流/变频（本案例，+64 A 合成 / −23.9 kW / 25.4 s 斜坡 / 峰值 1.59） | 3000 / 3000 | **confirmed** | 0.921 | 0.16 |
| B 电阻加热 3 kW（+8 A 合成 / −3 kW / 1 s 台阶） | 10 / 200 | **rejected** | 0.053 | 5.87 |
| C 电容补偿 20 kvar（+30 A / ΔQ +20 kvar / 2 s） | 10 / 300 | **confirmed** | 0.969 | 0.06 |
| D 变频 40 % 档（+22 A / −9.5 kW / 4 s） | 100 / 300 | **confirmed** | 0.849 | 0.33 |
| E 循环泵（+20 A / −13 kW / 6 s / 运行 45 s） | 10 / 600 | **confirmed** | 0.944 | 0.12 |
| F 电阻性 35 A（+60 A / −23 kW / 1 s 阶跃，用于干扰测试） | 10 / 200 | **confirmed** | 0.739 | 0.61 |

**表 1 的关键发现**

1. **5/6 类设备自画像都能识别** ⇒ 框架通用，没有对"整流/变频"做任何特化。
2. **B（3 kW）在同等条件下不稳定**：把合成数据长度从 12050 改成 12300 周波（噪声实现变化），同一份代码从 rejected 0.053 变成 **confirmed 0.607**。原因见限制 3：小功率设备的 ΔQ/ΔP 量级接近母线噪声，而 σ 的**绝对下限**只有 5 W / 5 var。
3. **画像窗必须覆盖设备过渡时间**：C 用 10/50（后窗 1 s < 2 s 上升）⇒ rejected 0.265；改成 10/300 ⇒ confirmed 0.969。E 用 10/50 ⇒ rejected 0.063；改 10/600 ⇒ confirmed 0.944。**这不是算法问题，是配置问题，但配错就是静默漏报。**

**表 2 交叉测试：用 A（本案例）的画像去测其它设备（误报风险）**

| 被测设备 | 结果 | conf | D²/维 | 主要 D² 贡献 |
|---|---|---|---|---|
| B 3 kW 电阻 | 无候选（低于 0.5×\|ΔI合成\| 门槛 32 A） | — | — | — |
| C 电容 20 kvar | rejected | 0.000 | 1034 | ΔQ 7184、ΔP 44 |
| D 变频 40 % 档 | 无候选（22 A < 32 A） | — | — | — |
| E 循环泵 20 A | rejected | 0.050 | 6.00 | ΔIa 8.9 + ΔIb 7.2 + ΔIc 10.2 + ΔP 9.3 |
| **F 同功率电阻负荷（35 A / −23 kW，仅功率因数不同）** | **rejected** | **0.213** | **3.09** | **ΔQ 15.9**（其余各维 0.1~1.2） |

F 的判别**完全靠 ΔQ 一维**：幅值差 5 %、ΔP 差 4 %，都在单样本 σ 给出的 23 % 判别半径内；只有 ΔQ 差 902 var（≈3.8 σ_eff）把它压到 conf 0.213。**离拒识门槛 0.30 只有 1.41 倍余量**，且与背景噪声无关（噪声 0.3/1/3 A 时 D²/维 3.10/3.09/3.09）。现场只要设备无功波动大一点，或母线 ΔQ 估计有偏差，**这个同功率他负荷就会被误报成设备启动**。

---

### 三、七条硬限制（每条给定量证据）

**限制 1：一份画像 = 一台设备的一个工况（代码级硬限制）**
`NilmConfig.profile_path` 是单个字符串，`NilmDetector._profile` 是单个 dict，`_evaluate_profile` 只匹配这一份；`profile_hist` 也按单一设备累积。运行目录 `run_info.json` 里两侧 `profile_copied_from` 是同一个文件——即"总线侧和分路侧用同一台设备的画像"。
⇒ 总线上有 N 台要监测的设备，就需要 N 次运行（或改代码支持多画像）。本案例总线同时有整流设备、45 kW 大负荷、电机 + 电容组，只能识别整流设备那一台。

**限制 2：σ 收缩下限决定判别半径（单样本 23 %）**
`_REL_FLOOR = {d_i 15 %, d_p 15 %, d_q 25 %, peak 30 %, dur 50 %}`，且 `min_confidence=0.3` 对应的实际门槛是 **D²/维 ≤ 2.41**（`conf = exp(−D²/14)`）：

| 设定 | 生效的 D²/维 上限 |
|---|---|
| `min_confidence = 0.5` | 1.39 |
| **`min_confidence = 0.3`（默认）** | **2.41** |
| `min_confidence = 0.1` | 4.61 |
| `d2_max = 9`（默认） | 9.02 ⇔ `min_confidence ≈ 0.011` |

⇒ **`d2_max=9` 实际上被 `min_confidence=0.3` 压制**，真正卡人的是 2.41。单样本时单维允许偏离：ΔI/ΔP **23 %**、ΔQ 39 %、峰值比 47 %、dur 78 %。
⇒ 与目标设备幅值差 <23 % 的其它设备，只能靠 ΔQ / 分相 / 峰值比区分。
⇒ 这也解释了第 167 轮 14:55:33 那次 −28 A 他负荷被判 STOP 0.46：幅值差 20 %，正好在半径内。

**限制 3：小功率设备被噪声主导**
候选门槛 = `max(0.5 × 画像幅值, k_sigma × σ_pre)`，`k_sigma=4`。3 kW 设备的 0.5×门槛只有 1.5 kW / 4.3 A，而工业母线的 ΔQ 噪声（本例 ±60 var、现场更大）足以产生 10 σ 的偏差（σ_dq 绝对下限仅 **5 var**）。本实验里 B 的结果在 confirmed / rejected 之间摆动就是这个原因。
⇒ 经验边界：**设备容量 < 母线容量的 ~5 % 时，单样本画像不可靠**；要么把 `k_sigma` 与 σ 绝对下限按现场噪声标定，要么不做。

**限制 4：特征只有稳态量，没有谐波/波形**
7 维特征全是"过渡前后电平差 + 峰值比 + 时长"。两个功率因数相近、相别相同的负荷在特征空间里几乎重合（表 2 的 F）。
本案例的设备是谐波源（设备侧 THD_I 50~60 %，第 170 轮实测它在总线上贡献 **+15 A 谐波电流**：停机 16~18 A、运行 27~33 A），而线性负荷贡献 0——**这是现成可用的最强判别维度，但当前代码完全没有用**。

**限制 5：单状态机 on/off，多档位/部分负荷不适配**
同一台设备只开 50 % 时：低于候选门槛，**不成候选**（静默漏报）；70 %：rejected（conf 0.261）；85 %：confirmed（0.651）。即单份画像的有效区间约 **85 %~115 %**。
变频器/多档位设备（如本例的 40 % 档）必须为每个档位各出一份画像，或改成"档位识别"。

**限制 6：只有启动画像时，停机不会报（且会被判成 START）**
实验 5：设备运行 40 s 后停机，画像只有 `startup` ⇒ 停机候选被判成 `START`、D²/维 97.02、rejected（同时带 `state_mismatch`）⇒ **停机漏报，状态机永远停在 on**。补上 `shutdown` 画像后：`STOP confirmed 0.710`（D²/维 0.68）。
⇒ 每台设备**必须双向提取画像**，否则只能看"启动"。

**限制 7：量纲 / 接线 / 相序错了是"静默无候选"，不报错**
把 A 画像的 ΔI、ΔP 各 ×250（模拟设备侧忘记填 CT）⇒ **无候选**，因为候选门槛 `0.5×|ΔI合成|` 变成 8000 A，现场根本达不到。`_evaluate_profile` 只会提示"两侧变比不同不影响匹配"，不会阻止。
同理：`phase_map` 错 ⇒ D² 变大；3p3w 未重构 ⇒ 跳过 ΔIb；`nilm.quantity` 与画像不一致 ⇒ 直接不运行（这一条有明确报错）。

**其它行为性事实（影响工程部署）**

- 检测窗需求 `_profile_window_need = pre + dur + 2·post·max_scale + 10`：本案例 3000/3000、×8 ⇒ **73281 周波 ≈ 24.4 min** 的缓存；实测回放 20 min 数据耗时 250 s（比实时快 ~4.8×）。小设备（10/50）约 1.8 k 周波，可忽略。
- 事件延迟：终点后还要等 `post_cycles` 才输出（本案例 **60 s**）；频繁启停设备会被 `min_gap_cycles`（本案例 500 周波 = 10 s）合并。
- 同时刻发生的两件事无法分离：A + 电容组同时投 ⇒ A 的候选 D²/维 1136.6 rejected（实验 4）。而 A 之前 10 s 有一次 +60 A 他负荷台阶时，v0.99.25 的变点截断仍能 confirmed 0.853。

---

### 四、适用性矩阵（按现场常见设备类型）

| 设备类型 | 可用性 | 关键条件 | 实测/证据 |
|---|---|---|---|
| 整流/变频电源、UPS（本例） | **✅ 推荐** | pre/post 覆盖斜坡（≥ 2× 过渡时间）；双向画像 | 本例 0.921 |
| 定速电机、水泵、风机（直接启动、5~7 倍冲击） | **✅ 可用** | `peak_ratio` 是强特征；注意冲击峰会把 dur 量短 | 峰值比 σ=30 % |
| 电容补偿组 | **✅ 可用** | ΔQ 是强特征（本例 conf 0.969）；**避免与目标设备同刻投切** | 实验 4 |
| 大功率电阻炉/加热 | **✅ 可用** | 需 ≥ 母线容量 5 %；ΔQ≈0 使其难以与其它电阻负荷区分 | 表 2 的 F |
| 小功率加热/照明（< 5 % 母线） | **❌ 不推荐** | 噪声主导，σ 绝对下限过小 | 表 1 的 B 不稳定 |
| 多档位 / 变频调速多工况 | **⚠️ 单画像不可用** | 每档一份画像，或改代码支持"档位" | 50 % 漏、70 % 拒、85 % 通过 |
| 频繁启停（空压机、循环泵） | **⚠️ 可用但需调窗** | pre/post 缩小（如 10/50~10/200）、双向画像、`min_confidence` 适当放宽、注意 post_wait 延迟 | 表 1 的 E |
| 与目标设备同功率、同相别的他负荷 | **❌ 不可靠** | 只能靠 ΔQ/谐波；本例余量 1.41× | 表 2 的 F |
| 三相不平衡的单相负荷 | **✅ 可用（反而更好）** | 分相 ΔI 与 `phase_map`；3p3w 时 ΔIb 被跳过 | 代码 `skip=("d_ib",)` |

---

### 五、迁移到一台新设备的标准作业流程（SOP）

1. **取设备侧录波**（分路 CT 或临时表），至少覆盖 **3 次启动 + 3 次停机**；采样率按现场（本例 10 kHz），列映射正确。
2. **提取画像**：设备画像提取界面，标签用真值表或自动定位；`pre_cycles / post_cycles` 取 **≥ 2 倍设备过渡时间**（本例 25 s 过渡用 3000/3000；泵 6 s 用 10/600；电阻 1 s 用 10/200）。
3. **检查 μ/σ**：`n ≥ 3` 时看 σ 是否收到实际重复性（本版本相对下限仍会兜底 15 %/25 %，见改进 3）；`dur_cycles` 的 σ 不要低于 50 %（在线终点估计本身有 ±50 % 误差，见限制 2）。
4. **同段总线验证**：拿**同一时段**的总线录波回放（本例 12:08 那轮就是这么做的），确认结论为 `confirmed` 且 `D²/维 < 1`。
5. **反向验证**：用这份画像去跑其它已知事件（他负荷、电容、电机），确认全部 `rejected` 且余量 ≥ 2 倍（本例 F 只有 1.41 倍，属警戒）。
6. **上线观察**：看 `output/{时间}/nilm/nilm_profile_candidates_{日期}.csv` 的 `status/flags/c_*`，按 `c_*` 最大的那一维定位问题（`d_q` 大 ⇒ 无功不像；`dur` 大 ⇒ 终点/窗长；`sign_flip` ⇒ 前后窗跨了别的动作）。
7. **参数**：`min_confidence` 默认 0.3（D²/维 2.41）；要更灵敏可降 0.2（3.22）或 0.1（4.61），但要同步接受误报增加；`d2_max` 只在 `min_confidence < 0.011` 时才真正生效。

---

### 六、改进建议（按投入产出排序）

1. **加谐波特征（最高 ROI）**：在 `CycleFeatures` 里补 2~13 次谐波电流 RMS（基波 DFT 已有，成本低），画像加 `d_ih` / `thd_i` 两维。本例设备贡献 +15 A 谐波电流而线性负荷为 0，可把表 2 的余量从 1.41× 拉到 10× 以上。
2. **多画像支持**：`profile_path` 改为"画像目录/列表"，`_profile` 改 dict[device_id]，`_evaluate_profile` 对每个画像算 D² 取最优 + 每设备独立状态机；同时解决多设备共存与相互干扰。
3. **σ 自适应**：绝对下限按背景噪声（如 `4×σ_noise`）标定而不是固定 5 W；相对下限按样本数收缩（n=1→15 %，n≥3→实际 sd，但 **dur 保持 50 %**）。v0.99.24 之前单样本 14:55:33 的误判就属这一类。
4. **档位/部分负荷**：允许在匹配时对画像幅值做 α∈[0.85,1.15] 的缩放搜索（或显式档位表），把"同一设备不同出力"纳入；否则明确提示"仅识别 100 % 档"。
5. **量纲与几何自检**：画像加载时用 `|ΔP| vs √3·U·|ΔI|` 的比值、ΔQ/ΔP 夹角做一次合理性检查；运行时如果所有候选幅值都 < 0.5×画像幅值，主动提示"疑似量纲/CT 不一致"，避免静默无事件。
6. **状态初始化**：对"中途开始录制"的文件，用稳态特征（基波电流水平 + 谐波电流，见第 170 轮）判一次初始 on/off，避免 `unknown` 状态下第一个事件漏检或错检。
7. **延迟优化**：终点后不必等满 `post_cycles`，可先出初判（`low_confidence`）再回填，改善循环设备的实时性。

---

### 七、结论

- **能用于其它设备**：算法链路（周波特征 → 多尺度候选 → 变点截断 → 7 维马氏距离 + 轨迹模板 → 状态机）不含任何针对"整流/变频设备"的假设，实验里电阻、电容、变频 40 % 档、循环泵用各自画像都 confirmed（0.74~0.97）。
- **但必须"一设备一画像、一工况一画像"**：换设备＝重新录波、重新提取、重新验证；不能用本案例的画像去识别别的设备（表 2 中 B/D 直接无候选，C/E/F 被拒但 F 只有 1.41 倍余量）。
- **能否用好的判据**：设备容量 ≥ 母线 5 %、画像窗 ≥ 2× 过渡时间、启停双向样本各 ≥ 3、PT/CT 与接线量纲一致、与其它负荷的 ΔQ/谐波差异明显。五条缺一条，就应预期"漏报或误报"而不是"精度略降"。
- **最值得做的两件事**：加谐波特征、支持多画像。这两项做完，本算法才能从"单台设备验证"走到"整条母线多设备监测"。

## 第 172 轮专题：bus-2-启停.csv（总线侧）与 bus-3-正常.csv（分路侧）两段数据里到底有没有该设备的启停

**先确认数据身份**（`tmp/run_info.json`，created 2026-10-30 16:50:36）：

| 侧 | 播放的文件 | 时间范围 | 长度 |
|---|---|---|---|
| 总线侧 | `化工行业-海湾化工-bus-2-启停.csv`（source_id 0） | 2021-05-25 12:36:35.766 → 12:53:14.742 | 977 个 1 s 点 = 49 949 周波（16.6 min） |
| 分路侧 | `化工行业-海湾化工-bus-3-正常.csv`（source_id 1） | 2021-05-25 12:51:12.203 → 13:07:51.179 | 977 个 1 s 点（16.6 min） |

- 两侧**不是同一段数据**：只有 12:51:12–12:53:14 这 2 min 重叠，其余各播各的。
- 两侧检测配置**实质相同**：`quantity=i`、`window_cycles=3000`、`min_gap_cycles=500`、`channels=[A]`、`transform` 全是 PT=4 / CT=250 / 3p3w / A 相取反 / 3P3W 重构；`algorithms.profile={"enabled":true}`，其余参数走默认（d2_max 9、min_confidence 0.3、k_sigma 4、margin 1.5、lambda_rel 0.1、state_check 1、phase_map 1、max_scale 8、min_scale 0.25）。差异只在 `source.path`、`events.u_nom`(220 vs 57.74)、`nilm.rel_tol_pct`/`min_delta_pct`（自动调参项）、`branch.enabled`、`processing.error_window_s` —— 都不影响画像匹配。
- 两侧加载的是**同一份画像**（`profile_bus_/profile_branch_profile_device_20261030_084954.json`，md5 相同），来自 `dev1.csv`，PT=CT=1、3p4w：
  - 启动 μ：ΔIa/Ib/Ic **+35.95/+31.20/+42.49 A**、ΔP **−23 933 W**、ΔQ **+902 var**、峰值比 **1.59**、持续 **1271 周波（25.4 s）**，σ = 5.39/4.68/6.37/3590/225/0.48/635
  - 停机 μ：**−36.26/−31.54/−42.23 A**、**+23 881 W**、**−934 var**、峰值比 1.0、**305 周波（6.1 s）**
  - 该画像幅值与总线幅值**可直接比较**：第 169 轮在 bus-1 上实测 15:00:08 的设备启动为 +35 A，与画像 36 A 一致（两侧都不是二次侧原始值）。

---

### 结论（先说）

1. **总线侧 `bus-2-启停.csv`：没有该设备的启动，也没有停机。** 段内只有三类**他负荷**动作 + 电容组频繁投切，见下表。
2. **分路侧 `bus-3-正常.csv`：没有该设备的启停，连一次负荷台阶都没有**，全程只有电容组投切（Q 在 −28 / −4 / +16 kvar 之间跳，ΔP ≈ 0，ΔI合成 最大 17.5 A）。
3. **两段的稳态都落在"设备在运"那一档**，与"设备停机"档差得很远（见证据 3）⇒ 录制期间设备一直在运行，段内本来就不该出现启停。工具报 0 条 profile 事件（总线侧 3 条候选全部 rejected）是**正确**的。

---

### 证据 1：段内全部动作 vs 画像签名

| 事件 | 时刻 | ΔIa / ΔIb / ΔIc (A) | C−A | ΔP | ΔQ | 谐波电流变化 | 形状 |
|---|---|---|---|---|---|---|---|
| **E1 45 kW 线性负荷投入** | 12:41:15（4 s 斜坡） | **+59.5 / +59.7 / +59.1** | −0.7 | **−44.7 kW** | −0.3 kvar | 27.7 → 25.8 A（**−2.0**） | 4 s 斜坡，峰值比 1.03，保持 66 s |
| **E2 同一切除** | 12:42:21（3 s） | −54.4 / −55.3 / −54.4 | −0.1 | +43.5 kW | +0.3 | 25.3 → 26.4 A（+1.0） | 3 s 回降，峰值比 1.00 |
| **E3 13 kW 谐波型负荷缓升** | 12:49:06（20 s 升） | +21.9 / +21.7 / +19.7 | −2.2 | −12.4 kW | −0.6 | 27.4 → 44.2 A（**+16.8**） | 20 s 升 / 18 s 平 / 27 s 降，峰值比 0.96 |
| 电容组投切（两段都有，合计 30+ 次） | 全程 | 5 ~ 12 | ±3 | ≈ 0 | **±25 / ±44 kvar** | ≈ 0 | 2~3 s 阶跃 |
| **画像设备启动** | — | **+36.0 / +31.2 / +42.5** | **+6.5** | **−23.9 kW** | **+0.9 kvar** | **+15 A** | **25.4 s 斜坡，峰值比 1.59** |

三条判别同时不成立的三处：
- **E1/E2 是设备的 1.65~1.9 倍**（电流 59.5/36.0 = 1.65，功率 44.7/23.9 = 1.87），而且**三相平衡**（C−A = −0.7，设备是 +6.5）。
- **E1/E2 完全不产生谐波电流**（−2.0 A）：这台设备是谐波源，第 170 轮在 bus-1 上标定过——它启动时总线谐波电流从 17→32 A（**+15 A**）。E1 投入 60 A 而谐波电流反而略降 ⇒ 纯线性负荷（电机/加热）。
- **E3 的幅值只有设备的 0.55~0.7 倍**（21.9/36 = 0.61、12.4/23.9 = 0.52），三相平衡，且 65 s 后自己回落；它的谐波增量 +16.8 A 与设备同量级，是三件事里**最像**这台设备的一件，但幅值与"启停后保持运行"的行为都不符（更像另一台变频/软启设备短时加载）。

---

### 证据 2：为什么"没有启停"而不是"漏检"

| | 本段 bus-2 | 本段 bus-3 |
|---|---|---|
| 候选门槛（0.5 × 画像 \|ΔI合成\|） | 31.9 A | 31.9 A（k_sigma·4σ 只有 0.2 A，故取 31.9） |
| 段内任意窗长、任意时刻的最大 \|ΔI合成\| | +103.1 A（12:41:16 大负荷） | **+17.5 A（13:06:15）** |
| 是否生成候选 | 3 条（12:40:38 / 12:41:16 / 12:42:21） | **0 条**（连门槛都没到） |

**总线侧 3 条候选（`tmp/nilm/nilm_profile_candidates_20261030.csv`）**

| 时刻 | scale | ΔIa/Ib/Ic | ΔP | ΔQ | dur | D²/维 | status / flags |
|---|---|---|---|---|---|---|---|
| 12:40:38.002 | 2.0 | +62.2/+62.7/+58.8 | −44 896 | −25 790 | 5999 | **2003.7** | rejected（d2_exceeds, ambiguous_direction, window_crowded） |
| 12:41:16.782 | 0.25 | +61.3/+61.4/+58.8 | −44 376 | −25 770 | 1 | **1789.7** | rejected（d2_exceeds, ambiguous_direction） |
| 12:42:20.862 | 0.25 | −53.6/−55.8/−51.2 | +43 679 | +423 | 39 | **14.4** | rejected（d2_exceeds） |

- 三条的 D² 都被 **ΔQ** 或 **幅值** 顶爆（贡献：ΔQ 占 11 318、ΔP 363、ΔIa 284）。d2_max = 9，实际 14.4 ~ 2003.7，最接近的 12:42 也差 1.6 倍。
- 12:41:16 / 12:40:38 两条的 ΔQ = −25.8 kvar、dur = 1 周波，是被 **5 s 之后（12:41:21）的电容投切污染**了特征后窗（见"附带发现"）。即使用干净窗口重算（ΔQ −0.33 kvar、dur 200 周波），D²/维 = **17.2**、conf 0.0002，**仍然拒绝**——结论不变。
- 12:42:21 那条（切除）已用干净窗口，D²/维 14.4，主要贡献 ΔQ 33.8 + ΔP 30.5 + ΔIb 22.3（幅值 1.8 倍）。

**分路侧：全程最大电流台阶只有 17.5 A**（13:06:15，一次小负荷 +13 A / −3.6 kW），连"画像幅值一半"的候选门槛都没到 ⇒ 引擎不会进入匹配环节，所以 CSV 里 `source_id=1` 一条 profile 候选也没有。这不是漏检：这段里根本没有任何量级接近设备的动作。

---

### 证据 3：稳态指纹——两段都像"设备在运"，不像"设备停机"

| 时段 | P | Q | I A/B/C | THD_I | 谐波电流（THD×I） | C−A |
|---|---|---|---|---|---|---|
| **设备停机**（bus-1，14:53–14:58，同站已知） | −47.5 kW | −7.7 | 64.4/72.8/69.5 | 25.5/25.2/23.9 % | **16.0/18.2/16.9** | +5.1 |
| **设备运行**（bus-1，15:00:45–15:01:00） | −58.7 kW | +0.8 | 80.1/92.4/90.6 | 42.0/38.7/37.4 % | **33.6/35.7/33.8** | +10.5 |
| **设备运行+电容**（bus-1，15:01:10–15:05:50） | −57.2 kW | −23.9 | 84.7/93.8/95.5 | 37.2/35.5/33.8 % | 31.5/33.3/32.2 | +10.8 |
| **bus-2 电容切除**（12:50:12–12:51:05） | **−57.3 kW** | −3.9 | **76.0/87.8/85.8** | 35.0/32.5/31.6 % | 26.6/28.5/27.1 | **+9.8** |
| **bus-2 电容投入**（12:52:58–12:53:10） | **−58.1 kW** | −28.1 | **84.4/94.8/95.9** | 29.7/29.1/26.9 % | 25.1/27.6/25.7 | **+11.5** |
| **bus-3 电容切除**（13:01:00–13:02:50） | **−57.3 kW** | −4.0 | **76.0/87.7/85.9** | 35.3/32.8/31.8 % | 26.8/28.7/27.3 | **+9.8** |
| **bus-3 电容投入**（13:03:20–13:05:30） | −58.0 kW | −12.5 | 80.7/90.5/89.3 | 33.4/31.6/30.7 % | 27.0/28.6/27.4 | +8.6 |

- P（−57.3~−58.1 kW）与设备运行档（−57.2~−58.7 kW）**几乎重合**，离停机档（−47.5 kW）差 10 kW；
- 电流矢量（76/88/86 与 84/95/96）与运行档（80/92/91、85/94/96）一致，离停机档（64/73/70）差 12~18 A；
- C−A（+9.8~+11.5）与运行档（+10.5~+10.8）一致，停机档只有 +5.1；
- 唯一不完全吻合的是谐波电流（26~28 A，运行档是 31~34 A）——说明这段时间除本设备外还挂着别的谐波负荷（E3 已经证明这里有第二台谐波源），但整体水平仍远高于停机档的 16~18 A。

⇒ **两段录制期间设备应处于运行状态**：既然全程在运，段内就没有"启动"可识别，也不会有"停机"。

---

### 证据 4：反证——把设备启动"注入"这两段，两侧都能认出来

用同一套 `detect_profile` + 同一份画像 + 同一组参数，把画像启动签名（+35.95/31.20/42.49 A、25.4 s 斜坡、峰值比 1.59、−23 933 W、+902 var）叠到：

| 侧 | 注入时刻 | 结果 |
|---|---|---|
| 总线侧 bus-2 | 12:45:00 | **12:45:09 START confirmed，conf 0.882、D²/维 0.25、ΔIa +38.3、ΔP −23 516 W** |
| 分路侧 bus-3 | 13:00:00 | **13:00:09 START confirmed，conf 0.909、D²/维 0.19、ΔIa +34.9、ΔP −23 786 W** |

⇒ 画像、门限、多尺度搜索、窗长在这两段数据上都工作正常，**0/3 事件的根因是数据里没有这个动作**，不是配置或代码。

---

### 证据 5：其它算法看到了什么（交叉验证）

`tmp/nilm/nilm_events_20261030.csv` 共 219 条（source 0：122 条；source 1：97 条），**没有一条 profile 事件**。其中 6 种通用算法（cusum / steady_state / two_window / glr / median_diff / threshold）都在 **12:41:14** 与 **12:42:20** 报了通道 A 的负荷投切（单周波/10 周波窗，ΔI +26.7 A、ΔP −7.6 kW——只覆盖 4 s 斜坡的起点）。也就是说：**工具确实"看到了"这两次负荷动作**，只是它们在画像空间里离这台设备很远（D²/维 14~2000），被正确拒绝。

分路侧最大的一条是 13:06:16 的小负荷（ΔI +13 A、ΔP −3.6 kW），同样与画像无关。

---

### 附带发现（值得改代码的一处）

**`quantity='i'` 时，纯无功阶跃（电容投切）不会成为变点。** `detect_profile` 里 `change_points(x, ...)` 的 `x` 只在 `i4[0]`（合成电流）与 `p4[0]`（有功）之间二选一，ΔQ 的阶跃（本轮 12:41:21 投了 25 kvar，合成电流只变 4~6 A）看不见，于是 12:41:16 那条候选的后窗把电容投切吃了进去，ΔQ 从 −0.33 kvar 变成 **−25 770 var**，dur 从 200 周波缩成 **1 周波**。

本轮不影响结论（干净窗口算出来仍是 D²/维 17.2、拒绝），但**"设备启动 + 电容同投"**这种现场常见组合会因此把 ΔQ 特征毁掉——如果事件本身接近画像（比如另一台同类设备启动叠加电容投切），就会真漏检。建议：`quantity='i'` 时把 `|ΔQ|` 超限也纳入 `change_points`（或对 ΔQ 单独跑一次截断，取两者并集）。

---

### 给现场的判断与建议

1. **两段都没有该设备的启停**：bus-2 里是 45 kW 线性负荷的一次启停（12:41:15–12:42:23）+ 13 kW 谐波负荷的一次短时加载（12:49:06–12:50:11）；bus-3 里只有电容组投切。两段稳态都在"设备运行"档 ⇒ 设备整段在运。
2. 若您认为 **12:41 那台 45 kW 就是该设备**：它与画像差 1.65~1.9 倍、三相平衡、完全不带谐波，而同一台设备 15:00:08 在总线上实测是 +35 A / +15 A 谐波电流。要么是另一台同类设备，要么这份画像（取自 `dev1.csv` 15:00:50 的 1 次启动 + 14:39:31 的 1 次停机）不代表它现在的工况——按该分路同期数据重提画像（≥3 次启停）才有意义。
3. 若 **12:49 那台 13 kW 谐波负荷**也是同一类设备（例如第二台变频），当前版本一次只能挂一份画像（`nilm.profile_path` 单值），需要多画像支持（第 171 轮"改进 2"）。
4. 要验证该设备的启停，**设备侧与总线必须是同一时段**：本轮分路侧播的是 `bus-3`（12:51–13:07，本身就是"正常"段，没有负荷动作），与总线侧 12:36–12:53 只有 2 min 重叠；`dev1.csv`（14:35–15:05）与这两段更是完全不重叠。
5. 两段都是"半路开始录制"，状态机只能从 `unknown` 起步，第一个事件无法借状态先验——这也是第 170 轮提过的"用稳态指纹（谐波电流 + 电流矢量）初始化设备状态"的适用场景。

---

## 第 173 轮专题：画像两项改进落地——① 谐波电流特征 `d_ih`；② 多画像同时加载（v0.99.26）

> 依据：第 171 轮（`61619b5`）给出的算法可移植性改进排序——**谐波特征 ROI 最高**（把"同功率的线性负荷"与"整流类设备"分开）、**多画像次之**（一台机器挂多台设备的画像，替代"打补丁式调门限"）。本轮在代码里实现这两项，并保持旧画像 / 旧配置向后兼容。

### 一、为什么是这两项（第 171/172 轮的实测依据）

| 现象 | 数据 | 说明 |
|---|---|---|
| 谐波电流是设备"在运/停机"的强指纹 | 停机 16.0~18.2 A，运行 31.5~35.7 A（同站、`THD_I×I`） | 与功率、电流相比，几乎不受他负荷投切影响 |
| 同样幅值的有功/电流，线性负荷与整流设备无法区分 | bus-2 12:41 的 45 kW 负荷：ΔI +59.5/+59.7/+59.1 A、ΔP −44.7 kW，谐波电流 **−1.7 A（不变）** | 7 维下这个事件靠 ΔQ/ΔP/ΔIb 三条各出 ~30 才凑到 D²/维 17.2（余量 1.9×）；而第 171 轮构造的"完全线性仿冒"（ΔI/ΔP/ΔQ 全对）7 维 **D²=0、置信度 1.0，必然误报** |
| 一台总线挂多台设备是常态 | bus-2 的 12:49 还有一台 13 kW 的谐波型负荷（Δ谐波 +18.3 A） | 单画像只能认一台，第二台只能靠"不是它"拒绝，无法给出设备级事件 |

### 二、实现（代码级）

#### 1. 逐周波谐波电流（`elec_tool/nilm.py::CycleFeatures`）

- 每周波对三相电流各做一次 `rfft`，取 **2~13 次**（`HARM_ORDERS`，GB/T 14549 关注的次数）幅值，合量 = `√Σ I_k²`（A）；
- `push()` 返回值新增 `ih`（4, M），行序同 `p/q/i`：**total 行＝三相平均**（线性可加，且与实时 `harmonic` 文件的 `THD_I×I` 同口径），其余为各相；
- 开销：6400 Hz/50 Hz 时 n=128，单周波 3×128 点 rfft，实测比 P/Q 的单频 DFT 还便宜；`CycleFeatures(..., harmonics=False)` 可关；
- 诊断量 `event_features()["thd_delta"]` ＝ `ΔIh / |ΔI合成|`（增量 THD，只进诊断，不进 D²）。

#### 2. 画像第 8 维 `d_ih`（`elec_tool/nilm_profile.py`）

```python
FEATURES = ["d_ia","d_ib","d_ic","d_p","d_q","peak_ratio","dur_cycles","d_ih"]   # 新维度一律追加在末尾
LEGACY_FEATURES = FEATURES[:7]                                                    # v0.99.25 及更早的画像
_REL_FLOOR["d_ih"] = 0.15 ; _ABS_FLOOR["d_ih"] = 2.0 A                            # σ 下限：15% / 2 A
```

- 口径与 ΔP/ΔI 完全一致：**后窗中位数 − 前窗中位数**（同一 `pre_lo/post_hi` 截断），因此"设备启动+他负荷同投"时仍按同一几何取数；
- **追加在末尾**是关键：旧画像的 μ/σ 下标 0~6 不变，`peak_ratio=5`、`dur_cycles=6` 等硬编码下标全部继续成立；
- 提取链：`load_cycles()` 多返回 `ih4` → `build_profile()` 传给 `event_features()` → `fit_group()` 自动多算一维 → 画像 JSON 新增 `features[7]` 与 `harmonic{orders,unit,feature}` 元信息。

#### 3. 旧画像 / 旧配置向后兼容（重点）

| 场景 | 处理 |
|---|---|
| v0.99.25 及更早的 7 维画像 | `profile_feature_names()` 返回 7 维；`match_event` 只在前 7 维上算 D²（等价于"该维不提供证据"），`d` 仍取 7 ⇒ **置信度口径与旧版完全一致**，不因新维度稀释 |
| 头部 `features` 被写成 8 项、μ/σ 仍是 7 项（半新不旧） | 以 μ 实际长度为准按 7 维解释，不报错（此前会拒绝加载） |
| 特征名不是当前版本的**前缀** | 仍拒绝加载（防止不同特征定义混用） |
| `nilm.profile_path` 单路径字符串（旧配置） | 照旧工作；含 `;` 时自动拆成多画像 |
| 旧 `nilm_events_*.csv` | 新增列 `delta_ih_a`，`_rotate_if_header_differs` 自动转表头；读回时缺列取 0 |
| 旧候选 CSV | 新增列 `device_id` / `d_ih` / `c_d_ih`，同样自动转表头 |

#### 4. 多画像（`NilmDetector`）

```python
cfg.nilm.profile_path  = "output/nilm/profile_A.json;output/nilm/profile_B.json"   # ; 分隔（向后兼容单值）
cfg.nilm.profile_paths = ["a.json", "b.json"]                                       # 或列表（等价，去重保序）
NilmConfig.MAX_PROFILES = 8                                                          # 超出在 validate 时报错
```

- 每个画像一个 slot：`{path, key(路径+mtime), profile, err, state, last, hist, last_end, notes}`；
  **状态机、去重（`last_end`）、候选历史、诊断全部独立**；一个画像文件坏掉不影响其余；
- 未变化的画像按 (绝对路径, mtime) 复用旧 slot ⇒ 改窗口 / 改别的算法参数做热更新时，设备状态不会被清零；
- `summary()["profile"]` 保持旧结构（＝第一个画像，`path/loaded/error/device_state/summary/last`），新增
  `count/loaded_count/paths/profiles[]`；旧界面 / 旧 CLI / 旧测试不用改；
- **不做跨设备压制**：多画像各报各的（`device_id` 区分）。曾设计"同一时刻（容差 `max(10, post/10)` 周波）只留 `(accepted, confidence)` 最优"，实现前放弃——两台设备真同时启动时会被误删，而"同一台阶被两个画像同时命中"本身就是有价值的诊断信息（提示两个画像过于相似）；
- 同一 `device_id` 挂两次会在 `notes` 里提示（两个 slot 仍各自检测）；
- `_evaluate_profile()` 的体检（各相有功符号 / 死相）、PT/CT 变比提示、接线提示改为"每个画像提示一次"（键＝device_id）。

#### 5. 消费端同步

| 位置 | 改动 |
|---|---|
| `app/server.py`（运行目录） | 逐个复制画像 → `nilm/profile_{侧}{序号}_{原名}.json`（单画像保持旧名 `profile_{侧}_{原名}.json`）；`run_info` 记 `profile_file`（首个，兼容）/`profile_files`/`profile_copied_from_all`/`profile_error`（逐条） |
| `app/static/app.js` | 「画像文件路径」提示多个用 `;` 分隔；画像状态行按 `profiles[]` 逐行显示（设备、样本数、状态机、是否含谐波维、最近候选、重复 device_id 提示）；「画像提取 → 填入本侧」由**覆盖**改为**追加**（已有别的画像时不冲掉） |
| `elec_tool/nilm.py::NilmWriter` | 事件 CSV 加 `delta_ih_a`；候选 CSV 加 `device_id`、`d_ih`、`c_d_ih` |
| `tools/nilm_profile.py` | 按画像实际维度打印 μ/σ（含 `d_ih`） |
| `tools/nilm_profile_diag.py` | 适配 `load_cycles()` 的 8 元组 |
| `tools/nilm_replay.py` | 画像诊断逐画像打印（多画像时带 `[1]/[2]` 前缀） |

### 三、验证

| 项 | 结果 |
|---|---|
| 新增 `tests/test_r173_harmonic_multi_profile.py` | **17 项全通过**（解析解谐波电流、ΔIh 口径与缺省、8 维取整/存盘/加载、7 维旧画像加载并跳过、半新不旧文件、未知特征名拒绝、谐波维把"线性仿冒"从 conf 1.0 压到 0.16、多画像独立状态机与 device_id、坏文件隔离、单画像旧字段兼容、候选 CSV 列） |
| 全量回归 | **493 passed / 1 skipped**（476 → +17），153 s |
| 真实数据回放（`tmp/` 两段，1 s 序列按 50 周波/秒展开） | bus-2：7 维 3 候选 / 8 维 3 候选，均 rejected；bus-3：0 候选（7 维与 8 维一致）⇒ **结论不变** |
| 注入检验（同一份画像，叠加启动签名） | bus-2 12:45:00：7 维 0.743 / 8 维 0.770 confirmed；bus-3 13:00:00：7 维 0.745 / 8 维 0.772 confirmed ⇒ 加了新维度后**检出能力没有退化** |

**用真实设备画像复核谐波维的判别力**（`tmp/nilm/profile_bus_profile_device_20261030_084954.json` 的 7 维 μ/σ，补一维 `μ=+14 A / σ=max(0.15×14, 2)=2.1 A`，即第 169/170 轮实测的设备谐波电流贡献）：

| 候选向量 | 7 维（旧画像） | 8 维（新画像） |
|---|---|---|
| **线性仿冒**：ΔI 35.9/31.2/42.5 A、ΔP −23.9 kW 与设备完全相同，ΔQ=0、峰值比 1.05、持续 200 周波、**ΔIh=0** | D²/维 **2.70**、conf **0.259**（险过 `min_confidence=0.3`，余量仅 14 %） | D²/维 **5.47**、conf **0.065**（拒识余量 4.6×；贡献 `d_ih=24.8` 首次超过 `d_q=16.0`） |
| 真设备：同一向量但 **ΔIh=+14** | — | D²/维 2.70、conf **0.307**（接受；新维完全对得上 ⇒ 不再因"维数变了"被误伤） |
| 谐波型他负荷（12:49 样式）：ΔI 22.6 A、ΔP −12.9 kW、ΔQ −0.5 kvar、ΔIh +18.3 | D²/维 9.48、conf 0.009 | D²/维 8.63、conf 0.013（仍拒绝：ΔI/ΔP 幅值只有设备的 0.55~0.63 倍，谐波对得上也救不回来） |

读法：**谐波维专治"线性负荷冒充"**（同幅值同功率的电阻/电机），对"另一台整流设备"不额外加分也不减分——后者靠 ΔI/ΔP 幅值区分。这也解释了 `D²/维` 分母 7→8 的副作用（同一 D² 被摊薄 12.5 %）：真设备的置信度反而略升，而线性仿冒的置信度从 0.259 掉到 0.065。

**多画像真实数据回放**（同一份 8 维画像 ＋ 一个"同型号小一档"的派生画像 B：ΔP/ΔI/ΔIh 全部 ×0.5，device_id 不同）：

| 数据集 | 画像 A（实录画像） | 画像 B（×0.5 派生） |
|---|---|---|
| bus-2（12:03–12:19） | 候选 3 / accepted 0，D²/维 **1757.1 / 1579.2 / 15.6**（与单画像回放逐位一致） | 候选 6 / accepted 0；12:49:06 那条谐波型负荷 D²/维 **4.8**、conf **0.090**（只差 `min_confidence=0.3` 就命中），贡献前二 `d_q=24.8`、`d_ih=8.96` |
| bus-3（12:31–12:47） | 候选 **0**（与单画像一致） | 候选 2 / accepted 0 |

结论：① 多画像并挂**不改动**任一画像的候选集合（A 的三条 D²/维与第 173 轮单画像回放逐位相同）⇒ 无串扰；② 派生画像 B 在 12:49 那条谐波负荷上 `d_ih` 贡献升到第二位（8.96），说明**谐波维确实在区分"谐波源"与"线性负荷"**，但它同时要求幅值对得上（ΔP/ΔQ），单靠谐波不足以命中——这正是设计意图。

**实测事件的 `d_ih` 读数**（1 s 回放，候选明细）：

| 候选 | ΔIh (A) | 说明 |
|---|---|---|
| bus-2 12:40:38（45 kW 负荷，粗尺度候选） | **−2.37** | 完全不带谐波 ⇒ 线性负荷 |
| bus-2 12:41:17（45 kW 负荷投入，细尺度候选） | **−2.35** | 同上 |
| bus-2 12:42:22（45 kW 负荷切除） | **+1.19** | ΔIh 反号且很小（切除后谐波略降）⇒ 同样是线性负荷 |
| （参考）bus-2 12:49:06 的 13 kW 谐波型负荷 | 60 s 中位数 **+18.3** | 这条负荷没到候选门槛，故没有 d_ih 读数；它说明"谐波维不是只有本设备有"——见限制 3 |

### 四、已知限制（写进文档，不再当作 bug）

1. **单样本画像的 σ 靠下限**：`d_ih` 的相对下限 15%、绝对下限 2 A。第 171 轮构造的"完全线性仿冒负荷"（ΔI/ΔP 与设备完全相同）在 8 维下 D²≈29、置信度 0.16 < `min_confidence` 0.3 ⇒ 被拒识；但若设备真实谐波贡献逐次波动 ±20%，σ 会随样本变大、这条证据随之变弱——**建议每次 ≥3 个启停样本**（工具 notes 里已提示）。
2. **`D²/维` 的分母随维度变化**：7 维 → 8 维，同样的证据每维均值下降 12.5%。处在门槛（`d2_max=9`）附近的候选，**重新提取画像后可能从拒绝变成接受**。升级后建议复核一次候选诊断 CSV（里面有逐维贡献 `c_d_*`）。
3. **谐波维分不开"两台同类设备"**：bus-2 的 12:49 那台也是谐波源（ΔIh +18 A），对 d_ih 来说它"更像设备"，压不住；最终靠 ΔP/ΔI 幅值（0.55 倍）与 ΔQ 拒绝（D²/维 10.6，余量仅 1.2×）。
4. **多画像是"并集"不是"互斥"**：两台设备同时启动时两条事件都会报，不做"占位"约束、也不做跨设备压制（会误删真实的同时启动）；`device_id` 相同时会提示"可能重复选择了同一设备"。
5. **`quantity='i'` 时纯无功阶跃仍不是变点**（第 172 轮附带发现，本轮未改）：`change_points()` 只在 `i4[0]`/`p4[0]` 中二选一，电容投切看不见，后窗会把 ΔQ 吃进去。本轮 12:41:16 候选的 ΔQ −25 770 var 即由此而来（干净窗只有 −0.33 kvar）。

### 五、端到端复核（Web API 全链路）与顺带修掉的一个真 bug

合成一份「设备侧」CSV（6400 Hz、24 s、三相电压 + 电流；基流 10 A/相，设备 3 次启停各注入 +5 A 基波与 1.5 A 5 次 / 0.8 A 7 次谐波）→ CLI 提取画像 → 经 `/api/config` 挂上 → `/api/engine/start` 播同一份文件：

| 检查点 | 结果 |
|---|---|
| 画像 JSON | `features` 8 项；`startup.mu[7] = 1.700 A`（= √(1.5²+0.8²)，解析解吻合）、`sigma[7] = 2.0`（绝对下限）、`shutdown.mu[7] = −1.700`；新增 `harmonic{orders,unit,feature,note}` 块 |
| 引擎检出 | `counts.profile = 6`（3 START + 3 STOP），全部 `confirmed`、`D²=0.00`、`conf=1.000`，`errors=[]` |
| 事件字段 | `delta_ih_a = +1.700 / −1.700`（逐条与注入量一致）；`nilm_events_*.csv` 末列、`nilm_profile_candidates_*.csv` 的 `d_ih`/`c_d_ih` 同步落盘 |
| 多画像并挂 | `profile_path` 同时挂 8 维新画像 + 7 维旧画像 ⇒ `loaded_count=2`、`has_harmonic` 分别 True/False、notes 逐画像一条；旧画像 `A` 口径与本侧 P 口径不符时按既有规则**只报错不误判** |
| 配置往返 | `/api/config` PUT `"a.json;b.json"` → GET 原样回显（不做规范化，去重发生在加载时） |

**顺带发现并修掉的真 bug（CLI 默认配置不对）**：`tools/nilm_profile.py` 的 `--config` 帮助写的是「缺省 configs/runtime.json，没有则 configs/default.json」，但代码直接 `load_or_default(None)` ＝**代码级默认值**（`pt_ratio=100`、`ct_ratio=15`），而 Web 界面跑的是 `configs/default.json`（PT=CT=1）。于是命令行提取的画像 ΔI/ΔP 比界面大 15 / 1500 倍，总线侧**永远匹配不上**，且只在 `errors` 里留一句"变比不同不影响匹配"（这句本身也是错的，已改）。修复：① 缺省按帮助里的顺序找 `configs/runtime.json` → `configs/default.json`，并把实际用的配置文件写进画像 `command`；② PT/CT 不一致的提示改为给出**实际倍数**（"本侧 ΔI 是画像的 1/15 倍、ΔP 的 1/1500 倍"）并说明什么情况下才真的不影响匹配。验证：修复后同一份文件重提画像 ⇒ `ΔI=5.096 A`、`ΔIh=1.700 A`（旧为 76.44 / 25.5），总线侧 6 条 confirmed。


---

## 第 174 轮专题（2026-10-30）：`quantity='i'` 下的纯无功阶跃 + 「每方向 ≥3 个启停样本」界面提示

**版本**：v0.99.27　**新增测试**：`tests/test_r174_reactive_changepoint.py` 7 项、`tests/test_r174_sample_size_hint.py` 6 项（共 13 项）　**全量**：**506 passed / 1 skipped**（154 s，基线 493 + 13）　**回归**：无

### 一、问题①：纯无功阶跃（电容组投切 / SVG 动作）在 I 口径下不是变点

**用户原话**：「针对 `quantity='i'` 时纯无功阶跃仍不是变点问题进行修改」。

**为什么以前不是变点**：`detect_profile()` 的候选搜索与 `change_points()` 都只在**一条**序列上跑——P 口径用 `p4[0]`（有功）、I 口径用 `i4[0]`（三相电流有效值合成）。电容组投切是**纯无功阶跃**：它在 P 上只动几百瓦、在 I 上只动几安，两个门槛（候选门槛＝0.5×画像幅值、变点门槛＝其中的 1/4）都够不到 ⇒ 既报不出来，也**不成"变点"**，于是候选的前后窗把它整个吃进去。

**实录证据**（`tmp/realtime`，bus-2 977 s 逐秒、每相电流 + 总 P/Q）：满足「|ΔQ| ≥ 3 kvar 且 |ΔP| < 2 kW 且 |ΔI| < 3 A」的秒级点 **6 个**（ΔQ 3.7～37.2 kvar，例如 t=1621917971 ΔQ **+37.2 kvar**、ΔP −220 W、ΔI −2.39 A）；放宽到 |ΔQ| ≥ 5 kvar 有 **29 个**。分路侧 bus-3 分别是 8 个 / 36 个。这就是第 172 轮候选 ΔQ 取到 −25.8 kvar 的来源。

**改法（`elec_tool/nilm_profile.py`）**：把 `q4[0]` 作为**第二条搜索序列**并联进 `detect_profile()`：

| 机制 | 规则 |
|---|---|
| 变点 | `change_points(q4[0], …)` 与 x 序列的变点按时间合并（同位置视为同一次动作），参与截断前 / 后窗；门槛 = max(0.5×画像 \|ΔQ\|, `_ABS_FLOOR["d_q"]`=5 var)——下限不能用 0，否则 q 很干净时局部方差为 0、`thr=0` 会把"零变化"的窗口也判成变点 |
| 候选 | 画像的**无功份额** \|ΔQ\| / √(ΔP²+ΔQ²) ≥ `Q_CANDIDATE_SHARE_MIN`=**10 %** 时，Q 序列单独出候选（`source='q'`）。纯电阻设备（ΔQ≈0）不造候选，否则任何投切都会越过它 \|ΔQ\|/2 的门槛 |
| 量纲隔离 | W/A 与 var **不可比大小**：`window_bounds(..., foreign=…)` 新增参数，另一条序列上的变点只按**时间**截断（超出候选自身 `onset+w` 的过渡窗就截），不参与"同号 / ≤1.5×"的幅值比较 |
| 合并 | Q 候选与 x 候选时间重叠 ⇒ 沿用 x 候选（事件的幅值 / 量纲以检测量为准）；`sign_flip` 检查对 Q 候选改为比 **ΔQ** 的符号 |
| 诊断 | 候选字典新增 `source`（`x`/`q`），候选诊断 CSV **末尾追加 `source` 列**（32 列） |

**合成 A/B**（`tests/test_r174_reactive_changepoint.py` 的算例：设备 +5 A/相、+866 W、+902 var；电容投切 −25 kvar 落在启动候选后窗内 20 周波）：

| 版本 | 候选 ΔQ | D²/维 | 置信 | 结论 |
|---|---|---|---|---|
| v0.99.26（只在 x 上找变点） | **−24 098 var** | 1392.30 | 0.000 | rejected，`c_d_q`=10 581 主导 |
| v0.99.27（并联 q 序列） | **+902 var** | 0.005 | 0.998 | **accepted**（`window_crowded`：后窗被投切截断到 10 周波，仍按这一段量） |

**实录 A/B**（bus-2 + 8 维画像，其余参数相同）：

| 候选 | v0.99.26 ΔQ / D²/维 | v0.99.27 ΔQ / D²/维 |
|---|---|---|
| t=1621917638 | **−25 809 var** / 1757.31 | **−16 var** / **14.68** |
| t=1621917677 | −25 802 var / 1579.35 | −25 801 var / 1579.31（不变：无功阶跃与该候选 onset 重合，属于设备自身的无功变化）|
| t=1621917742 | +300 var / 15.86 | +302 var / 15.86 |
| 候选数 / accepted | 3 / 0 | **3 / 0**（不新增误报）|

bus-3 两侧都是 0 候选。注入检验（bus-2 12:45 / bus-3 13:00）仍是 **0.770 / 0.772**，检出能力不退化。

**纯无功阶跃单独成候选的验收**：合成算例里「只有 −25 kvar 阶跃、I 与 P 不动」时，v0.99.26 一个候选都没有；v0.99.27 在 t=420 出 `source=q` 候选（ΔQ −25 000 var，画像 +902 var ⇒ D² 爆表被拒——**候选出来了，是否为本设备仍由匹配把关**）。同一算例把画像换成纯电阻（ΔQ≈0）则**不**出 Q 候选。

### 二、问题②：「每方向 ≥3 个启停样本」的界面提示

**用户原话**：「建议每方向 ≥3 个启停样本，这点修改代码在界面上给出提示」。

**为什么要在界面上讲**：σ 由样本估计——1 个样本 σ=0，完全靠 `_REL_FLOOR`/`_ABS_FLOOR` 托底（ΔI/ΔP/ΔIh 15 %、ΔQ 25 %、dur 5 周波）；2 个样本只有 1 个自由度。容差偏紧的直接后果第 167 轮已实录：单样本画像把一次幅值只差 20 % 的他负荷两级下跌判成 `STOP confirmed 0.46`。这是"数据不够、算法无解"，必须让用户看见，而不是埋在文档里。

**落点（同一段文字，四处复用 `sample_size_notes()`）**：

| 位置 | 呈现 |
|---|---|
| 设备画像提取 → 结果区 | 卡片「启动 / 停止样本 **nS / nD**」标红 + 「（建议各 ≥3）」；下面一行加粗「**样本量不足：启动 x / 停止 y（建议每方向 ≥3 次独立启停）**——样本不够时 σ 只能取经验下限…」；`/api/process/nilm_profile` 返回 `profile.sample_notes` 与 `notes` |
| 负荷辨识 → 画像状态行 | 每画像一行，样本数 <3 标红（tooltip「建议每方向 ≥3 次独立启停」），红字提示来自 `summary.profile.profiles[].notes` |
| 设备画像提取界面（静态） | 「③ 事件前后窗」标题提示 + 底部<b>样本量</b>说明段 |
| CLI `tools/nilm_profile.py` | 照旧 `⚠` 逐行打印（`build_profile` 的 notes 已并入）|

**文字内容**（两个方向各一条，`MIN_EVENTS_PER_DIR = 3`）：
- `启动画像只有 1 次事件（建议每方向 ≥3 次启停）：σ 取经验下限（ΔI/ΔP/ΔIh 15 %、ΔQ 25 % 与绝对下限），容差偏紧 ⇒ 现场噪声容易判成不匹配、幅值相近的他负荷也更容易被误认成同一设备（第 167 轮实录：单样本画像把他负荷两级下跌判成 STOP 0.46）；请补录不同日期 / 工况的启停后重新提取（方案 §3.4）`
- `没有停止事件样本（建议每方向 ≥3 次启停）：画像只含另一方向，总线侧只能辨识该方向`

**兼容**：提示只读 `startup/shutdown.n`，**旧 7 维画像同样适用**；不改变匹配结果（`tests/test_r174_sample_size_hint.py::test_detector_summary_shows_hint_in_profile_row` 同时断言 3/3 画像不出提示）。

### 三、兼容与风险

1. `window_bounds()` 的新参数 `foreign` **加在位置参数末尾并有默认值** ⇒ `tests/test_r167_sandwiched_start.py`（按位置调用）与 `test_r168`（monkeypatch 整个函数）无需改动，41 项相关回归全绿。
2. 候选 CSV 从 31 列变 32 列（末尾 `source`）；`_rotate_if_header_differs` 会自动转表头，旧文件不受影响。
3. **无功份额 10 % 的闸门**是工程折中（写在 `Q_CANDIDATE_SHARE_MIN` 注释里）：份额低于 10 % 的画像只把无功阶跃当变点、不造候选。本实录的画像 084954 ΔQ 份额 3.8 % ⇒ 不新增候选，只改善窗口——这与"不引入误报"一致。
4. **仍未做**：`quantity='q'`（纯无功检测量）仍未作为可选的检测量提供；Q 候选的事件幅值仍是 \|ΔI\|（A）或 \|ΔP\|（W），不提供 var 幅值列。

### 四、界面/接口实录（live server，`uvicorn app.server:app :8017`）

| 检查 | 结果 |
|---|---|
| `POST /api/process/nilm_profile`（1 次启动 + 1 次停止的合成文件） | `profile.startup.n=1`、`shutdown.n=1`、`min_events=3`、`sample_notes` **2 条**、`notes` 里样本量提示也是 **2 条**（不重复）|
| 同上（3 次启动 + 3 次停止的 `dev_side.csv`） | `3 / 3`、`sample_notes = []` ⇒ 够样本不提示 |
| `PUT /api/config`（把 1/1 画像挂到总线侧并勾选「设备画像匹配」）→ `GET /api/nilm/events` | `summary.profile.profiles[0].notes` 含两条「启动 / 停止画像只有 1 次事件（建议每方向 ≥3 次启停）…」，全局 `summary.notes` 同样含 ⇒ 负荷辨识页画像状态行会红字显示 |
| `GET /` | 200（前端资源正常）|

> 前端渲染（`app.js`）：`nilmProfileState()` 把样本数 <`min_events` 的「n 次」标红并挂 tooltip；`npRender()` 把「启动 / 停止样本」卡片标红 +「（建议各 ≥3）」，并在结果区顶部加一行加粗提示。jsdom 在本沙盒不可用（`node_modules/css-tree` 缺 `data/patch.json`），前端只做了 `node --check` + 关键字符串契约测试。

---

## [2026-10-30] 专题：19:23 那次「bus-停止 / bus-启动」两侧回放为什么都没识别到启停 —— 基于 `tmp/` 输出的定量归因（第 175 轮）

- **类型**：用户专题（归因分析，**本轮不改代码**）
- **目标与假设**：用户问题＝「使用之前带设备停止的总线波形数据和带设备启动的总线波形数据分别在总线侧和分路侧重新播放，基于设备画像匹配算法两侧均没有识别到启停，详细输出见 tmp 目录下相关文件，请根据输出的数据详细分析原因。」  
  对应运行＝`tmp/run_info.json` 的 **2026-10-30 19:23:30.584**：总线侧播 `化工行业-海湾化工-bus-停止.csv`（`source_id=0`，1172 s）、分路侧播 `化工行业-海湾化工-bus-启动.csv`（`source_id=1`，977 s）——与用户描述的「停止 / 启动」两个文件一一对应。
- **方法 / 数据 / 参数**：只读 `tmp/`（两侧 1 s 落盘的 power/current/voltage、事件 CSV、画像、两侧配置、run_info）。沙盒**没有 `data/`**（配置是 Windows 路径），不能重放原始周波文件。复算一律 `.venv/bin/python`：把 1 s 序列按 50 周波/秒展开后**直接调用原函数**（`detect_profile` / `load_profile` / `evaluate`），并严格照抄两侧配置（PT4/CT250、3p3w+重构、`invert_phases='A'`、`window_cycles=3000`、profile 参数全默认）。
- **用户执行命令**：用户在 Windows 上「启动两侧回放」；实录路径＝`tmp/`（`run_info.json`、`config_bus.json`、`config_branch.json`、`nilm/nilm_events_20261030.csv`、`nilm/profile_branch_profile_device_20261030_192047.json`、`realtime/*`）。
- **是否进入 REPORT.md（稳定结论）**：**否**（一次回放的归因；可复用判据已写在本节，等用户按第七节的顺序改完配置复跑后再定）

### 一、先定版本：这次跑的是 **v0.99.25 及更早**，不是 v0.99.27

| 证据 | 本次读数 | 含义 |
|---|---|---|
| 事件 CSV 表头 | 末列 `quality_flags`，**没有 `delta_ih_a`** | `delta_ih_a` 是 v0.99.26 新增列 ⇒ **运行的是 r173 之前的版本** |
| 画像 `192047` 的 `features` | **7 项**（无 `d_ih`） | v0.99.26 起提取的画像固定 8 维 |
| `run_info.json` 的 `profile_error` | `画像文件不存在：output\nilm\…_120634.json;output\nilm\…_192047.json`（**两条路径用 `;` 连成一串、整串报一次**） | 这是 v0.99.25 的写法（`f"画像文件不存在：{c.nilm.profile_path}"`）；v0.99.26 起会按 `;` 拆开、逐条报错并用全角「；」连接 |
| 源文件根目录 | `D:\LiteWork\test1Pycharm\NILM_2026\NILM_Web\nilm_calc_tool\…`（上次是 `D:\Work\testPython\NILM_Test2026\nilm_calc_tool\…`） | 用户有**两个代码副本**，这次跑的那个没有更新到 v0.99.26/27 |

> 这一条决定了整个解释：**第 173 轮的「多画像（`;` 分隔）」在这个版本里不存在**，「每方向 ≥3 样本」提示也不存在。所有「为什么没识别」都要先按这个版本读。

### 二、结论总表：**两侧的画像匹配一次都没有真正跑起来**

| 侧 | 源文件 | 画像加载 | 匹配是否运行 | 候选 | 画像事件 | 直接原因 |
|---|---|---|---|---|---|---|
| 总线 | `bus-停止.csv`（sid0） | ✗ **0 个** | **否** | 0（候选 CSV 文件都没生成） | 0 | `nilm.profile_path` 填了 `A;B` 两条，旧版把**整串当成一个文件名** ⇒ 找不到 ⇒ `self._profile is None` ⇒ `_evaluate_profile()` 第一句 `return []` |
| 分路 | `bus-启动.csv`（sid1） | ✓ 1 个 | **否** | 0 | 0 | `nilm.quantity='auto'` ＋有电压 ⇒ 检测量按 **P**；画像是 **I** 口径 ⇒ 口径守卫直接 `return []` 并写 errors |

两条证据是硬的：
- `tmp/nilm/nilm_events_20261030.csv` 共 299 行，6 种通用算法（cusum 70 / steady_state 54 / median_diff 52 / glr 48 / two_window 44 / threshold 31），**`algorithm=profile` 的行数 = 0**。
- `tmp/nilm/nilm_profile_candidates_20261030.csv` **文件根本不存在**（上一次 16:50:36 的回放有 3 行 rejected）⇒ 一条候选都没产生。

### 三、总线侧：画像没加载上（唯一原因）

- 配置：`nilm.quantity='i'`（**与画像的 I 口径一致**，这侧本来是对的）、`profile.enabled=true`、`profile_path` = `output\nilm\profile_device_20261030_120634.json;output\nilm\profile_device_20261030_192047.json`。
- `run_info.json` 白纸黑字：`"profile_file": null, "profile_error": "画像文件不存在：…120634.json;…192047.json"`。
- 旧版（v0.99.25）`_load_profile()` 是 `path = str(self.ncfg.profile_path).strip()`，**不拆 `;`**；`os.path.join(root, 整串)` 当然不是文件。所以两个画像一个都没加载，`_profile is None` ⇒ 检测直接返回。
- **这一侧跟阈值、窗口、幅值、相序、PT/CT 全都无关** —— 它连一次 `detect_profile()` 都没调用。

**反证（本机复算，按 I 口径，1 s→50 周波展开）**：把 `192047` 手动加载后，这段数据是**能匹配上的**：

| 场景 | 06:38:17 那次（P −66.9 kW → −44.0 kW，合成电流 170 → 110 A） |
|---|---|
| 按当前配置（`invert_phases='A'`） | 4 候选 / **0 accepted**；STOP D²/维 **21.76**、conf 0.0000（A 相 ΔI 被取反成 +34.7） |
| **去掉 A 相取反** | 4 候选 / **1 accepted**：**STOP D² 2.55、D²/维 0.36、conf 0.833**，`dur` 239 周波，ΔI **−34.7 / −37.1 / −38.0 A**、ΔP **+24 642 W**、ΔQ **−742 var**、peak 1.23 |

对照画像是 STOP μ = −36.26 / −31.54 / −42.23 A、+23 881 W、−933.8 var、305 周波 —— **逐维都在 1σ 上下**。也就是说：只要画像加载上、A 相别取反，这一侧会是 `confirmed 0.83`。

### 四、分路侧：画像加载了，但检测量口径对不上（唯一原因）

- 配置：`nilm.quantity='auto'`（**这侧和总线侧不一样**）、有电压（Ua≈241.7 V）⇒ `quantity_effective` 返回 **`p`** ⇒ `use_p=True`；而画像 `quantity='i'`（单位 A）。
- `NilmDetector._evaluate_profile()` 的第一段就是守卫（v0.99.26 起改名 `_evaluate_one_profile`，判断逻辑一字未变；第 171 轮专题已把它记为「第一道硬门槛」）：
  ```python
  use_p = (qty == "p")
  if prof.get("quantity") != ("p" if use_p else "i"):
      self.errors.append(f"画像按 {prof.get('unit')} 口径构建，本侧检测量为 {'P' if use_p else 'I'}："
                         f"ΔP/ΔI 特征不可比，该画像匹配未运行（请统一 nilm.quantity）")
      return []
  ```
  ⇒ **一次都没跑**，并在 `errors` 里留了一条「画像按 A 口径构建，本侧检测量为 P：ΔP/ΔI 特征不可比，该画像匹配未运行（请统一 nilm.quantity）」。
- 这一侧与「数据里有没有启动」无关，也跟窗口/门槛无关。

**反证（本机复算）**：把口径统一后，这段数据里 **07:00:09 的设备启动是能 confirmed 的**：

| 场景 | 候选 / accepted | 06:55:33 | 06:59:08 | 07:00:09 | 07:00:40 |
|---|---|---|---|---|---|
| 按当前配置（P 口径 ＋ A 相取反） | 4 / **0** | 21.05 / 0.0000 | 51.36 / 0.0000 | 18.30 / 0.0001 | 256.01 / 0.0000 |
| 统一到 P、仍 A 相取反 | 4 / **0** | 21.05 / 0.0000 | 51.36 / 0.0000 | 18.30 / 0.0001 | 256.01 / 0.0000 |
| **统一到 P ＋ 去掉 A 相取反** | 4 / **2** | **2.05 / 0.360 ✓** | 14.73 / 0.0006 | **1.37 / 0.504 ✓** | 233.54 / 0.0000 |
| 统一到 I ＋ 去掉 A 相取反 | 5 / **2** | **2.05 / 0.360 ✓** | 14.73 / 0.0006 | **1.35 / 0.509 ✓** | 233.54 / 0.0000 |

（单元格＝`D²/维 / conf`；✓＝confirmed。多出来的第 5 条是 07:08:13 的电容投切，ΔQ −22 366 var，被正确拒绝。）

**06:59:08 那条为什么修好口径也过不了**：它的 ΔI = **+59.1 / +59.4 / +58.2 A**、ΔP = **−44 033 W**、ΔQ = **+9 var**、`dur` 50 周波 —— 幅值是画像（35.95/31.20/42.49、−23 933 W）的 **1.6~1.8 倍**、ΔQ 差 900 var。这是 06:59:07→10 的三级爬升（−45.5 → −66.9 → −69.9 → −89.1 kW），**要么是另一台更大的负荷，要么与本设备不同负荷点**。被拒是对的。

### 五、第三个坑：两侧都勾了「A 相电流取反」，而画像是无取反提的

- 两侧 `transform.invert_phases = "A"`，画像 `wiring.invert_phases = ""`。
- 后果：A 相 ΔI 变号。总线侧那次停机从 **conf 0.833 直接掉到 0（D²/维 0.36 → 21.76）**；分路侧从 **2 条 confirmed 变成 0**。
- 这段数据上「取反」是错的：停机时三相 ΔI 实测 **全为负**（−34.7/−37.1/−38.0），与画像 STOP 的负值同号；取反 A 相后变成 +34.7，物理上讲不通（停机只会让电流变小）。
- 经验规则：**画像在哪一侧、用什么极性提的，回放侧就必须用同一极性**；`invert_phases` 是「修正接线」的手段，不是可以随手勾的开关。

### 六、数据里到底有没有启停（回答「是不是漏检」）

| 文件 | 段长 | 稳态 | 最大持续台阶 | 形态 |
|---|---|---|---|---|
| `bus-停止`（总线段） | 1172 s | P −50 571 W / Q −7 158 var（中位），合成电流 95.0~200.2 A | 06:38:17→30 **P −66.3 → −44.1 kW（+22.2 kW）**、合成电流 **167.5 → 111.1 A（−56.4 A）**，12 s 内四级下降（窗内中位差 ΔP **+24 642 W**、ΔQ **−742 var**） | 与画像 STOP（+23 881 W、−64.3 A、−934 var）吻合 ⇒ **是本设备的停机** |
| `bus-启动`（分路段） | 977 s | P −57 439 W / Q −7 873 var，合成电流 97.7~295.3 A | 06:59:07→10 **P −45.5 → −89.1 kW（−43.6 kW）/ 合成电流 114.9 → 215.3 A（+100 A）**；07:00:07→13 再 **−21.7 kW**；07:00:38→41 **P −115.3 → −63.6 kW（+51.7 kW）/ 合成电流 282.9 → 163.0 A（−120 A）** 切除 | 07:00:09 那一级（−21 kW、+27/+29/+33 A、ΔQ +725）**与画像 START 匹配（0.504）**；06:59:08 那一级是 1.8 倍幅值的另一台负荷 |

⇒ **两段数据里都有该设备的动作**，而且按第七节改完配置后**能识别出来**（总线 0.833、分路 0.504）。本次 0 条不是「算法看不见」，是「匹配没跑」。

### 七、修法（按顺序，全部是配置/版本，不用改代码）

1. **先把运行目录的代码更新到 v0.99.27 并确认版本**。本次跑的 `D:\LiteWork\…\NILM_Web\nilm_calc_tool` 是 v0.99.25 的旧副本（事件 CSV 无 `delta_ih_a`、画像 7 维、`;` 未拆）。判定方法：跑完看事件 CSV 末列是不是 `delta_ih_a`。
2. **总线侧 `profile_path` 只填一个存在的文件**（或升级后才可以写 `A;B`）。相对路径以程序根目录为准，建议填绝对路径；填完先看「负荷辨识 → 画像状态行」是否显示该画像 `loaded`。
3. **两侧 `nilm.quantity` 统一成 `i`**（画像 `quantity=i`、单位 A）。分路侧现在是 `auto`，有电压就变 P ⇒ 守卫直接不跑。要么统一 `i`，要么用 `quantity=p` 重提一次画像。
4. **去掉两侧的「A 相电流取反」**（`transform.invert_phases` 置空），除非确认该侧 A 相 CT 真的接反 —— 本段数据上取反是错的。
5. 顺手把 `window_cycles=3000` 调大或把画像前后窗改小：画像 `pre/post=3000` ＋ `max_scale=8` 需要 **73 281 周波（1466 s）** 的缓存，而两侧文件只有 977 / 1172 s ⇒ 会命中「窗口不够，已自动按 73281 周波缓存评估」的提示，事件时刻与特征窗都会被拉长（例如 06:59:08 与 07:00:09 被 60 s 窗切开成两条）。典型画像用 10/50~10/200 即可。
6. PT/CT 口径要澄清：画像按 **PT=1 / CT=1** 提，回放用 **PT=4 / CT=250**，引擎会提示「本侧 ΔI 是画像的 250 倍、ΔP 的 1000 倍」。本次实测 ΔP（±24 kW）与画像（±24 kW）同量级 ⇒ 说明 `dev1.csv` 里本来就是一次值，这条提示属**误报**；但两侧必须用同一套口径提画像与回放，否则一旦真是二次值就永远匹配不上。

### 八、遗留与边界

- 沙盒无 `data/`，所有复算都建立在 **1 s 落盘序列按 50 周波展开**上：时刻只到秒级、`dur`/`peak_ratio` 与引擎逐周波结果有 ~0.6 % 级差异（第 174 轮实测）。本文的结论都是「有 / 无」级别的，不受影响；具体 D² 数值仅供排序参考。
- 本节**未改任何代码**。若用户希望「口径不一致时不要静默 return、而是明确告诉用户画像没生效」，那属于界面/状态行的改进项（v0.99.27 的 `summary.profile` 已有 `loaded/error` 字段，可考虑在负荷辨识页把 `errors` 里的这条做成醒目标记），待用户确认后再立项。
- 「06:59:08 的 1.8 倍幅值负荷不是本设备」这一条依赖画像与数据同口径的假设；若用户的画像本来就该用 `quantity=p` 重提，结论可能变化 —— 需用户确认设备侧文件的采集口径。

---

## [2026-10-31] 专题：23:38 那次「bus-停止 / bus-启动」两侧回放——两侧都识别到了启停，这次对不对、正不正常？（第 176 轮）

- **类型**：用户专题（结果判读 + 残留风险清点，**本轮不改代码**）
- **目标与假设**：用户问题＝「使用之前带设备停止的总线波形数据和带设备启动的总线波形数据分别在总线侧和分路侧重新播放，基于设备画像匹配算法两侧均已识别到对应的启停，详细输出见 tmp 目录下相关文件，请根据输出的数据详细分析是否正常。」逐条要回答的是：① 识别到的两条事件**是不是**那台设备；② 匹配质量（与画像 μ/σ 的逐维对照）；③ 与逐秒实测台阶是否自洽；④ 该拒的有没有拒、该报的有没有漏；⑤ 「正常」还差什么。
- **方法 / 数据 / 参数**：只读 `tmp/`（`run_info.json`、两侧 `config_*.json`、`nilm/nilm_profile_candidates_20261030.csv`（5 行 32 列）、`nilm/nilm_events_20261030.csv`（325 行）与 `nilm_events_20261031.csv`（15 行）、两份画像 JSON、`realtime/{power,current,voltage,fundamental,harmonic}_2026103*.csv` 的 1 s 落盘）。沙盒没有 `data/`（配置里是 Windows 路径 `D:\LiteWork\…\nilm_calc_tool\data\…`），**不能重放原始周波**；因此"实测台阶"一律用**落盘后的 1 s 序列**做中位差独立复算，再与引擎的逐周波特征对照——两者管线不同（1 s 窗 RMS/P vs 逐周波 DFT 的中位差），能对上就说明引擎特征不是拟合出来的。
- **用户执行命令**：Windows 上「启动两侧回放」（`run_info.json` 两次启动 `2026-10-30 23:38:35.818` / `23:38:36.380`，`started_side=bus`，两侧 `config_mode=verbatim_copy`）。
- **是否进入 REPORT.md（稳定结论）**：**否**（一次回放的判读）。可复用的判据是第七节的三条「这次能对上、但换个文件就会失效」的前提。

### 一、版本与运行身份：这次终于是 v0.99.27，而且画像真的加载了

| 证据 | 本次读数 | 含义 |
|---|---|---|
| 事件 CSV 表头 | 30 列，末列 `delta_ih_a` | v0.99.26 起才有 ⇒ **不是 19:23 的旧副本** |
| 候选 CSV | 32 列（末列 `source`），**5 行** | v0.99.27 的列集；文件存在＝画像匹配真的跑起来了 |
| 画像 `features` | **8 项**（含 `d_ih`） | v0.99.26+ 提取 |
| `run_info.json` | 有 `profile_files` / `profile_copied_from_all`，**无 `profile_error`** | 多画像字段（v0.99.26+）＋画像复制成功 |
| 画像 `command` | `python tools/nilm_profile.py --file data\化工行业-海湾化工-dev1.csv … --pre 3000 --post 3000 --merge-gap 20 --quantity i` | 两侧**同一份 dev1.csv**、同一条命令提取（见第八节第 2 条） |
| 数据文件 | 总线 `bus-停止.csv` 覆盖 `14:33:19.789~14:53:18.765`（1172 s）；分路 `bus-启动.csv` 覆盖 `14:53:19.789~15:09:58.765`（977 s） | **两个文件是同一次录波的前后两段**（首尾只差 1 s），所以总线段里只可能看到"设备停"、分路段里只可能看到"设备启" |

### 二、结论总表：**识别正确、匹配质量合格**，但「能对上」有两处是凑巧成立的

| 判读项 | 结论 | 依据（见下方各节） |
|---|---|---|
| 总线侧是否识别到"设备停机" | ✅ **是**，`14:38:16.905 STOP confirmed` | D² 4.299（0.537/维）、conf 0.7644，8 维全在 1.5σ 内（第三节） |
| 分路侧是否识别到"设备启动" | ✅ **是**，`15:00:08.065 START low_confidence` | D² 3.974（0.497/维）、conf 0.7801，8 维全在 1.5σ 内；`low_confidence` 只因 `window_crowded`（第四节、第六节） |
| 是否把别的负荷认成这台设备（误报） | ✅ **没有**，画像事件两侧各 1 条 | 全部 5 条候选里另 3 条都 rejected（第五节） |
| 是否漏报本设备 | ✅ **没有** | 设备在本设备段内的唯一一次停机 / 一次启动都被报出；没报的动作全是别的负荷或低于门槛（第六节） |
| 「是否正常」 | **是**，但**不是"随便换一份数据都能这样"** | 两处凑巧：`invert_phases='A'` 仍在配置里却**本次未生效**；画像与回放**不同源、不同 PT/CT 口径**却能幅值对上（第七节） |

### 三、两侧 accepted 事件 vs 画像 μ/σ 逐维对照

画像 `profile_{bus,branch}_profile_device_20261030_233706.json`：8 维、`quantity='i'`、`pt_ct 1/1`、`3p4w`、`invert_phases=''`、`pre/post=3000/3000`、`fs=10000`、启停各 **1** 次（σ 取经验下限：ΔI/ΔP/ΔIh 15%、ΔQ 25%）。D² 是对角马氏距离（Σ+0.1·median(σ²) 收缩），`conf = exp(−D²/(2d))`，`d=8`。

**总线侧 `14:38:16.905` STOP（sid0，`confirmed`，D²=4.299 / 0.537·维 / conf 0.7644 / scale 0.25 / scales_hit 0.25·0.5·1.0）**

| 特征 | 引擎实测 | 画像 μ | 画像 σ | z=(实测−μ)/σ | D² 贡献 | 占比 |
|---|---:|---:|---:|---:|---:|---:|
| `d_ia` | −33.312 A | −36.260 | 5.439 | **+0.54** | 0.260 | 6 % |
| `d_ib` | −36.305 A | −31.544 | 4.732 | **−1.01** | 0.880 | 20 % |
| `d_ic` | −33.109 A | −42.229 | 6.334 | **+1.44** | 1.910 | 44 % |
| `d_p` | +25 049 W | +23 881 | 3 582 | **+0.33** | 0.110 | 3 % |
| `d_q` | −824.5 var | −933.8 | 233.4 | **+0.47** | 0.220 | 5 % |
| `peak_ratio` | 1.223 | 1.001 | 0.300 | **+0.74** | 0.010 | 0 % |
| `dur_cycles` | 429 周波（8.6 s） | 305（6.1 s） | 152.5 | **+0.81** | 0.660 | 15 % |
| `d_ih` | −15.305 A | −16.886 | 2.533 | **+0.62** | 0.250 | 6 % |

**分路侧 `15:00:08.065` START（sid1，`low_confidence`，D²=3.974 / 0.497·维 / conf 0.7801 / scale 0.25 / scales_hit 0.25·0.5 / `window_crowded`）**

| 特征 | 引擎实测 | 画像 μ | 画像 σ | z | D² 贡献 | 占比 |
|---|---:|---:|---:|---:|---:|---:|
| `d_ia` | +32.428 A | +35.946 | 5.392 | **−0.65** | 0.380 | 10 % |
| `d_ib` | +34.775 A | +31.195 | 4.679 | **+0.76** | 0.500 | 13 % |
| `d_ic` | +37.639 A | +42.495 | 6.374 | **−0.76** | 0.530 | 13 % |
| `d_p` | −24 524 W | −23 933 | 3 590 | **−0.16** | 0.030 | 1 % |
| `d_q` | +567.5 var | +901.8 | 225.4 | **−1.48** | 2.200 | 55 % |
| `peak_ratio` | 1.355 | 1.592 | 0.478 | **−0.50** | 0.020 | 1 % |
| `dur_cycles` | 1 356 周波（27.1 s） | 1 271（25.4 s） | 635.5 | **+0.13** | 0.020 | 1 % |
| `d_ih` | +14.918 A | +16.609 | 2.491 | **−0.68** | 0.300 | 8 % |

**判读**：
1. **8 个维度全部落在 ±1.5σ 以内**，最大偏离是分路的 `d_q`（z=−1.48，占 D² 的 55%）——它是"无功小了 37 %"，不是方向错。
2. 符号**全同**：总线 STOP 的 ΔI 三相都向下、ΔP 为正；分路 START 的 ΔI 三相都向上、ΔP 为负——与画像完全一致。注意画像本身 ΔP 与 ΔI **异号**（提取时 `notes` 已记「CT 极性接反或电压/电流相别未配对」），所以判方向看的是**画像自己的 μ**，不是"ΔP 为正即启动"。
3. `scale=0.25` 说明事件是**用 1/4 画像窗长（750 周波＝15 s）找到的**；总线那条同时命中 0.25/0.5/1.0 三个尺度（多尺度一致 ⇒ 可信度更高），分路命中 0.25/0.5。这与画像 `pre/post=3000`（60 s）远大于事件本身的过渡时间有关（第七节第 3 条）。
4. 分路的 `low_confidence` **不是因为置信度低**（0.7801 比总线的 0.7644 还高），是因为 `status = confirmed if accepted and not flags`——它带了 `window_crowded` 标志（后窗被 15:00:39 的大负荷切除截断，见第六节）。

### 四、与逐秒实测台阶的独立对照：引擎的特征向量是可复现的

用 `realtime/power|current_*.csv` 的 1 s 落盘数据，取「事件前 60 s 中位」与「事件后稳定段中位」作差（与画像的 60 s 前后窗同几何）：

| 侧 / 事件 | 窗口 | 实测 ΔP | 实测 ΔQ | 实测 ΔI（A/B/C） | 实测 ΔI 合成 |
|---|---|---:|---:|---|---:|
| 总线 `14:38:17` 停机 | 前 14:37:17–14:38:16 / 后 14:38:26–14:38:46 | **+24 052 W** | −728 var | **−34.0 / −36.0 / −36.9** | −61.7 A |
| 分路 `15:00:08` 启动 | 前 14:59:08–15:00:05 / 后 15:00:25–15:00:38 | **−24 573 W** | +654 var | **+33.0 / +35.1 / +39.4** | +62.2 A |

对照引擎的 `(d_p, d_q, d_ia, d_ib, d_ic)`：总线 **+25 049 / −824.5 / −33.3 / −36.3 / −33.1**（ΔP 差 4 %、ΔQ 差 12 %、ΔI 最大差 3.8 A）；分路 **−24 524 / +567.5 / +32.4 / +34.8 / +37.6**（ΔP 差 0.2 %、ΔQ 差 13 %、ΔI 最大差 1.8 A）。

> 两条管线互相独立（1 s 窗 vs 逐周波），差异来源可解释：① 引擎的 `d_*` 是"后窗中位数 − 前窗中位数"，总线的后 60 s 里还含 `14:38:53` 的第二级下跌与 `14:39:44` 的回弹；② 1 s 落盘的 P 是整 1 s 窗均值。**能这样对上，说明这两条事件不是"凑出来的数"**。

物理形态也对得上：总线停机是 **2~3 s 的过渡**（`14:38:16 P −63.9 kW → 14:38:19 −48.7 kW`，引擎 `dur=429 周波=8.6 s`，画像 305 周波=6.1 s）；分路启动是**约 28 s 的斜坡**（`Ia 123 A → 162 A`，`15:00:05` 起爬、`15:00:33` 到顶；引擎 `dur=1356 周波=27.1 s`，画像 1271 周波=25.4 s）——**斜坡时长几乎一样**，这是"同一台设备"最硬的证据（不是只有幅值像）。

### 五、被拒的 3 条：全部拒得对

| 侧 / 时刻 | 方向 | D²（/维） | conf | 否决 | 实测台阶 | 为什么该拒 |
|---|---|---:|---:|---|---|---|
| sid1 `14:55:32.785` | STOP | 72.8（9.1） | 0.011 | `d2_exceeds` | ΔP +15 890 W、ΔQ −64 var、ΔI −22.6/−18.0/−21.5（ΔIt −35.7 A） | 幅值只有画像的 ~55 %（`d_ia` z=+2.9、`d_ib` z=+3.1、`d_ic` z=+4.0、`d_p` z=−2.5、`d_q` z=+3.4），且 **`d_ih=−1.46 A`（z=+6.1）而画像是 −16.9 A** ⇒ 线性负荷，不是这台谐波型设备 |
| sid1 `14:59:08.825` | START | 220.3（27.5） | 0.000 | `d2_exceeds`、`window_crowded` | ΔP −48 998 W、ΔQ −1 062 var、ΔI +66.2/+66.4/+65.3（ΔIt +114.2 A） | 幅值是画像的 **1.7~1.8 倍**（`d_p` z=−6.9、`d_q` z=−8.6），`d_ih` 只有 +1.05 A（z=−6.2）⇒ 另一台更大、且几乎不产生谐波的负荷 |
| sid0 `14:48:27.405` | START | 25.8（3.23） | 0.199 | 置信度 < 0.3（无 `d2_exceeds`） | ΔP −17 304 W、ΔQ +73 var、ΔI +28.9/+28.5/+26.8（ΔIt +48.4 A） | 幅值是画像的 ~0.67 倍（`d_ic` z=−3.4、`d_ia` z=−2.1、`d_p` z=+2.2）⇒ **边界情形**：`d_ih=+14.9 A` 恰好落在 1σ 内，如果这确实是同一台设备的"轻载启动"，那就属于"该报没报"；正确做法是给该设备补一条轻载画像（多画像），**不是**放宽 `min_confidence` |

### 六、没报出来的动作：三种不同的「没报」，没有一种是漏报本设备

| 动作 | 实测 | 为什么没出事件 |
|---|---|---|
| bus `14:38:53` 第二级下跌 | ΔP **+4 463 W**、ΔIt **−11.8 A**（106.9→95.1） | 候选门槛 `min_d = 0.5·min(√Σμ²)`＝0.5×63.8/64.0 ≈ **31.9 / 32.0 A**，11.8 A 只有门槛的 37 % ⇒ **连候选都成不了**（候选 CSV 里没有这一行）。与画像提取时"分级带载合并"的处理一致（dev1 那次停机 dur=305 单级） |
| bus `14:39:44` 回弹 | ΔP −6 196 W、ΔIt +16.4 A | 同上（16.4 A＝门槛的 52 %） |
| branch `15:00:39` 大负荷切除 | ΔP **+57 924 W**、ΔQ +8 901 var、ΔI **−77.0/−75.9/−77.7**（ΔIt −133 A） | **`nilm.min_gap_cycles = 1000`（20 s）去重**：上一条 accepted 的 `g_end = 15:00:08.065 + 1356 周波 = 15:00:35.2`，`15:00:39` 的候选 `g_on ≤ g_end + 1000` ⇒ 判为 `seen`，`write_profile_candidate()` 对 `seen` 的候选**不落盘**。它幅值是本设备的 2.1 倍、ΔQ 是 10 倍 ⇒ 就算出候选也必被拒；但**候选诊断 CSV 里看不到它**，复盘时会误以为"没检测到" |
| 其余 6 个算法 | 两个事件文件合计 **340 行**（`nilm_events_20261030.csv` 325 + `nilm_events_20261031.csv` 15）= 画像 **2** + 通用算法 **338** | 与画像匹配无关（见第八节第 4 条） |

### 七、这次「正常」的前提：两处凑巧 + 三条要修的配置

#### 7.1 凑巧一：`invert_phases = "A"` 还在配置里，但**本次运行没有生效**

两侧 `tmp/config_{bus,branch}.json` 的 `transform` 都是 `{"pt_ratio":4,"ct_ratio":250,"wiring":"3p3w","reconstruct_3w":true,"invert_phases":"A"}`。如果它真的生效，3P3W 重构会先取反 A 相、再由 `ib = −(ia+ic)` 推导 B 相 ⇒ B 相变成 `ia−ic`。本机用**同一份配置 + 平衡三相负荷**跑端到端（`MetricsCalculator.compute`，合成 6400 Hz / 2 s）：

| `invert_phases` | `i_rms` A/B/C | `unbalance_pct` | `p_total` | `p_per_phase` A/B/C | `pf_total` |
|---|---|---:|---:|---|---:|
| `"A"` | 17 678 / **30 619** / 17 678 A | **200.0 %** | **0.0 W** | −12.1 MW / **≈0** / +12.1 MW | **0.0** |
| `""` | 17 678 / 17 678 / 17 678 A | 0.0 % | 36.3 MW | 12.1 / 12.1 / 12.1 MW | 1.0 |

而本次落盘的实测是：`i_rms ≈ 92/104/102 A`（B/A=1.12，**不是 √3**）、`unbalance_pct = 4~9 %`、`p_total = −60.79 kW = Pa+Pb+Pc`（三相同号各≈1/3）。**这组数只有"没有取反"才能出现** ⇒ 运行态里这个残留**没有进入计算**。

> **对第 175 轮的更正**：那一轮把「两侧 `invert_phases='A'`」列为"没识别到"的原因之一。现在看：19:23 与 23:38 两次落盘的**电流数值逐字节相同**（只有 `run_id` 不同），而本次数据证明没有取反 ⇒ **19:23 那次同样没有取反**，第 175 轮的反证表里"保留取反 ⇒ D²/维 21.76 / conf 0"是**若生效的形态**（这个数本身没错），但**不是当时的实际情况**；当时那两条事件没报出来，原因仍然只有第 175 轮的第一、二条（画像 0 个加载 / 口径守卫）。**结论更正，判据保留。**
>
> **风险不变**：这个残留只要在某次启动时真的被带上（换机器、换代码副本、从 `configs/runtime.json` 冷启动），同样的数据会全灭——`d_ib` 会变成 `Δ(ia−ic)`，D²/维 直接越 9。**必须清掉。**

#### 7.2 凑巧二：画像与回放**不同源、不同口径**，幅值却刚好对上

| 项 | 画像（两侧同一份） | 回放 | 影响 |
|---|---|---|---|
| 源文件 | `data\化工行业-海湾化工-dev1.csv`（设备侧，2021-05-25 14:39:31 / 15:00:50 两次动作） | `bus-停止.csv` / `bus-启动.csv`（2021-05-25 14:33–15:10） | 两段录波不同源，事件时刻差 75 s / 42 s，靠**特征**匹配（本来就该如此） |
| 采样率 | 10 000 Hz | 6 400 Hz | 周波特征口径一致（都按 f_nom=50 整周波），不影响 |
| PT/CT | **1 / 1** | **4 / 250** | 见下 |
| 接线 | 3p4w、不重构 | 3p3w + 重构 | **这个设定核对过了，是对的**：重构后 `U1a/U1b/U1c = 241.9/241.9/239.8 V`、线电压 `Uab 420.3 V ≈ √3×242 V`、`In ≡ 4×10⁻¹⁵ A`（重构生效）、三相有功各≈1/3（本机反证：把「3p4w 相电压」误当「3p3w 线电压」喂给同一套配置，重构出的三相电压是 **604/228/604 V**、`p_per_phase` **10.1/4.0/10.1 MW**，与实测的 241.9/241.9/239.8 V、三相有功各≈1/3 完全不符）⇒ **文件里 A/C 电压列确是 Uab/Ucb、B 相电流由重构给出** |

PT/CT 这条要说清楚：画像 `pt_ct=1/1` **不是错误**——`dev1.csv` 里的电流本来就是一次侧安培量级（否则画像 μ 会是 0.036 A 而不是 36 A）；回放的 `bus-*.csv` 是二次侧，乘 4×250=1000 后同样落在一次侧安培量级。**所以两侧数值同口径、匹配成立**。但这条**只靠数字对上，文件里没有任何一处写明**：下次若把画像的 PT/CT 改成 4/250 重提（得到 36 000 A）或换一份二次侧的设备文件，就会 1000 倍错位、永远匹配不上。引擎已有 `_profile_ptct_noted` 提示（`k_i = ct_r/ct_p`、`k_p = pt_r·ct_r/(pt_p·ct_p)`），本次应当在 errors 里出现过一条 `本侧 ΔI 是画像的 250 倍、ΔP 的 1000 倍` 的提示——**这条提示在本次属「数值不同但口径相同」的情形**（引擎文案本身也写了「两侧都是同一变比体系时只是提示」），需要人工确认而不是一键忽略。

#### 7.3 要修的三条

| # | 项 | 现状 | 建议 | 不改的后果 |
|---|---|---|---|---|
| 1 | 两侧 `transform.invert_phases` | `"A"`（本次未生效） | **清空**；同时把「本次运行实际使用的 transform」落盘（见第八节第 1 条），避免再拿磁盘副本当运行证据 | 真生效时 3p3w 重构下 B 相 = `ia−ic`，8 维画像的 `d_ib` 全错，两条事件必 `d2_exceeds` |
| 2 | 画像 / 回放的 PT/CT 与源文件 | 画像 1/1（一次侧量级文件）、回放 4/250（二次侧文件） | 要么把回放文件也按 1/1 播（数值直接可比），要么把画像改成与回放同 PT/CT 重提；**关键是让画像 JSON 里的 `pt_ct` 与提取时实际用的口径一致** | 换一份文件/一台设备就 1000 倍错位；本次能对上纯属两套口径的数值恰好都在一次侧安培量级 |
| 3 | 画像 `pre/post = 3000/3000`（60 s）与 `nilm.window_cycles = 3000` | `_profile_need_one(×8) = 3000×8 + 1271 + 2×3000×8 + 10 = 73 281 周波 = 1466 s`，大于两个文件（1172 s / 977 s）⇒ **≥2 倍尺度永远不可能命中**（实到 `scales_hit` 最高只到 1.0，实测印证）；引擎会自动按需扩缓存并写提示，但要付出内存/延迟 | 画像前后窗改小（典型 **10/50 ~ 10/200**）重提，或把 `window_cycles` 提到 ≥75 000 | ① 多尺度只能用到 0.25~1.0；② 60 s 前后窗会把相邻动作吃进同一个窗（分路 `window_crowded`、总线后窗含第二级与回弹，都是这么来的） |

### 八、附带发现（与本次判定无关，但下次复盘会咬人）

1. **运行目录里的 `config_bus.json` / `config_branch.json` 不是本次实际用的配置。** `_dump_run_configs()` 是 `shutil.copyfile(r.persist_path, …)`——**磁盘持久化文件的逐字节副本**；而引擎跑的是 `RUNNER.cfg`（`/api/config` 深合并累积的对象）。两者本次**确实不一致**（文件说 `invert_phases="A"`，数据说没取反）。建议在运行目录另写一份 `config_effective_{bus,branch}.json`（`cfg.to_dict()`），并在 `run_info.json` 里记 `config_mode=effective_dump`；否则"复盘证据"会被磁盘残留污染（第 175 轮的误判就是这么来的）。
2. **两侧画像其实是同一份**：`profile_bus_…` 与 `profile_branch_…` 的 `source_file`、`command`、`side`（都是 `bus`）、`base_config` 完全一样，都是 `dev1.csv` + `--quantity i --pre 3000 --post 3000`。本次任务（设备画像 → 总线波形回放）这样用是对的，但要清楚：**这不是"总线侧画像 + 分路侧画像"**，而是"同一台设备画像挂到两侧"。
3. **分路侧播的是总线波形**（`run_info.sides.branch.source_path = …bus-启动.csv`，`source_id=1`）。所以这次是**算法闭环验证**，不是"分路侧现场数据 + 设备画像"的真实拓扑；分路侧结论不能直接推广到真实分路 CT。
4. **通用算法事件 338 条**（340 − 2，含跨午夜切到 `nilm_events_20261031.csv` 的 15 条）：cusum 74 / steady_state 60 / threshold 57 / median_diff 52 / glr 51 / two_window 44。`min_delta_w=50 W` 相对 −60 kW 的基值只有 0.08 %，工业负荷的连续调节全被报成事件。这不影响画像判定（画像有完整 8 维 + D² 把关），但界面事件表会被刷屏——建议对这类数据把 `nilm.rel_tol_pct` 调到 0.3~0.5 % 或按"同方向 1 s 内合并"。
5. **跨午夜文件切分**：`realtime/*_20261030.csv` 与 `*_20261031.csv` 属**同一次运行**（`run_id` 都是 `1793374715816`/`…716352`），切分点是**墙钟**跨 0 点（总线侧回放比实时慢约 0.9×，23:38:35 启动、数据时间走到 14:52:00 时墙钟过了 0 点）。复盘时不要当成两次运行。

### 九、复现方式与一条 10 秒判据

- 逐维对照 / z / D² 贡献：直接读 `tmp/nilm/nilm_profile_candidates_20261030.csv` 的 `d_*`、`c_d_*` 与画像 JSON 的 `mu/sigma`（本次脚本见 `/tmp/r176_*.py`，沙盒内一次性，不随仓库提交）。
- 1 s 台阶复算：`.venv/bin/python` 读 `tmp/realtime/{power,current}_2026103*.csv`，按 `time_local[11:19]` 取窗口、`numpy.median` 作差（本文所有 Δ 值均由此得来）。
- 取反指纹复现：`.venv/bin/python` 里用 `AppConfig.from_dict(两侧配置)` + 合成 3p3w 两表法 `SampleBlock` → `scale_block` → `MetricsCalculator.compute`，对比 `invert_phases="A"` 与 `""`（本文 7.1 的表）。
- **用户侧 10 秒判据**（下次怀疑"取反到底有没有生效"时用）：波形预览打开同一个 `bus-停止.csv`，`分相电流极性反转` 空 vs 填 `A` 各看一次——`Ib` 应从 ≈104 A 跳到 ≈180 A（√3 倍）、`电流不平衡度` 从 5 % 跳到 ~200 %、`P` 从 −60.8 kW 跳到 ≈0。**若运行落盘的数（−60.8 kW / 5 %）与"空"一致，就说明取反没生效。**

---

## [2026-10-31] 专题：画像 `pre/post` 与 `nilm.window_cycles` 到底什么关系、该怎么设（第 177 轮，承接第 176 轮 7.3 第 3 条）

- **类型**：用户问答（参数口径说明 + 本机实测；**不改代码**）
- **问题（原话）**：「针对画像 `pre/post=3000/3000` 与 `window_cycles=3000` 不匹配这个问题如何理解，并说明如何设置这些参数。」
- **是否进入 REPORT.md**：否（口径说明；等用户按方案改完复跑后再定）

### 一、三个参数各管什么

| 参数 | 在哪 | 含义 | 谁在用 |
|---|---|---|---|
| `profile.pre_cycles` / `post_cycles` | **画像 JSON**（提取时写入，匹配时**原样沿用**） | 设备侧"事件前 / 事件后"各取多少个周波量特征：`pre` 建基线、`post` 量稳态 | ① `detect_profile()` 的**候选搜索窗**（`_two_window_candidates` 的前/后半窗，按尺度 ×sc）；② `transition_end()` 的**目标电平**（后窗中位数）；③ `event_features()` 的**特征窗口**（`[onset-pre, onset)` 与 `[end, end+post)`） |
| `nilm.window_cycles` | 运行配置（负荷辨识页） | 引擎环形缓冲长度 / 界面"周波窗"设定值 | ① `W = max(window_cycles, _profile_window_need())` —— **画像需要更大时会被默默放大**；② 6 个通用算法与界面周波窗的窗长（它们只扫尾部切片，见 `v0.99.17`） |
| `nilm.algorithms.profile.max_scale` / `min_scale` | 运行配置 | 候选搜索的多尺度范围（1 表示只用画像原尺度） | 只为"现场形态比画像更快/更慢"兜底；**不改变特征口径** |

### 二、一个公式：画像要多少窗口

```
need(周波) = pre_cycles × sc + dur_max + 2 × post_cycles × sc + 10      （sc = max_scale）
              ①基线          ②过渡      ③搜索窗 + ④终点后再等 post 确认
```
- ② `dur_max` ＝ 画像 startup/shutdown 里 `dur_cycles.max` 的**较大者**（本机 1271 周波＝25.4 s 的启动斜坡）。
- ④ 终点 `end = onset + dur`，特征要 `[end, end+post)`，事件确认还要再等 `post` 个周波（`g_end + post_wait ≤ g_last`）。
- 代码：`NilmDetector._profile_need_one()`（`elec_tool/nilm.py:808`）与 `_profile_window_need()`（`:814`）。

代入本机画像（`dur=1271`）：

| sc | need | ＝ 多少秒 | 与 `window_cycles=3000`（60 s）比 |
|---:|---:|---:|---|
| 1 | 3 000+1 271+6 000+10 = **10 281** | 206 s | 3.4 倍 |
| 2 | 6 000+1 271+12 000+10 = **19 281** | 386 s | 6.4 倍 |
| 8 | 24 000+1 271+48 000+10 = **73 281** | 1 466 s | **24.4 倍** |

`2·post·sc` 占 65 %、`pre·sc` 占 33 %、`dur` 只占 1.7 % ⇒ **要压窗口，先压 pre，其次压 post**。

### 三、"不匹配"的四个实际后果（不是崩，都是暗坑）

1. **缓冲被默默放大**：`W = max(window_cycles, need)` ⇒ 实际缓存 73 281 周波。占用 ≈ 17 条 float64 × 8 B = 136 B/周波 ⇒ **9.5 MB**（3 000 周波时 398 KB）。
2. **每次评估全窗扫描**：实测 `detect_profile()`（合成无事件序列）L＝3 000 → **0.5 ms**、10 281 → **2.4 ms**、20 000 → **7.1 ms**、73 281 → **36 ms**；真实数据全段（4.9~5.9 万周波）**45~55 ms**。评估节流 `eval_every_cycles=10`（0.2 s）⇒ 单画像就占约 **18~27 % 单核**。
3. **大尺度在前段根本用不上**：尺度 sc 需要在候选**前后各留 pre·sc / post·sc 的上下文**，×8 时前/后各要 480 s。本机两个文件里事件距文件头只有 297 s（总线）/ 409 s（分路），都 < 480 s ⇒ **×8 永远轮不到**，这与引擎实测 `scales_hit` 最高只到 1.0 完全吻合。
4. **界面显示的不是真相**：负荷辨识页「周波窗」卡片 `fill / window_cycles` 会显示 **73 281 / 3 000**；`errors` 里那条"需要约 73 281 周波的检测窗…已自动按 73 281 周波缓存评估"也只在状态行，容易忽略。

> **所以"不匹配"本身不会导致漏检**（第 176 轮两条事件都正常识别），代价是内存、CPU、大尺度失效、以及"看到的窗口不是以为的窗口"。

### 四、`post` 不只是"看多长"，它决定**量什么**

`post` 有三重身份（第一节表），其中最容易忽略的是 ②`transition_end` 的目标电平＝**后窗中位数**：

- post 太短 ⇒ 目标电平落在过渡斜坡中段 ⇒ 判出的 `end` 提前、`dur` 偏小、ΔP/ΔI 系统性偏小。
- **本机反证**（同一份真实数据、只改画像 JSON 的 pre/post、μ/σ 不动）：`3000/3000 → 500/1000` 后，总线那条从
  `D²/维 0.37 / conf 0.831 / dur 239 / ΔP +24 642` 变成 `D²/维 3.26 / conf 0.196 / dur 39 / ΔP +19 312` ⇒ **直接拒掉**；
  `→ 10/50` 更差（conf 0.014）。

> 这条实验说明的是**"只改几何不重提画像"会毁掉匹配**，不是"小窗口不好"。真要改，必须用新的 `--pre/--post` **重新提取**，让 μ/σ 与几何同口径。

### 五、怎么设：三条原则 + 设备形态表

1. **`post` ≥ 1.2~2 × 该设备最长过渡 `dur`**（保证目标电平落在平台上、且单尺度搜索就能看到全幅）；`pre` 只要 **10~50 周波（0.2~1 s）**——它只用来建基线，越长越容易把上一个动作卷进来。
2. **`window_cycles` ≥ need（按你要用的 `max_scale` 算），再留 10~20 % 余量**。设小了不会崩（引擎会自动扩），但界面与提示会对不上。
3. **`max_scale` 只在该设备"现场可能出现比画像更慢的形态"时才要大**；画像是慢设备（`post` 已覆盖过渡）时 `1~2` 就够——本机实测 `max_scale = 1/2/4/8` 的**候选与结论逐条完全一致**（5 条候选、2 条接受，一条不差）。

| 设备形态 | 典型 `dur` | `pre` | `post` | `max_scale` | need | 建议 `window_cycles` |
|---|---:|---:|---:|---:|---:|---:|
| 接触器投切（<0.5 s） | ≈25 | 10 | 50 | 2 | 255 | 3 000（默认够） |
| 电机 / 变频器（3~6 s） | 150~300 | 25 | 500 | 2 | 1 400~2 300 | 3 000 |
| **本机慢启停（25 s 斜坡）** | **1 271** | **25** | **1 600** | **2** | **7 731** | **8 000** |
| 同上但保留 3000/3000 | 1 271 | 3 000 | 3 000 | 1 | 10 281 | 10 500 |
| 同上 + 想用 ×8 | 1 271 | 3 000 | 3 000 | 8 | 73 281 | 75 000 |

### 六、本机的三套方案（按"改动最小"排序）

| 方案 | 画像 | `max_scale` | `window_cycles` | 沙盒是否验证过 | 说明 |
|---|---|---:|---:|---|---|
| **A（推荐，最稳）** | 不改（3000/3000） | **1**（或 2） | **10 500**（或 19 500） | ✅ 实测：本数据上 `max_scale=1/2/4/8` 结果完全一致 | 只改两个数字，事件结论不变；缓冲 1.4 MB、评估 ≤2.4 ms |
| B（口径最干净） | **重提**：`--pre 25 --post 1600` | 2 | 8 000 | ❌ 沙盒无 `dev1.csv`，无法重提 | 前后窗覆盖过渡即可；顺带降低 `window_crowded` 概率（后窗截断判据是 `gap < post/20`，post 越小门槛越低） |
| C（维持现状） | 不改 | 8 | 不改（3 000） | ✅（本机就是） | 引擎自动扩到 73 281；接受 9.5 MB / 45~55 ms / 大尺度在前段不可用 |

**改完怎么验**：① 「周波窗」卡片 `fill / window_cycles` 应 ≈ 1:1（不再是 73 281 / 3 000）；② 状态行不再出现"需要约 73 281 周波的检测窗"；③ 候选 CSV 的 `scales_hit` 要覆盖你想用的尺度（若只到 1.0 而 `max_scale=8`，说明大尺度没生效）；④ 两条事件仍应各报 1 条，`D²/维 < 1`、conf 变化在 ±0.1 内。

### 七、顺带：内置提示文案对慢设备是错的（建议改）

`_evaluate_one_profile()` 的提示写的是「建议把画像前后窗改小（典型 10/50～10/200）重提」——对接触器类设备正确，对**25 s 斜坡的本机就是错的**（实测 10/50 会让 conf 掉到 0.014）。建议改成按画像自己的 `dur_cycles` 给建议值：`post ≈ clip(2×dur, 50, 3000)`、`pre ≈ 25`，并按 `max_scale` 直接算出建议的 `window_cycles`。**本轮未改**，等用户确认后立项。

---

## [2026-10-31] 专题：00:07 那次「bus-停止-1 / bus-启动-1」两侧回放**都没识别**——这两段数据里到底有没有该设备的启停？（第 178 轮）

- **类型**：用户专题（数据内容判定 + 检出行为核验；**本轮不改代码**）
- **问题（原话）**：「重新使用该设备2段总线波形数据分别在总线侧与分路侧进行播放，两侧都没有识别到该设备启停，详细输出见 tmp 目录下相关文件，请根据输出的数据详细分析两侧总线数据是否有该设备启停。」
- **是否进入 REPORT.md**：否（一次回放的数据判定）

### 一、先定运行：这次是**新录波的两段**，不是上一轮那两个文件

| 项 | 上一次（第 176 轮，23:38） | **本次（00:07:41）** |
|---|---|---|
| 总线源 | `data\…-bus-停止.csv`（14:33:19–14:53:18） | **`…-bus-停止-1.csv`（16:37:58–16:57:57）** |
| 分路源 | `data\…-bus-启动.csv`（14:53:19–15:09:58） | **`…-bus-启动-1.csv`（15:45:03–16:05:02）** |
| 画像 | `profile_device_20261030_233706.json`（8 维） | **同一份**（两侧 md5 相同，`ebd1c09c…`） |
| 配置 | PT 4 / CT 250、3p3w+重构、`invert_phases='A'`、`quantity='i'`、`window_cycles=3000`、`min_gap_cycles=1000` | **逐字节同**（只有 `source.path` 变了） |
| 版本 | v0.99.27 | v0.99.27（事件 CSV 30 列含 `delta_ih_a`、候选 CSV 32 列） |

- 两侧各 **1172 个 1 s 点**；`run_id` 1793376461432（sid0）/ 1793376461971（sid1），全部写在 `realtime/*_20261031.csv`（墙钟已过 0 点）。
- **注意时间关系**：这两段都在**设备 15:00:08 那次启动之后**（15:45–16:05 与 16:38–16:58），两段之间还空着 33 min，**不是**上一轮那种「首尾相接的停止段/启动段」。
- 配置里 `invert_phases='A'` 这条残留还在，但**依然没有生效**：电流不平衡度中位 4.6 %（总线）/ 6.2 %（分路）、`Ib/Ia = 1.07 / 1.10`、`In ≡ 5×10⁻¹⁵ A` —— 与第 176 轮 7.1 节的判据一致（若生效，3p3w 重构下 B 相＝`ia−ic`，不平衡度会到 ~200 %）。

### 二、结论（先给答案）

| 问题 | 结论 |
|---|---|
| 引擎这次报了几条画像事件？ | **0 条**（两侧）。`nilm_events_20261031.csv` 199 行全是 6 种通用算法；候选诊断 9 条**全部 rejected**，最小 D²/维 **12.90**（阈值 9）。 |
| 是漏检 / 参数没生效吗？ | **不是**。所有超过候选门槛（`min_d`＝½×画像 \|ΔI合成\| ≈ **31.9 A**）的台阶都被评估了：总线 4/4 条、分路 4/4 条（引擎多出一个 scale 2.0 的重叠候选，共 5 条），**没有一条被跳过**。 |
| **这两段数据里有该设备的启停吗？** | **没有。** ①没有任何一条台阶的 8 维签名接近画像（见第四节）；②更硬的一条：**设备当时一直在运行**——已知「停机」时谐波电流 ih＝16.6~16.9 A、「运行」时 ih＝30.5~30.7 A，而这两段的中位分别是 **26.2 A（总线）/ 29.2 A（分路）**，且段内**没有任何 ±15 A 的 ih 台阶**（见第五节）。 |
| 那为什么「两侧都没识别到」？ | **正确行为**，不是缺陷。数据里没有该设备的启停动作，自然没有可报的事件。 |

### 三、引擎输出全表（`tmp/nilm/nilm_profile_candidates_20261031.csv`，9 行）

| 侧 | 时刻 | 方向 | 状态 | 否决标志 | scale | D² | D²/维 | conf |
|---|---|---|---|---|---|---|---:|---:|
| 0 | 16:42:19.321 | START | rejected | `d2_exceeds` | 0.25 | 171.515 | **21.44** | 0.0000 |
| 0 | 16:42:55.541 | START | rejected | `d2_exceeds` | 0.25 | 128.048 | 16.01 | 0.0003 |
| 0 | 16:44:05.961 | STOP | rejected | `d2_exceeds` | 0.25 | 103.190 | **12.90** ← 最接近 | 0.0016 |
| 0 | 16:53:26.421 | STOP | rejected | `d2_exceeds,ambiguous_direction,window_crowded` | 0.25 | 32 852.7 | 4 106.6 | 0.0000 |
| 1 | 15:50:14.374 | START | rejected | `d2_exceeds,sign_flip,window_crowded` | **2.0** | 387.319 | 48.42 | 0.0000 |
| 1 | 15:51:03.634 | START | rejected | `d2_exceeds` | 0.25 | 117.847 | 14.73 | 0.0006 |
| 1 | 15:52:13.674 | STOP | rejected | `d2_exceeds` | 0.25 | 126.417 | 15.80 | 0.0004 |
| 1 | 16:00:01.573 | START | rejected | `d2_exceeds,ambiguous_direction,trajectory_deviates,window_crowded` | 1.0 | 699.234 | 87.40 | 0.0000 |
| 1 | 16:00:48.053 | START | rejected | `d2_exceeds,window_crowded` | 0.25 | 892.913 | 111.61 | 0.0000 |

本机复算（`/tmp/r178/replica.py`：1 s→50 周波展开 + 真实 ih 由 `THD_I×I` 反推 + 原函数 `detect_profile`）得到**同样的 4+5＝9 条候选、同样 0 accepted**（个别 D² 值因 1 s 聚合与本机重采样有 ±10~50 % 差异，结论一致）。

### 四、把两段的**全部台阶**摊开：没有一条是这台设备

以 30 s 前窗 / 30 s 后窗中位差扫描（`|ΔIt|>8 A` 或 `|ΔP|>3 kW` 或 `|ΔIh|>4 A`），总线 22 条、分路 14 条。**画像参考**：START `ΔP −23 933 W / ΔI 35.9,31.2,42.5 A / ΔIt 63.8 / ΔQ +902 var / ΔIh +16.61 / dur 1271 周波`；STOP 为镜像（`ΔIh −16.89`）。

**总线 `bus-停止-1`（16:37:58–16:57:57）**

| 时刻 | ΔP(W) | ΔQ(var) | ΔIa/Ib/Ic (A) | ΔIt | **ΔIh** | 判读 |
|---|---:|---:|---|---:|---:|---|
| 16:39:43 | +10 598 | −174 | −15.2/−14.1/−15.7 | −25.9 | −2.11 | 小负荷，非谐波 |
| 16:41:08 | +7 861 | −486 | −10.5/−11.0/−10.8 | −18.6 | −2.46 | 小负荷 |
| **16:42:15** | **−29 344** | **−2 056** | **+45.3/+43.7/+41.5** | **+75.5** | **+18.82** | **唯一的谐波型启动**（见 4.1） |
| 16:42:54 | −31 356 | −370 | +41.1/+41.6/+42.5 | +72.3 | **−4.91** | 第二个负荷，**不产谐波** |
| 16:44:08 | +60 820 | +1 545 | −87.5/−83.7/−82.1 | −146.1 | −10.46 | 上面两个**一起停**（≈ +30.8k −79 A +19.5ih 与 +32.1k −74 A −5.8ih 之和） |
| 16:46:04 | −11 139 | −623 | +17.7/+12.2/+16.5 | +26.5 | +1.44 | 非谐波 |
| 16:46:53 | +10 355 | +1 175 | −13.3/−14.6/−14.4 | −24.9 | −4.10 | 非谐波 |
| 16:48:11 | +9 499 | +219 | −13.3/−13.1/−11.7 | −22.2 | −2.90 | 非谐波 |
| 16:50:26 | +14 043 | +2 566 | −19.2/−19.4/−20.0 | −33.8 | −2.94 | 非谐波（ΔQ 像电容） |
| 16:53:29 | **+58 924** | **+43 080** | −66.7/−64.0/−74.1 | −118.1 | **−1.63** | **电容组 + 大负荷**，不是设备（ΔIh 几乎为 0） |
| 16:55:04 | +10 404 | **−36 185** | −19.8/−26.1/−14.6 | −35.8 | −0.95 | 电容组 |
| 其余 11 条 | ±3~7 kW | ±0.2~2.9 kvar | ±4~10 A | ±8~15 A | ±1~5 | 小负荷/调节，与设备无关 |

**分路 `bus-启动-1`（15:45:03–16:05:02）**

| 时刻 | ΔP(W) | ΔQ(var) | ΔIa/Ib/Ic (A) | ΔIt | **ΔIh** | 判读 |
|---|---:|---:|---|---:|---:|---|
| **15:47:11** | **−11 637** | −335 | **+20.4/+20.8/+19.9** | **+35.5** | **+14.15** | **谐波型，但只有画像的 ~0.5 倍**（见 4.2） |
| 15:48:07 | +11 363 | +455 | −19.1/−19.2/−18.3 | −32.8 | −12.94 | 上面那台的**停机**（历时 56 s） |
| 15:51:13 | −45 128 | −138 | +60.9/+59.6/+58.4 | +103.0 | +3.57 | 大负荷，**非谐波** |
| 15:52:25 | +45 356 | −99 | −59.4/−60.4/−58.5 | −103.0 | −2.36 | 它的停机 |
| 16:00:55 | **−69 703** | −1 545 | +90.3/+94.1/+89.2 | +158.6 | **+1.05** | 更大的负荷，**非谐波** |
| 其余 9 条 | ±0.8~7 kW | ±0.1~3.7 kvar | ±2~18 A | ±4~18 A | ±0.7~6.2 | 小负荷/调节 |

#### 4.1 最接近的一条：总线 `16:42:15`（唯一「谐波型 + 斜坡」的启动）

用干净的前窗（16:41:40–16:42:12）与平台窗（16:42:36–16:52）重算，避开 16:42:54 的第二个负荷：

| 维度 | 实测 | 画像 START μ | σ | z | 说明 |
|---|---:|---:|---:|---:|---|
| ΔP | **−30 772 W** | −23 933 | 3 590 | **−1.90** | 1.29 倍 |
| ΔQ | **−1 763 var** | +901.8 | 225.4 | **−11.8** | **符号相反**（D² 的 92 % 来自这一维） |
| ΔIa | **+47.8 A** | +35.9 | 5.39 | **+2.20** | 1.33 倍 |
| ΔIb | **+46.5 A** | +31.2 | 4.68 | **+3.27** | 1.49 倍 |
| ΔIc | **+43.3 A** | +42.5 | 6.37 | **+0.13** | 1.02 倍 |
| ΔIh | **+19.49 A** | +16.61 | 2.49 | +1.16 | 1.17 倍，**同号且接近** |
| 斜坡时长 | **约 20 s**（16:42:12 起，16:42:32 到平台） | 25.4 s（1271 周波） | — | — | 形态吻合 |

**这条怎么看**：
- 三个能量量（ΔP 1.29×、ΔIt 1.24×、ΔIh 1.17×）**同时**是画像的 1.2~1.3 倍，`ΔIh/ΔP` 比值为 **0.63 A/kW**，画像为 **0.69 A/kW** —— **属同一类谐波源**，只是这一台比画像那台大一档。
- 两处硬不一致：① **ΔQ 反号**（−1.76 kvar vs +0.90 kvar，12σ）；② **相别次序不同**（实测 A>B>C，画像 C>A>B）。
- 引擎给出的 D²＝171.5 里，**ΔQ 一维占 157.3（92 %）**；其余 7 维合计只有 14.2（2.03/维）。**如果去掉 ΔQ，这一条会被接受**（conf＝e^(−14.2/14)＝0.36）。
- 而现场的 Q **确实不可靠**：16:41:41 有一次电容投切（Q 由 −19.1 跳到 −16.9，+2.4 kvar），16:42:10–16:42:14 又跳 −2.6 kvar，全段还有 ±36 kvar 级的电容投切（16:53、16:55）。⇒ **这条不能一句「不是该设备」就打发，需要人工确认**（见第七节）。

#### 4.2 次接近的一条：分路 `15:47:11`（谐波型但只有一半）

| 维度 | 实测 | 画像 START | 比值 |
|---|---:|---:|---:|
| ΔP | −11 786 W | −23 933 | **0.49** |
| ΔIt | +34.6 A | +63.8 | **0.54** |
| ΔIh | +13.70 A | +16.61 | **0.82** |
| 持续 | 约 56 s（15:47:12 起、15:48:12 回） | 启动斜坡 25.4 s | — |

⇒ 功率和电流只有一半，**谐波却接近全幅**（`ΔIh/ΔP = 1.16 A/kW`，画像是 0.69）⇒ 是**另一个更「脏」的谐波源**（小功率、大谐波，典型变频/整流小负载），不是这台设备。它在 15:48:07 停了，成对出现，形态是「启动→60 s→停止」，与设备的「启动后长期运行」不符。

#### 4.3 STOP 方向：**连一条像的都没有**

画像 STOP 的特征是 `ΔIh −16.89 ± 2.53`。两段的负向台阶里最大的三个是 −12.94（15:48:07）、−11.95（16:44:08，两个负荷一起停）、−10.46（16:44:08 的 30 s 窗版本）——**都在 2σ 之外**，而且它们的 ΔP（+11.4k / +62.3k / +60.8k）与画像的 +23.9 kW 也对不上（0.48× / 2.6×）。

### 五、更硬的一条：**设备当时在运行**，所以两段里没有它的启停

谐波电流 `ih`（2~13 次合量、三相平均，与画像 `d_ih` 同口径，由 `THD_I×I` 反推）是这台设备最好的"在不在跑"指纹——它启停时 `ΔIh ≈ ±16.6 A`：

| 区段 | ih 中位 | ih 四分位 | ih>20 A 的秒数占比 | P 中位 | 说明 |
|---|---:|---|---:|---:|---|
| 上一轮 总线 14:33:19–14:38:17 | **30.67 A** | 28.91–31.87 | **100 %** | −68.7 kW | 设备**运行**（14:38:17 停机后掉到 16.5） |
| 上一轮 总线 14:38:26–14:53:18 | **16.61 A** | 15.26–18.37 | **12 %** | −46.6 kW | 设备**停机** |
| 上一轮 分路 14:53:19–15:00:05 | **16.85 A** | 15.78–17.93 | **9 %** | −48.6 kW | 设备**停机** |
| 上一轮 分路 15:00:33–15:09:58 | **30.47 A** | 29.40–31.89 | **100 %** | −58.0 kW | 设备**运行**（15:00:08 启动后） |
| **本轮 分路 15:45:03–16:05:02** | **29.20 A** | 26.88–30.79 | **100 %** | −56.5 kW | **运行档** |
| **本轮 总线 16:37:58–16:57:57** | **26.24 A** | 23.31–29.24 | **98 %** | −120.9 kW | **运行档**（末端 16:54–16:58 降到 ~22 A，仍远高于停机档 16.6） |

**判读**：
1. 两段的 ih 都落在「运行」档（26~29 A），离「停机」档（16.6~16.9 A）有 9~13 A 的差距。
2. 两段内部**没有任何一条 ±15 A 的 ih 台阶**——最大的正台阶是 16:42:15 的 +19.5（另一台谐波设备），最大的负台阶是 16:44:08 的 −12.0（两台他负荷一起停）。
3. 设备 15:00:08 启动之后，在整段录波的这两段里**一直在运行**；它的下一次停机若发生，应该在 16:58 之后（或两段之间的 33 min 空隙里，但空隙后 16:38 的 ih 仍是 27 A ⇒ 空隙里也没停）。

⇒ **「两侧都没识别到」＝ 数据里确实没有设备启停，检出行为正确。**

### 六、如果这台设备其实**就是** 16:42:15 那台，会是什么情况？

那时要解释三件事，**都不是靠放宽 `d2_max` 能解决的**：

1. **负载率不同**（ΔP/ΔIt/ΔIh 齐刷刷 1.2~1.3 倍）⇒ 画像的 μ 是用设备侧一次启停算的，若设备在不同负载率下启动，应当**按不同负载率补多画像**（`nilm.profile_path` 用 `;` 挂多个，v0.99.26 已支持），而不是放大 σ。
2. **ΔQ 反号**（−1.76 kvar vs +0.90 kvar）⇒ 要么现场无功补偿在这台设备启动时同时动作，要么这台设备的功率因数与画像那台不同。**这件事必须现场核实**，不能靠算法猜。
3. **相别次序不同**（A>B>C vs C>A>B）⇒ 可能是**不同的一次/二次接线**（另一段母线、另一组 CT），或设备内部单相负载分配不同。可用 `profile.phase_map`（1 ABC…6 CBA, 0 自动）试映射——本机把 6 种映射都试了（用 4.1 的实测向量代进 `mahalanobis_diag`）：
   ABC 19.75 / ACB 19.36 / BAC 19.84 / BCA 19.66 / CAB 19.28 / CBA 19.49（D²/维），ΔQ 贡献恒为 **139.7**（占 88~91 %）⇒ **换相序救不回来，瓶颈自始至终是 ΔQ 一维**，不是相序。

### 七、请用户侧确认的三件事（每条 10 秒）

1. **看 ih（谐波电流）曲线**：这两段应该是一条**平直的 26~30 A**，没有 ±15 A 的台阶。对照上一轮那两段（14:38:17 的 −14 A、15:00:08 的 +15 A）——**设备真启停时这个台阶是藏不住的**。
2. **核对文件选段**：`-1` 这两段分别在 15:45–16:05 与 16:38–16:58，**都在 15:00:08 那次启动之后**，中间还空 33 min。如果要验证「设备停止」，应当取**停机那一刻 ±10 min** 的窗口（上一轮 14:33–14:53 那样的选段才对）。建议用「导出指定时间段原始数据」按 ih 台阶重新切两段。
3. **如果 16:42:15 那台就是该设备**：请提供那一刻的设备侧数据（或确认它的负载率 / 无功 / 接线），我们按它**重新提取一条画像**（多画像并存），不要动 `d2_max`。

### 八、复现方式

- 台阶清单 / ΔIh：`.venv/bin/python` 读 `tmp/realtime/{power,current,harmonic}_20261031.csv`（按 `source_id` 分流，`time_local[11:19]` 对齐），30 s 前窗 / 30 s 后窗中位差；ih＝各相 `THD_I/100·I/√(1+THD²)` 的三相均值。
- 引擎同构复算：`detect_profile()` 原函数（1 s→50 周波展开、`ih4` 由 `THD_I×I` 反推、PRM 全默认）⇒ 4+5＝9 条候选、0 accepted，与引擎候选 CSV 一致。
- 本机脚本：`/tmp/r178/{scan,steps,ih,d2,replica,ref,plateau,final}.py`（沙盒内一次性，不随仓库提交）。

---

# 第 179 轮专题：变频 / 多档位设备只录到部分档位 —— 对画像提取的影响与无追加录波时的补救（2026-10-31）

> 用户问题（原话）：「针对目前基于设备画像匹配的算法，如果该设备是变频设备，有多档工作负荷，但设备画像提取时使用的设备侧录波数据只有部分档位的启停，请详细分析这是否影响设备画像提取？如果影响，在没有其它档位负荷录波数据的情况下如何补救？」
>
> 结论先说：**影响，而且影响是结构性的**（μ/σ/候选门槛三处都被"只录到的那一档"绑死）。补救有两条可落地的路：**派生档位画像**（本轮已实现，纯命令行、不改匹配语义）与**档位自由匹配**（原型已实测可用，需改判定语义，待确认后再动）。
> 本轮代码：`elec_tool/nilm_profile.py`（`stage_window` / `derive_stage_profile` / `derive_stage_profiles` / `derive_stage_ladder` / `stage_grid_ratio`）、`tools/nilm_profile.py`（`--derive-stages` / `--derive-grid` / `--derive-from` / `--stage-*`）、`tests/test_r179_stage_profile.py`（8 项）；全量 **514 passed / 1 skipped**。

## 一、直接回答

| 问题 | 回答 |
|---|---|
| 只录到部分档位，影响画像**提取**吗？ | **影响**。画像的 μ 是"被录到的那一档"的均值、σ 是它的重复性（单样本时是经验下限），`min_d` 候选门槛也是它的幅值的一半 —— 三者都只描述了**那一档**这个"点"，而不是这台设备这个"多峰分布"。 |
| 影响有多大？ | 实测（本设备画像，8 维、I 口径）：**只有 0.70~1.30× 的档位能被认出**；**低于 0.50× 的档位连候选都不会生成**（静默漏报，诊断 CSV 里连一行都没有）；把不同档位混进同一份画像更糟 —— μ 落到两档之间（一个不存在的档位）、σ 涨到 41~64 %、接受区间被拉成 **0.10~1.45×**，"同幅值纯线性假负荷"会被**确认**（conf 0.43）。 |
| 没有其它档位的录波，能补救吗？ | 能，但要接受"外推"这件事：① **派生档位画像**（把已录档位按倍数 k 缩放成一组假设画像，用 `nilm.profile_path` 的 `;` 列表一起加载）——本轮已实现并验证；② **档位自由匹配**（判定时把整体幅度当自由参数，先解出档位 k 再算形状残差）——原型实测可用，但要改判定语义与方向标签，待确认；③ **稳态运行态辨识**（不靠启停台阶，靠运行态的 I/P/ih 水平聚类）——路线级改动。 |

---

## 二、画像提取里到底哪几个量被"档位"绑住（代码级）

| 量 | 代码位置 | 语义 | 只录到部分档位时的后果 |
|---|---|---|---|
| μ | `nilm_profile.py:134` `mu = X.mean(axis=0)` | 该方向多次事件的**均值** | μ ＝ 被录到的那几档的均值。只录一档 ⇒ μ 就是那一档；录了两档 ⇒ μ 落在两档之间（**不存在的档位**） |
| σ | `nilm_profile.py:136` `max(sd, 15 %/25 %·\|μ\|, 绝对下限)` | 事件间**重复性**，n=1 时全靠下限 | 下限是**相对**的（15 %），所以 σ 永远只覆盖"同一档内"的波动，不可能覆盖档与档之间 2~3 倍的差距 |
| 候选门槛 `min_d` | `nilm_profile.py:511` `min_d = 0.5·min(amp)` | 双滑窗候选的最小台阶幅值 | ＝ **0.5×画像幅值** ⇒ 比录制档位小一半以上的档位**连候选都不生成**（没有任何诊断行，看起来像"设备没动"） |
| 判定 | `nilm_profile.py:635` `accepted = 无 d2_exceeds/sign_flip 且 conf ≥ min_conf` | `conf = exp(−D²/2d)` | 档位差 δ 时，跑幅的那些维各贡献 `(δ/0.15)²` ⇒ 平均到 8 维：**conf ≥ 0.3 等价于档位在 ±30 % 内** |
| 轨迹模板 | `fit_group` 的 `template` | 归一化（除以稳态 Δ） | 归一化后与档位无关 ⇒ **不是**瓶颈（实测把 dur 按 k 缩放、peak 改成 2.0，D²/维 只变 0.06~0.21） |
| 状态机 | `_evaluate_one_profile` 的 `slot["state"]` | 二态 on/off | 多档设备"40 % → 100 %"是**档位变化**，不是启停；按现在语义它要么被拒、要么被误当第二次启动 |

**一个容易忽略的副作用（λ 收缩）**：`mahalanobis_diag`（`nilm_profile.py:269`）的 `var += λ·median(var)` 用的是**跨量纲**方差的中位数（A²、W²、比值²、周波² 混在一起）。本画像 `median(var)=34.85`（由 3 个 ΔI 维与 d_ic 维主导）⇒ `λ·median=3.49` 被**加到每一维**。后果：

| 维 | 名义 σ | λ 之后有效 σ | 放大 |
|---|---:|---:|---:|
| ΔIa | 5.392 A | 5.706 A | 1.06× |
| ΔIh | 2.491 A | 3.113 A | **1.25×** |
| 启动峰值比 | 0.478 | 1.927 | **4.03×** |
| ΔP / ΔQ / dur | 3590 W / 225 var / 635 | 不变 | 1.00× |

即 **`peak_ratio` 这一维事实上失效**（±1.93 的容差，电机 5~7 倍冲击也只剩 2.5σ），`d_ih` 的判别余量也被削掉 20 %。这与第 178 轮"16:42 那条 92 % 的 D² 来自 ΔQ、其余 7 维只剩 2.03/维"是同一件事的两面。**本机 λ=0.1 是默认值**；若在意峰值比/谐波判别，建议把 `profile.lambda_rel` 降到 **0.01~0.02**（实测：档位窗口 0.70~1.30 → 0.75~1.25、线性假负荷 conf 0.062 → 0.027）。本轮**未改默认值**（向后兼容），列入第 180 轮候选。

---

## 三、实测一：单档画像到底"认几档"

方法：把本设备画像（`tmp/nilm/profile_bus_profile_device_20261030_233706.json`，8 维、I 口径、单样本/方向）自己的 μ 按 k 缩放成合成事件，走真实 `match_event`（同一套 λ、`d2_max=9`、`min_confidence=0.3`）。

| k（相对录制档位） | 0.20 | 0.40 | 0.50 | 0.60 | **0.70** | 0.85 | **1.00** | **1.30** | 1.40 | 1.50 | 2.00 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| D²/维 | 16.6 | 9.4 | 6.5 | 4.2 | **2.34** | 0.65 | 0 | **2.34** | 4.2 | 6.5 | 26.0 |
| conf | 0.000 | 0.009 | 0.039 | 0.125 | **0.311** | 0.72 | 1.000 | **0.311** | 0.125 | 0.039 | 0.000 |
| 判定 | 拒 | 拒 | 拒 | 拒 | **接受** | 接受 | 接受 | **接受** | 拒 | 拒 | 拒 |

- **可接受区间 = 0.70~1.30×**（宽 1.86 倍），**起作用的约束是 `min_confidence=0.3`（D²/维 ≤ 2.41）而不是 `d2_max=9`**（与第 171 轮结论一致）。
- **候选门槛对应的档位 = 0.499×**（`min_d = 31.90 A`，画像幅值 63.98 A）⇒ **0.5× 以下静默**（连诊断行都不产生）。
- 把 λ 改成 0（`lambda_rel=0`）⇒ 窗口收窄到 **0.75~1.25**；其余结论不变。

**推论**：变频设备若实际有 30 / 50 / 70 / 100 % 四档，只录到 100 % 时 —— 70 % 档能认（边缘）、50 % 档被拒、30 % 档**完全看不见**。

---

## 四、实测二：把不同档位**混进同一份画像**（最坏做法）

用同一份真值向量，按不同档位组合造事件、走真实 `fit_group` 重新提取：

| 提取时的样本 | μ 折算档位 | σ/\|μ\|（ΔI/ΔP/ΔQ/ΔIh） | 接受区间 | "同幅值纯线性假负荷"（ΔQ=ΔIh=0） |
|---|---:|---|---:|---|
| ① 100 % ×1（现状） | 0.973 | 15 % / 15 % / 25 % / 15 % | **0.70~1.30** | D²/维 7.3、conf 0.027 ⇒ 拒 ✅ |
| ② 100 % ×3（同档重复） | 0.998 | 15 % / 15 % / 25 % / 15 % | 0.70~1.30 | 7.4、0.024 ⇒ 拒 ✅ |
| ③ 100 % + 40 % 各 1 | **0.687** | **64 % / 61 % / 59 % / 62 %** | **0.10~1.45** | 1.7、**0.426 ⇒ 接受 ❌** |
| ④ 100 % + 70 % 各 1 | 0.832 | 27 % / 28 % / 25 % / 25 % | 0.45~1.25 | 5.0、0.080 ⇒ 拒（勉强） |
| ⑤ 100/70/40 各 1 | 0.688 | 42 % / 42 % / 43 % / 44 % | 0.15~1.25 | 2.8、0.245 ⇒ 拒（贴边） |
| ⑥ 100×2 + 40×2 | 0.697 | 50 % / 50 % / 49 % / 47 % | 0.10~1.35 | 2.3、**0.324 ⇒ 接受 ❌** |

三句话：
1. **μ 会落在两档之间**（69 % 这种"不存在的档位"）——等于给设备编了一个假身份；
2. **σ 从 15 % 涨到 41~64 %**（两个样本时 `sd=ddof1`＝档距/√2），判别力按平方衰减；
3. 于是"同幅值、同相别、纯线性"的他负荷也能过 —— 这正是第 171 轮警告的"孪生设备"场景。

⇒ **绝对不要用"把各档事件都提进一份画像 + 放大 σ"的办法覆盖档位**。同理，把 `d2_max` 从 9 放到 30 也不解决（它只影响"要不要报 `d2_exceeds`"，真正卡人的是 `min_confidence`），只会把误报放进来。

---

## 五、补救方案 A（已实现）：派生档位画像

思路：已录档位的画像（μ, σ）＝这台设备在**某一档**的指纹；档位变化在特征空间里近似是**同比缩放**（ΔIa/Ib/Ic、ΔP、ΔQ、ΔIh 都随出力同比变），因此可以把 μ、σ 同乘 k 得到"假设画像"，覆盖未录档位。派生件就是普通画像 JSON（多了一个 `stage` 段说明来源与假设），用 `;` 挂进 `nilm.profile_path` 即可，**引擎侧零改动**。

**新增代码**（`elec_tool/nilm_profile.py`）：

| 函数 | 作用 |
|---|---|
| `stage_window(doc)` | 量出"这份画像认几档"（`k_lo~k_hi`）与"低于多低连候选都不生成"（`k_gate`）——与线上判定同一口 |
| `derive_stage_profile(doc, k, q_mode, ih_exp, dur_exp)` | 派生一份：幅度维 ×k、σ 同乘并抬回经验下限、`peak_ratio` 不动、`dur_cycles` 默认不动、丢弃原始 `events` 明细、写 `stage` 元数据 |
| `derive_stage_ladder(doc, count, center)` | 按**每份派生画像自己实测的窗口**接力铺开（`k_new·k_lo(k_new) = k_prev·k_hi(prev)`，3 次不动点迭代）⇒ 相邻两份首尾相接：不漏档、不重复报 |
| `derive_stage_profiles`、`stage_grid_ratio` | 上层封装；`ratio` 缺省＝实测 `k_hi/k_lo`（不是硬编码常数） |

**CLI**（`tools/nilm_profile.py`）：`--derive-stages "0.4,0.7"`、`--derive-grid N`、`--derive-from <既有画像.json>`（不重跑提取）、`--stage-q-mode scale|const`、`--stage-ih-exp`、`--stage-dur-exp`、`--stage-out-dir`。

**实跑**（本设备真实画像，5 份阶梯）：

```
python tools/nilm_profile.py --derive-from tmp/nilm/profile_bus_profile_device_20261030_233706.json --derive-grid 5 --stage-out-dir output/nilm/stage

基准画像：…_233706.json（设备 device，未重新提取）
档位派生（v0.99.28）：基准画像录到的是 1 档，可接受区间 0.7~1.3×，候选门槛 31.9022 A（低于 0.499× 的档位连候选都不会生成）
  · device@29%   k=0.2899   可接受 0.68~1.32×  min_d=9.2498 A
  · device@54%   k=0.5385   可接受 0.69~1.31×  min_d=17.1781 A
  · device       k=1        （＝基准画像，未复制）
  · device@186%  k=1.857    可接受 0.7~1.3×   min_d=59.247 A
  · device@345%  k=3.449    可接受 0.7~1.3×   min_d=110.03 A
```

**验证**（`tests/test_r179_stage_profile.py` 8 项 + 本机实测）：

| 检验 | 结果 |
|---|---|
| 合成档位 0.25~2.5× 的覆盖 | 5 份阶梯：**无空洞**；只有交接带（±1 %）会被两份同时接受 |
| 派生画像认自己那一档 | 40 % 档事件 → 派生 40 % 画像 D²/维 ≈ 0、conf 1.000；同事件给 100 % 画像 → 拒 |
| 对真实他负荷的误纳 | 00:07 那次 **9 条真实候选（16:42:19 / 16:42:55 / 16:44:05 / 16:53:26 / 15:47… / 16:00…）全部 rejected，0 误纳** |
| 端到端 | 合成 40 % 台阶喂派生 40 % 画像 → `detect_profile` 报出 1 条 accepted START（D²/维 < 2）；同段给 100 % 画像 → 0 条 accepted |
| 成本 | 每个画像每次评估 ≈ 4~5 ms（L≈10 281 周波）；5 份 ≈ +20~25 ms/块（块 0.64 s）≈ 3~4 % 单核；20 min 回放墙钟约 +30~60 s |
| 运行目录 | 引擎按 `;` 列表逐画像复制到 `output/{时间}/nilm/`（第 173 轮已实现），派生的 `device_id`（`device@54%`）不同名 ⇒ 不会触发"重复 device_id"提示 |

**必须知道的三条限制**：

1. **派生是假设**：只有 ΔP/ΔI/ΔQ/ΔIh 按倍数外推，`peak_ratio` / `dur` 不外推（实测这样反而最稳：真按 k 缩放 dur、把 peak 提到 2.0，D²/维 只变 0.06~0.21）。档位变了以后真实的无功与谐波未必同比 —— 若知道"励磁无功≈不变"，用 `--stage-q-mode const`；若轻载 THD 明显升高，用 `--stage-ih-exp 0.7~0.9`。
2. **低档位的判别余量最薄**：ΔIh 只有 5 A 的小谐波设备，派生到 40 % 档后 σ_ih 被 **2 A 绝对下限**接管 —— "同幅值纯线性假负荷"的 conf 落在 **0.26~0.35**（贴着 0.3 的门槛，可能误纳）；带 3 A 谐波的他负荷实测 conf 0.351 **会被接受**。派生档位 ≈0.3× 以下请务必看候选 CSV 的 `c_d_q`/`c_d_ih`，或干脆只派生 0.5× 以上。
3. **档位"切换"仍然看不见**：派生画像只覆盖"在某档启停"；设备从 70 % 调到 100 % 是一个 0.3× 的台阶，落在所有派生画像的窗口之间 ⇒ 不报（这通常可以接受：它不是启停）。要识别档位切换必须走方案 B 或 C。

---

## 六、补救方案 B（原型已验证，需确认后实施）：档位自由匹配

思路：判定时把**整体幅度当自由参数**——用加权最小二乘解出唯一缩放 `s`（`s* = Σ(x_i μ_i/var_i) / Σ(μ_i²/var_i)`，只用 6 个幅度维），σ 随 s 同比缩放，再算**形状残差** D²。`s` 就是"这一档是多少 ×"，直接作为事件字段输出。窗口 0.70~1.30 的硬边界随之消失，一份画像覆盖任意档位。

**实测**（同一份真实画像、同一套 λ/d2_max/min_confidence）：

| 用例 | 结果 |
|---|---|
| 合成档位 0.15 / 0.30 / 0.50 / 0.70 / 1.00 / 1.50 / 2.00 / 3.00× | **全部 ACCEPT**，解出的 s 与真值逐位相同（0.15/0.30/…） |
| 00:07 那次 9 条真实候选 | **全部 rejected**（最好的 16:44:05 从 D²/维 12.90 降到 5.62，仍 > 2.41） |
| 16:42:19（同形状但 ΔQ 反号） | 拒（D²/维 24.6）——自由档位**没有**绕过无功符号这条证据 |
| 假设"ΔQ 也同号"的同形状事件 | **ACCEPT**（s=1.19、D²/维 0.79、conf 0.673）⇒ 正是"同一台设备的另一档"该有的行为 |
| 同幅值纯线性假负荷（ΔQ=ΔIh=0） | 拒（D²/维 6.97、conf 0.031）；半幅值版本 4.69、conf 0.096（余量 2 倍，比固定档位时薄） |

**要落地必须一起改的三处**（否则会出新问题）：

1. **候选门槛**：`min_d = 0.5·amp` 仍是"档位下限 0.5×"的硬闸，自由档位也必须把它放开（新增 `profile.min_stage`，如 0.2 ⇒ `min_d = min_stage·amp`），否则低档位照样静默；
2. **方向语义**：档位切换（70 %→100 %）会被解成 `s=0.3` 的 "START"，状态机误置 on。要新增 `event_kind = start|stop|stage_up|stage_down`（按 s 与当前状态判定），CSV 加 `stage_scale` 列；
3. **误报闸门**：自由档位把"形状像"的他负荷也放进来了，建议同时输出 `s` 与残差的**各维贡献**，并把 `min_confidence` 提到 0.4（实测线性假负荷 0.031、半幅 0.096，余量仍够）或加"ΔIh/ΔP 比值"的一致性约束。

**投入**：`match_event` 加一个 `stage_free` 分支（≈60 行）+ `detect_profile` 传参 + 事件字段/CSV 列 + 界面开关 + 测试（≈150 行），与现有语义**互斥可关**（配置 `profile.stage_mode = fixed|free|grid`）。

---

## 七、补救方案 C（路线级，供决策）：稳态运行态辨识

变频设备多数时间是"一直在跑、偶尔换档"，**启停事件本身很少**。更贴合现场需求的其实是"这台设备现在在不在跑、在哪一档"。做法：用**稳态水平**（三相基波电流、ΣP、ΔIh、与该设备"停机基线"的差）在总线上做 2~3 维聚类，把"运行档位"当成状态而不是事件；启停由状态迁移触发。代价是：需要该设备的"停机基线"（可从夜间/停机段估）、需要更长的时间尺度（分钟级），且与现在的"事件流"输出模型不同 —— **不建议本轮动**，作为第 180+ 轮的方向。

---

## 八、操作 SOP（用户侧，三条命令）

```powershell
# ① 已有画像 → 派生 5 档（不改匹配语义，引擎照旧）
python tools/nilm_profile.py --derive-from output\nilm\profile_device_20261030_233706.json --derive-grid 5 --stage-out-dir output\nilm\stage

# ② 把打印出来的整串路径（; 分隔）填进总线侧「设备画像匹配 → 画像文件路径」，勾选启用，保存总线侧配置
#    然后正常播放；事件表 / CSV 里 device_id 会带 @29% / @54% / @186%，一眼能看出是哪一档

# ③ 复核：看 output\{时间}\nilm\nilm_profile_candidates_*.csv
#    · 每一档的 accepted 事件 D²/维 是否 < 1、c_* 里最大的是哪一维
#    · 低档（≤0.5×）若出现 accepted 但 c_d_q / c_d_ih 很大 ⇒ 大概率是"同幅值的他负荷"，回头收紧
```

**判断要不要派生**：先用 `stage_window` 看一眼（CLI 会打印"可接受区间"）。若现场各档位都落在 **0.70~1.30×** 内（例如变频器只有 ±15 % 的调速），**不用派生**；若有 2 倍以上的档位差，按需派生 1~2 份就够（不是越多越好：每份都会把候选门槛降低一档、候选数增加）。

---

## 九、本轮没做的事 / 风险

1. **界面入口没做**：目前只有 CLI（`--derive-*`）与 Python API；Web「数据处理 · 设备画像提取」面板还没有"派生档位"输入框与按钮。需要的话下一轮加（后端 `POST /api/process/nilm_profile` 加 `derive_stages` 字段 + 前端一个小节 + 结果表列）。
2. **方案 B 未实施**：语义变更（`stage_mode`、`start/stop/stage` 事件类型、CSV 新列）需用户确认后再动。
3. **λ 收缩跨量纲**：`peak_ratio` 有效容差被放大 4 倍（见第二节）。改 `lambda_rel` 默认值会影响所有既有画像的判定结果，属"需用户拍板"的兼容性变更。
4. **派生档位的真值校验缺数据**：沙盒没有这台设备的低档实录，端到端只能合成验证；上线前请用"已知某一档启停"的一段总线数据做一次反向验证（预期：该档 accepted、相邻档 rejected）。

---

# 第 180 轮（2026-10-31）：按第 179 轮的第 1~3 项落地——派生档位界面入口 / 档位自由匹配（方案 B）/ `lambda_rel` 默认 0.02

> 第 179 轮末尾问了四件事，用户答复「按上述 1-3 点进行实施修改」：
> ① 派生档位的**界面入口**；② **方案 B**（档位自由匹配）；③ `profile.lambda_rel` 默认 **0.1 → 0.01~0.02**。
> 第 4 项（用"已知某一档"的总线数据做反向验证）**用户未答复** ⇒ 本节把它列为待验证，不做结论。

## 一、本轮交付（三项，全部可用）

| 项 | 落地内容 | 默认行为 |
|---|---|---|
| ① 派生档位界面入口 | 数据处理页「设备画像提取」新增 **④ 派生档位画像**：倍数（逗号分隔）/ 输出目录 / ΔQ 缩放方式 / 谐波指数 + 「派生档位画像」「复制派生路径串」；结果区给出**每档的可接受区间、候选门槛 min_d、静默区、文件名**与可直接粘贴的 `;` 路径串、等价命令 | 不上总线、不改匹配语义，只是**写文件** |
| ② 档位自由匹配（方案 B） | `match_event(..., stage_free=True)`：加权最小二乘解唯一缩放 `s*`（只用 ΔI/ΔP 标定）→ σ 随 s 同比缩放 → 形状残差 ⇒ `conf`；事件新增 `stage_scale`（解出的档位倍数）与 `event_kind`（`start/stop/stage_up/stage_down`）；已在运行时出现的同向台阶＝**升档/降档**（不改 on/off 状态、不再记 `state_mismatch`） | `stage_free=0`（**关**）＝旧行为一字不改 |
| ③ `lambda_rel` 默认 | `0.1 → 0.02`（配置默认值 + `nilm_profile` 里 3 处函数默认值同步） | 全局判定口径**变更**，见第三节 |

新增配置项（`nilm.algorithms.profile`，旧配置缺键自动取默认 ⇒ 兼容）：

| 键 | 默认 | 作用 | 校验 |
|---|---|---|---|
| `stage_free` | `0` | 1＝档位自由匹配（一份画像覆盖任意档位） | 只能是 0 / 1 |
| `min_stage` | `0.5` | 候选门槛＝`min_stage × 画像幅值`（0.5＝旧行为；档位自由建议 0.2~0.3） | (0, 3] |
| `stage_min_scale` | `0.2` | 解出的 s 的下限 | (0, 20] 且 < 上限 |
| `stage_max_scale` | `3.0` | s 的上限 | 同上 |
| `stage_dim_max` | `9.0` | **单维否决**：任一维 D² > 该值就拒（只在 `stage_free=1` 时生效；0＝关） | ≥ 0 |
| `lambda_rel` | `0.02`（原 0.1） | 协方差收缩系数 | > 0 |

## 二、代码改动清单

| 文件 | 改动 |
|---|---|
| `elec_tool/nilm_profile.py` | 新增 `STAGE_REF_FEATURES`（标定 s 只用 ΔI/ΔP）、`_stage_scaled_stats`（σ 随 s 缩放并抬回下限）、`_fit_stage`（加权最小二乘 + 残差）；`match_event` 加 `stage_free/stage_range` 参数并返回 `stage_scale` / `d2_dim_max` / `d2_dim_name`；`detect_profile` 读 5 个新参数、落 `dim_exceeds` 标志、把"运行中同向台阶"识别为 `stage_change`；`stage_window` 的候选门槛改按 `min_stage`；`derive_stage_profiles` / `derive_stage_ladder` 修掉"混入 `lam_rel` 就 TypeError"的问题 |
| `elec_tool/config.py` | 新增 5 个参数默认值；校验放行 0（`stage_free` / `stage_dim_max`）；`lambda_rel` 默认 0.02（附回退说明：改回 0.1 即恢复旧口径） |
| `elec_tool/nilm.py` | `NilmEvent` 加 `stage_scale` / `event_kind`；`_CSV_FIELDS` 末尾追加两列（旧的 31 列不变，`_rotate_if_header_differs` 自动转表头）；候选诊断 CSV 追加同名两列；档位变化不改 `slot["state"]`；`summary["profile"]` 暴露 `stage_free/min_stage/lambda_rel` |
| `app/server.py` | 新接口 `POST /api/process/nilm_profile_stage`（派生 + 写盘 + 每份实测窗口/门槛 + 路径串 + 等价命令） |
| `app/static/index.html` / `app.js` | ④ 派生档位画像小节、结果表、复制路径串；事件表显示「xx % 档」「升档/降档」；画像算法参数区新增 5 个输入 |
| `tests/test_r180_stage_free.py`（新，22 用例） | 配置默认值与校验、λ 收窄、全档位收/拒、量程夹取、谐波/无功假负荷、单维否决、`min_stage` 门槛、档位变化不改状态、CSV 列、7 维旧画像、派生 JSON 元数据、界面元素与接口注册 |
| `tests/test_r12_nilm.py` | 事件 CSV 表头断言 `[-7:]` → `[-9:]`（新列追加在末尾） |

## 三、改动 ③ 的实测影响（`lambda_rel` 0.1 → 0.02）

λ·median(σ²) 是**跨量纲**的常数项（本机 median(σ²)=34.85，λ=0.1 时每维 +3.49）——对小量纲的维（`peak_ratio`≈1.6、`d_ih`≈16.6）相当于"白送容差"：

| 维 | σ 原值 | λ=0.1 有效 σ | λ=0.02 有效 σ |
|---|---|---|---|
| `peak_ratio` | 0.478 | 1.927（**4.03×**） | 0.962（2.01×） |
| `d_ih` | 2.491 | 3.113（1.25×） | 2.615（1.05×） |
| `d_ia` | 5.392 | 5.706（1.06×） | 5.446（1.01×） |
| `d_p` / `d_q` / `dur_cycles` | — | 1.00× | 1.00× |

判定结果的变化（同一画像、同一候选）：

| 项 | λ=0.1 | λ=0.02 |
|---|---|---|
| 单档可接受区间 | 0.70~1.30× | **0.72~1.28×**（窗口收窄） |
| 第 178 轮确认的 bus 14:38:16 STOP | D²/维 0.54、conf 0.748 | 0.58、**0.755**（真实事件反而略升：收缩项不再把 peak 维撑大） |
| branch 15:00:08 START | 0.50、0.764 | 0.54、**0.777** |
| 同幅值纯线性假负荷（ΔIh=0、ΔQ=0） | D²/维 5.57、conf 0.062 | **7.04、0.030**（判别力回收） |
| 00:07 那次 9 条真实候选 | 全部 rejected | 全部 rejected（无回退） |

**回退方式**：把 `nilm.algorithms.profile.lambda_rel` 改回 `0.1` 即恢复旧口径（配置文件 / 界面参数框都可改）。窗口收窄的副作用是**单份画像认的档位更少**，所以本轮的 ② 与 ① 正好配套（自由档位/派生网格负责覆盖，λ 负责判别力）。

## 四、改动 ② 的实测（档位自由匹配）

### 4.1 合成事件：严格同比的整档 0.2~3.0× 全收，且 s 精确

| k | 0.2 | 0.3 | 0.5 | 0.7 | 1.0 | 1.5 | 2.0 | 3.0 |
|---|---|---|---|---|---|---|---|---|
| 解出 s | 0.20 | 0.30 | 0.50 | 0.70 | 1.00 | 1.50 | 2.00 | 3.00 |
| conf | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

（合成事件与画像严格共线 ⇒ 残差 0。这一列只能证明"机械上能覆盖全档"，**不能**证明现场判别力——判别力看 4.2~4.4。）

### 4.2 真实事件不能掉链子

| 事件 | 固定档位 | 档位自由 |
|---|---|---|
| bus 14:38:16 STOP（第 178 轮确认） | D²/维 0.58、conf 0.755 | D²/维 0.56、conf **0.755**、s=0.975、单维最大 1.68 |
| branch 15:00:08 START（第 178 轮确认） | 0.54、0.764 | 0.51、**0.777**、s=0.982、单维最大 2.06 |

### 4.3 00:07 那次回放的 9 条真实候选：仍然全部拒

| 时刻 | 方向 | 固定 D²/维 / conf | 自由 D²/维 / conf | 解出 s | 单维最大 |
|---|---|---|---|---|---|
| 16:42:19 | START | 21.59 / 0.000 | 16.34 / 0.000 | 1.20 | 124.1 |
| 16:42:55 | START | 17.78 / 0.000 | 12.00 / 0.002 | 1.38 | 49.6 |
| 15:51:03 | START | 16.93 / 0.000 | 8.91 / 0.012 | 1.55 | 44.9 |
| 16:44:05 | STOP | 15.00 / 0.001 | **6.37 / 0.041** | 1.56 | 44.0 |
| 15:52:13 | STOP | 17.50 / 0.000 | 7.53 / 0.023 | 1.66 | 34.7 |
| 16:00:48 | START | 116.55 / 0.000 | 11.03 / 0.004 | 2.50 | 42.7 |
| 其余 3 条 | — | >100 / 0 | >170 / 0 | 0.15~2.11 | >300 |

**注意**：档位自由**会系统性压低平均 D²**（16:44:05 从 15.00 掉到 6.37，看似快过 `d2_max=9` 了）。真正拦下它的是 `min_confidence=0.3`（等价 D²/维 ≤ 2.41）与单维否决。⇒ **开 `stage_free` 时不要同时调大 `min_confidence` 之外的闸门、也不要把 `min_confidence` 降到 0.2 以下**。

### 4.4 误报闸门（单维否决是必须的）

| 构造的事件 | 平均门（仅 conf ≥ 0.3） | 加单维否决（`stage_dim_max=9`） | 单维最大 | s |
|---|---|---|---|---|
| ΔIh 只有 0.4× 的同幅值事件 | **收**（0.407） | **拒** | 14.4 | 1.00 |
| ΔQ=0 的同幅值事件 | **收**（0.368） | **拒** | 16.0 | 1.00 |
| ΔIh=0（纯线性） | 拒（0.082） | 拒 | 40.0 | 1.00 |
| ΔQ 反号 | 拒（0.018） | 拒 | 64.0 | 1.00 |
| 16:42:19 他设备实测 | 拒（0.000） | 拒 | 124.0 | 1.20 |
| **同形状且 ΔQ 同号**（假设的另一档） | 收（0.442） | 收（单维 6.4） | 6.4 | 1.20 |

* 前两行正是第 179 轮担心的"丢谐波判据"：8 维平均会把单维 4σ 摊成"还行"，必须补**单维否决**；
* 最后一行是**期望行为**（同一台设备的另一档就该收）；
* **标定 s 只用 ΔI/ΔP**（`STAGE_REF_FEATURES`）：若让 ΔQ/ΔIh 参与标定，一个"谐波不成比例"的他负荷会把 s 拖走、残差摊到所有维，单维否决就失效了（实测 s 掉到 0.6~0.9、单维贡献只有 1.5~2.2）。

### 4.5 候选门槛 `min_stage`

| `min_stage` | 0.5（旧） | 0.3 | 0.2 |
|---|---|---|---|
| 候选门槛（本机画像，三相合成 63.98 A） | 31.90 A（＝50 % 档） | 19.14 A（30 %） | 12.76 A（20 %） |
| 效果 | 0.5× 以下静默 | 0.3× 以上能出候选 | 0.2× 以上能出候选 |

⚠ 降门槛只是"看得见"，**认不认**仍由形状残差决定：0.3~0.5× 的档位在 8 维下 conf 只有 0.10~0.39，通常**过不了 0.3**（见 4.3 第一张表的固定档位列）。所以 `min_stage` 必须与 `stage_free`（或派生网格）**一起开**才有意义。

### 4.6 方向语义与状态机

* 设备在 OFF、出现正台阶 ⇒ `event_kind=start`，`state` 置 on；
* 设备在 ON、再出现正台阶 ⇒ `event_kind=stage_up`（`stage_scale`＝**台阶幅值**占画像档位的比例，如 1.0→1.6 记 0.6），**`state` 不变**、不再记 `state_mismatch`、置信度不再折半；
* 负向同理 `stage_down` / `stop`；
* 事件 CSV 的旧列（`direction=up/down`）语义不变，老工具照旧能用。

### 4.7 成本

| 场景 | 一次 `detect_profile`（L=10 281 周波） |
|---|---|
| 固定档位（`stage_free=0`） | 7.5 ms/块 |
| 档位自由（`stage_free=1`） | 12.1 ms/块（多一次最小二乘 + σ 重算，≈+60 %） |

块长 0.64 s ⇒ 档位自由单画像约占单核 1.9 %；配 5 份派生画像（路线 A）则 ≈37 ms/块 ≈ 6 %。两者都可接受，不必为此加缓存。

## 五、界面（数据处理页 ④ 派生档位画像）

* 位置：数据处理 → 设备画像提取 → 表单第 ④ 组（在 ③ 事件前后窗之后）；「提取设备画像」成功后按钮才可用；
* 输入：档位倍数（`0.4,0.7,1.2`，相对**本次提取到的那一档**）、输出目录（空＝画像同目录）、ΔQ 缩放（scale / const）、谐波指数 `ih_exp`；
* 输出：结果表 **档位倍数 / 档位 % / 设备 ID / 可接受区间 / 候选门槛 min_d / 静默区 / 文件名**，外加基准画像的单档窗口提示与三条注意事项；
* 「复制派生路径串」把 `;` 分隔的**全部**路径复制到剪贴板（含基准画像），到负荷辨识页「画像文件路径」粘贴即可；结果区同时显示**等价 CLI 命令**（`python tools/nilm_profile.py --derive-from … --derive-stages …`），便于离屏复现；
* 事件表：画像事件在「检验量」列显示 `xx % 档`（`stage_scale≠1` 时）与 `升档` / `降档` 徽标。

## 六、向后兼容

| 对象 | 兼容方式 | 验证 |
|---|---|---|
| 旧配置（无新键） | `NilmConfig.params()` 只取默认值里存在的键，缺键 → 默认 | `test_config_defaults_stage_free_and_lambda` |
| 旧画像（7 维，无 `d_ih`） | 维数按 μ 长度定，缺的维跳过；`stage_free` 照常可用 | `test_old_seven_dim_profile_still_works_with_stage_free` |
| 旧事件 CSV（31 列） | 读回时按表头索引，缺列取默认；新写文件自动转表头 | `test_r12_nilm`（读回旧文件） + `_rotate_if_header_differs` |
| 旧判定口径 | `stage_free=0` + `min_stage=0.5` + `stage_dim_max` 不生效 ＝ 与 v0.99.28 完全一致；`lambda_rel` 是唯一的全局变更，改回 0.1 即可 | 全量 pytest 536 passed / 1 skipped |

**建议的开启顺序**（现场）：先只改 `lambda_rel`（保持 `stage_free=0`）跑一轮 → 确认真实事件仍 confirmed、误报没变多 → 再开 `stage_free=1`（同时 `min_stage=0.2~0.3`，`min_confidence` 0.3→0.35~0.4）→ 最后视需要开派生网格补低档。

## 七、仍然存在 / 待验证

1. **第 4 项（反向验证）用户未答复，本轮未做**：仍缺"已知某一档"的总线实录来验证"该档 accepted、相邻档 rejected"。合成台阶验证见 `tests/test_r180_stage_free.py::test_detect_profile_applies_dim_veto_and_reports_stage_scale`；现场可用第 179 轮第二节的判据（候选 CSV 的 `c_*`）复核。
2. **低档位谐波维余量薄**：ΔIh 的绝对下限 2 A 在低档位接管（0.4× 档时名义 σ_ih 只有 0.96 A），`ΔIh=0.4×` 的假负荷在低档能到 conf 0.4 以上 ⇒ 低档仍要人工看 `c_d_ih`。
3. **ΔQ 是否随档位缩放因设备而异**：本机制假定各幅度维同比缩放；电机励磁无功基本恒定（`q_mode=const`）的设备，k≤0.5 时会被拒（实测误杀 8/48 组，全是 `q_mode=const` 且 k≤0.5）。这类设备走**派生网格 + `--stage-q-mode const`** 更稳。
4. **`lambda_rel` 是全局口径**：0.02 让"认档窗口"从 ±30 % 收到 ±28 %、判别力回收；若现场发现真实事件被误拒，先查 `min_confidence` 再考虑把它调回 0.05。
5. **`stage_dim_max` 只在 `stage_free=1` 生效**（固定档位保持旧口径，避免升级后历史结果变化）；如果希望固定档位也用单维否决，需要单独评审。

## 八、运行档位账本：`stop` 与 `stage_down` 分不开是方向语义的漏洞（本轮补）

### 8.1 现象（端到端实测，合成但量级真实）

画像＝500 W 设备的满档启停；总线侧三步：3 s +500（1.0 档启动）→ 6 s −300（降到 0.4 档）→ 9 s −200（停机）。
按第二轮交付的规则（"已在运行又 START＝升档 / 已停机又 STOP＝降档"）跑硬件级 `NilmDetector`（`stage_free=1`、`min_stage=0.2`、`max_scale=1`）：

| 时刻 | 方向 | s | 旧 `event_kind` | 实际语义 | 问题 |
|---|---|---|---|---|---|
| 3.0 s | START | 1.00 | `start` | 启动 | ✔ |
| 6.0 s | STOP | 0.60 | `stop` | **降档**（设备还在 0.4 档运行） | 状态机被误翻成 off |
| 9.0 s | STOP | 0.40 | `stage_down` | **停机** | 状态已是 off ⇒ 被当成"降档"，`state` 永远翻不回来 |

根因：`stage_change` 只看 **方向 vs 二元 on/off**，而"降档"与"停机"在方向上都是 STOP、在幅值上都可能小于 1 档
（从 1.0 档降到 0.6 剩 0.4 档，与从 0.4 档直接停机的 s 都是 0.4）——**只有把"当前运行在第几档"记下来才分得开**。

### 8.2 改法（`elec_tool/nilm.py`）

1. 新增 `STAGE_LEVEL_EPS = 0.15`（≈档位拟合误差量级）与 `_stage_kind(m, s, level) -> (kind, level_after)`：
   * START：`level ≤ eps` ⇒ `start`，否则 `stage_up`；`level_after = level + s`；
   * STOP：`level − s ≤ eps` ⇒ `stop`，否则 `stage_down`；`level_after = max(0, level − s)`。
2. `_evaluate_one_profile` 维护 `slot["level"]`（画像档位的倍数，0＝停机），**只在事件真正落盘后推进**；
   `slot["state"]` 也由 `level` 反推（`> eps` ⇒ on）。重扫旧候选（`g_on ≤ last_end + gap`）时不重复推进，
   并按 `slot["kinds"][g_on]` 回填当时的类型——否则候选诊断 CSV 里已报过的候选会被记成新的档位语义（实测过：会全变成 `stop`）。
3. `nilm_profile.detect_profile` 里 `stage_change` 保持原样（它只影响 `state_mismatch` 折半），事件类型不再由它决定；
   档位自由模式下"同向台阶"本来就不算状态机冲突，所以两条规则不会打架。
4. `summary().profile.profiles[]` 增加 `level`（当前运行档位，固定档位模式恒为 0/1 的账本，仅展示）。

改后同一段数据：`start(1.00) → stage_down(0.60) → stop(0.40)`，`device_state=off`、`level=0.00`；候选诊断同表一致。

### 8.3 边界

| 情形 | 行为 | 说明 |
|---|---|---|
| 停机 → 0.2 档启动 | `start`，level 0.2 | 低档启动仍是启动，不是升档 |
| 0.2 档运行 → 停机 | `stop` | s 虽小，但 level 归零 ⇒ 停机 |
| 两次升档 1.0 → 1.6 → 2.2 | `stage_up` + `stage_up`，level 1.6 / 2.2 | s 是**相对画像档位**的台阶（0.6 / 0.6），不是台价比 |
| 缓冲区内第一个候选就是部分 STOP（state unknown） | 记 `stop`，level 归零 | 缺前史时无法区分"停机"与"降档"，取保守语义；下一轮全量重放（state 已知）即可纠正 |
| 漏报一次降档（`min_gap` 压制 / 被拒） | level 会偏高，后续 `stop` 可能落成 `stage_down` | 账本无回正机制；`min_confidence` 别调太松，必要时看候选 CSV 的 `level` 与 `stage_scale` 对账 |
| `stage_free=0` | 行为一字未改（`_event_kind` 只看方向） | 固定档位没有"档位"可记 |

### 8.4 验证

* `tests/test_r180_stage_free.py::test_stage_kind_table`（7 条语义表）+ `::test_detector_labels_stage_down_before_stop`
  （6400 Hz 合成波形 → `build_profile` → `NilmDetector` 逐块喂入 → 断言 `event_kind == [start, stage_down, stop]`、
  `stage_scale == [1.00, 0.60, 0.40]`、时刻 3/6/9 s、`device_state=off`、`level≈0`）；
* `tests/test_r180_stage_free.py` 22 → **25 项全通过**；画像相关 5 个测试文件 **103 passed**；
* 全量 pytest **539 passed / 1 skipped**（158 s；`tests/test_sources.py::test_tcp_binary_frames` 为偶发端口竞态，单独重跑 0.06 s 通过）。
