"""Web 前端静态一致性测试（不需要起服务、不需要 node）。

这些测试盯的是**界面与后端契约**这一层，全部来自 T-003 下拉框专项检查（缺陷 F-06~F-09）：
前端选项与 `elec_tool.config` 的枚举脱节、app.js 引用了 HTML 里不存在的元素、
下拉框没注册联动、空输入框被 `+''===0` 变成 0 送出去 —— 这类问题在 pytest 里跑不出来，
但会让用户「选了没反应／保存必 400」，所以用文本级断言钉住。

界面真实交互（选中→启用禁用→载荷→服务端回显）由 `tools/ui_dropdown_check.cjs` 端到端验证。
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from elec_tool.config import APPARENT_MODES, REACTIVE_MODES, SOURCE_KINDS, VOLTAGE_INPUT_MODES

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
APPJS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")

# config.py:301 `frame: str = "text_csv"  # text_csv | binary`（后端无常量元组，此处显式对齐）
TCP_FRAMES = ("text_csv", "binary")


class _SelectCollector(HTMLParser):
    """把 <select id=...> 下所有 <option> 的**生效值**抓出来（无 value 属性时取文本）。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.selects: dict[str, list[str]] = {}
        self.ids: set[str] = set()
        self._cur: str | None = None
        self._in_option = False
        self._opt_value: str | None = None
        self._opt_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if d.get("id"):
            self.ids.add(d["id"])
        if tag == "select":
            self._cur = d.get("id")
            self.selects.setdefault(self._cur or "", [])
        elif tag == "option" and self._cur:
            self._in_option = True
            self._opt_value = d.get("value")
            self._opt_text = []

    def handle_endtag(self, tag):
        if tag == "option" and self._in_option and self._cur:
            text = "".join(self._opt_text).strip()
            self.selects[self._cur].append(self._opt_value if self._opt_value is not None else text)
            self._in_option = False
        elif tag == "select":
            self._cur = None

    def handle_data(self, data):
        if self._in_option:
            self._opt_text.append(data)


@pytest.fixture(scope="module")
def page() -> _SelectCollector:
    p = _SelectCollector()
    p.feed(HTML)
    return p


@pytest.mark.parametrize(
    "select_id, expected",
    [
        ("src-kind", SOURCE_KINDS),                 # 数据源输入方式：4 种
        ("src-frame", TCP_FRAMES),                  # TCP 帧格式
        ("cfg-uin", VOLTAGE_INPUT_MODES),           # 电压输入口径：相/线
        ("cfg-apparent", APPARENT_MODES),           # 视在功率口径
        ("cfg-reactive", REACTIVE_MODES),           # 无功功率口径
    ],
)
def test_select_options_match_backend_enums(page, select_id, expected):
    """下拉框选项必须与后端枚举一一对应（集合相等），否则会出现「选了后端不认」。"""
    assert select_id in page.selects, f"index.html 缺少 #{select_id}"
    assert set(page.selects[select_id]) == set(expected), (
        f"#{select_id} 选项 {sorted(page.selects[select_id])} 与后端枚举 {sorted(expected)} 不一致"
    )


def test_spectrum_selects_are_self_consistent(page):
    """频谱面板三个下拉框属前端自有枚举：通道 6 相、比例 2 种、频段上限为数字。"""
    assert set(page.selects["sp-chan"]) == {"Ua", "Ub", "Uc", "Ia", "Ib", "Ic"}
    assert set(page.selects["sp-scale"]) == {"lin", "db"}
    assert page.selects["sp-limit"], "#sp-limit 无选项"
    for v in page.selects["sp-limit"]:
        assert re.fullmatch(r"\d+", v), f"#sp-limit 选项 {v!r} 不是数字（前端按 parseInt 处理）"


def test_appjs_only_references_existing_element_ids():
    """app.js 里 $('#id') / getElementById('id') 指向的元素必须在 HTML 中存在（F-06 类拼写/漏加）。"""
    refs = set(re.findall(r"""\$\(\s*['"]#([A-Za-z][\w-]*)""", APPJS))
    refs |= set(re.findall(r"""getElementById\(\s*['"]#?([A-Za-z][\w-]*)['"]""", APPJS))
    assert refs, "没抓到任何元素引用，正则可能失效"
    parser = _SelectCollector()
    parser.feed(HTML)
    missing = sorted(refs - parser.ids)
    assert not missing, f"app.js 引用了 HTML 中不存在的元素 id：{missing}"


