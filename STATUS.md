# STATUS.md

> 续接文件（BOOTSTRAP.md v2.2 台账）。每次收尾必更新；只改本文件，不另建同类文件。
> 最后更新：2026-10-13（第 12 次收尾：负荷辨识子界面·逐周波事件检测）

## 当前角色
- 角色：**资深电力算法专家**（`ROLE.md` v1.4 指定的默认当前角色）
- 本任务级覆盖：**工程实现工程师**（对「实现电气量计算工具」及其后续界面缺陷修复 / 功能增补任务生效；任务收尾后回归默认角色）
- 生效范围：任务级（非全迭代）
- 默认执行模式：**混合**——沙盒侧（模式 A）写码 + 合成信号解析解自验证 + live preview 实跑，**已有实录**；用户侧（模式 B）Windows 部署 / 真实数据对账 / 生产常驻，**只出执行包，未获实录不下结论**（执行包见 `REPORT_TEST.md` T-002 的 W/R/P 三组）
  - 说明：更早任务用户显式指定过模式 B（仅对「补齐台账骨架」生效）；此后各任务用户均跳过模式澄清，故一律按上述混合模式执行并在此声明。第 5 轮（界面下拉框检查）沙盒侧＝jsdom 驱动真实页面打真实服务端 + REST 空值语义实录，**已✅实录**；用户侧＝浏览器手点 U 组 7 步，**🔶待回报**。**第 6 轮（四功能）**沙盒侧＝pytest 25 项 + jsdom 30 项 + REST/CLI 实录，**已✅实录**；用户侧＝浏览器手点 U6 组 8 步，**🔶待回报**。**第 7 轮（三功能）**沙盒侧＝pytest 18 项 + jsdom 39 项 + CLI/源层实录，**已✅实录**；用户侧＝U7 组 8 步，**🔶待回报**。**第 9 轮（间谐波/直流/事件）**沙盒侧＝pytest 13 项 + jsdom 28 项 + live preview 实跑，**已✅实录**；用户侧＝U9 组 6 步，**🔶待回报**。**第 10 轮（离线列映射开关）**沙盒侧＝pytest 8 项 + jsdom 15 项 + REST 实录，**已✅实录**；用户侧＝U10 组 6 步，**🔶待回报**。**第 11 轮（时标 UTC 开关）**沙盒侧＝pytest 6 项 + 双时区全量 + jsdom 11 项，**已✅实录**；用户侧＝U11 组 5 步，**🔶待回报**。**第 12 轮（负荷辨识）**沙盒侧＝pytest 8 项 + jsdom 16 项 + 引擎/CSV 实录，**已✅实录**；用户侧＝U12 组 5 步，**🔶待回报**

## 当前目标
- **本任务（2026-10-13 第 12 轮，已交付、沙盒侧✅实录）**：用户需求——负荷辨识子界面：① 尽量多的事件检测算法实时检测窗口内周波数据；② 事件含发生时刻、方向、幅度；③ 各算法参数可配；④ 事件保存 CSV（算法类型、起止时间、方向、幅值）。
  - 实现：`elec_tool/nilm.py`（`CycleFeatures` 逐周波 P/Q/I，4 对象；6 算法纯函数 `detect_steps`：threshold / two_window / cusum / glr / steady_state / median_diff；`NilmDetector` 滚动窗重评估 + 终点序号去重 + 确认周波；`NilmWriter` → `output/nilm/nilm_events_<日期>.csv` 18 列）；`config.NilmConfig`（通用 + 相对门槛 `rel_tol_pct/min_delta_pct` + `algorithms` 字典，`from_dict` 合并默认、`validate` 逐参数校验）；引擎 `_ingest` 后 `_detect_nilm`、状态 `nilm_events_total/nilm_cycles`、`info().nilm`；REST `/api/nilm/events|cycles|clear`、WS `nilm_event/nilm_cleared`；前端「🧩 负荷辨识」视图（卡片、周波窗曲线 + `drawLine opt.marks` 事件竖线、事件表 + 过滤、按算法生成的参数表单、徽标）；`tools/gen_nilm_sample.py`
  - 验证：`tests/test_r12_nilm.py` **8 项**；`tools/ui_r12_check.cjs` **16/16**；全量 **257 passed**（4 次中 1 次偶发 1 项失败未复现，F-39 观察）
  - 问题 **F-38**（绝对门槛跨量级失效 / CUSUM 起点提前 / 噪声触发粘连）已修；**F-40**（用户 Windows 回报：`0/00/00` 时标按本地解释后负 epoch → `localtime` OSError → `/api/nilm/events` 500）已修：基准 1970-01-02 + `elec_tool/timefmt.py` 统一安全出口 + 模拟 Windows 的回归 3 项，全量 **260 passed**；2026-10-14 第 14 轮：总线侧+分路侧双数据源（contextvar 代理 RUNNER + ASGI 路径改写，既有接口零改动；联动启停）→ 274 passed；F-42（暂停无效＝文件秒播完；加离线倍速 file_speed、界面默认 1×；资源版本号防旧缓存）→ 270 passed；F-41（播完不自动更新状态）已修 → 266 passed；第 13 轮：离线文件暂停/恢复播放（`/api/engine/pause|resume`，Runner 级 pause_event，仅 csv_file）→ 全量 265 passed；此前追加 `NILM_TUNING_GUIDE.md`（调参手册）+ `tools/nilm_tune.py`（量噪声给参数）+ 2 用例 → 262
  - 文档：README v0.11（§3.1 新小节含算法表与假设、变更记录）；REPORT_TEST **T-010**；REPORT **C-23** + 第 12 次判定
  - 验收状态：沙盒侧 ✅；**用户侧 🔶 待回报**（T-010 U12 组）
  - 假设（已在 README 标注）：对象＝逐周波 P；只做事件检测不做分类；周波按额定频率定长；双滑窗/CUSUM 尖峰特性；幅值＝稳态差
