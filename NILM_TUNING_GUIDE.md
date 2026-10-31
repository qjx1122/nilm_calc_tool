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
#     ⚠ 启动画像只有 1 次事件（建议每方向 ≥3 次启停）：σ 取经验下限（…）   ← 出现这行就再录几次
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

**常见坑（v0.92）：启动事件 ΔI<0、停止事件 ΔI>0。** 先跑 `python tools/nilm_profile_diag.py --profile <画像.json>`：
- 提示「ΔP 与 ΔI 异号」⇒ 有功为负（CT 接反 / 电压电流相别未配对）。在「数据源与控制 → 量纲与口径」勾选该侧的 **电流极性反转**（`transform.invert_current`）后重提；不修的话画像里 ΔP/ΔQ 符号与总线侧相反，在线必然匹配不上。
- 同方向事件几秒内连续出现多次（一次启动被稳态分段切碎、分级带载、反复重启）⇒ 自动定位模式用「合并间隔」（`--merge-gap`，默认 10 s）合并，或直接给标签。
- **P 口径能找到的事件 I 口径找不到（或反之）** ⇒ 跑 `python tools/nilm_profile_diag.py --file <设备侧.csv> --config <基准配置> --at 15:01:15`，它按口径打印 tol / min_steady / max_transient / min_delta 和该时刻前后的稳态段：常见是「前后稳态段间隔 > max_transient」（电机启动电流慢衰减）或「一侧没有稳态段」（该口径波动相对 tol 太大）。v0.92.1 起自动定位会用双滑窗补充这类事件（`source=auto:two_window`），但其 ΔI/ΔP 可能取在过渡中，仍建议加大 `--post` 或给标签。
- **在线一个事件都不报** ⇒ 用回放看候选明细：`python tools/nilm_replay.py --file <本侧文件> --config <本侧配置>`（profile 勾选时末尾打印「设备画像匹配诊断」：每个候选的方向 / D²/维 / 置信 / 标记 / 最大贡献维）。没有候选 ⇒ 幅值口径不一致（PT/CT、检测量 P/I）或数据里没有 ≥ 画像最小 |Δ| 一半的台阶；有候选但 `d2_exceeds` ⇒ 看最大贡献维：`d_q` 多为无功符号/幅值与画像不符（单样本画像 σ 只有 25 % 下限），`d_p/d_ia` 多为启动后窗落在过渡中（加大 post）或 PT/CT；`state_mismatch` ⇒ 状态机与实际不符，可先把 `state_check` 置 0。
- 启动过渡长于后窗（`dur_cycles` 顶到 post、template 末端远大于 1）⇒ 把 `--post` 放大到 ≥ 启动过程周波数（大电机常需 200+）。

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
| `profile` 设备画像匹配（v0.90，v0.99.26 加谐波维） | 拿每个台阶前后的 ΔIa/ΔIb/ΔIc/ΔP/ΔQ/启动冲击比/持续周波/Δ谐波电流 这 8 个数，和事先录好的这台设备"画像"比，像的才报，并给**置信度**和**设备 ID** | 总线上多台设备时**只报这一台**、能分开/关；设备侧录波必不可少；两台长得一样的设备分不开；不做幅值校准 | **默认关闭**；`nilm.profile_path`（画像文件，§5-C ① 生成）；`d2_max`（每维平均允许偏几个 σ²，默认 9＝平均 3σ；漏报放大、误报缩小）；`min_confidence`（最低置信度，默认 0.3；误报多 → 0.5）；`k_sigma`（候选台阶要超过前窗噪声几倍，默认 4；候选缺失 → 3）；`margin`（启动/停止 D² 比至少多少才算方向明确，默认 1.5）；`lambda_rel`（协方差收缩，默认 0.1，一般不动）；`state_check`（1＝启用 OFF→开 / ON→关 状态机，默认 1）。**不受「自适应算法参数」影响**，`nilm_tune.py` 也不给它建议值——它的"噪声尺度"来自画像的 σ |

**全局参数**（`nilm.*`）：

| 参数 | 含义 | 建议 |
|---|---|---|
| `channels` | 检测对象：`total` 三相总有功 / `A` `B` `C` 分相 | 三相设备用 `total`；单相设备用它所在的相 |
| `window_cycles` | 算法只看最近多少个点（默认 300 = 6 s） | ≥ 2 × 暂态周波数 + 100；电机软启动 2 s → ≥ 300 |
| `min_gap_cycles` | 同一算法两次事件最小间隔（默认 10 = 0.2 s） | 重复报 → 调大；快速连续投切 → 调小 |
| `rel_tol_pct` | 容差至少是基荷的百分之几（默认 1.0） | 基荷大、设备小时降到 0.1~0.3；`nilm_tune` 会给 |
| `min_delta_pct` | 最小台阶至少是基荷的百分之几（默认 0） | 一般用 `nilm_tune` 给的值 |
| `profile_path`（v0.90；v0.99.26 支持多画像） | 设备画像 JSON 路径（相对软件目录），只给 `profile` 算法用；**多个设备用 `;` 分隔**（也可用 `nilm.profile_paths` 列表，最多 8 个） | 由 `tools/nilm_profile.py` 或界面「数据处理 · 设备画像提取」生成；空＝即使勾了 `profile` 也不检测（界面与 summary.notes 会提示）；多画像各自独立状态机 / 去重，事件以 `device_id` 区分 |

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
3. **每次事件取特征向量**（v0.99.26 起 8 维）`FEATURES = [d_ia, d_ib, d_ic, d_p, d_q, peak_ratio, dur_cycles, d_ih]`：
   - `d_*` ＝ 事件后窗 `[end, end+post_cycles)` 的中位数 − 事件前窗 `[onset−pre_cycles, onset)` 的中位数（前后差分，不受基荷影响）；
   - `peak_ratio` ＝ 事件窗内三相电流合成量相对前窗基线的**最大偏移 / 稳态偏移**（≥ 1；电机直启 1.5~6，阻性负荷 1.0）；
   - `dur_cycles` ＝ 从起点到"进入事件后电平 ±20 % 带"的周波数（启动过程长短）；
   - `d_ih`（v0.99.26）＝ 同一前后窗的 **2~13 次谐波电流有效值合量之差**（A，三相平均；`√ΣI_k²`）。设备是谐波源（整流 / 变频 / UPS）时 ≈ 设备自身的谐波贡献（本案例 +14~15 A），线性负荷（电机 / 电阻）≈ 0——用来把"功率电流都像、但不带谐波"的负荷区分开；
   - 另存一条 **16 点归一化轨迹模板**（事件窗内合成电流相对基线的变化 / 稳态变化，时间归一化），作为"启动形状"证据。
4. **启动 / 停止各自统计**：中心 μ ＝ 各次均值，σ ＝ 各次标准差，但 σ 不小于 `max(相对下限 × |μ|, 绝对下限)`（相对下限：电流 / 有功 / 谐波电流 15 %、无功 25 %、峰值比 30 %、持续周波 50 %；绝对下限：0.02 A / 5 W / 5 var / 0.1 / 2 周波 / 2 A 谐波电流）——这样 1 次事件也能用，但 notes 会 ⚠ 建议 ≥ 3 次。模板取各次均值，并记录各次与均值的 RMS 散布 `template_spread`。
5. 写成一个 JSON（schema `nilm_profile/1`）：`device_id / quantity(p|i) / unit / pre_cycles / post_cycles / features / startup{n, mu[8], sigma[8], template[16], template_spread, dur_cycles{min,max}, events[…逐事件 vec/t_start/source]} / shutdown{同} / harmonic{orders, unit, feature} / calibration{bus_mapping: null} / notes / command`。**旧画像（v0.99.25 及更早）是 7 维**——加载后按 7 维参与匹配（第 8 维不提供证据），D² 的维度 d 也仍取 7，置信度口径不变；要吃到谐波维需重新提取一次。

**(b) 总线侧在线检测**（`detect_profile`，每块数据到达后在最近 `window_cycles` 个周波的窗上跑一次，对象固定为**三相合成**）

| 步骤 | 做法 | 参数 |
|---|---|---|
| ① 候选 | 稳健双滑窗：前窗长 = 画像 `pre_cycles`、后窗长 = `post_cycles`，`\|mean(后) − mean(前)\| ≥ max(min_d, k_sigma × 前窗标准差)` 的连通区取峰值为 onset；`min_d` ＝ 画像里启动 / 停止 \|ΔP\| 最小者的一半（I 口径用 √(ΔIa²+ΔIb²+ΔIc²)）；终点 ＝ onset 后首个进入事件后电平 ±20 % 带的周波（封顶 `post_cycles`） | `k_sigma`（默认 4） |
| ② 特征 | 对每个候选按 (a)-3 同一公式取**与画像同维度**的向量（新画像 8 维含 `d_ih`、旧画像 7 维）与 16 点模板（用的是**总线侧**的 P/Q/I 与逐周波谐波电流序列） | — |
| ③ 匹配 | 与启动、停止画像分别算**对角马氏距离** `D² = Σ_j (x_j − μ_j)² / (σ_j² + λ·median(σ²))`（λ 收缩避免某一维 σ 过小一票否决）；取 D² 小者为方向 `START/STOP`；`margin` ＝ 另一方向 D² / 本方向 D²（越大方向越明确）；轨迹：模板 RMS 距离 `td` > 3 × `template_spread` 时置信度乘 `max(0.3, 3·spread/td)`，并打 `trajectory_deviates` | `lambda_rel`（默认 0.1） |
| ④ 置信度 | `confidence = exp(−D² / (2·d)) × 轨迹折扣`，**d ＝ 画像实际维度**（v0.99.26 之后提取的 8、旧画像 7）。直觉：每维平均偏 1σ → D² = 7 → 0.61；平均偏 2σ → 0.14；平均偏 3σ（D²/d = 9）→ 0.011 | — |
| ⑤ 拒识 | `D²/d > d2_max` → `d2_exceeds`（直接拒）；`margin < margin` → `ambiguous_direction`（只打标记）；状态机：当前已 ON 又来 START、或已 OFF 又来 STOP → `state_mismatch`，置信度 × 0.5；最终 `confidence < min_confidence` → 拒 | `d2_max`（默认 9）、`margin`（1.5）、`min_confidence`（0.3）、`state_check`（1） |
| ⑥ 状态机 | 接受的 START → 设备状态 `on`，STOP → `off`（初始 `unknown` 时第一个事件不做状态检查）；状态写在 `summary.profile.device_state`，界面画像面板可见 | `state_check` |
| ⑦ 确认与去重 | 事件终点之后窗里还要有 ≥ `post_cycles` 个周波才输出（所以比 6 种标量算法滞后约 `post_cycles` 周波）；同一事件在后续窗里按全局周波号去重（`min_gap_cycles` 同样适用） | — |

**(c) 输出**：`NilmEvent` 公共字段照旧（`t_start/t_end/direction(up=START,down=STOP)/delta_p_w/delta_q_var/delta_i_a/pre_p_w/post_p_w`，`score` ＝ 置信度），另加 `device_id / confidence / d2 / profile_direction / status(confirmed|low_confidence) / quality_flags`；`to_dict` 里 `observed_delta_p` ＝ 总线侧观测 ΔP、`estimated_device_delta_p = null`。事件 CSV `nilm_events_*.csv` 末尾多 6 列（旧文件自动改名 `.pre-v090.csv`），v0.99.26 起再加一列 `delta_ih_a`（本次事件的谐波电流增量，A）。`summary.profile.last` 保留最近 20 个候选（含被拒的）及各维 `contrib`（每一维对 D² 的贡献）——排查漏报 / 误报先看它。

**(d) 与标量算法的区别与限制**