@pytest.mark.parametrize("select_id", ["src-kind", "src-frame"])
def test_source_selects_have_change_listener(select_id):
    """F-06：两个数据源下拉框必须注册 change（联动禁用无关字段＋切换填写说明）。"""
    pat = rf"""\$\(['"]#{select_id}['"]\)\.addEventListener\(\s*['"]change['"]"""
    assert re.search(pat, APPJS), f"#{select_id} 没有 change 监听：选了不会联动"


def test_form_has_dirty_guard_and_sync():
    """F-09：实时推送触发 render() 时不得覆盖用户正在编辑的表单。"""
    assert "formDirty" in APPJS, "缺少表单脏标记"
    assert re.search(r"if\s*\(\s*S\.formDirty\s*\)", APPJS), "renderSource() 未按脏标记跳过回填"
    assert "function fillSourceForm(" in APPJS, "回填逻辑未拆成独立函数"
    assert "function syncSourceForm(" in APPJS, "缺少按 kind/frame 启用禁用字段的联动函数"
    # 用户一旦输入就置脏（input + change 都要，否则打字过程会被 0.2s 一次的推送打断）
    assert re.search(r"#view-source input, #view-source select", APPJS), "未对源面板控件绑定脏值标记"


def test_source_payload_omits_irrelevant_and_empty_fields():
    """F-07：启动载荷只送当前 kind 相关字段，空串/空数字不得覆盖服务端已存配置。"""
    assert "path: $('#src-path').value.trim()," not in APPJS, "仍在无条件发送 path（空串会抹掉服务端配置）"
    assert "host: $('#src-host').value.trim()," not in APPJS, "仍在无条件发送 host"
    assert re.search(r"if\s*\(path\)\s*p\.path\s*=\s*path", APPJS), "path 未按「非空才送」处理"
    assert re.search(r"if\s*\(host\)\s*p\.host\s*=\s*host", APPJS), "host 未按「非空才送」处理"
    assert re.search(r"if\s*\(p\.frame\s*===\s*'binary'\)", APPJS), "struct_fmt/struct_fields 未按帧格式条件发送"


def test_config_payload_skips_empty_numbers():
    """F-08：PUT /api/config 是深合并，空输入框必须跳过而不是送 0（否则 fs/PT/CT=0 直接 400）。"""
    for bad in ("fs: +$('#cfg-fs').value", "pt_ratio: +$('#cfg-pt').value", "order_max: +$('#cfg-hmax').value"):
        assert bad not in APPJS, f"仍在直接发送 {bad!r}：空框会变成 0"
    assert "Number.isFinite(v) && v > 0" in APPJS, "缺少「有限且 >0 才送」的闸门"
    assert "skipped" in APPJS, "未向用户回报哪些字段被跳过（静默保留原值会让人误判已保存）"


def test_start_engine_does_not_smuggle_ignored_config():
    """F-09b：/api/engine/start 只吃 source 白名单，夹带 transform/sampling 会被静默忽略。"""
    assert "collectSourcePayload(), collectConfigPayload()" not in APPJS, (
        "启动数据源仍夹带配置段：用户改完 PT/CT 点启动会以为生效，实际被服务端忽略"
    )


def test_source_hint_covers_every_kind():
    """每种源都要有填写说明，缺一种就会在界面上留空白（提示文案与 SOURCE_KINDS 对齐）。"""
    block = APPJS[APPJS.index("const SRC_HINT = {"): APPJS.index("const SRC_HINT = {") + 4000]
    for kind in SOURCE_KINDS:
        assert re.search(rf"^\s*{kind}:\s*'", block, re.M), f"SRC_HINT 缺少 {kind}"
    assert 'id="src-hint"' in HTML, "index.html 缺少 #src-hint 容器"
    assert 'id="src-formnote"' in HTML, "index.html 缺少 #src-formnote（未保存提示）"


