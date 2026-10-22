#!/usr/bin/env node
/* 第 12 轮界面检查：「负荷辨识」子界面（事件检测 6 算法 / 周波窗 / 参数表单 / 落盘）。
 * jsdom 驱动真实 index.html + app.js，打真实服务端（需先 serve 在 8000，data/sample_6400hz.csv 存在）。
 *
 *   L1 导航含「负荷辨识」；参数表单按 6 个算法生成并回填服务端配置
 *   L2 播放 data/nilm_steps.csv 后：卡片计数、事件表含 6 算法、方向 ↑/↓、幅值、起止时间；周波窗曲线有点
 *   L3 过滤算法 → 表格只剩该算法；改 GLR 门限 → 保存 → PUT /api/config 载荷含 nilm.algorithms.glr.threshold；服务端生效
 *   L4 清空 → 表格为空；徽标归零
 *
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r12_check.cjs [baseUrl]
 */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require(path.join(process.env.JSDOM_DIR || '/tmp/uitest', 'node_modules/jsdom'));

const BASE = process.argv[2] || 'http://127.0.0.1:8000';
const ROOT = path.resolve(__dirname, '..');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let pass = 0, fail = 0; const fails = [];
function check(name, ok, detail = '') {
  if (ok) { pass++; console.log(`  ✓ ${name}${detail ? '　' + detail : ''}`); }
  else { fail++; fails.push(name); console.log(`  ✗ ${name}　${detail}`); }
}