- 不参与「自适应算法参数」（它的噪声尺度来自画像 σ，不是窗内数据）；`nilm_tune.py` 不给它建议值；`NILM_SCALAR_ALGOS` 只含原 6 种。
- 画像与总线侧 `nilm.quantity` 口径必须一致，否则不检测并在 `summary.errors` 说明。
- 设备侧电流 ≠ 总线侧增量（变压器 / 补偿 / 损耗）；本版不做校准，差异大时请用总线侧"只有这台设备在动"的录波提画像（§5-C）。
- 两台特征相近的设备会互相高置信度匹配——这是相似性匹配的固有局限，不是参数问题；此时只能到分路侧。
- 多画像（v0.99.26）：`nilm.profile_path` 用 `;` 分隔多个画像（或 `nilm.profile_paths` 列表），最多 8 个；每个画像独立状态机 / 去重，事件以 `device_id` 区分。**仍是"一画像一设备一工况"**：不做多设备联合判决（两台同时启动各报一条），同一 `device_id` 重复挂载会提示。
- 谐波维度 `d_ih`（v0.99.26）：第 8 维是事件前后 2~13 次谐波电流合量之差（A，三相平均）。它是"线性负荷 vs 整流 / 变频类设备"的分水岭；旧 7 维画像照旧可用，但**重新提取一次**才能用上这条证据（`summary.profile.profiles[i].has_harmonic` 为 false 说明是旧画像）。

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
| 波形文件 / 起止时间 / 自定义时间 / 基准配置 / 列映射 / 检测量 | `--file` `--t-start` `--t-end` `--custom-time*` `--config` `--quantity` | v0.99.5 起为**本区独立的一套配置**（与上方「负荷辨识调参」互不影响）：独立基准配置或沿用某侧运行配置；检测对象固定三相总 total（不可选）；选**设备侧**文件 |
| 设备 ID | `--device` | 写进画像与事件表 |
| 启停标签（多行文本） | `--labels` | 每行「时间,动作」；时间写法同真值表；留空＝自动定位 |
| 标签时刻容差 (s) | `--label-tol` | 默认 2 |
| 前窗 / 后窗 (周波) | `--pre` / `--post` | 后窗 ≥ 设备启动过程；总线侧确认事件也要等这么多周波 |
| 画像文件名 | `--out` | 写到 `output\nilm\`，留空＝`profile_{设备}_{时间}.json` |
| 「提取设备画像」 | 运行 | 结果区：状态行（设备 / 口径 / 标签方式 / 前后窗）、等价命令、启动 / 停止画像表（μ、σ 与逐事件特征、标签来源；v0.99.26 起含 `d_ih`）、原始 JSON；⚠ 提示同命令行 |
| 「填入总线侧画像路径」/「填入分路侧画像路径」 | 手工把路径写进 `nilm.profile_path` | 把本次画像路径填进该侧「负荷辨识」页的「画像文件路径」框并**勾选「设备画像匹配」**，表单标脏；**要到负荷辨识页点「保存总线侧 / 分路侧配置」才生效** |

「负荷辨识」页：算法面板最后一个是「设备画像匹配」（两侧各一份），含画像文件路径、6 个参数（附录 A）、加载状态行（设备 / 口径 / 启动·停止样本数 / 当前设备状态 / 最近候选与拒识原因）。事件表中 `profile` 行的「检验量」列显示 `设备 ID · 置信度 (D²=…, 标记)`，低置信事件带「低置信」徽标；筛选 / 标注下拉里也有它。勾选「自适应算法参数」时其它算法参数灰显，`profile` 的参数**不灰显**（不由自适应推导）。

常见提示：「设备画像匹配已勾选但 nilm.profile_path 为空」→ 先提取画像再填路径；「画像加载失败：…」→ 路径错 / 文件不是画像 JSON；「画像按 A 口径构建，本侧检测量为 P」→ 两边口径不一致，统一 `nilm.quantity` 或重提画像。



### H.15 设备侧提取 → 总线侧应用：可行性与接线不一致的影响（v0.99.6）

#### 1. 算法参数（`nilm_tune`，6 种标量算法）
| 参数类 | 来源应为 | 用设备侧文件提取后套到总线侧 |
|---|---|---|
| 噪声 / 容差类（`settle_tol_w`、`drift_w`、`threshold_w`、`noise_w`、`k_sigma`、`rel_tol_pct`） | **总线侧**稳态背景 | **不可行**：设备侧背景只有该设备或为空载，σ 远小于总线侧（多负荷叠加、波动大），套到总线侧会大量误报 |
| 幅值类（`min_delta_w` / `min_delta_a`、`min_delta_pct`） | 设备台阶幅值 | **可行**：设备侧文件「估计最小关心负荷」得到的台阶（P 口径）在总线侧按叠加原理不变；工具已支持「分路侧文件估计 → 套用到总线侧」 |
| 窗长类（`settle_cycles`、`pre/post_cycles`、`max_rise_cycles`、GLR `window_cycles`） | 设备过渡过程时长 | **可行**：由设备启动过程时长决定，与总线无关 |

推荐做法：**噪声类用总线侧稳态段量测，幅值类 / 窗长类用设备侧文件估计**，两次调参后分别套用（界面「套用目标」）。

界面对应（数据处理 · 负荷辨识调参，v0.99.11 起界面本身即按「第 ① 步 / 第 ② 步 / 第 ③ 步」三个分组排列）：
1. 波形文件选**设备侧**文件 → 勾「从文件投切台阶估计最小关心负荷」→ 量噪声 → 结果区「最小关心负荷估计」行点「填入输入框」（幅值类来源＝设备侧）；
2. 波形文件改选**总线侧稳态背景**文件 → 取消该勾选 → 基准配置「沿用总线侧运行配置」→ 再点「量噪声并给出参数」（噪声 / 容差类来源＝总线侧；此时建议参数表里 `settle_tol_w / drift_w / threshold_w / noise_w / k_sigma / rel_tol_pct` 全部来自总线侧背景，`min_delta_w` 来自第 1 步填入的值）；
3. 「套用目标」选总线侧 → 「套用到运行配置」。
调参区本身不区分"文件是哪一侧"——量的就是所选文件的背景噪声，所以第 2 步选对文件即可；不存在也不需要单独的"总线侧噪声"按钮。

接线不一致（总线三相三线两表法、分路三相四线）的影响：P 口径总有功两表法读数正确、不受影响；I 口径（单相电流）幅值在总线侧只对应设备所接的那一相，总线侧应选设备实际所接相别作为检测对象；B 相在总线侧无 CT 时勾选 3P3W 重构（Ib=−(Ia+Ic)）。

#### 2. 设备画像（`profile`）
| 特征 | 总线侧可比性 | 接线不一致影响 |
|---|---|---|
| ΔP / ΔQ | 可比（叠加原理） | 两表法总 P/Q 正确；需两侧 PT/CT 口径一致（见下） |
| ΔIa / ΔIb / ΔIc | 近似可比（同相位角下有效值差近似线性叠加） | **受相序影响**：设备 A 相可能接在总线 B/C 相 ⇒ 用 `profile.phase_map` 重排或设为 0 自动；总线三相三线未重构 ⇒ 跳过 ΔIb |
| peak_ratio / dur_cycles / 轨迹模板 | 可比（基于合成电流相对事件前基线的变化） | 不受影响 |

口径要求（v0.99.6 修正后）：两侧**都启用 PT/CT 并各填本侧真实变比**（变比不同没关系，比较在一次侧进行）；一侧启用一侧关闭**只提示不拒绝**（v0.99.22：设备侧记录仪常直接输出一次侧值，此时 PT/CT 关闭是对的；口径是否真差一个变比看候选诊断 CSV 的 ΔI 即可）；两侧都关闭只在两侧 CT 相同时可比。极性：设备侧与总线侧各自用 `invert_phases` 修到 P 为正，再比较。

结论：**画像从设备侧提取再用于总线侧是可行的**，前提是 ① 一次侧口径一致 ② 相序映射正确（或自动）③ 总线侧背景噪声下 `k_sigma`/`d2_max` 适当放宽。


## 附录 I（v0.99.7）：手把手——两种总线接线下，怎样把"设备侧调参 / 画像"用到总线侧做事件检测

> 读者：不懂算法的工程师 / 运维 / 交付 / 现场实施同学。只要会开网页、会点鼠标、会抄命令就能照做。
> 本附录不讲原理，只讲"**在哪个页面、填什么、点什么、看到什么算对**"。看不懂的词直接跳过，按步骤做即可。

### I.0 先记住 4 个事实（做完全部步骤再回头看也行）

1. **总线侧**＝进线总表那一路，上面挂着很多设备；**分路侧 / 设备侧**＝只带这一台设备的那一路。我们的目标：**在总线侧看出"这台设备"什么时候开、什么时候关**。
2. 软件里有 **7 种算法**。前 6 种（阈值差分 / 中值滤波差分 / 双滑窗 / CUSUM / GLR / 稳态分段）只回答"**总线上有没有东西开关、台阶多大**"，它们**认不出是哪台设备**；第 7 种「**设备画像匹配**」才回答"**是不是这一台**"。
3. 前 6 种算法的参数分两类：
   * "**多大的台阶才算事件**"（最小关心负荷）→ 用**设备侧**文件量出来，拿到总线侧用（设备开一次在总线上台阶一样大）；
   * "**背景抖多厉害**"（噪声 / 容差）→ **必须用总线侧**自己的平稳段量，设备侧量出来的太小，拿到总线侧会满屏误报。
4. 「设备画像」= 用**设备侧**文件提一份"这台设备开 / 关长什么样"的 JSON 文件，然后让**总线侧**去对照它。前提：两侧都勾「启用 PT/CT」并各填**自己真实的**变比（变比不一样没关系）。

### I.1 两个例子的现场情况

| | 例 1：总线三相三线 | 例 2：总线三相四线 |
|---|---|---|
| 总线侧接线 | **三相三线两表法**：只有 A、C 两相 CT，**B 相没有电流**（B 相电流列全 0 或没有）；电压是线电压 Uab、Ucb | **三相四线**：A、B、C 三相都有 CT，相电压 Ua/Ub/Uc |
| 总线侧 PT / CT | PT=100、**CT=40** | PT=100、**CT=15** |
| 设备侧（分路）接线 | 三相四线（三 CT），PT=100、**CT=15** | 三相四线（三 CT），PT=100、**CT=15** |
| 设备 | 22 kW 水泵 `pumpA`，直接启动（有 0.3 s 冲击） | 同一台泵 |
| 手上的文件 | `data\bus_bg_3w.csv`（总线侧平稳 1 分钟）、`data\bus_run_3w.csv`（总线侧含这台泵 2 次开关、还有别的设备开关）、`data\pumpA_dev.csv`（设备侧含 3 次开关） | `data\bus_bg_4w.csv`、`data\bus_run_4w.csv`、`data\pumpA_dev.csv` |
| 真值表 | `data\truth_pumpA_dev.csv`（设备侧 3 次开关时刻）、`data\truth_bus.csv`（总线段里这台泵的 2 次开关时刻） | 同左 |

> 文件列顺序都是标准的「时间, A相电压, A相电流, B相电压, B相电流, C相电压, C相电流」，所以下面所有「启用离线文件列映射」都**不勾**。列顺序不标准才勾，并填每列在第几列。

### I.2 第 0 步：把两侧"接线和变比"在界面上填对（两个例子的唯一区别就在这里）

打开网页 → 左侧「🔌 数据源与控制」。页面分左右两半：左＝总线侧，右＝分路侧。

**总线侧（左半）：**

| 项 | 例 1 三相三线 | 例 2 三相四线 |
|---|---|---|
| 启用 PT/CT | ✅ 勾 | ✅ 勾 |
| PT 变比 / CT 变比 | 100 / **40** | 100 / **15** |
| 接线方式 | **三相三线两表法（B 相无 CT）** | 三相四线（三 CT） |
| 3P3W 虚拟中性点重构 | ✅ 勾（软件把 B 相电流算出来：Ib = −(Ia+Ic)，后面画像的 ΔIb 才有数） | 不用管 |
| 电流极性反转 / 分相反转 | 先都不勾，**做完 I.3 第 ③ 条再决定** | 同左 |

**分路侧（右半）：** 启用 PT/CT ✅、PT 100 / CT 15、接线方式 三相四线、极性先都不勾。

填完分别点「**保存总线侧配置**」「**保存分路侧配置**」。

**怎么判断极性接反了（两个例子都要做）：** 到「⚡ 三相功率」页看实时卡片（或先用「数据源」页把 `bus_bg_*.csv` 播放起来）。
* 例 2（四线）：A、B、C 三相有功 P 应该**都是正数**。哪一相是负的，就在「分相电流极性反转」勾哪一相，保存。
* 例 1（三线两表法）：只有两块表，**两块表读数一正一负是允许的**（功率因数低于 0.5 时正常），不要看单相，**看总有功 ΣP 是不是正数、大小对不对**（22 kW 泵开着时总线 ΣP 应比关着时大 ≈22 kW）。如果开泵时 ΣP 反而**变小**，说明某相 CT 反了：勾 A 保存看一次，不对再换成勾 C。
* 分路侧同理：泵开着时分路 P ≈ +22 kW。

> 这一步做错，后面所有算法都会"看反"：开当关、关当开，或者台阶被抵消看不见。所以多花 5 分钟确认。

### I.3 第 1 步：用总线侧平稳段"量噪声"（前 6 种算法的容差参数）

左侧「🧮 数据处理」→ 往下找「**负荷辨识调参**」区。

1. 波形文件：下拉选 `bus_bg_3w.csv`（例 2 选 `bus_bg_4w.csv`）。这段里**不要有大设备开关**，1 分钟够了。
2. 起始 / 结束时间：留空（整个文件）。
3. 基准模式下拉：选「**沿用总线侧运行配置**」——这样 PT/CT、接线、极性全部自动跟 I.2 填的一样，不用再填。（它是只读的；想手改就选「独立基准配置」再点「填入总线侧值」。）
4. 检测量：留空（有电压 → 自动按有功 P）。检测对象：留空（P 口径默认三相总）。
5. **最小关心负荷 (W)**：填 **22000**（泵的额定有功，一次侧 W。只会用一个数的话就填这个）。
   * 不知道额定功率？勾「从文件投切台阶估计最小关心负荷」，但文件要换成**设备侧** `pumpA_dev.csv` 跑一次，看结果区「最小关心负荷估计」那行的候选值，点「填入输入框」，再把文件换回 `bus_bg_*.csv`、取消勾选重跑一次。（这就是事实 3 说的"台阶用设备侧量、噪声用总线侧量"。）
6. 点「**量噪声并给出参数**」。结果区看到两张表：噪声统计 + 6 种算法建议参数。只要第一行写着「口径 一次侧(PT/CT)」「检测量 P」就对。
7. 「套用目标」选「总线侧」，点「**套用到运行配置**」→ 6 种算法参数立刻热生效到总线侧（不改配置文件；更新后的完整配置副本写在 `output\nilm\`）。想永久保存：到「负荷辨识」页点「保存总线侧配置」。

**两个例子的区别：** 例 1 的三相三线因为 I.2 已经选对接线并勾了重构，这里**不用做任何额外操作**；软件按两表法算总有功。唯一注意：例 1 如果你想按"电流 I"而不是"有功 P"调参（比如电压没接），检测对象**不能选 B 相**（没有 CT），选 A 或 C。

等价命令（留档用，界面结果区会自动给一条一模一样的）：
```powershell
# 例 1
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg_3w.csv --config configs\runtime.json --min-load-w 22000 --wiring 3p3w --reconstruct-3w
# 例 2
.\.venv\Scripts\python.exe tools\nilm_tune.py --file data\bus_bg_4w.csv --config configs\runtime.json --min-load-w 22000
```

### I.4 第 2 步：用设备侧文件"提取设备画像"（第 7 种算法）

还是「🧮 数据处理」页，再往下「**设备画像提取**」区（v0.99.5 起它有**自己独立的一套**文件 / 时间 / 基准配置，和上面调参区互不影响）。

1. 波形文件：选 **设备侧** `pumpA_dev.csv`。
2. 基准模式：选「**沿用分路侧运行配置**」（PT 100 / CT 15、三相四线、分路侧极性都自动带过来）。
   * **两个例子这里完全一样**——画像永远在设备侧提，和总线是几线无关。
3. 检测量：留空（跟随分路侧配置，有电压就是 P）。检测对象：固定"三相总"，不用选。
4. 设备 ID：`pumpA`。
5. 启停标签：把真值表里 3 次开关抄进来，一行一个，例如
   ```
   2026-10-13 08:00:02,开
   2026-10-13 08:00:32,关
   2026-10-13 08:01:02,开
   2026-10-13 08:01:32,关
   2026-10-13 08:02:02,开
   2026-10-13 08:02:32,关
   ```
   没有真值表就留空，软件自动找（幅值为正当"开"、为负当"关"）。
6. 前窗 10、后窗 50 周波（默认）。泵启动冲击 0.3 s＝15 个周波，50 够。软启动 2 s 的设备要把后窗改成 ≥120。
7. 画像文件名留空，点「**提取设备画像**」。结果摘要卡片应显示「启动 / 停止样本 3 / 3」；表里 `ΔP (W)` 的 μ ≈ 22000。出现「⚠ 启动画像只有 1 次事件（建议每方向 ≥3 次启停）」或卡片上样本数标红就多录几次。
8. 点「**填入总线侧画像路径**」→ 软件自动把画像路径填进「负荷辨识」页总线侧的「设备画像匹配」面板并勾选它。

等价命令：
```powershell
.\.venv\Scripts\python.exe tools\nilm_profile.py --file data\pumpA_dev.csv --config configs\branch_runtime.json --device pumpA --labels data\truth_pumpA_dev.csv --out output\nilm\profile_pumpA.json
```

### I.5 第 3 步：在总线侧启用画像匹配，并处理"两侧接线不一样"

左侧「📈 负荷辨识」页（顶部选总线侧）→ 拉到「检测参数」→ 最后一个面板「**设备画像匹配**」：

| 参数 | 例 1 总线三相三线 | 例 2 总线三相四线 | 说明（不懂就按表填） |
|---|---|---|---|
| 勾选启用 | ✅ | ✅ | |
| 画像文件路径 | `output/nilm/profile_pumpA_….json`（I.4 已自动填） | 同左 | |
| 检测对象（固定） | 三相总（不可选） | 三相总 | 画像是"三相一起"的特征 |
| 检测量（固定） | 随画像文件 = P | P | 要和上方「检测量」实际口径一致（有电压就是 P，不用动） |
| D² 上限 / 最低置信度 | 9 / 0.3 默认 | 默认 | 总线上背景乱时放宽：D² 上限 16、置信度 0.2 |
| **相序映射 phase_map** | **0（自动）** | 1（ABC）先试；对不上再 0 | 设备的 A 相不一定接在总线的 A 相。例 1 两表法下相别更容易对不上，直接填 0 让软件 6 种都试、挑最像的 |
| 状态机 state_check | 1 | 1 | 防止连报两次"开" |

然后看面板下面那行"加载状态"：应显示「已加载：设备 pumpA（W 口径，启动样本 3 次 / 停止样本 3 次 …）」。
* 看到「**一次 / 二次侧口径不一致**」→ 回 I.2：总线侧和分路侧必须**都勾**「启用 PT/CT」（变比不同没关系，v0.99.6 起不再误报）。
* 看到「画像在 3p4w 接线下提取，本侧为 3p3w …」→ 这是**提示不是错误**（例 1 一定会看到一次）：告诉你 ΔIb 用的是重构值、相序可能对不上，已经靠 phase_map=0 处理。
* 看到「画像匹配数据体检：… 各相有功符号不一致」→ 回 I.2 调极性。

点「**保存总线侧配置**」。

### I.6 第 4 步：用总线侧"带开关的文件"验证（最关键的一步，两个例子一样）

1. 「🔌 数据源与控制」页总线侧：文件选 `bus_run_3w.csv`（例 2 `bus_run_4w.csv`），点「启动」播放。
2. 「📈 负荷辨识」页看事件表：
   * 前 6 种算法每种都会报出**所有**设备的开关（包括别的设备）——这是正常的，它们认不出设备。
   * `profile`（设备画像匹配）那一行**只应出现 2 条**：pumpA ↑ 和 pumpA ↓，时刻和 `truth_bus.csv` 对得上（差 1 秒以内），「检验量」列置信度 > 0.5。
   * 例 1 用了 phase_map=0 时，标记里可能出现 `phase_map_BCA` 之类——意思是软件发现设备 A 相接在总线 C 相上。记下来，下次直接把 phase_map 填成对应数字（ABC=1 ACB=2 BAC=3 BCA=4 CAB=5 CBA=6），比"自动"更稳。
3. 想用命令离线对账（可选）：
```powershell
# 回放总线文件（用当前总线侧配置，含刚套用的参数和画像）
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\bus_run_3w.csv --config configs\runtime.json --out output\replay_bus.csv
# 和真值表对账（结论表按算法一行一行列；只看 profile 那一行，其它 6 行把别的设备算成"误报"是正常的）
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\replay_bus.csv --truth data\truth_bus.csv --tol-s 1.0
```
`profile` 行 ✅ 就可以上线；⚠/✗ 看 I.7。

### I.7 对不上怎么办（按顺序只改一项，改完回 I.6）

| 现象 | 最可能原因 | 怎么改 |
|---|---|---|
| profile 一条都没有，状态行有「口径不一致」 | 一侧勾了 PT/CT 一侧没勾 | 两侧都勾，各填真实变比（I.2） |
| profile 一条都没有，候选都是 `rejected`，D² 很大，`ΔIa/ΔIb/ΔIc` 贡献最大 | 相序没对上（例 1 常见） | phase_map 改 0；或按 I.6 第 2 条记录的映射填数字 |
| profile 没有，候选 `rejected`，`ΔP` 贡献最大、总线 ΔP 是负的 | 总线某相 CT 反了 | I.2 调「分相电流极性反转」 |
| profile 有，但别的设备也被当成 pumpA | 别的设备功率和它太接近 | 画像多录几次让 σ 变小；D² 上限从 9 降到 6；分路侧再录 ΔQ 差别大的时段 |
| 前 6 种算法满屏事件（几秒一条） | 噪声参数是用设备侧文件量的 | 回 I.3，**用总线侧平稳段**重新量噪声并套用 |
| 前 6 种算法漏掉这台泵 | 最小关心负荷填大了 / 填成二次侧值 | I.3 填一次侧 W（22000 不是 22000/40） |
| 例 1 事件时刻对、但 ΔIb 一直是 0 | 没勾 3P3W 重构 | I.2 勾上重构并保存（不勾也能用，软件会自动跳过 ΔIb，只是少一维特征） |

### I.8 一页纸总结（贴在工位上）

```
总线三相三线（例 1）                          总线三相四线（例 2）
──────────────────────────────            ──────────────────────────────
I.2 数据源：总线 PT100/CT40，接线 3p3w，      I.2 数据源：总线 PT100/CT15，接线 3p4w；
    勾 3P3W 重构；看 ΣP 定极性                   看 A/B/C 三相 P 都为正定极性
    分路 PT100/CT15，3p4w                        分路同左
I.3 调参：总线平稳段 + 最小关心负荷 22000 W  I.3 同左
    基准「沿用总线侧」→ 套用到总线侧              基准「沿用总线侧」→ 套用到总线侧
I.4 画像：设备侧文件 + 真值标签，               I.4 同左（画像和总线几线无关）
    基准「沿用分路侧」→ 填入总线侧画像路径
I.5 负荷辨识：画像匹配 ✓，phase_map = 0       I.5 画像匹配 ✓，phase_map = 1（不行再 0）
    两侧都勾 PT/CT！                               两侧都勾 PT/CT！
