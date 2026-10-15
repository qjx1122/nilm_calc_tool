# README.md — nilm_calc_tool（电力系统各类电气量计算工具）

> 台账文件（BOOTSTRAP.md v2.2）：安装与环境 / 运行命令 / 数据目录 / 配置结构 / 输出产物 / 生产推荐流程。
> **当前状态：v0.11（2026-10-13）**——软件已实现并在沙盒跑通（算法核心 + 4 类数据源 + 计算引擎 + 电能质量事件 + **负荷辨识事件检测（6 算法）** + 离线重采样 + 列映射 / 时标时区开关 + CLI + Web 界面 + 257 项测试 + 11 项验证工具）。
> 状态标注：✅已确认（有代码 / 实录 / 官方来源佐证）｜🔶待确认（占位或推断，需用户回填）｜❌已废弃（不删行，只翻状态）
> **本文所有 ✅ 均为沙盒实录：Linux 6.1.158+ / CPython 3.11.2 / numpy 2.4.6，采集时间 2026-10-10。**
> **Windows 命令、真实现场数据、生产部署三项尚未在用户环境验证，一律标 🔶，请按 `REPORT_TEST.md`「T-002 本地部署与验收执行包」逐条回填。**

---

## 0. 30 秒快速开始

```bash
# 1) 取代码（当前代码在 session 分支上；若已合并到 main 则可省略 -b）
git clone -b arena/82e34fb8-nilm-calc-tool https://github.com/qjx1122/nilm_calc_tool.git
cd nilm_calc_tool

# 2) 建虚拟环境 + 装依赖
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt          # Linux / macOS ✅沙盒实录
# Windows（🔶未实测）：py -m venv .venv && .venv\Scripts\pip install -r requirements.txt

# 3) 一键算法自检（不需要任何真实数据，44 项解析解对账）
.venv/bin/python cli.py selftest
#   期望：自检项 44 个：通过 44，失败 0，通过率 100.0%，最差相对误差 1.508e-05

# 4) 启动 Web 界面（导航条 + 各电气量子界面 + 实时推送）
.venv/bin/python cli.py serve
#   期望：● 启动 Web 界面：http://0.0.0.0:8000
#   浏览器打开 http://127.0.0.1:8000 →「数据源与控制」→ 选模拟器 → 点「启动数据源」
```

> 只想跑批处理、不开浏览器：`.venv/bin/python cli.py compute --file 你的数据.csv --format table`（见 §3.2）。

---

## 1. 软件定位与验收对照

**定位**：电力系统各类电气量计算工具。输入三相电压/电流瞬时采样（6400 Hz），输出三相电压、三相电流、有功/无功/视在功率、功率因数、基波、谐波（2–50 次）、频谱等电气量；每类电气量可**分别**配置计算时间段。✅（代码 + 测试实录）

| # | 验收标准（用户原始需求） | 实现位置 | 验证方式（沙盒实录） | 状态 |
| --- | --- | --- | --- | --- |
| ① | 软件总体为电力系统各类电气量计算工具 | `elec_tool/`（算法核心）+ `app/`（Web）+ `cli.py` | `cli.py selftest` 44/44；`pytest tests/ -q` 141 passed | ✅沙盒 |
| ② | 各类电气量计算分到各子界面 | `app/static/index.html` 中 12 个 `view-*` 容器 | `tests/test_server.py::test_index_page_has_nav_and_one_subview_per_quantity` | ✅沙盒 |
| ③ | 子界面通过导航条切换 | `<nav id="navbar">` 12 个 `data-view` 按钮 + `app.js:switchView()` | 同上测试断言每个子界面都有导航入口 | ✅沙盒 |
| ④ | 输入支持实时采集数据与离线文件数据 | `elec_tool/sources/`：`csv_file`(离线)、`csv_tail`(实时追加)、`tcp`(实时流)、`simulator`(实时联调) | 实时链路 `test_realtime_simulator_streams_*`；离线链路 `test_offline_csv_end_to_end_values` | ✅沙盒（真实采集设备 🔶） |
| ⑤ | 三相电压/电流、功率因数、有功、无功、基波、谐波(2–50)、频谱；**v0.8 增：间谐波、直流偏置、事件** | `elec_tool/analysis/{rms,harmonic,power,window}.py` + `metrics.py` + `events.py` | 数值对齐解析解（`expected_values()`），见 §8；间谐波/直流/事件见 `tests/test_r9_events.py` | ✅沙盒 |
| ⑥ | 各电气量分别配置指定时间段计算 | `configs/*.json` 的 `windows.<量>.length_s/step_s`；引擎按量独立调度 | 实测：电压窗 1s→输出 6 次、谐波窗 0.2s→输出 26 次（同一份 5s 数据）；改 5s→输出 2 次、缓冲自动扩到 49280 点 | ✅沙盒 |

**代码规模**（`wc -l` 实录）：`elec_tool/` + `app/server.py` + `cli.py` = 4922 行；`app/static/`（HTML/CSS/JS）= 1318 行；`tests/` = 2006 行。

**技术栈**（沙盒实录）：Python 3.11.2、numpy 2.4.6、fastapi 0.143.0、uvicorn 0.54.0、starlette 1.7.0、pydantic 2.14.0、websockets 17.2、pytest 9.1.1、httpx 0.28.1。前端为原生 JS + canvas，**无任何 CDN/外部资源依赖**（内网可直接用，测试有断言）。

---

## 2. 本地部署（详细）

### 2.1 环境要求

| 项 | 要求 | 状态 |
| --- | --- | --- |
| 操作系统 | Linux / macOS / Windows 10+ 均可（纯 Python + 浏览器，无 GUI 依赖） | Linux ✅沙盒实录；Windows/macOS 🔶未实测 |
| Python | **实测 3.11.2**。语法层面兼容 3.9+：用 `ast.parse(feature_version=(3,9))` 扫描全部 31 个 `.py` 文件无不兼容语法，且未使用 3.10+ 专属 stdlib（`match`/`pairwise`/`KW_ONLY`/`tomllib` 等） | 3.11.2 ✅；3.9/3.10 运行时 🔶未逐版实测 |
| CPU/内存 | 单核即可跑实时（实测 6400 点/s 实时摄入，速率 6398–6400 点/s）。内存主要是环形缓冲：`容量 = ceil(最长窗长 × fs × 1.5) + max(每块点数, 64)`（且不小于 fs），按 7 通道 float64 计——实测 1s 窗 + 块 640 → 容量 10240 点 ≈ 0.55 MB；1s 窗 + 块 1280 → 10880 点；5s 窗 + 块 1280 → 49280 点 ≈ 2.7 MB。窗长变化时缓冲自动扩容并保留已有数据尾部 | ✅沙盒实录（2 核 / 3 GB 环境；公式见 `elec_tool/engine.py:LiveEngine.__init__`） |
| 浏览器 | 任一现代浏览器（Chrome/Edge/Firefox），需支持 WebSocket；不支持时前端自动降级为 1.5 s 轮询 | ✅（降级逻辑见 `app.js:startPolling`） |
| 磁盘 | 代码 + 依赖 ≈ 200 MB；结果 CSV 视时长而定（实测 5 s 数据导出 26 次结果 = 1.4 MB） | ✅沙盒实录 |
| 网络 | **运行期完全离线**（无外部服务、无 CDN、无遥测）；仅安装依赖时需要 PyPI 或内网镜像 | ✅ |

### 2.2 获取代码

```bash
git clone -b arena/82e34fb8-nilm-calc-tool https://github.com/qjx1122/nilm_calc_tool.git
cd nilm_calc_tool
```

- 无 git 或内网机器：在 GitHub 页面 `Code → Download ZIP`（选上面这个分支），解压后目录名任意。🔶（ZIP 方式未实测）
- 代码提交历史（本分支，`git log --oneline` 实录）：`880bf5f` 算法核心 → `8166743` 数据源+引擎+CLI+测试 → `b09f2a6` Web 界面+20 项 Web 测试 → `d2337ab` STATUS 决策记录。

### 2.3 创建虚拟环境

```bash
# Linux / macOS ✅沙盒实录
python3 -m venv .venv
source .venv/bin/activate            # 或不激活，直接用 ./.venv/bin/python

# Windows PowerShell / CMD（🔶未实测，按 Python 官方 venv 文档写法）
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1           # PowerShell；CMD 用 .venv\Scripts\activate.bat
```

> **必须用虚拟环境**：Debian/Ubuntu 系统 Python 受 PEP 668 保护，直接 `pip install` 会报
> `error: externally-managed-environment`（沙盒实测踩过）。若企业策略禁止 venv，可加 `--break-system-packages`，但不推荐。

### 2.4 安装依赖

依赖声明见 `requirements.txt`，分三层，可按需裁剪：

| 层 | 包 | 用途 | 能否省略 |
| --- | --- | --- | --- |
| 算法核心 | `numpy>=1.24` | 全部电气量计算 | ❌ 必需 |
| Web 界面 | `fastapi>=0.110`、`uvicorn[standard]>=0.27`（Windows 自动降级为 `uvicorn` + `websockets`） | 子界面 + WebSocket 实时推送 | 可省（只用 CLI 时） |
| 开发验证 | `pytest>=8.0`、`httpx>=0.27` | 跑 142 项测试（httpx 是 FastAPI TestClient 依赖） | 可省（生产机） |

**(a) 在线安装（有 PyPI 或内网镜像）** ✅沙盒实录

```bash
.venv/bin/pip install -r requirements.txt
# 内网镜像：.venv/bin/pip install -r requirements.txt -i http://<内网镜像>/simple --trusted-host <内网镜像>   🔶未实测
```

**(b) 内网离线安装 —— Linux 目标机** ✅沙盒实录（全流程实测通过）

```bash
# 在能联网的同架构机器上下载 wheel（实测 29 个包 / 28 MB）
.venv/bin/pip download -r requirements.txt -d ./wheels

# 拷贝 wheels/ 与代码到目标机后，完全无网安装
python3 -m venv .venv
.venv/bin/pip install --no-index --find-links ./wheels -r requirements.txt

# 验证（实测输出）
.venv/bin/python cli.py selftest      # → 44/44 通过，最差相对误差 1.508e-05
.venv/bin/python -m pytest tests/ -q  # → 141 passed, 1 skipped
```

**(c) 内网离线安装 —— Windows 目标机** ✅下载侧实录 / 🔶安装侧未实测

wheel 与平台绑定，必须在打包时指定目标平台。**坑（实测踩过）**：直接用 `-r requirements.txt` 跨平台下载会失败——
`uvicorn[standard]` 的 extra 会拉 `uvloop`，而 uvloop 没有 Windows wheel，pip 报 `ResolutionImpossible`（补 `--implementation cp --abi cp311` 也无效）。
解决办法是**显式列包**、不带 `[standard]` extra：

```bash
# 在联网机器上（实测得到 24 个包 / 18 MB，含 numpy-2.4.6-cp311-cp311-win_amd64.whl）
pip download --platform win_amd64 --python-version 3.11 --implementation cp --abi cp311 \
    --only-binary=:all: -d ./wheels_win \
    numpy fastapi uvicorn websockets pytest httpx

# 目标 Windows 机器上（🔶未实测，命令为 pip 官方离线用法）
py -3.11 -m venv .venv
.venv\Scripts\pip install --no-index --find-links .\wheels_win numpy fastapi uvicorn websockets pytest httpx
```

> `requirements.txt` 已用 PEP 508 平台标记分流：Windows 上联网 `pip install -r requirements.txt` 会自动选 `uvicorn` + `websockets`（不拉 uvloop）。该分流逻辑在 Linux 侧实测生效，**Windows 侧未实测 🔶**。

**(d) 最小安装（只用 CLI，不要 Web）**

```bash
.venv/bin/pip install numpy          # 之后 cli.py 除 serve 外的 6 个子命令都能用
.venv/bin/python cli.py serve        # 会明确报错并给出安装提示，退出码 2：
#   ✗ 未安装 Web 依赖：pip install fastapi 'uvicorn[standard]'
```

### 2.5 安装验证（5 条命令，逐条对照期望输出）

```bash
.venv/bin/python cli.py --version
#   elec_tool 0.1.0                                                     ✅实录

.venv/bin/python -c "import numpy, elec_tool; print(numpy.__version__)"
#   2.4.6                                                               ✅实录

.venv/bin/python cli.py selftest | tail -2
#   自检项 44 个：通过 44，失败 0，通过率 100.0%，最差相对误差 1.508e-05，耗时 0.32s
#   工况：fs=6400.0Hz  f=50.0Hz  PT=100.0  CT=15.0  窗长=1.0s            ✅实录

.venv/bin/python cli.py gen-sample --out data/sample_6400hz.csv --duration 5 \
    --harmonics "3:0.08,5:0.06,7:0.03,11:0.015,13:0.01"
#   时间戳格式=epoch  编码=utf-8
#   基波=50.0Hz  二次侧 U1=57.735V(相)  I1=5.000A  φ=30°  噪声比=0.001
#   一次侧期望：U1=5773.5V  I1=75.0A  （PT=100.0, CT=15.0）              ✅实录（生成 2.5 MB / 32000 行）

.venv/bin/python -m pytest tests/ -q
#   141 passed, 1 skipped in ~55s                                       ✅实录
#   唯一 skip：tests/test_cli.py:43「60Hz 下 50 次谐波=3000Hz，接近 6400Hz 的 Nyquist(3200Hz)，另行测试」
```

> 以上 5 条全绿即代表**本地环境安装成功且算法口径与解析解一致**，无需真实数据。任何一条不符，请先看 §2.7 / §3.5 排错表，再把实录贴回 `REPORT_TEST.md` T-002。

### 2.6 目录结构

```
nilm_calc_tool/
├── cli.py                     # 命令行入口（7 个子命令）
├── requirements.txt           # 依赖声明（含平台标记）
├── configs/
│   ├── default.json           # ✅出厂配置模板（入库，界面操作不会污染它）
│   └── runtime.json           # 界面里保存的配置（自动生成，已 gitignore）
├── elec_tool/                 # 算法核心包（可独立当库用，只依赖 numpy）
│   ├── config.py              #   配置模型 + 校验 + 列名映射
│   ├── blocks.py              #   SampleBlock / FrameBuffer（环形缓冲）
│   ├── scaling.py             #   PT/CT 变比、一次/二次值
│   ├── analysis/
│   │   ├── window.py          #   窗切分（整周期策略）、频率估计与精修
│   │   ├── rms.py             #   RMS / 相量 / 序分量 / 逐周期
│   │   ├── harmonic.py        #   谐波 2–50 次、THD、HR、间谐波
│   │   └── power.py           #   P/Q/S/PF/DPF、四象限、零线电流
│   ├── metrics.py             #   七类电气量的编排与结果对象
│   ├── engine.py              #   LiveEngine：各量独立窗调度（需求⑥）
│   ├── sources/               #   csv_file / csv_tail / tcp / simulator + 解析
│   └── selftest.py            #   44 项解析解自检（合成信号 + 期望值）
├── app/
│   ├── server.py              # FastAPI + WebSocket + 引擎后台线程
│   └── static/                # index.html / style.css / app.js（原生 canvas，无外链）
├── tools/                     # 联调与验证工具（无真实硬件时扮演采集侧）
│   ├── tcp_feeder.py          #   TCP 喂数器：text_csv / binary 两种帧，可指定 struct_fmt
│   ├── csv_appender.py        #   CSV 追加喂数器：按用户列格式边写边追加，可分片轮转
│   ├── verify_sources.py      #   库级四源验证：自动拉起上面两个，输出与解析解的对账表
│   ├── ui_dropdown_check.cjs  #   Web 下拉框端到端检查（jsdom 驱动真实页面，打真实服务端）
│   ├── ui_r6_check.cjs        #   第 6 轮界面检查：自定义播放时间 / 24h 曲线 / 保存曲线勾选（PASS 30）
│   └── ui_r7_check.cjs        #   第 7 轮界面检查：实时落盘 / 播放起点 / 曲线悬停取值（PASS 39）
├── data/                      # 输入 CSV（gitignore，不入库）
├── output/                    # 导出结果（gitignore）
├── tests/                     # 205 项测试（单元 + 端到端 + Web 层 + 前端契约 + 工具防腐 + 第 6/7 轮功能）
└── 台账：BOOTSTRAP/ROLE/STATUS/README/REPORT/REPORT_TEST/NILM_DATA_DICT/session/
```

### 2.7 安装期常见故障

| 现象 | 原因 | 处理 | 状态 |
| --- | --- | --- | --- |
| `error: externally-managed-environment` | Debian/Ubuntu PEP 668 保护系统 Python | 用 venv（§2.3） | ✅沙盒实测 |
| `ResolutionImpossible ... uvicorn[standard]` | 跨平台下载时 uvloop 无 Windows wheel | 用 §2.4(c) 的显式列包命令 | ✅沙盒实测 |
| `ModuleNotFoundError: No module named 'fastapi'` | 只装了核心依赖却执行 `serve` | `pip install fastapi "uvicorn[standard]"`；或改用 CLI 子命令 | ✅（cli.py 会主动提示，退出码 2） |
| `ModuleNotFoundError: No module named 'httpx'` | 跑 `tests/test_server.py` 缺 TestClient 依赖 | `pip install httpx`（不装则该模块自动 skip，不影响其余测试） | ✅沙盒实测 |
| `pip download` 得到目标机装不上的 wheel | wheel 与平台/Python 版本绑定 | 打包时指定 `--platform/--python-version/--implementation/--abi`，且与目标机 Python 小版本一致 | ✅沙盒实测 |
| Windows 上 `python` 指向 Microsoft Store 别名 | 未装真实 Python | 用 `py -3.11` 或在「应用执行别名」中关闭 | 🔶未实测（常见环境问题的通用处置） |

---

## 3. 运行说明（详细）

三种运行方式，按需选一种：**Web 界面**（人工看数、验收演示）、**CLI**（脚本/批处理/无浏览器）、**Python 库**（嵌入既有系统）。三者共用同一套算法核心与配置文件，结果口径完全一致。

### 3.1 方式一：Web 界面（推荐）

**启动**

```bash
.venv/bin/python cli.py serve                                  # 默认 0.0.0.0:8000 ✅沙盒实录
.venv/bin/python cli.py serve --host 127.0.0.1 --port 8001     # 只监听本机 / 换端口 ✅沙盒实录
.venv/bin/python cli.py serve --pt 100 --ct 15 --set-window voltage=5 --adaptive   # 启动时覆盖配置 ✅沙盒实录

# 等价写法（不经 cli.py，直接用 uvicorn；此时 --pt 之类的覆盖需改用环境变量或配置文件）
.venv/bin/python -m uvicorn app.server:app --host 0.0.0.0 --port 8000
```

启动后终端打印（实录）：

```
● 启动 Web 界面：http://0.0.0.0:8000  （配置：fs=6400.0Hz PT=100.0 CT=15.0 source=simulator）
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**访问**

- 本机：`http://127.0.0.1:8000`
- 局域网其它机器：`http://<部署机 IP>:8000`（默认已绑 `0.0.0.0`；需在防火墙放行该端口 🔶未实测）
- 反向代理（nginx 等）：必须转发 WebSocket 升级头，否则前端自动降级为 1.5 s 轮询（功能不受影响，实时性下降）：
  ```nginx
  location / { proxy_pass http://127.0.0.1:8000;
               proxy_http_version 1.1;
               proxy_set_header Upgrade $http_upgrade;
               proxy_set_header Connection "upgrade";
               proxy_read_timeout 3600s; }        # 🔶配置未实测，为 nginx 官方 WebSocket 代理写法
  ```

**`serve` 参数与环境变量**

| 名称 | 默认 | 作用 | 状态 |
| --- | --- | --- | --- |
| `--host` | `0.0.0.0` | 监听地址（`127.0.0.1` = 只允许本机） | ✅ |
| `--port` | `8000` | 监听端口 | ✅ |
| `--log-level` | `warning` | uvicorn 日志级别（排障时改 `info` 可看到每个请求） | ✅ |
| `--config` | `configs/default.json` | 配置文件路径 | ✅ |
| `--pt/--ct/--fs/--freq/--hmax/--adaptive/--no-scale/--set-window/--apparent/--reactive` | 见 §6 | 启动时覆盖配置（通过 `ELEC_TOOL_CONFIG` 传给服务，实测 `/api/state` 回读一致） | ✅沙盒实录 |
| 环境变量 `ELEC_TOOL_AUTOSTART` | 空 | 非空则启动即自动跑引擎（否则需在界面点「启动数据源」） | ✅沙盒实录 |
| 环境变量 `ELEC_TOOL_CONFIG_PATH` | 空 | 强制指定配置文件（加载与保存都用它） | ✅ |
| 环境变量 `ELEC_TOOL_PERSIST_CONFIG` | `1` | 置 `0` 则界面改动只留在内存，不落盘 | ✅ |
| 环境变量 `ELEC_TOOL_CONFIG` | 空 | 直接传整份配置 JSON（`cli.py serve` 内部用这个实现参数覆盖） | ✅ |

**界面导览（左侧导航条 12 项，`index.html` 实录）**

