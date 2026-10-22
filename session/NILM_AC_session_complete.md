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

- **[2026-10-13 补记] F-32 热修**（用户回报：启动事件检测且事件很多时，界面弹出告警过多）：`app/static/app.js onEventPush` 去掉逐条 toast，事件到达只更新导航徽标（活动数）并刷新「事件」页；加回归断言；沙盒再次重置后按 `git fetch + reset --mixed` 接回 `0ffc7e2`、重建 venv/样例/jsdom，`ui_r9_check` 28/28。

- **[2026-10-13] 第 10 轮｜离线文件列映射开关**：用户需求「增加是否启用离线文件数据映射关系配置功能：未启用默认依次为 时间,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流；启用则只播放有映射关系的列」。角色＝工程实现工程师（任务级），模式＝混合。沙盒开局再次被回收（第 5 次），`git fetch + reset --mixed FETCH_HEAD` 接回 `32a17a4`，重建 venv / 样例 / jsdom / 8000 预览。实现：`ColumnMap.mapping_enabled/mapping` + `layout()`（离线取列唯一规则，parsing / probe / CLI / 重采样预扫描共用）、未映射通道置 0 + note、时间戳未映射按 fs 合成跨块连续时间轴、`validate()` 四类报错；前端「数据源」页新面板 + 探查输出带列号与未映射提示。问题 F-33（合成时间轴每块从 0 起）、F-34（识别不出列名的表头当数据）、F-35（拼接 id 回归陷阱）。验证：`test_r10_colmap.py` 8 项、`ui_r10_check.cjs` 15/15、全量 **243 passed**。台账：README v0.9、REPORT_TEST T-008（U10 组待回报）、REPORT C-21 + 第 10 次判定、STATUS。假设已标注：未映射按 0 不剔除、表头优先兼容、对下次启动生效、TCP 不受影响。

- **[2026-10-13] 第 11 轮｜离线文件时标 UTC 开关**：用户需求「离线文件不启用自定义时间时，增加是否使用 UTC 时间配置；不使用 UTC 时曲线时间与文件时间一致」。根因：文本时标一律按 UTC 解析（`tz_offset_h=0`）而界面按本地显示 → 北京时间下 +8 h。沙盒开局第 6 次被回收，`git fetch + reset --mixed FETCH_HEAD` 接回 `3fe01f2`（本轮未提交改动保留在工作树），重建 venv / jsdom / 8000 预览（服务端以 `TZ=Asia/Shanghai` 起以复现偏差）。实现 `source.file_time_utc`（默认 false＝按本机本地时间解释）、`file_tz_offset_h()` 统一推导、无日期 `0/00/00` 写法与播放起点当天时刻同偏移、probe/start/CLI/界面透传。问题 F-36（无日期写法漏减偏移）、F-37（旧用例隐含沙盒＝UTC）。验证：`test_r11_file_time.py` 6 项、`ui_r11_check.cjs` 11/11、全量 **249 passed**（UTC + Asia/Shanghai）。台账：README v0.10、REPORT_TEST T-009（U11 组待回报）、REPORT C-22 + 第 11 次判定、STATUS。

- **[2026-10-13] 第 12 轮｜负荷辨识子界面（逐周波事件检测）**：用户需求 4 点（尽量多的检测算法实时检测窗口内周波数据 / 事件含时刻、方向、幅度 / 参数可配 / CSV 含算法类型、起止时间、方向、幅值）。沙盒开局第 7 次被回收，`fetch + reset --mixed` 接回 `ece4f1d`，重建 venv / jsdom / 8000 预览。实现 `elec_tool/nilm.py`：逐周波 P/Q/I（128 点、跨块结转、基波单频 DFT Q）→ 滚动窗 → 6 算法（阈值差分 / 双滑窗均值差 / CUSUM / GLR / 稳态分段 Hart / 中值滤波差分）→ 终点序号去重 + 确认周波 → 事件（算法、对象、起止、方向、ΔP/ΔQ/ΔI、前后稳态、检验量）→ CSV；`NilmConfig` 全参数 + 相对门槛；引擎/REST/WS/前端视图（周波窗曲线事件竖线、按算法生成参数表单）。发现并修 F-38（绝对 W 门槛在一次侧 MW 级失效、CUSUM 起点提前、噪声触发粘连 → 相对门槛 + 起点精修），F-39 偶发失败观察。验证：`test_r12_nilm.py` 8 项、`ui_r12_check.cjs` 16/16、全量 **257 passed**；样例 6 算法均在 2.000 s ↑750 kW / 4.400 s ↓450 kW 报出。台账：README v0.11、REPORT_TEST T-010（U12 待回报）、REPORT C-23 + 第 12 次判定（NILM 侧首次落地）、STATUS。

- **[2026-10-13 补记] F-40 热修**（用户 Windows 回报：离线文件自定义时间启动后 `GET /api/nilm/events` 500，`time.localtime` OSError 22）：根因＝v0.10 把无日期时标 `0/00/00` 按本地时间解释，基准 1970-01-01 减 8 h 成负 epoch；Linux 容忍、Windows CRT 拒绝，沙盒未暴露。修：`_NO_DATE_BASE`→86400（1970-01-02），新建 `elec_tool/timefmt.py`（`fmt_local/local_day/local_tod_s`，失败时 datetime 手工换算）替换 nilm/events/realtime_writer/server/cli/`_tod_of` 的全部 localtime 出口；`tests/test_f40_negative_epoch.py` 用 monkeypatch 模拟 Windows + 东八区复现；旧用例基准常量同步 +86400。全量 260 passed（UTC / Asia/Shanghai）。沙盒开局第 8 次回收，已按套路接回。教训：**跨平台的时间 API 要在"目标平台的失败模式"下测**，仅靠 Linux 全绿不够。

- **[2026-10-14] 调参手册**（用户：从调参运维人员角度详细说明各算法参数如何确定）：新建 `NILM_TUNING_GUIDE.md`（机制 4 条 → 先量 σ / Δ_min → 逐算法「作用 / 怎么定 / 现象→对策」→ 5 类现场套路 → 验证流程 → 对照表 → 调参解决不了的限制）；配套 `tools/nilm_tune.py`：读背景 CSV 走 CycleFeatures 算稳健 σ（差分 MAD/√2）、5/10 周波极差（min(p95, 2×中位数) 抗事件）、10 周波均值差 σ，按手册公式给 6 算法起点；`tests/test_nilm_tune_tool.py` 证明建议参数在同噪声下检出恰为最小负荷的 600 W 阶跃（6 算法、起点误差 ≤2 周波、幅值误差 <10%）且 3000 周波纯噪声 0 误报。沙盒开局第 9 次回收，接回。

- **[2026-10-14] 第 13 轮：离线文件暂停/恢复播放**（用户原话「在数据源为离线文件输入方式下，增加暂定(停)播放和恢复播放功能」）。实现：`EngineRunner` 增 `pause_event`（每轮运行新对象，与 stop_event 同生命周期）、`pause()/resume()/_pausable()`，线程循环在 set 时 sleep 0.05 不 poll；`stop()` 顺手 clear；`state()` 增 `paused/pausable/paused_total_s`；`duration_s` 扣除暂停时长；REST `POST /api/engine/pause|resume`（非 csv_file / 未运行 / 已播完 → 400）；前端顶栏「暂停/恢复」+ 数据源页「暂停播放/恢复播放」、pill「已暂停」(`.pill.warn`)。只做 csv_file：实时源暂停会丢数据或追赶突发，按设计拒绝并提示。测试 `tests/test_r13_pause.py` 3 项（用 monkeypatch 给 poll_once 加 15 ms 使回放慢到可暂停）；全量 265 passed。沙盒开局第 10 次回收，接回。

- **[2026-10-14] F-41**（用户：离线文件播放完界面运行状态不自动更新）：根因＝`_run` 在循环结束处广播 state，早于 `finally: engine.stop()`，终态推送仍是 running=True；沙盒里 WS 1 s 定时 state 掩盖了它（下一秒就对了），用户环境推送链路可能更脆弱。修三层：终态广播挪到 engine.stop() 后 + `_thread_done`；WS 定时 state 抗 state() 异常、state() 单项 `_safe`；前端 `startStateWatch` 2 s 校对。回归用例先在旧代码上确认失败再通过。教训：**"最后一条推送"要在所有状态落定之后发**，定时兜底不能替代正确的终态事件。

