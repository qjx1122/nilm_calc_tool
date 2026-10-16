#!/usr/bin/env node
/* ui_r30_check.cjs —— v0.30 重启后负荷辨识上次数据加载检查（需 8000 服务在跑；用法 TZ=Asia/Shanghai JSDOM_DIR=/tmp/uitest node tools/ui_r30_check.cjs） */
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


/* v0.30：重启后负荷辨识页加载上次数据——事件表、P/Q/S 趋势事件竖线、摘要卡片；周波窗提示。
 * 前提：服务器已 autoload（本脚本不重启服务，直接在当前进程上调 /api/history/load_last 模拟重启后的加载）。 */
async function main() {
  const api = async (u, o) => (await fetch(BASE + u, o)).json();
  const post = (u, body) => api(u, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
  const put = (u, body) => api(u, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const RESTART_ONLY = !!process.env.RESTART_ONLY;      // =1：服务刚重启（autoload 已完成），跳过播放阶段只查页面
  let live = null;
  if (!RESTART_ONLY) {
  await post('/api/engine/stop'); await post('/api/branch/engine/stop');
  await put('/api/config', { branch: { enabled: false }, output: { realtime_save: true } });
  // 1) 播放 nilm_steps（数据时标 2026-10-13）直到结束 → 记录事件
  await post('/api/engine/start', { kind: 'csv_file', path: 'data/nilm_steps.csv', file_speed: 0, custom_time: false });
  for (let k = 0; k < 60; k++) { await sleep(500); const st = await api('/api/state'); if (!st.running) break; }
  live = await api('/api/nilm/events?limit=1000');
  const livePow = await api('/api/history/power');
  check('播放结束：负荷事件 > 0、power 趋势点 > 1', live.events.length > 0 && livePow.count > 1, `events=${live.events.length} power=${livePow.count}`);
  // 2) 再播放一个「数据时标更新」的文件（样例 sample_6400hz 的时标是今天）——制造目录里混有更新时标数据的情形，
  //    然后再播一次 nilm_steps，使「上次播放」是时标更旧的数据
  await post('/api/engine/start', { kind: 'csv_file', path: 'data/sample_6400hz.csv', file_speed: 0, custom_time: false });
  for (let k = 0; k < 60; k++) { await sleep(500); const st = await api('/api/state'); if (!st.running) break; }
  await post('/api/engine/start', { kind: 'csv_file', path: 'data/nilm_steps.csv', file_speed: 0, custom_time: false });
  for (let k = 0; k < 60; k++) { await sleep(500); const st = await api('/api/state'); if (!st.running) break; }
  await sleep(800);
  // 3) 模拟重启：丢弃引擎内存 → load_last
  const r = await post('/api/history/load_last', {});
  check('load_last 以 last_result 的 t_ref 为锚点（t_anchor 存在且 = 上次播放结束时刻，2026-10-13）', r.ok && typeof r.t_anchor === 'number' && /^2026-10-13/.test(r.t_anchor_local || ''), JSON.stringify([r.t_anchor_local, r.t_last_local]));
  check('重启加载：负荷事件数 = 播放时事件数', r.nilm_events === live.events.length, `${r.nilm_events} vs ${live.events.length}`);
  check('重启加载：power 曲线点都落在锚点前 24 h 内（不混入今天时标的样例数据）', (await api('/api/history/power')).points.every(p => p.t <= r.t_anchor + 1 && p.t >= r.t_anchor - 86400));
  const after = await api('/api/nilm/events?limit=1000');
  const key = (e) => `${e.algorithm}|${e.channel}|${e.t_start.toFixed(3)}|${e.direction}|${Math.round(e.magnitude_w)}`;
  const sa = new Set(after.events.map(key)), sl = new Set(live.events.map(key));
  check('重启加载：事件逐条一致（算法/对象/起点/方向/幅值）', sa.size === sl.size && [...sl].every(k => sa.has(k)), `${sa.size}/${sl.size}`);
  check('重启加载：事件带本地时间与算法名、摘要计数一致', after.events.every(e => e.t_start_local && e.algorithm_name) && after.summary.total === live.events.length);
  }
  const after = await api('/api/nilm/events?limit=1000');
  const cyc = await api('/api/nilm/cycles?n=2000');
  if (RESTART_ONLY) check('真实重启后：autoload 已加载负荷事件 > 0、周波窗为空', after.events.length > 0 && !(cyc.t || []).length, `events=${after.events.length} cycles=${(cyc.t || []).length}`);

  // 4) 前端：负荷辨识页
  const calls = [];
  const dom = makeDom(calls);
  const { window } = dom, { document } = window;
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(900); };
  const sync = async () => { window.__S().state = await api('/api/state'); const rr = await fetch(BASE + '/api/result?full=true'); window.__S().result = rr.ok ? await rr.json() : null; window.__renderTop(); await window.__render(); };
  await nav('nilm'); await sync(); await sleep(1500); await window.__render(); await sleep(300);
  check('负荷辨识页事件表行数 = 加载的事件数', $('nilm-table').querySelectorAll('tbody tr').length === after.events.length && $('nilm-total').textContent === String(after.events.length), `${$('nilm-table').querySelectorAll('tbody tr').length}`);
  const pq = $('nilm-pqs').__chart;
  check('P/Q/S 趋势已绘制（上次播放的 power 曲线）', !!pq && pq.pts.some(s => s.data.length > 1));
  const nMarks = +$('nilm-pqs-n').textContent;
  const inRange = after.events.filter(e => e.t_start >= pq.xfull[0] + pq.opt.tbase && e.t_start <= pq.xfull[1] + pq.opt.tbase).length;
  check('P/Q/S 趋势上的事件竖线数 = 落在曲线时间范围内的事件数（> 0）', nMarks > 0 && nMarks === inRange && pq.opt.marks.length === nMarks, `marks=${nMarks} inRange=${inRange} total=${after.events.length}`);
  check('负荷辨识摘要卡片累计 = 事件数', new RegExp(`累计 ${after.events.length} 条`).test($('nilm-cards').textContent), $('nilm-cards').textContent.slice(0, 80));
  if ((cyc.t || []).length) check('同进程 load_last：周波窗仍在内存 → 不显示「重启后不恢复」提示', !/重启后不恢复/.test($('nilm-notes').textContent) && $('nilm-win-n').textContent === String(cyc.t.length));
  else check('真实重启后：周波窗为空 → 说明区与空图给出「周波窗是内存数据，重启后不恢复」提示', /重启后不恢复/.test($('nilm-notes').textContent), $('nilm-notes').textContent.slice(0, 120));
  console.log(`\n结果：${pass} 通过，${fail} 失败${fail ? '：' + fails.join('；') : ''}`);
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
