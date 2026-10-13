# NILM_AC 会话纪要（完整存档）

> 台账文件（BOOTSTRAP.md v2.2）：**只追加，每 session 一条，不新建文件**。
> 每条纪要结构（勿改）：
> ```markdown
> ## [YYYY-MM-DD] 会话纪要
> - 目标：
> - 本会话角色：
> - 完成项：
> - 关键决策：
> - 未决问题：
> - 相关文件/分支：
> ```
> 纪律：命令类实录须含「用户执行命令（含实录路径）+ 输出 + 判读」三件套，正文过长时指向 `REPORT_TEST.md` 对应专题号，不重复粘贴。

---

## [2026-10-10] 会话纪要
- **目标**：① 执行 BOOTSTRAP.md v2.2 开局仪式、恢复现场；② 任务「补齐台账骨架」——按台账规则初始化 `README.md` / `REPORT.md` / `REPORT_TEST.md` / `NILM_DATA_DICT.md` / `session/NILM_AC_session_complete.md`（本 session 不写业务代码）
- **本会话角色**：工程实现工程师（任务级覆盖；`ROLE.md` 默认当前角色仍为资深电力算法专家）｜**执行模式**：模式 B（用户显式指定）
- **完成项**：
  1. 开局仪式全过：git 现场核对、`ROLE.md` 读取、`gh auth status` 通过（GH_TOKEN / qjx1122）、`git ls-remote origin` 通过（远端 `main`=`27b28ea`）
  2. `STATUS.md` 按模板初始化（原缺失）→ commit `e821ef3` 即刻 push（防快照回退丢工作）
  3. `README.md` v0.1：9 节骨架；仅登记沙盒可实证的事实（远端地址、`git ls-files` 结果），6 个实操章节（安装/运行命令/数据目录/配置/产物/生产流程）全部 🔶占位
  4. `REPORT.md` v0.1：算法路线（4 候选，无推荐）/ 稳定结论（暂无）/ KPI 口径（3.1 通用数学定义已落盘、3.2 项目口径全 🔶）/ 推荐版本（暂无）/ 事故教训（转录协议层 3 条并标注性质）/ 收尾触发检查表
  5. `REPORT_TEST.md` v0.1：条目模板 + 专题索引 + 待归档专题 **T-001「环境与数据基线核对」模式 B 执行包**（E-0 环境说明 / A~D 四组只读命令（PowerShell+bash 双版本）/ 预期输出样例（标注「示例，非实录」）/ J-\* 判读要点（标注「经验判据」）/ 结果回收格式含实录路径必填项）
  6. `NILM_DATA_DICT.md` v0.1：8 章节模板（数据源/字段字典/粒度口径/文件命名/质量规则 Q-01~Q-08/预处理与双标定 P-01~P-08/设备标签库/数据集划分）+ 变更记录；🔶=116 处，未填任何未经用户确认的字段名与数值
  7. `session/NILM_AC_session_complete.md` 创建并追加本条纪要
  8. 文件级验证 V1–V8 全通过；V4/V5 暴露 3 处标注松动并已修正
- **验证三件套（沙盒侧，模式 B 下仅文件级验证）**：
  - 命令：`for f in STATUS.md README.md REPORT.md REPORT_TEST.md NILM_DATA_DICT.md session/NILM_AC_session_complete.md; do [ -s "$f" ] && stat -c%s "$f" && wc -l < "$f"; done`；`grep -qF "<章节名>"` 逐项校验（README 6 节 / REPORT 5 节 / DATA_DICT 8 节 / STATUS 7 节 / REPORT_TEST 模板+索引+三件套字段）；`grep -nH '✅' | grep -vE 'git |实录|来源|…'`（无依据断言扫描）；`grep -nHE '[0-9]+(\.[0-9]+)? *(W|kW|%|GB|min)'`（数值断言扫描）；`git status --short --branch`（仓库边界）
  - 输出：6 文件全部 OK 非空（STATUS 45 行 / README 107→109 行 / REPORT 89 行 / REPORT_TEST 218→220 行 / DATA_DICT 114 行 / session 16→本条）；章节校验退出码 0，0 处 MISS；标注统计 README 🔶=35、REPORT 🔶=20、DATA_DICT 🔶=116；数值扫描仅命中「命令行本身 + J-\* 经验阈值」；`git status` 无台账外散文件（仅 6 个台账文件 + 2 个协议文件）
  - 判读：结构完整、边界干净、无编造事实 → 骨架交付合格；**但用户环境侧 0 验证**（无代码可跑），故 `README.md` 第 9 节明示「沙盒已验证 / 用户环境未验证 / 已知缺口」三段
- **关键决策**：
  1. 依赖恢复步骤跳过（无 README、无任何依赖声明文件，无据可依）→ 记入 `STATUS.md` 决策记录
  2. 不另建 `feature/*` 分支，直接用平台固定 session 分支（BOOTSTRAP 任务协议允许）
  3. 模式 B 纪律落地：`ROLE.md` 的项目背景（双标定 / 四模型 / 终端·用户粒度 / CSV 合并规则）只作「背景描述·推断」引用并显式标注，不当事实；`NILM_DUAL_SCALER` 两种可能含义标「推测，不作事实」
  4. `TUNING_GUIDE.md` 本次**不创建**：BOOTSTRAP 规定该文件「整篇重写对账、不追加流水」，当前无稳定方法论可对账，建空骨架只会制造噪音（理由记入 STATUS TODO 5）
  5. T-001 记为「待归档专题」而非「已完结专题」：收尾仪式第 3 步只对已完结专题追加报告，T-001 结果待用户回报
  6. 尽早 push：开局产物与收尾产物均即时 commit+push（`ROLE.md` v1.3 快照回退教训）
- **未决问题**：
  1. **（阻塞，用户侧）** T-001 执行包未跑：代码在哪（B6）、数据在哪与是否可入库（C1/C6）、`NILM_DUAL_SCALER` 实际取值与含义（C4/D7）、KPI 主判据与阈值（D1）、粒度与划分口径（D2/D5）全部未知
  2. 依赖声明文件缺失 → 是否需由 `pip list` 反推生成 `requirements.txt`（待 J-B4 结果）
  3. 数据是否入 git、`.gitignore` 策略未定（待 C5/C6 结果）
  4. `TUNING_GUIDE.md` 何时建（待有稳定方法论/SOP）