- **[2026-10-14] F-42**（用户：界面暂停播放没有生效）：先看服务端日志——用户的 `POST /api/engine/pause` 全是 400，不是前端没发请求。根因＝离线文件不限速（2.6× 实时），样例几秒播完，按钮亮着但服务端已「播放完毕」。修：`source.file_speed`（csv_file 倍速，相邻块间隔限速，恢复不追赶）、界面默认 1×、配置默认 0 兼容 CLI/测试；看门狗无条件校对；`/` 注入资源版本号 + no-cache 杜绝旧 app.js。`tools/ui_r13_check.cjs` 用 jsdom 走真实界面 12/12；全量 270。教训：**用户说"没生效"先查服务端日志的状态码**；"播放"类功能没有速率概念就谈不上暂停。

- **[2026-10-14] 第 14 轮：总线侧 + 分路侧设备双数据源**。设计取舍：不复制 30 多个端点，而是 `RUNNERS={bus,branch}` + contextvar `_SIDE` + `RUNNER` 属性代理 + 纯 ASGI 中间件把 `/api/branch/...`→`/api/...`、`/ws/branch`→`/ws`，既有端点代码零改动即服务两侧；前端同理只在 `api()` 入口加前缀、WS 路径按侧选择，所有子界面天然"按当前侧显示"。总线侧 `branch.enabled` 决定联动；分路侧是独立 AppConfig（`configs/branch_runtime.json`，输出 `output/branch/`）。联动点只在 start/stop/pause/resume 四个端点且仅 side==bus 时触发。测试 4 项 + jsdom 19 项 + 全量 274。沙盒开局未回收。教训：**横向复制功能时优先在"路由/上下文"层做乘法，不在"端点"层做加法。**
- **[2026-10-14] 第 14 轮补充**（用户重述需求并限定「离线文件输入方式下」）：分路侧面板改为固定 csv_file，补齐文件参数（探查 / 从 data/ 选择 / 倍速 / 自定义播放时间 / UTC / 块大小）；服务端联动条件加「两侧都是 csv_file」，否则 `branch.skipped/error` 带原因；ui_r14 23/23、全量 274。

- **[2026-10-14] 第 15 轮：导航按侧别三分组**（用户：1 总览＝总览面板+数据源与控制；2 总线侧＝总线侧电气量子界面；3 分路侧＝分路侧电气量子界面）。实现：`index.html` 导航项加 `data-side`，总线/分路两组各复制一套子界面入口（分路组徽标 id 加 `-br` 后缀避免重复 id，并多一项「分路侧数据源与口径」给 fs/PT-CT 配置留入口）；`switchView(v, side)` 先静默 `setSide` 再切页，高亮按 view+side 匹配；删除顶栏 `.sideswitch`（避免两个真相源）与 localStorage 侧别记忆（刷新回到总览＝总线侧）；总览面板新增 `#ov-sides` 两侧状态卡、分路组标题 `#nav-br-state` 徽标。验证：ui_r14 27/27、ui_r12/ui_r13 通过、全量 274。踩坑：批量替换脚本里 `sub()` 已落盘后又用早先读入的旧串整体回写，把 app.js 清空——**同一文件只保留一个写入点**，改完立即 `git diff --stat` 看行数。

- **[2026-10-14] 第 15 轮补充**（用户 5 条：①分路侧配置集中到总览数据源页；②徽标对侧也要刷新；③两侧时间轴对齐、跨侧差值；④顶栏不显示分路侧状态；⑤两侧量纲口径分别配置保存）。实现：`_side_summary(side)` 通用化并挂到对侧 state（`branch`/`bus`，加 `events_active`），前端 `renderBadges` 同时刷两侧徽标、顶栏 `#st-branch` 变成「对侧胶囊」常显（④的根因：旧实现在分路侧把胶囊隐藏了，且分路侧 state 无总线摘要）；分路面板新增量纲口径 10 个字段与对齐 2 个字段，一次保存分别 PUT `/api/config`（branch.enabled/time_offset_s/align_tol_s）与 `/api/branch/config`（source+transform+sampling+harmonic+power）；`BranchConfig` 加 `time_offset_s/align_tol_s`；`_align_rows` 最近邻配对（排序+searchsorted，一对一），差值＝总线−分路、占比＝分路/总线；「跨侧对比」页。验证：ui_r14 36/36、ui_r12/13 通过、全量 275（`test_r7` 的 fmtTip 计数 9→11）。事实：仓库两份样例起点差 93171.9 s，默认偏移 0 对不上，「按起点对齐」后 5 对——这正是偏移参数存在的理由，已写进检查脚本。

- **[2026-10-14] v0.14.2**（用户：列映射分总线侧/分路侧独立配置）：列映射表单函数改为按侧前缀寻址（`MAP_UI` 表：`cfg-map-*` / `br-map-*`），`fillColumnsForm/collectColumnsPayload/fillColmapDefault/fillColmapFromProbe/saveColumns(side)`；分路侧探查结果存 `BR.lastProbe` 供「按分路侧表头填入」；分路侧列映射既可单独保存也随分路侧配置整体保存。ui_r14 37/37；`test_r10_colmap` 的正则断言随实现改（`cfg.columns.mapping_enabled` 字面不再出现）。

- **[2026-10-14] v0.14.3**（用户：总览增加分路侧数据与曲线）：`OVB` 缓存 + `refreshOverviewBranch()`（总览页、总线侧上下文下直接 fetch `/api/branch/result` 与 4 条 `/api/branch/history`，2 s 节流，随 WS state 触发）+ `renderOverviewBranch()`（卡片复用总线侧卡片逻辑 + P 差值/占比最新值 + 4 图）。`test_r7` 的 fmtTip 计数 11→15。

- **[2026-10-14] v0.14.4**（用户：顶栏按总线侧/分路侧分开显示，分路侧只显示不切换）：`renderTop` 改为先构造 cur/peer 两份字段对象再按 `S.side` 分配到 `st-*`（总线行）/`st-br-*`（分路行）；服务端对侧摘要补 fs/PT/CT/频率/数据时刻/时长；删除可点击的 `renderBranchChip`。切侧入口只剩左侧导航。

- **[2026-10-15] v0.15**（用户 5 条：增量刷新 / 倍速一致 / 总览合并 / 公共时间段 / 自定义起始）。沙盒重置后按既定流程恢复（fetch+reset、venv、样例、jsdom）。关键实现与坑：①增量刷新用 `Element.prototype.innerHTML` / `Node.prototype.textContent` setter 包装做「同串跳过」，副作用＝手动 appendChild 过的元素要 `domTouched()`；画布 `chartSig` 跳过重绘，`__redraw` 必须 `force`。②公共时间段的两处坑：**custom_time 时间轴原来按"播放的第 1 块"起算**，跳行后整条轴左移 → 改为配置起始时间时计入 `skipped_rows`；**联动自动写入的 play_start/play_end 会残留在 RUNNER.cfg**，下次普通启动秒播完 → `_AUTO_PLAY/_ORIG_PLAY` 记录并在下次启动还原（失败的启动不弹出条目）。③仓库两份样例时间不重叠：检查脚本给分路侧设自定义时间轴（总线起点+1 s）后公共段 ≈4.28 s（起始文本按秒取整）。全量 pytest 中 `test_tcp_binary_frames` 偶发失败、单测 3/3 通过、stash 后同样，判定为既有偶发。

