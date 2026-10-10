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