| 导航项 | 子界面内容 |
| --- | --- |
| 📊 总览面板 | 七类量关键值卡片 + 波形缩略 + 全局告警汇总 |
| 🔌 数据源与控制 | 选数据源（离线文件 / 文件追加 / TCP / 模拟器）、路径探查与目录列举、csv_tail 两个开关（从末尾开始 / 跟目录最新文件）、TCP 主机端口帧格式、每块点数、模拟器速率、启动停止、PT/CT、fs/f_nom、谐波上限、功率口径、保存配置、数据源状态摘要 |
| 🔆 三相电压 | 相电压/线电压 RMS、序分量与不平衡度、零序、逐周期表、趋势图 |
| 🔌 三相电流 | 相电流 RMS、零线电流、波峰系数、序分量、趋势图 |
| ⚙️ 有功/无功/视在 | P/Q/S（总分相）、四象限图、残差校验 `p_residual_pct` |
| 📐 功率因数 | PF/DPF、象限判定与含义、趋势图 |
| 〰️ 基波 | 频率估计（含方法与来源）、U1/I1、相序、初相角 |
| 📶 谐波 (2–50 次) | THD_U/THD_I、各次含有率柱状图、逐次 RMS、间谐波占比 |
| 🌈 频谱 | 0–3200 Hz 幅值谱（RMS/dB 切换、通道切换、频率上限）、主峰与分辨率 |
| ⏱ 窗口配置（需求⑥） | 逐量设置窗长/步长/截断策略/窗函数/去直流，并显示本次运行各量实际输出次数 |
| 💾 导出与日志 | 导出 CSV/JSON、告警与数据缺口日志、原始结果 JSON 预览 |
| ✅ 算法自检 | 一键跑 44 项解析解对账，可改 fs/f/PT/CT/窗长，显示运行环境（Python/OS/numpy） |

**数据源面板：4 种输入方式的联动、空值语义与两个保存入口（✅沙盒实录）**

「数据源输入方式」下拉框 4 项与后端 `SOURCE_KINDS` 一一对应；选中后界面**只放开与该源相关的字段**，其余置灰禁用（填了也不生效，置灰是为了不让人白填）：

| 选中 | 可编辑 | 置灰 |
| --- | --- | --- |
| `csv_file` 离线文件 | CSV 路径、每块点数 | 主机 / 端口 / 帧格式 / struct 两项 / 速率 / csv_tail 两开关 |
| `csv_tail` 文件追加 | CSV 路径（**文件或目录**）、从文件末尾开始、跟目录最新文件、每块点数 | 主机 / 端口 / 帧格式 / struct 两项 / 速率 |
| `tcp` TCP 客户端 | 主机、端口、帧格式、每块点数；帧格式选 `binary` 时才放开 struct 格式与字段顺序 | CSV 路径 / 速率 / csv_tail 两开关 |
| `simulator` 模拟器 | 速率倍数、每块点数 | CSV 路径 / 主机 / 端口 / 帧格式 / struct 两项 / csv_tail 两开关 |

下拉框下方有一行**随选择切换的填写说明**（`#src-hint`）：例如选 `tcp` 会写明 `text_csv`（每行一条 CSV，可带中文表头）与 `binary`（定长帧，默认 `<7d`＝7 个 double 小端＝56 字节/帧）的区别；选 `csv_tail` 会写明目录模式与「从文件末尾开始」的含义。

**两个保存入口的服务端语义不同，别混用**：

| 按钮 | 请求 | 服务端吃什么 | 用于 |
| --- | --- | --- | --- |
| 保存配置（热更新） | `PUT /api/config` | **深合并**：只更新送出的键，未送的键保留原值 | PT/CT、电压输入口径（相/线）、fs/f_nom、谐波上限、视在/无功口径、数据源默认值 |
| 启动数据源 | `POST /api/engine/start` | 只吃 `source` 白名单键（`kind/path/host/port/frame/block_samples/poll_interval_s/tail_from_end/sim_speed/watch_dir_newest/struct_fmt/struct_fields`）与 `windows` | 换源、换路径、立即开跑 |

> ⚠️ 改了 **PT/CT 或功率口径**后必须点「保存配置（热更新）」：这些键不在 `/api/engine/start` 的白名单内，点「启动数据源」会被服务端**静默忽略**（界面已在提示里指明该点哪个按钮）。

**空输入框＝沿用服务端已保存的值，不是清空**：留空的文本框、非正数或非数字的数字框都不会进入请求体（`PUT` 深合并，省略即保留）。两个实测理由：① 空 `path` 送出去会被拒 `HTTP 400 source.kind=csv_file 需要 source.path（文件或目录路径）`；② 空数字框若按 `+'' === 0` 送出会得到 `HTTP 400 sampling.fs 必须 > 0（当前 0）`。被跳过的字段名会写进保存成功的提示，不静默。

**正在编辑时不会被实时推送打断**：快量每 0.2 s 推一次结果并触发界面刷新；一旦你在本页动过任何控件，自动回填立即暂停并显示「⚠ 界面有未保存的修改…」。点「刷新」＝丢弃未保存修改、按服务端配置重新回填；保存或启动成功后自动恢复回填。

**回归方式**（任选其一）：

```bash
# ① 端到端自动检查：需 node ≥18 + jsdom（npm install jsdom --prefix /tmp/uitest，或用 JSDOM_DIR 指定安装目录）
#    脚本用 jsdom 加载真实 index.html/app.js 并打真实服务端，还会自己在 9000 端口拉起 TCP 喂数器
JSDOM_DIR=/tmp/uitest node tools/ui_dropdown_check.cjs http://127.0.0.1:8000
# ✅沙盒实录：PASS 74 / FAIL 0 —— 4 种源逐个选中→联动禁用→载荷裁剪→服务端真跑起来
#    （csv_file 读完即 finished、csv_tail/tcp/simulator running=true）、binary 帧字段联动、
#    脏值保护（推送后 kind 与半截路径不变）、3 个口径下拉框 PUT 后服务端回显、频谱 3 个下拉框触发重绘

# ② 前端契约静态检查：随 pytest 一起跑，不需要 node/浏览器
.venv/bin/python -m pytest tests/test_web_ui.py -q          # ✅沙盒实录：14 passed
```

没有 node 时的**手工点检清单**（6 步，含期望值）：

| # | 操作 | 期望 |
| --- | --- | --- |
| 1 | 打开页面 → 点左侧「🔌 数据源与控制」 | PT=100、CT=15、fs=6400、主机=127.0.0.1 等**均已回填**（不是空框） |
| 2 | 「数据源输入方式」依次选 4 项 | 每次切换后无关字段**置灰**，下方说明文字随之变化 |
| 3 | 选 `tcp` → 帧格式选 `binary` | struct 格式/字段顺序两框由灰变可编辑；切回 `text_csv` 又变灰 |
| 4 | 选 `simulator` → 速率填 4 → 点「启动数据源」 | 右上状态变运行中；顶部提示「已启动数据源：simulator」 |
| 5 | 在路径框打半截字，**不点任何按钮**，等 2 s | 半截字**不被清掉**、下拉框不被改回，出现「⚠ 界面有未保存的修改」 |
| 6 | 电压输入口径改「线电压」→ 点「保存配置（热更新）」 | 提示保存成功；刷新页面后仍是「线电压」（`GET /api/config` 回显 `line`） |

**停止与常驻**

```bash
# 前台运行：Ctrl+C 停止（会走 lifespan 关闭，停引擎线程）                              ✅
# Linux 后台常驻（🔶未实测，为标准写法）
nohup .venv/bin/python cli.py serve --port 8000 > logs/serve.log 2>&1 &

# Linux systemd（🔶未实测）：/etc/systemd/system/elec-tool.service
#   [Unit]  Description=电气量计算工具   After=network.target
#   [Service] WorkingDirectory=/opt/nilm_calc_tool
#             Environment=ELEC_TOOL_AUTOSTART=1
#             ExecStart=/opt/nilm_calc_tool/.venv/bin/python cli.py serve --host 0.0.0.0 --port 8000
#             Restart=always
#   [Install] WantedBy=multi-user.target
#   → systemctl daemon-reload && systemctl enable --now elec-tool

# Windows（🔶未实测）：用 NSSM 把 `.venv\Scripts\python.exe cli.py serve` 注册成服务，
#   或「任务计划程序」→ 开机触发 → 操作填上述命令、起始于填仓库目录。
```

> 单进程单 worker 即可满足 6400 Hz 实时（实测速率 6398–6400 点/s，CPU 单核占用不高）。**不要**加 `--workers N`：引擎与历史保存在进程内存中，多 worker 会导致各 worker 数据不一致。✅（架构约束，见 `app/server.py` 的 `EngineRunner` 单例）

#### 趋势曲线＝最近 24 小时 ＋ 每条曲线可选「保存曲线数据」（v0.5）

界面共 **6 条趋势曲线**：概览页的三相电压 / 三相电流 / P·Q·S / THD，功率因数页的 PF·DPF，基波页的频率（电压/电流/功率页的「波形」与频谱页是**单窗瞬时量**，不是时间趋势，不在此列）。

| 项 | 行为 | 依据 |
| --- | --- | --- |
| 显示范围 | **最近 `output.history_hours`（默认 24）小时**的数据，按**数据时间**计（离线回放同样成立）；不足 24 h 则显示全部 | `History._trim()`：以最新一条记录的时间为基准丢弃更早的点 |
| 传输量 | 每条曲线每次最多传 1500 点；点数更多时服务端**均匀分桶、每桶保留首点＋最大值点＋最小值点**（保峰谷，不糊掉尖峰），面板标题处显示「最近 x · N 点（显示抽稀至 M）」 | `GET /api/history/{q}?max_points=1500`；43 万点抽到 1500 点实测 40 ms |
| 内存 | 每条曲线上限 `output.history_max_points`（默认 50 万点，0.2 s 步长 24 h＝43.2 万点可完整保留）；按列紧凑存储每值 8 字节，两条快量 24 h 实测 38.5 MB | `History` 用 `array('d')`，缺值存 NaN |
| 热更新不丢 | 改窗长 / 改 PT-CT / 勾「保存曲线」都走热更新，趋势历史**保留**（旧版会清空）；**重新启动数据源**才清空（一次运行＝一个数据集） | `LiveEngine.update_config()` 搬运 history |
| 保存曲线 | 每条曲线面板右上角「保存曲线」勾选框 ＋ 「导出与日志」页同一份 6 项列表，改动即 `PUT /api/config {output:{curve_save:{…}}}` 并写入配置文件；**未勾选的曲线在保存/下载时不输出** | `output.curve_save`（6 键，默认全 true） |
| 保存到哪 | 「导出与日志」→「保存曲线数据到 output/」→ `output/curves_<时间>/<曲线>.csv`（每曲线一个文件：`t_epoch_s,time_local,quantity,window_s,字段…`，UTF-8 带 BOM，Excel 直接打开）；「下载已勾选曲线」→ 浏览器下载合并长表 `t_epoch_s,time_local,quantity,field,value` | `POST /api/curves/save`、`GET /api/curves/export[?quantity=]`；未勾选的单曲线下载返回 403，一个都没勾返回 400 |

手工点检（浏览器）：① 概览 4 个曲线面板标题右侧各有「保存曲线」勾选框，取消「三相电流」→ 右下 toast「已排除出保存项」，F5 后仍是未勾选；② 「导出与日志」页列表里「三相电流」同样未勾选，下载链接文案变「4/6」→ 点「保存曲线数据到 output/」→ 下方列出 4 个文件 ＋「三相电流：未勾选，已跳过」；③ 概览页底部有「趋势曲线显示最近 24 小时…」说明，曲线面板标题处有「最近 x · N 点（保留窗 24h）」。jsdom 自动版：`JSDOM_DIR=/tmp/uitest node tools/ui_r6_check.cjs http://127.0.0.1:8000` 期望 **PASS 30 / FAIL 0**。

#### 实时落盘 ＋ 离线播放起点 ＋ 曲线悬停取值（v0.6）

| 功能 | 在哪里 | 行为 | 依据 |
| --- | --- | --- | --- |
| **实时落盘** | 「导出与日志」→「实时落盘」面板（开关 / 目录 / 应用 / 刷新状态） | 开启后（出厂默认开）**每算出一个曲线点就追加写** `output/realtime/<曲线>_<数据日期>.csv`，6 条曲线各一个文件，按**数据时间**的本地日期分文件、跨午夜自动换文件；每次写后 flush（进程被杀最多丢最后一行）；同一天再跑续写同一文件、不重复表头；**受「保存曲线」勾选过滤**：未勾选的曲线不落盘。列＝`t_epoch_s,time_local,window_s,字段…`（与趋势曲线/手工保存同一提取规则），UTF-8-BOM | `elec_tool/realtime_writer.py`、`output.realtime_save/realtime_dir`、`GET /api/realtime`；环境变量 `ELEC_TOOL_REALTIME_DIR` 可整体改写目录 |
| **播放起点** | 「数据源与控制」→ csv_file 下「播放起点」下拉框 ＋ 取值框（其它源置灰；选「文件开头」时取值框置灰） | 五种：`begin` 开头 / `row` 第 N 条数据行（1 起算，不含表头）/ `seconds` 跳过开头 N 秒（按配置 fs 换算成行）/ `percent` 文件 N% 处（按字节定位再对齐到行首，大文件 O(1)）/ `time` 文件时标 ≥ 指定时刻的第一条（完整 `2026-10-12 08:00:00`，或只填 `08:00:00` 与当天时刻比较——适合 `0/00/00` 写法）。之前的数据**直接跳过不参与计算**；起点超出文件 → 引擎报「播放起点超出文件范围」；非法取值 → 保存/启动时 400 | `source.play_start_mode/play_start_value`、CLI `--play-from row:120001|sec:30|pct:50|time:08:00:00`、`iter_csv_blocks(skip_rows/start_percent/start_time)`；状态摘要显示「播放起点：…（跳过 N 行）」 |
| **曲线悬停取值** | 所有 canvas 曲线（6 条趋势、3 个波形、频谱） | 鼠标移入绘图区 → 竖向虚线吸附到**最近数据点**，各条曲线在该点处画圆点，右侧浮框列出「时刻（趋势图含毫秒 / 波形为秒 / 频谱为 Hz）＋每条曲线名: 数值」；浮框靠右边时自动翻到左侧；实时推送重绘（0.2 s 一次）后悬停仍在；移出清除；鼠标在刻度区不显示 | `app.js: bindHover/hoverInfo/drawHover`（有序二分找最近点；`cv.__hoverInfo` 可供脚本读取） |

手工点检（浏览器）：① 「导出与日志」→「实时落盘」开关为勾选、目录 `output/realtime` → 启动模拟器 10 s → 点「刷新状态」→ 列出 6 个 `<曲线>_<今天>.csv` 与行数，用 Excel 打开 `voltage_<今天>.csv` 行数应随时间增长；取消概览页「三相电流」的「保存曲线」→ 再刷新 → `current_*.csv` 行数不再增长；② 数据源页选 csv_file、「播放起点」选「跳过开头 N 秒」填 `2` → 启动 → 摘要「已摄入」比全量少 2×fs 点、告警「播放起点：跳过开头 2 s…实际跳过 12800 行」；选「指定时刻」填 `23:59:59` → 启动 → 状态「✗ 播放起点超出文件范围」；③ 概览页把鼠标移到电压趋势上 → 出现虚线＋三色圆点＋浮框 `HH:MM:SS.mmm / Ua: … / Ub: … / Uc: …`，移到 y 轴刻度区浮框消失。jsdom 自动版：`JSDOM_DIR=/tmp/uitest node tools/ui_r7_check.cjs http://127.0.0.1:8000` 期望 **PASS 39 / FAIL 0**。

#### 数据处理子界面：离线波形 CSV 重采样（v0.7）

左侧导航 **「🧮 数据处理」**。把指定路径的离线波形 CSV 按指定采样频率重采样，结果写入 `data/`，文件名＝**原文件名 + `_re_` + 目标采样率**：
`波形_农业排灌_大水泵_80_1.csv` → 6400 Hz → `波形_农业排灌_大水泵_80_1_re_6400.csv`。

| 项 | 行为 | 依据 |
| --- | --- | --- |
| 源文件 | 下拉框列出 `data/` 下 CSV（选中即填路径），也可手填仓库相对路径或绝对路径；「探查源文件」显示行数 / 编码 / 首个时间戳 / 推算采样率 | `tools/ui_r8_check.cjs` E1/E2 |
| 目标采样率 | 任意 >0 的数；输出名即时预览，已存在会提示（需勾「覆盖」） | E1/E4 |
| 原采样率 | 留空＝由时间戳列前 20000 行线性拟合推算（贴近整数则取整）；可手填覆盖（与推算偏差 >5% 会提示） | `test_r8_resample.py` |
| 插值方法 | `linear` 线性插值（**流式分块，内存 O(块)**，默认）/ `nearest` 最近邻 / `fft` 频域（等价 `scipy.signal.resample`，**降采样自带理想低通抗混叠**，但整文件载入） | 同上 |
| 时间轴 | 按**等间隔**原采样率重建：第 i 行＝起点 + i/fs_src，输出第 k 行＝起点 + k/fs_new（不逐行用原时标，避免 0.1 ms 量化抖动放大）；不外推 | 同上 |
| 时间戳写法 | 与源一致：epoch 数值→同单位（小数位自动加足到 ≤步长/10）；`0/00/00 HH:MM:SS.ffff`→原日期段原样、小数位 = max(原位数, 覆盖 1/fs_new 所需)；ISO→`YYYY-MM-DD HH:MM:SS.ffffff` | 同上 |
| 保留项 | 表头、列顺序、分隔符、编码（含 BOM 有无）；数值 6 位小数（CLI `--decimals`） | 同上 |
| 进度与取消 | 后台线程 + 进度条（按已读字节）+ 「取消」；失败/取消不留 `.part` 半成品 | E3/E4 |
| 衔接播放 | 完成后「用重采样文件作为离线播放源 →」一键切到数据源页并填入路径 | E5 |

手工点检：① 「数据处理」下拉选 `data/sample_6400hz.csv`，目标 3200 → 开始 → 进度条到 100%，结果区显示 `data/sample_6400hz_re_3200.csv`、行数 32000 → 16000；② 再点开始 → 提示「已存在」；勾「覆盖」选 `fft` 再点 → 成功；③ 「用重采样文件作为离线播放源」→ 数据源页 `csv_file` 路径已填 → 把配置采样率改为 3200 后启动。

CLI 同等能力：`.venv/bin/python cli.py resample "data/波形_农业排灌_大水泵_80_1.csv" --fs 6400 [--fs-src 3200] [--method fft] [--overwrite] [--format json]`。
库：`from elec_tool.resample import resample_csv; resample_csv(path, 6400, out_dir="data")`。

**注意**：`linear` 降采样无抗混叠（高于新 Nyquist 的谐波会折叠到低频），要做谐波分析请用 `fft`；`fft` 的输出点数 = round(N·fs_new/fs_src)（周期语义），比例非整时实际采样率略有偏差并写入 notes；重采样后播放时请把「配置采样率 fs」改成目标值。


#### 负荷辨识子界面：逐周波事件检测（v0.11）

> 导航「🧩 负荷辨识」。对**逐周波**的 P / Q / I 序列（每周波＝fs/f_nom＝128 点：P=mean(u·i)，Q=基波单频 DFT 无功，I=周波有效值；对象 total/A/B/C）在最近 `nilm.window_cycles` 个周波的滚动窗上并行运行 6 种突变检测算法；每条事件给出**算法、对象、开始/结束时刻（数据时间）、方向（up 投入 / down 切除）、幅值 |ΔP| 与带符号 ΔP / ΔQ / ΔI、事件前后稳态值、算法检验量**，并落盘 `output/nilm/nilm_events_<数据日期>.csv`（每事件一行，UTF-8-BOM，逐行 flush，`ELEC_TOOL_NILM_DIR` 可改）。

| 算法键 | 名称 | 原理 | 参数（`nilm.algorithms.<键>`，W＝有功，周波＝cycles） |
|---|---|---|---|
| `threshold` | 阈值差分 | 相邻周波 ΔP ≥ max(min_delta/2, 容差) 为起点；随后 settle 个周波极差 ≤ 容差为终点；起点精修到越过 Δ/2 中线的周波 | `min_delta_w` 50, `settle_cycles` 5, `settle_tol_w` 20, `max_rise_cycles` 40 |
| `two_window` | 双滑窗均值差 | \|mean(后窗)−mean(前窗)\| 的局部极大值 ≥ min_delta 且 ≥ k·σ(前窗) | `pre_cycles` 10, `post_cycles` 10, `min_delta_w` 50, `k_sigma` 3 |
| `cusum` | CUSUM 累积和 | 双侧 Page CUSUM：相对参考均值累积偏差 > h 触发，起点＝累积量最后归零处，触发后重置参考均值 | `drift_w` 10, `threshold_w` 200, `min_delta_w` 50, `settle_cycles` 5 |
| `glr` | GLR 广义似然比 | 高斯均值突变：n/4·(m1−m0)²/σ² 的局部极大值 ≥ 门限（σ² 取两侧方差均值，不低于 noise_w²） | `window_cycles` 15, `threshold` 25, `min_delta_w` 50, `noise_w` 10, `settle_cycles` 5 |
| `steady_state` | 稳态分段（Hart 1992） | 连续 ≥ N 个周波极差 ≤ 容差为稳态；相邻稳态均值差 ≥ min_delta 即事件（起点＝前稳态结束，终点＝后稳态开始） | `tol_w` 30, `min_steady_cycles` 10, `min_delta_w` 50, `max_transient_cycles` 100 |
| `median_diff` | 中值滤波差分 | N 点中值滤波去尖峰后再做阈值差分（单周波尖峰/缺口不触发） | `median_cycles` 5, `min_delta_w` 50, `settle_cycles` 5, `settle_tol_w` 20, `max_rise_cycles` 40 |