- **上一任务（2026-10-13 第 11 轮，已交付、沙盒侧✅实录）**：用户需求——「离线文件不启用自定义时间时，增加是否使用 UTC 时间配置；不使用 UTC 时曲线上数据时间与文件中的数据时间一致」。
  - 实现：`source.file_time_utc`（默认 false）；`parsing.local_utc_offset_h()/file_tz_offset_h(cfg)`；`create_source/LiveEngine` 的 `tz_offset_h` 默认 None→按配置推导；`_parse_slash_clock` 无日期写法同样减偏移、`_seek_time/_tod_of` 当天时刻按偏移还原；`/api/probe` 增 `file_time_utc/tz_offset_h/t_first_local`、start 白名单、CsvFileSource.info、CLI `--file-time-utc`；界面「文件时标按 UTC 解释」勾选框（csv_file 未自定义时间 / csv_tail 可用），摘要显示解释方式
  - 验证：`tests/test_r11_file_time.py` **6 项**；`tools/ui_r11_check.cjs` **11/11**（服务端 TZ=Asia/Shanghai）；全量 **249 passed** 在 UTC 与 Asia/Shanghai 双时区
  - 问题 **F-36**（无日期写法未减偏移）、**F-37**（旧用例隐含 UTC 假设）已修
  - 文档：README v0.10（§3.1 新小节、§6、§11、变更记录）；REPORT_TEST **T-009**；REPORT **C-22**
  - 验收状态：沙盒侧 ✅；**用户侧 🔶 待回报**（T-009 U11 组）
  - 假设（已在 README 标注）：浏览器与服务端同时区；自定义时间开启时开关不显示但起始时间仍按其解释；偏移按当前时刻取；默认值由「当 UTC」改为「当本地」
- **上一任务（2026-10-13 第 10 轮，已交付、沙盒侧✅实录）**：用户需求——「增加是否启用离线文件数据映射关系配置功能。未启用：默认依次为 时间,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流；启用：只播放有映射关系的列数据」。
  - 实现：`config.ColumnMap` 新增 `mapping_enabled`（默认 false）/ `mapping`（7 字段→列号从 1 起或表头列名，空＝不映射）+ `layout()/looks_like_header()/validate()/unmapped()`；`parsing` 只读已映射列、未映射通道置 0 + note、时间戳未映射按 fs 合成**跨块连续**时间轴（`row_offset`）；`/api/probe`（`mapping_enabled/unmapped/ncols`）、`cli.py probe`、`resample._prescan`（无时间戳映射→可读错误）全部改走 `layout()`；前端「数据源」页「离线文件列映射」面板（开关 + 7 输入 + 填入默认列序 / 按探查表头填入），`collectConfigPayload` 带 `columns`
  - 验证：`tests/test_r10_colmap.py` **8 项**；`tools/ui_r10_check.cjs` **PASS 15 / FAIL 0**；全量 **243 passed, 1 skipped**
  - 问题 **F-33**（合成时间轴每块从 0 起）、**F-34**（识别不出列名的表头被当数据）、**F-35**（拼接 id 触发回归）已修
  - 文档：`README.md` v0.9（§3.1 新小节含规则表与假设、§4.2/§6 配置项、§11、变更记录）；`REPORT_TEST.md` v0.9 **T-008**；`REPORT.md` v0.9 **C-21**
  - 验收状态：沙盒侧 ✅；**用户侧 🔶 待回报**（T-008 U10 组）
  - 假设（已在 README 标注）：未映射通道按 0 不剔除；未启用时可识别表头优先于默认列序；映射对下次启动数据源生效；TCP 源不受影响；`csv_tail` 只认列号
- **上一任务（2026-10-13 第 9 轮，已交付、沙盒侧✅实录）**：用户需求——① 间谐波电气量子界面；② 事件子界面（基波相量/谐波相量/间谐波相量/频率/频率变化率 超限 + 功率振荡）；③ 直流偏置电气量。
  - 实现：`config.py`（`QUANTITY_KEYS` 7→9：`interharmonic`(0.2 s) / `dc`(1 s, 不去直流)；`CURVE_KEYS` 6→8；`EventConfig` 全部阈值 + `limits_secondary` PT/CT 自动折算）；`analysis/harmonic.py` `interharmonic_analysis`（IEC 61000-4-7 组/中心子组/主导相量/TIHD）与 `dc_analysis`（整周期均值/逐周期漂移）；`metrics.py` `_q_interharmonic/_q_dc` + 趋势标量；**`elec_tool/events.py`**（6 类事件状态机：开始/峰值/复归滞回、频率绝对滞回带、阈值热改按新阈值复归、数据时间、`output/events/events_<日期>.csv`）；`engine.py` 接入检测器 + 状态计数；`server.py` `GET /api/events`、`POST /api/events/clear`、WS `type=event`；前端 3 个子界面 + 导航徽标 + 阈值表单
  - 验证：`tests/test_r9_events.py` **13 项**（解析解 1e-9）；`tools/ui_r9_check.cjs` **PASS 28 / FAIL 0**；旧 harness 复跑 dropdown 74/74、r6 30/30、r8 29/29、r7 38/39（1 项 jsdom 时序，改动前后一致，F-31 观察）；全量 **235 passed, 1 skipped**；selftest 44/44
  - 问题 **F-29**（阈值未按 PT/CT 折算 → 一开机 6 条假基波超限）、**F-30**（复归用旧阈值 + 频率相对滞回永不复归）已修；F-31 观察
  - 文档：`README.md` v0.8（§1 ⑤、§3.1 新小节「间谐波 / 直流偏置 / 事件」含**假设与可配置项表**、§3.4 3 接口、§11、变更记录）；`REPORT_TEST.md` v0.8 **T-007**；`REPORT.md` v0.8 **C-19/C-20**
  - 验收状态：沙盒侧 ✅；**用户侧 🔶 待回报**（T-007 U9 组）
  - 假设（已在 README 标注）：间谐波＝IEC 分组单窗值（无 10/15 min 聚合）；直流＝整周期均值；事件默认阈值 110/90% U_nom、6 A、HR 5/10%、THD 5/10%、IH 1/2%、49.5–50.5 Hz、1 Hz/s、功率振荡 0.1–2.5 Hz 峰峰 5%；阈值按二次侧填并自动折算
