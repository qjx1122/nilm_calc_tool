# STATUS.md

> 续接文件（BOOTSTRAP.md v2.2 台账）。每次收尾必更新；只改本文件，不另建同类文件。
> 最后更新：2026-10-12（第 6 次收尾：第 6 轮四功能——用户时标格式 / 24h 曲线 / 逐曲线保存开关 / 自定义播放时间，修复 F-11~F-16）

## 当前角色
- 角色：**资深电力算法专家**（`ROLE.md` v1.4 指定的默认当前角色）
- 本任务级覆盖：**工程实现工程师**（对「实现电气量计算工具」及其后续界面缺陷修复 / 功能增补任务生效；任务收尾后回归默认角色）
- 生效范围：任务级（非全迭代）
- 默认执行模式：**混合**——沙盒侧（模式 A）写码 + 合成信号解析解自验证 + live preview 实跑，**已有实录**；用户侧（模式 B）Windows 部署 / 真实数据对账 / 生产常驻，**只出执行包，未获实录不下结论**（执行包见 `REPORT_TEST.md` T-002 的 W/R/P 三组）
  - 说明：更早任务用户显式指定过模式 B（仅对「补齐台账骨架」生效）；此后各任务用户均跳过模式澄清，故一律按上述混合模式执行并在此声明。第 5 轮（界面下拉框检查）沙盒侧＝jsdom 驱动真实页面打真实服务端 + REST 空值语义实录，**已✅实录**；用户侧＝浏览器手点 U 组 7 步，**🔶待回报**。**第 6 轮（四功能）**沙盒侧＝pytest 25 项 + jsdom 30 项 + REST/CLI 实录，**已✅实录**；用户侧＝浏览器手点 U6 组 8 步，**🔶待回报**

## 当前目标
- **本任务（2026-10-12 第 6 轮，已交付、沙盒侧✅实录）**：用户 5 点需求——① 离线 CSV 支持 `0/00/00 00:12:40.0000,290.175751,…` 格式 ② 界面所有曲线＝最新 24 小时（不足则全部）③ 每条曲线可分别配置是否保存，保存曲线数据时未勾选项不保存 ④ 离线播放可选「自定义时间」（起始默认文件第 1 条，后续按采样率推算；否则用文件时间）⑤ 完成后验证
  - 实现：`parsing.py` `_parse_slash_clock`/`_unwrap_midnight`（无日期时标→当天时刻、跨午夜展开、按位数换算小数）+ `parse_rows` 跳过时间戳列 + `/api/probe` 无表头回退；`metrics.History` 重写为按数据时间保留的紧凑列存储（`array('d')`、锁、numpy 峰谷抽稀）+ `/api/history` 新参数 `hours/max_points` + `output.history_hours/history_max_points`；`output.curve_save` 六键 + `POST /api/curves/save` + `GET /api/curves/export` + 6 个面板勾选框与导出页列表同步；`source.custom_time/custom_time_start` + `CsvFileSource._apply_custom_time` + CLI `--custom-time[-start]` + 界面勾选框/起始框联动 + start 白名单放行
  - 验证：`tests/test_r6_features.py` **25 项**（每项写明撤销修复如何 FAIL）；`tools/ui_r6_check.cjs` **PASS 30 / FAIL 0**；旧 `ui_dropdown_check.cjs` 复跑 **PASS 74 / FAIL 0**；全量 **186 passed, 1 skipped**；selftest 44/44；History 24h 性能实测（43.2 万点 38.5 MB、抽稀 40 ms、并发读写 0 异常）
  - 实测发现并修复 **F-11~F-16**（时标格式 / probe 无表头 / 时间戳列记非数值 / 历史定长 600 点 / 热更新清空历史与结果 / 抽稀性能与读写竞争）
  - 交付文档：`README.md` v0.5（§3.1 新增「趋势曲线＝最近 24 小时＋保存曲线」、§3.4 新端点、§4.1 时标格式与无表头、§4.2 自定义播放时间字段/用法/实测、§6 配置、§7 产物、§8 第 6 层验证、§11、变更记录）；`REPORT_TEST.md` v0.5 新增 **T-004**（S1~S9、F-11~F-16、U6 组执行包、J-U6、回收格式）；`REPORT.md` v0.5 新增 **C-14/C-15** + 1 条教训
  - 验收状态：沙盒侧 ✅ 已复现；**用户侧 🔶 待回报**（T-004 U6 组：真实文件探查、自定义时间、勾选保存、过夜 24h 内存）
  - 假设（用户未说明、已在 README 标注）：24 h 按**数据时间**计；「曲线」＝6 条时间趋势（波形/频谱为单窗瞬时量）；保存＝服务端写 `output/curves_<ts>/` + 浏览器下载两入口；自定义起始时间按本地时区