- **相关文件/分支**：`STATUS.md`、`README.md`、`REPORT.md`、`REPORT_TEST.md`（T-001 执行包在此）、`NILM_DATA_DICT.md`、`session/NILM_AC_session_complete.md`｜分支 `arena/82e34fb8-nilm-calc-tool`（已 push）｜基点 `main`=`27b28ea`

---

## [2026-10-10] 会话纪要（第 2 条：电气量计算工具实现 + Web 界面验证 + 本地部署文档）

- **任务**：实现「电力系统各类电气量计算工具」软件代码（用户 6 条验收标准 + 数据事实：二次侧三相电压电流、fs=6400 Hz、CSV 七列、PT=100/CT=15 可配）；本轮收尾追加用户要求的「README 中增加软件本地详细部署及运行说明」
- **角色 / 模式**：工程实现工程师（任务级覆盖）｜**混合模式**——沙盒侧写码 + 合成信号解析解自验证 + live preview 实跑（模式 A，已有实录）；Windows 部署 / 真实数据对账 / 生产常驻交用户本地（模式 B，执行包＝`REPORT_TEST.md` T-002 的 W/R/P 三组）
- **本轮产物**：
  1. 代码（4 层）：`elec_tool/`（config/blocks/scaling/metrics/selftest + `analysis/{window,rms,harmonic,power}` + `sources/{csv_file,csv_tail,tcp_stream,simulator,parsing}` + `engine.py`）、`cli.py`（7 子命令）、`configs/default.json`、`app/server.py`（FastAPI + WebSocket + 引擎后台线程 + 12 组 REST）、`app/static/{index.html,style.css,app.js}`（12 个导航子界面、原生 canvas、零外链、WS 断开降级轮询）
  2. 测试：`tests/`（config/parsing/analysis/sources/engine/cli/server）＝**142 项**，`pytest tests/ -q` → **141 passed, 1 skipped**（skip＝60 Hz×50 次逼近 Nyquist，理由写在 skip 里）
  3. 文档：`README.md` **v0.2**（新增 §2 本地部署 7 小节、§3 运行说明 5 小节、§4 接真实数据、§9 生产推荐流程、两张排错表）、`REPORT_TEST.md` **v0.2**（追加 T-002：沙盒侧 A1~A10 三件套 + B1/B2 缺陷记录 + 用户侧 W/R/P 执行包 + J-\* 判读 + 回收格式）、`NILM_DATA_DICT.md` **v0.2**（用户确认事实翻 ✅：17 处 ✅ / 111 处 🔶）、`REPORT.md` **v0.2**（C-01~C-08 稳定结论 + 3.3 电气量计算与验收口径 + 推荐版本 v0.1.0 + 3 条本仓库教训）、`STATUS.md` 整体更新（范围边界「不写业务代码」翻 ❌ 失效）
  4. 工程细节：配置持久化分离（出厂 `configs/default.json` 入库不被污染 / 运行 `configs/runtime.json` gitignore）；csv_tail 补 `--from-end`、`--watch-newest` 与界面勾选框；导出格式校验；重启引擎清空历史；自检报告显示运行环境（Python/OS/numpy）
- **验证三件套（沙盒侧实录）**：
  - 命令：`cli.py selftest`；`pytest tests/ -q`；`cli.py gen-sample/sources/compute/live`（含 `--set-window voltage=5`、`--format csv`、`--pace 20`、`--from-end`、`--watch-newest`）；`cli.py serve --port 8001 --pt 100 --ct 15 --set-window voltage=2` + `curl /api/state|/api/result|/api/selftest|/api/export|/api/probe|/api/files`；WebSocket 客户端收包；`pip download`/`--no-index` 离线安装两轮（Linux 与 win_amd64 目标）；`ast.parse(feature_version=(3,9)/(3,10))` 扫 31 个 .py
  - 输出：自检 44/44、最差相对误差 1.508e-05；测试 141 passed/1 skipped(54.95 s)；5 s 样例实算 26 次输出、emits `{fundamental:26, harmonic:26, voltage:6, …, spectrum:6}`；改 5 s 窗 → voltage 2 次、缓冲 10880→49280；导出 CSV 34.6 万行；实时速率 6397–6400 点/s；`serve` 覆盖参数经 `/api/state` 回读一致；离线安装后自检与测试全绿；Windows 目标 24 包/18 MB（含 `numpy-…-win_amd64.whl`）；3.9/3.10 语法不兼容项＝无
  - 判读：6 条验收标准逐条有代码与测试对应（`README.md` §1 对照表）；窗长口径修后**精确**等于请求值（1 s → 6400 点/50 周期/1.000 s，频谱分辨率 1.0 Hz）；内网可离线部署；**用户环境侧 0 验证**（Windows/真实数据/常驻），一律 🔶 并出执行包
- **关键决策**：
  1. UI＝Web 版（可当场 live preview 验收、内网零外链、跨平台免装 GUI 依赖）；**Qt 桌面壳延后**；算法核心独立成包只依赖 numpy，CLI 与库调用同等交付
  2. 实时源＝统一 `DataSource` 接口 + 内置模拟器先跑通全链路，再做 csv_tail 与 tcp（真实协议帧格式 🔶）
  3. 谐波口径＝额定 50 Hz 整周期矩形窗 FFT（128 点/周期，50 次=2500 Hz<Nyquist 3200 Hz）+ 可选 45–65 Hz 自适应估频抗泄漏；**IEC 61000-4-7 分组延后**
  4. 单进程单 worker（引擎状态在进程内存）→ `README.md` §9 明列「不推荐 `--workers N`」
  5. 文档纪律强化：README 里每条命令**先实跑取证再写**（实测发现 `--every` 只有 compute 有、live 没有；`watch_dir_newest` 默认已是 true）；所有数字改为代码级/实测值（缓冲容量公式 `ceil(最长窗×fs×1.5)+max(块,64)`、内存 0.55/2.7 MB、selftest 退出码 0/1）；Windows 与真实数据一律标 🔶未实测