- **上一任务（2026-10-12 第 8 轮，已交付、沙盒侧✅实录）**：用户需求——新增「数据处理」子界面：对指定路径离线波形 CSV 按指定采样率重采样，输出到 `data/`，文件名＝原名+`_re_`+采样率（`波形_农业排灌_大水泵_80_1.csv` → `波形_农业排灌_大水泵_80_1_re_6400.csv`）
  - 实现：`elec_tool/resample.py`（numpy only：linear 流式分块 / nearest / fft 抗混叠；原采样率推算或手填；时间轴等间隔重建；时标按源写法重生成；表头/列序/编码/BOM 保留；`.part` 原子写；进度/取消句柄）；`app/server.py` `POST/GET /api/process/resample`、`/cancel`、`/preview`（单任务后台线程）；`cli.py resample`；前端「🧮 数据处理」视图（下拉选文件/探查/参数/进度条/结果/用作播放源）
  - 验证：`tests/test_r8_resample.py` **16 项**；`tools/ui_r8_check.cjs` **PASS 29 / FAIL 0**；旧 harness 复跑 39/0、30/0、74/0；全量 **222 passed, 1 skipped**
  - 问题 **F-24~F-28**（fft 周期语义 / 大整数 epoch 精度 / 伪 BOM / `.part` 残留 / 测试轮询竞争）均已修
  - 文档：`README.md` v0.7（§3.1 新小节、§3.2 8 子命令、§3.4 4 接口、变更记录）；`REPORT_TEST.md` v0.7 **T-006**；`REPORT.md` v0.7 **C-18**
  - 验收状态：沙盒侧 ✅；**用户侧 🔶 待回报**（T-006 U8 组）
  - 假设（已在 README 标注）：原采样率默认推算；等间隔时间轴；默认 linear；输出已存在默认拒绝；重采样不改 `sampling.fs`
- **上一任务（第 7 轮，已交付）**：用户 3 点需求——① 计算的曲线数据实时保存到 `output/realtime` 目录 CSV ② 离线文件可指定位置播放 ③ 鼠标移到曲线上显示该位置数据
  - 实现：`elec_tool/realtime_writer.py`（每点追加＋flush、按数据日期分文件、续写不重表头、受 `curve_save` 过滤、`ELEC_TOOL_REALTIME_DIR` 优先）＋ `metrics.curve_record()` 抽成三出口共用；`output.realtime_save/realtime_dir`、`GET /api/realtime`、导出页面板、CLI `--realtime-save/--realtime-dir`；`source.play_start_mode/value`（begin/row/seconds/percent/time）＋ `iter_csv_blocks(skip_rows/start_percent/start_time)` ＋ 超范围 `ParseError` ＋ 界面下拉框联动 ＋ start 白名单 ＋ CLI `--play-from`；`app.js` `bindHover/hoverInfo/drawHover`（所有 canvas，吸附最近点，重绘不丢）
  - 验证：`tests/test_r7_features.py` **18 项**；`tools/ui_r7_check.cjs` **PASS 39 / FAIL 0**（连跑 3 次稳定）；旧 harness 复跑 30/0、74/0；全量 **206 passed, 1 skipped**
  - 问题 **F-17~F-23**（F-22/F-23 为用户真实环境回报，均已修＋回归）（超范围静默 0 样本 / 默认落盘污染仓库目录 / finished≠flush 完成的测试竞争 / 常驻模拟器污染测试目录 / begin 模式送空值）
  - 文档：`README.md` v0.6（§3.1 新小节、§3.4 `/api/realtime`、§4.2 字段＋CLI 示例、§6/§7/§8/§11、变更记录）；`REPORT_TEST.md` v0.6 **T-005**；`REPORT.md` v0.6 **C-16/C-17**＋1 条教训
  - 验收状态：沙盒侧 ✅；**用户侧 🔶 待回报**（T-005 U7 组）
  - 假设（已在 README 标注）：实时落盘默认**开**；「曲线数据」＝6 条趋势曲线标量点；按数据日期分文件；受「保存曲线」勾选过滤；悬停吸附最近点不插值
- **上一任务（2026-10-12 第 6 轮，已交付、沙盒侧✅实录）**：用户 5 点需求——① 离线 CSV 支持 `0/00/00 00:12:40.0000,290.175751,…` 格式 ② 界面所有曲线＝最新 24 小时（不足则全部）③ 每条曲线可分别配置是否保存，保存曲线数据时未勾选项不保存 ④ 离线播放可选「自定义时间」（起始默认文件第 1 条，后续按采样率推算；否则用文件时间）⑤ 完成后验证
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
- **待用户回报的专题**：T-001（环境与数据基线核对，A~D 组）、T-002（本地部署与真实数据验收，W/R/P 组）、T-003（四源复现 S 组 / 真实装置 D 组 / 界面点检 U 组）、**T-004（第 6 轮四功能浏览器点检 U6 组）**、**T-005（第 7 轮三功能点检 U7 组）**——均未获实录
- 范围边界：~~本 session 不写业务代码~~ ❌**已失效**（该边界属上一任务；本任务即为写代码）；仍然遵守：不新建台账外散文件、不把数据/产物入库

