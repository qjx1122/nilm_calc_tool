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
  await put('/api/config', { source: { kind: 'csv_file', path: 'data/nilm_bus_mixed.csv', file_speed: 0, play_window: false, custom_time: false }, branch: { enabled: false } });
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
  window.eval(js + '\n;window.__refreshHistory = refreshHistory; window.__NLs = NLs;');
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
  const boxes = Array.from(document.querySelectorAll('#p-wave-sel .pw-sel'));
  check('勾选框 12 个（总/A/B/C × P/Q/S），默认勾选 总 P/Q/S', boxes.length === 12 && boxes.filter((b) => b.checked).map((b) => b.dataset.ph + b.dataset.k).join(',') === 'totalP,totalQ,totalS');
  let pw = $('p-wave').__chart;
  check('默认画 3 条：总有功 / 无功 / 视在瞬时波形', !!pw && pw.pts.length === 3 && pw.pts.map((p) => p.name).join('|').includes('总有功') && /总无功/.test(pw.pts[1].name) && /总视在/.test(pw.pts[2].name), pw ? pw.pts.map((p) => p.name).join(' | ') : '无图');
  const n0 = pw ? pw.pts[0].data.length : 0;
  const bA = boxes.find((b) => b.dataset.ph === 'A' && b.dataset.k === 'P'), bQ = boxes.find((b) => b.dataset.ph === 'total' && b.dataset.k === 'Q');
  bA.checked = true; change(bA); bQ.checked = false; change(bQ); await sleep(300);
  pw = $('p-wave').__chart;
  check('勾 A 相 P、去掉总 Q → 3 条：总 P、总 S、A 相 P，点数一致', !!pw && pw.pts.length === 3 && pw.pts.some((p) => /A 相有功/.test(p.name)) && !pw.pts.some((p) => /总无功/.test(p.name)) && pw.pts.every((p) => p.data.length === n0), pw ? pw.pts.map((p) => p.name).join(' | ') : '');
  const sA = pw.pts.find((p) => /A 相有功/.test(p.name)).data.map((x) => x[1]), sT = pw.pts.find((p) => /总有功/.test(p.name)).data.map((x) => x[1]);
  const mean = (a) => a.reduce((s, v) => s + v, 0) / a.length;
  check('A 相有功均值 < 总有功均值（分相 ≤ 总）', mean(sA) > 0 && mean(sA) < mean(sT), `A ${mean(sA).toFixed(1)} W，总 ${mean(sT).toFixed(1)} W`);
  const bS = boxes.find((b) => b.dataset.ph === 'A' && b.dataset.k === 'S'); bS.checked = true; change(bS); await sleep(300);
  pw = $('p-wave').__chart; const sS = pw.pts.find((p) => /A 相视在/.test(p.name)).data.map((x) => x[1]);
  check('A 相视在 s(t)=√(p²+q²) ≥ |p(t)| 逐点成立', sS.every((v, i) => v + 1e-6 >= Math.abs(sA[i])));
  boxes.forEach((b) => { b.checked = false; }); change(boxes[0]); await sleep(300);
  check('全部取消 → 空态提示「请在上方勾选要显示的曲线」', $('p-wave').__chart === null || ($('p-wave').__chart && $('p-wave').__chart.pts.length === 0));
  console.log(fail ? `FAIL ${fail}` : 'ALL PASS');
  window.close(); process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
