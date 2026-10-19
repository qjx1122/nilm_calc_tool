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

**全局参数**（`nilm.*`）：

| 参数 | 含义 | 建议 |
|---|---|---|
| `channels` | 检测对象：`total` 三相总有功 / `A` `B` `C` 分相 | 三相设备用 `total`；单相设备用它所在的相 |
| `window_cycles` | 算法只看最近多少个点（默认 300 = 6 s） | ≥ 2 × 暂态周波数 + 100；电机软启动 2 s → ≥ 300 |
| `min_gap_cycles` | 同一算法两次事件最小间隔（默认 10 = 0.2 s） | 重复报 → 调大；快速连续投切 → 调小 |
| `rel_tol_pct` | 容差至少是基荷的百分之几（默认 1.0） | 基荷大、设备小时降到 0.1~0.3；`nilm_tune` 会给 |
| `min_delta_pct` | 最小台阶至少是基荷的百分之几（默认 0） | 一般用 `nilm_tune` 给的值 |

**检测 ≠ 归属（再强调一次）**：6 种算法在线只做"事件检测"，界面「负荷辨识」页的事件表里**不会**写是哪台设备；把事件归到设备是 `nilm_check.py` 用幅值带做的离线辅助。总线上多台设备时，线上看到的事件数 = 所有设备的开关数之和，这是正常的。

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
# 5 定稿 + 推送
.\.venv\Scripts\python.exe tools\nilm_replay.py --file data\dev_onoff.csv --config configs\default.json --params output\tune.json --set threshold.min_delta_w=100000 --save-config output\site.json --out output\replay_events.csv
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
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\dev_events_i.csv --truth data\truth.csv --tol-s 1
.\.venv\Scripts\python.exe tools\nilm_check.py --events output\bus_events_i.csv --truth data\truth_bus.csv --mag-a 25 --mag-tol-pct 30
#   --signature-from 同样可用：从设备侧命中事件取 |ΔI| 均值作指纹
# 4 定稿：同 §7；界面「检测参数」里 A 口径一列会点亮、W 一列灰显（quantity_effective = i）
```

**建议值是怎么算的**：与附录 E 完全相同的规则，只是把 P 序列换成 I 序列——`settle_tol_a = 5 周波极差 95 分位 × 1.2`、
`min_delta_a = max(额定电流/2, 6σ)`、CUSUM `drift_a = min_delta_a/4`、`threshold_a = 2×(min_delta_a − drift_a)`、GLR `noise_a = σ`、
`steady_state.tol_a = 10 周波极差 95 分位 × 1.2`。`rel_tol_pct / min_delta_pct` 对 |I| 中位数折算，与绝对值取较大者生效。

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