def test_canvas_prep_does_not_reread_scaled_height_attribute():
    """F-22：`cv.height = h*dpr` 会同步改写 HTML height 属性；若 prep() 每次回读 getAttribute('height')，
    devicePixelRatio≠1（Windows 125% 缩放 / 浏览器对某主机名记忆了缩放级别）时每次重绘高度乘一次 dpr，
    页面纵向无限拉伸（127.0.0.1 缩放 100% 看不出、换 IP 访问就复现）。逻辑高度必须缓存（data-h）。"""
    import re
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    body = js.split("function prep(")[1].split("\nfunction ")[0]
    assert "cv.dataset.h" in body, "prep() 必须把逻辑高度缓存在 data-h"
    # 回读属性只允许出现在「首次缓存」那一行里
    reads = [ln for ln in body.splitlines() if "getAttribute('height')" in ln and not ln.strip().startswith("//")]
    assert len(reads) == 1 and "if (!cv.dataset.h)" in reads[0], reads
    assert not re.search(r"const height = h \|\| cv\.getAttribute", body)

def test_nilm_config_two_layer_layout():
    """v0.99.33（第 186 轮）：负荷辨识事件界面算法配置两层布局的静态契约。

    大模块① 7 个算法公共配置（#nilm-common7 > #nilm-form，5 项）；
    大模块② 7 个算法配置（#nilm-algos）＝ ②-1 前 6 个（#nilm-scalar-algos 动态 6 面板
    ＋ #nilm-scalar-common > #nilm-form-scalar 前6公共 4 项 + #nilm-auto-out）
    ＋ ②-2 画像（#nilm-profile-group > #nilm-profile-algo 动态 1 面板）。
    jsdom 行为级见 tools/ui_r186_check.cjs。"""
    # ── ① 层级与容器存在 ──
    for i in ("nilm-common7", "nilm-form", "nilm-algos", "nilm-scalar-group", "nilm-scalar-algos",
              "nilm-scalar-common", "nilm-form-scalar", "nilm-auto-out", "nilm-profile-group", "nilm-profile-algo"):
        assert f'id="{i}"' in HTML, f"index.html 缺少 #{i}"
    # 顺序断言＝层级（线性文档流里父组先开、子组在其内）：common7 < algos < scalar-group < scalar-algos
    # < scalar-common < form-scalar < auto-out < profile-group < profile-algo
    marks = ["id=\"nilm-common7\"", "id=\"nilm-form\"", "id=\"nilm-algos\"", "id=\"nilm-scalar-group\"",
             "id=\"nilm-scalar-algos\"", "id=\"nilm-scalar-common\"", "id=\"nilm-form-scalar\"",
             "id=\"nilm-auto-out\"", "id=\"nilm-profile-group\"", "id=\"nilm-profile-algo\""]
    idx = [HTML.index(m) for m in marks]
    assert idx == sorted(idx), f"两层布局顺序被破坏：{list(zip(marks, idx))}"
    # common7 与 algos 同级（同缩进的 wp-group），scalar-group / profile-group 是 algos 的子组
    c7 = HTML[HTML.index('id="nilm-common7"') - 40:HTML.index('id="nilm-common7"')]
    ag = HTML[HTML.index('id="nilm-algos"') - 40:HTML.index('id="nilm-algos"')]
    assert 'class="wp-group"' in c7 and 'class="wp-group"' in ag, "两大模块都应是 wp-group"

    # ── ② 字段归属互斥且完整（9 个原字段拆 5 + 4） ──
    seg_common = HTML[HTML.index('id="nilm-form"'):HTML.index('id="nilm-algos"')]
    seg_scalar = HTML[HTML.index('id="nilm-form-scalar"'):HTML.index('id="nilm-auto-out"')]
    for i in ("nilm-enabled", "nilm-save", "nilm-quantity", "nilm-window_cycles", "nilm-min_gap_cycles"):
        assert f'id="{i}"' in seg_common, f"①组缺 {i}"
    for i in ("nilm-rel_tol_pct", "nilm-min_delta_pct", "nilm-auto_params", "nilm-ch-total"):
        assert f'id="{i}"' in seg_scalar, f"前6公共组缺 {i}"
    # 互斥：前6公共的 4 项不得出现在①组段内，①组 5 项不得出现在前6公共段内
    for i in ("nilm-rel_tol_pct", "nilm-min_delta_pct", "nilm-auto_params", "nilm-ch-A"):
        assert f'id="{i}"' not in seg_common, f"{i} 错放在①组"
    for i in ("nilm-enabled", "nilm-save", "nilm-window_cycles", "nilm-min_gap_cycles"):
        assert f'id="{i}"' not in seg_scalar, f"{i} 错放在前6公共组"
    # 检测量属于①组（7 算法共用，画像要求 quantity 一致）
    assert 'id="nilm-quantity"' in seg_common and 'id="nilm-quantity"' not in seg_scalar

    # ── ③ app.js：6+1 分容器填充 ──
    assert "const scalarHost = E(side, 'nilm-scalar-algos')" in APPJS, "buildNilmForm 未按新容器填充前 6 个"
    assert "const profileHost = E(side, 'nilm-profile-algo')" in APPJS, "buildNilmForm 未单列画像容器"
    assert "filter(a => a !== 'profile')" in APPJS, "前 6 容器未排除 profile"
    assert "profileHost.innerHTML = panelHtml('profile')" in APPJS, "画像面板未填入 #nilm-profile-algo"
    # 脏标记绑定覆盖两大容器（前6公共在 #nilm-algos 深处）
    assert re.search(r"\[E\(side, 'nilm-form'\), E\(side, 'nilm-algos'\)\]", APPJS), "bindNilmForm 绑定范围被改"

    # ── ④ 灰显样式覆盖迁入 #nilm-form-scalar 的 rel_tol/min_delta ──
    style = (ROOT / "app/static/style.css").read_text(encoding="utf-8")
    assert "#nilm-form-scalar label.nilm-auto-off" in style, "style.css 缺 #nilm-form-scalar 灰显规则"
    assert "#nilm-form-scalar-br label.nilm-auto-off" in style, "style.css 缺分路侧灰显规则"


