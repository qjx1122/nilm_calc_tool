#!/usr/bin/env node
/* v0.24 界面检查：事件 / 负荷辨识 / 窗口配置 / 导出与日志 也合并为「左：总线侧 / 右：分路侧」；
 * 负荷辨识页新增 P/Q/S 趋势（同总览）+ 各算法事件竖线 + 「标注算法」多选（默认全部）。
 * 需先 serve 在 8000；数据：data/sample_6400hz.csv（总线）、data/nilm_steps.csv（分路，含启停事件）。
 *
 *   E1 结构：4 个 section 也是 .dual；右列 id 全带 -br；右列下载链接指向 /api/branch/…；导航无分路侧专属项、徽标 badge-br 存在
 *   E2 未启用分路侧：4 页 .dual 均 no-branch
 *   E3 两侧播放（总线 sample / 分路 nilm_steps）：
 *        事件页：左右两列卡片/表格各自有内容，右列摘要来自 /api/branch/events
 *        负荷辨识页：右列事件表有分路侧事件（nilm_steps 有启停），左列无或不同；右列 P/Q/S 画布存在、标注算法 6 个全勾选、图内标注数 > 0；
 *                   取消勾选所有算法 → 图内标注数 0；只勾一个 → 标注数 = 该算法事件数
 *        窗口页：右列表格行来自分路侧配置；点右列「保存窗口配置」→ PUT /api/branch/config 且不碰 /api/config
 *        导出页：右列运行状态 JSON 是分路侧（source_path 含 nilm_steps）；右列「保存曲线数据」→ POST /api/branch/curves/save
 *   E4 右列事件阈值保存 → PUT /api/branch/config {events}；左列保存 → PUT /api/config
 *
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r24_check.cjs [baseUrl]
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

function makeDom(calls) {
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
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
  const { window } = dom;
  window.eval(js + '\n;window.__S = () => S; window.__render = render; window.__renderTop = renderTop; window.__BRD = BRD; window.__refreshBranchDual = refreshBranchDual;');
  return dom;
}

const VIEWS = ['events', 'nilm', 'windows', 'export'];

async function main() {
  const api = async (u, o) => (await fetch(BASE + u, o)).json();
  const post = (u, body) => api(u, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
  const put = (u, body) => api(u, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  await post('/api/engine/stop'); await post('/api/branch/engine/stop');
  await put('/api/config', { branch: { enabled: false, common_window: false, common_start: '' } });
  await post('/api/branch/nilm/clear'); await post('/api/nilm/clear');

  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  const calls = [];
  const dom = makeDom(calls);
  const { window } = dom, { document } = window;
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(900); };
  const sync = async () => { window.__S().state = await api('/api/state'); const r = await fetch(BASE + '/api/result?full=true'); window.__S().result = r.ok ? await r.json() : null; window.__renderTop(); await window.__render(); };
  const brSync = async () => { window.__BRD.at = 0; window.__BRD.evAt = 0; window.__BRD.nlAt = 0; await window.__refreshBranchDual(true); await sleep(1200); await window.__render(); };

  console.log('E1 结构');
  check('导航无分路侧专属项；事件/负荷辨识项带分路侧徽标 badge-br', (html.match(/navitem" data-view="\w+" data-side="branch"/g) || []).length === 0 && !!$('nav-ev-badge-br') && $('nav-ev-badge-br').classList.contains('badge-br') && !!$('nav-nilm-badge-br'));
  check('4 个 section 都有 .dual > .dual-bus + .dual-br', VIEWS.every(v => $(`view-${v}`).querySelector('.dual > .dual-bus') && $(`view-${v}`).querySelector('.dual > .dual-br')));
  check('右列所有 id 以 -br 结尾、左列不含 -br', VIEWS.every(v => {
    const br = Array.from($(`view-${v}`).querySelectorAll('.dual-br [id]')), bus = Array.from($(`view-${v}`).querySelectorAll('.dual-bus [id]'));
    return br.length > 0 && br.every(e => e.id.endsWith('-br')) && bus.every(e => !e.id.endsWith('-br'));
  }));
  check('导出页右列下载链接指向 /api/branch/…、左列仍 /api/…', Array.from($('view-export').querySelectorAll('.dual-br a[href]')).every(a => a.getAttribute('href').startsWith('/api/branch/')) &&
    Array.from($('view-export').querySelectorAll('.dual-bus a[href]')).every(a => a.getAttribute('href').startsWith('/api/') && !a.getAttribute('href').startsWith('/api/branch/')));
  check('负荷辨识页：两列都有 P/Q/S 画布与 6 个「标注算法」勾选（默认全选）', !!$('nilm-pqs') && !!$('nilm-pqs-br') &&
    $('nilm-pqs-algos').querySelectorAll('.nilm-pqs-algo').length === 6 && $('nilm-pqs-algos-br').querySelectorAll('.nilm-pqs-algo').length === 6 &&
    Array.from(document.querySelectorAll('.nilm-pqs-algo')).every(c => c.checked));
  check('v0.26.1：算法卡片标题＝勾选框紧挨色块与算法名，说明另起一行（两列各 6 个）', ['nilm-algos', 'nilm-algos-br'].every(id => {
    const cards = Array.from($(id).querySelectorAll('.nilm-algo'));
    return cards.length === 6 && cards.every(c => { const lab = c.querySelector('h3.algohdr label.check'); const inp = lab && lab.querySelector('input[type=checkbox]');
      return inp && inp.nextElementSibling && inp.nextElementSibling.classList.contains('sw') && lab.textContent.trim().length > 0 && c.querySelector('.algodesc') && !lab.contains(c.querySelector('.algodesc')); });
  }));
  check('导航三组标题无说明后缀', (() => { const t = Array.from(document.querySelectorAll('.navgroup')).map(g => Array.from(g.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim());   /* 只看文字节点，排除状态徽标 */ return t.includes('实时监测') && t.includes('事件与分析') && t.includes('工具'); })(), Array.from(document.querySelectorAll('.navgroup')).map(g => g.textContent.trim()).join(' | '));
  check('负荷辨识页：两列都有 6 组算法参数表单（右列 id 带 -br）', $('nilm-algos').querySelectorAll('input[id$="-enabled"]').length === 6 && $('nilm-algos-br').querySelectorAll('input[id$="-enabled-br"]').length === 6);

  console.log('E2 未启用分路侧');
  for (const v of VIEWS) { await nav(v); await sync(); check(`${v}：.dual 带 no-branch`, $(`view-${v}`).querySelector('.dual').classList.contains('no-branch')); }
  check('body.no-branch-nav（分路侧徽标隐藏规则）', document.body.classList.contains('no-branch-nav') && /body\.no-branch-nav \.badge-br[^{]*\{[^}]*display:\s*none/.test(fs.readFileSync(path.join(ROOT, 'app/static/style.css'), 'utf8')));

  // 启动两侧：总线 sample、分路 nilm_steps
  await put('/api/config', { branch: { enabled: true, common_window: false } });
  await put('/api/branch/config', { source: { kind: 'csv_file', path: 'data/nilm_steps.csv', file_speed: 1, custom_time: false } });
  const st = await post('/api/engine/start', { kind: 'csv_file', path: 'data/sample_6400hz.csv', file_speed: 1, custom_time: false });
  check('两侧启动成功', st.ok && st.branch && st.branch.ok, JSON.stringify(st.branch || {}).slice(0, 100));
  await sleep(7000);   // nilm_steps 6 s，让事件都出来

  console.log('E3 两侧播放');
  // --- 事件页
  await nav('events'); await sync(); await brSync();
  check('事件页：.dual 显示右列', !$('view-events').querySelector('.dual').classList.contains('no-branch'));
  const evBr = await api('/api/branch/events?limit=10');
  check('事件页右列卡片有内容且来自分路侧摘要', $('ev-cards-br').textContent.includes('事件检测') && $('ev-cards-br').textContent.length > 20 && window.SD.branch.evSummary && window.SD.branch.evSummary.total === evBr.summary.total, `branch total=${evBr.summary.total}`);
  check('事件页左列卡片有内容（总线侧）', $('ev-cards').textContent.includes('事件检测') && window.SD.bus.evSummary !== null);
  check('右列请求走 /api/branch/events', calls.some(c => c.url.startsWith('/api/branch/events')) && calls.some(c => /^\/api\/events/.test(c.url)));

  // --- 负荷辨识页
  await nav('nilm'); await sync(); await brSync(); await sleep(500); await window.__render();
  const nlBr = await api('/api/branch/nilm/events?limit=1000');
  const nlBus = await api('/api/nilm/events?limit=1000');
  check('分路侧（nilm_steps）有负荷事件、总线侧（sample）事件数不同', nlBr.events.length > 0 && nlBr.events.length !== nlBus.events.length, `branch=${nlBr.events.length} bus=${nlBus.events.length}`);
  check('右列事件表行数 = 分路侧事件数；左列 = 总线侧', $('nilm-table-br').querySelectorAll('tbody tr').length === nlBr.events.length && $('nilm-table').querySelectorAll('tbody tr').length === nlBus.events.length,
    `br rows=${$('nilm-table-br').querySelectorAll('tbody tr').length} bus rows=${$('nilm-table').querySelectorAll('tbody tr').length}`);
  check('右列卡片累计数 = 分路侧 summary.total', $('nilm-cards-br').textContent.includes(`累计 ${nlBr.summary.total} 条`), $('nilm-cards-br').textContent.slice(0, 60));
  check('右列 P/Q/S 趋势有分路侧 power 历史', (window.__BRD.histCache.power || []).length >= 2, `points=${(window.__BRD.histCache.power || []).length}`);
  const nAll = +$('nilm-pqs-n-br').textContent;
  const hp = window.__BRD.histCache.power, t0 = hp[0].t, t1 = hp[hp.length - 1].t;
  const inRange = nlBr.events.filter(e => e.t_start >= t0 && e.t_start <= t1).length;
  check('右列图内标注数 = 落在趋势时间范围内的全部算法事件数（默认全部）', nAll === inRange && nAll > 0, `shown=${nAll} expected=${inRange}`);
  // 只勾一个算法
  const boxes = Array.from($('nilm-pqs-algos-br').querySelectorAll('.nilm-pqs-algo'));
  const algoCounts = {}; nlBr.events.filter(e => e.t_start >= t0 && e.t_start <= t1).forEach(e => { algoCounts[e.algorithm] = (algoCounts[e.algorithm] || 0) + 1; });
  const one = Object.keys(algoCounts)[0];
  boxes.forEach(b => { b.checked = b.dataset.algo === one; }); change(boxes[0]); await sleep(300);
  check(`右列只勾「${one}」→ 标注数 = 该算法事件数`, +$('nilm-pqs-n-br').textContent === algoCounts[one], `shown=${$('nilm-pqs-n-br').textContent} expected=${algoCounts[one]}`);
  check('左列「标注算法」不受右列影响（仍全选）', Array.from($('nilm-pqs-algos').querySelectorAll('.nilm-pqs-algo')).every(c => c.checked));
  boxes.forEach(b => { b.checked = false; }); change(boxes[0]); await sleep(300);
  check('右列全部取消 → 标注数 0', $('nilm-pqs-n-br').textContent === '0');
  boxes.forEach(b => { b.checked = true; }); change(boxes[0]); await sleep(300);
  // 右列对象过滤
  $('nilm-pqs-ch-br').value = 'total'; change($('nilm-pqs-ch-br')); await sleep(300);
  const totalCnt = nlBr.events.filter(e => e.channel === 'total' && e.t_start >= t0 && e.t_start <= t1).length;
  check('右列对象选「三相总」→ 标注数 = total 对象事件数', +$('nilm-pqs-n-br').textContent === totalCnt, `shown=${$('nilm-pqs-n-br').textContent} expected=${totalCnt}`);
  check('右列参数表单回填分路侧配置（window_cycles 有值）', +$('nilm-window_cycles-br').value >= 30);

  // --- 窗口页
  await nav('windows'); await sync(); await brSync();
  const nWin = Object.keys((await api('/api/branch/config')).windows).length;
  check(`窗口页右列表格来自分路侧配置（${nWin} 行）`, $('w-table-br').querySelectorAll('tbody tr').length === nWin && $('w-table').querySelectorAll('tbody tr').length === nWin);
  const before = calls.length;
  const inp = $('w-table-br').querySelector('input[data-w="voltage"][data-f="length_s"]'); inp.value = '0.4';
  click($('btn-save-win-br')); await sleep(1500);
  const putBr = calls.slice(before).filter(c => c.method === 'PUT' && c.url === '/api/branch/config');
  const putBus = calls.slice(before).filter(c => c.method === 'PUT' && c.url === '/api/config');
  check('右列「保存窗口配置」→ PUT /api/branch/config（不碰 /api/config）', putBr.length === 1 && putBus.length === 0 && JSON.parse(putBr[0].body).windows.voltage.length_s === 0.4);
  const brCfg = await api('/api/branch/config');
  check('分路侧配置已更新 voltage.length_s=0.4、总线侧不变', brCfg.windows.voltage.length_s === 0.4 && (await api('/api/config')).windows.voltage.length_s !== 0.4);
  await put('/api/branch/config', { windows: { voltage: { length_s: 1, step_s: 1 } } });

  // --- 导出页
  await nav('export'); await sync(); await brSync();
  const bEng = (await api('/api/branch/state')).engine, uEng = (await api('/api/state')).engine;
  check('导出页右列运行状态 JSON 是分路侧引擎（samples_in 与 /api/branch/state 一致且 ≠ 总线侧）', JSON.parse($('ex-state-br').textContent).samples_in === bEng.samples_in && JSON.parse($('ex-state').textContent).samples_in === uEng.samples_in && bEng.samples_in !== uEng.samples_in, `br=${bEng.samples_in} bus=${uEng.samples_in}`);
  const b2 = calls.length; click($('btn-save-curves-br')); await sleep(2500);
  check('右列「保存曲线数据」→ POST /api/branch/curves/save', calls.slice(b2).some(c => c.method === 'POST' && c.url === '/api/branch/curves/save') && /已保存|✗/.test($('curves-out-br').textContent));
  check('右列实时落盘状态来自 /api/branch/realtime', calls.some(c => c.url === '/api/branch/realtime') && $('rt-out-br').textContent.includes('状态'));

  console.log('E4 事件阈值保存');
  await nav('events'); await sync(); await brSync();
  const b3 = calls.length; $('ev-hysteresis-br').value = '0.93'; click($('btn-ev-save-br')); await sleep(1200);
  const p3 = calls.slice(b3).filter(c => c.method === 'PUT');
  check('右列保存 → PUT /api/branch/config {events}', p3.length === 1 && p3[0].url === '/api/branch/config' && JSON.parse(p3[0].body).events.hysteresis === 0.93);
  const b4 = calls.length; click($('btn-ev-save')); await sleep(1200);
  const p4 = calls.slice(b4).filter(c => c.method === 'PUT');
  check('左列保存 → PUT /api/config', p4.length === 1 && p4[0].url === '/api/config');
  await put('/api/branch/config', { events: { hysteresis: 0.95 } });

  await post('/api/engine/stop'); await post('/api/branch/engine/stop');
  await put('/api/config', { branch: { enabled: false } });
  console.log(`\n结果：${pass} 通过，${fail} 失败${fail ? '：' + fails.join('；') : ''}`);
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