- **踩坑（本轮实录，均已修 + 加回归测试）**：
  1. **B1 并发**：`EngineRunner.start()` 持锁 join 旧线程 ↔ 旧线程写结果要拿同一把锁 → 互等到 2 s 超时后旧线程存活，且每轮重读 `self.engine` → 继续轮询被替换的新引擎 → 同批数据双重摄入（32000 行报 `samples_in=32640`）。修：锁外 join + 每轮全新 Event + 线程私有 engine/stop_event + 被取代即退场。教训：**并发缺陷不崩，只让数字悄悄变错**，须端到端断言「摄入点数==文件行数」
  2. **B2 数值口径**：`plan_window` 用绝对容差 `floor(cyc_req+1e-9)` 判整周期，遇估频 `f_used=49.999987`（相对误差 2.6e-7）少算一个周期 → 用户配 1 s 实际 0.98 s/49 周期、分辨率 1.0204 Hz 并持续误报截断。修：相对容差 `max(1e-9,1e-5·|cyc_req|)`；真·非整数周期（49.85 Hz→49 周期）行为不变
  3. **前端**：服务端按各量独立步长推送**分量子集**，整体替换会让慢窗量被 0.2 s 快量推送抹掉 → `mergeResult()` 按键合并
  4. **部署**：`uvicorn[standard]` 的 extra 拉 uvloop（无 Windows wheel）→ 跨平台 `pip download -r requirements.txt` 直接 `ResolutionImpossible`（补 `--implementation/--abi` 也无效）→ 显式列包 + `requirements.txt` 用 PEP 508 平台标记分流
  5. **事故：沙盒回收**：`.venv`/`data/`/后台进程全丢，仓库被重新克隆到基线 `27b28ea`，本地 `d07476d`/`3126e4c` 两个提交灭失（远端只到 `2b7d3c3`）→ 靠工作树文件尚存 + `git fetch` + `git reset --mixed FETCH_HEAD` 接回远端 tip，再按原结构重提交 4 个 commit 并 push（`880bf5f`/`8166743`/`b09f2a6`/`d2337ab`）。教训：**每个逻辑单元即刻 commit+push**（`ROLE.md` v1.3 同类事故第二次发生）；环境必须可一键重建
- **未决问题**：
  1. **（阻塞，用户侧）** T-002 的 W/R/P 三组未跑：Windows 安装与常驻、真实数据对账（U/I/P/PF/THD 与现场表计比对）、生产部署形态未知
  2. 电压列是**相电压还是线电压** 🔶（影响 `transform.voltage_input`）；现场实际编码与时间戳写法 🔶；PT/CT 实际值是否恒为 100/15 🔶
  3. 实时落地方式：采集器写文件（csv_tail 可用）还是 TCP（需协议文档：字节序/字段顺序/缩放/帧头尾）🔶
  4. 是否需要 IEC 61000-4-7 分组口径、是否需要 Qt 桌面壳、是否需要多用户/历史入库/报警推送
  5. T-001 的 B6/C6/D1~D7 仍未回报；`TUNING_GUIDE.md` 仍未创建（待真实数据后写窗长/口径选择教学才有依据）
- **相关文件/分支**：`README.md`(v0.2，本地部署与运行说明)、`REPORT.md`(v0.2)、`REPORT_TEST.md`(v0.2，T-002 执行包在此)、`NILM_DATA_DICT.md`(v0.2)、`STATUS.md`、`cli.py`、`elec_tool/`、`app/`、`configs/`、`tests/`｜分支 `arena/82e34fb8-nilm-calc-tool`（已 push）｜基点 `main`=`27b28ea`｜live preview：`uvicorn app.server:app --host 0.0.0.0 --port 8000`（`ELEC_TOOL_AUTOSTART=1` + 模拟器源）

---

## [2026-10-10] 会话纪要（第 3 条：四种数据源的配置·运行·验证 + tools/ 联调工具链）

- **任务**：用户要求「分别详细说明 4 种输入方式的数据源如何配置及运行，并进行验证测试」——4 种源＝`csv_file`（离线文件）/`csv_tail`（实时·文件追加，文件或目录）/`tcp`（实时·TCP 客户端，`text_csv` 与 `binary` 两种帧）/`simulator`（内置合成源）；交付须含每源完整配置字段（默认值与约束）、CLI/Web/库三种运行入口的具体操作、**真实验证测试（实跑取证，不是纸面说明）**，并按台账纪律落 `REPORT_TEST.md` 与 `README.md`
- **角色 / 模式**：工程实现工程师（延续上一任务）／**混合模式**——沙盒侧（模式 A）四源 × 三入口全部实跑取证 ✅；用户侧（模式 B）真实采集装置与真实 TCP 协议只出执行包，未获实录不下结论 🔶
- **本轮产物**：
  1. `README.md` **v0.3**：§4 由 2.2 KB 扩为 15 KB 的「四种数据源详解」——每源给出配置字段表（含默认值/约束/在哪设）、三入口操作步骤、沙盒实测输出、注意事项、可复现的验证方法；新增 §4.0 四源一览、§4.6 四源横向对账表、§4.8 一键复现；§3.2 的 `live` 段补 TCP 两帧实测与新增开关；§2.6 目录树补 `tools/`；§11 验证状态与已知缺口更新
  2. `REPORT_TEST.md` **v0.3**：追加专题 **T-003**（沙盒侧 S1~S13 三件套实录、四源对账表、F-01~F-05 缺陷记录、能力补齐、用户侧 **S 组**（无硬件可复现）与 **D 组**（真实装置/协议）执行包、J-S/J-D 判读要点、结果回收格式）
  3. `REPORT.md` **v0.3**：第 2 节新增稳定结论 **C-09~C-12**；第 5 节新增 2 条实录教训；第 6 节记录第 4 次收尾触发判定
  4. **`tools/` 三件套（新增，交付物）**：`tcp_feeder.py`（TCP 服务端扮演采集装置，`--mode text_csv|binary`、`--struct-fmt`、中文表头、单客户端串行、断开后继续服务）、`csv_appender.py`（按用户列格式持续追加写文件，`--rotate-every` 分片轮转、`--no-header`）、`verify_sources.py`（库级四源自动对账：自动拉起前两者、跑完即清理、输出 PASS/SKIP/FAIL 与解析解偏差；退出码 0/1/2 区分通过/验证失败/参数错误）
  5. **代码修复 5 处（F-01~F-05）**＋**测试 141→147**：`csv_tail._drain_current()`（切换前补读旧文件）、`parsing._flag_degenerate_clock()` 与合理性闸门、`base.note_key()` 告警去重（tcp/csv_tail 共用）、`cli.py::_print_diagnostics()`/`_fmt_clock()`、`cli.py live --frame/--struct-fmt/--struct-fields`、界面 TCP 面板两字段 + `/api/engine/start` 白名单、`app.js::collectSourcePayload` 死代码；新增 `tests/test_tools.py`（5 项防腐）与 `test_csv_tail_dir_switch_drains_old_file`（1 项回归）
  6. `STATUS.md` 第 4 次收尾滚动更新