- **上一任务（2026-10-10 第 5 轮，已交付、沙盒侧✅实录）**：「检查 Web 总览面板-数据源与控制界面中数据源输入方式下拉列表框是否可正常选择 4 种输入方式分别进行配置（含其它下拉列表框）」
  - 结论：**4 种输入方式修复后均可正常选中并分别配置**，服务端确实按所选 kind 摄入；「帧格式」「电压输入口径」「视在/无功口径」「频谱通道/比例/频段上限」共 8 个下拉框全部可用（`tools/ui_dropdown_check.cjs` 实测 **PASS 74 / FAIL 0**，修复前同脚本 PASS 37 / **FAIL 10**）
  - 检查方法：**jsdom 加载真实 `index.html`/`app.js` + 打真实服务端**（自动拉起 9000 端口 TCP 喂数器、捕获 PUT/POST 载荷原文、以 canvas 绘制调用计数验证重绘），不用「读代码 + 手点一次」下结论
  - 发现并修复 **5 个界面缺陷 F-06~F-10**（详见「决策记录 / 踩坑」与 `REPORT_TEST.md` T-003）；新增 `tests/test_web_ui.py` 14 项前端契约测试（**撤销修复必 FAIL 已验证**）；测试 147 → **161 passed, 1 skipped**
  - 交付文档：`README.md` §3.1 新增「数据源面板：4 种输入方式的联动、空值语义与两个保存入口」（逐源可编辑/置灰字段表、PUT 深合并 vs start 白名单对照、6 步手工点检清单）＋ §8 升为五层验证；`REPORT_TEST.md` T-003 追加 S14~S18 + F-06~F-10 + U 组执行包；`REPORT.md` 新增 C-13
  - 验收状态：沙盒侧 ✅ 已复现；**用户侧 🔶 待回报**（T-003 的 **U 组**＝浏览器手点 7 步，真实浏览器下的视觉/输入法/焦点行为未实测）
- **上一任务（2026-10-10，已交付、沙盒侧✅实录）**：「分别详细说明 4 种输入方式的数据源如何配置及运行，并进行验证测试」
  - 交付＝`README.md` §4 重写为「四种数据源详解」（每源：完整配置字段含默认值与约束 / CLI·Web·库三种运行方式 / 沙盒实测输出 / 注意事项 / 可复现的验证方法）＋ §4.6 四源横向对账表 ＋ §4.8 一键复现
  - 验证＝四种源 × 三条入口全部**实跑取证**（`REPORT_TEST.md` T-003 的 S1~S13 三件套）；新增 `tools/`（`tcp_feeder.py` / `csv_appender.py` / `verify_sources.py`）使**无采集硬件也能复现全部验证**
  - 实测发现并修复 5 个问题（F-01~F-05，见「决策记录 / 踩坑」）；测试 141 → **147 passed, 1 skipped**
  - 验收状态：沙盒侧 ✅ 已复现；**用户侧 🔶 待回报**（T-003 的 S 组＝无硬件复现、D 组＝真实装置/协议）
- **更早任务（2026-10-10 立项，代码已交付、待用户本地验收）**：实现「电力系统各类电气量计算工具」软件代码
  - 需求（用户 2026-10-10 原文）：① 总体为电力系统各类电气量计算工具 ② 各电气量分子界面 ③ 导航条切换子界面 ④ 输入支持实时采集 + 离线文件两种方式 ⑤ 电气量＝三相电压、电流、功率因数、有功、无功、基波、谐波（2–50 次）、频谱 ⑥ 各电气量可分别配置计算时间段（如电压有效值 1s 或 5s）
  - 数据事实（用户确认，2026-10-10）：二次侧三相电压电流实时采集；fs=6400 Hz；CSV 列＝`时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流`；PT=100、CT=15，**均可配置**
  - 交付形态：算法核心包 `elec_tool/` + 4 类数据源 + 计算引擎 + CLI（7 子命令）+ Web 界面（FastAPI + WebSocket + 12 个导航子界面）+ 142 项测试
  - 验收状态：**沙盒侧 ✅ 已复现**（6 条标准逐条有代码与测试对应，见 `README.md` §1 对照表）；**用户侧 🔶 待回报**（T-002 W/R/P 组）
- **上一任务（已完结）**：补齐台账骨架（`README.md` / `REPORT.md` / `REPORT_TEST.md` / `NILM_DATA_DICT.md` / `session/…`）
- **待用户回报的专题**：T-001（环境与数据基线核对，A~D 组）、T-002（本地部署与真实数据验收，W/R/P 组）、T-003（四源复现 S 组 / 真实装置 D 组 / 界面点检 U 组）、**T-004（第 6 轮四功能浏览器点检 U6 组）**——均未获实录
- 范围边界：~~本 session 不写业务代码~~ ❌**已失效**（该边界属上一任务；本任务即为写代码）；仍然遵守：不新建台账外散文件、不把数据/产物入库