def test_profile_stage_free_is_select_and_gated_params():
    """v0.99.32：stage_free 后端只接受 0/1（config.py:923-924）⇒ 界面必须是列表框（number 输入能键入 2、1.5 被保存时 400）；
    且只有选 1（档位自由匹配）时 stage_min_scale / stage_max_scale / stage_dim_max 才可配置
    （stage_free=0 时后端不使用这三项：stage_range 只进 _fit_stage、单维否决只在 stage_free 分支生效）。"""
    from elec_tool.config import ConfigError, NilmConfig

    # ① 后端取值只有 0/1 —— 与界面列表框选项一一对应
    cfg = NilmConfig()
    for bad in (2, -1, 0.5):
        cfg.algorithms["profile"]["stage_free"] = bad
        with pytest.raises(ConfigError, match="stage_free"):
            cfg.validate()
    cfg.algorithms["profile"]["stage_free"] = 1
    cfg.validate()                                                  # 0/1 都合法

    # ② app.js 把 stage_free 定义成列表框（selects 枚举），选项恰为 0/1
    m = re.search(r"""selects:\s*\{\s*stage_free:\s*(\[\[.*?\]\])\s*\}""", APPJS, re.S)
    assert m, "app.js 没把 stage_free 定义成列表框（NILM_ALGOS.profile.selects）"
    opts = dict(re.findall(r"""\['(\d+)',\s*'([^']+)'\]""", m.group(1)))
    assert set(opts) == {"0", "1"}, f"stage_free 列表框选项 {sorted(opts)} 应恰为 0/1"
    assert "派生网格" in opts["0"] and "固定档位" in opts["0"], opts["0"]
    assert "档位自由匹配" in opts["1"] and "任意档位" in opts["1"], opts["1"]
    # 渲染分支：有 selects 的参数走 <select>，其余仍走 number 输入
    assert "sp.selects && sp.selects[k]" in APPJS, "buildNilmForm 没有按 selects 渲染 <select>"

    # ③ 联动：只有选 1 才放开三项（nilmStageGate 在建表、绑定、回填三处都被调用）
    assert "function nilmStageGate(" in APPJS, "缺少 stage_free → 档位参数的联动函数 nilmStageGate"
    gate = re.search(r"function nilmStageGate\(.*?\)\s*\{(.*?)\n\}", APPJS, re.S)
    assert gate, "nilmStageGate 函数体解析失败（正则需同步）"
    body = gate.group(1)
    for k in ("stage_min_scale", "stage_max_scale", "stage_dim_max"):
        assert k in body, f"nilmStageGate 没处理 {k}"
    assert "el.disabled = !free" in body, "nilmStageGate 没有按 stage_free 禁用/启用输入框"
    assert APPJS.count("nilmStageGate(side)") >= 3, "nilmStageGate 应在 bind/fill（含 dirty 早退）等 ≥3 处调用"
    assert re.search(r"""const sf = E\(side, 'nilm-profile-stage_free'\);.*?sf\.addEventListener\(\s*'change'""", APPJS, re.S), \
        "stage_free 下拉没注册 change 联动"
    # ④ 灰显样式存在
    style = (ROOT / "app/static/style.css").read_text(encoding="utf-8")
    assert "label.nilm-stage-off" in style, "style.css 缺 nilm-stage-off 灰显规则"