I.6 播总线带开关文件：profile 行只有这台泵   I.6 同左
```

### H.16 v0.99.15：自适应参数的秒级漂移与画像多尺度候选

- **自适应（auto_params）为什么以前在总线上误报多**：σ 只量逐周波差分，看不见其它负荷造成的秒级漂移。现在额外量 min_steady 尺度块均值的 Allan 偏差 `sigma_block`，`min_delta` 与 ≥ min_steady 跨度的门槛都按 `max(sigma_block, σ/√min_steady)` 计算。界面自适应面板若显示「秒级漂移 ×n」，说明背景在漂、门槛已相应抬高；n≈1 为纯白噪声。该改动对纯白噪声数据的结果不变。
- **画像匹配为什么以前对慢停机没有事件**：候选门槛是画像幅值的一半，而单尺度双滑窗只看 1 s，慢斜坡达不到。`nilm.algorithms.profile.max_scale`（默认 8）让候选搜索在 ×1/2/4/8 的前后窗上各跑一遍并合并。代价：检测窗需求变为 `pre·S + dur + 2·post·S + 10`（S=max_scale），事件确认最多延后 post·S 周波（默认 50×8=400 周波=8 s）；若设备都是快速投切、追求低延迟可设 1。

### H.17 v0.99.17：性能参数 `eval_every_cycles` / `auto_stats_every_cycles`

- `nilm.eval_every_cycles`（默认 10）：每进 10 个新周波（0.2 s）评估一次全部算法；只影响事件上报延迟（≤0.2 s），不影响事件时刻与幅值。要恢复逐块评估设 1。
- `nilm.auto_stats_every_cycles`（默认 50）：自适应公共统计量每 1 s 重算一次；窗内统计本来就按几千周波的中位数计算，1 s 内不会有可感变化。
- 算法只在窗尾切片上运行，窗长 `window_cycles` 不再决定每次评估的算法耗时（只决定界面曲线与自适应统计用到的数据量），可以放心用 9000。

### H.18 v0.99.19：多尺度候选只找不量；总线 6 种算法的定位

- 画像匹配的特征窗口（pre/post）必须与画像提取时一致，多尺度（`max_scale`）只负责在慢斜坡上**找到**候选，不改变量特征的窗口。若画像是按 post=50 提取的慢停机（只量到快降段），总线侧也只按同样窗口量——两边一致才可比。想让画像反映全幅，请在提取时把 post 加大（如 400），运行时自动同口径。
- 总线上 6 种阈值类算法报的是**所有负荷**的台阶。其它设备投切幅值与目标设备同量级时，它们必然"误报"（其实是真实事件、只是不是你的设备）。设备归属请看 profile 事件；6 种算法可作总线事件日志或关闭。

### H.19 v0.99.20：复盘所需文件都在运行目录

`output/{yyyyMMdd_hhmmss}/`：`config_bus.json`、`config_branch.json`、`run_info.json`（含 `profile_file`）、`nilm/profile_{side}_*.json`（画像副本）、`nilm/nilm_events_{日期}.csv`（已接受事件）、`nilm/nilm_profile_candidates_{日期}.csv`（画像匹配全部候选，含被拒原因 flags 与各维 D² 贡献——"为什么没报"看这里）。把整个目录发来即可复盘。

### H.20 v0.99.22：画像匹配「一次都没跑」的隐蔽原因——PT/CT 启用标志不一致

第 164 轮实录（海湾化工 bus-停止 / dev1）：总线侧配置 PT=4、CT=250 **启用**，设备侧文件本身已是一次侧值（239 V / 37 A），画像提取时 PT/CT **关闭**。两侧 ΔI 完全可比（总线 −36/−38/−39 A，画像 −36/−32/−42 A），但 v0.99.6 的口径检查按**标志位**硬拒绝 ⇒ 画像匹配一次都没运行、`nilm_profile_candidates_*.csv` 根本不生成，界面只在负荷辨识页提示列表里有一条「口径不一致」。v0.99.22 起改为**只提示、照常匹配**；用真实 1 s RMS 序列驱动引擎复验：14:38:17 停机 `confirmed`，置信度 0.83，D²/维 0.37；另两个候选（其它负荷 +9 A / +19 A）`rejected` D²/维 >130。

排查口诀：画像启用却**连候选 CSV 都没有** ⇒ 先看负荷辨识页「提示 / 错误」列表（口径、quantity、画像加载失败三类会直接让匹配不运行），再谈参数。

顺带：两侧文件时间戳**不同步**（总线侧停机 14:38:16，设备侧 14:39:30，差约 74 s）——比对两侧事件时请按波形对齐而不是按时间戳。

### H.21 v0.99.23：候选 ΔI/ΔP 都对却被拒——看 `c_dur_cycles` 与 `c_d_q`

第 165 轮实录（候选 CSV 终于有了）：总线侧 14:38:16 候选 ΔIa/b/c −35/−40/−36 A、ΔP +27.5 kW 与画像完全一致（贡献 0.03/2.6/0.9/1.0），但 `c_dur_cycles=221`、`c_d_q=110` ⇒ D²/维 48 ⇒ `d2_exceeds`。原因是过渡终点规则「最后一次越出 ±20 %·|Δ| 带」在总线侧太脆：35 A 停机的带只有 7 A，60 s 后窗里其它负荷随便一次 ±7 A 抖动就把终点推到几十秒后（dur 2161 vs 画像 256），后窗整体后移后 ΔQ 也量到别的东西。

v0.99.23 起终点＝滑动中值平滑后**首次进带并保持 ≈post/10 周波**（三处共用：在线候选、标签定位、自动定位），设备侧与总线侧按同一规则量 dur（实录重算：设备侧 422、总线侧 343 周波）。**旧画像需重提一次**（dur 定义变了）。

排查口诀：候选 CSV 里 `c_*` 列就是每维 D² 贡献，哪一维大就查哪一维；`c_dur_cycles` 独大 ⇒ 终点规则 / 画像 dur 定义问题，不是设备不匹配。

### H.22 v0.99.23：PT/CT 不再有「启用」开关

界面只剩 PT、CT 两个输入（出厂 1/1）。要看一次侧就填真实变比，不需要换算就填 1。旧配置 / 旧画像里 `enabled=false` 会被自动折算为 PT=CT=1，数值结果不变。画像匹配两侧变比不同（总线 CT=250、分路 CT=1）属正常，只提示不影响。

### H.23 v0.99.24：启动「夹」在两次他负荷之间——为什么没有候选、现在怎么处理

**给运维 / 现场的说法**：总线上 1 分钟内先后发生了三件事（别的负荷 +60 A、你的设备 +35 A 慢慢爬上来、别的负荷 −70 A）。老版本用 60 s 的「前后对比窗」看，这三件事糊成一团，只认出最大的那一下（+60 A，不是你的设备）。新版本会先用 15 s / 30 s 的短窗把三件事拆开，再给你的设备单独量前后差值，量的时候**前后窗一碰到别的事件就截断**，不会把 −70 A 算到设备头上。

**例 1（总线 3p3w，CT 250，画像 pre/post=3000）**：候选 CSV 里 15:00:08 一行 `scales_hit=0.25/0.5`（只有细尺度命中）、`status=confirmed`、`c_*` 全部 <1.1；14:59:08 一行 `d_ia=65` `status=rejected` `c_d_ia=25.9`——那是他负荷。没有细尺度时（`min_scale=1`）15:00:08 这行根本不会出现。

**例 2（分路 3p4w，CT=1，pre/post=10/50）**：窗本来就短（0.2 s / 1 s），细尺度最小到 5 周波，对快速启停设备无影响；若分路上只有这一台设备，`min_scale=1` 与 0.25 结果一致。

**代价**：灵敏度提高后，与设备幅值差 20 % 以内、功率因数又相近的他负荷可能被判成本设备（实录 14:55:33 −28 A 两级下跌被判 STOP 0.46）。这不是算法 bug 而是画像只有 1 个样本：σ 只能取 15 % 相对下限。对策按优先级：① 多录几次启停，**≥3 个样本**后 σ 会收到实际重复性（通常 2～5 %）；② 把 `min_confidence` 提到 0.5（本次真启动 0.79、真停机 0.75，误判 0.46）；③ 分路侧有装置就以分路侧结果为准。

### H.24 v0.99.25：候选有、特征却反号——前后窗跨过了相邻他负荷

**现象**：候选 CSV 里设备启动那一刻有行、`scales_hit` 也有细尺度，但 `d_ia/d_ib/d_ic` 是**负**的、`d_p` 是**正**的，`status=rejected` 且 `flags` 带 `d2_exceeds,trajectory_deviates`；同一侧的 `nilm_events` 里因此没有任何 `profile confirmed`。第 168 轮实录（总线 3p3w，CT 250，画像 pre/post=3000，15:00:08 一行：ΔIa/b/c −39.2/−38.8/−30.5 A、ΔP +33.5 kW、ΔQ −15.2 kvar、dur 1356）。

**怎么一眼看出是「窗取错」而不是「设备不匹配」**：把这一行的 `d_*` 与**相邻两次他负荷**的 `d_*` 对一下——
`d_p +33.5 kW ≈ +57.9 kW（15:00:39 他负荷切除）− 25.6 kW（设备本身）`，
`d_q −15.2 kvar ≈ −16.0（那次切除）+ 0.9（设备）`，
`d_ia −39 A ≈ +62（14:59:08 他负荷投入）+35（设备）−71（那次切除）−62`。
三项都能对上 ⇒ 前窗取到了 14:59:08 之后的电平、后窗取到了 15:00:39 之后的电平，候选自身没被量到。

**例 1（总线 3p3w，PT 4 / CT 250）**：14:59:08 他负荷 +60 A → 15:00:05 设备 +35 A/18 s 斜坡 → 15:00:39 他负荷 −70 A。v0.99.25 起，后窗前界（`post_hi`）由 onset 之后的第一个「非自身」变点决定，−70 A 台阶不再被当成自身过渡；候选按画像几何重算终点后 `dur≈580`、ΔIa 34 A ⇒ `START confirmed 0.789`。若现场仍看到 `sign_flip`，说明前后还有一次动作贴着事件终点（`window_crowded` 同时出现），把设备单独跑一次或用分路侧数据复核。

**例 2（分路 3p4w，CT=1）**：同一份画像在分路侧本来就是 `START confirmed 0.776`（15:01:22，ΔIa 34.4/29.3/40.5 A、ΔP −23.1 kW、dur 175）。两侧结果不一致时，先用这条差异确认「总线侧窗被邻居污染」，而不是去改画像或阈值。

**新增诊断标志**：`sign_flip`（量出的 Δ 与搜索 Δ 反号 ⇒ 前后窗错了，事件直接拒）、`window_crowded`（下一个他负荷紧贴终点，后窗只能取 `post/20` 周波，仍照常按 D²/置信度判）。

### H.25 v0.99.26：为什么"同功率的线性负荷"骗得过旧画像——谐波维 `d_ih` 怎么用

**现象**：一台设备（整流 / 变频）停机和运行时，基波电流只差 25~35 A，但**谐波电流差 15 A**（停机 16~18 A、运行 31~34 A）。旧 7 维画像里没有这一维，于是一台"功率、电流都差不多、但不带谐波"的电机 / 电阻负荷会落进同一个特征点：第 171 轮构造的完全线性仿冒负荷在 7 维下 D²=0、置信度 1.0（必然误报）。

**现在怎么判**：`d_ih` = 事件后窗 2~13 次谐波电流合量的中位数 − 前窗中位数（A，三相平均）。设备启动 ⇒ 约等于设备自身的谐波贡献（本案例 +14~15 A）；线性负荷投入 ⇒ ≈0（实测两段录波的 45 kW 负荷：−2.37 / −2.35 / +1.19 A）。

**读候选诊断 CSV**：`nilm_profile_candidates_<日期>.csv` 里 `d_ih` 是量到的值、`c_d_ih` 是它对 D² 的贡献。判读顺序：
1. `c_d_ih` 占 D² 的绝大部分 ⇒ 幅值都对、只是"不像这台设备的谐波特性" ⇒ 不是本设备（或本设备当前不是满载 / 不是同一工况）；
2. `d_ih` ≈ 设备画像的 μ ⇒ 谐波特性吻合；
3. 其它维度都小、只有 `c_d_q` 大 ⇒ 先查那次动作前后有没有电容组投切（第 172 轮）。**v0.99.27 起**无功序列也参与找变点，前后窗会被投切截断（`window_crowded` 标记）；若这一维仍然大，说明真的在那次动作里伴随了无功变化（电机励磁涌流、SVG 动作、电容器与设备同时投切），不是窗口取错。

**注意**：`d_ih` 是 8 维之一，进的是同一个平均 D²，所以它的权重是 1/8；单样本画像的 σ 只能取下限（15 % / 2 A），若设备谐波贡献逐次波动 ±20 %，这条证据会变弱——**每个方向至少 3 个启停样本**再重提画像。

**多画像**：同一侧要同时盯多台设备时，把各自的画像路径用 `;` 拼在「画像文件路径」里即可（例如 `output/nilm/profile_泵A.json;output/nilm/profile_压缩机B.json`）。状态行会逐个显示设备、样本数、当前状态与最近候选；`device_id` 重复会在状态行标红。

**最容易踩的坑（v0.99.26.1 已修一半，另一半靠你确认）**：画像里存的是**换算后**的 ΔI / ΔP。如果设备侧文件是**二次侧原始值**，而提取时填了 PT=100 / CT=15，画像的 ΔI 就是原始值的 15 倍；总线侧若按 PT=CT=1 跑，两边差 15 倍 ⇒ **永远匹配不上**，界面上只会看到"候选 0 条"。两个动作：
1. 提取画像时**务必让 PT/CT 与总线侧运行配置一致**——命令行加 `--config configs/runtime.json`（或在界面「设备画像提取」里选「运行配置」基准）；
2. 看 `summary.errors` 里有没有"本侧 ΔI 是画像的 X 倍"的提示——这句会直接告诉你差多少倍。
（v0.99.26.1 已把命令行的**缺省配置**改成与界面一致，并把提示改成给倍数；此前命令行缺省会悄悄用代码级默认值 PT=100 / CT=15。）

### H.26 v0.99.27：电容组投切把候选的 ΔQ 带偏了——无功序列也来当变点

**现象（第 172 轮实录）**：设备启动那一刻ΔI/ΔP 都对，但候选的 `d_q` 是 **−25.8 kvar**，画像里只有 **+902 var**，`c_d_q` 独占 D²。去查那段波形：设备启动前后 1 秒内电容组投切了（+37 kvar / −19 kvar 那种台阶），而 `quantity='i'` 的候选搜索只在**三相合成电流**这一条序列上找变点——纯无功阶跃在电流上只动几安，够不到门槛，于是它既不是候选、也**不是变点**，候选的后窗一路盖到它身上，把 ΔQ 整个量错。

**现在怎么处理**：
1. **变点**：`q4[0]` 上的变点与 i/p 上的变点一起参与截断前后窗。两条序列单位不同（A/W vs var），所以**只按时间截断**，不参与"同号 / 幅值不超过 1.5 倍"那套幅值比较。截断后若后窗短于 `max(10, post/20)` 周波，候选会带 `window_crowded` 标记——**这是正常现象**（说明旁边确实有别的动作），特征仍按截断后的干净段量。
2. **候选**：画像本身有可观无功份额（\|ΔQ\|/√(ΔP²+ΔQ²) ≥ 10 %）时，Q 序列单独找候选，候选诊断 CSV 的 `source` 列为 `q`。纯电阻设备（ΔQ≈0）不会有这类候选——否则任何投切都会越过它 \|ΔQ\|/2 的门槛被当成它的启停。

**怎么判读**：候选 CSV 的 `source` 列。
- `x`：检测量序列上的候选（正常路径）；
- `q`：无功序列上的候选。若你的设备本来就是无功型（电容器、SVG、空压机卸载），这类候选才是它的本体；若画像 ΔQ 很小而 `source=q` 的候选很多，说明闸门没挡住——检查画像的 ΔQ 是不是被单次样本的偶然值带偏了（**每方向 ≥3 个样本**）。

**实录效果**（bus-2 977 s + 8 维画像）：t=1621917638 的候选 ΔQ **−25 809 → −16 var**、D²/维 **1757.31 → 14.68**；候选数不变（3→3），说明只修了特征、没有引入误报。

**仍然不是银弹**：这条路只解决"别的无功动作污染窗口"。设备自身的无功怎么变、CT 极性/相别是否配对（第 171 轮：ΔP 与 ΔI 异号）仍然要靠重提画像前先核对 PT/CT 与接线。

### H.27 v0.99.28/v0.99.29：变频 / 多档位设备——一份画像只认一档，两种补法

**现象**：设备有 30 % / 50 % / 70 % / 100 % 几档，提画像时只录到了 100 % 那一档。总线侧只认 0.72~1.28×（`lambda_rel=0.02`，旧值 0.1 时 0.70~1.30×），**低于候选门槛（默认 0.5×画像幅值）的台阶连候选都不生成**——界面上"什么都没有"，最容易误判成"设备没启动"。把不同档位的启停混进**同一份**画像更糟：μ 会落在两档之间、σ 涨到 40~60 %，同幅值的线性负荷也能混进来（实测 conf 0.41~0.64 被判确认）。

**补法一（推荐先试）：档位自由匹配**（`nilm.algorithms.profile.stage_free = 1`）

1. 判定的不再是"幅值像不像"，而是**形状**像不像：每次先解出"这一档是画像档位的多少倍"（`s`），再算形状残差；
2. 事件表 / CSV 里多了 `stage_scale`（解出的倍数，`1.0`＝就是画像那一档）与 `event_kind`（`start/stop/stage_up/stage_down`）。
   **类型按"运行档位账本"判**（`level`＝当前在第几档，0＝停机）：停机起步＝`start`（哪怕只到 0.2 档）、运行中再加一档＝`stage_up`、
   降档后还剩档位＝`stage_down`（设备还在低速运行，状态保持 on）、降到 0＝`stop`。所以"1.0 档运行 → 降到 0.4 档 → 停机"是
   `start / stage_down / stop`，**不是**看成方向就写 `start / stop / stage_down`（那是 v0.99.29 首版的漏洞：把还在运行的降档报成停机，
   把真停机报成降档，状态机再也翻不回来）。现场对账就看事件表这三列（`stage_scale` + `event_kind`）与负荷辨识页画像状态行的 `level`：
   停机后 `level` 应为 0；如果一条停机事件后 `level` 还挂着 0.4，说明中途漏了一次降档（`min_gap` 压制或被拒），先查候选 CSV；
3. 三个配套参数：`min_stage`（候选门槛÷画像幅值，建议 **0.2~0.3**，否则 50 % 以下的档位照样静默）、`stage_min_scale`/`stage_max_scale`（s 的取值范围，默认 0.2~3.0）、`stage_dim_max`（**单维否决**，默认 9＝任一维偏差 3σ 就拒；**别关**——自由档位会把平均 D² 系统性压低，实测"谐波只有 40 %"的假负荷平均 conf 0.407 会被收，靠这条拦下）；
4. 建议同时把 `min_confidence` 从 0.3 提到 **0.35~0.4**（真实事件实测 0.75 以上，余量很大）；
5. 代价：每块多约 60 % 的计算量（10 281 周波段 7.5 → 12.1 ms）。

**补法二（不改判定语义）：派生档位画像**——数据处理页「设备画像提取 → ④ 派生档位画像」填倍数（如 `0.4,0.7`）→ 点「派生档位画像」→ 结果表看每档的**可接受区间 / 候选门槛**→「复制派生路径串」→ 到负荷辨识页「画像文件路径」粘贴。派生件是**按倍数外推的假设画像**（`device_id` 带 `@40%`），只外推幅度维，峰值比与持续周波保持；ΔQ 恒定（电机励磁无功）时选 `const`，轻载 THD 升高时把 `ih_exp` 调到 0.7~0.9。间距建议 ≥1.3~1.8 倍（太密同一事件会被两份画像重复报出）。

**判读**：候选 CSV 里 `status=rejected` 且 `flags` 有 `d2_exceeds`、`confidence` 0.1~0.3 ⇒ 多半是**另一档**；`flags` 有 `sign_flip`、`c_d_q` 很大 ⇒ 是**别的设备**；`flags` 有 `dim_exceeds`（档位自由时）⇒ 单维超 3σ，看 `c_*` 里是哪一维。

**不要做**：① 把多档事件混进同一份画像；② 为了覆盖档位去调大 `d2_max` 或 σ 下限；③ 把 `min_stage` 砍到 0.05 却不开形状闸门——候选会暴增、他负荷全进。

### H.28 v0.99.29：多档位设备怎么**用派生网格验证测试**——三相四线 / 三相三线两个例子

> **给谁看**：现场实施、运维、交付——不需要懂算法，照着敲命令、对着表看结果就行。
> **解决什么问题**：变频泵、多档风机、有 30 %/50 %/70 %/100 % 几档的设备，提画像时**只录到了其中一档**。这时总线侧只认这一档的 ±30 % 左右，其它档位要么报不出来、要么低到连候选都不生成。
> **这一节讲什么**：怎么用「派生档位画像」把这一档**复制成一组**（叫**派生网格**），再用**带已知档位的总线数据**回放，**证明**每个档位都恰好被一份画像认出来、且别的设备没被认错。文末有验收清单和一页纸。
> **两个例子**：例 1＝**三相四线**（3p4w，PT=CT=1，有功口径，500 W 设备）；例 2＝**三相三线**（3p3w＋虚拟中性点重构，PT=4、CT=250，电流口径，25 kW 电机）。全部数字是 v0.99.29 在仓库里实跑出来的，可以照着复现。

---

#### H.28.0 先用三句话把事说清

1. **一份画像 = 一个档位**。画像里记的是"这台设备开一次，电流涨多少、功率涨多少、谐波涨多少"。录的是 100 % 档，它就只认 100 % 档（实测只认 **0.67~1.33 倍**；低于 **0.50 倍**的台阶连候选都不生成，界面上"什么都没有"）。
2. **派生网格 = 把这一份画像按倍数复制成好几份**，例如 0.50× / 1.00× / 1.99×，每份覆盖一段档位，**首尾相接、不漏也不重叠**。挂上去以后，70 % 档由 0.50× 那份认、100 % 档由 1.00× 那份认，事件表里会写清楚是**哪一份**认的（`device_id` 带 `@50%` 后缀）。
3. **验证测试 = 拿一段"你明明知道设备在哪个档位开、哪个档位关"的总线数据回放**，看三件事：① 每个已知档位**恰有一份**画像命中；② 相邻档位**不会**被别的份认走；③ 同段里**别的设备**的启停**一条都不认**。三件事都成立才算通过。

> ⚠ **派生是"假设"不是"实测"**：网格里的每一份都是把已录档位的 μ/σ 按倍数外推出来的。它能把"看不见的档位"变成"看得见的候选"，但**判别力比真实画像弱**（尤其低档位、谐波维）。所以**必须**用真数据验证过才上线，验证方法就是本节。

**什么时候该用网格**（满足任意一条）：
* 设备铭牌/工艺上确实有多个档位，且现场会用到；
* 只录到了其中一档（常见：录波时设备刚好满负荷跑）；
* 已经出现过"明明开了、软件没报"（低档位静默）；或"报了但不是这台"（幅值相近的他设备，见 H.25/H.27）。

**什么时候不要用**：只用一档运行 → 单份画像就够，多挂几份只会增加重复报的风险；设备是"无级变频"（连续调功）→ 用 `stage_free=1` 档位自由匹配（H.27 补法一），**不要**再叠网格。

---

#### H.28.1 验证分四个层次（从便宜到贵，按顺序做）

| 层次 | 做什么 | 花多久 | 判据 |
|---|---|---|---|
| ① 画像自检 | 看 CLI/界面打印的「可接受区间」与「候选门槛 min_d」 | 秒级 | 区间是不是 0.6~1.4 倍量级；min_d 是不是明显低于最低档 |
| ② 派生网格自检 | 看派生结果表的每份「可接受区间（绝对值）」 | 秒级 | 相邻两份**首尾相接**（下一份下界 ≤ 上一份上界），覆盖到最低档 |
| ③ 回放验证 | 用带已知档位的总线数据回放，看**判定矩阵** | 分钟级 | 每个台阶**恰一份** ✔，其余 ✘ |
| ④ 对账 | `nilm_check.py` 与真值表逐条比 | 秒级 | `profile` 行：命中 100 %、漏报 0、误报 0 |

本节两个例子会把 ②③④ 全部走一遍。

---

#### H.28.2 例 1：三相四线（3p4w，PT=1、CT=1，有功口径，500 W 设备）

**现场情况**：一台 500 W 的小设备（有点像风机/水泵），实际会跑 **100 % / 55 % / 35 %** 三档；录波时只录到了 **100 %** 那一档。同一段总线上还有另一台设备（约 1500 W 的普通负荷，开关时会切掉 1500 W）。

##### 第 0 步：准备两份数据 + 一张真值表

| 文件 | 内容 | 本例用到的 |
|---|---|---|
| `dev_3p4w.csv` | **设备支路**录波，含 2 次开、2 次关（都在 100 % 档） | 提画像用 |
| `bus_3p4w.csv` | **总线**录波，含该设备 3 次启停（100 %/55 %/35 % 各一次）+ 21 s 处别的设备切负荷 | 验证用 |
| `truth.csv` | 上面那段的真实开关表 | 对账用 |

`truth.csv` 写法（Excel 三列，另存 CSV UTF-8；**别的设备的动作写「其它」**，这样它被认出来才算误报、没认出来不算）：

```csv
时间,动作,备注
2026-10-31 09:00:03,开,pumpA 100%
2026-10-31 09:00:06,关,pumpA 100%
2026-10-31 09:00:09,开,pumpA 55%
2026-10-31 09:00:12,关,pumpA 55%
2026-10-31 09:00:15,开,pumpA 35%
2026-10-31 09:00:18,关,pumpA 35%
2026-10-31 09:00:21,其它,别的设备切负荷
2026-10-31 09:00:24,其它,别的设备恢复
```

##### 第 1 步：提画像（只要录到的那一档，**别混档**）

```powershell
python tools/nilm_profile.py --file data\dev_3p4w.csv --device pumpA `
    --labels "09:00:02,开;09:00:05,关;09:00:08,开;09:00:11,关" `
    --config configs\default.json --pre 10 --post 50 --out output\pumpA.json
