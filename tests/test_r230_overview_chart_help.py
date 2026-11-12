"""总览面板的精简工具条仅移除指定文字，不影响其他界面。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_overview_compact_chart_labels_are_scoped():
    js = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')
    css = (ROOT / 'app/static/style.css').read_text(encoding='utf-8')
    zoom = js[js.index('function renderZoomBar('):js.index('/* 公共时间段模式：')]
    legend = js[js.index('function renderSeriesLegend('):js.index('async function setSeriesVisible(')]
    assert "board || !!cv.closest('#view-nilm') || !!cv.closest('#view-overview')" in zoom
    assert "cv.closest('.wb-module') || cv.closest('#view-overview')" in legend
    assert "(compactHelp ? '' : '<span class=\"muted\">缩放：</span>')" in zoom
    assert "(compactHelp ? '' : '<span class=\"muted panlbl\">移动：</span>')" in zoom
    assert "tip.textContent = compactHelp ? ''" in zoom
    assert '#view-overview .zoomtip:empty{display:none}' in css
    assert 'title="${tip}"' in zoom and 'aria-label=' in zoom