- **[2026-10-15] v0.15.1**（用户 3 条：公共时间段下曲线只留公共段、坐标轴同步 / 两侧播放速率严格同步且按各自采样率 / 长度不一致时先播完的停刷、另一侧继续）。沙盒再次重置，按套路接回 `30f1d2c`。设计：把"相邻块间隔限速"换成 `PaceClock` 绝对节拍（误差不累积）+ 两侧互锁（块**起点**领先对侧进度 >0.1 s 才等；用起点而非终点判断，第一块永远放行、A/B 不可能互等 → 无死锁）；先播完一侧 `finish()` 释放对侧。调试中踩到的四个"旧"问题全是被同步暴露出来的：①互锁第一版用块终点判断 + 分路侧残留 fs=3200 配置 → 0.2>0.2 浮点相等直接死锁；②按时标/行定位后 `buf` 里残留 8192 行被当成一块（首块 0.3～2.5 s），节拍和同步都被它打乱 → 定位后先按块大小切；③`_run` 在"读到块但无量到期"时也睡 0.2 s，两侧吞吐 <1× 实时、UI 轮询下 0.13× → 只在没读到数据时才睡；④两侧严格同步后**同时**播完、同时广播终态，`state()` 持自己的锁取对侧摘要 → AB/BA 死锁整个服务挂起（py-spy 抓到两条 elec-engine 线程互等）→ 对侧摘要改在持锁前取。另：`/api/branch/result?full=false` 只给最近一次发射（常常只有基波/谐波三项），总览分路卡片闪「—」→ 服务端维护各量并集 `latest_merged`。验证：`test_pace_clock.py` 3 项、`test_r15_1_pace_sync_and_merged_result`（两侧 wall0 相同、进度差 ≤0.25 s、短侧播完长侧播完整、full=false 含电压/功率）、ui_r14 55/55 连跑两次、全量 279。教训：**"同步"会把所有靠时间差掩盖的竞态一次性翻出来**——加互锁前先想清楚谁等谁、谁来解锁、第一步能不能走；跨对象取状态的函数不要在持自己锁时去拿别人的锁。ui_r14 的 L2 倍速从 1× 改 0.5×（节拍变准后 5 s 文件会在检查途中播完），不是放宽断言。

- **[2026-10-15] v0.15.2**（用户：总览面板的总线侧曲线和分路侧曲线分开展示，不在同一坐标轴下）。沙盒又一次重置（第 N 次），`fetch + reset --mixed` 接回 `b4325eb`，重建 venv / jsdom / 样例。实现：`index.html` 总览曲线区改为 4 行 × 2 列（左总线 `ov-*`、右分路 `ov-*-br`），分路列 `.ov-br-panel` 在未启用时由 `.ov-curves.no-branch` 隐藏；`renderOverview` 删除 `brSeries/ovBranchX` 叠加逻辑，分路侧四图用自己的 `tref/span`。样例重新生成后秒内相位变了（t_first 小数 .94 而非 .28），ui_r14 L6 的「公共段≈4 s」硬编码区间失效 → 改为按 probe 现算期望值（总线终点 − floor(总线起点+1)）。ui_r14 56/56、全量 280。

- **[2026-10-15] v0.15.3**（用户：检查为什么离线文件启动后要过很久才开始）。沙盒再次重置，接回 `94bd657`。排查：服务端在样例与 5 分钟大文件上启动→首块 0.1 s、首结果 0.3 s，正常；按时标定位 +200 s 需 2.3 s（逐行扫）。复现泄漏链：联动公共时间段启动后 `GET /api/config` 的 source 已是 `time/1792044861.0/1792044865.41`（`cfg` 属性直接返回引擎配置），再 PUT 任意字段即被持久化；v0.15 的 `_AUTO_PLAY/_ORIG_PLAY` 还原表只在内存，服务重启即失效 → 之后每次启动都按陈旧时标扫文件（新文件时标更早则扫到 EOF 才报错，这就是「很久才开始」）。修：自动起止只进引擎（`Runner.start(play_user=)` + `cfg` 视图 + `set_cfg` 不回写）、`play_end_time` 不落盘、`_sanitize_leaked_play` 启动清理、`_file_time_range` 字节计行+头尾取样。删除 `_AUTO_PLAY/_ORIG_PLAY/_restore_auto_play`。教训：**"运行期派生值"与"用户配置"必须是两个对象**，靠"记住再还原"的内存表在重启面前一定失效；凡是能被持久化的字段都要问一句"用户填得出来吗"。

- **[2026-10-15] v0.15.4**（用户：「需要优化」，承接 v0.15.3 交付末尾「按时标定位为顺序扫描、未做二分」的缺口）。角色：工程实现工程师（混合模式）。改动集中在 `elec_tool/sources/parsing.py`：新增 `_ts_values`（abs→epoch、tod→当天秒的统一比较值，`_seek_time` 同步改用）、`SEEK_FAST_MIN_BYTES=4 MB`、`_line_starts_after`、`_byte_offset_of_row`（8 MB 块计换行）、`_count_newlines`、`_bisect_time`（字节二分，每次探测只读一行；解析失败/非单调返回 None 回退顺序扫）；`iter_csv_blocks` 增 `_rewrap(byte_pos)` 从任意行首重建 csv reader，`seek_info["method"]` 标识 `time(bisect)`/`time`/`row(bytes)`/`row`。实测 /tmp/big.csv（300 s、1.92M 行、157 MB）：time 3.44→0.125 s、row 1.79→0.108 s、seconds 1.93→0.107 s、tod 7.39→0.158 s、越界 4.7→0.153 s，`t_start`/`skipped_rows` 与顺序扫逐项一致。**假设**：无带引号换行字段；按行快速路径把空行也计入 skipped_rows；<4 MB 或无表头文件走旧顺序路径；percent 模式未改。测试：新增 `tests/test_r15_4_fast_seek.py`（2 用例，首版因 `row 1` 不产生 seek_info 取 `None[...]` 报 TypeError，改为断言 `row 2`），`test_r7_features` 断言补 `method`；全量 283 passed/1 skipped；预览重启后 ui_r14 56/56。

- **[2026-10-15] v0.16**（用户 6 条：①数据源与控制页左总线/右分路；②仅启用分路侧时显示分路列；③分路侧 4 种输入方式功能同总线侧；④同类配置左右同行；⑤多曲线图各线可选显示并可保存；⑥总览分路侧曲线状态栏同总线侧）。角色：工程实现工程师（混合模式）。改动：`app/static/index.html` 重写 `#view-source`（顶部「分路侧设备联动」面板 + `#srcgrid` 4×2，`.col-bus/.col-br`，`br-*` 字段与 `src-*` 一一对应，新增 `btn-br-start/pause/stop`、`br-state`）；总览分路侧 4 张曲线标题栏加 `curve-save[data-side=branch]` 与 `curvespan[data-side=branch]`；`style.css` 加 `.srcgrid`/`.serlegend`；`app.js`：`fillSourceFields/syncSourceFields/collectSourceFields(pre)` 前缀参数化（修复旧版播放起点只在 csv_tail 分支发送的 bug）、`syncBranchColumns`、分路侧状态栏 `sourceSummaryLines` 共用、`startBranchAlone/stopBranchAlone/toggleBranchPause`、`seriesHiddenSet/renderSeriesLegend/setSeriesVisible`（drawLine 过滤隐藏线，PUT `output.series_hidden`）、`curveSaveMap/setCurveSave(side)`、`OVB.meta`；`elec_tool/config.py` `OutputConfig.series_hidden`（校验清理空项）；`app/server.py` `_start_branch_if_enabled` 允许任意输入方式（两侧 csv_file 才共用节拍钟/公共时间段，返回 `synced_pace`），`engine_start` 公共时间段不适用时不报错、返回 `common_window.reason`。测试：`tests/test_r14_branch.py` 按新语义改 3 处（混合组合同时启动、分路文件不存在→异步 error）；`test_r6/r7/r9/r11/r13b` 5 处字符串断言随前缀参数化更新；新增 `tests/test_r16_layout_series.py`（结构 + series_hidden 校验/深合并/落盘/两侧独立）与 `tools/ui_r16_check.cjs`（31 项，含重开页面仍隐藏、分路侧 tcp/csv_tail/csv_file+播放起点保存、分路模拟器与总线离线文件同启、单独启停）。`ui_r14_check` 改 3 项（`br-kind` 需显式选 csv_file——出厂占位是 simulator；模拟器总线也带起分路）→ 56/56。全量 pytest 288 passed/1 skipped。既有现象：`ui_r7/ui_r11` 各 1–2 项时区断言在 UTC 沙盒失败（需 `TZ=Asia/Shanghai`），`ui_r10` 紧跟 `ui_r7` 运行受残留配置影响、单独运行 15/15。