```

界面上等价操作：**数据处理 → 设备画像提取 → ③ 事件前后窗填 10 / 50 → 填启停标签 → 提取设备画像**。

本例实跑结果（P 口径）：

| 特征 | ΔIa / ΔIb / ΔIc | ΔP | ΔQ | 峰值比 | 持续周波 | ΔIh |
|---|---|---|---|---|---|---|
| μ（均值） | 3.240 / 3.239 / 3.240 A | **500.0 W** | 242.2 var | 1.00 | 1 | 0.641 A |
| σ（标准差） | 0.486 A | 75.0 W | 60.5 var | 0.30 | 5 | 2.0 A |

画像打印的关键三行（**这就是"这份画像认几档"**）：

```
可接受区间 0.67~1.33×，候选门槛 250.003 W（低于 0.5× 的档位连候选都不会生成）
```

> 记下这两个数：**0.67~1.33×**（判定窗口）和 **250 W**（候选门槛＝画像幅值的 0.5 倍）。
> 本例最低档 35 % = 175 W **小于 250 W** ⇒ 单份画像时它**连候选都不会生成**，后面第 3 步会看到。

⚠ 本例每个方向只有 2 次启停，CLI 会提示"建议每方向 ≥3 次"——**这是提示不是错误**，可以继续，但 σ 会取下限、判别力偏弱；现场尽量补到 3 次以上。

##### 第 2 步：派生网格（界面 ④ 或 CLI，二选一）

**界面（推荐现场用）**：数据处理 → 设备画像提取 → 表单第 **④ 组「派生档位画像」**
1. 「**档位倍数（相对本次画像）**」填 `0.504,1,1.985`（就是下面 CLI 算出的那三个倍数；不想算就填 `0.5,1,2`，效果几乎一样）；
2. 「输出目录」留空＝与画像同目录；
3. 「ΔQ 缩放」保持 `scale`（电机类励磁无功基本不变时改 `const`，见 H.28.5）；「谐波指数 ih_exp」保持 1（轻载 THD 明显升高时改 0.7~0.9）；
4. 点 **「派生档位画像」**；
5. 结果表逐份显示 **档位倍数 / 档位 % / 设备 ID / 可接受区间 / 候选门槛 min_d / 静默区 / 文件名**；
6. 点 **「复制派生路径串」**——得到一串用 `;` 分隔的完整路径，下一步直接粘贴。

> **界面只认"你填的倍数"，不会自己算网格**。要"等间距自动铺开"就用下面的 CLI `--derive-grid`（它按**每份自己实测的窗口**接力摆，间距不是常数）；界面适合"档位数值已知"的场合（直接填 0.35,0.55,0.75,1.0）。两种方式产出的文件完全相同，混用没有关系。

**CLI（等价，可留档复现）**：

```powershell
python tools/nilm_profile.py --derive-from output\pumpA.json --derive-grid 3 `
    --stage-out-dir output\pumpA_grid --config configs\default.json
```

本例实跑输出：

```
基准画像：output\pumpA.json（设备 pumpA，未重新提取）
档位派生（v0.99.28）：基准画像录到的是 **1 档**，可接受区间 0.67~1.33×，候选门槛 250.003 W
  · pumpA@50%   k=0.5038  可接受 0.63~1.37×  min_d=125.941 W  → output\pumpA_grid\pumpA_stage0.504.json
  · pumpA       k=1       可接受 0.67~1.33×  min_d=250.003 W  → output\pumpA.json（＝基准画像，未复制）
  · pumpA@199%  k=1.985   可接受 0.67~1.33×  min_d=496.274 W  → output\pumpA_grid\pumpA_stage1.99.json

  把下面这串填到总线侧 nilm.profile_path：
    output\pumpA.json;output\pumpA_grid\pumpA_stage0.504.json;output\pumpA_grid\pumpA_stage1.99.json
```

**这一步要自己核对的两件事（② 层）**：

| 检查 | 本例 | 怎么判 |
|---|---|---|
| 相邻两份**首尾相接** | 0.50× 覆盖 159~345 W，1.00× 覆盖 335~665 W，1.99× 覆盖 665~1320 W | 375（上一份上界×基准）≈ 335（下一份下界）——重叠一点点是正常的，**留大缝**就是漏档 |
| 覆盖到**最低档** | 最低档 35 % = 175 W，落在 0.50× 那份（159~345 W）里 ✔ | 最低档幅值 **≥** 最下面那份的下界 |

> **换算方法**：表里的"绝对覆盖"＝`k × 该份自己的可接受区间 × 画像幅值`。不用手算——界面/CLI 打印的"可接受区间"逐份都有。

##### 第 3 步：挂上网格回放，出判定矩阵（③ 层）

用 `nilm_replay.py` 离线回放（不启动 Web，直接出事件 CSV，并且**把每份画像的每次判定都打印出来**）：

```powershell
$P = "output\pumpA.json;output\pumpA_grid\pumpA_stage0.504.json;output\pumpA_grid\pumpA_stage1.99.json"
python tools/nilm_replay.py --file data\bus_3p4w.csv --config configs\default.json `
    --set profile.enabled=1 --set "nilm.profile_path=$P" --out output\events_pumpA.csv
```

（Web 里等价：数据源页挂上这串路径 + 勾「设备画像匹配」→ 播放 → 看负荷辨识事件表。）

**先看对照：只挂基准画像（单份）**，你会看到恰好在**最低档**那个位置什么都没有：

| 台阶 | 真实档位 | 只有基准画像 |
|---|---|---|
| 09:00:03 / 06 | 100 % | ✔ 0.99 |
| 09:00:09 / 12 | 55 % | ✘ 0.10 / 0.05 |
| 09:00:15 / 18 | 35 % | **（连候选都没有：175 W < 250 W 门槛）** |
| 09:00:21 / 24 | 别的设备 | ✘ 0.00 |

**再挂 3 份网格**（`min_stage` 保持默认 0.5）：

| 台阶 | 真实档位 | @50% | @100% | @199% | 结论 |
|---|---|---|---|---|---|
| 09:00:03 开 | 100 % | ✘ 0.00 | **✔ 0.99** | ✘ 0.06 | 恰一份命中 |
| 09:00:06 关 | 100 % | ✘ 0.00 | **✔ 0.99** | ✘ 0.06 | 恰一份命中 |
| 09:00:09 开 | 55 % | **✔ 0.96** | ✘ 0.10 | — | 恰一份命中 |
| 09:00:12 关 | 55 % | **✔ 0.96** | ✘ 0.05 | — | 恰一份命中 |
| 09:00:15 开 | 35 % | **✔ 0.41** | — | — | 恰一份命中（**置信度天然偏低**，见下方 ⚠） |
| 09:00:18 关 | 35 % | **✔ 0.41** | — | — | 恰一份命中 |
| 09:00:21 切负荷 | 别的设备 | ✘ 0.00 | ✘ 0.00 | ✘ 0.00 | 全拒 ✔ |
| 09:00:24 恢复 | 别的设备 | ✘ 0.00 | ✘ 0.00 | ✘ 0.00 | 全拒 ✔ |

**怎么读这张表**：

| 符号 | 含义 | 出现位置说明 |
|---|---|---|
| **✔ n.nn** | 该份画像**认了**（confirmed），数字是置信度 | 每个已知台阶**应该只有一个** ✔ |
| **✘ n.nn** | 该份画像**看了但拒了**（rejected） | 正常；说明这一档不归它 |
| **△ n.nn** | 认了但带标志（低置信 / 窗被挤 / 低频…） | 需看候选 CSV 的 `flags`；`low_confidence` ≠ 置信度低 |
| **—** | 该份**连候选都没生成**（幅值低于它的 `min_d`） | 也正常；网格"份数不够"就表现为低档**整行都是 —** |

> ⚠ **低档位置信度天然更低**：35 % 档只有 0.41，不是匹配失败。原因是幅值小，几项**绝对下限**（谐波 2 A、无功 30 var）占比变大，容差相对变松。**不要**为了让低档更好看而把 `min_confidence` 改成 0.2（下面"不要做"会给实测后果）。

##### 第 4 步：对账（④ 层，一条命令给结论）

```powershell
python tools/nilm_check.py --events output\events_pumpA.csv --truth data\truth.csv --tol-s 1.5
```

本例实跑（3 份网格）：

```
  算法               真值   命中   漏报   误报   其它设备     命中率  结论
  ...
  profile           6    6    0    0      0    100%  ✅ 可上线   (设备画像匹配)
