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
  window.eval(js + '\n;window.__S = () => S;');
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
  $('nilm-filter').value = ''; change($('nilm-filter')); await sleep(800);
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
  check('auto + I 口径 → 趋势标题为三相电流', /三相电流 I 趋势/.test($('nilm-pqs-title').textContent));
  const cs = document.querySelector('#view-nilm .curvespan'); check('曲线跨度标签切到 current', cs && cs.dataset.curve === 'current', cs && cs.dataset.curve);
  $('nilm-pqs-kind').value = 'pqs'; change($('nilm-pqs-kind')); await sleep(300);
  check('切到 P/Q/S → 标题复原', /P \/ Q \/ S 趋势/.test($('nilm-pqs-title').textContent));
  $('nilm-pqs-kind').value = 'auto'; change($('nilm-pqs-kind')); await sleep(200);
  await api('/api/engine/stop', { method: 'POST' });

  console.log('L4 清空');
  click($('btn-nilm-clear')); await sleep(1500);
  check('清空后表格为空', ($('nilm-table').textContent || '').includes('暂无事件'));
  check('徽标隐藏', $('nav-nilm-badge').style.display === 'none');
  await api('/api/engine/stop', { method: 'POST' });
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nilm: { algorithms: { glr: { threshold: 25 } } } }) });

  console.log(`\n结果：${pass} 通过 / ${fail} 失败${fail ? '：' + fails.join('；') : ''}`);
  window.close();
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
