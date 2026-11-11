"""第 214 轮：周波窗与选中的波形预览主曲线同一行。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_paired_grid_is_limited_to_wave_board_and_scrolls_on_narrow_screens():
    css = (ROOT / 'app/static/style.css').read_text(encoding='utf-8')
    rule = next(line for line in css.splitlines() if line.startswith('.wb-chart-row.wb-paired{'))
    assert 'display:grid' in rule
    assert 'grid-template-columns:repeat(2,minmax(260px,1fr))' in rule
    assert 'overflow-x:auto' in rule
    assert 'align-items:start' in rule
    assert '.wb-detail[hidden]{display:none}' in css


def test_detail_attaches_to_the_selected_chart_and_redraws_on_layout_changes():
    js = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')
    board = js[js.index('/* ------------------------------------------------------------------ 数据处理 · 波形预览（v0.99.51'):js.index('/* v0.96 / v0.97：数据处理 · 估计 CT')]
    for expected in ('data-wb-row=', "row.appendChild(box)", "row.classList.add('wb-paired')", 'box.dataset.wbKey = key',
                     'detail.dataset.wbKey', 'if (paired) wbDraw(m)', 'if (row) { row.appendChild(detail)'):
        assert expected in board
    assert "else wbClearDetail(m)" in board
    assert 'wbDraw(m); // 主图宽度变窄后立即重画' in board