- 通用参数：`nilm.enabled`、`save`、`channels`（默认 `["total"]`）、`window_cycles` 300、`min_gap_cycles` 10（同算法同对象去重间隔）、**`rel_tol_pct` 1.0**（容差/漂移/噪声/CUSUM 门限按窗内 |P| 中位数折算，与绝对值取大）、**`min_delta_pct` 0**（最小幅值的相对版本）。阈值单位为 W、按计算口径（启用 PT/CT 时为一次侧）；相对门槛让同一套默认值在 W 级（二次侧）与 MW 级（一次侧）都可用。全部在界面「检测参数」表单热更新（`PUT /api/config {"nilm": …}` 深合并）。
- 去重/确认：每个算法都在整窗上重新评估，只对「终点全局周波序号 > 上次已报终点 + min_gap」且「终点之后已再看到 confirm 个周波」的候选报事件，所以事件会滞后几个周波（≤ 后窗/GLR 窗）出现，且**不随块边界重复**。
- 接口：`GET /api/nilm/events?limit&algos&channel&since_id`、`GET /api/nilm/cycles?n`（最近 n 周波 P/Q/I）、`POST /api/nilm/clear`；WS `type=nilm_event` 推送；`/api/state.engine.nilm_events_total/nilm_cycles`。
- 样例：`.venv/bin/python tools/gen_nilm_sample.py` 生成 `data/nilm_steps.csv`（1000 W → 2.0 s +500 W → 4.4 s −300 W，3.0 s 单周波尖峰）；默认 PT/CT 下 6 种算法均在 **2.000 s ↑750 kW、4.400 s ↓450 kW** 报出（起点误差 ≤1 周波，幅值误差 <1%）。
- **假设与已知特性（可改）**：① 周波按额定频率定长切分（不随频率自适应）；② 事件＝稳态间阶跃，不做负荷类型识别/聚类（辨识的「特征提取 + 事件库」已就位，分类留后续）；③ 双滑窗与 CUSUM 对单周波尖峰会按均值摊成小事件（样例中 60 kW），需要抗尖峰请看中值滤波差分/稳态分段或抬高 `min_delta_pct`；④ 幅值取事件后 settle 均值 − 事件前 settle 均值，暂态（电机启动冲击）期间不计入。
- 验证：`tests/test_r12_nilm.py` 8 项；`tools/ui_r12_check.cjs` 16 项；全量 **257 passed**。
- **调参**：运维向手册 **[`NILM_TUNING_GUIDE.md`](NILM_TUNING_GUIDE.md)**（每个参数管什么 / 先量 σ 与最小关心负荷 / 推荐公式 / 现象→对策 / 典型现场套路 / 验证流程）；配套 `python tools/nilm_tune.py --file <背景.csv> [--min-load-w N] [--json]` 自动量噪声并给 6 算法起点参数（`tests/test_nilm_tune_tool.py` 证明建议参数在同噪声下检出恰为最小负荷的阶跃、纯噪声 0 误报）。

#### 总线侧 + 分路侧设备 双数据源（v0.13，第 14 轮）

> 原有数据源即**总线侧**；新增**分路侧设备数据源**——一份完全独立的配置（数据源 / 采样 / PT-CT / 窗口 / 事件阈值 / 负荷辨识参数）+ 独立引擎，计算同一套电气量，所有子界面按「当前侧」显示。

| 项 | 总线侧（bus） | 分路侧设备（branch） |
|---|---|---|
| 配置文件 | `configs/runtime.json`（模板 `default.json`） | `configs/branch_runtime.json`（模板 `configs/branch.json`；或 `ELEC_TOOL_BRANCH_CONFIG_PATH`） |
| REST / WS | `/api/...`、`/ws` | **`/api/branch/...`（与总线侧同名同语义）**、`/ws/branch` |
| 输出目录（出厂） | `output/realtime` `output/events` `output/nilm` | **与总线侧相同**（v0.17.2 起两侧写同一文件，按 `source_id` 区分；分路侧配置里的目录会被强制同步为总线侧的值） |
| 概览接口 | `GET /api/sides`（两侧标签 / 配置文件 / 运行状态 / 前缀） | 同左 |

- **界面**：顶栏「总线侧 | 分路侧设备」切换器（记忆在浏览器）；切换后左侧全部子界面（总览、电压/电流/功率、谐波、间谐波、直流、事件、负荷辨识、窗口配置、数据源…）显示并编辑**当前侧**的数据与配置；分路侧时页眉带橙色标识。顶栏新增「分路侧」状态胶囊（未启用 / 运行中 / 已暂停 / 已完成 / 错误，点击即切换）。
- **启用与联动（离线文件模式）**：总线侧「数据源」页新增面板「分路侧设备数据源」：勾选 **启用** + 离线文件路径（可「探查」/「从 data/ 选择」）/ 播放倍速 / 自定义播放时间 / 时标 UTC / 每块样本数 →「保存分路侧数据源」。**分路侧固定为离线文件 `csv_file`**；总线侧不是离线文件时面板给出提示、启动不联动（`/api/engine/start` 返回 `branch.skipped` 与原因）（开关存总线侧 `branch.enabled`，源参数存分路侧配置）。启用后总线侧**「启动」会同时启动分路侧；「停止 / 暂停 / 恢复」联动**（分路侧不可暂停时忽略）。分路侧也可单独控制：切到分路侧后点「启动 / 停止 / 暂停」只作用于分路侧（`/api/branch/engine/*`）。
- 分路侧启动失败（如路径不存在）不影响总线侧：错误显示在胶囊与面板，`/api/state.branch.error`。
- **假设（按此实现，可改）**：① 两侧时间轴独立，不做对齐/同步（各自按文件时标或自定义时间播放，倍速各自设置）；② 不做总线−分路差值/占比等跨侧计算（后续可加「分路对账」子界面）；③ CLI 不变（一次只跑一份配置，分路侧用 `--config configs/branch_runtime.json` 即可）；④ 测试环境变量 `ELEC_TOOL_*_DIR` 对两侧同时生效。
- 验证：`tests/test_r14_branch.py` 4 项（两侧配置隔离与各自持久化 / 联动启动-暂停-恢复-停止与分路侧单独控制、两侧结果独立 / `/ws/branch` 与分路侧落盘 / 前端接线）；`tools/ui_r14_check.cjs` **19/19**（jsdom 走真实界面：配置分路侧 → 总线启动两侧同播 → 联动暂停 → 切侧后总览/负荷辨识显示分路侧数据 → 联动停止）；全量 **274 passed**。

#### 离线文件的暂停 / 恢复播放（v0.12）

> 顶栏「暂停」按钮与「数据源」页「暂停播放」按钮（同一功能），**只在离线文件（`csv_file`）源运行且未播完时可用**，其他源置灰并提示。

- **倍速**：「数据源」页「离线文件播放倍速」（1× 真实速率 / 2× / 5× / 10× / 0.5× / 不限速），对应 `source.file_speed`（配置与 CLI 默认 0＝不限速；界面默认 1×）。限速由**节拍钟**（`elec_tool/pace.py`，v0.15.1）按绝对墙钟计算：块时长＝块样本数/本侧 fs，目标时刻＝起点 + 已播数据时长/倍速，误差不累积；暂停后恢复不会突发追赶。联动启动时总线侧与分路侧**共用一只节拍钟并互锁**（任一侧块起点最多领先对侧进度 0.1 s）——两侧播放的数据时刻严格同步，与两侧采样率是否相同无关；CPU 跟不上名义倍速时两侧一起变慢而不是一侧跑飞；先播完的一侧退出互锁，另一侧继续播到自己的结尾。
- **暂停**：引擎线程停止读文件与计算，顶栏状态变「已暂停」，数据时刻、样本数、周波窗、事件表全部原地冻结；期间「刷新快照」、历史曲线、导出、负荷辨识/事件查询照常可用（看的是暂停时刻的缓冲）。
- **恢复**：从暂停处的下一块继续，不重读、不跳过；`duration_s` 限时运行会扣除暂停时长（`/api/state.paused_total_s`）。
- 暂停中点「停止」立即停止；重新「启动」从头（或所选播放起点）开始。对 `csv_tail`/`tcp`/`simulator` 不提供暂停（实时源暂停会丢数据或造成追赶突发，按设计拒绝）。
- 验证：`tests/test_r13_pause.py` 3 项（暂停冻结样本数与数据时刻 / 恢复继续且单调 / 播完后拒绝 / 暂停中停止 <1.5 s / 模拟器源 400 / 前端接线）。

#### 离线文件时标的 UTC 开关（v0.10）

> 适用 `csv_file`（未启用「自定义播放时间」时）与 `csv_tail`；配置项 `source.file_time_utc`（默认 **false**），界面在「数据源」页「自定义播放时间」勾选框下方；启动数据源时随表单下发，也可 CLI `--file-time-utc`。

| `file_time_utc` | 文件文本时标（`2026-10-12 08:00:00` / `0/00/00 00:12:40.0000`）如何解释 | 曲线 / 落盘 CSV / 事件 上看到的时间 |
|---|---|---|
| **false**（默认） | 按本机**本地时间**解释（解析时 tz_offset_h＝本机时区偏移，东八区 8） | **与文件中的数据时间一致**（文件 `00:12:40` → 界面 `00:12:40`） |
| **true** | 视为 **UTC** | 换算成本地时间显示（北京时间下文件 `00:12:40` → 界面 `08:12:40`，即 v0.9 及之前的表现） |

- 纯数字 epoch 时标是绝对时刻，不受本开关影响；`sampling`/计算结果也不受影响（只平移时间轴的绝对位置）。
- 播放起点 `time` 模式与 `0/00/00` 写法的「当天时刻」比较已按同一偏移还原，所填时刻仍是文件里的时刻。
- **假设（已按此实现，可改）**：① 浏览器与服务端在同一时区（界面用浏览器本地时间格式化 epoch）；② 启用「自定义播放时间」时时间轴由起始时间决定，本开关不显示（起始时间留空＝文件第 1 条时间，仍按本开关解释）；③ 偏移按当前时刻的本机时区取（含夏令时），不按每条数据各自判断；④ TCP 文本帧沿用同一开关。
- 验证：`tests/test_r11_file_time.py` 6 项（`TZ=Asia/Shanghai` 下日期时间 / 0/00/00 / epoch 三种写法、`create_source` 默认偏移、REST 探查与启动透传）；`tools/ui_r11_check.cjs` 11 项；全量测试在 `TZ=UTC` 与 `TZ=Asia/Shanghai` 下均通过。

#### 离线文件列映射开关（v0.9）

> 适用 `csv_file` / `csv_tail`（离线与追加文件）。TCP 实时源的字段顺序仍由 `source.struct_fields` 决定，不受本开关影响。界面位置：「数据源」页 →「离线文件列映射」面板；配置项 `columns.mapping_enabled` / `columns.mapping`，`PUT /api/config` 热更新，**对下次启动数据源生效**。

| 开关 | 取列规则 | 未映射的列 |
|---|---|---|
| **未启用**（默认） | 默认依次为 **时间, A相电压, A相电流, B相电压, B相电流, C相电压, C相电流**（第 1~7 列）。兼容规则：若首行是可识别表头（列名/别名命中全部 7 个字段），仍按表头取列（与 v0.8 及之前一致）；首行非数值但识别不出列名 → 判为表头并跳过，按默认列序 | 不存在的概念：7 列全部参与 |
| **启用** | **只播放有映射关系的列**。`columns.mapping` 7 个字段各填一个：**列号**（从 1 起）或**表头列名**（精确或忽略大小写/空格/下划线），留空＝不映射 | 未映射的 U/I 通道**按 0 播放**（不插值、不跳过），数据源状态 notes 提示「列映射：未映射字段 … 不播放」，`/api/probe` 返回 `unmapped`；**时间戳未映射**→ 时间轴按 `sampling.fs` 合成（t = 行号/fs，跨块连续），此时重采样子界面不可用（需要时间戳列） |

- 校验（保存时 400、`cli.py sources --file` 直接报错）：启用时必须至少映射 1 个电压/电流通道；列号 ≥1；两个字段不能映射同一列；按名映射的列名必须在表头中。
- 界面：勾选「启用列映射」后 7 个输入可编辑；「填入默认列序 1~7」一键填入；先「探查数据」再「按探查表头填入」会按别名把表头名写进各字段（识别不到的留空）。探查输出会列出 `[序号] 表头名`，方便填列号。
- **假设（用户跳过澄清，按此实现，可改）**：① 未映射通道按 0 而不是从计算中剔除——这样功率/不平衡度等三相量仍可算出，但未映射相的结果就是 0，请结合 notes 判读；② 未启用时「表头优先」是为了兼容既有现场文件（列顺序与默认不同但表头规范）；如需严格按位置，请启用映射并填 1~7；③ CLI `analyze` 与 Web 使用同一套 `ColumnMap.layout()`，行为一致。
- 验证：`tests/test_r10_colmap.py` 8 项（默认列序 / 表头乱序 / 列号+列名混填 / 未映射置 0 / 无时间戳合成连续时间轴 / 表头判定 / 校验报错 / REST 端到端 B、C 相为 0）；`tools/ui_r10_check.cjs` 15 项。

#### 间谐波 / 直流偏置 / 事件 子界面（v0.8）

左侧导航 **「🎚 间谐波」「➖ 直流偏置」「🚨 事件」**（事件项带活动事件数徽标）。三者都走既有管线：各有独立窗长（「窗口配置」页 `interharmonic` / `dc` 两行）、趋势曲线（`CURVE_KEYS` 从 6 条扩到 **8 条**：`interharmonic`＝TIHD_U/TIHD_I 与最大组含有率，`dc`＝Ua/Ub/Uc/Ia/Ib/Ic/In 直流）、保存/实时落盘/导出/CLI 标量表自动纳入。

| 子界面 | 口径（**假设与可配置项**） | 显示 | 依据 |
| --- | --- | --- | --- |
| **间谐波** | **IEC 61000-4-7 分组**：窗 = 整数周期（出厂 **0.2 s ＝ 10 周波 → Δf = 5 Hz，每组 9 条谱线**；1 周波窗无法分辨间谐波，界面会提示）。第 h 间谐波组（h=0…order_max−1，介于 h 与 h+1 次之间）：**组有效值** `IHG_h = √Σ C_k²`（不含两端谐波 bin）、**中心子组** `IHSG_h`（再去掉紧邻谐波的各 1 个 bin，抗泄漏）、**间谐波相量**＝组内最大谱线的 频率 / RMS 幅值 / 相角（cos 参考，与基波相量同口径）；**含有率** = IHG_h / X1 ×100%；**TIHD** = √Σ IHG_h² / X1 ×100%。*未做* IEC 的 10/15 min 平滑与 200 ms 聚合（与谐波一样是单窗值） | TIHD 卡片（三相 U/I、最大组）、各组柱状图（含有率 % / 组有效值 切换）、三相「前 10 组」相量表、TIHD 趋势 | `elec_tool/analysis/harmonic.py:interharmonic_analysis`，`tests/test_r9_events.py::test_interharmonic_groups_exact`（175 Hz 注入 → 第 3 组 2.000 A、175.0 Hz、17.19°，其余组 <1e-9） |
| **直流偏置** | 直流 = **整数周期窗的算术均值**（整周期上交流分量均值恒为 0，故无偏；窗出厂 1 s，`remove_dc=false` 且不可被误开）；相对值 = DC / 基波有效值 ×100%；中性线直流 = (Ia+Ib+Ic) 的均值；窗内**逐周期均值**给出漂移范围 | 三相 U/I 直流卡片、表格（含 N 行）、逐周期曲线、直流趋势（U/I 切换） | `dc_analysis`，`test_dc_analysis_exact` |
| **事件** | 6 类，阈值全部在界面「阈值配置」表单可改（即 `events.*`，PUT 热生效）。① **基波相量超限**：任一相 U1 > `u1_high_pct`%·`u_nom` 或 < `u1_low_pct`%·`u_nom`，I1 > `i1_high`；**`limits_secondary=true`（默认）时 `u_nom`/`i1_high` 按二次侧填（57.74 V / 6 A），启用 PT/CT 变换则自动 ×PT/×CT 与一次值结果比较**（界面卡片显示折算后有效阈值）。② **谐波相量超限**：任一相任一次 HR_h > `hr_u/i_limit_pct` 或 THD > `thd_u/i_limit_pct`。③ **间谐波相量超限**：任一相任一组含有率 > `ih_u/i_limit_pct`（出厂 1% / 2%）。④ **频率超限**：f ∉ [`f_low`,`f_high`]（出厂 49.5/50.5）。⑤ **频率变化率超限**：|Δf/Δt| > `rocof_limit`（出厂 1 Hz/s），Δ 取相邻两次 fundamental 输出（故时间分辨率＝fundamental 步长）。⑥ **功率振荡**：最近 `osc_window_s`（10 s）内 P 总序列 → 均匀重采样 → 去线性趋势 → hann+FFT，在 [`osc_f_min`,`osc_f_max`]（0.1–2.5 Hz）取主导分量，**峰峰值 ≥ `osc_limit_pct`%·|P̄| 且 ≥ `osc_min_w`** 判为振荡（可分辨的最高频率 = 1/(2×power 步长)，power 步长 1 s 时只到 0.5 Hz，要看 2 Hz 请把 power 窗/步长改到 0.2 s）。**生命周期**：同一(类型,对象)只有一个活动事件，记录开始/峰值/结束，复归用**滞回**（`hysteresis`=0.95：越上限事件需回到 limit×0.95 以下；频率用绝对带 0.05×(f_high−f_low)），**阈值热改后按新阈值复归**；所有时刻＝**数据时间**（离线回放同样成立）。**落盘**：`output/events/events_<数据日期>.csv`（start/end 各一行，UTF-8-BOM，每行 flush，`ELEC_TOOL_EVENTS_DIR` 可改）。⑦ 若 `sampling.adaptive_freq=false`，频率恒为额定值 → 频率/ROCOF 事件不会触发，界面给出提示 | 6 类计数卡片、活动事件表、历史表（类型过滤/只看活动/刷新/清空）、阈值表单；事件到达**不弹窗**（v0.8.1 起，事件多时会刷屏），只更新导航徽标与事件页 | `elec_tool/events.py`，`tests/test_r9_events.py`（6 类事件 9 项用例），`tools/ui_r9_check.cjs` 28 项 |

手工点检：① 启动离线样例 `data/sample_6400hz.csv`（含 8% 3 次 / 6% 5 次谐波）→「事件」页应出现 **12 条「谐波相量超限」活动事件**（THD_U/HR_U-h3/HR_U-h5 ×3 相 + THD_I ×3 相），基波相量不报（二次 57.7 V/5 A 折算后在限内）；② 把 THD_U/HR_U 上限改到 50%、THD_I 到 50% → 保存 → 1–2 s 后活动表清空、历史表状态变「已结束」且有持续时长；③ 「间谐波」页 TIHD 约 0.24%、最大组含有率 <0.1%（样例无间谐波，只有数值噪声）；④ 「直流偏置」页三相直流 |DC| < 0.5 V（样例含微小偏置）。

CLI/库：`cli.py run/analyze` 的标量表自动含 `interharmonic`/`dc` 两行；库用法 `MetricsCalculator(cfg).compute(block).quantities["interharmonic"].values["top_u"]`、`EventDetector(cfg).process(result)` 返回本次开始/结束的事件列表。

### 3.2 方式二：CLI（8 个子命令，全部实测）

```
.venv/bin/python cli.py --help      # 实录：init-config / gen-sample / selftest / sources / compute / live / resample / serve
```

**(1) `init-config` — 生成配置文件**

```bash
.venv/bin/python cli.py init-config --out configs/mine.json --fs 6400 --pt 100 --ct 15
# ✓ 默认配置已写入 configs/mine.json
#   fs=6400.0Hz  f_nom=50.0Hz  PT=100.0  CT=15.0  谐波=2~50次
#   各量窗长：voltage=1.0s, current=1.0s, power=1.0s, power_factor=1.0s, fundamental=0.2s, harmonic=0.2s, spectrum=1.0s
# 参数：--out --force(覆盖已存在) --fs --pt --ct                                    ✅实录
```

**(2) `gen-sample` — 生成样例数据（列格式与用户给定一致）**

```bash
.venv/bin/python cli.py gen-sample --out data/sample_6400hz.csv --duration 5 \
    --harmonics "3:0.08,5:0.06,7:0.03,11:0.015,13:0.01"
# 参数：--out --duration --freq --noise --harmonics(次:相对幅值,逗号分隔) --t0(起始epoch秒)
#       --ts-format {epoch,iso,ms} --encoding --config --fs
# 用途：无真实数据时联调全链路；--ts-format/--encoding 专门用于验证解析器对各种格式的兼容性   ✅实录
```

**(3) `selftest` — 解析解自检（模式 B 验收核心，不需真实数据）**

```bash
.venv/bin/python cli.py selftest                       # 汇总表
.venv/bin/python cli.py selftest -v                    # 逐项明细
.venv/bin/python cli.py selftest --json                # 机器可读（含 summary + checks 数组）
.venv/bin/python cli.py selftest --fs 6400 --freq 50 --pt 100 --ct 15 --window 1
# 实测输出：自检项 44 个：通过 44，失败 0，通过率 100.0%，最差相对误差 1.508e-05，耗时 0.32s
#           工况：fs=6400.0Hz  f=50.0Hz  PT=100.0  CT=15.0  窗长=1.0s
# 退出码：全绿 0，有失败 1（可直接接 CI / 批处理判断）                                  ✅实录
```

**(4) `sources` — 数据体检（只探查不计算，排查数据问题第一步）**

```bash
.venv/bin/python cli.py sources --file data/sample_6400hz.csv
# ● 文件：data/sample_6400hz.csv
#   大小：2.49 MB   编码：utf-8-sig（表头读取用 utf-8-sig）
#   表头：['时间戳', 'A相电压', 'A相电流', 'B相电压', 'B相电流', 'C相电压', 'C相电流']
#   列映射：{'timestamp': 0, 'ua': 1, 'ia': 2, 'ub': 3, 'ib': 4, 'uc': 5, 'ic': 6}
#   时间戳模式：s   推算采样率：6399.9943 Hz（配置 6400.0 Hz）
#   已扫描行数（上限 20 万）：32000
# 参数：--file（也可给目录，会列出目录下的 CSV） --config                            ✅实录
```

**(5) `compute` — 离线文件批算**