- **验证三件套（沙盒侧实录，Linux 6.1.158+ / CPython 3.11.2 / numpy 2.4.6）**：
  - **库层**：`python tools/verify_sources.py` → **PASS 5 / SKIP 0 / FAIL 0**；`csv_file` U1均=5773.60 V（偏差 0.17‱，解析解 5773.503 V）、P=1140.644 kW、THDu 偏差 0.003 百分点、缺口 0；`csv_tail` U1均偏差 0.70‱、P=1127.747 kW；`tcp binary <7d` U1均偏差 0.42‱、P=1127.751 kW；`simulator` P=1127.727 kW；P 比基波解析解 P₁=1125.000 kW 高 0.24%＝谐波功率贡献（预期）
  - **CLI**：`csv_tail --from-end` 6 s → 输出 78 次、样本 100480、15.70 s、**16749 样本/s**、U=5805.9/5921.8/5689.5 V、P=1127.76 kW、缺口 0；`csv_tail` 目录 + `--watch-newest` 10 s（喂数器每 20 块轮转）→ 输出 125 次、样本 160640、**93 个分片**、缺口 0、告警自证「旧文件补读 640 行」；`tcp text_csv` 6 s → 输出 42 次、样本 54400、18134 样本/s、中文表头映射正确；`tcp binary >7f`（28 字节/帧）→ 输出 3 次、样本 60800、10201 样本/s，数值与文本帧一致 ⇒ 字节序/类型可配且解析无损
  - **Web/REST**（第二实例 8002，`ELEC_TOOL_AUTOSTART=0 ELEC_TOOL_PERSIST_CONFIG=0`，不动 8000 预览、不污染入库配置）：`/api/probe` 判对 `encoding=utf-8-sig`、7 列中文表头、`fs_est=6399.99`；五种配置逐个 `POST /api/engine/start` → `GET /api/state`+`/api/result`，P 落在 1127.73~1140.63 kW、PF=0.8584（csv_file 0.8637）、缺口全 0
  - **横向对账结论**：同源四路（csv_tail / tcp text / tcp binary / simulator）在三条入口下 **P 极差 0.013%**、U1 偏差 ≤0.70‱、THDu 偏差 ≤0.005 百分点 ⇒ **源类型与入口都不影响算法结果**
  - **异常路径**：帧格式不匹配（`<7d` 解 `>7f` 流）修复前崩 `OverflowError`，修复后为可诊断 `ParseError` + 自动退回合成时间轴 + 打印三条排查项；float32 存 epoch 秒 → 显式告警「时间戳整块无递增…步长约 128 s」；端口未监听 → `ParseError: TCP 连接失败 …[Errno 111] Connection refused。排查：①②③`；无喂数器时 `verify_sources.py` 是 SKIP + 提示且退出码 0
  - **回归**：`pytest tests/ -q` → **147 passed, 1 skipped**（59 s；唯一 skip＝`test_cli.py:43`，60 Hz×50 次逼近 Nyquist）；`cli.py selftest` → **44/44**，`worst_rel_err=1.508e-05`；F-01 的回归测试经「撤销修复→断言 1280≠1920 失败」验证过**确实能抓住 bug**
- **关键决策**：
  1. **无硬件验证路径进交付物**：用户没有采集装置，所以把「扮演采集侧」的喂数器/追加器与「一键四源对账」的验证工具做成 `tools/` 正式交付物，并加 5 项防腐测试——否则 README/T-003 里的验证步骤只是空头承诺
  2. **判定口径写进工具**：U1 用三相均值对账（合成信号含 2% 不平衡，单相值本就偏离）、容差 5‱；P 对 P₁ 容差 0.5%；THDu 容差 0.05 百分点；**出现数据缺口直接 FAIL**（正是这条硬判定让 F-01 无法蒙混过关）
  3. **编号命名空间分离**：`REPORT.md` 稳定结论用 C-0x、T-003 缺陷用 **F-0x**、T-001 用户命令用 A~D 组、T-002 缺陷用 B1/B2——本轮曾把缺陷编成 C-09~C-13 与结论撞车、又发现 B3~B5 与 T-001 命令编号撞车，最终改为 F-01~F-05
  4. **告警治理**：同类告警按「中文骨架」去重（去数字与 ASCII），CLI 收尾统一打印「缺口 + 引擎告警 + 源告警」并截断——不打印源告警等于「看着正常、其实时间轴是合成的」
  5. Web 侧验证跑**第二实例**（8002）而非复用 8000 预览，避免打断用户可见的实时演示
- **踩坑（本轮实录）**：
  1. **F-01 假缺口**：目录分片切换直接 `_reopen()` → 旧分片未读走的尾部被静默丢弃，每切换丢一整块（640 点/100.2 ms），形成与轮转周期同频的「疑似丢点」告警（8 s 内 8 处、间隔恰 2.000 s）。教训：**告警本身也可能是 bug 的产物**，先证伪告警再怀疑现场数据
  2. **F-02 显示层崩溃**：坏时标（1e308 量级）能穿过 `np.isfinite` 检查，崩在 `time.localtime`；必须在**解析层**设合理性闸门（|t|>1e11 秒即拒），显示层再兜一道
  3. **F-04 float32 存 epoch 秒**：量化步长 ~128 s，显示时刻偏早约 2 分钟且原先无任何告警
  4. **F-05 工具链三连**：① `node --check` **只验语法不验逻辑**（`return {…}` 后接死代码照样通过）→ 另做「`return` 之后残留语句数＝0」静态检查；② 给已有方法**中间**插入新方法会把原方法劈成两半（`TcpStreamSource.__init__` 尾部两行被吞进 `_note` → `NameError: cfg`）；③ 全量 `str.replace("self._notes.append(", "self._note(")` 把 `_note` 自身也改了 → **无限递归**（`RecursionError`）
  5. **heredoc 补丁纪律**：本轮 3 次 `assert old in s` 失败（类名写成 `TCPStreamSource` 实为 `TcpStreamSource`；`old` 未含原缩进导致 `lstrip()` 吃掉缩进 → `IndentationError`；文件里有两个 `return TimestampInfo` 分支）→ 教训：**patch 前先 grep 出精确原文与全部匹配点**，改完必须 `ast.parse` + 跑测试，不能只看语法
  6. `tools/tcp_feeder.py` 的 `--duration` 在阻塞于 `srv.accept()` 时不生效（无客户端就一直挂着）→ 遗留进程必须显式 `stop_process`；本轮 900 s 到期的喂数器曾让一次 Web 验证拿到 0 样本，重启后复测正常