## 已完成
- [x] 2026-10-10 开局仪式：`git status` / `git log` / `git branch --show-current`；读 `ROLE.md`；`gh auth status` 通过（qjx1122）；`git ls-remote origin` 通过
- [x] 2026-10-10 初始化 `STATUS.md` 并即刻 push（`e821ef3`）；创建 5 份台账骨架 v0.1 + 文件级验证 V1–V8（`2b7d3c3`）
- [x] 2026-10-10 **算法核心**（`880bf5f`）：`elec_tool/{config,blocks,scaling,metrics,selftest}.py` + `analysis/{window,rms,harmonic,power}.py`——整周期矩形窗 FFT、RMS/相量/序分量、谐波 2–50 次与 THD/HR/间谐波、P/Q/S/PF/DPF/四象限/零线电流、过零+基带精修估频、窗切分与降级策略、PT/CT 变比
- [x] 2026-10-10 **数据源 + 引擎 + CLI + 测试**（`8166743`）：`sources/{csv_file,csv_tail,tcp_stream,simulator,parsing}.py`（编码/时间戳格式/列名别名自适应、缺测插值+告警、fs 反推对账、缺口检测）；`engine.py:LiveEngine`（各量独立窗调度＝需求⑥、缓冲自动扩容、热更新配置）；`cli.py` 7 子命令；`configs/default.json`
- [x] 2026-10-10 **Web 界面与服务**（`b09f2a6`）：`app/server.py`（FastAPI + WebSocket + 引擎后台线程 + 12 组 REST）、`app/static/{index.html,style.css,app.js}`（12 个导航子界面、原生 canvas 图表、**无任何外链/CDN**、WS 断开自动降级 1.5 s 轮询）、`tests/test_server.py`（20 项 Web 层端到端）
- [x] 2026-10-10 **沙盒侧验证全绿**：`cli.py selftest` 44/44（最差相对误差 1.508e-05）；`pytest tests/ -q` **141 passed, 1 skipped**（约 55 s）；实时链路实测 6398–6400 点/s；离线 5 s 样例实算 26 次输出、emits 分层（快量 26 / 慢量 6）；窗长改 5 s → 输出 2 次且缓冲扩到 49280 点；导出 CSV 34.6 万行；内网离线安装（Linux 29 包 / Windows 目标 24 包）实测可用
- [x] 2026-10-10 **修复两个真 bug（均由新增测试暴露，已加回归测试）**：B1 引擎线程换代竞争 → 同批数据双重摄入（`samples_in` 虚高、窗内点数不足）；B2 `plan_window` 绝对容差 → 估频 49.999987 Hz 时 1 s 窗实际只算 0.98 s/49 周期。详见 `REPORT_TEST.md` T-002
- [x] 2026-10-10 **`README.md` v0.2**：新增「本地详细部署与运行说明」（§2 部署 7 小节 + §3 运行 5 小节 + §4 接真实数据 + §9 生产推荐流程 + 两张排错表），台账 6 章由占位改为沙盒实录；所有数字改为代码级/实测值（缓冲容量公式、内存、退出码、默认值）
- [x] 2026-10-10 **`REPORT_TEST.md` v0.2**：追加专题 **T-002**（沙盒侧 A1~A10 三件套实录 + B1/B2 缺陷记录 + 用户侧 W/R/P 三组模式 B 执行包 + J-\* 判读要点 + 结果回收格式）
- [x] 2026-10-10 补齐 csv_tail 现场开关：CLI `--from-end` / `--watch-newest` + 界面两个勾选框（此前只能改配置文件），并加 CLI 回归测试
- [x] 2026-10-10 配置持久化分离：出厂模板 `configs/default.json`（入库、不被界面污染）/ 运行时 `configs/runtime.json`（gitignore）
- [x] 2026-10-10 **Web 界面下拉框专项检查与修复（第 5 轮）**：`tools/ui_dropdown_check.cjs`（jsdom 端到端，实测 PASS 74 / FAIL 0；修复前 PASS 37 / FAIL 10）+ `tests/test_web_ui.py`（14 项前端契约，撤销修复必 FAIL 已验证）+ 修 F-06~F-10 + 新增 `#src-hint`/`#src-formnote`/置灰视觉 + `README.md` §3.1 联动说明与 6 步手工点检清单 + `REPORT_TEST.md` T-003 追加 S14~S18/U 组 + `REPORT.md` C-13；`pytest tests/ -q` **161 passed, 1 skipped**
- [x] 2026-10-10 **沙盒回收事故恢复**：venv 重建、样例数据重生成、git 历史按原结构重提交并 push（远端 `d2337ab`）
- [x] 2026-10-12 **沙盒回收事故恢复（第 3 次）**：`.git` 退回基线、工作树尚存 → `git fetch` + `reset --mixed FETCH_HEAD` 接回 `a88dcaa`（零差异、无丢失），venv/样例重建
- [x] 2026-10-12 **第 6 轮四功能**：用户时标格式（F-11~F-13）/ 24h 趋势历史（F-14~F-16）/ 逐曲线保存开关 / 离线自定义播放时间；`tests/test_r6_features.py` 25 项 + `tools/ui_r6_check.cjs` PASS 30 + 旧 harness PASS 74 + 全量 **186 passed, 1 skipped**；README v0.5 / REPORT_TEST T-004 / REPORT C-14、C-15

