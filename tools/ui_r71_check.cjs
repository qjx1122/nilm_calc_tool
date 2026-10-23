/* 第 71 轮界面检查（v0.71）：三相电压 / 三相电流 / 有功无功视在 三个子界面新增 趋势图 + 周波窗（有效值）+ 周波窗（瞬时值），
 * 曲线功能 / 右键菜单 / 风格同负荷辨识事件页。打真实服务端；需 data/nilm_bus_mixed.csv。
 * 用法：TZ=Asia/Shanghai JSDOM_DIR=/tmp/uitest node tools/ui_r71_check.cjs http://127.0.0.1:8000 */
const fs = require('fs'), path = require('path');
const { JSDOM } = require(path.join(process.env.JSDOM_DIR || '/tmp/uitest', 'node_modules/jsdom'));
const ROOT = path.join(__dirname, '..'); const BASE = (process.argv[2] || 'http://127.0.0.1:8000').replace(/\/$/, '');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function main() {
  const J = async (u, o) => (await fetch(BASE + u, o)).json();
  const put = (u, b) => J(u, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
  await J('/api/engine/stop', { method: 'POST' }); await J('/api/branch/engine/stop', { method: 'POST' });
  await put('/api/config', { source: { kind: 'csv_file', path: 'data/nilm_bus_mixed.csv', file_speed: 0, play_window: false, custom_time: false }, branch: { enabled: false } });
  // 先播一遍文件，让趋势 history 有数据
  await J('/api/engine/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: 'csv_file', path: 'data/nilm_bus_mixed.csv', file_speed: 0 }) });
  for (let k = 0; k < 60; k++) { await sleep(500); const st = await J('/api/state'); if (!st.running) break; }
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8'); const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const calls = [];
  const dom = new JSDOM(html, { url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true, beforeParse(window) {
    window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, { get: (t, p) => (p === 'measureText' ? () => ({ width: 8 }) : p === 'createLinearGradient' ? () => ({ addColorStop() {} }) : () => {}), set: () => true });
    window.WebSocket = class { constructor() { this.readyState = 0; } close() {} send() {} };
    window.fetch = async (url, opts = {}) => { const abs = String(url).startsWith('http') ? String(url) : BASE + url; const r = await fetch(abs, opts); calls.push({ url: String(url), method: opts.method || 'GET', status: r.status, body: opts.body || null }); return r; };
    window.alert = () => {}; window.scrollTo = () => {};
  } });
  const { window } = dom, { document } = window;
  window.__toasts = [];
  window.eval(js + '\n;window.__S = () => S; window.__SD = SD; window.__refreshHistory = refreshHistory; const __toast0 = toast; toast = function (m, k) { window.__toasts.push([String(m), k]); return __toast0(m, k); };');
  if (typeof window.init === 'function') window.init();
  await sleep(2500); await window.__refreshHistory(); await sleep(500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(1500); };
  const ctx = (cv, frac = 0.5) => { const r = { left: 0, width: 800 }; cv.getBoundingClientRect = () => ({ left: 0, top: 0, width: 800, height: 240 }); cv.dispatchEvent(new window.MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX: 60 + (740 * frac), clientY: 100 })); return $('ctxmenu') || document.querySelector('.ctxmenu'); };
  const menuKeys = (m) => Array.from(m.querySelectorAll('.mi')).map((d) => d.dataset.key + (d.classList.contains('disabled') ? '!' : ''));
  const menuItem = (m, key) => Array.from(m.querySelectorAll('.mi')).find((d) => d.dataset.key === key);
  let fail = 0; const check = (n, ok, info) => { console.log((ok ? '  ✓ ' : '  ✗ ') + n + (info ? '　' + String(info).slice(0, 160) : '')); if (!ok) fail++; };
  const V = [['voltage', 'v', 3, 'U'], ['current', 'i', 3, 'I'], ['power', 'p', 3, 'P']];
  for (const [view, pre, nSer, f] of V) {
    console.log(`— ${view}`);
    await nav(view); await sleep(1200);
    const cvT = $(pre + '-trend'), cvC = $(pre + '-cyc'), cvW = $(pre + '-wave2');
    check(`${view}：趋势 / 周波窗（有效值）/ 周波窗（瞬时值）三块画布存在`, !!cvT && !!cvC && !!cvW);
    const ch = cvT.__chart;
    check(`${view}：趋势图有曲线（history）`, !!ch && ch.pts && ch.pts.length >= nSer && ch.pts[0].data.length >= 2, ch && ch.pts ? ch.pts.length + ' 条 × ' + ch.pts[0].data.length : '无 chart');
    const m = ctx(cvT, 0.5);
    check(`${view}：趋势图右键菜单＝原生三项 + 显示周波窗（有效值）+ 显示周波窗（瞬时值）+ 复位缩放（同负荷辨识页）`, !!m && menuKeys(m).join(',') === 'copy-image,save-image,open-image,show-window,show-window2,zoom-reset,native!', m && menuKeys(m).join(','));
    // 点「显示周波窗（有效值）」
    calls.length = 0; click(menuItem(m, 'show-window')); await sleep(2500);
    const cc = cvC.__chart; const cycCall = calls.find((c) => /\/api\/elec\/cycles_file/.test(c.url));
    check(`${view}：周波窗（有效值）走 /api/elec/cycles_file?t=中心&n=300，画出 ${nSer} 条 × 300 点`, !!cycCall && /t=/.test(cycCall.url) && /n=300/.test(cycCall.url) && cc && cc.pts.length === nSer && cc.pts.every((s) => s.data.length === 300), cycCall && cycCall.url.slice(0, 80));
    const vals = cc ? cc.pts[0].data.map((p) => p[1]) : [];
    check(`${view}：周波窗（有效值）是有效值 / 功率（同周波内恒定、非正弦瞬时值）`, vals.length && vals.every((v) => f === 'P' || v > 0) && (Math.max(...vals) / Math.min(...vals.filter((v) => v > 0)) < 50), vals.slice(0, 3).join(','));
    check(`${view}：周波窗（有效值）副标题含周波数与中心时刻`, /300 个周波/.test($(pre + '-cyc-sub').textContent) && /中心/.test($(pre + '-cyc-sub').textContent), $(pre + '-cyc-sub').textContent.slice(0, 100));
    check(`${view}：装载时刻输入框被回填为中心时刻`, /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}$/.test($(pre + '-win-t').value), $(pre + '-win-t').value);
    // 点「显示周波窗（瞬时值）」
    const m2 = ctx(cvT, 0.5); calls.length = 0; click(menuItem(m2, 'show-window2')); await sleep(2500);
    const cw = cvW.__chart; const wCall = calls.find((c) => /\/api\/nilm\/wave_file/.test(c.url));
    const nVis = view === 'power' ? 1 : nSer;        // 功率页：总 p(t) 可见，分相 pA/pB/pC 默认隐藏（图例勾选）
    check(`${view}：周波窗（瞬时值）走 /api/nilm/wave_file（通道 ${view === 'power' ? '6' : '3'}），300 周波 × 128 点 = 38400 点`, !!wCall && cw && cw.pts.length === nVis && cw.pts[0].data.length === 38400 && (view !== 'power' || /6 通道/.test($(pre + '-wave2-sub').textContent)), wCall && wCall.url.slice(0, 90) + ' | ' + (cw ? cw.pts.length + '×' + cw.pts[0].data.length : ''));
    const w0 = cw ? cw.pts[0].data.map((p) => p[1]) : [];
    check(`${view}：周波窗（瞬时值）为瞬时值（${view === 'power' ? '对称负荷 p(t) 总≈3×P 且恒正' : '同一周波内有正有负'}）`, w0.length && (view === 'power' ? (Math.min(...w0.slice(0, 128)) > 0 && Math.abs(w0[0] - vals[0]) / vals[0] < 0.05) : (Math.min(...w0.slice(0, 128)) < 0 && Math.max(...w0.slice(0, 128)) > 0)), w0.slice(0, 2).join(','));
    check(`${view}：周波窗（有效值）与周波窗（瞬时值）同一段（起点时刻一致）`, cc && cw && Math.abs(cc.opt.tbase - cw.opt.tbase) < 1.5 / 50, cc && cw ? (cc.opt.tbase - cw.opt.tbase) : '');
    const m3 = ctx(cvC); check(`${view}：周波窗（有效值）右键＝原生三项 + 复位缩放`, !!m3 && /copy-image.*save-image.*open-image.*zoom-reset/.test(menuKeys(m3).join(',')), m3 && menuKeys(m3).join(','));
    const m4 = ctx(cvW); check(`${view}：周波窗（瞬时值）右键＝原生三项 + 复位缩放`, !!m4 && /copy-image.*save-image.*open-image.*zoom-reset/.test(menuKeys(m4).join(',')), m4 && menuKeys(m4).join(','));
    if (view === 'power') {
      $('p-cyc-ch').value = 'A'; change($('p-cyc-ch')); await sleep(400);
      const ccA = cvC.__chart; check('power：对象切到 A 相 → 周波窗（有效值）画 A 相 P/Q/S', ccA && /A 相/.test(ccA.pts[0].name) && Math.abs(ccA.pts[0].data[0][1]) < Math.abs(vals[0]), ccA && ccA.pts[0].name);
      check('power：周波窗（瞬时值）可见曲线＝总 p(t)（分相 pA/pB/pC 默认隐藏于图例）', cw.pts.length === 1 && /总瞬时功率/.test(cw.pts[0].name), cw.pts[0].name);
    }
    // 清除
    click($('btn-' + pre + '-wave2-clear')); await sleep(300);
    check(`${view}：「清除」周波窗（瞬时值）后画布为空、周波窗（有效值）保留`, !(cvW.__chart && cvW.__chart.pts && cvW.__chart.pts.length) && cvC.__chart && cvC.__chart.pts.length >= 1);
    click($('btn-' + pre + '-win-clear')); await sleep(300);
    check(`${view}：「清除」后周波窗（有效值）也为空`, !(cvC.__chart && cvC.__chart.pts && cvC.__chart.pts.length));
    // 手动装载（时刻留空＝数据起点起 50 个周波）
    $(pre + '-win-t').value = ''; $(pre + '-win-count').value = '50'; click($('btn-' + pre + '-win-load')); await sleep(2000);
    const ccB = cvC.__chart; check(`${view}：手动装载（留空＝数据起点起 50 周波）`, ccB && ccB.pts[0].data.length === 50 && /数据起点起/.test($(pre + '-win-src').textContent), $(pre + '-win-src').textContent.slice(0, 80));
  }
  // 实时源：菜单灰显、装载按钮禁用
  console.log('— 实时源（模拟器）');
  await put('/api/config', { source: { kind: 'simulator' } }); await sleep(2500); await nav('voltage'); await sleep(800);
  const m5 = ctx($('v-trend')); const keys5 = m5 ? menuKeys(m5) : [];
  check('模拟器源：趋势图右键「显示周波窗（有效值）/（瞬时值）」灰显、原生项与复位缩放仍可用', keys5.includes('show-window!') && keys5.includes('show-window2!') && keys5.includes('copy-image') && keys5.includes('zoom-reset'), keys5.join(','));
  check('模拟器源：装载按钮禁用并提示只能离线文件', $('btn-v-win-load').disabled && /离线文件/.test($('v-win-src').textContent), $('v-win-src').textContent);
  await put('/api/config', { source: { kind: 'csv_file', path: 'data/nilm_bus_mixed.csv' } }); await sleep(2500); click(document.querySelector('.navitem[data-view="current"]')); await sleep(800); await nav('voltage'); await sleep(800);
  check('改回离线文件：装载按钮恢复可用', !$('btn-v-win-load').disabled);
  // 分路侧右列：独立面板、独立数据
  console.log('— 分路侧右列');
  await put('/api/branch/config', { source: { kind: 'csv_file', path: 'data/nilm_steps.csv', custom_time: false } });
  await put('/api/config', { branch: { enabled: true, common_window: false } }); await sleep(2500);
  await nav('source'); await sleep(800); await nav('current'); await sleep(2000);
  const brT = $('i-trend-br'), brC = $('i-cyc-br');
  check('分路侧右列有自己的趋势 / 周波窗画布与按钮', !!brT && !!brC && !!$('btn-i-win-load-br') && !!$('i-win-count-br'));
  $('i-win-t-br').value = ''; $('i-win-count-br').value = '40'; calls.length = 0; click($('btn-i-win-load-br')); await sleep(2500);
  const brCall = calls.find((c) => /\/api\/branch\/elec\/cycles_file/.test(c.url));
  check('右列「装载周波窗」→ /api/branch/elec/cycles_file，画 40 周波（nilm_steps.csv），左列不受影响', !!brCall && brC.__chart && brC.__chart.pts[0].data.length === 40 && /nilm_steps/.test($('i-win-src-br').textContent) && $('i-cyc').__chart && $('i-cyc').__chart.pts[0].data.length === 50 && /nilm_bus_mixed/.test($('i-win-src').textContent), (brCall || {}).url + ' | ' + $('i-win-src-br').textContent.slice(0, 60));
  await put('/api/config', { branch: { enabled: false } });
  console.log(fail ? `FAIL ${fail}` : 'ALL PASS'); process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