```bash
.venv/bin/python cli.py compute --file data/sample_6400hz.csv --format table --every 5
# ✓ 完成：输出 26 次；读入样本 32000（5.00s 数据），块 25，缓冲 10880/10880
#   各量输出次数：{'fundamental': 26, 'harmonic': 26, 'voltage': 6, 'current': 6,
#                  'power': 6, 'power_factor': 6, 'spectrum': 6}          ← 需求⑥：各量独立步长

.venv/bin/python cli.py compute --file data/sample_6400hz.csv --format csv --out output/demo_result.csv
#   CSV 结果：output/demo_result.csv（实测 1.4 MB；表头 t_ref,quantity,metric,value,unit,window_s）

.venv/bin/python cli.py compute --file 你的.csv --set-window voltage=5 --set-window harmonic=0.2
# ✓ 完成：… 缓冲 32000/49280   各量输出次数：{…, 'voltage': 2}   ← 电压窗改 5s 后只出 2 次，缓冲自动扩容

# 常用参数：--config --pt --ct --fs --freq --hmax --adaptive --no-scale
#           --set-window 量=秒（可重复）--apparent {arithmetic,vector} --reactive {harmonic_sum,quadrature}
#           --file --format {table,json,csv} --out --quantities 量,量 --block 每块点数
#           --every 每N次打印一次 --limit 最多输出次数 --max-ticks 最多轮询次数
# 注意：--quantities 只影响**打印内容**，不影响计算调度（各量仍按窗口配置计算）        ✅实录
# 注意：--every 只有 compute 有，live 没有（实测会报 unrecognized arguments）          ✅实录
```

**(6) `live` — 实时监视（模拟器 / 文件追加 / TCP）**

```bash
# 模拟器联调（20 倍速跑 2 秒）
.venv/bin/python cli.py live --source simulator --pace 20 --duration 2 --quantities voltage,power
# ● 实时监视：source=simulator  fs=6400.0Hz  PT=100.0 CT=15.0
#   按 Ctrl+C 停止；时长限制 2.0s
# [06:44:28] U=5805.7/5921.5/5689.6V  P=1127.74kW Q=660.37kvar   (voltage,current,power,…)
# ✓ 结束：输出 30 次，样本 38400，数据时长 6.00s，实时速率 19513 样本/s

# 实时采集落盘的文件（边写边算，监视追加）
.venv/bin/python cli.py live --source csv_tail --path data/sample_6400hz.csv --duration 2
# ✓ 结束：输出 25 次，样本 32000，数据时长 5.00s，实时速率 16140 样本/s

# TCP 文本帧——先用 tools/tcp_feeder.py 扮演采集装置，无需真实硬件            ✅沙盒实录
.venv/bin/python tools/tcp_feeder.py --port 9000 --mode text_csv --header --rate 4   # 另开一个终端
.venv/bin/python cli.py live --source tcp --host 127.0.0.1 --port 9000 --duration 6
# [07:44:12] U=5805.8/5921.7/5689.5V  P=1127.72kW Q=660.38kvar  f=50.000Hz  THDu=10.60%
# ✓ 结束：输出 42 次，样本 54400，数据时长 8.50s，实时速率 18134 样本/s
#   · 源：识别到表头：['时间戳','A相电压',…] → 映射 {'timestamp':0,'ua':1,'ia':2,…}

# TCP 二进制帧：帧格式三处可配（--frame/--struct-fmt/--struct-fields 本轮新增）  ✅沙盒实录
.venv/bin/python tools/tcp_feeder.py --port 9001 --mode binary --struct-fmt ">7f" --rate 4
.venv/bin/python cli.py live --source tcp --port 9001 --frame binary --struct-fmt ">7f" --duration 6
# ✓ 结束：输出 3 次，样本 60800，数据时长 9.50s，实时速率 10201 样本/s   ← 大端 float32（28 字节/帧）
# 真实协议帧格式仍待现场文档 🔶（拆帧改造点与三条实测注意事项见 §4.4）
# 收尾会打印数据缺口、引擎告警与**源告警**（本轮新增）：帧格式不匹配、时标退化、文件轮转等
# 只在这里可见，不打印就会「看着正常、其实时间轴是合成的」
# csv_tail 专用开关（实测）：
.venv/bin/python cli.py live --source csv_tail --path data/live.csv --from-end --duration 1
# ✓ 结束：输出 0 次，样本 0   ← 从文件末尾起只算新写入数据；静态文件没有新增故为 0，不报错
.venv/bin/python cli.py live --source csv_tail --path data/ --watch-newest --duration 1
# ✓ 结束：输出 13 次，样本 16640   ← 路径给目录时自动跟目录内 mtime 最新的 CSV
# 参数：--source {simulator,csv_tail,tcp} --path --host --port --frame {text_csv,binary}
#       --struct-fmt(如 "<7d" / ">7f") --struct-fields(默认 t,ua,ia,ub,ib,uc,ic)
#       --block --pace(速率倍数,0.001≈全速)
#       --from-end --watch-newest --duration --format {table,json,csv} --out --quantities --max-ticks
#       + 与 compute 相同的口径覆盖参数                                                ✅实录
```

**(7) `serve` — Web 界面**：见 §3.1。

### 3.3 方式三：作为 Python 库嵌入（实测代码与输出）

```python
from elec_tool.config import SourceConfig, load_or_default
from elec_tool.engine import LiveEngine

cfg = load_or_default("configs/default.json")           # 或 AppConfig() 用内置默认
cfg.source = SourceConfig(kind="csv_file", path="data/sample_6400hz.csv", block_samples=6400)
cfg.transform.pt_ratio, cfg.transform.ct_ratio = 100.0, 15.0
cfg.windows["voltage"].length_s = 1.0                   # 需求⑥：按量配置时间段
cfg.validate()                                          # 不合法配置会抛 ConfigError（含中文原因）

eng = LiveEngine(cfg)
last = None
for res in eng.run():                                   # 生成器：每到期一批电气量产出一次
    last = res

v, p, h = last.quantities["voltage"], last.quantities["power"], last.quantities["harmonic"]
print(v.values["rms"], p.values["p_total"], h.values["thd_u_pct"])
print(v.window)                                         # 窗长口径自证：请求/实际/点数/周期数/f_used/泄漏标志
print(eng.calc.history.get("voltage", 100))             # 历史趋势（每量独立）
```

实测输出（沙盒）：

```
U(A/B/C) = [5805.7, 5805.7, 5805.8] V
P/Q/PF   = 1140.62 kW 662.65 kvar 0.8637
THDu(A)  = 10.593 %   5次 = 346.4 V
窗长     = 1.0 s → 6400 点 / 50 周期
```

### 3.4 REST / WebSocket 接口清单（供二次集成，`/openapi.json` 实录）

| 方法与路径 | 作用 |
| --- | --- |
| `GET /api/health` | 存活与版本（`{"ok":true,"version":"0.1.0","running":true}`） |
| `GET /api/state` | 全量状态：引擎（摄入点数/速率/缓冲/各量输出次数/告警/缺口）、数据源 info、生效配置、配置文件路径 |
| `GET /api/config` | 读当前生效配置 |
| `PUT /api/config` | **深合并**局部更新（只传要改的字段）并热更新到运行中的引擎；非法值返回 400 + 中文原因 |
| `POST /api/engine/start` | 启动引擎；body 可覆盖 `kind/path/host/port/frame/block_samples/poll_interval_s/tail_from_end/sim_speed/watch_dir_newest/struct_fmt/struct_fields/custom_time/custom_time_start/play_start_mode/play_start_value/windows/duration_s` |
| `GET /api/common_window?preview=0|1` | **公共时间段**（v0.15）：preview=1 按当前两侧配置现算；否则返回最近一次联动启动采用的时间段（state 中亦含 `common_window`） |
| `GET /api/compare/{quantity}?offset_s&tol_s&hours&max_points`、`GET /api/compare` | **跨侧对齐与差值**（v0.14.1）：总线/分路最近邻配对，`diff`＝总线−分路、`ratio_pct`＝分路/总线×100；偏移/容差默认取总线侧 `config.branch.time_offset_s / align_tol_s` |
| `/api/branch/<任意上述接口>`、`/ws/branch` | **分路侧设备**：与总线侧同名同语义的全套接口（v0.13）；`GET /api/sides` 两侧概览 |
| `POST /api/engine/pause` / `resume` | **离线文件源**暂停 / 恢复播放（v0.12）：暂停＝不读文件、不计算、数据时刻原地不动，缓冲/历史/事件保留；恢复＝从暂停处继续。非 `csv_file`、未运行、已播完 → 400 `{error}`；`/api/state` 增 `paused` / `pausable` / `paused_total_s` |
| `POST /api/engine/stop` | 停止引擎（结果仍可查询/导出） |
| `GET /api/result?full=true|false` | 最新结果；`full=true` 强制按当前缓冲把七类量都算一遍，`false` 取最近缓存；无结果返回 409 |
| `GET /api/history/{quantity}?max_points=1500&hours=&n=` | 某量趋势点：默认返回**最近 `output.history_hours`（24h）内全部**，超过 `max_points` 按峰谷抽稀；`hours` 覆盖时间窗、`n` 兼容旧用法（只取最后 n 条）；附 `count_total/span_s/t_first/t_last/decimated` |
| `POST /api/curves/save` | 把**已勾选**（`output.curve_save`）的曲线写到 `output/curves_<时间>/<曲线>.csv`；body 可选 `{"quantities":[…],"hours":24}`；未勾选项出现在 `skipped`，一个都没勾返回 400，有勾选但无数据返回 409 |
| `GET /api/curves/export?quantity=&hours=` | 下载曲线 CSV：给 `quantity` ＝单曲线（未勾选返回 403）；不给＝所有已勾选曲线合并长表 |
| `GET /api/realtime` | 实时落盘状态：`enabled/dir/rows_written{曲线:行}/files[本次会话打开的文件]/dir_files[目录现有 CSV 及大小]/curve_save/errors`；开关与目录通过 `PUT /api/config {output:{realtime_save,realtime_dir}}` 改，热更新即时生效 |
| `GET /api/export?fmt=csv|json&quantity=` | 导出累计结果（CSV 扁平表 / JSON 全量）；未知 `fmt` 返回 400；无结果 409 |
| `GET /api/selftest?fs=&freq=&pt=&ct=&window=` | 一键 44 项解析解自检 + 运行环境 |
| `GET /api/probe?path=` | 数据体检（表头/编码/行数/时间戳模式/推算 fs/偏差） |
| `GET /api/files?sub=data` | 列目录下的 CSV |
| `POST /api/process/resample` | 启动离线 CSV 重采样后台任务（`path, fs_new, [fs_src], [method], [overwrite], [out_dir=data]`） |
| `GET /api/process/resample` | 任务进度/结果/错误（`running, progress, stage, rows_in, rows_out, result, error`） |
| `POST /api/process/resample/cancel` | 取消运行中的重采样 |
| `GET /api/process/resample/preview?path&fs_new` | 只算输出文件名与是否已存在 |
| `GET /api/events?active=&limit=&types=&since_id=` | v0.8 事件列表 + 摘要（`counts/active_by_type/effective_limits/limit_scale/writer/osc/notes`）；`types` 逗号分隔；`since_id` 增量拉取 |
| `POST /api/events/clear` | 清空内存事件与活动状态（不删已落盘 CSV），并 WS 广播 `events_cleared` |
| `WS /ws` 新消息 | `{"type":"event","data":[事件…]}`：每次有事件开始/结束即推（对象含 `id/type/type_name/subject/start_t/end_t/value_start/value_peak/limit/unit/direction/detail/active`） |
| `GET /` `/static/*` | 界面与静态资源 |
| `WS /ws` | 实时推送：连上即发 `hello`(状态) + `snapshot`(结果)，之后按 `result`/`state`/`error` 推送。**注意推送是「分量子集」**（只含本次到期的电气量），客户端必须按键合并——`app.js:mergeResult()` 已实现 |

```bash
curl -s http://127.0.0.1:8000/api/health
curl -s -X PUT http://127.0.0.1:8000/api/config -H 'Content-Type: application/json' \
     -d '{"windows":{"voltage":{"length_s":5.0}}}'
curl -s -X POST http://127.0.0.1:8000/api/engine/start -H 'Content-Type: application/json' \
     -d '{"kind":"csv_file","path":"data/sample_6400hz.csv"}'
curl -s "http://127.0.0.1:8000/api/result?full=true"
curl -s "http://127.0.0.1:8000/api/export?fmt=csv" -o output/result.csv
```

### 3.5 运行期常见故障

| 现象 | 原因 | 处理 | 状态 |
| --- | --- | --- | --- |
| 离线文件播放中顶栏「样本」、「数据源状态」汇总停在启动瞬间，点「刷新」才变 | v0.6.1 及更早：WS 只在队列空闲 1s 时发 state，连续 result 流下永不触发 | 升级到 v0.6.2（F-23 已修，state 每 1s 必发） |
| 用 IP（如 192.168.x.x）访问时页面每次刷新纵向变长、滚动条不断增加；127.0.0.1 正常 | v0.6 及更早：画布高度按 `devicePixelRatio` 复利放大；浏览器按主机名记忆缩放级别，故两个地址表现不同 | 升级到 v0.6.1（F-22 已修）；临时规避：在该页面按 **Ctrl+0** 把缩放恢复 100%（系统缩放也须 100%） |
| `[Errno 98] Address already in use` | 端口被占 | 换端口 `--port 8001`；查占用：Linux `ss -lntp \| grep 8000`，Windows `netstat -ano \| findstr :8000` | Linux ✅ / Windows 🔶 |
| 页面能打开但没有数据 | 引擎未启动（默认不自动跑） | 界面「数据源与控制」→ 点「启动数据源」；或启动服务时带 `ELEC_TOOL_AUTOSTART=1` | ✅沙盒实录 |
| 界面右下角显示「推送断开 → 已降级为轮询」 | WebSocket 被反代/防火墙拦 | 功能正常但实时性降为 1.5 s；按 §3.1 配置反代升级头 | ✅（降级逻辑实录） |
| 结果里出现「整周期截断：请求 1.0s → 实际 49 周期(6272点)」 | 缓冲内可用数据不足一个完整窗（刚启动/数据缺口） | 属**如实降级**，等数据积满即恢复；持续出现则检查数据是否断流 | ✅沙盒实录 |
| 「频谱点数 3201 > 1200，已按桶内取最大抽稀…」 | `output.spectrum_max_points` 限制（仅为显示性能） | 抽稀**保峰不保能量**；要精确谱就调大该值或缩短窗长 | ✅沙盒实录 |
| 「采样率校验」告警 | 时间戳推算 fs 与配置偏差 > `sampling.fs_tolerance`(默认 1%) | 先 `cli.py sources --file` 看推算值；时间戳精度不足（如只有 ms）会造成假偏差，提高时间戳精度或调 `fs_tolerance` | ✅沙盒实录 |
| 中文表头乱码 | 文件是 GBK/GB18030 | `columns.encoding` 默认 `auto`，会依次试 utf-8-sig/utf-8/gb18030/gbk/big5/latin-1；仍不行就显式指定编码 | ✅（解析器测试覆盖 gbk/big5） |
| 出现「缺测/NaN 已线性插值」告警 | 原始数据有空值或 NaN | 少量可接受；告警中若出现「>5%」字样则该段数据**不可用于验收** | ✅（解析器会无条件记 note） |
| 数值明显偏大/偏小 100 或 15 倍 | PT/CT 设置与实际不符，或输入本就是一次值 | 界面/配置里改 `transform.pt_ratio`、`ct_ratio`；`--no-scale` 可直接看二次值对账 | ✅ |
| 长时间运行内存上涨 | 历史与结果缓存 | 环形缓冲上限 = 最长窗 × fs × 1.6（自动扩容，有上限）；`output.history_len`(默认 900) 与服务端结果缓存 `maxlen=2000` 都是定长队列 | ✅（架构实录） |
| 改了界面配置，重启后没了 / 或出厂模板被改 | 配置持久化机制 | 界面保存写入 `configs/runtime.json`（gitignore），下次启动优先加载；`configs/default.json` 是出厂模板不会被界面污染。要恢复出厂：删掉 `runtime.json` | ✅沙盒实录 |

---

## 4. 四种数据源详解（配置 · 运行 · 验证）

验收④「输入支持实时采集与离线文件」在本工具里落成 **4 种数据源**：`csv_file`（离线文件）、`csv_tail`（实时·文件追加）、`tcp`（实时·TCP 客户端）、`simulator`（内置合成源）。本章逐源给出：**① 完整配置字段（含默认值与约束）② CLI / Web / Python 库三种运行方式 ③ 沙盒实测输出 ④ 注意事项 ⑤ 你自己能复现的验证方法**。

> **实测条件**（本章所有数字均为沙盒实录，2026-10-10，Linux 6.1.158+ / CPython 3.11.2 / numpy 2.4.6 / 2 核 3 GB）。
> 实时数据由 `tools/csv_appender.py`（写文件）与 `tools/tcp_feeder.py`（TCP 推送）扮演采集装置，两者与内置 `simulator` **共用同一信号模型**：二次侧 U1=100/√3 V、I1=5 A、φ=30°、谐波 3/5/7/11/13 次＝8%/6%/3%/1.5%/1%、噪声 0.2%、不平衡 2%、fs=6400 Hz。
> 经 PT=100 / CT=15 变换后的**一次侧解析解**：U1=5773.503 V、I1=75.0 A、P₁=3·U1·I1·cos30°=**1125.000 kW**、THDu=√(0.08²+0.06²+0.03²+0.015²+0.01²)=**10.595%**。实测 P 略高于 P₁（+0.24%）＝谐波功率贡献，属预期。

### 4.0 四种源一览

| `source.kind` | 定位 | 必填字段 | 实时 | 读完即止 | 验证状态 |
| --- | --- | --- | --- | --- | --- |
| `csv_file` | 离线历史文件，一次读完、按窗滚动计算 | `path` | 否 | 是（`exhausted=True`） | ✅沙盒实录（CLI/Web/库三入口）＋单测 |
| `csv_tail` | 采集器边写 CSV 边算（单文件或目录分片） | `path` | 是 | 否 | ✅沙盒实录（4 种组合）＋单测（含本轮新增回归） |
| `tcp` | 采集装置 TCP 推送（文本行 / 二进制定长帧） | `host`,`port` | 是 | 否 | ✅沙盒实录（`text_csv`＋`binary` 两种帧、两种字节序）；**真实协议帧格式 🔶待现场文档** |
| `simulator` | 内置合成源：无硬件联调、算法自证、演示 | —（默认源） | 是 | 否 | ✅沙盒实录＋解析解对账 |

**四种源共用的字段**（`configs/default.json` → `source` / `sampling` / `transform`）：

| 字段 | 默认 | 含义与约束 |
| --- | --- | --- |
| `source.kind` | `simulator` | 必须是上表 4 值之一，否则启动即 `ConfigError` |
| `source.block_samples` | `640` | 每块样本数（6400 Hz 下＝0.1 s）；必须 >0。块越小越跟手、越大越省 CPU |
| `source.poll_interval_s` | `0.2` | 实时源无新数据时的轮询间隔（`csv_tail`/`tcp`） |
| `sampling.fs` | `6400.0` | 采样率。时间戳可推算时会做校验并告警（实测偏差 ≤0.003%） |
| `sampling.f_nom` / `f_min` / `f_max` | `50.0` / `45.0` / `65.0` | 额定频率与自适应估频搜索范围 |
| `transform.pt_ratio` / `ct_ratio` | `100.0` / `15.0` | 一次值＝二次值×变比；`transform.enabled=false`（CLI `--no-scale`）输出二次值 |
| `columns.*` | 见 §6 | 列映射/编码/表头/时间戳单位，`csv_file` 与 `csv_tail` 共用 |

**三种运行入口对照**（详细操作见 §3）：

| 入口 | 离线（`csv_file`） | 实时（`csv_tail`/`tcp`/`simulator`） |
| --- | --- | --- |
| CLI | `cli.py compute --file <路径>` | `cli.py live --source <kind> …` |
| Web | 「数据源与控制」选 `离线文件(csv_file)` → 填路径 → 探测 → 启动 | 同界面选对应源 → 填字段 → 启动（REST：`POST /api/engine/start`） |
| 库 | `create_source(cfg)` → `LiveEngine(cfg).run()`（§3.3） | 同左 |

### 4.1 数据格式（用户已确认的事实）

| 项 | 内容 | 状态 |
| --- | --- | --- |
| 采集对象 | 二次侧三相电压、三相电流 | ✅（来源：用户 2026-10-10 需求描述） |
| 采样频率 | 6400 Hz | ✅（同上；奈奎斯特 3200 Hz，50 次谐波=2500 Hz 不混叠） |
| 存储 | CSV | ✅（同上） |
| 列格式 | `时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流` | ✅（同上；`configs/default.json` 的 `columns` 已按此设置） |
| 变比 | PT=100、CT=15，均可配置 | ✅（同上；界面/配置/CLI 三处都可改） |
| 电压是相电压还是线电压 | 默认按**相电压**处理（`transform.voltage_input=phase`） | 🔶待确认（若现场给的是线电压，改成 `line`） |
| 时间戳格式 | epoch 秒 / `YYYY-MM-DD HH:MM:SS.ffffff` / epoch 毫秒 / **`0/00/00 00:12:40.0000`（日期段全 0、只有当天时刻、4 位小数＝0.1 ms；用户 2026-10-12 给出的采集器写法）** 都能自动识别；`2026/1/5 8:03:07.5` 这类不补零写法也可 | ✅解析器实录（用户三行样例 + 3 s 合成文件实跑）；无日期格式的处理规则见 §4.2「自定义播放时间」 |
| 文件编码 | utf-8-sig/utf-8/gb18030/gbk/big5/latin-1 自动探测 | ✅解析器实录；**你的实际编码** 🔶待确认 |
| 表头 | 有表头按列名/别名映射；**无表头**（第一行就是数据，如用户样例）自动识别并按 `时间戳,Ua,Ia,Ub,Ib,Uc,Ic` 顺序取列 | ✅实录（`cli.py compute`、`/api/probe`、Web 启动三处） |
| 实时传输方式 | 「采集器写 CSV → 本工具 tail 追加读取」已完整验证；TCP 两种帧格式已验证，**真实协议帧格式未定** | 🔶待确认（TCP `frame`/`struct_fmt`/`struct_fields` 需按现场协议文档填） |