## 进行中
- 等用户执行 **T-004 的 U6 组**（浏览器手点 8 步：真实 0/00/00 文件探查 → 不开/开自定义时间启动 → 勾选保存框与 F5 保持 → 保存曲线数据查 output/ → 跑 ≥10 min 看曲线标题跨度；可选过夜看 24.00h 与内存）并回报实录
- 等用户执行 **T-003 的 U 组**（浏览器手点 7 步，约 5 分钟：回填/联动置灰/binary 帧字段/启动出数/脏值保护/口径保存/可选 node 脚本）并回报实录
- 等用户执行 **T-003 的 S 组**（无硬件复现四源验证，约 10 分钟）与 **D 组**（真实采集 CSV / 真实 TCP 协议）并回报实录
- 等用户执行 T-002 的 W/R/P 组（Windows 部署 / 真实数据对账 / 生产常驻）并回报实录

## 下一步（TODO）
1. **用户侧（阻塞项，模式 B）**：先跑 **T-004 的 U6 组**（用真实采集文件，期望见 `REPORT_TEST.md` T-004），再跑 T-003 的 **S 组**（`python tools/verify_sources.py` 期望 PASS 5 / FAIL 0；`pytest tests/ -q` 期望 **186 passed**；两个终端跑 tcp_feeder / csv_appender + `cli.py live` 期望缺口 0），**T-003 的 U 组**（浏览器手点 7 步，界面下拉框，期望见 `REPORT_TEST.md`），再跑 T-002 的 W 组（Windows 部署，预计 10 分钟）与 R 组（真实数据对账，核心验收），按「结果回收格式」贴回；P 组（生产常驻）可选
2. Agent 侧（收到实录后）：把三件套写入 T-002「结果 / 结论」，按 J-\* 逐条对账，回填 `README.md` §2/§3/§4 与 `NILM_DATA_DICT.md` 的 🔶 项（注明来源＋日期）
3. **待确认口径**：电压列是相电压还是线电压（`transform.voltage_input`）、真实编码与时间戳格式、PT/CT 实际值、实时落地方式（文件 or TCP 协议文档）
4. 若验收方要求 IEC 口径：另立专题实现 IEC 61000-4-7 谐波分组（10/15 分钟评估、分组平方和）——当前为整周期矩形窗口径
5. TCP 实时源联调：`--frame/--struct-fmt/--struct-fields` 三处已可配（CLI/界面/REST 白名单），文本帧与二进制帧均已用喂数器验证；**仍需现场协议文档**确认帧头帧尾/长度字段/缩放系数/时标类型；若协议含帧头+长度+校验，需在 `sources/tcp_stream.py::_flush_block` 加拆帧（`DataSource` 接口不变，上层零改动）
5b. TCP 的 `timeout_s` / `reconnect_s`（各默认 2.0 s）目前只是构造参数，未暴露到配置文件与界面——待现场联调时按需提升为配置项
5c. `csv_tail` 目录模式按 mtime 选最新文件；若现场分片命名与 mtime 不一致（如补写旧分片），需改成按文件名排序——待 T-003 的 D-5 回报后决定
6. 是否需要 Qt 桌面壳（本轮决策 Web 优先）——等用户表态
7. `TUNING_GUIDE.md` 仍未创建：待用户真实数据回报后，把「窗长/口径/变比怎么选」写成调参教学（BOOTSTRAP 规定该文件整篇重写、不追加流水，空骨架无意义）
8. T-001 的 B6 / C6 / D1~D7 仍未回报（其中 fs、列格式、PT/CT 已由本轮需求描述实质回答）
9. 可选增强（当前为单机工具形态）：用户/权限、历史入库（数据库）、报警推送、多测点并行
10. **T-004 遗留**：自定义播放时间目前只对 `csv_file` 生效（`csv_tail` 若现场文件也是 0/00/00 写法需扩展）；趋势历史随「重新启动数据源」清空，跨运行/跨进程的 24 h 需落盘（SQLite/滚动 CSV）；`history_hours`/`history_max_points` 未上界面；曲线横轴跨午夜不显示日期；自定义起始时间按本地时区（若现场要 UTC 需加 `tz` 字段）

