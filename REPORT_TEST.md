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

## 🗒 变更记录
- v0.2（2026-10-10）：追加专题 **T-002**（电气量计算工具实现自验证 + 本地部署与真实数据验收执行包）：沙盒侧 A1~A10 实录三件套、本轮修复的两个真 bug（B1 引擎线程换代竞争导致双重摄入、B2 整周期窗少算一个周期）、用户侧 W/R/P 三组模式 B 执行包与 J-* 判读要点、结果回收格式；专题索引与 T-001 状态保持不变（仍待回报）
- v0.1（2026-10-10）：创建台账骨架 + 条目模板 + 专题索引；登记待归档专题 T-001（模式 B 执行包：E-0 环境说明 / A~D 四组只读命令 / 预期输出样例 / J-* 判读要点 / 结果回收格式）。⚠️ 本条**尚无结果**，等用户实录回报后追加三件套，不新建文件
