"""第 163 轮（v0.99.21）：画像提取结果表 μ/σ 行不得复用顶部状态栏的全局 class="stat"。

回归背景：style.css 全局 ``.stat{display:flex;flex-direction:column;min-width:78px}`` 作用于 <td class="n stat">，
μ/σ 两行 7 个数值格被拉成竖排 flex 块（右对齐、列宽失效）。"""
import pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_np_render_does_not_use_global_stat_class():
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    i = js.index("function npRender("); j = js.index("async function npRun(", i)
    body = js[i:j]
    body = body.replace('\\"', '"')          # app.js 模板字符串内使用 \" 转义
    assert 'class="stat"' not in body and 'class="n stat"' not in body
    assert body.count('class="n np-stat"') == 2 and body.count('<tr class="np-stat">') == 2


def test_css_np_stat_rules_present_and_global_stat_is_flex():
    css = (ROOT / "app/static/style.css").read_text(encoding="utf-8")
    assert re.search(r"^\.stat\{display:flex;flex-direction:column", css, re.M)   # 全局规则仍在（状态栏用）
    assert ".np-tbl td.np-stat,.np-tbl th.np-stat{" in css
    assert ".np-tbl tr.stat" not in css and ".np-tbl td.stat" not in css