## 决策记录 / 踩坑
- 2026-10-10｜**UI 形态＝Web 版**（用户跳过澄清）：FastAPI + WebSocket + 浏览器导航条/子界面，理由是沙盒可 live preview 当场验收、内网零外链可部署、跨平台无需装 GUI 依赖；**Qt 桌面壳延后**（列 TODO 6）。算法核心独立成包（只依赖 numpy），CLI 与库调用同等交付，避免绑死界面
- 2026-10-10｜**实时源＝统一 `DataSource` 适配器接口 + 内置模拟器**：先用模拟器跑通全链路（可解析解对账），再实现 CSV tail（监视追加）与 TCP 客户端（帧格式配置化，真实协议 🔶待确认）；离线 CSV 读取做编码（utf-8/gbk/big5…）与时间戳格式（ISO / epoch s·ms·µs·ns / 相对秒）自适应
- 2026-10-10｜**谐波口径＝额定 50 Hz 整周期矩形窗 FFT**：6400/50＝128 点/周期；50 次＝2500 Hz < Nyquist 3200 Hz 不混叠；可选 45–65 Hz 自适应估频后整周期截断抗泄漏（默认开启）；IEC 61000-4-7 分组延后（TODO 4）
- 2026-10-10｜**执行模式＝混合**：沙盒写码 + 合成信号解析解自验证 + live preview（模式 A 部分）；真实数据/Windows/生产常驻交用户本地（模式 B 部分）。用户跳过澄清＝默许按推荐路线走，已在此声明
- 2026-10-10｜**单进程单 worker 约束**：引擎与历史保存在进程内存（`EngineRunner` 单例），**禁止** `uvicorn --workers N`（多 worker 会各算各的）；已写入 `README.md` §9「不推荐」
- 2026-10-10｜**配置持久化分离**：界面改动写 `configs/runtime.json`（gitignore），出厂模板 `configs/default.json` 保持干净可回溯；加载优先级 `ELEC_TOOL_CONFIG` > `ELEC_TOOL_CONFIG_PATH` > `runtime.json` > `default.json`
- 2026-10-10｜**数据与产物不入库**：`data/`、`*.csv`、`output/`、`logs/`、`configs/runtime.json` 全部 gitignore（现场电力数据可能涉密且体量大：6400 Hz × 7 列 ≈ 0.5 MB/s）；样例数据用 `cli.py gen-sample` 现场生成即可复现
- 2026-10-10｜**踩坑 B1（并发）**：`EngineRunner.start()` 持锁 join 旧线程，与旧线程「写结果要拿同一把锁」互等到超时 → 旧线程存活后每轮重读 `self.engine`，继续轮询**被替换的新引擎** → 同批数据双重摄入（32000 行文件跑出 `samples_in=32640`）。教训：**换代必须在锁外 join，且线程只持有本轮私有对象**（engine/stop_event 按值传参 + 每轮自检被取代即退场）
- 2026-10-10｜**踩坑 B2（数值口径）**：整周期判定用绝对容差 `floor(cyc_req + 1e-9)`，而 `f_used` 是**估计值**（相对误差 2.6e-7）→ 用户配 1 s 实际只算 0.98 s/49 周期，还持续误报「整周期截断」。教训：**对带误差的估计量做整数判定必须用相对容差**；已改 `max(1e-9, 1e-5·|cyc_req|)` 并加回归测试
- 2026-10-10｜**踩坑（前端）**：服务端按各量独立步长推送**分量子集**，前端若整体替换结果，慢窗量会被 0.2 s 的快量推送抹掉 → 必须按键合并（`app.js:mergeResult()`）
- 2026-10-10｜**踩坑（部署）**：`uvicorn[standard]` 的 extra 拉 uvloop，而 uvloop 无 Windows wheel → 跨平台 `pip download --platform win_amd64 -r requirements.txt` 直接 `ResolutionImpossible`（补 `--implementation/--abi` 也无效）；解法＝显式列包不带 extra，并在 `requirements.txt` 用 PEP 508 平台标记分流
- 2026-10-10｜**事故：沙盒回收致本地未推送提交灭失**：环境中断后 `.venv`、`data/`、后台进程全部消失，仓库被重新克隆到基线 `27b28ea`，本地 `d07476d`/`3126e4c` 等提交丢失（远端只到 `2b7d3c3`）；靠工作树文件尚存 + `git fetch` + `git reset --mixed FETCH_HEAD` 接回远端 tip，再按原结构重提交 4 个 commit 并 push（`d2337ab`）。教训：**每个逻辑单元完成即刻 commit + push**（与 `ROLE.md` v1.3 记载的「快照回退致未推送工作灭失」同类，已第二次发生）；venv 与样例数据必须可一键重建（`requirements.txt` + `cli.py gen-sample`）
- 2026-10-10｜**文档纪律（本轮强化）**：`README.md` 里每条命令都先在沙盒实跑取证再写（实测发现 `--every` 只有 `compute` 有、`live` 没有；`watch_dir_newest` 默认已是 true），所有数字改为代码级/实测值（缓冲容量公式 `ceil(最长窗×fs×1.5)+max(块,64)`、内存、退出码 0/1），Windows 与真实数据相关一律标 🔶未实测
- 2026-10-10｜**踩坑 F-01（实时源·本轮实测发现）**：`csv_tail` 目录模式检测到更新分片就直接 `_reopen()`，旧分片在上次轮询之后新写入的数据被静默丢弃 → 每切换一次丢**正好一整块**（640 点＝100.2 ms），结果里表现为与轮转周期同频的「疑似丢点」**假缺口**（实测 8 s 内 8 处、间隔恰 2.000 s）。修法＝切换前 `_drain_current()` 补读旧文件并在告警里写明补读行数；回归测试 `test_csv_tail_dir_switch_drains_old_file`（撤销修复则 1280≠1920 失败）。教训：**告警本身也可能是 bug 的产物**，先证伪告警再怀疑现场数据；「缺口＝0」应写进验证工具的硬判定
- 2026-10-10｜**踩坑 F-02/F-03（可诊断性）**：① 二进制帧格式不匹配时坏时标一路传到显示层 `time.localtime` → CLI 崩 `OverflowError: timestamp out of range for platform time_t`（`np.isfinite` 挡不住「超大但有限」）；修法＝解析层合理性闸门（非有限或 max|t|>1e11 秒 → 可诊断 `ParseError`）+ 显示层 `_fmt_clock()` 兜底 + 源退回合成时间轴。② 同类告警每块重发且文本含变化数值 → 3 s 刷 8 条，且 `cli.py live` 收尾**根本不打印源告警**＝「看着正常、其实时间轴是合成的」；修法＝`sources/base.py::note_key()` 按中文骨架去重（tcp/csv_tail 共用）+ `_print_diagnostics()` 让 compute/live 收尾统一打印「缺口 + 引擎告警 + 源告警」
- 2026-10-10｜**协议约束 F-04（实测）**：**不得用 float32 存 epoch 秒**——float32 在 1.7e9 秒处量化步长约 128 s，一整块 0.1 s 样本时标全同（实测显示时刻偏早约 2 分钟）；电气量不受影响（只用样本序＋配置 fs），但时间轴与缺口检测失真。已加 `_flag_degenerate_clock()` 显式告警（整块无递增 / 存在回退两种退化）
- 2026-10-10｜**踩坑 F-05（工具链）**：`node --check` **只验语法不验逻辑**——patch `app.js` 时把 `return {…}` 后直接接「删空值 + return payload」形成死代码且 `payload` 未定义，语法检查照样通过；修法＝改 `const payload = {…}` 并另做「`return` 之后残留语句数＝0」静态检查。同类：给已有方法**中间**插入新方法会把原方法劈成两半（本轮把 `TcpStreamSource.__init__` 尾部两行吞进 `_note`），以及全量 `str.replace("self._notes.append(", "self._note(")` 会把 `_note` 自身也改成无限递归——插入/替换后必须跑测试，不能只看语法
- 2026-10-10｜**决策：无硬件验证路径进交付物**：`tools/tcp_feeder.py`（TCP 服务端，text_csv/binary，可指定 `--struct-fmt`）、`tools/csv_appender.py`（按用户列格式追加、可 `--rotate-every` 分片轮转）、`tools/verify_sources.py`（库级四源自动对账，实测 PASS 5/FAIL 0；退出码 0＝通过含 SKIP、1＝验证失败、2＝参数错误），三者与内置 `simulator` 共用信号模型，故可与 `selftest` 解析解对账；另加 `tests/test_tools.py` 5 项防腐测试，避免「文档承诺的验证步骤悄悄坏掉」
- 2026-10-10｜**踩坑 F-06~F-10（界面层，本轮 jsdom 端到端检查发现）**：① **F-06** `#src-kind`/`#src-frame` 在 `bind()` 里**没有任何 change 监听**（只有频谱 3 个下拉框有）→ 选了界面毫无变化、4 种源的字段全部平铺可编辑、填了不生效也无提示；修法＝新增 `syncSourceForm()` 按 kind/frame 决定 10 个字段的 `disabled` 并写 `#src-hint` 逐源说明（`SRC_HINT` 单一事实来源）。② **F-07** `collectSourcePayload()` 全字段平铺 → 选 simulator 仍带 `path/host/frame`、TCP 切回 text_csv 仍带旧 `struct_fmt`；实测空 `path` 被服务端 **400 拒**「source.kind=csv_file 需要 source.path」，空 `host` 被 **静默存成 ''**；修法＝按 kind 裁剪 + 「非空/有限才送」。③ **F-08** 空数字框经 `+$('#cfg-fs').value` 变 `0` 送出，而 `PUT /api/config` 是深合并 → **全新加载页面第一次点「保存配置」必 400**「sampling.fs 必须 > 0（当前 0）」且用户看不出是哪个框；修法＝只送「有限且 >0」，被跳过的字段名写进成功提示。④ **F-09（最隐蔽）** 快量 0.2 s 一次的推送 → `render()` → `renderSource()` **无条件回填** → 停在数据源页时「刚选的下拉框被改回服务端 kind、输入一半的路径被清空」；修法＝拆出 `fillSourceForm()`、`S.formDirty` 脏值保护 + `#src-formnote` 提示、「刷新」＝丢弃修改重新回填。⑤ **F-10** `startEngine()` 夹带 `collectConfigPayload()`，而 `/api/engine/start` 只取 source 白名单 + `windows` → 改完 PT/CT 点「启动数据源」被**静默忽略**；修法＝启动只送 source，提示指向「保存配置（热更新）」
- 2026-10-10｜**方法论：界面缺陷需要「双层可复现验证」**：`node --check`（只验语法）与 `pytest`（不碰前端）全绿的情况下，上述 5 个缺陷全部隐身；最隐蔽的 F-09 只在「停在数据源页 + 引擎在跑」时每 0.2 s 复现一次。对策＝① `tools/ui_dropdown_check.cjs`（jsdom 驱动**真实页面**打**真实服务端**，可断言请求载荷原文、服务端回显、推送后的 DOM 值）② `tests/test_web_ui.py`（前端契约静态测试：下拉框选项 ↔ 后端枚举集合相等、`$('#id')` 引用的元素必须存在、四道闸门在位；不需 node，随 pytest 跑）。**踩坑**：断言「字段不可编辑」要用 `.disabled`，不能用 `offsetParent`（jsdom 无布局，恒为 null → 假 PASS）；捕获请求要同时过滤 PUT 与 POST，否则漏掉 `saveConfig`；`const` 声明在 `window.eval` 后不可见，需在同一次 eval 里用闭包导出（`window.__S=()=>S`）
- 2026-10-12｜**决策（第 6 轮）**：① 无日期时标基准＝1970-01-01（保持 epoch 秒语义，界面时:分:秒正确），真实日期交给「自定义播放时间」而不是猜今天的日期（猜错比显示 1970 更危险）；② 24 h 按**数据时间**而非墙钟（离线回放同样成立，且与「不足 24 h 显示全部」自洽）；③ 「保存曲线」勾选＝配置项（`output.curve_save`，`PUT /api/config` 即时持久化），面板与导出页共用一份，而不是导出时临时勾选——用户要的是「配置功能」；④ 保存给两个入口：服务端写 `output/curves_<ts>/<曲线>.csv`（每曲线一文件，UTF-8-BOM 供 Excel）+ 浏览器下载合并长表；⑤ 热更新一律保留趋势历史与最近结果（含已结束的离线引擎），只有「重新启动数据源」清空
- 2026-10-12｜**踩坑 F-15（功能互相打架）**：功能③的勾选框走 `PUT /api/config` 热更新，而 `EngineRunner.set_cfg()` 对「线程不存活」的引擎整个重建、`LiveEngine.update_config()` 重建 `MetricsCalculator` → 功能②的 24 h 曲线和 `/api/result` 一起清空；单测各绿，连起来点才暴露。修法＝已有引擎一律 `update_config`，`update_config` 搬运 `history` 并按新配置更新 `hours/max_points`；回归 `test_engine_hot_update_preserves_history` / `test_web_curve_save_toggle_persists_and_keeps_history`
- 2026-10-12｜**踩坑 F-16（性能按目标规模实测）**：`History.get` 纯 Python 抽稀在 3 s 样例上无感，按 24 h@0.2 s＝43.2 万点实测 757 ms，6 曲线 / 3 s 轮询会把 2 核吃满；改 numpy 分桶（`linspace` 边界 + `nanargmax/nanargmin`）→ 40 ms。并发：引擎线程 `push` 与 Web 线程 `get`/`del` 切片竞争 → 加 `threading.Lock`；读侧用 `np.array(arr)` 单次拷贝，**不能**用 `np.frombuffer` 视图（`array('d')` 扩容时 `BufferError: cannot resize an array that is exporting buffers`，会打死引擎线程）
- 2026-10-12｜**踩坑（时间格式细节）**：`time_local` 小数部分用 `f"{t%1:.3f}"[1:]` 在 .9998 时进位成 `.000` 但整秒没进位（显示 :40.000 实为 :40.9998）→ 改截断 `int((t%1)*1000)`；`notes()` 会转义 HTML，保存结果里的 `<code>` 会原样显示 → 列表文本不带标签
- 2026-10-10｜历史决策（更早任务，仍有效）：分支策略用平台固定 session 分支；不编造项目事实（`ROLE.md` 背景只作推断引用）；KPI 通用数学定义属数学事实可写死；✅ 必须同行带来源、经验阈值必须显式标「经验推测」

