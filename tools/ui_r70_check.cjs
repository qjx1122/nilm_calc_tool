/* 第 70 轮界面检查（v0.70）：数据源页分路侧联动参数按「界面当前值」启动 / 预览（不写配置）。
 * 场景（用户实录）：已保存 common_window=true 且两侧文件无公共时间段；界面取消勾选但不保存 → 点「启动」不得报「两侧文件没有公共时间段」。
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r70_check.cjs http://127.0.0.1:8000   （需 data/ov_bus.csv、data/ov_br.csv，脚本自动生成） */
const fs = require('fs'), path = require('path');
const { JSDOM } = require(path.join(process.env.JSDOM_DIR || '/tmp/uitest', 'node_modules/jsdom'));
const ROOT = path.join(__dirname, '..'); const BASE = (process.argv[2] || 'http://127.0.0.1:8000').replace(/\/$/, '');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function genCsv(p, t0, dur, fs0 = 6400) {
  const n = Math.round(dur * fs0); const rows = ['时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流'];
  for (let k = 0; k < n; k++) { const ph = 2 * Math.PI * 50 * k / fs0; const r = [(t0 + k / fs0).toFixed(6)];
    for (const o of [0, -2.0944, 2.0944]) r.push((81.65 * Math.sin(ph + o)).toFixed(4), (5 * Math.sin(ph + o)).toFixed(5)); rows.push(r.join(',')); }
  fs.writeFileSync(p, rows.join('\n') + '\n');
}
async function main() {
  fs.mkdirSync(path.join(ROOT, 'data'), { recursive: true });
  genCsv(path.join(ROOT, 'data/ov_bus.csv'), 1760300000, 1.0); genCsv(path.join(ROOT, 'data/ov_br.csv'), 1760300100, 1.0);
  const J = async (u, o) => (await fetch(BASE + u, o)).json();
  const put = (u, b) => J(u, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
  await J('/api/engine/stop', { method: 'POST' }); await J('/api/branch/engine/stop', { method: 'POST' });
  await put('/api/config', { source: { kind: 'csv_file', path: 'data/ov_bus.csv', file_speed: 0, play_window: false, custom_time: false }, branch: { enabled: true, common_window: true, common_start: '', common_end: '' } });
  await put('/api/branch/config', { source: { kind: 'csv_file', path: 'data/ov_br.csv', custom_time: false } });
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8'); const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const calls = [];
  const dom = new JSDOM(html, { url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true, beforeParse(window) {
    window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, { get: (t, p) => (p === 'measureText' ? () => ({ width: 8 }) : p === 'createLinearGradient' ? () => ({ addColorStop() {} }) : () => {}), set: () => true });
    window.WebSocket = class { constructor() { this.readyState = 0; } close() {} send() {} };
    window.fetch = async (url, opts = {}) => { const abs = String(url).startsWith('http') ? String(url) : BASE + url; const r = await fetch(abs, opts); calls.push({ url: String(url), method: opts.method || 'GET', status: r.status, body: opts.body || null }); return r; };
    window.alert = () => {};
  } });
  const { window } = dom, { document } = window;
  window.__toasts = [];
  window.eval(js + '\n;window.__S = () => S; const __toast0 = toast; toast = function (m, k) { window.__toasts.push([String(m), k]); return __toast0(m, k); };');
  if (typeof window.init === 'function') window.init();
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(1200); };
  let fail = 0; const check = (n, ok, info) => { console.log((ok ? '  ✓ ' : '  ✗ ') + n + (info ? '　' + info : '')); if (!ok) fail++; };
  await nav('source'); await sleep(1500);
  check('面板已按保存值填充：启用分路侧 + 公共时间段已勾选', $('br-enabled').checked && $('br-common').checked);
  $('br-common').checked = false; change($('br-common'));
  window.__toasts.length = 0; calls.length = 0; click($('btn-start')); await sleep(3500);
  const toasts = window.__toasts.map((t) => t[0]);
  check('取消勾选（未保存）后点「启动」成功，不再报「两侧文件没有公共时间段」', !toasts.some((t) => /没有公共时间段|启动失败/.test(t)) && toasts.some((t) => /已启动总线侧数据源/.test(t)), JSON.stringify(toasts.map((t) => t.slice(0, 70))));
  const sc = calls.find((c) => /\/api\/engine\/start$/.test(c.url)); const body = sc && JSON.parse(sc.body);
  check('启动请求带 branch.common_window=false、branch.enabled=true 与 branch_source（分路侧文件）', !!body && body.branch && body.branch.common_window === false && body.branch.enabled === true && body.branch_source && /ov_br/.test(body.branch_source.path || ''), sc && sc.body.slice(0, 200));
  const st = await J('/api/state'), brst = await J('/api/branch/state');
  check('两侧都启动了（各播各的；总线 1 s 文件 6400 点、分路侧同理）', st.engine.samples_in > 0 && brst.engine.samples_in > 0, `bus=${st.engine.samples_in} br=${brst.engine.samples_in}`);
  // 重新勾选 → 「预览公共时间段」按界面值 → 提示没有公共时间段（不启动、不报启动失败）
  $('br-common').checked = true; calls.length = 0; click($('btn-br-common-preview')); await sleep(1500);
  const pv = calls.find((c) => /common_window\/preview/.test(c.url));
  check('预览走 POST /api/common_window/preview 且带界面值（common_window=true + branch_source）', !!pv && JSON.parse(pv.body).branch.common_window === true && /ov_br/.test(JSON.parse(pv.body).branch_source.path || ''));
  check('预览结果提示「没有公共时间段」', /没有公共时间段/.test($('br-common-out').textContent), $('br-common-out').textContent.slice(0, 90));
  // 改分路侧文件为有交集的（未保存）→ 预览给出交集；配置文件里仍是旧文件
  genCsv(path.join(ROOT, 'data/ov_br2.csv'), 1760300000.5, 1.0);
  $('br-path').value = 'data/ov_br2.csv'; change($('br-path')); click($('btn-br-common-preview')); await sleep(1500);
  check('改分路侧文件（未保存）→ 预览按界面文件算出公共时间段 0.5 s', /公共时间段：/.test($('br-common-out').textContent) && /0\.5\d* s/.test($('br-common-out').textContent), $('br-common-out').textContent.slice(0, 120));
  const brcfg = await J('/api/branch/config');
  check('分路侧配置未被预览改写（仍为 ov_br.csv）', /ov_br\.csv$/.test(brcfg.source.path));
  await J('/api/engine/stop', { method: 'POST' }); await J('/api/branch/engine/stop', { method: 'POST' });
  await put('/api/config', { branch: { enabled: false, common_window: false } });
  for (const f of ['ov_bus.csv', 'ov_br.csv', 'ov_br2.csv']) { try { fs.unlinkSync(path.join(ROOT, 'data', f)); } catch (e) {} }
  console.log(fail ? `FAIL ${fail}` : `ALL PASS`); process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
