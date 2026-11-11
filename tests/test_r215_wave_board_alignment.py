"""第 215 轮：同排周波图的排版契约。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_board_titles_and_empty_error_status_do_not_shift_chart():
    css = (ROOT / 'app/static/style.css').read_text(encoding='utf-8')
    for text in ('.wb-paired .wb-chart-title{height:26px;line-height:26px;',
                 '.wb-detail-head{height:26px;', '.wb-detail-head .wb-chart-title{min-width:0;margin:0}',
                 '.wb-detail .zoomtip{display:none}', '.wb-detail-status:empty{display:none}'):
        assert text in css
    js = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')
    html = next(line for line in js.splitlines() if '<div class="wb-detail" hidden>' in line)
    assert 'class="wb-chart-title wb-detail-title"' in html
    assert html.index('wb-detail-chart') < html.index('wb-detail-status')
    assert 'aria-live="polite"' in html


def test_board_detail_height_follows_selected_chart():
    js = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')
    detail = js[js.index('function wbDrawDetail(m)'):js.index('/* ---- 读文件 ---- */', js.index('function wbDrawDetail(m)'))]
    assert 'wbCharts(m).find(ch => ch.key === key)' in detail
    assert 'height, ownRange: true' in detail
    assert "status.textContent = '';" in detail
    assert '周波曲线读取失败：' in detail
    assert 'status.textContent = `原始文件' not in detail
