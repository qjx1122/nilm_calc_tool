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

## 🗒 变更记录
- v0.1（2026-10-10）：创建台账骨架 + 条目模板 + 专题索引；登记待归档专题 T-001（模式 B 执行包：E-0 环境说明 / A~D 四组只读命令 / 预期输出样例 / J-* 判读要点 / 结果回收格式）。⚠️ 本条**尚无结果**，等用户实录回报后追加三件套，不新建文件