- **[2026-10-15] v0.17**（用户 3 条：①离线播放两侧各自可指定时间段，默认不启用，公共时间段启用时可指定公共时间段的起止，起/止留空＝数据起点/终点；②所有曲线 X/Y 分别缩放 + 拖选区间只显示该区间；③所有保存的 CSV 加数据来源号 0 总线/1 分路，启用分路时保存 CSV 同时保存分路数据）。角色：工程实现工程师（混合模式）。实现：`SourceConfig.play_window(_start/_end)`（validate 用 `parse_play_start('time')` 支持 HH:MM:SS）、`BranchConfig.common_end`、`OutputConfig.source_id`；`csv_file.py` 终点支持 tod 写法（第 1 块到达后按 `_tod_of` 折算）；`server.py` `_apply_play_window(cfg)` 在 `engine_start` 两侧与 `_start_branch_if_enabled` 的非公共分支调用，仍走 `play_user` 保护；`_compute_common_window` 加 `play_end/play_end_source`，`_apply_window_to_source` 终点改用 `play_end`；`SIDE_SOURCE_ID` 在 `set_cfg/start` 强制；`_curve_rows(side=)`、`_curve_csv(source_id)`、`/api/curves/save` 分路 `branch/` 子目录、合并下载/导出加列；`realtime_writer` 3 列固定头 + legacy 兼容；events/nilm `_CSV_FIELDS` 首列 `source_id`。前端 `ZOOM` 状态 + `zoomAxis/zoomReset/renderZoomBar`，`bindHover` 增 wheel（passive:false）/mousedown/mouseup/dblclick，`drawLine` 在计算全图范围后套用缩放、只在画折线时 clip，`cv.__chart` 增 `xfull/yfull/xAt/yAt/zoom`；两列各加 `*-window/*-winstart/*-winend`，联动面板 `br-common-end`。踩坑：① jsdom 里悬停最近点可能落在缩放视窗外（样本稀疏时属正常行为，断言改为「有最近点信息」）；② `ui_r14` 对服务端残留状态敏感（前一脚本留下 kind=simulator）且 node 侧也要 `TZ=Asia/Shanghai`（本地时间文本由 node 生成），干净重启后 56/56；③ conftest 的 `ELEC_TOOL_REALTIME_DIR` 会把两侧落盘指到同一目录，两侧 source_id 测试需 pop 该环境变量；④ `/api/curves/save` 的 `dir` 为相对路径时相对仓库根而非 cwd。全量 296 passed/1 skipped。

- **[2026-10-15] v0.17.1**（用户：保存数据时分路侧与总线侧保存在同一个 CSV，不另建目录/文件）。`/api/curves/save` 合并写法：行级 `_sid` 标记 → `_curve_csv` 按行写 `source_id`，按 t 稳定排序；删除 `branch/` 子目录与 `branch_files`，返回 `rows_bus/rows_branch/source_ids/branch_quantities`。test_r17/ui_r17 随之改断言；全量 296 passed。实时落盘未合并（两侧独立引擎各自目录），已在 README 标注。

- **[2026-10-15] v0.17.2**（用户：播放分路侧 CSV 仍创建 branch 目录；要求所有保存文件两侧共用、只按 source_id 区分）。教训：上一轮只盯住自己新加的「保存曲线」链路，漏了既有的三条落盘链路——「不新建目录」应按**所有写文件的出口**逐一核对。实现：`_share_output_dirs` 强制分路侧四个目录＝总线侧、总线 set_cfg 后联动刷新分路；`filelock.SHARED_FILE_LOCK` 包住三个 writer 的 open/append；`configs/branch.json` 出厂目录改 `output/*`。全量 296 passed。

- **[2026-10-15] v0.17.3**（用户：配置界面 ①勾选框与标签对齐 ②说明文字与配置项区分、缩进换行合理 ③左标签+右输入框成对）。先用 jsdom 统计 145 个 label 的结构（T+input 82、input+T 勾选 29…）发现根因：`.chk` 在 CSS 里根本没有规则（继承 `.form label` 的 column 布局，勾选框和文字上下错开），说明文字全写在 label 文本里。选择「JS 规范化 + CSS」而非手改 100 多个 label：`normalizeConfigForms()` 拆 scope/标题/说明并套 `.f`/`.chk` 结构。踩坑：`test_web_ui` 的「app.js 引用的 id 必须存在」正则会把注释里的 `$('#id')` 字样当引用 → 注释改措辞。无浏览器截图，视觉按 CSS 推断，已在 README 标注请用户核对。

- **[2026-10-15] v0.18**（用户：「界面上的各曲线在没有播放情况下支持直接加载上次播放的数据源计算的电气量数据或事件的数据」）。方案：不新增落盘，直接从三条已有落盘链路的 CSV 读回（`elec_tool/replay_load.py`），按本侧 source_id 过滤，两侧共用文件不变；`POST /api/history/load_last`（运行中 409，总线侧联动分路侧）；顶栏/数据源页「加载上次数据」按钮，播放中置灰；成功后刷新曲线/事件/负荷辨识页并在数据源页显示提示。验证：`tests/test_r18_load_last.py` 4 项（纯函数去重/合并/旧文件、加载器、两侧 Web 端到端含 409、前端契约）；全量 pytest 299 passed 1 skipped；ui_r16 31/31、ui_r17 36/36；jsdom 实点按钮：POST 200、toast、曲线/事件进内存、提示显示。缺口：沙盒无浏览器截图；事件时间窗按曲线最新点推算，若上次只播了事件没有曲线则不按时间过滤（受 max_log 限制）。

- **[2026-10-15] v0.19**（用户：总览 P/Q/S 趋势曲线增加 3 相 P/Q/S 趋势曲线，默认显示 3 相总 P/Q/S）。改动：metrics power 趋势记录追加 Pa/Pb/Pc/Qa/Qb/Qc/Sa/Sb/Sc；app.js `pqsSeries()` 组 12 条曲线、`defaultHidden` 机制 + `*none*` 哨兵；两侧总览 P/Q/S 图共用。验证：jsdom 实测图例 P✓Q✓S✓ 其余 ✗、12 条曲线均有数据、勾选 Pa 后 PUT series_hidden 为其余 8 条、全部勾选后为 `*none*`；全量 pytest 301 passed 1 skipped；ui_r16 31/31、ui_r17 36/36。缺口：当天已有 power CSV 表头不含分相列（续写不写分相）；功率子界面趋势未改（用户只要求总览）。

- **[2026-10-15] v0.20**（用户：软件重启后各子界面展示的数据从上次运行保存的 CSV 或配置文件加载显示）。设计：曲线/事件/负荷辨识事件复用 v0.18 CSV 读回；「最新电气量」此前无落盘 → 新增 `output/last_result.json`（两侧共用、按 source_id 分键，运行中节流 5 s + 终态写入，原子替换）；启动时 `_autoload_last()`；`output.autoload_last` 默认开。验证：`test_r20_restart_autoload`（两侧播→停→JSON 两键→模拟重启自动恢复→关闭开关不加载）；全量 pytest 302 passed 1 skipped；ui_r16 31/31、ui_r17 36/36；jsdom 冷启动：state.loaded_last.auto=true、result 9 个量、电压/电流/功率/谐波/事件各子页有数值、数据源页提示与勾选框正确。缺口：快照文件约 1.3 MB（含频谱 series），每 5 s 重写一次，HDD 环境可调；波形类面板（原始采样）不在恢复范围；沙盒无浏览器截图。

- **[2026-10-15] v0.20.1**（用户：检查总览三相无功、视在功率曲线为散点显示的原因）。分析：数据连续（history/power 分相字段无 None）；绘图 `drawLine` 对非数值断线、数值连续时连线正常；真正原因是 v0.19 分相线样式——Q 虚线 [5,3]、S 虚线 [2,2]、线宽 1.1，三相重合 + 高密度点 → 视觉上为散点。修复为实线 + 基色明暗分相。验证：JS 语法、test_r19 字符串断言更新、ui_r16/r17 通过。