## 已完成
- **v0.61**：数据处理页「波形预览」：文件信息 / 原始波形（重采样率、通道、时间段或起点+点数）/ 逐周波有效值曲线 + 右键「显示周波窗」到单独周波窗曲线；`elec_tool/wave_preview.py`、`/api/process/wave/{info,load,rms}`、`test_r61` 4 项、`ui_r61` 23/23、全量 358 passed / 1 skipped。
- **v0.60**：运行目录名改 `yyyyMMdd_HHmmss`；`config_bus/branch.json` 改为本侧配置文件逐字节复制；曲线 / 事件 / 负荷事件仍分 `realtime/ events/ nilm/` 子目录。354 passed / 1 skipped。
- **v0.59**：离线文件播放每次启动新建运行目录 `output/<yyyyMMddHHmmss>/`（两侧共用），实时曲线 / 事件 / 负荷事件 CSV 与 `config_bus.json` / `config_branch.json` / `run_info.json` 都写在里面；`run_dir` 进 start 响应 / state / last_result，`load_last` 读回。全量 354 passed / 1 skipped。
- **v0.58**：实时曲线 / 事件 / 负荷事件 CSV 文件名改按墙钟本地日期（`timefmt.wall_day`），两侧不同数据日期也写同一文件；`load_curves` 去掉按文件名日期跳过。
- **v0.57**：复查修复 `estimate_min_load`：改用"是否在动"掩码切稳态（斜坡/劈半阶跃/纹波都正确），新增 `candidate_from`。
- **v0.56**：`longest_transient` 量最长暂态；>100 周波时 `suggest` 自动放大 `steady_state.max_transient_cycles` / `min_steady_cycles` 并给 `window_cycles`；CLI/界面显示暂态行；`gen_nilm_sample.py --soft-start`。
- **v0.55**：`estimate_min_load` 从分路侧含启停录波的投切台阶估计最小关心负荷；CLI `--min-load-auto`、端点 `min_load_auto`、界面勾选 + 估计行 + 「填入输入框」。
- **v0.54**：调参结果 JSON / 保存文件 `_tuning` / 界面结果区均附带等价 `tools/nilm_tune.py` 命令（`build_cli_command`）。
- **v0.53**：调参面板「保存」＝以本侧原配置文件（runtime.json / branch_runtime.json）为基准只更新算法参数的完整配置，写 `output/nilm/tune_<时间>.json`，原文件不动。
- **v0.52**：「数据处理」页新增「负荷辨识调参」面板（文件/时间段或时长/基准侧/保存勾选+文件名默认 `tune_{时间}.json`），`POST /api/process/nilm_tune`，`run_tune` 入 `elec_tool/nilm_tuning.py`，CLI 新增 `--t-start/--t-end/--duration`。
- **v0.51**：`NILM_TUNING_GUIDE.md` 附录 H：`nilm_tune.py` 命令手册（全部参数 + 9 种用法逐条举例）。
- **v0.50**：nilm_tune 结果一键套用到当前运行配置（`nilm_tune.py --apply`、`POST /api/nilm/tune/apply`、界面「套用 nilm_tune 结果」），更新后的完整配置写 `output/nilm/nilm_tuned_config_*.json`，默认不写配置文件；手册 §3/§7-2′ 同步。
- **v0.49**：`NILM_TUNING_GUIDE.md` 附录 G：六种算法实现流程与参数说明（文档）。
- **v0.48**：负荷辨识页事件列表筛选改为客户端过滤，不再连带改变趋势图/周波窗的事件竖线；三面板选择互相独立。
- **v0.47**：右键菜单复现浏览器原生图片三项并追加业务项，Shift+右键弹原生菜单。
- **v0.46**：趋势曲线右键「显示周波窗」+ 周波窗手动装载（`/api/nilm/cycles_file`、`load_cycles_from_file`），仅非运行状态。
- **v0.45**：`nilm_tune.py` `--quantity` 默认跟随配置 `nilm.quantity`（修复配置为 i 仍输出 W 参数）。
- **v0.44**：负荷辨识页括号提示与标题同一行（inline + 单行省略号）。
- **v0.43**：负荷辨识页括号提示单行（nowrap+省略号），去掉「与总览面板同一曲线」。
- **v0.42**：负荷辨识页三块面板标题栏控件另起一行可换行、事件表单元格不折行（`.nilm-hdr`）。
- **v0.41**：负荷辨识页三块面板标题的括号提示换行（`.hdrhint`）。
- **v0.40**：负荷辨识趋势图去掉标题栏重复的 Ia/Ib/Ic 勾选，三相显隐统一用曲线下方图例。
- **v0.39**：I 口径只能单相（total 忽略/回退 A/B/C，`channels_effective`），趋势图可切三相电流（Ia/Ib/Ic 可选）；nilm_tune/check 配套 `--channel`。
- **v0.38**：`nilm_tune/replay/check` 三脚本支持电流口径（`--quantity`、`--min-load-a`、`--mag-a`、建议 `*_a`），调参手册附录 F。
- **v0.37**：负荷辨识 I 口径改用独立 A 单位阈值（每算法 `*_a` 一套，默认二次侧 ≈6 A 量级，CUSUM h/k 比例保留），W/A 两套按口径二选一、表单灰显不参与的一套。
- **v0.36**：负荷辨识仅电流事件检测——`nilm.quantity` auto/p/i，无电压自动按逐周波 I 检测（六算法可用，W 阈值→相对门槛），事件 quantity/magnitude/unit，列映射识别仅电流表头，p 口径无电压显式告警。
- **v0.35**：重采样输出已存在且要算误差 → 跳过重采样只算误差；任务进度与结果分两步（重采样 / 相对误差）显示。
- **v0.34**：重采样前后相对误差（RMS 相对误差 + 波形 NRMSE），按可配时间窗 `processing.error_window_s` 逐窗写 `<输出名>_err.csv`；界面勾选/窗长输入、CLI `--err-window`。
- **v0.33**：配置 `branch.hide_ui`（数据源页勾选框，即时生效）→ 实时监测 / 事件与分析四个双列页右侧分路侧内容隐藏；分路仍计算落盘；总览 / 跨侧对比不受影响。
- **v0.32**：`run_id` 写入曲线/事件/负荷事件 CSV 与 last_result；重启加载只取上次那一次运行的行（修复同时段多次播放事件混入）。
- **v0.31**：放大状态下在 X / Y 轴刻度带上拖选＝只缩放该轴（绘图区内仍为平移 / Ctrl 框选）；ui_r17 54/54。
- **v0.30**：重启后上次数据加载以 `last_result.t_ref` 为锚点（修复「目录混有更新时标数据 → 上次播放的曲线与负荷事件被滤掉」）；周波窗不恢复给出明确提示；`tools/ui_r30_check.cjs`。
- **v0.29**：曲线放大后可平移坐标轴——拖动图面 / ◀▶▲▼ 按钮 / 方向键 / Alt+滚轮；Ctrl+拖选再放大；`zoomPan/zoomPanFrac`；ui_r17 47/47。
- **v0.28**：谐波 `#h-trend`、间谐波、基波 `#f-u1/i1-trend` 分相趋势线（默认隐藏图例勾选）；功率页改为分相瞬时功率波形 `#p-wave-ph`（服务端放行 `series.p_per_phase`）；总览最新电气量 9 张多行卡片，每行「总线数据 / 分路数据」，U/I 分三相、P/Q/S/PF 分三相+总；ui_r24 53/53，pytest 317 passed。
- **v0.27**：功率因数/基波/谐波/间谐波/直流 曲线记录追加三相分相标量（历史、实时落盘、保存曲线三出口共用；旧表头实时文件轮转 `.pre-v027.csv`）；功率页新增 `#p-trend` P/Q/S 趋势（分相默认隐藏、图例勾选可选）、功率因数页加 PFa/PFb/PFc；`tests/test_r27_phase_curves.py`、ui_r24 44/44。
- **v0.26.1 / v0.26.2**：导航组标题去说明、算法卡片勾选排版；事件落盘卡片长路径换行。
- **v0.26**：导航按用户指定重排为 总览 / 实时监测 / 事件与分析 / 工具 四组。
- **v0.25**：标题/导航/各子界面 h2 按现有功能重写；`unitScale()` 把列表单位统一放表头、单元格只放数字（15 类表）；`tools/ui_r25_check.cjs` 23/23。
- **v0.24**：事件 / 负荷辨识 / 窗口 / 导出也合并为左总线/右分路双列（`SD` 侧别状态、`bindSideViews`、`api(path,opt,side)`）；负荷辨识页 P/Q/S 趋势 + 算法事件标注（默认全部、可勾选）；`tools/ui_r24_check.cjs` 34/34。
- **v0.23**：电气量 9 个子界面合并为「左总线侧 / 右分路侧」双列（`buildDualViews/renderDual`），分路侧未启用时右列与导航分路侧分组隐藏；`tools/ui_r23_check.cjs` 26/26。
- **v0.22.2**：修复 nilm_tune 在基荷小时给出 >100% 的 min_delta_pct 导致保存参数报错；前端/服务端校验文案带字段值与解释。
- **v0.22.1**：总线多设备情形——`nilm_check` 幅值带归属（`--mag-w/--signature-from`、真值 `其它`）、`gen_nilm_sample --bus`、手册路线 A/B 与 §5-B。
- **v0.22**：NILM_TUNING_GUIDE.md 重写为现场实施版 7 步流程；新增 `tools/nilm_replay.py`（离线回放）、`tools/nilm_check.py`（真值对账 + 上线结论）。
- **v0.21.1**：原始数据导出两侧独立——总线侧 / 分路侧各自面板、各自 API 前缀、各自文件 `raw_<起>_<止>_src<sid>.csv`，去掉联动。
- **v0.21（重做版）**：从离线文件 CSV 按时间段切片原始采样行到新 CSV（两侧同文件、尾列 source_id）——`elec_tool/raw_export.py`、`/api/source/export_range`、数据源页面板；原 NILM 周波保留区版 v0.21 已 revert。
- **v0.20.1**：总览分相 Q/S 曲线「散点」修复——去掉虚线样式，改实线 + 量基色亮/原/暗三档。
- **v0.20**：重启后各子界面自动恢复上次运行数据——`output/last_result.json`（两侧共用、source_id 分键）保存最新电气量；启动时 `_autoload_last()` 读回 CSV + 快照；`output.autoload_last` 开关。
- **v0.19**：总览 P/Q/S 趋势增加分相 Pa..Sc 曲线（默认隐藏、图例勾选显示，总 P/Q/S 默认显示）；power 趋势记录新增 9 个分相字段。
- **v0.18**：不播放时「加载上次数据」——从 realtime/events/nilm 三条落盘 CSV 按 source_id 读回曲线点/事件/负荷辨识事件；`POST /api/history/load_last`；两侧按钮；test_r18 4 项。
- **v0.17.3**：配置界面排版规范化（勾选框对齐 / 说明文字独立行 / 左标签右输入框两列）——`normalizeConfigForms()` + CSS，不改 id。test_web_ui 15、ui_r16 31、ui_r17 36 通过。
- **v0.17.2**：实时落盘/事件/负荷辨识 CSV 两侧共用同一文件（分路侧目录强制＝总线侧，共享文件锁），不再有 `output/branch/`。全量 296 passed/1 skipped。
- **v0.17.1**：保存曲线时分路侧数据与总线侧写同一个 `<曲线>.csv`（source_id 区分、按时间排序），不再建 `branch/`。ui_r17 36/36、全量 296 passed/1 skipped。
- **v0.17**：离线文件两侧各自「指定时间段播放」（起止留空＝数据起点/终点，公共时间段优先并新增结束时间 `common_end`）；所有折线图 X/Y 独立缩放 + 拖选区间 + 双击复位；所有 CSV 增 `source_id`（0 总线 / 1 分路，服务端强制），保存曲线时分路侧一并写 `branch/`。test_r17 8 项、ui_r17 35/35、ui_r16 31/31、ui_r14 56/56、全量 pytest 296 passed/1 skipped。
- **v0.16**：数据源与控制页左总线/右分路两列同行布局（仅启用分路侧时显示右列）；分路侧 4 种输入方式与总线侧同构、任意组合同时启动；曲线分线显示开关（`output.series_hidden` 持久化）；总览分路侧曲线状态栏同总线侧。ui_r16 31/31、ui_r14 56/56、全量 pytest 288 passed/1 skipped。
- **v0.15.4**：大文件播放起点快速定位（时标字节二分 / 行号字节计行，结果与顺序扫一致，提速 15～45×）。全量 pytest 283 passed/1 skipped、ui_r14 56/56。
- **v0.15.3**：修「离线文件启动后很久才开始」——公共时间段自动起止泄漏进活配置/持久化 → 只进引擎 + 加载清理 + `_file_time_range` 提速 10×。全量 pytest 281 passed/1 skipped、ui_r14 56/56。
- **v0.15.2**：总览面板总线侧/分路侧曲线分列独立画布（不同轴）。ui_r14 56/56（连跑 2 次）、全量 pytest 280 passed/1 skipped。
- **v0.15.1**：公共时间段坐标轴固定、两侧共享节拍钟严格同步（按各自采样率、互锁）、先播完一侧停刷另一侧继续；附带修复首块过大 / 空转睡眠 / state() 死锁 / full=false 并集。ui_r14 55/55（连续 2 次）、ui_r12 16、ui_r13 12、全量 pytest 279 passed/1 skipped。执行模式：混合模式（用户未指定）；角色：工程实现工程师（任务级）。
- **v0.15**：增量刷新、两侧倍速一致、总览两侧合并显示、公共时间段播放 + 自定义起始时间（顶栏显示）。ui_r14 51/51、ui_r12 16、ui_r13 12、全量 pytest 275 passed/1 skipped（`test_tcp_binary_frames` 在全量下偶发、单测稳定通过，与本轮改动无关）。
- **v0.14.4**：顶栏分总线侧/分路侧两行显示，分路侧只显示不切换。ui_r14 40/40、全量 pytest 275 passed/1 skipped。
- **v0.14.3**：总览面板增加分路侧最新电气量卡片 + 四张趋势图。ui_r14 38/38、全量 pytest 275 passed/1 skipped。
- **v0.14.2**：离线文件列映射分总线侧/分路侧独立配置与保存。ui_r14 37/37、全量 pytest 275 passed/1 skipped。
- **第 15 轮补充（v0.14.1）**：分路侧配置集中到数据源页、两侧徽标实时、跨侧对齐/差值（`/api/compare`）+「跨侧对比」页、顶栏对侧状态胶囊常显、两侧量纲口径分别保存。ui_r14 36/36、全量 pytest 275 passed/1 skipped。
- **第 15 轮（v0.14）**：导航三分组「总览 / 总线侧 / 分路侧」（+「工具」），侧别随导航分组切换；总览面板两侧状态卡；ui_r14 27/27、ui_r12 16/16、ui_r13 12/12、全量 pytest 274 passed/1 skipped。执行模式：混合模式（用户未指定）。
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
- [x] 2026-10-13 **F-32 热修**（用户回报：事件多时告警弹窗刷屏）：`onEventPush` 去掉逐条 toast，只更新徽标/事件页；回归 28/28
- [x] 2026-10-13 **第 9 轮三功能**：间谐波（IEC 分组）/ 直流偏置 / 事件（6 类）三个子界面 + `events.py` + REST/WS + CSV 落盘；`tests/test_r9_events.py` 13 项 + `tools/ui_r9_check.cjs` PASS 28 + 全量 235 passed；提交 `8539d8a`（feat）+ docs
- [x] 2026-10-12 **第 7 轮三功能**：曲线实时落盘 `output/realtime/<曲线>_<日期>.csv` / 离线播放起点（5 模式）/ 曲线悬停取值；`tests/test_r7_features.py` 18 项 + `tools/ui_r7_check.cjs` PASS 39 + 旧 harness 30/74 + 全量 **204 passed, 1 skipped**；README v0.6 / REPORT_TEST T-005 / REPORT C-16、C-17

