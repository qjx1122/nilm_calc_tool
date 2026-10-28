# 负荷辨识 · 新设备接入与事件检测调参手册（现场实施版）

> **给谁看**：工程师、运维、交付、现场实施——**不需要懂算法**。
> **需要会什么**：① 复制粘贴 PowerShell 命令；② 用 Excel 打开 / 另存 CSV；③ 看懂"开 / 关"。
> **能做到什么**：把一个从未见过的新设备，从"只有两份 CSV"开始，一步步配好 6 种事件检测算法的参数，并**用数字判断它能不能上线**。
> **配套脚本**（都在仓库 `tools/` 下，本手册会告诉你每一步敲什么）：`nilm_tune.py`（量噪声给参数）、`nilm_replay.py`（离线回放跑检测）、`nilm_check.py`（和真实开关表对账、出结论）。
> 正文按**有功 P（W）**口径写；数据源**只有电流**时三个脚本自动按电流 I（A）口径工作，差异见**附录 F**。
> 想看算法推导的同学直接跳到 [附录 E](#附录-e进阶参数是怎么算出来的)。

---

## 0. 先搞懂 3 句话

1. **软件在看什么**：它把电流电压算成"每 20 毫秒一个点的有功功率 P"（叫**一个周波**）。设备**开**，P 突然**升**一个台阶；设备**关**，P 突然**降**一个台阶。6 种算法都是在找这种台阶，只是找法不同。
2. **调参调的是什么**：只有两个概念——
   - **台阶多高才算事件**（参数名里带 `min_delta`）：填小了把噪声当事件（**误报**），填大了把真设备漏掉（**漏报**）。
   - **多"平"才算平稳**（参数名里带 `tol` / `noise` / `drift`）：这个由数据里的噪声决定，**脚本会替你量出来**，你不用猜。
3. **怎么知道配对了**：拿一段**明知道设备什么时候开、什么时候关**的数据回放一遍，软件报出来的开关时刻和你知道的一一对上、而且没有多报，就是配对了。本手册的 `nilm_check.py` 会直接打印 ✅ / ⚠ / ✗。
4. **检测 ≠ 归属**：软件报的是"总线上有一个台阶"，不是"是这台设备"。在**设备自己的支路**上两者一回事；在**总线**上，别的设备开关也会报出来——它们**不是误报**，要靠"台阶多高"（设备指纹）把它们分开。所以本手册分两条路：**路线 A 分路侧**（简单，优先）和**路线 B 总线侧**（多一步"取指纹"）。§1 会告诉你走哪条。

5. **v0.90 新增第 7 种算法「设备画像匹配」（`profile`）——唯一一个会写"是哪台设备"的算法**：先在**设备自己的支路**录几次开/关，提取成一份"设备画像"（JSON 文件），再让总线侧拿每个台阶的 ΔIa/ΔIb/ΔIc/ΔP/ΔQ/启动冲击/持续时间去和画像比，像的才报，并给出**置信度**；不像的（其它设备）直接拒识。它把路线 B 里"靠幅值带离线归属"这一步搬到了线上，适合**总线上有多台设备、但待检设备特征与别家差异明显**的场景。详见 **§5-C**、附录 A 末行、附录 G.9、附录 C 第 6 条、H.14。

> **单位提醒（最常见的坑）**：所有阈值的单位都是 **W（瓦）**。如果配置里启用了 PT/CT 变比（`transform.enabled=true`），阈值要按**一次侧**填（比如 1 台 500 kW 的电机就是 500000）；没启用就按二次侧 W 填。脚本的输出会告诉你当前是哪种口径，照抄即可。

---

## 1. 开工前准备清单

| # | 要准备的东西 | 从哪里来 | 没有怎么办 |
|---|---|---|---|
| A | **总线侧背景文件** `bus_bg.csv`：进线处录的 30 s ~ 10 min 波形 CSV，**最好**没有设备开关 | 软件数据源页「导出指定时间段的原始数据」（总线侧面板）切一段，或采集装置直接导出 | 有零星开关也能用（脚本用的是抗干扰统计），见 §3 的 ⚠ 说明 |
| B | **设备侧带启停文件** `dev_onoff.csv`：这台新设备支路（或总线）录的、**里面有它至少 2 次开、2 次关**的波形 CSV | 同上，分路侧面板切一段 | 至少要 1 开 1 关；越多次结论越可靠 |
| C | **真值表** `truth.csv`：设备每次开 / 关的真实时刻（看操作记录 / 盯现场记下来 / 看分路电流曲线读出来） | 用 Excel 填，§4 有模板 | 没有真值表就没法判断能否上线——这是**必备**项 |
| D | **PT / CT 变比、采样率** | 现场接线图 / 采集装置参数 | 样例数据：PT=100、CT=15、6400 Hz |
| E | 一台装好本软件的 Windows 电脑（PowerShell）或 Linux 机器 | 见 `README.md` §安装 | — |

CSV 格式与数据源一致：`时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流`，时间戳可以是 `0/00/00 09:12:30.1234` 这种只有时刻的写法。

**先选路线（只问两个问题）：**

| 问题 | 答"是" | 答"否" |
|---|---|---|
| Q1 这台设备有**自己的支路**接了采集（分路侧）？ | **路线 A**：全部步骤用分路侧文件、推到分路侧（§7 用 `/api/branch/config`）。总线上别的设备与你无关。 | 看 Q2 |
| Q2 只能在总线上检：总线上**其它设备的功率**与这台设备相差 ≥ 30 %？（看铭牌即可） | **路线 B**：§3–§5 先用设备侧文件做一遍拿"指纹"，再用总线文件做一遍并带指纹对账（§5-B）。 | **总线侧无法区分这台设备与功率相近的那台**——软件只看台阶高度。要么加装分路采集走路线 A，要么接受"报的是这两台之一"。 |

> 路线 B 还有一个硬限制：待检设备开关的 **±0.2 s 内恰好有别的设备动作**时，两个台阶叠在一起，那一次无法单独识别（对账时会表现为"漏报"或幅值不对）。真值表里这种次数多（> 10 %），换一段数据。

**文件放哪**：把 A、B、C 三个文件拷到软件目录的 `data\` 文件夹里（下文命令都假设软件装在 `D:\nilm_calc_tool`，请按实际路径改）。

---

## 2. 第一步：打开 PowerShell、进入软件目录

```powershell
# 开始菜单搜 "PowerShell"，右键"以管理员身份运行"不是必须的，普通打开即可
cd D:\nilm_calc_tool
.\.venv\Scripts\python.exe --version     # 看到 Python 3.x 就对了
```

> Linux / macOS 把下文所有 `.\.venv\Scripts\python.exe` 换成 `.venv/bin/python`，路径里的 `\` 换成 `/`。
> 若提示"无法加载脚本 / 禁止运行"，本手册的命令**不需要**激活 venv，直接用上面的完整路径调用 python 即可绕过。

---

## 3. 第二步：量噪声，拿到一套"起点参数"

```powershell
# 把 bus_bg.csv 换成你的总线侧背景文件；--min-load-w 填这台设备的额定有功（W，一次侧口径）
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --config configs\default.json --min-load-w 300000
```

屏幕会打印两块内容，你只需要看 **3 个地方**：

```
文件 data/bus_bg.csv  对象 total  周波 15000  时长 300.0 s  口径 一次侧(PT/CT)      ← ① 口径：和你填的 --min-load-w 单位要一致
—— 噪声统计（W）——
  基荷 |P| 中位数        level      = 1.5e+06
  单周波噪声 σ(稳健)     sigma      = 28.3  (0.002 % 基荷)                        ← ② σ：数据有多"毛"，后面所有容差都从它来
  相邻周波最大 |ΔP|      max|diff|  = 7.5e+05   ⚠ >10σ：段内含事件/尖峰，统计已用稳健口径   ← 有 ⚠ 说明这段里有开关，见下方说明
  ...
—— 建议参数（起点，按 NILM_TUNING_GUIDE.md 复核）——
  min_delta_w = max(最小关心负荷/2, 6σ)                                            ← ③ 这一行若出现 ⚠，设备太小检不出来，见下
  nilm.rel_tol_pct = 0.05   nilm.min_delta_pct = 0.01
  threshold     min_delta_w=150000  settle_cycles=5  settle_tol_w=150 ...
  （后面 5 行是另外 5 种算法的建议，不用看懂）
```

**然后把建议存成文件**（机器可读，后面的步骤直接用它，不用手抄）：

```powershell
New-Item -ItemType Directory -Force output | Out-Null
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --config configs\default.json --min-load-w 300000 --json > output\tune.json
```

**（v0.52）不想开命令行？** 同样的功能在 Web 界面「🧮 数据处理 → 负荷辨识调参」里：选波形文件（或手填路径）→ 可选填**起始时间 / 结束时间（或时长）**（都留空＝整个文件；v0.73 可勾选「启用自定义时间」：与波形预览同一套——时间轴＝自定义起始时间 + 行号/采样率，文件时长＝数据点数 / 采样率，起止写法 `2026-10-12 08:00:00` / epoch 秒 / `08:00:00`；CLI 对应 `--custom-time --custom-time-start --custom-time-end`）→ 基准配置（v0.72 默认**独立基准配置**：出厂配置 + 本页的 fs / f_nom / PT·CT / 时标 UTC，与两侧运行配置互不关联、可单独修改，并写到 `output\nilm\nilm_tune_base.json` 供 `--config` 复现；也可改选沿用总线侧 / 分路侧运行配置，决定 PT/CT 与列映射；此时检测量 / 检测对象随该侧 `nilm.quantity` / `nilm.channels[0]`，界面上不可改，只有独立基准配置下可单独选择）→ 填最小关心负荷 → 「量噪声并给出参数」。结果表与本节命令输出一一对应；勾选「保存为配置文件」才会在基准配置（独立基准配置，或所选侧原配置文件 `runtime.json` / `branch_runtime.json`）基础上只更新算法参数、其它不变，把完整配置写到 `output\nilm\`（文件名可填，默认 `tune_{时间}.json`，默认**不保存**，原配置文件不改动）；「套用到运行配置」＝ §7-2′ 的一键热生效（v0.72 由「套用目标」下拉选总线侧 / 分路侧，与基准配置无关）。详见附录 H.13。

**（v0.50）想一步到位、直接得到"套好参数的完整配置"**：加 `--apply`。脚本会在**当前运行配置**（`--config` 指定的文件；不填时取界面保存的 `configs\runtime.json`，没有则 `configs\default.json`）基础上只替换 `nilm.quantity / rel_tol_pct / min_delta_pct` 和 6 种算法的建议参数，其余（PT/CT、列映射、输出目录、各算法 `enabled`、建议里没给的键）一律保留，把更新后的**完整配置**写到输出目录 `output\nilm\nilm_tuned_config_<时间戳>.json`；**默认不改配置文件本身**：

```powershell
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --config configs\default.json --min-load-w 300000 --apply
#   末尾多出一段「—— 已更新配置（--apply）——」：基准配置 / 已保存到 output\nilm\nilm_tuned_config_20261021_103000.json / 配置文件 未改动
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --min-load-w 300000 --apply --out output\site_tuned.json   # 自定义输出文件
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --config configs\site.json --min-load-w 300000 --apply --save-config
#   --save-config 才会把更新后的配置**回写到 --config 那个文件**（显式要求才做；运行中的软件要重新加载才生效）
```

写出的文件是完整配置，可以直接 `--config output\nilm\nilm_tuned_config_xxx.json` 给 `nilm_replay.py` 回放核对（§5 不再需要 `--params`），或作为软件启动配置（`ELEC_TOOL_CONFIG_PATH`）。文件末尾带 `_tuning` 元信息（来源文件、对象、时间、改了哪些项），软件加载时忽略它。`--json` 与 `--apply` 可以同时用，JSON 里多一个 `applied` 字段（`saved_to / changes / config_file_updated`）。

**怎么判断这一步的结果靠不靠谱：**

| 看到什么 | 含义 | 怎么办 |
|---|---|---|
| ③ 处写 `min_delta_w = max(最小关心负荷/2, 6σ)`，无 ⚠ | 设备幅值远大于噪声，好检 | 继续 |
| ③ 处写 `⚠ 最小关心负荷 … 的一半低于噪声底 …` | **这台设备太小，淹没在总线噪声里**，在总线侧基本检不出来 | 改在**分路侧**检（用 `dev_onoff.csv` 重新跑本步骤，分路噪声小得多）；仍有 ⚠ 则该设备不适合上线 |
| `max|diff|` 行有 ⚠ | 背景段里混了开关 | 可以用（见下），但建议把 `bus_bg.csv` 从中间切成两半各跑一次，两次 `sigma` 相差 < 20% 就放心 |
| `sigma_cycle_pct` > 1 % | 噪声异常大 | 检查采样率 / 列映射是否配错（`README.md` §数据源）；波形有缺口也会这样 |

> **背景段里有别的设备开关可以用吗？** 可以。σ 用的是"中位数"类统计，几次开关只污染几个点，不影响结果。前提是开关是"偶发"的（粗略：30 s 的段里不超过 7 次，5 min 的段里不超过 70 次），而且段内多数时间处于同一基荷。反例：变频器一直在调速、电机一直在软启动——这种"一直在变"的段换一段再量。

---

## 4. 第三步：用 Excel 填真值表

新建 Excel，按下面填，**另存为 → "CSV UTF-8 (逗号分隔)"** → 文件名 `truth.csv` 放到 `data\`：

| 时间 | 动作 | 备注 |
|---|---|---|
| 2026-10-15 09:12:30 | 开 | 1# 空压机 |
| 2026-10-15 09:20:05 | 关 | 1# 空压机 |
| 09:35:10 | 开 | 1# 空压机（只写时刻也行） |
| 09:41:00.5 | 关 | 1# 空压机 |

规则：
- 第 1 行是表头，随便写；从第 2 行开始每行一次动作。
- 「时间」：精确到秒（能到 0.1 s 更好）。只写 `时:分:秒` 时按数据文件里的日期补齐。
- 「动作」：`开` / `关`（也认 on/off、投入/切除、1/0）。路线 B 时，**已知的其它设备动作**写 `其它`（备注写是哪台）——对账时这些时刻的事件归"其它设备"，不算误报；不知道的不用写，靠指纹（§5-B）兜底。
- 「备注」随意，会原样出现在对账结果里。
- 时间对不准怎么办？打开软件 → 数据源页播放 `dev_onoff.csv` → 「负荷辨识」页看周波 P 曲线，台阶出现的时刻就是真值；或 Excel 打开 `dev_onoff.csv` 看电流列突然变大 / 变小的那行的时间戳。

---

## 5. 第四步：回放 + 对账（核心一步）

```powershell
# 5-1 用建议参数回放设备侧文件，6 种算法同时跑，事件写到 output\replay_events.csv
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\dev_onoff.csv --config configs\default.json --params output\tune.json --out output\replay_events.csv

# 5-2 和真值表对账（时刻允许差 1 秒；想严一点改 --tol-s 0.5）
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\replay_events.csv --truth data\truth.csv --tol-s 1 --out output\replay_check.csv
```

5-1 打印每种算法报了几条事件（↑投入 / ↓切除）；5-2 打印**结论表**，长这样：

```
  算法            真值  命中  漏报  误报   命中率  结论
  threshold         4    4    0    0   100%  ✅ 可上线   (阈值差分)
  two_window        4    4    0    1   100%  ⚠ 有 1 条误报：调高 min_delta_w / 容差，或核对误报时刻是否为其它设备
  cusum             4    4    0    0   100%  ✅ 可上线
  glr               4    3    1    0    75%  ✗ 漏 1 条：调低 min_delta_w（不低于 6σ），或加长 window/pre/post
  steady_state      4    4    0    0   100%  ✅ 可上线
  median_diff       4    4    0    0   100%  ✅ 可上线
—— 设备特征（命中事件的 |ΔP| 均值，W）——
  threshold      2.96e+05 （4 次）          ← 这就是软件"看到"的设备功率，应接近铭牌 × 功率因数
—— 总结论 ——
  ✅ 4 种算法全部命中且 0 误报（threshold, cusum, steady_state, median_diff）：该设备可以上线；建议生产只保留这几种，其余关闭。
```

- **命中**：真值时刻 ±1 s 内报了同方向（开→↑ / 关→↓）的事件。
- **漏报**：真值时刻附近什么都没报。
- **误报**：报了事件，但真值表里没有这次动作。**先别急着调参**——用 Excel 打开 `output\replay_check.csv`，看"误报"行的事件时间，去现场记录核对：很可能是**别的设备**真的在那一刻动了（真值表漏写了），那就补进真值表重跑 5-2，不用改参数。
- `output\replay_check.csv` 是逐条明细（算法 / 真值时间 / 结果 / 事件时间 / ΔP / ΔQ / 时刻误差），Excel 打开按"结果"列筛选即可。

### 5-B 路线 B（总线侧，还有其它设备在启停）：带指纹对账

不带指纹直接对账总线文件，其它设备的每次开关都会被算成"误报"，**没有一种算法能 ✅**——这是正常现象，不是参数错了，**不要去调参**。按下面做：

```powershell
# ① 先在设备侧文件上做 5-1 / 5-2（拿到 ✅ 后，output\dev_events.csv 里命中事件的 ΔP/ΔQ 就是这台设备的"指纹"）
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\dev_onoff.csv --config configs\default.json --params output\tune.json --out output\dev_events.csv
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\dev_events.csv --truth data\truth_dev.csv --tol-s 1

# ② 回放总线文件（真值表 truth_bus.csv 只写这台设备在总线段里的开/关，已知的其它设备写"其它"）
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\bus_onoff.csv --config configs\default.json --params output\tune.json --out output\bus_events.csv

# ③ 带指纹对账：指纹自动取自 ① 的命中事件（--signature-truth 是设备侧文件自己的真值表）
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\bus_events.csv --truth data\truth_bus.csv --tol-s 1 --signature-from output\dev_events.csv --signature-truth data\truth_dev.csv --mag-tol-pct 30 --out output\bus_check.csv
#    没有设备侧文件、只知道铭牌：手填指纹（W，计算口径；例 500 kW 电机 PF 0.9 → 450000）
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\bus_events.csv --truth data\truth_bus.csv --tol-s 1 --mag-w 450000 --mag-tol-pct 30
```

③ 的结论表多一列 **"其它设备"**：ΔP 不在指纹 ±30 % 带内（或匹配到 `其它` 真值行）的事件都计在这里，**不算误报**；"误报"列只剩**带内**的——那才是真要调参的。首行会打印"幅值带 X~Y W"，`output\bus_check.csv` 里"结果"列能看到每条事件被归到了哪一类（命中 / 漏报 / 误报 / 其它设备(带外) / 其它设备(真值)）。

**带宽怎么定**：默认 ±30 %。其它设备里最接近的那台功率与待检设备差 D %，带宽取 **< D/2**（例：差 50 % → 取 20 %）；差 < 30 % 的就是 §1 Q2 说的"无法区分"。

### 5-C 路线 C（v0.90，总线侧，在线归属）：设备画像匹配算法

路线 B 是"6 种算法先报所有台阶，再离线用幅值带挑出这台设备"。路线 C 把这件事做成**第 7 种在线算法 `profile`**：设备侧录波 → 画像文件 → 总线侧只报与画像相似的事件，事件表里直接写 `device_id · 置信度`。**前提与路线 B 相同**：必须有一段**设备自己支路**的录波（含 ≥ 2 次开、≥ 2 次关，建议 ≥ 3 次、不同日期 / 工况），并且这台设备和总线上其它设备的"长相"（ΔP、ΔQ、三相分配、启动冲击、暂态时长）有明显差别。

**第 ① 步 提取画像**（设备侧文件 + 真值表，表格式同 §4，动作写 开/关 或 on/off / start/stop 都行）：

```powershell
# --labels 可以是真值表 CSV，也可直接写文本 "08:00:02,开;08:00:32,关"；不给 --labels ＝自动定位（稳态分段 + 自适应参数，ΔP>0 当启动、<0 当停止）
# --pre / --post：事件前 / 后各取多少周波算"稳态"（默认 10 / 50；--post 必须 ≥ 设备启动过程时长，电机软启 2 s → --post 120）
.\.venv\Scripts\python.exe tools\nilm_profile.py --file data\dev_onoff.csv --device pumpA --labels data\truth_dev.csv --config configs\default.json --pre 10 --post 50 --out output\nilm\profile_pumpA.json
# 期望输出（节选）：
#   设备画像已写出：output\nilm\profile_pumpA.json
#     设备 pumpA  口径 W  周波 1000  标签方式 labels  前后窗 10/50
#     启动画像：3 次事件  持续 15~17 周波
#         d_p         μ=      500.0  σ=     75.0      ← μ＝3 次的中心值，σ＝离散度（样本少时按 15 % 中心值给下限）
#         peak_ratio  μ=        1.6  σ=     0.48      ← 启动冲击峰值 / 稳态台阶（1.0＝没有冲击）
#     停止画像：3 次事件  持续 1~1 周波
#     ⚠ 启动画像只有 1 次事件：σ 按相对下限给出，建议采集 ≥3 次独立启停   ← 出现这行就再录几次
```

看三件事：(a) 启动 / 停止各 ≥ 2 次事件、起点时刻与真值表吻合（逐事件一行，`label:08:00:02` 为标签来源）；(b) `d_p` 的 μ 与铭牌功率 × 功率因数同量级、三次之间 σ 不离谱（σ/μ > 30 % 说明有一次定位错了或工况差异大，去看那一行）；(c) 没有 ⚠。画像与总线侧**检测量口径必须一致**（总线侧按 P 检测就用 P 口径画像；只有电流的数据源两边都用 I 口径，`--quantity i`）。

**第 ② 步 总线侧回放验证**（把画像路径写进配置，开启 `profile`；其它 6 种算法可以同时开着——它们照常报所有台阶，`profile` 只报这台设备）：

```powershell
# 配置里：nilm.profile_path = "output/nilm/profile_pumpA.json"，nilm.algorithms.profile.enabled = true（可用 --set 临时覆盖）
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\bus_onoff.csv --config configs\default.json --set nilm.profile_path=output/nilm/profile_pumpA.json --set profile.enabled=1 --out output\bus_events.csv
# 期望：各算法事件数表里 profile 一行只有这台设备的开 / 关次数；其它 6 行 = 总线上所有设备的开关数之和
#   profile           2     1     1  500 ~ 500   设备画像匹配
# 对账：真值表只写这台设备 → profile 行直接按普通方式对账即可，不需要 --signature-*：
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\bus_events.csv --truth data\truth_bus.csv --tol-s 1
#   结论表按算法一行一行列，只看 profile 那一行 ✅/⚠/✗（其它 6 行照例把别的设备算成"误报"，忽略或按 5-B 带指纹对账）
```

`bus_events.csv` 里 `profile` 事件多出 6 列：`device_id`、`confidence`（0~1）、`d2`（与画像的马氏距离平方，越小越像；≈ 维数 7 时相当于平均偏 1σ）、`profile_direction`（START/STOP）、`status`（`confirmed` 干净命中 / `low_confidence` 被接受但带标记）、`quality_flags`（`state_mismatch` 状态机不合理 / `ambiguous_direction` 启动停止分不清 / `trajectory_deviates` 启动轨迹形状不像）。

**第 ③ 步 不达标怎么调**（只改一个参数，改完回到 ②；全部在 `nilm.algorithms.profile`，界面「负荷辨识」页同名）：

| 现象 | 看什么 | 改什么 |
|---|---|---|
| 这台设备的开/关**漏报** | 界面画像面板「最近候选」或 `summary.profile.last`：该时刻候选存在但 `rejected[d2_exceeds]` → 看 `contrib` 哪一维贡献最大 | 那一维在总线侧确实和设备侧不同（最常见：总线侧 ΔQ 被别的无功补偿吃掉、三相分配不同）→ 先用更多次启停重做画像让 σ 变大；仍不行把 `d2_max` 9 → 16 |
| 候选**根本没出现** | `last` 里没有该时刻 | 台阶没过候选门槛：`k_sigma` 4 → 3；或画像 `d_p` 比总线上这台设备的实际增量大很多（设备侧电流 ≠ 总线增量）→ 用总线侧录波重做画像（见下"画像从哪一侧取"） |
| 报出的是**别的设备**（误报） | 误报行 `confidence` 很高说明两台设备长得一样——方法局限，到分路侧 | 置信度中等（0.3~0.6）→ `min_confidence` 0.3 → 0.5；`d2_max` 9 → 4 |
| 开关方向反了 / `ambiguous_direction` | 启动与停止画像太像（无冲击的纯阻性设备） | 正常现象：方向由 ΔP 符号兜底；`margin` 1.5 → 1.2 放宽，或忽略该标记 |
| 连续两次 START、`state_mismatch` | 上一次 STOP 漏了（状态机卡在 ON） | 先解决 STOP 漏报；临时可 `state_check=0` 关状态机 |

**画像从哪一侧取**：方案与本工具都**不做**设备侧 ↔ 总线侧的幅值校准（事件只给 `observed_delta_p`，`estimated_device_delta_p` 恒为 null）。设备侧与总线侧之间有变压器 / 无功补偿 / 线路损耗时，ΔP、ΔQ、ΔI 会系统性不同——这时**用总线侧一段"只有这台设备在动"的录波来提画像**（`tools/nilm_profile.py --file data\bus_only_pumpA.csv ...`）效果更好，设备侧录波只用来确认标签时刻。

**与路线 B 的关系**：两者可以同时用——`profile` 在线给归属与置信度，`nilm_check.py` 离线用幅值带复核；上线打勾清单（§8）里路线 C 的要求见倒数第 3 项。

---

## 6. 第五步：不达标怎么调（只改一个，改完回到 §5 重跑）

每次**只改一个参数**，用 `--set 算法.参数=值` 叠加在建议参数上，**不用手工编辑任何文件**：

```powershell
# 例：threshold 漏报 → 把它的最小台阶从 150000 降到 100000
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\dev_onoff.csv --config configs\default.json --params output\tune.json --set threshold.min_delta_w=100000 --out output\replay_events.csv
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\replay_events.csv --truth data\truth.csv --tol-s 1
```

**症状 → 动作对照表**（参数值参考 `output\tune.json` 里的建议值和 `sigma`）：

| 症状（nilm_check 的结论） | 最可能的原因 | 改哪个（每种算法对应的名字） | 改多少 |
|---|---|---|---|
| 6 种**全部**"全漏" | 单位 / 口径填错（二次侧 W 当一次侧填、或反过来） | 重做 §3，核对 `口径` 字样与 `--min-load-w` | — |
| 6 种**全部**"全漏"，口径没错 | 设备幅值 < 6σ（§3 ③ 有 ⚠） | 换**分路侧**数据检；或接受"该设备不可检" | — |
| 某算法**漏报** | 台阶门槛偏高 | 该算法的 `min_delta_w` | 每次 ×0.7，**不低于 6×sigma** |
| 某算法漏报，且设备是**慢启动**（电机、风机 > 1 s 才稳） | 暂态比窗长 | `two_window.pre_cycles/post_cycles`、`glr.window_cycles` 调到 ≥ 暂态周波数（1 s = 50 周波）；`threshold/median_diff.max_rise_cycles` ≥ 暂态周波数；`steady_state.max_transient_cycles` ≥ 暂态周波数 | 按暂态时长换算 |
| （总线侧）6 种都有好几条"误报"，且误报时刻的 ΔP 与待检设备明显不同 | **其它设备在动，不是误报** | **不要调参**：走 §5-B 带指纹对账（或把已知动作写成 `其它`） | — |
| 某算法**带内误报**，误报时刻**没有**任何设备动作 | 门槛偏低 / 容差偏小 | 先调 `min_delta_w` ×1.5；仍误报再调容差：`threshold/median_diff.settle_tol_w`、`steady_state.tol_w` ×1.5，`cusum.threshold_w` ×1.5，`glr.threshold` 25→40 | 一次一个 |
| 带内误报时刻**确有**其它设备动作 | 那台设备功率与待检设备相近 | 真值表写 `其它`；若经常发生 → 总线侧无法区分，见 §1 Q2 | — |
| 漏报的那一次，±0.2 s 内有其它设备动作 | 两个台阶叠加 | 不调参；该次不计，换一段数据复核 | — |
| 同一次开关被报成 **2 条**（相隔 < 0.5 s） | 暂态被当成两次 | `nilm.min_gap_cycles` 10→25；或 `settle_cycles` 5→10 | — |
| 事件报出来**幅值明显偏小**（只有铭牌的一半） | 前后稳态窗没覆盖完暂态 | `settle_cycles` 5→10；`two_window.post_cycles` 10→25 | — |
| 只在大负荷时段误报 | 基荷大、相对容差 1% 太粗 | `nilm.rel_tol_pct` 1.0→0.2（§3 建议值通常已经给了） | — |

关掉某种算法：`--set glr.enabled=0`。改总开关参数：`--set nilm.rel_tol_pct=0.2`、`--set nilm.min_gap_cycles=25`。

**停止条件**：至少 **2 种**算法 ✅（命中 100% 且 0 误报）。不必追求 6 种全 ✅——生产上只开达标的几种即可。

---

## 7. 第六步：把参数写进生产（Web 界面）

### 7-1 把最终参数存成配置文件

把 §6 里最后一次成功的那条 `nilm_replay.py` 命令，**原样再加上** `--save-config output\site.json` 跑一遍：

```powershell
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\dev_onoff.csv --config configs\default.json --params output\tune.json --set threshold.min_delta_w=100000 --set glr.enabled=0 --save-config output\site.json --out output\replay_events.csv
```

### 7-2 推送给正在运行的软件（不用重启）

软件地址按实际改（下例为本机 8000 端口）。**总线侧**推 `/api/config`，**分路侧**推 `/api/branch/config`——两侧参数独立，设备在哪一侧检就推哪一侧：

```powershell
$cfg  = Get-Content output\site.json -Raw -Encoding UTF8 | ConvertFrom-Json
$body = [System.Text.Encoding]::UTF8.GetBytes((@{ nilm = $cfg.nilm } | ConvertTo-Json -Depth 10))
# 总线侧：
Invoke-RestMethod -Method Put -Uri http://localhost:8000/api/config -ContentType 'application/json; charset=utf-8' -Body $body | Select-Object ok
# 分路侧（设备支路）：
Invoke-RestMethod -Method Put -Uri http://localhost:8000/api/branch/config -ContentType 'application/json; charset=utf-8' -Body $body | Select-Object ok
```

看到 `ok : True` 即生效（参数热更新，不清历史事件）。软件默认会把界面改动持久化到 `configs\runtime.json`，重启后仍在。

### 7-2′（v0.50）直接套用 `tune.json`——界面或 `POST /api/nilm/tune/apply`

不想手工拼 `nilm` 片段时，可把 §3 的 `output\tune.json`（`nilm_tune.py --json` 的原始输出）**原样**交给软件，由软件在**当前侧正在运行的配置**基础上更新算法参数：

* **界面**：「负荷辨识」→「检测参数」→ 底部「套用 nilm_tune 结果」选择 `tune.json` → 「套用到当前配置」。表单立即回填、参数热生效，提示行给出更新后的完整配置落在哪（`output\nilm\nilm_tuned_config_<bus|branch>_<时间戳>.json`）。**默认不写配置文件**（提示「配置文件未改动」）；勾选「同时写入配置文件」才回写 `configs\runtime.json`（或分路侧 `branch_runtime.json`）。
* **命令行**：

```powershell
$body = Get-Content output\tune.json -Raw -Encoding UTF8
$body = [System.Text.Encoding]::UTF8.GetBytes('{"params": ' + $body + ', "hot": true, "persist": false}')
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/nilm/tune/apply -ContentType 'application/json; charset=utf-8' -Body $body | Select-Object ok, saved_to, config_file_updated
# 分路侧改 /api/branch/nilm/tune/apply；"persist": true 才回写配置文件；"hot": false 只写文件、不改运行参数
```

返回 `changes`（逐项改了什么）、`saved_to`（输出目录里的完整配置文件）、`config`（更新后的运行配置）。`params` 可以是整份 `tune.json`、其中的 `suggest` 片段，或 `{"nilm": {...}}`；只有 `quantity / rel_tol_pct / min_delta_pct / algorithms.<算法>.<已知参数>` 会被采用，其它键忽略；非法值（如 `glr.threshold=0`）返回 400 且不改任何东西。

> 与 7-1/7-2 的关系：7-1 是「回放微调后定稿」的路径（`nilm_replay.py --save-config`），7-2′ 是「量完噪声直接套用起点参数」的快捷路径；两者都不会自动替你改 `configs\default.json`。

### 7-3 在界面上确认

打开浏览器 → 左侧导航「负荷辨识」（总线侧 / 分路侧各一个）→ 下方「检测参数」：各算法的数值应与 `output\site.json` 一致，关掉的算法勾选框为空。
再用数据源页播放一遍 `dev_onoff.csv`（离线文件、不限速），「负荷辨识」页事件表里应出现与 §5 相同的事件；表里每行有 `算法 / 方向 / 幅值 / 起止时间`，与真值表核对一次。

---

## 8. 第七步：能不能上线——打勾清单

全部打勾才算"可上线"；任何一项打叉，回到对应章节。

- [ ] §3 建议行**没有** ⚠（设备幅值 ≥ 噪声底）—— 否则该设备在该侧不可检
- [ ] 真值表 ≥ **2 开 2 关**（越多越可信）
- [ ] §5 对账：至少 **2 种**算法 ✅（命中 100%、误报 0）
- [ ] 换**另一段**包含该设备开关的数据（不同日期 / 不同时段）再跑一次 §5，结论仍 ✅ —— 防止参数只对一段数据有效
- [ ] 用一段**不含**该设备开关的长数据（≥ 10 min）跑 §5-1 并对账（真值表只写表头、路线 B 带指纹），达标算法的**带内**事件数应为 0 —— 验证不会误报（总线上其它设备的事件不算）
- [ ] （路线 B）待检设备指纹与总线上其它设备的功率相差 ≥ 30 %，且 `bus_check.csv` 中"其它设备"行的 ΔP 确实都明显偏离指纹 —— 否则总线侧无法区分，必须到分路侧
- [ ] （路线 C）画像启动 / 停止各 ≥ 3 次事件且无 ⚠；§5-C ② 回放中 `profile` 行命中 100%、误报 0，命中事件 `status` 全为 `confirmed`、`confidence` ≥ 0.8；用一段不含该设备开关的总线数据回放，`profile` 行事件数为 0（其它设备的台阶全部被拒识）
- [ ] "设备特征 |ΔP|" 与铭牌功率 × 功率因数同一量级（相差 < 30 %）—— 否则口径或变比可能错
- [ ] §7 已推送、界面「检测参数」与 `site.json` 一致，重启软件后仍一致
- [ ] 把 `output\site.json`、`output\tune.json`、`data\truth.csv`、`output\replay_check.csv` 四个文件归档到项目资料里（下次调参 / 排障的依据）

---

## 附录 A：6 种算法一句话 + 各自参数怎么填

> 所有算法共用：`enabled`（开关）、`min_delta_w`（**台阶多高才算事件**，W）。下表只列各自独有的。"建议值"指 `nilm_tune.py` 给的起点。

| 算法 | 人话解释 | 擅长 / 不擅长 | 独有参数（含义 → 怎么填） |
|---|---|---|---|
| `threshold` 阈值差分 | 相邻两个点一跳超过门槛就算开始，之后连续几个点"平"了算结束 | 干净的阶跃最准最快；怕尖峰 | `settle_cycles`（几个点平了算结束，默认 5）；`settle_tol_w`（多平算平，= 建议值）；`max_rise_cycles`（最多等多久变平，≥ 暂态周波数） |
| `median_diff` 中值滤波差分 | 先把尖刺抹掉再做阈值差分 | 同上但不怕尖峰 | 多一个 `median_cycles`（抹尖刺窗，默认 5；暂态很长的设备可到 9） |
| `two_window` 双滑窗均值差 | 比较"前 10 个点平均"和"后 10 个点平均" | 噪声大时稳；两次开关挨太近会合并 | `pre_cycles`/`post_cycles`（窗长，≥ 暂态周波数、≤ 两次开关最小间隔）；`k_sigma`（均值差要超过几倍噪声，默认 3，误报多改 4） |
| `cusum` 累积和 | 把偏离累加起来，累到门限就报 | 能捉**慢慢爬升**的负荷 | `drift_w`（多小的偏差忽略，= 建议值）；`threshold_w`（累到多少报，= 建议值；误报 ×1.5） |
| `glr` 广义似然比 | 统计学意义上"前后两段是不是两个不同平均值" | 对噪声尺度最敏感、最"讲理" | `window_cycles`（看多宽，默认 15）；`threshold`（门限，无单位，回放 15~25，无人值守 30~50）；`noise_w`（= 量出的 σ） |
| `steady_state` 稳态分段 | 先把曲线切成一段段"平的"，相邻两段平均值差多少就是事件 | 幅值最准；暂态超长会丢 | `tol_w`（多平算一段，= 建议值）；`min_steady_cycles`（至少平几个点，默认 10）；`max_transient_cycles`（两段之间最多允许多长暂态，≥ 暂态周波数） |
| `profile` 设备画像匹配（v0.90） | 拿每个台阶前后的 ΔIa/ΔIb/ΔIc/ΔP/ΔQ/启动冲击比/持续周波 这 7 个数，和事先录好的这台设备"画像"比，像的才报，并给**置信度**和**设备 ID** | 总线上多台设备时**只报这一台**、能分开/关；设备侧录波必不可少；两台长得一样的设备分不开；不做幅值校准 | **默认关闭**；`nilm.profile_path`（画像文件，§5-C ① 生成）；`d2_max`（每维平均允许偏几个 σ²，默认 9＝平均 3σ；漏报放大、误报缩小）；`min_confidence`（最低置信度，默认 0.3；误报多 → 0.5）；`k_sigma`（候选台阶要超过前窗噪声几倍，默认 4；候选缺失 → 3）；`margin`（启动/停止 D² 比至少多少才算方向明确，默认 1.5）；`lambda_rel`（协方差收缩，默认 0.1，一般不动）；`state_check`（1＝启用 OFF→开 / ON→关 状态机，默认 1）。**不受「自适应算法参数」影响**，`nilm_tune.py` 也不给它建议值——它的"噪声尺度"来自画像的 σ |

**全局参数**（`nilm.*`）：

| 参数 | 含义 | 建议 |
|---|---|---|
| `channels` | 检测对象：`total` 三相总有功 / `A` `B` `C` 分相 | 三相设备用 `total`；单相设备用它所在的相 |
| `window_cycles` | 算法只看最近多少个点（默认 300 = 6 s） | ≥ 2 × 暂态周波数 + 100；电机软启动 2 s → ≥ 300 |
| `min_gap_cycles` | 同一算法两次事件最小间隔（默认 10 = 0.2 s） | 重复报 → 调大；快速连续投切 → 调小 |
| `rel_tol_pct` | 容差至少是基荷的百分之几（默认 1.0） | 基荷大、设备小时降到 0.1~0.3；`nilm_tune` 会给 |
| `min_delta_pct` | 最小台阶至少是基荷的百分之几（默认 0） | 一般用 `nilm_tune` 给的值 |
| `profile_path`（v0.90） | 设备画像 JSON 路径（相对软件目录），只给 `profile` 算法用 | 由 `tools/nilm_profile.py` 或界面「数据处理 · 设备画像提取」生成；空＝即使勾了 `profile` 也不检测（界面与 summary.notes 会提示） |

**检测 ≠ 归属（再强调一次）**：6 种标量算法在线只做"事件检测"，界面「负荷辨识」页的事件表里**不会**写是哪台设备；把事件归到设备是 `nilm_check.py` 用幅值带做的离线辅助。总线上多台设备时，线上看到的事件数 = 所有设备的开关数之和，这是正常的。**唯一例外是 `profile`**（v0.90）：它只报与画像相似的事件，事件表「检验量」列写 `设备 ID · 置信度 (D², 标记)`——但它也只是"相似性匹配"，不是物理上的唯一辨识（§5-C）。

---

## 附录 B：常见报错与现象

| 现象 | 原因 | 处理 |
|---|---|---|
| `无法将".\.venv\Scripts\python.exe"识别…` | 不在软件目录，或没装 venv | `cd D:\nilm_calc_tool`；按 README 安装 |
| `没有读到整周波数据` | 文件太短 / 列映射错 / 采样率配错 | `.\.venv\Scripts\python.exe cli.py sources --file data\xxx.csv` 探查；文件至少 1 s |
| `真值表「动作」不认识` | 动作列写了别的字 | 只写 开/关 |
| `真值表只写了时刻、事件文件又为空` | 回放一条事件都没有，无法补日期 | 真值表至少一行写完整日期；同时说明门槛太高（§6） |
| `--signature-from … 在真值时刻附近没有事件` | 设备侧回放还没 ✅ 就拿来取指纹，或 `--signature-truth` 的时刻与设备侧文件对不上 | 先把设备侧 §5 做到 ✅；指纹真值表用设备侧文件自己的时刻 |
| 总线对账"其它设备"列很大、"命中"也全对，但指纹带外还有几条 ΔP 和待检设备差不多 | 总线上有功率相近的其它设备 | 见 §1 Q2：总线侧无法区分 |
| nilm_check 全是漏报，但界面播放明明能看到台阶 | 真值表时间与文件时间轴差了固定值（时区 / 日期） | 用界面「负荷辨识」页读台阶时刻重填真值表；或回放加 `--custom-time-start "2026-10-15 09:00:00"` 对齐 |
| 事件幅值是铭牌的 100 倍 / 百分之一 | PT/CT 口径 | 检查 `transform.enabled` 与变比；`--min-load-w` 要同口径 |
| 保存参数报 `nilm.min_delta_pct 必须在 0~100` | 把 W 值填进了百分比框；或旧版 `nilm_tune` 在基荷很小（设备侧文件）时给出了 >100 的值 | `min_delta_pct` 是「占基荷的百分比」，只用绝对值就填 0；W 级门槛填各算法的 `min_delta_w`。重新跑一次 §3 生成 tune.json 即可 |
| 中文乱码 | Excel 打开 CSV 未识别 UTF-8 | 本工具输出带 BOM，Excel 可直接双击；若仍乱码用"数据 → 从文本/CSV → UTF-8" |
| PowerShell 里 `ConvertTo-Json` 后参数丢了一层 | Windows PowerShell 5 默认深度 2 | 命令里必须带 `-Depth 10`（§7-2 已带） |

---

## 附录 C：命令速查（复制整段即可）

```powershell
cd D:\nilm_calc_tool
# 1 量噪声（总线侧背景；--min-load-w = 设备额定有功 W，一次侧口径）
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --config configs\default.json --min-load-w 300000 --json > output\tune.json
# 2 回放设备侧文件
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\dev_onoff.csv --config configs\default.json --params output\tune.json --out output\replay_events.csv
# 3 对账
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\replay_events.csv --truth data\truth.csv --tol-s 1 --out output\replay_check.csv
# 4 微调（示例）后重复 2、3
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\dev_onoff.csv --config configs\default.json --params output\tune.json --set threshold.min_delta_w=100000 --out output\replay_events.csv
# 1′（v0.50）量噪声并直接生成套好参数的完整配置（写到 output\nilm\，不改配置文件；回写加 --save-config）
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --config configs\default.json --min-load-w 300000 --apply
#    之后回放可直接 --config output\nilm\nilm_tuned_config_<时间戳>.json，不用 --params
# 5 定稿 + 推送
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\dev_onoff.csv --config configs\default.json --params output\tune.json --set threshold.min_delta_w=100000 --save-config output\site.json --out output\replay_events.csv
# 6（v0.90）设备画像：设备侧录波 + 真值表 → 画像 JSON；总线侧回放只看 profile 行（详见 §5-C）
.\.venv\Scripts\python.exe tools\nilm_profile.py --file data\dev_onoff.csv --device pumpA --labels data\truth_dev.csv --config configs\default.json --out output\nilm\profile_pumpA.json
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\bus_onoff.csv --config configs\default.json --set nilm.profile_path=output/nilm/profile_pumpA.json --set profile.enabled=1 --out output\bus_events.csv
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\bus_events.csv --truth data\truth_bus.csv --tol-s 1      # 只看 profile 行
# 5′（v0.50）把 tune.json 直接套到运行中的软件（当前侧运行配置为基准；persist=false 不写配置文件）
$body = [System.Text.Encoding]::UTF8.GetBytes('{"params": ' + (Get-Content output\tune.json -Raw -Encoding UTF8) + ', "persist": false}')
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/nilm/tune/apply -ContentType 'application/json; charset=utf-8' -Body $body | Select-Object ok, saved_to
$cfg = Get-Content output\site.json -Raw -Encoding UTF8 | ConvertFrom-Json
$body = [System.Text.Encoding]::UTF8.GetBytes((@{ nilm = $cfg.nilm } | ConvertTo-Json -Depth 10))
Invoke-RestMethod -Method Put -Uri http://localhost:8000/api/branch/config -ContentType 'application/json; charset=utf-8' -Body $body | Select-Object ok
```

想先用自带样例走一遍流程（1 分钟）：

```powershell
.\.venv\Scripts\python.exe tools\gen_nilm_sample.py                      # 生成 data\nilm_steps.csv：2.0 s 开(+500 W 二次侧)、4.4 s 关(-300 W)、3.0 s 一个尖峰
"时间,动作,备注`n2026-10-13 08:00:02,开,样例`n08:00:04.4,关,样例" | Set-Content data\truth_sample.csv -Encoding UTF8
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\nilm_steps.csv --min-load-w 300000 --json > output\tune.json
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\nilm_steps.csv --params output\tune.json --out output\replay_events.csv
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\replay_events.csv --truth data\truth_sample.csv --tol-s 0.5
```
期望：6 种算法全部 ✅（用出厂默认参数回放时 `two_window` 会把 3.0 s 的尖峰误报 1 条——这正是"先量噪声再定参数"的意义）。

再走一遍**路线 B**（总线上还有别的设备）：

```powershell
.\.venv\Scripts\python.exe tools\gen_nilm_sample.py --bus                # data\nilm_bus_mixed.csv：待检 2.0 s 开/6.0 s 关(±500 W)；其它 3.5 s +1500、8.0 s −1500、5.0 s +120 W
"时间,动作,备注`n2026-10-13 08:00:02,开,待检`n08:00:06,关,待检" | Set-Content data\truth_bus.csv -Encoding UTF8
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\nilm_bus_mixed.csv --out output\bus_events.csv
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\bus_events.csv --truth data\truth_bus.csv --tol-s 0.5                      # 不带指纹：每种算法 3 条"误报"，无一 ✅
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\bus_events.csv --truth data\truth_bus.csv --tol-s 0.5 --mag-w 750000      # 带指纹(500 W × PT·CT 1500)：其它设备 3 条、误报 0，6 种 ✅
```

---

## 附录 F（v0.38）：数据源只有电流、没有电压——按电流 I 调参

> 适用：CSV 只有三相电流列（电压列未映射或全为 0）、或 Web 界面 `nilm.quantity` 选了 `i`。此时有功 P 恒为 0，**所有 `*_w`（W）参数都不生效**，
> 软件改用逐周波**电流有效值 I（A）**做检测，参数换成每种算法各自的 `*_a`（A）一套：`min_delta_a / settle_tol_a / tol_a / drift_a / threshold_a / noise_a`。
> 其它参数（窗长、周波数、`k_sigma`、GLR 门限 `threshold`、`rel_tol_pct`、`min_delta_pct`）两种口径共用。

**步骤与 §3～§7 完全一样，只是单位从 W 换成 A**（三个脚本都已支持，自动按文件/事件的口径切换）：

```powershell
# 1 量噪声：没有电压时 --quantity 默认 auto 会自动按 I 统计；--min-load-a = 设备额定电流（A，一次侧口径；铭牌 kW 换算：I ≈ P / (√3 × U线 × PF)）
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg_i.csv --config configs\default.json --min-load-a 30
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg_i.csv --config configs\default.json --min-load-a 30 --json > output\tune_i.json
#   第 1 行会写「检测量 电流有效值 I（数据源无电压，auto 自动选 I）」；建议行是 min_delta_a= / settle_tol_a= …，并带 nilm.quantity = i
#   若写成 --quantity p 会直接报错退出（有功恒为 0，无法按 P 调参），不会给出一套没意义的 W 参数
# 2 回放：--params 会一并把 nilm.quantity=i 和 *_a 参数套上；表头为「幅值范围(A)」，事件 CSV 的 unit 列 = A、magnitude 列 = |ΔI|
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\dev_onoff_i.csv --params output\tune_i.json --out output\dev_events_i.csv
#   也可对有电压的文件强制按电流检测：加 --quantity i（或 --set threshold.min_delta_a=0.5 单项覆盖）
# 3 对账：真值表不变；总线侧带指纹归属改用 --mag-a（A），--mag-w / --dq-var 对电流口径事件不适用（ΔQ 恒 0，脚本会提示并忽略）
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\dev_events_i.csv --truth data\truth.csv --tol-s 1 --channel A
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\bus_events_i.csv --truth data\truth_bus.csv --channel A --mag-a 25 --mag-tol-pct 30
#   --signature-from 同样可用：从设备侧命中事件取 |ΔI| 均值作指纹
# 4 定稿：同 §7；界面「检测参数」里 A 口径一列会点亮、W 一列灰显（quantity_effective = i）
```

**建议值是怎么算的**：与附录 E 完全相同的规则，只是把 P 序列换成 I 序列——`settle_tol_a = 5 周波极差 95 分位 × 1.2`、
`min_delta_a = max(额定电流/2, 6σ)`、CUSUM `drift_a = min_delta_a/4`、`threshold_a = 2×(min_delta_a − drift_a)`、GLR `noise_a = σ`、
`steady_state.tol_a = 10 周波极差 95 分位 × 1.2`。`rel_tol_pct / min_delta_pct` 对 |I| 中位数折算，与绝对值取较大者生效。

**只能单相（v0.39）**：I 口径没有「三相总」——三相电流有效值不能像有功那样相加，跨相合并没有物理意义。软件在 I 口径忽略检测对象 `total`
（只配了 `total` 时按 A/B/C 三相各自单独检测，事件 `channel` 列为 A/B/C）；`nilm_tune.py` I 口径默认 `--channel A`（填 total 会报错）；
`nilm_check.py` 对账时**必须加 `--channel A`（或 B/C）**，否则三相各一条的同一次投切会互相算成误报（脚本会提示）。界面趋势图「曲线」选 电流 I 可看三相电流（Ia/Ib/Ic 勾选）。

**电流口径的两个注意点**：

| 现象 | 原因 | 怎么办 |
|---|---|---|
| 感性设备（电机）投入时 ΔI 比按 kW 换算的大 20%～50% | 电流含无功分量，I 口径看到的是视在电流 | `--min-load-a` 按**铭牌额定电流**填，不要按 kW/U 粗算；指纹 `--mag-a` 取设备侧命中事件的 |ΔI| 均值 |
| 功率因数补偿电容投切被报成事件 | 电容只改无功，P 不变但 I 变 | 这是电流口径的固有特性：用 `--mag-a` 幅值带归属，或在真值表把电容投切写成「其它」 |

## 附录 D：数据怎么切、用哪一侧

- **切片**：软件 → 数据源页 → 左列「总线侧 导出指定时间段的原始数据」/ 右列「分路侧 …」→ 点「填入文件时间范围」看文件覆盖的时间 → 改成想要的起止（可只写 `09:12:00`）→「导出到新 CSV」，文件在 `output\raw_<起>_<止>_src0.csv`（总线）/ `_src1.csv`（分路）。两侧互不影响。
- **量噪声用哪侧**：设备最终在哪一侧检，就用哪一侧的背景量 σ。总线侧 σ 通常比分路侧大 5~50 倍。
- **总线上其它设备也在开关时**：量 σ 不受影响（§3 已说明）；**对账必须带指纹**（§5-B），否则其它设备全算误报；调参只看"带内误报"。
- **设备侧文件也能量噪声吗**：能——`nilm_tune.py --file data\dev_onoff.csv` 会自动忽略开关点，并在 `max|diff|` 行提示 ⚠。
- **线上落盘的事件也能对账**：生产运行时事件在 `output\nilm\nilm_events_<日期>.csv`（两侧同文件，`source_id` 0/1 区分），用 `nilm_check.py --events 该文件 --source-id 1 --truth ...` 即可做事后复核。

---

## 附录 E（进阶）：参数是怎么算出来的

> 给想知道"为什么"的同学；现场实施不需要看。`nilm_tune.py` 内置的就是这些规则，自测 `tests/test_nilm_tune_tool.py` 证明：在同一噪声水平下，建议参数能检出恰等于最小关心负荷的阶跃，且 3000 个纯噪声周波 0 误报。

**量出来的 5 个数**（都按周波 P 序列算，稳健统计）：

| 量 | 定义 | 用途 |
|---|---|---|
| `level` | 窗内 \|P\| 中位数（基荷） | 相对门槛换算、量级自检 |
| `sigma` σ | 相邻差分的 MAD × 1.4826 / √2 | 一切噪声尺度 |
| `range5` / `range10` | 连续 5 / 10 周波极差的 95 分位，再与 2×中位数取小 | `settle_tol_w` / `tol_w` |
| `sigma_m10` | 相邻两个 10 周波均值之差的 MAD σ | 双滑窗 / GLR 灵敏度参考 |
| `max|diff|` | 相邻周波最大跳变；> 10σ 提示段内含事件 | 只是提醒 |

**推荐公式**（Δ_min = 最小关心负荷有功）：

| 算法 | 参数 | 公式 |
|---|---|---|
| 所有 | `min_delta_w` | max(Δ_min / 2, 6σ) |
| threshold / median_diff | `settle_tol_w` | max(range5 × 1.2, 4σ) |
| two_window | `k_sigma` | 3（均值差 ≥ 3 × 前窗 std） |
| cusum | `drift_w` k | max(min_delta_w / 4, 0.5σ) |
| cusum | `threshold_w` h | max(2 × (min_delta_w − k), 5σ)（恰为最小台阶约 2 周波触发） |
| glr | `noise_w` | σ |
| glr | `threshold` | 25（等价均值差 ≥ √(4·thr/w)·σ ≈ 2.6σ @ w=15） |
| steady_state | `tol_w` | max(range10 × 1.2, 5σ) |
| 全局 | `rel_tol_pct` | 100 × settle_tol_w / level（夹在 0.05~5） |
| 全局 | `min_delta_pct` | 100 × min_delta_w / level |

**关键比例**：`min_delta_w / 容差 ≥ 3` 时检测才稳；`min_delta_w ≥ 6σ` 保证纯噪声不触发（触发门槛是它的一半，3σ 单侧误报率约 0.13 %/周波，再经 settle 确认后实际远低于此）。

**机制备忘**：
- 幅值 = 事件后稳态均值 − 事件前稳态均值（各取 `settle_cycles`），电机起动冲击不计入。
- 相对门槛：生效值 = max(绝对参数, 窗内 \|P\| 中位数 × 百分比)。
- 去重：同一算法同一对象两次事件终点相距 < `min_gap_cycles` 只报第一条；事件要在终点之后再看到"确认周波数"（阈值类 = `settle_cycles`，双滑窗 = `post_cycles`，GLR = `window_cycles`，稳态分段 = `min_steady_cycles`）才出现，因此界面滞后 0.1~0.3 s 属正常。
- 周波按额定频率定长切分，频率偏离 ±0.5 Hz 以上逐周波 P 会有微小拍频，表现为 σ 偏大——按量出来的填即可。
- 场景经验：商业楼宇（阶跃干净、σ 小、负荷多）全开 6 算法、`rel_tol_pct` 0.1~0.3；工业电机（软启动、暂态长）优先 `steady_state` + `cusum`，窗长 ≥ 暂态 × 2；变频 / 调光负荷（缓变）优先 `cusum`，其余易漏。

## 附录 G（v0.49）：6 种事件检测算法的实现流程（输入 / 输出 / 过程参数）

> 依据 `elec_tool/nilm.py` 当前实现逐行整理；参数默认值见 `elec_tool/config.py` `NILM_ALGO_DEFAULTS`。
> 下文"W 口径"指按有功 P 检测、"A 口径"指按电流有效值 I 检测（附录 F）；两种口径算法完全相同，只是输入序列与绝对阈值那一套不同。

### G.0 公共部分：所有算法共用的输入、输出与前后处理

**1. 输入序列是怎么来的（`CycleFeatures.push`）**

| 步骤 | 说明 |
|---|---|
| 切周波 | 按额定频率定长切分：每周波 `n_cycle = round(fs / f_nom)` 个采样点（6400 Hz / 50 Hz = 128 点），不足一个周波的零头结转到下一块；时间不连续（缺口 > 1.5/fs）时丢弃零头，避免拼出假周波 |
| 逐周波有功 P | 每相 `P = mean(u·i)`（一个周波内逐点乘积的均值），`total = Pa+Pb+Pc` |
| 逐周波无功 Q | 基波单频 DFT 得 U、I 复相量，`Q = Im(½·U·conj(I))`，`total` 为三相之和（只用于事件的 ΔQ 字段，不参与检测） |
| 逐周波电流 I | 每相 `I = sqrt(mean(i²))`（周波有效值）；`total = sqrt(Ia²+Ib²+Ic²)` 只作幅值参考，**I 口径不检测 total** |
| 口径 | 启用 PT/CT 时序列已换算到一次侧，所有阈值按同一口径填 |

**2. 检测器怎么调用算法（`NilmDetector._evaluate`）**

| 过程参数 | 含义 / 用途 |
|---|---|
| `nilm.window_cycles`（默认 300） | 内存里保留的最近周波数 = 每次算法评估的序列长度 `L`；窗按滑动方式更新，每来一块新数据就对整窗重新跑一遍算法 |
| `nilm.channels` → `channels_effective` | 检测对象 total / A / B / C；I 口径自动去掉 total（只配 total 时按 A/B/C 各自检测） |
| `level` | 窗内 `median(|序列|)`，作为相对门槛的基准 |
| `params_for_current()` | I 口径把 `*_a` 的值写到算法读取的 `*_w` 键上（算法函数只认 `*_w` 键名，键名里的 "w" 此时只是名字） |
| `effective_params()` | 把相对门槛折算进绝对参数：容差类 `settle_tol_w / tol_w / drift_w / noise_w / threshold_w` 取 `max(绝对值, level × rel_tol_pct%)`；`min_delta_w` 取 `max(绝对值, level × min_delta_pct%)`。算法实际使用的就是折算后的"生效值" |
| 算法输出 `Step` | 每条候选事件是一个五元组 `(onset, end, pre, post, score)`：起点 / 终点周波在窗内的索引、事件前稳态值、事件后稳态值、检验量 |
| 确认周波数 `_confirm_cycles` | 终点之后至少还要再看到这么多周波事件才"确认"（否则等下一块数据）：阈值类 / CUSUM / 中值 = `settle_cycles`，双滑窗 = `post_cycles`，GLR = `window_cycles`，稳态分段 = `min_steady_cycles`。这就是界面上事件滞后 0.1~0.3 s 出现的原因 |
| 去重 `nilm.min_gap_cycles`（默认 10） | 同一算法同一对象：新事件起点 ≤ 上一事件终点 + gap 的不再报（窗滑动时同一事件会被反复检出，靠全局周波序号 `g_start/g_end` 去重） |
| 事件字段 | `t_start/t_end`（起点 / 终点周波的时间）、`direction`（post − pre 的符号：↑up / ↓down）、`magnitude`（检测量口径的 \|post − pre\|，W 或 A）、`delta_p_w / delta_q_var / delta_i_a`（事件前后各取 `settle` 个周波均值之差；P 口径 ΔP 直接用算法的 pre/post，I 口径 ΔI 用算法的 pre/post、ΔP 另算）、`cycles = end − onset`（暂态周波数）、`score`（检验量，含义随算法） |

**3. 共用的辅助函数 `_settle_end(p, start, settle, tol, max_rise)`**
从 `start` 起逐位置 `j` 看 `p[j : j+settle]` 的极差（max − min）是否 ≤ `tol`，第一个满足的 `j` 就是"暂态结束 / 新稳态开始"的终点；向后最多看 `max_rise` 个位置，超过返回 None（暂态还没结束或数据还不够）。

---

### G.1 阈值差分 `threshold`（`_steps_threshold`）

**思想**：相邻周波的一阶差分超过门槛 → 事件起点；随后找到稳定段 → 终点；前后稳态均值之差 ≥ 最小幅值才算事件。

| 参数 | 默认（W / A） | 用途 |
|---|---|---|
| `min_delta_w` / `min_delta_a` | 50 / 0.3 | 最小事件幅值：\|post − pre\| 低于它丢弃；同时决定触发门槛 |
| `settle_cycles` | 5 | 稳态判定与均值统计的周波数 |
| `settle_tol_w` / `settle_tol_a` | 20 / 0.1 | 稳态容差：`settle` 个周波极差 ≤ 它即稳定 |
| `max_rise_cycles` | 40 | 起点之后最多等多少周波暂态结束；超过则放弃本次（等更多数据） |

**流程**
1. `d = diff(p)`；触发门槛 `trig = max(0.5 × min_delta, settle_tol)`——取一半是因为阶跃落在周波边界内时会被分摊到相邻两个周波，各占一半；不低于容差是防噪声误触发。
2. 从 `i = settle` 起扫描：若 `|d[i−1]| ≥ trig`，记 `onset = i`。
3. `end = _settle_end(p, onset+1, settle, settle_tol, max_rise)`；为 None 则停止本轮（暂态未结束）。
4. `pre = mean(p[onset−settle : onset])`，`post = mean(p[end : end+settle])`；`|post − pre| < min_delta` → 不是事件。
5. **起点精修**：在 `[onset, end]` 内找第一个越过中线 `pre + Δ/2` 的周波作为最终 `onset`（让起点落在阶跃真正发生的周波上，而不是差分刚冒头的周波）。
6. 输出 `(onset, end, pre, post, score = post − pre)`；扫描指针跳到 `end + settle` 继续。

**特点**：最直接、对干净阶跃最准；对单周波尖峰敏感（尖峰也会使差分越过门槛，但随后 \|post − pre\| 小会被第 4 步丢掉）；缓慢爬坡（每周波增量 < trig）检不出。

---

### G.2 中值滤波差分 `median_diff`（`_steps_median`）

**思想**：先用中值滤波去掉孤立尖峰 / 单周波缺口，再套用阈值差分法。

| 参数 | 默认 | 用途 |
|---|---|---|
| `median_cycles` | 5 | 中值滤波窗长（偶数自动 +1 变奇数） |
| 其余 | 同阈值差分 | 滤波后的序列直接交给 `_steps_threshold` |

**流程**
1. 两端 edge 填充 `k//2` 个点，滑窗取 `k` 点中值得 `pm`（长度与 `p` 相同，无相位偏移）。
2. `_steps_threshold(pm, prm)`，起点 / 终点索引对应回原序列。

**特点**：宽度 ≤ `k//2` 个周波的尖峰 / 缺口被完全抹掉，不会触发；代价是阶跃边沿被"推迟" ≈ `k//2` 个周波才充分反映（起点精修能部分补偿），`k` 过大会把短暂态（如几周波的启动冲击 + 回落）整体抹掉。

---

### G.3 双滑窗均值差 `two_window`（`_steps_two_window`）

**思想**：在每个候选点左右各开一个窗，比较"后窗均值 − 前窗均值"，超过门槛且显著高于前窗噪声的局部极大值即事件。

| 参数 | 默认（W / A） | 用途 |
|---|---|---|
| `pre_cycles` | 10 | 前窗长度（事件前基准） |
| `post_cycles` | 10 | 后窗长度（事件后水平），也是该算法的"确认周波数" |
| `min_delta_w` / `min_delta_a` | 50 / 0.3 | 均值差绝对门槛 |
| `k_sigma` | 3.0 | 均值差还须 ≥ `k_sigma × σ_pre`（前窗标准差），噪声大的段门槛自动抬高 |

**流程**
1. 用前缀和 `cs = cumsum(p)`、`cs2 = cumsum(p²)` 一次性算出所有候选点 `idx ∈ [pre, L−post]` 的 `m_pre / m_post / v_pre`（O(L)）。
2. `delta = m_post − m_pre`；门槛 `thr = max(min_delta, k_sigma × sqrt(v_pre))`；`exceed = |delta| ≥ thr`。
3. 把连续为真的 `exceed` 归成一段，段内取 `|delta|` 最大处 `pk` 为事件：`onset = idx[pk]`、`end = min(onset + post, L−1)`。
4. 输出 `(onset, end, m_pre[pk], m_post[pk], score = delta[pk])`。

**特点**：对阶跃位置的估计是 `|均值差|` 峰值，天然抗单点噪声；但单周波尖峰会被摊进后窗均值（幅值 ≈ 尖峰 / post），尖峰足够大时仍会报出一条"小事件"——这就是 README 提到的"对尖峰较敏感"。`pre/post` 必须 ≥ 暂态长度，否则暂态会同时进入两个窗，使 `delta` 偏小。

---

### G.4 CUSUM 累积和 `cusum`（`_steps_cusum`）

**思想**：Page 的双侧 CUSUM。相对参考均值 `mu` 累积正 / 负偏差（每步扣掉允许漂移 `k`），累积量越过门限 `h` 判定均值发生了变化；能把很多个小增量累加起来，适合缓慢爬坡 / 软启动。

| 参数 | 默认（W / A） | 用途 |
|---|---|---|
| `drift_w` / `drift_a`（k） | 10 / 0.05 | 允许漂移：小于 k 的偏差不累积（吸收噪声与缓慢波动）；也用作终点稳态容差（`2k`） |
| `threshold_w` / `threshold_a`（h） | 200 / 1.0 | 触发门限：累积量 > h 判定事件。h/k 默认 20 倍——恰为 min_delta 的阶跃约 2 个周波触发，纯噪声累积不到 |
| `min_delta_w` / `min_delta_a` | 50 / 0.3 | 触发后仍要求 \|post − pre\| ≥ 它，否则只更新参考均值不报事件 |
| `settle_cycles` | 5 | 初始参考均值 `mu = mean(p[:settle])` 的长度、终点稳态判定长度、事件后均值长度 |

**流程**
1. `mu = mean(p[:settle])`；`sp = sn = 0`；`zp = zn = 0`（累积量最后一次归零的位置 = 起点估计）。
2. 对 `i ≥ settle`：`x = p[i] − mu`；`sp = max(0, sp + x − k)`；`sn = max(0, sn − x − k)`；`sp == 0` 时记 `zp = i`，`sn == 0` 时记 `zn = i`。
3. 若 `sp > h` 或 `sn > h`：`onset = (zp 或 zn) + 1`（累积开始的那个周波），`score = 越限的累积量`。
4. 终点：`end = _settle_end(p, i, settle, tol = 2k, max_rise = 4×settle)`；找不到且数据不够则停止等待，否则 `end = i`。
5. `pre = mu`，`post = mean(p[end : end+settle])`；`|post − pre| ≥ min_delta` 才输出 `(onset, end, pre, post, score)`。
6. 无论是否报出，都把 `mu = post`、累积量清零、`i = end + settle` 继续（参考均值随负荷水平自适应）。

**特点**：唯一能可靠检出缓变（每周波增量小于任何差分门槛）的算法；起点估计 = 累积开始点，对软启动给的是"开始爬坡"的时刻。单周波尖峰：一个高于 `h + k` 的尖峰当周波就能触发，随后 `post ≈ pre` 被 `min_delta` 挡掉（但 `mu` 已重置为 post，无影响）。**A 口径下 k、h 必须填 A 单位的 `drift_a / threshold_a`**（v0.37 之前清零 W 阈值会让 h = k 退化）。

---

### G.5 GLR 广义似然比 `glr`（`_steps_glr`）

**思想**：高斯均值突变的广义似然比检验：在候选点左右各取 `w` 个周波，比较"两段均值不同"与"均值相同"两个假设的对数似然比。

| 参数 | 默认（W / A） | 用途 |
|---|---|---|
| `window_cycles`（w） | 15 | 左右窗长；也是"确认周波数" |
| `threshold` | 25.0 | 对数似然比门限（无量纲，两种口径共用） |
| `noise_w` / `noise_a` | 10 / 0.05 | 噪声 σ 下限：窗内方差小于 `noise²` 时按 `noise²` 算，防止极平稳段把微小变化放大成巨大的似然比 |
| `min_delta_w` / `min_delta_a` | 50 / 0.3 | 幅值门槛：`|m1 − m0| ≥ min_delta` 与似然比门限同时满足才触发 |
| `settle_cycles` | 5 | `end = onset + settle`（事件时长按固定周波数给出） |

**流程**
1. 前缀和一次算出所有候选点 `idx ∈ [w, L−w]` 的左窗均值 / 方差 `m0, v0` 与右窗 `m1, v1`。
2. `σ² = max(½(v0+v1), noise²)`；`llr = (w/2) · (m1 − m0)² / (2σ²)`（代码中写作 `w·w/(2w) · Δ²/(2σ²)`）。
3. `exceed = (llr ≥ threshold) & (|m1 − m0| ≥ min_delta)`。
4. 连续越限段内取 `llr` 最大处 `pk`：`onset = idx[pk]`，`end = min(onset + settle, L−1)`。
5. 输出 `(onset, end, m0[pk], m1[pk], score = llr[pk])`。

**特点**：`score` 有统计意义（≈ 信噪比的平方 × 窗长 / 4），同一门限在 W 级与 MW 级都适用，噪声大的段自动变"迟钝"；但 `threshold` 固定意味着窗长变化会改变灵敏度（`llr ∝ w`）。暂态长于 `w` 时两窗都被污染，峰值位置可能偏移。

---

### G.6 稳态分段 `steady_state`（`_steps_steady`，Hart 1992 的边沿检测思路）

**思想**：不找"突变"，而是找"稳态"：把序列切成若干段"极差 ≤ tol 且长度 ≥ 最少周波"的稳态段，相邻两个稳态段之间就是一次暂态，两段均值之差即事件幅值。

| 参数 | 默认（W / A） | 用途 |
|---|---|---|
| `tol_w` / `tol_a` | 30 / 0.15 | 稳态容差：一个稳态段内 max − min 不得超过它（随数据增长在线维护 lo/hi） |
| `min_steady_cycles` | 10 | 稳态段最少周波数（短于它的平台不算稳态，会并入暂态）；也是"确认周波数" |
| `min_delta_w` / `min_delta_a` | 50 / 0.3 | 相邻稳态均值差门槛 |
| `max_transient_cycles` | 100 | 两个稳态段之间的暂态最长允许周波数；超过视为"数据缺口 / 长时间不稳"，不配对成事件 |

**流程**
1. 单遍扫描：维护当前段 `[a, i)` 的 `lo/hi`；新点加入后若 `hi − lo ≤ tol` 则继续，否则当前段结束——长度 ≥ `min_n` 的记为稳态段 `(a, i)`，然后从 `i` 新开一段。
2. 对相邻稳态段 `(a0,b0)`、`(a1,b1)`：若暂态长度 `a1 − b0 > max_tr` 跳过；否则 `pre = mean(p[a0:b0])`，`post = mean(p[a1:b1])`。
3. `|post − pre| ≥ min_delta` → 输出 `(onset = b0, end = a1, pre, post, score = post − pre)`：起点 = 前一稳态的最后一个周波之后，终点 = 新稳态的第一个周波。

**特点**：对暂态形状完全不敏感（启动冲击、振荡、爬坡都只是"两个稳态之间的东西"），最适合电机 / 软启动类设备；代价是事件要等到新稳态积满 `min_steady_cycles` 才出现，且 `tol` 填小了会把带纹波的正常运行切成很多短段、没有一段够长 → 整体漏报；`tol` 填大了会把小阶跃吞进同一稳态段。单周波尖峰 = 一个长度为 1 的"段"，不够 `min_n`，自然被忽略。

---

### G.9（v0.90）设备画像匹配 `profile`（`elec_tool/nilm_profile.py`）——唯一的多特征算法

> 放在 G.7 之前是因为它**不走 G.0 的公共流程**：不是标量序列上的"找台阶"，而是"找台阶 → 量 7 个特征 → 和画像比"。实现依据仓库根《设备画像提取与总线侧负荷辨识事件检测算法方案.md》的基础版路线（无 DTW、无幅值校准）。

**(a) 画像是什么**（`build_profile`，设备侧离线一次性完成）

1. 用与调参 / 波形预览同一套基准配置（PT/CT、列映射、自定义时间）回放设备侧文件，得到逐周波 `P / Q / Ia / Ib / Ic`（口径同 G.0）。
2. **定位每次启停**：有标签 → 在标签 ± `label_tol_s`（默认 2 s）内找"前窗（`pre_cycles`）中位数 vs 紧随其后 5 周波的最小偏离"最大的周波，再取第一个得分 ≥ 0.5×最大的周波作起点（台阶恰为跳变周波、斜坡落在坡脚）；无标签 → `steady_state` + 自适应参数（G.6 / 附录 E）找台阶，ΔP > 0 记为启动、< 0 记为停止。
3. **每次事件取 7 维特征向量** `FEATURES = [d_ia, d_ib, d_ic, d_p, d_q, peak_ratio, dur_cycles]`：
   - `d_*` ＝ 事件后窗 `[end, end+post_cycles)` 的中位数 − 事件前窗 `[onset−pre_cycles, onset)` 的中位数（前后差分，不受基荷影响）；
   - `peak_ratio` ＝ 事件窗内三相电流合成量相对前窗基线的**最大偏移 / 稳态偏移**（≥ 1；电机直启 1.5~6，阻性负荷 1.0）；
   - `dur_cycles` ＝ 从起点到"进入事件后电平 ±20 % 带"的周波数（启动过程长短）；
   - 另存一条 **16 点归一化轨迹模板**（事件窗内合成电流相对基线的变化 / 稳态变化，时间归一化），作为"启动形状"证据。
4. **启动 / 停止各自统计**：中心 μ ＝ 各次均值，σ ＝ 各次标准差，但 σ 不小于 `max(相对下限 × |μ|, 绝对下限)`（相对下限：电流 / 有功 15 %、无功 25 %、峰值比 30 %、持续周波 50 %；绝对下限：0.02 A / 5 W / 5 var / 0.1 / 2 周波）——这样 1 次事件也能用，但 notes 会 ⚠ 建议 ≥ 3 次。模板取各次均值，并记录各次与均值的 RMS 散布 `template_spread`。
5. 写成一个 JSON（schema `nilm_profile/1`）：`device_id / quantity(p|i) / unit / pre_cycles / post_cycles / features / startup{n, mu[7], sigma[7], template[16], template_spread, dur_cycles{min,max}, events[…逐事件 vec/t_start/source]} / shutdown{同} / calibration{bus_mapping: null} / notes / command`。

**(b) 总线侧在线检测**（`detect_profile`，每块数据到达后在最近 `window_cycles` 个周波的窗上跑一次，对象固定为**三相合成**）

| 步骤 | 做法 | 参数 |
|---|---|---|
| ① 候选 | 稳健双滑窗：前窗长 = 画像 `pre_cycles`、后窗长 = `post_cycles`，`\|mean(后) − mean(前)\| ≥ max(min_d, k_sigma × 前窗标准差)` 的连通区取峰值为 onset；`min_d` ＝ 画像里启动 / 停止 \|ΔP\| 最小者的一半（I 口径用 √(ΔIa²+ΔIb²+ΔIc²)）；终点 ＝ onset 后首个进入事件后电平 ±20 % 带的周波（封顶 `post_cycles`） | `k_sigma`（默认 4） |
| ② 特征 | 对每个候选按 (a)-3 同一公式取 7 维向量与 16 点模板（用的是**总线侧**的 P/Q/I 序列） | — |
| ③ 匹配 | 与启动、停止画像分别算**对角马氏距离** `D² = Σ_j (x_j − μ_j)² / (σ_j² + λ·median(σ²))`（λ 收缩避免某一维 σ 过小一票否决）；取 D² 小者为方向 `START/STOP`；`margin` ＝ 另一方向 D² / 本方向 D²（越大方向越明确）；轨迹：模板 RMS 距离 `td` > 3 × `template_spread` 时置信度乘 `max(0.3, 3·spread/td)`，并打 `trajectory_deviates` | `lambda_rel`（默认 0.1） |
| ④ 置信度 | `confidence = exp(−D² / (2·d)) × 轨迹折扣`，d = 7。直觉：每维平均偏 1σ → D² = 7 → 0.61；平均偏 2σ → 0.14；平均偏 3σ（D²/d = 9）→ 0.011 | — |
| ⑤ 拒识 | `D²/d > d2_max` → `d2_exceeds`（直接拒）；`margin < margin` → `ambiguous_direction`（只打标记）；状态机：当前已 ON 又来 START、或已 OFF 又来 STOP → `state_mismatch`，置信度 × 0.5；最终 `confidence < min_confidence` → 拒 | `d2_max`（默认 9）、`margin`（1.5）、`min_confidence`（0.3）、`state_check`（1） |
| ⑥ 状态机 | 接受的 START → 设备状态 `on`，STOP → `off`（初始 `unknown` 时第一个事件不做状态检查）；状态写在 `summary.profile.device_state`，界面画像面板可见 | `state_check` |
| ⑦ 确认与去重 | 事件终点之后窗里还要有 ≥ `post_cycles` 个周波才输出（所以比 6 种标量算法滞后约 `post_cycles` 周波）；同一事件在后续窗里按全局周波号去重（`min_gap_cycles` 同样适用） | — |

**(c) 输出**：`NilmEvent` 公共字段照旧（`t_start/t_end/direction(up=START,down=STOP)/delta_p_w/delta_q_var/delta_i_a/pre_p_w/post_p_w`，`score` ＝ 置信度），另加 `device_id / confidence / d2 / profile_direction / status(confirmed|low_confidence) / quality_flags`；`to_dict` 里 `observed_delta_p` ＝ 总线侧观测 ΔP、`estimated_device_delta_p = null`。事件 CSV `nilm_events_*.csv` 末尾多 6 列（旧文件自动改名 `.pre-v090.csv`）。`summary.profile.last` 保留最近 20 个候选（含被拒的）及各维 `contrib`（每一维对 D² 的贡献）——排查漏报 / 误报先看它。

**(d) 与标量算法的区别与限制**

- 不参与「自适应算法参数」（它的噪声尺度来自画像 σ，不是窗内数据）；`nilm_tune.py` 不给它建议值；`NILM_SCALAR_ALGOS` 只含原 6 种。
- 画像与总线侧 `nilm.quantity` 口径必须一致，否则不检测并在 `summary.errors` 说明。
- 设备侧电流 ≠ 总线侧增量（变压器 / 补偿 / 损耗）；本版不做校准，差异大时请用总线侧"只有这台设备在动"的录波提画像（§5-C）。
- 两台特征相近的设备会互相高置信度匹配——这是相似性匹配的固有局限，不是参数问题；此时只能到分路侧。
- 单画像单设备：多台设备要各自一份画像、分别配置（本版不做多设备联合判决 / 画像库）。

### G.7 一张表对比

| 算法 | 起点怎么定 | 终点怎么定 | 检验量 score | 擅长 | 弱点 |
|---|---|---|---|---|---|
| threshold | 差分越门槛 → 精修到越过中线的周波 | 之后首个 `settle` 周波极差 ≤ 容差处 | post − pre | 干净阶跃，定位最准 | 缓变漏报；尖峰可能误触发 |
| median_diff | 同上（在中值滤波后的序列上） | 同上 | post − pre | 带尖峰 / 缺口的数据 | 边沿略延迟；短暂态被抹掉 |
| two_window | \|后窗均值 − 前窗均值\| 的峰 | onset + post_cycles | m_post − m_pre | 噪声大的总线 | 尖峰被摊成小事件；窗短于暂态时幅值偏小 |
| cusum | 累积量最后一次归零处 + 1 | 触发后首个极差 ≤ 2k 处（找不到即触发点） | 越限的累积量 | 缓慢爬坡 / 软启动 | 参数两个且有比例关系；尖峰当周波触发 |
| glr | 对数似然比的峰 | onset + settle_cycles | llr | 统一门限跨量级可用 | 灵敏度随窗长变；长暂态位置偏移 |
| steady_state | 前一稳态结束处 | 新稳态开始处 | post − pre | 电机 / 任意暂态形状 | 出事件最慢；tol 过小整体漏报 |
| profile（v0.90） | 稳健双滑窗峰（窗长取画像 pre/post） | onset 后首个进入 ±20 % 带处 | 置信度 exp(−D²/2d)（D²＝与画像的对角马氏距离） | 总线上多设备时只报这一台、带设备 ID 与置信度 | 需设备侧录波做画像；相似设备分不开；滞后 post_cycles；不做幅值校准 |

### G.8 参数与 `nilm_tune.py` 建议值的对应关系（见附录 E）

`settle_tol = 5 周波极差 P95 × 1.2`（threshold / median 的稳态容差）；`steady_state.tol = 10 周波极差 P95 × 1.2`；`min_delta = max(最小关心负荷/2, 6σ)`；`cusum.drift = max(min_delta/4, 0.5σ)`、`cusum.threshold = max(2(min_delta − drift), 5σ)`；`glr.noise = σ`；其余窗长 / 周波数用默认值。A 口径同一套公式作用在 I 序列上，输出 `*_a`。

**建议值怎么进配置（v0.50）**：套用逻辑在 `elec_tool/nilm_tuning.py`（`apply_nilm_params` / `export_tuned_config`），`nilm_tune.py --apply`、`nilm_replay.py --params`、`POST /api/nilm/tune/apply` 与界面「套用 nilm_tune 结果」共用同一份：在基准配置的**副本**上只覆盖 `nilm.quantity / rel_tol_pct / min_delta_pct` 和各算法里 `NILM_ALGO_DEFAULTS` 认识的键（`enabled` 与未知键不动），`validate()` 通过后写成完整配置到 `nilm.nilm_dir`（默认 `output/nilm`），文件名 `nilm_tuned_config[_<侧>]_<YYYYmmdd_HHMMSS>.json`，附 `_tuning` 元信息；是否回写正式配置文件由调用方显式决定（CLI `--save-config` / API `persist`），默认一律不写。

---

## 附录 H（v0.51）：`nilm_tune.py` 命令手册——每个参数、每种用法一条命令

> 正文 §3 只讲"现场最常用的一条命令"；这里把脚本的**全部参数**和**每一种用法**单独列出来，每种都给一条可直接复制的命令和你会看到的输出要点。命令都在仓库根目录、以 Windows PowerShell 写法给出（`.\.venv\Scripts\python.exe`）；Linux/macOS 把开头换成 `.venv/bin/python`、`\` 换成 `/` 即可。随时可 `python tools\nilm_tune.py --help` 看参数表。

### H.0 这个脚本做什么、不做什么

- **做**：读一段"背景"数据（最好是没有投切的稳态段，几十秒即可）→ 按 §E 的规则量 5 个噪声统计量 → 给出 `nilm.quantity / rel_tol_pct / min_delta_pct` 和 6 种算法的一套**起点参数**。可选地（`--apply`）把这套参数叠加到一份配置上并写出完整配置文件。
- **不做**：不回放、不对账（那是 `nilm_replay.py` / `nilm_check.py`）；**默认不改任何配置文件**，只有显式 `--save-config` 才回写。
- **退出码**：`0` 成功；`2` 输入不满足（没有整周波数据 / 无电压却要按 P 调参 / I 口径填了 `total`），错误原因打印到 stderr，不会给出一套没意义的参数。

### H.1 参数一览

| 参数 | 必填 | 默认 | 作用 |
|---|---|---|---|
| `--file <csv>` | ✅ | — | 背景数据文件，格式与软件数据源一致（`时间戳,A相电压,A相电流,…`，列映射用 `--config` 里的） |
| `--config <json>` | | `configs\runtime.json`（界面保存过的当前运行配置）→ 没有则 `configs\default.json`；设了环境变量 `ELEC_TOOL_CONFIG_PATH` 则用它 | 从这里读 **PT/CT、fs、f_nom、列映射、`nilm.quantity`**；也是 `--apply` 的**基准配置** |
| `--channel total\|A\|B\|C` | | P 口径 `total`，I 口径 `A` | 量哪个对象的噪声。I 口径不接受 `total`（电流有效值不能跨相相加） |
| `--min-load-w <W>` | | 不填 | 现场**最小关心负荷**的有功（一次侧 W）。P 口径用；给了它 `min_delta_w` 才有"针对这台设备"的含义 |
| `--min-load-a <A>` | | 不填 | 同上，电流版（一次侧 A）。I 口径用 |
| （无开关） | | 自动 | v0.56：文件里有 >100 周波的慢启动斜坡时，`steady_state.max_transient_cycles` / `min_steady_cycles` 自动按暂态放大，必要时给 `nilm.window_cycles`（见 H.4‴） |
| `--min-load-auto` | | 关 | v0.55：未手填最小关心负荷时，从文件里的**投切台阶**估计它（见 H.4″）。只对分路侧单设备、含启停的录波有效；估计不可靠则按未指定处理 |
| `--quantity auto\|p\|i` | | 跟随 `--config` 的 `nilm.quantity`；配置也没有才 `auto` | 检测量：`p` 逐周波有功、`i` 逐周波电流有效值、`auto`＝有电压取 P、无电压取 I |
| `--t-start <时间>` | | 空＝文件开头 | v0.52：分析起始时间。写法同播放时间段：`2026-10-13 08:00:02.5` / `08:00:02.5`（与文件时标当天时刻比较）/ epoch 秒 |
| `--t-end <时间>` | | 空＝文件结尾 | v0.52：分析结束时间，格式同上 |
| `--duration <秒>` | | 空 | v0.52：从起始时间（或文件开头）起分析的时长；与 `--t-end` 同时给时取先到者 |
| `--max-cycles <n>` | | `30000`（≈10 min@50 Hz） | 最多分析多少个周波，防止超大文件跑太久 |
| `--json` | | 关 | 只输出一份 JSON（机器可读，给 `nilm_replay.py --params`、`POST /api/nilm/tune/apply` 或留档） |
| `--apply` | | 关 | 把建议叠加到 `--config` 基准配置上，写出**完整配置**到 `output\nilm\nilm_tuned_config_<时间戳>.json`；**不改配置文件** |
| `--out <path>` | | 自动命名 | `--apply` 的输出文件路径 |
| `--save-config` | | 关 | 与 `--apply` 连用：**额外**把更新后的配置回写到 `--config` 那个文件（显式要求才做） |

> 单位口径：所有阈值与软件界面一致——配置里启用 PT/CT（`transform.enabled=true`）时是**一次侧** W / A，否则是二次侧。首行输出会写明「口径 一次侧(PT/CT)」或「二次侧」。

### H.2 用法 1：最基本——只看噪声，拿一套通用起点

```powershell
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv
```

不给 `--min-load-w` 时 `min_delta_w = max(6σ, 2%×基荷)`，注释行会写「未指定 --min-load-w … 请按现场最小关心负荷改」。输出分三段：

```
文件 data\bus_bg.csv  对象 total  周波 300  时长 6.0 s  口径 一次侧(PT/CT)  检测量 有功 P（配置 nilm.quantity=auto）
—— 噪声统计（W）——
  基荷 |P| 中位数        level      = 1.8e+06
  单周波噪声 σ(稳健)     sigma      = 27.92  (0.002 % 基荷)
  相邻周波最大 |Δ|       max|diff|  = 7.5e+05   ⚠ >10σ：段内含事件/尖峰，统计已用稳健口径
  5 周波极差 95 分位     range5     = 122.5   → settle_tol_w 的依据
  10 周波极差 95 分位    range10    = 161.9   → steady_state.tol_w 的依据
  10 周波均值差 σ        sigma_m10  = 14.83   → 双滑窗/GLR 的噪声尺度
—— 建议参数（起点，按 NILM_TUNING_GUIDE.md 复核）——
  未指定 --min-load-w，min_delta_w 取 max(6σ, 2%×基荷)；请按现场最小关心负荷改
  nilm.quantity = p   nilm.rel_tol_pct = 0.05   nilm.min_delta_pct = 2.06
  threshold     min_delta_w=37000  settle_cycles=5  settle_tol_w=150  max_rise_cycles=40
  …（6 行，一算法一行）
```

第 1 行告诉你**数据怎么被理解的**（对象、口径、检测量及其来源）；第 2 段是量出来的数（含义见 §3 的"靠不靠谱"表与附录 E）；第 3 段就是可以填进界面「检测参数」的值。

### H.3 用法 2：针对一台设备——给出最小关心负荷（现场最常用）

```powershell
# 这台设备额定 300 kW（一次侧口径）
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --config configs\default.json --min-load-w 300000
```

此时 `min_delta_w = max(最小关心负荷/2, 6σ)`，门槛放在设备幅值的一半、但不低于噪声底，其余算法参数据此联动（CUSUM 的 `drift/threshold`、GLR 的 `noise` 等，见附录 E / G.8）。关键看注释行：

- `min_delta_w = max(最小关心负荷/2, 6σ)` 且无 ⚠ → 好检，继续；
- `⚠ 最小关心负荷 … 的一半低于噪声底 …` → 这台设备在这一侧淹没在噪声里，换**分路侧**文件重跑（附录 D）。

### H.4 用法 3：指定配置文件 / 指定对象 / 限制分析长度

```powershell
# 用现场配置（PT/CT、列映射与生产一致），只量 A 相
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --config configs\site.json --channel A --min-load-w 300000
# 文件很大（几十分钟），只分析前 6000 个周波（≈2 min@50 Hz）
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg_long.csv --max-cycles 6000 --min-load-w 300000
```

`--config` 决定三件事：① PT/CT 与列映射（影响量出来的数值和单位口径）；② 缺省检测量 `nilm.quantity`；③ `--apply` 的基准。**不填**时取界面保存过的 `configs\runtime.json`，没有才是 `configs\default.json`——所以在已经用界面改过 PT/CT 的机器上，不填 `--config` 得到的就是"和界面一样"的口径。

### H.4′ 用法 3′：只分析文件中的一段时间（v0.52）

背景文件里只有某一段是"干净稳态"时，不必先切文件：

```powershell
# 08:00:10 ~ 08:00:40 这 30 s（与文件时标当天时刻比较，也可写完整日期或 epoch 秒）
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --t-start 08:00:10 --t-end 08:00:40 --min-load-w 300000
# 从 08:00:10 起 30 s
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --t-start "2026-10-13 08:00:10" --duration 30 --min-load-w 300000
# 文件开头起 20 s
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --duration 20 --min-load-w 300000
```

首行之后多一行「时间段  起 → 止   实际 <首个周波时刻> → <末个周波时刻>」，请核对"实际"一栏确认落在你想要的段上。三个参数都不填＝整个文件（受 `--max-cycles` 限制）。段内没有数据、结束早于开始、时间文本无法解析都会退出码 2 并说明原因。JSON 输出里对应 `t_range{start,end,duration_s,t_first,t_last,whole_file}`。

### H.4″ 用法 3″：让脚本从分路侧录波里估计最小关心负荷（v0.55）

**能不能从文件直接得到最小关心负荷？** 分情况：

- **纯背景文件（没有投切）**：不能。文件里只有噪声，只能量出"能检出的最小幅值"≈6σ，这不是"关心"的含义。此时脚本按未指定处理（`max(6σ, 2%×基荷)`）。
- **分路侧、含设备启停的录波**：可以——文件里就有这台设备的负荷台阶。脚本用与 H.4‴ 相同的"是否在动"判据（25 周波滑动均值前后窗之差 / 单周波 |Δ|>6σ）把逐周波 P（或 I）切成"不动 ≥ 25 周波"的稳态台阶（启动冲击、软启斜坡、跨周波边界被劈成两半的阶跃都算"在动"，不会被并进稳态），再取 **min(相邻稳态最小跳变幅值, 台阶最小间距)** 为候选值；候选 ≥ 20σ 且 ≥ 1 % 最大台阶才算"可靠"。JSON `candidate_from`：`step`＝文件里直接看到过这么大的一次投切；`level_gap`＝来自两个**不相邻**状态之差（没直接看到这么小的投切，note 会写明，更可能是上界候选）。
  > v0.57 修复：v0.55 按相邻周波 |Δ| > 8σ 切段，软启斜坡（每周波只变零点几 σ）和被劈成两半的阶跃（每半 < 8σ）切不开，斜坡 + 平台会并成一段、中位数变成无意义的中间值，候选错却标"可靠"（现场形状的合成数据：真值 1.16 A，旧版给 2.24 A ✓可靠）。
- **总线侧多设备混合文件**：量出的是"所有设备里最小的一次"，不是目标设备的——不要在总线侧用它（附录 D 的分工）。

```powershell
# 分路侧录波（含这台设备的开/关）：自动估计并直接用于建议参数
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\dev_onoff.csv --config configs\branch_runtime.json --min-load-auto
```

输出多一段：

```
—— 最小关心负荷估计（文件投切台阶）——
  候选 3e+05 W  （最小跳变 4.5e+05，最小台阶间距 3e+05，稳态段 4，台阶 [1501000, 1801000, 2250000]）  ✓ 可靠  → 本次已采用（--min-load-auto）
```

不加 `--min-load-auto` 时这一段也会打印（仅供参考，不采用）；手填了 `--min-load-w/-a` 时手填优先。JSON 里对应 `min_load_estimate{candidate, min_step, min_level_gap, levels, n_steady, n_events, reliable, note}`、`min_load_used`、`min_load_source = manual | estimated | none`。

**v0.80 分簇与拼接检测**：文件里同时有主负荷启停（如 19 A）和二级小波动（如 0.6 A）时，最小投切是二级波动，按它定门槛会把每个二级波动都报成事件。估计器把投切幅值按对数间隙分两簇（最大/最小 > 10 倍、排序后相邻比 > 5 处切开）：JSON 多出 `max_step, step_ratio, split, primary_step, secondary_step, n_primary, n_secondary`，分簇时 `reliable=False`（`--min-load-auto` 不自动采用），由你决定：只关心主负荷 → `--min-load-a <primary_step>`（界面「取值方式＝按最大台阶」）；二级波动也要报 → 候选值（「按最小台阶」）；或手填。另有 `repetition{suspected, period_s, match_pct}`：逐周波序列按固定周期逐位重复 ≥ 80 % 即告警「文件疑似模板拼接」——同一次投切被复制成多次，噪声统计与事件计数不代表真实现场，请换连续真实录波。

> 它给的是**上界候选**：样例里设备有 1.5 / 1.8 / 2.25 MW 三档，候选 300 kW 能覆盖它所有状态变化；若现场只关心主负荷（750 kW 启停）、不关心二级档位切换，请手工改大。界面上对应「从文件投切台阶估计最小关心负荷」勾选和结果区的「填入输入框」按钮（H.13）。

### H.4‴ 用法 3‴：慢启动 / 软启斜坡——`steady_state` 的暂态上限自动放大（v0.56）

**现象**：电机、风机、变频设备投入时电流不是一步到位，而是几秒到几十秒的斜坡（现场分路侧曾录到 ~40 s 从 1.66 A 爬到 4.56 A）。
`threshold / median_diff / two_window / glr` 只看"突变"，对这种斜坡只会报其中的硬跳变（起动冲击、硬切），爬坡本身漏掉；
只有 `steady_state`（稳态分段）能把"两个稳态之间的东西"整体当一次事件——前提是它的 `max_transient_cycles`（默认 100 周波 = 2 s）
装得下整条斜坡，而且 `min_steady_cycles` 要比斜坡上"极差刚好不超 tol 的伪平台"长（否则斜坡被切成一串 < min_delta 的小台阶，照样配不出事件）。

**脚本现在自动做**（`suggest` 收到逐周波序列时）：
1. 量**最长暂态**：25 周波滑动均值前后窗之差 > max(4σ√(2/25), 5%·min_delta) 或单周波 |Δ| > 6σ 处记为"在动"，连续不动 ≥ 10 周波为锚点稳态，相邻锚点均值差 ≥ min_delta 之间的周波数即一次暂态；
2. 最长暂态 ≤ 100 周波：参数不变（`max_transient_cycles=100`、`min_steady_cycles=10`）；
3. 最长暂态 > 100 周波：`steady_state.max_transient_cycles = ⌈1.5 × 最长暂态⌉₂位`，`min_steady_cycles = ⌈1.5 × 斜坡上最长伪平台 + 1⌉₂位`（≥10，封顶 250），并在需要时给出 `nilm.window_cycles ≥ max_transient + 2×min_steady + 20`（检测窗装不下暂态+前后稳态时稳态配对永远配不成；`--apply` / 界面「套用」只放大不缩小 window_cycles）。

```powershell
# 样例：8 s 软启斜坡（tools/gen_nilm_sample.py --soft-start → data/nilm_softstart.csv）
.\.venv\Scripts\python.exe tools\gen_nilm_sample.py --soft-start
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\nilm_softstart.csv --min-load-w 1000
```

输出里 note 多一句：`文件中最长暂态 427 周波（8.5 s @50Hz，慢启动/软启斜坡），steady_state.max_transient_cycles 放大到 650、min_steady_cycles 抬到 33（斜坡上最长伪稳态平台 21 周波，稳态必须比它长），nilm.window_cycles 需 ≥ 740 …`；
文本输出多一行「最长暂态 … 周波（暂态 n 次，锚点稳态 m 段）」，JSON 里对应 `suggest.transient`（longest / n_transients / n_steady / transients[≤5] / max_pseudo_steady / max_transient_cycles / min_steady_cycles / window_cycles）与可选的 `suggest.window_cycles`。

> 代价：`min_steady_cycles` 抬高后，事件要等新稳态积满这么多周波才出现（33 周波 ≈ 0.7 s），且两次投切之间的平台短于它时会被当成同一段暂态；伪平台封顶 250 仍放不下的超缓斜坡（note 带 ⚠），稳态分段只能报其中的硬跳变。
> 其它四种算法不动：它们对斜坡无能为力，加大 `max_rise_cycles` / 窗长只会增加误报，不如让 `steady_state` 负责斜坡。

### H.5 用法 4：机器可读输出 `--json`（供回放脚本 / 接口 / 留档）

```powershell
New-Item -ItemType Directory -Force output | Out-Null
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --config configs\default.json --min-load-w 300000 --json > output\tune.json
```

JSON 结构（节选）：

```json
{
  "file": "data/bus_bg.csv", "channel": "total", "fs": 6400.0, "f_nom": 50.0,
  "quantity": "p", "quantity_requested": "auto", "unit": "W", "voltage_present": true, "scaled": true,
  "t_span_s": 5.98,
  "measure": { "cycles": 300, "level": 1800012.7, "sigma_cycle": 27.9, "range5_p95": 122.5, "range10_p95": 161.9, "sigma_mean10": 14.8, "has_events_hint": true, "...": "..." },
  "suggest": {
    "note": "min_delta_w = max(最小关心负荷/2, 6σ)", "quantity": "p",
    "rel_tol_pct": 0.05, "min_delta_pct": 0.01,
    "algorithms": { "threshold": { "min_delta_w": 150000, "settle_cycles": 5, "settle_tol_w": 150, "max_rise_cycles": 40 }, "median_diff": { "...": "..." }, "two_window": {}, "cusum": {}, "glr": {}, "steady_state": {} }
  }
}
```

这份文件可以：`nilm_replay.py --params output\tune.json`（§5）；`POST /api/nilm/tune/apply` 的 `params`（§7-2′）；界面「套用 nilm_tune 结果」直接选它。stderr 的警告不会混进 JSON，重定向是安全的。

### H.6 用法 5：数据源只有电流——按 I 口径调参（详见附录 F）

```powershell
# 文件没有电压列（或电压全 0）：auto 自动按电流有效值 I 统计；--min-load-a 为设备额定电流（一次侧 A）
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg_i.csv --min-load-a 30
# 文件有电压、但生产上就是按电流检测：显式 --quantity i（或把 --config 里 nilm.quantity 设成 i，脚本会跟随）
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --quantity i --channel B --min-load-a 30 --json > output\tune_i.json
```

首行会写「检测量 电流有效值 I（… 数据源无电压 → auto 选 I）」，建议行全是 `*_a` 参数并带 `nilm.quantity = i`。两种会直接退出（码 2）的误用：

```powershell
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg_i.csv --quantity p
#  ⚠ 数据源没有电压（电压列未映射或全为 0）：有功恒为 0，无法按 P 调参；请用 --quantity i（或 auto）
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg_i.csv --min-load-a 30 --channel total
#  ⚠ 仅电流（I 口径）检测不存在跨相合并 … 只能单相：--channel 请填 A / B / C
```

I 口径下给了 `--min-load-w` 会被忽略并提示「I 口径请用 --min-load-a」。

### H.7 用法 6：`--apply`——直接生成"套好参数的完整配置"（v0.50）

```powershell
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --config configs\default.json --min-load-w 300000 --apply
```

在正常输出之后多一段：

```
—— 已更新配置（--apply）——
  基准配置   configs\default.json
  已保存到   output\nilm\nilm_tuned_config_20261021_103000.json   （完整配置，可作 --config / ELEC_TOOL_CONFIG_PATH 使用，或 nilm_replay.py --config 回放核对）
  配置文件   未改动（默认；要回写加 --save-config）
```

规则：只替换 `nilm.quantity / rel_tol_pct / min_delta_pct` 和 6 种算法里建议给出的键；各算法 `enabled`、建议没给的键、PT/CT、列映射、输出目录等全部保留；写出前经过与界面保存同样的配置校验。文件末尾的 `_tuning` 块记录来源文件、对象、时间和逐项改动，软件加载时忽略它。

`--json` 与 `--apply` 可以同时用，JSON 里多一个字段：

```json
"applied": { "base_config": "configs/default.json", "saved_to": "output/nilm/nilm_tuned_config_20261021_103000.json",
             "changes": ["nilm.quantity = p", "nilm.rel_tol_pct = 0.05", "threshold: min_delta_w=150000  settle_cycles=5  settle_tol_w=150  max_rise_cycles=40", "..."],
             "config_file_updated": false }
```

### H.8 用法 7：`--apply --out`——指定输出文件名

```powershell
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --min-load-w 300000 --apply --out output\site_tuned.json
# 之后回放直接用它当配置，不再需要 --params：
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\dev_onoff.csv --config output\site_tuned.json --out output\replay_events.csv
```

### H.9 用法 8：`--apply --save-config`——显式回写配置文件

```powershell
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --config configs\site.json --min-load-w 300000 --apply --save-config
#   配置文件   已回写（--save-config）
```

只有加了这个开关才会改 `--config` 指向的文件（没给 `--config` 时就是 `configs\runtime.json` / `default.json`，请确认你真的想改它）。输出目录里的副本仍会生成。**正在运行的软件不会自动重载**，要么重启，要么按 §7-2′ 用界面 / `POST /api/nilm/tune/apply` 推送。基准文件不存在时（例如没给 `--config` 且两份默认文件都不在）会报错退出，不会凭空创建。

### H.10 用法 9：直接套到运行中的软件（不经文件）

脚本本身不连软件；把 `--json` 的输出交给接口即可，软件在**当前侧正在运行的配置**上更新并写 `output\nilm\nilm_tuned_config_<bus|branch>_<时间戳>.json`，默认不写配置文件：

```powershell
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg.csv --min-load-w 300000 --json > output\tune.json
$body = [System.Text.Encoding]::UTF8.GetBytes('{"params": ' + (Get-Content output\tune.json -Raw -Encoding UTF8) + ', "hot": true, "persist": false}')
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/nilm/tune/apply -ContentType 'application/json; charset=utf-8' -Body $body | Select-Object ok, saved_to, config_file_updated
# 分路侧：/api/branch/nilm/tune/apply；"persist": true 才回写运行配置文件；"hot": false 只写文件不改运行参数
```

或在界面「负荷辨识 → 检测参数 → 套用 nilm_tune 结果」里选 `output\tune.json`。

### H.11 组合示例：从拿到数据到上线的最短路径

```powershell
# ① 量噪声 + 生成完整配置（不改配置文件）
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\dev_bg.csv --config configs\site.json --min-load-w 300000 --apply --out output\site_tuned.json --json > output\tune.json
# ② 用它回放含已知投切的文件
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\dev_onoff.csv --config output\site_tuned.json --out output\replay_events.csv
# ③ 对账
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\replay_events.csv --truth data\truth.csv
# ④ ✅ 后推送到运行中的软件（§7-2′），或 ⚠/✗ 则回到 §6 微调
```

### H.12 常见问题速查

| 现象 | 原因 | 处理 |
|---|---|---|
| `没有读到整周波数据`（退出码 2） | 文件不足一个周波 / 列映射不对 / fs 配错 | 检查 `--config` 的 `columns`、`sampling.fs` |
| 首行「口径 二次侧」但现场参数是一次侧 | `--config` 里 `transform.enabled=false` 或没指到现场配置 | 指定正确的 `--config` |
| 建议值与界面显示差了 PT×CT 倍 | 同上，口径不一致 | 同上 |
| `max|diff|` 带 ⚠ | 背景段混了投切 | 允许（稳健统计），建议切两半各跑一次比对 σ |
| `nilm.min_delta_pct` 被置 0 并提示"基荷相对门槛过小" | 基荷很小（设备侧、设备关着） | 正常：门槛以各算法绝对值 W/A 为准 |
| `--apply` 后界面没变 | `--apply` 只写输出目录文件，不碰运行配置 | 用 §7-2′ 推送，或 `--save-config` 后重启 |

### H.13 用法 10：在 Web 界面「数据处理」里做同样的事（v0.52）

「🧮 数据处理」页下半部分「负荷辨识调参（量背景噪声 → 6 种算法参数）」与本脚本**同一实现**（`POST /api/process/nilm_tune`），对应关系：

| 界面项 | 对应命令行参数 | 说明 |
|---|---|---|
| 波形文件（下拉 / 路径） | `--file` | 下拉列出 `data\` 下的 CSV；也可手填仓库内相对路径或绝对路径 |
| 起始时间 / 结束时间 | `--t-start` / `--t-end` | 都留空＝整个文件 |
| 或 时长 (s) | `--duration` | 与结束时间同时填时取先到者 |
| 基准配置（总线侧 / 分路侧运行配置） | `--config` | 用该侧**正在运行**的配置的 PT/CT、列映射、缺省 `nilm.quantity`；不改动它 |
| 检测量 / 检测对象 | `--quantity` / `--channel` | 留空＝跟随配置 / 默认对象 |
| 最小关心负荷 (W) / (A) | `--min-load-w` / `--min-load-a` | |
| （自动）慢启动斜坡 | （自动） | v0.56：结果区「暂态」行显示最长暂态周波数 / 秒数、暂态次数、锚点稳态段数；>100 周波时 steady_state 的 max_transient_cycles / min_steady_cycles 已放大、nilm 行附 window_cycles，「套用」一并写入（H.4‴） |
| 从文件投切台阶估计最小关心负荷（勾选） | `--min-load-auto` | v0.55：未手填时由文件里的投切台阶估计（H.4″）；结果区「最小关心负荷估计」行显示候选 / 可靠性 / 依据与是否已采用，「填入输入框」把候选写进 W 或 A 输入框并取消勾选，再点一次即按手填值计算 |
| 保存为配置文件（原配置基础上更新算法参数）+ 文件名 | 相当于 `--config <本侧原配置文件> --apply --out output\nilm\<文件名>` | **默认不保存**；勾选后以所选侧的**原配置文件**（总线侧 `configs\runtime.json`、分路侧 `configs\branch_runtime.json`，即界面改动的持久化文件）为基准，**只更新** `nilm.quantity / rel_tol_pct / min_delta_pct` 与各算法建议参数，**其它参数原样保留**，把更新后的完整配置写到 `output\nilm\<文件名>`（留空＝`tune_{时间}.json`，可写 `{时间}` 占位符）；原配置文件本身不改动。文件可直接作 `--config` / `ELEC_TOOL_CONFIG_PATH` / 回放配置使用，`_tuning` 块里附带本次 measure/suggest 与时间段。原配置文件尚不存在（界面从未保存过）时以该侧当前运行配置为基准并在结果里注明（v0.53） |
| 「套用到运行配置」按钮 | 相当于 §7-2′ 的 `POST /api/nilm/tune/apply` | 把本次结果热生效到所选侧，更新后的完整配置写 `output\nilm\nilm_tuned_config_<侧>_<时间戳>.json`，**不写配置文件** |

**等价命令（v0.54）**：每次运行后结果区多一行「等价命令」（带「复制」按钮），结果 JSON 的 `command` 字段、保存文件的 `_tuning.command` 也带同一条——即与这次界面操作完全等价的 `tools/nilm_tune.py` 命令：只列实际填写的参数，`--config` 为该侧原配置文件（不存在则省略），勾选保存时追加 `--apply --out <保存路径>`。例：`python tools/nilm_tune.py --file data/bus_bg.csv --config configs/runtime.json --min-load-w 300000 --t-start 08:00:10 --duration 30 --json --apply --out output/nilm/tune_20261021_103000.json`。用途：留档、在 PowerShell 复现（把 `python` 换成 `.\.venv\Scripts\python.exe`，含空格的路径已自动加引号）、或改几个参数再跑。

结果区：第一行＝文件 / 对象 / 周波数 / 时长 / 口径 / 检测量；第二行＝时间段与实际落到的首末周波时刻；之后是噪声统计表与建议参数表（与命令行输出逐项相同）；「原始结果 JSON」可展开复制。错误（文件不存在、时间文本无法解析、段内无数据、I 口径填三相总）直接显示在结果区，不会改动任何配置。

### H.14（v0.90）在 Web 界面里提取设备画像、启用「设备画像匹配」

命令行 `tools/nilm_profile.py` 与「🧮 数据处理」页「**设备画像提取**」区（紧跟在「负荷辨识调参」之后，`POST /api/process/nilm_profile`）同一实现：

| 界面项 | 对应命令行参数 | 说明 |
|---|---|---|
| 波形文件 / 起止时间 / 自定义时间 / 基准配置 / 列映射 | `--file` `--t-start` `--t-end` `--custom-time*` `--config` | **沿用上方「负荷辨识调参」区当前填写的公共配置**（独立基准配置或某侧运行配置），本区不重复出现；先在上方选好**设备侧**文件 |
| 设备 ID | `--device` | 写进画像与事件表 |
| 启停标签（多行文本） | `--labels` | 每行「时间,动作」；时间写法同真值表；留空＝自动定位 |
| 标签时刻容差 (s) | `--label-tol` | 默认 2 |
| 前窗 / 后窗 (周波) | `--pre` / `--post` | 后窗 ≥ 设备启动过程；总线侧确认事件也要等这么多周波 |
| 画像文件名 | `--out` | 写到 `output\nilm\`，留空＝`profile_{设备}_{时间}.json` |
| 「提取设备画像」 | 运行 | 结果区：状态行（设备 / 口径 / 标签方式 / 前后窗）、等价命令、启动 / 停止画像表（μ、σ 与逐事件 7 维特征、标签来源）、原始 JSON；⚠ 提示同命令行 |
| 「填入总线侧画像路径」/「填入分路侧画像路径」 | 手工把路径写进 `nilm.profile_path` | 把本次画像路径填进该侧「负荷辨识」页的「画像文件路径」框并**勾选「设备画像匹配」**，表单标脏；**要到负荷辨识页点「保存总线侧 / 分路侧配置」才生效** |

「负荷辨识」页：算法面板最后一个是「设备画像匹配」（两侧各一份），含画像文件路径、6 个参数（附录 A）、加载状态行（设备 / 口径 / 启动·停止样本数 / 当前设备状态 / 最近候选与拒识原因）。事件表中 `profile` 行的「检验量」列显示 `设备 ID · 置信度 (D²=…, 标记)`，低置信事件带「低置信」徽标；筛选 / 标注下拉里也有它。勾选「自适应算法参数」时其它算法参数灰显，`profile` 的参数**不灰显**（不由自适应推导）。

常见提示：「设备画像匹配已勾选但 nilm.profile_path 为空」→ 先提取画像再填路径；「画像加载失败：…」→ 路径错 / 文件不是画像 JSON；「画像按 A 口径构建，本侧检测量为 P」→ 两边口径不一致，统一 `nilm.quantity` 或重提画像。