- **[2026-10-15] v0.21（重做）**（用户纠正：「总线侧与分路侧增加导出指定时间段的原始周波数据」＝从离线文件模式指定的 CSV 中把指定时间段的数据重新导出为新 CSV）。处置：`git revert 5a3188d` 撤回基于 NILM 周波保留区的首版（API `/api/nilm/cycles/*`、负荷辨识页面板、test_r21_cycles_export 全部移除）；重做为 `parsing.iter_csv_blocks(keep_rows)` + `elec_tool/raw_export.py`（复用 CsvFileSource，时间口径＝播放时间轴；起点用 play_start time 定位，起点超文件尾 → 0 行）+ `/api/source/raw_range`、`/api/source/export_range`（分路前缀路由镜像）+ 数据源页全宽面板。两侧行写**同一个**文件、原始行原样 + 尾列 `source_id`，可直接回放。时间输入支持只写 `HH:MM:SS.ffff`（与文件时标写法一致，按文件首行日期补齐）。验证：test_r21_raw_export 4 项；全量 pytest 306 passed / 1 skipped；ui_r12 16/16、ui_r16 31/31（脚本放行 `col-full` 面板）、ui_r17 36/36；预览实测导出 0.5 s → 3200 行。缺口：custom_time 下顺序全扫；分路侧表头不同只保 7 列；不换算变比。

- **[2026-10-15] v0.21.1**（用户：总线侧和分路侧的原始数据导出要独立、无关联）。改动：服务端只取当前侧（去掉 with_branch 联动）、默认名加 `_src<sid>`；界面拆成左右两列各一个面板（分路侧 id 前缀 `br-`），显式用 `/api/source` 与 `/api/branch/source` 前缀。沙盒曾被重置（venv / 样例 / jsdom 丢失、git HEAD 退回基线），已按恢复套路重建并 `reset --mixed FETCH_HEAD`。验证：test_r21 4 项（含分路侧段外 409 证明无关联）、test_r16 网格 5×2、全量 306 passed / 1 skipped、ui_r12/r16/r17 全过、预览实测两侧各自导出。

- **[2026-10-15] v0.22**（用户：根据已有总线侧数据 + 设备侧带启停周波数据，详细说明如何配置各事件检测算法参数并重写 NILM_TUNING_GUIDE.md，面向完全不懂算法的现场人员，只需复制 PowerShell / Excel 开 CSV / 看懂开关）。分析：原手册以参数解释为主，缺「可执行的闭环」——缺离线回放命令（检测只在 Web 引擎里跑）与「和真实开关对账」的工具，非专业人员无法判断能否上线。实现：手册重写为 7 步 + 打勾清单；新增 `nilm_replay.py` 与 `nilm_check.py` 两脚本补齐闭环（tune→replay→check→set→save-config→Invoke-RestMethod PUT）。沙盒再次被重置（第 2 次），恢复同前。验证：test_nilm_replay_check 5 项、全量 311 passed / 1 skipped、附录 C 样例流程实跑（默认参数 two_window 误报尖峰 1 条 → 建议参数 6 种全 ✅）。缺口：PowerShell 未在 Windows 实测；对账不校验幅值。

- **[2026-10-15] v0.22.1**（用户：总线数据里还有其它设备启停时手册是否适用 → 「需要」按方案改）。分析：检测≠归属是根因（见 README 条目）。实现 nilm_check 幅值带归属 + 指纹自取 + `其它` 真值、`--bus` 混合样例、手册 9 处修改（路线 A/B、§5-B、§6/§8 拆带内误报）。沙盒第 3 次被重置，恢复同前。验证：混合总线样例不带指纹无一 ✅（复现用户担心的情形）→ 带指纹 6 种 ✅；全量 312 passed / 1 skipped。缺口：归属只看幅值带；线上不归属。

- **[2026-10-15] v0.22.2**（用户：保存负荷辨识参数时报错 nilm.min_delta_pct 必须在 0~100）。复现：`suggest(measure(100 W 基荷), min_load_w=5000)` → min_delta_pct=2502.82。修复 nilm_tune 夹值置 0 + 前端预校验 + 服务端文案；手册 §3 流程不变（tune.json 直接可用）。验证：新增用例、全量 312 passed、ui 三套通过。

- **[2026-10-16] v0.23**（用户：分路侧与总线侧的电气量子界面合并，左总线/右分路，未启用分路侧则隐藏分路侧内容；未指定模式 → 混合模式、角色工程实现工程师）。探查：9 个电气量 render 函数全部直接 `$('#id')` + `S.result/S.state/S.histCache`，分路侧原靠 `setSide()` 整页切换。方案：不复制 render 代码，改为「上下文化」——`$()`、`q()`、`curHist()`、`curState()`、`radioVal()` 按 `RC.side` 取元素/数据，`renderDual(fn)` 跑两遍；右列 DOM 由 `buildDualViews()` 克隆并给 id 加 `-br`；分路数据 `BRD` 走 `/api/branch/*` 轮询。导航从 2×13 改为 9+4+4。踩坑：jsdom 不加载外链 CSS，`getComputedStyle` 判可见性无效 → 检查脚本改为「类名 + style.css 规则」双断言；`test_web_ui` 的 id 引用正则把注释里的 `$('#id')` 和 `getElementById('view-' + v)` 当成 id → 改写代码避免误报而非放宽测试。验证：ui_r23 26/26、ui_r12/16/17 全过、pytest 313 passed / 1 skipped。缺口：右列图例隐藏写总线侧配置；右列 1 s 轮询非 WS；events/nilm/windows/export 仍按侧分组；真实浏览器排版未实测。

- **[2026-10-16] v0.24**（用户：①分路侧事件/负荷辨识/窗口/导出也与总线侧合并、左总线右分路、未启用隐藏；②负荷辨识页加与总览一致的 P/Q/S 趋势，各算法事件标到曲线上，可选只标注某些算法，默认全部）。探查：这 4 页与电气量页不同——有按钮/表单/异步请求，且 `api()` 只看 `S.side`；异步函数 `await` 之后 `RC.side` 已复位，不能再依赖 `$()`。方案：`sideOf()`＋`E(side,id)`＋`api(path,opt,side)`，所有异步函数带 `side` 入参并在闭包里固定；状态拆成 `SD.bus/SD.branch`；`bindSideViews(side)` 两列各绑一份；负荷辨识动态表单先 `buildNilmForm('bus')` 再克隆。P/Q/S 图复用 `pqsSeries()` 与 `drawLine` 的 `marks`，新增 `renderNilmPqs()`。踩坑：`setEventBadge` 用 `className=` 覆盖掉了新加的 `badge-br` 类 → 改 `classList.toggle`。验证：ui_r24 34/34、ui_r12/16/17/23 全过、pytest 313 passed / 1 skipped。缺口：右列事件轮询非 WS；双列下宽表横向滚动；真实浏览器排版未实测。

- **[2026-10-16] v0.25**（用户：按现有功能重整软件标题与导航/子界面标题；列表单位放表头、数据不带单位）。沙盒两次重置（.venv/data/tools 丢失、git HEAD 回退），均按「fetch 远端 tip → reset → 保留工作区改动 → 重建 venv/jsdom/样例」恢复。方案：`unitScale()` 整列选一个 SI 前缀（避免同列 kV/V 混排），表头 `名称 (单位)`；多单位混杂的表（电能质量事件、跨侧对比、频谱信息）用独立「单位」列；负荷辨识 |ΔP| 与事件前后 P 各自选前缀（小事件叠在大基荷上不至于显示 0.000）。验证：ui_r25 23/23（43 个表）、ui_r12/16/17/23/24 全过、pytest 313 passed。缺口：README 界面导览表文案未同步；卡片仍带单位（非列表）。

- **[2026-10-16] v0.26**（用户：导航按四组重排——总览 / 实时监测 / 事件与分析 / 工具，并给定每组条目名）。纯文案与分组改动，功能代码不动；`ui_r25` 改为按组解析 data-view 顺序比对。全部检查与 pytest 通过。

- **[2026-10-16] v0.26.1**（用户：导航三组标题去说明；算法卡片勾选框离色块太远；勾选标题与说明换行）。根因：`h3.curvehdr>span:first-child{flex:1}` 把色块撑开。改为 `h3.algohdr>label.check`（勾选框+色块+名）+ 独立 `.algodesc` 行。ui_r24 36/36、r25 23/23、r12 16/16、pytest 313 passed。