```

`profile` 这一行就是结论：**命中 6 / 漏报 0 / 误报 0 ⇒ 通过**。

> 若同段还开着另外 6 种算法，它们也会各占一行——那些是另一套参数的事（见 §3、附录 H.1~H.13），本节只看 `profile` 行。

##### 第 5 步：故意做错一次，确认这套方法"看得见错"

这一步不是走过场——**验证方法本身要靠它证明有效**。用同样的数据，把网格从 3 份改成 **5 份**（往上铺到 3.94×）：

```powershell
python tools/nilm_profile.py --derive-from output\pumpA.json --derive-grid 5 --stage-out-dir output\pumpA_grid5
```

5 份的覆盖是 0.25× / 0.50× / 1.00× / 1.99× / **3.94×**，最上面那份的候选门槛是 **985 W**、判定窗口是 **1340~2601 W**。于是 21 s 那台**别的设备切了 1500 W** 正好落进它的窗口：

| | 结果 |
|---|---|
| 事件表（误报） | 多出 2 条：09:00:21 `STOP` 0.6824、09:00:24 `START` 0.6824，都记在 `pumpA@394%` 名下 |
| 事件表（重复） | **还多 2 条**：35 % 档被 `pumpA@25%`（0.4568）与 `pumpA@50%`（0.4075）**同时**确认 ⇒ 一共 **10 条 confirmed**（应为 6），违反"每个台阶恰一份" |
| `nilm_check` | `profile` 行：命中 6、漏报 0、**2 条带内误报** ⇒ ⚠（重复的 2 条并入同一次启停，不计入误报，但事件表里看得到） |
| 结论 | **网格铺太宽** ⇒ ① 收到"看起来像 3.9 档"的大负荷；② 低档两份窗口重叠、一条启停被报两次。修法：把份数降回 3（覆盖 0.50~1.99×），或把上限卡在设备铭牌最高档；重叠严重时用精确派生（`--derive-stages`） |

> 这就是"验证测试"的价值：**不是证明它一定对，而是能证明它哪里不对**。5 份那次如果没有第 4 步对账，你会以为一切正常。

---

#### H.28.3 例 2：三相三线（3p3w＋重构，PT=4、CT=250，电流口径，25 kW 电机）

**现场情况**：同一台 25 kW 电机接在**三相三线**（两表法）进线上，进线 PT=4、CT=250，数据源**没有电压**或电压不可信 ⇒ 用**电流口径（I）**。电机实际跑 **100 % / 55 % / 35 %** 三档，录波只录到 **100 %**。总线上另有一台大负荷（21 s 切掉 60 kW，24 s 恢复）。

> **为什么单独讲这个例子**：三相三线的 B 相电流要靠**虚拟中性点重构**算出来（`ib = −(ia + ic)`），少勾一个勾选框，ΔIb 那一维就整个失效；PT/CT 又都是非 1，**两侧口径必须完全一致**，否则永远匹配不上（H.20、H.22）。

##### 第 0 步：把三件事填对（**这是本例唯一比例 1 多的地方**）

| 项 | 填什么 | 填错会怎样 |
|---|---|---|
| 接线方式 | **3p3w（三相三线）** | 当 3p4w 算 ⇒ 电压/功率全错（实测 Uab 会得 604 V、P 会大 3 倍） |
| 3P3W 虚拟中性点重构 | **勾选** | 不勾 ⇒ ΔIb 直接跳过（引擎提示"画像在 3p4w 提取、本侧 3p3w，跳过 ΔIb"），剩 7 维也能跑但判别力下降 |
| PT / CT | **4 / 250**（设备侧、总线侧**都要一样**） | 一侧填、一侧不填 ⇒ ΔI 差 250 倍，永远匹配不上（H.20） |

设备侧文件在界面上用「**启用离线文件列映射**」也行：3p3w 的两表法数据，A/C 列放的是**线电压 Uab/Ucb**，B 列电流为 0。

##### 第 1 步：提画像（I 口径）

```powershell
python tools/nilm_profile.py --file data\dev_3p3w_ct250.csv --device motorC `
    --labels "09:00:02,开;09:00:05,关;09:00:08,开;09:00:11,关" `
    --config configs\site_3p3w.json --quantity i --wiring 3p3w --reconstruct-3w `
    --pre 10 --post 50 --out output\motorC.json
```

本例实跑结果（I 口径；文件里是**二次值**，画像里已经是**一次值**）：

| 特征 | ΔIa / ΔIb / ΔIc | ΔP | ΔQ | 峰值比 | ΔIh |
|---|---|---|---|---|---|
| μ | 40.50 / 40.50 / 40.50 A | 25 000 W | 12 106 var | 1.00 | **8.019 A** |
| 幅值 amp（三相合成） | **70.14 A** | — | — | — | — |

```
可接受区间 0.70~1.30×，候选门槛 35.072 A
```

> **换算核对**（现场必做一次）：25 kW、400 V、pf 0.9 ⇒ 线电流 ≈ 25 000 / (1.732×400×0.9) ≈ **40.1 A**，与 μ 的 40.50 A 对得上 ⇒ PT/CT 与接线都填对了。对不上就先别往下走。

##### 第 2 步：派生网格——**份数由"最低档"决定**

先按 3 份做（和例 1 一样的习惯），再看它够不够：

```
  · motorC@53%   k=0.534  可接受 0.69~1.31×  min_d=18.7 A
  · motorC       k=1      可接受 0.70~1.30×  min_d=35.1 A
  · motorC@186%  k=1.857  可接受 0.70~1.30×  min_d=65.1 A
```

换算成**绝对档位**：

| 份 | 覆盖（相对已录档） | 绝对覆盖 | 该份门槛 min_d |
|---|---|---|---|
| @53% | 0.369~0.700 | **25.9~49.1 A** | 18.7 A |
| @100% | 0.700~1.300 | 49.1~91.2 A | 35.1 A |
| @186% | 1.300~2.414 | 91.2~169.3 A | 65.1 A |

**问题立刻暴露**：35 % 档的三相合成幅值＝0.35 × 70.14 = **24.55 A**，比最下面那份的下界 **25.9 A** 还小一点点（差 5 %）⇒ 3 份**覆盖不到最低档**。这正是第 2 层自检的意义：**不用去回放就能看出来**。

改成 **5 份**（`--derive-grid 5`）：

| 份 | 绝对覆盖 | 门槛 min_d |
|---|---|---|
| @28% | **13.6~25.9 A** | 9.9 A |
| @53% | 25.9~49.1 A | 18.7 A |
| @100% | 49.1~91.2 A | 35.1 A |
| @186% | 91.2~169.3 A | 65.1 A |
| @345% | 169.3~314.5 A | 121.0 A |

最低档 24.55 A 落进 @28% 那份 ✔。

##### 第 3 步：回放出判定矩阵

```powershell
$P = "output\motorC.json;output\motorC_grid\motorC_stage0.281.json;...;output\motorC_grid\motorC_stage3.449.json"
python tools/nilm_replay.py --file data\bus_3p3w_ct250.csv --config configs\site_3p3w.json `
    --set profile.enabled=1 --set "nilm.profile_path=$P" --out output\events_motorC.csv
```

**3 份时**（覆盖不到最低档）：

| 台阶 | 真实档位 | @53% | @100% | @186% |
|---|---|---|---|---|
| 09:00:03 / 06 | 100 % | ✘ 0.00 | **✔ 0.993** | ✘ 0.06 |
| 09:00:09 / 12 | 55 % | **✔ 0.996** | ✘ 0.07 | — |
| 09:00:15 / 18 | **35 %** | ✘ 0.22 / 0.11 | — | — |

> ☞ 最后一行就是"**整档漏报**"：35 % 档的合成幅值 24.55 A 比 @53% 的下界 25.9 A 小 5 %，连候选都没生成（`—`），事件表里看不到任何异常痕迹。
| 09:00:21 / 24 | 别的设备（60 kW） | ✘ 0.00 | ✘ 0.00 | ✘ 0.01 |

**5 份时**：

| 台阶 | 真实档位 | @28% | @53% | @100% | @186% | @345% |
|---|---|---|---|---|---|---|
| 09:00:03 开 | 100 % | ✘ 0.00 | ✘ 0.00 | **✔ 0.993** | ✘ 0.06 | — |
| 09:00:06 关 | 100 % | ✘ 0.00 | ✘ 0.00 | **✔ 0.993** | ✘ 0.06 | — |
| 09:00:09 开 | 55 % | ✘ 0.00 | **✔ 0.996** | ✘ 0.07 | — | — |
| 09:00:12 关 | 55 % | ✘ 0.00 | **✔ 0.996** | ✘ 0.03 | — | — |
| 09:00:15 开 | 35 % | **✔ 0.576** | ✘ 0.22 | — | — | — |
| 09:00:18 关 | 35 % | **✔ 0.576** | ✘ 0.11 | — | — | — |
| 09:00:21 切负荷 | 别的设备 | ✘ 0.00 | ✘ 0.00 | ✘ 0.00 | ✘ 0.01 | ✘ 0.29 |
| 09:00:24 恢复 | 别的设备 | ✘ 0.00 | ✘ 0.00 | ✘ 0.00 | ✘ 0.01 | ✘ 0.29 |

**6/6 命中、每个台阶恰一份 ✔、别的设备全拒（最高 0.29 < 0.3 门槛）⇒ 通过。**

##### 第 4 步：对账

```powershell
python tools/nilm_check.py --events output\events_motorC.csv --truth data\truth_3p3w.csv --tol-s 1.5
```

`profile` 行：**命中 6 / 漏报 0 / 误报 0**。

##### 顺带验证一下"重构勾没勾"的影响（一次就够，不必每次做）

把「3P3W 虚拟中性点重构」取消勾选、其余不变，用**同一套 5 份网格**回放：

| | 勾了重构 | 没勾重构 |
|---|---|---|
| 100 % 档 | ✔ 0.993 | ✔ 0.893 |
| 55 % 档 | ✔ 0.996 | ✔ 0.966 |
| 35 % 档（由 @28% 认） | ✔ 0.576 | ✔ 0.604 |
| 6 条启停是否全中 | 6/6 | 6/6 |
| 别的设备 | 全拒 | 全拒 |

**本例数据里差别不大**——因为三相对称（Ia=Ib=Ic），少一维 ΔIb 几乎不损失信息；**不要因此以为可以不勾**：
1. 不勾时引擎会给提示"本侧为 3p3w **未勾选 3P3W 重构则跳过 ΔIb**"，`quality_flags` 与候选 CSV 里也能看到维度少一维；
2. 重构用的是严格等式 `ib = −(ia + ic)`（没有中性线，这是物理事实，不是估计）；相电流**不平衡**时，不勾就等于把 B 相的真实信息整段丢掉——档位越低、绝对下限占比越大，丢的那一维伤害越明显；
3. 只有三相三线才有这个勾选框（3p4w 灰掉），所以**看到能勾就勾**，不会错。

---

#### H.28.4 份数到底怎么定（照这张表填，不用算）

网格间距是**每份画像实测**出来的（本例 1.985、例 2 1.857，不是固定常数），所以"份数 → 覆盖范围"是按实测窗口接力算出来的。本机实测：

| 份数 | 例 1（500 W，间距 1.985） | 例 2（25 kW，间距 1.857） |
|---|---|---|
| 1 份（不派生） | 0.67~1.33 ｜ 335~665 W | 0.70~1.30 ｜ 49~91 A |
| **3 份** | **0.50~1.99** ｜ 159~1320 W | 0.53~1.86 ｜ 25.9~169 A |
| **5 份** | **0.25~3.94** ｜ 71~2601 W | 0.28~3.45 ｜ 13.6~314 A |

> 两例的间距不同（1.985 / 1.857），因为间距是**每份画像实测的接受窗口之比**，不是常数；同一台设备换一次画像、间距也会跟着变。**永远以 CLI/界面打印的"可接受区间"为准**，别记死数字。

**三步定份数**：

1. **算最低档**：`最低档 / 已录档`。本例 1 是 35 %/100 % = 0.35；例 2 也是 0.35。
2. **查表要几份**：0.35 落在 3 份的 0.50 之下 ⇒ **3 份不够**（例 1 只差一点点就够，因为它的绝对下限把窗口撑宽了；**不能想当然，必须看第 2 步打印的绝对覆盖**）。
3. **再看上限**：最上面那份的绝对上界**不要超过设备铭牌最高档**太多。例 1 铺 5 份到 3.94 倍（2601 W），就把别人 1500 W 的切负荷收进来了。

> **经验数**：现场按 `最低档/已录档 = 0.35~1.0` 估，通常 **3 份（0.5~2×）** 够用；要到 25 % 档才需要 **5 份**；**超过 5 份基本没有必要**——真正连续可调的设备应当用 `stage_free=1`（一份画像覆盖任意档），而不是铺很多份。
>
> 更省事的一条：**如果知道档位数值**（铭牌/工艺卡有 30 %、50 %、70 %、100 %），就别用"等间距网格"，直接用**精确派生**：
> ```powershell
> python tools/nilm_profile.py --derive-from output\pumpA.json --derive-stages "0.35,0.55,0.75,1.0"
> ```
> 实测（例 1）：精确派生 3 份 ⇒ 6/6 命中，**置信度 0.99 以上**（网格 3 份的低档只有 0.41）；别的设备全拒。**前提是档位数值可信**——派生出来的画像只在那个倍数附近有效（窗口约 ±30 %），档位估错 20 % 就白搭。

---

#### H.28.5 五种常见失败与处置（照着改，一次只改一项）

| 现象（在判定矩阵/事件表里看到的） | 多半原因 | 怎么改 |
|---|---|---|
| 某个已知档位**整行都是「—」** | 幅值低于所有份的 `min_d`（网格没覆盖到） | 加份数（3→5）或直接用 `--derive-stages` 精确派生该档 |
| 某档位有 **✘ 0.1~0.25** 但没有 ✔ | 落在两份**交界处**／该份窗口够不着 | 精确派生该档；或把 `min_stage` 从 0.5 降到 0.3（**只影响"有没有候选"，不改判定口径**） |
| **同一个台阶被两份同时 ✔** | 两份窗口重叠太多（手动指定的倍数太密） | 相邻倍数差 **≥1.3 倍**；用 `--derive-grid` 让程序按实测窗口接力 |
| **别的设备被认了**（误报） | 网格铺太宽，高档那份的窗口覆盖了别人 | 减份数/减上限；必要时 `min_confidence` 0.3→0.4~0.5（**注意低档会一起被拦**，见下） |
| 低档位 conf 只有 0.4~0.6，想抬高 | 幅值小、绝对下限占比大 | **不要动**。0.4 是正常的；要提升只能补录该档真实数据重提画像 |

**实测反例：用提高 `min_confidence` 压误报，会把低档一起拦掉**

例 1：3 份网格 + `min_confidence=0.5` ⇒ 35 % 档（conf 0.41）被判拒 ⇒ `nilm_check` 从 6/6 掉到 **4/6（漏 2 条）**。
所以顺序永远是：**先用份数把覆盖范围调对，再考虑置信度**；置信度只在"确实有一类固定幅值的干扰设备"时才微调。

---

#### H.28.6 不要做（每条都有实测后果）

| 不要做 | 后果（实测） |
|---|---|
| **把不同档位的启停混进同一份画像**（"多录几档不是更好吗"） | μ 落到两档之间（实测 0.687 档，实际不存在）、σ 涨到 59~64 %，一份"同幅值纯线性假负荷"以 **conf 0.43** 被确认 ⇒ 判别力整体丧失 |
| **派生网格 + `stage_free=1` 同时开** | 每份画像都能缩放到任意档位 ⇒ 一次启停被 4~5 份**同时**报出：6 条真实启停变成 **26 条**。**二选一**：要么网格（要"是哪一档"，可解释），要么自由匹配（要"任意档"，省事） |
| **靠调大 `d2_max` / 放宽 σ 来"覆盖档位"** | 所有档位都"像"，所有他设备也"像"。派生/自由匹配就是为了**不动判定口径**而做的 |
| **网格只往上铺、不管最低档** | 例 2 的 3 份就是这样：35 % 档 24.55 A 差 5 % 落在窗口外，**整档漏报**，事件表里看不出来任何异常 |
| **派生完直接上线，不做第 3/4 步** | 例 1 的 5 份网格单看事件表"每个档位都报了"，对账才发现多报 2 条 |

---

#### H.28.7 一页纸（贴工位）

**A. 四步走**

```
① 提画像（只录到的那一档，别混档）
   python tools/nilm_profile.py --file data\dev.csv --device 设备名 --labels "..." `
       --config configs\现场.json --pre 10 --post 50 --out output\设备.json
   → 记下：可接受区间（约 0.67~1.33×）、候选门槛 min_d

② 派生网格（份数按"最低档 ÷ 已录档"查 H.28.4 表；知道档位就用 --derive-stages）
   python tools/nilm_profile.py --derive-from output\设备.json --derive-grid 3 --stage-out-dir output\grid
   → 核对：相邻两份首尾相接、最下面一份的下界 ≤ 最低档幅值

③ 挂上回放（把打印出来的 ; 路径串整段粘进去）
   python tools/nilm_replay.py --file data\bus.csv --config configs\现场.json `
       --set profile.enabled=1 --set "nilm.profile_path=<路径串>" --out output\events.csv

④ 对账
   python tools/nilm_check.py --events output\events.csv --truth data\truth.csv --tol-s 1.5