## 关键文件路径
- `BOOTSTRAP.md` / `ROLE.md` — 协议 v2.2 与角色库 v1.4（默认角色：资深电力算法专家）
- `STATUS.md` — 本文件，续接现场唯一入口
- `README.md` — **v0.5**（§3.1 增「趋势曲线＝最近 24 小时＋保存曲线」、§4.2 增「自定义播放时间」与用户格式实测、§8 六层验证）：§0 快速开始、§1 验收对照、**§2 本地部署（详细）**、**§3 运行说明（Web/CLI/库/REST 四种；§3.1 含数据源面板逐源可编辑/置灰字段表、两个保存入口语义对照、空值语义与 6 步手工点检清单）**、**§4 四种数据源详解（配置·三入口·实测·注意事项·验证，含 §4.6 四源对账表与 §4.8 一键复现）**、§5 数据目录、§6 配置结构、§7 输出产物、§8 五层验证、§9 生产推荐流程、§10 台账索引、§11 交付说明
- `REPORT.md` — **v0.5**（新增 C-14 趋势历史保留与抽稀、C-15 无日期时标规则）：稳定结论 C-01~C-08（电气量计算）+ C-09~C-12（四源等价性 / 切换前 drain / float32 禁存 epoch 秒与可诊断降级 / 无硬件验证路径）+ **C-13（界面层验证方法 + 深合并接口空值语义 + 推送覆盖用户输入）**；§3.3 十五类量口径；§5 六条实录教训
- `REPORT_TEST.md` — **v0.5**（新增 **T-004** 第 6 轮四功能：S1~S9 / F-11~F-16 / U6 组）：T-001（待回报）+ T-002（沙盒 A1~A10、B1/B2、用户侧 W/R/P）+ **T-003（沙盒 S1~S18 实录、四源对账表、F-01~F-10 修复、用户侧 S/U/D 三组执行包 + J-\* 判读 + 回收格式）**
- `NILM_DATA_DICT.md` — v0.2（用户已确认 fs/列格式/PT/CT）；另有 v0.1 模板（🔶=116 处；用户已确认的 fs/列格式/PT/CT 待本轮翻 ✅）
- `session/NILM_AC_session_complete.md` — 会话纪要（只追加）
- 代码：`cli.py`（7 子命令入口）、`elec_tool/`（算法核心 + `sources/` + `analysis/`）、`app/server.py` + `app/static/`（Web）、`configs/default.json`（出厂模板）、**`tools/`（tcp_feeder / csv_appender / verify_sources / ui_dropdown_check.cjs / ui_r6_check.cjs）**、`tests/`（**187 项，12 个文件**；第 6 轮＝`test_r6_features.py`）
- 数据与产物（均 gitignore）：`data/`（输入 CSV，`cli.py gen-sample` 可重建样例）、`output/`（导出结果）、`configs/runtime.json`（界面保存的配置）
- 运行环境：`.venv/`（gitignore，沙盒回收后需重建：`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`）
- 分支：`arena/82e34fb8-nilm-calc-tool`（远端同名，已 push；第 5 轮 tip `a88dcaa`；第 6 轮提交＝feat(r6) 代码 / test+tools / docs 三个）｜基点 `main`=`27b28ea`
- live preview：`cli.py serve` 或 `uvicorn app.server:app --host 0.0.0.0 --port 8000`（沙盒内已常驻，`ELEC_TOOL_AUTOSTART=1` + 模拟器源）