## 进行中
- 等用户执行 **T-007 的 U9 组**（浏览器手点 6 步：样例事件分布与徽标 → 热改阈值复归 → 间谐波页 → 直流页 → 真实文件事件分布 → 事件 CSV）并回报实录
- 等用户执行 **T-006 的 U8 组**（浏览器手点 5+2 步：真实文件探查 → 重采样 6400 → 文件表头/时标核对 → 覆盖保护与 fft → 用作播放源并对账 RMS）并回报实录
- 等用户执行 **T-005 的 U7 组**（浏览器手点 8 步：实时落盘文件与行数 → 勾选过滤 → 开关关/开续写 → 真实文件跳过 60 s / 指定时刻 / 90% → 悬停浮框 → 可选过夜换文件）并回报实录
- 等用户执行 **T-004 的 U6 组**（浏览器手点 8 步：真实 0/00/00 文件探查 → 不开/开自定义时间启动 → 勾选保存框与 F5 保持 → 保存曲线数据查 output/ → 跑 ≥10 min 看曲线标题跨度；可选过夜看 24.00h 与内存）并回报实录
- 等用户执行 **T-003 的 U 组**（浏览器手点 7 步，约 5 分钟：回填/联动置灰/binary 帧字段/启动出数/脏值保护/口径保存/可选 node 脚本）并回报实录
- 等用户执行 **T-003 的 S 组**（无硬件复现四源验证，约 10 分钟）与 **D 组**（真实采集 CSV / 真实 TCP 协议）并回报实录
- 等用户执行 T-002 的 W/R/P 组（Windows 部署 / 真实数据对账 / 生产常驻）并回报实录