```

**B. 验收清单（5 条全过才算通过）**

1. 每个**已知档位**都有一份画像 **✔**（且只有一份）；
2. 每个**已知档位**的相邻档**没有**被那份认走（✘ 或 —）；
3. **别的设备**的启停**一条都没被认**（真值表里写「其它」的那些）；
4. `nilm_check` 的 `profile` 行：**命中率 100 %、漏报 0、误报 0**；
5. 低档位的置信度即便只有 0.4~0.6 也**照原样保留**（别为了好看改阈值）。

**C. 三个"记得看"**

* **三相三线**记得勾「3P3W 虚拟中性点重构」，PT/CT 两侧填一样（例 2）；
* 事件表里 `device_id` 带 `@50%` 后缀 ⇒ 是**派生画像**认的（该档无实录，属推断）；
* 事件表里 `event_kind` 是 `stage_up` / `stage_down` ⇒ 设备**没停机、只是换档**（v0.99.29，H.27）。

---

### H.29 v0.99.29：多档位 + 派生网格的**验收测试用例集**（照单执行、填表签字）

> **和 H.28 的分工**：H.28 讲"为什么"——一份画像为什么只认一档、派生网格怎么首尾相接、判定矩阵的 ✔ / ✘ / — 怎么读；这一节是**执行层**：14 条编号用例，每条给「命令 → 期望值 → 看到什么算过 → 看到什么算不过」，外加一张能直接抄进交付文档的记录表，以及"改了哪个参数、只需重跑哪几步"的复测表。
> **给谁看**：现场实施、运维、交付验收。**不需要懂算法**，会复制命令、会对着数字打勾就行。
> **两个例子照旧**：例 1＝三相四线（3p4w，PT=CT=1，有功口径，500 W 设备）；例 2＝三相三线＋虚拟中性点重构（3p3w，PT=4、CT=250，电流口径，25 kW 电机）。
> **期望值怎么用**：下面的数字都是 v0.99.29 实测。你的结果**允许差一点**（置信度 ±0.05、门槛 ±2 %），但三个结论必须对得上：① 每个已知档位**恰有一份**画像 ✔；② 别的设备**一条都不认**；③ 对账 **命中 100 % / 漏报 0 / 误报 0**。

#### H.29.0 四个词先对齐

| 词 | 在这套测试里指什么 | 在哪看 |
|---|---|---|
| **一档** | 设备的一种出力工况（100 % / 55 % / 35 % …） | 工艺记录、操作票、铭牌 |
| **一份画像** | 一个 `profile_*.json` 文件：基准那份不带后缀，派生那份带 `@50%` 之类后缀 | `output\nilm\` 或派生目录 |
| **派生网格** | 由一份画像按倍数复制出的一组画像，**首尾相接**覆盖多档 | `--derive-grid N` 的打印 / 界面 ④ 组结果表 |
| **判定矩阵** | 每个台阶 × 每份画像的 ✔ / ✘ / — 表 | 事件 CSV 里 `algorithm=profile` 的行 |

> **三种符号**（H.28 讲过，验收时天天用，再抄一遍）：
> **✔ 置信度**＝这份画像认了（`status=confirmed`）；**✘ 置信度**＝看了但拒了（`rejected`）；**—**＝连候选都没生成（幅值低于该份 `min_d`，事件表里**什么都没有**）。

#### H.29.1 开测前 5 分钟（5 项，缺一项就别开测）

| # | 检查项 | 怎么做 | 不合格的现象 |
|---|---|---|---|
| 1 | **功能对得上**（不是看版本号） | `python tools/nilm_profile.py --help` → 输出里应出现 `--derive-grid` / `--derive-stages` / `--derive-from`；界面「设备画像提取」下方应有 **④ 派生档位画像** 一组 | 低版本没有这三个参数、界面没有 ④ 组 ⇒ 先升级再测（⚠ `elec_tool.__version__` 仍写着 `0.1.0`，那是历史遗留，**不要**拿它判版本，以功能为准） |
| 2 | **三份文件在位** | ① 设备支路录波（含 2 组以上启停）② 总线录波（含**已知档位**的启停 + 至少一台别的设备）③ 真值表 CSV | 少真值表就只能看事件表，做不了④层对账 |
| 3 | **两侧口径一致** | 接线方式、PT/CT（启用勾选＋变比）、检测量（P / I）在**设备侧与总线侧填成同一套** | 例 2 那种 PT=4 / CT=250：一侧漏填 ⇒ ΔI 差 250 倍，**永远匹配不上** |
| 4 | **"已知档位"从哪来** | 见下方三条路 | 不知道档位就没法判"恰一份"，只能看有没有报 |
| 5 | **记录表打印出来** | 抄 H.29.5 那张表，一个用例一行 | 没有记录＝没有验收（返工全靠印象） |

**没有"已知档位"的总线数据怎么办**（三条路，从可靠到将就）：

1. **现场录一段**（最可靠）：按操作票**从低档到高档、每档开 3 s 关 3 s**，同时用手机/秒表记时刻 → 直接生成真值表。
2. **自己拼一段**（次可靠）：把设备支路录波按 0.35 / 0.55 / 1.0 倍**缩放后依次叠加**到一段基线负荷上，写成总线 CSV；叠加时刻就是你写进真值表的时刻。本轮两个例子就是这么造的（脚本 `gen4.py`，不在仓库里，逻辑就是"基线 + k×设备支路"）。
3. **仓库自带的演示台阶**（只能验证流程通不通，不代表现场）：`python tools/gen_nilm_sample.py` 出 `data/nilm_steps.csv`（2.0 s +500 W、4.4 s −300 W），拿来跑一遍 A2→A5 熟悉操作可以，**不能当验收证据**。

> **排障入口**：某条台阶"明明动了却没报"，先跑
> `python tools/nilm_profile_diag.py --profile output\pumpA.json`（看画像本身的方向/幅值是否正常），
> 再跑 `python tools/nilm_profile_diag.py --file data\dev_3p4w.csv --at 09:00:15`（看那一刻稳态段怎么切、为什么某个口径找不到事件）。

---

#### H.29.2 A 组：三相四线（3p4w，PT=CT=1，P 口径，500 W 设备）

**场景**：设备实际跑 **100 % / 55 % / 35 %** 三档；录波只录到 100 % 档；总线上还有一台约 1500 W 的普通负荷（21 s 切、24 s 恢复）。

##### A1｜画像自检（30 秒，决定后面全部用例的判据）

```powershell
python tools/nilm_profile.py --file data\dev_3p4w.csv --device pumpA `
    --labels "09:00:02,开;09:00:05,关;09:00:08,开;09:00:11,关" `
    --config configs\default.json --pre 10 --post 50 --out output\pumpA.json
```

| 期望看到的数 | 实测值（本例） | 判据 |
|---|---|---|
| 可接受区间 | **0.670 ~ 1.330×** | 应在 0.6 ~ 1.4 之间；窄到 0.9~1.1 说明样本太整齐（少见），宽到 0.3~3.0 说明**混档了**（H.28.6） |
| 候选门槛 `min_d` | **250.003 W** | ≈ 幅值的一半；它决定"多小的台阶连候选都没有" |
| 画像幅值 `amp` | **500.005 W** | 与 μΔP 一致 |
| 相邻份间距 `grid_ratio` | **1.985** | 每份画像自己算的，不是常数（例 2 是 1.857） |
| μ 关键维 | ΔIa **3.240 A**、ΔP **500.0 W**、ΔIh **0.641 A** | ΔIh 接近 0 ⇒ 可能是线性负荷或数据源无谐波 |

> ⚠ 本例每方向只有 2 次启停，CLI 会打"建议每方向 ≥3 次"。**这是提示不是错误**，可以继续，但要在记录表"备注"里写明——σ 取下限，判别力偏弱。

**A1 的作用**：把 0.670 / 1.330 / 250.003 这三个数抄到记录表上。后面所有"通过/不通过"都是拿它们比出来的。

##### A2｜派生网格自检（3 份，不出门就能判"够不够"）

```powershell
python tools/nilm_profile.py --derive-from output\pumpA.json --derive-grid 3 `
    --stage-out-dir output\pumpA_grid --config configs\default.json
```

| 期望输出（3 行 + 1 条路径串） | k | 可接受区间 | `min_d` |
|---|---|---|---|
| `pumpA@50%` | 0.5038 | 0.63 ~ 1.37× | **125.941 W** |
| `pumpA`（＝基准，不复制） | 1.000 | 0.67 ~ 1.33× | **250.003 W** |
| `pumpA@199%` | 1.985 | 0.67 ~ 1.33× | **496.274 W** |

**两条自检判据（都要打勾）**：

| 检查 | 本例换算 | 怎么判 |
|---|---|---|
| 相邻两份**首尾相接** | 0.50× 覆盖 **159~345 W**；1.00× 覆盖 **335~665 W**；1.99× 覆盖 **665~1320 W** | 上一份上界 ≈ 下一份下界（重叠一点点正常）；**留大缝**就是漏档 |
| 覆盖到**最低档** | 最低档 35 % = **175 W**，落在 0.50× 的 159~345 W 里 ✔ | 最低档幅值 ≥ 最下面那份的下界 |

> **换算口诀**：绝对覆盖 ＝ `k × 该份自己的可接受区间 × 画像幅值`。不用手算，CLI / 界面逐份都打印。

##### A3｜对照组：**只挂基准画像**（证明网格不是心理安慰）

```powershell
python tools/nilm_replay.py --file data\bus_3p4w.csv --config configs\default.json `
    --set profile.enabled=1 --set "nilm.profile_path=output\pumpA.json" --out output\events_single.csv
```

| 台阶 | 真实档位 | 期望 |
|---|---|---|
| 09:00:03 / 06 | 100 % | ✔ 0.99 |
| 09:00:09 / 12 | 55 % | ✘ 0.10 / 0.05（拒） |
| 09:00:15 / 18 | 35 % = 175 W | **—（175 W < 250 W 门槛，连候选都没有）** |
| 09:00:21 / 24 | 别的设备 | ✘ 0.00 |

**判据**：这条用例必须**看到漏报**。如果单份就 6/6 全中，说明你的设备档位本来就在 ±30 % 内——那就不需要网格，省一步。

##### A4｜3 份网格回放，出判定矩阵（核心用例）

```powershell
$P = "output\pumpA.json;output\pumpA_grid\pumpA_stage0.504.json;output\pumpA_grid\pumpA_stage1.99.json"
python tools/nilm_replay.py --file data\bus_3p4w.csv --config configs\default.json `
    --set profile.enabled=1 --set "nilm.profile_path=$P" --out output\events_pumpA.csv
```

本例实跑（`algorithm=profile` 共 **6 行**）：

| 台阶 | 真实档位 | @50% | @100% | @199% | 结论 |
|---|---|---|---|---|---|
| 09:00:03 开 | 100 % | ✘ 0.00 | **✔ 0.9916** | ✘ 0.06 | 恰一份 |
| 09:00:06 关 | 100 % | ✘ 0.00 | **✔ 0.9916** | ✘ 0.06 | 恰一份 |
| 09:00:09 开 | 55 % | **✔ 0.9562** | ✘ 0.10 | — | 恰一份 |
| 09:00:12 关 | 55 % | **✔ 0.9562** | ✘ 0.05 | — | 恰一份 |
| 09:00:15 开 | 35 % | **✔ 0.4075** | — | — | 恰一份（低档置信度天然低） |
| 09:00:18 关 | 35 % | **✔ 0.4074** | — | — | 恰一份 |
| 09:00:21 / 24 | 别的设备 | ✘ 0.00 | ✘ 0.00 | ✘ 0.00 | 全拒 ✔ |

**判据（三条全中才算过）**：
1. 6 个已知台阶 → **6 条 confirmed**，不多不少；
2. 每个台阶的 ✔ **只落在同一份**画像上；
3. `09:00:21 / 24` 两行**一条 confirmed 都没有**。

> **0.41 不是失败**。低档幅值小，几项绝对下限（谐波 2 A、无功 30 var）占比变大、相对容差变松，置信度天然落在 0.4~0.6。**不要**为了让数字好看去改 `min_confidence`（见 N3）。

##### A5｜对账（一条命令给结论）

```powershell
python tools/nilm_check.py --events output\events_pumpA.csv --truth data\truth.csv --tol-s 1.5
```

期望 `profile` 行：

```
  profile           6    6    0    0      0    100%  ✅ 可上线   (设备画像匹配)
```

| 列 | 含义 | 本例 |
|---|---|---|
| 命中 / 漏报 / 误报 | 对真值表（真值表里别的设备写「其它」） | **6 / 0 / 0** |
| 总结论 | 7 种算法一起看 | ✅ 7 种算法全部命中且 0 误报 |

> 同一段里其它 6 种算法也会各占一行，**那是另一套参数的事**；本节只看 `profile` 行。其它算法显示"其它设备 2 条"是正常的（它们不认设备，只认台阶）。

##### A6｜负向用例：故意铺 **5 份**，你必须看到它出错

```powershell
python tools/nilm_profile.py --derive-from output\pumpA.json --derive-grid 5 --stage-out-dir output\pumpA_grid5
```

5 份的覆盖是 0.25 / 0.50 / 1.00 / 1.99 / **3.94×**，最上面那份 `min_d` = **985.140 W**、判定窗口 **1340~2601 W**。于是那台 **1500 W** 的别的设备正好落进窗口：

| 期望看到 | 实测 |
|---|---|
| 事件表 confirmed **10 条**（应为 6） | 6 条真实 + 2 条误报 + 2 条重复 |
| 误报 | 09:00:21 `STOP`、09:00:24 `START`，各 **0.6824**，记在 `pumpA@394%` 名下 |
| 重复 | 35 % 档被 `pumpA@25%`（**0.4568**）与 `pumpA@50%`（**0.4075**）**同时**认 ⇒ 违反"恰一份" |
| `nilm_check` | `profile` 命中 6、漏报 0、**2 条带内误报** ⇒ ⚠ |

**判据**：这条用例**必须"不通过"**。如果你铺 5 份仍然只有 6 条，只能说明你那段数据里没有幅值落进顶档窗口的其它负荷，**不代表 5 份安全**——记录表备注里要写清这一点。

##### A7｜加分用例：知道档位数值就用精确派生（比网格干净）

```powershell
python tools/nilm_profile.py --derive-from output\pumpA.json --derive-stages "0.35,0.55,1.0" `
    --stage-out-dir output\pumpA_exact
```

| | 3 份网格（A4） | 精确派生 3 份（A7） |
|---|---|---|
| 100 % 档 | ✔ 0.9916 | ✔ **0.992** |
| 55 % 档 | ✔ 0.9562 | ✔ **0.993** |
| 35 % 档 | ✔ 0.4075 | ✔ **0.995** |
| 别的设备 | 全拒 | 全拒 |
| `nilm_check` | 6/6 0/0 ✅ | 6/6 0/0 ✅ |

**结论**：档位数值可信（铭牌 / 工艺卡 / 操作票）就优先精确派生——低档置信度从 0.41 抬到 0.995，且不会有重叠。**前提**：档位估错 20 % 就白搭（窗口只有 ±30 %）。

---

#### H.29.3 B 组：三相三线＋重构（3p3w，PT=4、CT=250，I 口径，25 kW 电机）

**场景**：25 kW 电机接在**三相三线**（两表法）进线上，PT=4、CT=250，数据源没有可信电压 ⇒ **电流口径 I**；实际跑 100 % / 55 % / 35 % 三档，只录到 100 %；总线上另有一台大负荷（21 s 切、24 s 恢复）。

##### B1｜接线与量纲自检（先算一遍，再信软件）

| 检查项 | 怎么做 | 期望 |
|---|---|---|
| 接线方式 | 设备侧与总线侧都选 **3p3w** | 选成 3p4w：Uab 会算成 604 V、P 大 3 倍（实测） |
| 虚拟中性点重构 | **勾选**（仅 3p3w 可勾） | 不勾：ΔIb 整维跳过，引擎会给提示 |
| PT / CT | 两侧都 **4 / 250** | 一侧漏填 ⇒ ΔI 差 250 倍，永远匹配不上 |
| 量纲手算 | 25 kW / (1.732 × 400 V × 0.9) ≈ **40.1 A** | 画像 μΔIa 应 ≈ 40.5 A（实测 **40.497 A**） |

```powershell
python tools/nilm_profile.py --file data\dev_3p3w_ct250.csv --device motorC `
    --labels "09:00:02,开;09:00:05,关;09:00:08,开;09:00:11,关" `
    --config configs\site_3p3w.json --quantity i --wiring 3p3w --reconstruct-3w `
    --pre 10 --post 50 --out output\motorC.json
```

| 期望看到的数 | 实测 |
|---|---|
| 可接受区间 | **0.700 ~ 1.300×** |
| 候选门槛 `min_d` | **35.072 A** |
| 画像幅值 `amp`（三相合成） | **70.143 A** |
| μΔIa / μΔIh | 40.497 A / **8.019 A** |
| 间距 `grid_ratio` | **1.857** |

**判据**：手算 40.1 A 与 μ 40.497 A 差 <5 % ⇒ 接线与 PT/CT 都对；差 3 倍或 250 倍 ⇒ 先改配置，别往下走。

##### B2｜3 份**不够**——这一条用例的价值就是"不用回放也能看出来"

3 份派生：`@53%`（k=0.534，0.69~1.31×，`min_d` 18.7405 A）、`1.0`（0.700~1.300×，35.0715 A）、`@186%`（k=1.857，65.1328 A）。换算成绝对档位：**25.9~49.1 / 49.1~91.2 / 91.2~169.3 A**。

最低档 35 % 的合成幅值 ＝ 0.35 × 70.143 = **24.55 A**，比最下面那份的下界 **25.9 A** 还小 5 %：

| 判据 | 本例 |
|---|---|
| 最低档幅值 ≥ 最下面一份的下界？ | 24.55 A **<** 25.9 A ⇒ **不够** |
| 回放会看到什么 | 6 条真实启停只出 **4 条 confirmed**（0.993 ×2、0.996 ×2），35 % 档**整行都是 —**，事件表里毫无异常痕迹 |

**判据**：如果你在图 / 表上看到"低档位静默"但 A2 的自检也显示覆盖不到，那就不用回放——直接加份数。

##### B3｜改成 5 份，回放通过

```powershell
python tools/nilm_profile.py --derive-from output\motorC.json --derive-grid 5 --stage-out-dir output\motorC_grid
```

| 份 | k | 绝对覆盖 | `min_d` |
|---|---|---|---|
| @28% | 0.281 | **13.6 ~ 25.9 A** | 9.871 A |
| @53% | 0.534 | 25.9 ~ 49.1 A | 18.7405 A |
| @100% | 1.000 | 49.1 ~ 91.2 A | 35.0715 A |
| @186% | 1.857 | 91.2 ~ 169.3 A | 65.1328 A |
| @345% | 3.449 | 169.3 ~ 314.5 A | 120.961 A |

最低档 24.55 A 落进 @28% 那份 ✔。回放（`profile.enabled=1` + 5 份路径串）：

| 台阶 | 真实档位 | 期望 |
|---|---|---|
| 09:00:03 / 06 | 100 % | **✔ 0.993**（@100%） |
| 09:00:09 / 12 | 55 % | **✔ 0.996**（@53%） |
| 09:00:15 / 18 | 35 % | **✔ 0.576**（@28%） |
| 09:00:21 / 24 | 别的设备 | **全拒**（最高候选 0.29 < 0.3） |