async function main() {
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const calls = [];
  const dom = new JSDOM(html, {
    url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true,
    beforeParse(window) {
      window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, {
        get: (t, p) => (p === 'measureText' ? () => ({ width: 8 }) : p === 'createLinearGradient' ? () => ({ addColorStop() {} }) : () => {}),
        set: () => true,
      });
      window.WebSocket = class { constructor() { this.readyState = 0; } close() {} send() {} };
      window.fetch = async (url, opts = {}) => {
        const abs = String(url).startsWith('http') ? String(url) : BASE + url;
        const r = await fetch(abs, opts);
        calls.push({ url: String(url), method: opts.method || 'GET', status: r.status, body: opts.body || null });
        return r;
      };
      window.alert = () => {};
    },
  });
  const { window } = dom, { document } = window;
  window.eval(js + '\n;window.__S = () => S; window.__render = render;');
  if (typeof window.init === 'function') window.init();
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const input = (el) => el.dispatchEvent(new window.Event('input', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(700); };
  const api = async (u, o) => (await fetch(BASE + u, o)).json();
  const bodies = (u, m) => calls.filter((c) => c.url.includes(u) && c.method === m && c.body).map((c) => JSON.parse(c.body));

  await api('/api/engine/stop', { method: 'POST' });
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nilm: { enabled: true, min_delta_pct: 0, channels: ['total'], algorithms: { glr: { threshold: 25, enabled: true } } } }) });
  await api('/api/nilm/clear', { method: 'POST' });
  console.log('L1 导航与表单');
  check('导航含负荷辨识', !!document.querySelector('.navitem[data-view="nilm"]'));
  await nav('nilm'); await sleep(1200);
  const algos = ['threshold', 'two_window', 'cusum', 'glr', 'steady_state', 'median_diff'];
  check('6 个算法启用框存在', algos.every(a => !!$(`nilm-${a}-enabled`)));
  check('GLR 门限回填 25', $('nilm-glr-threshold').value === '25', $('nilm-glr-threshold').value);
  check('检测对象回填 total', $('nilm-ch-total').checked && !$('nilm-ch-A').checked);
  check('周波窗长回填', +$('nilm-window_cycles').value >= 30);

  console.log('L2 播放与事件');
  await api('/api/engine/start', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind: 'csv_file', path: 'data/nilm_steps.csv', realtime: false }) });
  await sleep(9000);
  click($('btn-nilm-refresh')); await sleep(1500);
  const txt = $('nilm-table').textContent || '';
  check('事件表含 6 种算法', ['阈值差分', '双滑窗', 'CUSUM', 'GLR', '稳态分段', '中值滤波'].every(n => txt.includes(n)), txt.slice(0, 120));
  check('事件表含方向 ↑投入 与 ↓切除', txt.includes('投入') && txt.includes('切除'));
  check('事件表幅值列表头带 kW/MW 单位、单元格纯数字（v0.25 单位进表头）', /幅值 \|ΔP\| \([kM]W\)/.test(txt) && !/\d+(\.\d+)?\s*[kM]?W(?!\))/.test(txt), (txt.match(/幅值[^）]*?\)/) || [''])[0]);
  const cards = $('nilm-cards').textContent;
  check('卡片含累计条数与周波窗', /累计 \d+ 条/.test(cards) && /周波/.test(cards));
  check('周波窗曲线有点', +$('nilm-win-n').textContent > 0, $('nilm-win-n').textContent);
  const ev = await api('/api/nilm/events?limit=5');
  check('REST 事件含 t_start/t_end/direction/magnitude_w', ev.events.length > 0 && ['t_start', 't_end', 'direction', 'magnitude_w', 'algorithm'].every(k => k in ev.events[0]));

  console.log('L3 过滤与保存');
  $('nilm-filter').value = 'glr'; change($('nilm-filter')); await sleep(1200);
  const t2 = $('nilm-table').textContent;
  check('过滤 GLR 后只剩 GLR', t2.includes('GLR') && !t2.includes('CUSUM') && !t2.includes('稳态分段'));
  // v0.48：三块面板的选择各自独立——列表筛选不改变趋势图/周波窗的事件竖线数；周波窗对象/算法不改变趋势图与列表；趋势图对象不改变周波窗与列表
  const nPqs0 = $('nilm-pqs-n').textContent, nEv0 = window.SD.bus.nl.events.length;
  check('列表筛选 GLR 后：趋势图竖线数不变、nl.events 仍全量', $('nilm-pqs-n').textContent === nPqs0 && window.SD.bus.nl.events.length === nEv0 && /\//.test($('nilm-total').textContent), JSON.stringify([nPqs0, $('nilm-pqs-n').textContent, $('nilm-total').textContent]));
  $('nilm-chfilter').value = 'A'; change($('nilm-chfilter')); await sleep(300);
  check('列表对象筛选 A（无 A 事件）→ 列表「当前筛选下无事件」、趋势图竖线仍不变', /当前筛选下无事件/.test($('nilm-table').textContent) && $('nilm-pqs-n').textContent === nPqs0);
  $('nilm-chfilter').value = ''; $('nilm-filter').value = ''; change($('nilm-filter')); await sleep(300);
  const rows0 = $('nilm-table').querySelectorAll('tbody tr').length;
  $('nilm-mark').value = 'cusum'; $('nilm-qty').value = 'q'; change($('nilm-mark')); await sleep(300);
  check('周波窗标注算法/量切换 → 列表行数与趋势图竖线数不变', $('nilm-table').querySelectorAll('tbody tr').length === rows0 && $('nilm-pqs-n').textContent === nPqs0);
  $('nilm-mark').value = ''; $('nilm-qty').value = 'p'; change($('nilm-qty'));
  const winN0 = $('nilm-win-n').textContent;
  $('nilm-pqs-ch').value = 'A'; change($('nilm-pqs-ch')); await sleep(300);
  check('趋势图对象切 A → 竖线变 0，但周波窗周波数与列表行数不变', $('nilm-pqs-n').textContent === '0' && $('nilm-win-n').textContent === winN0 && $('nilm-table').querySelectorAll('tbody tr').length === rows0);
  $('nilm-pqs-ch').value = ''; change($('nilm-pqs-ch')); await sleep(200);
  $('nilm-glr-threshold').value = '40'; input($('nilm-glr-threshold'));
  click($('btn-nilm-save')); await sleep(1500);
  const puts = bodies('/api/config', 'PUT'); const last = puts[puts.length - 1] || {};
  check('PUT 载荷 nilm.algorithms.glr.threshold=40', last.nilm && last.nilm.algorithms && last.nilm.algorithms.glr.threshold === 40, JSON.stringify(last.nilm && last.nilm.algorithms && last.nilm.algorithms.glr));
  const st = await api('/api/state');
  check('服务端配置生效', st.config.nilm.algorithms.glr.threshold === 40 && st.config.nilm.algorithms.cusum.threshold_w === 200);

  console.log('L5 v0.36 仅电流检测（quantity）');
  check('表单含检测量下拉 auto/p/i', !!$('nilm-quantity') && [...$('nilm-quantity').options].map((o) => o.value).join(',') === 'auto,p,i');
  check('回填默认 auto', $('nilm-quantity').value === 'auto');
  $('nilm-quantity').value = 'i'; change($('nilm-quantity')); click($('btn-nilm-save')); await sleep(1200);
  const putsQ = bodies('/api/config', 'PUT'); const lastQ = putsQ[putsQ.length - 1] || {};
  check('PUT 载荷 nilm.quantity="i"（字符串）', lastQ.nilm && lastQ.nilm.quantity === 'i', JSON.stringify(lastQ.nilm && lastQ.nilm.quantity));
  check('服务端配置 quantity=i', (await api('/api/state')).config.nilm.quantity === 'i');
  $('nilm-quantity').value = 'auto'; change($('nilm-quantity')); click($('btn-nilm-save')); await sleep(1200);
  await api('/api/nilm/clear', { method: 'POST' });
  const stQ = await api('/api/engine/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: 'csv_file', path: 'data/nilm_steps_i.csv', realtime: false }) });
  check('仅电流样例 data/nilm_steps_i.csv 可启动播放', stQ.ok !== false, JSON.stringify(stQ).slice(0, 120));
  for (let k = 0; k < 60; k++) { const s2 = await api('/api/state'); if (s2.finished || s2.error) break; await sleep(500); }
  const evQ = await api('/api/nilm/events?limit=200');
  check('summary.voltage_missing=true、quantity_effective=i、事件 ≥ 12', evQ.summary.voltage_missing === true && evQ.summary.quantity_effective === 'i' && evQ.summary.total >= 12, JSON.stringify([evQ.summary.voltage_missing, evQ.summary.quantity_effective, evQ.summary.total]));
  check('六种算法都有事件、全部 unit=A', new Set(evQ.events.map((e) => e.algorithm)).size === 6 && evQ.events.every((e) => e.unit === 'A' && e.quantity === 'i'));
  click($('btn-nilm-refresh')); await sleep(1500);
  check('界面表头幅值列为 |ΔI|（A）', /幅值 \|ΔI\|/.test($('nilm-table').textContent) && !/幅值 \|ΔP\|/.test($('nilm-table').textContent), ($('nilm-table').textContent.match(/幅值[^）]*）?/) || [''])[0]);
  check('提示区说明按电流有效值检测（auto 自动切换）', /电流有效值/.test($('nilm-notes').textContent) && /auto 自动切换/.test($('nilm-notes').textContent));
  console.log('L6 v0.37 A 口径阈值');
  const aIds = ['nilm-threshold-min_delta_a', 'nilm-threshold-settle_tol_a', 'nilm-two_window-min_delta_a', 'nilm-cusum-drift_a', 'nilm-cusum-threshold_a', 'nilm-glr-noise_a', 'nilm-steady_state-tol_a', 'nilm-median_diff-settle_tol_a'];
  check('表单含各算法 A 口径阈值输入', aIds.every((id) => !!$(id)), aIds.filter((id) => !$(id)).join(','));
  check('A 套回填默认值（cusum threshold_a=1, drift_a=0.05）', +$('nilm-cusum-threshold_a').value === 1 && +$('nilm-cusum-drift_a').value === 0.05, $('nilm-cusum-threshold_a').value);
  check('auto + 无电压（effective=i）→ W 套灰显、A 套高亮', $('nilm-cusum-threshold_w').parentElement.classList.contains('nilm-inactive') && !$('nilm-cusum-threshold_a').parentElement.classList.contains('nilm-inactive'));
  $('nilm-quantity').value = 'p'; change($('nilm-quantity')); await sleep(200);
  check('切到 p → A 套灰显、W 套高亮', $('nilm-cusum-threshold_a').parentElement.classList.contains('nilm-inactive') && !$('nilm-cusum-threshold_w').parentElement.classList.contains('nilm-inactive'));
  $('nilm-quantity').value = 'auto'; change($('nilm-quantity'));
  $('nilm-glr-noise_a').value = '0.2'; input($('nilm-glr-noise_a')); click($('btn-nilm-save')); await sleep(1200);
  const putsA = bodies('/api/config', 'PUT'); const lastA = putsA[putsA.length - 1] || {};
  check('保存 → PUT 含 glr.noise_a=0.2 且 noise_w 仍为 10', lastA.nilm && lastA.nilm.algorithms.glr.noise_a === 0.2 && lastA.nilm.algorithms.glr.noise_w === 10, JSON.stringify(lastA.nilm && lastA.nilm.algorithms.glr));
  check('服务端 glr.noise_a=0.2', (await api('/api/state')).config.nilm.algorithms.glr.noise_a === 0.2);
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nilm: { algorithms: { glr: { noise_a: 0.05 } } } }) });
  console.log('L7 v0.39 I 口径只能单相 + 电流趋势');
  check('仅电流播放：事件无 total、只有 A/B/C（配置 total → 三相各自检测）', !evQ.events.some((e) => e.channel === 'total') && new Set(evQ.events.map((e) => e.channel)).size === 3, JSON.stringify([...new Set(evQ.events.map((e) => e.channel))]));
  check('summary.channels_effective=[A,B,C]', JSON.stringify(evQ.summary.channels_effective) === '["A","B","C"]', JSON.stringify(evQ.summary.channels_effective));
  check('提示区说明「只能单相检测」', /只能单相检测/.test($('nilm-notes').textContent));
  check('检测对象「三相总」灰显（effective=i）', $('nilm-ch-total-lbl').classList.contains('nilm-inactive'));
  check('周波窗卡片对象显示 A/B/C', /对象 A\/B\/C/.test($('nilm-cards').textContent));
  check('趋势图曲线选择器存在、标题栏无重复的三相勾选框（v0.40）', !!$('nilm-pqs-kind') && !document.querySelector('#nilm-pqs-phases') && document.querySelectorAll('.nilm-pqs-ph').length === 0);
  check('v0.44 三块面板括号提示与标题同一行（.hdrhint display:inline、标题行 nowrap）', ['nilm-pqs-n', 'nilm-win-n', 'nilm-total'].every((id) => { const h = $(id).closest('.hdrhint'); return h && h.tagName === 'SMALL' && h.parentElement === h.closest('h3').firstElementChild; }) && /\.hdrhint\{display:inline/.test(await (await fetch(BASE + '/static/style.css')).text()) && /nilm-hdr>span:first-child\{display:flex;align-items:baseline;white-space:nowrap/.test(await (await fetch(BASE + '/static/style.css')).text()));
  check('v0.42 三块面板标题栏带 nilm-hdr、控件栏可换行（CSS 规则存在）', ['nilm-pqs-n', 'nilm-win-n', 'nilm-total'].every((id) => $(id).closest('h3').classList.contains('nilm-hdr')) && /h3\.nilm-hdr>\.toggle\{[^}]*flex-wrap:wrap/.test(await (await fetch(BASE + '/static/style.css')).text()) && /#nilm-table th[^{]*\{white-space:nowrap/.test(await (await fetch(BASE + '/static/style.css')).text()));
  check('v0.43 趋势提示不含「与总览面板同一曲线」、提示单行（nowrap+ellipsis）', !/与总览面板同一曲线/.test($('nilm-pqs-n').closest('.hdrhint').textContent) && /\.hdrhint\{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis/.test(await (await fetch(BASE + '/static/style.css')).text()));
  check('v0.41 标题文本本身不再含括号提示', !/（/.test($('nilm-pqs-title').textContent) && $('nilm-win-n').closest('h3').firstElementChild.firstChild.textContent.trim() === '周波窗');
  check('auto + I 口径 → 趋势标题为三相电流', /三相电流 I 趋势/.test($('nilm-pqs-title').textContent));
  const cs = document.querySelector('#view-nilm .curvespan'); check('曲线跨度标签切到 current', cs && cs.dataset.curve === 'current', cs && cs.dataset.curve);
  $('nilm-pqs-kind').value = 'pqs'; change($('nilm-pqs-kind')); await sleep(300);
  check('切到 P/Q/S → 标题复原', /P \/ Q \/ S 趋势/.test($('nilm-pqs-title').textContent));
  $('nilm-pqs-kind').value = 'auto'; change($('nilm-pqs-kind')); await sleep(200);
  await api('/api/engine/stop', { method: 'POST' });

  console.log('L8 v0.46 右键「显示周波窗」+ 手动装载（仅非运行）');
  // 运行中：接口 409、按钮禁用、右键菜单项禁用
  await api('/api/engine/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: 'csv_file', path: 'data/nilm_bus_mixed.csv', file_speed: 1.0 }) });
  for (let k = 0; k < 20 && !(window.S && window.S.state && window.S.state.running); k++) await sleep(200);   // 等前端状态推送到位
  click($('btn-nilm-refresh')); await sleep(600);
  check('（前提）引擎运行中', (await api('/api/state')).running === true && window.S.state.running === true);
  const rRun = await fetch(BASE + '/api/nilm/cycles_file?n=50');
  check('运行中 GET /api/nilm/cycles_file → 409', rRun.status === 409, String(rRun.status));
  check('运行中「装载周波窗」按钮与输入禁用', $('btn-nilm-win-load').disabled && $('nilm-win-t').disabled && $('nilm-win-count').disabled);
  const cvP = $('nilm-pqs');
  const rc = (cv, x) => { const r = cv.getBoundingClientRect(); cv.dispatchEvent(new window.MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX: r.left + x, clientY: r.top + 60 })); };
  rc(cvP, 300); await sleep(200);
  let menu = document.getElementById('ctxmenu');
  check('运行中右键：菜单出现、「显示周波窗」项禁用', !!menu && !!menu.querySelector('.mi[data-key="show-window"].disabled'), menu ? menu.textContent.slice(0, 60) : 'no menu');
  window.closeCtxMenu();
  await api('/api/engine/stop', { method: 'POST' }); await sleep(1500); click($('btn-nilm-refresh')); await sleep(800);
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source: { kind: 'csv_file', path: 'data/nilm_steps.csv' } }) });
  // 非运行：手动装载（留空 → 起点 300）
  check('停止后按钮可用', !$('btn-nilm-win-load').disabled && !$('nilm-win-t').disabled);
  $('nilm-win-t').value = ''; $('nilm-win-count').value = '300'; click($('btn-nilm-win-load')); await sleep(2500);
  const nlBus = window.SD ? window.SD.bus.nl : null;
  check('留空装载 → 数据起点起 300 个周波', nlBus && nlBus.winFile && nlBus.winFile.source.mode === 'begin' && nlBus.winFile.t.length === 300, nlBus && nlBus.winFile ? JSON.stringify(nlBus.winFile.source) : 'none');
  check('周波窗标题计数=300、来源说明含「数据起点起」', $('nilm-win-n').textContent === '300' && /数据起点起/.test($('nilm-win-src').textContent), $('nilm-win-src').textContent);
  // 指定时刻（事件时刻 2.0 s）+ 100 周波 → 中心
  const tUp = nlBus.winFile.t[0] + 2.0;
  $('nilm-win-t').value = String(tUp); $('nilm-win-count').value = '100'; click($('btn-nilm-win-load')); await sleep(2500);
  const wf = nlBus.winFile;
  check('指定时刻装载 → 以该时刻为中心 100 周波（第 50 个周波 ≈ 中心）', wf && wf.source.mode === 'center' && wf.t.length === 100 && Math.abs(wf.t[50] - tUp) < 0.011, wf ? JSON.stringify([wf.t.length, wf.t[50] - tUp]) : 'none');
  check('中心左右有功阶跃（1.5 MW → 2.25 MW）', wf && wf.channels.total.p[45] < 1.6e6 && wf.channels.total.p[55] > 2.1e6, wf ? JSON.stringify([wf.channels.total.p[45], wf.channels.total.p[55]]) : '');
  // 右键菜单 → 显示周波窗（非运行）
  rc(cvP, 200); await sleep(200);
  menu = document.getElementById('ctxmenu');
  const mi = menu && menu.querySelector('.mi[data-key="show-window"]');
  check('v0.47 菜单保留原生图片三项（复制/另存为/新标签页打开）且排在业务项之前', !!menu && ['copy-image', 'save-image', 'open-image'].every((k) => !!menu.querySelector(`.mi[data-key="${k}"]`)) && Array.from(menu.querySelectorAll('.mi')).findIndex((d) => d.dataset.key === 'open-image') < Array.from(menu.querySelectorAll('.mi')).findIndex((d) => d.dataset.key === 'show-window'));
  { const r0 = cvP.getBoundingClientRect(); const ev = new window.MouseEvent('contextmenu', { bubbles: true, cancelable: true, shiftKey: true, clientX: r0.left + 100, clientY: r0.top + 50 }); const before = document.getElementById('ctxmenu'); window.closeCtxMenu(); cvP.dispatchEvent(ev);
    check('v0.47 Shift+右键不拦截（defaultPrevented=false、不弹自定义菜单）→ 浏览器原生菜单', !ev.defaultPrevented && !document.getElementById('ctxmenu')); rc(cvP, 200); await sleep(200); menu = document.getElementById('ctxmenu'); void before; }
  const mi2 = menu && menu.querySelector('.mi[data-key="show-window"]'); void mi2;
  check('非运行右键：「显示周波窗（时刻）」可点', !!mi && !mi.classList.contains('disabled') && /显示周波窗（\d{4}-/.test(mi.textContent), mi ? mi.textContent.slice(0, 50) : 'none');
  if (mi) { mi.dispatchEvent(new window.Event('click', { bubbles: true })); await sleep(2500); }
  check('右键装载后周波窗为 center 模式、时刻输入框回填', nlBus.winFile && nlBus.winFile.source.mode === 'center' && /^\d{4}-\d{2}-\d{2} /.test($('nilm-win-t').value), $('nilm-win-t').value);
  click($('btn-nilm-win-live')); await sleep(300);
  check('「清除」后回到引擎周波窗', !nlBus.winFile && $('btn-nilm-win-live').disabled);
  // v0.65：趋势曲线右键「显示周波窗 2」→ 采样瞬时值曲线到单独的「周波窗 2」画布
  window.closeCtxMenu(); rc(cvP, 200); await sleep(200); menu = document.getElementById('ctxmenu');
  const mw2 = menu && menu.querySelector('.mi[data-key="show-window2"]');
  check('v0.65 趋势曲线右键菜单新增「显示周波窗 2（瞬时值）」，排在「显示周波窗」之后、原项保留', !!mw2 && !!menu.querySelector('.mi[data-key="show-window"]') && /瞬时值/.test(mw2.textContent) && !mw2.classList.contains('disabled') && Array.from(menu.querySelectorAll('.mi')).findIndex(d => d.dataset.key === 'show-window') < Array.from(menu.querySelectorAll('.mi')).findIndex(d => d.dataset.key === 'show-window2'), mw2 ? mw2.textContent.slice(0, 60) : 'none');
  check('页面有「周波窗 2（瞬时值）」画布与清除按钮', !!$('nilm-wave2') && !!$('btn-nilm-wave2-clear') && /瞬时值/.test($('nilm-wave2-sub').textContent));
  if (mw2) { mw2.dispatchEvent(new window.Event('click', { bubbles: true })); await sleep(3000); }
  const w2 = nlBus.wave2; const w2c = $('nilm-wave2').__chart;
  const nExp = w2 ? w2.source.n_cycles * 128 : -1;   // 周波数取右键时「周波窗」面板周波数框的值（随前序用例变化）
  check('周波窗 2 已装载：6 通道 × 周波数 × 128 点（周波数随「周波数」框），source.mode=center，来自本侧离线文件', !!w2 && w2.n === nExp && w2.source.n_cycles === w2.cyc_n && (w2.channels_loaded || []).length === 6 && w2.source && w2.source.mode === 'center' && /nilm_.*\.csv/.test(w2.source.path) && !!w2c && w2c.pts.length === 6 && w2c.pts[0].data.length === nExp, w2 ? `${w2.n} / ${w2.source && w2.source.mode}` : 'none');
  check('周波窗 2 是采样瞬时值（Ua 一周波内有正有负、峰值≈√2×RMS），不是逐周波计算值', (() => { if (!w2c) return false; const a = w2c.pts.find(s => /Ua/.test(s.name)).data.slice(0, 128).map(p => p[1]); const mx = Math.max(...a), mn = Math.min(...a); const rms = Math.sqrt(a.reduce((q, v) => q + v * v, 0) / a.length); return mn < 0 && mx > 0 && Math.abs(mx / rms - Math.SQRT2) < 0.1; })());
  check('周波窗 2 不影响周波窗 1（仍为引擎周波窗，未装载离线数据）', !nlBus.winFile);
  click($('btn-nilm-wave2-clear')); await sleep(300);
  check('「周波窗 2 清除」后画布回到空提示', !nlBus.wave2 && /右键「显示周波窗 2」后显示/.test($('nilm-wave2-sub').textContent));
  // v0.66：实时源（模拟器）时「显示周波窗 2」不可选
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source: { kind: 'simulator' } }) });
  await api('/api/state').then(st => { window.S.state = st; }); window.__render(); await sleep(300);
  window.closeCtxMenu(); rc(cvP, 200); await sleep(200); menu = document.getElementById('ctxmenu');
  const mw2s = menu && menu.querySelector('.mi[data-key="show-window2"]');
  check('v0.66 输入方式＝模拟器时「显示周波窗 2」灰显不可选（提示注明只能离线文件），原「显示周波窗」不受影响', !!mw2s && mw2s.classList.contains('disabled') && /离线文件/.test(mw2s.title || mw2s.textContent || '') && !!menu.querySelector('.mi[data-key="show-window"]'), mw2s ? (mw2s.title || '').slice(0, 60) : 'none');
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source: { kind: 'csv_file', path: 'data/nilm_bus_mixed.csv' } }) });
  await api('/api/state').then(st => { window.S.state = st; }); window.__render(); await sleep(200);
  window.closeCtxMenu(); rc(cvP, 200); await sleep(200); menu = document.getElementById('ctxmenu');
  check('改回离线文件后「显示周波窗 2」恢复可选', !!menu && !!menu.querySelector('.mi[data-key="show-window2"]') && !menu.querySelector('.mi[data-key="show-window2"]').classList.contains('disabled'));
  window.closeCtxMenu();

  console.log('L4 清空');
  click($('btn-nilm-clear')); await sleep(1500);
  check('清空后表格为空', ($('nilm-table').textContent || '').includes('暂无事件'));
  check('徽标隐藏', $('nav-nilm-badge').style.display === 'none');
  await api('/api/engine/stop', { method: 'POST' });

  console.log('L5 v0.50 套用 nilm_tune 结果');
  check('表单含 nilm-tune-file / btn-nilm-tune-apply / nilm-tune-persist / nilm-tune-note', ['nilm-tune-file', 'btn-nilm-tune-apply', 'nilm-tune-persist', 'nilm-tune-note'].every(id => !!$(id)));
  check('分路侧也有同名 -br 控件', !!document.getElementById('btn-nilm-tune-apply-br') && !!document.getElementById('nilm-tune-file-br'));
  const tuneJson = { suggest: { quantity: 'p', rel_tol_pct: 1.5, min_delta_pct: 3, algorithms: { glr: { threshold: 37 }, cusum: { drift_w: 11 } } } };
  const fileObj = new window.File([JSON.stringify(tuneJson)], 'tune.json', { type: 'application/json' });
  Object.defineProperty($('nilm-tune-file'), 'files', { value: [fileObj], configurable: true });
  if (typeof fileObj.text !== 'function') fileObj.text = async () => JSON.stringify(tuneJson);
  click($('btn-nilm-tune-apply')); await sleep(1500);
  const note5 = $('nilm-tune-note').textContent || '';
  check('提示含「已套用 … 项」且「配置文件未改动」', /已套用 \d+ 项/.test(note5) && note5.includes('配置文件未改动'), note5);
  check('表单 glr.threshold 回填 37、cusum.drift_w 回填 11、rel_tol_pct 1.5', +$('nilm-glr-threshold').value === 37 && +$('nilm-cusum-drift_w').value === 11 && +$('nilm-rel_tol_pct').value === 1.5,
        `${$('nilm-glr-threshold').value}/${$('nilm-cusum-drift_w').value}/${$('nilm-rel_tol_pct').value}`);
  const cfg5 = await api('/api/config');
  check('运行配置已热更新（/api/config glr.threshold=37）', cfg5.nilm.algorithms.glr.threshold === 37);
  check('提示里给出输出目录文件名 nilm_tuned_config_bus_', /nilm_tuned_config_bus_\d{8}_\d{6}\.json/.test(note5), note5);
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nilm: { rel_tol_pct: 1.0, min_delta_pct: 0, algorithms: { glr: { threshold: 25 }, cusum: { drift_w: 10 } } } }) });

  console.log(`\n结果：${pass} 通过 / ${fail} 失败${fail ? '：' + fails.join('；') : ''}`);
  window.close();
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
