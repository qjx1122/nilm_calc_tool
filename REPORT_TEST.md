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
| T-008 | 2026-10-13 | 第 10 轮：离线文件列映射开关 | 用户专题（实现＋验证） | 混合（沙盒 A 已实录 / 用户侧 U10 组待回报） | 🔶待用户回报（沙盒侧已✅实录） | 是（C-21） |
| T-009 | 2026-10-13 | 第 11 轮：离线文件时标 UTC 开关 | 用户专题（实现＋验证） | 混合（沙盒 A 已实录 / 用户侧 U11 组待回报） | 🔶待用户回报（沙盒侧已✅实录） | 是（C-22） |
| T-010 | 2026-10-13 | 第 12 轮：负荷辨识子界面（逐周波事件检测） | 用户专题（实现＋验证） | 混合（沙盒 A 已实录 / 用户侧 U12 组待回报） | 🔶待用户回报（沙盒侧已✅实录） | 是（C-23） |
| T-011 | 2026-11-04 | 智能问答逐会话后端 / 模型选择、本地配置收敛与 46 项受控工具覆盖 | 用户专题（实现＋验证） | A（沙盒自验证） | ✅沙盒代码 / 回归 / 文档已完成；真实浏览器 / 模型现场验收待用户 | 否（产品功能与安全边界，不是算法结论） |
| T-012 | 2026-11-04 | 智能问答工具误路由复核与明确指令确定性路由 | 用户专题（修复＋验证） | A（沙盒自验证） | ✅代码 / 回归已完成；真实 Qwen / 浏览器仍待用户现场验收 | 否（产品工具路由与权限边界，不是算法结论） |
| T-013 | 2026-11-05 | 智能问答“播放 / 启动数据源”误识别分析与修复 | 用户专题（修复＋验证） | A（沙盒自验证） | ✅确定性路由 / 全量回归完成；真实 provider 未测 | 否（产品工具路由，不是算法结论） |
| T-014 | 2026-11-05 | 智能问答扩展表达意图识别方案分析 | 用户专题（方案分析） | A（代码审查） | ✅方案已归档；按用户要求继续实现 46 项意图规则与服务端校验 | 否（产品工具路由，不是算法结论） |
| T-015 | 2026-11-05 | 智能问答 46 项有限意图合同、模型提案前校验与澄清 | 用户专题（实现＋验证） | A（沙盒自验证） | ✅代码 / 回归 / 文档完成；真实 provider 未测 | 否（产品工具路由与安全边界，不是算法结论） |
| T-016 | 2026-11-06 | “播放离线数据源”仍识别成调速的根因复核 | 用户专题（代码审查＋定向回归） | A（沙盒自验证） | ✅当前代码路径确认应选启动；现场服务版本 / 请求实录待核 | 否（产品工具路由与部署诊断，不是算法结论） |
| T-017 | 2026-11-06 | 为“播放离线数据源”误识别增加后台路由诊断日志 | 用户专题（实现＋验证） | A（沙盒自验证） | ✅日志、trace 头、脱敏约束与回归完成；现场日志待用户提供 | 否（产品可观测性 / 部署诊断，不是算法结论） |
| T-018 | 2026-11-06 | 离线数据源启动意图回归语料（正/负/易混淆/复合/状态） | 用户专题（实现＋验证） | A（沙盒自验证） | ✅回归语料建立并通过完整回归；未连接真实 provider | 否（产品工具路由回归，不是算法结论） |
| T-014b | 2026-11-06 | 智能问答基于大模型技术的意图识别技术设计文档（落盘） | 用户专题（设计文档） | A（代码对照） | ✅文档已落盘；现场未验。该条目标题自编为「T-014」，与 2026-11-05 的 T-014 重号，本索引记作 T-014b | 否（产品设计文档，不是算法结论） |
| T-019 | 2026-11-10 | 旧文件覆盖新提交的事故复盘、`app/server.py` 恢复与台账补录 | 验证专题（事故复盘＋恢复） | A（沙盒自验证） | ✅`app/server.py`、`tests/test_server.py` 已恢复，台账已补录；✅`app/assistant.py` 的澄清返回与路由诊断日志已由 T-020 修复（2026-11-10 翻状态） | 是（第 5 节教训，v0.12） |
| T-020 | 2026-11-10 | 模型选错工具时不返回澄清的回归修复（放回 T-015 门控与 T-017 排查日志，新增前端澄清标记） | 用户专题（实现＋验证） | A（沙盒自验证） | ✅代码 / 回归 / 文档完成；🔶真实模型、真实浏览器未测；✅INFO 级路由日志已在 T-023 改为默认可见 | 否（产品工具路由与可观测性，不是算法结论） |
| T-021 | 2026-11-10 | （补记）2026-11-06 智能问答 23 个无台账提交的事后核对 | 验证专题（事后补记） | A（读 diff＋当前代码复测） | ✅已补记；✅核对出的 补-A1～A10 共 10 处问题已于 2026-11-11 修复（T-023） | 否 |
| T-022 | 2026-11-10 | （补记）2026-11-09 前端 13 个无台账提交的事后核对，附 11-10 的 1 个数据提交 | 验证专题（事后补记） | A（读 diff＋jsdom / pytest 复测；无真实浏览器） | ✅已补记；✅核对出的 补-B1～B5 共 5 处问题已于 2026-11-11 修复（T-023）；🔶界面未经浏览器验收 | 否 |
| T-023 | 2026-11-11 | 修 15 处已登记问题（补-A1～A10、补-B1～B5）、路由日志默认可见、「波形预览」子界面改名「波形分析」 | 用户专题（实现＋验证） | A（沙盒自验证；真实接口用例＋jsdom 对临时服务） | ✅代码 / 回归 / 文档完成；🔶真实模型、真实浏览器、Windows、Excel 未测；🔶修复中新发现 补-A12～A14、补-B6、补-B7 共 5 处，未修 | 是（只进方法论教训 2 条，`REPORT.md` v0.13） |
| T-024 | 2026-11-11 | 数据处理页新增「波形预览」子界面（多个可增删的预览模块；离线波形 CSV 与实时监测输出文件） | 用户专题（实现＋验证） | A（沙盒自验证；真实引擎写出的文件＋jsdom 对临时服务） | ✅代码 / 回归 / 文档完成；🔶真实浏览器、Windows、现场文件未测；🔶12 条由实现方决定的做法待用户确认（尤其是离线模块显示有效值曲线、“实时监测输出的波形文件”按实时落盘曲线文件理解） | 否（界面功能与读文件接口，不是算法结论） |
| T-025 | 2026-11-11 | 设备画像匹配能否只用一相电流完成画像提取和匹配（只分析，没有改程序） | 用户专题（代码分析＋合成数据实验） | A（沙盒；合成波形走真实的提取、回放入口） | ✅分析完成，结论与配置方法已给出；🔶没有现场数据，结论只在合成波形上验证；🔶顺带发现的 补-D1～D5 只登记未修；🔶是否在程序里做「只按一相」待用户决定 | 否（合成波形上的分析，不是稳定结论） |
| T-026 | 2026-11-10 | 设备画像自动定位漏停止事件修复（第 212 轮） | 用户专题（修复＋合成验证） | A（沙盒） | ✅代码 / 回归 / 文档完成；🔶原设备 CSV 现场复验待用户 | 否（现场未验证） |
| T-027 | 2026-11-10 | 波形预览右键显示周波瞬时与有效值曲线（第 213 轮） | 用户专题（实现＋验证） | A（沙盒，真实接口＋jsdom） | ✅代码 / 沙盒验证 / 文档完成；🔶真实浏览器及现场数据待验 | 否（界面功能） |
| T-028 | 2026-11-10 | 波形预览周波曲线与原曲线并排（第 214 轮） | 用户专题（实现＋验证） | A（沙盒） | ✅代码 / 沙盒验证 / 文档完成；🔶真实浏览器布局待验 | 否（界面布局） |
| T-029 | 2026-11-10 | 波形预览同排曲线对齐（第 215 轮） | 用户专题（实现＋验证） | A（沙盒） | ✅代码 / 沙盒验证 / 文档完成；🔶真实浏览器布局待验 | 否（界面布局） |
| T-030 | 2026-11-10 | 波形预览无头 Chromium 补验（第 216 轮） | 验证专题 | A（沙盒隔离服务 / 合成数据） | ✅无头浏览器检查通过；🔶目标浏览器及字体视觉待验 | 否（界面验证） |
| T-031 | 2026-11-10 | 波形预览去掉曲线移动说明（第 217 轮） | 用户专题（实现＋验证） | A（沙盒） | ✅代码 / 沙盒验证完成；🔶目标浏览器待验 | 否（界面提示） |
| T-032 | 2026-11-10 | 复查波形预览移动说明并保留悬停提示（第 218 轮） | 用户专题（实现＋验证） | A（沙盒） | ✅代码 / 沙盒验证完成；🔶目标浏览器待验 | 否（界面提示） |
| T-033 | 2026-11-10 | 恢复波形预览移动说明并去掉拖选与缩放说明（第 219 轮） | 用户专题（实现＋验证） | A（沙盒） | ✅代码 / 沙盒验证完成；🔶目标浏览器待验 | 否（界面提示） |
| T-034 | 2026-11-10 | 波形预览曲线去除操作文字标签（第 220 轮） | 用户专题（实现＋验证） | A（沙盒） | ✅代码 / 沙盒验证完成；🔶目标浏览器待验 | 否（界面提示） |
| T-035 | 2026-11-10 | 波形预览去掉缩放后的移动说明（第 221 轮） | 用户专题（实现＋验证） | A（沙盒） | ✅代码 / 沙盒验证完成；🔶目标浏览器待验 | 否（界面提示） |

> **2026-11-10 补录说明**：T-013～T-018 六行原已入库（最后完整版本见提交 `ca5dc28`），在提交 `c5cf96f`（2026-11-06）中被旧文件覆盖而丢失，现按原文补回；T-014～T-017 的正文同样丢失，已原文补录在文末「[2026-11-10] 补录」一节，T-018 当时只有索引行与会话纪要、没有专题正文。T-014b 是为现存「[2026-11-06] T-014 …设计文档（落盘）」条目加的区分编号。经过见 T-019。

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
| A6 | `cli.py serve --host 127.0.0.1 --port 8001 --pt 100 --ct 15 --set-window voltage=2` + `curl /api/state` | `serve 生效配置: PT=100.0 CT=15.0 fs=6400.0 \| voltage 窗=2.0s \| source=simulator`；`running: False` | CLI 覆盖参数确实传到 Web 会话；未设 `ELEC_TOOL_AUTOSTART` 时不自动跑引擎（需界面点启动） |
| A7 | Web 实时链路（`ELEC_TOOL_AUTOSTART=1`，模拟器 `sim_speed=1`） | `速率 6398–6400 点/s`；`emits {'fundamental': 258, 'harmonic': 258, 'voltage': 51, …}`；`voltage 请求1.0s → 实际1.0s 6400点/50周期 f_used=49.999992 泄漏=False` | 实时摄入达额定速率；窗长口径**精确**等于请求值；WebSocket 推送为「分量子集」，前端 `mergeResult()` 按键合并 |
| A8 | 离线安装（内网场景）：`pip download -r requirements.txt -d wheels` → 新 venv `pip install --no-index --find-links wheels -r requirements.txt` | Linux：29 包/28 MB，装完 `selftest 44/44`、`pytest 140 passed`（当时值） | 完全无网可部署；Windows 目标须显式列包（见 A9） |
| A9 | `pip download --platform win_amd64 --python-version 3.11 --implementation cp --abi cp311 --only-binary=:all: numpy fastapi uvicorn websockets pytest httpx -d wheels_win` | 24 包/18 MB，含 `numpy-2.4.6-cp311-cp311-win_amd64.whl` | ✅下载侧通过；⚠️ 用 `-r requirements.txt` 跨平台下载会 `ResolutionImpossible`（`uvicorn[standard]`→uvloop 无 Windows wheel），已在 requirements.txt 用 PEP 508 平台标记分流 + README §2.4(c) 给出显式列包命令 |
| A10 | `ast.parse(feature_version=(3,9)/(3,10))` 扫描 31 个 `.py` | `3.9/3.10 语法不兼容项：无`；且无 `match`/`itertools.pairwise`/`KW_ONLY`/`tomllib` 等 3.10+ 专属用法 | 语法层面兼容 3.9+；**运行时未逐版实测**（🔶） |

**本轮修复的两个真 bug（均由新增测试暴露，已加回归测试锁死）**

| # | 现象（实测） | 根因 | 修法与回归测试 |
| --- | --- | --- | --- |
| B1 | 32000 行的 CSV 跑出 `samples_in=32640`；等满 1.2 s 数据却只算出 6272 点 | `EngineRunner.start()` **持锁** join 旧线程，旧线程正卡在「写结果要拿同一把锁」→ 互等到 2 s 超时后旧线程存活；旧线程每轮重读 `self.engine`，于是继续轮询**被替换的新引擎** → 同批数据双重摄入 | 锁外 join + 每轮全新 `threading.Event` + 线程只持有本轮私有 `engine/stop_event` + 每轮自检「被取代即退场」；回归：`tests/test_server.py::test_offline_window_length_changes_output_count`（断言 `samples_in == 文件行数`） |
| B2 | 用户配 **1 s** 窗，实际只算 **0.98 s / 49 周期**，频谱分辨率变 1.0204 Hz，并持续打印「整周期截断」告警 | `plan_window` 用**绝对**容差 `floor(cyc_req + 1e-9)` 判整周期；估频 `f_used=49.999987`（相对误差 2.6e-7）时 `cyc_req=49.999987` 直接掉到 49 周期 | 改相对容差 `max(1e-9, 1e-5·\|cyc_req\|)`；真·非整数周期（49.85 Hz→49 周期）行为不变；回归：`tests/test_analysis.py::test_plan_window_estimated_freq_near_integer_keeps_all_cycles` |

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
| S1 | `.venv/bin/python -m pytest tests/test_r10_colmap.py -q` | `8 passed` | 默认列序 / 表头乱序按表头 / 列号+列名混填 / 未映射置 0（`max\|u_b\|==0`）/ 无时间戳 3 块时间轴 `diff==1/6400` 连续 / 表头判定 / 校验 4 类报错 / REST 端到端 `rms A=5770 B=0 C=0` ✅ |
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

---

# 第 181 轮（2026-10-31）：把"多档位怎么用派生网格验证测试"写成两份可执行文档（H.28 原理＋两例详解 / H.29 验收用例集）

- 类型：用户专题（文档类，**未改代码**）
- 目标与假设：用户要求"在 `NILM_TUNING_GUIDE.md` 附录中增加一节，举例详细说明如何测试多档位、如何使用派生网格验证测试"。假设：读者是**不懂算法的现场实施 / 运维 / 交付**，只需会复制命令、会对照数字打勾；因此必须给**两个不同接线**（3p4w / 3p3w）的完整例子，且期望值必须是**本机实测**而不是推算。
- 方法 / 数据 / 参数：合成数据两套（`/tmp/r181/gen4.py`、`gen5.py`、本轮新增 `gen6.py` 复跑）；CLI 端到端 `/tmp/r181/cli/`；`stage_window` 逐份实测；`nilm_check --tol-s 1.5` 对账。参数：`lambda_rel=0.02`（v0.99.29 默认）、`min_stage=0.5`、`stage_free=0`、`window_cycles=600`。
- 用户执行命令（含实录路径）：
  - 提画像 `python tools/nilm_profile.py --file dev_3p4w.csv --device pumpA --labels "09:00:02,开;09:00:05,关;09:00:08,开;09:00:11,关" --config cfg1.json --pre 10 --post 50 --out pumpA.json`
  - 派生 `--derive-from pumpA.json --derive-grid 3|5 --stage-out-dir grid|grid5`
  - 回放 `tools/nilm_replay.py --set profile.enabled=1 --set "nilm.profile_path=<;串>"`
  - 对账 `tools/nilm_check.py --events events.csv --truth truth.csv --tol-s 1.5`
  - 实录：`/tmp/r181/cli/{pumpA.json,grid/,grid5/,events.csv,events5.csv,events_c5.csv,truth.csv}`、`/tmp/r181/motorC_g{3,5}_stage*.json`
- 结果 / 结论：

**一、交付结构**

| 节 | 位置 | 内容 |
|---|---|---|
| **H.28** | `NILM_TUNING_GUIDE.md`（原 1398 行之后追加） | H.28.0 三句话总纲 → H.28.1 四层验证（自检 / 网格自检 / 回放判定 / 对账）→ H.28.2 例 1（3p4w，500 W，3 份网格全链路 + 判定矩阵 + 5 份反例）→ H.28.3 例 2（3p3w＋重构，PT4/CT250，I 口径）→ H.28.4 份数定法 → H.28.5 五种失败对照 → H.28.6 禁做清单 → H.28.7 一页纸 |
| **H.29** | 紧随 H.28 之后追加（本轮新增，+372 行） | 执行层：14 条编号用例（A1–A7 三相四线 / B1–B5 三相三线 / N1–N4 负向）、每条给"命令 → 期望值 → 判据 → 不过怎么办"；外加测试记录表模板、判定三档（通过 / 有条件通过 / 不通过）、复测矩阵（改了什么只重跑哪几步）、一页纸 10 条命令 |

**二、本轮补测与勘误（3 条，均已改进文档）**

1. **例 1 的 5 份网格不止"多 2 条误报"**：复读 `events5.csv` ⇒ `algorithm=profile` 共 **10 条 confirmed**（应为 6）：除 `09:00:21/24` 被 `pumpA@394%` 认（**0.6824 ×2**）外，35 % 档还被 `pumpA@25%`（**0.4568**）与 `pumpA@50%`（**0.4075**）**同时**确认 ⇒ 违反"每个台阶恰一份"。H.28.2 第 5 步已补"重复"行并改写结论。
2. **例 2 的 5 份置信度复跑确认**（`gen6.py`，同 5 份网格）：重构 on ⇒ **0.993 / 0.996 / 0.576**；off ⇒ **0.893 / 0.966 / 0.604**；两态均 6/6。**3 份时只有 4 条 confirmed**（0.993 ×2、0.996 ×2），35 % 档整行 `—` ⇒ "3 份不够"的证据由"算覆盖"升级为"回放实测"。
3. **界面 ④ 组不做自动网格**：`index.html` / `app.js` 的真实字段是「档位倍数（相对本次画像）/ 输出目录 / ΔQ 缩放 / 谐波指数 ih_exp」，要"按实测窗口自动铺开"只能用 CLI `--derive-grid`。H.28.2 第 2 步已按此改写，并在 H.29 的 A2/B2 用例里只用 CLI 命令。

**三、逐份实测窗口（`stage_window`，本轮复核）**

| 数据 | 份 | k | 可接受区间 | `min_d` | 幅值 |
|---|---|---|---|---|---|
| 例 1 基准 | 1 | 1.000 | 0.670~1.330× | 250.0026 W | 500.0054 W |
| 例 1 网格 3 | 3 | 0.5038 / 1 / 1.985 | 0.63~1.37 / 0.67~1.33 / 0.67~1.33 | 125.941 / 250.003 / 496.274 W | 251.88 / 500.01 / 992.55 W |
| 例 1 网格 5 | 5 | 0.254 / 0.504 / 1 / 1.99 / 3.94 | 0.56~1.44 / 0.63~1.37 / 0.67~1.33 / 0.67~1.33 / 0.68~1.32 | 63.444 / 125.941 / 250.003 / 496.274 / 985.141 W | 126.89 / 251.88 / 500.01 / 992.55 / 1970.28 W |
| 例 2 基准 | 1 | 1.000 | 0.700~1.300× | 35.0715 A | 70.1433 A |
| 例 2 网格 3 | 3 | 0.534 / 1 / 1.857 | 0.69~1.31 / 0.70~1.30 / 0.70~1.30 | 18.7405 / 35.0715 / 65.1328 A | 37.4811 / 70.1433 / 130.2661 A |
| 例 2 网格 5 | 5 | 0.281 / 0.534 / 1 / 1.857 / 3.449 | 0.69~1.31（前两份）/ 0.70~1.30（后三份） | 9.871 / 18.7405 / 35.0715 / 65.1328 / 120.961 A | 19.742 / 37.4811 / 70.1433 / 130.2661 / 241.9227 A |

**四、对账实录（例 1，`--tol-s 1.5`）**

```
3 份：profile   6  6  0  0   0  100%  ✅ 可上线   → 7 种算法全部命中且 0 误报
5 份：profile   6  6  0  2   2  100%  ⚠ 有 2 条带内误报
```

**五、H.29 的 14 条用例覆盖**

| 组 | 用例 | 关键期望（实测） |
|---|---|---|
| A（3p4w） | A1 画像自检 / A2 3 份网格自检 / A3 单份对照 / A4 3 份判定矩阵 / A5 对账 / A6 5 份负向 / A7 精确派生 | 0.670~1.330×、`min_d` 250.003 W；6 条 0.9916/0.9562/0.4075；对账 6/0/0；5 份 10 条 + 2 带内误报；精确派生 0.992/0.993/0.995 |
| B（3p3w） | B1 接线与量纲自检 / B2 3 份不足 / B3 5 份通过 / B4 重构对照 / B5 对账 | μΔIa 40.497 A（手算 40.1 A）；3 份只 4 条、35 % 整行 —；5 份 0.993/0.996/0.576；off 0.893/0.966/0.604；对账 6/0/0 |
| N（负向） | N1 混档 / N2 网格+`stage_free` / N3 提 `min_confidence` / N4 倍数太密 | 0.687 档/σ 59~64 %/线性假负荷 conf 0.43；6→26 条；6→4 条（67 %）；同一台阶 2~3 份同时 ✔ |

- 是否进入 `REPORT.md`（稳定结论）：**否**——属方法与验收口径，已沉淀在 `NILM_TUNING_GUIDE.md` 附录 H.28/H.29（用户指定文件），不重复上卷。
- 遗留问题：
  1. A3（单份对照）的 55 % 档拒识值 0.10 / 0.05 沿用本轮之前的实测，**本轮未重跑**（`events_single.csv` 未落盘留档）；
  2. 两例均为**合成数据**（三相严格对称、按 k 缩放）；真实设备的低档 THD 上升、无功不随档位比例等情形仍只在 H.28.5 里给出方向，未做实录；
  3. 用户侧（Windows + 现场数据）尚未按 H.29 的 14 条走一遍，属 🔶 待回报；
  4. 在此期间用户另报"设备画像提取 HTTP 500"，排查中（见 `STATUS.md` 下一步）。

## 第 181 轮 · 补（2026-10-31）：设备画像提取 ↔ 负荷辨识「设备画像匹配」参数对照手册（H.30）

- 类型：用户专题（文档类，**未改代码**）
- 目标与假设：用户问"设备画像提取中各算法参数如何设定、对应负荷辨识事件界面中该算法又如何设置"。假设读者要**逐项可查**：每个参数给出「位置 / 默认 / 代码行为 / 怎么定 / 填错的后果」，并说明两侧的耦合关系。
- 方法 / 数据 / 参数：逐行读代码取证——`app/static/index.html:1118-1245`（提取侧 ①②③④ 与基准配置）、`index.html:812-833` + `app.js:3227-3240`（检测侧公共项与「设备画像匹配」14 项）、`elec_tool/config.py:770-802`（默认值）、`elec_tool/nilm_profile.py:475-560`（候选生成 `_two_window_candidates`）、`:381-431`（`match_event` / `mahalanobis_diag`）、`:554-760`（`detect_profile` 判据）、`elec_tool/nilm.py:837-857`（缓存窗口需求）、`:911-1040`（`_evaluate_one_profile`）。
- 用户执行命令（含实录路径）：本节为文档，无用户命令；取证命令：`python -c "from elec_tool.config import NILM_ALGO_DEFAULTS; print(NILM_ALGO_DEFAULTS['profile'])"`、`NilmDetector._profile_window_need()`（`/tmp/r181/need.py`）。
- 结果 / 结论：

**一、交付**：`NILM_TUNING_GUIDE.md` 新增 **H.30**（+242 行，全 2451 行）——
| 小节 | 内容 |
|---|---|
| H.30.0 | 参数分布总表 + 三个"配了也不生效"的坑（`rel_tol_pct`/`min_delta_pct`/`auto_params` 只作用于 6 种标量算法；只填路径不勾 enabled；检测量不一致直接跳过画像） |
| H.30.1 | 提取侧基准配置 8 项（fs、f_nom、PT/CT、时标 UTC、接线、3P3W 重构、极性、检测量）+ 手算核对 |
| H.30.2 | ①②③④ 四组：设备 ID/文件名、标签/容差 2 s/合并 10 s、**pre 10 / post 50**（同时决定设备侧特征、总线侧候选、总线侧特征、检出延迟）、派生档位 4 项；含 `need = pre×max_scale + dur + 2×post×max_scale + 10` 与四类典型组合 |
| H.30.3 | 检测侧公共项 6 个（quantity / window_cycles / min_gap_cycles / save / auto_params / rel_tol_pct / min_delta_pct） |
| H.30.4 | 「设备画像匹配」16 项分 6 组（总开关与画像、候选门槛、相似度判据、方向与相序、窗口几何、档位策略），每项给默认值 / 代码行为 / 怎么定 |
| H.30.5 | 三套预设（保守 / 标准 / 宽松） |
| H.30.6 | 配参六步（每步只看一个数） |
| H.30.7 | 12 条"现象 → 根因 → 改哪一项" |
| H.30.8 | 一页纸 |

**二、本次取证得到的两条关键事实**

1. **缓存窗口需求**：默认 `pre/post=10/50` + `max_scale=8` ⇒ `_profile_window_need()` = **891 周波（≈17.8 s）**，而 `nilm.window_cycles` 默认 300 ⇒ 引擎自动扩窗并在状态行提示。实测：`max_scale=1/2/4/8` ⇒ need **121 / 231 / 451 / 891**。
2. **`auto_params` 不影响画像匹配**：`elec_tool/nilm.py:753-800` 的自适应参数推导只发生在 `for algo in NILM_SCALAR_ALGOS` 循环内；画像匹配的判据完全由画像 σ + `k_sigma`/`min_stage`/`d2_max`/`min_confidence` 决定。`rel_tol_pct` / `min_delta_pct` 同理。

**三、判据换算（写进文档，便于现场自查）**

| 参数 | 值 | 等价判据 |
|---|---|---|
| `min_confidence=0.3` | `exp(−D²/2d) ≥ 0.3` | `D²/维 ≤ 2.41` |
| `d2_max=9` | `D²/维 ≤ 9` | 平均 \|z\| ≤ 3（对应 conf ≥ 0.011，通常不是卡点） |
| `stage_dim_max=9` | 任一维贡献 ≤ 9 | 单维 \|z\| ≤ 3（仅 `stage_free=1` 生效） |
| `min_stage=0.5` | 候选门槛 = 0.5×画像幅值 | 0.35× 档位**连候选都不生成** |
| `k_sigma=4` | 候选门槛 = max(min_d, 4×前窗 σ) | 噪声大时自动抬高 |

- 是否进入 `REPORT.md`（稳定结论）：**否**（参数口径属操作手册，已沉淀在 `NILM_TUNING_GUIDE.md` H.30）。
- 遗留问题：① 文中"填错的后果"多数来自代码行为与 H.28/H.29 已实测的两例，**逐项参数单独做 A/B 实测仍未做**（例如只把 `k_sigma` 从 4 调到 6 的命中率变化）；② 三套预设的"保守/宽松"边界未用现场数据回归；③ 用户侧尚未按 H.30 实际配一遍。


---

## 第 182 轮（2026-11-01）：改画像前后窗后回放误识别——现场产物逐条取证

**用户原话**：「修改提取设备画像时的前后窗参数后，重新提取设备画像并基于新提取的设备画像分别使用带设备停机和带设备开机的总线波形数据通过总线侧和分路侧进行播放并辨识，结果误识别很多，详细输出见 tmp 目录下相关文件，请详细分析原因。」

**性质**：只读取证 + 复算，**未改代码**；文档交付 `NILM_TUNING_GUIDE.md` 附录 **H.31**（+212 行，2451 → 2663）。

### 1. 现场（`tmp/`，2026-10-31 23:43 那一次回放）

| 项 | 内容 |
|---|---|
| run_info | `created_local 2026-10-31 23:43:51`，两侧同时起播（bus 0.416 s / branch 0.531 s） |
| 波形 | 总线侧 `化工行业-海湾化工-bus-停止.csv`、分路侧 `…-bus-启动.csv`（**注意：与 10-30 那次用的 `…-停止-1.csv` / `…-启动-1.csv` 不是同一份导出**） |
| 画像 | 两侧都复制自 `output\nilm\profile_device_20261031_222210.json`（**改后画像，pre/post=10/200**） |
| 检测配置 | `quantity=i`、`channels=[A]`、`window_cycles=3000`、`min_gap_cycles=1000`、`auto_params=true`、6 标量算法全开、profile `enabled=true` 其余默认（`d2_max 9 / min_confidence 0.3 / state_check 1 / max_scale 8`） |
| 数据量 | 事件 `nilm_events_20261031.csv` 382 条（14:33:19~15:09:45）+ `nilm_events_20261101.csv` 69 条（跨零点续写，同一 run_id） |
| 候选 | `nilm_profile_candidates_20261031.csv` 213 行 + `_20261101.csv` 54 行 |

### 2. 画像取证（决定性）

| 项 | 改前 `…_20261030_233706` | 改后 `…_20261031_222210` |
|---|---|---|
| `pre / post` | 3000 / 3000 | **10 / 200** |
| startup `n` | 1 | **2** |
| startup μΔIa / σΔIa | +35.95 / 5.39（=15 % 下限） | **+8.102 / 10.582（σ/\|μ\|=1.31）** |
| startup μΔP | −23 933 W | −6 936 W |
| startup dur | 1271 周波（25.4 s） | 63.5 周波（39~88） |
| startup peak_ratio | 1.59 | 3.48 |
| shutdown n / μΔIa / dur | 1 / −36.26 / 305 | 1 / **−18.21 / 1 周波** |
| `need`（max_scale 8） | **73 281 周波 = 1466 s**（> 数据 1093/976 s ⇒ 不裁剪） | **3 378 周波 = 67.6 s**（正常） |

**改后画像的两个「启动」样本**（`startup.events`）：

| 时刻 | source | ΔIa | ΔIb | ΔIc | ΔP | peak_ratio | dur |
|---|---|---|---|---|---|---|---|
| 15:00:40.624 | `auto:steady_state` | **+0.62 A** | +0.90 | +0.92 | −405 W | 4.05 | 39 |
| 15:01:21.024 | `auto:two_window` | **+15.58 A** | +11.04 | +20.76 | −13 468 W | 2.90 | 88 |

⇒ 相差 25 倍的两个事件被平均成 μ=8.10 A，样本 σ=10.58 A（**σ>μ**）。`0.62 A` 低于总线 1 s 噪声峰峰值（60 A）两个量级，判为噪声级；`label_mode=auto`（无人工标签）是它被收进来的前提。
画像 `notes` 已自带三条警告：「建议每方向 ≥3 次」「3/3 个事件的 ΔP 与 ΔI 异号（CT 极性接反）」「启动画像只有 2 次事件…幅值相近的他负荷也更容易被误认」。

### 3. 回放取证

**3.1 事件分布**

| 算法 | 20261031 | 20261101 | 合计 |
|---|---|---|---|
| cusum | 65 | 12 | 77 |
| threshold | 57 | 9 | 66 |
| glr | 54 | 10 | 64 |
| steady_state | 52 | 10 | 62 |
| median_diff | 52 | 8 | 60 |
| two_window | 47 | 9 | 56 |
| **profile** | **55** | **11** | **66** |
| 合计 | 382 | 69 | **451** |

**3.2 画像事件**

| 指标 | 20261031 | 20261101 |
|---|---|---|
| 条数 | 55 | 11 |
| 方向 | **START 54 / STOP 1** | **START 11 / STOP 0** |
| status | confirmed **2** / low_confidence 53 | low_confidence 11 |
| conf | 0.303 / **0.376** / 0.768（min/中位/max） | 0.308 / 0.360 / 0.419 |
| D² | 0.87 / 4.60 / 16.60 | 2.83 / 5.27 / 7.76 |
| \|ΔI\| | 3.37 / 10.52 / 26.50 A | 6.71 / 10.34 / 16.88 A |

**3.3 候选与 flags**

| 指标 | 20261031（213 行） | 20261101（54 行） |
|---|---|---|
| `state_mismatch` | **208（97.7 %）** | **54（100 %）** |
| `window_crowded` | 66 | 13 |
| `trajectory_deviates` | 48 | 11 |
| `d2_exceeds` | 33 | 15 |
| `sign_flip` | 20 | 5 |
| `ambiguous_direction` | 6 | 0 |
| confirmed / low_confidence / rejected | 2 / 53 / 158 | 0 / 11 / 43 |

**3.4 事件率与背景台阶**

| 指标 | 总线侧 | 分路侧 |
|---|---|---|
| 画像事件（该 run） | 35 条 | 31 条 |
| 时间跨度 | 14:33:19~14:53:10 | 14:53:19~15:09:45 |
| 间隔中位 / 最小 | **25 s / 20 s** | **29 s / 21 s** |
| 背景台阶（≥2 A，±5 s 中位，3 s 去重） | **156 个**，\|Δ\| 中位 **4.2 A** | **159 个**，中位 **4.4 A** |
| 画像事件落在背景台阶 ±5 s 内 | （两侧合计） | **52 / 66（79 %）** |

> `min_gap_cycles=1000`＝20 s，正是最小间隔 ⇒ **抑制器已饱和**，系统在满速报警。

**3.5 文件头假事件**：两条首报（14:33:19.165 / 14:53:19.165）正好落在两段数据的第一个采样附近；`_window()` 在 `onset < pre_n` 时前窗被压成一个点（`p4[0, onset-1]`），任何起始电平差都成为台阶。分路侧那条以 **conf 0.768** 成为全表最高分，并把状态机翻成 `on`，此后 63 条 START 全部带 `state_mismatch`。

### 4. 与 10-30 那次（`pre/post=3000/3000`）的对照

| 项 | 3000/3000（10-30） | 10/200（10-31） |
|---|---|---|
| 画像 μΔIa / σ | 35.95 / 5.39（下限） | 8.10 / 10.58（样本差） |
| `need` / 缓冲 | 73 281 / 不裁剪 | 3 378 / 67.6 s |
| 画像事件 | **2** | **66** |
| 标量算法事件 | 323 | 385 |
| 候选 | 5 行（4 条 `window_crowded`） | 267 行（262 条 `state_mismatch`） |

⇒ **换前后窗只改变了画像算法自己的行为**：从「几乎不动」变成「每 25 s 一次」；6 个标量算法的条数在同一量级（323 → 385），它们的问题与前后窗无关。

### 5. 结论与改动清单

见 `NILM_TUNING_GUIDE.md` H.31.0（三句话）/ H.31.6（归因汇总）/ H.31.7（A 参数 4 条 + B 代码 5 条 + C 提取侧 3 条）/ H.31.9（一页纸）。

**不改码即可见效的三条**：`min_confidence` 0.3→**0.42**（66 条 → 7 条，两条 confirmed 全留；**不要用 0.45**，会把 conf 0.436 的唯一真 STOP 杀掉）、`min_gap_cycles` 1000→180 000、重提画像（剔 0.62 A 噪声、每方向 ≥3 样本、先修 CT 极性）。

### 6. 未验证 / 遗留

1. **设备真值缺失**：`dev1.csv` 不在 `tmp/`，无法确证 15:00:40 的 0.62 A 不是设备动作（按量级判噪声）。
2. **两批波形不可直接比**：本次是 `…-bus-停止.csv`/`…-bus-启动.csv`（背景台阶 156/159），10-30 是 `…-停止-1.csv`/`…-启动-1.csv`（28/30）⇒ 只能比「同一画像在不同参数下的行为」，不能比两次回放的误报率。
3. **原始 10 kHz 波形缺失**：逐周波 σ、`min_delta` 均为重建推断。
4. **参数改动未实跑**：`min_confidence=0.42`（66→7）、`min_gap=180 000` 的收益是按事件表逐条扫描推算，下一轮需真跑复测。
5. **500 错误**：与本次无关，仍未定位（见 STATUS）。

---

# 第 183 轮（2026-11-03）：`NILM_TUNING_GUIDE.md` 全量复核——对照代码 v0.99.29 的 16 条问题

**用户原话**：「结合当前最新版本代码，重新检查 NILM_TUNING_GUIDE.md 文档每章节各部分内容，分析是否有问题。」

**性质**：只读复核，**未改代码、未改指南正文**（修正清单见 §7，等确认后一次性落笔）。基线 `1588626`（r182 交付，指南 2663 行）、代码 `v0.99.29`。

## 0. 结论摘要（先看 6 行）

1. **1 条硬伤会让人照着做却找不到控件**：v0.99.23 已取消「启用 PT/CT」开关，但指南仍有 **15 处**写"勾选启用 / 两侧都勾"（P183-01，含开头 §0、附录 B、附录 H.30 与整个附录 I）。
2. **1 条硬伤会让参数调错方向**：`profile.lambda_rel` 默认值写成 **0.1**，代码是 **0.02**；实测同一画像 λ=0.1 得窗口 0.62~1.38×、λ=0.02 得 0.67~1.33×（P183-03）。
3. **1 条整段逻辑已成死代码**：工具首行永远打印「口径 一次侧(PT/CT)」（`scaled = bool(cfg.transform.enabled)`，而 `enabled` 恒 True），指南却有 3 处按"会打印二次侧"写排障（P183-02）。
4. **画像算法（第 7 种）的描述落后 6 个版本**：`dur_cycles` 定义、终点规则、`min_d` 口径、σ 绝对下限、CSV 列数、8 个新参数全部缺（P183-05~08、P183-04）。
5. **界面已改两步法，指南仍写一步勾选**：调参页现在是「第 ① 步 设备侧估幅值 → 第 ② 步 总线侧量噪声 → 第 ③ 步 套用」，勾选框文案也换了（P183-11）。
6. **§I.3 的"等价命令"在新装机器上直接崩**：`--config configs\runtime.json` 在未保存过总线侧配置时抛裸 traceback（退出码 1），且界面实际生成的命令里**不含** `--wiring/--reconstruct-3w`（P183-10）。

## 1. 复核方法与覆盖

| 手段 | 做法 | 覆盖 |
|---|---|---|
| 逐节通读 | 指南 2663 行按 §0–§8、附录 A–I 分 22 段读完，逐段记"可被代码证伪的断言" | 全文 |
| 参数默认值机器比对 | 脚本抽 `NILM_ALGO_DEFAULTS` + `NilmConfig` 默认值，与文档"默认 X"逐条人工复核（区间写法不自动抓） | 7 种算法 × 全部参数 + `nilm.*` 9 项 |
| CLI 参数存在性 | 扫文档全部 `--flag`（49 个）与 5 个工具源码的 `add_argument` 比对 | 49/49 存在（仅 `--help` 未在文档出现，非缺陷） |
| API 路径 | 扫文档 `/api/*` 与 `app/server.py` 路由比对 | 全部存在；`/api/branch/nilm/tune/apply` 由 `_SideRouter`（766–800）改写，非缺陷 |
| 界面控件 | 按 `<input id=...>`／`<button id=...>` 而不是文字命中判定（`grep "启用 PT/CT"` 只命中隐藏注释，会误判） | 调参区 988–1130、画像区 1118–1250、负荷辨识区 |
| 数值实跑 | `stage_window`（λ 对比）、`gen_nilm_sample.py --soft-start`（H.4‴ 数字）、`nilm_tune.py`（口径行 / JSON `scaled` / 缺配置崩溃） | 4 组 |

## 2. 逐章核对表

| 章节（行号） | 结论 | 编号 |
|---|---|---|
| §0 先搞懂 3 句话（12–26） | ⚠ 单位提醒仍在讲"启用 PT/CT 才按一次侧" | 01、02 |
| §1 开工前准备（27–51） | ✅ | — |
| §2 打开 PowerShell（52–64） | ✅ | — |
| §3 量噪声（65–121） | ✅ 12 个 CLI 参数全对；`--config configs\default.json` 可直接跑 | — |
| §4 真值表（122–141） | ✅ | — |
| §5 回放+对账（142–246，含 5-B / 5-C） | ✅ 算法数、`--set` 写法、对账列均对 | — |
| §6 第五步微调（247–278） | ⚠ "二次侧 W 当一次侧填"这一整类失效 | 02（L261） |
| §7 写进生产（279–352） | ⚠ §7-2′ 未提 `auto_params` 开启时的 `warning`（`server.py:1852–1855`） | 14 |
| 附录 A（353–381） | ❌ 标题"6 种"；profile 行 λ 错、缺 8 个参数 | 04、15、03 |
| 附录 B（382–399） | ⚠ 排障行"检查 `transform.enabled` 与变比" | 01（L393） |
| 附录 C（400–451） | ✅ 全部命令可执行（样例日期只是文件名） | — |
| 附录 F（452–490） | ✅ I 口径参数、`--min-load-a`、单相限制均对 | — |
| 附录 D（491–500） | ✅ | — |
| 附录 E（501–538） | ✅ 公式与 `suggest` 实算一致（`min_d=max(Δ/2,6σ)`、`k=max(min_d/4,0.5σ)`、`h=max(2(min_d−k),5σ)`） | — |
| 附录 G（539–761） | ✅ G.0–G.8（参数表逐项对 `NILM_ALGO_DEFAULTS`）；❌ G.9 | 05–08、16 |
| 附录 H（762–2454） | ✅ H.0–H.12、H.14、H.16–H.23、H.26–H.29；⚠ H.4‴(L904)、H.13(L1040–1050)、H.15(L1046)、H.24(L1869)、H.30(L2225/L2243)、H.31.4(L2570) | 01、09、11、12、13 |
| 附录 I（1106–1273） | ❌ P183-01 六处 + 两步法流程 + 等价命令 | 01、10、11 |

> 说明：✅ 表示"逐字核对过且未发现与当前代码矛盾"；不代表现场实测。

## 3. 问题清单

### P183-01【高】「启用 PT/CT」在 15 处仍是操作前提，界面已无此控件

- **现状**：以下位置要求读者"勾选启用 PT/CT / 两侧都勾"：
  `L23`（§0 单位提醒）、`L393`（附录 B）、`L554`（§5 口径）、`L793`（H.2 输出说明）、`L1027`（H.12 排障）、`L1101`（I.0 口径要求）、`L1118`（I.0 事实 4）、`L1141`/`L1147`（I.2 表与正文）、`L1224`（I.5）、`L1250`（I.7）、`L1271`（I.8 一页纸）、`L1869`（H.24 检查表）、`L2225`/`L2243`（H.30.1）。
- **代码依据**：`elec_tool/config.py:169–191`——`TransformConfig.enabled` 注释写明"v0.99.23：恒为 True（保留字段只为兼容旧配置）"，`__post_init__` 把 `enabled=False` 折算成 `PT=CT=1`；`validate()` 也再折一次。界面侧 `app/static/index.html:1007` 该 checkbox 是 `<input id="nt-base-ptct" ... checked hidden>`，可见文案已改成「PT/CT 变比在下一行填写（默认 1＝不换算）」；负荷辨识页与画像页均无对应勾选框。
- **为何是硬伤**：读者按 I.2 会去找一个不存在的勾选框；按 I.8 一页纸会以为"没勾"是口径不一致的原因，从而把真问题（变比填错 / 一侧填 1 一侧填 100）漏掉。
- **建议改法**：统一改成"PT/CT **始终参与换算**，两侧填本侧真实变比；不需要换算就填 1（等效旧版'不启用'）"。`L2243` 的"界面默认不启用 = PT=CT=1"改为"出厂 PT=CT=1（等效不换算）"。
- **自相矛盾证据**：指南 H.22（`L1311`）标题就是「v0.99.23：PT/CT 不再有『启用』开关」，同一文件里两种说法并存。

### P183-02【高】「口径 二次侧」这条输出分支已经不可达，3 处排障逻辑连带失效

- **现状**：`L793` 写"首行输出会写明「口径 一次侧(PT/CT)」**或「二次侧」**"；`L1027` 排障表写"首行「口径 二次侧」但现场参数是一次侧 ⇒ `--config` 里 `transform.enabled=false`"；`L23`/`L261`/`L554` 同样以"一次/二次"二分描述。
- **代码依据**：`elec_tool/nilm_tuning.py:624` `"scaled": bool(cfg.transform.enabled)`；`TransformConfig.enabled` 恒 True（P183-01）⇒ `out["scaled"]` 恒 `True` ⇒ `tools/nilm_tune.py:121` 的三元表达式永远走「一次侧(PT/CT)」。
- **实测**：用出厂 `configs/default.json`（PT=CT=1）跑 `nilm_tune.py`，首行仍为 `口径 一次侧(PT/CT)`，JSON `"scaled": true`。
- **建议改法**：① 指南改为"首行恒显示「口径 一次侧(PT/CT)」，后面可加变比数值（如 `PT=1, CT=1` 时与二次侧数值相同）"；`L1027` 整行替换为"变比填错（一侧 1 一侧 100）⇒ ΔI 差 100 倍"。② 代码建议把首行改成 `口径 一次侧(PT=…, CT=…)`，一次讲清——否则"一次侧"三个字在 PT=CT=1 时等于没说。

### P183-03【高】`profile.lambda_rel` 默认值写错（0.1 vs 0.02）

- **位置**：`L365`（附录 A profile 行"`lambda_rel`（协方差收缩，默认 0.1，一般不动）"）、`L725`（G.9(b)③ 参数列"`lambda_rel`（默认 0.1）"）。
- **代码依据**：`elec_tool/config.py` `NILM_ALGO_DEFAULTS["profile"]["lambda_rel"] = 0.02`（v0.99.29 改；`elec_tool/nilm_profile.py:263/381` 函数默认值同为 0.02）。
- **实测影响**（同一份 μΔIa 3.24 A / σ 0.486 A、μΔP 500 W 的画像，`stage_window` 默认参数）：

| λ | 可接受区间 | 区间比 `k_hi/k_lo` | `min_d` |
|---|---|---|---|
| 0.1（文档写的） | 0.62~1.38× | 2.226 | 250.0 W |
| **0.02（代码）** | **0.67~1.33×** | **1.985** | 250.0 W |

- **连带**：H.28 例 1 的 1.985 与 G.9 附近 `STAGE_GRID_RATIO = 1.857`（代码常量，注释写"λ=0.1 时的窗口比"）并存——指南读者会以为两者矛盾，其实一个是实测值、一个是 λ=0.1 时代的兜底常量。
- **建议改法**：两处改 0.02，并加一句"λ 越小窗口越窄（每维 σ 收缩得越少⇒越严）"；`STAGE_GRID_RATIO` 那句注明"仅作兜底，实际一律用 `stage_grid_ratio()` 实测"。

### P183-04【中】附录 A 的 profile 行只列 8 个参数，实有 14 个

- **现状**：`L365` 列了 `enabled / profile_path / d2_max / min_confidence / k_sigma / margin / lambda_rel / state_check`。
- **代码依据**：`NILM_ALGO_DEFAULTS["profile"]` 15 个键（含 `enabled`），即 **14 个数值参数**：另缺 `phase_map`(1)、`max_scale`(8)、`min_scale`(0.25)、`min_stage`(0.5)、`stage_free`(0)、`stage_min_scale`(0.2)、`stage_max_scale`(3.0)、`stage_dim_max`(9)；界面 `app/static/app.js` `NILM_ALGOS.profile.params` 也是这 14 个。
- **建议改法**：附录 A 只留一行"其余 8 个见 H.30.4（权威表）＋一句话：前 4 个管候选（`max_scale/min_scale/min_stage`）、后 4 个管档位（`stage_*`）＋`phase_map` 管相序"。不重复抄默认值，避免第三次漂移。

### P183-05【中】G.9(a)④：`dur_cycles` 的 σ 绝对下限写"2 周波"，代码是 5

- **位置**：`L716`「绝对下限：0.02 A / 5 W / 5 var / 0.1 / **2 周波** / 2 A 谐波电流」。
- **代码依据**：`elec_tool/nilm_profile.py` `_ABS_FLOOR = {..., "dur_cycles": 5.0, ...}`，注释写明"v0.92.5：dur_cycles 下限 2→5 周波（在线终点估计对噪声敏感，单样本画像 σ=2 时 10 周波偏差就贡献 25）"。
- **同段遗漏**：`template_spread` 有下限 **0.25**（`fit_group`：`"template_spread": max(tspread, 0.25)`，v0.99.19），文档只写"记录 RMS 散布"，没说下限——而 H.30/H.31 都用它当轨迹折扣的基准。
- **建议改法**：改 5 周波；补"`template_spread` 不低于 0.25（样本少时防止轨迹判别一票否决）"。

### P183-06【中】G.9(a)③：`dur_cycles` 定义还是 v0.92.2 的"进入 ±20 % 带"

- **位置**：`L713`「`dur_cycles` ＝ 从起点到"进入事件后电平 ±20 % 带"的周波数」。
- **代码依据**：`transition_end`（`nilm_profile.py:435–473`，v0.99.23）——先做长度 `w=max(1,min(25,post_n//20))` 的滑动**中值平滑**，终点＝平滑轨迹**首次进入** `±0.2·|Δ|` 带并**连续保持** `hold=max(3,min(250,post_n//10))` 周波的那个周波；从未保持则退回"最后一次越带的下一周波"；封顶 `onset+post_n−1`。`build_profile`（`nilm_profile.py:907–912`）与在线候选（`:506`）、标签定位（`:694`）、自动定位（`:797`）**四处共用**。
- **为何要改**：这是 H.21（`L1303`，同文件）已正确描述过的规则，G.9 没跟着改——同一份文档里两处对"终点"的定义不同。

### P183-07【中】G.9(b)①：候选门槛写死"一半"、终点同样过时

- **位置**：`L723`「`min_d` ＝ 画像里启动 / 停止 |ΔP| 最小者的一半……终点 ＝ onset 后首个进入事件后电平 ±20 % 带的周波（封顶 `post_cycles`）」。
- **代码依据**：`detect_profile`（`nilm_profile.py:589`）`min_d = float(prm.get("min_stage", 0.5)) * min(amp)`——**`min_stage` 可配**，v0.99.29 档位自由匹配时建议 0.2~0.3，否则低于 0.5× 的档位连候选都不生成（H.30.4 已按新口径写，G.9 没改）。终点同上（`transition_end`，P183-06）。
- **建议改法**：`min_d = min_stage × min(启动/停止幅值)`，默认 0.5＝旧行为；终点一句改为"`transition_end`（平滑＋首次进带并保持），见 H.21"。

### P183-08【中】G.9(c)：事件 CSV 附加列写 7 个，实为 9 个

- **位置**：`L731`「事件 CSV `nilm_events_*.csv` 末尾多 6 列……v0.99.26 起再加一列 `delta_ih_a`」。
- **代码依据**：`elec_tool/nilm.py:52` 列尾为 `device_id, confidence, d2, profile_direction, status, quality_flags, delta_ih_a, stage_scale, event_kind`（注释"v0.90 画像匹配附加列；v0.99.26：delta_ih_a；v0.99.29：档位倍数 / 事件类型"）；实测 `tmp/nilm/nilm_events_20261031.csv` 共 **32 列**，末三列正是 `delta_ih_a, stage_scale, event_kind`。
- **建议改法**：补"v0.99.29 起再加 `stage_scale`（该事件是画像档位的几倍）与 `event_kind`（start/stop/stage_up/stage_down，非画像算法为空）"。

### P183-09【中】H.13 的「界面项 ↔ 命令行参数」表缺整个「公共配置」组

- **现状**：`L1040–1051` 只映射了 `--file / --t-start / --t-end / --duration / --config / --quantity / --channel / --min-load-* / --apply`。
- **界面现状**：调参页顶部新增 `nt-common`「公共配置 · 读波形数据与口径」（`index.html:991–1035`）：采样率 fs、额定频率 f_nom、PT 变比、CT 变比、接线方式、3P3W 重构、电流极性反转、分相极性、离线文件列映射、检测量、检测对象。
- **代码依据**：其中接线/极性有 CLI 覆盖参数（`tools/nilm_tune.py:62–68`：`--wiring/--reconstruct-3w/--invert-current/--invert-phases`），而 **fs / f_nom / PT / CT / 列映射没有 CLI 覆盖参数**（argparse 里不存在 `--pt/--ct/--fs/--f-nom/--colmap`），只能靠 `--config`（或界面写出的 `output/nilm/nilm_tune_base.json`）复现。
- **影响**：读者想"界面里改了 PT/CT，命令行怎么复现"会找不到答案；也会有人以为 `--wiring` 不需要（其实用 `configs/default.json` 当基准时必须给）。
- **建议改法**：表里补 5 行——`接线方式→--wiring`、`3P3W 重构→--reconstruct-3w`、`电流极性反转→--invert-current`、`分相极性→--invert-phases`、`fs/f_nom/PT/CT/列映射→无 CLI 参数，写进基准配置（独立基准会落 output/nilm/nilm_tune_base.json，用 --config 指向它即复现）`。

### P183-10【中】§I.3「等价命令」在新装机器上崩、且与界面实际生成的命令不同

- **现状**：`L1176`（例 1）/`L1178`（例 2）各一条 `--config configs\runtime.json`，并说"界面结果区会自动给一条一模一样的"。
- **实测 1（崩）**：仓库里 `configs/` 只有 `default.json` / `branch.json`（`runtime.json` 是界面保存后才生成）。此时
  `python tools/nilm_tune.py --file … --config configs/runtime.json --min-load-w 22000`
  ⇒ `ConfigError: 配置文件不存在：configs/runtime.json` 的**裸 traceback**，**退出码 1**（不是文档 §H.6 承诺的"⚠ ＋ 码 2"）。原因：`tools/nilm_tune.py:85` 的 `load_or_default(cfg_path, strict=bool(a.config))` 写在 `try` 之外。
- **实测 2（命令不同）**：界面等价命令由 `build_cli_command(...)` 生成（`app/server.py:2813–2816`），参数里**没有** `wiring/reconstruct_3w/invert_*`；`--config` 在「独立基准配置」时指向 `output/nilm/nilm_tune_base.json`（`:2799–2807`），在「沿用某侧」时指向该侧持久化配置。所以界面给的命令与 `L1178` 那条字面不同（大概率更短、没有 `--wiring`）。
- **建议改法**：① 文档改为 `--config configs\default.json --wiring 3p3w --reconstruct-3w`（新装即可跑），并注明"若已保存总线侧配置，可换成 `configs\runtime.json` 并省掉 `--wiring`"；② 删掉/改写"一模一样"的说法，改为"界面给的命令以本页基准配置为 `--config`，接线在基准配置里"。③ 代码建议把 `load_or_default` 挪进 `try`，返回码 2 ＋ 一句"配置文件不存在，请先在界面保存该侧配置或改用 configs/default.json"。

### P183-11【中】H.15 / §I.3 的"勾选估计最小关心负荷"流程已被两步法取代

- **现状**：`L1046`（H.13 表最后几行之一）「从文件投切台阶估计最小关心负荷（勾选）」；`L1087`（H.15）「波形文件选设备侧 → 勾『从文件投切台阶估计最小关心负荷』→ 量噪声 → 结果区点『填入输入框』」；`L1167`（I.3 第 5 条）同样。
- **界面现状**：`index.html` 里该区已按 **第 ① 步（可选）· 设备侧文件 → 估计最小关心负荷**（按钮 `#btn-nt-est-dev`「① 估计最小关心负荷并填入第 ② 步」，`:1042–1050`）／**第 ② 步 · 总线侧稳态背景文件 → 量噪声**（`:1056`）／**第 ③ 步** 分组。同页勾选框的真实文案是「**直接从本步所选文件估计最小关心负荷**（仅当本步文件就是单设备含启停录波时勾选；**总线侧背景文件请勿勾选，改用第 ① 步**）」（`:1079`）。
- **影响**：读者按 `L1167` 在**第 ② 步**对总线侧文件勾选，恰好是界面明确劝阻的用法（`app.js:4196` 的两步法注释也说明第 ① 步专管幅值）。
- **建议改法**：三步走——① 第 ① 步选设备侧文件、点「① 估计最小关心负荷并填入第 ② 步」；② 第 ② 步换总线侧背景文件、基准配置「沿用总线侧运行配置」、点「量噪声并给出参数」；③ 第 ③ 步「套用目标」选总线侧 → 「套用到运行配置」。`L1046` 的界面项文案同步换成新文案。

### P183-12【低】H.4‴ 的软启样例数字与当前样例生成器不一致

- **位置**：`L904`「`min_steady_cycles` 抬到 **33**（斜坡上最长伪稳态平台 **21** 周波）」，同句 `427 / 650 / 740`。
- **实测**：`python tools/gen_nilm_sample.py --soft-start` + `nilm_tune.py --min-load-w 1000` ⇒ **34 / 22**，`427 / 650 / 740` 一致（`+1` 与 `+1` 的差来自伪平台周波数取整/放宽路径）。
- **建议改法**：改成"≈33~34 / ≈21~22"或直接照抄最新一次实跑值。

### P183-13【低】H.31.4 引用了不存在的函数名，机制描述也过强（上轮引入）

- **位置**：H.31.4「**文件头假事件的成因**：`_window()`（`nilm_profile.py:80-124`）在 `onset < pre_n` 时 `a0=max(0, onset-pre_n)=0`，前窗被压成**一个点**」。
- **代码依据**：`nilm_profile.py` 里**没有** `_window()`；对应实现是 `event_features()`（`:67–124`，`a0,a1 = max(0,onset-pre_n), onset` 在 `:82`）。当 `onset>0` 时前窗是 `[0, onset)`，长度＝`onset`（**短于** `pre_n`），只有 `onset==0` 时切片为空、走 `_median(..., p4[0, max(0,onset-1)])` 的单点回退。所以"一个点"只在首采样成立，通常应是"前窗被截短、前后窗不对称，Δ 被系统性放大"。
- **建议改法**：函数名改 `event_features()`，行号 `67–124`；机制改成"前窗被截短到 `[0,onset)`（`onset=0` 时退化为单点 `p4[0,0]`），前后窗长度不对称 ⇒ 文件头首个候选的 Δ 与 D² 都不可信"。

### P183-14【低】§7-2′ 未提 `auto_params` 开启时接口返回的 `warning`

- **位置**：`L311–327`。
- **代码依据**：`app/server.py:1852–1855`——目标侧 `nilm.auto_params=True` 时返回
  `"warning": "目标侧已启用「自适应算法参数」：…已写入配置但检测时不参与…请取消勾选…"`，返回体还有 `auto_params` 字段。
- **建议改法**：在"返回 `changes / saved_to / config`"那句里补 `warning`（"自适应参数开着时套用的数值参数不参与检测"），并链到 H.30.0 坑②。

### P183-15【低】附录 A 标题"6 种算法"，表里 7 行

- **位置**：`L353` 标题 + `L365` profile 行。
- **建议改法**：标题改「7 种算法（6 种标量 + 设备画像匹配）一句话」，或保留标题但加注"第 7 种见末行，参数权威表在 H.30.4"。

### P183-16【低】G.9 导语仍写"量 7 个特征"

- **位置**：`L704`「找台阶 → 量 **7 个**特征 → 和画像比」。
- **代码依据**：`FEATURES` 8 项（v0.99.26 加 `d_ih`）；同节 `L708` 已写"v0.99.26 起 8 维"。
- **建议改法**：导语改"量 8 个特征（旧画像 7 维）"。

## 4. 实跑取证

**4.1 λ 对窗口的影响**（`stage_window`，画像 μΔIa=3.240/σ=0.486、μΔP=500/σ=75）

| λ | `k_lo~k_hi` | 比值 | `min_d` | `k_gate` |
|---|---|---|---|---|
| 0.1 | 0.62~1.38× | 2.226 | 250.0 W | 0.5 |
| 0.02 | 0.67~1.33× | **1.985** | 250.0 W | 0.5 |

⇒ 指南 `L365/L725` 的 0.1 是旧默认；H.28 例 1 的 `1.985` 恰好等于 λ=0.02 的区间比，可作为"λ 已改"的旁证。

**4.2 口径行**：`configs/default.json`（PT=CT=1）⇒ 首行 `口径 一次侧(PT/CT)`、JSON `"scaled": true`（P183-02）。

**4.3 缺 `runtime.json`**：`--config configs/runtime.json` ⇒ `ConfigError` 裸栈、退出码 **1**（P183-10）。

**4.4 软启样例**：`427 周波 / 650 / 740 / min_steady 34 / 伪平台 22`（P183-12）。

## 5. 已核对无误的部分（可作为"没白读"的清单）

- CLI 49 个 `--flag` 全部存在于对应工具；`--min-load-auto / --custom-time* / --wiring / --reconstruct-3w / --invert-* / --save-config` 的语义与文档一致。
- `nilm_tune.py --json` 的字段（`file/channel/quantity/scaled/t_range/min_load_*/measure/suggest/algorithms/transient`）与 `L921–933` 的 JSON 节选一致；`suggest` 里确实**没有** profile 行（`NILM_SCALAR_ALGOS` 只含 6 种）。
- 附录 E 的四条公式与 `nilm_tuning.py:403–480` 逐项吻合（`min_d / tol / k / h / tol10 / rel_tol_pct 夹 0.05–5 / min_delta_pct>50→0`）。
- G.0–G.8 的参数名与默认值全部与 `NILM_ALGO_DEFAULTS` 相同（`min_delta_w 50 / settle_tol_w 20 / max_rise_cycles 40 / settle_cycles 5 / pre-post 10 / k_sigma 3 / drift 10 / threshold_w 200 / glr window 15 / thr 25 / noise 10 / tol_w 30 / min_steady 10 / max_transient 100 / median_cycles 5`）。
- 附录 A 全局表 5 项默认值对（`window_cycles 300 / min_gap_cycles 10 / rel_tol_pct 1.0 / min_delta_pct 0 / MAX_PROFILES 8`）。
- H.28（多档位派生网格）与 H.29（验收用例）里的数值可被 `stage_window / stage_grid_ratio` 复现：例 1 窗口 0.67~1.33×、`min_d 250.003 W`、间距 1.985；例 1 界面 ④ 组字段（倍数/输出目录/ΔQ 缩放/ih_exp）与 `server.py:2628–2712` 的请求体一致。
- H.30.4 的 14 个参数与 `app.js NILM_ALGOS.profile.params` 完全一致（含 `stage_dim_max` 的单维否决语义）。
- API：`POST /api/nilm/tune/apply`（`hot=true / persist=false`、非法值 400、`changes/saved_to/config`）与 §7-2′ 一致；`/api/branch/*` 由 `_SideRouter` 改写，文档里的分路侧写法正确。
- §5-B 指纹对账、`nilm_check.py` 的 7 行算法表（含 profile 行与"关闭"提示）、`--tol-s` 语义均与 `tools/nilm_check.py:113–125` 一致。

## 6. 代码侧顺带发现（不影响本轮结论，建议登记待修）

| # | 位置 | 问题 |
|---|---|---|
| C1 | `elec_tool/nilm_profile.py:475–476` | `_two_window_candidates` docstring 写「`\|median(后) − median(前)\|`」，实现是**均值**（cumsum 求 mean）。指南 G.9(a) 写 mean 是对的，**代码注释错**。 |
| C2 | `elec_tool/config.py:711` | `limits_secondary` 的注释仍写"若 `transform.enabled` 则检测时自动乘 PT/CT 折算到一次侧"——v0.99.23 起恒换算，注释应删条件。 |
| C3 | `tools/nilm_tune.py:17` | 模块 docstring「启用 PT/CT 时为一次侧 W / A」同上。 |
| C4 | `tools/nilm_tune.py:85` | `load_or_default(strict=True)` 在 `try` 之外 ⇒ 配置文件不存在时裸 traceback / 退出码 1（P183-10）。 |
| C5 | `app/static/index.html:1007` | 残留 `hidden` 的 `nt-base-ptct` 复选框（`checked hidden`），只作为占位保留；建议删掉或改成纯文本，免得后人 grep 到又以为有开关。 |

## 7. 建议修正清单（按严重度，**未执行**）

| 序 | 动作 | 影响行数（估） |
|---|---|---|
| 1 | P183-01 + P183-02：15 处「启用 PT/CT」与「二次侧」统一改为"恒换算、填 1 等效不换算" | 15 行改写 + §H.22 加一句交叉引用 |
| 2 | P183-03：`L365`、`L725` 的 `lambda_rel` 0.1 → 0.02，加一句窗口比说明 | 2 行 |
| 3 | P183-05~08 + P183-16：G.9 四段（σ 下限 5 周波 / `transition_end` / `min_stage` / CSV 9 列 / 7→8 维） | 1 段重写 + 3 行改数 |
| 4 | P183-11 + P183-09 + P183-10：H.13/H.15/I.3 改成两步法、补公共配置映射、改等价命令（含代码 catch） | 3 段重写 + 1 处代码 |
| 5 | P183-04 + P183-15：附录 A 标题与 profile 行收敛到 H.30.4 | 2 行 |
| 6 | P183-12/13/14：样例数字、H.31.4 函数名、§7-2′ warning | 3 行 |

> 建议顺序：1 → 2 → 3 先做（都是"照做会错"），4 需要同时动代码（catch ConfigError），5/6 收尾。

## 8. 未覆盖 / 遗留

1. **未逐字复核**：附录 D（491–500）只核了"用哪一侧"的结论与 `data/` 目录约定，没核采样率/时标细节；§1 的安装步骤（PowerShell 版本、`requirements.txt` 内容）未在本沙盒 Windows 复现。
2. **界面类结论基于静态源码**：本轮没有起服务点页面，控件存在性靠 `index.html/app.js` 的 `id` 判定；真实渲染（例如 `nt-common` 是否折叠）未截图验证。
3. **P183-12 的 33/21 vs 34/22**：只跑了一次 `--soft-start` 样例；若样例生成器有随机性，需再跑两次确认。
4. **未测**：H.29 的 14 条验收用例本轮未重跑（r181 已跑过，本轮只核参数与判据文字）。

---

# 第 184 轮（2026-11-03）：设备画像提取增加「设备单相 / 分相」支持——分析、实现与实测

**用户原话**：「暂时不需要，先分析代码，考虑在基于设备画像提取算法中增加对设备单相画像提取的支持。」

**性质**：**分析 + 已实现**（6 个产品文件 + 1 个测试文件；分析完成后未再请示即推进实现，见 §184.4.4 回退方式）。基线 `33e6701`（r183 交付）、代码 `v0.99.29` → 本轮 `v0.99.30`。

## 0. 三句话结论

1. **现状确实硬性假定三相**：事件定位只在「三相总有功/三相合成电流」上做（`detect_profile` 取 `p4[0]`/`i4[0]`），特征向量固定 8 维（`d_ia/d_ib/d_ic` + `d_p/d_q/peak_ratio/dur_cycles/d_ih`），`PHASE_MAPS` 只解决「接错相」、解决不了「那两相根本是别人的负荷」。
2. **单相设备拿旧画像直接匹配必炸**：未接相的 μ≈0，σ 被绝对下限 0.02 A 托底 ⇒ 总线上任何一个他负荷在那两相投切，D² 就爆。实测（A 相 3 A 真启动 + B/C 相 2 A/−1.5 A 他负荷落在窗内）**D²/维 14.10、conf 0.001，真事件被拒**；把 `d_ib/d_ic` 跳过 ⇒ 3.39，仍被 ΔP 的窗污染拒。
3. **跳维是必要条件、不是充分条件**：跳维只解决"不该比的维度不该参与"，解决不了"该比的维度被邻窗他负荷污染"（实测 690→920 W 后 `window_crowded`）；另外 `d_ih` 是**三相平均**（单相设备只贡献 1/3，见 §184.5.2）。所以本轮交付的是「单相设备**能被正确比较**」，不是「单相场景下什么都认得出」——现有限制写在 §184.5，不要对外宣称"单相支持已闭环"。

## 184.1 现状：哪几处硬性假定三相

| # | 位置（v0.99.29） | 现状 | 对单相设备的影响 |
|---|---|---|---|
| 1 | `detect_profile()` 的候选：`p4[0]` / `i4[0]` | 只用**三相总**（ΣP / 合成电流）做双窗、稳态、CUSUM 等候选 | 单相设备的台阶级台阶被另外两相的总量稀释；他负荷在三相任一处投切都会造成候选（这部分是**总线侧**的既有行为，与画像无关） |
| 2 | `FEATURES`（8 维，3 个 ΔI 维） | 画像必须给出 `d_ia/d_ib/d_ic` 的 μ/σ | 未接相的 μ≈0、σ 只有 0.02 A 绝对下限（`_ABS_FLOOR`）⇒ 该维成为"最敏感维" |
| 3 | `mahalanobis_diag()` 的对角 D² | 每维贡献相加，无"该维缺失"语义 | 未接相的任何抖动直接进 D² |
| 4 | `skip` 机制（v0.93） | 只在**3p3w 无 B 相 CT** 时 `skip=("d_ib",)` | 是唯一的"某维不参与"通道，但没有"设备本来就没接这一相"的来源 |
| 5 | `PHASE_MAPS`(6 种) / `remap_phases` | 解决「CT 接错相、A/B/C 互换」 | 不能表达"这台设备只接 A 相" |
| 6 | 画像 schema `nilm_profile/1` | 只有 `pt_ct/wiring/quantity/unit/features…`，无相别字段 | 匹配侧无从知道该跳过哪些维 |
| 7 | `CycleFeatures` 的 `q` / `ih`（total 行） | `q[0]`＝三相**求和**；`ih[0]`＝三相**平均** | 求和口径对单相设备**无损**（ΔQ_total 就是设备自身）；平均口径会把单相设备的谐波**压到 1/3**（见 §184.5.2） |

## 184.2 单相设备到底缺什么

1. **缺"这台设备接在哪几相"这一事实**——它决定了哪些 ΔI 维**根本不该参与**比较。
2. **缺一个能自动判出来的手段**：现场经常只给三列（`时间,A相电压,A相电流`）或六列（3p4w 记录仪，另两相没接），人工填相别容易错。
3. **缺一条可解释的提示链**：跳过之后要让人看到"跳了哪两维、为什么"，否则运维会以为软件"算错了"。

> 结论：**不需要改特征维、不需要改 schema 主版本**。最小改动＝在画像里记一个 `phases` 字段，匹配时把未接相的 ΔI 维并进已有的 `skip` 通道。

## 184.3 实测证据（改动前的现状基线）

### 3.1 设备侧三列单相录波能否提取（能）

`/tmp/r184/dev1ph.csv`：`时间,A相电压,A相电流`，A 相 5 A@0.5 s、0.15 s 后 8 A、再回 5 A。旧版 `build_profile` 可直接跑通（缺列按 0 播放，`ColumnMap._resolve_partial`），得到 `d_ia μ=3.0 σ=0.45`、`d_p μ=690 W`、`d_ib/d_ic μ=0 σ=0.02`——**问题不在提取，在匹配**。

### 3.2 三组总线侧对照（同一份画像、同一段数据，只改相别）

| 数据 | 目标事件 | 他负荷 | 现状（画像记 ABC） | 跳过未接相后 |
|---|---|---|---|---|
| `bus3ph1` | A 相 +3 A/+690 W @500 周波 | B 相 +2 A @700（**远离**窗口） | D²/维 **0.20**、conf **0.906**、confirmed；700 周波处被判 16.97/0.000 rejected（max=d_ib） | 同（本来就该中） |
| `bus3ph2` | 同上 @500 | B 相 +2 A @505、C 相 −1.5 A @480（**落在前后窗内**） | D²/维 **14.10**、conf **0.001**、rejected（d_ib 贡献 92.4、d_p 19.8） | D²/维 **3.39**、conf **0.183**、仍 rejected |
| `bus3ph3` | 同上 @2.0 s | B 相 +1 A @2.3 s（落在**后窗**） | D²/维 **3.564**、conf **0.1683**、rejected | D²/维 **0.823**、conf **0.6626**、**low_confidence + `window_crowded`**（ΔP 690→920） |

第三行是本节最重要的一行：**跳维把 D² 从 3.56 压到 0.82，但事件仍标 `low_confidence`**，因为 ΔP 被邻窗他负荷污染了（690→920 W）。⇒ 跳维必要、不充分。

### 3.3 另一组：同一画像、改 `phases=ABC` vs `A`（差分对照）

`bus3ph2` 的 3.4 s 处 B 相他负荷（+1 A）事件：

| 画像相别 | `d_ib` 实测 | D²/维 |
|---|---|---|
| `A`（跳过 d_ib/d_ic） | **0**（不参与） | **6.957** |
| `ABC`（旧行为） | **94.28** | **17.004** |

### 3.4 AB 相（线间 380 V）设备能否提取（能，但 ΔI 无符号）

设备侧 3p4w 记录仪接 A-B 单相：`ia=+3·sin`、`ib=−3·sin`（同一电流在两相 CT 上反号），提取结果 `phases="AB"`、`d_ia μ=3.0`、`d_ib μ=3.0`、`d_p μ=1195 W`、`d_q≈0`。

> **发现（写入限制）**：`d_ia/d_ib/d_ic` 来自**逐周波有效值**，与符号无关 ⇒ `+3 A` 与 `−3 A` 记成同一个数，"A-B 单相"与"两台各接一相的单相设备"在画像上不可分。要用无功/相角区分，得改 `CycleFeatures` 的口径，本轮不做。

## 184.4 已实现的改动

### 4.1 画像 schema（向后兼容）

```json
{"schema": "nilm_profile/1", "phases": "A", "phase_source": "auto",
 "phase_stats": {"A": {"mu_abs_di": 3.0, "sigma": 0.45, "active": true}, "...": {}}}
```

* `phases` 取值：`A/B/C/AB/AC/BC/ABC`（按 ABC 排序、大小写不敏感、`a,c` 与 `AC` 等价）；**字段缺省 ⇒ `ABC`**，旧画像行为完全不变。
* `phase_source`：`auto`（按事件幅值自动判定）/ `manual`（人工 `--phases`）。
* `phase_stats`：三相 ΔI 的 μ/σ 与是否判为"接了"，供界面对账与排障。
* `validate_profile` 只在字段**存在**时校验（非法字符抛 `ProfileError`）；显式给空串视为错误。

### 4.2 代码清单

| 文件 | 改动 |
|---|---|
| `elec_tool/nilm_profile.py` | 新增 `PHASE_DIMS / PHASE_ROWS / PHASES_ALL / PROFILE_PHASE_NAMES`、`normalize_phases()`、`profile_phases()`、`profile_skip_dims()`、`detect_phases()`；`build_profile(..., phases="auto")` 写 `phases/phase_source/phase_stats` 并加 notes；`validate_profile` 归一 `phases`；`profile_summary` 暴露 4 个新键；`detect_profile` 把 `skip` 与 `profile_skip_dims(doc)` 合并；`amp` 兜底（三相 ΔI 全被跳过时仍用画像自己的合成幅值定候选门槛，避免 `min_d=0` 变成"任何台阶都成候选"） |
| `elec_tool/nilm.py` | `_load_profiles()` 每槽追加两条提示：① 跳维清单（含 3p3w 无 B 相 CT 的 `d_ib`）；② 画像电流证据**只在 B 相**而本侧 3p3w 无 B 相 CT 时给"不要指望 ΔI、容易漏报/误认"的警告 |
| `tools/nilm_profile.py` | `--phases {auto,ABC,A,B,C,AB,AC,BC}`；`build_cli_command(..., phases=)` **读 `doc["phases"]`**（不能用 argparse 默认值，否则自动判相时命令串漏写相别）；结果头打印「相别 X」 |
| `app/server.py` | `POST /api/process/nilm_profile` 收 `phases`（非法 ⇒ 400），透传、写进 `command`、响应增 `phases/phase_skip/phase_stats` |
| `app/static/index.html` | 「设备画像提取」① 组新增下拉 `#np-phases`（8 选项，默认 `auto`） |
| `app/static/app.js` | `npPayload` 带 `phases`；`npRender` 增「设备相别」卡片（非 ABC 标红并列出跳过的维） |
| `tests/test_r184_single_phase_profile.py` | 32 项（见 §184.6） |

### 4.3 判定规则（`detect_phases`）

对**启动/停止两个方向的所有事件**取各相 `|ΔI|` 的均值 μ_p 与标准差 σ_p：

* 某相 `active` ⇔ `μ_p ≥ max(2 % × 最大相 μ, 3 σ_p)`——2 % 防"大电流设备的小相"被误判，3σ 防噪声相被误判；
* 三相全为 0（无电流证据，例如纯有功维差异）⇒ 退回 `ABC`（不改变旧行为）；
* 只一相显著 ⇒ 单相；多相显著 ⇒ 按实际相别组合（如 `AB`）。

## 184.5 使用与限制（现场必读）

1. **单相画像的 `d_p` 仍是"三相总有功"**：单相设备投运时，`d_p` 就等于该设备的有功（另两相没变），所以**单相场景下 `d_p` 反而更干净**；但若前后窗里有他负荷，`d_p` 一样会被污染（§3.2 第三行 690→920 W）。
2. **`d_ih` 只取到真实值的 1/3**：`CycleFeatures.ih[0]` 是三相平均（`nilm.py` 里 `ih = np.vstack([np.mean(ih_ph, axis=0), ih_ph])`）。实测（本机合成：A 相基波 5 A + 5 次谐波 3 A、B/C 为 0）**`ih_total=1.000 A`、`ih_A=3.000 A`**，正好 1/3。
   * 两侧同口径 ⇒ **可比性不受影响**（设备侧画像与总线侧事件都是 1/3）；
   * 但 σ 的 `d_ih` 绝对下限是 **2 A**，折回单相真实值相当于 **6 A** ⇒ 谐波电流小于 ~6 A 的单相设备，这一维基本不提供判别力（`σ` 由下限接管，不是由设备重复性决定）。
3. **`d_p` / `d_q` 是三相求和，对单相设备没有摊薄**：`p[0]=Σp_ph`、`q[0]=Σq_ph`，设备只在 A 相动作时 `ΔP_total` 就等于设备自身的有功（实测：A 相设备 690 W + B 相他负荷 230 W 同时投切 ⇒ `ΔP=920 W`，**是相加不是平均**）。所以单相设备的功率判据不需要另算"本相 P"；真正吃掉它的是**窗内他负荷**（同上）。
4. **ΔI 无符号**：见 §3.4，`+3 A` 与 `−3 A` 不可分。
5. **3p3w 无 B 相 CT**：若画像含 B 相，`nilm.py` 会把 `d_ib` 并进 skip 并给提示；但**"只在 B 相有电流证据"的画像在本侧等于没有 ΔI 证据**（剩 ΔP/ΔQ/峰值比/持续周波/ΔIh），能认但更容易漏报/误认——提示里已写明。
6. **人工指定相别要复核**：`--phases B` 但数据里 A 相最显著时，画像 notes 会写「⚠ 指定的相别与数据里最显著的相别不一致」，先查接线 / 列映射。
7. **跳维 ≠ 免疫邻窗他负荷**：见 §3.2/§3.3，仍要靠 `pre/post`、`window_crowded` 与 `min_confidence` 一起判。

## 184.6 验证记录

| 检查 | 方法 | 结果 |
|---|---|---|
| `normalize_phases` | 10 组输入（`auto/None/''/ABC/abc/A/a,c/AB/['B']/C/A`）+ 4 组非法 | 全对；非法抛 `ProfileError` |
| `profile_skip_dims` | 无字段 / `ABC` / `A` / `AB` | `()` / `()` / `{d_ib,d_ic}` / `{d_ic}` |
| `detect_phases` | 单相（A 相 3 A、B/C 噪声）、三相不平衡 3/2/1.2、全零 | `A` / `ABC` / `ABC` |
| 三列单相 CSV 提取 | `tools/nilm_profile.py --file dev1ph.csv` | `phases=A`、`phase_source=auto`、`d_ia 3.00/0.45`、`d_p 690`、notes 含单相提示 |
| 人工相别与数据不符 | `phases="B"`（数据是 A） | `phase_source=manual` + ⚠ 不一致提示 |
| 显式 `ABC` | 三列 CSV + `--phases ABC` | 不跳维、不加单相提示（等价旧行为） |
| 端到端匹配（差分对照） | 合成 A 相 3 A + B 相 1 A 同时投切 | `A` 画像 D² 8.47（1.41/维）conf 0.494 confirmed；`ABC` 画像 D² 31.14（3.89/维）conf 0.143 rejected（d_ib 贡献 22.7） |
| 负向（跳维 ≠ 全收） | 只在 B 相投切的同幅值设备 vs `A` 画像 | 拒（最大贡献维 `d_ia`） |
| 档位派生继承 | `derive_stage_profile(doc, 0.5)` | `phases` 继承、skip 一致 |
| 引擎提示 | 单相画像 / `B` 相画像 × 3p3w（重构开/关）/ `AB` 相画像 × 3p3w | 提示文本与预期一致；重构后不再警告 |
| 端点 | `POST /api/process/nilm_profile`（`phases=auto` / `D` / `ABC`） | 200（`phases=A`、`phase_skip=[d_ib,d_ic]`、命令含 `--phases A`）/ **400**「phases 只能含 A/B/C（或 auto / ABC）」/ 200（`ABC`、skip 空） |
| 页面 | `GET /` 含 `#np-phases`；`node --check` | 1 处、语法 OK |
| 回归 | `pytest -q tests` | **572 passed / 1 skipped**（164 s；改动前 539 passed + 1 skipped，本轮 +32 项 r184 + 1 项 Web 契约） |

### 6.1 本轮自己踩的坑（已修，留档）

| 坑 | 现象 | 根因 / 修法 |
|---|---|---|
| 参数加错端点 | 全量测试 **9 个无关用例挂**（`test_r12_nilm` 的 `nilm_tune`、`test_r61`、`test_r86`），端点返回 400「NameError: name 'phases' is not defined」 | 用脚本按字符串替换时，把 `phases=phases` 插到了 `nilm_tune` 端点的 `dict(...)` 里（两个 `dict` 的收尾行文本相同）⇒ 改成锚定 `doc = await asyncio.to_thread(build_profile, …)` 这一行 |
| 文档引用悬空 | 画像 notes 写「见 NILM_TUNING_GUIDE H.32」，但该节不存在 | 上轮已定"指南正文先别落笔" ⇒ 改为引用本报告 §184.5；H.32 留作待批准项 |
| 测试数据写错位置 | 合成 B 相他负荷放在 520 周波，`min_stage=0.5×690 W` 把 230 W 的台阶直接滤掉，负向用例变成"没有候选" | 改成与目标同时刻投切（同窗），才能验证"跳维不等于全收" |
| 空 `phases` 兼容 | `validate_profile` 原先对 `phases=""` 静默归一为 `ABC` | 改为：字段**缺省**才等价旧画像；**显式**给空串 ⇒ 报错（避免拼装 JSON 时误留 `""` 被悄悄当成三相） |

## 184.7 未做 / 待批准

1. **手册 H.32 未写**：用户上一轮明确「先别落笔」指南修正清单，本轮同样**未动 `NILM_TUNING_GUIDE.md`**。单相设备的现场用法目前只有本报告 §184.5。
2. **`d_p`/`d_q` 单相重算 —— 复核后判定"不需要"**：`p4[0]/q4[0]` 是三相**求和**，单相设备的增量已经等于它自身（§184.5.3 实测 920＝690+230）；另算一套"本相 P"只会让同一次候选出现两套 ΔP、事件表与 `min_delta` 门槛分裂，收益为零。**撤销上一版报告里的这条待办**。
3. **ΔI 保留符号**：要改 `CycleFeatures` 输出（RMS→带符号基波相量），影响面覆盖 6 种标量算法与全部历史数据口径，**不做**。
4. **前端未做 jsdom 端到端**：只做了 `node --check` + 起服务 `curl` 页面/端点；`tools/ui_*.check.cjs` 家族未加单相用例。
5. **真实单相数据未验证**：全部数据为本机合成（6400 Hz、50 Hz、PT=CT=1）；现场三相不平衡、CT 相位误差、单相设备启动冲击未覆盖。

## 184.8 一页纸

* **改了什么**：画像里多一个 `phases`；匹配时自动跳过未接相的 ΔI 维；CLI/界面/接口三处可选 `--phases`（默认 `auto`，按事件幅值判定）。
* **为什么要改**：单相设备画像的未接相 σ 只有 0.02 A，任何他负荷在那两相动一下就把 D² 顶爆（实测 14.10 vs 0.20）。
* **改到哪一步**：跳维后同一份画像从"rejected 0.001"变成"confirmed 0.494"（差分对照）；但 ΔP 被邻窗污染时仍会 `low_confidence`（0.823/0.6626，`window_crowded`）。
* **旧画像怎么办**：无 `phases` 字段 ⇒ 按 `ABC`，行为与 v0.99.29 逐位一致（32 项测试覆盖）。
* **别宣称什么**：别宣称"单相设备什么都认得出"——跳维只去掉不该比的维度，邻窗他负荷照样污染 ΔP；`d_ih` 是三相平均（小谐波设备这一维无效）、ΔI 是有效值无符号。
* **回退**：`git checkout -- elec_tool/nilm_profile.py elec_tool/nilm.py tools/nilm_profile.py app/server.py app/static/index.html app/static/app.js` + 删除 `tests/test_r184_single_phase_profile.py`。

## 184.9 复核补记（同一轮追加，2026-11-03）

**起因**：收尾时逐条复核 §184.5 的口径表述，发现上一版把「三相求和」与「三相平均」混为一谈，两处结论下重了。改动与依据：

| 原表述 | 更正 | 依据 |
|---|---|---|
| `d_p/d_q` 三相合成 ⇒ 单相设备的功率/无功「被其它两相摊薄」 | **不成立**：`p[0]=Σp_ph`、`q[0]=Σq_ph` 是求和，单相设备的 ΔP/ΔQ **就等于设备自身** | `nilm.py:155` `p = np.vstack([p_ph.sum(axis=0), p_ph])`；实测 A 相 690 W + B 相 230 W 同时投切 ⇒ ΔP=**920 W**（相加） |
| `d_ih` 被摊薄 ⇒ 「判别力下降」 | 摊薄是对的（**恰好 1/3**），但**可比性不受影响**（两侧同口径）；真正的问题是 **σ 的 2 A 绝对下限**折回单相真实值相当于 **6 A** | 实测：A 相 5 A 基波 + 3 A 五次谐波、B/C=0 ⇒ `ih_total=1.000 A`、`ih_A=3.000 A`；`_ABS_FLOOR["d_ih"]=2.0` |
| §184.7 待办②「`d_p/d_q` 单相重算」 | **撤销**（收益为零、会让同一次候选出现两套 ΔP） | 同上第一条 |

**保留不变的结论**：
1. 单相画像必须跳过未接相的 ΔI 维（否则 D² 必爆）——实测 14.10/0.001 → 3.39/0.183 → 0.823/0.6626 `window_crowded`；
2. 跳维**必要不充分**，邻窗他负荷对 ΔP 的污染仍然会压低置信度（690→920 W）；
3. `d_ia/d_ib/d_ic` 来自逐周波**有效值**，`+3 A` 与 `−3 A` 记为同一个数（A-B 线间设备与「两台单相各接一相」在画像上不可分）；
4. I 口径的**候选搜索**跑在三相合成电流 `√(ΣI_ph²)` 上，单相设备对它的贡献会被其它两相的基流压缩（实测算例：`I_A=5 A / I_B=I_C=50 A` 时 A 相 +3 A 只让合成量 **70.887→71.162 A，Δ=0.275 A**；同样的 +3 A 在 `I_B=I_C=5 A` 时是 **8.660→10.677 A，Δ=2.017 A**）——这一条**不影响**匹配（匹配用分相 ΔI），只影响"能不能生成候选"，因此 I 口径下挂单相画像时 `min_stage`/`k_sigma` 要比 P 口径更宽松。

## 184.10 补做：候选台阶序列也按相别取（同一轮追加）

**为什么补**：§184.5 只把未接相的 ΔI 从**匹配**里剔掉，候选台阶仍然在三相合成序列上找。复核时发现这对 I 口径是**硬伤**（不是精度问题）。

### 10.1 实测：I 口径的单相设备会「静默漏报」

`CycleFeatures` 的 total 电流是三相**均方根合成** `√(ΣI_ph²)`。A 相 +3 A、B/C 各 50 A 基流时：

| 序列 | 事件前 | 事件后 | Δ |
|---|---|---|---|
| 三相合成 `i4[0]` | 70.887 A | 71.162 A | **0.275 A** |
| 本相 `i4[1]` | 5.000 A | 8.000 A | **3.000 A** |

画像 `min_stage=0.5` × 幅值 3 A ⇒ 候选门槛 1.5 A > 0.275 A ⇒ **一条候选都不生成**，界面上什么也没有（`profile_last` 为空，连 `rejected` 都看不到）。

### 10.2 改法（`detect_profile`）

```
_rows = profile_phase_rows(profile)          # "A" → (1,)，"AC" → (1,3)，"ABC" → ()
x = p4[0] if not _rows else Σ p4[r]          # P 口径
x = i4[0] if not _rows else √(Σ i4[r]²)      # I 口径
q_sig = q4[0] if not _rows else Σ q4[r]      # 无功序列同理
```

* **三相画像 `_rows=()` ⇒ 仍取 total 行，与 v0.99.29 逐位一致**（回归靠这一点）；
* 单相画像的候选台阶回到"本相"，与画像 μ（设备侧按本相测的 ΔI）同口径；
* P 口径的附带收益：候选 delta 不再被他相负荷抬高（实测 690 W vs 920 W），门槛判定更贴近设备本身。

### 10.3 改后实测

| 场景 | 改前 | 改后 |
|---|---|---|
| I 口径，A 相 3 A，B/C 背景 50 A，画像 `phases=A` | **0 条候选**（静默漏报） | 1 条，`delta=3.000 A`，正常进入匹配 |
| 同数据、画像 `phases=ABC`（等价旧行为） | 0 条候选 | 0 条候选（**不变**，确认只对声明了相别的画像生效） |
| P 口径，A 相设备 690 W + B 相他负荷 230 W 同刻投切，画像 `phases=A` | 候选 `delta=920 W` | 候选 `delta=690 W`（匹配仍是 `d_p=920 W` 的三相求和特征） |
| 三相画像（无 `phases`） | — | 逐位不变 |

### 10.4 新增/调整的测试与文档

* `tests/test_r184_single_phase_profile.py`：+4 项（`profile_phase_rows`、P 序列 690 vs 920、I 序列 3.0 A vs 0 候选、引擎提示措辞），共 **34 项**（含 `profile_phase_rows`、P 序列 690/920/920、I/P 口径事件幅值、I 序列 3.0 A vs 0 候选、旧画像仍走 total、AB 两相求和）；`test_detect_profile_single_phase_still_rejects_other_load` 改为"该台阶在 A 相序列上根本不成候选（或必须被拒）"。
* `elec_tool/nilm.py`：画像状态行「对象固定为三相合成」→ 按相别显示；B 相画像 + 3P3W 无 B 相 CT 改为明确写"**永远匹配不上**"（原来的措辞是"ΔI 不参与匹配"，容易被理解成还能凑合用）。
* `NILM_TUNING_GUIDE.md` 新增 **H.32**（单相设备怎么做画像匹配：操作、跳维后的六维行为、四个坑、三条限制、三步验收）。
* `README.md` 变更记录 **v0.99.30**；《设备画像提取与总线侧负荷辨识事件检测算法方案.md》§3.5 / §5.5 补相别字段与未接相维处理。
* `tests/test_web_ui.py` 新增 `test_profile_phases_control_and_payload`（`#np-phases` 的 8 个选项与 `normalize_phases` 对得上、`app.js` 真的把它放进提取载荷、结果区有「设备相别」卡片）。
* 全量 `pytest -q tests`：**574 passed / 1 skipped**。

**§184.12 补充实测（同一口径的另一个面）**：候选序列按本相取之后，**事件幅值**仍取三相合成 ΔI（A 相 +3 A / B、C 各 50 A 基流时 0.2746 A vs 本相 3.0 A）⇒ v0.99.31 修正，见 §184.12。

---

## 184.11 双界面覆盖审计：单相画像在「数据处理界面」与「负荷辨识事件界面」到底支持到哪一步（2026-11-03，**只检查 + 活体验证，未改任何代码**）

> 用户指令：「检查设备画像提取对设备单相画像提取功能是否已在**数据处理界面**及**负荷辨识事件界面**功能均已支持」。
> 本节只给覆盖结论与证据，**不预设结论、不动代码**；要改的地方列在 §11.5，等用户点头。

### 11.1 三句话结论

1. **功能面：两个界面都已支持。** 提取侧可以选/自动判相别并写进画像（8 个选项、非法 400、等价命令带 `--phases`）；匹配侧**总线侧与分路侧共用同一套 `NilmDetector` / `_load_profiles` / `detect_profile`**，声明了相别的画像会自动跳维、候选台阶按本相取、状态行给出中文提示、B 相 × 3P3W 直接写"永远匹配不上"。
2. **表现面：只覆盖了数据处理界面。** 负荷辨识页**没有相别控件，也没有相别字段**——相别只以"状态行里的一句红字提示"存在；事件表、事件 CSV、候选诊断 CSV、派生档位表**全部看不出相别或跳了哪几维**。
3. **顺带查出 2 处真问题**（都不是"没实现"，是"说错/显示错"）：① I 口径下单相设备的**事件幅值**仍用三相合成 ΔI（实测本相 3.000 A 的事件显示成 **0.2746 A**）；② 指南 H.32.3 让用户"看结果区「各相 |ΔI| 均值」"，**该区块在界面上并不存在**（只有"人工指定 ≠ 自动判定"时提示文字里才打印这张表）。

### 11.2 审计方法

* 静态走查：`app/static/index.html`（1170–1198）、`app/static/app.js`（3255–3260、3350–3382、4660–4790）、`app/server.py`（2901–3010 提取端点、2625–2717 派生端点、766–810 分路侧路由）、`elec_tool/nilm.py`（596–665 加载、1091–1178 汇总、1031 幅值）、`elec_tool/nilm_profile.py`（69–112 相别工具、662–700 候选序列、1218–1262 档位派生）、`tools/nilm_profile.py`（51–52、177、277）。
* 活体验证：`TestClient` 打 `POST /api/process/nilm_profile` 五态 + 非法态；`NilmDetector(cfg).summary()` 取负荷辨识侧真实下发结构；候选 CSV 表头实读。
* 数据：`/tmp/r184b/dev1ph.csv`（三列单相、5→8 A）、`/tmp/r184b/p1.json`（`phases=A` 的真实产物）。

### 11.3 覆盖矩阵

| 能力 | 数据处理界面（提取） | 负荷辨识事件界面（匹配，总/分两侧） |
|---|---|---|
| 相别入口 | ✅ `#np-phases`（`index.html:1189–1198`，auto / ABC / A / B / C / AB / AC / BC，默认 auto）；**不受基准配置模式影响**——`ntSyncBaseUI` 的禁用清单（`app.js:4082`）里没有它 | ❌ 无控件（设计如此：相别只来自画像 JSON，改相别＝重提画像） |
| 相别下发 | ✅ `npPayload` 带 `phases`（`app.js:4666`） | — |
| 服务端校验 | ✅ `normalize_phases` 归一，非法 ⇒ 400（`server.py:2947–2950`） | — 画像 JSON 的 `phases` 由 `validate_profile` 校验 |
| 写进画像 | ✅ `phases / phase_source / phase_stats`（`nilm_profile.py:1088–1093`） | — |
| 命令行 | ✅ `--phases`（`tools/nilm_profile.py:177`）；等价命令仅非 ABC 时带（`:51–52`、`:255`） | — |
| 结果区显示 | ✅「设备相别」卡，非 ABC 标红并列出跳过维（`app.js:4677–4679`） | ⚠ 只有状态行中文提示（`nilm.py:643`、`:1157`；前端 `app.js:3373` 渲染），**无结构化字段/徽标** |
| 跳维生效 | — | ✅ `detect_profile` 合并 `profile_skip_dims`（`nilm_profile.py:671`） |
| 候选台阶按本相 | — | ✅ `profile_phase_rows`（`:683–690`） |
| 3P3W 冲突 | ⚠ 无专门校验；靠"指定相别 ≠ 自动判定"的通用告警兜（`:1060–1064`） | ✅ B 相画像 × 3P3W 无 B 相 CT ⇒「**永远匹配不上**」+ 跳过 `d_ib`（`nilm.py:635–650`） |
| 分路侧 | — | ✅ 同一端点 + `_SideRouter` 改写（`server.py:799–800`）；页面右列是克隆 DOM、id 加 `-br`（`app.js:1203–1205`），`E('branch', …)` 取 `-br` |
| 派生档位 | ⚠ JSON 继承 `phases`（`derive_stage_profile` 用 `deepcopy`），但派生接口与结果表**不显示**相别（`server.py:2712–2717`、`app.js:4764–4768`） | — |
| 旧画像（无 `phases`） | — | ⚠ 按 ABC 匹配；界面**没有任何提示**说明"该画像没有相别字段、未跳维" |

### 11.4 实测证据

**A. 提取端点**（五态 + 非法态，同一份三列单相文件）

```
auto     200 phases=A    src=auto    skip=['d_ib','d_ic'] cmd=True  saved=A
A        200 phases=A    src=manual  skip=['d_ib','d_ic'] cmd=True  saved=A
AB       200 phases=AB   src=manual  skip=['d_ic']          cmd=True  saved=AB
ABC      200 phases=ABC  src=manual  skip=[]                cmd=False saved=ABC
<empty>  200 phases=A    src=auto    skip=['d_ib','d_ic'] cmd=True  saved=A
D        400 phases 只能含 A/B/C（或 auto / ABC），当前 'D'
```

- `cmd=True/False` = 等价命令里是否出现 `--phases`；`saved` = 落盘 JSON 的 `phases`（与响应一致）。
- `phase_stats` 实际键名是 **`mu_abs_di`**（不是 `mu`）——本文件 §184.4 的示例已按实况更正。

**B. 派生档位端点**（对 `phases=A` 的画像派生 0.6× 与 1.4×）

```
base keys = [device_id, grid_ratio, path, window]                       ← 无 phases
row0 keys = [amp, device_id, gate_pct, k_hi, k_lo, min_d, path, pct, scale, unit]  ← 无 phases
derived profile_..._stage0.6.json  phases= A     ← 落盘继承正确
derived profile_..._stage1.4.json  phases= A
```

**C. 负荷辨识侧真实下发结构**（`NilmDetector.summary()`，`phases=A` 的画像）

```
profile.profiles[0] 的键：candidates, device_id, device_state, error, features, has_harmonic,
                          last, level, loaded, notes, path, summary        ← 无 phases / phase_skip
profiles[0].notes：画像相别 A：匹配时跳过 d_ib、d_ic；候选台阶按本相取，ΔP/ΔQ 仍是三相求和口径（单相设备即其自身）
summary.notes    ：设备画像匹配：设备 pump1ph（W 口径…）；对象＝A 相（候选台阶按本相序列取，ΔP/ΔQ 仍为三相求和）…
旧画像（删掉 phases）：对象＝三相合成            ← 无"缺 phases 字段"的提示
B 相 × 3p3w        ：summary.notes 含"永远匹配不上" = True
候选诊断 CSV 表头  ：… 共 31 列，无 phases / skip / phase_any 列
```

**D. I 口径事件幅值（本相 vs 三合相成）**

```
A 相 5 A → 8 A，B/C 各 50 A 背景：
  d_it（三相合成 √ΣI² 的差）= 0.2746 A
  d_ia（本相）             = 3.0000 A
```
`nilm.py:1031`：`d_main = dp if use_p else f["d_it"]` ⇒ I 口径下事件表「ΔI (A)」列显示 **0.27 A**（画像 μ 是 3.0 A）。候选门槛与 D² 都用本相 3.0 A，**只误导人、不影响判定**；P 口径无此问题（`d_p` 三相求和，单相设备即其自身）。

### 11.5 缺口清单（三档，附落地成本）

**已支持（无需改）**：相别输入 / 下发 / 校验、画像字段、CLI、结果卡、跳维、按本相取候选、状态行提示、3P3W-B 警告、分路侧同源。

**部分支持（4 项）**

| 编号 | 现象 | 证据 | 建议（未实施） |
|---|---|---|---|
| P1 | `phase_stats`（各相 \|ΔI\| μ/σ）**不在界面显示**，但《NILM_TUNING_GUIDE.md》**H.32.3 让用户"看结果区「各相 \|ΔI\| 均值」"** ⇒ 文档指向不存在的显示 | `nilm_profile.py:1060–1064`（只有"人工指定≠自动"时才在提示里打印各相均值）vs `app.js:4677–4680`（卡片只有相别 + 跳过维） | **已解决（v0.99.31，§184.12.5）**：改为**结果提示行始终打印**「各相 \|ΔI\| 均值」+ 判据，未动界面布局 |
| P2 | 负荷辨识侧相别只有 notes 文本：`profiles[]` 无 `phases / phase_skip` | `nilm.py:1123–1128` | 该 dict 补 2 个键（3 行，无行为变化），前端即可做徽标 |
| P3 | 派生档位接口/结果表不显示相别（JSON 继承是对的） | `server.py:2712–2717`、`app.js:4764–4768` | `base`/`rows` 各加 `phases`，表头加 1 列 |
| P4 | 提取侧没有「B 相 × 3P3W」专门告警，只有通用"指定相别与数据最显著相别不一致" | `nilm_profile.py:1060–1064` | 提取时若 `wiring=3p3w ∧ ¬reconstruct_3w ∧ "B" ∈ phases` ⇒ 加一条 note（与匹配侧同措辞） |

**未支持（3 项）**

| 编号 | 现象 | 证据 | 影响 |
|---|---|---|---|
| N1 | 事件 CSV / 候选诊断 CSV 都没有相别或"跳过维"列；`c_d_ib / c_d_ic` 全 0 无法区分"跳过"与"真的没变化" | `nilm.py:47–54`、`:499–501` | 事后对账只能靠 `device_id` 回查画像 JSON；加 2 列会改表头，需走已有的 `_rotate_if_header_differs` 轮转 |
| N2 | 旧画像（无 `phases`）在负荷辨识页**完全没有提示** | 实测：`对象＝三相合成`，无缺字段提示 | 用户不知道自己在用"三相口径"匹配单相设备（这正是 §184.3 里 D² 爆表的那个坑） |
| N3 | 不能"就地改画像相别"（只能重提，或手工编辑 JSON） | 无端点、无界面入口 | 属新功能；要不要做请用户定 |

**口径不一致（1 条，非界面问题）**：见 §11.4-D，I 口径事件幅值用三相合成 ΔI。**已按方案 ① 修复（v0.99.31，见 §184.12）**：只在画像声明了 `phases`（非 ABC）时按设备所接相取，三相画像 / 旧画像逐位不变；想回到旧口径可把画像的 `phases` 删掉或写 `ABC`。

**顺带（文案过期，2 处）**：`index.html:1170` 与 `app.js:3258` 的「检测对象（固定）」提示仍写"候选按**三相合成量**搜索"——v0.99.30 起，声明了相别的画像候选序列是**按本相**取的（`nilm_profile.py:683–690`）。事件对象仍是 `total`、这句话的前半段没错，后半段已不成立。

### 11.6 结论与下一步（等用户决定）

* **回答用户的问题**：功能上**已支持**（两个界面都能跑通单相画像；分路侧与总线侧同源，已实测）；**但负荷辨识事件界面的支持只到"状态行提示"这一层**，事件表 / CSV / 派生表都看不出相别，旧画像也没有"未声明相别"的提醒。
* **优先级建议**（按"照做会错 → 看不出来 → 体验"）：
  1. **~~C1（I 口径事件幅值）~~——已修复（v0.99.31，§184.12）：单相画像按本相取，3 A 不再显示成 0.27 A；
  2. **P1（H.32.3 指向不存在的显示）**——现场按指南排障会找不到东西；改文档 0 风险；
  3. **N2（旧画像无提示）** + **P2（`profiles[]` 补 `phases`）**——各 3~10 行，直接决定"看不看得出来"；
  4. **N1（CSV 加列）**、**P3（派生表）**、**P4（提取侧告警）**、**文案 2 处**；
  5. **N3（就地改相别）**——新功能，单独评估。
* **本节未改任何代码 / 文档正文**（仅更正本文件 §184.4 一处键名：`"mu"` → `"mu_abs_di"`）。

### 11.7 本节未覆盖

* 未在真实浏览器里点页面（静态契约 + 服务端实测；前端 DOM 由 `tests/test_web_ui.py` 的静态断言兜底）；
* 未跑真实单相设备录波（§184.6 的遗留仍然有效）；
* 未验证"同一台单相设备在两路（总线 + 分路）各自提取、相别不同"的现场情形。

---

## 184.12 补做（同轮再续）：单相 / 分相画像的**事件幅值**口径修正（v0.99.31）

### 12.1 问题（§184.11 审计发现的 C1）

v0.99.30 把候选台阶序列改成"按画像相别取"（`profile_phase_rows`），但**事件幅值**没跟着改：
`elec_tool/nilm.py` 里 `delta_i_a` 与 I 口径的 `magnitude` 仍取 `f["d_it"]`（三相合成 `√ΣI_ph²` 的差）。

实测（A 相 5 A→8 A，B/C 各 50 A 基流）：

| 量 | 数值 | 口径 |
|---|---|---|
| `d_it`（旧的事件幅值 / CSV ΔI 列） | **0.2746 A** | 三相合成量之差 |
| `d_ia`（画像 μ / 候选序列台阶 / D² 用的那一维） | **3.0000 A** | 本相电流之差 |

⇒ 事件表里 3 A 的设备显示成 **0.27 A**，与画像 μ 差 11 倍。**判定不受影响**（候选门槛、D² 本来就用本相），
纯粹是"给人看的那一列"和画像对不上——现场第一反应会是"画像提错了"，而实际上匹配是好的。

### 12.2 改法

```python
rows = profile_phase_rows(prof)                      # 三相 / 旧画像 ⇒ ()
if rows:                                             # 单相 / 分相：按设备所接相的电流合成量
    d_i_obs = √Σ_{r∈rows} post[i_ph_r]² − √Σ_{r∈rows} pre[i_ph_r]²
else:
    d_i_obs = f["d_it"]                              # 旧行为，逐位不变
magnitude  = |ΔP|            (P 口径)  /  |d_i_obs| (I 口径)
delta_i_a  = d_i_obs
```

* 与候选序列、画像 μ(d_ia…) **同一口径**（I 口径的候选序列就是 `√Σi_ph²`，其台阶正是上式）；
* P 口径的 `magnitude` 仍是 ΔP（W），只有 `delta_i_a` 这一列按本相取；
* 三相画像 / 旧画像 / 3P3W 缺相（无 `phases` 声明）**逐位不变**。

### 12.3 验证

| 检查 | 结果 |
|---|---|
| 新增 `test_single_phase_event_amplitude_uses_own_phase_i`（引擎端到端，I 口径） | `magnitude ≈ 3.0 A`、`delta_i_a ≈ 3.0 A`；同段数据给 `phases=ABC` 的画像 **一条都不报**（合成台阶 0.275 A 连候选门槛都过不了） |
| 同测试**撤掉改动**复查 | 失败，实测值 **0.27455310483929907** — 用例确实钉住了这个缺陷 |
| 新增 `test_single_phase_event_delta_i_uses_own_phase_p`（P 口径） | `magnitude ≈ 690 W`、`delta_i_a ≈ 3.0 A` |
| `tests/test_r184_single_phase_profile.py` | **34 项**（原 32 + 2） |
| 全量 `pytest -q tests` | **574 passed / 1 skipped**（160 s） |

### 12.4 仍未做（与 §184.11.5 的其余项一致）

* ~~P1 各相 |ΔI| 均值未上界面~~ —— 已在 §12.5 解决（提示行固定打印）；
* N2 旧画像（无 `phases`）在负荷辨识页无提示；N1 CSV 无相别 / 跳过维列；
* 现场真实单相录波未验证（本节的 3 A / 50 A 背景为合成数据）。

### 12.5 顺手解决 P1：判相依据「各相 |ΔI| 均值」现在总会打印

* 之前只有"人工指定 ≠ 自动判定"时才在 ⚠ 提示里给出各相均值，而《指南》H.32.3 却让现场"看结果区「各相 |ΔI| 均值」"——指向一个平时不存在的显示。
* 现在 `build_profile()` 的单相 / 分相提示**固定带上**：`各相 |ΔI| 均值：A=3 A、B=0 A、C=0 A（某相 ≥ max(2 %×最大相, 3×离散度) 才判为接线，其余算噪声）`；
  界面「提示」区、CLI 的 `⚠` 行、`profile.notes` 与 `summary.notes` 都会出现同一句；判据与 `detect_phases()` 完全一致，可现场对账。
* 《指南》H.32.1 的「结果区」行与 H.32.3 第一行同步改指向（提示行 / 「原始画像 JSON」的 `phase_stats`）。
* 测试：`test_build_profile_from_three_column_csv` 增断言（提示里含「各相 |ΔI| 均值」且 `phase_stats["A"].mu_abs_di > 0`、`B == 0`）。

## 185 负荷辨识事件界面：`stage_free` 改列表框 + 三项档位参数联动可配（v0.99.32，2026-11-03）

用户指令：「检查基于设备画像匹配算法中**档位自由匹配配置**是否取值只有 0（派生网格：固定档位）和 1（档位自由匹配：一份画像覆盖任意档位），如果是，则改成**列表框**选择，且只有选择档位自由匹配配置时，才可配置 `stage_min_scale` / `stage_max_scale` / `stage_dim_max` 这 3 个配置」。

### 185.1 检查结论（改前）

| 侧 | 位置 | 改前状态 | 结论 |
|---|---|---|---|
| 后端校验 | `elec_tool/config.py:923-924` | `int(fv) not in (0, 1)` ⇒ 拒 2 / -1；**但 `int(0.5)==0`、`int(1.5)==1`、`int(-0.5)==0` 会被截断放行** | **意图上只有 0/1，但对小数有洞**（`phase_map` 有 `int(fv) != fv` 整数校验，`stage_free` 没有） |
| 后端默认 | `elec_tool/config.py:800` | `stage_free: 0` | 与列表框默认项一致 |
| 前端渲染 | `app.js buildNilmForm`（改前 3253-3254） | 所有算法参数一律 `<input type="number">`，`stage_free` 可键入 2、1.5、任意数（保存时才 400） | **不是列表框** ⇒ 满足「如果是，则改」条件 |
| 前端门控 | — | `stage_min_scale/stage_max_scale/stage_dim_max` 恒可编辑，与 `stage_free` 取值无关 | 后端 `stage_range` 只进 `_fit_stage`、单维否决带 `if stage_free`（`nilm_profile.py:814`），0 时这三项**完全不参与判定**，界面却可改 ⇒ 满足联动门控条件 |

### 185.2 改动（3 个文件 + 1 处后端收紧）

1. **`app/static/app.js`**：
   - `NILM_ALGOS.profile` 新增 `selects: { stage_free: [['0','0 派生网格（固定档位）'], ['1','1 档位自由匹配（一份画像覆盖任意档位）']] }`，`stage_free` 标签改为「档位自由匹配配置」；
   - `buildNilmForm`：参数有 `selects` 定义时渲染 `<select>`（含 option），否则仍渲染 number 输入 —— 机制是通用的，后续其它枚举参数可直接复用；
   - 新增 **`nilmStageGate(side)`**：按 `stage_free` 是否为 `'1'` 启用/禁用三项输入框，并给 label 打 `nilm-stage-off` 灰显 + title 提示；在 **bind（建表后）、fill（回填，含 dirty 早退路径）** 共 3 处调用（程序赋值 `el.value=…` 不触发 `change`，必须显式调）；
   - `bindNilmForm` 给下拉注册 `change → nilmStageGate`；总线/分路两列分别经 `buildNilmForm('bus')` / `bindNilm('branch')` 走到同一逻辑。
2. **`app/static/style.css`**：新增 `.nilm-algo label.nilm-stage-off{opacity:.4}` + 灰底（对齐既有 `nilm-auto-off` 观感）。
3. **`elec_tool/config.py`（后端收紧）**：`stage_free` 校验加 `int(fv) != fv` —— `0.5/1.5/-1.5` 从「截断放行、静默当 0/1 用」改为 **400**，与「取值只有 0/1」的约定和界面列表框口径一致。
4. **`tests/test_web_ui.py`**：新增 `test_profile_stage_free_is_select_and_gated_params`（7 组断言）：后端 0/1 合法、2/-1/0.5 拒；列表框选项恰为 0/1 且文案含「派生网格」「档位自由匹配」；`sp.selects` 渲染分支存在；`nilmStageGate` 函数体处理三项且按 `!free` 禁用；≥3 处调用；`change` 注册；`nilm-stage-off` 样式存在。

### 185.3 验证

- **pytest**：`tests/test_web_ui.py` **17 passed**；`tests/test_r180_stage_free.py` **25 passed**（既有 stage_free 用例不受影响）；全量 **575 passed / 1 skipped**（136 s）。
- **接口实录**（TestClient 打真实 `PUT /api/config`）：

| `stage_free` | 结果 |
|---|---|
| `0` | 200，回显 0 |
| `1` | 200，回显 1 |
| `0.5` / `1.5` / `2` / `-1` | **400** `必须是 0（固定档位）或 1（档位自由匹配）`（0.5/1.5 是本轮收紧后才拒的） |

- **行为级**（node 提取 `nilmStageGate` 函数体 + mock DOM，11 项）：`stage_free=0` ⇒ 三项 `disabled=true`、label 带 `nilm-stage-off`、有 title；`stage_free=1` ⇒ 三项可用、无灰显；非法值 `2` 按非自由档位处理；选项恰 0/1；`fillNilmForm` 回填与 dirty 早退路径均调用 gate —— **11 passed / 0 failed**。

### 185.4 覆盖范围与缺口

- **覆盖**：总线侧 + 分路侧（克隆列由 `bindNilm('branch')` 绑定同一 gate）；新建表、保存回显、套用 nilm_tune、画像「填入本侧」四条回填路径都过 gate；number 输入保留（`min_stage` 等不受影响，它两种模式都生效）。
- **不在本次范围**：`min_stage` / `phase_map` 仍是数字输入（`phase_map` 后端本就拒非整数；用户未要求）；`nilm_tune` 结果套用链路不解析 `stage_free` 列表框（走后端合并，本就兼容）。
- **缺口（🔶待用户回报）**：浏览器真实手点未做（沙盒无 jsdom），列表框观感 / 灰显切换建议用户在 preview 里点一次确认；`0.5/1.5` 收紧后，**存量非法配置文件**加载时会直接 `ConfigError`（此前会被截断成 0/1 静默工作）——如现场有此类文件需改成 0 或 1。

## 186 负荷辨识事件界面：算法配置改两层布局（v0.99.33，2026-11-03）

用户指令：「修改负荷辨识事件界面中算法配置布局，总体分为 2 大布局模块：1. 7 个算法公共配置模块；2. 7 个算法配置。其中 7 个算法配置又可分为 2 大模块：1. 前 6 个算法配置模块；2. 基于设备画像匹配算法配置模块。其中前 6 个算法配置模块又可分为以下 7 大模块：阈值差分 / 双滑窗均值差 / CUSUM 累积和 / GLR 广义似然比 / 稳态分段 (Hart) / 中值滤波差分 / 前 6 个算法公共配置模块。」（同轮另确认把第 186 轮前的「前后窗 vs 过程时长定量分析」追加进指南 H.30.2。）

### 186.1 设计：字段按「作用域」归组

原 `#nilm-form` 混装 9 项，实际作用域分两类——这正是拆组依据：

| 归属 | 字段 | 作用域依据 |
|---|---|---|
| **① 7 个算法公共配置**（`#nilm-common7` > `#nilm-form`，5 项） | 启用、事件落盘、检测量、周波窗长、最小事件间隔 | 画像匹配同样吃：enabled/save 全局；检测量须与画像 `quantity` 一致；`window_cycles` 参与 need 公式（`nilm.py:859`）；`min_gap_cycles` 对画像同样去重（`last_end+gap`） |
| **前 6 个算法公共配置**（②-1 内 `#nilm-scalar-common` > `#nilm-form-scalar`，4 项） | 检测对象、自适应算法参数、rel_tol_pct、min_delta_pct | 检测对象对画像固定 total（面板内注明"上方勾选只作用于其它算法"）；`nilmDimAuto` 明确排除 profile（`app.js` "画像匹配参数不由自适应推导"）；rel_tol/min_delta 只作用 6 标量算法（指南 H.30.0 坑①） |

6 个算法面板与 1 个画像面板**保持原有 `.panel.nilm-algo` 结构不变**，只换容器：面板即"模块 1~6"，分组标题给出组名，避免每面板再包一层边框的视觉噪音。

### 186.2 改动清单（3 个文件 + 1 个新 jsdom 工具）

1. **`app/static/index.html`**：检测参数区重写为——`#nilm-common7`（wp-group，含 5 字段的 `#nilm-form`）＋ `#nilm-algos`（wp-group，②大组）内嵌 `#nilm-scalar-group`（含空容器 `#nilm-scalar-algos` ＋ `#nilm-scalar-common`：4 字段 `#nilm-form-scalar` ＋ `#nilm-auto-out`）与 `#nilm-profile-group`（含空容器 `#nilm-profile-algo`）。**9 个字段的原 HTML 逐字搬运**（含 title 长文案），只换缩进与分组。
2. **`app/static/app.js`**：`buildNilmForm` 抽出 `panelHtml(a)`，`scalarHost.innerHTML = keys.filter(a !== 'profile').map(panelHtml)`、`profileHost.innerHTML = panelHtml('profile')`；`normalizeConfigForms(host)` 仍传 `#nilm-algos`（深度覆盖两容器）；`bindNilmForm` 绑定范围注释更新（`[nilm-form, nilm-algos]` 深度覆盖前6公共，**代码未改**——前6公共在 `#nilm-algos` 深处）。
3. **`app/static/style.css`**：新增 `#nilm-form-scalar{,-br} label.nilm-auto-off` 灰显两行（rel_tol/min_delta 迁组后原 `#nilm-form …` 选择器覆盖不到）。
4. **`tools/ui_r186_check.cjs`**（新增）：jsdom + 真实服务端的行为级检查 A~F 六组（见 186.3）。

### 186.3 验证

- **pytest 静态契约**：`test_web_ui.py` 新增 `test_nilm_config_two_layer_layout`——层级顺序（10 个 id 的文档流顺序）、字段互斥完整（5+4=9、无交叉、检测量属①组）、分容器填充（`filter(a !== 'profile')`、`panelHtml('profile')`）、绑定范围未改、灰显规则存在 ⇒ `test_web_ui.py` **18 passed**；既有 `test_r12::test_frontend_wiring`（`nilm-algos` 等 id 存在）、`test_r87`（auto 相关 id 存在）不受影响。
- **jsdom 行为级**（`node tools/ui_r186_check.cjs`，打真实 :8000）**36 passed / 0 failed**：
  - A 结构：总线/分路两列 `#nilm-scalar-algos` 恰 6 面板、`#nilm-profile-algo` 恰 1、`#nilm-algos` 深度合计 7；①组恰 5 字段、前6公共恰 7 控件（4 相 checkbox + 自适应 + rel_tol + min_delta）、两组互斥；层级 common7∥algos、scalar-common⊂scalar-group、profile-group∥scalar-group；`#nilm-auto-out` 在前6公共组内。
  - B 回填：`fillNilmForm` 按 id 跨新容器回填检测量/周波/rel_tol/profile.d2_max/threshold.enabled，两列各 7 项全对。
  - C 自适应：默认 0 灰显 → 勾选后 `label.nilm-auto-off` 40 个（>20）、含 checkbox 的 0 个（算法启停/检测对象/自适应仍可用）、rel_tol/min_delta 灰显+disabled、**①组 5 项不被灰显**（在 `#nilm-algos` 外，与旧行为一致）、推导面板显示、取消恢复。
  - D 脏标记：改前6公共 rel_tol / ①组 周波窗长 / ②-2 profile 参数 ⇒ 三处都置脏。
  - E 载荷：9 字段 + 7 算法 + channels 齐全。
  - F `stage_free` 联动（第 185 轮）在 profile 面板迁入 `#nilm-profile-algo` 后仍 0 禁 1 放。
- **兼容性**：jsdom 旧工具的选择器（`#nilm-algos .nilm-algo[...]`、`label.nilm-auto-off` 深度查询）全部兼容（面板仍在 `#nilm-algos` 深处）；`ui_r24` 的 `===6` 断言在 v0.90 加入画像后本就过期（实际 7），本轮不使其变差。
- 全量 pytest：**576 passed / 1 skipped**（139 s）。

### 186.4 指南同步（防文案过期 + 落实上轮「需要」）

1. **H.30.2 ③ 追加「定量版：由启停过程时长算前后窗」**（第 186 轮前实测）：三波形系数表（线性 post≥1.2×D、指数尾 4~5τ、冲击 ≥2×D20 及各自症状）；post<D 连候选都不生成 + `max_scale` 只救候选不救特征；pre 与过程时长无关；五步计算链（`longest_transient` 独立量 T → ×f_nom → 波形系数 → 两上界 → need）；⚠ `dur_cycles ≤ post−1` 鸡生蛋陷阱；post 过大的三笔代价（延迟/自动扩窗/吃邻事件）。
2. **H.30.0 分布表**：原「检测侧·公共项（算法列表上方）」一行拆为「7 算法公共（①）」「前 6 算法公共（② 内）」两行。
3. **H.30.3 标题**：「算法列表上方那几个」→「v0.99.33 起分两处：① 7 个算法公共配置 ＋ ② 内前 6 个算法公共配置」。

### 186.5 覆盖范围与缺口

- **覆盖**：总线/分路两列同构（克隆机制沿用）；保存 / 套用 nilm_tune / 自适应 / 脏标记 / stage_free 联动四条链路在新容器下全部实测通过；旧 jsdom 工具选择器兼容。
- **缺口（🔶待回报）**：① 浏览器真实手点确认两层分组的视觉观感（wp-group 嵌套边框）；② 检测对象位于 ②-1 末尾（前6公共组内、6 面板之后），画像面板在它**下方**——面板内「上方检测对象勾选」文案仍成立，但若你希望前6公共组放在 6 面板**之前**（先配公共再逐个调算法），说一声即调（纯 HTML 顺序调整）；③ `ui_r24`/`ui_r87` 等历史 jsdom 工具的个别过期断言（r24 的 `===6`）未顺修，与本轮无关。

## 187 离线 CSV 播放速率：耗时超过数据时间的根因与修复（v0.99.34，2026-11-03）

用户指令：「当前播放离线数据源 CSV 文件速率**耗时超过数据时间**，修改代码，优化离线数据源播放速率。」

### 187.1 定位过程（沙盒实测，逐层排除）

| 步骤 | 实验 | 结果 → 结论 |
|---|---|---|
| 1 | 库路径 bench（合成 relative 秒 60 s 文件） | **47.81× 实时**——"很快"，但**只有 3 次结果**（60 s 数据应有数百次）⇒ 异常，先查 |
| 2 | 服务端默认（不限速）播 60 s | 1.56 s 跑完、`emits` 每量仅 2 次、`data_t_end=0.0998` 卡在首块末 | 
| 3 | 逐块打桩（relative 秒文件） | **三块 `t[0]` 全为 0**、`t_end` 全为 0.1 → **时间轴逐块归零** ⇒ 根因 B |
| 4 | 绝对时刻（`HH:MM:SS.ffff`）文件 speed=1/4/8 扫描 | **全部恒 ≈1×**（30.27/27.09/28.45 s）⇒ **名义倍速完全失效** ⇒ 根因 A |
| 5 | 节拍钟打桩（speed=8） | `wait_until` 累计仅 0.01 s、目标 3.75 s 精确 ⇒ **钟与等待都对，是 poll_once 每块 ≈87 ms 把墙钟吃满** |
| 6 | `tools/bench_playback.py --profile`（绝对时刻 30 s 文件） | **0.52× 实时**；cProfile：`parse_timestamps` **54.24/58.08 s（93 %）**、`strptime` 192 万次（=全部行）⇒ A 实锤 |
| 7 | 溯源 | `_RE_SLASH_CLOCK` 要求 `Y/M/D ` 前缀，纯 `HH:MM:SS.ffff` 不匹配 → 快路径 `_parse_slash_clock_block` 返回 None → 逐行 `datetime.strptime`（基准 **1900-01-01、负 epoch −2.2e9**、`mode=datetime` **不跨午夜展开**）；而 `00/00/00` 走快路径（`_NO_DATE_BASE=86400`、`clock_time`、展开）⇒ **同为无日期写法两套语义** |

**两个根因**：

- **A（主因，用户主诉）**：纯时刻列逐行 strptime，30 s 数据解析 54 s ⇒ 墙钟超过数据时间；8×/4× 被拖到 ≈1×。附带：1900 负 epoch（Windows localtime 风险 F-40）、跨午夜不展开。
- **B**：`relative_s` 每块减本块首值 ⇒ 时间轴冻结 ⇒ 曲线只出首尾点、`_due_keys` 不触发、节拍钟只等第一块（限速失效）、事件时标全错——此前 bench 的"47.81×"是**不执行计算的假快**。

### 187.2 修复（`elec_tool/sources/parsing.py` + 2 处消费端）

1. **A**：新增 `_RE_TIME_CLOCK`；`_parse_slash_clock` 认纯时间（与 `0/00/00` 同 `_NO_DATE_BASE` 基准、同 `no_date=True` ⇒ `parse_timestamps` 自动获得 `clock_time` + 跨午夜展开 + 正 epoch）；`_parse_slash_clock_block` 放行纯时间并**向量化重写**——`np.char.partition('.')` 切 (head, frac) → `np.unique(heads)` 整秒唯一值各解析一次 → `inverse` 映射基值 + `np.char.add("0.", frac).astype(float)` 向量小数；任一 head 解析失败 / 小数非数字 → 返回 None 走慢路径（**与逐值逐位一致、拒绝语义不变**）。
2. **B**：`parse_timestamps(..., relative_base=None)`——relative_s 时 `t = t - relative_base`（缺省仍为 `t - t[0]`，旧调用方行为不变）；`iter_csv_blocks` 在 **seek 前**读文件首行时标数值（无表头时复用已读首行，有表头时按 `data_lo` 读一行）→ `ts_base` 贯通 3 个 `_rows_to_block` 调用点 → `_assemble`。
3. **同口径消费端**：`app/server.py _file_time_range` 末段 `parse_timestamps(..., relative_base=首段值)`（否则 relative 文件公共时间段 `t1≈0`、算不出交集）；`elec_tool/wave_preview.py` 末段同理（预览时间轴范围塌缩）。
4. **保留的既有语义**：时标缺口按数据时间轴等待（实测 gap30 speed=4 → 15.18 s ≈ 跨度 60/4）——两侧同步与公共时间段依赖同一时刻口径，**未动**。

### 187.3 验证

- **新增 `tests/test_r187_playback_pace.py` 8 项**（全过）：纯时间快路径与逐值逐位一致 + 拒绝语义（epoch 纯数字 / 非时间串 / 小数非数字）；纯时间与 `00/00/00` 基准相等且为正、跨午夜展开；20 万行纯时间解析 <2 s（实测 217 ms，原 5~6 s）；relative 分块首值 = k·640/fs、整列 diff=1/fs、与整列一次解析逐位一致；`_file_time_range` relative `t0≈0`、`t1≈2 s`（原 ≈0）；端到端 8×（纯时间 10 s → wall 0.7~4 s）与 4×（relative 10 s → 2~7 s，**下界防限速失效**）且 `data_t_end` 推进、每量 ≥9 个结果点；缺口文件保持跨度语义。
- **既有回归**：`test_r82_playback_perf + test_pace_clock` **6 passed**（快慢路径一致、混合拒绝、跨午夜、`engine.run` 不逐块睡等原语义保持）；全量 **584 passed / 1 skipped**（190 s；时长增长来自 B 修复——此前时间轴冻结的用例现在真正执行到期计算，属预期）。
- **端到端实录（服务端 REST，修前 → 修后）**：

| 场景 | 修前 | 修后 |
|---|---|---|
| 纯时间 30 s，speed=8 | 28.45 s（实效 1.05×） | **3.93 s（7.63×，期望 3.75 s）** |
| 纯时间 30 s，speed=4 | 27.09 s（1.11×） | **7.65 s（3.92×）** |
| 纯时间 30 s，speed=1 | 30.27 s（0.99×） | 30.17 s（0.99×） |
| relative 60 s，speed=4 | 轴冻结、曲线不出点 | **15.13 s（3.97×）**、`emits 61/301`、`data_t_end=60` |
| 相对秒库路径 bench | 47.81×（假快、3 结果） | **10.31×、301 结果** |
| 纯时间库路径 bench | **0.52×（58.11 s > 30 s 数据）** | **11.75×（2.55 s）** |

### 187.4 行为变更与缺口

- **行为变更（有意）**：纯时刻列文件时间轴基准 1900 负 epoch → 与 `00/00/00` 相同的 1970+1 天正 epoch；`mode` datetime→clock_time，**获得跨午夜展开**（对齐已文档化语义；`_file_time_range`/`wave_preview` 同步改，公共时间段/自定义时间两端同口径）。
- **缺口（🔶）**：① 真实用户文件复验（本沙盒为合成文件）；② 解析修复后 8× 已贴预算（3.93 vs 3.75 s），更重配置 / 更大 `block_samples` 下 8× 或略欠、**4× 内稳定**——新瓶颈为 compute+broadcast，如需再提可续挖；③ 时标缺口仍按跨度等待（"跳过缺口更快放"属产品决策，改动会破坏两侧同步/公共时间段口径，未动）；④ 界面/文档中"数据时间"口径说明未单独立条（数据时长=样本/fs，时标跨度=含缺口）。

## [2026-11-04] 专题：业务网页智能问答（本地 / 云端模型、SSE、RAG 与安全边界）
- 类型：用户专题 / 验证专题
- 目标与假设：在现有 FastAPI + 原生 JS 网页内新增技术问答，覆盖 NILM、电能质量、算法参数、工具操作、报错排查；本地 / 云端统一 OpenAI-compatible Chat Completions 协议。既有应用没有用户登录 / 角色体系，因此页面可见范围只作入口显隐；必须显式交代云端数据边界。
- 方法 / 数据 / 参数：新增 `app/assistant.py`（标准库 `urllib` 调模型、local 请求绕过代理、local 地址限制 loopback / 私有网段 / 明确内网域名、cloud HTTPS、SSE / 非流式解析、错误脱敏、60 秒 12 次限流 / 3 个并发、文本分块 + TF-IDF 词项检索）；新增 assistant REST 路由与前端弹窗。RAG 文件由管理员导入 UTF-8 md/txt/json/py/csv/html/yaml/log（单文件 1 MB、一次 10 个/5 MB、总 100 个/20 MB），普通配置和知识库默认位于 gitignore 的 `output/assistant/`。密钥环境变量优先、不会由 GET 回传、不写普通 JSON；UI 输入密钥仅在服务进程内存；敏感词正文仅管理员口令端点返回，聊天错误不回显匹配词。会话不写 localStorage；云端风险提示覆盖问题/历史/命中片段，说明扫描不是 DLP。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无（本轮沙盒实现与验证；现场模型验收待后续）。
- 结果 / 结论：`./.venv/bin/python -m pytest -q` **596 passed / 1 skipped**（158.39 s，另有 1 条既有 Starlette/httpx deprecation warning）；`node tools/ui_assistant_check.cjs` **PASS 21 checks**（同一测试覆盖 DOM 页面显隐/禁用态、分片 SSE、Markdown / XSS 安全、引用、模型切换新会话、管理员配置/敏感词管理及本地文件导入）；`py_compile`、`node --check app/static/app.js`、`node --check tools/ui_assistant_check.cjs`、`git diff --check` 通过。新增 API 集成测试 mock 上游文本，验证 SSE / 非流式路由；服务单测检查 local/cloud request headers/body/proxy、上游 SSE、401 错误脱敏、RAG 文档导入/检索/删除、敏感历史与检索片段拦截、限流、密钥不落盘。应用已在沙盒 `0.0.0.0:8001` 启动，`GET /` 与 `GET /api/assistant/config` 为 200。
- 是否进入 REPORT.md（稳定结论）：否（属于本轮工程实现 / 验证报告；尚无真实模型或现场性能稳定结论）。
- 遗留问题：未连接真实 Ollama/vLLM，也未配置真实云端 Key/供应商，故 upstream 只用 mock 验证；Windows 安装、目标内网 DNS/代理、真实浏览器视觉与 HTTPS 反代仍待用户回报。`visible_views` 不是账户级权限；chat API 当前无登录，生产暴露仍需网络访问控制；敏感词检测不保证识别所有业务秘密。

## [2026-11-04] 专题：智能问答零配置演示通道、右侧抽屉与来源文件名脱敏
- 类型：用户专题 / 验证专题
- 目标与假设：承接网页智能问答 v0.99.35，落实用户新增验收项：①在现有业务页面内用右侧抽屉呈现，而非跳转独立页面；②未配置本地或云端模型时可零配置使用“内置知识库（演示）”摘录通道，展示本地摘录与引用且不调用模型；③来源隐藏时，回答与引用内的支撑文件名必须脱敏。代码未找到助手专用来源显示开关；已向用户说明，暂按现有总线配置 `branch.hide_ui` 作为服务端隐藏判据，若非此规则需按用户指出的正式开关调整。此映射是本轮假设，不宣称是助手既有专用配置。
- 方法 / 数据 / 参数：
  - `app/assistant.py`：新增随程序打包的 4 条演示知识摘录；新增 `builtin` backend 与本地检索 / 引用，设为新安装默认；该 backend 构造本地答案，不访问 `urllib` 模型 endpoint。扩展来源名脱敏，知识库**全部**文件名（不仅是当前检索命中文件）参与脱敏；清理 RAG 片段、system context、问题 / 历史、completion 答案、来源 citation 与 SSE token 分片（覆盖文件名跨分片情况）。
  - `app/server.py`：聊天路由只根据服务端 `RUNNERS["bus"].cfg.branch.hide_ui` 传递脱敏条件，忽略客户端是否要求显示文件名；非流式和 SSE 共用同一份已净化 plan。
  - `app/static/index.html` / `style.css` / `app.js`：`<dialog>` 固定在当前业务页右侧，移动端全屏；助手首次会话、管理员默认后端和恢复配置均加入 builtin 选项；入口、面板关闭 / 遮罩、零配置说明联动。
  - 测试：`tests/test_assistant.py` 覆盖无模型请求的 builtin 摘录与引用、提示 / 历史 / 检索内容清理、completion 与跨分片 streaming 文件名清理；`tests/test_server.py` 覆盖服务端隐藏判据及 JSON + SSE 路由；`tests/test_web_ui.py` 覆盖右抽屉与 builtin 默认静态契约；`tools/ui_assistant_check.cjs` 第 68 行按 backend 返回不同模拟引用 / 答案，新增 builtin 与 local 流程、抽屉和遮罩交互检查。
  - 本地验证数据与配置隔离于 `/tmp/nilm-assistant-preview/`；未写入、删除或暂存 `tmp/` 用户工件。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无（仅沙盒侧验证；live preview 面向用户提供手工点检）。
- 结果 / 结论：
  - 全量 `./.venv/bin/python -m pytest -q`：**600 passed / 1 skipped**，174.88 s；另有一条既有 Starlette/httpx TestClient deprecation warning。
  - `node tools/ui_assistant_check.cjs`：**PASS 33 checks**（业务页入口显隐、右侧抽屉 / 遮罩关闭、默认 builtin、零配置说明、内置摘录 / 引用、local 流式分片解析、Markdown / XSS 安全、会话切换、管理员配置与知识库导入）。`node --check`（app.js 与工具脚本）、`py_compile`、`git diff --check` 均通过。
  - 隔离配置下 live preview 监听 `0.0.0.0:8001`：`GET /`、`GET /api/assistant/config` 均 HTTP 200，配置默认 backend=`builtin`；非流式 JSON 与 SSE 聊天均 HTTP 200，返回本地演示摘录与引用。builtin 请求由服务单测 monkeypatch `_open_request` 为立即失败，仍通过，证明不触发模型端点。
  - 来源隐藏判据分别覆盖隐藏 / 可见；隐藏时 API 的 JSON 与 SSE source frame、答案 delta 均不出现原支撑文件名，只返回脱敏来源名。右侧抽屉行为通过 jsdom 与 CSS 契约检查；没有声称已做真实浏览器像素级视觉验收。
- 是否进入 REPORT.md（稳定结论）：否（是用户界面 / 工程实现及安全规则假设；暂无真实模型或现场验收稳定结论）。
- 遗留问题：①未接真实 Ollama/vLLM 或云端 provider；②Windows / 用户内网 DNS、代理、HTTPS 反向代理和真实浏览器视觉仍待用户验收；③`branch.hide_ui` 原意是隐藏分路侧业务界面，并非助手专用来源开关，本轮暂作来源脱敏映射，若用户提供独立规则应调整服务端；④切换隐藏规则后，既有页面中已经渲染的历史消息不会被服务器追溯改写，后续新请求会按当时的服务端规则脱敏。

## [2026-11-04] 专题：智能问答同页文档复合侧栏与完整本地资料库
- 类型：用户专题 / 验证专题
- 目标与假设：按用户新增要求，把助手改成同一业务页固定复合侧栏，左侧浏览完整结构化产品帮助和平台参数、右侧保留原会话问答 / 模型 / 管理员操作；标题“智能问答助手”，定位调参辅助文档助手，参数问题优先查平台参数清单。实验能力默认解释为提供可复现步骤，不声称可直接执行命令或改配置（当前无受控实验 API）。
- 方法 / 数据 / 参数：新增 `app/assistant_docs.py`，服务启动时从白名单加载 7 类文档：README 架构 / 使用 / 部署章节、稳定结论 `REPORT.md`、设备画像算法方案、完整 `NILM_TUNING_GUIDE.md`、`NILM_DATA_DICT.md`、助手说明、平台参数清单；后者由 `AppConfig()` 代码默认与跟踪的 `configs/default.json` / `configs/branch.json` 生成，参数路径 264 个，三类来源分列，避免误报当前运行值。新增只读 `GET /api/assistant/documents` 返回目录 / 全文；builtin 与 local/cloud RAG 共用内置语料及管理员附加资料，参数问句提高清单检索权重，显式字段名再作片段级排序；文本分块尽量保留行边界、引用摘要按命中字段截取。`index.html/style.css/app.js` 改为固定 `<aside>`：桌面双栏、窄屏“文档 / 问答”切换，支持搜索、选择、安全 Markdown 正文；管理员上传知识仍独立可清空，会话 / 模型切换 / SSE / 配置 / 来源脱敏逻辑保留。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无（本节仅沙盒执行；`./.venv/bin/python -m pytest -q`、`node tools/ui_assistant_check.cjs`、`npm ci`，live preview 输出隔离 `/tmp/nilm-assistant-preview-189`）。
- 结果 / 结论：全量 pytest **603 passed / 1 skipped**（138.94 s，1 条既有 Starlette/httpx deprecation warning）；定向 `tests/test_assistant.py tests/test_server.py tests/test_web_ui.py` **58 passed**；`node tools/ui_assistant_check.cjs` **42 checks**；`node --check app/static/app.js`、`node --check tools/ui_assistant_check.cjs` 与 `git diff --check` 通过。测试覆盖文档完整性 / 参数来源分列、字段优先命中、builtin 不调用模型、local/cloud RAG 上下文、`GET /api/assistant/documents`、脱敏、文档搜索 / 正文浏览 / 移动端标签、SSE / 会话 / 管理员兼容。隔离预览监听 `0.0.0.0:8001`：首页、文档 API（7 份 / 462,782 字符）、助手配置与 builtin `sampling.fs` 问答均 HTTP 200，引用摘要包含命中参数。`tmp/` 测试期间新增的 12 个当日输出已清理；任务前备份 `/tmp/nilm-tmp-before-188-sync.tar.gz` 中的原有工件已恢复，另将初始工作区已有的 12 个被测试覆盖的跟踪样本从当前 HEAD 恢复。最后一次全量测试前另存 `/tmp/nilm-tmp-before-final-pytest.tar.gz`，测试后 `diff -qr` 为空；未把任何 `tmp/` 路径纳入本轮提交，原有用户工件保持不变。
- 是否进入 REPORT.md（稳定结论）：否（属于助手文档 / UI 工程实现与回归，没有新的算法稳定结论；真实模型和现场验收待后续）。
- 遗留问题：真实 Ollama/vLLM、云端供应商与 API Key、Windows / 现场网络 / HTTPS、用户真实浏览器视觉仍待外部验收；`branch.hide_ui` 来源脱敏映射仍是既有暂定规则。当前仍为词项 TF-IDF 检索，不是语义向量或生成式内置回答。

## [2026-11-04] 专题：同一波形下 200/3000 与 600/3000 设备画像前窗对照

- **类型**：用户专题 / 现场产物取证（未改算法代码）
- **目标与假设**：按用户要求比较总线侧、分路侧以不同前后窗提取的画像，在相同波形回放时为何出现“能认停机 / 额外误报”。用户本轮文字两处都写 `600/3000`；刚拉取的最新提交 `1fad72a` 提交说明明确为「更新测试数据，比较前后窗区别（200/3000与600/3000）」，故将前一组按 **200/3000** 解读。误报真值按用户陈述处理；日志没有设备级人工真值标签。
- **方法 / 数据 / 参数**：代码 / 工作树快进到 session 分支最新 `1fad72a`（其相对前一提交仅更新 `tmp/` 测试产物，算法代码未变）。核对 `tmp/run_info.json`、`config_bus.json`、`config_branch.json`、两份画像 JSON、`nilm_events_20261104.csv`、`nilm_profile_candidates_20261104.csv` 及 `tmp/realtime/*_20261104.csv`。按 `elec_tool.nilm_profile.mahalanobis_diag()` 使用两份画像的 μ/σ、`lambda_rel=0.02`，对候选 CSV 中的同一事件向量交叉复算；核对运行配置 `nilm.algorithms.profile` 默认阈值：`d2_max=9`、`min_confidence=0.3`、`margin=1.5`、`state_check=1`，两侧 `max_scale=1`、`min_scale=0.25`、`window_cycles=3000`。
- **用户执行命令（含实录路径；本节无用户命令则注明）**：无新增用户命令；证据是已拉取并保留在 `tmp/` 的现场产物。原始 `D:\Work\testPython\NILM_Test2026\nilm_calc_tool\data\化工行业-海湾化工-bus-停止.csv` 不在沙盒 `data/` 中，因此本轮是对已落盘候选 / 事件 / 趋势的复核，不声称从原始周波 CSV 完整重放。

### 1. 同波形与配置一致性

- `run_info.json` 记 `source_id=0`（bus）与 `source_id=1`（branch）都播放 `化工行业-海湾化工-bus-停止.csv`；启动相差约 **0.760 s**。趋势产物按共同的 `(t_epoch_s, window_s)` 逐点对比，六类量均完全相同：`current/power/voltage` 各 **1,172** 对，`fundamental/harmonic/interharmonic` 各 **4,688** 对，所有物理字段最大差 **0**。因此现有回放输出支持“同一波形值”对照。
- 对照映射：bus `source_id=0` 使用 `profile_bus_profile_device_20261104_090215.json`（画像 `pre/post=600/3000`）；branch `source_id=1` 使用 `profile_branch_profile_device_20261104_112427.json`（`200/3000`）。两份画像均由同一个设备文件 `...dev1.csv` 提取，`fs=10,000 Hz`、`f_nom=50 Hz`、`quantity=i`、3p4w、PT=CT=1、`phases=ABC`、`label_mode=auto`；两份 JSON 的内嵌 `side` 都是 **`bus`**。故文件名 / `source_id` 说明了本轮挂载位置，但不能证明 200 画像本身是按分路侧测量配置提取的。
- **归档不一致项**：`run_info.json` 的 branch `source_path` 为 `...bus-停止.csv`，但 `config_branch.json` 的 `source.path` 为 `...bus-启动.csv`。趋势逐点一致支持本轮实际输出同源，但配置快照路径彼此矛盾；需现场确认哪个是生效配置，不能只凭 JSON 快照复现实验。
- 两侧画像匹配参数相同；bus / branch 的 `rel_tol_pct`、`min_delta_pct` 数值不同，但它们只用于六个标量算法，不是画像匹配误报的原因。

### 2. 回放结果：两者都识别了停机，200/3000 多报一次启动

| 回放侧 / 画像窗 | 停机输出 | 额外启动输出 | 画像候选总数 |
|---|---|---|---:|
| bus / 600/3000 | 14:38:11.085 STOP `confirmed`；D²=11.113，D²/8=1.389，confidence=0.4993，scale=0.25 | 无已接受的 START | 52：1 条 STOP 确认；51 条 START 候选全部拒绝（49 条带 `window_crowded`，2 条 `d2_exceeds,trajectory_deviates`） |
| branch / 200/3000 | 14:38:14.325 STOP `confirmed`；D²=6.474，D²/8=0.809，confidence=0.6672，scale=0.25 | 14:48:10.465 START `confirmed`；D²=17.297，D²/8=2.162，confidence=0.3392，margin=52.88 | 6：1 条 STOP、1 条 START 确认，4 条后续 START 拒绝 |

**关键更正**：本轮的 `200/3000` 并未漏掉停机；它对停机的匹配反而比 `600/3000` 更近。差别是 `200/3000` 在后续 14:48 增加一条用户认为不属于目标设备的 START。`confirmed` 是算法通过判据，不是独立真值认证。

停机向量交叉代入两份 shutdown 画像也均通过：

| 候选向量来源 | 对 600/3000 shutdown 画像 | 对 200/3000 shutdown 画像 |
|---|---|---|
| bus 14:38:11.085 | D²/8=1.389；本侧实录 confidence=0.4993 | D²/8=1.265；base confidence≈0.5313 |
| branch 14:38:14.325 | D²/8=0.907；base confidence≈0.6354 | D²/8=0.809；本侧实录 confidence=0.6672 |

这里的 off-diagonal `base confidence` 只由 μ/σ 的 D² 换算，不含轨迹模板惩罚：候选 CSV 未保存该候选的 16 点 trajectory，因此不能把它说成完整跨画像最终置信度；对角项则是运行记录的实测值。两侧各自的 STOP 已在原运行中 confirmed。故本数据不支持“只有 600/3000 能识别停机”。

### 3. 为什么 200/3000 会误识别

1. **它不是随机噪声，而是一段与画像启动形态相似的缓慢负荷变化。** 同源 1 s 趋势在 14:48:08.621 为 `Ia/Ib/Ic=51.96/63.32/60.90 A`、`P/Q=−40.97/−7.36 kW/kvar`；14:48:58.797 为 `89.83/101.08/96.41 A`、`−64.71/−6.80 kW/kvar`。约 50.176 s 内 ΔP≈−23.74 kW、三相电流均增加约 35–38 A，接近画像启动的 `ΔP=−23.61 kW`、`ΔI=+35.19/+30.37/+41.74 A`。按用户的设备真值它是“他负荷 / 非目标动作”，但波形确有与目标启动相似的变化。
2. **200 周波前窗把该长变化切出一个更像目标启动的局部候选。** 200/3000 记录的误报向量为 `dIa/dIb/dIc=+32.38/+33.97/+28.08 A`、`dP=−21.55 kW`、`dQ=+0.369 kvar`、`peak_ratio=1.397`、`dur=835 cycles`；目标 startup 为 `+35.19/+30.37/+41.74 A`、`−23.61 kW`、`+0.866 kvar`、`1.618`、`1288 cycles`。误报各维贡献最高为 `dIh=5.58`、`dQ=5.26`、`dIc=4.68`；都未形成单维硬否决，平均 D²/维仍是 2.162。
3. **门槛允许它通过。** `confidence=exp(−D²/(2×8))≈0.3392`，高于 `min_confidence=0.3`；等价边界是 D²/维约 **2.408**，本候选 2.162。`d2_max=9` 检查的是平均 D²/维，并非每个特征必须低于 9；`stage_free=0`，单维档位否决不启用。它的方向 margin=52.88，方向很明确；设备在前一 STOP 后处于 off，故 START 也不违反 `state_check`。这些门槛回答“为什么被算法确认”，不等于证明它真是目标设备。
4. **画像样本太少、容差由经验下限决定。** 两份画像均 `startup.n=1`、`shutdown.n=1`、`label_mode=auto`。单样本没有可估计的重复性，σ 按下限生成（主要幅值维约 15%，ΔQ 约 25%，持续周波约 50%）；JSON 自带“每方向建议 ≥3 次”警告。因此两份画像都容易接受电气量级相近的他负荷。
5. **600/3000 本轮拒绝的是不同的特征切片，不是相同误报向量。** `600/3000` 在 14:48:17.105 附近的近邻候选变成 `dur=2638 cycles`、`dP=−18.32 kW`、`dQ=+0.170 kvar`、D²/8=3.548、confidence=0.1696，并带 `window_crowded`；后续同向候选亦未通过置信度。它比 startup 的 1288 周波长得多，也落在不同的局部前后窗，因此被拒。
6. **不能把差异简单归因于两张画像的均值不同。** 两份 startup 的 μ/σ 各维差不超过约 **0.04%**，因为自动定位到同一个 1288 周波启动事件；shutdown μ 有约 2.4–5.5% 差别、dur 为 305 vs 320 周波。将 14:48:10.465 的同一向量交叉代入两份 startup μ/σ，得到 D²=17.294 / 17.297、D²/8=2.162、未计轨迹惩罚的 base confidence≈0.3393 / 0.3392；两份 startup template 自身 RMS 差仅 2.32×10⁻⁵，形状也几乎一致。候选 CSV 未保存该事件的 16 点轨迹模板，因此不能精确复算它在另一 profile 上的最终 trajectory penalty；但画像均值 / 方差没有显示出能拒掉该向量的差异。已观测到的 600 拒绝，是它生成了另一条不同候选（14:48:17.105、duration 2638）而不是同一向量被 600 均值拒绝。可复现证据支持前窗改变候选定位与比较几何；由于原始周波 CSV 不在仓库，候选形成的逐周波因果仍未实证。

### 4. 前窗大小如何设置，以及本数据的建议

- **单位是额定频率下的周波数，不是秒，也不是采样点数。** `pre_cycles=200/600` 在 50 Hz 下分别是 **4/12 s**；`post_cycles=3000` 是 **60 s**。当前 `fs=10 kHz`、50 Hz，每周波 200 个采样点，故 pre 约为 40,000 / 120,000 个原始采样点。
- **在“数据处理 → 设备画像提取”配置**「前窗 (周波)」设 `600`、「后窗 (周波)」设 `3000`，然后重新提取；确认新 JSON 中 `pre_cycles=600`、`post_cycles=3000`，再让对应侧的 `nilm.profile_path` 指向这份 JSON 并重新回放。CLI 等价参数是 `--pre 600 --post 3000`（例如 `python tools/nilm_profile.py --file <设备侧CSV> --device device --config <基准配置> --quantity i --pre 600 --post 3000 --out <新画像.json>`）。
- **改完必须重提画像**：匹配时读取的是画像 JSON 内保存的 `pre_cycles/post_cycles`，不是检测界面上另一个参数。不要把它与标量算法 `nilm.algorithms.two_window.pre_cycles`（只影响双滑窗算法）混淆；`nilm.window_cycles` 是循环缓存大小，也不是画像前窗。
- **缓存需求核对**：按 `NilmDetector._profile_need_one()`，`need=pre×max_scale+dur_max+2×post×max_scale+10`。本轮 `max_scale=1`、`dur_max=1288`：200/3000 约 **7,498 cycles / 149.96 s**；600/3000 约 **7,898 cycles / 157.96 s**。配置 `window_cycles=3000`（60 s）小于需求，但本版本会自动按画像需求扩窗；不是两侧差别的直接来源。
- **本波形暂行建议**：若 14:48:10 确认不是目标启动，当前这次 A/B 结果支持优先试 **pre=600、post=3000**，它对该段宽缓变化未生成确认启动；不要把 600 当所有设备的固定值。理想前窗应覆盖足以稳定估计事件前基线的稳态时长，同时避开更早的其他负荷变点。保持其他设置和标签不变，进一步以同一原始 CSV 做 `pre=200/400/600` 对照，并增加每方向至少 3 条人工核验事件，再定最终值。
- **仅作敏感性推演，不是本轮实测部署建议**：把 `min_confidence` 从 0.30 提至 0.35 会过滤这条 0.3392 误报，同时保留本次两个 STOP 的 0.4993 / 0.6672；该结论只对这三条已记录事件成立，其他负荷 / 轻载真事件可能被误拒，需有标签的留出数据验证。

- **是否进入 REPORT.md（稳定结论）**：否（单份用户波形、自动定位且每方向仅 1 样本；属于个案取证，尚不足以形成通用最优前窗结论）。
- **遗留问题**：①确认 14:48:10.465 是否确为他负荷而非目标设备；②核对 `config_branch.json` 中 `bus-启动.csv` 是否为过期快照，并确认分路画像为何 `side=bus`；③提供原始 `bus-停止.csv` 或现场复跑记录后，才能固定其他参数做周期级 A/B；④每方向补足 ≥3 个已知动作，避免 σ 全靠经验下限。

## [2026-11-04] 专题：智能问答确认式受控工具执行与授权边界
- 类型：用户专题 / 验证专题
- 目标与假设：在既有固定文档 + 问答侧栏、本地 / 云端模型、RAG、SSE 与会话管理基础上，提供“自然语言操作意图 → 影响预览 → 用户确认 → 服务端重新授权 → 固定业务 API”闭环，并提供管理员工具开关、逐工具 allow-list 和审计。既有系统没有登录账号 / 角色体系；按用户授权决策，采用服务端独立操作员令牌和每工具 scope，不把页面入口显隐当授权。云端工具默认关闭，不实现任意命令、路径或 SQL 执行器。
- 方法 / 数据 / 参数：
  - `app/assistant_tools.py` 定义 8 项闭集工具及严格参数 schema；模型输出不可信，只能创建进程内 proposal。`app/assistant.py` 实现 operator token / scope、5 分钟 proposal TTL、侧别绑定、单次消费、高风险二次码、限流、JSONL 审计与 10 分钟临时 CSV 导出。`app/server.py` 在确认时重新检查操作员、scope、工具及云端开关、proposal TTL、侧别和二次码，再复用现有总线 / 分路业务 handler；聊天保留 `/api/assistant/chat`，分路走 `/api/branch/assistant/...`。
  - 前端新增令牌验证、proposal 影响 / 有效期 / 过期或已处理状态、取消和二次确认；新增 UI mock 行为验证确认请求携带操作员令牌与二次码。管理员界面支持全局 `tools_enabled`、逐工具 `enabled_tools`、`cloud_tools_enabled`、`tool_audit_enabled` 和审计查看。
  - 安全修正：无效 / 已撤销的可选令牌只让本轮没有工具 schema，仍允许只读问答；identity 端点照样拒绝该令牌。持久配置的 `enabled_tools` 若类型异常，改为空 allow-list（fail-closed），不再回退到所有注册工具；并保留工具总开关默认关闭。
  - 配套修正：画像目录仅在调用可用画像工具时扫描；按 `profile_branch1_...` / `profile_bus1_...` 文件名识别侧别；扩展云端对常见本地资料扩展名的引用拦截（不把该规则套用到完整内置 RAG 语料）。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无用户侧命令或真实数据实录；本节记录均为沙盒自动化验证。
- 结果 / 结论：
  - 隔离源码副本 `/tmp/nilm-calc-tool-test-191` 全量 `pytest -q`：**608 passed / 1 skipped / 1 warning**（134.16 s）；warning 是既有 Starlette/httpx `TestClient` deprecation。隔离副本排除了仓库 `tmp/` 和 `output/`，避免全量测试改写用户运行数据。
  - 原工作树定向 `.venv/bin/pytest tests/test_assistant.py -q`：**16 passed**；`tests/test_server.py -q`：**27 passed**（同类 deprecation warning）。`node tools/ui_assistant_check.cjs`：**PASS 50 checks**，覆盖 fixed sidebar / 文档 / SSE / 安全 Markdown / 会话 / 管理配置 / 导入与操作 proposal 确认。Python `py_compile`、`node --check app/static/app.js`、`node --check tools/ui_assistant_check.cjs`、`git diff --check` 均通过。
  - 回归覆盖：无效可选令牌只读问答及 identity 403；畸形 allow-list 不扩权；工具 scope 与管理员开关撤销、proposal 过期 / 侧别冲突 / 单次消费 / 二次确认；JSON 和 SSE proposal；画像 output 目录与侧别筛选；浏览器确认调用携带 operator token 和二次码。没有连接真实 Ollama/vLLM、云服务或用户浏览器，也没有声称现场验证通过。
  - 当前工作区的 `tmp/` 存在运行数据的修改 / 新增 / 删除状态；按用户约束保留原状并排除在本专题文件变更之外，不纳入本任务提交。
- 是否进入 REPORT.md（稳定结论）：否（本专题为工程实现与安全回归，没有形成 NILM 算法稳定结论）。
- 遗留问题：真实模型 function calling、云端 provider / Key、真实浏览器视觉 / 移动端、Windows / 生产网络与真实业务 API 操作仍需用户环境验收；无账号 / SSO 时审计只能关联 operator ID，不能证明自然人身份；`/api/chat` 别名未实现 / 未评估，现有兼容路径为 `/api/assistant/chat`；Starlette/httpx 弃用警告仍待依赖升级时处理。云端工具继续默认关闭。

## [2026-11-04] 专题：智能问答知识库正式手册与静态文件加载
- 类型：用户专题 / 文档与验证专题
- 目标与假设：交付软件设计、软件使用、软件部署说明、软件算法调参与验证、智能问答模块说明五份正式文档。已有 `docs/智能问答助手说明.md` 应核对并更新，不再另建重复文件；四份项目手册落盘为可重复生成的 Markdown，并由 Assistant 文档库直接读取。
- 方法 / 数据 / 参数：
  - 新增 `tools/generate_assistant_docs.py`：软件设计文档由 README 指定架构 / 配置章节、`REPORT.md` 稳定记录和设备画像算法方案组成；软件使用文档来自完整 README；软件部署说明由 README 快速开始 / 安装 / Web / 生产章节组成；调参与验证文档来自完整 `NILM_TUNING_GUIDE.md`。脚本只写四个指定 `docs/*.md`，提供 `--check`，不读写 `tmp/`。
  - `app/assistant_docs.py` 常规从四个静态 Markdown 加载内置知识库；静态文件缺失时保留旧源文档回退拼装。平台参数清单仍按 `AppConfig` 代码默认值、`configs/default.json`、`configs/branch.json` 动态生成，标注不代表当前运行值；`NILM_DATA_DICT.md` 与现有助手说明继续独立加载。
  - 更新 `docs/智能问答助手说明.md`、README 的助手知识源 / 生成说明 / 验证记录；新增回归确认静态文件存在时不会触发动态回退拼装。未处理第 183 轮旧指南清单，未修改算法实现或 `tmp/`。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无用户侧命令。本节命令均由 Agent 在沙盒执行；全量测试隔离目录为 `/tmp/nilm-calc-tool-test-192-final`，归档时排除了仓库 `tmp/`。
- 结果 / 结论：
  - 四份生成文档最终长度：软件设计 **42,677** 字符、软件使用 **216,251**、软件部署 **36,580**、算法调参与验证 **142,220**；生成器 `--check` 对四份均输出 `OK`。
  - `tests/test_assistant.py -q`：**17 passed**；最终隔离副本全量 `pytest -q`：**609 passed / 1 skipped / 1 warning**（131.13 s）。唯一 warning 是现有 Starlette/httpx `TestClient` 弃用提示。
  - `node tools/ui_assistant_check.cjs`：**PASS 50 checks**；覆盖固定文档 / 问答侧栏、内置文档、窄屏标签、builtin 检索、安全 Markdown、引用、会话、管理员配置、导入及受控操作员确认流程。
  - `python -m py_compile app/assistant_docs.py tools/generate_assistant_docs.py`、`node --check app/static/app.js`、`node --check tools/ui_assistant_check.cjs`、`git diff --check` 均通过。README 最终变化后重新生成使用手册、再次跑 `--check` 四项及助手定向测试，结果仍通过。
  - 内容口径保持来源边界：平台模板 / 代码默认不冒充用户当前运行值；部署手册保留原文中 Windows / 现场网络等待验证标记，不宣称用户环境验收完成。工作树原 `tmp/` 运行数据状态完整排除在测试和文件变更范围外。
- 是否进入 REPORT.md（稳定结论）：否（本专题为正式文档整理与知识库加载，不产生新的稳定算法结论）。
- 遗留问题：真实 Ollama / 云端模型、用户真实浏览器视觉、Windows / 现场网络与部署、真实现场数据均未在本专题验证；生成后的静态文档需在服务重启后由 AssistantService 读取。后续若上游 README / REPORT / 算法方案 / 调参手册更新，需运行 `python tools/generate_assistant_docs.py` 再提交生成文件。

## [2026-11-04] 专题：管理员令牌与受控工具现场操作说明
- 类型：用户专题 / 文档与验证专题
- 目标与假设：按用户要求，从实施工程师、交付工程师和现场运维视角，详细说明 `ELEC_TOOL_ASSISTANT_ADMIN_TOKEN` 的设置与服务重启，以及如何配置操作员凭证、scope 并通过 UI 开启受控工具。只更新助手模块说明文档，不改变现有授权和执行逻辑。
- 方法 / 数据 / 参数：核对 `app/assistant.py` 的管理员环境变量判定、操作员 token JSON 解析 / scope 校验 / 工具交集，`app/assistant_tools.py` 的闭集工具及 high-risk 标记，以及 `app/static/index.html` / `app/static/app.js` 的管理员与操作员 UI 字段。文档补充 Linux / macOS 当前终端、PowerShell、systemd `EnvironmentFile` 示例；以只读 `recordings.read` / `profiles.read` 为起步示例，并引用完整工具 / scope 表；说明 builtin、云端工具额外开关、提案预览 / 确认、过期和高风险二次确认。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无用户侧执行命令。本节命令为文档示例；Linux 片段在沙盒语法检查并执行环境 JSON 部分，没有启动服务。PowerShell / systemd 示例未在目标系统实跑。
- 结果 / 结论：
  - 更新 `docs/智能问答助手说明.md` §6.1–6.5：明确管理员口令与操作员令牌不同、环境变量必须进入实际服务进程并在修改后重启、管理 UI 全局开关 / allow-list / 云端独立开关、按角色分工的操作流程和故障排查。
  - 更正高风险工具说明：`set_profile_parameters`、`set_wiring_mode`、`load_latest_profile`、`clear_nilm_events` 需要服务端提供的 6 位二次确认码。保留 `clear_nilm_events` 仅清当前侧内存事件、不删磁盘 CSV / 不清缓存的边界。
  - `tests/test_assistant.py -q`：**18 passed**。文档 Linux 命令块 `bash -n` 通过；示例实际生成并解析了操作员 JSON，确认最小只读 scope；PowerShell 路径与环境变量名断言通过；四份生成文档 `--check` 全 `OK`；`git diff --check` 通过。
  - 泛化查询“如何部署软件”现在也会命中新增的助手环境配置说明；为保持回归语义稳定，将原部署手册检索断言收紧为“Linux 离线部署 安装”的具体问题。
  - 本轮没有修改 `app/` 执行代码；仓库 `tmp/` 状态未触碰、未暂存。
- 是否进入 REPORT.md（稳定结论）：否（部署与权限说明专题，不产生稳定算法结论）。
- 遗留问题：没有在用户的 Windows、systemd / Docker 或现场网络上实际设置变量和重启服务；需要部署方在目标系统按手册验证 secret 管理、网络访问控制、真实模型 tool/function calling 与审批流程。应用无账号 / SSO，操作员 ID 只是审计标签；不要向聊天、工单或 Git 提交真实令牌。

## [2026-11-04] 专题：管理员 / 操作员令牌生成说明跨文档同步与排障
- 类型：用户专题 / 文档与验证专题
- 目标与假设：按现场 PowerShell 生成并重启后台服务后的验证反馈，把管理员口令与操作员令牌的生成方法、服务环境注入边界、scope 格式和错误判读同步到 README 及相关内置手册。保留现有权限实现与安全边界，不改助手授权执行逻辑。
- 方法 / 数据 / 参数：
  - 核对 `app/assistant.py` 的 `_operator_token_records()` / `authenticate_operator()` / `public_config()` 与 `app/server.py` 的公开配置接口；确认 `operator_tokens_configured` 只表示至少有一条格式有效记录，未知 scope 会被过滤而非使令牌身份记录整体失效。
  - README §3.1 / §3.6 增加 Linux/macOS、Windows PowerShell 的 `secrets.token_urlsafe(32)` 生成示例，操作员最小 scope 使用纯文本 `recordings.read`、`profiles.read`；强调当前 shell 变量不会自动注入由 NSSM / 任务计划程序 / systemd / Docker 等另行启动的服务，且普通重启不应重新生成令牌。
  - 更新 `docs/智能问答助手说明.md` §6.1 / §6.3 / §6.5：加入秘密元数据检查、公开配置的无秘密验证、Markdown 链接 scope 误填说明，以及“令牌未匹配”与“身份通过但 scope / 工具条件不满足”的区别。`app/assistant_docs.py` 的部署手册选择器新增 README §3.6，随后重生成软件使用 / 部署手册；新增文档回归检查三份助手 / 使用 / 部署内容。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无用户侧命令或真实令牌实录；所有生成的随机值均仅用于沙盒验证、未输出到记录。本轮没有在 Windows PowerShell / Windows Service / NSSM / systemd 现场执行。
- 结果 / 结论：
  - `.venv/bin/pytest tests/test_assistant.py -q`：**18 passed**。
  - `.venv/bin/python tools/generate_assistant_docs.py --check`：软件设计、软件使用、软件部署、算法调参与验证四份均 `OK`；部署文档现包含 README §3.6。
  - README 与助手说明的 Linux token 构造代码块均 `bash -n` 通过；实际执行 shell→JSON 示例并只输出元数据，验证 token 长度 43、scope 精确为 `recordings.read` / `profiles.read`。
  - PowerShell 代码只做静态检查（venv 可执行路径、`&` 调用运算符、纯文本 scope），并未声称在 Windows 运行通过。`py_compile` 与 `git diff --check` 通过；全量 pytest 未运行。
  - 权限逻辑不变。文档明确：错误“操作员令牌无效或已撤销”指服务进程无匹配的已解析记录；scope 拼成 Markdown 链接时一般被过滤，可能表现为身份验证通过但没有可用工具。`Remove-Item Env:OPERATOR_TOKEN` 只删临时变量，不会删 JSON 环境变量中的令牌。
  - 仓库 `tmp/` 既有数据修改 / 删除 / 未跟踪文件未读取、未修改、未暂存或提交。
- 是否进入 REPORT.md（稳定结论）：否（工程文档同步；未产生稳定算法结论或现场服务验证结果）。
- 遗留问题：PowerShell 示例、Windows 服务管理器环境注入、真实 systemd / Docker secret 权限和现场模型工具调用都需部署方实测；`operator_tokens_configured=true` 不证明当前用户输入 token 匹配。遇后续环境反馈时只收集布尔值、ID、长度、scope 等不含秘密的诊断信息。

## [2026-11-04] 专题：智能问答本地模型候选列表与手动输入
- 类型：用户专题 / 验证专题
- 目标与假设：管理员配置中的本地模型名称既可从已配置的本地模型服务选择，也可手动输入任意模型标识；页面初始化后填充候选并提供刷新按钮，不改问答通道或云端模型字段，也不改变既有保存 / 聊天字段。
- 方法 / 数据 / 参数：
  - `app/assistant.py` 启动发现采用 daemon 线程，不阻塞 ASGI lifespan；模型发现只从经 `_validate_base_url(..., "local")` 校验的本地 URL 读取，`urllib` 使用空 `ProxyHandler`、单端点 5 s 超时、1 MB 响应上限，响应最多列出 200 个、每名最多 160 字符的模型标识。先请求 OpenAI-compatible `GET {local_base_url}/models`，没有可用候选时回退 Ollama `GET /api/tags`；解析 `data[].id`、`models[].name/model` 等常见结构。
  - `GET /api/assistant/local-models` 只返回内存缓存；`POST /api/assistant/local-models/refresh` 需 `X-Assistant-Admin-Token`，刷新 URL 仍受本地地址校验，可在保存前按当前输入地址试读。配置新 URL 后 UI 保存流程自动刷新。
  - 管理员表单只将 `assistant-local-model` 改为 `input[list] + datalist`；所有模型请求均由浏览器调用本应用相对 API。前端加载候选只重建 datalist、不写输入框；空列表清空候选但不改当前值，请求失败时保留已有候选与手填值。模型仍通过既有 `local_model` 配置保存，聊天侧无需额外参数。
  - 新增服务解析 / 无代理 / OpenAI 与 Ollama 回退 / 管理员鉴权 / 启动预取测试、API 缓存与刷新测试、HTML / JS 静态契约，以及 jsdom 对页面初始加载、手动刷新、空列表、失败和自定义模型保存的行为检查。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无用户侧命令或实录；全部验证由 Agent 在沙盒执行。未连接真实 Ollama、vLLM、LM Studio 或其他本地模型服务。
- 结果 / 结论：
  - `.venv/bin/pytest tests/test_assistant.py tests/test_server.py tests/test_web_ui.py -q`：**70 passed / 1 warning**（10.00 s）；唯一 warning 是既有 Starlette/httpx `TestClient` deprecation。
  - `node tools/ui_assistant_check.cjs`：**PASS 62 checks**，包括新增本地模型候选、刷新、任意手填与错误 / 空列表保值检查。
  - `node --check app/static/app.js`、`node --check tools/ui_assistant_check.cjs`、`.venv/bin/python -m py_compile app/assistant.py app/server.py tests/test_assistant.py tests/test_server.py tests/test_web_ui.py` 和本轮明确文件的 `git diff --check` 均通过。
  - 真实模型服务上的返回字段差异、服务鉴权策略、用户浏览器 datalist 外观 / 操作及现场部署网络均未实测；本专题不将沙盒结果表述为现场验收。
  - 仓库 `tmp/` 中既有运行数据修改 / 删除 / 未跟踪状态原样保留，不读取、不清理、不暂存、不提交。
- 是否进入 REPORT.md（稳定结论）：否（配置界面与服务端模型发现功能，不涉及稳定 NILM 算法结论）。
- 遗留问题：用户需在真实本地服务启动时验证自动候选加载、管理员刷新、空 / 错误响应后的手动填写与保存，并确认浏览器外观；若某个 OpenAI-compatible provider 使用不同模型目录路径或字段，再按其非敏感接口样例补适配。

## [2026-11-04] 专题：智能问答会话管理双栏重构与波形截图输入
- 类型：用户专题 / UI、接口与安全验证专题
- 目标与假设：按第 196 轮验收要求，将同页固定智能问答侧栏重排为左侧会话管理 + 右侧自适应聊天；把完整本地文档 / 参数目录、模型 / RAG 设置及管理员 / 操作员凭据收拢到“配置与附加知识库”；新增受限截图分析输入。会话继续仅保存在当前页面内存，不增加刷新后持久化。
- 方法 / 数据 / 参数：
  - 桌面左栏固定 260 px；按当前顺序将前 5 条显示为“最近会话”、其余为“历史会话”，标题搜索、时间、切换、拖动排序、右键 / 菜单重命名 / 清上下文 / 删除，标题单行省略。新建对话按钮在列表上方；窄屏可折叠会话栏。右栏含助手标题、builtin / local / cloud 选择、关闭按钮、用户 / AI 气泡、滚动消息、SSE Markdown、思考状态、停止生成、超时 / 连接错误提示；Enter 发送、Shift+Enter 换行。
  - 完整本地文档与平台参数目录放入同页配置详情区，并保持 `/api/assistant/documents` 全文加载、平台参数优先检索、本地 / 云端 RAG、管理员附加文本知识、现有本地模型候选发现、受控工具 scope / 服务端复核 / 用户确认机制。管理员口令、操作员令牌及其验证 UI 均在配置区；两类凭据仍分离，浏览器令牌仅页面内存。
  - 图片接受 PNG / JPEG / WebP；每张 ≤3 MiB、每轮最多 3 张、每轮合计 ≤5 MiB。前端支持文件选择、粘贴和拖放；服务端检查 MIME、Base64、文件签名、单图 / 合计上限，并在 JSON 解析前按 `Content-Length` 与实际流式读取字节数限制请求体 ≤7 MiB，超限返回 413。图片通过 OpenAI-compatible `image_url` data URI 仅随本轮 local / cloud 请求发送；builtin 不接受图片。后端仅验证传输格式 / 签名，不据此宣称完整图像解码或模型兼容。
  - 云端每次附图发送前由浏览器再次确认；明确告知图像不经过既有文本敏感词扫描，不能当作图像 DLP，提醒勿上传个人 / 涉密内容。图像不写助手知识库或持久目录；浏览器消息与会话刷新后清除。
  - README §3.6、变更记录及 `docs/智能问答助手说明.md` 同步更新；运行 `tools/generate_assistant_docs.py` 后更新软件使用 / 部署手册。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无用户侧执行命令；无真实截图 / 用户数据输入。
- 结果 / 结论：
  - `./.venv/bin/pytest tests/test_web_ui.py tests/test_assistant.py tests/test_server.py -q`：**72 passed / 1 warning**；唯一 warning 为现有 Starlette/httpx `TestClient` deprecation。
  - 隔离源码副本（在 `/tmp` 由跟踪源码及显式本轮补丁构建，未复制工作树未跟踪数据）全量 `pytest -q`：**617 passed / 1 skipped / 1 warning**，138.88 s；warning 同为 Starlette/httpx deprecation。
  - `node tools/ui_assistant_check.cjs`：**PASS 84 checks**，覆盖会话列表、菜单 / 拖拽、响应式折叠、配置区文档、SSE / 安全 Markdown、图像粘贴 / 拖放、本地图像请求、云端确认、受控操作提案确认。
  - `python tools/generate_assistant_docs.py --check`：软件设计 **42,713** 字符、软件使用 **221,857**、软件部署 **44,975**、算法调参与验证 **142,220**，全部 `OK`；定向 Python `py_compile`、`node --check app/static/app.js` / harness、明确文件 `git diff --check` 均通过。
  - 隔离 live preview `0.0.0.0:8001`：`/`、`/static/app.js`、`/static/style.css` 均 HTTP 200；配置 API 返回 assistant enabled / builtin。此为服务与静态资源 smoke check，不代表真实浏览器视觉验收。
  - 仓库工作树 `tmp/` 的既有用户运行数据未读取、清理、修改、暂存或提交；测试副本与提交文件均按明确路径控制。
- 是否进入 REPORT.md（稳定结论）：否（这是 UI / 传输接口实现专题，没有新的稳定电气算法结论）。
- 遗留问题：没有连接真实本地视觉模型或云端 provider，未确认具体 OpenAI-compatible 实现是否接受图片 data URI / `image_url` 形态及图片效果；未做目标浏览器、Windows、现场网络 / HTTPS 实测。云端图片无图像敏感扫描，不得将文本拦截说成图像 DLP；截图后续追问需要重新附图，历史会话不持久化。

## [2026-11-04] 专题：智能问答本地模型候选选择与鼠标滚轮修复
- 类型：用户专题 / UI 交互与回归验证专题
- 目标与决策：修复本地模型候选下拉操作异常及助手侧栏鼠标滚轮无法浏览的问题。候选列表改成明确可打开的原生 `<select>`，但保留独立可编辑模型名输入框；不改本地模型发现 API、管理员刷新授权、配置保存字段或 `tmp/`。
- 方法 / 实现：
  - `app/static/index.html` 增加 `#assistant-local-model-select`，候选选择后同步至 `#assistant-local-model`；手动输入列表外名称仍可保存。初始加载、手动刷新、空列表与失败路径都不覆盖输入值；既有 `GET /api/assistant/local-models` 与管理员鉴权 `POST /api/assistant/local-models/refresh` 保持不变。
  - 消息滚动静态检查定位到两处强制回底：SSE 每次消息更新时 `assistantRefreshMessage()` 无条件滚至 `scrollHeight`，且请求结束重绘同样无条件回底；同时消息区用了 `scroll-behavior:smooth`。现仅在用户原本距底部 ≤72 px 时自动跟随；请求结束按原位置重绘；消息区改为即时滚动。
  - 助手 fixed 面板新增受限 wheel 路由：消息 / 会话 / 设置 / 文档等已滚动区域优先原生滚动；嵌套内容到边界时继续滚动父级；标题或空白处将滚轮送至对应消息区 / 会话列表 / 设置主体。显式设置纵向 overflow、`min-height:0`、细滚动条与面板内 overscroll 行为。
  - 扩展 `tests/test_web_ui.py` 与 `tools/ui_assistant_check.cjs`：覆盖候选选择与手填同步、刷新 / 空列表不丢输入、候选值走原配置保存字段、流式更新 / 完成重绘保持阅读位置、底部跟随、标题空白区和嵌套设置文档区滚轮传递。
- 用户执行命令：无；未连接真实本地模型服务，未进行用户目标浏览器手动验收。
- 结果 / 结论：
  - 定向 `.venv/bin/pytest tests/test_assistant.py tests/test_server.py tests/test_web_ui.py -q`：**73 passed / 1 warning**（10.24 s）；唯一 warning 是既有 Starlette/httpx `TestClient` 弃用提示。
  - 隔离源码副本全量 pytest（`/tmp/nilm-calc-tool-test-197-final-q53aFy`，由 `git archive HEAD` 加本轮明确文件构建，不复制仓库 `tmp/`）：**618 passed / 1 skipped / 1 warning**（137.50 s）；warning 同为既有弃用提示。
  - `node tools/ui_assistant_check.cjs`：**PASS 99 checks**；`node --check app/static/app.js`、`node --check tools/ui_assistant_check.cjs`、`.venv/bin/python -m py_compile tests/test_web_ui.py` 与明确文件 `git diff --check` 通过。实现提交 `cb23f2d` 已创建。
  - 现有 live preview `0.0.0.0:8001` 的首页、`/static/app.js`、`/static/style.css` 均 HTTP 200，且包含本轮 UI 标记。此项是服务 / 静态资源 smoke check，不等于浏览器交互验收。
  - jsdom 覆盖事件同步与滚动路由，但不模拟浏览器原生 `<select>` 弹出层、真实鼠标滚轮惯性或目标浏览器布局；不得据此宣称用户浏览器已验收。仓库 `tmp/` 未读取、未修改、未暂存或提交。
- 是否进入 REPORT.md（稳定结论）：否（纯 UI / 前端交互修复，不涉及稳定 NILM 算法结论）。
- 遗留问题：请在目标浏览器确认候选可点击展开、选中后可保存、列表外模型名仍可手填；在生成中从底部滚到较早消息后确认不跳回，并在会话栏、配置 / 文档区及空白处验证滚轮。真实 Ollama / OpenAI-compatible 服务、浏览器外观与现场网络仍待用户环境实测。

## [2026-11-04] 专题：智能问答具体模型选择、多云端 API 档案与滚动复验
- 类型：用户专题 / 功能实现与 UI 回归验证专题
- 目标与假设：除复核助手滚动容器、流式消息阅读位置、嵌套滚动与空白区 wheel 路由外，新增问答头部的具体模型选择和云端 API 动态配置。实施假设为：本地显示发现 / 管理员配置的模型；cloud 保留旧单一云端字段作为默认档案，额外最多 10 个命名档案，每档一个 OpenAI-compatible HTTPS endpoint、模型 ID 与 API Key；模型切换创建独立会话；API Key 仅服务进程内存保存、不写盘、不回传；档案写操作受管理员口令保护。
- 方法 / 实现：
  - `AssistantService` 新增 `cloud_api_profiles` 普通配置字段；校验 profile ID 唯一且不含保留值、显示名 / endpoint / model ID 长度和控制字符、云端地址 HTTPS 规则、最多 10 档。额外 profile API Key 独立存于 `_cloud_profile_secrets` 内存映射，配置保存只写 metadata；公开配置仅返回 `api_key_set` 布尔状态。管理员可增加、更新、清密钥、删除；删档同步移除该 ID 的内存密钥，重启后需要重新输入。
  - 聊天服务端对 local 请求校验并使用 `model_name`，仍只请求管理员配置的 local endpoint；cloud 请求只接受服务端档案 ID，禁止客户端覆盖 `model_name`、endpoint 或 Key。档案 ID 命中服务端 metadata 后才路由 endpoint / model / Key；legacy default 继续使用 `cloud_base_url` / `cloud_model` / `cloud_api_key` 与旧环境变量。
  - 问答头部增加独立“问答后端 / 具体模型”选择器：local 候选合并服务发现列表与默认模型，cloud 显示默认和命名档案；具体模型变化时有消息的对话会确认并新建会话，原会话保留其 model / profile。设置区添加 profile 卡片、密钥状态、增改删和清 key；密钥使用 password 输入框并仅在管理员 PUT 中独立提交。
  - 扩展 `tests/test_assistant.py` / `tests/test_server.py`，覆盖 profile 校验、管理员鉴权、默认配置兼容、密钥不回传 / 不落盘 / 重启失效、清除和删档、local model override、cloud ID 路由及不接受客户端 cloud model override。扩展 `tests/test_web_ui.py` 与 `tools/ui_assistant_check.cjs`，覆盖两个选择器、独立会话、动态加档、API Key 单独提交、聊天 payload 只带选中模型 / 档案 ID及滚动回归。
  - 更新 README §3.6、v0.99.40 变更记录与 `docs/智能问答助手说明.md`，用 `.venv/bin/python tools/generate_assistant_docs.py` 同步使用 / 部署手册；未新增同类报告文件。
- 用户执行命令：无；没有连接真实本地模型或云端 API；没有可用 Chromium / Firefox / Playwright / Puppeteer，因此本轮仍无法进行真实浏览器视觉与原生鼠标滚轮验收。
- 结果 / 结论：
  - `.venv/bin/pytest tests/test_assistant.py tests/test_server.py tests/test_web_ui.py -q`：**75 passed / 1 warning**（约 10.2 s）；唯一 warning 为既有 Starlette/httpx `TestClient` 弃用提示。
  - 当前源码全量 `.venv/bin/pytest -q`：**620 passed / 1 skipped / 1 warning**（140.23 s）；同一既有 deprecation warning。
  - `node tools/ui_assistant_check.cjs`：**PASS 121 checks**；包含消息流式期间上翻 / 底部跟随、标题 / 空白区与嵌套滚动，以及 local / cloud 具体模型切换、旧会话保留、动态云端档案与密钥单独提交。
  - `node --check app/static/app.js`、harness `node --check`、定向 `py_compile`、`git diff --check` 均通过；生成的四份手册 `--check` 均 `OK`（软件设计 42,713 字、软件使用 223,483 字、软件部署 45,589 字、调参验证 142,220 字）。
  - 重启后的 live preview `0.0.0.0:8001` 中 `/`、`/static/app.js`、`/static/style.css` 均 HTTP 200 并含新 UI / 档案标记。此为服务与资源 smoke check，不是浏览器滚轮 / 布局实测。
  - 本轮未连接真实模型、provider、目标浏览器、Windows 或现场网络；`tmp/` 用户数据未读取、修改、暂存或提交。
- 是否进入 REPORT.md（稳定结论）：否（配置与 UI 实现及滚动回归，不产生新的稳定 NILM 算法结论）。
- 遗留问题：目标浏览器需手测原生选择器、响应式 header 两个下拉框、消息滚轮和嵌套滚动边界；真实 Ollama / cloud provider 需验证具体 model ID 与 endpoint 的兼容性、权限与网络策略。额外 profile Key 在服务重启后刻意不恢复，管理员需重新配置；云端请求已有隐私 / 敏感内容边界仍适用。

## [2026-11-04] 专题：智能问答助手受限视口整体滚动条
- 类型：用户专题 / UI 交互与回归验证专题
- 目标与假设：用户要求在助手界面不能同时显示全部界面内容时增加滚动条，确保短屏 / 窄屏下头部、会话、问答、输入和设置入口仍可访问。保留既有同页固定侧栏及消息、会话、设置各自的内层滚动。
- 方法 / 实现：
  - 将 `.assistant-shell` 设为外层按需纵向滚动容器，设置可辨认的滚动条轨道 / 滑块，并加 `tabindex=0` 与可访问标签，让滚动区域支持键盘聚焦。
  - 主工作区设置 420px 最小高度、窄屏 480px、极窄屏 540px，避免 flex 在短视口中把控制项压缩或裁切；工作区和问答列允许溢出传递给 shell。
  - 内层消息 / 会话 / 设置滚动区仍优先处理滚轮；到达边界后将滚轮转给 shell。设置覆盖层打开时锁住被覆盖主界面的外层滚动，设置关闭时解除，并在打开设置或面板时重置外层滚动位置。
  - `tests/test_web_ui.py` 增加外层 overflow、滚动条对比度、最小高度、窄屏策略和键盘可达静态契约；`tools/ui_assistant_check.cjs` 以模拟滚动尺寸回归消息 / 设置边界到外层的传递及设置覆盖层锁定。
  - README 与助手使用说明更新为 v0.99.41；四份生成手册重新生成并以 `--check` 验证。
- 用户执行命令：无；本环境未提供可用的真实浏览器渲染 / 滚动条视觉验收。
- 结果 / 结论：
  - 定向 `.venv/bin/pytest tests/test_assistant.py tests/test_server.py tests/test_web_ui.py -q`：**75 passed / 1 warning**（12.39 s）；warning 为既有 Starlette/httpx `TestClient` deprecation。
  - 全量 `.venv/bin/pytest -q`：**620 passed / 1 skipped / 1 warning**（149.72 s）；同一既有弃用 warning。
  - `node tools/ui_assistant_check.cjs`：**PASS 133 checks**；`node --check app/static/app.js`、`node --check tools/ui_assistant_check.cjs`、定向 Python `py_compile` 通过。
  - `.venv/bin/python tools/generate_assistant_docs.py --check` 四份手册全 `OK`（设计 42,713、使用 224,310、部署 45,672、调参验证 142,220 字符）；`git diff --check` 通过。
  - live preview `/`、`/static/app.js`、`/static/style.css` 均 HTTP 200 且含本轮滚动标记；这是服务 / 静态资源 smoke check，不代表真实浏览器布局或原生滚动条验收。
- 是否进入 REPORT.md（稳定结论）：否（助手界面布局与滚动行为，不涉及稳定 NILM 算法结论）。
- 遗留问题：需用户在目标浏览器用较矮窗口、窄屏、消息 / 会话列表及长设置文档实测实际滚动条显示、触控 / 鼠标滚轮与键盘访问；jsdom 不能验证浏览器原生滚动条外观。`tmp/` 用户数据不读取、不修改、不暂存或提交。

## [2026-11-04] 专题：智能问答“配置与附加知识库”溢出滚动条
- 类型：用户专题 / UI 可访问性与滚动回归
- 目标与假设：用户要求当助手“配置与附加知识库”界面内容超出可用窗口高度时出现滚动条，以便访问完整配置和附加知识。现有 `.assistant-settings-body` 已处理纵向 overflow，但轨道透明、滑块过细且不够醒目；本轮保留该滚动容器和嵌套文档滚动，增强滚动条可见性，并提供键盘可达标记，不改变模型 / API 配置行为。
- 方法 / 实现：
  - `.assistant-settings-body` 使用 `scrollbar-width:auto`、有对比度的 thumb / track 颜色与稳定滚动条槽；为 WebKit 设置 12px 滚动条宽度、清晰轨道 / 滑块及 hover 样式。仍用 `overflow-y:auto`，仅在内容超出覆盖层可用高度时出现滚动条。
  - 设置内容区增加 `role="region"`、中文 `aria-label` 与 `tabindex="0"`，可通过键盘聚焦和滚动；固定标题与关闭按钮仍在已有 sticky header 内，长文档内部滚动及设置外层滚动锁定逻辑保持不变。
  - `tests/test_web_ui.py` 和 jsdom harness 增加滚动容器、scrollbar 颜色 / WebKit 轨道和键盘 region 的契约断言；既有 harness 继续覆盖设置正文、文档内层到边界时的滚轮路由。
  - README 更新到 v0.99.42，助手说明增加设置区滚动说明；重新生成软件使用 / 部署等手册。
- 用户执行命令：无；未提供真实浏览器自动化 / 视觉验收。
- 结果 / 结论：
  - 定向 `.venv/bin/pytest tests/test_assistant.py tests/test_server.py tests/test_web_ui.py -q`：**75 passed / 1 warning**（13.07 s）；既有 Starlette/httpx `TestClient` deprecation。
  - 全量 `.venv/bin/pytest -q`：**620 passed / 1 skipped / 1 warning**（151.46 s）；同一既有弃用 warning。
  - `node tools/ui_assistant_check.cjs`：**PASS 137 checks**；app.js / harness `node --check`、`tests/test_web_ui.py` `py_compile` 通过。
  - 四份手册 `tools/generate_assistant_docs.py --check` 全 `OK`（设计 42,713、使用 225,574、部署 45,735、调参验证 142,220 字符）；排除 `tmp/` 的 `git diff --check` 通过。
  - 当前 live preview 的 `/` 与 `/static/style.css` 均 HTTP 200，且包含设置区新标记；这是服务 / 资源 smoke check，不代表浏览器原生滚动条视觉或键盘验收。
- 是否进入 REPORT.md（稳定结论）：否（界面可达性修复，不涉及稳定 NILM 算法结论）。
- 遗留问题：需用户在目标浏览器缩小助手窗口高度、打开长设置页和文档列表，确认可见滚动条样式、滚轮及键盘访问；系统级 overlay scrollbar 策略可能影响常驻显示。`tmp/` 不读取、不修改、不暂存、不提交。

## [2026-11-04] 专题：配置与附加知识库展开后的滚动条复修
- 类型：用户复测反馈 / UI 根因复核与滚动回归
- 目标与根因：用户反馈展开“浏览本地帮助文档与完整平台参数清单”后仍有内容被遮挡且不显示滚动条。代码检查发现 v0.99.42 的 scrollport / scrollbar 样式位于内层 `.assistant-settings-body`，固定定位的 `.assistant-settings[open]` 本身仍 `overflow:hidden`；滚动容器层级与完整设置覆盖层不一致。将滚动端点移至设置覆盖层本身，不改模型 / API 配置功能。
- 方法 / 实现：
  - `.assistant-settings[open]` 改为固定大小的 block scrollport，使用 `overflow-y:scroll` 强制显示滚动槽，设置 Firefox `scrollbar-width/color` 及 WebKit 12px thumb / track 样式；即使设置内容适配窗口，也保留可发现的滚动条。
  - `.assistant-settings-body` 改回普通内容流，避免重复的双层设置滚动；设置标题仍用 sticky 定位于滚动覆盖层，关闭按钮保持可见。将 `tabindex="0"` 和清晰焦点指示移到真正滚动的 `<details id="assistant-settings">` 上。
  - wheel 路由把打开的 `.assistant-settings[open]` 作为滚动节点；文档正文 / 目录先内部滚动，到边界后滚动完整设置层；设置层到边界仍阻止底层助手 shell 移动。
  - 更新 Python 静态契约与 jsdom harness，验证滚动样式和键盘焦点，并把模拟滚动尺寸放到实际 settings overlay；README / 助手说明更新到 v0.99.43，重新生成软件使用 / 部署手册。
- 用户执行命令：无；用户报告的是实际展开后的界面复测结果。本环境没有真实浏览器视觉自动化工具。
- 结果 / 结论：
  - 定向 `.venv/bin/pytest tests/test_assistant.py tests/test_server.py tests/test_web_ui.py -q`：**75 passed / 1 warning**（13.56 s）。
  - 全量 `.venv/bin/pytest -q`：**620 passed / 1 skipped / 1 warning**（150.46 s）。两组唯一 warning 都是既有 Starlette/httpx `TestClient` deprecation。
  - `node tools/ui_assistant_check.cjs`：**PASS 138 checks**；app.js / harness `node --check` 与测试文件 `py_compile` 通过。
  - 四份生成手册 `--check`、`git diff --check` 通过；live preview `/`、`/static/style.css`、`/static/app.js` 均 HTTP 200 且含新的设置 overlay scrollbar 标记。HTTP/jsdom 不等于浏览器视觉验收。
- 是否进入 REPORT.md（稳定结论）：否（UI 滚动行为修正，不涉及 NILM 算法结论）。
- 遗留问题：请用户再次展开本地文档 / 完整参数详情，确认设置 overlay 滚动条可见、从文档内层滚动到整层、关闭按钮始终可达；目标浏览器 / OS 的 scrollbar 自隐藏行为尚未实测。`tmp/` 未读取、修改、暂存或提交。

## [2026-11-04] 专题：展开帮助文档后的设置独立滚动区复修
- 类型：用户复测反馈 / UI 根因复核与回归验证专题
- 目标与假设：用户指出第 201 轮后，展开“浏览本地帮助文档与完整平台参数清单”仍看不到滚动条、后续设置不可达。前两次方案分别把 scrollbar 放在 `.assistant-settings-body` 与 `<details>` overlay 上均未通过实际复验。本轮假设滚动端点需要成为设置 overlay 内的普通、边界尺寸明确的 block viewport，而不是依赖 details / flex 自动计算。
- 方法 / 实现：
  - `.assistant-settings[open]` 继续负责固定 overlay 定位和 `overflow:hidden` 裁剪；新增普通 `#assistant-settings-scroll.assistant-settings-scroll`，直接包住全部配置 / 文档内容，使用 `position:absolute; inset:0; overflow-x:hidden; overflow-y:scroll`，设置 Firefox / WebKit 高对比 scrollbar、14px WebKit track/thumb、`scrollbar-gutter:stable` 与 `overscroll-behavior-y:contain`。
  - 键盘 region / `tabindex="0"` 与 focus ring 放到真正滚动的 wrapper；关闭入口仍在 sticky header。窄屏时外层 inset 为 5px、内部 padding 7px。
  - `assistantHandlePanelWheel()` 的滚动节点与 fallback target 都改为 `#assistant-settings-scroll`：文档列表 / 正文可滚时先保留给内层，到达边界后转交设置 viewport；设置 viewport 到边界时阻止继续滚动被遮挡的助手 shell。
  - 扩展 Python CSS / HTML / JS 契约与 jsdom harness：明确检查独立 wrapper 有绝对定位和 inset、全部设置及完整文档处于该节点、其高对比 scrollbar / 键盘标记存在；模拟展开本地文档、正文未到底时内层优先、正文到边界后设置区接管、正文无溢出时设置区继续滚动，以及设置底部不移动背景。
  - README 升为 v0.99.44、修订 v0.99.43 历史描述以记录用户复验未通过；同步更新 `docs/智能问答助手说明.md`，重生成四份项目手册。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无用户命令；以下均由 Agent 在沙盒执行，实录为本会话工具输出，无用户侧日志路径。全量测试在临时隔离源码副本 `/tmp/nilm-calc-tool-test-202-gWiq1B` 执行，副本已在完成后清理；由 `git archive HEAD` 与排除 `tmp/` 的显式工作区 patch 构建，不读取仓库 `tmp/`。
- 结果 / 结论：
  - `.venv/bin/python -m pytest -o addopts='' tests/test_web_ui.py -q`：**23 passed**（0.22 s）。
  - 隔离副本 `/home/user/nilm_calc_tool/.venv/bin/python -m pytest -o addopts='' -q`：**620 passed / 1 skipped / 1 warning**（155.29 s）；唯一 warning 为既有 Starlette/httpx `TestClient` 弃用提醒。
  - `node tools/ui_assistant_check.cjs`：**PASS 142 checks**；`node --check app/static/app.js`、`node --check tools/ui_assistant_check.cjs` 和 `.venv/bin/python -m py_compile tests/test_web_ui.py` 通过。
  - `.venv/bin/python tools/generate_assistant_docs.py --check` 四份均 `OK`：设计 **42,713**、使用 **226,846**、部署 **45,973**、算法调参与验证 **142,220** 字符；明确文件 `git diff --check` 通过。
  - 这些是 Python 测试、静态 CSS / HTML 契约及 jsdom 行为模拟；不代表真实浏览器 layout、原生 scrollbar 外观或键盘 / 鼠标现场验收。
- 是否进入 REPORT.md（稳定结论）：否（属于 UI 滚动行为修复，没有新的 NILM 算法或稳定工程结论）。
- 遗留问题：请用户在实际目标浏览器重新展开帮助文档 / 参数清单，确认滚动条可见、滚轮可从文档内层传到后续设置、关闭按钮可达，并可用 Tab 聚焦设置区；窄屏及系统 overlay scrollbar 是否自动淡出仍待实测。真实浏览器未提供；仓库 `tmp/` 未读取、修改、暂存或提交。

## [2026-11-04] 专题：智能问答助手多界面滚动问题代码复审
- 类型：用户专题 / UI 滚动与可达性代码审计
- 目标与假设：重新检查智能问答助手几个界面，确认是否仍有因 scrollbar 未显示 / 嵌套滚动链断开，造成后续内容无法向下访问的问题。审计区分“代码允许滚动”与“目标浏览器常驻显示 scrollbar”，不能以静态 CSS 或 jsdom 代替现场视觉验收。
- 方法 / 覆盖范围：
  - 对照 `app/static/style.css`、`index.html`、`app.js` 中 `.assistant-shell`、会话列表、消息、设置 wrapper、本地文档目录 / 正文、图片预览、审计列表与 Markdown / proposal / audit `<pre>`、表格等区域的 overflow、最大 / 最小高度、flex 约束、父级裁剪和 wheel 处理。
  - 检查嵌套内容到边界后的路由：助手 wheel handler 对文档列表 / 正文、设置 wrapper、审计、图片预览、会话、消息做显式处理；在设置 / 消息 / shell 父级之间转交。代码块和表格等未逐一列入 handler 的普通嵌套节点由浏览器原生 scroll chaining 处理；静态 / jsdom 不能模拟其原生滚动。
  - 搜索浏览器可执行文件 / Playwright、Puppeteer、Selenium 依赖；环境只有 jsdom，无可用 Chromium / Firefox / Playwright / Puppeteer。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无用户命令；实际浏览器现场操作待用户执行并回报浏览器、OS、窗口尺寸和复现步骤。
- 结果 / 结论：
  - **代码层未发现明确的内容不可滚动断点**：外层 `.assistant-shell` 有有限视口高度、`overflow-y:auto` 和 shell 兜底；会话 / 消息区为 flex 子项且 `min-height:0` 并启用纵向滚动；设置 overlay 内 `.assistant-settings-scroll` 为 `position:absolute; inset:0; overflow-y:scroll`，全部设置 / 本地文档均位于其内；目录 `max-height:190px`、正文 `min-height:190px; max-height:50vh` 且两轴 `overflow:auto`；审计列表、待发截图预览、受限高度代码 / 审计 / 提案块也有相应 overflow。
  - **仍存在可发现性差异，不等于不可滚**：会话、消息、文档列表 / 正文部分使用 `scrollbar-width:thin` 与透明轨道；审计、预览及一些 Markdown 内层使用浏览器默认 scrollbar。OS / 浏览器的 overlay scrollbar 可能在闲置时淡出，因此用户可能暂时看不到滚动提示；鼠标 / 触控滚动仍可触发内容滚动。设置 wrapper 与外层 shell 的颜色 / WebKit scrollbar 样式更明确。
  - `.venv/bin/python -m pytest -o addopts='' tests/test_web_ui.py -q`：**23 passed**；`node tools/ui_assistant_check.cjs`：**PASS 142 checks**；app.js 与 harness `node --check` 通过；本轮仅为代码审计，未修改助手源代码。
  - 上述自动化只证明当前静态契约与模拟行为；本环境没有原生浏览器布局 / scrollbar 工具，故不声称目标浏览器视觉、原生 wheel / 触屏或窄屏现场验收通过。
- 是否进入 REPORT.md（稳定结论）：否（前端代码审计，没有新的稳定 NILM 算法结论）。
- 遗留问题：用户需在目标浏览器依次检查长会话、消息、帮助文档 / 参数、审计区、短视口和窄屏的实际滚动条与 wheel / 触控滚动，并确认内层到边界后父级接管、设置后续内容可达。若 bar 闲置自动隐藏，应区分系统 overlay 策略与真正不可滚动；若仍复现，提供浏览器 / OS / 视口与复现步骤继续定位。`tmp/` 严格未读、未改、未暂存、未提交。

## [2026-11-04] 专题：智能问答助手会话管理侧栏可收起
- 类型：用户专题 / UI 功能实现与回归验证
- 目标与假设：用户要求增加智能问答助手左侧会话管理面板收起功能。桌面应可从问答标题栏收起 / 恢复左栏，收起后问答区应占满可用宽度；窄屏保留现有抽屉式会话栏。
- 方法 / 实现：
  - 将现有 `#assistant-session-toggle` 从窄屏专用入口提升为所有尺寸可用的按钮。桌面默认显示会话栏，窄屏在打开助手时默认收起；点击后用 `sessions-collapsed` 状态隐藏 / 显示会话 pane。
  - 桌面收起时工作区网格改为单列 `minmax(0,1fr)`，问答区占满侧栏；恢复时沿用原桌面 / 中等屏幕双栏尺寸。窄屏继续使用浮层式会话抽屉，不改变既有覆盖层交互。
  - 按状态更新按钮可见文字、`title`、`aria-label` 与 `aria-expanded`；`aria-controls` 仍指向会话面板。折叠状态只存在于当前页面，不写入 localStorage / 配置，也不改对话状态。
  - 扩展 `tests/test_web_ui.py` 样式 / HTML / JS 契约及 `tools/ui_assistant_check.cjs` 行为验证，覆盖桌面默认展开、收起、恢复，窄屏默认折叠、展开、再折叠；README §3.6 和 `docs/智能问答助手说明.md` 加入操作说明，并重新生成四份使用 / 部署知识库手册。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无；目标浏览器现场验收待用户执行。
- 结果 / 结论：
  - `.venv/bin/python -m pytest -o addopts='' tests/test_assistant.py tests/test_web_ui.py -q`：**46 passed**。
  - `node tools/ui_assistant_check.cjs`：**PASS 150 checks**；包含桌面 / 窄屏侧栏状态切换和 `aria-expanded` / 名称同步。
  - `node --check app/static/app.js`、`node --check tools/ui_assistant_check.cjs`、`.venv/bin/python -m py_compile tests/test_web_ui.py`、`git diff --check` 通过。
  - `.venv/bin/python tools/generate_assistant_docs.py --check` 四份手册全部 `OK`：设计 **42,721**、使用 **227,563**、部署 **46,072**、算法调参与验证 **142,220** 字符。
  - 本轮没有可用目标浏览器自动化；jsdom 测试验证行为状态，不证明真实桌面 / 窄屏视觉或实际键盘 / 屏幕阅读器验收。
- 是否进入 REPORT.md（稳定结论）：否（智能问答 UI 交互，不涉及 NILM 算法结论）。
- 遗留问题：请用户在目标浏览器桌面和窄屏检查标题栏按钮位置、收起后的问答宽度、恢复后的双栏宽度及 Tab / Enter 可操作性；如有异常请回报浏览器 / OS / 视口尺寸。仓库 `tmp/` 未读取、修改、暂存或提交。

## [2026-11-04] 专题：智能问答助手悬浮入口、会话标题与模型选择布局
- 类型：用户专题 / 前端交互功能实现与回归验证
- 目标与假设：落实三项界面调整：助手窗口打开时隐藏悬浮球、关闭后恢复；会话侧栏标题显示“智能问答助手”，右侧问答区按当前会话显示标题，新会话在正式问答前不显示标题；问答后端与具体模型下拉移至右侧问答区底部、发送按钮左侧。保持现有 enabled / `visible_views` 入口权限、模型路由、会话隔离及工具授权逻辑。
- 方法 / 实现：
  - 新增共享的 `assistantLauncherEnabledForView()` 判定；助手面板打开时将 launcher 置 `hidden`，关闭后按既有配置 / 当前页面权限恢复，并同步 `aria-expanded`。Escape 逐层关闭设置或窄屏会话抽屉，助手真正关闭后悬浮入口恢复。
  - 左侧面板标题改为“智能问答助手”。右侧 `#assistant-title` 初始隐藏，仅当当前会话同时有非空用户问题和非空助手回答 / 操作提案时显示会话名；新建、尚无回答、清空上下文时隐藏。会话切换、重命名及流式回答更新都会刷新标题。
  - 将问答后端、具体模型及发送按钮置于同一底部控制组，两个选择器紧邻发送按钮左侧；保留原控件 ID、变更处理、模型配置与权限行为，并为窄屏 / 极窄屏增加可换行布局。
  - 扩展 `tests/test_web_ui.py` HTML / DOM 契约与 `tools/ui_assistant_check.cjs`，覆盖悬浮球打开 / 关闭 / Escape / 禁用状态、标题更新 / 空标题 / 会话切换 / 重命名 / 清空、选择器位于标题栏之外并排在发送按钮左侧。同步 README、助手说明并由 README 重生成四份手册。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无用户侧命令；验证由 Agent 在沙盒执行，命令与输出见下列清单。本节没有用户环境实录路径。
- 结果 / 结论：
  - `.venv/bin/python -m pytest -o addopts='' tests/test_assistant.py tests/test_web_ui.py -q`：**46 passed**。
  - `node tools/ui_assistant_check.cjs`：**PASS 172 checks**，覆盖本轮三个界面要求及既有助手主要交互。
  - `node --check app/static/app.js`、`node --check tools/ui_assistant_check.cjs`、`.venv/bin/python -m py_compile tests/test_web_ui.py` 通过。
  - `.venv/bin/python tools/generate_assistant_docs.py --check`：四份均 `OK`（设计 42,721、使用 228,527、部署 46,241、算法调参与验证 142,220 字符）。本轮明确文件范围的 `git diff --check` 通过。
  - 未运行全量 pytest；本环境未做目标浏览器视觉、键盘或屏幕阅读器验收。jsdom 与静态契约不能替代真实浏览器验证。
- 是否进入 REPORT.md（稳定结论）：否（助手 UI 交互改动，不涉及 NILM 算法稳定结论）。
- 遗留问题：请用户在目标浏览器验证助手开 / 关时悬浮球显隐、完成 / 未完成会话标题、桌面 / 窄屏底部模型选择器及发送按钮的实际视觉 / 键盘操作。`tmp/` 用户运行数据未读取、修改、暂存或提交。

## [2026-11-04] 专题：智能问答助手悬浮球拖动与底部控制区精简
- 类型：用户专题 / 前端交互功能实现与回归验证
- 目标与假设：按用户四项要求实现：悬浮球能在助手允许显示的页面上拖动；右侧 composer 移除“问答后端”单轮下拉与“具体模型”可见标题；“添加截图”按钮改名为“附件”；整理底部控件。模型路由与安全授权仍由配置、当前会话和服务端负责。
- 方法 / 实现：
  - 为悬浮按钮加入 Pointer Events 拖动；鼠标 / 触屏均可操作，5px 移动阈值区分点击与拖动，坐标夹在当前视口内，`resize` 时在按钮可见后重夹限；拖动后抑制合成 click，避免误打开助手。继续使用原生 `<button>`，轻点 / 键盘激活逻辑不变。位置只在当前页面运行期间保留，不写入 localStorage。
  - 删除 composer 内 `assistant-model-type` 下拉及其逐会话切换处理。默认后端继续由“配置与附加知识库”设置的 `assistant-default-backend` 管理；保存后新会话用配置默认值，已有会话仍保留 `conv.backend` / 具体模型。`assistantVerifyOperator`、隐私提示、聊天 payload 改从当前会话 / 设置默认后端取值；设置变更导致空会话后端变化时，使用新路由重新验证现有操作员令牌；API 与服务端权限校验不变。
  - 具体模型 `<select>` 保留，移除可见 `<label>具体模型</label>`；保留 aria-label。在 builtin 会话隐藏该选择器，在 local / cloud 会话显示。重新整理 select + 发送按钮 flex 组和窄屏规则。
  - 将“添加截图”可见文案与 title 改为“附件”，增加清晰 aria-label“添加附件”；更新 README、助手说明与由 README 生成的手册。
  - 扩展 `tests/test_web_ui.py` 与 `tools/ui_assistant_check.cjs`，覆盖无后端下拉 / 无可见标题、附件标签、默认后端对新旧会话的影响、模型选择器显隐 / 无障碍名称、浮球拖动坐标、边界夹限、拖动不误开及视口缩小后的恢复夹限。
- 用户执行命令（含实录路径；本节无用户命令则注明）：无用户侧命令；验证由 Agent 在沙盒执行，目标浏览器操作尚待用户实测。本节无用户环境实录路径。
- 结果 / 结论：
  - `.venv/bin/python -m pytest -o addopts='' tests/test_assistant.py tests/test_web_ui.py -q`：**46 passed**（6.14 s）。
  - `node tools/ui_assistant_check.cjs`：**PASS 188 checks**；覆盖悬浮球拖动 / 夹限 / click 抑制、控件移除 / 标签与附件文案、默认后端及旧会话隔离、默认后端变更后重新验证操作员令牌和既有助手交互。
  - `node --check app/static/app.js`、`node --check tools/ui_assistant_check.cjs` 与 `.venv/bin/python -m py_compile tests/test_web_ui.py` 均通过。
  - `.venv/bin/python tools/generate_assistant_docs.py --check`：四份均 `OK`（设计 42,721、使用 229,549、部署 46,426、算法调参与验证 142,220 字符）。明确文件范围 `git diff --check` 通过。
  - 未运行全量 pytest；未在真实浏览器验收浮球拖动手感、触屏手势、底部桌面 / 窄屏视觉或原生键盘操作；jsdom 不能代替现场浏览器验收。
- 是否进入 REPORT.md（稳定结论）：否（纯助手 UI 交互，不涉及 NILM 算法稳定结论）。
- 遗留问题：请用户验证浮球可移至期望位置、窗口缩放后仍完全可见，轻点仍可开窗；确认后续新会话按设置默认后端启动、旧会话不被改路由；确认 local / cloud 具体模型选择器与“附件”按钮在目标桌面 / 窄屏的视觉排列。`tmp/` 用户运行数据未读取、修改、暂存或提交。

## [2026-11-04] 专题 T-011：智能问答逐会话后端 / 模型选择、本地配置收敛与受控工具覆盖

- **类型**：用户专题（实现＋验证）
- **执行模式**：模式 A（沙盒自执行）；用户侧真实浏览器 / 真实本地或云端模型未提供，保持待验，不作现场结论。
- **目标与假设**：按本轮验收恢复 composer 底部 local / cloud / builtin 后端选择并按会话隔离；local 候选由已保存本地服务地址发现、cloud 候选来自已配置模型 / 档案、builtin 不显示具体模型；管理员设置移除 local 模型名称，服务地址与 API Key 继续共用；盘点全局工具允许范围，覆盖可安全代理的业务操作并清楚列出不开放能力。所有操作继续使用闭集业务 schema、管理员 allow-list、操作员 scope、服务端重验、逐项确认、高风险二次确认、侧别绑定与审计，不扩成通用命令执行器。
- **方法 / 数据 / 参数**：审查 `TOOL_CATALOG`、服务端 `_execute_assistant_tool` 分发与前端 `ASSISTANT_TOOL_LABELS`；在 `docs/智能问答助手说明.md` §6.6 建立 46 行工具 / scope / 影响限制 / 确认级别矩阵，并明确 26 项高风险与未开放操作。检查 `/api/assistant/local-models/refresh` 只接受空请求或 `{}`，拒绝 `null`、非法 JSON、非空对象及任何自定义 endpoint 参数；刷新只读取已保存 endpoint / API Key。修正隐藏来源名模式下录波 / 画像列表及画像加载结果的名称脱敏并加服务端回归；单通道 RMS 分析强制指定通道，避免空通道请求返回无统计结果；重采样状态仅提供错误标记，避免 worker 异常文本泄露路径。
- **沙盒侧验证三件套（命令 + 输出 + 判读）✅**：
  1. 定向：`.venv/bin/python -m pytest -o addopts='' tests/test_assistant.py tests/test_web_ui.py tests/test_server.py -q` → **84 passed / 1 warning**（12.43 s）；warning 为既有 Starlette/httpx `TestClient` 弃用提示。
  2. 全量：`.venv/bin/python -m pytest -o addopts='' tests -q` → **629 passed / 1 skipped / 1 warning**（167.63 s）；测试夹具将运行态数据输出隔离至临时目录。
  3. 前端行为：`node tools/ui_assistant_check.cjs` → **188 checks passed**；`node --check app/static/app.js`、Python `py_compile`（助手 / 服务端 / 对应测试）通过。
  4. 工具覆盖：新增测试从 Python AST 提取服务端 dispatcher 名称并与 46 项 `TOOL_CATALOG`、前端 46 个工具标签逐项比较；独立检查确认文档矩阵恰好 46 个唯一 ID、scope 逐项一致、26 项二次确认标记与代码 `high_risk` 一致。
  5. 文档生成：运行 `python tools/generate_assistant_docs.py` 更新四份派生手册；`python tools/generate_assistant_docs.py --check` 四份均 `OK`。最终 `git diff --check` 与显式文件范围差异审查在收尾前完成。
- **结果 / 结论**：沙盒内 composer / 管理员设置 / 工具 allow-list 与服务端分发可对齐；刷新接口无法用 body 覆盖保存的本地 endpoint；工具可用面限于矩阵中的注册业务动作。录波 / 画像目录与画像加载输出在隐藏来源名设置下保持脱敏；录波 RMS 工具现要求显式提供通道。未开放任意 shell、Python、SQL、路径、URL/API、配置文件路径、文件删除和系统级清缓存等操作；不开放能力由现有页面或管理员接口处理，不宣称助手覆盖全部软件 API。jsdom / pytest / 静态检查不等同真实浏览器原生视觉、键盘或触屏验收。
- **用户执行命令（含实录路径；本节无用户命令则注明）**：本专题没有用户侧命令；现场实录路径待用户回报。建议用户在目标浏览器核验后端 / 模型下拉、切换后独立会话与窄屏布局；如部署模型服务，另验证 `/models` / Ollama 候选发现、管理员刷新和实际聊天。不得在聊天中发送管理员口令、操作员令牌或 API Key。
- **是否进入 REPORT.md（稳定结论）**：否——本专题是助手产品功能与安全边界，不涉及稳定算法结论 / KPI 口径。
- **遗留问题**：真实浏览器视觉、原生键盘 / 触屏行为未验；未连接真实本地服务或云端 provider，provider 兼容性和实际回答效果未验；管理员 / 操作员令牌仍需部署方按现有文档在目标服务进程配置。`tmp/` 用户数据未读取、修改、暂存或提交。

## [2026-11-04] 专题 T-012：智能问答工具误路由复核与明确指令确定性路由

- **类型**：用户专题（代码复核 / 修复 / 回归验证）
- **执行模式**：模式 A（沙盒自执行）；真实 Qwen 服务与用户浏览器未连接，现场识别效果待验。
- **目标与复现**：用户在新建会话分别输入“启动当前侧数据源检测”与“启动当前侧数据源检测，不要查询或更换录波文件”，观察到结果分别为 `list_recordings`（查询可用录波文件）和 `list_profiles`（查询设备画像）。新会话排除了同一会话旧历史作为这两次输出的原因；由于当时未记录实际发给模型的 schema，不能仅凭复现判断 `start_current_source` 是被权限过滤，还是 Qwen 从可用工具中选错。
- **方法 / 代码审计**：检查 `AssistantService.prepare_chat()` → `operator_tools()` → `openai_tool_schemas()` → `_open_request()` 的实际路由链，以及 `_execute_assistant_tool()` 的服务器分发。确认 schema 先受 `tools_enabled`、管理员 `enabled_tools` allow-list、操作员 token 的精确 scope 与 cloud 独立开关控制；`tool_choice="auto"` 保留模型选择；服务端按注册工具名分发，不会把启动请求映射成查询工具。既有 `/api/assistant/tools/identity` 返回当前 operator / model_type 的有效 `available_tools`，可用于区分授权清单是否包含启动工具。
- **实现 / 安全边界**：
  1. 对 local / cloud 请求增加严格的确定性入口：匹配注册工具标题且 `{}` 经该工具参数 validator 接受时，直接建立待确认提案；不使用模糊自然语言解析。明确标题“启动当前侧数据源检测”及限定补充“不查询或更换录波文件”直接路由 `start_current_source`，不会落入 `list_recordings` / `list_profiles`。
  2. 新建会话的精确命令不依赖旧 history，也不调用 Qwen；因此不再把“同一会话历史”或“改措辞”当成根因 / 解决方案。目标工具未在当前有效清单时，返回具体阻断原因（无有效操作员、总开关、cloud 开关、allow-list 或所需 scope），不会用相似查询工具兜底。
  3. 启动前核对当前侧有配置、未运行、离线来源具有文件路径；明确的离线播放别名只接受 `csv_file` / `csv_tail`。路由只生成预览，不会直接执行。已有 operator token / scope、全局 allow-list、用户确认、高风险 6 位二次确认、服务端确认时重验、操作侧绑定、审计与速率限制不变；未开放任意 shell / SQL / Python / 路径 / API。
  4. 工具目录描述与系统提示补充“启动不得由录波 / 画像查询替代”。对带必需参数的自然语言请求、非精确标题与图片请求，仍由模型 `tool_choice=auto` 处理，不宣称所有模型都能正确识别自由表达。
- **全局工具核验**：测试复核 46 个 catalog ID 与 server dispatcher / 前端标签一致；对目录中所有空参数校验通过的工具标题逐个断言确定性解析结果；权限回归分别构造“allow-list 有 start 但 operator 缺 `engine.start`”与“operator 有 `engine.start` 但管理员 allow-list 不含 start”，并验证普通请求的模型 schema 只包含实际可用工具。该结论验证软件注册 / 筛选 / dispatcher 契约，不等于真实 Qwen 自然语言识别 46 个工具全部通过。
- **用户执行命令（含实录路径；本节无用户命令则注明）**：本专题没有用户侧命令或真实模型实录。沙盒命令与输出如下：
  - `./.venv/bin/python -m pytest -o addopts='' tests/test_assistant.py tests/test_server.py -q` → **66 passed / 1 warning**（18.97 s）；包含 JSON / SSE 端到端提案、分路绑定、缺 scope / allow-list 负向与确认码校验。warning 为 Starlette `TestClient` 与 httpx 的既有弃用提示。
  - `./.venv/bin/python -m pytest -o addopts='' tests -q` → **634 passed / 1 skipped / 1 warning**（194.53 s）；仅使用 pytest 临时目录隔离运行态数据，没有触碰仓库 `tmp/`。
  - `npm ci --ignore-scripts && node tools/ui_assistant_check.cjs && node --check app/static/app.js && node --check tools/ui_assistant_check.cjs` → **188 jsdom checks passed**、JS 语法通过；npm 审计 0 漏洞。
  - `./.venv/bin/python -m py_compile app/assistant.py app/assistant_tools.py tests/test_assistant.py tests/test_server.py`、`node --check app/static/app.js`、`node --check tools/ui_assistant_check.cjs` 与明确 8 文件范围的 `git diff --check` 均通过。真实 Qwen / provider 未连接；不得把自动化路由测试表述成 Qwen 识别效果通过。
- **结果 / 结论**：已修复用户给出的精确启动命令误选查询工具：在权限满足时直接生成 `start_current_source` 的确认预览；若权限缺失则解释具体阻断项，而非返回查询工具。全局 catalog / schema / dispatcher / UI 标签有回归契约。精确标题以外的参数型或自由表达仍受 `tool_choice=auto` 的模型选择影响，真实 qwen3:8b 运行 schema 与识别效果待现场验证。
- **是否进入 REPORT.md（稳定结论）**：否（助手工具路由与安全边界，不涉及 NILM 算法结论 / KPI）。
- **提交 / 推送**：实现 commit `b6accec`（`fix: route explicit assistant tool commands deterministically`）已推送至 `origin/arena/82e34fb8-nilm-calc-tool`；本轮仅显式提交 8 个文件，未添加 / 提交 `tmp/`。
- **遗留问题**：请用户在真实 Qwen3:8b 新会话复测两条原指令，确认提案工具为 `start_current_source`；另用不含 `engine.start` 的操作员 token 验证返回权限原因、不调用查询工具。需再以真实环境的 operator / model_type 查看 `/api/assistant/tools/identity` 中 `available_tools`，辨别实际授权清单。真实浏览器视觉 / 原生键盘 / 触屏待验；不得在聊天发送任何令牌或 API Key。`tmp/` 严格未读、未修改、未暂存、未提交。

### T-012 现场权限核验补记（2026-11-04）

- **用户实测结果**：用户在助手界面点击“验证操作权限”，回报提示为：`验证成功：field-readonly-1 · scope: profiles.read, recordings.read · 当前模型可用工具 2 项。`
- **判读**：身份有效，但该操作员只有画像 / 录波只读 scope；`start_current_source` 要求精确 `engine.start`，因此当前有效工具清单必然不含启动工具。这确认**当前部署存在授权缺项**；若最初两条启动请求使用同一操作员 token 与同一配置，Qwen 不可能从 schema 中选择启动工具，只能在可见的查询工具中误选。此回报没有显示管理员 `enabled_tools` allow-list 内容，不能排除 allow-list 也未勾选；也不是实际模型工具调用记录，不能单独证明最初请求的配置完全相同。
- **处理建议 / 待验**：管理员需在操作员 scope 中增加 `engine.start`（可给专用最小权限 token），并确认助手总开关与 allow-list 同时启用 `start_current_source`；环境变量变更需重启实际服务。随后重新验证，确认工具出现在可用清单中，再用真实 Qwen3:8b 新会话复测，预期只收到启动工具待确认提案；高风险执行仍需服务端 6 位确认码。不要在聊天中提交 token 或 API Key。
- **现场边界**：此 UI 权限检查是用户提供的现场结果；尚未回报补权后的可用清单、真实 Qwen 工具调用或确认执行结果。`tmp/` 未读取或修改。

## [2026-11-04] 专题：恢复应用预览（8000 端口）
- 类型：验证专题
- 目标与假设：按用户要求先检查现有进程，再在 8000 端口恢复 Web 预览；不启动数据源、不读取或修改 `tmp/`。
- 方法 / 数据 / 参数：检查时没有 Python/ASGI 服务进程，8000 端口无监听且 HTTP 连接被拒；项目 `.venv` 不存在。依照 `requirements.txt` 创建 `.venv` 并安装依赖。启动命令：`ELEC_TOOL_AUTOLOAD_LAST=0 ./.venv/bin/python cli.py serve --host 0.0.0.0 --port 8000 --log-level info`。验证 `/`、`/static/app.js`、`/static/style.css`、`/api/state` 均为 HTTP 200；WebSocket `/ws` 握手成功并收到 `hello`；监听地址为 `0.0.0.0:8000`。
- 用户执行命令（含实录路径）：本节无用户命令；以上为沙盒执行，启动日志和 smoke 输出见当前会话工具记录，无单独实录文件。
- 结果 / 结论：应用预览已在端口 8000 恢复运行；未改应用源码或运行配置文件，`tmp/` 未读、未修改、未暂存或提交。关闭自动加载上次运行数据，未启动任何数据源。
- 是否进入 REPORT.md（稳定结论）：否
- 遗留问题：只完成 HTTP / WebSocket 冒烟，未做真实浏览器视觉、原生键盘或触屏验收；真实模型服务未验证。

## [2026-11-04] 专题：全局工具 allow-list 逐工具 scope 展示与说明
- 类型：用户专题 / 验证专题
- 目标与假设：使管理员在「配置与附加知识库 → 受控业务工具与审计 → 全局允许的工具」查看每个工具实际要求的 operator scope；讲清全局工具 ID 与操作员 `scopes[]` 是两层不同配置，并在 `docs/智能问答助手说明.md` 中说明全部 46 项映射。
- 方法 / 数据 / 参数：前端复选项使用现有 `GET /api/assistant/config` 返回的 `tools[].scope` 展示「所需 scope」，不复制维护第二份权限目录；说明全局复选框只设置 `enabled_tools` 中的工具 ID，scope 固定在服务端目录，逐操作员 scope 仍需配置在服务端环境变量 `ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS`。文档 §6.2 增加三类操作示例、配置步骤与共享 scope 说明；§6.6 将表头改为 operator `scopes[]` 必须包含的 scope，并由测试校验每个 TOOL_CATALOG ID / scope 均有对应文档行。
- 用户执行命令（含实录路径）：本节无用户命令；依赖恢复、测试与 HTTP 验证均由沙盒执行，命令 / 输出见当前会话工具记录，无单独用户实录文件。
- 结果 / 结论：`./.venv/bin/python -m pytest -o addopts='' tests/test_assistant.py tests/test_server.py tests/test_web_ui.py -q` → **90 passed / 1 warning**（20.18 s）；`node tools/ui_assistant_check.cjs` → **192 checks passed**；`node --check app/static/app.js` 通过。目标预览绑定 `0.0.0.0:8000`；`/`、`/static/app.js`、`/static/style.css`、`/api/assistant/config`、`/api/assistant/documents` 均 HTTP 200；运行态目录 46 项均带 scope，`start_current_source` 显示 `engine.start`，更新后的说明文档已加载。未改后端授权模型或 `TOOL_CATALOG`，未新增逐操作员 UI scope 编辑。
- 是否进入 REPORT.md（稳定结论）：否
- 遗留问题：未做真实目标浏览器视觉 / 键盘 / 触屏验收；需用户确认工具列表 46 项在现场设置面板中的滚动、换行及 scope 可读性。`tmp/` 未读、未修改、未暂存或提交。

## [2026-11-05] 专题 T-013：智能问答“播放 / 启动数据源”误识别分析与修复

- **类型**：用户专题（代码审查 / 确定性路由修复 / 回归验证）
- **执行模式**：模式 A（沙盒自执行）。没有连接用户的 Qwen / 云端 provider；不声称重现或验证了真实模型的原始输出。
- **目标与用户报告**：修复以下六句误选「修改离线播放速度」或未识别工具的问题：①“播放离线数据源CSV文件”；②“播放离线数据源”；③“播放数据源”；④“启动离线数据源CSV文件”；⑤“播放数据源与控制中的离线数据源CSV文件”；⑥“启动数据源与控制中的离线数据源CSV文件”。六句目标均为操作当前侧已经配置的数据源，不以口语中的“CSV文件”推断新文件。
- **原因分析（静态代码证据与边界）**：
  - 原 `app/assistant.py::_explicit_tool_command` 只确定性处理精确工具标题和少数固定启动别名；上述六句不在原规则中，因此 local / cloud 且无图会进入 OpenAI-compatible `tool_choice=auto` 工具选择。模型可能把“播放 / 离线”与调速工具关联，但本轮没有原始模型请求 / 返回记录，不能断言这是实际 Qwen 根因。
  - `set_playback_speed` 需要数值 `speed`，scope 为 `config.source.write`，只改当前 CSV 倍速、不启动来源；`start_current_source` 是空参数操作工具，要求 `engine.start`。若操作员 scope 或管理员 allow-list 过滤掉启动工具，模型根本看不到 `start_current_source`。此前用户提供的 `field-readonly-1` 权限回报仅有 `profiles.read`、`recordings.read`、当前可用 2 项工具，确定该身份当时缺少 `engine.start`；但无法证明六次报告当时使用的正是这套身份 / 配置。
  - 第五、六句的“数据源与控制中的”是 UI 位置描述，不是路径或资源 ID。CSV 文件名不是服务端 `file_id`，不能据此选择或构造路径。
- **实现 / 优化**：
  1. 在 `_explicit_tool_command` 增加窄范围的明确语法：`播放 / 启动 / 开始播放 / 运行 + 数据源`；仅归一化全角形式、空白及已知“数据源与控制中的”页面位置词。六条报告短句在调用模型前确定性路由至 `start_current_source`，不再让模型在 start / speed / query 工具间猜选。
  2. system prompt 与工具描述明确：普通“播放 / 启动数据源”不是调速；`set_playback_speed` 只用于明确请求改速度 / 倍速并提供目标数值，而且不负责启动。保留原有 `speed` 参数 schema 与 `config.source.write` scope。
  3. 仍以当前侧保存的来源为准，校验来源已配置、运行状态、离线来源种类和文件可用性。泛称“播放数据源”不强行要求离线来源；带“离线 / CSV文件”的短句仍要求 `csv_file` / `csv_tail`。无配置、来源不匹配或无可用文件时提示用户去「数据源与控制」为当前侧配置 / 核验后重试，不查询目录、不切换来源、不推断路径或 `file_id`。
  4. 路由只创建绑定当前操作侧的待确认提案；不执行操作。token / scope、管理员 allow-list、确认与高风险二次确认、执行时服务端复验、审计和闭集工具目录均保持不变；未授权时说明阻断，不用相似查询工具兜底。
- **回归 / 命令与结果**：
  - `.venv/bin/python -m pytest -o addopts='' tests/test_assistant.py tests/test_server.py -q` → **66 passed / 1 warning**（18.48 s）。覆盖六句直接路由、无需调用模型、API JSON 提案、侧别绑定、授权拒绝、离线类型 / 文件状态失败提示，以及既有确认流程。唯一 warning 为 Starlette `TestClient` 与 httpx 的弃用提示。
  - `.venv/bin/python -m pytest -o addopts='' tests -q` → **635 passed / 1 skipped / 1 warning**（187.83 s）。
  - `.venv/bin/python -m py_compile app/assistant.py app/assistant_tools.py tests/test_assistant.py tests/test_server.py` 通过；`.venv/bin/python tools/generate_assistant_docs.py --check` 四份派生手册均 `OK`。
  - 上述测试直接验证服务端确定性路由和提案，没有调用真实 Qwen；不证明模型自由表达的通用工具选择效果。无前端代码变更，因此本专题未跑 jsdom / 浏览器验收。
- **用户执行命令（含实录路径；本节无用户命令则注明）**：本专题无用户侧命令或真实模型实录；六条输入来自用户报告。未请求或输出令牌 / API Key。仓库 `tmp/` 未读取、修改、暂存或提交。
- **结果 / 结论**：六条已报告短句现在在 local / cloud、无图片的确定性路径中选择当前侧 `start_current_source`，即使模型可能把“播放”误判为速度操作，也不会再询问模型选工具。安全结果仍取决于服务端有效权限与当前来源配置；不得将代码级回归表述成真实模型实测通过。
- **是否进入 REPORT.md（稳定结论）**：否（助手工具路由 / 安全边界，不涉及 NILM 算法路线或 KPI）。
- **遗留问题**：如需现场确认，请部署方先核验当前 operator 的实际 `available_tools` 同时含 `start_current_source`、授权 scope `engine.start`，且管理员全局 allow-list 已勾选该工具；再在真实 Qwen 新会话逐句检查预览工具名和当前侧来源，不点击执行前先核对影响。真实 provider 未连接，现场模型输出仍待用户回报；不要发送 token / API Key。
- **Git 交付状态**：本地 `HEAD` `27b28ea` 仅跟踪 `BOOTSTRAP.md`、`ROLE.md`，应用源码 / 测试 / 说明在 checkout 显示为 untracked；为避免把不完整源码集合当新增文件推送，本轮未暂存 / commit / push。先确认 / 修复 checkout 基线再处理 Git 交付。
## [2026-11-06] T-014 智能问答基于大模型技术的意图识别技术设计文档（落盘）

### 一、文档基本信息
| 项 | 内容 |
|---|---|
| 文件 | `docs/智能问答助手基于大模型技术的意图识别技术设计文档.md`（V2.0，约 580 行） |
| 结构 | 用户提供的 12 章 + 4 附录模板：项目概述（1）、需求分析（2）、系统架构设计（3）、技术方案设计（4）、意图识别方案设计（5）、意图字典与标签体系（6）、Prompt 设计与优化（7）、接口与数据流设计（8）、安全与合规设计（9）、部署与运维设计（10）、评估与质量保证（11）、实施计划与风险控制（12）、附录 A 意图字典模板、附录 B Prompt 全文示例、附录 C 输入输出 JSON Schema、附录 D 评估测试用例表 |
| 核心编码规则 | `tool#action#object`，`category#object#action`；业务意图分三组：启动控制（start_current_source）、暂停控制（pause_current_source）、恢复播放（resume_current_source）、停止控制（stop_current_source）；确定性路由仅 cover start/pause/resume/stop，英文单字支持，非文件源与槽位不足拒绝 |
| 落盘状态 | md 文件已落盘，与 `app/assistant.py`、`app/assistant_intents.py`、`app/assistant_tools.py`、`app/server.py` 对齐（46 个受控工具、确定性路由、服务端门控、trace_id、脱敏日志） |
| 关联任务 | T-016 计算功能卡片技术设计 / T-017 智能问答功能卡片配置 / T-018 助手意图识别路由优化（已完成并推送） |

### 二、与代码的一致性核查
| 检查点 | 代码事实 | 设计文档 |
|---|---|---|
| 受控工具总数 | `app/assistant_tools.py::TOOL_CATALOG` 46 项，每项 `id/name/description/parameters/strict: true/scope` | §5、附录 C 以 46 工具闭集为前提，start/pause/resume/stop 列为受控核心命令 |
| 确定性路由 | `app/assistant.py::_explicit_tool_command` cover start/pause/resume/stop；含“执行”动词 + 可选“播放”后缀；英文单字分支 `_EXACT_SOURCE_VERB_RE` | §5 意图字典与标签体系、§7 Prompt 意图判定 |
| 服务端门控 | `app/assistant_intents.py::validate_model_tool_result` 三级校验 + `_value_grounded` 参数 grounding + 复合拆解 `split_compound_intent` | §8 接口与数据流设计、§9 安全与合规 |
| trace_id | 响应头 `X-Assistant-Trace-ID`，审计写入 `tool_audit.jsonl` | §8、§9 |
| 脱敏日志 | `_redact_names` / `_StreamingNameRedactor` 流式脱敏文件名；图像不写知识库/持久目录 | §9 |
| py_compile / pytest | `py_compile app/assistant.py` 通过；`pytest tests/test_assistant.py` 回归通过（含英文单字回归） | 附录 D |

### 三、验收结论
md 文件已落盘；内容与 NILM 系统实际代码一致（46 个受控工具、确定性路由仅 cover start/pause/resume/stop、英文单字支持、服务端门控、trace_id、脱敏日志）。未启动/重启用户服务，未获现场日志，未连接真实 Qwen，不声称现场验收通过；`tmp/` 未读取、修改、清理或提交。

## [2026-11-10] 补录：2026-11-05～11-06 被覆盖丢失的 4 篇专题（T-014～T-017，原文）

> **补录说明（2026-11-10，经过见 T-019）**：以下 4 篇专题原已入库（提交 `b3d1cc5`，最后完整版本见 `ca5dc28`），在提交 `c5cf96f`（2026-11-06 02:30 UTC）中连同索引行被旧文件覆盖而丢失。
> 此处按 `ca5dc28:REPORT_TEST.md` 第 4239–4320 行逐字补回，未作改写，所以位置晚于时间顺序。读这 4 篇时注意：
> 1. 文中写「已完成」的实现有一部分随后同样被覆盖：`app/assistant.py` 的澄清返回与路由诊断日志、对应测试、`docs/智能问答助手说明.md` §6.8 / §6.9 至今未恢复，现状见 T-019。文中的验证数字是当时的实录，不代表当前代码。
> 2. 编号：本节的 T-014 是 2026-11-05 的方案分析；上方现存的「[2026-11-06] T-014 …设计文档（落盘）」是另一篇，专题索引中记作 T-014b。
> 3. 现存 T-014b 条目「关联任务」一行里写的 T-016 / T-017 / T-018 名称与本节各篇的实际专题名不一致，以专题索引和本节原文为准。

## [2026-11-05] 专题 T-014：智能问答扩展表达的意图识别方案分析

- **类型**：用户专题（方案分析）
- **执行模式**：模式 A（基于代码静态审查）；没有真实模型服务调用或用户现场日志，不把假设写成实测结论。
- **目标与问题**：分析如何让智能问答助手面对六条已修复表达之外的口语、语序变化、省略、否定、疑问、复合动作和参数缺失请求时，意图识别更精确。
- **方法 / 分析结论**：审查当前 `app/assistant.py` 中窄范围启动规则、`tool_choice=auto` 退路、有效工具过滤与提案校验入口；对照 46 项 `TOOL_CATALOG` 与各工具参数 schema。提出不应无限叠加正则，而应按受控工具建立有限意图目录，并将自然语言意图、参数抽取、权限 / 当前状态检查分层。
- **方案归档**：
  1. 每工具定义正例、负例、易混淆动作和参数要求；明确 start / pause / resume / stop、文件选择 / 查询、调速、加载历史等彼此不同的动作。
  2. 仅对可解释的格式变化和有限 UI 位置词归一化；保留疑问、否定、过去时、引用文本与复合请求等语义差异。
  3. 把模型选择结果视为候选；服务端校验候选工具是否与用户要求一致，参数是否明确、合法且来自本轮受控资源。出现冲突、缺参或低置信度时走澄清，不创建提案。
  4. 以正例 / 负例 / 缺参 / 越权 / 状态冲突矩阵做回归，优先降低会触发副作用工具的误识别；如要评估真实模型，需记录当次可用工具集并连接实际 provider。
- **用户执行命令（含实录路径；本节无用户命令则注明）**：无用户执行命令；没有真实 Qwen 请求 / 响应实录。本节仅归档分析方案，不报告模型识别准确率。
- **结果 / 结论**：该方案作为下一步实现范围；模型不能绕过闭集目录、schema、权限 / 当前侧检查、确认流程与服务端复验。模糊表达应澄清而不是选择近似工具兜底。
- **是否进入 REPORT.md（稳定结论）**：否（智能问答产品路由方案，不涉及 NILM 算法结论）。
- **遗留问题**：用户随后要求为全部 46 个受控工具建立逐工具规则，并增加模型结果服务端校验与澄清分支；此实现作为独立后续专题推进。真实 provider 验收仍需用户部署环境测试。

## [2026-11-05] 专题 T-015：智能问答 46 项有限意图合同、模型提案前校验与澄清

- **类型 / 执行模式**：用户专题（实现＋验证）；模式 A（沙盒自验证）。无真实 Qwen / provider 请求，不报告模型选择质量或现场验收通过。
- **目标与验收**：将 T-014 方案应用于助手全部 46 个固定受控工具；为每项定义有限意图、正反例与参数规则。模型返回的工具调用只作候选；服务端在创建 proposal 前核对用户意图与工具、参数值与本轮表达 / 受控资源上下文。错工具、疑问 / 否定、复合冲突、歧义、必填缺失、未 grounding 的值或 schema 不合法时不产生操作预览并明确澄清。保留闭集权限及确认执行流程。
- **实现**：
  1. 新增 `app/assistant_intents.py`，为 `TOOL_CATALOG` 46 项建立意图合同，包含动作 / 目标词、例句、反例、参数要求、必填项及缺参提示；自动化测试验证工具目录覆盖完整。
  2. 接入 `app/assistant.py` 提案前服务端验证。模型函数调用本身不视为用户授权 / 意图证明；值须可追溯到用户表达或本轮受控资源上下文，并继续通过既有工具 schema 验证。多动作、错工具、参数语义冲突、缺参、歧义和未 grounding 显式值进入澄清，不回退到相似工具。
  3. 普通 JSON 响应暴露 `clarification`（澄清时 `proposal=null`）；SSE 使用 `type=clarification` 事件。存在模型工具调用时先缓冲流式文本，等候服务端验证；若模型候选不匹配则丢弃未经核验的模型成功自述，避免向用户展示与实际结果矛盾的“已完成”。前端为澄清回答显示专用标记。
  4. 更新 `_TOOL_SYSTEM_PROMPT`、`README.md` §3.6 / §11 与《智能问答助手说明》§6.8 / §7 API bullet；同步四份由 `tools/generate_assistant_docs.py` 派生的手册。
- **安全边界**：未开放任意 shell / SQL / Python / 文件路径 / API；原有 operator token / scope、管理员 allow-list、opaque resource ID、当前侧绑定、用户确认、高风险二次确认、执行时服务端复验、审计及限流保持。无权或无证据时澄清 / 拒绝，不用相似查询工具兜底。
- **验证命令 / 输出 / 判读**：
  - `.venv/bin/python -m pytest -o addopts='' tests/test_assistant.py tests/test_server.py -q` → **70 passed / 1 warning**；覆盖合同 / 参数 grounding、错工具与歧义门控，以及 JSON / SSE 澄清。
  - `.venv/bin/python -m pytest -o addopts='' tests -q` → **640 passed / 1 skipped / 1 warning**（187.92 s）。唯一 warning 为既有 Starlette `TestClient` / httpx 弃用提醒。
  - `node tools/ui_assistant_check.cjs` → **192 checks passed**；`node --check app/static/app.js`、修改的 Python 文件 `py_compile` 通过。
  - `.venv/bin/python tools/generate_assistant_docs.py --check` → 四份派生手册均 `OK`；先按更新后的 README 重新生成再检查。`npm ci --ignore-scripts --no-audit --no-fund` 只安装 harness 依赖；未修改 `package.json` / lockfile。
- **用户执行命令 / 实录**：无用户侧命令或真实 provider 实录；模型端到端用例使用受控假响应，不能证明真实模型工具选择准确率。未索取 / 输出 token 或 API Key。
- **结果 / 结论**：JSON 与 SSE 提案路径均经同一服务端意图门控；未通过时不创建操作提案，SSE 不泄漏未核验工具调用后的成功自述。工具目录与权限边界仍为闭集。`tmp/` 未读取、修改、清理、暂存或提交。
- **遗留 / 现场验收**：真实 Qwen / provider、目标浏览器视觉、原生键盘 / 触屏尚未验；部署端仍需测试自由表达、模型工具选择与澄清文案。pytest 假响应与 jsdom 不构成真实现场验收。
- **Git 交付状态**：本会话未暂存、commit 或 push。此前发现此 checkout 的应用源码 / 测试 / 文档跟踪基线不完整，避免把既有源码集合误作本轮新增文件；后续需先核实 Git 基线。
- **相关文件 / 分支**：`app/assistant_intents.py`、`app/assistant.py`、`app/server.py`、`app/static/app.js`、`app/static/style.css`、`tests/test_assistant.py`、`tests/test_server.py`、`tests/test_web_ui.py`、`docs/智能问答助手说明.md`、README、`STATUS.md`、本报告；`arena/82e34fb8-nilm-calc-tool`。

## [2026-11-06] 专题 T-016：“播放离线数据源”仍识别成调速的根因复核

- **类型 / 模式**：用户专题（代码路径分析＋定向回归）；模式 A。没有连用户部署的 Qwen/provider，未取得该次 HTTP 请求 / 响应实录，因此把代码级事实与部署侧假设分开。
- **用户报告**：输入“播放离线数据源”后界面仍显示“修改离线播放速度”。本专题复核本工作区当前活动分支代码是否能产生该结果，并分析实测与源码预期不一致的可能原因。
- **当前代码的确定性路径**：
  1. `app/assistant.py::_normalize_source_start_prompt` 只做受限归一化：全角 / NFKC、空白、少量礼貌前缀、已知“数据源与控制”页面位置词和句末标点；`_explicit_source_start_command` 的闭合语法接受“播放 + 离线 + 数据源”。对字面输入“播放离线数据源”，`_explicit_tool_command` 返回 `start_current_source`，而非 `set_playback_speed`。
  2. `AssistantService.prepare_chat` 在当前模型为 local / cloud 且没有图片时，先执行 `_explicit_tool_command`。命中后直接向 `_accept_tool_calls` 提交受控的空参数启动候选并 `return direct_plan`；此路径不会调用 `_open_request`，即模型没有机会在启动 / 调速间自由选工具。
  3. 命中后的权限 / 状态失败也不会回退为调速：`start_current_source` 不在有效工具集时返回 403，并说明缺少 `engine.start` / 管理员 allow-list 等阻断项；当前侧来源未配置、已运行、要求离线但来源非 `csv_file` / `csv_tail`、离线文件路径不可用时返回相应 409。不存在“启动工具不可用就换 `set_playback_speed`”的兜底。
  4. 即使确定性路径因条件未满足而让请求进入模型工具选择，当前 `_accept_tool_calls` 也会调用 `validate_model_tool_result`。在当前工作区，对该原句的唯一最高意图候选是 `start_current_source`（分数 47）；若模型错报 `set_playback_speed`（本例尝试参数 `speed=2`），验证结果为 `ok=false`，提示请求符合启动数据源而不是修改离线速度，不会创建 proposal。SSE / JSON 的拒绝路径同样不应产生调速提案。
- **复现 / 验证**：沙盒直接调用结果：`_explicit_tool_command` → `start_current_source`；`_explicit_offline_source_start` → `True`；`find_tool_intent_candidates` → `[('start_current_source', 47)]`；把候选硬设为 `set_playback_speed` → 澄清、无操作预览。`tests/test_server.py::test_assistant_explicit_source_start_routes_to_bound_proposal_without_model` 用不可调用模型的断言覆盖 API 路由；当前 `tests/test_assistant.py tests/test_server.py tests/test_web_ui.py` → **95 passed / 1 warning**（19.27 s）；相关 `py_compile` 与四份生成手册 `--check` 通过。warning 为既有 Starlette `TestClient` / httpx 弃用提示。测试是当前代码 / mock 环境证据，不是用户部署现场证据。
- **原因判读（分确定事实与假设）**：
  - **确定事实**：在当前源代码、字面 prompt、local / cloud、无图且实际命中本分支的条件下，服务端不会生成 `set_playback_speed` proposal；如果权限或数据源条件不满足，表现应为 403 / 409，而非错误地改成调速。
  - **最可能的部署差异**：实际请求由尚未载入本分支代码的旧服务进程、旧安装目录、另一端口 / 反向代理目标或未全部重启的多 worker 处理。此前未经覆盖的旧路径把自然语言交给 OpenAI-compatible `tool_choice="auto"`；“播放 / 离线”与调速工具名的词面关联可能促使模型误选。这是与历史代码和报告现象相符的解释，但没有现场模型原始请求 / 响应，不能声称已证明实际 Qwen 的推理根因。README 程序版本仍为 v0.99.48，不能仅凭 UI 版本号判断服务是否包含本轮改动。
  - **其他需排除项**：请求实际带了图片（确定性直达条件排除图片）；最终发给服务端的 `prompt` 还有未报告的附加词 / 隐藏字符，未匹配窄语法；浏览器展示的是先前会话 / 先前回答的旧 proposal；或实际结果只是模型普通文字而非带确认按钮的 proposal。普通回答文字不一定是工具调用；意图门控只裁决实际工具候选。即便有图片 / 文本变体而让请求转模型，当前代码若实际执行仍应由后置门控拒绝错工具调用。
  - **不是当前代码中的解释**：只缺 `engine.start` scope、allow-list 未勾选、云端工具关闭或当前侧数据源状态异常，都不会使当前代码改选速度工具；它们分别导致权限错误 / 无工具提案 / 状态错误。真实日志未提供，不能判定报告发生时哪一条件成立。
- **建议的无密钥定位信息**：在浏览器 Network 中只核对该次 `/api/assistant/chat` 的 `model_type`、原样 `prompt`、图片数量和响应 `proposal.tool` / `clarification`。不要复制任何 Authorization 头、operator token 或 API Key。若响应中真有 `proposal.tool=set_playback_speed`，检查实际服务进程加载的代码目录、进程启动时间、目标端口 / 代理 worker 与是否重启；若只有 `answer` 文字、`proposal=null`，应按普通模型回答而不是实际操作提案分析。沙盒预览状态不代表用户 Windows PowerShell / 服务进程状态。
- **代码改动 / 安全边界**：本专题仅作根因分析与定向验证，未改路由代码或权限配置。没有重启用户服务，没有索取 / 输出令牌；仓库 `tmp/` 未读取、修改、清理、暂存或提交。
- **Git 交付状态**：未暂存、commit 或 push；遵循当前 checkout 跟踪基线不完整的既有约束。
- **相关文件 / 分支**：`app/assistant.py`、`app/assistant_intents.py`、`app/server.py`、`tests/test_assistant.py`、`tests/test_server.py`、`STATUS.md`、本报告；`arena/82e34fb8-nilm-calc-tool`。

## [2026-11-06] 专题 T-017：为“播放离线数据源”误识别增加后台路由诊断日志

- **类型 / 模式**：用户专题（实现＋验证）；模式 A（沙盒自验证）。未连接用户部署的服务进程或真实 Qwen / 云 provider，因此只报告日志能力与沙盒验证结果，不把日志内容解读成现场根因。
- **目标**：用户要求“在后台服务中增加运行日志进行排查”。在不记录问题原文、令牌、API Key、截图内容、文件路径的前提下，让现场日志能回答四个问题：本次请求走了确定性直达还是模型选择；模型实际返回了哪个工具；服务端接受还是澄清；若是权限 / 来源状态问题，被哪一项阻断。
- **实现**：
  1. `app/server.py::assistant_chat` 为每次有效问答请求生成 16 位十六进制 `trace_id`（`secrets.token_hex(8)`），写入 `X-Assistant-Trace-ID` 响应头（JSON 与 SSE、错误响应均带），并在准备阶段拒绝 / 完成阶段拒绝 / 未预期异常时记录带同一 `trace_id` 的日志。
  2. `app/assistant.py::prepare_chat` 在工具路由决策点记录 `assistant_route_decision`（普通）或 `assistant_route_diagnostic`（“离线 + 数据源 + 播放 / 启动 / 开始 / 运行”请求，`WARNING` 级）：`trace_id`、`side`、`backend`、`image_count`、`decision`（`deterministic_direct` / `model_fallback` / `images_attached` / `backend_not_tool_capable`）、`direct_tool`、`start_tool_available`、`speed_tool_available`、`available_tool_count`、`source_kind`、`source_running`、`source_has_path`、`operator_authenticated`。
  3. `_accept_tool_calls` 记录 `assistant_tool_candidate`（候选工具名、意图候选及分数、参数**字段名**、未知字段数）与 `assistant_tool_decision`（`proposal_created` / `clarification` + `reason`：`intent_mismatch` / `no_intent_match` / `ambiguous_intent_or_compound_request` / `parameter_grounding_or_schema` / `tool_call_count` / `blocked`）。
  4. `complete` / `stream` 在模型未返回工具调用时记录 `assistant_model_result outcome=plain_text`，用于区分“普通文字回答”与“真创建了调速提案”。
  5. 直达路由的四类 409 与 403 阻断分别记录 `assistant_route_blocked reason=source_not_configured / source_already_running / offline_source_kind_mismatch / offline_file_unavailable / tool_unavailable`；`_open_request` 记录 `assistant_model_request`（`trace_id`、后端、流式与否、工具数、`tool_choice`）。
  6. `app/server.py::lifespan` 启动时记录 `服务启动 version=… pid=… assistant_module=… modified=…`，用于核对实际加载目录与文件时间，排除未重启 / 指向旧目录的旧进程。
- **脱敏约束**：日志不记录原始问题、历史文本、参数值（只记录固定 schema 字段名）、截图内容、API Key、`Authorization` 头、操作员令牌、操作员 ID、模型 endpoint 或数据源文件路径；`source_kind` 仅保留 `csv_file` / `csv_tail` / `tcp` / `simulator` / `other` / `none`，未知值归并为 `other`。模型候选工具名不在注册目录时记为 `unregistered`。未开启 `log_queries` 时不会记录问题文本；该既有开关的隐私影响已在文档标注。
- **沙盒实测日志样例（真实调用当前代码，未连接真实模型）**：
  - 直达路径：`WARNING elec_tool.assistant: assistant_route_diagnostic trace_id=a0bd7178c3b2fd2b side=branch backend=local image_count=0 decision=deterministic_direct direct_tool=start_current_source start_tool_available=True speed_tool_available=True available_tool_count=2 source_kind=csv_file source_running=False source_has_path=True operator_authenticated=True`
  - 模型错报调速：`WARNING elec_tool.assistant: assistant_tool_decision trace_id=adfdfac776a0873e origin=model outcome=clarification reason=intent_mismatch candidate=set_playback_speed intent_candidates=start_current_source:47 argument_fields=speed unknown_argument_field_count=0`
  - 来源未配置：`WARNING elec_tool.assistant: assistant_route_blocked trace_id=8d4baac42b5cc1b2 reason=source_not_configured`
- **验证命令 / 输出**：
  - `.venv/bin/python -m pytest -o addopts='' tests/test_assistant.py tests/test_server.py tests/test_web_ui.py -q` → **96 passed / 1 warning**（20.32 s）；warning 为既有 Starlette `TestClient` / httpx 弃用提示。
  - 新增 `tests/test_assistant.py::test_offline_source_playback_diagnostics_log_route_and_rejected_tool_without_values`：断言诊断事件、`trace_id` 长度 / 字符集、`decision=deterministic_direct`、错工具候选的 `intent_candidates=start_current_source:47` 与 `reason=intent_mismatch`，并断言问题原文、管理员 / 操作员令牌、`speed=2`、`Authorization`、`api_key` 均不出现在日志中。
  - `tests/test_server.py` 两个既有 API 用例增加 `X-Assistant-Trace-ID` 断言（JSON 与 SSE）。
  - `app/assistant.py`、`app/server.py`、两个测试文件 `py_compile` 通过；`node --check app/static/app.js` 通过（本轮未改前端）；`tools/generate_assistant_docs.py --check` 四份派生手册均 `OK`。
- **现场判读方法**：先用 Network 响应头 `X-Assistant-Trace-ID` 定位该次请求，再在服务日志中 grep 同一 ID。若**完全没有**该 ID 的日志，说明处理请求的进程未载入本版本（旧进程 / 旧目录 / 旧 worker / 代理指向别处）。若出现 `decision=model_fallback` 且 `candidate=set_playback_speed`，说明请求未命中直达规则（如附图、措辞差异）且服务端门控未生效，应核对进程版本；若为 `outcome=clarification reason=intent_mismatch`，说明门控按设计拒绝，界面不应出现调速确认卡。`assistant_model_result outcome=plain_text` 表示模型只输出文字，未产生工具提案。
- **安全边界 / 未验**：未新增任何可执行入口、任意日志读取接口或远程诊断端点；日志只写服务端标准输出。没有重启用户服务、没有读取或输出令牌；`tmp/` 未读取、修改、清理、暂存或提交。真实部署日志与真实 provider 工具选择仍待用户现场回传（只回传日志行与 trace ID，不要回传令牌）。
- **Git 交付状态**：未暂存、commit 或 push；沿用当前 checkout 跟踪基线不完整的既有约束，避免全量暂存。
- **相关文件 / 分支**：`app/assistant.py`、`app/server.py`、`tests/test_assistant.py`、`tests/test_server.py`、`docs/智能问答助手说明.md`、`STATUS.md`、本报告；`arena/82e34fb8-nilm-calc-tool`。

## [2026-11-10] 专题 T-019：旧文件覆盖新提交的事故复盘、`app/server.py` 恢复与台账补录

- **类型 / 模式**：验证专题（事故复盘＋恢复）；模式 A（沙盒自执行），角色为工程实现工程师。分支 `arena/51b63974-nilm-calc-tool`，基线 `e05542a`（远端 `restore2remote`）。没有连接真实模型、真实浏览器和用户部署环境。
- **目标与假设**：开局基线全量 pytest 有 1 个失败。最初假设是某次改动只做了一半；查 git 历史后否定——出错的代码在 2026-11-06 是完整的，11-09 被一份旧文件盖掉了。目标因此改为：查清覆盖范围；恢复用户 2026-11-10 批准的部分（`app/server.py`、`tests/test_server.py` 丢失的断言、丢失的台账条目）；其余只登记待办。
- **方法 / 数据 / 参数**：
  - **历史来源**：本地检出是浅克隆，用 `git fetch --no-tags --depth=60 origin restore_branch_full_history` 取回 60 个提交（`75cac52` 2026-11-04 15:33 ～ `22d8d9c` 2026-11-10 09:05）。更早的历史没有取回，也没有检查。本节时间均为 UTC。
  - **覆盖扫描**：对这 60 个提交里每个被修改的文件（排除 `node_modules/`、`tmp/`），计算提交后内容与父提交版本的差异行数，以及与更早各版本的差异行数；后者更小就列为疑似「写回旧内容」，再逐个看 diff 判断。
  - **恢复手法**：`git merge-file` 三方合并，ours 取覆盖前最后一个好版本，base 取被写回的旧版本，theirs 取当前版本。这样既还原丢失的修改，又保住覆盖提交里夹带的新改动。
  - **验证**：全量与定向 pytest；真实 `cli.py serve` 进程上的 HTTP 冒烟（旧文件与恢复后各一次）；负对照（新测试文件配旧 `app/server.py`）；按提交回放两份助手 / 服务端测试；jsdom 界面检查；四份生成手册一致性检查。
- **用户执行命令（含实录路径）**：本节无用户命令。全部命令在沙盒执行，输出摘录见下文，没有单独的实录文件。
- **结果 / 结论**：
  1. **失败现象**。`e05542a` 上全量 pytest 为 1 failed / 638 passed / 1 skipped。失败用例是 `tests/test_server.py::test_assistant_proposal_confirm_is_branch_scoped_and_reauthorized`：`app/server.py:2120` 调用 `AssistantService.claim_tool_proposal()` 时多传了一个侧别参数（`current_side()`），抛 `TypeError: … takes from 3 to 4 positional arguments but 5 were given`。这次调用是「确认执行」处理函数取出令牌头之后的第一步，`TypeError` 又不在它捕获的异常之内，所以在 `e05542a` 上，助手操作提案的两个确认接口（`POST /api/assistant/tools/confirm`、`POST /api/branch/assistant/tools/confirm`）每次调用都返回 HTTP 500，助手提出的操作无法确认执行。
  2. **根因**。提交 `2c51d2f`（11-09 08:49，标题「前端：分路侧顶栏显示完整状态」）里的 `app/server.py` 与 `7a88bd3`（11-05 01:40）时点的版本只差 1 行：`git diff --numstat 7a88bd3 2c51d2f -- app/server.py` 输出 `1 0`，多出的是 `_side_summary` 里的 `"pausable"` 字段。相对它的父提交 `05b7ba8` 则是 +60 / −108。也就是说，11-05 16:49 ～ 11-06 08:50 之间 8 个提交对该文件的修改被整体退回：`b3d1cc5`（T-015～T-017 的服务端部分：`clarification` 返回字段、`X-Assistant-Trace-ID` 响应头、启动日志），以及 `bc4e329`、`5be8837`、`5b490c6`、`568083f`、`c01a5d6`、`6aff7c0`、`24f2d09`（跨侧操作的侧别绑定修复）。`app/assistant.py` 没有被这个提交改动，仍是新签名，两边对不上。
  3. **覆盖范围**。扫描加人工确认，共 3 个提交、8 个文件。三个提交的 `Co-authored-by` 都是 `arena-agent`，即都出自 Agent 会话。按差异行数，被写回的内容最接近 11-05 凌晨的版本（`b6accec` 01:33 ～ `7a88bd3` 01:40），再加上各会话自己的改动；`app/server.py` 一项只差 1 行。

     | 提交 | 时间 | 提交标题 | 被覆盖的文件（相对父提交的增 / 删行数） | 丢失的内容 |
     | --- | --- | --- | --- | --- |
     | `c5cf96f` | 11-06 02:30 | T-018: 修复停止/暂停/恢复离线数据源的确定性路由 | `REPORT_TEST.md`（+1 / −90）、会话纪要（+0 / −59）、`STATUS.md`（+5 / −25）、`app/assistant.py`（+176 / −224）、`tests/test_assistant.py`（+124 / −213）、`docs/智能问答助手说明.md`（+11 / −17） | 专题 T-014～T-017 正文与 6 行索引；5 条会话纪要；`STATUS.md` 的 T-015～T-018 条目；`app/assistant.py` 的澄清返回与路由诊断日志；5 个测试用例；说明书 §6.8、§6.9 |
     | `e31e0d9` | 11-06 03:50 | feat: 上传 app/static cli.py configs elec_tool package.json requirements.txt tests tools 最新版本 | `tests/test_server.py`（+0 / −53） | 澄清用例 1 个；另一个用例里 JSON / SSE 两处 `X-Assistant-Trace-ID` 断言 |
     | `2c51d2f` | 11-09 08:49 | 前端：分路侧顶栏显示完整状态 | `app/server.py`（+60 / −108） | 见第 2 点 |

     扫描还列出 `cd2c1f5`、`e7a39fd`、`88b9a08` 三个提交，看 diff 后判断是有意改写，不属于覆盖。
  4. **测试为什么没拦住**。把相关提交的 `app/`、`tests/` 等目录导出到临时目录，各跑一次 `pytest tests/test_server.py tests/test_assistant.py`：

     | 提交 | 结果 | 说明 |
     | --- | --- | --- |
     | `ca5dc28`（第一次覆盖之前） | 71 passed | — |
     | `c5cf96f`（第一次覆盖） | 1 failed / 66 passed | 失败的是 `tests/test_server.py` 的澄清用例：`app/assistant.py` 已退回，澄清行为没有了 |
     | `e31e0d9`（第二次覆盖） | 66 passed | 上面那个失败用例被旧版 `tests/test_server.py` 盖掉，测试恢复全绿，回归从此不可见 |
     | `05b7ba8`（第三次覆盖之前） | 70 passed | — |
     | `2c51d2f`（第三次覆盖） | 1 failed / 69 passed | 失败的是第 1 点的确认用例 |

     第三次覆盖造成的失败一直留到 `e05542a`（其后又有 13 个提交；中间提交没有逐个回放，两端都失败），到本次开局跑全量测试才发现。
  5. **成因只能推断**。T-013 的记录写明当时的检出 `HEAD` 是 `27b28ea`（只跟踪 `BOOTSTRAP.md`、`ROLE.md`），源码全部是未跟踪文件；`e31e0d9` 的标题是整目录「上传最新版本」。推断：这几次会话的工作目录里有一批文件停留在旧状态，提交时整份盖到了更新的远端历史上。`REPORT.md` 第 5 节 2026-10-10 一条给出的恢复手法（`git fetch` + `git reset --mixed <远端tip>` 后重新提交）在工作树比远端旧的时候恰好会产生这种结果。git 历史只能证明「提交的内容等于旧版本加该会话自己的改动」，证明不了旧文件的来历。
  6. **本次恢复的内容**（立项登记另有提交 `5f815cb`，只改 `STATUS.md`）。
     - `0af3a01`：`app/server.py`。`git merge-file -p`（ours＝`05b7ba8` 版，base＝`7a88bd3` 版，theirs＝`e05542a` 版）退出码 0、无冲突；结果等于 `05b7ba8` 版加 `pausable` 一行。这一行是 `2c51d2f` 的有效新增（前端读取 `brFull.pausable`），予以保留。
     - `5f91b5d`：`tests/test_server.py` 放回被删的 53 行，即 `test_assistant_explicit_source_start_routes_to_bound_proposal_without_model` 里的两处 `X-Assistant-Trace-ID` 断言，和用例 `test_assistant_chat_returns_clarification_for_mismatched_model_tool_in_json_and_sse`。后者在当前代码上不通过（见第 8 点），按用户决定本任务不修，所以加 `xfail(strict=True)` 放回：它不计为失败；修复后它会因「意外通过」而报错，提醒删掉标记。
     - `164b852`：台账补录。`REPORT_TEST.md` 的 6 行索引与 T-014～T-017 正文、5 条会话纪要、`STATUS.md` 的 T-015～T-018 条目，均按 `ca5dc28` 版本逐字追加，没有改动现存行。逐行比对结果：现存行 0 删除，`ca5dc28` 的非空行 0 缺失。
     - 本专题所在的收尾提交：`REPORT.md` v0.12（第 5 节新增 1 条教训），以及随之重新生成的 `docs/软件设计文档.md`（该手册内嵌整份 `REPORT.md`）。
  7. **验证（命令 / 输出 / 判读）**。

     | 步骤 | 命令 | 输出 | 判读 |
     | --- | --- | --- | --- |
     | 基线 | `.venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider`（`e05542a`） | 1 failed / 638 passed / 1 skipped（188 s） | 失败即第 1 点的确认用例 |
     | 旧文件冒烟 | 用旧 `app/server.py` 起 `cli.py serve --host 127.0.0.1`，再 `curl -X POST http://127.0.0.1:<端口>/api/assistant/tools/confirm -H 'Content-Type: application/json' -H 'X-Assistant-Operator-Token: not-a-real-token' -d '{"proposal_id":"does-not-exist","confirmation_code":""}'`，分路侧路径同样一次 | 两个确认接口均 HTTP 500 `Internal Server Error`，服务日志 2 行 `TypeError`；`POST /api/assistant/chat`（内置模型）200，但没有 `X-Assistant-Trace-ID` 头 | 故障在真实进程上复现，而且发生在令牌校验之前 |
     | 恢复后冒烟 | 同上，在仓库当前代码上 | 两个确认接口均 HTTP 403 `{"ok":false,"error":"操作员令牌无效或已撤销"}`，服务日志 0 行 `TypeError`；问答接口 200，带 `x-assistant-trace-id: e3e0455fae4e15e6`，返回字段多出 `clarification` | 接口回到正常的鉴权拒绝。本步只走到令牌校验；有效令牌下的确认执行由 pytest 用例覆盖，没有在真实进程上做 |
     | 负对照 | 新 `tests/test_server.py` 配旧 `app/server.py`：`pytest tests/test_server.py` | 2 failed / 36 passed / 1 xfailed | 放回的 trace 断言（`assert 0 == 16`）和确认用例都在旧文件上失败，说明放回的断言确实在检查被恢复的行为 |
     | 定向 | `pytest tests/test_server.py` | 38 passed / 1 xfailed | — |
     | 全量 | `.venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs` | 639 passed / 1 skipped / 1 xfailed / 1 warning（190.90 s） | 无失败。skipped 是既有的 60 Hz 用例，xfailed 是上面的澄清用例，warning 是既有的 Starlette / httpx 弃用提示。运行时的代码即提交 `5f91b5d`，其后的提交只改 Markdown 文件；收尾提交前重跑一次，结果相同（192.13 s） |
     | 界面 | `node tools/ui_assistant_check.cjs` | `PASS 192 checks` | 需要先补齐 `node_modules/` 缺的 10 个文件，见遗留问题 |
     | 手册 | `.venv/bin/python tools/generate_assistant_docs.py --check` | 四份均 `OK` | — |
     | 自检 | `.venv/bin/python cli.py selftest` | 44 项通过 44 | 计算核心不受影响 |
     | `tmp/` | 对 `tmp/` 全部文件的 sha256 再求 sha256，开局与结束比对 | 一致 | 没有改动 `tmp/` |

  8. **没有恢复、现在仍然存在的问题**（均出自 `c5cf96f` 对 `app/assistant.py` 的覆盖；按用户决定本任务不修）。
     - **模型选错工具时不返回澄清**。按上面 xfail 用例的场景实测（在用例副本里加打印，`--runxfail` 运行）：用户输入「切换接线模式到3p4w」，模型却调用 `get_runtime_status` 并回答「操作已经完成。」。当前代码拦下了这次工具调用，没有生成操作提案（`proposal` 为 `null`，待确认队列为空），但 JSON 返回 `{"ok": true, "answer": "操作已经完成。", "sources": [], "proposal": null, "clarification": false}`，SSE 只有 `sources`、`delta`（文本同上）、`done` 三帧。用户看到的是模型未经核实的「操作已经完成」，而实际什么都没执行。`ca5dc28` 版本此时返回 `clarification: true` 和「我暂未创建操作预览。…」。非流式下若模型没有附带文字，则返回 HTTP 502「模型返回了空回答，请重试」。
     - **代码位置**：`app/assistant.py` 的 `complete()` 在校验不通过时把澄清文字写进 `plan["_clarification_response"]`，但没有改本次的返回值，函数接着返回模型原文；`stream()` 同样，并且文字在校验前已经逐段发出。`app/server.py:2403` 读取的是 `plan["_tool_clarification"]`，`app/assistant.py` 里已经没有任何地方给它赋值。
     - **T-017 路由诊断日志只剩服务端一半**。`app/server.py` 恢复后，`X-Assistant-Trace-ID` 响应头、`assistant_chat_received` 等请求日志和启动日志都在；`app/assistant.py` 里 T-017 列出的 7 种事件（`assistant_route_decision`、`assistant_route_diagnostic`、`assistant_tool_candidate`、`assistant_tool_decision`、`assistant_model_result`、`assistant_route_blocked`、`assistant_model_request`）出现次数为 0，服务端传入的 `payload["_assistant_trace_id"]` 没有代码读取。
     - **`tests/test_assistant.py` 少 5 个用例**。把 `ca5dc28` 版的这份测试放到当前代码上跑，27 passed / 5 failed。丢失的 5 个里，`test_finite_intent_contracts_cover_all_46_tools_and_examples`、`test_server_intent_gate_clarifies_ambiguity_missing_and_wrong_slots` 现在能通过；`test_model_tool_calls_are_gated_and_stream_text_is_buffered_until_validation` 失败在 `assert '暂未创建操作预览' in '操作已经完成。'`；`test_offline_source_playback_diagnostics_log_route_and_rejected_tool_without_values` 失败在 `KeyError: '_trace_id'`；`test_offline_source_playback_regression_corpus` 的全部语句断言都通过，只在最后一行 `plan["_tool_call_origin"]`（`KeyError`）失败，即 T-018 的启动语料行为还在，只是这个内部字段没有了。另外 2 个失败来自两边都有的用例（`test_tool_catalog_validation_and_closed_scope_proposal`、`test_explicit_source_start_bypasses_model_selection_but_keeps_confirmation`），从报错看是 11-06 后续提交有意改了 `claim_tool_proposal` 签名和侧别文案，不属于丢失。
     - **不能直接从旧版本合并**。对 `app/assistant.py` 做同样的三方合并会产生 13 个冲突块（486 行），`tests/test_assistant.py` 5 个冲突块（285 行），因为 11-06 的意图识别改造重写了同一片代码。澄清行为需要在当前代码上重新实现。
     - **文档与前端**。`docs/智能问答助手说明.md` 的 §6.8、§6.9 描述的正是上面缺失的澄清与诊断行为，所以没有放回，等代码修复后一起恢复。T-015 提到的前端澄清标记（`app/static/app.js`、`style.css`）和 README §3.6 / §11 的相应文字在取回的历史里从未提交过，无法从 git 恢复。
  9. **台账缺口**。`afd21dd`（11-06 03:53）之后到 `e05542a` 共 37 个提交没有任何台账记录。下面的索引依据提交标题和改动文件整理，功能没有逐项复核，也没有对应的专题报告；完整列表见 `git log --reverse afd21dd..e05542a`。
     - **11-06，23 个（`c74f6c1` ～ `05b7ba8`），智能问答助手**。意图识别按设计文档 V2.0 改造：`c74f6c1`、`af802fb`、`8ad80fc`、`cd2c1f5`、`7d93fc2`、`9ef75bd`（`recognize_intent` 接入 `prepare_chat` 并对全部 46 个受控工具生效）。跨侧操作的侧别绑定：`928899d`、`bc4e329`、`5be8837`、`5b490c6`、`568083f`、`226ab56`、`c01a5d6`、`06b2baa`、`6aff7c0`、`24f2d09`。`get_runtime_status` 无输出：`03b97ea`、`e592aef`。意图契约外置到 `configs/intent_actions.csv`：`3d81987`、`8de1e35`。录波文件查询与模型路径语义核验：`8f50318`、`e7a39fd`、`05b7ba8`。改动文件：`app/assistant.py`、`app/assistant_intents.py`、`app/assistant_tools.py`、`app/server.py`、`configs/intent_actions.csv`、`.gitignore`、两份助手测试。
     - **11-09，13 个（`2c51d2f` ～ `e9bf4e7`），前端**。顶栏双侧状态与暂停 / 停止按钮：`2c51d2f`、`511b93c`、`2d82768`、`4e2c84c`。数据处理页 5 个功能模块改为内部子界面：`2681e6e`、`88b9a08`、`678f6c8`、`1810165`、`b02e35c`、`a43edf0`、`97954b5`。波形预览曲线标题：`f7f9806`、`e9bf4e7`。改动文件：`app/static/app.js`、`index.html`、`style.css`，以及 `2c51d2f` 里的 `app/server.py`。
     - **11-10，1 个**：`e05542a`，只改了 `tmp/` 下 22 个文件。
- **是否进入 REPORT.md（稳定结论）**：是。第 5 节新增 1 条工程教训（v0.12）。
- **遗留问题**：
  1. 第 8 点各项：修复澄清返回、恢复 T-017 诊断日志、补回 5 个用例、恢复说明书 §6.8 / §6.9、补前端澄清标记。修复后删除 `tests/test_server.py` 里的 `xfail` 标记。
  2. 远端 `restore_branch_full_history`（`22d8d9c`）比本分支基线多 3 个提交（`bbf7fca`、`63a2378`、`22d8d9c`，波形分析子界面，只改 `app/static/`）。按用户决定本任务没有合入。
  3. `README.md` 第 15、72 行让用户克隆 `arena/82e34fb8-nilm-calc-tool`，该分支现在指向 `27b28ea`，只有 `BOOTSTRAP.md` 和 `ROLE.md`，没有代码。哪条分支是正式分支需要用户确定，README 本任务未改。
  4. `README.md` 仍标 v0.99.48（2026-11-04）。11-06 新增的 `configs/intent_actions.csv` 在 README、助手说明书、意图识别设计文档里都没有提到；11-09 的界面改动是否已写入文档没有核对。
  5. 入库的 `node_modules/` 缺 10 个文件：`.gitignore` 第 10 行的 `data/` 没有限定在根目录，把 `node_modules/**/data/` 也忽略了。干净克隆下 `node tools/ui_assistant_check.cjs` 报 `Cannot find module '../data/patch.json'`。本次的做法是在仓库外执行 `npm ci`，再把这 10 个文件拷进来（它们被忽略，不会入库）。
  6. 全量 pytest 会在当前目录留下 `data/`、`output/` 两个目录（都被 `.gitignore` 忽略）。本次每次运行后已删除。
  7. `elec_tool.__version__` 是 `0.1.0`，README 写 v0.99.48，两处版本号不一致。
  8. 用户 2026-10-31 报告的「设备画像提取提示 HTTP 500」（`POST /api/process/nilm_profile`）仍未结，`STATUS.md` 记录的状态是等服务端 traceback；本次未处理。
  9. 真实模型（Qwen / 云端）、真实浏览器、Windows 部署环境均未验证。

## [2026-11-10] 专题 T-020：模型选错工具时不返回澄清的回归修复（放回 T-015 门控与 T-017 排查日志，新增前端澄清标记）

- **类型 / 模式**：用户专题（实现＋验证）；模式 A（沙盒自执行），角色为工程实现工程师。分支 `arena/51b63974-nilm-calc-tool`，开局远端 tip `161bd00`。没有连接真实模型、真实浏览器和用户部署环境；模型响应全部是测试里的假响应。
- **目标与假设**：用户指令「澄清回归立即修」。缺陷见 T-019 第 8 点：用户说「切换接线模式到3p4w」，模型却调用 `get_runtime_status` 并回答「操作已经完成。」，接口把模型这句话当作回答返回（模型没有文字时返回 502），`clarification` 恒为 `false`，SSE 没有澄清帧。完成标准取 `STATUS.md`「下一步」原先登记的 5 点：① 修 `complete()` / `stream()` 与 SSE 澄清帧，删除 `xfail` 标记；② 补回 `tests/test_assistant.py` 丢失的 5 个用例；③ 恢复 T-017 的 7 种路由日志并接上请求追踪号；④ 放回说明书 §6.8 / §6.9；⑤ 做前端澄清标记。用户原话只对应第 ① 点，②～⑤ 是按已登记的标准一并做的。
- **方法 / 数据 / 参数**：
  - **重写而不是合并**。T-019 已查明从旧版本三方合并会有 13 个冲突块，所以在当前代码上重写门控，行为对照 `ca5dc28` 版的测试和说明书。
  - **门控 `_accept_tool_calls`**（`app/assistant.py`）。模型的工具调用只是候选，依次检查：恰好一个调用，否则澄清；工具名非空、已注册、在本轮授权清单内，否则 HTTP 403；用 `validate_model_tool_result` 对照**本轮用户原话**核对意图与参数（修复前取的是对话里最早的一条用户消息），不通过就写入澄清文字、不留提案。`get_runtime_status`、`get_runtime_settings`、`list_recordings` 三个工具的 schema 没有 `side`，模型多传的 `side` 在核对前去掉，与 `validate_tool_arguments` 的既有约定一致（常量 `SIDE_ARGUMENT_IGNORED_TOOLS`）。
  - **回答文字**。模型一旦调用工具，回答只用服务端文字：通过时是「已识别为「…」。请核对操作摘要与影响，再确认执行。」，否则是澄清；模型自己的文字不外发。流式响应在向模型提供了工具时先攒文字，模型输出结束后再决定放出还是丢弃。实测的 SSE 帧顺序：澄清时为 `sources`、`delta`、`clarification`、`done`；生成提案时（确定性路由）为 `sources`、`delta`、`proposal`、`done`。
  - **日志**。放回 7 种事件：`assistant_route_decision`、`assistant_route_diagnostic`、`assistant_route_blocked`、`assistant_tool_candidate`、`assistant_tool_decision`、`assistant_model_request`、`assistant_model_result`。追踪号沿用 `app/server.py` 写进响应头 `X-Assistant-Trace-ID` 的那一个。`validate_model_tool_result` 的每种拒绝带固定原因码。字段与级别见说明书 §6.9。
  - **前端**。收到 SSE `clarification` 帧或 JSON `clarification: true` 时，在回答正文上方显示「待澄清：未创建操作预览」，消息加琥珀色边框；会话重画后标记仍在（`app/static/app.js`、`app/static/style.css`）。
  - **验证手段**。pytest（假模型响应）；负对照（把修复的文件临时换回修复前的版本）；jsdom 界面检查及其负对照；在真实 `cli.py serve` 进程上观察日志。
- **用户执行命令（含实录路径）**：本节无用户命令。全部命令在沙盒执行，输出摘录见下，没有单独的实录文件。
- **结果 / 结论**：
  1. **验收用例通过**。`tests/test_server.py::test_assistant_chat_returns_clarification_for_mismatched_model_tool_in_json_and_sse` 去掉 `xfail` 标记后通过：JSON 响应 `clarification` 为 `true`、`proposal` 为 `null`、回答含「暂未创建操作预览」；SSE 有 `delta` 和 `type=clarification` 帧，没有 `proposal` 帧。
  2. **提交**。`1cabfb6`：`app/assistant.py`、`app/assistant_intents.py`、`app/assistant_tools.py` 和两个测试文件。`03a2854`：前端标记、`tests/test_web_ui.py`、`tools/ui_assistant_check.cjs`。`0f37e54`：只改 `app/assistant.py` 里的一段注释（见第 7 点）。`c912674`：说明书、README、三份重新生成的手册，以及 `tests/test_server.py` 里的一段注释（见第 8 点）。`48a16de`（收尾）：说明书已知限制改写两条、新增一条，README 相应三处，重新生成两份手册（见第 8 点末段和 T-021 的补-A10）。立项登记 `eda5357` 只改 `STATUS.md`。
  3. **测试改动**。
     - `tests/test_assistant.py` 由 32 个用例增至 45 个。放回 `c5cf96f` 覆盖时丢失的 5 个：`test_finite_intent_contracts_cover_all_46_tools_and_examples`、`test_server_intent_gate_clarifies_ambiguity_missing_and_wrong_slots`、`test_model_tool_calls_are_gated_and_stream_text_is_buffered_until_validation`、`test_offline_source_playback_diagnostics_log_route_and_rejected_tool_without_values`、`test_offline_source_playback_regression_corpus`。新增 7 个：`test_intent_gate_rejections_carry_a_fixed_reason_code`、`test_normalised_tool_arguments_pass_validation_again_unchanged`、`test_model_tool_gate_checks_this_turns_message_not_the_history`、`test_model_tool_gate_handles_several_calls_unlisted_tools_and_a_stray_side_argument`、`test_model_text_is_replaced_for_accepted_tool_calls_and_held_until_the_model_finishes`、`test_route_and_gate_logs_follow_the_request_trace_id_and_carry_no_user_text_or_values`、`test_model_request_log_has_metadata_only`。
     - 另给 `test_expanded_tool_allowlist_is_closed_and_model_context_contains_only_safe_resource_ids` 补回 `def` 行。这一行此前丢失，函数体接在上一个用例的尾部，没有作为独立用例运行；这是我的判断，补回后该用例通过。
     - `tests/test_server.py` 由 39 增至 40：澄清用例去掉 `xfail`；新增 `test_assistant_chat_trace_id_header_matches_the_assistant_route_and_gate_logs`。`tests/test_web_ui.py` 的助手契约用例增加 3 条 `assert`（共 4 个字符串条件）。`tools/ui_assistant_check.cjs` 新增 13 项检查（192 → 205）。
  4. **验证（命令 / 输出 / 判读）**。

     | 步骤 | 命令 | 输出 | 判读 |
     | --- | --- | --- | --- |
     | 开局基线 | `.venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs`（`161bd00`） | 639 passed / 1 skipped / 1 xfailed | xfailed 即待修的澄清用例 |
     | 负对照（服务端） | 把三个 `app/assistant*.py` 文件换回 `eda5357` 的版本，`pytest tests/test_assistant.py tests/test_server.py`，再换回并用 sha256 核对 | 11 failed / 74 passed | 失败的是 `tests/test_assistant.py` 9 个、`tests/test_server.py` 2 个，都是本次放回或新增的用例，说明它们确实在检查被修复的行为。2026-11-10 写本节时重跑得到这组数字 |
     | 定向 | `pytest tests/test_assistant.py tests/test_server.py tests/test_web_ui.py` | 109 passed | 当前代码 |
     | 全量 | `.venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs` | 654 passed / 1 skipped / 1 warning | 无失败、无 xfail。skipped 是既有的 60 Hz 用例，warning 是既有的 Starlette / httpx 弃用提示。`03a2854` 上 174.50 s。收尾时又跑了两次，结果相同：`c912674` 上 169.77 s，`48a16de`（最终的代码与文档内容）上 168.68 s |
     | 界面 | `node tools/ui_assistant_check.cjs` | `PASS 205 checks` | 不在 pytest 里，需单独运行；要先补齐 `node_modules/` 缺的 10 个文件 |
     | 负对照（前端） | 把 `app/static/app.js` 换回 `1cabfb6` 的版本再跑上一条，随后换回 | `FAIL: Error: SSE clarification 帧没有显示澄清标记` | 新增的检查确实在检查标记。2026-11-10 写本节时重跑得到 |
     | 日志可见性 | `cli.py serve --host 127.0.0.1 --port <端口>`，默认级别和 `--log-level info` 各起一次，发问答请求，看标准错误 | WARNING 行出现，只有消息正文；INFO 行（`assistant_route_decision`、`proposal_created`、`服务启动 …`）一行都没有 | 见第 5 点 |
     | INFO 的启动方式 | `python -c "import logging, sys, cli; logging.basicConfig(level=logging.INFO, style='{', format='{asctime} {levelname} {name} {message}'); sys.exit(cli.main(['serve', '--host', '127.0.0.1', '--port', '18796']))"`，发一次 builtin 问答 | 标准错误出现 `服务启动 …`、`assistant_chat_received trace_id=4d0bda039d079c1a …`、`assistant_route_decision trace_id=4d0bda039d079c1a … decision=backend_not_tool_capable`；响应头追踪号相同 | 不改代码也能看到 INFO 行；已写入说明书 §6.9 |

  5. **日志在默认启动方式下大部分看不到**。仓库里没有任何地方给 `elec_tool.*` 记录器配置输出（`ca5dc28` 时也没有），所以 `python cli.py serve` 下 WARNING 及以上的行靠 Python 的兜底处理器打到标准错误，INFO 行全部丢弃；`--log-level` 只管 uvicorn 自己的日志。因此有两句旧说法需要更正。旧说明书 §6.9（`ca5dc28` 版）写「以 `python cli.py serve --log-level info` 启动」可查看普通路由日志和启动信息，实测看不到。T-017「现场判读方法」写「完全没有该 ID 的日志，说明处理请求的进程未载入本版本」，这只对含「离线＋数据源＋播放 / 启动 / 开始 / 运行」的请求成立（它们按 WARNING 写）；其他请求在正常生成提案或普通回答时只写 INFO 行，本来就没有输出。说明书 §6.9 按实测重写，没有照搬旧文。是否给 `cli.py serve` 加日志输出（约 8 行代码加 1 个用例）待用户决定，本次没有改。
  6. **与 T-015 / T-017 原样不同、由我决定的地方**。
     - 说明书 §6.8 / §6.9 是重写的。旧 §6.8 说契约规则会写进发给模型的工具描述，当前代码没有这样做（`tool_intent_hint()` 无人调用，本次也没有接回）；旧 §6.9 关于 `--log-level info` 的一句见第 5 点。另新增 §6.10。
     - 日志词表比 T-017 多：`decision=intent_direct`、`origin=intent`、`outcome=read_executed`、`outcome=empty`、`reason=proposal_rejected`，字段 `target_side`、`intent_tier`、`side_argument`、`bound_side`、`route`，以及更细的澄清原因码。原因是 11-06 之后多了意图识别直达和跨侧两条逻辑。
     - 前端标记是新做的。T-015 提到的原始实现从未入库，没有可参照的样子；本次取最小做法（一行标签加边框）。
     - 意图识别直达与确定性路由对侧别的处理没有改；模型路径仍把提案绑定在提问页面所在的一侧（T-021 的补-A5）。
  7. **一处自我更正**。`1cabfb6` 里我写的注释称「两个只读状态工具在 medium tier 也直接路由」。实测「查看当前运行状态和计算配置」（两个候选同为 46 分，tier 为 low）时日志是 `decision=intent_direct direct_tool=get_runtime_settings intent_tier=low` 和 `outcome=read_executed`，即任何 tier 都直接执行。`0f37e54` 更正了这段注释；修改前后 `ast.dump(ast.parse(源码))` 完全相同，没有改任何语句。
  8. **文档措辞会改变知识库检索，并曾让验收用例失败**。写 README §11 的本轮条目时，我先照抄了验收用例的提问「切换接线模式到3p4w」和假模型的自述「操作已经完成。」。README 整份进入 `docs/软件使用文档.md`，后者是知识库文档；检索按约 900 字分块、TF-IDF 余弦相似度、取前 4 段、阈值 0.08。结果这一段成了该提问唯一命中的片段（得分 0.170；改文档前该提问命中 0 段），出现在 SSE 的 `sources` 帧里，验收用例最后一条断言（整个 SSE 文本不含「操作已经完成」）随之失败：三个助手测试文件 1 failed / 108 passed。真实运行时这个片段还会进入发给模型的上下文，等于把「调用查询状态的工具并说已完成」这段描述摆在模型面前。处理：README 改成不照抄原话的概述（原话只留在本文件，本文件不在知识库里）；断言没有放宽，只在它前面加了说明注释（`ast.dump` 前后相同）。改后该提问命中回到 0 段，三个助手测试文件 109 passed。
     同一次测量里的其他变化（共试 8 个提问，对比文档修改前后各自命中的前 4 段）：「怎么修改意图配置」由 0 段变为 4 段，都含这次新写的意图配置说明；「查看后台重采样任务状态」「暂停分路侧数据源」新命中说明书 §6.8 的已知限制和跨侧说明；「启动数据源」的第 4 段换成了 README「快速开始」一段（那里改了取代码的注释）；另外 4 个提问没有变化。前三项是这次写文档想要的效果。README 的验证记录和变更记录一直整段在知识库里（改文档前，「暂停分路侧数据源」的第 4 段就是 v0.13.1 的变更记录）；是否应把它们排除出知识库，本次没有评估。
     收尾时又清了一次（`48a16de`）。README §3.6 和说明书 §6.8 各有一句还带着假模型的原话「操作已经完成」。当时用例能通过，只是因为这两段没有被验收提问检索到：知识库按字符位置顺序分块（每块约 900 字、重叠 120 字），文档任何一处改动都会让它后面的分块边界移动，这句话一旦和说明书里「接线模式切换到3p4w」的例句落进同一块并被检索到，最后一条断言就会再次失败。改写前，「查看后台重采样任务状态」命中的第 4 段就带着这句原话。两处改写后，README、说明书、`REPORT.md`、调参手册、数据字典里都不再有这句原话；验收提问仍命中 0 段，三个助手测试文件 109 passed。
- **是否进入 REPORT.md（稳定结论）**：否。属于产品工具路由与可观测性，不是算法结论。
- **遗留问题**：
  1. **流式响应里模型的工具调用完全不带 `arguments`**：拼出来是空串，按 `arguments_not_json` 澄清；非流式的同样情况缺省为 `{}`，按空参数处理。两条路径不一致，本次没有改，也没有用例。
  2. **INFO 级路由日志默认不可见**（第 5 点）。
  3. **真实模型没有测**。假响应只能验证服务端拿到某种模型输出后的行为，不能说明真实 Qwen 或云端模型会不会选对工具。
  4. **前端标记没有在真实浏览器里看过**，只有 jsdom 的 DOM 断言和 CSS 字符串断言；颜色、位置、窄屏表现未知。
  5. `node tools/ui_assistant_check.cjs` 不在 pytest 里，干净克隆下还缺 10 个 `node_modules` 文件（T-019 遗留 5），容易被漏跑。

## [2026-11-10] 专题 T-021（补记）：2026-11-06 智能问答 23 个无台账提交的事后核对（意图识别直达、跨侧操作、状态直接返回、意图配置外置）

> **补记说明**：本节写于 2026-11-10，依据是 23 个提交的 diff 和在当前代码上的复测，不是 2026-11-06 当时的实录。当时的用户原话、设计讨论、每个提交提交时跑过什么测试，都没有记录可查，本节不作推测。凡标「实测」的是 2026-11-10 在提交 `0f37e54` 的代码上运行得到的；标「读代码」的只读了 diff 或源码，没有运行。

- **类型 / 模式**：验证专题（事后补记）；模式 A（沙盒自执行），角色为工程实现工程师。没有连接真实模型、真实浏览器和用户部署环境。
- **目标与假设**：用户指令「11-06 到 11-09 有 37 个提交补充台账记录」。本节覆盖其中 2026-11-06 的 23 个（`c74f6c1` ～ `05b7ba8`，UTC 03:59 ～ 16:57），全部是智能问答助手；11-09 的 13 个前端提交和 11-10 的 1 个见 T-022。目标是写清每组提交改了什么、现在的代码是否还是那样、有哪些问题。
- **方法 / 数据 / 参数**：
  - 逐个读 `git show <提交>`（23 个都读了）。
  - 对读出来的可疑路径写脚本探查：直接调用 `AssistantService.prepare_chat` 或经 FastAPI `TestClient` 走 HTTP 接口；模型调用用假响应或不触发；数据目录用临时目录；操作员令牌的 scope 和启用的工具按各项探查设置：多数探查带全部 scope、46 个工具全部启用，权限与审计两项探查按需收窄。脚本在 `/tmp` 下，没有入库。
  - 没有把仓库回退到这 23 个提交各自的状态去运行。唯一的逐提交证据是 T-019 第 4 点：`05b7ba8` 上两份助手 / 服务端测试 70 passed。
  - 2026-11-10 收尾时把本节标「实测」的各条重跑了一遍，并让两侧处于不同的运行状态再试跨侧操作：改正了补-A4、补-A9 两条里写得不准的前提，新发现补-A10。
- **用户执行命令（含实录路径）**：本节无用户命令。
- **结果 / 结论**：
  1. **各组提交做了什么**（读 diff）。

     | 组 | 提交（UTC 时间） | 改动 | 当时是否加了测试 |
     | --- | --- | --- | --- |
     | 意图识别 V2.0 | `c74f6c1`（03:59）、`af802fb`（04:05） | 系统提示词改写为 10 条编号规则；`app/assistant_intents.py` 新增置信度常量（`CONFIDENCE_HIGH` 0.80、`CONFIDENCE_MED_LOW` 0.55、前两名最小分差 `CONFIDENCE_GAP_MIN` 0.15）、置信度归一与分档函数、识别结果的 schema（`INTENT_RECOGNITION_RESULT_SCHEMA`）及其构造 / 校验函数（`c74f6c1`）；候选召回 `find_tool_intent_candidates`（top-k）、置信度融合 `fuse_confidence`、缓存 `_IntentCache`（有效期 3600 秒）、入口 `recognize_intent`（`af802fb`） | 否 |
     | 阶段 B 直达 | `8ad80fc`（04:12）、`cd2c1f5`（05:21）、`7d93fc2`（05:35）、`9ef75bd`（05:41） | `recognize_intent` 接进 `prepare_chat`：确定性路由没命中时先做意图识别，高置信且工具可不带参数调用就直接生成提案、不调用模型。起初只对 4 个数据源工具，`cd2c1f5` 扩到所有可不带参数的工具；`7d93fc2` 让停止 / 启动动词互斥，只有一个候选且 ≥ 40 分即算高置信；`9ef75bd` 补短目标词（录波、调参、重采样、画像、自检） | 否 |
     | 跨侧操作 | `928899d`（06:26）、`bc4e329`（06:36）、`5be8837`（06:48）、`5b490c6`（06:55）、`568083f`（07:11）、`226ab56`（07:21）、`c01a5d6`（07:33）、`06b2baa`（07:50）、`6aff7c0`（08:07）、`24f2d09`（08:50） | 从话里解析侧别、延时指令拒绝、排他限定词检测（`928899d`）；认领 / 取消 / 执行不再与请求所在侧比较（`bc4e329`、`5b490c6`）；`engine_start/pause/resume/stop` 增加 `side` 参数，确定性短命令接受「只 / 分路侧 / 总线侧 / 的」（`5be8837`、`568083f`）；跨侧的停止 / 暂停 / 恢复跳过「是否在运行」的预检（`226ab56`）；提示文字和摘要用目标侧的标签与数据（`c01a5d6`、`06b2baa`、`6aff7c0`）；确认时按提案记录的侧执行（`24f2d09`） | 没有新增用例，改了既有用例：`bc4e329` 删掉「从另一侧认领会被拒绝」的断言；`c01a5d6` 把一处期望文字改为「启动分路侧数据源检测」；`24f2d09` 把 `tests/test_server.py::test_assistant_proposal_confirm_is_branch_scoped_and_reauthorized` 里跨侧确认的期望由 HTTP 409 改为 200 并按分路侧执行，另把 `test_assistant_explicit_source_start_routes_to_bound_proposal_without_model` 里的一处期望文字改为「启动分路侧数据源检测」 |
     | 状态直接返回 | `03b97ea`（09:17）、`e592aef`（09:40） | 阶段 B 识别为 `get_runtime_status` / `get_runtime_settings` 时直接执行并把结果作为回答，不生成提案；动词加「获取」；这两个工具忽略模型多传的 `side` | 否 |
     | 意图配置外置 | `3d81987`（10:01）、`8de1e35`（10:28） | 46 条意图契约从 `app/assistant_intents.py` 移到 `configs/intent_actions.csv`（`.gitignore` 加例外、CSV 读取函数、4 个 `test_intent_config_*` 用例）；`8de1e35` 给文件加 UTF-8 BOM 并改用 `utf-8-sig` 读取 | `3d81987` 加 4 个用例 |
     | 录波 / 画像混淆 | `8f50318`（16:35）、`e7a39fd`（16:47） | `list_recordings` 只接受 `folder`，未知字段的报错写得更清楚；系统提示词第 5 条区分 `list_recordings` 与 `list_profiles`；CSV 里 `list_recordings` 一行加「获取」「文件路径」 | 否 |
     | 模型路径核对 | `05b7ba8`（16:57） | 模型选的工具与用户意图不符时拦下工具调用。只做了一半：拦下后仍把模型原话当回答返回（T-019 第 8 点），已由 T-020 的 `1cabfb6` 取代 | 否 |

  2. **其中一部分曾经丢失**。跨侧一组里 `bc4e329`、`5be8837`、`5b490c6`、`568083f`、`c01a5d6`、`6aff7c0`、`24f2d09` 对 `app/server.py` 的修改，在 2026-11-09 被 `2c51d2f` 用旧文件盖掉，2026-11-10 由 `0af3a01` 恢复（T-019）。也就是说 `2c51d2f` ～ `e05542a` 之间的代码里，助手的确认接口每次调用都抛 `TypeError`（HTTP 500），任何提案都无法确认。
  3. **现在仍然成立的行为**（实测，经 `TestClient` 走 HTTP 接口，两侧都未运行、数据源为模拟器）。

     | 请求端点 | 输入 | 结果 |
     | --- | --- | --- |
     | `/api/assistant/chat` | 启动分路侧数据源 | 提案 `start_current_source`，`side=branch`，摘要「启动分路侧已配置的数据源」 |
     | `/api/assistant/chat` | 停止分路侧数据源 | 提案 `stop_current_source`，`side=branch` |
     | `/api/branch/assistant/chat` | 启动总线侧数据源 | 提案 `start_current_source`，`side=bus` |
     | `/api/assistant/chat` | 启动数据源 | 提案 `start_current_source`，`side=bus`（没有侧别词，取提问页面所在侧） |

     分路侧创建的提案从总线侧端点确认，按分路侧执行：既有用例 `test_assistant_proposal_confirm_is_branch_scoped_and_reauthorized` 通过。`configs/intent_actions.csv` 的读取与 46 条契约的一致性：`pytest tests/test_assistant.py -k intent` 为 7 passed。
  4. **核对出的问题**（编号「补-A」；均未修，是否修由用户决定）。

     | 编号 | 来源提交 | 问题 | 证据 |
     | --- | --- | --- | --- |
     | 补-A1 | `928899d` | 延时指令检查把单个「后」字当成延时。前两条直达路由上，「查看后台重采样任务状态」「取消后台重采样」「查询最后10条电能质量事件」返回 HTTP 400「请求包含延时执行指令…」；「查看当前重采样任务状态」「列出当前电能质量事件」正常生成提案。46 个工具的标题和正例里没有被误伤的，所以现有测试发现不了 | 实测 |
     | 补-A2 | `928899d` | 侧别词按子串匹配，先出现的优先。在分路侧页面说「查看 Modbus 运行状态」，返回的是总线侧状态（「Modbus」含「bus」）；「对比总线侧和分路侧」取总线侧 | 实测 |
     | 补-A3 | `928899d` | 提交标题里的「排他性限定词」「服务端侧别复验」没有实现完：`_has_exclusive_limit` 的结果和解析出的侧别写进了计划的 `_exclusive_limit`、`_parsed_side` 两个键，但 `app/` 下没有任何代码读取它们 | 读代码（全文搜索） |
     | 补-A4 | `8ad80fc`、`cd2c1f5` | 同一个意思走不同路由，结果不同。在总线侧页面提问、传入的数据源上下文为模拟器时，「启动分路侧数据源检测」返回 HTTP 409「分路侧配置不是离线文件数据源…」；「启动分路侧数据源」「启动当前侧数据源检测」「播放数据源」在同样条件下生成提案。前者走意图识别直达，那里对 `start_current_source` 一律要求文件数据源；后者走确定性路由，只在话里明确提到离线播放时才这样要求（「播放离线数据源」同样返回 409）。这项检查读的也是提问页面一侧的上下文，见补-A10 | 实测 |
     | 补-A5 | 跨侧一组 | 跨侧只做到了前两条直达路由。模型路径生成的提案绑定在提问页面所在的一侧：在总线侧页面说「把分路侧接线模式切换到3p4w」，假模型返回 `set_wiring_mode`，得到的提案 `side=bus`，卡片摘要是「将总线侧接线模式切换为 3p4w」；日志里 `target_side=branch`、`bound_side=bus`。确认是按提案记录的侧执行的，所以确认后改的会是总线侧（确认这一步没有运行） | 实测（到生成提案为止） |
     | 补-A6 | `cd2c1f5` | 意图识别直达只在识别出的工具属于操作员本轮可用清单时才介入；工具没授权时不报错，请求转入模型路径。直达分支里 5 处「工具不可用」的 403 检查因此走不到。确定性路由在同样情况下返回 403，并说明缺少的权限 | 实测 |
     | 补-A7 | `03b97ea`、`e592aef` | `get_runtime_status` / `get_runtime_settings` 被直接执行：回答是一行说明加 JSON 原文，没有提案和确认，也**不写 `tool_audit.jsonl`**（对照：`get_event_list` 会生成提案并写 `pending_confirmation` 记录）。`e592aef` 的注释写「只要不是 low」，代码没有这个条件：「查看当前运行状态和计算配置」两个候选同为 46 分、tier 为 low，仍直接执行了排在首位的 `get_runtime_settings`，状态没有返回 | 实测 |
     | 补-A8 | `8de1e35`、`e7a39fd` | `8de1e35`（10:28）为「Excel 打开中文乱码」加的 BOM，被当天 16:47 的 `e7a39fd` 去掉了。各版本文件头三个字节：`3d81987` 为 `74 6f 6f`，`8de1e35` 为 `ef bb bf`，`e7a39fd` 和当前为 `74 6f 6f`。`e7a39fd` 的标题没有提到这一点，是否有意无从判断。读取端用 `utf-8-sig`，有没有 BOM 都能读 | 实测（文件字节）；Excel 里的显示没有条件验证 |
     | 补-A9 | `226ab56` | 跨侧的暂停 / 恢复 / 停止在生成提案时不检查目标侧的运行状态，留到确认时才检查。同侧说「暂停数据源」「停止数据源」而数据源未运行，返回 HTTP 409；在总线侧页面说「暂停分路侧数据源」「恢复分路侧数据源」而分路侧未运行，照样生成提案，确认时才返回 HTTP 400「数据源未在运行」；「停止分路侧数据源」确认后返回成功「分路侧数据源已停止」，当时并没有在运行。（同侧的「恢复数据源」只在数据源正在运行时被拒绝，未运行时同样生成提案，这一点与跨侧无关。） | 实测（`TestClient`，两侧都未运行） |
     | 补-A10 | `928899d`、`226ab56` | 跨侧「启动」的前置检查读的是提问页面所在一侧的状态，不是目标侧。① 总线侧在运行、分路侧未运行：在总线侧页面说「启动分路侧数据源」返回 HTTP 409「分路侧数据源已在运行或暂停，不会重复启动…」，而分路侧并没有运行；「启动分路侧数据源检测」「启动分路侧已配置的数据源」「播放分路侧数据源」同样被拒，日志里 `route=deterministic` 和 `route=intent` 都有。此时在分路侧页面说「启动数据源」可以生成提案。② 分路侧在运行、总线侧未运行：在分路侧页面说「启动总线侧数据源」同样被 409 误拒；在总线侧页面说「启动分路侧数据源」则生成提案，确认时才返回 HTTP 409「当前侧数据源已在运行；助手不会自动停止或重启它」。原因：服务端只为提问页面所在的一侧准备数据源上下文（`_assistant_tool_context(current_side())`）。`226ab56` 的注释写明了这一点，并给暂停 / 恢复 / 停止加了跨侧豁免（即补-A9），但没有处理启动。数据源类型、文件是否存在两项检查读的是同一个上下文（读代码，没有单独实测）。本条是 2026-11-10 收尾复核补-A9 时发现的：此前的跨侧探查两侧都处于未运行状态，看不出读错了侧 | 实测（`TestClient` 走 HTTP 接口，模拟器数据源，两侧运行状态不同） |

  5. **没有核对的**。意图识别对真实口语的识别率（只有契约自带的正例 / 反例和少量手写句子）；缓存 `_IntentCache` 在配置或上下文变化后的行为；云端模型通道（`model_type=cloud`）下的直达；并发；真实模型。阶段 B 这一批提交当时没有加测试，现在覆盖它的用例主要是 T-020 新增的日志与门控用例，直达分支里各工具的前置检查没有逐个测试。另有一处只看到、没有评估的现象：跨侧提案的 `title` 字段仍是工具目录里的固定标题（如「启动当前侧数据源检测」），`summary` 写的是目标侧（「启动分路侧已配置的数据源」）；两者同时显示在卡片上的观感没有看过。
- **是否进入 REPORT.md（稳定结论）**：否。
- **遗留问题**：补-A1 ～ 补-A10 均未修，登记在 `STATUS.md`「下一步」。我的判断是 补-A5（确认后改错侧）、补-A10（总线侧运行时无法从总线侧页面启动分路侧）和 补-A1（正常查询被拒）对使用影响最大，补-A7 涉及审计完整性；先修哪些由用户决定。

## [2026-11-10] 专题 T-022（补记）：2026-11-09 前端 13 个无台账提交的事后核对（顶栏双侧状态与控制、数据处理页五个子界面、波形预览标题），附 2026-11-10 的 1 个数据提交

> **补记说明**：本节写于 2026-11-10，依据是提交的 diff、当前代码和少量复测，不是 2026-11-09 当时的实录。这些改动全部是界面改动，而本环境没有真实浏览器：下面没有任何一条结论来自「在浏览器里看到」。标「实测」的是 2026-11-10 用 jsdom 或 pytest 运行得到的；标「读代码」的只读了 diff 或源码。

- **类型 / 模式**：验证专题（事后补记）；模式 A（沙盒自执行），角色为工程实现工程师。
- **目标与假设**：用户指令「11-06 到 11-09 有 37 个提交补充台账记录」中 2026-11-09 的 13 个（`2c51d2f` ～ `e9bf4e7`，UTC 08:49 ～ 16:47）和 2026-11-10 的 `e05542a`。11-06 的 23 个见 T-021。
- **方法 / 数据 / 参数**：
  - 逐个读 `git show <提交>`（14 个都读了），再读当前的 `renderTop`、`togglePause`、`stopEngine`、`renderProcess`、`bindProcess`、`initCtEstimate` 和 `.sub-nav` 样式。
  - 运行与这些界面有关的既有 pytest 文件。
  - 把提交 `03a2854` 导出到临时目录（`git archive`），用 `tools/gen_nilm_sample.py --bus` 生成 `data/nilm_bus_mixed.csv`，起真实的 `cli.py serve`，运行既有的 jsdom 脚本 `tools/ui_r61_check.cjs`（波形预览）；再对改版前的最后一个提交 `4e2c84c` 做同样的事，比较两边的结果。
  - 用 jsdom 把 `initCtEstimate` 单独取出来调用两次，数各按钮触发了几次处理函数。
  - 把 `stopEngine`、`togglePause`、`api`、`apiUrl` 四个函数从 `app.js` 取出，在 node 里配假的 `fetch` 和页面状态运行 8 种情形（两种视图、单侧 / 双侧运行、服务端返回成功或 HTTP 400），记录发出的请求和提示文字。
- **用户执行命令（含实录路径）**：本节无用户命令。
- **结果 / 结论**：
  1. **各组提交做了什么**（读 diff）。

     | 组 | 提交（UTC 时间） | 改动 |
     | --- | --- | --- |
     | 顶栏双侧状态与控制 | `2c51d2f`（08:49）、`511b93c`（09:13）、`2d82768`（09:33）、`4e2c84c`（10:06） | 总线侧视图定时取 `/api/branch/state` 存入 `S.branchFullState`，顶栏分路侧一行由简要摘要改为完整状态（`2c51d2f`；同一提交里的 `app/server.py` 是旧文件覆盖，只有 `pausable` 一行是有效新增，见 T-019）。「暂停」「停止」可以作用于正在运行的分路侧（`511b93c`）。任一侧在运行时「启动」「加载上次数据」禁用、「停止」可用（`2d82768`）。两侧都在运行时「暂停」「停止」同时作用于两侧；分路侧播放耗时的初始值（`4e2c84c`）。只改 `app/static/app.js` |
     | 数据处理页子界面 | `2681e6e`（11:37）、`88b9a08`（12:00）、`678f6c8`（12:04）、`1810165`（12:19）、`b02e35c`（15:55）、`a43edf0`（16:03）、`97954b5`（16:17） | 先把 4 个功能拆成左侧导航里的独立页面（`2681e6e`），随后改为留在「数据处理」页内、用页内导航条切换的 5 个子界面（`88b9a08`、`678f6c8`、`1810165`），再修导航条切换与样式（`b02e35c`、`a43edf0`），最后去掉重复标题（`97954b5`）。最终状态：`#view-process` 顶部 5 个按钮（重采样 / 负荷辨识调参 / 设备画像提取 / 波形预览 / 估计 CT），一次显示一个子界面，每个子界面第一次打开时才初始化 |
     | 波形预览标题 | `f7f9806`（16:37）、`e9bf4e7`（16:47） | 各曲线图的序列名去掉单位；逐周波有效值曲线和周波窗曲线的名称去掉「RMS」 |
     | 数据 | `e05542a`（11-10 01:40；提交记录里的时间是 +0800 时区的 09:40，其余 36 个提交都是 +0000） | 只改 `tmp/` 下 22 个文件（从文件名看是两侧配置、运行信息、负荷辨识事件和实时曲线 CSV），没有程序改动。本任务没有查看这些文件的内容，也没有改动 `tmp/`（只计算过整个目录的校验和） |

     这 14 个提交没有新增或修改任何测试。
  2. **既有测试**（实测，当前代码）。`tests/test_r13_pause.py` 4 passed；`tests/test_r61_wave_preview.py` 9 passed / 2 skipped；`tests/test_r8_resample.py` 21 passed；`tests/test_web_ui.py` 24 passed；全量 654 passed / 1 skipped。这些用例检查的是接口和页面里的固定字符串，没有一条覆盖 `S.branchFullState`、「任一侧运行」的按钮状态或子界面切换。`app/static/app.js` 里有两处注释写明「保留原字面量供契约测试」「兼容前端契约测试所需字符串」，即为了让旧的字符串断言继续通过而保留了旧字符串；这类断言通过不能说明新行为正确。
  3. **数据处理页改版前后的对比**（实测，`tools/ui_r61_check.cjs`，真实服务进程）。

     | 代码 | 脚本 | 结果 |
     | --- | --- | --- |
     | 当前（`03a2854`） | 原样 | 5 项通过、5 项失败后脚本崩溃（第 67 行 `Cannot read properties of undefined (reading 'url')`）：脚本只点了「数据处理」，没有点「波形预览」子界面，面板没有初始化 |
     | 当前（`03a2854`） | 加两行：先点击 `.sub-navitem[data-subview="wave-preview"]`，再等待 300 ms | 20 项通过、15 项失败，随后在第 166 行崩溃（`Cannot read properties of null (reading 'pad')`） |
     | 改版前（`4e2c84c`） | 原样 | 20 项通过、15 项失败，随后在第 164 行崩溃（同一处） |

     判读：补上「先点子界面」这一步后，改版前后崩溃前的 35 项检查结果逐项相同（失败的 15 项名称完全一致），即这 35 项没有显示出改版引入的差异。这**不是通过**：该脚本本身已经过期，改版前就有 15 项失败并中途崩溃，失败原因没有逐项查（脚本是为 v0.61 ～ v0.65 写的，例如它期望基准配置初始为 PT 100 / CT 15，实际为 1 / 1）；崩溃之后的检查两边都没有运行。`4e2c84c` 包含同一天稍早的顶栏改动，所以这个对比只说明数据处理页改版和波形预览标题这两组。
  4. **核对出的问题**（编号「补-B」；均未修，是否修由用户决定）。

     | 编号 | 来源提交 | 问题 | 证据 |
     | --- | --- | --- | --- |
     | 补-B1 | `2c51d2f` | 顶栏里对侧一行的频率恒为「—」。改动前这里显示对侧摘要的 `f_used`（`isNum(ps.f_used) ? num(ps.f_used, 3) + ' Hz' : '—'`），`2c51d2f` 把它换成了常量 `'—'`；服务端的对侧摘要仍带 `f_used` 字段。属于这次改动带来的功能倒退 | 读 diff 与当前代码 |
     | 补-B2 | `511b93c`、`4e2c84c` | 顶栏「暂停」「停止」的提示不可靠，有三处。① 在分路侧视图下，请求发到分路侧（`POST /api/branch/engine/stop`、`POST /api/branch/engine/pause`），提示却是「总线侧已停止」「bus侧已暂停」，侧别说反了。② 在总线侧视图下对分路侧的暂停 / 恢复 / 停止用的是裸 `fetch`，不检查返回状态：让假服务端返回 HTTP 400，提示仍是「分路侧已停止」「branch侧已暂停」（对总线侧的同类请求走 `api()`，会提示「bus侧停止失败：…」）。③ 暂停 / 恢复的提示和各失败提示里，侧别是英文标识（「bus侧」「branch侧」）。改动前的提示不带侧别（「已停止」「已暂停播放（数据时刻停在 …）」），没有这些问题 | 实测（把 `stopEngine`、`togglePause` 从 `app.js` 取出，在 node 里配假 `fetch` 运行，记录发出的请求和提示文字；不是浏览器） |
     | 补-B3 | `1810165` | 「估计 CT」子界面的事件被绑定两次：`initCtEstimate()` 在页面初始化时由 `bindProcess()` 调一次，第一次打开该子界面时由 `renderProcess()` 再调一次，函数自身没有防重。调用两次后，用匿名函数绑定的控件点一次触发两次：「加载逐周波 RMS 曲线」调 `ctLoadRms` 2 次，「复制」提示 2 次；各输入框的 `change` 处理按同样的写法绑定，也会是两次（读代码，未计数）。用具名函数绑定的「估计 CT」（`ctRun`）和「刷新文件列表」（`ctListFiles`）仍是 1 次，因为同一个函数重复 `addEventListener` 不会叠加 | 实测（jsdom，单独调用该函数两次后点击计数） |
     | 补-B4 | `b02e35c`、`a43edf0` | 页内导航条用的是写死的浅色（背景 `#f0f0f0`、文字 `#333`、边框 `#ccc`、选中 `#0066cc`），没有用页面的主题变量；页面主题是深色（`--bg:#0f1420`）。实际观感没有看过 | 读代码 |
     | 补-B5 | 数据处理页一组 | 针对数据处理页的 jsdom 脚本没有随改版更新。`tools/` 下 34 个 `ui_*check*.cjs` 脚本没有一个引用页内导航（`sub-navitem` / `data-subview`）。`ui_r61_check.cjs`（波形预览）原样运行已失败（第 3 点）。同样操作数据处理页控件的还有 `ui_r72_check.cjs` 和 `ui_r80_check.cjs`（负荷辨识调参）、`ui_r90_check.cjs`（设备画像提取）、`ui_r86_check.cjs`（列映射）、`ui_r8_check.cjs`（重采样，即默认打开的子界面）；这 5 个没有运行，是否受影响未知 | `ui_r61_check.cjs` 实测；其余读代码（全文搜索） |

  5. **没有核对的**。顶栏双侧状态的显示是否正确、按钮在各种运行组合下的可用状态、两侧同时暂停 / 停止的实际效果（需要两侧都在运行的服务进程，没有做）；子界面切换时未保存输入是否保留；窄屏下导航条的表现；波形预览标题改动后的图例显示。这些都需要在浏览器里看。
- **是否进入 REPORT.md（稳定结论）**：否。
- **遗留问题**：补-B1 ～ 补-B5 均未修，登记在 `STATUS.md`「下一步」。2026-11-09 这批界面改动至今没有真实浏览器验收，也没有针对性的自动化测试。

## [2026-11-11] 专题 T-023：修 15 处已登记问题（补-A1～A10、补-B1～B5）、路由日志默认可见、「波形预览」子界面改名「波形分析」

- **类型 / 模式**：用户专题（实现＋验证）；模式 A（沙盒自执行），角色为工程实现工程师。2026-11-10 立项（`b38c2a7`），2026-11-11 完成。分支 `arena/51b63974-nilm-calc-tool`，开局远端 tip `4cad4f2`。没有连接真实模型、真实浏览器和用户部署环境：模型响应全部是测试里的假响应，界面检查用 jsdom。
- **目标与假设**：用户 2026-11-10 的三条指令，原话：① 「核对出的 15 处问题修改」② 「让路由日志默认可见」③ 「将数据处理界面中波形预览子界面标题改为波形分析」。
  - 「15 处」按 `STATUS.md`「下一步」当时的登记理解为 T-021 的补-A1～A10 与 T-022 的补-B1～B5。
  - 登记时写「待定」的 4 个子项（补-A3、补-A7、补-A8、补-B5）用户没有另作指示，立项时由我定了做法并写进 `STATUS.md`「当前目标」，见结果第 9 点。
  - 完成标准（立项时登记）：每处修复有回归用例，并对修复前的代码做反向对照；全量 pytest 无失败；`node tools/ui_assistant_check.cjs` 通过；四份手册 `--check` 为 `OK`；说明书 §6.8 已知限制、README、`STATUS.md`「下一步」按修复结果更新；全部提交并推送。
  - 指令 ③ 按「只改名称」理解：界面上的名称和文档里描述当前界面的地方改，内部标识（`wave-preview`、`wp-*`、接口路径、模块名）和历史记录不动。`restore_branch_full_history` 上另有一个功能不同的子界面 `wave-analyze`，按用户第二项任务的决定不合入，与这次改名无关。
- **方法 / 数据 / 参数**：
  - **开局**。在 `4cad4f2` 上重跑助手三个测试文件和 jsdom 作基线。动手前先用真实接口把登记的现象复现一遍，过程中发现登记之外的补-A11（「恢复」的前置检查方向反了）。补-A9 要给跨侧的恢复补上检查，绕不开它，所以一并修，并在立项提交里登记。
  - **后端（补-A1～A11，`818c3a5`）**。改 `app/assistant.py`、`app/server.py`、`app/assistant_intents.py`、`configs/intent_actions.csv`。主要是三件事：① 侧别解析统一到 `_resolve_target_side`，返回目标侧和「是否同时点名了两侧」；② 服务端给助手的上下文可以按侧取（`prepare_chat` 新增参数 `tool_context_for`），前置条件、资源清单、参数核对都用目标侧的上下文，上下文里新增 `paused`；③ 启动 / 暂停 / 恢复 / 停止的前置条件集中到 `_source_state_blocker`，确定性路由和意图识别直达共用。
  - **指令 ②（`480206a`）**。`cli.py` 新增 `configure_app_logging()`，`cmd_serve` 在启动 uvicorn 之前调用；新增选项 `--app-log-level`。
  - **前端与改名（`4be5c9a`）**。改 `app/static/app.js`、`index.html`、`style.css`、`tools/nilm_tune.py`。
  - **补-B5（`def6ccb`）**。6 个脚本先逐个原样运行，按失败项找原因，再改脚本。这些脚本会在 `data/`、`output/` 下写文件并改运行配置，所以把仓库拷到 `/tmp` 下的副本里，在副本目录用 `python cli.py serve` 起临时服务；服务与脚本同为 `TZ=Asia/Shanghai`；每个脚本各用一个全新的服务进程和全新的副本。
  - **文档（`04bbfd7`）**。说明书 §6.7～§6.10、§7；README；调参手册；四份生成手册；`REPORT.md` v0.13。动笔之前，把要写进说明书的行为在真实接口上逐条试过：延时的 6 种说法、同时点名两侧、档位边界、日志在三种启动方式下的输出、意图配置的 5 种编码。
  - **验证手段**。
    - pytest，模型用假响应。
    - 真实接口用例（新文件 `tests/test_assistant_cross_side.py`）：同进程 `TestClient` 走真实 HTTP 接口；两侧的数据源由真实的引擎线程运行，以 0.25 倍速播放一份 8 秒的录波文件；凡是跨侧的用例，两侧的运行状态都不相同，并且从非目标侧的页面发起。这些用例只依赖 HTTP 接口，可以原样拿去跑修复前的代码。
    - jsdom 驱动真实的 `index.html` + `app.js`，对着真实的临时服务（新脚本 `tools/ui_r209_check.cjs` 和 6 个旧脚本）。
    - 反向对照：把修复前的文件换回去跑新用例。各次提交前做过一遍；收尾时在 `/tmp` 下的仓库副本里又完整做了一遍（不动仓库），第 7 点的数字是收尾这一遍的。
    - `tests/test_cli.py` 新增的 5 条都在独立的子进程里执行，其中 2 条启动真实的服务进程、发一次问答请求、读标准错误。
- **用户执行命令（含实录路径）**：本节无用户命令。全部命令在沙盒执行，输出摘录见下，没有单独的实录文件。
- **结果 / 结论**：
  1. **提交**（均已推送）。`b38c2a7` 立项，只改 `STATUS.md`；`818c3a5` 后端补-A1～A11；`480206a` 指令 ②；`4be5c9a` 补-B1～B4 与改名；`def6ccb` 补-B5；`04bbfd7` 文档；另有本专题所在的台账提交。`4cad4f2..04bbfd7` 共 30 个文件，+2368 / −648 行。
  2. **逐项结果**。「修复前」取自 T-021 / T-022 的登记。用例名里，`tests/test_assistant.py` 的记作「单元」，`tests/test_assistant_cross_side.py` 的记作「真实接口」，`tests/test_web_ui.py` 的记作「静态」。

     | 编号 | 修复前 | 修复后 | 回归用例 |
     | --- | --- | --- | --- |
     | 补-A1 | 延时检查把单个「后」字当成延时，「查看后台重采样任务状态」「取消后台重采样」「查询最后10条电能质量事件」被 400 拒绝 | 只认 6 种延时写法：时长加「后 / 之后 / 以后 / 过后」；「等 / 过 / 推迟 / 晚」加时长；「定时」「稍后」等词；「之后 / 然后」紧接动作；动作加「后」再接动作；「等……完……再」。上面三句正常处理，「15秒过后启动数据源」等仍返回 400 | 单元 `test_delay_refusal_needs_a_delay_phrase_not_a_bare_hou_character`；真实接口 `test_background_and_last_n_requests_are_not_refused_as_delayed` |
     | 补-A2 | 侧别词按子串匹配，先出现的优先；在分路侧页面说「查看 Modbus 运行状态」返回总线侧的状态 | 英文 `bus` / `branch` 只在是独立单词时才算。一句话同时点名两侧时不取先出现的一侧：确定性路由返回 400，意图识别直达不介入，模型路径返回澄清（原因码 `ambiguous_target_side`）。`compare_sides`、`estimate_ct_ratio`、`set_compare_alignment` 本身涉及两侧，不受此限 | 单元 `test_side_words_are_whole_words_and_two_named_sides_are_never_guessed`；真实接口 `test_modbus_is_not_read_as_the_bus_side`、`test_a_prompt_naming_both_sides_is_never_resolved_to_the_first_one` |
     | 补-A3 | `_exclusive_limit`、`_parsed_side` 写入计划后无人读取 | 删除 `_parsed_side`。`_exclusive_limit` 现在由 `create_tool_proposal` 读取：提案绑定总线侧、且该操作会连带分路侧时，卡片的影响说明里加一句「系统不支持只作用于总线侧；不想影响分路侧请取消」。实际执行的内容不变 | 单元 `test_exclusive_wording_adds_a_linkage_warning_and_no_unread_plan_keys`；真实接口 `test_exclusive_wording_warns_that_the_bus_side_cannot_act_alone` |
     | 补-A4 | 意图识别直达对「启动」一律要求文件数据源：数据源是模拟器时「启动分路侧数据源检测」返回 409，而「启动分路侧数据源」可以生成提案 | 两条路由共用 `_source_state_blocker`，只有话里说到离线 / CSV / 文件时才要求文件数据源 | 单元 `test_intent_route_start_requires_a_file_source_only_for_offline_wording`；真实接口 `test_simulator_source_can_be_started_through_either_direct_route` |
     | 补-A5 | 模型路径的提案绑定在提问页面所在的一侧 | 提案绑定话里点名的一侧，资源清单和参数核对用那一侧的上下文，跨侧提案的标题写实际执行的一侧。连带修了一处：导出文件的下载地址按结果里的 `side` 拼，此前跨侧导出下载返回 403 | 单元 `test_model_path_proposal_is_bound_to_the_side_named_in_the_prompt`；真实接口 `test_model_path_proposal_runs_on_the_side_named_in_the_prompt`、`test_cross_side_export_is_downloaded_from_the_side_that_produced_it`；`tools/ui_assistant_check.cjs` 新增 5 项 |
     | 补-A6 | 意图识别直达只在工具已授权时介入，未授权时转入模型路径；直达分支里 5 处 403 检查走不到 | 保留「未授权时不报 403、转入模型路径」，删掉走不到的 5 处检查；路由日志新增 `intent_tool`、`intent_tool_available`，从日志能看出这种情况 | 单元 `test_intent_route_leaves_unauthorized_requests_to_the_model_path`；真实接口 `test_unavailable_intent_tool_falls_through_to_the_model_and_is_logged` |
     | 补-A7 | `get_runtime_status` / `get_runtime_settings` 直接执行时不写审计，并且任何档位都直接执行 | 只在非 low 档位直接执行，low 档位交给模型。每次直接执行写一条审计记录（`status=direct_read`、`origin=intent`，没有 `proposal_id`）。摘要由 `app/server.py` 的 `assistant_read_tool` 生成，与确认后执行是同一段代码 | 单元 `test_direct_reads_skip_the_low_tier_and_leave_an_audit_record`；真实接口 `test_direct_reads_leave_an_audit_record`、`test_low_tier_read_request_is_left_to_the_model` |
     | 补-A8 | `configs/intent_actions.csv` 没有 BOM；文件存成 GBK 时服务无法启动 | 恢复 UTF-8 BOM，其余字节不变；读取时 UTF-8 解码失败改按 GB18030 再读一次；其它编码报「意图配置 CSV 的编码无法识别…」 | 单元 `test_intent_config_csv_in_the_repository_has_a_utf8_bom`、`test_intent_config_csv_saved_as_gbk_still_loads` |
     | 补-A9 | 跨侧的暂停 / 恢复 / 停止在生成提案时不检查目标侧是否在运行 | 按目标侧自己的状态检查，不满足时返回 409，与同侧的规则相同 | 单元 `test_cross_side_source_checks_read_the_target_side_state`；真实接口 `test_cross_side_pause_resume_stop_are_refused_when_the_target_is_not_running` |
     | 补-A10 | 跨侧「启动」的前置检查读的是提问页面所在一侧的状态：总线侧在运行、分路侧未运行时，在总线侧页面说「启动分路侧数据源」被 409 误拒；目标侧已在运行时提案照样生成 | 读目标侧的状态 | 单元同上一行；真实接口 `test_cross_side_start_is_not_blocked_by_the_state_of_the_page_side`、`test_bus_playing_branch_stopped_from_the_branch_page`、`test_branch_playing_bus_stopped_from_the_bus_page` |
     | 补-A11（登记之外） | 同侧「恢复」的检查方向反了：数据源已暂停时被 409「…正在运行，无需恢复」拒绝；已停止时反而生成提案，确认时才 400 | 上下文新增 `paused`；「恢复」只在已暂停时生成提案，未运行、在运行但没有暂停都返回 409 | 真实接口 `test_resume_is_offered_only_while_the_source_is_paused`；既有用例的预期改正，见第 8 点 |
     | 补-B1 | 顶栏对侧一行的频率恒为「—」 | 取对侧摘要的 `f_used`，3 位小数；对侧还没有结果时仍显示「—」 | 静态 `test_topbar_peer_row_shows_frequency_from_peer_summary`；`ui_r209_check.cjs` B1 段 6 项，其中 2 项是两侧模拟器运行时的实测 |
     | 补-B2 | 顶栏「暂停」「停止」的提示：分路侧视图下把侧别说成总线侧；总线侧视图下操作分路侧时不检查返回状态，服务端报错也提示成功；侧别用英文标识 | 按实际操作的一侧提示，写「总线侧」「分路侧」；两侧都经 `api()`，服务端拒绝时提示「<侧>暂停 / 恢复 / 停止失败：<原因>」并用错误样式；操作成功而刷新状态失败时不再算作失败 | 静态 `test_topbar_pause_and_stop_report_the_right_side_and_real_outcome`（2 条）；`ui_r209_check.cjs` B2 段 19 项：11 项用假响应重现服务端返回 400 / 500，8 项是两侧各自播放录波文件的实测 |
     | 补-B3 | `initCtEstimate()` 被调用两次且没有防重，「加载逐周波 RMS 曲线」点一次发两次请求 | 加一次性标记，只绑定一次；两个调用点都保留 | 静态 `test_ct_estimate_binds_its_events_only_once`；`ui_r209_check.cjs` B3 段 3 项 |
     | 补-B4 | 页内导航条用写死的浅色，没有用主题变量 | 改为取主题变量，选中态与左侧导航条的选中态同一套配色 | 静态 `test_sub_nav_uses_theme_variables`。只核对了样式表的写法，实际观感没有看过 |
     | 补-B5 | 数据处理页的 6 个 jsdom 脚本没有随改版更新；`ui_r61` 原样运行失败，其余 5 个当时没有运行 | 6 个脚本全部更新，没有停用，也没有删除；结果见第 5 点 | 脚本本身；更新前后在同一条件下各跑一遍 |
     | 指令 ② | `python cli.py serve` 下 `elec_tool.*` 的 INFO 行不输出，WARNING 行只有消息正文 | 见第 3 点 | `tests/test_cli.py` 新增 5 条 |
     | 指令 ③ | 子界面叫「波形预览」 | 见第 4 点 | 静态 `test_wave_subview_is_named_wave_analysis_and_keeps_internal_ids`；`ui_r209_check.cjs` N 段 11 项 |

  3. **指令 ②：路由日志默认可见**。
     - `python cli.py serve` 默认给 `elec_tool` 记录器装一个写标准错误的输出，级别 INFO，每行是「时间 级别 记录器名 消息」，例如 `2026-11-11 01:33:13,318 INFO elec_tool.assistant assistant_route_decision trace_id=…`。
     - 新增 `--app-log-level {debug,info,warning,error,critical}`，默认 `info`。`--log-level` 的含义和默认值不变（`warning`，只管 uvicorn），两者互不影响。
     - 重复调用只更新级别，不装第二个输出。根记录器或 `elec_tool` 记录器上已经有别处装的输出时不再另装，只设级别，同一行只输出一次。保留向根记录器传播，pytest 的 `caplog` 照常工作。
     - 实测输出（2026-11-11，Linux）：默认启动时，「● 启动 Web 界面…」一行之后是「服务启动 version=…」和「启动自动加载上次数据…」两行 INFO；`--app-log-level warning` 时只剩「●」一行；`--log-level info` 时另有 uvicorn 自己的 INFO 行。
     - 没有覆盖的启动方式：不经 `cli.py`、直接 `python -m uvicorn app.server:app` 启动时没有这项配置，INFO 行仍不输出，WARNING 行仍只有正文（实测）。说明书 §6.9 和 README §3.1 已写明。
     - 一个连带的变化：管理员打开 `log_queries` 之后的 `assistant_question` 行（脱敏后的问题原文）也是 INFO 级，现在同样默认输出。该开关默认关闭。
  4. **指令 ③：改名**。页内导航按钮、子界面标题、助手里该子界面的名称、另外两个子界面提示文字里对它的称呼、`tools/nilm_tune.py` 中 `--custom-time` 的帮助文字，都由「波形预览」改为「波形分析」。README 该节标题和 §3.1 的说明、调参手册两处同步，并注明原名。变更记录、验证记录里的历史条目和内部标识不动。
  5. **补-B5：6 个脚本更新前后**。同一条件：全新的临时服务，服务与脚本同为东八区。数字是「通过 / 失败」的检查项数。

     | 脚本 | 更新前（脚本取自 `4be5c9a`） | 更新后 |
     | --- | --- | --- |
     | `ui_r8_check.cjs` | 50 / 7，随后异常退出（退出码 2） | 70 / 0 |
     | `ui_r61_check.cjs` | 5 / 5，随后异常退出（退出码 2） | 48 / 0 |
     | `ui_r72_check.cjs` | 3 / 5，随后异常退出（退出码 2） | 30 / 1（退出码 1） |
     | `ui_r80_check.cjs` | 7 / 3，退出码 0 | 10 / 0 |
     | `ui_r86_check.cjs` | 15 / 3，退出码 0 | 18 / 0 |
     | `ui_r90_check.cjs` | 5 / 8 | 13 / 0 |

     - 更新后的结果在 `def6ccb` 提交前连续 3 轮相同，收尾时在 `04bbfd7` 上又跑一轮，仍相同。
     - 过期的原因有两类。一是 2026-11-09 的改版：数据处理页分成 5 个子界面，各子界面的文件列表、默认值、事件绑定推迟到第一次打开时才做，脚本进入页面后没有点子界面。二是 v0.99.23（2026-10-30）：去掉了「启用 PT/CT」开关，出厂变比由 PT 100 / CT 15 改成 1 / 1，脚本里写死的出厂值和「取消勾选开关」的步骤对不上。第二类比改版早 10 天：T-022 第 3 点已经看到 `ui_r61` 在改版前就有 15 项失败，当时没有逐项查原因，这次查明主要是这一条。
     - 另外改了三处。`ui_r8` / `ui_r72` / `ui_r90` 手动调用 `init()`，而 `app.js` 自己在 `DOMContentLoaded` 时也调用，jsdom 在构造函数返回之后才派发这个事件，`init` 实际跑了两遍（开局 2 秒内的请求 31 次，改后 19 次）；改为先去掉监听再调一次。`ui_r80` / `ui_r86` 的退出码原来恒为 0，改为有失败项时返回 1。`ui_r90` 原来钉死「算法面板有 6 个数值参数」，现在面板有 13 个，改为要求 v0.90 的 6 个参数都在。
     - `ui_r72` 剩下的 1 项失败不是脚本过期，是产品问题，见第 10 点补-B7。这一项保留，问题修掉后应通过。
     - 运行这些脚本的前提写在各自的文件头里。两个容易踩的：服务用了状态目录覆盖（`ELEC_TOOL_NILM_DIR` 等环境变量）时，`ui_r8` 有 8 项会失败，因为它到仓库目录下的 `output/nilm` 找文件；服务在 UTC、脚本在东八区时，`ui_r61` 通过 20 项后抛 `TypeError`。
  6. **验证（命令 / 输出 / 判读）**。除注明的以外都在 `04bbfd7`（最终的代码与文档）上运行。

     | 步骤 | 命令 | 输出 | 判读 |
     | --- | --- | --- | --- |
     | 开局基线 | `pytest tests/test_assistant.py tests/test_server.py tests/test_web_ui.py`；`node tools/ui_assistant_check.cjs`（`4cad4f2`） | 109 passed；`PASS 205 checks` | 与第二项任务收尾时一致 |
     | 真实接口用例的稳定性 | `pytest tests/test_assistant_cross_side.py` 连跑 5 次（`818c3a5` 提交前） | 5 次都是 15 passed | 用例里有真实线程和等待，确认结果不抖 |
     | 全量 | `.venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs` | `690 passed, 1 skipped, 1 warning in 220.75s` | 654 + 36（真实接口 15、单元 10、CLI 5、静态 6）。skipped 是既有的 60 Hz 用例，warning 是既有的 Starlette / httpx 弃用提示。文档最后几处修改之前也跑过一次，同为 690 passed / 1 skipped（215.90 s）；后端刚修完、只写了头 9 条单元用例时是 663 passed / 1 skipped |
     | 定向 | `pytest tests/test_assistant.py tests/test_assistant_cross_side.py tests/test_server.py tests/test_web_ui.py tests/test_cli.py` | 164 passed / 1 skipped | 各文件用例数：55、15、40、30、25（其中 1 条跳过） |
     | 助手界面 | `node tools/ui_assistant_check.cjs` | `PASS 210 checks` | 205 + 5（跨侧导出的下载地址）。不在 pytest 里，要先补齐 `node_modules/` 缺的 10 个文件 |
     | 本轮界面 | 临时服务；`TZ=Asia/Shanghai JSDOM_DIR=/tmp/uitest node tools/ui_r209_check.cjs http://127.0.0.1:8766` | `PASS：通过 40 项，失败 0 项` | N 段 11、B3 段 3、B1 段 6、B2 段 19、页面没有未捕获的脚本错误 1 |
     | 6 个旧脚本 | 同样方式逐个运行，每个脚本一个全新的临时服务 | 70 / 0、48 / 0、30 / 1、10 / 0、18 / 0、13 / 0 | 与第 5 点一致 |
     | 手册 | `.venv/bin/python tools/generate_assistant_docs.py --check` | 四份均 `OK` | — |
     | 自检 | `.venv/bin/python cli.py selftest` | 44 项通过 44 | 电气量计算没有受影响 |
     | 语法与静态检查 | `node --check`：`app/static/app.js` 和 8 个 `.cjs` 脚本；pyflakes：`app/assistant.py`、`app/assistant_intents.py`、`app/server.py`、`cli.py` | 全部通过；pyflakes 的告警条数与 `4cad4f2` 相同（1 / 2 / 8 / 6，逐条相同，都是既有的未使用导入等） | 没有新增告警 |
     | `app.js` 顶层函数清单 | `grep -oE '^(async )?function [A-Za-z0-9_$]+' app/static/app.js \| sort`，与 `4cad4f2` 的对比 | 418 个，完全相同 | 防误删，见第 11 点 |
     | 知识库措辞 | 在 README、`REPORT.md`、调参手册、`docs/*.md` 里搜第二项任务验收用例的提问原话和假模型的自述 | 0 处 | T-020 第 8 点的约束 |
     | `tmp/` | `find tmp -type f -print0 \| sort -z \| xargs -0 sha256sum \| sha256sum` | 开头 `c480302f2baa0020`，与任务开始时相同 | 只计算过校验和，没有查看内容 |

  7. **反向对照**。收尾时在 `/tmp` 下的仓库副本里做，仓库本身不动；用例是 `04bbfd7` 的。

     | 换回的文件 | 命令 | 输出 | 判读 |
     | --- | --- | --- | --- |
     | `app/assistant.py`、`app/server.py`、`app/assistant_intents.py`、`configs/intent_actions.csv` 换成 `b38c2a7` 的版本 | `pytest tests/test_assistant.py tests/test_assistant_cross_side.py` | `26 failed, 44 passed` | 失败的 26 条 = 真实接口 15 条 + 新增单元 10 条 + 改了预期的既有用例 1 条；通过的 44 条是 `tests/test_assistant.py` 其余的既有用例 |
     | `cli.py` 换成 `b38c2a7` 的版本 | `pytest tests/test_cli.py` | `5 failed, 19 passed, 1 skipped` | 新增的 5 条全部失败 |
     | `app/static/app.js`、`index.html`、`style.css` 换成 `480206a` 的版本 | `pytest tests/test_web_ui.py` | `6 failed, 24 passed` | 新增的 6 条全部失败 |
     | 同上 | `ui_r209_check.cjs`（临时服务） | `FAIL：通过 12 项，失败 28 项` | 失败处就是登记的现象，例子见下 |
     | `app/static/app.js` 换成 `b38c2a7` 的版本 | `node tools/ui_assistant_check.cjs` | `FAIL: Error: 总线侧页面下载分路侧的导出文件时，地址没有带分路侧前缀` | 换回当前文件后 `PASS 210 checks` |

     - 15 条真实接口用例在旧代码上都失败在各自登记的现象上。例如：总线侧在运行、分路侧已停止时，在总线侧页面说「启动分路侧数据源」得到 409「分路侧数据源已在运行或暂停，不会重复启动…」（补-A10）；「暂停分路侧离线播放」在分路侧未运行时照样生成提案（补-A9）；「查看后台重采样任务状态」得到 400「请求包含延时执行指令…」（补-A1）；在分路侧页面问 Modbus 的运行状态，回答是「查询总线侧运行状态」（补-A2）；直接执行之后审计记录为空（补-A7）；模型路径的提案 `side` 是 `bus` 而不是 `branch`（补-A5）。
     - 新增的 10 条单元用例里，5 条失败在行为上（没有 BOM、`UnicodeDecodeError`、「查看后台重采样任务状态」被判为延时、「查看只读配置」被判为带限定词、日志里没有 `intent_tool` 字段）。另外 5 条失败在旧代码没有新接口（4 条是 `prepare_chat` 不认识 `tool_context_for` 参数，1 条是没有 `_resolve_target_side`），**这 5 条单独不能证明现象**；它们对应的现象（补-A4、补-A5、补-A7、补-A9 / A10、补-A2）由上一条的真实接口用例证明。
     - `cli.py` 的 5 条里，「默认启动能看到路由日志」一条失败在标准错误为空，即登记的现象；3 条失败在没有 `configure_app_logging`；1 条失败在服务进程不认识 `--app-log-level` 而退出。
     - jsdom 失败的 28 项里有：分路侧视图下提示「bus侧已暂停」「总线侧已停止」；总线侧视图下分路侧被拒仍提示「branch侧已暂停」；「加载逐周波 RMS 曲线」点一次发 2 次请求；对侧频率「—」；子界面仍叫旧名称。
  8. **改动的既有预期**（都是原预期把错误行为写成了正确结果，或者写死了已经变更的出厂值）。
     - `tests/test_assistant.py::test_offline_source_stop_resume_pause_regression_corpus`：「恢复」的正常路径由 `running=False` 改为 `running=True, paused=True`，并补上 `running=False` 时被拒绝的情形。原预期对应补-A11 的错误行为。
     - 6 个旧 jsdom 脚本里写死的出厂变比（PT 100 / CT 15 → 1 / 1）、「取消勾选启用 PT/CT」的步骤（开关已在 v0.99.23 去掉）、`ui_r90` 的参数个数（6 → 要求 v0.90 的 6 个都在）。
     - 没有删除任何既有用例，也没有放宽任何断言来让测试通过。
  9. **由我决定的事项**（用户可以改）。前 4 条是立项时登记的，其余是实施中定的。
     - **补-A3**：不做「只操作总线侧」的执行方式，改为在卡片上提示。理由：两侧联动播放共用同一个节拍，单独暂停或停止总线侧是新功能，不属于修已登记的问题。另一种做法是遇到这类限定词直接拒绝。加载上次历史数据（`load_last_history`）在总线侧也可能连带分路侧，一并纳入提示。
     - **补-A7**：直接执行只限非 low 档位，并写审计。理由：提交 `e592aef` 的注释原意如此；审计记录不完整是这一条登记时最主要的顾虑。另一种做法是取消直接执行，一律走确认卡片。
     - **补-A8**：恢复 BOM，并让 GBK 文件也能读入。理由：中文版 Excel 靠 BOM 识别 UTF-8，另存为「CSV（逗号分隔）」时写出的是 GBK。Excel 的实际表现没有条件验证。
     - **补-B5**：6 个脚本全部更新，没有停用。
     - **补-A11**：不在登记的 15 处里，一并修了，理由见「方法」。
     - **补-A2**：同时点名两侧时拒绝或澄清，不替用户选一侧，也不拆成两步执行。
     - **补-A5**：跨侧提案的标题写实际执行的一侧；导出的下载地址跟随结果里的 `side`（测补-A5 时发现的连带问题）。
     - **补-A6**：保留「未授权时转入模型路径」，不报 403。试过报 403：知识性问题也会被打成 high 档位，而工具总开关默认关闭，这样会挡住普通问答，所以放弃。
     - **补-A8**：UTF-8 和 GB18030 都解不开的文件给出明确的中文报错，不再抛 `UnicodeDecodeError`。
     - **指令 ②**：选项名用 `--app-log-level`，默认 `info`；不改 `--log-level` 的含义。
     - **指令 ③**：改名的范围见第 4 点。
     - **补-B2**：只改提示和错误处理，没有改「每一侧按它自己的暂停状态取反」这个点击语义；它在两侧状态不同时的表现登记为补-B6，留给用户决定。
     - **补-B5**：`ui_r72` 保留那一项失败的检查，不为了全绿而放宽。
     - **版本号**：按 README 的惯例记为 v0.99.50、第 209 轮。`elec_tool.__version__` 仍是 `0.1.0`，没有动（已登记在环境卫生一条）。
     - **`REPORT.md`**：按收尾仪式新增 2 条方法论教训（v0.13），并把 2026-11-10 一行的状态翻为已恢复（依据 T-020）。
  10. **修复过程中新发现、只登记没有修的 5 处**。都不在登记的 15 处里，各自需要先定行为。前三条 2026-11-11 在 `04bbfd7` 上用真实接口重新确认过（假模型）。
      - **补-A12**：「暂停」的前置条件只看数据源是否在运行。① 总线侧离线文件已经暂停时，说「暂停当前侧离线播放」或「暂停数据源」仍生成 `pause_current_source` 提案；确认返回 200「总线侧离线播放已暂停」，状态不变。② 总线侧模拟器在运行时，说「暂停数据源」同样生成提案；确认返回 400「暂停/恢复仅支持离线文件（csv_file）源，当前为 simulator」。补-A9 登记的只是「目标侧未运行」这一种情形，已修；这两种是同一项检查里没有覆盖的。
      - **补-A13**：只给出时刻的说法不算延时。「明天8点启动总线侧数据源」「今晚10点启动数据源」得到一张**立即**启动的提案（意图识别直达），回答里不提时间被忽略；「15秒过后启动数据源」返回 400。延时检查只认第 2 点补-A1 一行列出的 6 种写法；修复前的代码同样不认绝对时刻。
      - **补-A14**：知识性问句被认成查询。「电能质量事件有哪些类型」在操作员有 `events.read` 时得到 `get_event_list` 提案；没有该权限时是模型的文字回答；「电能质量事件怎么定义」是模型的文字回答。原因是打分只看用词。补-A6 保留「未授权时转入模型路径」正是因为这一点。
      - **补-B6**：总线侧视图下两侧暂停状态不同时，顶栏暂停按钮点一次是两侧状态互换。实测（jsdom 驱动真实页面，真实临时服务，两侧各自播放录波文件）：总线侧在播、分路侧已暂停时，按钮文字是「恢复」（只跟分路侧走）；点一次，请求是 `/api/engine/pause` 和 `/api/branch/engine/resume`，提示「总线侧已暂停，分路侧已恢复」，服务端变成总线侧已暂停、分路侧运行中；再点一次又换回来。修复前后在这一点上相同；这次只把提示改对了，`togglePause` 里留了注释。
      - **补-B7**：「负荷辨识调参」「设备画像提取」两个子界面，基准配置选「沿用总线侧 / 分路侧运行配置」时，标题写着「不可修改」，PT、CT 两个输入框在约 1 秒后又变回可编辑。原因：`ntFillQCFromRunning` → `ntSetBase` → `ptctSync`，后者自 v0.99.23 起无条件解除禁用。这种模式下请求不上送界面上的基准配置，改了也不生效。`ui_r72_check.cjs` 剩下的 1 项失败就是它。
  11. **过程中的问题**。
      - **沙盒重置 3 次**。每次都是本地 HEAD 回到 `e05542a`、工作区是最新内容、`.venv` 和 `/tmp` 清空。处理同第二项任务：`git fetch` 后看 `git diff --stat FETCH_HEAD`，确认只多出进行中的文件；在旧 HEAD 之后才入库的文件此时显示为「未跟踪」，逐个与远端版本比 sha256；一致后 `git reset --mixed FETCH_HEAD`，重建环境。没有在旧 HEAD 上提交，没有丢改动。丢的是 `/tmp` 下的探针脚本和中间日志，所以第 7、10 点在收尾时重做了一遍。第三次重置后，文档改完就先提交推送（`04bbfd7`），再做最终验证。
      - **一次自动替换误删了 74 行**。用脚本替换 `app.js` 的 `togglePause` 时，切片的终点取成了「下一个 `async function`」，把中间 6 个无关的函数一起删了；`node tools/ui_assistant_check.cjs` 仍然全部通过，因为那些函数不在它的覆盖范围里。提交前发现，从 HEAD 恢复。之后的做法：切片按函数自己的结束行界定；每次脚本替换后对比顶层函数清单（第 6 点倒数第三行）。
      - **工具中断一次**，下一轮恢复，没有丢东西。
      - **jsdom 里 `init` 跑两遍**，见第 5 点。新脚本 `ui_r209_check.cjs` 按同样的办法处理（先去掉监听再调一次）；不这样做的话，B3 数出来的请求次数会比浏览器里多 1。
  12. **没有验证的**。
      - 真实模型：全部是假响应。模型路径上的侧别绑定、澄清，只验证了服务端拿到某种模型输出之后的行为。
      - 真实浏览器：补-B4 的配色只核对了样式表；提示条、子界面名称只看了 DOM 文字；窄屏没有看。
      - Windows：`--app-log-level` 和日志输出只在 Linux 上试过。
      - Excel：没有实际用 Excel 打开和保存意图配置文件。
      - 直接用 uvicorn 启动时程序的 INFO 日志仍不输出（没有改，文档已写明）。
      - 流式响应里模型的工具调用不带 `arguments` 的情形仍没有用例（T-020 遗留 1）。
      - `docs/智能问答助手基于大模型技术的意图识别技术设计文档.md`（V2.0）没有按这次的改动更新（立项时列为不在范围）。
- **是否进入 REPORT.md（稳定结论）**：是，只进方法论教训：第 5 节新增 2 条（涉及两侧的功能没有在两侧状态不同的情况下测过；不在回归入口里的检查脚本无声过期），`REPORT.md` v0.13。产品行为本身不进入。
- **遗留问题**：
  1. 补-A12、补-A13、补-A14、补-B6、补-B7 未修，登记在 `STATUS.md`「下一步」。
  2. 真实模型、真实浏览器、Windows、Excel 未验（第 12 点）。
  3. 数据处理页的 6 个旧脚本和 `ui_r209_check.cjs` 都不在 pytest 里，要有临时服务才能跑，容易被漏跑。
  4. `main` 上仍没有程序代码，用户没有答复。
  5. 以前登记、这次没有处理的：流式工具调用不带 `arguments`；`tool_intent_hint()` 无人调用；README 的验证记录和变更记录整段在知识库里；意图识别设计文档；`node_modules/` 缺 10 个文件；全量 pytest 在当前目录留下 `data/`、`output/`；`elec_tool.__version__`。

## [2026-11-11] 专题 T-024：数据处理页新增「波形预览」子界面（多个可增删的预览模块；离线波形 CSV 与实时监测输出文件）

- **类型 / 模式**：用户专题（实现＋验证）；模式 A（沙盒自执行），角色为工程实现工程师。2026-11-11 立项（`1a26e4e`），当日完成。分支 `arena/51b63974-nilm-calc-tool`，开局远端 tip `006e777`。没有真实浏览器，没有用户的部署环境和现场数据：界面检查用 jsdom；用到的文件是合成信号经真实引擎播放后写出的，或按同样格式手写的。
- **目标与假设**：用户 2026-11-11 的要求，原话：「修改代码，数据处理界面增加波形预览子界面功能，具体要求如下：1.支持动态配置并展示多个波形预览模块；2.每个波形预览模块支持可选加载离线数据源CSV波形数据文件（电压和电流）和实时监测输出的波形文件（支持电压、电流、有功、无功、功率因素）进行波形曲线显示；3.离线数据源CSV波形数据文件曲线显示支持文件路径、展示的数据时间段、计算曲线数据点的需要的周波数可配置均可配置 4.实时监测输出的波形文件曲线显示支持文件路径可配置」
  - 要求里没有写明的地方，立项时由我定了做法并写进 `STATUS.md`「当前目标」，见结果第 8 点。影响最大的两条：离线波形 CSV 显示的是有效值曲线（要求 3 说「计算曲线数据点的需要的周波数」，按“每个点由 N 个周波算出”理解），不是原始采样波形；「实时监测输出的波形文件」按实时落盘写出的曲线 CSV 理解。
  - 界面上的名称用「波形预览」。第三项任务（T-023）刚把原来的「波形预览」改名为「波形分析」，两者不是同一个功能：新子界面的内部标识是 `wave-board`，原子界面的 `wave-preview` 不动。
  - 完成标准（立项时登记）：读取实时监测输出文件的函数与接口有 pytest 用例；新增 jsdom 脚本对着临时服务检查；第三项任务里因为多了一个按钮而要改预期的检查在交付时列出；全量 pytest 无失败；`node tools/ui_assistant_check.cjs` 通过；四份手册 `--check` 为 `OK`；README 与 `STATUS.md` 更新；全部提交并推送。
- **方法 / 数据 / 参数**：
  - **后端（`7d4f8bf`、`23d0ac9`）**。新文件 `elec_tool/monitor_curve.py`：读实时落盘的曲线 CSV，先按数据来源（总线侧 / 分路侧）、再按运行批次筛选，然后按时间筛选、排序、抽稀。`app/server.py` 新增两个 GET 接口 `/api/process/monitor/files`、`/api/process/monitor/curve`。离线波形 CSV 沿用已有的 `/api/process/wave/rms`，没有新增接口。
  - **前端（`16cdcb8`、`9e7a756`、`841984f`）**。`index.html` 新增页内导航按钮和子界面容器；`app.js` 新增 `wb*` 共 58 个函数；`style.css` 新增 `.wb-*` 一段，只用主题变量。公共绘图部分加了两处可选开关：图例勾选状态可以由图表自己保管（`cv.__hiddenOwn` / `cv.__onSeriesToggle`），时间轴可以不套用「公共时间段」（`opt.ownRange`）。
  - **文档（`e586a17`）**。README 升到 v0.99.51：§3.1 新增一节，另改 §3.4 接口清单、§11、变更记录、目录树、状态行；重新生成手册。写进 README 的每一条行为，动笔前都对着代码核对过；核对时发现「保存曲线数据」文件也能读这一条只有注释、没有读过真文件，先补了用例（第 5 点 ⑤）。
  - **验证手段**。
    - pytest `tests/test_r210_wave_board.py`（22 条）。读取器的用例用手写的小文件。接口的 6 条用同进程 `TestClient` 走真实 HTTP 接口，其中 4 条由真实的引擎线程播放一份 3 秒的合成录波，再读它写出的文件；数值与信号的解析值比较。
    - jsdom 脚本 `tools/ui_r210_check.cjs`（75 项）：驱动真实的 `index.html` + `app.js`，对着在 `/tmp` 下仓库副本里临时启动的真实服务（`python cli.py serve`，127.0.0.1:8766，服务与脚本同为东八区）。脚本自己在总线侧播放一份 6 秒的合成录波来产生实时监测输出文件，另外按同样格式手写一份含两侧、两次运行的电压文件。每项配置的检查方式是：改了它之后，发给服务端的请求和画布拿到的曲线数据是否跟着变。
    - 变异检查：在仓库副本里把代码改坏一处，再跑一遍 jsdom 脚本，看有没有检查项失败。共 20 个变异（第 4 点）。
    - 反向对照：把用例放到本轮第一版读取器（`7d4f8bf`）上运行。
    - 静态断言：`tests/test_web_ui.py` 新增 4 条。
- **用户执行命令（含实录路径）**：本节无用户命令。全部命令在沙盒执行，输出摘录见下，没有单独的实录文件。
- **结果 / 结论**：
  1. **提交**（均已推送）。`1a26e4e` 立项，只改 `STATUS.md`；`7d4f8bf` 读取器与两个接口；`23d0ac9` 半行与粘连行；`16cdcb8` 界面、用例、检查脚本；`9e7a756` 页面高频重画时不做重复工作；`841984f` 宽度核对、「保存曲线数据」文件的用例、检查脚本的一处时序；`e586a17` 文档；另有本专题所在的台账提交。`006e777..e586a17` 共 14 个文件，+2554 / −33 行，其中程序代码 5 个文件 +1097 / −3 行。
  2. **对照用户的 4 条要求**。

     | 要求 | 做法 | 覆盖它的检查（`ui_r210_check.cjs` 的项号） |
     | --- | --- | --- |
     | 1 动态配置并展示多个模块 | 工具条添加两种模块；模块可改名、上移、下移、复制、收起配置、删除，可全部删除；每行 1 个或 2 个；最多 12 个。模块清单和配置存浏览器本地，重开页面恢复并自动重新读取 | M1～M14、L1～L7 |
     | 2 每个模块可选两种文件 | 模块内「数据源类型」可随时切换，两种类型的配置各自保留。离线波形 CSV：三相电压、电流有效值曲线各一张图。实时监测输出文件：电压 / 电流 / 有功 / 无功 / 功率因数五种量，一个模块显示一种 | M9、O5～O7、R2～R9；pytest 的接口用例 |
     | 3 离线：文件路径、时间段、周波数可配置 | 文件下拉或手填路径；起止时刻，留空＝整个文件；每个点的周波数，默认 10 | O1～O4、O9～O11、O15～O17 |
     | 4 实时监测输出：文件路径可配置 | 文件下拉（实时落盘目录和最近 5 个运行目录）或手填路径 | R1、R2、R11 |

     要求之外、为了能用而加的配置：实时监测输出模块的数据来源、运行批次、起止时刻、只看最近 N 分钟、自动刷新；离线模块的显示开关、PT、CT、额定频率、文件时标是否为 UTC、曲线点数上限。用法见 README §3.1「数据处理子界面：波形预览」。
  3. **验证结果**（2026-11-11，最终的代码与文档内容 `e586a17`）。
     - `.venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs` → `716 passed, 1 skipped, 1 warning in 213.19s`。跳过的是 `tests/test_cli.py:46`（原有）；warning 是 `StarletteDeprecationWarning`（原有）。716 = 上一轮 690 + `tests/test_r210_wave_board.py` 22 + `tests/test_web_ui.py` 新增 4。
     - `JSDOM_DIR=/tmp/uitest node tools/ui_assistant_check.cjs` → `PASS 210 checks`。
     - `tools/ui_r210_check.cjs` 对临时服务 → `PASS：通过 75 项，失败 0 项`（准备 1、N 6、M 14、O 20、R 24、L 7、X 3）。R19 的时序改掉之后连续 5 次相同：前 3 次是 O18 加强之前的脚本，后 2 次是最终的脚本（`841984f`、`e586a17` 各 1 次）。
     - `tools/ui_r209_check.cjs` 对临时服务 → `PASS：通过 41 项，失败 0 项`。
     - 数据处理页 6 个旧脚本（通过 / 失败）：`ui_r8` 70 / 0、`ui_r61` 48 / 0、`ui_r72` 30 / 1、`ui_r80` 10 / 0、`ui_r86` 18 / 0、`ui_r90` 13 / 0，与 T-023 收尾时相同；`ui_r72` 的 1 项失败仍是补-B7。
     - `.venv/bin/python tools/generate_assistant_docs.py --check` → 四份均 `OK`。`python cli.py selftest` → 44 / 44。`tmp/` 校验和前后一致。
     - `app.js` 顶层函数 418 → 476，新增的 58 个都以 `wb` 开头，没有减少。pyflakes：`app/server.py` 5 条（`006e777` 时 8 条，都是原有的未使用导入），两个新文件 0 条。
     - 反向对照：`23d0ac9` 的 21 条用例放到 `7d4f8bf` 的读取器上 → `2 failed, 19 passed`，失败的是 `test_a_line_still_being_written_is_not_read`、`test_glued_lines_and_impossible_times_are_skipped`。把读取器改成“没有 `run_id` 列就拒绝” → `2 failed, 20 passed`，失败的是 `test_legacy_file_without_source_and_run_columns`、`test_saved_curve_files_can_also_be_read`。
  4. **变异检查**（最终的检查脚本和代码上重跑了一遍，20 个全部被发现）。

     | 改坏的地方 | 失败的检查项 |
     | --- | --- |
     | 离线：请求不带起止时刻 | O10、O11、L4 |
     | 离线：每个点的周波数恒为 1 | O3、O4、O6～O11、O11b、O17、L4 |
     | 离线：请求不带 PT 变比 | O13 |
     | 离线：模块的时间轴套用「公共时间段」 | O11b |
     | 监测：不读「文件路径」输入框 | R11～R19、R21、L2～L4 |
     | 监测：请求不带「显示的量」 | R7、R9 |
     | 监测：请求不带「数据来源」 | R10、R16 |
     | 监测：运行批次恒为最近一次 | R14、R15、L4 |
     | 监测：请求不带「只看最近」 | R17 |
     | 监测：不在本子界面时也自动刷新 | R22、R22b |
     | 读取器：读没写完的最后一行 | R21 |
     | 图例勾选仍写运行配置 | L1、L5、X1、X3 |
     | 不保存到浏览器本地 | M5（M 段随后中断）、L2～L6 |
     | 打开页面时不恢复 | L3～L7 |
     | 恢复后不自动读取 | L4、L5 |
     | 去掉 12 个模块的上限 | M13 |
     | 切换数据源类型时清空配置 | M9、M12 |
     | 每次页面重画都重排曲线数据并重画 | O18、O19 |
     | 每次页面重画都去列文件 | O18 |
     | 每秒的定时检查不核对宽度 | O19 |

     “每次页面重画都去列文件”第一次没有被发现：列文件有 5 秒的节流，检查只看了 0.3 秒。把 O18 改为先把“上次列文件的时间”清零、再看 1.3 秒之后才测得出来。
  5. **实现过程中自己发现并改掉的问题**。
     已经提交之后才发现的 6 条（括号里是改掉它的提交）：
     - ① 读取器读了没写完的最后一行：被截断的 `run_id` 会被当成另一次运行，「最近一次运行」只剩一个点（`7d4f8bf` 里有，`23d0ac9` 改）。
     - ② 半行后面续写、两行粘成一行时，numpy 的解析器按列号取值，不报错而是取到错位的格子。改为逗号总数对不上就逐行解析，比表头长的行整行跳过。断在时间格子里时粘出来的“时间”是天文数字，大于 1e11 秒的行不用（`7d4f8bf` 里有，`23d0ac9` 改）。
     - ③ 引擎运行时整个页面每 0.2 秒重画一次，子界面的“显示时”钩子挂在这上面，于是每 0.2 秒把每条曲线的几万个点重新整理一遍，每 5 秒重新列一次文件。`16cdcb8` 推送之后复查时发现，`9e7a756` 改：曲线数据按“同一次读取的结果”缓存；只有宽度变了才重画；只有离开过子界面再回来才重新列文件（O18）。
     - ④ 出现滚动条这类变化不触发页面重画，引擎不运行时模块会一直按旧宽度画。每秒的定时检查里加了宽度核对（`841984f`，O19）。这一条在 jsdom 里只能用替换 `clientWidth` 取值函数的办法模拟，真实浏览器里没有看过。
     - ⑤ 读取器的注释写着「保存曲线数据」写出的文件也能读，但没有读过真文件。补了用例：真实引擎播放 → 保存曲线 → 读回来，与同一次运行的实时落盘文件逐点相同（`841984f`）。读取器本身不用改。
     - ⑥ 检查脚本 R19 的一处时序竞争：自动请求数从追加文件之后才数，第一次自动读取若在追加之前发出、追加之后才读到文件，曲线已经更新而计数为 0，误报失败。出现过 1 次（74 / 1，「原 30 点 → 35 点；自动请求 0 次」），改为从打开自动刷新那一刻数起（`841984f`）。这是检查脚本的问题，界面行为没有问题。

     界面第一次提交（`16cdcb8`）之前复查时改的 4 条（改之前的状态没有入库）：
     - ⑦ 模块的曲线会被两侧播放的「公共时间段」截掉；模块的图表改为不套用它（O11b；去掉这个开关的变异会让 O11b 失败）。
     - ⑧ 读取队列里的重画加了异常保护：画图出错只记到浏览器控制台，后面的模块照常加载。没有对应的检查项。
     - ⑨ 恢复时对浏览器本地存储内容的容错：不能解析就按没有模块处理；不是对象的条目丢掉；取值不合法的字段回到默认值（L7）。
     - ⑩ 起止时刻写错时，服务端的报错原来一律写“起始时间”，分不清是哪个输入框；改为写明「起始时刻」或「结束时刻」（`tests/test_r210_wave_board.py::test_monitor_curve_errors_are_400_with_a_readable_message`）。
  6. **改了预期的检查**（3 处）。前两处是上一轮的检查，原因是界面上多了一个叫「波形预览」的子界面；第三处是本轮自己的用例。
     - `tests/test_web_ui.py::test_wave_subview_is_named_wave_analysis_and_keeps_internal_ids`：原来断言页面里不再出现「波形预览」，改为只允许出现在新子界面自己的按钮和容器里。
     - `tools/ui_r209_check.cjs`：N1 的子界面按钮数 5 → 6；N5 由“数据处理页不再出现「波形预览」”改为“除了新子界面自己，别处不出现「波形预览」”；N3 对每个子界面按钮各检查一次，随按钮数多出 1 项，共 40 → 41 项。
     - `tests/test_r210_wave_board.py::test_fast_and_slow_parsers_give_the_same_result`（本轮 `7d4f8bf` 新增、`23d0ac9` 修改）：“半行里有的格子照用”改为“比表头短的完整行照用”，因为半行现在不读。
  7. **数值核对**。jsdom 脚本里的 6 秒录波：相电压峰值 81.65 V（有效值 57.735 V）；电流峰值前 3 秒 7.07 A（有效值 4.9992 A）、之后加倍；电流滞后 0.3 rad。服务端 PT 1 / CT 1。离线模块和监测模块读到的值：电压 57.735 V；电流 4.999 / 9.998 A；有功 827.22 / 1654.45 W；无功 255.89 / 511.78 var；功率因数 0.9553。按公式算的值：有功 3 × 57.735 × 4.9992 × cos 0.3 = 827.22 W，无功 3 × 57.735 × 4.9992 × sin 0.3 = 255.89 var，功率因数 cos 0.3 = 0.9553；后 3 秒的有功、无功加倍。pytest 的接口用例对另一份 3 秒录波做同样的比较，容差 1%（功率因数 0.01）。读取器速度：43 万行、91 MB 的文件约 1.2 秒（开发时的一次实测，记在 `7d4f8bf` 的提交说明里；探针脚本没有入库）。
  8. **由我决定、用户可以改的事项**（共 12 条）。
     - ① 离线波形 CSV 模块显示有效值曲线，每个点由连续 N 个周波算出，默认 10；不显示原始采样波形。理由：要求 3 的「计算曲线数据点的需要的周波数」只有对有效值曲线才有意义；原始波形在「波形分析」里已有。另一种做法：模块里再加一张原始波形图。
     - ② 「实时监测输出的波形文件」＝实时落盘写出的曲线 CSV（`voltage` / `current` / `power` / `power_factor` 四种文件）。理由：程序在监测时持续写出、并且含有功、无功、功率因数的文件只有这一种。如果用户指的是别的文件，需要给出样例。
     - ③ 模块清单和配置保存在浏览器本地，不写运行配置，不在服务端保存。理由：数据处理页其他子界面的配置也是这样保存的；预览不应改动运行配置。代价：换浏览器或换电脑后不保留。
     - ④ 最多 12 个模块。理由：每个模块都要读文件、占画布，需要一个上限；12 是我定的数。
     - ⑤ 离线模块的 PT、CT、额定频率、时标留空时取出厂配置（PT 1、CT 1、50 Hz），不跟随两侧的运行配置；不提供列映射、接线方式、电流极性。理由：与「波形分析」的独立基准配置一致；立项时已列为不在范围。
     - ⑥ 实时监测输出模块默认只显示最近一次运行；两侧都有数据时默认总线侧。理由：同一份离线文件重复播放时各次的数据时间重叠，合在一起画会来回折返。
     - ⑦ 自动刷新默认关，可选 2～60 秒，只在本子界面显示时刷新，读得慢时间隔拉长到耗时的 4 倍。
     - ⑧ 选中离线文件只显示文件信息，要点「加载曲线」才读；选中监测文件立即读，改任何一项配置都立即重读。理由：离线波形文件可能很大，监测文件读得快。
     - ⑨ 各模块读曲线的请求排成一队，一次只发一个。
     - ⑩ 模块图表的图例勾选状态按模块存在浏览器本地；时间轴不受「公共时间段」限制。
     - ⑪ 没写完的最后一行不显示；粘连的行整行跳过并提示行数。
     - ⑫ 版本记为 v0.99.51 / 第 210 轮；`REPORT.md` 不更新（第 10 点）。
  9. **顺带发现、只登记没有处理**。补-C1：README 至少有 4 处仍把 PT 100 / CT 15 写成界面或配置文件的默认值（§3.1 手工点检表的「PT=100、CT=15…均已回填」、§4.0 一览表、§4.7、§6 配置表）。实际情况：`configs/default.json` 从 v0.99.23 起是 PT 1 / CT 1，界面的出厂值和 `cli.py` 各子命令默认读的都是这个文件；代码级缺省（`AppConfig()`）和 `selftest` 的工况仍是 100 / 15。README 里其余带 PT=100、CT=15 的命令输出实录没有逐条核对。这些不是本轮写的，核对离线模块的 PT、CT 缺省值时看到，没有改。
  10. **`REPORT.md` 触发检查**：算法路线＝无变化；稳定实验结论＝无新增；KPI / 验收口径＝无变化；重大工程事故或方法论教训＝无（第 5 点的问题都在本任务内发现并改掉，属于常规实现缺陷）；推荐稳定版本＝无变化。五项都不成立，`REPORT.md` 没有改。
- **是否进入 REPORT.md（稳定结论）**：否（界面功能与读文件接口，不是算法结论）。
- **遗留问题**：
  1. 真实浏览器没有验证：排版、配色、每行 2 个时的宽度、曲线画出来的样子、滚轮和拖动等鼠标操作、右键菜单，都只有代码和 jsdom 检查作依据。jsdom 不做排版，也不画图。
  2. Windows 没有验证。
  3. 没有用现场写出的实时监测输出文件和现场的离线波形文件试过。很大的离线波形文件在这个子界面里的加载耗时没有测（接口是已有的 `/api/process/wave/rms`）。
  4. 第 8 点的 12 条待用户确认，尤其是 ① 和 ②。
  5. `tools/ui_r210_check.cjs`、`ui_r209_check.cjs` 和 6 个旧脚本不在 pytest 里，要有临时服务才能跑。
  6. 上一轮登记的补-A12～A14、补-B6、补-B7 和本轮登记的补-C1 没有处理；`main` 上仍然没有程序代码。
- **T-024 补充（2026-11-11，收尾提交 `8eee08d` 之后）**：
  1. 调参手册 `NILM_TUNING_GUIDE.md` 有两处用「原名 / 之前叫「波形预览」」指代现在的「波形分析」（§1「不想开命令行？」一段、设备画像提取步骤第 1 条）。这两句是上一轮（T-023）改名时写的，本身没有错；本轮新增了一个叫「波形预览」的子界面之后，读的人可能把两者当成同一个功能。两处都补上「v0.99.51 新增的「🧩 波形预览」是另一个子界面」，并重新生成 `docs/软件算法调参与验证文档.md`（提交 `2b9c9c8`）。程序和测试没有改动。
  2. 这次修改之后重跑：全量 pytest `716 passed, 1 skipped, 1 warning in 206.53s`；`node tools/ui_assistant_check.cjs` → `PASS 210 checks`；四份手册 `--check` 均 `OK`；`tmp/` 校验和不变。jsdom 的界面脚本（`ui_r210_check.cjs` 等）没有重跑：它们不读这两份文档。
  3. 第 3 点写的「最终的代码与文档内容 `e586a17`」因此要读作：程序、测试、检查脚本和 README 的最终内容是 `e586a17`；调参手册和它生成的那一份手册的最终内容是 `2b9c9c8`。

## [2026-11-11] 专题 T-025：设备画像匹配能否只用一相电流完成画像提取和匹配（第 211 轮；只分析，没有改程序）

- **类型 / 模式**：用户专题（代码分析＋合成数据实验）；模式 A（沙盒自执行），角色为资深电力算法专家（`ROLE.md` 默认角色，本任务没有角色覆盖）。2026-11-11 当日完成。分支 `arena/51b63974-nilm-calc-tool`，开局远端 tip `0a7904d`。程序、测试、文档源都没有改，版本仍是 v0.99.51。没有现场数据：全部实验用合成波形，下面的数字都来自合成波形。
- **目标与假设**：用户 2026-11-11 的问题，原话：「分析代码基于设备画像匹配算法负荷辨识事件检测功能，是否可配置只使用其中1相电流进行完成设备画像提取及基于该相的设备画像匹配来完成负荷辨识事件检测」。
  - 按两问回答：① 设备画像提取能不能只用一相电流；② 总线侧能不能只按这一相做画像匹配。
  - 「只使用其中 1 相电流」有两种读法，两种都分析。宽的读法：声明设备只接在某一相，匹配时只比这一相的电流增量。严的读法：画像的每一个特征都只来自这一相的电流，不用电压，也不用另外两相。
  - 用户没有要求改代码，本任务不改程序；分析中发现的问题只登记（结果第 7 点）。
- **方法 / 数据 / 参数**：
  - **读代码（只读）**：`elec_tool/nilm_profile.py`（`event_features`、`detect_phases`、`profile_skip_dims`、`profile_phase_rows`、`match_event`、`detect_profile`、`phase_map_code`、`build_profile`）、`elec_tool/nilm.py`（`CycleFeatures.push`、`NilmDetector._profile_health_check`、`_evaluate_profile`、`_evaluate_one_profile`）、`elec_tool/config.py`（`ColumnMap`、`NILM_ALGO_DEFAULTS`、`NilmConfig`）、`elec_tool/nilm_auto.py`（`window_stats`、`_hold_length`）、`elec_tool/wave_preview.py`（`apply_col_map`）、`elec_tool/engine.py`（调用 `NilmDetector.ingest` 的位置）、`app/server.py`（`POST /api/process/nilm_profile`）、`app/static/app.js`（`npPayload`、`cmMap`、`collectNilmPayload`）、`tools/nilm_profile.py`、`tools/nilm_replay.py`、调参手册 `NILM_TUNING_GUIDE.md` H.32。
  - **合成波形**：6400 Hz、50 Hz、相电压 230 V，7 列（时间, A相电压, A相电流, B相电压, B相电流, C相电压, C相电流）。
    - 设备：A 相 3 A（有效值），电流滞后电压 30°，带 10 % 的 5 次谐波，启停过渡 0.06 s。设备侧文件 42 s，启动 3 次、停止 3 次（幅值 3.00 / 3.05 / 2.96 A），电流噪声 0.004 A。另有只含 3 列（时间、A 相电压、A 相电流）和只含 2 列（时间、A 相电流）的版本。
    - 总线侧文件 56 s：每相 20 A 的背景负荷（滞后 25.8°，噪声 0.02 A）；设备在 8 s、35 s 启动，20 s、47 s 停止；另有一个 B 相 4 A 的负荷在 28 s 投入、52 s 切除（离设备动作至少 5 s，不在画像的前后窗里）。
    - 变体：每次设备动作后 0.4 s 在 B 相（或 A 相）投切一个 2 A 负荷（落在画像后窗里）；设备接在总线 C 相；三相设备（每相 3 A）的设备侧和总线侧文件；设备停机期间在 A 相先后投切两个电流同为 3 A 的其他负荷（电阻性，滞后 0°，23～26 s；感性，滞后 80°，28.5～31.5 s）；背景负荷的相角改为滞后 0°、超前 30°；事件间隔 20 s 的 130 s 设备侧文件（试自动定位用）。
  - **运行方式**：提取走 `build_profile`，匹配走 `NilmDetector`，数据经 `create_source` + `scale_block` 喂入（与 `tools/nilm_replay.py` 相同；实时引擎 `elec_tool/engine.py` 调的也是 `NilmDetector.ingest`）。6 种标量算法关闭，只开画像匹配，参数用出厂值（`d2_max` 9、`min_confidence` 0.3、`k_sigma` 4、`min_stage` 0.5、`phase_map` 1、`max_scale` 8、`min_scale` 0.25、`state_check` 1），PT / CT 为 1，接线 3P4W，前后窗 10 / 50 周波。提取时给人工启停标签（专门试自动定位的一组除外）。
  - **「只取一相」的实现办法**：离线文件列映射。启用列映射，只给要用的列填列号，其余留空；留空的通道按 0 播放（`ColumnMap.mapping` 的既有行为）。
  - **真实入口复核**：`tools/nilm_profile.py --config <列映射只留时间和 A 相电流的配置>` 与 `tools/nilm_replay.py --config <同一份> --set profile.enabled=1 --set nilm.profile_path=<画像>` 各跑一遍；在 `/tmp` 下的仓库副本里起临时服务（127.0.0.1:8767），按界面 `npPayload()` 的请求体形状调 `POST /api/process/nilm_profile` 3 次。没有通过网页把总线侧实际播放一遍。
- **用户执行命令（含实录路径）**：本节无用户命令。全部命令在沙盒执行；实验脚本和合成数据放在 `/tmp/probe/t5`，不入库，沙盒重置后消失；关键输出摘录在下面的表里，没有单独的实录文件。
- **结果 / 结论**：
  1. **结论：能，靠现有配置就能做到，不用改程序；但效果取决于怎么配。** 有三种做法：
     - **做法一：只在提取时把「设备相别」声明为单相**（v0.99.30 的既有功能）。只做到一半：候选台阶和电流增量只看这一相，有功、无功、谐波电流、启动峰值比、轨迹仍按三相算。另外两相有负荷落在前后窗里时，有功、无功被带偏，真事件可能被拒（第 3 点第 2 行：B 相 2 A 负荷，4 次全拒）。同一份数据不声明单相、按三相画像处理反而能接受（第 24 行），原因见第 7 点 补-D5。
     - **做法二：两侧都用列映射只取这一相的电流**。画像的每个特征都只来自这一相的电流，另外两相的负荷不再有影响（第 6 行：4 次全部 `confirmed`）。代价是区分能力明显变弱：同一相上电流台阶相近的其他负荷会被认成这台设备（第 9 行：两个 3 A 的其他负荷都被报成设备启停）。
     - **做法三：两侧都用列映射只取这一相的电压和电流**。同样不受另外两相影响（第 5 行），并保留有功、无功两个特征，第 9 行那两个负荷都被拒（第 10 行）。这一相的电压拿得到时，三种里它最稳妥。
  2. **代码依据：画像声明为单相时，每个量取自哪里**（`event_features`、`detect_profile`、`CycleFeatures.push`）。

      | 量 | 取法 | 只看声明的相吗 |
      | --- | --- | --- |
      | 候选台阶序列 | P 口径：声明相的有功之和；I 口径：声明相电流的方和根 | 是 |
      | `d_ia` / `d_ib` / `d_ic` | 各相电流有效值在前后窗的中位数之差；未声明的相不参与 D²，也不计入维数 | 是 |
      | `d_p`、`d_q` | 三相之和 | 否 |
      | `d_ih`（2～13 次谐波电流） | 三相平均 | 否 |
      | `peak_ratio`、轨迹模板 | 三相电流的方和根 | 否 |
      | `dur_cycles` | 匹配时：候选序列上的过渡时长。提取时：事件在三相合成序列上定位，过渡时长也在它上面量（设备侧只有这一台设备时，两者相同） | 匹配时是 |
      | 相邻变点（用来截短前后窗、避开别的负荷） | 只在候选序列和声明相的无功序列上找 | 是 |
      | 候选门槛 | P 口径：`min_stage` × 画像的 `d_p`（三相之和）；I 口径：`min_stage` × 画像里声明相的电流增量 | P 口径否，I 口径是 |

     - 匹配一侧没有相别参数。`nilm.algorithms.profile` 的 15 个参数里没有，相别只来自画像文件的 `phases` 字段。
     - 「检测对象」`nilm.channels`（total / A / B / C）只管 6 种标量算法，对画像匹配不起作用。实测取 total、A、B，画像事件完全相同，事件的 `channel` 都是 `total`。
     - 「检测量」`nilm.quantity` 选 I，只是把候选台阶序列从有功换成电流，`d_p`、`d_q` 仍在特征向量里（第 3 点第 4 行）。只有两侧都没有电压时，这两维才在两侧都是 0。
     - 只映射一相时，表里的「三相之和 / 三相平均 / 方和根」算出来就是这一相自己的值（谐波电流是这一相的 1/3），两侧同样处理，可以直接比较。做法二、三靠的就是这一点。
  3. **实验结果**。设备在总线上动作 4 次（2 次启动、2 次停止）；「4 / 4」表示 4 次都报成了事件，状态写在后面；「0 / 4」表示 4 次都没有报出来。

      | 行 | 画像怎么提 | 总线侧取哪些通道 | 总线上的情况 | 结果 |
      | --- | --- | --- | --- | --- |
      | 1 | 7 列全取，相别自动（判为 A），P 口径 | 三相全取 | 没有负荷落在画像的前后窗里 | 4 / 4 `confirmed`，置信度 1.000；B 相 4 A 负荷不产生候选 |
      | 2 | 同第 1 行 | 三相全取 | 每次动作后 0.4 s，B 相投切 2 A | 0 / 4。4 个真事件全部 `rejected`：D²/维 4.40～4.51，置信度 0.105～0.111；贡献 `d_p` 21.4～21.9、`d_q` 5.0～5.1、`d_ia` 0.0 |
      | 3 | 同第 1 行 | 三相全取 | 每次动作后 0.4 s，A 相投切 2 A | 4 / 4 `low_confidence`（`window_crowded`），置信度 1.000；2 A 负荷自己的台阶被拒（`state_mismatch`，置信度约 0.19） |
      | 4 | 7 列全取，相别自动（A），I 口径 | 三相全取，检测量 I | 同第 2 行 | 0 / 4，D²/维 4.40～4.51，贡献仍是 `d_p` 21.4～21.9；没有干扰时 4 / 4 `confirmed` |
      | 5 | 只有时间、A 相电压、A 相电流，P 口径 | 列映射只取 A 相电压、电流 | 同第 2 行 | 4 / 4 `confirmed`，置信度 1.000。同一份画像、总线三相全取时 0 / 4（D²/维 4.40～4.51） |
      | 6 | 只有时间、A 相电流；口径自动成为 I | 列映射只取 A 相电流；检测量自动成为 I | 同第 2 行 | 4 / 4 `confirmed`，置信度 1.000 |
      | 7 | 同第 6 行 | 同第 6 行 | 同第 3 行 | 设备 4 次 `low_confidence`（`window_crowded`）；2 A 负荷的 4 个台阶也被报成设备的启停（`low_confidence`、`state_mismatch`，置信度 0.353） |
      | 8 | 同第 5 行 | 同第 5 行 | 同第 3 行 | 设备 4 次 `low_confidence`（`window_crowded`）；2 A 负荷的台阶被拒（置信度 0.195） |
      | 9 | 同第 6 行（只有电流） | 同第 6 行 | 设备停机期间，A 相先后投切 3 A 电阻性负荷、3 A 感性负荷 | 设备 4 / 4 `confirmed`。两个负荷的 4 个台阶全部被报成设备启停：电阻性 `confirmed`，置信度 0.974（总线上量到 2.74 A）；感性 `confirmed`，置信度 0.652（量到 1.89 A） |
      | 10 | 同第 5 行（电压＋电流） | 同第 5 行 | 同第 9 行 | 设备 4 / 4 `confirmed`。两个负荷全部被拒：电阻性置信度 0.236 / 0.118（`d_q` 贡献 16.0），感性 0.0175 / 0.0088 |
      | 11 | 同第 1 行 | 三相全取 | 同第 9 行 | 与第 10 行相同：设备 4 / 4；两个负荷被拒（0.235 / 0.118，0.0175 / 0.0088） |
      | 12 | 同第 6 行（只有电流） | 三相全取、有电压，检测量 I | 没有干扰 | 0 / 4，D²/维 3170～3216（`d_p` 贡献 14252～14470）。没有任何提示说两侧通道不一致 |
      | 13 | 第 6 行、第 5 行的画像各一次 | 与画像对应 | 背景负荷电流与设备电流的相角差为 4.2° / 30° / 60° | 第一次启动在总线上量到的电流增量 2.995 / 2.649 / 1.659 A（按相量算 2.993 / 2.648 / 1.656 A）；置信度 1.000 / 0.956～0.960 / 0.537～0.543，两种做法相同；I 口径的候选门槛是 1.507 A |
      | 14 | 同第 1 行（相别 A） | 三相全取 | 设备接在总线 C 相 | 没有候选。相序映射取 1、4、6、数值 0、字符串 `"0"` 都一样 |
      | 15 | 设备侧用列映射把这一路电压、电流放进 C 相的列（判为 C） | 三相全取 | 同第 14 行 | 4 / 4 `confirmed` |
      | 16 | 同第 1 行（相别 A） | 列映射把总线 C 相的电压、电流放进 A 相的列 | 同第 14 行 | 4 / 4 `confirmed` |
      | 17 | 电流在 A 相的列里，人工指定相别 C | 三相全取 | 同第 14 行 | 相序映射 1：0 / 4，D²/维 35.2～35.7（`d_ic` 贡献 211～214）。相序映射 6：4 / 4 `confirmed`，但这时设备的电流增量没有参与比较（被比较的是两侧都为 0 的那一维） |
      | 18 | 三相设备，相别自动（ABC），P 口径 | 三相全取 | 每次动作后 0.4 s，B 相投切 2 A | 4 / 4 `low_confidence`（`window_crowded`），置信度 0.997 |
      | 19 | 三相设备，人工指定相别 A，P 口径 | 三相全取 | 有没有干扰都一样 | 没有候选：门槛是 0.5 × 1794.6 W ＝ 897 W，A 相的台阶只有 598 W |
      | 20 | 三相设备，人工指定相别 A，I 口径 | 三相全取，检测量 I | 没有干扰 / 同第 18 行 | 4 / 4 `confirmed`，置信度 1.000、0.997 / 0.770～0.784（`d_p` 量成 2208 W，画像是 1794.6 W） |
      | 21 | 三相设备，列映射只取 A 相电压、电流 | 同样只取 A 相电压、电流 | 同第 18 行 | 4 / 4 `confirmed`，置信度 1.000 |
      | 22 | 三相设备，列映射只取 A 相电流 | 同样只取 A 相电流 | 同第 18 行 | 4 / 4 `confirmed`，置信度 1.000 |
      | 23 | 同第 21 行 | 三相全取 | 没有干扰 | 0 / 4，D²/维 40.1～41.0（`d_p` 贡献 177～181） |
      | 24 | 单相设备（同第 1 行的文件），人工指定相别 ABC，P 口径 | 三相全取 | 同第 2 行 / 没有干扰 | 4 / 4 `low_confidence`（`window_crowded`），置信度 1.000 / 4 / 4 `confirmed`，置信度 1.000。B 相负荷自己的台阶都被拒（`d_ib` 贡献 94～374） |

     - 提取结果：单相设备的 7 列、3 列、2 列文件，相别都自动判为 A；启动画像 `d_ia` 3.014 A、`d_ih` 0.100 A；有电压时 `d_p` 598.2 W、`d_q` 345.3 var，没有电压时 `d_p`、`d_q` 为 0（σ 取下限 5）。三相设备人工指定 A 时，软件提示「指定的相别 A 与数据里最显著的相别 ABC 不一致」，画像里 `d_p` 仍是三相之和 1794.6 W。
     - 自动定位（不给启停标签）：事件间隔 20 s 的 130 s 文件，7 列全取（P 口径）和只取 A 相电流（I 口径）各一次，都找到 3 次启动、3 次停止，时刻正确。42 s、相邻事件只隔 6～7 s 的那份文件报「文件太短（不足 60 个有效周波）」，见第 7 点 补-D3。
     - 真实入口：`tools/nilm_profile.py` 在列映射只留时间和 A 相电流时写出 I 口径、相别 A 的画像；`tools/nilm_replay.py` 用同一份配置回放第 2 行的总线文件，打印「检测量 电流有效值 I (A)（数据源无电压）」，`profile` 行 4 个事件（投入 2、切除 2），4 个都是 `confirmed`，置信度 0.9999～1。`POST /api/process/nilm_profile` 的 3 次调用都返回 200：只留时间和 A 相电流 → I 口径、相别 A；留时间、A 相电压、A 相电流 → P 口径、相别 A；7 列全取并人工选 A → P 口径、相别 A。
  4. **怎么配置**。
     - 做法一：数据处理页 →「设备画像提取」→「设备相别」选单相 A / B / C，或留「自动判定」；命令行 `tools/nilm_profile.py --phases A`；接口字段 `phases`。总线侧不用另设。
     - 做法二、三的设备侧：「设备画像提取」里勾选「启用离线文件列映射」，只保留「时间」和这一相电流的列号（做法三再加这一相电压），其余清空；「设备相别」留自动。文件本身只有这几列、表头能识别时，不用列映射。命令行用 `--config` 指向一份 `columns.mapping_enabled` 为 true、`columns.mapping` 里其余字段为空串的配置。直接调接口时，`col_map` 里不要的字段必须显式给空串；字段缺失会按默认列号 1～7 取（`apply_col_map`）。
     - 做法二、三的总线侧：「数据源与控制」页的「总线侧 离线文件列映射」同样只保留这几列；「负荷辨识事件」页的「检测量」留自动（没有电压时自动成为 I），或与画像的口径一致；同一页勾选「设备画像匹配」并填画像路径。命令行回放：`tools/nilm_replay.py --config <同样的列映射> --set profile.enabled=1 --set nilm.profile_path=<画像>`。
     - 两侧取的通道必须一样，画像的相别必须是设备在总线上实际所在的那一相。
  5. **限制**。
     1. 列映射是整一侧数据源的设置，不是画像匹配自己的设置。总线侧只映射一相之后，这一侧的实时电气量、另外 6 种算法看到的也只有这一相，另外两相是 0。想让总线侧其余功能照常看三相、只让画像匹配看一相，现有配置做不到。界面上写明列映射是离线文件数据源（`csv_file` / `csv_tail`）的取列规则；TCP 数据源怎么只取一相，没有看也没有试。
     2. 只映射一相时，每次运行都会出现一条「画像匹配数据体检：B/C 相电流≈0 … 先修正接线方式/极性再用画像匹配」。它只是提示，不影响匹配（`_profile_health_check` 只往消息列表里加一条）；提示里「候选按三相合成量搜索」对单相画像不成立。
     3. 两侧通道不一致时软件不提示，只是一直匹配不上（第 12、23 行）。要看候选诊断里 `d_p`、`d_q` 的贡献才能发现。
     4. 只用电流（做法二）时没有有功、无功两个特征。实际起作用的只剩这一相的电流增量、峰值比、过渡时长和轨迹；谐波电流这一维的 σ 下限是 2 A，小设备基本用不上。按实测的贡献值折算，同相上别的负荷只要电流台阶与画像值相差不到约 1.9 A（画像值的六成左右；σ 取 15 % 下限、`min_confidence` 0.3 时）并且高于候选门槛，过渡时长和峰值比又相近，置信度就在 0.3 以上（第 7、9 行）。
     5. 电流有效值不能直接相加。设备电流与总线背景电流的相角差越大，总线上量到的增量越小（约为设备电流 × 相角差的余弦）。第 13 行：相角差 60° 时 3 A 只量到 1.66 A，置信度降到 0.54。按公式推算，相角差约 64° 起增量低于候选门槛（1.507 A），只用电流时连候选都没有；这一点没有实测。有电压时候选在有功上找，有功可以直接相加，不会因此漏候选，但电流增量这一维同样拉低置信度。这一点对三相画像的电流维同样成立，只是只用电流时它是主要特征。
     6. 画像的相别必须是设备在总线上所在的相。相序映射 `phase_map` 只重排总线三相的电流增量，候选台阶仍按画像里写的相去找，所以设备在另一相时没有候选（第 14 行）。可行的办法是用列映射把电流放到对应的列（第 15、16 行）。
     7. 同一相上有别的负荷落在前后窗里时，三种做法都只能得到 `low_confidence`（第 3、7、8 行）。
     8. 三相设备想只用一相：两侧都用列映射只取这一相（第 21、22 行）可以；只把「设备相别」人工指定为单相，P 口径下没有候选（第 19 行），I 口径下能匹配，但 `d_p`、`d_q` 仍是三相之和（第 20 行）。
  6. **如果要在程序里做「画像匹配只按一相」**（总线侧仍取三相，另外两相不影响匹配），要改的地方：① `event_features` 的 `d_p`、`d_q`、`d_ih`、峰值比、轨迹改为按声明的相取，提取和匹配两处同时改；② P 口径的候选门槛改用声明相的有功增量（①、② 改了之后，补-D5 的矛盾也随之消失）；③ 需要「只用电流」时，增加把 `d_p`、`d_q` 排除出匹配的开关；④ 候选所在的相跟随相序映射；⑤ 画像文件加一个字段标明特征是按哪种口径算的，旧画像按旧口径匹配；⑥ 界面、命令行、调参手册 H.32 和用例同步。本任务没有做，待用户决定。
  7. **顺带发现，只登记没有处理**。
     - **补-D1：相序映射填 0（自动）不起作用，实际按 1（ABC）执行。** `phase_map_code` 里是 `int(float(v or 1))`，数值 0 先被 `or 1` 换成了 1；只有字符串 `"0"`、`"auto"` 才得到自动。界面（`collectNilmPayload` 用 `parseFloat`）、`tools/nilm_replay.py --set profile.phase_map=0`（存成 0.0）和 JSON 配置里的 0 都是数值。实测（第 17 行的画像和总线文件）：数值 0 的结果与 1 逐位相同（0 / 4，D²/维 35.226）；字符串 `"0"` 得到 4 个事件并带 `phase_map_CAB` / `phase_map_ACB` 标志；用真实命令行 `--set profile.phase_map=0` 复现，结果同数值 0。已有用例 `test_detector_auto_phase_map_still_detects` 用的是三相平衡的数据，自动与 ABC 结果相同，所以没有发现。这一行从本分支的基线提交 `e05542a` 起就在。
     - **补-D2：调参手册 H.32.3 第一行的第二个办法照做匹配不上。** 手册写：设备侧电流被录进了别的相的列时，「改正列映射或直接指定 `--phases C`」。实测直接指定（第 17 行）：画像的相别是 C，但电流增量的均值仍在 A 相那一维，C 相那一维的均值是 0、σ 是 0.02 A；总线上设备在 C 相，量到的 3 A 与 0 比，默认相序映射下 4 次全拒。改正列映射（第 15 行）可以。
     - **补-D3：自动定位在事件很密的文件上报「文件太短（不足 60 个有效周波）」，提示与原因不符。** 那份文件有 2100 个周波。原因：`_hold_length` 把「相邻事件只隔 6～7 s、噪声很小」的序列判成了每 200 周波才更新一次的采样保持数据，抽稀后只剩 10 个点，少于 60。事件间隔 20 s 的文件正常。只试了这两种间隔，没有找临界值。给启停标签可以绕开。
     - **补-D4：只映射一相时的数据体检提示有误导，两侧通道不一致时又没有提示。** 见第 5 点的第 2、3 条。
     - **补-D5：画像声明为单相后，另外两相的负荷不再截短前后窗，却照样计入有功、无功。** 前后窗遇到相邻的变点会截短，以避开别的负荷（v0.99.24）；声明单相后，变点只在声明的那一相上找（`detect_profile` 里的 `change_points(x, …)` 和按声明相取的无功序列），而 `d_p`、`d_q` 仍是三相之和。结果是：B 相负荷在设备动作后 0.4 s 投切时，声明为 A 的画像 4 次全拒（第 2 行，没有 `window_crowded` 标志），同一份设备数据按三相画像处理则 4 次都接受（第 24 行，`window_crowded`）。调参手册 H.32.0 写了「跳维是必要但不充分」，没有写到这一层。按三相画像处理有它自己的问题（未接相的两维 σ 只有 0.02 A，窗里截不掉的他相变化会直接拒），不能当作解决办法。
  8. **与第 184 轮记录的关系**（单相画像功能的实现记录，本文件「第 184 轮」一节）。§184.5、§184.9 已写明 `d_p`、`d_q` 是三相之和、`d_ih` 是三相平均、「跳维必要不充分」，本轮复核一致。有两点是新的：
     - §184.9 撤销了「`d_p` / `d_q` 按本相重算」的待办，理由是「收益为零」。那个判断只考虑了设备自身的增量不会被另外两相摊薄。对另外两相落在窗里的负荷，按本相取是有收益的：本轮第 2 行与第 5 行用的是同一份总线数据，三相求和时 0 / 4，只取本相时 4 / 4。
     - 补-D5（声明单相后，另外两相的台阶不再截短前后窗）此前没有记录。
  9. **`REPORT.md` 触发检查**：算法路线＝无变化；稳定实验结论＝无（只有合成数据）；KPI / 验收口径＝无变化；重大工程事故或方法论教训＝无；推荐稳定版本＝无变化。五项都不成立，`REPORT.md` 没有改。README 的六类触发项（安装、运行命令、数据目录、配置结构、输出产物、生产推荐流程）也都没有变化。
- **是否进入 REPORT.md（稳定结论）**：否（合成波形上的分析，没有现场数据）。
- **遗留问题**：
  1. 没有现场数据。结论、置信度数字和「够不够用」的判断都只在合成波形上成立；真实设备的启动冲击、背景负荷波动、谐波都会改变结果。建议用一段现场的设备侧和总线侧录波，按第 4 点的做法二、做法三各回放一遍。
  2. 总线侧只通过 `NilmDetector` 和 `tools/nilm_replay.py` 回放过，没有在网页上用实时引擎播放；设备画像提取的网页界面没有在浏览器里点过，只按界面的请求体调了接口。
  3. TCP 数据源、`csv_tail`、三相三线（3P3W）接线、PT / CT 不为 1、档位自由匹配（`stage_free`）、多份画像同时挂载，都没有在「只取一相」下试过。
  4. 补-D1～D5 没有处理。
  5. 第 6 点的程序内支持做不做，待用户决定。
  6. 实验脚本和合成数据没有入库（`/tmp/probe/t5`），重做要按「方法 / 数据 / 参数」重新生成。


## [2026-11-10] 专题 T-026：设备画像自动定位漏掉停止事件（第 212 轮 / v0.99.52）

- **类型 / 角色 / 模式**：用户专题（修复＋验证），资深电力算法专家，模式 A；分支 `arena/51b63974-nilm-calc-tool`。代码 `6f8a3b7`，文档 `48643ec`。
- **目标与假设**：无标签从设备侧 CSV 提取画像时漏了多次停止。分析已有画像，复现并修复，只调整设备画像自动定位，不修改共享的在线检测、自适应参数、画像匹配或界面。
- **方法 / 数据 / 参数**：只读 `tmp/profile_周期运行设备_20261111_163532.json` 与同源标签画像 `tmp/nilm/profile_branch_profile_device_20261110_104744.json`；原始设备波形不在仓库。用户画像 60000 周波、I 口径、A 相、pre/post=10/50，启动 9 次、停止 4 次；标签画像有 10 次停止，6 次未出现在自动画像，另一次停止定位提前 55 周波。`tmp/run_info.json` 表明 `tmp/realtime` 实际是 bus4 录波的输出而非这份设备 CSV，不能用它作为该设备逐周波真值。以带运行波动和启动冲击的合成逐周波序列及合成 CSV 测试。
- **用户执行命令（待执行）**：也可在网页「设备画像提取」选择原文件与原基准配置、不填标签、pre=10、post=50、I 口径、相别 A、合并间隔 10 秒，核对结果并保存；命令行示例（替换实际路径，配置须包含原采样率、列映射及缩放）：
  `python tools/nilm_profile.py --file <原设备侧CSV> --config <原配置JSON> --device mixer --pre 10 --post 50 --merge-gap 10 --quantity i --phases A --out <新画像JSON>`。用户尚未执行，输出和现场判读待回报；不要覆盖旧画像。
- **原因与改法**：稳态分段依赖事件前的平稳段；双滑窗门槛随前窗波动升高。运行时电流有较大波动而停机电平平稳，前者更容易漏掉停止；合成波形复现了此机制，但原始现场波形未验证。保留两种检测器，对稳态事件先有条件精修起点；再检查相邻同方向主要动作间及首尾的保持状态翻转，幅值与方向足够才补入 `auto:alternation`，未确认则写 notes，仍需人工核对。最初计划的任意相邻事件电平连续性检查在漂移和星三角动作中误补，故改为交替检查；事件的起止范围内翻转视为已找到，避免两段式停止重复补报。
- **结果 / 结论（均为沙盒合成）**：
  1. 同一 1600 Hz 合成 CSV、设备波动 / 启动冲击，旧版启动 9/9、停止 4/10，新版启动 9/9、停止 10/10、无多余事件，停止起点与真值一致。18 组波形网格新版均 9/9、10/10、无多余事件；旧版只有 3 组全部正确，其他停止 0–5/10、最多多 7 个事件。
  2. 新增 `tests/test_r212_profile_auto_alternation.py` 40 项，定向 r90/r92/r165/r180/r184/r212 共 132 passed；全量 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs` 为 **756 passed、1 skipped、1 warning**（skip 60Hz 高次谐波，warning 为 Starlette/httpx 弃用）。四份生成手册 `--check` 全 OK；`tmp/` SHA256 汇总 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5` 不变。
  3. 逐周波实验：36 组中新版 35 组全部停止在 3 周波容差内；两组各有 1 个额外事件，另 1 组有 1 个停止提前 6 周波；17 组周期网格全部正确，零调制另有大量既有碎片，`build_profile` 会合并。旧有 24 组画像夹具输出与旧版一致；分级带载、长冲击、两段式停止、漂移和软停有对照用例。漂移夹具 2 个随机种子各精修一次起点，这是预期的新行为，不是全场景不变。软停可有未解决提示。
  4. 49 个变异中 45 个被新测试杀死；存活的 `no_sort_before_check`、`refine_hi_far`、`amp_short_side_not_zero`、`accept_unsigned_amplitude` 未证等价，说明排序、搜索上界、短侧振幅和方向保护的边界仍有测试缺口。新测试在旧 HEAD 直接运行因不存在新增 API 在收集期失败；另有早期插桩对照证明两个画像波形用例在旧逻辑失败。既有回归的固定期望未修改；本轮新写测试的未解决提示期望随提示措辞改为「有 3 段里还有动作没能补出来」「没有明确的突变台阶」。
- **局限 / 未处理**：① 启动冲击台阶回落、星三角后运行波动时，停止仍可能 0/3，回落反而被当成停止；缓降 ≥30 周波多只提示未解决，10–25 周波可能部分漏并有 3–17 周波延迟；强接触器抖动及长时间分级停止也可能无法补出。② 既有 `_hold_length` 在强波动或长冲击时可能误判采样保持并报「文件太短」，与补-D3 同源；低于自适应 min_delta 的干净台阶、短运行、软停与漂移碎片亦可能漏报或多报，均未改共享算法。③ 补-D1～D5、其他历史待办均未处理。④ 测试脚本以外的实验数据 / 脚本在临时目录，不入库。
- **是否进入 REPORT.md**：否；当前为针对画像提取的局部修复，效果仅合成数据验证，尚无稳定现场结论。
- **遗留问题**：请用原设备 CSV 和原配置无标签重提，核对 10 次停止的时间及幅值、额外事件与 notes，与旧标签画像对照并回报；必要时给标签，不能将自动补漏视为现场验收。


## [2026-11-10] 专题 T-027：波形预览右键显示周波瞬时采样和有效值曲线（第 213 轮 / v0.99.53）

- **类型 / 模式 / 角色**：用户专题（实现＋验证）；模式 A，资深电力算法专家；当前分支 `arena/51b63974-nilm-calc-tool`；代码 `0c73374`，文档 `fdb0c42`。
- **目标**：用户要求「波形预览模块中波形曲线鼠标右键菜单增加显示周波瞬时采样曲线及显示周波有效值曲线功能」。不改变「波形分析」，保留原右键功能。
- **数据来源的决策（用户确认）**：实时监测文件只有汇总数据，不含原始采样；用户在选项中选择为监测模块配置对应原始波形 CSV 和口径。系统不推算原始波形、不默认使用当前运行数据源；用户负责确认侧别、运行批次、时间和变比一致。
- **实现**：各模块主图右键添加两项，按所选点时间在该模块下方显示独立曲线；默认 50 周波，允许 1～1000，离线图使用实际加载的文件及 PT/CT/频率/时标。监测模块在更多选项配置原始路径、PT/CT、频率和 UTC 时标，未填时菜单置灰；电压 / 电流对应三相，功率或功率因数曲线显示源文件电压、电流。使用 `/api/process/wave/info`、`load`、`rms`，有效值按 1 周波/点，瞬时曲线不重采样，超过 200000 采样点拒绝并提示减小窗口；时间超出源文件拒绝，靠近文件边界平移。支持关闭与缩放、图例开关，模块数据和请求隔离，晚到结果不重开已关闭窗口。配置和图例存浏览器本地，不改运行配置。
- **方法 / 数据**：合成 50Hz 正弦波 CSV，测试原始采样、逐周波 RMS、PT/CT 口径和时间；`tools/ui_r213_check.cjs` 在临时服务上以 jsdom 驱动实际页面和真实只读接口，测试正常与错误路径。原始用户数据 `tmp/` 未修改，目录汇总 SHA256 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5` 不变。
- **用户执行命令 / 输出 / 判读**：无需命令；请在目标浏览器打开「数据处理 → 波形预览」，加载离线 CSV，在主图右键选择两种周波曲线；监测模块展开更多选项、填写对应原始 CSV 后同样检查。期望两张曲线分别为原始采样和每周波一点的有效值，文件、时刻和量纲正确；现场执行与输出尚待用户回报。
- **结果**：新 jsdom 脚本 22/22；旧 `ui_r210_check.cjs` 75/75、`ui_r209_check.cjs` 41/41（均对隔离临时服务）；针对 r213 / r210 / r61 / UI 的 pytest 为 68 passed / 2 skipped；最终全量 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs` 为 **759 passed / 1 skipped / 1 warning**。四份生成手册 `--check` 均 OK。
- **测试过程记录**：第一次全量 1 failed / 758 passed / 1 skipped：`test_save_only_patch_keeps_rest` 的配置保存响应为 400，失败信息未打印响应体，具体原因未定位；单独运行 r213+r63 为 11 passed，随后单独重跑完整测试 759 passed。未修改既有固定期望，不声称问题根因已解决。
- **是否进入 REPORT.md**：否，界面功能变更，不是稳定算法结论。
- **遗留问题**：未在真实浏览器、Windows 或用户现场原文件上验证；jsdom 不绘制真实图形。监测与源文件是否同一侧、批次和口径需用户确认；模块暂不提供自定义列映射、接线及电流极性设置。


## [2026-11-10] 专题 T-028：波形预览周波曲线与原曲线同一行并排（第 214 轮 / v0.99.54）

- **类型 / 模式 / 角色**：用户专题（实现＋验证）；模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`，代码 `3ef040d`、文档 `23a069c`。
- **目标与方法**：右键打开的瞬时采样或逐周波有效值图放在被选中主图右侧同一行（离线电压、电流各对应自己的行，监测图同理）；两列最小 260px，窄屏该行横向滚动。保留取数、校准、图例、图片和缩放；切换主图、关闭及布局变化时重画，重建后被选主图不存在则关闭周波图并取消旧请求。
- **用户执行命令 / 输出 / 判读**：无需命令；请在目标浏览器打开「数据处理 → 波形预览」，分别右键离线电压 / 电流和监测主图选择两种周波图，检查所选主图与周波图同一行；收窄窗口或选择两列模块布局时横向滚动，关闭周波图检查主图恢复宽度。现场尚无用户回报。
- **沙盒结果**：`tools/ui_r213_check.cjs` 对临时服务与合成 CSV 的 jsdom 回归 28/28，包含切换选中图、图表重建、关闭、两列及监测模块隔离；旧 `ui_r210_check.cjs` 75/75。新增静态布局断言及相关定向 pytest 61 passed / 1 warning；全量 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs` **761 passed / 1 skipped / 1 warning**（高次谐波 skip，Starlette/httpx 弃用 warning）。四份生成手册 `--check` OK。`find tmp -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum` 为 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5`，与此前一致。
- **局限**：jsdom 不计算真实布局，CSS 横向滚动仅静态断言；未在真实浏览器、Windows、现场文件下视觉验收。监测原始 CSV 对应关系仍需用户确认；此前 T-027 的一次 r63 保存失败原因仍未定位。
- **是否进入 REPORT.md**：否，界面布局非稳定算法结论。


## [2026-11-10] 专题 T-029：波形预览同排主曲线与周波曲线对齐（第 215 轮 / v0.99.55）

- **类型 / 模式 / 角色**：用户专题（实现＋验证）；模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`，代码 `632497e`，文档 `a8b58aa`。
- **目标**：同排主图与周波瞬时 / 有效值图对齐、去掉周波图说明、标题字体一致、处理显示与缩放移动控件。
- **用户确认的交互**：选择「仅合并显示区域」——两张图对齐、减少重复说明，显示图例、缩放和移动仍分别操作，**不联动**，不把各自不同的数据时段或量纲混为同一坐标。
- **实现 / 方法**：同排标题用相同类和等高标题行，长标题省略并可通过主图标题提示查看全文；周波画布跟随选中主图高度（离线双图 210、单图 / 监测 280），加载和错误状态也保持等高；去掉常规文件 / 时段 / 点数说明与周波图重复操作提示，失败原因显示于图下，服务端返回的 notes 用通知显示。保留两套独立图例和缩放移动控件、关闭、取数和校准逻辑，监测源对应关系的确认说明仍在配置里。窄屏沿用上一轮同排滚动；不改「波形分析」。
- **用户执行命令 / 输出 / 判读**：无需命令；请在目标浏览器的「数据处理 → 波形预览」中，分别对离线电压、电流和监测曲线右键打开两种周波图，查看标题和画布上下边界对齐、正常情况下没有周波说明；分别操作两图的图例、缩放与移动确认互不影响，再缩窄窗口检查滚动。错误文件应在画布下显示原因。现场尚无用户回报。
- **沙盒结果**：`tools/ui_r213_check.cjs` 对隔离服务及合成 CSV 的 jsdom 回归 **37/37**，包括 210 / 280 高度、单 / 双图切换、监测、标题类、正常 / 加载 / 错误状态、各自图例 / 缩放 / 移动及异步关闭；旧 `ui_r210_check.cjs` **75/75**。针对 r215/r214/r213/r210/UI 的 pytest **63 passed / 1 warning**；隔离副本全量 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs` 为 **763 passed / 1 skipped / 1 warning**（60Hz 高次谐波 skip；Starlette/httpx 弃用 warning）。四份生成手册 `--check` OK。`find tmp -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum` 为 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5`，与此前一致。
- **局限**：jsdom 不计算真实排版，标题 / 高度对齐及窄屏仅作 DOM、CSS 和画布逻辑检查，未在真实浏览器 / Windows / 现场文件视觉验收。此前 T-027 的一次 r63 保存失败原因仍未定位。
- **是否进入 REPORT.md**：否，界面布局而非稳定算法结论。


## [2026-11-10] 专题 T-030：波形预览同排布局无头 Chromium 补验（第 216 轮）

- **类型 / 模式 / 角色**：验证专题，模式 A，资深电力算法专家；当前分支 `arena/51b63974-nilm-calc-tool`。用户要求继续，对 T-029 的浏览器缺口补验；检查脚本 `52ffdd9`、文档 `2086128`。本轮不改应用代码。
- **方法 / 数据**：隔离副本 `/tmp/b5/repo` 用 `ELEC_TOOL_AUTOLOAD_LAST=0` 起测试服务；检查脚本创建 6 秒 6400Hz 三相正弦波和合成监测文件，自动删临时输入。以 Playwright Core 1.65.0 驱动 `@sparticuz/chromium` 153.0.0 附带的无头 Chromium 153.0.8010.0，测量 `getBoundingClientRect()` 和计算样式，测试图例 / 缩放 / 移动及 API 请求。依赖安装于 `/tmp/probe/t10`，浏览器启动所缺的 NSS 库取自该包自带的 `al2023.tar.br`，不安装到项目；服务已停止。
- **用户执行命令 / 输出 / 判读**：现场无需命令；可在用户目标浏览器打开「数据处理 → 波形预览」，用自己的 CSV 分别核对电压、电流和监测图右键周波图，检查中文字体、标题与曲线对齐、窄屏滚动及两图独立操作。用户现场输出尚未回报。沙盒执行命令为 `NODE_PATH=/tmp/probe/t10/node_modules LD_LIBRARY_PATH=/tmp/probe/t10/aws/lib node tools/ui_r216_browser_check.cjs http://127.0.0.1:8767`，临时实录 `/tmp/probe/t10/result.log`，输出 **PASS 25**；`/tmp` 不是持久成果，脚本已入库。
- **结果**：1440px 双主图电压瞬时 / 电流 RMS 画布均为 210px、标题与画布上下坐标一致；单图及监测画布 280px；500px 视口两图仍同行、行内容宽 536px / 可见宽 247px 且可设置横向滚动；1600px 两模块双列下仍对齐。每对标题计算出的字号、字重、字体族、颜色、行高一致；显示图例、缩放与移动互不影响；无脚本错误和修改类 API 请求。四份生成手册 `--check` OK，`tmp/` SHA256 汇总仍 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5`。此前第 215 轮全量 763 passed / 1 skipped / 1 warning，本轮未重跑全量（只加测试脚本和文档）。
- **局限**：这是自动化无头 Chromium 的几何 / 样式及事件检查，不是人工截图审阅；沙盒中文字体和系统回退未验证，且无头启动参数隐藏滚动条（只验证程序化横向滚动），未覆盖真实 Windows / 目标浏览器、触控或现场文件。T-027 的一次 r63 保存失败原因未定位。
- **是否进入 REPORT.md**：否，界面验证并非算法结论。


## [2026-11-10] 专题 T-031：波形预览去掉曲线移动说明（第 217 轮 / v0.99.56）

- **类型 / 模式 / 角色**：用户专题（实现＋验证），模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`，代码 `edf98b7`、文档 `68d1815`。
- **目标与实现**：用户要求去掉波形预览模块曲线里的移动说明。对波形预览内的主图 / 周波图，放大后的动态文字去掉「拖动图面 / 方向键 / ◀▶▲▼ 移动坐标轴」；继续显示缩放和复位提示，周波图的整段提示仍沿用此前隐藏设置。移动文字标签、按钮、按钮悬停提示以及拖动 / 方向键 / 滚轮功能保留；其他页面的曲线提示维持原样，不改「波形分析」。
- **用户执行命令 / 输出 / 判读**：无需命令；请在目标浏览器打开「数据处理 → 波形预览」，加载曲线并放大，确认不出现移动操作说明，按移动按钮或拖动画面仍可平移；在其他页面核对原说明仍在。用户现场输出尚未回报。
- **沙盒结果**：`ui_r213_check.cjs` 用隔离服务和合成文件验证离线主图、周波图、监测主图及模块外曲线提示，**41/41**；通用旧图回归 `ui_r17_check.cjs` **54/54**。`ui_r216_browser_check.cjs` 在隔离服务以无头 Chromium 153 和合成数据检查主图提示、主图 / 周波图按钮平移及不联动，**28/28**；目标浏览器及中文字体视觉仍待验。相关定向 pytest **63 passed / 1 warning**；隔离副本全量 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs` **763 passed / 1 skipped / 1 warning**（60Hz 高次谐波 skip，Starlette/httpx 弃用 warning）。四份生成手册 `--check` OK；`tmp/` SHA256 汇总 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5` 不变。
- **局限**：无头 Chromium 只自动检查计算样式和交互，未在用户目标浏览器 / Windows / 现场文件验收。T-027 中的一次 r63 保存失败原因仍未定位。
- **是否进入 REPORT.md**：否，界面提示非稳定算法结论。


## [2026-11-10] 专题 T-032：复查波形预览移动说明并保留悬停提示（第 218 轮 / v0.99.57）

- **类型 / 模式 / 角色**：用户专题（实现＋验证），模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`，代码 `fc161b4`、文档 `b07d5e3`。
- **目标与纠正**：用户要求重新检查波形预览各曲线是否有移动说明，有则删除；随后明确「鼠标悬停说明保留」。复查发现上轮虽然去掉了放大后的长段移动说明，仍有工具栏「移动：」标签；初步曾拟移除悬停说明，但在用户补充后撤回，最终保留原有按钮 `title` 提示。
- **实现**：仅对波形预览模块内的离线、监测主图与周波瞬时 / 有效值曲线，不显示常显「移动：」标签，原长段移动说明继续不显示；保留方向按钮、原鼠标悬停说明和图面悬停取值，另为按钮提供简短无障碍方向名称。缩放 / 移动等功能及其他页面不变，不改「波形分析」。
- **用户执行命令 / 输出 / 判读**：无需命令；请在目标浏览器加载预览模块，分别检查各主图及两种周波图在放大前后不常显移动说明，将鼠标停在方向按钮验证原说明仍显示，将鼠标停在曲线上验证数值提示；按钮仍可平移。用户现场输出尚未回报。
- **沙盒结果**：`ui_r213_check.cjs` 真实只读接口 + jsdom **46/46**（含各曲线常显文字、按钮 title、悬停取值、模块外原提示），旧 `ui_r17_check.cjs` **54/54**；隔离服务上的无头 Chromium 153 自动检查 **37/37**，含两图方向按钮悬停说明、悬停取值和移动操作；相关定向 pytest **63 passed / 1 warning**（用户补充前、应用变化仅按钮 title），补充后隔离副本全量 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs` **763 passed / 1 skipped / 1 warning**（60Hz 高次谐波 skip，Starlette/httpx 弃用 warning）。四份生成手册 `--check` OK，`tmp/` SHA256 汇总 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5` 不变。
- **局限**：无头 Chromium 检查 title 属性与悬停事件，未人工验收操作系统弹出的悬停样式或中文字体；目标浏览器、Windows 和现场文件待验。T-027 的一次 r63 保存失败原因仍未定位。
- **是否进入 REPORT.md**：否，界面提示非稳定算法结论。


## [2026-11-10] 专题 T-033：恢复波形预览移动说明并去掉拖选与缩放说明（第 219 轮 / v0.99.58）

- **类型 / 模式 / 角色**：用户专题（实现＋验证），模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`，代码 `6bbc33f`、文档 `83c94e7`。
- **目标与实现**：用户变更先前要求，恢复波形预览模块各曲线原来的移动说明，去掉曲线右下角的拖选区间及缩放说明。预览主图和周波图均恢复「移动：」标签；放大后恢复「拖动图面 / 方向键 / ◀▶▲▼ 移动坐标轴」，不再显示「拖选区间」「已缩放」及轴带拖选 / 双击复位说明；未放大时说明为空。保留方向按钮及鼠标悬停说明、曲线悬停取值、缩放、拖选和移动功能，其他页面的说明原样保留；不改「波形分析」。周波图原本整体隐藏说明，现仅对非空移动说明显示。与新要求冲突的 r215 测试断言同步更新为空说明不占空间。
- **用户执行命令 / 输出 / 判读**：无需命令；请在目标浏览器打开「数据处理 → 波形预览」，对离线、监测主图及两种周波曲线观察工具栏「移动」标签，放大后检查移动操作说明出现，拖选和缩放说明不出现；悬停按钮 / 曲线及尝试缩放、拖选、移动应仍正常。用户现场输出尚未回报。
- **沙盒结果**：隔离服务及合成文件下 `ui_r213_check.cjs` **46/46**（包括离线 / 监测和两种周波曲线、缩放前后移动说明、悬停及模块外原提示），通用曲线 `ui_r17_check.cjs` **54/54**；无头 Chromium 153 自动检查 **37/37**（同排及窄屏、移动说明、悬停和移动按钮），定向 pytest **63 passed / 1 warning**。隔离副本全量 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs` **763 passed / 1 skipped / 1 warning**（60Hz 高次谐波 skip，Starlette/httpx 弃用 warning）。四份生成手册 `--check` OK，`tmp/` SHA256 汇总 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5` 不变。
- **局限**：无头浏览器未人工验收中文字体 / 提示样式；用户目标浏览器、Windows 和现场文件待验。T-027 的一次 r63 保存失败原因仍未定位。
- **是否进入 REPORT.md**：否，界面提示非稳定算法结论。


## [2026-11-10] 专题 T-034：波形预览曲线去除操作文字标签（第 220 轮 / v0.99.59）

- **类型 / 模式 / 角色**：用户专题（实现＋验证），模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`，代码 `7db4517`、文档 `ffb6785`。
- **目标与实现**：用户要求去掉波形预览各曲线内「显示」「缩放」「移动」标签，鼠标缩放后去掉右下角拖选区间和缩放说明。仅在波形预览模块的图例和操作条省略三个标签，保留曲线复选框、缩放 / 复位 / 移动按钮、操作和原悬停提示；之前根据用户要求保留的放大后移动说明仍在，鼠标框选 / 滚轮缩放后说明不含拖选或缩放内容。其他页面原标签和提示不变，不改「波形分析」。
- **用户执行命令 / 输出 / 判读**：无需命令；请在目标浏览器打开「数据处理 → 波形预览」，检查离线、监测主图及两种周波曲线无三个文字标签，但图例与操作按钮仍可用；以滚轮和鼠标框选缩放，右下角无拖选及缩放说明，移动说明和按钮悬停提示保留。用户现场输出尚未回报。
- **沙盒结果**：隔离服务及合成文件 `ui_r213_check.cjs` **47/47**（含离线 / 监测 / 周波图、图例重绘、鼠标滚轮及其他页面原标签），通用曲线 `ui_r17_check.cjs` **54/54**；无头 Chromium 153 自动检查 **41/41**（含主图滚轮与框选、周波图滚轮、缩放 / 移动按钮、悬停、同排及窄屏），定向 pytest **63 passed / 1 warning**。隔离副本全量 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs` **763 passed / 1 skipped / 1 warning**（60Hz 高次谐波 skip，Starlette/httpx 弃用 warning）。四份生成手册 `--check` OK，`tmp/` SHA256 汇总 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5` 不变。
- **局限**：无头浏览器未人工验收中文字体 / 悬停样式；用户目标浏览器、Windows 和现场文件待验。T-027 的一次 r63 保存失败原因仍未定位。
- **是否进入 REPORT.md**：否，界面提示非稳定算法结论。


## [2026-11-10] 专题 T-035：波形预览去掉缩放后的移动说明（第 221 轮 / v0.99.60）

- **类型 / 模式 / 角色**：用户专题（实现＋验证），模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`，代码 `16f0cf7`、文档 `88d6af6`。
- **目标与实现**：用户要求检查并删除波形预览曲线鼠标缩放后右下角「拖动图面 / 方向键 / 移动坐标轴」说明。确认上一轮确实保留了该段，按本轮新要求仅在波形预览主图及周波图将操作说明置空并隐藏空提示；拖选 / 缩放说明此前已去掉，三个文字标签继续不显示。曲线勾选、缩放 / 移动按钮和功能、按钮鼠标悬停提示及曲线悬停取值均保留；其他页面原说明不变，不改「波形分析」。
- **用户执行命令 / 输出 / 判读**：无需命令；请在目标浏览器打开「数据处理 → 波形预览」，加载离线 / 监测及周波曲线，鼠标滚轮或框选放大后检查右下角无移动 / 拖选 / 缩放说明；方向按钮悬停仍有提示、移动仍可用。用户现场输出尚未回报。
- **沙盒结果**：隔离服务和合成文件 `ui_r213_check.cjs` **47/47**（含放大前后 / 周波图 / 监测 / 其他页面），通用曲线 `ui_r17_check.cjs` **54/54**；无头 Chromium 153 **43/43**（主图滚轮 / 框选、瞬时及有效值周波图滚轮、监测图滚轮、按钮悬停及移动、窄屏），定向 pytest **63 passed / 1 warning**。隔离副本全量 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -o addopts='' tests -q -p no:cacheprovider -rxXs` **763 passed / 1 skipped / 1 warning**（60Hz 高次谐波 skip，Starlette/httpx 弃用 warning）。四份生成手册 `--check` OK，`tmp/` SHA256 汇总 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5` 不变。
- **局限**：无头浏览器未人工验收中文字体 / 悬停样式；用户目标浏览器、Windows 和现场文件待验。T-027 的一次 r63 保存失败原因仍未定位。
- **是否进入 REPORT.md**：否，界面提示非稳定算法结论。


## [2026-11-10] 专题 T-036：波形预览离线文件列映射（第 222 轮 / v0.99.61）

- **类型 / 模式 / 角色**：用户专题（实现＋验证），模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`，代码 `47ee97e`、文档 `c07491d`。
- **目标与实现**：波形预览每个离线模块「更多选项」独立启用列映射，时间及六通道的列号从 1 起、空为不映射；默认关闭保留旧表头识别 / 默认列序，至少映射一个电压或电流通道。重复、非法数值及超过 CSV 首行宽度报错；严格列数检查由新参数 `strict_col_map` 仅在预览模块启用时请求，其他调用默认不变。文件信息、主 RMS 和右键两种周波图一致，周波图使用主图成功加载时的快照；异步文件信息遇配置变更作废。配置本地保存并复制，不更改运行配置；监测模块和「波形分析」前端未改。
- **用户执行命令 / 输出 / 判读**：无需命令；在「数据处理 → 波形预览」的离线模块中展开「更多选项」并勾选列映射，按实际 CSV 填列号（从 1 起），点「文件信息」「加载曲线」及右键周波图检查通道、数值、时间；修改映射要重新加载主图。用户现场输出尚未回报。
- **沙盒结果**：真实服务及重排列合成 CSV 配合 `tools/ui_r222_colmap_check.cjs` **19/19**，覆盖时间列重排、映射数值、详情快照、部分映射、重复 / 非法 / 越界、异步失效、复制、模块隔离与刷新恢复；既有 `ui_r213_check.cjs` **47/47**，`ui_r210_check.cjs` **75/75**；无头 Chromium 153 的临时脚本检查开关、7 个输入、1440px / 500px 适配及刷新恢复通过（脚本位于临时目录，不入库）。隔离副本全量 pytest **769 passed / 1 skipped / 1 warning**（60Hz 高次谐波 skip、Starlette/httpx 弃用 warning）。四份生成手册 `--check` OK；`tmp/` SHA256 汇总 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5` 未变。
- **过程**：第一次隔离全量 768 passed / 1 failed / 1 skipped，失败是 `test_web_ui.py` 旧静态断言未将新增独立处理的开关计入例外；更新该断言并增加动态列映射处理检查后，全量重跑通过。
- **局限**：严格列数基于首行，不能保证后续所有 CSV 行等宽；未验证目标浏览器、Windows 和用户实际波形文件，仍需现场核对列与量纲；实时监测模块所选原始文件未提供列映射。T-027 的一次 r63 保存失败原因仍未定位。
- **是否进入 REPORT.md**：否，界面功能非稳定算法结论。


## [2026-11-10] 专题 T-037：波形预览电压、电流周波曲线独立显示（第 223 轮 / v0.99.62）

- **类型 / 模式 / 角色**：用户专题（检查、修正、验证），模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`，主体代码 `1d2a195`、文档 `230d75f`，监测兼容收尾 `ddfa381`。
- **检查与实现**：原模块只有一个 `.wb-detail`、画布、`rt.detail` 及请求令牌，电压图右键后再点电流会搬移面板并替换数据。现按电压 / 电流 / 监测主图键分别持有周波面板、画布、数据和请求令牌，离线电压与电流可同时显示不同时间与类型，关闭 / 缩放 / 移动 / 图例互不影响；同一主图的瞬时和有效值仍在其自己的周波面板中切换。改变显示方式隐藏主图时只关闭其周波图；重新加载主曲线时清除旧周波图。离线模块共用周波数设置只影响下一次右键，不清除已显示周波图；监测模块修改周波数仍关闭现有周波图。继承旧图例配置，列映射取主图加载快照；保持串行请求、同排布局、悬停说明及其余界面。
- **用户执行命令 / 输出 / 判读**：无需命令；在「数据处理 → 波形预览」离线模块加载 CSV，在电压图右键打开周波图，再在电流图右键打开另一周波图；应两图各自位于主图右侧并可同时显示。缩放、切换图例或关闭其中一个，不应改变另一个。用户现场输出尚未回报。
- **沙盒结果**：真实服务及合成 CSV 的 `ui_r223_independent_detail_check.cjs` **15/15**，覆盖同时显示、不同类型及时间、各自数值、图例 / 缩放、单侧关闭、改变显示模式、读取错误与延迟请求隔离、重新加载清除；`ui_r213_check.cjs` **47/47**、列映射 `ui_r222_colmap_check.cjs` **19/19**、旧模块 `ui_r210_check.cjs` **75/75**；无头 Chromium 153 `ui_r216_browser_check.cjs` **49/49**，包括两张周波图同时显示、关闭及独立缩放、同排、窄屏和监测回归（运行于监测兼容收尾小调整前）。主体修改后隔离全量 pytest **769 passed / 1 skipped / 1 warning**（60Hz 高次谐波 skip，Starlette/httpx 弃用 warning）；监测兼容收尾后定向 pytest **41 passed / 1 warning**、jsdom 独立性 15/15 和周波回归 47/47，未再次跑全量及 Chromium。四份生成手册 `--check` OK；`tmp/` SHA256 汇总 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5` 不变。
- **过程**：定向 pytest 第一次因原先静态断言固定了单个周波面板的代码结构而 1 failed / 40 passed，更新断言以检查多面板结构后全量通过。
- **局限**：目标浏览器、Windows、中文字体和用户实际波形文件待验；不同主图的请求仍排队，文件大时不保证同时完成。T-027 的一次 r63 保存失败原因仍未定位。
- **是否进入 REPORT.md**：否，界面交互非稳定算法结论。


## [2026-11-10] 专题 T-038：设备画像后窗与启停时长分析（第 224 轮）

- **类型 / 模式 / 角色**：用户咨询，模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`；仅分析、无程序改动。
- **代码结论**：`build_profile` 只接收一个 `post_cycles`，两方向共用（`elec_tool/nilm_profile.py:1228,1250,1260-1274`）；`_locate_near`、`auto_locate_events` 均先在 `[onset,onset+post)` 取中位数作为目标，再调用 `transition_end` 搜索首个进入目标 ±20% 并保持的点；后者最大 `end=onset+post−1`，平滑窗为 `max(1,min(25,post//20))`，保持 `max(3,min(250,post//10))`。`event_features` 的前后稳态分别取 `[onset-pre,onset)` 和 `[end,end+post)` 中位数，`dur_cycles=end−onset`；`fit_group` 分别给 startup / shutdown 存持续统计与逐事件值。标签只提供时间、方向，起点在容差内重定位，并不指定终点。UI 与 CLI 的后窗提示只提启动，未覆盖停止较慢的情形。
- **沙盒合成探针（非完整文件提取）**：`_locate_near` 直接对 2400 点无噪声逐周波合成量运行：启动 300→400 点线性从 0 升到 10（100 周波），1300→1320 点从 10 降到 0（20 周波），`pre=10`、标签容差 ±10 周波。post=50/120/200/400 时，启动计算持续分别为 20/46/74/69 周波，停止为 14/12/10/5；post=50/120/200/400 时启动搜索目标中位数分别为 2.75/6.25/10/10。由此证明同一个后窗可以得出不同方向的值，但后窗长度、半窗目标和前向平滑可让结果显著小于完整爬升 / 下降时间，未触及 post−1 也不能证明未低估。本探针不验证真实文件、自动定位或完整画像，物理结束定义另需约定。
- **建议**：独立波形和启停真值测量两方向起止、确认单位及工频，依据较长过程选择有余量的共同 post 并留出下一次动作前的干净后稳态；使用标签且核对逐次起终点、后稳态、中位数、峰值和 notes；对多个 post 做敏感性对照、分方向多次采样并在留出样本上核对误差与漏检。若需要严格的时长精度，应将终点定义、稳定带和保持时长、独立人工起止真值及方向独立配置纳入设计，并同步考虑在线匹配使用的画像窗口、版本与兼容；仅修改后窗不能保证。
- **局限**：没有现场原始录波 / 同步传感器真值，不声称任何现场误差或修复；电气信号的稳定时间未必等于机械转速或工艺过程结束。
- **是否进入 REPORT.md**：否，代码分析及合成探针非稳定现场算法结论。

## [2026-11-10] 专题 T-039：单相电流画像的检测口径（第 225 轮）

- **类型 / 模式 / 角色**：用户咨询，模式 A、资深电力算法专家；只读代码分析及隔离测试，未修改算法；补充已有单相配置专题 T-025。
- **结论**：`quantity=i` 且 `phases=A` 的画像，在检测有效量为 I 时，对总线 A 相周波 RMS 电流使用多尺度双滑窗找候选；两相采用所声明相的 RMS 合成，`ABC` 或缺失 `phases` 的旧画像使用三相 RMS 合成。P 画像则使用指定相有功。`auto` 一旦有电压即选 P；画像量和检测有效量不同则不运行匹配。Q 条件满足时还可独立产生候选或参与切窗。
- **匹配并非只看单相电流**：跳过非画像相的分相 ΔI 特征，但 `event_features` 仍提取总 ΔP、ΔQ、平均谐波、三相合成电流的峰值比、轨迹与方向检查；匹配所用维度与画像版本有关。单相输出电流幅值用画像所声明行的前后 RMS 差，而非 event_features 的三相合成 ΔI。同步动作及前后窗可能污染匹配。
- **合成函数探针**：`runpy.run_path('tests/test_r184_single_phase_profile.py')` 获得 `_single_phase_doc('A')` 与 PRM，改画像量 I、ΔP 均值为 0，长度 1200 的 `p/q/i` 周波数组，基线各相 5 A、目标 500 处阶跃；①仅 B 相 +3 A、Q 全 0 时 `phase_map` 数值 1、3、0 及字符串 '0' 均无候选：候选按画像相别选行、相序变换发生于匹配之后，故不能依赖映射补救未进入候选的其他相；②A +3 A、B 50→30 A、C 50 A 时检出 A 候选但三相合成 ΔI=-12.031 A，`sign_flip` 否决；③A +3 A、总 ΔP=690 W、画像 ΔP=0 时 `d_p` 贡献 48.576、`d2_per_dim=8.358` 且结果 rejected（置信度门限）；量的选择为 I 不会自动跳过 P/Q。合成探针不代表现场准确率。
- **相序 0 问题**：`phase_map_code(0)` 返回 1，而 `phase_map_code('0')` 返回 0；数值型 0 被 `v or 1` 吞掉，`match_event` 虽实现 0 自动试映射，但经 `detect_profile` 的数值 0 调用不会进入该分支。旧测试直接检查 `match_event` 的自动映射及平衡场景，不能证明此入口的数值 0 正常。具体 UI/序列化值类型应依现场配置核实。
- **沙盒验证**：将 git 已跟踪文件复制到 `/tmp/r225`，运行 `/home/user/nilm_calc_tool/.venv/bin/python -m pytest -o addopts='' tests/test_r184_single_phase_profile.py tests/test_r90_nilm_profile.py -q -p no:cacheprovider`，52 passed / 1 Starlette/httpx 弃用 warning。测试未覆盖上述所有反例；无现场原始数据。
- **建议 / 局限**：核对画像 `quantity`、`phases`、`phase_source` 和分相统计，检测侧量、真实设备所接相、采集映射及 PT/CT；旧画像需要核验或重提。若要纯单相需使两侧可用通道和特征口径一致并先离线验证（参见 T-025），不能在真实数据重要通道上随意屏蔽。未修复相序候选、数字 0、跨相 sign_flip 或 P/Q 口径问题；更改需用户确认及回归测试。
- **用户执行命令 / 输出 / 判读**：无需命令；提供画像 JSON、检测配置、接线及同步录波才能核实具体现场；尚无现场输出。
- **是否进入 REPORT.md**：否，仅代码分析、单元测试及合成探针，非现场稳定结论。

## [2026-11-10] 专题 T-040：设备画像匹配增加单相检测的可行性（第 226 轮）

- **类型 / 模式 / 角色**：用户咨询；模式 A、资深电力算法专家；代码分析，不修改算法。基于 T-025、T-039 与当前代码；无新增实验和现场数据。
- **现状**：`CycleFeatures` 已同时输出 total/A/B/C 的 P、Q、I RMS、谐波；`detect_profile` 的候选已对单相画像使用本相 P/I/Q，但 `event_features` 对 P/Q、谐波、峰值和模板仍用 total，符号检查 I 用 total，`NilmEvent.channel` 固定 total。普通六种标量算法循环 `channels_effective`，画像算法在循环之外单独执行，配置 `nilm.channels` 不足以切换画像算法检测相。`build_profile` 先用 total 序列定位和计算特征，之后才判定/保存 phases，因此仅声明相别不保证提取全过程单相。
- **可行设计（提议，非已实现）**：为画像声明版本化特征口径（原有、单相纯电流、可选单相电压电流），保留设备侧特征相别，单独确定总线实际相与相序；提取和在线共用同一套单相特征定义、门槛及窗口几何：目标相候选/变点/终点、ΔI、峰值、归一轨迹、方向/符号与输出；纯电流模式排除 P/Q 维并禁用 Q 变点/候选，谐波可用目标相电流，但需重新标定 σ 下限；电压电流模式则用目标相 P/Q 与匹配的目标相电压，I 模式不应误以为天然忽略 P/Q。需审计档位比例、单维否决、后窗、全量诊断与状态账本。
- **相别和旧画像**：相序转换必须在候选选相之前，且贯穿特征和输出；数值型 phase_map=0 的默认转换问题需修复。优先显式设备侧相→总线侧相；如自动扫描 A/B/C，需设计多重候选、去重、冲突决策和状态隔离，禁止每个事件随意更换相；不能假称自动相可唯一识别。旧画像无新标记时原路径原数值原输出、7/8 维兼容；旧三相汇总特征 / 模板一般无法凭统计量还原目标相，新口径建议由原始录波重提，不强制迁移或静默改义。每画像仍有独立状态；多相扫描的状态键与竞争策略需明确。`nilm.quantity` 当前按整个检测器生效，并非逐画像选择，若想同一侧混用 P/I 画像需额外设计。
- **输出和外部接口**：新模式输出真实总线 channel A/B/C（或维持字段兼容并新增明确的检测相字段，待确认）；核对 API 按 channel 筛选、前端曲线打点、CSV、状态诊断、重启恢复、历史数据兼容。单相电流不应标为 total。校验缺相 / 三相三线是否有测量或合适重构及变比极性，不能把缺通道零值当有效测量；不修改全局数据源映射以避免影响其他算法和实时功能。
- **建议验证**：A/B/C 画像与实际接相映射；其他相同窗正/反动作不影响目标相；同相并发干扰、相角导致总线上 ΔRMS 非线性以及模板污染；单相纯电流但在线有电压、无功干扰、谐波口径；错误接线或缺相报清楚；旧 7/8 维、三相/两相、档位、多画像、状态去重、输出筛选与图表兼容；标签/自动提取与在线回放端到端；现场按设备真值统计召回/误报及方向、时间误差。I RMS 的设备与背景不可直接相加，单相不保证识别准确。
- **依据 / 用户执行命令**：本轮无新增运行；上一轮隔离测试 52 passed / 1 warning，T-025 的真实提取/回放入口与合成实验、T-039 的函数探针均非现场验证。用户无需执行命令；需要画像 JSON、设备侧及总线侧同步标注录波、接线及采样变比才能做现场验收。
- **未决**：单相纯电流还是同时支持电压电流；每画像指定检测相还是允许自动；旧画像默认兼容策略及新模式是否强制重提；输出 channel 约定。用户尚未要求实现。
- **是否进入 REPORT.md**：否，仅可行性分析与方案，未改程序、未形成现场稳定结论。

## [2026-11-10] 专题 T-041：逐画像指定两侧相的单相画像匹配（第 227 轮 / v0.99.63）

- **类型 / 模式 / 角色**：用户开发专题，模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`。用户要求两种模式并由用户为每个画像指定总线和分路相。
- **实现**：提取页新增特征口径 legacy/current/voltage_current 和必选分路、总线相；API、CLI 同步，画像写 `single_phase={version:1, mode, branch_phase, bus_phase}` 并严格校验。新画像须重提，旧画像没有字段则原行为。每个检测器按 `output.source_id` 选择其侧相，将所选相投影至设备特征坐标；提取、候选/无功变点、窗口、轨迹、P/Q/I/谐波、符号检查与观测幅值均一致按目标相，纯电流 P/Q 不参与也不产生 Q 候选（事件功率字段是 0 占位），匹配方差收缩对新模式只使用有效维，档位自由和 `stage_window` 同步跳过无效维。新画像按自身模式运行，不受全局检测量与检测对象限制，事件 channel 为实际检测相；不同画像可混用 A/W，事件表逐行标单位。其他算法与数据源三相不变。
- **有效性约束**：分路/总线目标相无电流时不运行，电压＋电流还要求该相电压存在；未重构两表法 B 相不可用，未重构三相三线或线电压不能用于单相 P/Q；重构电压的前提需现场确认。用户明确相别不走旧 `phase_map`。检测累计曾出现非零通道不等于能检测持续性掉线，也不替代现场接线核查。候选特征 `d_ia/ib/ic` 按画像分路坐标显示，而事件 channel 为本侧实际相。
- **验证**：隔离副本 `/tmp/r226` 分组完整回归：画像相关及 UI 等 8 文件 `190 passed / 1 warning`，其余文件 `596 passed / 1 skipped / 1 warning`，合计 **786 passed / 1 skipped**；最后只修改 HTML 公共检测量解释后，相关 `test_web_ui` + 新测试 **51 passed / 1 warning**。新增 17 个测试覆盖 A/B/C 两侧九种映射×两模式、纯电流排除 P/Q 与无功干扰、跨相符号干扰、分路和总线、混合多画像及 channel 筛选、缺相/线电压、全局 P 且无电压的纯电流、活动维收缩与档位、API / CLI。Starlette/httpx 弃用 warning；skip 为已有 60Hz 高次谐波限制。`node --check` 通过；隔离服务 + 合成 CSV 的 jsdom 测试两模式通过、相别载荷/结果正确、无 JS 错误，另 3 项 jsdom 检查涵盖混合 A/W 表格（jsdom 的 scrollTo 提示无害）；未做目标浏览器视觉 / Windows / 现场波形验收。4 份生成手册 `--check` OK，`git diff --check` OK，`tmp/` 汇总 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5` 未变。
- **过程与兼容**：起初尝试修旧 `phase_map=0` 数值型自动映射后，既有 `test_detector_auto_phase_map_still_detects` 因重排可能改变状态而失败（58 passed / 1 failed）；鉴于本任务需保持旧行为且新单相模式使用显式相别，撤回该旧模式改动，后续测试通过。历史补-D1 数值 0 问题仍未修；补-D3 自动定位与现场问题仍待。旧画像相别标记不等于本次新特征口径，不能静默转换。
- **用户执行命令 / 输出 / 判读**：无需命令。在提取页选新口径，明确分路与总线相、配置数据和标签并提取，分别填入两侧画像路径；观察事件对象、单位及候选贡献；以带真值的设备侧/总线侧留出录波评估方向、时刻、召回及误报，用户现场输出尚未回报。
- **局限**：同相其他设备、RMS 与背景相角、前后窗、阈值及经验性的谐波 2 A σ 下限仍可能造成漏报或误报；合成和自动化结果不构成现场准确率或上线结论。未修改波形分析子界面及 `tmp/`。
- **是否进入 REPORT.md**：否，尚无现场稳定结论。

## [2026-11-10] 专题 T-042：画像提取相别控件按口径联动（第 228 轮 / v0.99.64）

- **类型 / 模式 / 角色**：用户界面修改，模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`。
- **实现**：默认原有口径时分路和总线相 select 均 disabled 并应用现有 `label.off` 置灰，设备相别可用；切换纯电流或电压＋电流时两侧相启用，设备相别 disabled 并置灰。控件初始化及 change 均同步；切换保留各自已经选择的值，保持原有 payload 和后端算法，未修改「波形分析」及 `tmp/`。
- **验证**：`tests/test_web_ui.py` 新增静态结构和联动绑定检查；隔离副本 full pytest **787 passed / 1 skipped / 1 Starlette/httpx 弃用 warning**，运行时仍是文档更新前的旧版手册，随后同步手册后相关 `test_nilm_replay_check.py` / `test_server.py` **46 passed / 1 warning**；jsdom 真实隔离服务 `tools/ui_r228_profile_phase_gate_check.cjs` **14/14**，涵盖默认、两模式切换、置灰、载荷、值保留、重新进入及无配置修改，jsdom 输出无害的 `Window.scrollTo` 未实现提示；隔离服务无头 Chromium 检查 disabled、计算样式 opacity、两种模式和切回后的值通过。`node --check`、4 份生成手册 `--check`、`git diff --check` 均通过；`tmp/` SHA256 汇总仍为 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5`。
- **用户执行命令 / 输出 / 判读**：无需命令；打开「数据处理 → 设备画像提取」切换「画像特征口径」，原有口径只有设备相别可选，单相口径只有两侧检测相可选。用户目标浏览器的现场结果尚未回报。
- **局限**：无头浏览器不代替用户实际浏览器 / Windows 验收；上一轮单相画像现场接线、误报和漏报仍待验证。
- **是否进入 REPORT.md**：否，仅界面联动，无算法变更。

## [2026-11-10] 专题 T-043：负荷辨识事件曲线精简操作说明（第 229 轮）

- **类型 / 模式 / 角色**：用户界面修改，模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`。
- **实现 / 决策**：只在 `#view-nilm` 的图表工具条移除缩放前拖选说明、缩放后移动及再次缩放说明和「缩放：」「移动：」标签，并隐藏空提示元素；与波形预览共用精简工具条条件，但不改变图例逻辑，仍保留「显示：」。9 个按钮及 title 保留，方向按钮补充 aria-label；缩放、图面 / 方向键 / 按钮平移、轴带选区及复位逻辑未改。未修改「波形分析」或用户 `tmp/`。
- **沙盒验证**：隔离真实服务 jsdom `tools/ui_r229_nilm_chart_help_check.cjs` **81/81**，覆盖总线和分路各三张画布、空数据 / 合成数据、图例与悬停、滚轮、框选、X 轴带选区、Ctrl 框选、图面与方向键及按钮平移、双击 / 按钮复位及其他界面保留说明；`ui_r213_check.cjs` **47/47**，覆盖波形预览及其他页面回归。无头 Chromium 在隔离服务检查六画布隐藏空元素、标签、图例、按钮 title 与按钮缩放平移复位（合成曲线、为分路测试强制显示隐藏列并暂停页面常规重画）。隔离全量 pytest **788 passed / 1 skipped / 1 Starlette/httpx 弃用 warning**，定向 pytest **38 passed**；`node --check`、`git diff --check` 和四份生成手册 `--check` 通过（生成器报告参数目录无法构建，但四份对比 OK）。jsdom 有无害的 scrollTo 未实现提示。`tmp/` 汇总 SHA256 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5` 未变。
- **过程 / 局限**：旧 `ui_r17_check.cjs` 在隔离副本缺少 `data/sample_6400hz.csv` 时无法装载数据，缩放相关步骤中途停止，并非通过；本轮另以合成曲线测试对应交互。无头测试不代替用户目标浏览器、Windows、真实数据验收；既有现场单相画像验证仍待完成。
- **用户执行命令 / 输出 / 判读**：无需命令；打开负荷辨识事件，查看两侧趋势和周波曲线，确认未缩放及缩放后不再出现指定说明、标签；鼠标悬停按钮仍有提示，缩放与移动仍可用。用户现场结果尚未回报。
- **是否进入 REPORT.md**：否，仅界面显示调整。

## [2026-11-10] 专题 T-044：总览面板曲线精简操作说明（第 230 轮）

- **类型 / 模式 / 角色**：用户界面修改，模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`。
- **实现 / 决策**：`#view-overview` 内总线及分路曲线隐藏缩放前拖选说明、缩放后移动和再次缩放说明、以及「显示：」「缩放：」「移动：」标签；隐藏空提示元素，不留空隙。图例勾选、工具条九个按钮、悬停 title 和方向按钮无障碍名称保留；不改变缩放、平移、图例选择及保存逻辑。仅影响总览面板，负荷辨识的「显示：」和其他页面既有行为不变，不修改「波形分析」或 `tmp/`。
- **沙盒验证**：隔离真实服务 jsdom `tools/ui_r230_overview_chart_help_check.cjs` **123/123**，覆盖总线 / 分路电压、电流、PQS、THD 共 8 个画布的空数据 / 合成数据、标签和提示、图例开关（模拟配置保存响应）、滚轮、框选、X 轴带选择、Ctrl 框选、图面 / 方向键 / 按钮平移、双击与按钮复位；普通页面说明仍在。旧负荷辨识 jsdom **81/81**、波形预览 jsdom **47/47**。无头 Chromium 对隔离服务以合成数据检查 8 画布文字 / 实际空元素隐藏、图例、按钮 title 和缩放平移复位；为分路验证强制显示默认隐藏列、暂停周期重绘。隔离全量 pytest **789 passed / 1 skipped / 1 Starlette/httpx 弃用 warning**，定向 pytest **39 passed**；`node --check`、`git diff --check`、四份生成手册 `--check` 通过（生成器报告参数目录无法构建，但四份对比 OK）。jsdom 输出无害的 scrollTo 未实现提示。`tmp/` 汇总 SHA256 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5` 未变。
- **用户执行命令 / 输出 / 判读**：无需命令；打开总览面板，检查总线和启用的分路各曲线缩放前后没有指定说明和三个标签，图例和按钮可操作，鼠标悬停仍显示提示。用户现场结果尚未回报。
- **局限**：无头浏览器及合成数据不代替目标浏览器、Windows 与真实数据验收；本任务未改变其他页面或算法。
- **是否进入 REPORT.md**：否，仅界面显示调整。

## [2026-11-10] 专题 T-045：实时监测各功能界面精简曲线操作说明（第 231 轮）

- **类型 / 模式 / 角色**：用户界面修改，模式 A、资深电力算法专家；分支 `arena/51b63974-nilm-calc-tool`。
- **实现 / 决策**：为实时监测下的电压、电流、功率、功率因数、基波、谐波、间谐波、直流偏置、频谱 9 个页面根元素标记 `realtime-view`；在这些页面的总线和分路曲线隐藏缩放前拖选说明、缩放后移动 / 再缩放说明与「显示：」「缩放：」「移动：」标签，隐藏空提示元素。保留图例勾选、按钮及 title、方向按钮无障碍名称；缩放、拖选、平移、复位和图例保存逻辑未改。非实时监测页面行为保持不变；不改「波形分析」及 `tmp/`。
- **沙盒验证**：静态测试确保 9 个标记页面与 `ELEC_VIEWS` 一致且其他页面不带该标记；隔离真实服务 jsdom `tools/ui_r231_realtime_chart_help_check.cjs` **751/751**，覆盖两侧 44 张折线画布空 / 单线 / 合成多线、标签、按钮 title、图例勾选（模拟配置保存响应）、数据悬停、滚轮、框选、X 轴带选择、Ctrl 框选、图面 / 方向键 / 按钮平移和双击 / 按钮复位；普通页面说明仍在。负荷辨识 **81/81**、总览 **123/123**、波形预览 **47/47** 回归通过。无头 Chromium 对隔离服务以合成数据检查 44 张画布实际空提示隐藏、标签、图例、按钮 title 和缩放平移复位；为测试分路强制显示默认隐藏列并暂停周期重绘。隔离全量 pytest **790 passed / 1 skipped / 1 Starlette/httpx 弃用 warning**，定向 pytest **40 passed**；`node --check`、`git diff --check`、四份生成手册 `--check` 通过（生成器报告参数目录无法构建，但四份对比 OK）。jsdom 有无害的 scrollTo 未实现提示。`tmp/` 汇总 SHA256 `9e064745b67decb5fa426821ad6d7145cdcae054510340e514850ec57b6213c5` 未变。
- **用户执行命令 / 输出 / 判读**：无需命令；在实时监测各界面查看总线与启用的分路曲线，确认缩放前后没有指定说明和三个标签，图例和缩放平移仍可用、按钮悬停有提示。用户现场结果尚未回报。
- **局限**：无头浏览器及合成数据不代替目标浏览器、Windows 和真实数据验收；本任务未改变其他页面或算法。
- **是否进入 REPORT.md**：否，仅界面显示调整。

## [2026-11-10] 专题 T-046：设备侧启停画像误识别初查（第 232 轮，待数据）

- **类型 / 模式 / 角色**：用户问题调查，模式 A、资深电力算法专家；正式分支 `arena/51b63974-nilm-calc-tool` 从 d8fb3f3 快进到用户最新提交 `1466933`，该提交更新 2026-11-12 测试数据而非代码。同步前旧 `tmp/` 已完整复制到 `/home/user/nilm_tmp_before_1466933`，新 `tmp/` 只读、未修改；不额外提交现场数据。
- **材料**：`tmp/profile_device_20261112_180540.json` 源文件为 Windows 路径下 2 号搅拌机启停 CSV；当前仓库缺该原始 10 kHz 波形。画像 auto、单相纯电流 A、fs=10000、50 Hz、前窗 10 周波 / 后窗 50 周波、merge_gap=10 秒、无标签，60,000 周波。`tmp/realtime/current_20261112.csv` 仅分路 source_id=1、run_id=1794482888958，1172 行、每行 window_s=1.0、约 1.024 秒间隔，时间 12:38:46.791～12:58:45.767；`tmp/run_info.json` 的分路 source_path 与画像源文件一致，但实时输出是窗口 RMS 聚合值，不是原始采样或逐周波序列，不能用于逐周波级重提 / 精确端点校验。实时电压和有功全零与该次只映射 A 电流的纯电流口径相符，不应当用零功率数据判断启停。
- **已有画像 6 条事件对照**：画像分别记录 12:44:11.528 STOP ΔIa=-0.2099 A、12:46:32.848 STOP -1.7646 A、12:49:42.848 STOP -5.2928 A、12:51:23.388 START +6.2836 A、12:51:45.308 START +0.0401 A、12:52:22.207 STOP -5.4032 A；前五条由 `auto:two_window` 补充，最后一条是 `auto:steady_state`。以最近 1 秒实时点的前 15～5 点 / 后 5～15 点中位数粗比（并非画像 10/50 周波口径）：依次约 7.091→6.977 A、7.236→7.055 A、7.049→0.546 A、0.355→6.487 A、6.480→6.861 A、6.776→0.282 A。故前三个小幅 / 非持续变化是强烈可疑误识别（按时间实际为 12:44:11、12:46:32、12:51:45），另三处有明显持续电平变化；不能仅凭这些约 1 秒汇总值断言物理启停真值或精确时间。文件开头已有约 7.1 A，不能凭文件内没有早先启动就认定漏检。
- **机制与影响**：`auto_locate_events` 先稳态分段，再把距离已有事件超过 guard 的双滑窗事件补入；`_steps_two_window` 按前后均值变化 / 自适应门槛找局部峰，`event_features` 却按事件终点之后 50 周波中位数减起点前 10 周波中位数量 Δ，`build_profile` 按 Δ 符号分类且未对补入候选再做持续状态变化确认；交替校验主要补检和报告不确定段，不会过滤这些候选。该机制与画像 3 个小变化被纳入相符，但缺逐周波数据无法复现每个候选的具体生成过程或证明根因唯一。画像 START 的 +6.2836 与 +0.0401 A 同时入样，均值 3.1619 A、σ 4.4148 A；STOP 四条含两条可疑样本，均值 -3.1676 A、σ 2.5968 A，可能污染距离匹配及轨迹。不要直接投入生产或直接手改均值，应以原始波形和人工标签重新提取并验证。
- **重要配对**：`run_info.json` 和 `config_branch.json` 显示此次实时播放加载 `tmp/nilm/profile_branch_profile_device_20261112_122347.json`（源为 1 号搅拌机停止 CSV），而用户指定的 `profile_device_20261112_180540.json` 来源为 2 号搅拌机。`tmp/nilm/nilm_profile_candidates_20261112.csv` 因而不能作为 180540 画像的匹配效果证明，亦不能把另外设备的拒绝 / 确认结果当作本画像误识别的验证。
- **用户执行命令 / 输出 / 判读**：无需命令；请提供 2 号搅拌机原始录波 CSV（大文件按仓库外或分片方式提供，不替换现有 tmp）、当次提取实际基准配置 / 列映射，以及人工确认的每次启动 / 停止时刻、时区和起止判据；至少确认以上 6 条哪些误报、是否有漏报。之后在隔离副本按同样参数重现逐周波序列、对照人工标签、设计避免短暂波动污染的修复与多设备回归。
- **局限**：仅分析现有输出及源码，未重跑原始数据提取、未修改算法、未声称已修复；1 秒窗口重叠 / 窗口中心差与过渡冲击均可能使 RMS 估计偏离逐周波真实前后值，设备多档和工艺真值未知，不能硬编码 6 A 阈值或将猜测事件作为金标准。
- **是否进入 REPORT.md**：否，初步诊断及资料缺失，非稳定结论。

### T-046 补充：用户确认的启停结果

- 用户确认：`12:44:11`、`12:46:32` 两条停止和 `12:51:45` 启动为误报；没有漏报。依此，画像另外三条记录对应已识别的有效动作：`12:49:42.848` 停止、`12:51:23.388` 启动、`12:52:22.207` 停止；上述为画像自动定位时刻，并非人工标定的精确起止点。
- 当前仍缺该 2 号搅拌机原始采样 CSV，不能以 1 秒 RMS 聚合数据重建逐周波输入或验证修复效果；已知画像元数据中的相别、fs、列映射等可先作为复现线索，当次实际完整基准配置如能提供也应核对。用户反馈未提供具体修复验收窗口和其他设备样本。
- 本次仅记录用户反馈，未修改算法、画像或 `tmp/`，没有运行新实验或声称修复。

### T-046 补充：切换模式 B 的本地复现

- 用户指定当前画像误识别任务切换模式 B，不改变项目默认模式；本次不运行新实验、不修改算法或用户数据，后续只依据用户本地实录判定。
- 用户本地执行包（Windows / 已安装本项目）：在 PowerShell 的项目目录运行 `git rev-parse --short HEAD` 记录版本。启动现有服务，进入「数据处理 → 设备画像提取」，选择本机 2 号搅拌机启停原始 CSV；按已有画像设置独立基准 fs=10000、f_nom=50、PT=CT=1、文件时标 UTC 不勾选、接线 3p4w，不反转；启用列映射：时间列 1、Ia 列 4、其余通道留空；时间段留空、自定义时间不启用；口径选单相纯电流，分路及总线检测相均为 A；前窗 10、后窗 50、合并间隔 10 秒、标签留空。设备 ID 可填 device，画像文件名留空以生成新的文件，不覆盖原有画像。提取后回传版本、结果页面完整提示和事件明细（含时刻、方向、来源、ΔIa）、新画像 JSON；用户可不上传原始波形。
- 判读：同一代码、输入及配置下期望可对照原画像 6 个候选；实际结果可能因版本、配置或输入不同而变化，以用户回报为准。用户已确认 12:44:11 / 12:46:32 停止与 12:51:45 启动为误报，另 3 条为有效动作、无漏报；记录的定位时刻不代表精确人工起止。当前版本未修复自动定位，本步骤仅复现，不应期待误报消失。现场数据 / 匹配表现尚未回传；提取结果不可未经验证直接用于生产。

### T-046 补充：模式 B 本地复现实录（版本 cad8d85）

- 用户报告本地版本 `cad8d85`，回传 `tmp/profile_device_20261113_085349.json`。当前分支快进至该版本之前，完整备份旧 `tmp/` 到 `/home/user/nilm_tmp_before_cad8d85`，再同步用户数据；用户新提交替换了原 `profile_device_20261112_180540.json`，备份保留旧文件。
- 比较新旧两份画像 JSON：仅 `created` 和 `command` 不同，其余顶层字段均相同。输入路径、单相电流 A、列映射、前后窗及 60000 周波一致；两次均 2 START / 4 STOP；用户确认三条误报仍在。该实录证明相同设置下问题可复现，并不证明此前推断为唯一根因；没有发生自动定位代码修复。
- 下一步模式 B：用户可在本地用本次提取生成的 `output/nilm/nilm_tune_base.json` 与原始 CSV，通过 `elec_tool.nilm_profile.load_cycles` 提取逐周波时间、A 相 RMS 电流及 A 相谐波电流至新的压缩诊断文件；执行前校验 fs、f_nom、列映射、PT/CT，执行后校验 60000 点和画像首末时刻，采用独占创建避免覆盖；该文件虽不含原始瞬时波形，仍包含设备数据，须用户自愿提供。参数不符 / 时刻不符时拒绝写文件并回传错误。不在沙盒运行真实原始数据；未获诊断文件之前不宣称修复或确定阈值。

### T-046 补充：模式 B 回传逐周波数据的只读诊断

- 用户提供 `tmp/profile_cycle_diag_20261113.npz`，正式分支从 `0b21d97` 快进到 `2485d7c`（用户提交只新增该文件，不替换原文件），NPZ SHA256 `f0804f511509b936bd30796ad158f4b89fa4d5b7d55fc009922e3592f2d024fe`。仅读取，`allow_pickle=False`；`t`、`ia`、`ih_a` 均 60000 个有限 float64，首末时刻与画像一致，中位间隔约 0.02 秒。原始波形未上传；计算该文件中每个事件的前后中位数是对用户回传实录的分析，不是重跑原始提取。
- 用画像 onset 索引对 `ia` 求中位数，窗口分别为事件前 [-5,-1) 秒、事件后 [0,1) 秒及 [2,6) 秒：12:44:11 STOP **7.287 / 7.097 / 7.087 A**（持续微小变化）；12:46:32 STOP **7.334 / 5.643 / 7.143 A**（短时下降后基本恢复）；12:51:45 START **6.600 / 7.681 / 6.871 A**（短时上冲后接近原运行电平）；两条真实 STOP 12:49:42 **6.867 / 1.156 / 1.161 A**、12:52:22 **6.906 / 1.163 / 1.158 A**；真实 START 12:51:23 **1.148 / 10.218 / 6.605 A**，启动冲击后稳定在新电平。真实 / 误报分类来自用户，并非仅凭波形自行判定。样本提取时段极短、额定不同设备和状态未知，这些数值不是通用门槛。按画像原 10/50 周波计算的六条 `ΔIa` 均与画像 `vec.d_ia` 在小数精度一致，说明此导出序列与画像事件特征一致；不能据此证实该数据能还原所有原始波形或其他特征。
- **重要口径差异**：`CycleFeatures` 对电流取 `sqrt(mean(i*i))` 含直流，监测的 `current` 窗口本次配置 `remove_dc=true`，`metrics.py` 计算交流有效值。例 12:58:20.295 实时交流 RMS 0.207 A、实时 `Ia_dc` -1.107 A，同窗推得含直流真 RMS 约 1.126 A；导出的相近逐周波中位数约 1.127 A。两者不同主要与去直流口径一致，但窗口、时间和聚合方式也不同；不能因此断定设备实际待机电流或设备传感器质量。先前 1 秒监测曲线数值只适合粗略对照，不能直接替代画像的含直流逐周波幅值；不应为此擅改画像 / 在线算法口径。
- **机制 / 方向**：已有画像显示误报均由双滑窗补入。结合具体序列，短暂扰动或运行态小幅变化被当作事件，但仅凭导出数组与代码还不能断言每条候选触发的完整内部参数及因果链。可能的修复方向是在自动画像提取候选后对持续电平变化 / 恢复进行核验，保留启动冲击与实际新稳态，保护短运行、缓慢启停、分档和文件边界，并对不确定事件作提示而非强行删；阈值和规则需多设备、多场景回归，不能直接以本样本的 0.2 A、6 A 或固定 2 秒当通用真值。标签模式可作为本地临时对照，不代表自动定位已修复。
- **局限**：只基于一段用户确认的设备录波与导出特征，未重跑原始 CSV、未修改算法、未作目标环境回归；其他设备及真实启停边界仍需验证。当前继续模式 B，进一步验证须提供用户本地执行步骤并回收实录。

### T-046 补充：持续电平核验修复与模式 B 待验

- **授权 / 范围**：用户同意按持续电平变化和恢复核验修复并继续模式 B。仅单相纯电流、无标签的设备画像启用；不改原有口径、单相电压＋电流、标签模式、总线在线匹配或波形分析，也不改 `tmp/`。
- **实现**：稳态分段、双滑窗补充及起点精修后、交替补检前，至少有 3 个幅值接近的主要候选并包含正负变化时，基于候选中位幅值建立相对参考，仅检查孤立的双滑窗候选。前窗、后续电平（终点后第 1～5 个 post 窗）、短窗中位数的最大偏离一起判断；后续差 < 参考 25%、最大偏离 < 参考 65% 才不直接纳入。缺前后数据、相邻候选过近、数据不有限、参考不足时保留。每项在 notes 报时刻、短窗 Δ、后续 Δ、参考值并提醒人工复核及标签回退；后续交替校验仍可能另行补检。没有用本设备固定安培阈值。
- **不可回避的局限**：小幅持续变档和运行波动可能仅凭电流不可区分，本规则可能排除真实小档位、低负载或短运行，提示并人工标签是回退而非保证；此前未生成候选的软启停仍可能漏，已有同向合并也不变。样本极少、两种时间窗和阈值是经验参数，不保证设备普适或现场可用。指南 H.33 及生成算法文档已说明。
- **验证**：新增 `tests/test_profile_small_transients.py`：3 种比例下三类小 / 恢复候选及记录、短运行 / 邻近、大幅冲击、缺参考、边界、非有限数、稳态来源保护；旧多档、短运行、启动冲击与两段式停止场景启用核验前后对照；mock 周波加载验证 build_profile 仅单相纯电流自动模式启用并有 notes，标签 / 其他口径不启用。新增测试最终 12 passed。定向（新增测试最终 12 项＋212、226、90）87 passed / 1 warning。隔离目录全量（新增测试当时 11 项）801 passed / 1 skipped / 1 Starlette/httpx 弃用 warning；新增最后 1 项随后单独通过。四份生成文档 `--check` 均 OK。
- **用户回传逐周波离线定位回归**：只读原 NPZ，保持 pre=10/post=50、50 Hz，对 `ia` 调用修复前后自动定位并以 mock 周波加载走画像组装（非 CSV / load_cycles 端到端）：由 6 条变为 3 条，保留用户确认的真实 STOP / START / STOP（onset 周波索引 32854 / 37881 / 40822，ΔIa -5.2928 / +6.2836 / -5.4032 A），3 条被报告的候选索引 16288 / 23354 / 38977，分别对应用户本地画像 12:44:11 / 12:46:32 / 12:51:45。沙盒本地时区展示为 04 点，不改变数据时间；结果不能当作用户 Windows 原始 CSV 验收。
- **模式 B 下一步**：用户更新正式分支后，以同一原始 CSV、采样与列映射、前 10 / 后 50、merge 10 秒、单相纯电流分路 A / 总线 A、无标签重新提取，输出到新文件，回传 HEAD、完整提示、事件明细和新画像 JSON；逐条核对三个保留事件、三个提示及是否有漏报。生产使用前还需其他设备和真实短运行 / 分档样本验证。

### T-046 补充：模式 B 用户本地新画像对照（8e27080）

- 用户回传本地版本 `8e27080` 及 `tmp/profile_device_20261113_103508.json`。正式分支从 `f3d5858` 快进至 `8e27080`（该用户提交只新增此画像），快进前完整备份旧 tmp 至 `/home/user/nilm_tmp_before_8e27080`；只读取、未修改画像或用户数据。通过 Git 祖先关系核实该版本包含修复 `f3d5858`。
- 新旧画像元数据均记录同一来源 CSV 路径、自动提取、单相纯电流分路 A / 总线 A、10000 Hz / 50 Hz、60000 周波、前 10 / 后 50、PT/CT=1、相同起止时间；命令中合并间隔均为 10 秒。元数据相同不能独立证明 CSV 字节和完整运行配置完全相同。
- 按事件完整记录对比，旧画像 2 START / 4 STOP，新画像 1 START / 2 STOP；保留的三条事件起止周波、时间、特征和来源**完全一致**：12:49:42.848 STOP（−5.2928 A）、12:51:23.388 START（+6.2836 A）、12:52:22.207 STOP（−5.4032 A）。删除的三个索引 16288 / 23354 / 38977 对应用户先前确认误报的 12:44:11、12:46:32、12:51:45，分别有核验提示；未新增事件。按用户先前确认的三条真实动作和无漏报，此样本的画像对照符合预期；尚未独立复核录波中所有物理真值。
- 新画像启动仅 1 次、停止仅 2 次，notes 都已提示少于建议的每方向 3 次；画像小样本且来自单次工况，尚不足以证明其他设备、分档 / 短运行及在线总线匹配的误报漏报，使用生产前仍需补录多工况并做现场匹配验证。该结果是用户本地回传的画像实录，不是沙盒重跑原始 CSV；本次只比对 JSON 与版本，未运行新算法实验或修改算法。

### T-047：模式 B 同源设备播放画像启动漏报诊断（5ed5293）

- **角色 / 模式 / 范围**：资深电力算法专家，继续模式 B。用户报告 `5ed5293` 用提取画像的离线 CSV 播放负荷辨识时漏报启动，并提供 `tmp/` 实录。fetch 后用户版本包含本分支前一记录及其数据提交；同步前完整复制旧 tmp 至 `/home/user/nilm_tmp_before_5ed5293`，再 fast-forward 到 5ed5293。只读用户数据，未修改在线算法、原始 CSV 或 tmp。
- **对应关系 / 配置**：`run_info.json` 的 started_side=branch、run_id 对应输出的 1794538131446；分路 source_path 与画像 `source_file` 记载同一 2 号搅拌机 CSV 路径；播放复制的 `tmp/nilm/profile_branch_profile_device_20261113_103508.json` 与用户所指定 `tmp/profile_device_20261113_103508.json` 字节一致。分路 fs=10000、f_nom=50、映射时间列 1 / Ia 列 4、PT/CT=1、I 量、profile enabled、窗口 3000、间隔 500 周波、max_scale=1；配置未指定 `min_confidence`，按 `NilmConfig.params` 实际使用默认 0.3。自适应参数只应用于标量算法，不修改画像阈值；源 CSV 本体不在沙盒，不能证明文件内容或重放完整过程。
- **用户回传的结果**：画像诊断 CSV 在已知真实启动 12:51:23.388（g_on=37881）有 START 候选，并非没生成；`rejected`、`trajectory_deviates`、conf=0.2995、D²=1.546、D²/维=0.386，ΔIa=+5.1990 A、peak_ratio=16.7568、dur=49。画像对应事件 ΔIa=+6.2836 A、peak_ratio=13.8643、dur=49。候选置信度低于 0.3 故拒识，主事件 CSV 不包含画像 START；多种其他非画像算法当时各自有 up 候选，不能等同画像识别成功。另有 12:51:23.727 异常大负向候选和其他候选，不可把它等同该真启动。
- **逐周波离线验证（不是原始 CSV 端到端）**：读取先前用户提供的 60000 周波 NPZ `ia` / `ih_a` 与同一画像，构造 3000 周波窗口，调用 `detect_profile`（配置参数、I 口径、off 状态）。窗口 global [35000,38000) 上 reproduces onset=37881、end=37930、ΔIa=5.19896、D²=1.54594、模板距离 2.06432、轨迹折扣 0.363315、confidence=0.299474、`trajectory_deviates`、rejected，与用户诊断值四舍五入一致。自动变点局部为 37881(+76.4773 A)、37900(−45.728 A)、37958(+5.9058 A)、37970(−4.0733 A)；画像最长持续 49，原逻辑认为自身过渡范围直到 37964，37970 被当成窗内其他变化，`post_hi=37960`，于是该候选的画像 50 周波后窗被截至 30 周波，模板也按更短序列重采样。若窗口恰好 [34980,37980)，尚未产生该截断，离线单次 `detect_profile` 返回原画像 ΔIa=6.2836、模板距离 0、conf=1；但实时需满足 end+post 的等待条件，不能声称该较早窗本来就会落盘。
- **状态联动**：事件 CSV 12:49:42.848 的画像 STOP confirmed（0.9981），后续 12:52:22.227 STOP 为 low_confidence、`state_mismatch`（0.4991）；代码对关机状态再 STOP 置信度折半。逐周波局部短窗对照该 STOP，在 off 时 0.4991 带 state_mismatch、on 时 0.9982 无标记；因此它与中间启动未被接纳、状态未翻到 on 的现象一致，但短窗实验不是完整回放。
- **判断 / 下一步**：这个样本的直接拒识链条是后窗截断导致的幅值和轨迹差异，再乘轨迹罚分低于置信度门槛；一个变点是否属于设备冲击或他设备真实动作不能仅凭当前单通道样本普遍断定。不要仅因 0.2995 接近 0.3 就全局调低门槛、关闭轨迹/状态检查，或无条件放宽后窗：会增加总线多设备相邻动作的误认和窗口污染风险。可进一步设计有条件的冲击回落 / 同一过渡核验或其他兼顾拥挤窗的修复，并做合成相邻他负荷、短运行、分档、波动、尺度回归，再由用户模式 B 本地用原 CSV 复测；尚未实现，也未验证真实总线侧。
