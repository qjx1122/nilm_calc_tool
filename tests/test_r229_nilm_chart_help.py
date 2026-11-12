"""负荷辨识页曲线仅隐藏指定操作说明，其他页面保持原有规则。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_nilm_zoom_help_is_scoped_and_display_legend_is_kept():
    js = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')
    css = (ROOT / 'app/static/style.css').read_text(encoding='utf-8')
    zoom = js[js.index('function renderZoomBar('):js.index('/* 公共时间段模式：', js.index('function renderZoomBar('))]
    legend = js[js.index('function renderSeriesLegend('):js.index('async function setSeriesVisible(', js.index('function renderSeriesLegend('))]
    assert "board || !!cv.closest('#view-nilm')" in zoom
    assert "(compactHelp ? '' : '<span class=\"muted\">缩放：</span>')" in zoom
    assert "(compactHelp ? '' : '<span class=\"muted panlbl\">移动：</span>')" in zoom
    assert "tip.textContent = compactHelp ? ''" in zoom
    assert "cv.closest('.wb-module') || cv.closest('#view-overview') ? '' : '<span class=\"muted\">显示：</span>'" in legend
    assert '#view-nilm .zoomtip:empty{display:none}' in css
    assert "title=\"${tip}\"" in zoom and 'aria-label=' in zoom
