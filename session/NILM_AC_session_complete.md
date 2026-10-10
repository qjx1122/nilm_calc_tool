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