## 下一步（TODO）
1. **用户侧（阻塞项，模式 B）**：先跑 **T-007 的 U9 组**、**T-006 的 U8 组**、**T-005 的 U7 组**与 **T-004 的 U6 组**（用真实采集文件，期望见 `REPORT_TEST.md`），再跑 T-003 的 **S 组**（`python tools/verify_sources.py` 期望 PASS 5 / FAIL 0；`pytest tests/ -q` 期望 **204 passed**；两个终端跑 tcp_feeder / csv_appender + `cli.py live` 期望缺口 0），**T-003 的 U 组**（浏览器手点 7 步，界面下拉框，期望见 `REPORT_TEST.md`），再跑 T-002 的 W 组（Windows 部署，预计 10 分钟）与 R 组（真实数据对账，核心验收），按「结果回收格式」贴回；P 组（生产常驻）可选
2. Agent 侧（收到实录后）：把三件套写入 T-002「结果 / 结论」，按 J-\* 逐条对账，回填 `README.md` §2/§3/§4 与 `NILM_DATA_DICT.md` 的 🔶 项（注明来源＋日期）
3. **待确认口径**：电压列是相电压还是线电压（`transform.voltage_input`）、真实编码与时间戳格式、PT/CT 实际值、实时落地方式（文件 or TCP 协议文档）
4. 若验收方要求 IEC 口径：另立专题实现 IEC 61000-4-7 的 10/15 分钟聚合（分组平方和已随 v0.8 间谐波实现）——当前谐波/间谐波均为整周期单窗值
4b. **T-007 遗留**：事件单级固定阈值（无持续时间门槛/分级/动态阈值）；功率振荡只看 P 总、可分辨上限受 power 步长限制；ROCOF 分辨率＝fundamental 步长；事件 CSV 无轮转
5. TCP 实时源联调：`--frame/--struct-fmt/--struct-fields` 三处已可配（CLI/界面/REST 白名单），文本帧与二进制帧均已用喂数器验证；**仍需现场协议文档**确认帧头帧尾/长度字段/缩放系数/时标类型；若协议含帧头+长度+校验，需在 `sources/tcp_stream.py::_flush_block` 加拆帧（`DataSource` 接口不变，上层零改动）
5b. TCP 的 `timeout_s` / `reconnect_s`（各默认 2.0 s）目前只是构造参数，未暴露到配置文件与界面——待现场联调时按需提升为配置项
5c. `csv_tail` 目录模式按 mtime 选最新文件；若现场分片命名与 mtime 不一致（如补写旧分片），需改成按文件名排序——待 T-003 的 D-5 回报后决定
6. 是否需要 Qt 桌面壳（本轮决策 Web 优先）——等用户表态
7. `TUNING_GUIDE.md` 仍未创建：待用户真实数据回报后，把「窗长/口径/变比怎么选」写成调参教学（BOOTSTRAP 规定该文件整篇重写、不追加流水，空骨架无意义）
8. T-001 的 B6 / C6 / D1~D7 仍未回报（其中 fs、列格式、PT/CT 已由本轮需求描述实质回答）
9. 可选增强（当前为单机工具形态）：用户/权限、历史入库（数据库）、报警推送、多测点并行
11. **T-005 遗留**：实时落盘无大小/天数轮转（快量约 40 MB/天/文件）；percent 模式跳过行数未知、time 模式只取第一次 ≥ 目标；播放起点只对 `csv_file` 生效；悬停不插值、各曲线各取最近点；「不落盘但手工保存」需关总开关
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
- 2026-10-12｜**决策（第 8 轮）**：① 重采样时间轴按**等间隔原采样率**重建而不逐行用原时标（采集器 0.1 ms 量化会被插值放大成波形失真）；② 默认 `linear` 流式（大文件内存安全），`fft` 作为抗混叠选项并明示整文件载入；③ 时标按源写法重生成（用户 `0/00/00` 文件输出仍是 `0/00/00`，播放链路零改动）；④ 输出已存在默认拒绝、需勾选覆盖；⑤ 单任务后台线程＋轮询进度（与引擎线程互不干扰）。踩坑 F-24~F-28 见 REPORT_TEST T-006
- 2026-10-12｜**踩坑 F-23（用户回报）**：离线播放时顶栏「样本」/数据源汇总冻结需手动刷新。根因 `/ws` 只在队列空闲 1s 才发 state，连续 result 流下永不触发；修为单调时钟每 1s 必发（`WS_STATE_INTERVAL_S`）；教训：周期性状态推送需独立时间判据，测试要在连续流下断言
- 2026-10-12｜**踩坑 F-22（用户回报，首个来自真实环境的缺陷）**：127.0.0.1 正常、局域网 IP 访问页面纵向无限拉伸。根因 `prep()` 每次回读 `getAttribute('height')`，而 `cv.height = h*dpr` 会改写该属性 → dpr≠1 时复利放大；两个地址差异＝浏览器按主机名记忆的缩放级别。修法缓存 `data-h`；教训：jsdom 默认 dpr=1，界面测试需显式覆盖 dpr≠1
- 2026-10-12｜**决策（第 7 轮）**：① 实时落盘**默认开**（用户明确要这个功能；关掉只需一个开关），目录 `output/realtime`，`ELEC_TOOL_REALTIME_DIR` 环境变量优先（测试隔离/现场指到数据盘）；② 落盘与界面趋势、手工保存**共用 `curve_record()` 与 `curve_save`**，三处数字必须对得上；③ 按**数据时间**日期分文件（与 24h 曲线按数据时间同一口径；0/00/00 文件落到 1970 文件名，真实日期靠自定义播放时间）；④ 播放起点给四种定位而不是只给行号：现场最常用的是「跳过前 N 秒」和「从某时刻开始」，percent 给大文件 O(1) 跳转；⑤ 悬停吸附最近点、不插值（显示的必须是真实算出的点）
- 2026-10-12｜**踩坑 F-19（状态位≠工作完成）**：`finished=true` 后运行线程还要 `flush_all`（收尾强算＋入历史＋落盘），测试立刻数行就偶发 `4 == 3`，只在全量跑时复现。等待条件要对准最后一个副作用；本轮在 r6/r7 的 `_wait_finished` 与 jsdom 脚本里置位后再等一拍并重读
- 2026-10-12｜**踩坑 F-18/F-20（默认开启的副作用要可隔离）**：默认落盘让每个测试/工具往仓库 `output/realtime/` 写文件 → env 优先级 + conftest autouse 夹具；jsdom 脚本切目录时预览进程里常驻的模拟器把「今天日期」文件写进测试目录 → 脚本先 stop 引擎再切
- 2026-10-12｜**踩坑 F-15（功能互相打架）**：功能③的勾选框走 `PUT /api/config` 热更新，而 `EngineRunner.set_cfg()` 对「线程不存活」的引擎整个重建、`LiveEngine.update_config()` 重建 `MetricsCalculator` → 功能②的 24 h 曲线和 `/api/result` 一起清空；单测各绿，连起来点才暴露。修法＝已有引擎一律 `update_config`，`update_config` 搬运 `history` 并按新配置更新 `hours/max_points`；回归 `test_engine_hot_update_preserves_history` / `test_web_curve_save_toggle_persists_and_keeps_history`
- 2026-10-12｜**踩坑 F-16（性能按目标规模实测）**：`History.get` 纯 Python 抽稀在 3 s 样例上无感，按 24 h@0.2 s＝43.2 万点实测 757 ms，6 曲线 / 3 s 轮询会把 2 核吃满；改 numpy 分桶（`linspace` 边界 + `nanargmax/nanargmin`）→ 40 ms。并发：引擎线程 `push` 与 Web 线程 `get`/`del` 切片竞争 → 加 `threading.Lock`；读侧用 `np.array(arr)` 单次拷贝，**不能**用 `np.frombuffer` 视图（`array('d')` 扩容时 `BufferError: cannot resize an array that is exporting buffers`，会打死引擎线程）
- 2026-10-12｜**踩坑（时间格式细节）**：`time_local` 小数部分用 `f"{t%1:.3f}"[1:]` 在 .9998 时进位成 `.000` 但整秒没进位（显示 :40.000 实为 :40.9998）→ 改截断 `int((t%1)*1000)`；`notes()` 会转义 HTML，保存结果里的 `<code>` 会原样显示 → 列表文本不带标签
- 2026-10-10｜历史决策（更早任务，仍有效）：分支策略用平台固定 session 分支；不编造项目事实（`ROLE.md` 背景只作推断引用）；KPI 通用数学定义属数学事实可写死；✅ 必须同行带来源、经验阈值必须显式标「经验推测」

