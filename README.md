# README.md — nilm_calc_tool（电力系统各类电气量计算工具）

> 台账文件（BOOTSTRAP.md v2.2）：安装与环境 / 运行命令 / 数据目录 / 配置结构 / 输出产物 / 生产推荐流程。
> **当前状态：v0.2（2026-10-10）**——软件已实现并在沙盒跑通（算法核心 + 4 类数据源 + 计算引擎 + CLI + Web 界面 + 142 项测试）。
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
| ⑤ | 三相电压/电流、功率因数、有功、无功、基波、谐波(2–50)、频谱 | `elec_tool/analysis/{rms,harmonic,power,window}.py` + `metrics.py` | 数值对齐解析解（`expected_values()`），见 §8 | ✅沙盒 |
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
├── data/                      # 输入 CSV（gitignore，不入库）
├── output/                    # 导出结果（gitignore）
├── tests/                     # 142 项测试（单元 + 端到端 + Web 层）
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

### 3.2 方式二：CLI（7 个子命令，全部实测）

```
.venv/bin/python cli.py --help      # 实录：init-config / gen-sample / selftest / sources / compute / live / serve
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

# TCP 流（真实协议帧格式待确认 🔶）
.venv/bin/python cli.py live --source tcp --host 192.168.1.50 --port 9000
# csv_tail 专用开关（本轮新增，实测）：
.venv/bin/python cli.py live --source csv_tail --path data/live.csv --from-end --duration 1
# ✓ 结束：输出 0 次，样本 0   ← 从文件末尾起只算新写入数据；静态文件没有新增故为 0，不报错
.venv/bin/python cli.py live --source csv_tail --path data/ --watch-newest --duration 1
# ✓ 结束：输出 13 次，样本 16640   ← 路径给目录时自动跟目录内 mtime 最新的 CSV
# 参数：--source {simulator,csv_tail,tcp} --path --host --port --block --pace(速率倍数,0.001≈全速)
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
| `POST /api/engine/start` | 启动引擎；body 可覆盖 `kind/path/host/port/frame/block_samples/poll_interval_s/tail_from_end/sim_speed/watch_dir_newest/windows/duration_s` |
| `POST /api/engine/stop` | 停止引擎（结果仍可查询/导出） |
| `GET /api/result?full=true|false` | 最新结果；`full=true` 强制按当前缓冲把七类量都算一遍，`false` 取最近缓存；无结果返回 409 |
| `GET /api/history/{quantity}?n=300` | 某量历史趋势点（`t` 非递减） |
| `GET /api/export?fmt=csv|json&quantity=` | 导出累计结果（CSV 扁平表 / JSON 全量）；未知 `fmt` 返回 400；无结果 409 |
| `GET /api/selftest?fs=&freq=&pt=&ct=&window=` | 一键 44 项解析解自检 + 运行环境 |
| `GET /api/probe?path=` | 数据体检（表头/编码/行数/时间戳模式/推算 fs/偏差） |
| `GET /api/files?sub=data` | 列目录下的 CSV |
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

## 4. 接你的真实数据（现场部署关键）

### 4.1 数据格式（用户已确认的事实）

| 项 | 内容 | 状态 |
| --- | --- | --- |
| 采集对象 | 二次侧三相电压、三相电流 | ✅（来源：用户 2026-10-10 需求描述） |
| 采样频率 | 6400 Hz | ✅（同上；奈奎斯特 3200 Hz，50 次谐波=2500 Hz 不混叠） |
| 存储 | CSV | ✅（同上） |
| 列格式 | `时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流` | ✅（同上；`configs/default.json` 的 `columns` 已按此设置） |
| 变比 | PT=100、CT=15，均可配置 | ✅（同上；界面/配置/CLI 三处都可改） |
| 电压是相电压还是线电压 | 默认按**相电压**处理（`transform.voltage_input=phase`） | 🔶待确认（若现场给的是线电压，改成 `line`） |
| 时间戳格式 | epoch 秒 / `YYYY-MM-DD HH:MM:SS.ffffff` / epoch 毫秒 三种都能自动识别 | ✅解析器实录；**你的采集器实际用哪种** 🔶待确认 |
| 文件编码 | utf-8-sig/utf-8/gb18030/gbk/big5/latin-1 自动探测 | ✅解析器实录；**你的实际编码** 🔶待确认 |
| 实时传输方式 | 目前是「采集器写 CSV → 本工具 tail 追加读取」或 TCP 流；TCP 帧格式未定 | 🔶待确认（TCP `frame`/`struct_fmt` 需按真实协议填） |

### 4.2 离线文件（拿一段历史数据算）

1. 把 CSV 放进 `data/`（该目录已 gitignore，不会误传）；
2. 体检：`cli.py sources --file data/你的.csv`（看编码/列映射/推算采样率是否符合预期）；
3. 算：`cli.py compute --file data/你的.csv --format table`，或界面上「数据源与控制」→ 源选 `离线文件(csv_file)` → 填路径 → 启动；
4. 需要 5s 电压有效值：界面「窗口配置」把 voltage 改 5s（或 `--set-window voltage=5`），其余量不受影响。

### 4.3 实时采集（采集器边写边算）

```bash
cli.py live --source csv_tail --path data/live.csv              # 给文件：监视追加，默认从文件头补算历史
cli.py live --source csv_tail --path data/live.csv --from-end   # 只算启动之后新写入的数据
cli.py live --source csv_tail --path data/                      # 给目录：自动跟 mtime 最新的 CSV
```

| 开关 | 默认 | 含义 | 在哪设 |
| --- | --- | --- | --- |
| `tail_from_end` | `false` | false=从文件头补算历史；true=只算新增 | CLI `--from-end`；界面「数据源与控制」勾选框；配置 `source.tail_from_end` |
| `watch_dir_newest` | **`true`** | path 为目录时自动跟最新 CSV（采集器按天/按段换文件时有用） | CLI `--watch-newest`；界面勾选框；配置 `source.watch_dir_newest` |

界面等价操作：源选 `实时·文件追加（csv_tail）` → 填路径 → 按需勾选上面两项 → 启动。
时间跳变（>1.5 个采样间隔）会被记为**数据缺口**并在界面「导出与日志」中告警。✅沙盒实录

### 4.4 TCP 实时流 🔶

`source.kind="tcp"` + `host/port` + `frame`（`text_csv` 文本行 / `struct` 二进制）+ `struct_fmt`/`struct_fields`。
**真实协议帧格式（字节序、字段顺序、缩放系数、帧头帧尾）尚未取得**，需按现场协议文档填写后联调；在此之前建议走「采集器落 CSV + csv_tail」路线。

### 4.5 PT/CT 与一次/二次值口径

- `一次值 = 二次值 × 变比`；`功率变比 = PT × CT`（默认 PT=100、CT=15 → 功率乘 1500）。
- `transform.enabled=false`（或 `--no-scale`）→ 直接输出二次值，便于与现场表计对账。
- 界面上所有卡片默认显示**一次值**，单位随之为 V/A/W/var。✅（`scaling.py` + 测试 `test_engine_applies_pt_ct` / `test_no_scale_option_uses_secondary`）

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
| `source` | `kind` | `simulator` | `csv_file`/`csv_tail`/`tcp`/`simulator` |
| | `path` / `host` / `port` / `frame` / `struct_fmt` / `struct_fields` | — | 各源参数（TCP 帧格式 🔶待确认） |
| | `block_samples` / `poll_interval_s` | 640 / 0.05 | 每块点数与轮询间隔 |
| | `tail_from_end` / `watch_dir_newest` | false / **true** | csv_tail 行为：只算新增 / 目录模式跟最新文件（CLI `--from-end`、`--watch-newest` 与界面勾选框可改） |
| | `sim_f` / `sim_harmonics` / `sim_noise_ratio` / `sim_unbalance` / `sim_speed` | 50 / {3:0.08,5:0.06,7:0.03,11:0.015,13:0.01} / 0.002 / 0.02 / 1.0 | 模拟器参数（`sim_speed>1` 加速联调） |
| `output` | `history_len` / `export_dir` / `spectrum_max_points` | 900 / `output` / 1200 | 历史点数、导出目录、频谱显示抽稀上限 |
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
| 历史趋势 | `GET /api/history/{quantity}?n=` | 每量独立时间序列（`t` 非递减） | ✅沙盒实录 |
| 自检报告 | `cli.py selftest --json`、`GET /api/selftest`、界面「算法自检」 | 44 项：`id/name/expected/actual/tol_rel/rel_err/ok/unit/note` + 运行环境（Python/OS/numpy） | ✅沙盒实录 |
| 告警与缺口 | 界面「导出与日志」、结果 `notes` 字段 | 整周期截断、频谱抽稀、NaN 插值、采样率偏差、数据缺口、功率残差、口径退化提示 | ✅沙盒实录 |

---

## 8. 验证与自检（三层，逐层可复现）

| 层 | 命令 | 期望结果（沙盒实录） | 作用 |
| --- | --- | --- | --- |
| 1. 算法解析解 | `cli.py selftest` | 44 项全 PASS，最差相对误差 1.508e-05，中位 1.1e-15 | 证明**计算口径正确**，不需要真实数据 |
| 2. 回归测试 | `.venv/bin/python -m pytest tests/ -q` | 141 passed, 1 skipped（约 55 s） | 证明解析/调度/Web 接口/边界行为未回退 |
| 3. 端到端实跑 | `cli.py compute --file data/sample_6400hz.csv` | 输出 26 次，emits 分层（快量 26 / 慢量 6） | 证明全链路（读→缩放→切窗→计算→输出）通 |

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
  - 算法：`selftest` 44/44（最差 1.508e-05）；`pytest tests/ -q` 141 passed, 1 skipped
  - CLI：7 个子命令逐条实跑（含 `--set-window`、`--format csv/json/table`、`--pace`、`--ts-format`）
  - Web：页面与静态资源 200、12 个子界面、REST 12 组端点、WebSocket 推送与降级、配置热更新与持久化分离、导出 34.6 万行 CSV
  - 实时：模拟器 6400 点/s 稳定摄入（实测 6398–6400 点/s），各量按独立窗长输出（0.2s 量 5 次/s、1s 量 1 次/s）
- **用户环境未验证（🔶，需按 `REPORT_TEST.md` T-002 执行包回填）**
  - Windows 安装与运行（含离线 wheel 安装侧、NSSM/任务计划常驻、防火墙放行）
  - 真实采集数据：编码、时间戳格式、电压是相/线、PT/CT 实际值、数据完整性
  - 与现场表计/其它系统的对账误差
  - TCP 实时协议帧格式
  - 生产部署形态（systemd/NSSM/nginx 反代）
- **已知缺口**
  - IEC 61000-4-7 谐波分组（10/15 分钟评估、分组平方和）未实现，当前为整周期矩形窗口径（已在代码与文档标注）
  - Qt 桌面壳未实现（本轮决策：Web 优先，见 `STATUS.md` 决策记录）
  - 用户/权限、历史数据库落盘、报警推送未实现（当前为单机工具形态）
  - `TUNING_GUIDE.md` 未建

---

## 🗒 变更记录

- **v0.2.1（2026-10-10）**：补齐 csv_tail 的两个现场关键开关（`--from-end` / `--watch-newest` + 界面勾选框），此前只能改配置文件；README 中缓冲容量、内存占用、退出码、目录模式默认值等数字全部改为代码级/实测值（原先为估算）。
- **v0.2（2026-10-10）**：代码落地后全面回填。**新增「本地详细部署与运行说明」**（§2 部署：环境要求/取码/venv/在线与内网离线安装/最小安装/5 条验证命令/目录结构/安装故障表；§3 运行：Web 界面（启动、参数与环境变量、访问与反代、12 个子界面导览、常驻与开机自启）、CLI 7 子命令逐条实测命令与输出、Python 库嵌入示例、REST/WS 接口清单、运行故障表；§4 接真实数据；§9 生产推荐流程）。§1/§5/§6/§7/§8 由占位改为沙盒实录事实，原 🔶 项按「沙盒已验证 ✅ / 用户环境待确认 🔶」重新标注。同步记录本轮修复的两个真 bug（引擎线程换代竞争导致双重摄入；`plan_window` 绝对容差导致 1s 窗实际只算 0.98s），并要求 Windows 命令一律标 🔶未实测。
- v0.1（2026-10-10）：按 BOOTSTRAP v2.2 台账要求初始化骨架，项目环境/数据/命令/配置/产物/流程 6 类内容全部标 🔶待确认。
