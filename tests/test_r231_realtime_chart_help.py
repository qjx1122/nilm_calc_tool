"""实时监测九个页面仅移除曲线说明文字，保留既有工具功能。"""
from html.parser import HTMLParser
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


class Sections(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'section' and a.get('id', '').startswith('view-'):
            self.sections[a['id'][5:]] = set(a.get('class', '').split())


def test_all_and_only_realtime_views_have_compact_chart_help():
    html = Sections()
    html.feed((ROOT / 'app/static/index.html').read_text(encoding='utf8'))
    js = (ROOT / 'app/static/app.js').read_text(encoding='utf8')
    css = (ROOT / 'app/static/style.css').read_text(encoding='utf8')
    elec = re.search(r"const ELEC_VIEWS = \[([^]]+)\]", js)
    assert elec
    views = set(re.findall(r"'([^']+)'", elec.group(1)))
    assert views == {'voltage', 'current', 'power', 'power_factor', 'fundamental', 'harmonic', 'interharmonic', 'dc', 'spectrum'}
    assert {v for v, classes in html.sections.items() if 'realtime-view' in classes} == views
    zoom = js[js.index('function renderZoomBar('):js.index('/* 公共时间段模式：')]
    legend = js[js.index('function renderSeriesLegend('):js.index('async function setSeriesVisible(')]
    assert "|| !!cv.closest('.realtime-view')" in zoom
    assert "|| cv.closest('.realtime-view') ? ''" in legend
    assert "tip.textContent = compactHelp ? ''" in zoom
    assert '.realtime-view .zoomtip:empty{display:none}' in css
    assert 'title="${tip}"' in zoom and 'aria-label=' in zoom