- **未决问题**：
  1. **（阻塞，用户侧）** T-003 的 **S 组**（无硬件复现四源验证，约 10 分钟）与 **D 组**（真实 CSV 体检/对账、真实 TCP 协议要点、分片规则）未回报；T-002 的 W/R/P 组仍未回报
  2. 真实 TCP 协议 🔶：帧头帧尾/长度字段/缩放系数/字节序/时标类型/心跳；若含帧头+长度+校验，`struct_fmt` 不足以描述，需在 `sources/tcp_stream.py::_flush_block` 加拆帧（属新工作项，需先拿协议文档评估）
  3. TCP 的 `timeout_s` / `reconnect_s`（各默认 2.0 s）只是构造参数，未暴露到配置文件与界面
  4. `csv_tail` 目录模式按 **mtime** 选最新文件；若现场补写旧分片或命名与 mtime 不一致，需改成按文件名排序（待 D-5 回报）
  5. 四个口径问题仍未答：电压是相/线、实际编码与时间戳写法、PT/CT 是否恒为 100/15、实时落地是文件还是 TCP
  6. Windows 侧 S 组未实测（子进程/路径分隔符/编码可能有差异）；`TUNING_GUIDE.md` 仍未创建；IEC 61000-4-7 分组与 Qt 壳仍延后
- **相关文件/分支**：`README.md`(v0.3，§4 四源详解)、`REPORT_TEST.md`(v0.3，**T-003 执行包在此**)、`REPORT.md`(v0.3，C-09~C-12)、`NILM_DATA_DICT.md`(v0.2)、`STATUS.md`(第 4 次收尾)、`tools/{tcp_feeder,csv_appender,verify_sources}.py`、`elec_tool/sources/{base,parsing,csv_tail,tcp_stream}.py`、`cli.py`、`app/server.py`、`app/static/{index.html,app.js}`、`tests/{test_sources,test_tools}.py`｜分支 `arena/82e34fb8-nilm-calc-tool`（本轮提交见下）｜基点 `main`=`27b28ea`｜live preview：8000 端口（`ELEC_TOOL_AUTOSTART=1` + 模拟器源）

---

## [2026-10-10] 会话纪要（第 4 条：Web 界面下拉框专项检查与修复 F-06~F-10 + 界面层双层回归）

- **任务**：用户要求「检查 Web 总览面板-数据源与控制界面中数据源输入方式下拉列表框是否可正常选择 4 种输入方式分别进行配置（含其它下拉列表框）」——验证＋修复类：须实跑取证，缺陷要修＋加回归，并按台账纪律落 `REPORT_TEST.md`（追加到 T-003）与 `README.md`
- **角色 / 模式**：工程实现工程师（延续）／**混合模式**——沙盒侧（模式 A）jsdom 驱动真实页面打真实服务端 ✅已实录；用户侧（模式 B）真实浏览器手点＝T-003 新增 **U 组 7 步** 🔶待回报
- **本轮产物**：
  1. `tools/ui_dropdown_check.cjs`（新增）：jsdom 加载**真实** `index.html`/`app.js`，`window.fetch` 转发到真实服务端并记录请求原文，canvas/WebSocket 打桩（以绘制调用计数验证重绘），自动探测 9000 端口并拉起 `tools/tcp_feeder.py` 扮演采集装置、结束清理并把预览恢复为 simulator；覆盖 A 四种源端到端 / A2 帧格式联动 / A3 脏值保护 / B 三个口径下拉框 PUT 回显 / C 频谱三下拉框重绘
  2. `app/static/app.js`：`renderSource()` 拆成「状态摘要（总刷新）＋`fillSourceForm()`（仅 `!S.formDirty` 时回填）」；新增 `syncSourceForm()`（按 kind/frame 决定 10 个字段的 `disabled`＋写 `#src-hint`）与 `SRC_HINT` 逐源文案；`#src-kind`/`#src-frame` 注册 change；`#view-source` 全部 input/select 绑 input/change 置脏；「刷新」＝清脏重新回填；`collectSourcePayload()` 按 kind 裁剪＋非空/有限才送；`collectConfigPayload()` 改返回 `{payload, skipped}`（只送有限且 >0，`order_max` 取整 ≥2）；`startEngine()` 不再夹带配置段
  3. `app/static/index.html` + `style.css`：新增 `#src-hint`（逐源填写说明）与 `#src-formnote`（未保存提示）；`label.off{opacity:.45}`、`input:disabled,select:disabled{cursor:not-allowed}`
  4. `tests/test_web_ui.py`（新增 14 项前端契约）：5 个下拉框选项 ↔ 后端枚举集合相等、频谱三下拉框自洽、app.js 引用的元素 id 全部存在、两个源下拉框已注册 change、脏值保护与联动函数在位、载荷裁剪/空值跳过/启动不夹带配置三道闸门、`SRC_HINT` 覆盖 4 源
  5. 文档：`README.md` v0.4（§3.1 新增「数据源面板：4 种输入方式的联动、空值语义与两个保存入口」＝逐源可编辑/置灰字段表＋PUT 深合并 vs start 白名单对照＋空值语义＋6 步手工点检清单；§8 三层→五层验证；§2.6/§11/头部状态行/变更记录）、`REPORT_TEST.md` v0.4（T-003 追加 **S14~S18** 实录 + **F-06~F-10** + **U 组**执行包 + J-U1~J-U4 + 回收格式 + 结论/遗留）、`REPORT.md` v0.4（**C-13** + 第 6 条实录教训 + 第 5 次收尾判定）、`STATUS.md`（第 5 次收尾）