def test_profile_phases_control_and_payload(page):
    """v0.99.30：设备画像提取的「设备相别」下拉——选项与后端 normalize_phases 一致，且确实进了载荷。"""
    from elec_tool.nilm_profile import PHASES_ALL, normalize_phases
    assert "np-phases" in page.selects, "index.html 缺少 #np-phases"
    opts = set(page.selects["np-phases"])
    assert opts == {"auto", "ABC", "A", "B", "C", "AB", "AC", "BC"}, f"#np-phases 选项 {sorted(opts)}"
    for v in opts:                                   # 每个选项后端都认（auto → ""）
        assert normalize_phases(v) in ("", "A", "B", "C", "AB", "AC", "BC", "ABC")
    assert "phases:" in APPJS and "np-phases" in APPJS, "app.js 没把 #np-phases 放进提取载荷"
    assert "设备相别" in APPJS, "app.js 结果区没有「设备相别」卡片"
    assert set(PHASES_ALL) == {"A", "B", "C"}


def test_assistant_ui_contract_and_safe_markdown_renderer(page):
    required_ids = (
        "assistant-launcher", "assistant-panel", "assistant-session-pane", "assistant-session-search",
        "assistant-conversation-list", "assistant-session-context-menu", "assistant-rename-conversation",
        "assistant-clear-context-menu", "assistant-delete-conversation", "assistant-new", "assistant-clear-context",
        "assistant-model-type", "assistant-model-name", "assistant-session-toggle", "assistant-close", "assistant-privacy-note",
        "assistant-doc-search", "assistant-doc-list", "assistant-doc-content", "assistant-doc-status",
        "assistant-messages", "assistant-thinking", "assistant-form", "assistant-prompt", "assistant-stop",
        "assistant-image-input", "assistant-image-previews", "assistant-attach-image", "assistant-settings-open",
        "assistant-settings-close", "assistant-settings", "assistant-settings-scroll", "assistant-operator-token", "assistant-verify-operator",
        "assistant-operator-status", "assistant-admin-token", "assistant-save-settings", "assistant-load-sensitive-terms",
        "assistant-local-model", "assistant-local-model-select", "assistant-refresh-local-models", "assistant-local-models-status",
        "assistant-tools-enabled", "assistant-cloud-tools-enabled", "assistant-tool-audit-enabled",
        "assistant-enabled-tool-checks", "assistant-audit-refresh", "assistant-audit-list",
        "assistant-clear-sensitive-terms", "assistant-bundled-docs", "assistant-doc-files", "assistant-import-docs", "assistant-knowledge-list",
    )
    for element_id in required_ids:
        assert element_id in page.ids, f"缺少智能问答界面 #{element_id}"

    start = APPJS.index("/* ------------------------------------------------------------------ 智能问答")
    end = APPJS.index("async function init() {", start)
    assistant_js = APPJS[start:end]
    assert "fetch(assistantApiUrl('/api/assistant/chat')" in assistant_js
    assert "assistantApiUrl(path) { return apiUrl(path, sideOf()); }" in assistant_js
    assert "text/event-stream" in assistant_js and "response.body.getReader" in assistant_js
    assert "data.type === 'proposal'" in assistant_js and "assistantConfirmProposal" in assistant_js
    assert "assistantClearContext" in assistant_js and "assistantVerifyOperator" in assistant_js
    assert "X-Assistant-Operator-Token" in assistant_js and "X-Assistant-Admin-Token" in assistant_js
    assert "localStorage" not in assistant_js and "sessionStorage" not in assistant_js
    assert "assistantNewConversation(next)" in assistant_js and "window.confirm(message)" in assistant_js
    assert "assistantRenderConversationList" in assistant_js and "assistantMoveConversation" in assistant_js
    assert "assistantSetSessionsCollapsed" in assistant_js and "assistantRenderDocumentList" in assistant_js
    assert "assistantAddImageFiles" in assistant_js and "payload.images" in assistant_js
    assert "assistantReadableRequestError" in assistant_js and "assistant-thinking" in assistant_js
    assert "visible_views" in assistant_js and "assistantSyncLauncher" in assistant_js
    assert "/api/assistant/documents" in assistant_js and "assistantLoadDocuments" in assistant_js
    assert "noopener noreferrer" in assistant_js, "Markdown 外链必须禁止 opener"
    assert "assistantRenderMarkdown" in assistant_js and "element.innerHTML" not in assistant_js
    assert "localStorage" not in assistant_js, "会话正文与截图只保存在页面内存，避免静默落浏览器持久存储"
    assert "云端模式" in assistant_js and "截图内容不经过文本敏感词扫描" in assistant_js
    settings_start = HTML.index('<details id="assistant-settings"')
    settings_end = HTML.index('</aside>', settings_start)
    for credential_id in ("assistant-operator-token", "assistant-admin-token", "assistant-verify-operator"):
        assert settings_start < HTML.index(f'id="{credential_id}"') < settings_end, f"#{credential_id} 必须归入配置区域"
    assert "会话仅保存在当前页面内存" in HTML


