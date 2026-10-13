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