### 4.2 源一：`csv_file`（离线文件）

**配置字段**

| 字段 | 默认 | 说明 |
| --- | --- | --- |
| `source.path` | `""` | **必填**。CSV 文件路径；相对路径按仓库根解析（Web 里传相对路径也可以） |
| `source.block_samples` | `640` | 分块读入，内存占用与文件大小无关（2.5 MB/32000 行实测分 50 块） |
| `columns.encoding` | `"auto"` | auto 时按 utf-8-sig→utf-8→gb18030→gbk→big5→latin-1 探测 |
| `columns.has_header` | `true` | 有表头按表头名映射（中文表头实测可识别）；无表头按 `t,ua,ia,ub,ib,uc,ic` 顺序取列 |
| `columns.mapping_enabled` / `mapping` | `false` / 1~7 | v0.9 列映射开关：启用后只播放有映射关系的列（列号或表头名），见 §3.1 |
| `columns.timestamp_unit` | `"auto"` | auto 按数量级判 epoch s/ms/us/ns 或相对秒；也可强制指定 |
| `columns.timestamp_col` 等 | 见 §6 | 列名映射（现场列名不同只需改这里，不用动代码） |
| `source.custom_time` | `false` | **自定义播放时间**（v0.5）：true → 时间轴＝起始时间＋样本序号/`fs`（严格等间隔，不再有缺口检测）；false → 按文件内时间戳播放 |
| `source.custom_time_start` | `""` | 自定义起始时间：**留空＝文件第 1 条数据的时间**；或填 `2026-10-12 08:00:00`（本地时间）/ `2026/10/12 08:00:00` / `2026-10-12T08:00:00` / `2026-10-12` / epoch 秒；非法文本在保存配置时即报错 |
| `source.play_start_mode` | `"begin"` | **播放起点**（v0.6）：`begin` 从头 / `row` 第 N 条数据行 / `seconds` 跳过开头 N 秒 / `percent` 文件 N% 处 / `time` 文件时标 ≥ 指定时刻；起点之前的数据不参与计算 |
| `source.play_start_value` | `""` | 起点取值，按模式解释：`120001` / `30` / `50` / `2026-10-12 08:00:00` 或 `08:00:00`（只填时刻＝与文件时标的当天时刻比较，适合 `0/00/00` 写法）；非法在保存配置时即报错；超出文件范围在启动后报「播放起点超出文件范围」 |

**自定义播放时间（什么时候用）**

- 采集器时标只有当天时刻（`0/00/00 00:12:40.0000`）：不开自定义时，解析器把它按 **1970-01-01 + 当天时刻**处理（界面时:分:秒正确、日期是 1970），并在告警里提示；**开自定义并填真实起始时间**即可得到真实日期；
- 时标被 0.1 ms 量化（6400 Hz 的间隔是 156.25 µs，文件里相邻差在 0.1/0.2 ms 之间跳）：不影响电气量计算（计算只按样本序与配置 fs），但时间轴有抖动；开自定义后严格等间隔；
- 时标跨午夜：无日期格式会自动展开（23:59:59.9999 → 00:00:00.0001 不判为回退）；
- 开启后文件里的时间**缺口不会被检测**（时间轴是合成的）——需要查缺口请关掉自定义时间跑一遍。

```bash
# 用户格式文件（无表头、0/00/00 时刻）：直接算
python cli.py compute --file data/你的.csv --format table
# 自定义播放时间：起始＝文件第 1 条数据时间
python cli.py compute --file data/你的.csv --custom-time
# 自定义播放时间：起始＝指定时刻（给了起始时间即隐含 --custom-time）
python cli.py compute --file data/你的.csv --custom-time-start "2026-10-12 08:00:00"
# 从指定位置开始播放（四选一）：
python cli.py compute --file data/你的.csv --play-from sec:30            # 跳过开头 30 s
python cli.py compute --file data/你的.csv --play-from row:120001        # 从第 120001 条数据行
python cli.py compute --file data/你的.csv --play-from pct:50            # 从文件一半处
python cli.py compute --file data/你的.csv --play-from time:08:00:00     # 时标 ≥ 08:00:00（0/00/00 写法只填时刻）
```

Web：「数据源与控制」→ 离线文件 → 勾「csv_file：自定义播放时间」→（可选）填「自定义起始时间」→「启动数据源」；数据源状态摘要会显示「自定义播放时间：起始 配置起始时间/文件第 1 条数据时间 …」。

**用户格式实测**（3 s 合成文件，写法与用户三行样例一致）：`/api/probe` → `has_header=false, rows=19200, ts_mode=clock_time, fs_est=6400.003 Hz`；`cli.py compute` → 输出 16 次、告警 `时间戳格式识别为 'Y/M/D HH:MM:SS.f(无日期=0/00/00)'`、`采样率校验通过 6400.008Hz`；`--custom-time-start "2026-10-12 08:00:00"` → 结果 `数据时刻 2026-10-12 08:00:00`，相邻样本差恒为 1/6400 s。

**运行方式（三入口）**

```bash
# ① 先体检：编码/表头/列映射/由时间戳推算的采样率
python cli.py sources --file data/sample_6400hz.csv
# ② 算：表格或 CSV 导出
python cli.py compute --file data/sample_6400hz.csv --format table
python cli.py compute --file data/sample_6400hz.csv --format csv --out output/demo_result.csv
# ③ 只把电压的有效值窗改成 5 s，其余量不受影响（验收⑥）
python cli.py compute --file data/你的.csv --set-window voltage=5
```

Web：「数据源与控制」→ 源选 `离线文件(csv_file)` → 填路径 → 点「探测」（走 `GET /api/probe`，实测返回 `encoding=utf-8-sig`、7 列中文表头、`fs_est=6399.99 Hz`）→「启动引擎」。
库：`tools/verify_sources.py --kinds csv_file`（§4.8）或 §3.3 的嵌入示例。

**实测输出**（5 s / 32000 行样例，CLI）

```
✓ 完成：输出 26 次；读入样本 32000（5.00s 数据），块 50
  各量输出次数：{'fundamental': 26, 'harmonic': 26, 'voltage': 6, 'current': 6,
                 'power': 6, 'power_factor': 6, 'spectrum': 6}
```

**实测数值**（`tools/verify_sources.py --kinds csv_file --duration 2`，与解析解对账）

```
[PASS] csv_file  U1均=5773.60V 偏差 0.17‱（解析解 5773.503V）；P=1140.644kW；THDu 偏差 0.003 百分点
    U(A/B/C)=[5805.9, 5805.9, 5806.0]V  U1=[5773.87, 5773.45, 5773.48]V  I1=[75.005, 74.999, 74.998]A
    P=1140.644kW  Q=662.658kvar  PF=0.8637  f=50.0Hz(nominal)  THDu=[10.589,10.592,10.594]%
    不平衡=0.0016%  输出 9 次  样本 12160  缺口 0
    · 源：采样率校验通过：时间戳推算 6399.855Hz ≈ 配置 6400.0Hz（偏差 0.0023%）
```

样例文件由 `cli.py gen-sample`（`build_signal`：三相**平衡**、谐波电流相角 40°）生成，与实时源的 `SimulatorSource`（2% 不平衡、谐波相角跟随 φ=30°）不是同一次信号实现，所以它的 P（1140.6 kW）比实时源（1127.7 kW）高约 1.1%——**这是数据差异不是算法误差**（U1 与 THDu 仍与解析解吻合到 0.17‱ / 0.003 百分点）。

**注意事项**

- 文件读完 → `exhausted=True`，引擎自动 `flush_all()` 收尾，不需要手工停；
- 时间戳只写到 ms 时（6400 Hz 间隔 156.25 µs），逐点差分会有 ~0.2% 量化假偏差 → 解析器改用**最长连续段线性拟合**推 fs，实测偏差降到 0.002% 量级；`gen-sample` 因此用 `%.9f` 写时间戳；
- 缺测（NaN/空单元格）按配置插值并在结果 `notes` 里告警，不会静默算错。

### 4.3 源二：`csv_tail`（实时·文件追加）

对应用户的实时落地方式：**采集器持续把二次侧三相 U/I 写进 CSV，本工具边写边算**。

**配置字段**

| 字段 | 默认 | 说明 |
| --- | --- | --- |
| `source.path` | `""` | **必填**。可以是**单个文件**，也可以是**目录**（目录模式需 `watch_dir_newest=true`，且目录内有 `*.csv`） |
| `source.tail_from_end` | `false` | `false`＝从文件头补算历史；`true`＝只算启动之后新写入的数据 |
| `source.watch_dir_newest` | **`true`** | 目录模式自动跟 mtime 最新的 CSV（采集器按段/按天换文件时有用） |
| `source.poll_interval_s` | `0.2` | 无新数据时的轮询间隔 |
| `source.block_samples` | `640` | 凑满一块才计算；不足一块时行留在 `pending_rows` |
| `columns.*` | 同 `csv_file` | 编码/表头/列映射/时间戳单位一致 |

**运行方式（三入口）**

```bash
# 四种组合（实测全部通过）
python cli.py live --source csv_tail --path data/tail_live.csv                 # 文件·含历史
python cli.py live --source csv_tail --path data/tail_live.csv --from-end      # 文件·只算新增
python cli.py live --source csv_tail --path data/tail_dir --watch-newest       # 目录·跟最新分片
python cli.py live --source csv_tail --path data/tail_dir                      # 目录·默认已跟最新
```

Web：源选 `实时·文件追加(csv_tail)` → 填路径 → 勾选 `tail_from_end` / `watch_dir_newest` → 启动（两个勾选框与 REST 白名单字段一一对应）。
库：`create_source(cfg)` 返回 `CsvTailSource`；或 `tools/verify_sources.py --kinds csv_tail`。

**没有采集装置怎么验证**（本轮新增工具，扮演采集器按用户列格式追加写文件）：

```bash
python tools/csv_appender.py --out data/tail_live.csv --rate 4              # 单文件，4 倍速追加
python tools/csv_appender.py --out data/tail_dir --rotate-every 20 --rate 4 # 目录分片，每 20 块换文件
python tools/csv_appender.py --out data/x.csv --no-header                   # 验证无表头解析路径
```

**实测输出**

| 组合 | 命令要点 | 实测结果 |
| --- | --- | --- |
| 文件·含历史 | `--path data/tail_live.csv` | 输出 14 次（历史＋新增） |
| 文件·只算新增 | `--from-end`，6 s | 输出 **78** 次、样本 100480、数据时长 15.70 s、**16749 样本/s**；U=5805.9/5921.8/5689.5 V，P=1127.76 kW，Q=660.31 kvar，THDu=10.60%，缺口 0 |
| 目录·跟最新＋轮转 | `--path data/tail_dir --watch-newest`，10 s | 输出 **125** 次、样本 160640、25.10 s、16103 样本/s；期间产生 **93 个分片**；U=5806.0/5922.0/5689.5 V，P=1127.74 kW，**缺口 0** |
| 库入口 | `verify_sources.py --kinds csv_tail` | U1均=5773.91 V（偏差 **0.70‱**）、P=1127.747 kW、THDu 偏差 0.005 百分点、缺口 0 |
| Web/REST | `POST /api/engine/start` | U=[5806.3, 5922.1, 5690.1] V、P=1127.87 kW、Q=660.32 kvar、PF=0.8584、不平衡=3.997%、缺口 0 |

`--from-end` 且启动后没有新增数据时，输出 0 次且**不报错**（这是正确行为，不是故障）。

**已修缺陷（本轮实测发现，务必知道）**：目录模式下切换分片时，旧分片在上次轮询之后新写入的数据被静默丢弃——每切换一次丢**正好一整块**（640 点＝100.2 ms），在结果里表现为与轮转周期同频的「疑似丢点」**假缺口**（实测 8 s 内 8 处、间隔恰好 2.000 s）。修法＝切换前先 drain 旧文件（`csv_tail._drain_current()`），回归测试 `tests/test_sources.py::test_csv_tail_dir_switch_drains_old_file`（撤销修复则断言 1280≠1920 失败）。修复后复测：**缺口 0**，且日志明写「旧文件补读 640 行」。

**注意事项**

- 文件轮转（inode 变化）与截断（长度变小）都会自动重开；文件消失会等待重建并告警；
- 半行数据（采集器正在写的那一行）**不会被消费**，留到下次凑齐（单测 `test_csv_tail_partial_line_not_consumed`）；
- 时间跳变 >1.5 个采样间隔 → 记为**数据缺口**并在界面「导出与日志」告警，跨该点的窗结果需复核；
- 告警按「中文骨架」去重（`sources/base.py::note_key`）：否则同一条告警每块重发一次，实测 3 s 就能刷出 8 条只差小数位的「采样率校验通过」，把关键信息淹没。

### 4.4 源三：`tcp`（实时·TCP 客户端）

本工具作**客户端**主动连接采集装置/网关并持续收数；支持两种帧格式。

**配置字段**

| 字段 | 默认 | 说明 |
| --- | --- | --- |
| `source.host` | `127.0.0.1` | 采集装置地址 |
| `source.port` | `9000` | 必须 0<port<65536，否则 `ConfigError` |
| `source.frame` | `text_csv` | `text_csv`＝每行一条 CSV（可带中文表头，自动识别）；`binary`＝定长二进制帧 |
| `source.struct_fmt` | `<7d` | `binary` 帧格式（Python `struct` 语法）：`<`小端/`>`大端/`!`网络序＋类型码。默认 7 个 double＝**56 字节/帧**；`>7f`＝大端 float32＝**28 字节/帧** |
| `source.struct_fields` | `t,ua,ia,ub,ib,uc,ic` | 帧内字段顺序，必须与 `struct_fmt` 的元素个数一致 |
| `source.struct_has_header` | `false` | 二进制流是否以一段表头开头 |
| `source.block_samples` | `640` | 凑满一块才计算；不足一帧的余数字节留待下次 |
| `timeout_s` / `reconnect_s` | `2.0` / `2.0` | 连接/接收超时与断线重连间隔。**目前是构造参数、未暴露到配置文件**（库调用可传，CLI/Web 用默认值）——已记为缺口，见 §11 |

**运行方式（三入口）**

```bash
# 文本帧（采集装置按行推 CSV，可带中文表头）
python cli.py live --source tcp --host 127.0.0.1 --port 9000 --frame text_csv
# 二进制帧：帧格式三处可配（CLI 开关为本轮新增）
python cli.py live --source tcp --port 9001 --frame binary --struct-fmt ">7f" \
                   --struct-fields t,ua,ia,ub,ib,uc,ic
```

Web：源选 `实时·TCP流(tcp)` → 填 host/port → 选帧格式 → 二进制时填 `struct_fmt` / `struct_fields`（两个输入框为本轮新增）→ 启动。
REST：`POST /api/engine/start`，载荷白名单含 `kind,host,port,frame,struct_fmt,struct_fields,block_samples,…`（§3.4）。
库：`create_source(cfg)` 返回 `TcpStreamSource`；`tools/verify_sources.py --kinds tcp_text,tcp_binary`。

**没有采集装置怎么验证**（本轮新增工具，扮演采集装置；单客户端串行，断开后接受下一个）：

```bash
python tools/tcp_feeder.py --port 9000 --mode text_csv --header --rate 4   # 文本帧＋中文表头
python tools/tcp_feeder.py --port 9001 --mode binary --rate 4              # 二进制 <7d（56 字节/帧）
python tools/tcp_feeder.py --port 9001 --mode binary --struct-fmt ">7f"    # 大端 float32（28 字节/帧）
```

**实测输出**

| 帧格式 | 入口 | 实测结果 |
| --- | --- | --- |
| `text_csv`（中文表头） | CLI，6 s | U=5805.8/5921.7/5689.5 V，P=1127.72 kW，Q=660.38 kvar，f=50.000 Hz，THDu=10.60%；`✓ 结束：输出 42 次，样本 54400，数据时长 8.50s，实时速率 18134 样本/s`；喂数器日志证实表头被识别为 `{'timestamp':0,'ua':1,'ia':2,'ub':3,'ib':4,'uc':5,'ic':6}`，3 次客户端连接、断开后继续服务 |
| `binary` `>7f`（28 字节） | CLI，6 s | U=5805.9/5922.0/5689.6 V，P=1127.80 kW，Q=660.30 kvar，THDu=10.60%；`输出 3 次，样本 60800，9.50s，10201 样本/s` |
| `binary` `<7d`（56 字节） | Web/REST | U=[5805.7, 5922.2, 5689.6] V，U1=5773.2 V，P=1127.74 kW，Q=660.38 kvar，PF=0.8584，THDu=10.596%，缺口 0 |
| `binary` `<7d` | 库 | U1均=5773.75 V（偏差 **0.42‱**），P=1127.751 kW（较 P₁ +0.245%＝谐波功率），THDu 偏差 0.002 百分点，缺口 0 |

**注意事项（三条都是实测踩到的）**

1. **不要用 float32 存 epoch 秒**：float32 在 1.7e9 秒处量化步长约 **128 s**，一整块 0.1 s 的样本时标会完全相同。电气量本身不受影响（只用样本序＋配置 fs），但时间轴显示与缺口检测会失真——实测 `>7f` 帧的显示时刻比真实早约 2 分钟。解析器现在会显式告警：`时间戳整块无递增（全部相同）…建议协议改用 double 或整数毫秒时标`。
2. **帧格式不匹配不再崩，且能自证**：实测用默认 `<7d` 去解 `>7f` 流，修复前 CLI 直接崩 `OverflowError: timestamp out of range for platform time_t`；现在解析层加了合理性闸门（换算后非有限或 |t|>1e11 秒即抛可诊断 `ParseError`），源自动退回「按 fs 合成时间轴」，并在 CLI 收尾/Web 源面板打出排查清单：① `struct_fmt` 字节序与类型 ② `struct_fields` 字段顺序 ③ CSV 列映射与 `timestamp_unit`。
3. **连不上/断线都有明确诊断**：端口未监听实测报 `ParseError: TCP 连接失败 127.0.0.1:9001 —— [Errno 111] Connection refused。排查：① 采集服务是否已启动并监听该端口 ② 防火墙/网段 ③ 配置 source.host/port 是否正确`；运行中断线按 `reconnect_s` 自动重连并计数（`info().reconnects`）。

**🔶 真实协议待定项**：帧头/帧尾、长度字段、缩放系数（是否已乘变比）、字节序、时标类型（epoch 秒/毫秒/相对秒）、是否有心跳或确认帧。拿到现场协议文档后，多数情况只需改 `struct_fmt`/`struct_fields`；若是「帧头＋长度＋校验」的复杂协议，则在 `elec_tool/sources/tcp_stream.py` 的 `_flush_block` 里加拆帧逻辑（`DataSource` 接口不变，上层零改动）。在此之前建议走「采集器落 CSV ＋ `csv_tail`」路线（已完整验证）。

### 4.5 源四：`simulator`（内置合成源）

**配置字段**

| 字段 | 默认 | 说明 |
| --- | --- | --- |
| `source.sim_f` | `50.0` | 基波频率（改 49.8/60 可验证自适应估频与抗泄漏） |
| `source.sim_harmonics` | `{3:0.08, 5:0.06, 7:0.03, 11:0.015, 13:0.01}` | 各次谐波相对基波幅值比（对应 THDu=10.595%） |
| `source.sim_noise_ratio` | `0.002` | 高斯噪声占比 |
| `source.sim_unbalance` | `0.02` | 三相幅值不平衡度（2%） |
| `source.sim_speed` | `1.0` | 1.0＝按真实时间速率产出；>1 加速（联调用，实测 4 倍速下 16000～18000 样本/s） |

**运行方式（三入口）**：`python cli.py live`（默认源就是 simulator）；Web 源选 `合成数据(simulator)` → 启动；库 `SimulatorSource(cfg, realtime_pace=True, speed=…)`。

**实测数值**（`verify_sources.py --kinds simulator`，Web/REST 同口径）

```
[PASS] simulator  U1均=5773.75V 偏差 0.42‱  P=1127.727kW 偏差 0.242%  THDu 偏差 0.002 百分点
    U(A/B/C)=[5805.6, 5922.4, 5689.5]V  I1=[74.99, 75.745, 74.247]A  PF=0.8584
    f=50.0Hz(nominal)  THDu=[10.593,10.594,10.604]%  不平衡=4.0123%  输出 14 次  缺口 0
```

**注意事项**

- `info()` 里恒有告警「合成数据：用于联调与算法自验证，**不代表真实电网**」——界面上看到它是正常的；
- `sim_unbalance=2%` 是**相电压幅值**不平衡，换算到线电压约 4%（实测 4.01%），别把它当成算法误差；
- 与 `cli.py selftest`（44/44，`worst_rel_err=1.508e-05`）同源，所以 simulator 的结果可直接和解析解对账。

### 4.6 四源横向对账（同一信号模型）

| 源 / 入口 | U(A/B/C) V | U1均 偏差 | P kW | Q kvar | PF | THDu % | 缺口 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `csv_file`（库，样例文件） | 5805.9 / 5805.9 / 5806.0 | 0.17‱ | 1140.644 | 662.658 | 0.8637 | 10.589 | 0 |
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