def test_assistant_local_model_picker_is_editable_and_uses_same_origin_discovery(page):
    assert re.search(r'<select id="assistant-local-model-select"[^>]*>', HTML), "候选模型必须有可直接打开的下拉框"
    assert re.search(r'<input id="assistant-local-model"[^>]*type="text"', HTML), "必须保留列表外模型名的手动输入"
    assert 'for="assistant-local-model"' in HTML and "assistant-refresh-local-models" in HTML
    start = APPJS.index("/* ------------------------------------------------------------------ 智能问答")
    end = APPJS.index("async function init() {", start)
    assistant_js = APPJS[start:end]
    assert "await assistantLoadLocalModels();" in assistant_js, "配置加载后应读取服务端候选列表"
    assert "assistantApi('/api/assistant/local-models')" in assistant_js
    assert "assistantApi('/api/assistant/local-models/refresh'" in assistant_js
    assert "X-Assistant-Admin-Token" in assistant_js
    assert "localModelSelect.addEventListener('change'" in assistant_js, "选择候选后应填入可编辑模型名"
    assert "localModelInput.addEventListener('input', assistantSyncLocalModelPicker)" in assistant_js
    render_start = assistant_js.index("function assistantRenderLocalModels(data) {")
    render_end = assistant_js.index("async function assistantLoadLocalModels(", render_start)
    render_js = assistant_js[render_start:render_end]
    assert "assistant-local-model-select" in render_js and "select.appendChild(option)" in render_js
    assert "assistantSyncLocalModelPicker();" in render_js
    assert "modelInput.value =" not in render_js, "刷新候选不得覆盖当前手填值"