- **[2026-10-16] v0.26.2**（用户：事件落盘卡片长路径溢出 → 换行）。`writerSub()` + `.card .s .path{display:block}` + `overflow-wrap:anywhere`。ui_r24 37/37。

- **[2026-10-16] v0.27**（用户：①功率/功率因数/基波/谐波/间谐波/直流偏置 增加三相分相实时数据保存；②功率与功率因数支持分相曲线、曲线可选）。`_EXTRACTORS` 追加 PFa/b/c、U1a/b/c、I1a/b/c、phiB/phiC、THD_Ua..Ic、TIHD_Ua..Ic、Ua_dc_pct..Ic_dc_pct（历史/实时落盘/保存曲线三处共用，两侧同文件按 source_id 区分）；实时落盘旧表头文件轮转为 `.pre-v027.csv`；功率页新增 `#p-trend`（复用 `pqsSeries`，分相默认隐藏图例勾选）、`#pf-trend` 加 PFa/b/c；新增 `tests/test_r27_phase_curves.py`，ui_r24 44/44，全量 pytest 316 passed。角色：工程实现工程师（混合模式）。

- **[2026-10-16] v0.28**（用户修正：谐波/间谐波/直流/基波增加分相趋势线；功率页是分相瞬时功率波形而非趋势线；总览卡片重排为 U/I/P/Q/S/PF/f/THD_U/THD_I 九张、行格式「总线数据 / 分路数据」、U/I 分三相、P/Q/S/PF 分三相+总）。`metrics.py` 放行 `series.p_per_phase`；`#p-trend` 删除 → `#p-wave-ph`；新增 `#h-trend`、`#f-u1-trend`、`#f-i1-trend`；`#ih-trend` 加 6 条分相；总览 `mcard/row` 多行卡片 + `.card.ovc` 样式。ui_r24 53/53、全量 pytest 317 passed；ui_r14 首项为 v0.26 起的历史失败。

- **[2026-10-16] v0.29**（用户：曲线放大后可上下/左右移动坐标轴）。缩放模块加 `zoomPan/zoomPanFrac`：放大后左键拖动＝平移（Ctrl+拖选才框选）、工具条 ◀▶▲▼、方向键、Alt+滚轮；边界夹全图、倍率不变。ui_r17 +11 项 47/47，全量 pytest 317 passed。沙箱重置一次已恢复。

- **[2026-10-16] v0.30**（用户：检查重启后负荷辨识加载的上次数据含曲线事件是否正常）。复现缺陷：先播今天时标样例再播 10-13 的 nilm_steps，重启后负荷事件 0 条——load_last 以目录最新时标为窗终点。修复：以 last_result.json `t_ref` 为锚点取 [t_ref−hours, t_ref]（曲线/事件/负荷事件统一，`t_anchor`/`t_to`）。真实重启核查 13/13 事件、13 条竖线、曲线范围正确；周波窗不恢复改为明确提示。ui_r30 11/11 + RESTART_ONLY 6/6，test_r18 +1，pytest 318 passed。

- **[2026-10-16] v0.31**（用户：放大状态下无法通过拖动坐标轴区域缩放、只能平移）。轴带识别 `axisZone()`：左 Y 带 / 底 X 带拖动＝该轴拖选缩放（任何状态），竖带/横带高亮，↔/↕ 光标；绘图区内仍平移 / Ctrl 框选。ui_r17 +7 项 54/54。

- **[2026-10-16] v0.32**（用户：再查重启后 P/Q/S 趋势是否标注上次运行所有事件）。复现：同时段两次播放 → 重启后 37 条（混入 7 条）。修复 run_id（引擎启动墙钟 ms）写三类 CSV 末列 + last_result，加载按 run_id 过滤、旧文件退回时间窗；旧表头轮转 .pre-v032。真实重启 13/13、竖线 13。pytest 320 passed。

- **[2026-10-16] v0.33**（用户：增加「是否隐藏分路侧数据」配置，为真隐藏实时监测 / 事件与分析右侧分路内容）。`BranchConfig.hide_ui` + state 下发；`branchDualActive()` 判 hide_ui → 四双列页 `.no-branch`、导航徽标隐藏；数据源页 `#br-hide-ui` 勾选即时 PUT 生效。仍计算落盘；总览/跨侧对比不受影响。ui_r24 +11 项 64/64，test_config +1，pytest 321 passed。

- **[2026-10-16] v0.34**（用户：数据处理重采样增加计算重采样前后相对误差并保存 CSV，时间窗可配）。配置段 `processing.error_window_s`（默认 1 s）/`error_report`；`resample.error_report()` 流式切窗、逐窗逐通道 RMS 相对误差 + NRMSE → `<输出名>_err.csv`（末行汇总）；界面勾选 + 窗长输入即时保存配置、结果显示误差表；CLI `--err-window/--no-err`。ui_r8 +11 项 40/40，test_r8 +4，pytest 325 passed。

- **[2026-10-16] v0.35**（用户：输出已存在且要算误差则跳过重采样只算误差；进度与结果分两步显示）。`error_only_if_exists`（未勾选覆盖时生效，覆盖仍重做，不算误差仍报错）；ResampleJob step/steps/step_status/overall，状态接口与结果 `steps`/`resample_skipped`；界面两步骤卡（#rs-bar/#rs-bar2、#rs-result/#rs-result2、标签）；CLI 分两步输出。ui_r8 47/47，pytest 326 passed。

- **[2026-10-16] 分析**（用户：负荷辨识几种算法能否单独用某一相电压/电流检测；再问只有三相电流时）。结论：算法层六种都只看一维序列、均可；电压不适合做负荷事件依据；当前实现硬编码有功 P，无电压时 P≡0 静默 0 事件。
- **[2026-10-16] v0.36**（用户：按 1–3 项实现仅电流检测最小可用版本）。`nilm.quantity` auto/p/i；检测器 voltage_missing/quantity_effective，i 口径取 I_rms、W 阈值清零只用相对门槛（兜底 3%）；事件/CSV 新增 quantity/magnitude/unit（旧文件 .pre-v036）；p 无电压告警；ColumnMap 识别仅电流表头；前端下拉+幅值列 |ΔI|；`gen_nilm_sample.py --current-only`。test_r12 +4、ui_r12 25/25、pytest 330 passed。

- **[2026-10-16] v0.37**（用户：检查仅电流检测时算法配置/阈值是否应为电流）。发现 v0.36 清零 W 阈值的做法使 CUSUM h=k 退化、无法填电流阈值、界面仍标 W。改为每算法 `*_a`（A）一套阈值 + `NILM_W_TO_A`、`params_for_current()`，去掉 3% 兜底；前端两套输入按口径灰显。test_r12 +3、ui_r12 31/31、pytest 333 passed。

- **[2026-10-19] v0.38**（用户：同步修改离线调参工具增加仅电流检测支持、修复 v0.37 交付说明中的两个缺口）。`nilm_tune.py` `--quantity auto/p/i` + `--min-load-a`，measure 键去单位、suggest 按 unit 给 `*_w`/`*_a`，JSON 带 quantity；`nilm_replay.py` 套用 quantity、口径标签；`nilm_check.py` 识别 unit=A 事件、`--mag-a` 指纹；`NILM_TUNING_GUIDE.md` 附录 F。实测仅电流样例：tune auto→I（σ≈0.0027 A、min_delta_a=15 @ --min-load-a 30）→ replay 六算法各 2 事件（83.3 A↑/50 A↓）→ check 6 算法 ✅。测试 `test_nilm_tune_tool` 5 passed；全量 pytest 335 passed / 1 skipped。

- **[2026-10-19] v0.39**（用户：① 仅电流检测不存在跨相合并、只能单相；② 趋势图增加电流显示、三相可选）。`NilmDetector.channels_effective`（I 口径去 total，仅 total → A/B/C），summary 带 `channels_effective` + note；nilm_tune I 口径默认 `--channel A`、total 报错；nilm_check `--channel` 过滤 + 多对象提示。前端：三相总灰显、趋势面板「曲线」自动/P/Q/S/电流 I + Ia/Ib/Ic 勾选（取 history/current）。验证：test_r12 +2 改 2、tune 端到端改三相（36 事件、`--channel A` ✅），ui_r12 41/41、ui_r24 64/64、ui_r30 11/11，全量 pytest 337 passed / 1 skipped。