**结论**：`csv_tail` / `tcp(text_csv)` / `tcp(binary)` / `simulator` 四种实时源在 **CLI、Web/REST、库**三条入口下的 P 落在 1127.727～1127.87 kW（极差 **0.013%**），U1 偏差 ≤0.70‱，THDu 偏差 ≤0.005 百分点，缺口全为 0 ⇒ **四种输入方式在算法层等价，入口不影响结果**；P 比基波解析解 P₁ 高 0.24% ＝谐波功率贡献（预期）。`csv_file` 的 P 高 1.1% 是因为样例文件是另一次信号实现（三相平衡＋谐波电流相角 40°），其 U1/THDu 仍与解析解吻合。

### 4.7 PT/CT 与一次/二次值口径

- `一次值 = 二次值 × 变比`；`功率变比 = PT × CT`（默认 PT=100、CT=15 → 功率乘 1500）。
- `transform.enabled=false`（或 `--no-scale`）→ 直接输出二次值，便于与现场表计对账。
- 界面上所有卡片默认显示**一次值**，单位随之为 V/A/W/var。✅（`scaling.py` + 测试 `test_engine_applies_pt_ct` / `test_no_scale_option_uses_secondary`）

### 4.8 一键复现本章全部验证

```bash
# ① 库级四源验证：自动拉起 csv_appender / tcp_feeder 扮演采集侧，跑完即清理（无需真实硬件）
python tools/verify_sources.py                    # 实测：PASS 5 / SKIP 0 / FAIL 0
python tools/verify_sources.py --json             # 机器可读（便于入库比对）
python tools/verify_sources.py --kinds csv_file,simulator      # 只跑不依赖外部进程的两例
# ② 单元测试（含数据源 13 项、工具防腐 5 项）
python -m pytest tests/ -q                        # 实测：147 passed, 1 skipped
# ③ 算法自检（44 项解析解对账）
python cli.py selftest                            # 实测：44/44，worst_rel_err=1.508e-05
```

`verify_sources.py` 的判定口径写在工具 docstring 里：U1 用三相均值对账（合成信号含 2% 不平衡，单相值本就偏离）、容差 5‱；P 对 P₁ 容差 0.5%；THDu 容差 0.05 百分点；出现数据缺口直接 FAIL；没有采集侧时是 **SKIP＋可操作提示**（退出码 0），参数错误退出码 2，验证失败退出码 1。
逐条取证（含命令、原始输出、判读）见 **`REPORT_TEST.md` → T-003**。

---

## 5. 数据目录（台账第 4 章）

| 路径 | 内容 | 是否入库 |
| --- | --- | --- |
| `data/` | 输入 CSV（真实数据、样例数据） | ❌ 不入库（`.gitignore`: `data/`、`*.csv`） |
| `output/` | `compute --format csv` 与界面导出的结果 CSV | ❌ 不入库 |
| `logs/` | 运行日志（自行重定向） | ❌ 不入库 |
| `configs/default.json` | 出厂配置模板 | ✅ 入库 |
| `configs/runtime.json` | 界面保存的当前配置 | ❌ 不入库（gitignore） |
| `tests/fixtures/*.csv` | 测试用小样本（如需） | ✅ 例外允许入库 |

> **数据不入库是既定策略**：现场电力数据可能涉密且体量大（6400 Hz × 7 列 ≈ 0.5 MB/s）。样例数据用 `cli.py gen-sample` 现场生成即可复现。✅

---

## 6. 配置结构（台账第 5 章）

配置文件：`configs/default.json`（出厂模板）→ 界面改动写 `configs/runtime.json`（优先加载）。加载优先级：`ELEC_TOOL_CONFIG`(整份 JSON) > `ELEC_TOOL_CONFIG_PATH` > `runtime.json`(存在时) > `default.json`。✅沙盒实录

| 段 | 字段 | 默认值 / 取值 | 说明 |
| --- | --- | --- | --- |
| `sampling` | `fs` | 6400.0 | 采样频率 Hz |
| | `f_nom` / `f_min` / `f_max` | 50.0 / 45.0 / 65.0 | 额定频率与估频允许区间（越界回退 `f_nom`） |
| | `adaptive_freq` | true | 开启后先估频再整周期截断（抗频谱泄漏） |
| | `fs_from_timestamps` / `fs_tolerance` | true / 0.01 | 用时间戳反推 fs 并与配置对账（偏差 >1% 告警） |
| `transform` | `pt_ratio` / `ct_ratio` | 100.0 / 15.0 | 电压/电流变比 |
| | `voltage_input` | `phase` | 输入是相电压还是线电压（`phase`/`line`）🔶现场待确认 |
| | `enabled` | true | false → 输出二次值 |
| `harmonic` | `order_min` / `order_max` | 2 / 50 | 谐波次数范围（需求⑤） |
| | `thd_order_max` | 50 | THD 计算到的最高次 |
| | `include_interharmonic` | true | 输出间谐波占比 |
| `power` | `apparent` | `arithmetic` | 视在功率口径：`arithmetic`(S=ΣU·I) / `vector`(S=√(P²+Q²)) |
| | `reactive` | `harmonic_sum` | 无功口径：`harmonic_sum`(Σ UₕIₕsinφₕ，严格) / `quadrature`(√(S²−P²)，等效) |
| | `fundamental_power` | true | 是否输出基波 P1/Q1 |
| | `three_phase_mode` | `four_wire` | 三相制式（影响零线电流口径） |
| `columns` | `timestamp/ua/ia/ub/ib/uc/ic` | 0..6 | 列名（支持别名，大小写/空格/下划线不敏感） |
| | `encoding` | `auto` | 编码探测顺序见 §4.1 |
| | `delimiter` / `has_header` | `,` / true | 分隔符与是否有表头 |
| | `timestamp_unit` | `auto` | `>1e17`→ns，`>1e14`→µs，`>1e11`→ms，`>1e8`→s，否则按相对秒（并记 note） |
| | `mapping_enabled` | `false` | v0.9：离线文件列映射开关。false＝默认列序 时间,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流（可识别表头时按表头）；true＝只播放 `mapping` 里有映射的列 |
| | `mapping` | `{"timestamp":"1","ua":"2",…,"ic":"7"}` | 字段→列号（从 1 起）或表头列名；空串＝不映射（通道按 0 播放；时间戳未映射则按 fs 合成时间轴）；见 §3.1「离线文件列映射开关」 |
| `source` | `kind` | `simulator` | `csv_file`/`csv_tail`/`tcp`/`simulator` |
| | `path` / `host` / `port` / `frame` / `struct_fmt` / `struct_fields` | — | 各源参数（TCP 帧格式 🔶待确认） |
| | `block_samples` / `poll_interval_s` | 640 / 0.05 | 每块点数与轮询间隔 |
| | `tail_from_end` / `watch_dir_newest` | false / **true** | csv_tail 行为：只算新增 / 目录模式跟最新文件（CLI `--from-end`、`--watch-newest` 与界面勾选框可改） |
| | `sim_f` / `sim_harmonics` / `sim_noise_ratio` / `sim_unbalance` / `sim_speed` | 50 / {3:0.08,5:0.06,7:0.03,11:0.015,13:0.01} / 0.002 / 0.02 / 1.0 | 模拟器参数（`sim_speed>1` 加速联调） |
| | `file_time_utc` | `false` | v0.10：离线文件文本时标是否按 UTC 解释；false＝曲线时间与文件时间一致（按本机本地时间解释），true＝视为 UTC 换算显示。epoch 数字时标不受影响 |
| | `custom_time` / `custom_time_start` | false / `""` | csv_file 自定义播放时间（§4.2）：时间轴＝起始＋序号/fs；起始留空＝文件第 1 条数据时间 |
| `output` | `history_hours` / `history_max_points` | 24.0 / 500000 | 趋势曲线保留窗（小时，按数据时间）与每条曲线内存上限（安全阀） |
| | `realtime_save` / `realtime_dir` | true / `output/realtime` | **实时落盘**（v0.6）：每算出一个曲线点就追加写 `<realtime_dir>/<曲线>_<数据日期>.csv`（受 `curve_save` 过滤）；CLI `--realtime-save on|off --realtime-dir …`；环境变量 `ELEC_TOOL_REALTIME_DIR` 优先 |
| | `curve_save` | 6 键全 true | 「保存曲线数据」时各曲线是否参与（`voltage/current/power/power_factor/fundamental/harmonic`）；false 的曲线保存/下载时跳过 |
| | `history_len` / `export_dir` / `spectrum_max_points` | 600（已不再作上限用，兼容旧配置）/ `output` / 1600 | 导出目录、频谱显示抽稀上限 |
| `windows.<量>` | `length_s` | voltage/current/power/power_factor/spectrum=1.0，fundamental/harmonic=0.2 | **需求⑥：逐量配置计算时间段** |
| | `step_s` | null(=等于 length_s) | 输出步长（可与窗长不同，实现滑动输出） |
| | `policy` | `integer_cycles` | FFT 类量强制整周期（改成 `full_window` 会记 note 并可能泄漏） |
| | `window_fn` / `remove_dc` / `min_cycles` | `rect` / true / 1 | 窗函数、去直流、最少周期数 |

> 非法配置会被拒绝并给出中文原因（实测样例）：`[voltage] length_s 必须 > 0（当前 -1）`、`sampling.f_min(70) 必须 < f_max(40)`、`PT/CT 变比必须 > 0（当前 PT=0, CT=15.0）`、`harmonic.order_max=200 次对应 10000Hz ≥ Nyquist 3200Hz，会混叠`。✅沙盒实录

---

## 7. 输出产物（台账第 6 章）

| 产物 | 位置 / 格式 | 内容 | 状态 |
| --- | --- | --- | --- |
| 界面实时结果 | 浏览器 12 个子界面 | 卡片数值 + 趋势图 + 谐波柱状图 + 四象限图 + 频谱 | ✅沙盒实录 |
| 结果 CSV | `output/result_<ts>.csv` 或 `--out` 指定；界面「导出与日志」也可下载 | 扁平表：`t_ref,quantity,metric,value,unit,window_s`（实测 5 s 数据 → 26 次输出 → 1.4 MB / 约 34.6 万行含全量谐波与频谱时） | ✅沙盒实录 |
| 结果 JSON | `GET /api/export?fmt=json`、`compute --format json`（每行一个结果对象） | 完整结构：`t_ref/f_used/f_source/meta/quantities{values,series,window,units,notes}` | ✅沙盒实录 |
| 历史趋势 | `GET /api/history/{quantity}?max_points=` | 每量独立时间序列（`t` 非递减），默认最近 24 h、超量峰谷抽稀 | ✅沙盒实录 |
| 曲线数据 CSV | `output/curves_<时间>/<曲线>.csv`（`POST /api/curves/save`）；`GET /api/curves/export` 合并长表 | 只含已勾选曲线：`t_epoch_s,time_local,quantity,window_s,Ua,Ub,Uc,…`（UTF-8-BOM） | ✅沙盒实录（4 文件 + skipped 2） |
| **实时落盘 CSV** | `output/realtime/<曲线>_<YYYYMMDD>.csv`（引擎每算一点追加一行，按数据日期分文件） | `t_epoch_s,time_local,window_s,字段…`（与趋势曲线同一提取规则，UTF-8-BOM，追加不重复表头） | ✅沙盒实录（文件行数 == 趋势历史点数 == `rows_written`） |
| 自检报告 | `cli.py selftest --json`、`GET /api/selftest`、界面「算法自检」 | 44 项：`id/name/expected/actual/tol_rel/rel_err/ok/unit/note` + 运行环境（Python/OS/numpy） | ✅沙盒实录 |
| 告警与缺口 | 界面「导出与日志」、结果 `notes` 字段 | 整周期截断、频谱抽稀、NaN 插值、采样率偏差、数据缺口、功率残差、口径退化提示 | ✅沙盒实录 |

---

## 8. 验证与自检（五层，逐层可复现）

| 层 | 命令 | 期望结果（沙盒实录） | 作用 |
| --- | --- | --- | --- |
| 1. 算法解析解 | `cli.py selftest` | 44 项全 PASS，最差相对误差 1.508e-05，中位 1.1e-15 | 证明**计算口径正确**，不需要真实数据 |
| 2. 回归测试 | `.venv/bin/python -m pytest tests/ -q` | **186 passed, 1 skipped**（约 61 s） | 证明解析/调度/Web 接口/前端契约/边界行为未回退 |
| 3. 端到端实跑 | `cli.py compute --file data/sample_6400hz.csv` | 输出 26 次，emits 分层（快量 26 / 慢量 6） | 证明全链路（读→缩放→切窗→计算→输出）通 |
| 4. 四源对账 | `tools/verify_sources.py` | PASS 5 / SKIP 0 / FAIL 0 | 证明 4 种数据源（含 TCP 两种帧）算出的电气量与解析解一致 |
| 5. 界面契约 | `pytest tests/test_web_ui.py` ＋ `node tools/ui_dropdown_check.cjs` | 14 passed；PASS 74 / FAIL 0 | 证明下拉框选项与后端枚举一致、4 种源可分别配置并真的跑起来 |
| 6. 第 6 轮四功能 | `pytest tests/test_r6_features.py` ＋ `node tools/ui_r6_check.cjs` | 25 passed；PASS 30 / FAIL 0 | 用户时标格式、24h 曲线、逐曲线保存开关、自定义播放时间（含界面联动与服务端真跑） |
| 7. 第 7 轮三功能 | `pytest tests/test_r7_features.py` ＋ `node tools/ui_r7_check.cjs` | 18 passed；PASS 39 / FAIL 0 | 实时落盘（文件行数＝历史点数、勾选过滤、热更新开关、按日期分文件）、播放起点（5 种模式精确行数、超范围可诊断、CLI）、曲线悬停（悬停值＝真实数据、重绘不丢、离开清除、频谱同样可用） |

自检 44 项覆盖（`cli.py selftest -v` 可看逐项）：S1 相电压/相电流/线电压/零线电流；S2 P/Q/S/PF/DPF/P1/Q1；S3 U1/I1/THD_U/THD_I 与 3·5·7·11·13 次；S4 频谱主峰与分辨率(=1/窗长)；S5 1s vs 5s 窗一致性；S6 PT/CT 缩放线性；S7 f=49.85Hz 非额定频率自适应抗泄漏；S8 5% 负序；S9 直流分量。

**算法口径**（稳定结论，详见 `REPORT.md`）：整周期矩形窗 FFT（6400/50 = 128 点/周期）；相量以 cos 为参考，`RMS相量 = √2·X[k]/Σw`；THD = `√(Σ₂..H Xₕ²)/X₁×100%`；序分量用 Fortescue；功率以时域 `P = Σ mean(uₖiₖ)` 为权威，与 `Σ Pₕ` 交叉校验（残差 >1% 自动告警，实测残差 6e-7%）。

---

## 9. 生产推荐流程（台账第 7 章）

**推荐拓扑（现场实时监测）** ✅架构实录 / 🔶现场未验证

```
采集装置(二次侧 6400Hz) ──写──> data/live.csv ──tail──> csv_tail 源 ──> LiveEngine ──WebSocket──> 浏览器(局域网)
                                                            │
                                                            └──> output/result_*.csv（定时导出/归档）
```

**推荐操作序列**

1. 部署：§2.2–2.5（离线机器走 §2.4(b)/(c)），5 条验证命令全绿；
2. 口径自检：`cli.py selftest --fs <现场fs> --freq <额定> --pt <PT> --ct <CT>` 必须 44/44；
3. 数据体检：`cli.py sources --file <现场数据>`，确认编码/列映射/推算采样率；
4. 离线对账：`cli.py compute --file <现场数据> --format csv --out output/对账.csv`，与现场表计/其它系统比 U、I、P、PF、THD（差异 >1% 要查变比与口径）；
5. 实时上线：`cli.py serve`（或 systemd/NSSM 常驻 + `ELEC_TOOL_AUTOSTART=1`），源切 `csv_tail`；
6. 窗长按业务设定：电能质量类建议 voltage/current/harmonic 用 1s~5s，趋势类可用 1s 步长滑动；
7. 归档：定时导出 CSV/JSON，保留 `notes` 与缺口日志作为数据质量证据。

**不推荐**：① `uvicorn --workers N`（引擎状态在进程内存，多 worker 会各算各的）；② 直接把 `configs/default.json` 当运行配置改（应改 `runtime.json` 或用 `--config`，便于回溯出厂口径）；③ 用抽稀后的频谱做定量结论（抽稀保峰不保能量，仅用于显示）。✅（架构约束 + 实测告警文案）

---

## 10. 台账文件索引（BOOTSTRAP.md v2.2）

| 文件 | 用途 | 状态 |
| --- | --- | --- |
| `BOOTSTRAP.md` | 会话与任务协议 v2.2 | ✅ 存在 |
| `ROLE.md` | 角色定义库 v1.4 | ✅ 存在 |
| `STATUS.md` | 续接文件（当前角色/目标/进度/决策/路径） | ✅ 2026-10-10 更新 |
| `README.md` | 本文件（安装/运行/数据/配置/产物/流程） | ✅ v0.2（沙盒实录；用户环境项 🔶） |
| `REPORT.md` | 稳定结论（算法口径/KPI 口径/推荐版本） | ✅ 电气量计算口径已稳定；NILM 算法路线仍 🔶 |
| `REPORT_TEST.md` | 专题报告（只追加） | ✅ 含 T-001（待归档）、T-002（本地部署与验收执行包） |
| `NILM_DATA_DICT.md` | 数据定义库 | ✅ 用户已确认项已翻 ✅；其余 🔶 |
| `session/NILM_AC_session_complete.md` | 会话纪要（每 session 追加） | ✅ |
| `TUNING_GUIDE.md` | 调参教学文档 | ⬜ 暂未创建（理由见 `STATUS.md`） |

---

## 11. 验证状态（工程实现工程师交付说明）

- **沙盒已验证（Linux / CPython 3.11.2，2026-10-10 实录）**
  - 安装：venv + `pip install -r requirements.txt`；离线安装（Linux 29 包 / Windows 目标 24 包下载）；最小安装报错提示
  - 算法：`selftest` 44/44（最差 1.508e-05）；`pytest tests/ -q` **257 passed, 1 skipped**（v0.11）
  - CLI：7 个子命令逐条实跑（含 `--set-window`、`--format csv/json/table`、`--pace`、`--ts-format`）
  - Web：页面与静态资源 200、12 个子界面、REST 12 组端点、WebSocket 推送与降级、配置热更新与持久化分离、导出 34.6 万行 CSV
  - 实时：模拟器 6400 点/s 稳定摄入（实测 6398–6400 点/s），各量按独立窗长输出（0.2s 量 5 次/s、1s 量 1 次/s）
  - **四种数据源 × 三条入口**（§4，`REPORT_TEST.md` T-003）：`csv_file`/`csv_tail`/`tcp(text_csv)`/`tcp(binary)`/`simulator` 在 CLI、Web/REST、库三条入口下实跑，同源四路 P 极差 **0.013%**、U1 偏差 ≤0.70‱、THDu 偏差 ≤0.005 百分点、缺口 0；`tools/verify_sources.py` 实测 **PASS 5 / FAIL 0**
  - 本轮实测发现并修复：① `csv_tail` 目录分片切换丢一整块（640 点/100.2 ms 假缺口）→ 切换前 drain 旧文件＋回归测试；② 二进制帧格式不匹配时 CLI 崩 `OverflowError` → 解析层合理性闸门＋显示层兜底＋自动退回合成时间轴并给排查清单；③ 实时源告警未去重（3 s 刷 8 条）→ 按中文骨架去重；④ float32 存 epoch 秒造成时标量化（~128 s）→ 显式告警
  - **Web 界面下拉框专项检查**（§3.1、`REPORT_TEST.md` T-003 S14~S16）：jsdom 驱动真实页面 + 真实服务端，实测 **PASS 74 / FAIL 0**。修复 5 个界面缺陷：⑥ `src-kind`/`src-frame` 无 change 监听（选了不联动、无关字段可编辑却静默不生效）；⑦ 启动/保存载荷无条件发送空 `path`/`host`（空 path 被服务端 400 拒、空 host 被静默存空）；⑧ 空数字框按 `+''===0` 送出 → `PUT /api/config` 必 400「sampling.fs 必须 > 0」；⑨ 快量 0.2 s 一次的推送触发无条件回填 → **把用户刚选的下拉框改回服务端值、清掉输入一半的路径**；⑩ 「启动数据源」夹带 `transform/sampling/harmonic/power`，而 `/api/engine/start` 白名单只吃 source 键 → 改完 PT/CT 点启动被静默忽略
  - **第 6 轮四项功能**（2026-10-12，`REPORT_TEST.md` T-004）：① 用户时标格式 `0/00/00 00:12:40.0000`（无日期/无表头/0.1 ms 截断）解析、跨午夜展开、fs 推算 6400.003 Hz；② 趋势曲线改为按数据时间保留最近 24 h（紧凑列存储、峰谷抽稀、热更新不丢）；③ 6 条曲线逐条「保存曲线」开关（面板＋导出页同步、写入配置、保存/下载严格按勾选过滤）；④ 离线「自定义播放时间」（起始默认文件第 1 条，支持指定时刻，非法文本保存时即拒）。`tests/test_r6_features.py` 25 项 ＋ `tools/ui_r6_check.cjs` PASS 30/FAIL 0 ＋ 旧 harness 复跑 PASS 74/FAIL 0
  - **第 7 轮三项功能**（2026-10-12，`REPORT_TEST.md` T-005）：① 曲线点实时落盘 `output/realtime/<曲线>_<数据日期>.csv`（每点追加＋flush、按数据日期分文件、受「保存曲线」勾选过滤、热更新开关即时生效、`GET /api/realtime`、界面面板）；② 离线文件指定位置播放（`row/seconds/percent/time` 四种定位＋`begin`，界面下拉框联动、CLI `--play-from`、超范围可诊断报错）；③ 曲线悬停取值（所有 canvas：吸附最近点、浮框列各曲线值、实时重绘不丢）。`tests/test_r7_features.py` 18 项 ＋ `tools/ui_r7_check.cjs` PASS 39/FAIL 0 ＋ 旧 harness 复跑 PASS 30/74