def test_assistant_model_name_picker_and_dynamic_cloud_profile_editor(page):
    for element_id in ("assistant-model-name", "assistant-cloud-profiles", "assistant-cloud-profile-add", "assistant-cloud-profile-status"):
        assert element_id in page.ids, f"缺少模型选择 / 云端档案管理元素 #{element_id}"
    assert "具体模型" in HTML and 'id="assistant-model-name"' in HTML
    assert "额外云端 API 配置档案" in HTML and "API Key 仅存服务进程内存" in HTML
    start = APPJS.index("/* ------------------------------------------------------------------ 智能问答")
    end = APPJS.index("async function init() {", start)
    assistant_js = APPJS[start:end]
    assert "function assistantRenderModelNameSelector" in assistant_js
    assert "assistantChangeModelName" in assistant_js
    assert "payload.model_name = conv.modelName" in assistant_js
    assert "payload.cloud_profile_id = conv.cloudProfileId" in assistant_js
    assert "payload.cloud_api_profiles = ASSISTANT_UI.cloudProfilesDraft.map" in assistant_js
    assert "payload.cloud_api_profile_secrets = profileSecrets" in assistant_js
    assert "payload.clear_cloud_api_profile_secrets = profilesToClear" in assistant_js
    assert "X-Assistant-Admin-Token" in assistant_js, "云端 API 档案保存必须走管理员配置接口"
    assert "profile.api_key_set" in assistant_js and "input.type = type" in assistant_js


def test_assistant_scroll_containers_preserve_reader_position_during_streaming():
    css = (ROOT / "app/static/style.css").read_text(encoding="utf-8")
    for selector in (".assistant-messages", ".assistant-conversation-list"):
        rule = re.search(re.escape(selector) + r"\{([^}]*)\}", css)
        assert rule, f"缺少 {selector} 滚动容器"
        assert "overflow-y:auto" in rule.group(1), f"{selector} 应可纵向滚轮滚动"
        assert "overscroll-behavior-y:contain" in rule.group(1), f"{selector} 应在侧栏内处理滚动"
    settings_rule = re.search(r"\.assistant-settings\[open\]\{([^}]*)\}", css)
    assert settings_rule and "position:absolute" in settings_rule.group(1) and "overflow:hidden" in settings_rule.group(1), "设置面板应裁剪覆盖层，并将滚动交给内部明确尺寸的滚动区"
    settings_scroll_rule = re.search(r"\.assistant-settings-scroll\{([^}]*)\}", css)
    assert settings_scroll_rule and all(token in settings_scroll_rule.group(1) for token in ("position:absolute", "inset:0", "overflow-y:scroll", "overflow-x:hidden")), "独立设置滚动区必须有明确边界和强制纵向溢出"
    assert "scrollbar-width:auto" in settings_scroll_rule.group(1) and "scrollbar-color:#7898c5 #172338" in settings_scroll_rule.group(1), "设置面板滚动条的滑块 / 轨道对比度不足"
    assert ".assistant-settings-scroll:focus-visible{outline:2px solid #4e8de8" in css, "键盘聚焦设置滚动区时应显示焦点指示"
    assert ".assistant-settings-scroll::-webkit-scrollbar{width:14px}" in css
    assert ".assistant-settings-scroll::-webkit-scrollbar-track{background:#172338" in css
    header_rule = re.search(r"\.assistant-settings-header\{([^}]*)\}", css)
    assert header_rule and "position:sticky" in header_rule.group(1) and "top:0" in header_rule.group(1), "设置滚动时标题 / 关闭按钮应保持可见"
    assert 'id="assistant-settings-scroll" class="assistant-settings-scroll" role="region" aria-label="配置与附加知识库，可滚动浏览全部设置" tabindex="0"' in HTML, "独立设置滚动区应可键盘访问并有无障碍名称"
    assert HTML.index('id="assistant-settings-scroll"') < HTML.index('class="assistant-settings-body"') < HTML.index('id="assistant-doc-pane"'), "配置正文 / 完整本地帮助文档必须位于实际滚动区内"
    shell_rule = re.search(r"\.assistant-shell\{([^}]*)\}", css)
    assert shell_rule and "overflow-y:auto" in shell_rule.group(1), "助手外层在视口受限时必须能纵向滚动"
    assert "scrollbar-width:auto" in shell_rule.group(1) and "scrollbar-color:#3d527a #111827" in shell_rule.group(1), "助手外层滚动条应有清晰可见的轨道和滑块"
    assert ".assistant-shell::-webkit-scrollbar{width:10px}" in css
    workspace_rule = re.search(r"\.assistant-workspace\{([^}]*)\}", css)
    assert workspace_rule and "flex:1 0 420px" in workspace_rule.group(1) and "min-height:420px" in workspace_rule.group(1), "主布局不能在短视口下被 flex 压缩裁切"
    assert "overflow:visible" in workspace_rule.group(1), "主布局不能裁剪溢出的头部 / 输入控件"
    chat_rule = re.search(r"\.assistant-chat-pane\{([^}]*)\}", css)
    assert chat_rule and "overflow:visible" in chat_rule.group(1), "问答列溢出的控件必须交给外层滚动条访问"
    assert ".assistant-workspace{position:relative;display:block;flex-basis:480px;min-height:480px}" in css
    assert ".assistant-workspace{flex-basis:540px;min-height:540px}" in css
    assert 'id="assistant-shell"' in HTML and 'tabindex="0"' in HTML, "外层滚动容器应可键盘聚焦"
    messages_rule = re.search(r"\.assistant-messages\{([^}]*)\}", css)
    assert messages_rule and "scroll-behavior:smooth" not in messages_rule.group(1), "流式更新不能用平滑自动滚动抢占滚轮"
    start = APPJS.index("/* ------------------------------------------------------------------ 智能问答")
    end = APPJS.index("async function init() {", start)
    assistant_js = APPJS[start:end]
    assert "function assistantNearMessagesBottom" in assistant_js
    assert "options.preserveScroll" in assistant_js
    assert "function assistantHandlePanelWheel(event)" in assistant_js
    assert "function assistantScrollByWheel(target, event)" in assistant_js
    assert "assistantScrollByWheel(assistantEl('assistant-shell'), event)" in assistant_js
    assert "const scrollable = '.assistant-doc-content, .assistant-doc-list, .assistant-settings-scroll," in assistant_js
    assert "? assistantEl('assistant-settings-scroll')" in assistant_js
    assert "if (inOpenSettings) { if (event.cancelable) event.preventDefault(); return; }" in assistant_js
    assert "panel.addEventListener('wheel', assistantHandlePanelWheel, { passive: false })" in assistant_js
    refresh = assistant_js[assistant_js.index("function assistantRefreshMessage(msg) {"):assistant_js.index("function assistantFormatConversationTime(")]
    assert "assistantNearMessagesBottom(list)" in refresh and "if (followBottom) list.scrollTop = list.scrollHeight" in refresh
    assert "assistantRenderConversation({ preserveScroll: true })" in assistant_js