- **[2026-10-19] v0.40**（用户：趋势曲线选电流时上方三相勾选框与曲线下方图例重复，统一去掉上方的）。删除 `nilm-pqs-phases`，`nilmCurrentSeries` 恒给 Ia/Ib/Ic 三条、由图例勾选显隐；ui_r12 40/40、ui_r24 64/64、test_r12 17 passed。

- **[2026-10-19] v0.41**（用户：负荷辨识页趋势/周波窗/事件列表标题后的括号提示换行显示）。`<small class="hdrhint">` 块级独占一行；ui_r12 42/42、ui_r24 64/64。

- **[2026-10-19] v0.42**（用户：负荷辨识页三部分文字拥挤、勾选框超出范围）。`h3.nilm-hdr`：标题行与控件行分开、控件可换行；事件表格单元格 nowrap+横向滚动。ui_r12 43/43、ui_r24 64/64。

- **[2026-10-19] v0.43**（用户：三块面板括号提示放一行、去掉「与总览面板同一曲线」）。`.hdrhint` nowrap+ellipsis+title；ui_r12 44/44、ui_r24 64/64。

- **[2026-10-19] v0.44**（用户：三块面板括号提示与标题改成一行）。`.hdrhint` inline、标题行 flex nowrap、提示省略号；ui_r12 44/44、ui_r24 64/64。

- **[2026-10-19] v0.45**（用户：配置仅电流检测、nilm_tune 仍输出功率参数——分析）。根因：`--quantity` 默认 auto 且只看电压，不读 `cfg.nilm.quantity`。修复为默认跟随配置；test_nilm_tune_tool 6 passed。

- **[2026-10-19] v0.46**（用户：趋势曲线右键「显示周波窗」、以鼠标时刻为中心显示周波数据、周波窗手动装载指定时刻/数量（默认起点 300）、仅非运行可操作）。后端 `load_cycles_from_file` + `GET /api/nilm/cycles_file`（运行中 409）；前端通用右键菜单、装载行、运行态禁用。test_r12 +3、ui_r12 L8 12 项 56/56、ui_r24 64/64。

- **[2026-10-19] v0.47**（用户：右键菜单应在原菜单上新增而非新建）。原菜单＝浏览器原生菜单（无法插项）→ 自定义菜单复现原生图片三项 + 分隔线 + 业务项，Shift+右键放行原生菜单；ui_r12 58/58、ui_r24 64/64。

- **[2026-10-19] v0.48**（用户：检查三块面板选择是否互相独立）。发现事件列表筛选会按条件重拉 nl.events → 趋势图/周波窗竖线被连带筛掉；改为全量拉取 + 客户端过滤。ui_r12 62/62、ui_r24 64/64。

- **[2026-10-19] v0.49**（用户：详细说明六种检测算法实现流程并写入调参手册附录 G）。按 nilm.py 逐函数整理 G.0~G.8，仅文档。

- **[2026-10-21] v0.50**（用户：nilm_tune 量噪声后支持在当前运行配置基础上更新算法参数、保存到输出目录、默认不写配置文件；同步手册）。新增 `elec_tool/nilm_tuning.py` 共用套用/导出逻辑；`nilm_tune.py --apply/--out/--save-config`；`POST /api/nilm/tune/apply`（hot 默认 true、persist 默认 false）+ 界面「套用 nilm_tune 结果」；手册 §3/§7-2′/附录 C/G.8。test_r12_nilm +3、ui_r12 +6 → 68/68。

- **[2026-10-21] v0.51**（用户：附录单独一节详述 nilm_tune.py 命令并逐用法举例）。新增附录 H.0–H.12，示例输出来自实跑。仅文档。

- **[2026-10-21] v0.52**（用户：把 nilm_tune 量噪声调参加入数据处理子界面：文件路径、起止时间/时长（空＝整文件）、是否保存与文件名默认 tune_{时间}.json）。核心迁入 `elec_tool/nilm_tuning.run_tune`，新端点 `POST /api/process/nilm_tune`，界面面板 + 套用按钮，CLI 增时间段参数；test_r12_nilm +2、ui_r8 +15 → 62/62；手册 §3/H.1/H.4′/H.13。

- **[2026-10-21] v0.53**（用户：调参保存须在原配置文件 runtime.json/branch_runtime.json 基础上更新算法参数、其它不变）。端点 save 改走 `export_tuned_config(AppConfig.load(persist_path), …)`，不存在时退回运行配置并注明；界面文案/结果行更新；test_r12_nilm 改写、ui_r8 63/63。

- **[2026-10-21] v0.54**（用户：界面调参结果 JSON 一并输出执行的调参命令）。`build_cli_command` + 端点 `command` 字段 + 保存文件 `_tuning.command` + 界面「等价命令/复制」；CLI 复现与界面结果一致；test_r12_nilm +1、ui_r8 65/65。

- **[2026-10-21] v0.55**（用户：能否从设备录波直接获取最小关心负荷 → 分析后确认实现）。`estimate_min_load` + `run_tune(min_load_auto)` + CLI/端点/界面；样例 300 kW / 19.24 A，纯背景不可估计；test_r12_nilm +2、ui_r8 70/70；手册 H.4″。

- **[2026-10-21] 第 74 轮（用户贴入现场 1 s 聚合 RMS 录波，要求量噪声并算各算法参数）**：手工转录 3 段稳态共 301 点，1 s σ：Ia 0.0039 A、Ib 0.0021、Ic 0.0062（4.56 A 段 0.0069、1.30 A 段 0.0051）；Ic 台阶 1.66/4.56/3.40/3.33/1.73/1.30，最小间距 0.42 A；周波级 σ 只能外推（k=1～√50，推荐 k=3），给出 Ic/Ia 两套 suggest 参数与限制说明；指出 ~40 s 软启斜坡只有 steady_state 能整体检出且需放大 max_transient_cycles。未改代码。

- **[2026-10-21] v0.56**（用户：把"长斜坡 → steady_state max_transient_cycles 自动放大"做进 suggest）。`longest_transient`（滑动均值前后窗差 + 半峰 + 闭运算 → 锚点稳态 → 暂态时长；附伪平台长度）；`suggest(m, min_load, x)` >100 周波时放大 max_transient_cycles、抬 min_steady_cycles（否则斜坡被 Hart 切成小台阶仍配不出）、需要时给 window_cycles；apply 套用 window_cycles 只放大；CLI/界面显示暂态行；`--soft-start` 样例。两次返工：① 按段线性拟合判漂移在噪声吃掉大半 tol 时失效，改为滑动均值差；② 滑动均值差直接外扩 ±1.5W 会吃掉 50 周波平台 → 半峰规则 + 闭运算。合成斜坡：稳态分段由只报硬跳变 → 整条斜坡一个事件。51 passed；ui_r8 70/70。

- **[2026-10-21] v0.57**（用户：检查「从文件投切台阶估计最小关心负荷」是否有问题）。用 9 种合成场景 + 5 个样例复查：发现 8σ 单周波切段对软启斜坡、劈半阶跃失效（候选错且标可靠）、不相邻状态差未区分；改为与 longest_transient 共用 `_moving_mask/_anchors`，门槛加 dm 低分位尺度兜底（第一版用 MAD/中位数在斜坡占半个文件时门槛被抬到看不见斜坡 → 改 20% 分位），半峰邻域 W/2 会让 2W 平台被吃掉、W 会压掉紧邻冲击的斜坡 → 取 3W/4。新增 candidate_from；样例/测试全部复核。

- **[2026-10-21] 第 76 轮（检查两侧实时数据是否写同一 CSV）**：代码走读 + 实机（联动启动、分路单独启动）确认 8 个曲线文件 / events / nilm_events 两侧共用、一行表头、source_id 0/1 共存；未改代码。
- **[2026-10-21] v0.58**（用户：两侧写同一 CSV 不分开保存，文件名时间用本地时间而非数据时间）。根因：文件名按数据日期 → 两侧播放不同日期文件时拆成两个文件。三个 writer 改 `wall_day()`；`load_curves` 删除按文件名日期跳过（否则今天写的旧数据被整体跳过）；测试 4 处期望改墙钟 + 新增两侧不同数据日期用例。