- **验证三件套（沙盒侧实录，Linux 6.1.158+ / CPython 3.11.2 / node v22.22.3）**：
  1. `JSDOM_DIR=/tmp/uitest node tools/ui_dropdown_check.cjs http://127.0.0.1:8000` → **PASS 74 / FAIL 0**（修复前同脚本 **PASS 37 / FAIL 10**）：4 种源逐个「可选中→无关字段已联动禁用→说明文案已切换→载荷只含该源相关字段→载荷无空值/0→服务端确实以该源运行」（csv_file `finished=true samples_in=32000`；csv_tail/tcp/simulator `running=true samples_in=32000/39040/44800`）；binary 才放开 struct 两项、切回 text_csv 载荷不带；脏值保护（经真实 WS `onmessage` 推入 `kind=simulator` 后 `#src-kind` 仍 csv_tail、半截路径仍在、提示出现，点「刷新」后恢复回填）；口径 6 组取值 PUT 全 200 且 `GET /api/config` 回显一致、载荷无 0 值；频谱 8 组取值均触发重绘（234~1245 次绘制调用）
  2. `pytest tests/ -q` → **161 passed, 1 skipped（59.28 s）**；`pytest tests/test_web_ui.py -q` → 14 passed；把 `app.js` 换回修复前版本再跑同一命令 → **7 failed / 7 passed**（撤销修复必 FAIL 已验证），还原后 14 passed
  3. 空值语义 REST 实录：`PUT {"source":{"path":""}}` → **HTTP 400**「source.kind=csv_file 需要 source.path（文件或目录路径）」；`PUT {"source":{"host":""}}` → **HTTP 200**（空 host 被静默存下）；`POST /api/engine/start {"kind":"csv_file"}`（省略 path）→ 200，沿用服务端已存路径读满 32000 样本 ⇒ **省略＝沿用、送空串＝被拒或被静默覆盖**，这是 F-07/F-08 修法的事实依据
- **关键决策**：
  1. **界面正确性用「真实 DOM + 真实服务端」验证**，不用「读代码 + 手点一次」下结论：jsdom 能断言请求载荷原文、服务端回显、推送后的 DOM 值——这是本轮 5 个缺陷全部现形的唯一手段（同期 `node --check` 与 `pytest` 全绿）
  2. **双层回归**：jsdom 端到端（需 node，可选）＋前端契约静态测试（不需 node，随 pytest 跑）；后者把「选项 ↔ 后端枚举一致」「引用 id 存在」「四道闸门在位」钉死
  3. **空值语义统一为「留空＝沿用服务端值」**，并在保存成功提示里列出被跳过的字段名（不静默）；两个保存入口的分工写进 README 与界面提示（口径/变比走 `PUT /api/config`，换源/开跑走 `POST /api/engine/start`）
  4. 脏值保护选「暂停自动回填 + 明确提示 + 刷新丢弃」而非「三方合并」：单人单机工具，语义越简单越不容易出错
- **踩坑（本轮实录）**：
  1. **F-09 最隐蔽**：快量 0.2 s 一次推送 → `render()` → `renderSource()` 无条件回填 → 停在数据源页时「刚选的下拉框被改回服务端 kind、输入一半的路径被清空」；只在「页面停留 + 引擎在跑」时复现，静态读代码看不出来
  2. **F-08 连锁**：`renderSource()` 只在源视图打开时执行 → 全新加载后表单停在 HTML 默认（PT/CT/fs 全空）→ 空框经 `+''===0` 送出 → 第一次点「保存配置」必 400，且提示不指明是哪个框
  3. **jsdom 三个坑**：① 无布局，`el.offsetParent` 恒为 null → 用「`!disabled && offsetParent!==null`」判「无关字段已被禁用」**恒真（假 PASS）**，必须只判 `.disabled`；② `window.eval(js)` 之后 `const S` 不可见（只有函数声明进 window）→ 需在**同一次** eval 里闭包导出 `window.__S=()=>S`；③ 捕获请求只过滤 POST 会漏掉 `saveConfig` 的 **PUT**
  4. `csv_file` 是离线源，读完即 `finished=true/running=false` → 断言必须写成 `(running||finished) && samples_in>0`，否则把正常行为判成失败
  5. TCP 用例必须先有采集侧：脚本自动探测 9000 端口，空闲则拉起喂数器（否则 `running=false samples_in=0` 会被误判成界面缺陷）
- **未决问题**：
  1. **（阻塞，用户侧）** T-003 新增 **U 组**（浏览器手点 7 步）未回报；真实浏览器（尤其 Windows/Edge）下的视觉置灰、输入法与焦点行为均未实测——jsdom 无渲染，置灰是 `disabled` 属性断言而非视觉核对
  2. T-003 的 S 组（无硬件复现）与 D 组（真实 CSV/TCP 协议）、T-002 的 W/R/P 组、T-001 的 B6/C6/D1~D7 仍未回报；4 个口径问题（相/线电压、实际编码与时标写法、PT/CT 是否恒 100/15、实时落地形态）仍未答
  3. 观察项（未修）：引擎启动后服务端把 `source.path` 解析为**绝对路径**并经 `/api/config` 回显到表单（`_persist` 写盘时仍还原为相对路径），属外观问题
  4. `tools/ui_dropdown_check.cjs` 依赖 node ≥18 + jsdom（沙盒装在 `/tmp/uitest`，**不入库**）；用户环境若无 node，只能跑 `tests/test_web_ui.py` ＋ README §3.1 手工点检清单
- **相关文件/分支**：`README.md`(v0.4，§3.1 数据源面板联动/空值语义/6 步点检)、`REPORT_TEST.md`(v0.4，**T-003 的 S14~S18 + F-06~F-10 + U 组**)、`REPORT.md`(v0.4，C-13)、`STATUS.md`(第 5 次收尾)、`app/static/{index.html,style.css,app.js}`、`tools/ui_dropdown_check.cjs`、`tests/test_web_ui.py`｜分支 `arena/82e34fb8-nilm-calc-tool`（本轮提交见下）｜基点 `main`=`27b28ea`｜live preview：8000 端口（`ELEC_TOOL_AUTOSTART=1` + 模拟器源）

---

## [2026-10-12] 会话纪要（第 5 条：第 6 轮四功能——用户时标格式 / 24h 曲线 / 逐曲线保存 / 自定义播放时间，修复 F-11~F-16）

