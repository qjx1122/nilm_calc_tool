/* 第 99 轮界面检查（v0.76）：① 三相电压 / 三相电流 / P·Q·S 子界面三条曲线无事件标注线、标题只留数据说明；
 * ② 功率页瞬时功率 + 分相瞬时功率合并为「有功 / 无功 / 视在功率瞬时波形」，勾选框选 总/A/B/C × P/Q/S；③ 周波窗两列等宽（minmax(0,1fr)）。
 * 用法：TZ=Asia/Shanghai JSDOM_DIR=/tmp/uitest node tools/ui_r76_check.cjs http://127.0.0.1:8035 */
const fs = require('fs'), path = require('path');
const { JSDOM } = require(path.join(process.env.JSDOM_DIR || '/tmp/uitest', 'node_modules/jsdom'));
const ROOT = path.join(__dirname, '..'); const BASE = (process.argv[2] || 'http://127.0.0.1:8000').replace(/\/$/, '');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function main() {
  const J = async (u, o) => (await fetch(BASE + u, o)).json();
  const put = (u, b) => J(u, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
  await J('/api/engine/stop', { method: 'POST' }); await J('/api/branch/engine/stop', { method: 'POST' });
  await put('/api/config', { source: { kind: 'csv_file', path: 'data/nilm_bus_mixed.csv', file_speed: 0, play_window: false, custom_time: false }, branch: { enabled: false }, output: { series_hidden: { 'p-wave': [] } } });   // 清掉上次实录留下的勾选状态
  await J('/api/engine/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: 'csv_file', path: 'data/nilm_bus_mixed.csv', file_speed: 0 }) });
  for (let k = 0; k < 60; k++) { await sleep(500); const st = await J('/api/state'); if (!st.running) break; }
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8'); const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const css = fs.readFileSync(path.join(ROOT, 'app/static/style.css'), 'utf8');
  const dom = new JSDOM(html, { url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true, beforeParse(window) {
    window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, { get: (t, p) => (p === 'measureText' ? () => ({ width: 8 }) : p === 'createLinearGradient' ? () => ({ addColorStop() {} }) : () => {}), set: () => true });
    Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get() { return 900; } });
    window.WebSocket = class { constructor() { this.readyState = 0; } close() {} send() {} };
    window.fetch = async (url, opts = {}) => fetch(String(url).startsWith('http') ? String(url) : BASE + url, opts);
    window.alert = () => {}; window.scrollTo = () => {};
  } });
  const { window } = dom, { document } = window;
  window.eval(js + '\n;window.__refreshHistory = refreshHistory; window.__NLs = NLs; window.__hid = seriesHiddenSet;');
  if (typeof window.init === 'function') window.init();
  await sleep(2500); await window.__refreshHistory(); await sleep(500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(1500); };
  let fail = 0; const check = (n, ok, info) => { console.log((ok ? '  ✓ ' : '  ✗ ') + n + (info ? '　' + String(info).slice(0, 200) : '')); if (!ok) fail++; };
  // 造几个负荷辨识事件进内存（原来趋势图会据此画竖线）
  await nav('nilm'); await sleep(800);
  const nl = window.__NLs('bus'); const st = await J('/api/state'); const hist = await J('/api/history/power?max_points=50');
  const t0 = hist.points && hist.points.length ? hist.points[0].t : Date.now() / 1000;
  nl.events = [{ t_start: t0 + 1, algorithm: 'threshold', channel: 'total', direction: 'up', delta_w: 100, unit: 'W' }];
  for (const [view, pre, label] of [['voltage', 'v', '三相电压趋势 Ua / Ub / Uc'], ['current', 'i', '三相电流趋势 Ia / Ib / Ic'], ['power', 'p', 'P / Q / S 趋势']]) {
    console.log(`— ${view}`);
    await nav(view); await sleep(1200);
    const cvT = $(pre + '-trend'), ch = cvT.__chart;
    check(`${view}：趋势图有曲线且无事件标注线（marks 空）`, !!ch && ch.pts.length >= 3 && !(ch.opt.marks && ch.opt.marks.length), ch ? `${ch.pts.length} 条, marks=${(ch.opt.marks || []).length}` : '无图');
    const h3 = cvT.parentElement.querySelector('h3').textContent.replace(/\s+/g, ' ').trim();
    check(`${view}：趋势图标题只保留数据说明`, h3.startsWith(label) && !/右键|竖线/.test(h3), h3);
    const h3c = $(pre + '-cyc').parentElement.querySelector('h3').textContent.replace(/\s+/g, ' ').trim();
    const h3w = $(pre + '-wave2').parentElement.querySelector('h3').textContent.replace(/\s+/g, ' ').trim();
    check(`${view}：周波窗（有效值）/（瞬时值）标题无操作提示`, /^周波窗（有效值）/.test(h3c) && /^周波窗（瞬时值）/.test(h3w) && !/右键/.test(h3c + h3w), h3c + ' ‖ ' + h3w);
    // 装载周波窗（有效值）→ 也不应有标注线
    click($(`btn-${pre}-win-load`)); await sleep(2500);
    const cc = $(pre + '-cyc').__chart;
    check(`${view}：周波窗（有效值）装载后有曲线且无事件标注线`, !!cc && cc.pts.length >= 3 && !(cc.opt.marks && cc.opt.marks.length), cc ? `${cc.pts.length} 条, marks=${(cc.opt.marks || []).length}` : '无图');
    const g = $(pre + '-cyc').closest('.grid2');
    check(`${view}：周波窗两列在同一 grid2 中（等宽列 minmax(0,1fr)，子项 min-width:0）`, !!g && g.children.length === 2 && /\.grid2\{display:grid;grid-template-columns:minmax\(0,1fr\) minmax\(0,1fr\)/.test(css) && /\.grid2>\*\{min-width:0\}/.test(css));
  }
  console.log('— power 瞬时波形合并');
  await nav('power'); await sleep(1000);
  check('旧 #p-wave-ph 已不存在，#p-wave 标题为「有功 / 无功 / 视在功率瞬时波形」', !$('p-wave-ph') && /^有功 \/ 无功 \/ 视在功率瞬时波形/.test($('p-wave').parentElement.querySelector('h3').textContent.trim()));
  // v0.78：勾选框＝canvas 下方图例复选框（.serlegend .ser-vis，与趋势图同一套）
  const leg = () => Array.from(document.querySelectorAll('.serlegend[data-chart="p-wave"] .ser-vis'));
  const legT = () => Array.from(document.querySelectorAll('.serlegend[data-chart="p-trend"] .ser-vis'));
  check('瞬时波形图例 12 个复选框（总/A/B/C × P/Q/S），与趋势图同一 .serlegend 风格', leg().length === 12 && legT().length >= 3 && leg()[0].parentElement.querySelector('i') !== null, leg().length + ' / 趋势 ' + legT().length);
  check('默认只勾总 P/Q/S（图例名与趋势图一致：P Q S / Pa Pb Pc …）', leg().filter((b) => b.checked).map((b) => b.dataset.name).join('|') === 'P|Q|S', leg().filter((b) => b.checked).map((b) => b.dataset.name).join('|'));
  let pw = $('p-wave').__chart;
  check('瞬时波形图例名 = 趋势图图例名（P Q S Pa Pb Pc Qa Qb Qc Sa Sb Sc）', leg().map((b) => b.dataset.name).sort().join(',') === legT().map((b) => b.dataset.name).sort().join(','), leg().map((b) => b.dataset.name).join(' '));
  check('功率页卡片含 A / B / C 相 P / Q / S 分相实时数据', ['A', 'B', 'C'].every((k) => Array.from(document.querySelectorAll('#p-cards .card .k')).some((e) => e.textContent === k + ' 相 P / Q / S')) && /Q .*S .*PF/.test($('p-cards').textContent));
  check('默认画 3 条可见：总有功 / 无功 / 视在', !!pw && pw.pts.length === 3 && pw.pts.map((p) => p.name).join('|') === 'P|Q|S', pw ? pw.pts.map((p) => p.name).join(' | ') : '无图');
  const n0 = pw.pts[0].data.length;
  const tick = async (name, on) => { const b = leg().find((x) => x.dataset.name === name); b.checked = on; b.dispatchEvent(new window.Event('change', { bubbles: true })); await sleep(600); pw = $('p-wave').__chart; };
  await tick('Pa', true); await tick('Q', false);
  const hid = window.__hid(document.getElementById('p-wave'));
  check('勾 A 相 P、去掉总 Q → 隐藏集合随之更新并写 output.series_hidden', !hid.has('Pa') && hid.has('Q') && pw.pts.length === 3 && pw.pts.some((p) => /^Pa$/.test(p.name)) && !pw.pts.some((p) => /^Q$/.test(p.name)) && pw.pts.every((p) => p.data.length === n0), [...hid].join(','));
  const sA = pw.pts.find((p) => /^Pa$/.test(p.name)).data.map((x) => x[1]), sT = pw.pts.find((p) => /^P$/.test(p.name)).data.map((x) => x[1]);
  const mean = (a) => a.reduce((s, v) => s + v, 0) / a.length;
  check('A 相有功均值 < 总有功均值（分相 ≤ 总）', mean(sA) > 0 && mean(sA) < mean(sT), `A ${mean(sA).toFixed(1)} W，总 ${mean(sT).toFixed(1)} W`);
  await tick('Sa', true);
  const sS = pw.pts.find((p) => /^Sa$/.test(p.name)).data.map((x) => x[1]);
  check('A 相视在 s(t)=√(p²+q²) ≥ |p(t)| 逐点成立', sS.every((v, i) => v + 1e-6 >= Math.abs(sA[i])));
  await tick('Pa', false); await tick('Sa', false); await tick('Q', true);
  // 说明段落
  await nav('source'); await sleep(800);
  const note = Array.from(document.querySelectorAll('#panel-link .notes.muted.p')).find((d) => /完全独立/.test(d.textContent));
  check('数据源页说明段为块级段落（.notes.p display:block，行内 <b>/<code> 不再被拆行）', !!note && window.getComputedStyle(note).display === 'block' && note.querySelector('b') && note.querySelector('code'));
  console.log(fail ? `FAIL ${fail}` : 'ALL PASS');
  window.close(); process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