- **[2026-10-22] v0.59**（用户：离线文件播放输出写 `output/{yyyyMMddhhmmss}/`，并在目录内输出两侧配置文件）。方案：仅 `csv_file` 源；`_alloc_run_dir`（对侧在跑→沿用，否则新建本地时间目录，同秒加 `_k`）；三 writer 加 `dir_override`，`LiveEngine(run_dir=)`；`_dump_run_configs` 写 config_bus/branch.json + run_info.json（保留首个启动侧，追加 starts）；start 响应 / state / last_result 带 `run_dir`，load_last 读回；界面启动提示显示目录。实机（端口 8013，`ELEC_TOOL_OUTPUT_DIR=/tmp/out59b`）：联动启动两侧同一 `20261022115905/`，run_info started_side=bus starts=[bus,branch]，load_last 两侧均从该目录读回。测试新增 `test_r17::test_offline_play_writes_run_dir_with_both_configs`；修 conftest 会话级环境隔离（module 级 TestClient 先于函数级 autouse，实机留下的真实 last_result.json 曾污染 test_r12）。全量 354 passed / 1 skipped。缺口：旧运行目录不清理；非 csv 源仍写固定目录；load_last 只认最近记录的 run_dir。

- **[2026-10-22] v0.60**（用户三点：目录名 `yyyyMMdd_hhmmss`；两侧配置文件原封不动输出；实时数据与事件仍放 realtime/events/nilm 三目录）。改 `_alloc_run_dir` 格式；`_dump_run_configs` 改 `shutil.copyfile` 复制 persist_path→cfg_path（都无才 to_dict 退回，run_info 记 `config_mode/config_copied_from`）；`LiveEngine` 三 writer 的 `dir_override`＝`<run_dir>/{realtime,events,nilm}`，`load_last` 相应读子目录。实机 8014：`20261022_121500/` 三子目录齐全、`cmp` 两配置文件与源逐字节一致、load_last 读回；测试更新；全量 354 passed / 1 skipped。沙箱本轮再次重置（HEAD 回 27b28ea、工作区文件保留），用 fetch+reset --mixed 恢复。

- **[2026-10-22] v0.61**（用户：数据处理子界面增加波形预览——路径可配；文件信息（通道数/采样率/时长/起止）；按重采样率/通道/时间段或起点+点数加载波形曲线（默认原采样率、全通道、1000 点、空＝整段）；指定时间的有效值曲线，右键在单独周波窗曲线中显示以当前时刻为中心 1000 周波）。新模块 `elec_tool/wave_preview.py`（file_info/load_waveform/rms_curve），端点 `/api/process/wave/{info,load,rms}`，界面新增面板 + 三张画布（复用 drawLine/bindCtxMenu/canvasNativeItems）。实机 8015：info 6 通道 6400 Hz；默认 1000 点；n= 整段 800 Hz → 8000 点；时间段 0.5 s → 3200 点；分路侧基准配置；RMS 时长/合并；1000 周波 × 6 通道 JSON 4.75 MB / 0.36 s。`test_r61` 4 项，`ui_r61` 23/23，全量 358 passed / 1 skipped。沙箱本轮再次重置，fetch+reset --mixed 恢复后继续。

- **[2026-10-22] v0.62**（用户：波形预览①重采样方式可选且含重采样功能的方法；②基准配置独立不关联运行配置；③默认起止＝文件数据时间；④时长＝采样率×点数；⑤默认 300 周波、右键周波窗 300 周波）。`wave_preview`：`method` linear/nearest/fft（fft 同 resample.py 实现）、`n_cycles`、`make_base`/`base_defaults`、info 时长=rows/fs 与 t_end=t0+(rows−1)/fs + `t_end_by_timestamp`；端点去 side 改收六项基准参数 + `/api/process/wave/defaults`；界面六个基准输入（localStorage）、方式下拉、加载周波数 300、周波窗 300、信息后自动填起止（静默补取不覆盖）。实机 8016 + `ui_r61` 33/33；`test_r61` 5 项；全量 359 passed / 1 skipped。沙箱再次重置，fetch+reset --mixed 恢复后继续。
- **[2026-10-22] v0.63**（用户：检查保存配置是否在原文件基础上只改所需项并保留其它配置 → 实测否：整份内存配置覆盖写；随后要求按建议修改并在数据源分组增加「保存总线侧配置」）。`app/server.py`：`_persist(cfg, patch)` 读原文件 → `_patch_pick`/`_apply_patch` 只合并本次改动（未知键不写、规范化删除项同步删）→ 校验 → 保留缩进原子写；`_persist_base_doc` 退回加载模板；tune apply persist 用 `_dict_diff` 只写 nilm 差异；`config.py` file_speed 转 float。界面 `btn-src-save` + `saveBusSource`/`collectBusSavePayload`；启动提示注明不写文件。`test_r63_persist` 6 项、`ui_r63_check` 11/11、`ui_r61` 33/33、全量 365 passed / 1 skipped（`test_server` 一处旧假设断言改为磁盘字节不变）。实机 8019（`ELEC_TOOL_CONFIG_PATH=/tmp/cfgchk/runtime.json`）。
- **[2026-10-22] v0.64**（用户：波形预览①最多加载点数可配默认 2000 万；②自定义时间：启用时自定义起止默认空＝文件数据起始 / 按采样率计算的结束，否则用文件时间且起止时刻默认空；③取消 harmonic.order_max ≥ Nyquist 对加载的限制）。`wave_preview`：MAX_POINTS_DEFAULT=2e7、make_base 三个自定义时间项、file_info 自定义模式、`_prep_cfg(info)` 行号定位 + 终点裁剪、`relax_harmonic_limits`；服务端 `max_points` 参数（上限 1e8）+ 三端点透传自定义时间；界面自定义时间行 / 最多加载点数 / 起止不再自动填入（占位提示）。`test_r61` 6 项、`ui_r61` 40/40、全量 366 passed / 1 skipped。实机 8020。
- **[2026-10-22] v0.65**（用户：①负荷辨识趋势曲线与数据处理有效值曲线右键增加「显示周波窗 2」＝周波瞬时值曲线；②波形预览基准配置 / 自定义时间为两条曲线的公共配置，采样率按文件数据时间计算不可改，界面明显区分公共 / 波形曲线 / 有效值曲线三组配置）。服务端 `GET /api/nilm/wave_file`；前端 `loadNilmWave2/renderNilmWave2`、`wpLoadCycleWindow(t,n,2)`、HTML 三组 `.wp-group` + `wp-cyc2`/`nilm-wave2` 画布；`_prep_cfg` 统一按时标推算 fs。`test_r61` 7 项、`ui_r61` 46/46、`ui_r12` 73/74（残留项）、全量 367 passed / 1 skipped。实机 8021/8022。
- **[2026-10-22] v0.66**（用户：①数据处理页原周波窗改为该段逐周波有效值；②负荷辨识页周波窗 2 仅离线文件，实时源时右键项不可选）。前端 `wpLoadCycleWindow` which=1 → `/api/process/wave/rms?agg_cycles=1` + `wpDrawCycRms`；NILM 右键菜单按 `state.config.source.kind==="csv_file"` 启用「显示周波窗 2」。`ui_r61` 47/47、`ui_r12` 76/76（脚本改用 `window.__render`）、全量 367 passed / 1 skipped。实机 8023。
- **[2026-10-22] v0.67**（用户：三块曲线标签改为「逐周波 RMS 曲线 / 周波窗（有效值）曲线 / 周波窗 2（瞬时值）」；周波窗两图左右布局；波形曲线配置 ‖ 波形曲线、有效值曲线配置 ‖ 逐周波 RMS 曲线并排）。只改 `index.html`（配置组从 `#wp-form` 移到各自曲线左侧面板 `#wp-form-wave/#wp-form-rms`，id 不变）与 `style.css`（`.wp-pair` 2fr/3fr，窄屏单列）。`ui_r61` 47/47、`ui_r12` 76/76、全量 367 passed / 1 skipped。实机 8024。
