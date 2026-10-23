/* 第 96 轮界面检查（v0.75）：界面上**所有**「保存总线侧配置 / 保存分路侧配置」按钮是否都在原配置文件基础上只改变化的键。
 * 方法：服务用临时配置文件（含自定义键 my_custom_note），每个按钮两步：① 不改任何值直接点 → 两侧文件字节一字不变；
 *       ② 改一项再点 → 文件只多出该项（及同面板键）的差异，自定义键 / 其它节 / 缩进原样。
 * 用法：ELEC_TOOL_CONFIG_PATH=/tmp/cfg75/runtime.json ELEC_TOOL_BRANCH_CONFIG_PATH=/tmp/cfg75/branch_runtime.json 起服务后：
 *       CFG_BUS=/tmp/cfg75/runtime.json CFG_BR=/tmp/cfg75/branch_runtime.json JSDOM_DIR=/tmp/uitest node tools/ui_r75_check.cjs http://127.0.0.1:8034 */
const fs = require('fs'), path = require('path');
const { JSDOM } = require(path.join(process.env.JSDOM_DIR || '/tmp/uitest', 'node_modules/jsdom'));
const ROOT = path.join(__dirname, '..'); const BASE = (process.argv[2] || 'http://127.0.0.1:8000').replace(/\/$/, '');
const CFG_BUS = process.env.CFG_BUS, CFG_BR = process.env.CFG_BR;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function flat(d, p = '', out = {}) { for (const k of Object.keys(d || {})) { const v = d[k]; if (v && typeof v === 'object' && !Array.isArray(v)) flat(v, p + k + '.', out); else out[p + k] = JSON.stringify(v); } return out; }
function diffKeys(a, b) { const fa = flat(a), fb = flat(b); const ks = new Set([...Object.keys(fa), ...Object.keys(fb)]); return [...ks].filter((k) => fa[k] !== fb[k]).sort(); }
const raw = (p) => fs.readFileSync(p, 'utf8');
async function main() {
  if (!CFG_BUS || !CFG_BR) { console.error('需要 CFG_BUS / CFG_BR'); process.exit(2); }
  const J = async (u, o) => (await fetch(BASE + u, o)).json();
  await J('/api/engine/stop', { method: 'POST' }); await J('/api/branch/engine/stop', { method: 'POST' });
  // 右列（分路侧）只有在分路侧启用时才渲染/可点，先启用（这一步本身会写 branch.enabled，属预期）
  await J('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ branch: { enabled: true } }) });
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8'); const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const calls = [];
  const dom = new JSDOM(html, { url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true, beforeParse(window) {
    window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, { get: (t, p) => (p === 'measureText' ? () => ({ width: 8 }) : p === 'createLinearGradient' ? () => ({ addColorStop() {} }) : () => {}), set: () => true });
    window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
    Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get() { return 900; } });
    window.WebSocket = class { constructor() { this.readyState = 0; } close() {} send() {} };
    window.fetch = async (url, opts = {}) => { const abs = String(url).startsWith('http') ? String(url) : BASE + url; const r = await fetch(abs, opts); calls.push({ url: String(url), method: opts.method || 'GET', status: r.status, body: opts.body || null }); return r; };
    window.alert = () => {};
  } });
  const { window } = dom, { document } = window;
  window.eval(js + '\n;window.__S = () => S;');
  if (typeof window.init === 'function') window.init();
  await sleep(1800);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => { el.dispatchEvent(new window.Event('input', { bubbles: true })); el.dispatchEvent(new window.Event('change', { bubbles: true })); };
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(1500); };
  let fail = 0; const check = (n, ok, info) => { console.log((ok ? '  ✓ ' : '  ✗ ') + n + (info ? '　' + info : '')); if (!ok) fail++; };
  const putsSince = (n) => calls.slice(n).filter((c) => /\/api\/(branch\/)?config$/.test(c.url) && c.method === 'PUT');

  // 先把两侧面板都加载一遍（数据源页会装载分路侧面板）
  await nav('source'); await sleep(1500);
  for (const v of ['windows', 'events', 'nilm', 'export', 'compare']) { await nav(v); }

  const buttons = [
    // [按钮 id, 所在视图, 侧, 允许变化的键前缀, 改一项的函数（返回描述）]
    ['btn-src-save', 'source', 'bus', /^(source|transform|sampling|harmonic|power|columns)\./, () => { $('cfg-ct').value = '16'; change($('cfg-ct')); return 'transform.ct_ratio=16'; }],
    ['btn-savecfg', 'source', 'bus', /^(transform|sampling|harmonic|power|source)\./, () => { $('cfg-pt').value = '101'; change($('cfg-pt')); return 'transform.pt_ratio=101'; }],
    ['btn-map-save', 'source', 'bus', /^columns\./, () => { $('cfg-map-ua').value = '9'; change($('cfg-map-ua')); return 'columns.mapping.ua=9'; }],
    ['btn-br-save', 'source', 'branch', /^(source|transform|sampling|harmonic|power|columns)\./, () => { const el = $('br-ct'); if (!el) return null; el.value = '17'; change(el); return 'branch transform.ct_ratio=17'; }],
    ['btn-br-savecfg', 'source', 'branch', /^(source|transform|sampling|harmonic|power|columns)\./, () => { const el = $('br-pt'); if (!el) return null; el.value = '102'; change(el); return 'branch transform.pt_ratio=102'; }],
    ['btn-br-map-save', 'source', 'branch', /^columns\./, () => { const el = $('br-map-ua'); if (!el) return null; el.value = '3'; change(el); return 'branch columns.mapping.ua=3'; }],
    ['btn-save-win', 'windows', 'bus', /^windows\./, () => { const el = document.querySelector('#view-windows input[type=number]'); if (!el) return null; el.value = String((+el.value || 1) + 1); change(el); return 'windows.*'; }],
    ['btn-save-win-br', 'windows', 'branch', /^windows\./, () => { const el = document.querySelector('#w-table-br input[type=number]'); if (!el) return null; el.value = String((+el.value || 1) + 1); change(el); return 'branch windows.*'; }],
    ['btn-ev-save', 'events', 'bus', /^events\./, () => { $('ev-u1_high_pct').value = '111'; change($('ev-u1_high_pct')); return 'events.u1_high_pct=111'; }],
    ['btn-ev-save-br', 'events', 'branch', /^events\./, () => { const el = $('ev-u1_high_pct-br'); if (!el) return null; el.value = '112'; change(el); return 'branch events.u1_high_pct=112'; }],
    ['btn-nilm-save', 'nilm', 'bus', /^nilm\./, () => { $('nilm-rel_tol_pct').value = '7'; change($('nilm-rel_tol_pct')); return 'nilm.rel_tol_pct=7'; }],
    ['btn-nilm-save-br', 'nilm', 'branch', /^nilm\./, () => { const el = $('nilm-rel_tol_pct-br'); if (!el) return null; el.value = '8'; change(el); return 'branch nilm.rel_tol_pct=8'; }],
    ['btn-rt-save', 'export', 'bus', /^output\./, () => { $('rt-enable').checked = !$('rt-enable').checked; change($('rt-enable')); return 'output.realtime_save 翻转'; }],
    ['btn-rt-save-br', 'export', 'branch', /^output\./, () => { const el = $('rt-enable-br'); if (!el) return null; el.checked = !el.checked; change(el); return 'branch output.realtime_save 翻转'; }],
    ['btn-save-cfgfile', 'export', 'bus', /^$/, null],
    ['btn-save-cfgfile-br', 'export', 'branch', /^$/, null],
    ['btn-cmp-save', 'compare', 'bus', /^branch\.time_offset_s$/, () => { $('cmp-offset').value = '1.5'; change($('cmp-offset')); return 'branch.time_offset_s=1.5'; }],
  ];
  for (const [id, view, side, allow, mutate] of buttons) {
    const btn = $(id);
    console.log(`— ${id}（${side === 'branch' ? '分路侧' : '总线侧'} · ${view}）`);
    if (!btn) { check(`按钮 ${id} 存在`, false); continue; }
    await nav(view); await sleep(500);
    // ① 不改值直接保存 → 两侧文件一字不变
    const b0 = raw(CFG_BUS), r0 = raw(CFG_BR); const n0 = calls.length;
    click(btn); await sleep(1500);
    const puts = putsSince(n0);
    check(`${id}：不改值点保存 → 发 PUT 且两侧配置文件字节不变`, puts.length >= 1 && puts.every((p) => p.status === 200) && raw(CFG_BUS) === b0 && raw(CFG_BR) === r0,
          puts.length ? `${puts.length} 次 PUT；bus ${raw(CFG_BUS) === b0 ? '不变' : '变了:' + diffKeys(JSON.parse(b0), JSON.parse(raw(CFG_BUS))).join(',')}；branch ${raw(CFG_BR) === r0 ? '不变' : '变了:' + diffKeys(JSON.parse(r0), JSON.parse(raw(CFG_BR))).join(',')}` : '未发 PUT');
    if (!mutate) continue;
    // ② 改一项再保存 → 只有该面板的键变化，自定义键 / 其它节 / 缩进原样
    const desc = mutate(); if (!desc) { check(`${id}：找到可改的输入项`, false); continue; }
    const b1 = raw(CFG_BUS), r1 = raw(CFG_BR);
    click(btn); await sleep(1500);
    const target = side === 'branch' && !/^btn-cmp/.test(id) ? CFG_BR : CFG_BUS, other = target === CFG_BR ? CFG_BUS : CFG_BR;
    const before = JSON.parse(target === CFG_BR ? r1 : b1), after = JSON.parse(raw(target));
    const dk = diffKeys(before, after); const p2 = putsSince(calls.length - 3).map((p) => p.status).join('/');
    const otherSame = raw(other) === (other === CFG_BR ? r1 : b1) || id === 'btn-br-save' || id === 'btn-br-savecfg';   // 分路侧保存会同时写总线侧 branch.* 联动键
    check(`${id}：改 ${desc} 后保存 → 目标文件只有 ${allow} 键变化（实际 ${dk.length} 项），自定义键保留，缩进 4 空格保留，另一侧文件不变`,
          dk.length >= 1 && dk.every((k) => allow.test(k)) && after.my_custom_note === before.my_custom_note && raw(target).startsWith('{\n    "') && otherSame, dk.slice(0, 6).join(',') + (dk.length > 6 ? '…' : '') + ' PUT状态:' + p2);
  }
  console.log(fail ? `FAIL ${fail}` : 'ALL PASS');
  window.close(); process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