## 关键文件路径
- `BOOTSTRAP.md` / `ROLE.md` — 协议 v2.2 与角色库 v1.4（默认角色：资深电力算法专家）
- `STATUS.md` — 本文件，续接现场唯一入口
- `README.md` — **v0.8**（§3.1 增「间谐波 / 直流偏置 / 事件 子界面」小节含假设与可配置项表、§3.4 `/api/events*` 与 WS `event`、§11 第 9 轮；v0.7：§3.1 增「数据处理子界面：离线波形 CSV 重采样」小节、§3.2 8 子命令、§3.4 4 个 `/api/process/resample*` 接口；v0.6：§3.1 增「实时落盘＋播放起点＋悬停取值」小节、§3.4 `/api/realtime`、§4.2 播放起点字段与 CLI、§8 七层验证）：§0 快速开始、§1 验收对照、**§2 本地部署（详细）**、**§3 运行说明（Web/CLI/库/REST 四种；§3.1 含数据源面板逐源可编辑/置灰字段表、两个保存入口语义对照、空值语义与 6 步手工点检清单）**、**§4 四种数据源详解（配置·三入口·实测·注意事项·验证，含 §4.6 四源对账表与 §4.8 一键复现）**、§5 数据目录、§6 配置结构、§7 输出产物、§8 五层验证、§9 生产推荐流程、§10 台账索引、§11 交付说明
- `REPORT.md` — **v0.8**（新增 C-19 间谐波分组分辨率前提、C-20 事件状态机四规则；v0.7：新增 C-18 重采样时间轴/时标规则；v0.6：新增 C-16 三出口共用提取规则与按日期分文件、C-17 播放起点定位代价与可诊断）：稳定结论 C-01~C-08（电气量计算）+ C-09~C-12（四源等价性 / 切换前 drain / float32 禁存 epoch 秒与可诊断降级 / 无硬件验证路径）+ **C-13（界面层验证方法 + 深合并接口空值语义 + 推送覆盖用户输入）**；§3.3 十五类量口径；§5 六条实录教训
- `REPORT_TEST.md` — **v0.8**（新增 **T-007** 第 9 轮间谐波/直流/事件：S1~S7 / F-29~F-31 / U9 组；v0.7：新增 **T-006** 第 8 轮数据处理子界面：S1~S7 / F-24~F-28 / U8 组；v0.6：新增 **T-005** 第 7 轮三功能：S1~S4 / F-17~F-21 / U7 组）：T-001（待回报）+ T-002（沙盒 A1~A10、B1/B2、用户侧 W/R/P）+ **T-003（沙盒 S1~S18 实录、四源对账表、F-01~F-10 修复、用户侧 S/U/D 三组执行包 + J-\* 判读 + 回收格式）**
- `NILM_DATA_DICT.md` — v0.2（用户已确认 fs/列格式/PT/CT）；另有 v0.1 模板（🔶=116 处；用户已确认的 fs/列格式/PT/CT 待本轮翻 ✅）
- `session/NILM_AC_session_complete.md` — 会话纪要（只追加）
- 代码：`cli.py`（8 子命令入口，含 `resample`）、`elec_tool/`（算法核心 + `sources/` + `analysis/` + `resample.py` 离线重采样 + **`events.py` 事件检测**）、`tools/ui_r9_check.cjs`（间谐波/直流/事件 28 项端到端）、`tests/test_r9_events.py`、`tools/ui_r8_check.cjs`（数据处理子界面 29 项端到端）、`tests/test_r8_resample.py`、`app/server.py` + `app/static/`（Web）、`configs/default.json`（出厂模板）、**`tools/`（tcp_feeder / csv_appender / verify_sources / ui_dropdown_check.cjs / ui_r6_check.cjs / ui_r7_check.cjs）**、`tests/`（**236 项，15 个文件**；第 9 轮＝`test_r9_events.py`）、**`elec_tool/realtime_writer.py`**
- 数据与产物（均 gitignore）：`data/`（输入 CSV，`cli.py gen-sample` 可重建样例）、`output/`（导出结果）、`configs/runtime.json`（界面保存的配置）
- 运行环境：`.venv/`（gitignore，沙盒回收后需重建：`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`）
- 分支：`arena/82e34fb8-nilm-calc-tool`（远端同名，已 push；第 9 轮提交＝`8539d8a`（feat）+ docs；第 8 轮提交＝`a6fd42d`（feat）+ `b6c7ca6`（docs）；第 6 轮 tip `f1966e8`；第 7 轮提交＝`f0fdea6` feat(r7) / `341fc9e` test(r7) / docs）｜基点 `main`=`27b28ea`
- live preview：`cli.py serve` 或 `uvicorn app.server:app --host 0.0.0.0 --port 8000`（沙盒内已常驻，`ELEC_TOOL_AUTOSTART=1` + 模拟器源）