- **用户环境未验证（🔶，需按 `REPORT_TEST.md` T-002 执行包回填）**
  - Windows 安装与运行（含离线 wheel 安装侧、NSSM/任务计划常驻、防火墙放行）
  - 真实采集数据：编码、时间戳格式、电压是相/线、PT/CT 实际值、数据完整性
  - 与现场表计/其它系统的对账误差
  - TCP 实时协议帧格式（帧头/长度字段/缩放系数/字节序/时标类型；两种帧格式已用喂数器验证，真实协议未验证）
  - 生产部署形态（systemd/NSSM/nginx 反代）
  - **第 9 轮三项功能**（2026-10-13，`REPORT_TEST.md` T-007）：① 间谐波子界面（IEC 61000-4-7 组/中心子组/主导相量/TIHD，解析解对齐 1e-9）；② 直流偏置子界面（整周期均值、逐周期漂移、中性线直流）；③ 事件子界面（6 类事件状态机 + 阈值表单热生效 + REST/WS + CSV 落盘）。`tests/test_r9_events.py` 13 项 ＋ `tools/ui_r9_check.cjs` PASS 28/FAIL 0 ＋ 全量 **235 passed**；旧 harness 复跑 dropdown 74/74、r6 30/30、r8 29/29、r7 38/39（1 项为 jsdom 无 WS 推送下的摘要刷新时序，与本轮改动无关，详见 T-007）
- **已知缺口**
  - IEC 61000-4-7 的 10/15 分钟评估与 200 ms 聚合未实现（谐波/间谐波都是单窗值；间谐波分组本身 v0.8 已实现）
  - 事件阈值为单级固定限值（无分级告警、无持续时间门槛、无按时段/负荷的动态阈值）；功率振荡只看 P 总，不区分机电/次同步模态
  - Qt 桌面壳未实现（本轮决策：Web 优先，见 `STATUS.md` 决策记录）
  - 用户/权限、历史数据库落盘、报警推送未实现（当前为单机工具形态）
  - `TUNING_GUIDE.md` 未建
  - TCP 的 `timeout_s` / `reconnect_s`（各默认 2.0 s）只是构造参数，未暴露到配置文件与界面
  - 喂数器/追加器是**联调工具**，不是采集侧替代品：真实装置的帧头、校验、背压与断连行为仍需现场联调
  - `tools/ui_dropdown_check.cjs` 需 node ≥18 + jsdom，Python 侧环境不含 node 时只能跑静态契约测试（`tests/test_web_ui.py`）＋手工点检清单（§3.1）
  - 界面检查在 jsdom 中进行，**无真实浏览器渲染**：canvas 绘制以调用计数代替像素比对，CSS 置灰效果以 `disabled` 属性断言代替视觉核对

---

## 🗒 变更记录
- **v0.21（2026-10-15，导出指定时间段的原始周波数据）**：用户要求「总线侧与分路侧增加导出指定时间段的原始周波数据到 CSV」。①`NilmDetector` 新增**原始周波保留区**（独立于检测窗；每周波 P/Q/I × total/A/B/C；`nilm.cycle_keep_cycles` 默认 180000 ≈ 1 h@50 Hz、每侧约 19 MB，0＝不保留），`cycles_between(t_from, t_to)` / `keep_info()`，`summary().keep` 带出保留区范围。②`POST /api/nilm/cycles/export`（body `t_from/t_to`：时间文本或 epoch 秒，空＝保留区端点；`with_branch` 默认 true）写 `output/cycles_<起>_<止>.csv`，列 `source_id,cycle_idx,t_epoch_s,time_local,P_total,P_A,P_B,P_C,Q_total,Q_A,Q_B,Q_C,I_total,I_A,I_B,I_C`；**总线侧导出且启用分路侧时，分路侧同一时间段写进同一文件（source_id=1），按时间排序**；`/api/branch/nilm/cycles/export` 只导分路侧；时间非法 400、段内无数据 409。`GET` 同路径直接下载 CSV（不落盘）。③「负荷辨识」页新增「导出指定时间段的原始周波数据」面板：起止时间框、「填入保留区范围」、「导出到 CSV」、「直接下载」链接、保留区范围提示；参数表单增加「原始周波保留数」。测试 `tests/test_r21_cycles_export.py`（保留区裁剪与按段取数 / 两侧 Web 端到端含文件校验、400/409、GET 下载 / 前端契约）。
- **v0.20.1（2026-10-15，缺陷修复）**：用户反馈总览三相无功 / 视在功率曲线呈「散点」。根因：v0.19 给分相线设了 Q `[5,3]`、S `[2,2]` 的虚线并把线宽压到 1.1——趋势点 0.2 s 一个、三相数值几乎重合，三条短虚线叠在一起在屏幕上就成了一串点；数据本身连续（已核对 `/api/history/power` 各分相字段无空值）。修复：分相线全部改实线（线宽 1.3），按量取基色（P 粉 / Q 紫 / S 青），A/B/C 相用基色的亮 / 原 / 暗三档区分（`shadeColor()`）。
- **v0.20（2026-10-15，重启后各子界面自动恢复上次运行的数据）**：用户要求「软件重启后，各子界面展示的数据从上次运行保存的 CSV 文件或配置文件中加载和显示」。①**最新电气量快照落盘**：`EngineRunner.persist_last_result()` 把各量最近一次结果的并集（含频谱 series）写入 `output/last_result.json`——**两侧共用一个文件，按 `source_id`（"0" 总线 / "1" 分路）分键**，运行中每 ≥5 s、停止 / 播完 / 异常退出时各写一次（临时文件 + 原子替换，`SHARED_FILE_LOCK` 互斥；路径可用 env `ELEC_TOOL_LAST_RESULT_FILE` 覆盖，测试已隔离）。②**启动自动加载**：`_startup()` 在非自动播放时调用 `_autoload_last()`，对总线侧（及已启用的分路侧）执行 `load_last()`：曲线点 / 事件 / 负荷辨识事件来自 CSV（v0.18 链路），最新电气量来自 last_result.json → `/api/result` 与 WS 首帧 snapshot 直接返回，各子界面卡片、频谱、趋势、事件表开页即有数据；`state.loaded_last` 带 `auto: true`、`result`、`result_saved_at_local`、`result_source`。受新配置项 `output.autoload_last`（默认 true）与 env `ELEC_TOOL_AUTOLOAD_LAST=0` 控制。③手动「加载上次数据」同样恢复最新电气量并广播 snapshot。④界面：数据源页新增「软件启动时自动加载上次运行的数据」勾选（写入配置），提示行区分「软件启动时已自动加载 / 已加载」，并给出最新电气量的保存时间与来源文件。配置本身一直由 `configs/*.json` 持久化，无需改动。测试 `test_r20_restart_autoload`：播两侧→停止→校验 JSON 两键→模拟重启自动恢复两侧曲线与结果→关闭 autoload_last 后不加载。
- **v0.19（2026-10-15，总览 P/Q/S 趋势增加分相曲线）**：用户要求「总览面板 P/Q/S 趋势曲线增加三相 P/Q/S 趋势曲线展示，默认显示三相总的 P/Q/S」。`elec_tool/metrics.py` power 趋势记录在 `P/Q/S` 之后追加 `Pa/Pb/Pc、Qa/Qb/Qc、Sa/Sb/Sc`（取 `p_per_phase/q_per_phase/s_per_phase`，随 `/api/history/power`、实时落盘与保存曲线 CSV 一并输出）；总览总线侧 / 分路侧两张 P/Q/S 图（`ov-p`、`ov-p-br`）改为 12 条曲线：三相总 P/Q/S 默认显示，9 条分相曲线**默认隐藏**（相色 A 蓝 / B 绿 / C 橙，P 实线、Q 虚线、S 点线），在图下方图例勾选即显示，勾选状态仍存 `output.series_hidden`（新增「全部显示」哨兵 `*none*`，避免空列表被清洗后又回到默认隐藏）。`drawLine` 曲线新增 `defaultHidden` 属性，通用于其它图。注意：**当天已存在的 `power_<日期>.csv` 表头没有分相列，续写时分相值不落盘**（次日新文件或更换 `realtime_dir` 后自动带上）。
- **v0.18（2026-10-15，不播放时加载上次播放的数据）**：用户要求「界面上的各曲线在没有播放情况下支持直接加载上次播放的数据源计算的电气量数据或事件的数据」。实现：新增 `elec_tool/replay_load.py`（从 `output/realtime/<曲线>_<日期>.csv`、`output/events/events_<日期>.csv`、`output/nilm/nilm_events_<日期>.csv` 读回，**按本侧 `source_id` 过滤**，旧文件无来源号列视为总线侧，`*.v016.csv` 备份跳过，同一时刻重复行只留最后一条，事件 start/end 两行合并），`History.load_records` / `EventDetector.load_events` / `NilmDetector.load_events` 把读回数据替换进内存；`POST /api/history/load_last`（body 可选 `hours`、`curves`、`events`、`nilm`、`with_branch`；运行中返回 409；总线侧且分路启用时同时加载分路侧，结果在 `branch` 字段）；`/api/state` 新增 `loaded_last`。界面：顶栏与数据源页各加「加载上次数据」按钮（播放中置灰），成功后 toast 给出两侧点数/事件数/数据时间范围，各曲线页、事件页、负荷辨识页直接显示读回数据，数据源页显示「已加载上次播放数据…」提示；重新启动播放后被新数据覆盖。时间窗＝曲线最新点往前 `output.history_hours`（事件/负荷辨识事件同窗）。测试 `tests/test_r18_load_last.py`（纯函数 / 加载器 / 两侧 Web 端到端 / 前端契约）。
- **v0.17.3（2026-10-15，配置界面排版）**：用户 3 条要求：①勾选框与标题/标签对齐；②说明文字与正式配置项区分、缩进换行合理；③左标签 + 右输入框成对排列。实现为**前端统一规范化**而非逐个改 HTML：`app.js` 新增 `normalizeConfigForms()`（`init` 最先执行；负荷辨识页动态生成的算法参数表单也调用），对 `.form` / `.row2` 内每个带控件的 `<label>` 做结构化——勾选/单选项 → `label.chk`（flex、勾选框固定 14px 顶部对齐、标题 `.ttl` + 说明 `.note` 分两行）；普通项 → `label.f`（两列网格：左标签 `minmax(96px,34%)` / 右输入框，说明 `.note` 单独一行缩进到输入框列）；标签文字按规则拆分：`csv_file：` / `csv_file / csv_tail：` 这类适用范围前缀渲染为等宽小标签 `.scope`，「标题：说明」按全角冒号拆分，尾部「（说明）」超过 10 字才拆成说明行（短单位如「（周波）」「(s)」保留在标题里）；`.notes.muted` 说明块加左侧竖线并在网格里独占一行；`.row` / `.toggle` 内的行内勾选统一 inline-flex 居中。只改 DOM 结构不改 id / 文本，既有 `按 id 取元素` / `disabled` / `label.off` / `textContent` 约定全部保持（`test_web_ui` 15 项、`ui_r16` 31/31、`ui_r17` 36/36 通过）。窄屏（≤760px）退化为上下排列。顺带修正数据源页说明文字里过时的「输出到 output/branch/」。缺口：沙盒无浏览器截图能力，视觉效果按 CSS 推断，请在浏览器里核对；拆分规则是启发式，若有个别标签拆得不合适请指出。
- **v0.17.2（2026-10-15，所有落盘文件两侧共用）**：用户回报播放分路侧离线文件时仍生成 `output/branch/…` 目录与文件。根因：实时落盘 / 事件 / 负荷辨识三条链路的目录来自分路侧自己的配置（出厂 `output/branch/*`），v0.17.1 只合并了「保存曲线」。改为：分路侧的 `output.realtime_dir / output.export_dir / events.events_dir / nilm.nilm_dir` 在 `set_cfg/start` 时**强制与总线侧相同**（`_share_output_dirs`，总线侧改目录时分路侧跟着改），出厂模板 `configs/branch.json` 同步改为 `output/*`；两侧引擎各自的 writer 追加到**同一个** `realtime/<曲线>_<日期>.csv`、`events/events_<日期>.csv`、`nilm/nilm_events_<日期>.csv`，只用 `source_id` 列区分，新增进程内共享锁 `elec_tool/filelock.py` 保证表头只写一次、整行不交错。验证：`test_r17` 改为「同一目录只有 1 个 voltage 文件、表头 1 行、source_id 同时含 0/1、各行列数一致、分路侧配置里填的其它目录不会被创建」，`test_r14` 出厂目录断言随之改；全量 296 passed/1 skipped。旧版实时落盘文件（表头无 `source_id`）不再续写：首次写入时改名为 `<名>.v016.csv` 保留，新建带 `source_id` 的同名文件（否则两侧行混在旧文件里无法区分）。遗留：历史上已生成的 `output/branch/` 目录不会自动删除，可手工清理。
- **v0.17.1（2026-10-15，保存曲线：两侧数据同文件）**：用户要求「保存数据时分路侧数据和总线侧数据保存在同一个 CSV 文件中，不另外新建目录和文件」。`/api/curves/save` 改为每个 `<曲线>.csv` 内同时写总线行（`source_id=0`）与分路行（`source_id=1`），按时间排序、同一时刻总线行在前；不再创建 `branch/` 子目录。返回项 `files[].rows_bus / rows_branch / source_ids`，`branch_quantities / branch_skipped`（分路侧仍按自己的「保存曲线」勾选过滤；分路侧勾选而总线侧未勾选的曲线也会生成只含 source_id=1 的文件）。界面保存结果显示「N 点＝总线 a + 分路 b，同一文件按 source_id 区分」。验证：`test_r17` 同文件/无子目录/排序断言、`ui_r17` 36/36、全量 296 passed/1 skipped。说明：实时落盘（`output/realtime`）两侧仍各自按 `realtime_dir` 写（两侧引擎独立、目录可配置），未合并。
- **v0.17（2026-10-15，指定时间段播放 + 曲线缩放 + CSV 数据来源号）**：用户 3 条要求。①**指定时间段播放**（`source.play_window / play_window_start / play_window_end`，默认不启用，两侧各自独立，仅 csv_file）：启用后起点＝文件时标 ≥ 起始时间的第一条、终点＝结束时间（块起点 ≥ 终点即停）；起始留空＝从该文件数据起点、结束留空＝播到数据终点；起止可写 `YYYY-MM-DD HH:MM:SS` / epoch 秒 / 只写 `HH:MM:SS`（按文件时标当天折算，早于起点时刻视为次日）。启动时映射到既有运行期字段（`play_start_mode=time` / `play_end_time`），走 v0.15.3 的 `play_user` 通道——用户的播放起点设置与持久化配置都不会被自动值污染。两侧都是离线文件且启用「公共时间段」时以公共时间段为准（单侧时间段被忽略），公共时间段新增 **自定义播放结束时间** `branch.common_end`（空＝公共终点；越界 → 400 两侧都不启动；预览/启动结果带 `play_end / play_end_source`）。状态栏显示「播放终点」。②**曲线缩放**（所有 `drawLine` 折线图）：滚轮＝X 轴缩放（以光标为中心）、Shift+滚轮＝Y 轴缩放；鼠标拖选区间＝只显示该区间（水平拖选限定 X，矩形拖选同时限定 X/Y）；双击或图例行「复位」还原；图例行另有 X＋/X－/Y＋/Y－ 按钮。缩放状态按画布保存在前端内存 `ZOOM[canvasId]`（趋势图按绝对时间记录，数据滚动时视窗不漂移），只影响显示；缩回全图即自动清除；与悬停取值共存（悬停仍按视窗换算）。③**CSV 数据来源号** `source_id`（0＝总线、1＝分路，服务端按侧别强制，配置里填什么都会被改回）：实时落盘 `realtime/*.csv` 第 3 列、事件 `events_*.csv` / 负荷辨识 `nilm_events_*.csv` 首列、曲线保存 `curves_<ts>/*.csv` 第 3 列、合并下载 `/api/curves/export` 第 3 列、结果导出 `/api/export?fmt=csv` 首列。总线侧「保存曲线数据」且启用分路侧时，分路侧曲线一并保存到 `curves_<ts>/branch/<曲线>.csv`（按分路侧自己的「保存曲线」勾选过滤，返回 `branch_files / branch_skipped`）；合并下载同样包含分路侧行。**旧版实时落盘文件**（表头只有 `t_epoch_s,time_local` 两列固定头）的处理见 v0.17.2（改名保留、新建新结构文件）。验证：新增 `tests/test_r17_window_sourceid.py` 8 项（起止/只起/只止/未启用 4 种语义按样本数核对、HH:MM:SS 终点、common_end 生效与越界、两侧 source_id 与 branch/ 保存、合并/导出表头）、`tools/ui_r17_check.cjs` 35/35（两侧勾选联动、启动载荷、状态栏、公共时间段终点预览、滚轮/Shift 滚轮/双击/拖选/矩形拖选/按钮、CSV 来源号）；`ui_r16` 31/31、`ui_r14` 56/56（需 `TZ=Asia/Shanghai` 起服务与 node，且服务端需干净状态）；既有测试 6 处表头断言随列变化更新；全量 pytest **296 passed / 1 skipped**。缺口：柱状图（谐波/间谐波）与频谱不做缩放；缩放状态不持久化（刷新页面复位）；时间段播放只对 csv_file 生效（csv_tail/tcp/模拟器无此语义）；单侧时间段与公共时间段同时启用时不提示被忽略（只在 README 说明）。
- **v0.16（2026-10-15，界面重排 + 分路侧全输入方式 + 曲线分线开关）**：用户 6 条要求。①「数据源与控制」页重排为 **左列总线侧 / 右列分路侧** 的 4 行 × 2 列网格（数据源 / 量纲与口径 / 离线文件列映射 / 数据源状态），同类配置左右同行；页顶「分路侧设备联动」面板放启用开关、公共时间段、时标偏移/配对容差。②只有勾选「启用分路侧设备数据源」时右列与联动字段才显示（`.srcgrid.no-branch .col-br{display:none}`）。③分路侧输入方式与总线侧一样 4 种（csv_file / csv_tail / tcp / simulator），字段一一对应（`br-*` ↔ `src-*`），表单填充/联动/采集函数按前缀参数化共用（`fillSourceFields / syncSourceFields / collectSourceFields`）；服务端 `_start_branch_if_enabled` 不再限定两侧都是离线文件：两侧都是 csv_file 时共用节拍钟（倍速随总线侧、可按公共时间段），其它组合各自按自身配置同时启动（`synced_pace` 标识；公共时间段不适用时启动结果带 `common_window.reason`）；右列新增「单独启动分路侧 / 暂停 / 停止分路侧」与分路侧「数据源状态」栏（格式同总线侧）。顺带修复：旧版 `collectSourcePayload` 把播放起点字段放在 `csv_tail` 分支下，离线文件的「播放起点」从界面启动时其实没有发送（现随 csv_file 发送）。⑤多条曲线的图在画布下方给出**图例勾选**（如 Ua/Ub/Uc、P/Q/S、THD_U/THD_I），取消＝不画该线、全部取消时提示；状态按「图表 id → 隐藏曲线名列表」存入 `config.output.series_hidden`（新增字段，随配置持久化，重开页面仍保持；只影响显示，不影响计算/保存）。⑥总览面板分路侧 4 张曲线的标题栏与总线侧一致：「保存曲线」勾选（写分路侧 `config.output.curve_save`）+「最近 … · N 点（保留窗 h）」+ 播放状态文本。验证：新增 `tools/ui_r16_check.cjs` 31/31、`tests/test_r16_layout_series.py` 5 项，`ui_r14_check` 56/56（按新语义更新 3 项）、`ui_r13` 12/12、`ui_dropdown` 74/74，全量 pytest 288 passed/1 skipped。缺口：两侧都是离线文件以外的组合不做时间轴同步（各自实时）；图例勾选只对 `drawLine` 折线图生效，柱状图（谐波/间谐波）与频谱不含；`ui_r7/ui_r11` 的 2 项时区断言需服务端以 `TZ=Asia/Shanghai` 启动（沙盒 UTC 下为既有现象，非本轮回归）。
- **v0.15.4（2026-10-15，性能优化）**：用户「需要优化」→ 大文件播放起点定位改为非顺序扫描。`elec_tool/sources/parsing.py`：按时标（abs/tod）起点用**字节二分**（每次探测只读一行，解析失败或时标非单调自动回退顺序扫），按行号/按秒起点用 **8 MB 块计 `\n`** 直接算字节偏移；定位后仍做原有逐行精扫，结果（`t_start`、`skipped_rows`）与顺序扫逐项一致。`seek_info["method"]` 新增 `time(bisect)` / `row(bytes)` 标识。实测 300 s/1.92M 行文件：按时标 3.44 s→0.125 s、按行 1.79→0.108 s、按秒 1.93→0.107 s、tod 7.39→0.158 s、越界报错 4.7→0.153 s。假设/边界：文件 <4 MB（`SEEK_FAST_MIN_BYTES`）或无表头（首行即数据）仍走顺序扫；不支持带引号换行的字段；按行快速路径把空行也计入行号；percent 模式未变。新增 `tests/test_r15_4_fast_seek.py`（40 s 文件 fast vs 顺序一致、EOF/起点之前），全量 pytest 283 passed/1 skipped，ui_r14 56/56。
- **v0.15.3（2026-10-15，缺陷修复）**：用户反馈「离线文件启动后要过很久才开始」。根因：v0.15～v0.15.2 公共时间段联动启动把自动算出的 `play_start_mode=time/play_start_value=<epoch>/play_end_time` 写进了**活配置**（`/api/config` 直接读引擎配置），之后任何一次保存设置都把它们持久化；服务重启后内存里的还原表丢失，再播放别的文件就按这个陈旧时标**逐行扫到文件尾**才开始（或报起点越界）/ 按陈旧终点提前结束。修复：①自动起止只进引擎，`EngineRunner.cfg` 对外呈现用户自己的播放字段（`_play_user`），热更新也不互相覆盖；`play_end_time` 永不落盘；②启动时 `_sanitize_leaked_play` 清理旧版本已泄漏到 `configs/*.json` 的残留（裸 epoch 的 time 起点 → begin；非空 play_end_time → 清空；日志有记录）；③`_file_time_range` 改为字节计行 + 头尾 64 KB 取时标，不再 csv 解析整文件（5 min 文件 1.7 s → 0.16 s，1 小时文件两侧约 40 s → 4 s）。`test_r15_3_auto_play_fields_never_leak`，全量 pytest 281 passed/1 skipped，ui_r14 56/56。
- **v0.15.2（2026-10-15）**：**总览曲线两侧分开展示**——四类趋势（电压/电流/P-Q-S/THD）各拆成左「总线侧」、右「分路侧」两张独立画布，各用各的时间轴与纵轴，不再把分路侧虚线叠进总线侧坐标系；分路侧未启用时右列隐藏（`.ov-curves.no-branch`），分路侧面板标题处显示播放中/已播放完毕；公共时间段模式下两列坐标轴同为公共段。两侧按时标对齐与差值仍在「跨侧对比」页。ui_r14 56 项、全量 pytest 280 passed/1 skipped。
- **v0.15.1（2026-10-15）**：①**公共时间段模式下坐标轴固定**——启用 `branch.common_window` 时，总览四图与各子界面趋势图的时间轴固定为 [公共起点, 公共终点]（`drawLine` 新增 `tbase`，段外点不画），两侧、各页坐标轴一致，曲线随播放逐步填满；②**两侧严格同步**——新建 `elec_tool/pace.py::PaceClock`：共同墙钟起点 + 每侧各自数据起点 + 倍速的绝对限速（块时长按**各自采样率**算），联动启动两侧共用一只钟并互锁（块起点领先对侧进度 >0.1 s 即等待；第一块永远放行、不可能互相等待），暂停/恢复同步计入；`state.source.pace_clock` 可查两侧进度；③**长度不一致**——先播完的一侧 `finish()` 退出互锁、曲线与数据停在终值（总览提示「已播放完毕（数据停在终值）」且不再请求该侧），另一侧继续播放刷新。顺带修复三处会破坏同步/刷新的既有问题：定位后首块异常大（按块切分残留行）；运行线程在"读到块但无量到期"时也睡 `poll_interval`（吞吐压到 <1×）；两侧同时播完时 `state()` 互取对侧摘要的 AB/BA 死锁（对侧摘要改在持锁前取）；`/api/result?full=false` 改为各量最近值的并集（总览分路卡片不再闪「—」）。`tests/test_pace_clock.py` 3 项、`test_r15_1_pace_sync_and_merged_result`、ui_r14 55 项、全量 pytest 279 passed/1 skipped。
- **v0.15（2026-10-15）**：①**增量刷新**——`innerHTML/textContent` 写入与上次相同即跳过（不触碰 DOM），画布按数据签名（点数/首末点/中点/宽度）跳过无变化重绘，悬停重绘走 `force`；②**两侧播放倍速一致**——分路侧倍速字段移除，保存与联动启动时都强制取总线侧 `file_speed`；③**总览两侧放一起**——每张卡片同时显示总线/分路值（P 卡附总线−分路与占比），四张趋势图实线＝总线、虚线＝分路（按 `time_offset_s` 平移，无交集时按起点对齐并提示；**v0.15.2 起改为两侧分列独立画布**）；④**只播放公共时间段**——`config.branch.common_window`，联动启动前读取两侧文件时间范围（`_file_time_range`，支持自定义时间轴）取交集，两侧均以「时标 ≥ 起点」定位、`source.play_end_time` 封顶（csv_file 新增字段），无交集/起点越界 → 400 两侧都不启动；顶栏新增「公共时间段」行（起始/终止/总时长/播放起点），`GET /api/common_window?preview=1` 可先预览；⑤**自定义播放起始时间** `config.branch.common_start`（空＝公共起点，须在段内）。另：custom_time + 播放起点跳行时时间轴计入跳过的行；联动自动写入的起点/终点在下次非公共时间段启动时自动还原。ui_r14 51 项、`test_r15_common_window`。
- **v0.14.4（2026-10-14）**：顶部状态栏改为**总线侧 / 分路侧两行分开显示**（各自：状态、数据源、数据时刻、频率、fs、PT/CT、样本）；分路侧行**只显示不可点击切侧**（切侧只通过左侧导航分组）。对侧数据来自 state 中的对侧摘要（`_side_summary` 新增 `fs/pt_ratio/ct_ratio/f_used/t_ref/data_duration_s`），每秒随 WS 刷新。移除原「对侧胶囊」。ui_r14 40 项。
- **v0.14.3（2026-10-14）**：总览面板新增**分路侧设备区块**——最新电气量卡片（三相 U/I、P/Q/S、PF、频率、THD，另加「P：总线 − 分路」及分路占比的最新值对照）与四张分路侧趋势图（电压 / 电流 / P-Q-S / THD）；数据直接走 `/api/branch/result` 与 `/api/branch/history/*`，不切侧，随 state 推送每 ≥2 s 刷新；分路侧未启用时折叠为提示卡。ui_r14 38 项。
- **v0.14.2（2026-10-14）**：数据源页「离线文件列映射」拆成**总线侧 / 分路侧两块独立配置**（各自启用开关、7 列映射、填默认列序、按各自探查表头填入、独立保存按钮；分路侧列映射也随「保存分路侧配置」一并写入 `configs/branch_runtime.json`）。ui_r14 37 项。
- **v0.14.1（2026-10-14）**：按用户 5 条要求补齐双侧机制——①分路侧配置**全部集中**在总览的「数据源与控制」页（分路侧分组不再有数据源项）；②两侧导航徽标（事件 / 负荷辨识）都实时刷新：当前侧用引擎计数，对侧用 state 中的对侧摘要（`branch` / `bus`，含 `events_active`）；③**跨侧时间轴对齐与差值**：`GET /api/compare/{quantity}`（最近邻配对，`offset_s` 分路侧时标偏移、`tol_s` 容差默认＝输出步长×0.6；返回 `bus/branch/diff(总线−分路)/ratio_pct(分路/总线)`）与 `GET /api/compare`（各量最新一组），总览组新增「跨侧对比」页（表格 + 两侧曲线 + 差值/占比曲线 + 「按起点对齐」+ 保存偏移），偏移/容差存总线侧 `config.branch.time_offset_s / align_tol_s`；④顶栏**始终**显示对侧状态胶囊（总线侧看分路侧、分路侧看总线侧，标签随侧切换）；⑤总线侧与分路侧的**量纲与口径分别配置、分别保存**（PT/CT、fs、额定频率、频率自适应、电压列含义、最高谐波次数、S/Q 口径——分路侧写入 `configs/branch_runtime.json`）。ui_r14 36 项、全量 pytest 275。
- **v0.14（2026-10-14）**：左侧导航按侧别重组为三组——①「总览」＝总览面板 + 数据源与控制（总线侧上下文，总览面板顶部新增两侧数据源状态卡）；②「总线侧」＝总线侧数据源计算的全部电气量子界面（电压…负荷辨识 + 窗口配置 / 导出）；③「分路侧」＝分路侧设备数据源计算的同一套子界面（另含「分路侧数据源与口径」用于改采样率 / PT-CT）。侧别由点击的导航分组决定（不再有顶栏切换按钮、不再记忆到 localStorage），分组标题徽标显示分路侧运行状态；「工具」组放算法自检 / 数据处理。ui_r14 27 项。
- **v0.13.1（2026-10-14）**：分路侧限定离线文件模式——面板改为固定 csv_file + 文件参数（探查 / 选择 / 倍速 / 自定义时间 / UTC / 块大小），总线侧非离线文件时不联动并提示；ui_r14 23 项。
- **v0.13（2026-10-14，第 14 轮）**：总线侧 + **分路侧设备**双数据源——独立配置/引擎/输出，`/api/branch/*` 与 `/ws/branch`，顶栏侧别切换，总线侧启动/停止/暂停/恢复联动分路侧；`tests/test_r14_branch.py` 4 项、`tools/ui_r14_check.cjs` 19 项，全量 274 passed。
- **v0.12.2（2026-10-14，F-42）**：离线文件**播放倍速** `source.file_speed`（界面「离线文件播放倍速」默认 1× 真实速率；0＝不限速为配置/CLI 默认）——此前不限速导致几秒播完、暂停按钮点下去已结束（400）；静态资源版本号 + no-cache；状态看门狗无条件校对。`tests/test_r13b_file_speed.py` 4 项、`tools/ui_r13_check.cjs` 12 项，全量 270 passed。
- **v0.12.1（2026-10-14，F-41）**：离线文件播完界面不自动翻「已完成」——终态 state 推送移到引擎停止之后、WS 状态推送抗异常、前端 2 s 状态看门狗；回归用例 1 项，全量 266 passed。
- **v0.12（2026-10-14，第 13 轮）**：离线文件源**暂停 / 恢复播放**（`POST /api/engine/pause|resume`、顶栏与数据源页按钮、状态 `paused/pausable/paused_total_s`）；`tests/test_r13_pause.py` 3 项，全量 265 passed。
- **v0.11.2（2026-10-14）**：新增 `NILM_TUNING_GUIDE.md`（负荷辨识 6 算法调参手册，运维版）与 `tools/nilm_tune.py`（噪声统计 + 参数建议）+ 2 项自检用例。
- **v0.11.1（2026-10-13，F-40 热修）**：Windows 下离线文件（`0/00/00` 时标）启动后负荷辨识/事件接口 500（`localtime` 不接受负 epoch）：无日期时标基准改为 **1970-01-02**（按本地时间解释后恒为正）；新增 `elec_tool/timefmt.py` 作为所有「epoch → 本地时间文本」的统一安全出口（localtime 失败自动手工换算），nilm / events / 实时落盘 / 导出 / probe / CLI 全部改走。回归 `tests/test_f40_negative_epoch.py`。
- **v0.11（2026-10-13，第 12 轮）**：新增 **「负荷辨识」子界面**：`elec_tool/nilm.py`（逐周波 P/Q/I 特征 + 6 种突变检测算法：阈值差分 / 双滑窗均值差 / CUSUM / GLR / 稳态分段(Hart) / 中值滤波差分；事件含算法、对象、起止时刻、方向、幅值 ΔP/ΔQ/ΔI；跨块去重与确认；`output/nilm/nilm_events_<日期>.csv` 落盘）；`NilmConfig` 全参数可配（含相对门槛 `rel_tol_pct/min_delta_pct`）；引擎逐块摄入；REST `/api/nilm/events|cycles|clear` + WS `nilm_event`；界面：卡片、周波窗曲线（事件竖线标注）、事件表（算法/对象过滤）、按算法生成的参数表单。`tests/test_r12_nilm.py` 8 项、`tools/ui_r12_check.cjs` 16 项、`tools/gen_nilm_sample.py`；全量 **257 passed**。
- **v0.10（2026-10-13，第 11 轮）**：新增 **离线文件时标 UTC 开关** `source.file_time_utc`（默认 false）：未启用自定义播放时间时，文件里的日期时间 / `0/00/00 HH:MM:SS` 文本时标按本机本地时间解释，**曲线、落盘 CSV、事件时间与文件中的时间一致**；true 则视为 UTC 换算显示（旧行为）。`create_source/LiveEngine` 的 `tz_offset_h` 默认改为按配置推导；`/api/probe` 增 `file_time_utc/tz_offset_h/t_first_local`；`/api/engine/start` 白名单放行；CLI `--file-time-utc`；界面勾选框随「自定义播放时间」联动。`tests/test_r11_file_time.py` 6 项、`tools/ui_r11_check.cjs` 11 项；全量 **249 passed**（UTC 与 Asia/Shanghai 双时区）。
- **v0.9（2026-10-13，第 10 轮）**：新增 **离线文件列映射开关** `columns.mapping_enabled` / `columns.mapping`：未启用＝默认列序「时间,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流」（可识别表头仍按表头）；启用＝只播放有映射的列（列号或表头名），未映射通道按 0 并提示，时间戳未映射按 fs 合成连续时间轴。`ColumnMap.layout()/looks_like_header()/validate()` 成为离线取列唯一规则（parsing / probe / CLI probe / 重采样预扫描共用）；界面「数据源」页新增面板（开关 + 7 字段 + 默认列序 / 按探查表头填入）；`/api/probe` 增 `mapping_enabled/unmapped/ncols`。`tests/test_r10_colmap.py` 8 项、`tools/ui_r10_check.cjs` 15 项；全量 **243 passed**。
- **v0.8.1（2026-10-13，F-32 热修）**：去掉事件告警的右下角弹出提示（事件多时刷屏）；活动事件数仍显示在导航徽标，明细在「事件」页。
- **v0.8（2026-10-13，第 9 轮）**：新增 **「间谐波」「直流偏置」「事件」三个子界面**。电气量 7→9（`interharmonic`、`dc`，各自独立窗长/趋势/落盘/导出），曲线 6→8；`elec_tool/events.py` 事件检测（基波相量/谐波相量/间谐波相量/频率/ROCOF 超限 + 功率振荡；开始/峰值/复归滞回、阈值热改即复归、数据时间、`output/events/events_<日期>.csv`）；`EventConfig` 全部阈值可配置（含 `limits_secondary` 按 PT/CT 自动折算）；REST `GET /api/events`、`POST /api/events/clear`，WS `type=event`。`tests/test_r9_events.py` 13 项、`tools/ui_r9_check.cjs` 28 项；全量 **235 passed**。
- **v0.7（2026-10-12，第 8 轮）**：新增 **「数据处理」子界面**——离线波形 CSV 按指定采样率重采样到 `data/<原名>_re_<fs>.csv`（`elec_tool/resample.py`：linear 流式 / nearest / fft 抗混叠；时间戳按源写法重生成；表头/编码/BOM 保留；后台任务＋进度＋取消）；REST 4 个接口；CLI `resample`；`tests/test_r8_resample.py` 16 项、`tools/ui_r8_check.cjs` 29 项。测试 **222 passed**。
- **v0.6.2（2026-10-12）**：修复 **F-23**——离线文件播放时顶栏「样本」/「数据源状态」汇总不自动更新：`/ws` 改为每 1 s 定期推送 `state`（`WS_STATE_INTERVAL_S`），不再依赖队列空闲。测试 **206 passed**。
- **v0.6.1（2026-10-12）**：修复 **F-22**——用局域网 IP 访问（或浏览器缩放≠100% / Windows 125% 缩放）时页面每次刷新纵向拉伸：`prep()` 不再回读被 `canvas.height` 改写的 `height` 属性，逻辑高度缓存于 `data-h`。测试 204→**205 passed**。
- **v0.6（2026-10-12）**：三项功能。① **实时落盘**：新增 `elec_tool/realtime_writer.py`，引擎每算出一个曲线点就追加到 `output/realtime/<曲线>_<数据日期>.csv`（与趋势曲线/手工保存同一提取规则 `metrics.curve_record`；按数据时间日期分文件；追加不重复表头；每次 flush；受 `output.curve_save` 过滤；配置 `output.realtime_save/realtime_dir`，环境变量 `ELEC_TOOL_REALTIME_DIR` 优先；热更新重建写入器）；`GET /api/realtime`；「导出与日志」页新增面板；CLI `--realtime-save on|off --realtime-dir`，收尾诊断打印落盘行数。② **离线播放起点**：`source.play_start_mode/play_start_value`（`begin/row/seconds/percent/time`），`iter_csv_blocks` 新增 `skip_rows/start_percent/start_time`（percent 按字节定位对齐行首；time 分块顺序扫描时标列，支持只填 `HH:MM:SS` 与当天时刻比较）；超出文件范围抛可诊断 `ParseError`；界面下拉框＋取值框（csv_file 下可用、begin 时取值框置灰、占位说明随模式变化），启动白名单放行，状态摘要显示跳过行数；CLI `--play-from 模式:值`。③ **曲线悬停取值**：`drawLine` 挂 `cv.__chart`、只绑定一次 `mousemove/mouseleave`、重绘末尾叠加十字线＋圆点＋浮框（趋势图提示含毫秒，频谱为 Hz），实时推送重绘不丢。新增 `tests/test_r7_features.py`（18 项）与 `tools/ui_r7_check.cjs`（PASS 39/FAIL 0）；修 r6 Web 测试「finished 后 flush_all 尚未完成」的等待竞争。测试 186→**204 passed, 1 skipped**。取证见 `REPORT_TEST.md` T-005。