**判据**：6 条 confirmed、每档恰一份、别的设备 0 条 ⇒ 通过。

##### B4｜对照用例：重构勾 vs 不勾（一次就够，不必每次做）

用**同一套 5 份网格**、只改「3P3W 虚拟中性点重构」：

| | 勾了重构 | 没勾重构 |
|---|---|---|
| 100 % 档 | ✔ 0.993 | ✔ 0.893 |
| 55 % 档 | ✔ 0.996 | ✔ 0.966 |
| 35 % 档 | ✔ 0.576 | ✔ 0.604 |
| 6 条启停是否全中 | **6/6** | **6/6** |

**判据**：本例三相对称（Ia=Ib=Ic），差别很小——**不要因此以为可以不勾**：不勾等于把 B 相信息整段丢掉，相电流不平衡时低档伤害最明显；而且面板上只有 3p3w 能勾，看到能勾就勾。

##### B5｜对账

```powershell
python tools/nilm_check.py --events output\events_motorC.csv --truth data\truth_3p3w.csv --tol-s 1.5
```

期望 `profile` 行：**命中 6 / 漏报 0 / 误报 0 ⇒ ✅ 可上线**。

---

#### H.29.4 N 组：14 条里的 4 条负向用例（**必须"失败"才算你的测试有效**）

> 只做正向用例的验收是"自证清白"：软件怎么报你都说对。下面 4 条要**主动把系统弄坏**，确认它**按预期坏**——坏不出来，说明你的测试数据太干净，换一段再测。

| # | 怎么弄坏 | 必须看到的现象（实测） | 说明什么 |
|---|---|---|---|
| **N1** | **混档提取**：把 100 % 与 55 % 的启停一起喂给 `--labels` | μ 落到 **0.687 档**（一个不存在的档位）、σ 涨到 **59~64 %**；一份"同幅值纯线性假负荷"被以 **conf 0.43** 确认 | 混档＝把画像做成"平均值"，判别力整体丧失（H.28.6） |
| **N2** | **网格 + `stage_free=1` 同开** | 6 条真实启停变成 **26 条**（每次启停被 4~5 份各报一次） | 二选一：网格（要知道"是哪一档"）或自由匹配（要"任意档"），**不能叠** |
| **N3** | 3 份网格 + `--set profile.min_confidence=0.5` | 6 条变 **4 条**：35 % 档（0.41）被一起拦掉 ⇒ `nilm_check` **67 % 命中、漏 2** | 置信度阈值是"一刀切"，压误报会连真命中一起杀 |
| **N4** | **手填太密的倍数**：`--derive-stages "0.9,1.0,1.1"` | 同一个台阶被 **2~3 份同时 ✔**（事件表重复） | 相邻倍数差必须 ≥ **1.3 倍**（本例 ≥1.99）；不知道间距就让 `--derive-grid` 按实测窗口接力 |

---

#### H.29.5 测试记录表（照抄到 Excel / 交付文档，一用例一行）

| 用例 | 数据 / 配置 | 期望（关键数字） | 实测 | 判定 | 备注 |
|---|---|---|---|---|---|
| A1 画像自检 | `dev_3p4w.csv`，pumpA，`--pre 10 --post 50` | 0.670~1.330×；`min_d` 250.003 W；`amp` 500.005 W；间距 1.985 | | ☐过 ☐不过 | 每方向几次？ |
| A2 网格自检（3 份） | `--derive-grid 3` | 125.941 / 250.003 / 496.274 W；覆盖 159~1320 W | | ☐过 ☐不过 | 最低档 175 W 是否覆盖 |
| A3 单份对照 | 单份路径串 | 只 100 % 两条 ✔ 0.99；35 % 整行 — | | ☐过 ☐不过 | 看到漏报才算过 |
| A4 3 份回放 | `bus_3p4w.csv` | 6 条 confirmed：0.9916 / 0.9562 / 0.4075；别的设备 0 | | ☐过 ☐不过 | 逐档是否恰一份 |
| A5 对账 | `nilm_check --tol-s 1.5` | `profile` 6 / 0 / 0，✅ 可上线 | | ☐过 ☐不过 | 其它算法行不看 |
| A6 负向 5 份 | `--derive-grid 5` | 10 条 confirmed；@394% 0.6824 ×2；@25% 0.4568 与 @50% 0.4075 重复 | | ☐预期失败 ☐没坏 | 没坏要换数据 |
| A7 精确派生 | `--derive-stages "0.35,0.55,1.0"` | 0.992 / 0.993 / 0.995；对账 6/0/0 | | ☐过 ☐不过 | 档位数值可信才做 |
| B1 接线自检 | 3p3w + 重构 + PT4/CT250 + I | μΔIa 40.497 A；手算 40.1 A；0.700~1.300×；`min_d` 35.072 A | | ☐过 ☐不过 | 差 3× / 250× 先改配置 |
| B2 3 份不足 | `--derive-grid 3` | 下界 25.9 A > 最低档 24.55 A；回放只 4 条 | | ☐过 ☐不过 | 整行 — 是预期 |
| B3 5 份通过 | `--derive-grid 5` | 6 条：0.993 / 0.996 / 0.576；别的设备全拒 | | ☐过 ☐不过 | 每档恰一份 |
| B4 重构对照 | 同 5 份，重构 off | 0.893 / 0.966 / 0.604，仍 6/6 | | ☐记录 ☐未做 | 一次即可 |
| B5 对账 | `nilm_check` | `profile` 6 / 0 / 0 | | ☐过 ☐不过 | |
| N1 混档 | 两个档位一起打标签 | μ 0.687 档、σ 59~64 %、假负荷 conf 0.43 | | ☐预期失败 ☐没坏 | |
| N2 网格+free | `stage_free=1` + 5 份 | 26 条事件 | | ☐预期失败 ☐没坏 | |
| N3 提阈值 | `min_confidence=0.5` | 6 → 4 条，命中 67 % | | ☐预期失败 ☐没坏 | |
| N4 倍数太密 | `--derive-stages "0.9,1.0,1.1"` | 同一台阶 2~3 份同时 ✔ | | ☐预期失败 ☐没坏 | |

---

#### H.29.6 判定与复测（改了什么，只重跑哪几步）

**结论只有三种**：

| 结论 | 条件 | 怎么处置 |
|---|---|---|
| ✅ **通过** | A1~A5、B1~B5 全过 **且** N1~N4 全部按预期"失败" | 可以上线；记录表签字 |
| ⚠ **有条件通过** | 低档 conf 0.4~0.6、每方向仅 2 次样本、或某档只靠派生（无实录） | 上线后**盯候选 CSV** 的 `c_*` 与 `status`；按 H.28.7 第 5 条保留原样，不改阈值 |
| ❌ **不通过** | 任一已知档位没有 ✔；同一台阶两份 ✔；别的设备被认；对账出现误报 | 按 H.28.5 改一项再测 |

**复测矩阵**（避免每次都从 A1 重来）：

| 你改了什么 | 只需重跑 | 说明 |
|---|---|---|
| 网格份数 / 派生倍数 | **A2 → A4 → A5** | 画像没变，不用重提 |
| `min_stage` / `min_confidence` / `d2_max` | **A4 → A5** | 记录表写清"改前 → 改后" |
| 重新提取画像（换数据、换样本量） | **A1 起全部** | μ/σ 变了，窗口与 `min_d` 都会变 |
| 接线方式 / PT / CT / 检测量 | **A1（B1）起全部** | 量纲变了，旧画像直接作废 |
| 换了总线录波（不同日期/工况） | **A3 → A4 → A5** | 画像可复用，判定矩阵要重出 |

---

#### H.29.7 一页纸：按顺序粘贴这 10 条（例 1 版本）

```powershell
# ① 自检：画像认几档
python tools/nilm_profile.py --file data\dev_3p4w.csv --device pumpA --labels "09:00:02,开;09:00:05,关;09:00:08,开;09:00:11,关" --config configs\default.json --pre 10 --post 50 --out output\pumpA.json
# ② 铺 3 份网格
python tools/nilm_profile.py --derive-from output\pumpA.json --derive-grid 3 --stage-out-dir output\pumpA_grid
# ③ 单份对照（必须看到 35 % 档漏）
python tools/nilm_replay.py --file data\bus_3p4w.csv --config configs\default.json --set profile.enabled=1 --set "nilm.profile_path=output\pumpA.json" --out output\events_single.csv
# ④ 3 份回放
python tools/nilm_replay.py --file data\bus_3p4w.csv --config configs\default.json --set profile.enabled=1 --set "nilm.profile_path=output\pumpA.json;output\pumpA_grid\pumpA_stage0.504.json;output\pumpA_grid\pumpA_stage1.99.json" --out output\events_pumpA.csv
# ⑤ 对账
python tools/nilm_check.py --events output\events_pumpA.csv --truth data\truth.csv --tol-s 1.5
# ⑥ 负向：5 份（必须坏）
python tools/nilm_profile.py --derive-from output\pumpA.json --derive-grid 5 --stage-out-dir output\pumpA_grid5
# ⑦ 精确派生（可选，最干净）
python tools/nilm_profile.py --derive-from output\pumpA.json --derive-stages "0.35,0.55,1.0" --stage-out-dir output\pumpA_exact
# ⑧ 排障：某台阶没报
python tools/nilm_profile_diag.py --profile output\pumpA.json
python tools/nilm_profile_diag.py --file data\dev_3p4w.csv --at 09:00:15
```

**记 6 个数就够（贴工位）**：

| 数 | 例 1（3p4w / P） | 例 2（3p3w / I） | 用来看什么 |
|---|---|---|---|
| 可接受区间 | 0.670~1.330× | 0.700~1.300× | 一份画像认多宽 |
| 候选门槛 `min_d` | 250.003 W | 35.072 A | 多小的台阶连候选都不生成 |
| 画像幅值 `amp` | 500.005 W | 70.143 A | 换算绝对档位 |
| 间距 `grid_ratio` | 1.985 | 1.857 | 相邻倍数最小差 |
| 3 份覆盖 | 159~1320 W | 25.9~169 A | 够不够最低档 |
| 5 份覆盖 | 71~2601 W | 13.6~314 A | 上限会不会收别人 |

> **一句话验收**：**每个已知档位恰有一份画像认、别的设备一条不认、对账 6/0/0**——三条全中才签字；三条里任一条对不上，回到 H.28.5 一次只改一项再测。

---

### H.30 v0.99.29：设备画像提取的参数怎么填、负荷辨识事件里「设备画像匹配」怎么配（逐项对照手册）

> **两个界面是一对**：左边（数据处理 → **设备画像提取**）产出"这台设备的指纹"，右边（**负荷辨识事件 → 设备画像匹配**）拿指纹到总线数据里找人。
> **一句话分工**：**提取侧决定"它长什么样"**（特征口径 + 窗口几何 + μ/σ + 轨迹模板），**检测侧只决定"多像才算像"**（候选门槛 + 相似度判据 + 档位策略）。所以**提取侧填错，检测侧怎么调都没用**；反过来检测侧配错，画像做得再准也报不出来。
> **本节怎么用**：H.30.1~H.30.2 是提取侧逐项；H.30.3 是检测侧"公共项"；H.30.4 是检测侧「设备画像匹配」的 14 个参数；H.30.5 给三套照抄的预设，H.30.6 给配参顺序，H.30.7 给"现象 → 改哪一项"。

#### H.30.0 先看清参数分布

| 位置 | 界面位置 | 参数 | 产出 / 去向 |
|---|---|---|---|
| **提取侧·基准配置** | 数据处理 → 设备画像提取 → 顶上「基准配置」组 | fs、f_nom、PT/CT（启用＋变比）、时标 UTC、接线方式、3P3W 重构、极性、检测量 | 写进画像 JSON（`pt_ct` / `wiring` / `quantity` / `unit`） |
| **提取侧·①②③** | 同页 ①设备与输出、②启停定位、③事件前后窗 | 设备 ID、文件名、启停标签、标签容差、合并间隔、前窗、后窗 | 设备 ID 与 **pre/post 窗口几何**写进画像，**检测侧直接用** |
| **提取侧·④** | 同页「④ 派生档位画像」 | 倍数、输出目录、ΔQ 缩放、谐波指数 | 生成多份画像，喂给检测侧的 `profile_path` |
| **检测侧·公共项** | 负荷辨识事件 → 检测参数（算法列表**上方**） | 检测量、周波窗长、最小事件间隔、事件落盘、自适应参数、相对容差、相对最小幅值 | 写进 `nilm.*` 与 `nilm.algorithms.*` |
| **检测侧·算法项** | 算法列表里的 **「设备画像匹配」** 一行（勾选后展开 14 项） | enabled、profile_path、d2_max、min_confidence、k_sigma、margin、lambda_rel、state_check、phase_map、max_scale、min_scale、stage_free、min_stage、stage_min_scale、stage_max_scale、stage_dim_max | 写进 `nilm.algorithms.profile` |

> ⚠ **三个"配了也不生效"的坑**（很多人卡在这）：
> ① 检测侧的「相对容差 `rel_tol_pct`」「相对最小幅值 `min_delta_pct`」「自适应算法参数 `auto_params`」**只作用于 6 种标量算法**（阈值差分 / 双滑窗 / CUSUM / GLR / 稳态分段 / 中值滤波），**对设备画像匹配一点影响都没有**——画像匹配的门槛来自**画像里的 σ** 与 `k_sigma`、`min_stage`、`d2_max`、`min_confidence`。
> ② 只填了 `profile_path` 但没勾「设备画像匹配」的 enabled ⇒ 不检测。
> ③ 检测量（P / I）与画像的 `quantity` 不一致 ⇒ 引擎**直接跳过这份画像**并在状态里报"画像按 W 口径构建，本侧检测量为 I：ΔP/ΔI 特征不可比"。

---

#### H.30.1 提取侧 A：基准配置（口径对不上，后面全白做）

| 项 | 默认 | 怎么定 | 填错的后果（实测） |
|---|---|---|---|
| **fs / f_nom** | 6400 Hz / 50 Hz | 照录波文件填；fs 错了周波切分就错 | fs 差 2 倍 ⇒ 周波数差 2 倍、所有"周波"参数（前后窗、持续）全错位 |
| **PT / CT（启用＋变比）** | 出厂 `enabled` 与变比⚠非 1，**界面默认不启用 = PT=CT=1** | 与总线侧**同一变比体系**（都换算成一次值） | 一侧填 PT=4/CT=250、另一侧没填 ⇒ ΔI 差 **250 倍**、ΔP 差 **1000 倍**，**永远匹配不上**；两侧都填（哪怕设备侧 CT=1、总线侧 CT=250）只提示、不影响匹配 |
| **时标 UTC** | 关（按本地时区解释文件时标） | 采集器写 UTC 才勾 | 差 8 h ⇒ 标签全部"不在文件时间范围内"，自动定位也跟着错 |
| **接线方式** | 3p4w | 三相三线（两表法）必须选 3p3w | 3p3w 选成 3p4w ⇒ Uab 算成 604 V、P 大 3 倍（实测） |
| **3P3W 虚拟中性点重构** | 关 | **3p3w 一律勾**（`ib = −(ia+ic)`，物理等式不是估计） | 不勾 ⇒ ΔIb 整维跳过（剩 7 维），相电流不平衡时判别力明显下降 |
| **极性反转** | 无 | CT 接反时填相别（如 `A`） | ΔP/ΔI 反号 ⇒ 画像与总线侧符号相反，永远对不上（候选 CSV 的 `sign_flip` 可定位） |
| **检测量 quantity** | auto（无电压→I） | **必须与总线侧 `nilm.quantity` 一致**：有可信电压用 p，只有电流用 i | 不一致 ⇒ 该画像不运行（见 H.30.0 坑③） |

> **模型对比手算一次**（现场 30 秒的自检）：I 口径下 `I ≈ P / (√3 × U线 × pf)`。例 2：25 kW、400 V、pf 0.9 ⇒ **40.1 A**，而画像实测 μΔIa = **40.497 A** ⇒ 口径对。差 3 倍＝接线错，差 250 倍＝CT 错。

---

#### H.30.2 提取侧 B：①②③④ 四组

##### ① 设备与输出

| 参数 | 默认 | 怎么定 | 说明 |
|---|---|---|---|
| **设备 ID** | `device` | 短英文/拼音（`pumpA`、`motorC`） | 写进画像与事件表 `device_id`；**多画像靠它区分**（去重键是"算法+设备"） |
| **画像文件名** | 空＝`profile_<设备>_<时间>.json` | 一般留空 | 写到 `nilm.nilm_dir`（默认 `output/nilm/`）；支持 `{时间}`/`{设备}` 占位 |

##### ② 启停定位（决定"取哪几次事件"）

| 参数 | 默认 | 怎么定 | 填错的后果 |
|---|---|---|---|
| **启停标签** | 空＝自动定位 | 有真值表就贴进来，每行 `时间,动作`（开/关、启动/停止、on/off、投入/切除 都认） | 标签写错方向 ⇒ 启动被当停止（会进 `shutdown` 组），μ/σ 分组整体错位 |
| **标签时刻容差** | **2 s** | 标签与实际变化点的时间差；秒表手记 1~3 s，采集延迟大取 3~5 s | 太小 ⇒ 找不到变化点（"标签 xx：附近没有找到最大变化"）；太大 ⇒ 跨到相邻事件，取到别人的台阶 |
| **合并间隔** | **10 s**（仅自动定位） | 分级带载 / 反复重启设备保持 10；动作很密的降到 3~5；不想合并填 0 | 太大 ⇒ 两次真启停被并成一次（少样本）；太小 ⇒ 一次启动被切成 3 段（μ 被拉偏） |