def test_assistant_is_a_fixed_session_and_chat_sidebar_with_zero_config_backend(page):
    """同页固定侧栏改为会话管理 + 问答双栏；内置知识库免模型配置，窄屏可收起会话栏。"""
    assert page.selects["assistant-model-type"] == ["builtin", "local", "cloud"]
    assert page.selects["assistant-default-backend"] == ["builtin", "local", "cloud"]
    assert '<aside id="assistant-panel"' in HTML and 'aria-controls="assistant-panel"' in HTML
    assert '<dialog id="assistant-dialog"' not in HTML and 'aria-modal="true"' not in HTML
    assert "assistant-launcher" in page.ids and "assistant-panel" in page.ids
    assert "assistant-session-pane" in HTML and "assistant-chat-pane" in HTML
    assert "assistant-bundled-docs" in HTML and "assistant-doc-pane" in HTML
    assert HTML.index('<details id="assistant-settings"') < HTML.index('id="assistant-doc-pane"')
    assert HTML.index('<aside id="assistant-session-pane"') < HTML.index('<main id="assistant-chat-pane"')
    style = (ROOT / "app/static/style.css").read_text(encoding="utf-8")
    sidebar = re.search(r"\.assistant-panel\s*\{([^}]*)\}", style)
    assert sidebar, "style.css 缺少固定侧栏样式"
    assert "position:fixed" in sidebar.group(1) and "inset:0 0 0 auto" in sidebar.group(1), sidebar.group(1)
    assert "width:min(1120px,100vw)" in sidebar.group(1) and "height:100dvh" in sidebar.group(1)
    assert ".assistant-workspace{display:grid;grid-template-columns:260px minmax(0,1fr)" in style
    assert "@media(max-width:680px)" in style and ".assistant-session-toggle{display:inline-flex" in style
    assert "assistantNewConversation('builtin')" in APPJS, "新对话未默认进入免模型通道"
    assert "model_type: conv.backend || 'builtin'" in APPJS, "聊天载荷仍回退到需要模型配置的后端"