- **v0.5（2026-10-12）**：四项功能。① 离线 CSV 支持用户采集器时标 `0/00/00 00:12:40.0000`（日期段全 0 → 当天时刻、跨午夜自动展开、0.1 ms 截断下 fs 仍按线性拟合推算；无表头文件在 `/api/probe`、CLI、Web 三处都正确识别；顺带修复无表头文件把时间戳列记为「非数值单元格」的噪声告警）。② 所有趋势曲线改为**最近 24 h（按数据时间，不足则全部）**：`History` 改为按时间修剪的紧凑列存储（`array('d')`、线程安全、50 万点上限），`/api/history` 新增 `hours/max_points` 与峰谷保形抽稀，前端不再固定取 400 点，横轴跨度 >1 h 自动省略毫秒，面板标题标注跨度/点数；热更新（含已结束的离线引擎）不再清空历史与结果。③ 每条曲线可单独勾选「保存曲线数据」（`output.curve_save`，面板右上角与导出页同一份配置），新增 `POST /api/curves/save`（写 `output/curves_<ts>/<曲线>.csv`）与 `GET /api/curves/export`，未勾选项严格跳过。④ 离线播放「自定义播放时间」（`source.custom_time/custom_time_start`，CLI `--custom-time[-start]`，界面勾选框＋起始时间框只在 csv_file 下可用）。新增 `tests/test_r6_features.py`（25 项）与 `tools/ui_r6_check.cjs`（PASS 30/FAIL 0）。测试 161→**186 passed, 1 skipped**。取证见 `REPORT_TEST.md` T-004。
- **v0.4（2026-10-10）**：§3.1 新增「数据源面板：4 种输入方式的联动、空值语义与两个保存入口」（含逐源可编辑/置灰字段表、`PUT /api/config` 深合并 vs `POST /api/engine/start` 白名单对照、6 步手工点检清单）。修复 Web 界面 5 个缺陷（F-06~F-10）：数据源两个下拉框无联动、载荷发送空值、空数字框导致保存必 400、实时推送覆盖用户正在编辑的表单、启动按钮夹带被服务端忽略的配置段；新增逐源填写说明 `#src-hint` 与未保存提示 `#src-formnote`。新增 `tools/ui_dropdown_check.cjs`（jsdom 端到端，实测 PASS 74/FAIL 0）与 `tests/test_web_ui.py`（前端契约静态检查 14 项，撤销修复必 FAIL 已验证）。测试 147→**161 passed, 1 skipped**。取证见 `REPORT_TEST.md` T-003 S14~S16。
- **v0.3（2026-10-10）**：§4 重写为「四种数据源详解」——每源给出完整配置字段（含默认值与约束）、CLI/Web/库三种运行方式、沙盒实测输出、注意事项与可复现的验证方法，并新增 §4.6 四源横向对账表与 §4.8 一键复现。新增 `tools/`（`tcp_feeder.py` TCP 喂数器、`csv_appender.py` CSV 追加喂数器、`verify_sources.py` 库级四源验证，实测 PASS 5/FAIL 0）。修复本轮实测发现的 4 个问题：`csv_tail` 目录分片切换丢一整块（含回归测试）、二进制帧格式不匹配导致 CLI 崩 `OverflowError`（解析层闸门＋显示层兜底＋可诊断降级）、实时源告警未去重、float32 存 epoch 秒的时标量化无告警；补齐 `cli.py live` 的 `--frame/--struct-fmt/--struct-fields` 与界面 TCP 面板两个输入框。测试 141→**147 passed, 1 skipped**。取证见 `REPORT_TEST.md` T-003。
- **v0.2.1（2026-10-10）**：补齐 csv_tail 的两个现场关键开关（`--from-end` / `--watch-newest` + 界面勾选框），此前只能改配置文件；README 中缓冲容量、内存占用、退出码、目录模式默认值等数字全部改为代码级/实测值（原先为估算）。
- **v0.2（2026-10-10）**：代码落地后全面回填。**新增「本地详细部署与运行说明」**（§2 部署：环境要求/取码/venv/在线与内网离线安装/最小安装/5 条验证命令/目录结构/安装故障表；§3 运行：Web 界面（启动、参数与环境变量、访问与反代、12 个子界面导览、常驻与开机自启）、CLI 7 子命令逐条实测命令与输出、Python 库嵌入示例、REST/WS 接口清单、运行故障表；§4 接真实数据；§9 生产推荐流程）。§1/§5/§6/§7/§8 由占位改为沙盒实录事实，原 🔶 项按「沙盒已验证 ✅ / 用户环境待确认 🔶」重新标注。同步记录本轮修复的两个真 bug（引擎线程换代竞争导致双重摄入；`plan_window` 绝对容差导致 1s 窗实际只算 0.98s），并要求 Windows 命令一律标 🔶未实测。
- v0.1（2026-10-10）：按 BOOTSTRAP v2.2 台账要求初始化骨架，项目环境/数据/命令/配置/产物/流程 6 类内容全部标 🔶待确认。