##### ③ 事件前后窗（**全节最重要的两个数字**）

| 参数 | 默认 | 怎么定 | 影响的三个地方 |
|---|---|---|---|
| **前窗 pre** | **10 周波**（0.2 s） | 取事件**前**的干净稳态；≥10 周波即可，紧邻他负荷动作时可缩到 5~10 | ① 设备侧"前值"中位数；② 总线侧候选搜索的前窗；③ 总线侧特征的前窗 |
| **后窗 post** | **50 周波**（1 s） | **≥ 设备启动过程时长**（冲击 + 爬升 + 收敛）：普通泵 50；软启/变频慢爬 200~400；密集投切 20 | ① 设备侧"后值"中位数；② 总线侧候选后窗；③ **检出延迟 ≈ post 周波** |

**为什么这两个数会"跨界面生效"**：画像 JSON 里写着 `pre_cycles` / `post_cycles`，引擎 `detect_profile` 直接读它们来
① 造候选（`_two_window_candidates` 的窗长）、② 量特征（`event_features` 的窗口）、③ 算检出延迟（事件要在 `end + post` 之后才确认）。**检测侧没有"前后窗"参数可以覆盖**——要改只能重提画像。

**窗长还会决定缓存窗口**：引擎要求

```
need = pre×max_scale + 最长持续 + 2×post×max_scale + 10        （周波）
```

默认 `pre/post=10/50`、`max_scale=8` ⇒ **need = 891 周波 ≈ 17.8 s**，而 `nilm.window_cycles` 默认 **300** ⇒ 引擎会自动把缓存扩到 891 并在状态里提示"已自动按 891 周波缓存评估；建议把画像前后窗改小或加大 window_cycles"（实测）。**不想扩窗就把 `max_scale` 降到 2（need=231）或 1（need=121）**——快事件本来不需要多尺度。

> **典型组合**（照抄）：
> | 设备类型 | pre / post | max_scale | 备注 |
> |---|---|---|---|
> | 普通泵 / 风机（硬启） | 10 / 50 | 2 | 通用默认，need=231 |
> | 电机软启动（斜坡 3~10 s） | 10 / 200 | 2~4 | need=821~1641，window_cycles 要跟上 |
> | 变频器慢降（20~60 s 尾） | 10 / 300~600 | 4~8 | 必须同时加大 `window_cycles` |
> | 密集投切（间隔 <1 s） | 5~10 / 20 | 1 | 后窗小才能分开相邻事件 |

##### ④ 派生档位（把"一档"铺成"多档"）

| 参数 | 默认 | 怎么定 | 说明 |
|---|---|---|---|
| **档位倍数** | 空 | 已知档位就填真实倍数（`0.35,0.55,0.75,1.0`）；不知道就用 CLI `--derive-grid N` 自动铺 | 相邻倍数差 **≥1.3~1.9 倍**（两例实测间距 1.985 / 1.857）；界面**不做自动网格** |
| **输出目录** | 空＝画像同目录 | 一般留空 | 生成 `<画像名>_stage<k>.json` |
| **ΔQ 缩放** | `scale` | 负载型无功（水泵、风机）用 scale；电机励磁无功基本恒定用 `const` | 填错 ⇒ 派生档的 ΔQ 维系统性偏大/偏小，低档更容易被拒 |
| **谐波指数 ih_exp** | 1.0 | 轻载 THD 明显升高（变频器/开关电源占比大）取 0.7~0.9 | 填错 ⇒ 低档 ΔIh 维与实测不符（这不是主判据，但会拖 D²） |

---

#### H.30.3 检测侧公共项（算法列表**上方**那几个）

| 参数 | 默认 | 怎么定 | 与画像的关系 |
|---|---|---|---|
| **检测量 quantity** | auto | **必须＝画像的 quantity**（P 口径对 P 口径） | 不一致 ⇒ 该画像不运行（状态栏报错） |
| **周波窗长 window_cycles** | 300 | ≥ `need`（见 H.30.2 公式），否则引擎自动扩并提示 | 只影响缓存/延迟，不改判据 |
| **最小事件间隔 min_gap_cycles** | 10 | 同一算法同一设备两次事件的最小间隔（去重）；密集设备可降到 2~5 | **画像匹配也吃这个间隔**（`last_end + gap` 之后的候选才落事件） |
| **事件落盘 save** | 勾 | 交付验收建议勾上（`output/nilm/nilm_events_<日期>.csv`） | 对账要用 |
| **自适应算法参数 auto_params** | 不勾 | **与画像匹配无关**（只推导 6 种标量算法的参数） | 勾不勾都不影响 profile 行 |
| **相对容差 rel_tol_pct / 相对最小幅值 min_delta_pct** | 1.0 / 0.0 | 同上，**只作用于 6 种标量算法** | 不影响 profile |

---

#### H.30.4 检测侧算法项：「设备画像匹配」14 个参数

> 界面：负荷辨识事件 → 算法列表 → 勾选 **「设备画像匹配」** → 展开 14 个输入框 + 1 个「画像文件路径」文本框 + 2 个只读项（检测对象固定 `total`、检测量随画像文件）。

##### (1) 总开关与画像

| 参数 | 默认 | 作用（代码行为） | 怎么定 / 调错的后果 |
|---|---|---|---|
| `enabled` | **0（关）** | 关＝完全不检测；开＝按 `profile_path` 逐个画像评估 | 交付前才打开；调试时可先只挂 1 份基准画像 |
| `profile_path` | 空 | `;` 分隔的画像路径（相对仓库根），最多 **8 份**；改路径后按 文件+mtime 自动重载 | 空 ⇒ 状态行"未加载画像"；超过 8 份只取前 8；**派生网格的路径串**就贴这里 |

##### (2) 候选生不生成（决定"看不看得见"）

| 参数 | 默认 | 作用（代码行为） | 怎么定 |
|---|---|---|---|
| `k_sigma` | **4.0** | 候选门槛＝`max(min_d, k_sigma × 前窗标准差)`；前窗噪声大时抬高门槛 | 现场噪声大/数据毛刺多 → 5~6；明明有台阶却成不了候选 → 降到 3（代价：假候选变多，靠 D² 再筛） |
| `min_stage` | **0.5** | 候选门槛的第二项＝`min_stage × 画像幅值`（`min(启动/停止两组的幅值)`） | 单档设备 0.5；**已知有低档（0.35× 那种）→ 0.3~0.35，或挂派生网格**；调到 0.2 以下会把 1/5 档的噪声当候选 |

> **实测边界**：`min_stage=0.5` 时 35 % 档（0.35×）**连候选都不生成**——事件表里什么都没有，而不是"报了被拒"。这是最容易被误判成"设备没启动"的一类漏报。

##### (3) 判"像不像"（决定"认不认"）

| 参数 | 默认 | 作用（代码行为） | 怎么定 |
|---|---|---|---|
| `d2_max` | **9.0** | 每维平均 D² 上限：`D²/维 > 9` ⇒ 标记 `d2_exceeds`，**必拒** | 等价"平均 \|z\| ≤ 3"。9 较宽松（对应 conf ≥ 0.011，真正卡人的是 `min_confidence`）；要更严 6~7 |
| `min_confidence` | **0.3** | `conf = exp(−D²/2d) × 轨迹罚`，`conf < 0.3` ⇒ 拒 | 0.3 ⇔ `D²/维 ≤ 2.41`。**不要低于 0.3**（低档 conf 天然 0.4~0.6，压到 0.2 会连真命中一起收）；误报多时 0.35~0.45，注意低档会先掉 |
| `margin` | **1.5** | 次优方向 D² / 最优方向 D²；< 1.5 ⇒ 打 `ambiguous_direction` 标志（仍可能 accepted，但状态变 `low_confidence`） | 启停两侧幅值接近的设备（如泵开/关几乎对称）会出现；一般保持 1.5，误方向多时提到 2.0 |
| `lambda_rel` | **0.02** | 协方差收缩：`var += λ·median(var)`（跨量纲中位数） | **0.02 是 v0.99.29 的推荐值**；0.1（旧默认）会把 `peak_ratio` 有效 σ 放大 **4.03×**、`d_ih` 1.25×（第 179 轮实测）；调小更严但各维被最紧的维支配 |

##### (4) 方向与相序

| 参数 | 默认 | 作用 | 怎么定 |
|---|---|---|---|
| `state_check` | **1** | 设备状态机：OFF→START / ON→STOP 合理；否则 `conf × 0.5` + `state_mismatch` 标志 | 单台设备在总线上跑 → 保持 1；多台同类设备混在一起、或数据分段拼接导致状态未知 → 0 |
| `phase_map` | **1（ABC）** | 总线三相 ↔ 设备三相的对应关系：1 ABC / 2 ACB / 3 BAC / 4 BCA / 5 CAB / 6 CBA / **0=自动试 6 种取最小 D²** | 两侧相别标注一致 → 1；不确定 → **0 自动**（代价：候选评估 ×6，且只在非 ABC 时记 `phase_map_x` 标志）；只有 ΔIa/ΔIb/ΔIc 三维受影响，ΔP/ΔQ/持续/峰值比不受影响 |

##### (5) 窗口几何（找候选用，不改变特征口径）

| 参数 | 默认 | 作用 | 怎么定 |
|---|---|---|---|
| `max_scale` | **8** | 候选搜索的前后窗依次 ×1、×2、×4 … ×8（**只用于找候选**，特征永远按画像自己的 pre/post 量） | 慢斜坡设备要它（否则 1 s 窗里只看得到全幅的 1/8）；快事件设 1~2。**注意它会把 need 放大到 ×max_scale**（H.30.2） |
| `min_scale` | **0.25** | 细尺度：前后窗 ÷2、÷4（最短 10 周波），用于**相邻 60 s 内的多事件**不被合并成一个 | 一般保持 0.25；`1`＝不用细尺度（事件稀疏时省算力） |

##### (6) 档位策略（多档位设备才动）

| 参数 | 默认 | 作用 | 怎么定 |
|---|---|---|---|
| `stage_free` | **0** | 1＝档位自由匹配：每个候选先解出"这是画像档位的几倍"（`stage_scale`），再算**形状**残差；0＝固定档位 | **与派生网格二选一**（同开会一次启停被 4~5 份各报一次，实测 6 → 26 条）；连续变频用 1，档位离散用网格 + 0 |
| `min_stage` | 0.5 | 同 (2)，档位自由时建议 **0.2~0.3**（否则低档连候选都没有） | — |
| `stage_min_scale` / `stage_max_scale` | **0.2 / 3.0** | 解出的档位倍数夹在这个范围 | 设备最低档/录到档 ≥0.2、最高档/录到档 ≤3.0 就保持；超出范围要加画像 |
| `stage_dim_max` | **9.0** | **单维否决**：任一维 D² 贡献 > 9（即 \|z\| > 3）就拒；只在 `stage_free=1` 时生效，0＝关 | **档位自由必须留着它**：自由参数会把平均 D² 压低（实测 16:44:05 由 15.0 → 7.8），没有单维否决时"ΔIh 只有 0.4× 的假负荷"以 conf 0.396 被收（第 180 轮实测）|

---

#### H.30.5 三套照抄的预设

| 参数 | 🟢 保守（先上线、宁可漏） | 🔵 标准（默认，推荐起点） | 🟡 宽松（排查漏报时临时用） |
|---|---|---|---|
| `enabled` | 1 | 1 | 1 |
| `profile_path` | 单份基准画像 | 基准 + 网格（3 份） | 基准 + 网格（5 份）或 `stage_free=1` |
| `d2_max` | 7.0 | 9.0 | 9.0 |
| `min_confidence` | 0.4 | **0.3** | 0.3 |
| `k_sigma` | 5.0 | 4.0 | 3.0 |
| `margin` | 1.5 | 1.5 | 1.5 |
| `lambda_rel` | 0.02 | **0.02** | 0.02 |
| `state_check` | 1 | 1 | 1 |
| `phase_map` | 1（已知相序） | 1 或 0（不确定就 0） | 0 |
| `max_scale` | 2 | 2（快事件）/ 8（慢启停） | 8 |
| `min_scale` | 0.25 | 0.25 | 0.5 |
| `stage_free` | 0 | 0 | 0（或 1，二选一） |
| `min_stage` | 0.5 | 0.5（网格）/ 0.3（无网格） | 0.3 |
| `stage_dim_max` | 9.0 | 9.0 | 9.0 |

> 两例的实测落点：例 1（3p4w / P）用 🔵 ⇒ 6/6、conf 0.9916 / 0.9562 / 0.4075、别的设备 0；例 2（3p3w / I）+ 5 份网格用 🔵 ⇒ 6/6、0.993 / 0.996 / 0.576、别的设备全拒。**照抄 🔵 就够，别一上来就调。**

---

#### H.30.6 配参顺序（六步，每步只看一个数）

| 步 | 做什么 | 只看这个数 | 不达标怎么办 |
|---|---|---|---|
| 1 | 提取侧：接线 / PT·CT / 检测量 / 时标填对，**手算一次幅值**核对 μ | μΔIa（或 μΔP）与手算差 <5 % | 差 3× / 250× ⇒ 回 H.30.1 改基准配置 |
| 2 | 提取侧：定 `pre/post` 与标签 | 画像打印的**可接受区间**（应 0.6~1.4×）与 `min_d` | 区间过宽（>0.5~2×）⇒ 混档了，拆开重提 |
| 3 | 检测侧：挂画像、勾 enabled、其余全默认 | 状态行"已加载 N 份画像"、检测量一致 | 报"口径不可比" ⇒ 改 `quantity` |
| 4 | 跑一段已知数据，看**候选** | 事件表里有没有"该报没报" | 整行没有 ⇒ `min_stage` 0.5→0.3 或加派生网格；有候选但 `d2_exceeds` ⇒ 提取侧窗口几何/H.28.5 |
| 5 | 看**误报** | 别的设备被认了几条 | 缩网格（顶档别超过铭牌最高档）；再考虑 `min_confidence` 0.35~0.45 |
| 6 | 对账并落表（H.29 的 14 条） | `nilm_check` 的 `profile` 行 | 命中 100 % / 漏 0 / 误 0 才签字 |

**改参数纪律**：一次只改一个，记录"改前 → 改后 + 结果"；改完先重跑**同一段**数据（别换数据，否则分不清是参数还是数据）。

---

#### H.30.7 现象 → 根因 → 改哪一项

| 现象（事件表 / 状态行 / 候选 CSV） | 根因 | 改哪一项 |
|---|---|---|
| 状态行："画像按 W 口径构建，本侧检测量为 I…未运行" | 检测量不一致 | 检测侧 `quantity` 或重提画像 |
| "两侧 PT 变比不同 ⇒ 本侧 ΔI 是画像的 250 倍" 且**一条都不报** | 一侧填了 PT/CT、另一侧没填 | 提取侧基准配置（H.30.1） |
| 事件表里该档**整行都没有** | `min_stage × 画像幅值` 高于该档 | `min_stage` 0.5→0.3，或加派生网格 |
| 有候选、`status=rejected`、`flags=d2_exceeds` | 特征不像（窗口几何错 / 混档 / 他负荷） | 先看 `contrib` 哪一维最大：ΔQ ⇒ `q_mode`；ΔIh ⇒ 谐波；全维都大 ⇒ 重提画像 |
| `flags=sign_flip` | 前后窗跨过了相邻的另一次动作 | 减 `post`、开 `min_scale`、或加 `min_gap_cycles` |
| `flags=state_mismatch` 且方向偶尔反 | 多台同类设备 / 状态机误判 | `state_check=0` |
| `flags=phase_map_ACB`（自动相序非 ABC） | 两侧相别标注不同 | 固定 `phase_map=2`（省 6× 计算） |
| 同一台阶**两条事件**（两份画像） | 网格太密 | 相邻倍数差 ≥1.3~1.9；或改精确派生 |
| 别的设备被认（如 1500 W 落进 @388%） | 网格顶档覆盖到别人 | 减份数 / 顶档不超过铭牌最高档 |
| 低档 conf 只有 0.4~0.6 | 幅值小、绝对下限占比大（正常） | **不要改**；要提升只能补录低档数据 |
| 状态行："需要约 891 周波…已自动扩窗" | `post×max_scale` 大于 `window_cycles` | 降 `max_scale` 或重提更小的 `post` |
| 事件时刻比实际晚 1 s 左右 | 检出延迟＝`post` 周波 | 正常；要更快就减 `post`（但启动过程要能收敛） |

---

#### H.30.8 一页纸（贴工位）

```
提取侧（数据处理 → 设备画像提取）
  基准配置：接线 3p4w/3p3w · 3p3w 勾重构 · PT/CT 与总线侧同一体系 · 检测量 P/I 与总线侧一致
  ② 标签（有真值就贴，容差 2 s）｜无标签靠自动定位，合并 10 s
  ③ 前窗 10 / 后窗 50（慢启停 200~400）←← 这两个数总线侧会直接用，改不了
  ④ 档位：知道倍数就精确派生（0.35,0.55,0.75,1.0）；不知道用 --derive-grid 3|5

检测侧（负荷辨识事件 → 设备画像匹配）
  勾 enabled · 画像文件路径贴 ; 串
  默认九件套：d2_max 9 · min_confidence 0.3 · k_sigma 4 · margin 1.5 · lambda_rel 0.02
             · state_check 1 · phase_map 1(或 0) · max_scale 2(快)/8(慢) · min_scale 0.25
  档位：stage_free 0 + min_stage 0.5（网格）；或 stage_free 1 + min_stage 0.3 + stage_dim_max 9（二选一）

三条硬规矩
  ① 检测量 / 接线 / PT·CT 三样，两侧必须同一体系（否则永远匹配不上）
  ② 相对容差、最小幅值、自适应参数 → 对画像匹配无效，别在这上面调
  ③ 一次只改一个参数，改完对同一段数据重跑对账
```