- **任务**（用户 5 点）：① 离线 CSV 支持 `0/00/00 00:12:40.0000,290.175751,…`（无日期、4 位小数秒、无表头）② 界面所有曲线只显示最新 24 小时（不足则全部）③ 每条曲线可分别配置是否保存，保存曲线数据时未勾选项不保存 ④ 离线播放可选「自定义时间」（起始默认文件第 1 条，后续按采样率推算；否则用文件时间）⑤ 完成后验证
- **角色 / 模式**：工程实现工程师（延续）／混合模式——沙盒侧 pytest + jsdom + REST/CLI 实录 ✅；用户侧真实文件/浏览器点检＝T-004 **U6 组 8 步** 🔶待回报
- **开局**：沙盒曾被回收（第 3 次），`.git` 退回基线但工作树尚存 → `git fetch` + `reset --mixed FETCH_HEAD` 接回 `a88dcaa`，零差异；venv/样例重建
- **本轮产物**：
  1. 解析层：`parsing.py` 新增 `_parse_slash_clock`（日期段任一为 0 → 只取当天时刻，基准 1970-01-01，小数按位数换算）、`_unwrap_midnight`（回退 >12 h 视为跨日）；`parse_rows` 跳过时间戳列的数值告警；`/api/probe` 无表头回退（F-11~F-13）
  2. 历史层：`metrics.History` 重写＝按**数据时间**保留 `hours=24`（懒修剪 + `get(hours=)` 精确）、`array('d')` 列存储、`threading.Lock`、numpy 峰谷分桶抽稀；`/api/history?hours&max_points`；`output.history_hours/history_max_points`（兼容旧 `history_len`）；热更新搬运历史（F-14~F-16）
  3. 保存层：`output.curve_save` 六键；`POST /api/curves/save`（写 `output/curves_<ts>/<曲线>.csv`，UTF-8-BOM，未勾选项「已跳过」）；`GET /api/curves/export`（浏览器下载合并长表，未勾选单曲线 403、全不勾 400、无数据 409）；6 个面板勾选框与导出页列表同步
  4. 播放时间：`source.custom_time/custom_time_start`；`CsvFileSource._apply_custom_time`（时间轴＝起始＋样本序/fs，起始留空＝文件第 1 条，非法起始 400+toast）；CLI `--custom-time[-start]`；start 白名单放行；告警标注来源
  5. 验证：`tests/test_r6_features.py` 25 项、`tools/ui_r6_check.cjs` PASS 30/0、旧 harness 复跑 74/0、全量 **186 passed, 1 skipped**、selftest 44/44；History 24h@0.2s×2 量＝43.2 万点 38.5 MB、抽稀 40 ms（纯 Python 757 ms）
  6. 文档：`README.md` v0.5、`REPORT_TEST.md` v0.5（T-004）、`REPORT.md` v0.5（C-14/C-15 + 1 条教训）、`STATUS.md` 第 6 次收尾
- **关键决策**：无日期时标基准 1970 而非猜「今天」（真实日期交给自定义时间）；24 h 按数据时间；保存勾选＝配置项（面板/导出页共用）；热更新一律保留历史与结果
- **踩坑**：F-15 两功能互相打架（勾选框热更新把 24 h 曲线清空，单测各绿连起来才暴露）；F-16 性能要按目标规模实测（43 万点）、`np.frombuffer` 视图会在 `array` 扩容时 `BufferError`；`time_local` 小数 `.3f` 进位错位→改截断；`notes()` 转义 HTML
- **未决问题**：T-004 U6 组待回报；自定义时间只对 `csv_file` 生效；历史不跨进程落盘；`history_hours/max_points` 未上界面；横轴跨午夜不显示日期；起始时间按本地时区；此前 T-001/T-002 W-R-P/T-003 S-U-D 仍未回报；四个口径问题仍未答
- **相关文件/分支**：`elec_tool/{metrics,engine,config}.py`、`elec_tool/sources/{parsing,csv_file}.py`、`app/server.py`、`app/static/*`、`cli.py`、`tests/test_r6_features.py`、`tools/ui_r6_check.cjs`、四份台账｜分支 `arena/82e34fb8-nilm-calc-tool`｜live preview 8000 端口

---

## [2026-10-12] 会话纪要（第 6 条：第 7 轮三功能——曲线实时落盘 / 离线文件指定位置播放 / 曲线悬停取值）

- **任务**（用户 3 点）：① 计算的曲线数据实时保存到 `output/realtime` 目录下 CSV ② 离线文件可指定位置进行播放 ③ 鼠标移到曲线上显示该位置数据
- **角色 / 模式**：工程实现工程师（延续）／混合模式——沙盒侧 pytest + jsdom + CLI/源层实录 ✅；用户侧＝T-005 **U7 组 8 步** 🔶待回报
- **本轮产物**：
  1. 实时落盘：`elec_tool/realtime_writer.py`（每点追加＋flush、按数据日期分文件、续写不重表头、受 `curve_save` 过滤、`ELEC_TOOL_REALTIME_DIR` 优先）；`metrics.curve_record()` 抽成界面趋势/手工保存/实时落盘三出口共用；`output.realtime_save/realtime_dir`；引擎 `poll_once/flush_all` 后写、热更新重建 writer、`stop()` 关句柄；`GET /api/realtime`；导出页「实时落盘」面板；CLI `--realtime-save on|off --realtime-dir`＋收尾诊断
  2. 播放起点：`source.play_start_mode/play_start_value`（begin/row/seconds/percent/time，`parse_play_start` 保存时校验）；`iter_csv_blocks(skip_rows/start_percent/start_time/seek_info)`（percent 字节定位对齐行首；time 分块扫描时标列，只填 HH:MM:SS 与当天时刻比较）；`CsvFileSource` 换算/告警/`play_seek` 信息/超范围 `ParseError`；界面下拉框＋取值框联动、占位随模式变化、start 白名单放行、摘要显示；CLI `--play-from 模式:值`
  3. 悬停取值：`app.js` `nearestIdx/hoverInfo/drawHover/bindHover`，`drawLine` 挂 `cv.__chart`、绑定一次事件、重绘末尾叠加；趋势图 `fmtTip` 含毫秒、频谱 Hz、波形带单位
  4. 验证：`tests/test_r7_features.py` 18 项、`tools/ui_r7_check.cjs` PASS 39/0（3 次稳定）、旧 harness 30/0 与 74/0、全量 **204 passed, 1 skipped**
  5. 文档：README v0.6、REPORT_TEST v0.6（T-005）、REPORT v0.6（C-16/C-17＋1 条教训）、STATUS 第 7 次收尾
- **关键决策**：落盘默认开、目录可由 env 改写；三出口共用一份提取与勾选；按数据日期分文件；播放起点四种定位；悬停吸附最近点不插值
- **踩坑**：F-17 超范围静默 0 样本→可诊断错误；F-18 默认落盘污染仓库目录→env＋autouse 夹具；F-19 `finished` 置位≠`flush_all` 完成→等待对准最后副作用；F-20 常驻模拟器污染测试目录→脚本先 stop；F-21 begin 模式送空值违反载荷纪律→只在非 begin 送
- **未决问题**：U7 组待回报；落盘无轮转；percent 跳过行数未知；播放起点只对 csv_file；悬停不插值；此前 T-001~T-004 用户侧仍未回报
- **相关文件/分支**：`elec_tool/{realtime_writer,engine,metrics,config}.py`、`elec_tool/sources/{parsing,csv_file}.py`、`app/server.py`、`app/static/*`、`cli.py`、`tests/{conftest,test_r6_features,test_r7_features}.py`、`tools/{ui_r6_check,ui_r7_check}.cjs`、四份台账｜分支 `arena/82e34fb8-nilm-calc-tool`（`f0fdea6`/`341fc9e`/docs）｜live preview 8000 端口

- **[2026-10-12 补记] F-22 热修**（用户回报：127.0.0.1 正常，用局域网 IP 访问时每次刷新页面纵向拉伸）：根因 `app.js prep()` 每次重绘回读 `getAttribute('height')`，而 `cv.height = h*dpr` 会同步改写该属性 → `devicePixelRatio≠1` 时高度按 dpr 复利放大（沙盒复现 dpr=1.25：200→250→312→390→487）；两个地址表现不同是因为浏览器按主机名记忆缩放级别（或另一台机 Windows 125% 缩放）。修法：逻辑高度首次读取后缓存 `data-h`；回归 `test_canvas_prep_does_not_reread_scaled_height_attribute`；全量 205 passed、三套 jsdom 39/30/74 全绿；提交 `fc5c688`＋docs。本轮沙盒又被回收两次（venv/.git 丢、工作树在），均按 `fetch + reset --mixed FETCH_HEAD` 接回，零丢失。

- **[2026-10-12 补记] F-23 热修**（用户回报：离线文件播放时顶栏「样本」汇总不自动同步、需手动刷新）：根因 `app/server.py` `/ws` 循环只在 `q.get()` 超时 1s（队列空闲）才发 `state`，而 samples_in/数据时长/缓冲等只随 state 下发；离线全速播放 result 连续、永不空闲 → state 永不发。修法：单调时钟每 `WS_STATE_INTERVAL_S=1.0s` 必发 state。实测 3s 播放 result 26/state 4、samples_in 17280→32000；旧代码 state=0。回归 `test_ws_pushes_state_periodically_during_continuous_playback`；全量 206 passed、jsdom 39/30/74；提交 `e20869a`＋docs。沙盒本轮又回收一次，已接回。

- **[2026-10-12] 第 8 轮｜数据处理子界面——离线波形 CSV 重采样**：用户需求「对指定路径离线波形 CSV 按指定采样率重采样，保存到 data，文件名 原名+re+采样率」。实现 `elec_tool/resample.py`（numpy only；linear 流式分块 / nearest / fft 周期语义抗混叠；fs_src 时标线性拟合推算或手填；时间轴等间隔重建；时标按源写法重生成（epoch/整数毫秒/`0/00/00`/ISO）；表头/编码/BOM 保留；`.part` 原子写；进度/取消）、REST `POST/GET /api/process/resample` + `/cancel` + `/preview`（单任务后台线程）、CLI `resample`、前端「🧮 数据处理」视图（下拉选文件→探查→参数→进度条→结果→用作播放源）。验证：pytest 16 项、jsdom `ui_r8_check.cjs` 29/0、旧 harness 39/30/74 无回退、全量 **222 passed**；实录 3200→6400 linear 误差 0.12（理论上限）、fft 1e-6、6400→800 fft 滤除 1250 Hz。问题 F-24~F-28（fft 点数语义 / 1e12 epoch float 精度 / 伪 BOM / `.part` 残留 / 测试轮询竞争）均已修。台账：README v0.7、REPORT_TEST T-006（U8 组待回报）、REPORT C-18＋第 8 次判定、STATUS。提交 `a6fd42d`＋docs。遗留：等间隔假设会压掉源文件缺口；fft 整文件内存；单文件；不改 `sampling.fs`。

- **[2026-10-13] 第 9 轮｜间谐波 / 直流偏置 / 事件 三个子界面**：用户需求「1.间谐波电气量子界面 2.事件子界面（基波相量/谐波相量/间谐波相量/频率/频率变化率超限、功率振荡）3.直流偏置电气量」，跳过澄清 → 按推荐路线实现并在 README 标注假设与可配置项。角色＝工程实现工程师（任务级），模式＝混合。实现：`QUANTITY_KEYS` 7→9（`interharmonic` 0.2 s / `dc` 1 s）、`CURVE_KEYS` 6→8；`interharmonic_analysis`（IEC 61000-4-7 组/中心子组/主导相量/TIHD，175 Hz 注入对齐 1e-14）、`dc_analysis`（整周期均值）；新建 `elec_tool/events.py`（6 类事件状态机、滞回、CSV 落盘、`EventConfig` 全可配）；引擎/REST（`/api/events`、`/clear`）/WS（`type=event`）/前端三子界面+徽标+阈值表单。实跑发现并修 **F-29**（阈值未按 PT/CT 折算，样例一开机 6 条假基波超限 → `limits_secondary` 自动 ×PT/×CT 并回显有效阈值）、**F-30**（复归用事件旧阈值 + 频率相对滞回 50.5×0.95 永不复归 → 当前阈值 + 绝对带）。验证：`test_r9_events.py` 13 项、`ui_r9_check.cjs` 28/28、全量 **235 passed**、selftest 44/44、旧 harness 74/30/29 无回退、r7 38/39（1 项 jsdom 时序，改动前后一致，F-31 观察）。台账：README v0.8、REPORT_TEST T-007、REPORT C-19/C-20、STATUS。提交 `8539d8a` + docs。待用户 U9 组回报。
