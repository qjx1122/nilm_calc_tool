#!/usr/bin/env node
/* 第 213 轮：波形预览右键周波曲线。必须对临时服务运行；本脚本只发 GET，生成合成文件于系统临时目录。
 * JSDOM_DIR=<jsdom 所在目录> node tools/ui_r213_check.cjs http://127.0.0.1:8766 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const { JSDOM } = require(path.join(process.env.JSDOM_DIR || ROOT, 'node_modules/jsdom'));
const BASE = process.argv[2] || 'http://127.0.0.1:8000';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const KEY = 'elec_tool.wave_board.v1';

let pass = 0, fail = 0;
const fails = [];
/* ok、detail 传函数，在这里求值：页面没读到数据时表达式里会取不到属性，这种异常记为这一项失败，脚本接着往下检查 */
function check(name, ok, detail = '') {
  let good = false, text = '';
  try { good = !!(typeof ok === 'function' ? ok() : ok); } catch (e) { text = `检查时出错：${e.message}`; }
  try { const d = typeof detail === 'function' ? detail() : detail; if (d) text = text ? `${text}；${d}` : String(d); } catch (e) { if (!text) text = `取不到详情：${e.message}`; }
  if (good) { pass++; console.log(`  ✓ ${name}${text ? '　' + text : ''}`); }
  else { fail++; fails.push(name); console.log(`  ✗ ${name}　${text}`); }
}
/* 一段检查：段内两项检查之间的操作如果抛异常（比如要点的按钮不存在），这一段记一项失败，后面的段照常进行 */
async function section(label, body) {
  console.log('— ' + label);
  try { await body(); }
  catch (e) {
    fail++; fails.push(`${label}：这一段中途出错`);
    console.log(`  ✗ 「${label}」中途出错，这一段后面的项没有检查：${e && e.stack ? e.stack.split('\n').slice(0, 3).join(' | ') : e}`);
  }
}
const near = (v, want, rel = 0.02) => typeof v === 'number' && Math.abs(v - want) <= Math.abs(want) * rel;
const allNear = (arr, want, rel = 0.02) => Array.isArray(arr) && arr.length > 0 && arr.every((v) => near(v, want, rel));

/* 三相录波文件：50 Hz 正弦，电压有效值 57.735 V；电流滞后 0.3 rad，前 3 秒有效值 5 A，3 秒起 10 A。列名与工具的离线文件格式一致 */
const WAVE_T0 = 1700000000, WAVE_SECONDS = 6, WAVE_STEP_AT = 3, U_RMS = 81.65 / Math.SQRT2, I_RMS = 7.07 / Math.SQRT2, PHI = 0.3;
function writeWaveCsv(file, fsHz = 6400) {
  const n = Math.round(WAVE_SECONDS * fsHz), lines = ['时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流'];
  for (let k = 0; k < n; k++) {
    const t = k / fsHz, w = 2 * Math.PI * 50 * t, amp = t >= WAVE_STEP_AT ? 14.14 : 7.07, row = [(WAVE_T0 + t).toFixed(6)];
    for (const ph of [0, -2.0943951, 2.0943951]) row.push((81.65 * Math.sin(w + ph)).toFixed(4), (amp * Math.sin(w + ph - PHI)).toFixed(5));
    lines.push(row.join(','));
  }
  fs.writeFileSync(file, lines.join('\n') + '\n', 'utf8');
}

/* 按实时落盘的格式手写一份电压曲线文件：总线侧两次运行（A：20 个点，B：30 个点，数据时间重叠），分路侧一次运行（10 个点） */
const MON_T0 = 1700000000, RUN_A = 1790000100111, RUN_B = 1790000200222, RUN_C = 1790000150333;
const MON_HEAD = 't_epoch_s,time_local,source_id,window_s,Ua,Ub,Uc,Uab,Ubc,Uca,unbalance_pct,U1,run_id';
const monRow = (k, sid, base, run) => `${MON_T0 + k}.0,2026-09-21 00:00:00.000,${sid},1.0,${base + k},${base + 100 + k},${base + 200 + k},1,2,3,0.1,,${run}`;
function writeMonitorCsv(file) {
  const rows = [];
  for (let k = 0; k < 5; k++) rows.push(monRow(k, 0, 100, RUN_A));
  for (let k = 0; k < 5; k++) rows.push(monRow(k, 1, 500, RUN_C));
  for (let k = 0; k < 5; k++) rows.push(monRow(k, 0, 110, RUN_B));
  fs.writeFileSync(file, '\ufeff' + MON_HEAD + '\r\n' + rows.join('\r\n') + '\r\n', 'utf8');
}

const real = async (p, method = 'GET', body) => {
  const r = await fetch(BASE + p, { method, headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined });
  return r.json();
};

/* 打开一个页面（相当于浏览器里打开或刷新一次）：seed＝事先放进浏览器本地存储的内容 */
async function boot(seed) {
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const calls = [], errors = [], confirms = [];
  const dom = new JSDOM(html, {
    url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true,
    beforeParse(window) {
      window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, {
        get: (t, p) => (p === 'measureText' ? () => ({ width: 8 }) : p === 'createLinearGradient' ? () => ({ addColorStop() {} }) : () => {}),
        set: () => true,
      });
      window.WebSocket = class { constructor() { this.readyState = 0; } close() {} send() {} };
      window.fetch = async (url, opts = {}) => {
        const u = String(url), method = String(opts.method || 'GET').toUpperCase();
        calls.push({ url: u, method });
        return fetch(u.startsWith('http') ? u : BASE + u, opts);
      };
      window.alert = () => {};
      window.confirm = (msg) => { confirms.push(String(msg || '')); return true; };
      window.addEventListener('error', (e) => errors.push(String(e.message)));
      if (seed !== undefined && seed !== null) window.localStorage.setItem(KEY, seed);
    },
  });
  const { window } = dom, { document } = window;
  window.eval(js + '\n;window.__labels = ASSISTANT_VIEW_LABELS; window.__S = S;');
  // app.js 末尾注册了 DOMContentLoaded → init，而 jsdom 在构造函数返回之后才派发这个事件：先去掉那个监听，只调一次 init
  document.removeEventListener('DOMContentLoaded', window.init);
  window.init();
  await sleep(1200);
  const click = (el) => el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const set = (el, v) => { el.value = String(v); change(el); };
  const idle = async (maxMs = 30000) => {                 // 等所有模块的读取都结束
    const t0 = Date.now();
    await sleep(60);
    while (Date.now() - t0 < maxMs) {
      const busy = Object.values(window.WB.rt).some((rt) => rt.queued || rt.loading);
      if (!busy) { await sleep(60); if (!Object.values(window.WB.rt).some((rt) => rt.queued || rt.loading)) return true; }
      await sleep(40);
    }
    return false;
  };
  const mods = () => Array.from(document.querySelectorAll('#wb-modules .wb-module'));
  const field = (el, name) => el.querySelector(`[data-wb-f="${name}"]`);
  const act = (el, name) => el.querySelector(`[data-wb-act="${name}"]`);
  const status = (el) => el.querySelector('.wb-status').textContent.trim();
  const lastToast = () => { const t = document.querySelectorAll('#toast .toast'); return t.length ? t[t.length - 1].textContent : ''; };
  const curveCalls = () => calls.filter((c) => c.url.includes('/api/process/wave/rms') || c.url.includes('/api/process/monitor/curve'));
  const openBoard = async () => {
    click(document.querySelector('.navitem[data-view="process"]')); await sleep(500);
    click(document.querySelector('#sub-nav-process .sub-navitem[data-subview="wave-board"]')); await sleep(500);
    await idle();
  };
  return { window, document, calls, errors, confirms, click, change, set, idle, mods, field, act, status, lastToast, curveCalls, openBoard };
}

async function main() {
 const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'ui_r213_'));
 const wave = path.join(temp, 'wave.csv'), mon = path.join(temp, 'voltage_20260921.csv');
 writeWaveCsv(wave); writeMonitorCsv(mon);
 const p = await boot(null); const {window, document, click, set, idle, mods, field, act} = p;
 const detail = (e) => window.WB.rt[e.dataset.wbId].detail;
 const dcv = (e) => document.getElementById('wb-detail-' + e.dataset.wbId);
 const checkBoardHelp = (el) => [...el.querySelectorAll('.zoombar')].every(bar => { const tip = bar.querySelector('.zoomtip').textContent, zoom = window.ZOOM[bar.dataset.chart]; return bar.querySelector('.panlbl')?.textContent === '移动：' && !/拖选|缩放|复位/.test(tip) && (zoom ? /拖动图面.*移动坐标轴/.test(tip) : tip === '') && [...bar.querySelectorAll('.pan-btn')].length === 4 && [...bar.querySelectorAll('.pan-btn')].every(btn => /移动/.test(btn.getAttribute('title') || '') && /平移/.test(btn.getAttribute('aria-label') || '')); });
 const ctx = (cv, shift = false, frac = 0.5) => {
   const c = cv.__chart; cv.getBoundingClientRect = () => ({left: 0, top: 0, width: c.w, height: c.h});
   const ev = new window.MouseEvent('contextmenu', {bubbles: true, cancelable: true, button: 2, clientX: c.pad.l + (c.w - c.pad.l - c.pad.r)*frac, clientY: 100, shiftKey: shift});
   cv.dispatchEvent(ev); return ev;
 };
 const choose = async (key) => { const item = document.querySelector('#ctxmenu [data-key="'+key+'"]'); if (!item) throw Error('missing menu '+key); click(item); await window.WB.chain; await sleep(80); };
 try {
  await p.openBoard();
  click(document.getElementById('btn-wb-add-offline')); click(document.getElementById('btn-wb-add-monitor'));
  const [off, monel] = mods();
  set(field(off, 'off-path'), wave); set(field(off, 'off-pt'), '2'); set(field(off, 'off-ct'), '3');
  click(act(off, 'load')); await idle();
  let cv = document.getElementById('wb-cv-'+off.dataset.wbId+'-u');
  const voltageCv = cv;
  Object.defineProperty(cv, 'clientWidth', {configurable:true, get() {return this.closest('.wb-chart-row').classList.contains('wb-paired') ? 360 : 720;}});
  window.wbDraw(window.WB.modules.find(m => m.id === off.dataset.wbId));
  check('离线模块加载主曲线', () => cv.__chart && cv.__chart.pts.length === 3);
  check('电压及电流主图保留移动标签和悬停说明，移除拖选和缩放说明', () => checkBoardHelp(off));
  let event = ctx(cv); let items = [...document.querySelectorAll('#ctxmenu .mi')].map(x => x.dataset.key);
  check('右键保留图片菜单和复位并增加两项', () => ['copy-image','save-image','open-image','show-window','show-window2','zoom-reset'].every(k=>items.includes(k)), () => items.join(','));
  await choose('show-window2');
  check('瞬时采样：50 周波、原始采样、所选电压、PT 生效', () => detail(off) && detail(off).kind === 'wave' && detail(off).data.n >= 6399 && detail(off).data.n <= 6401 && Object.keys(detail(off).data.channels).join(',') === 'Ua,Ub,Uc' && Math.max(...detail(off).data.channels.Ua) > 160);
  check('瞬时曲线实际已绘制且位于该模块内', () => dcv(off).__chart && dcv(off).__chart.pts.length === 3 && off.contains(dcv(off)));
  check('瞬时图与被右键的电压主图属于同一并排容器，主图宽度重新计算', () => { const row = cv.closest('.wb-chart-row'); return row.classList.contains('wb-paired') && row.querySelector('.wb-detail') === off.querySelector('.wb-detail') && cv.__chart.w === 360; });
  check('瞬时图与双主图模式的电压画布等高、标题共用样式且无说明文字', () => cv.__chart.h === 210 && dcv(off).__chart.h === cv.__chart.h && off.querySelector('.wb-detail-title').classList.contains('wb-chart-title') && !off.querySelector('.wb-detail-status').textContent);
  check('瞬时图与主图保留移动标签，移除拖选和缩放说明', () => checkBoardHelp(off));
  const mainLegend = off.querySelector('[data-wb-chart="u"] .serlegend'), detailLegend = off.querySelector('.wb-detail .serlegend');
  check('两图各有显示和缩放移动控件', () => mainLegend.querySelector('.ser-vis') && detailLegend.querySelector('.ser-vis') && mainLegend.querySelector('[data-z="x-"]') && detailLegend.querySelector('[data-z="pr"]'));
  click(mainLegend.querySelector('[data-z="x-"]')); const mainZoom = JSON.stringify(window.ZOOM[cv.id]);
  check('主图缩放不影响周波图', () => !!window.ZOOM[cv.id].x && !window.ZOOM[dcv(off).id]);
  check('主图放大后显示移动说明，无拖选和缩放说明', () => { const tip = mainLegend.querySelector('.zoomtip').textContent; return /拖动图面.*移动坐标轴/.test(tip) && !/拖选|缩放|复位/.test(tip) && mainLegend.querySelector('[data-z=pr]') && !mainLegend.querySelector('[data-z=pr]').disabled; });
  check('主图放大后保留移动说明、悬停说明和方向无障碍名称', () => checkBoardHelp(off));
  click(detailLegend.querySelector('[data-z="x-"]')); const beforePan = window.ZOOM[dcv(off).id].x[0]; click(detailLegend.querySelector('[data-z="pr"]'));
  check('周波图独立缩放移动不影响主图', () => window.ZOOM[dcv(off).id].x[0] > beforePan && JSON.stringify(window.ZOOM[cv.id]) === mainZoom);
  [cv, dcv(off)].forEach(c => { c.getBoundingClientRect = () => ({left:0, top:0, width:c.__chart.w, height:c.__chart.h}); c.dispatchEvent(new window.MouseEvent('mousemove', {bubbles:true, clientX:120, clientY:80})); });
  check('主图和周波图悬停取值保持可用', () => cv.__hoverInfo?.items.length === 3 && dcv(off).__hoverInfo?.items.length === 3);
  check('周波图放大后显示移动说明但没有拖选和缩放说明', () => {const tip = detailLegend.querySelector('.zoomtip').textContent; return /拖动图面.*移动坐标轴/.test(tip) && !/拖选|缩放|复位/.test(tip);});
  const other = document.createElement('canvas'); other.id='r217-other'; document.body.appendChild(other); window.drawLine(other,[{name:'test', data:[[0,1],[1,2]]}],{height:200}); click(other.__zoombar.querySelector('[data-z="x-"]'));
  check('其他曲线仍显示原移动说明与按钮悬停提示', () => /拖动图面.*移动坐标轴/.test(other.__zoombar.querySelector('.zoomtip').textContent) && other.__zoombar.querySelector('.panlbl') && /向右移动/.test(other.__zoombar.querySelector('[data-z=pr]').title)); other.remove();
  click(detailLegend.querySelector('[data-z="reset"]')); click(mainLegend.querySelector('[data-z="reset"]'));
  check('两图复位各自有效', () => !window.ZOOM[cv.id] && !window.ZOOM[dcv(off).id]);
  const toggle = off.querySelector('.wb-detail .ser-vis[data-name=Ua]'); toggle.checked = false; toggle.dispatchEvent(new window.Event('change', {bubbles:true})); await sleep(50);
  check('周波图图例切换保存在模块且不写运行配置', () => dcv(off).__chart.pts.length === 2 && JSON.parse(window.localStorage.getItem(KEY)).modules[0].hidden.detail.includes('Ua') && !p.calls.some(c=>c.method!=='GET'));
  check('周波图显示开关不影响主图', () => cv.__chart.pts.length === 3);
  ctx(cv); await choose('show-window');
  check('逐周波有效值：每周波一点且 PT 生效', () => detail(off).kind === 'rms' && detail(off).data.agg_cycles === 1 && detail(off).data.n >= 49 && detail(off).data.n <= 50 && Math.abs(detail(off).data.channels.Ua[0]-2*U_RMS) < 1);
  check('有效值周波图保留移动标签和悬停说明', () => checkBoardHelp(off));
  cv = document.getElementById('wb-cv-'+off.dataset.wbId+'-i'); ctx(cv); await choose('show-window');
  check('电流图右键只显示电流且 CT 生效', () => Object.keys(detail(off).data.channels).join(',') === 'Ia,Ib,Ic' && Math.abs(detail(off).data.channels.Ia[0]-3*I_RMS) < 1);
  check('有效值图随所选电流主图同一行，电压行不再配对', () => cv.closest('.wb-chart-row').classList.contains('wb-paired') && cv.closest('.wb-chart-row').contains(dcv(off)) && !off.querySelector('[data-wb-row="u"]').classList.contains('wb-paired'));
  check('周波图移到电流后，原电压主图按恢复的宽度重画', () => voltageCv.__chart.w === 720);
  set(field(off,'off-show'),'both'); cv = document.getElementById('wb-cv-'+off.dataset.wbId+'-i');
  check('主图重建后若所选图仍存在则保持并排及周波数据', () => cv.closest('.wb-chart-row').classList.contains('wb-paired') && cv.closest('.wb-chart-row').contains(dcv(off)) && detail(off).kind === 'rms');
  set(field(off,'off-show'),'i'); cv = document.getElementById('wb-cv-'+off.dataset.wbId+'-i');
  check('单主图模式变为 280 高时周波画布同步等高', () => cv.__chart.h === 280 && dcv(off).__chart.h === 280);
  set(field(off,'off-show'),'both'); cv = document.getElementById('wb-cv-'+off.dataset.wbId+'-i');
  check('切回双主图后周波画布恢复 210 高', () => cv.__chart.h === 210 && dcv(off).__chart.h === 210);
  set(field(off,'off-show'),'u');
  check('切换后所选主图不可见时关闭其周波图', () => off.querySelector('.wb-detail').hidden && !detail(off));
  set(field(off,'off-show'),'both'); cv = document.getElementById('wb-cv-'+off.dataset.wbId+'-i'); ctx(cv); await choose('show-window');
  set(field(off,'detail-cycles'),'0'); ctx(cv); await choose('show-window');
  check('非法周波数不启动请求', () => !detail(off)); set(field(off,'detail-cycles'),'20');
  set(field(off,'off-path'), path.join(temp,'not-loaded.csv')); ctx(cv); await choose('show-window');
  check('表单尚未重新加载时使用主图实际文件', () => detail(off) && detail(off).source === wave);
  set(field(off,'off-path'), wave);
  ctx(cv, false, 0); await choose('show-window');
  check('文件开头边界平移后仍可读取', () => detail(off) && detail(off).data.n >= 19 && detail(off).data.t[0] >= WAVE_T0);
  Object.defineProperty(cv, 'clientWidth', {configurable:true, get() {return this.closest('.wb-chart-row').classList.contains('wb-paired') ? 360 : 720;}});
  window.wbDraw(window.WB.modules.find(m => m.id === off.dataset.wbId));
  click(act(off,'detail-close')); check('关闭周波曲线后主图恢复宽度并重画', () => off.querySelector('.wb-detail').hidden && cv.__chart.w === 720 && !dcv(off));
  event=ctx(cv,true); check('Shift 右键保留浏览器原生菜单', () => !event.defaultPrevented);
  set(field(monel,'mon-path'),mon); await idle();
  const mc=document.getElementById('wb-cv-'+monel.dataset.wbId+'-m'); ctx(mc);
  check('监测文件没配原始 CSV 时两项均禁用并提示', () => ['show-window','show-window2'].every(k=>{let x=document.querySelector('#ctxmenu [data-key="'+k+'"]'); return x && x.classList.contains('disabled') && /原始波形/.test(x.textContent)}));
  set(field(monel,'mon-raw-path'),wave); set(field(monel,'mon-raw-pt'),'4'); set(field(monel,'detail-cycles'),'10');
  ctx(mc); await choose('show-window');
  check('监测模块从指定原始 CSV 读取，按选定时刻及独立 PT 显示', () => detail(monel) && detail(monel).data.n >= 9 && detail(monel).data.n <= 10 && Math.abs(detail(monel).data.channels.Ua[0]-4*U_RMS)<1 && !monel.querySelector('.wb-detail-status').textContent && mc.__chart.h === 280 && dcv(monel).__chart.h === 280);
  check('监测曲线与周波图同一行且其他模块不受影响', () => !detail(off) && detail(monel) && mc.closest('.wb-chart-row').classList.contains('wb-paired') && mc.closest('.wb-chart-row').contains(dcv(monel)));
  click(monel.querySelector('[data-wb-chart="m"] [data-z="x-"]'));
  check('监测主图与周波图保留移动标签和悬停说明', () => checkBoardHelp(monel));
  click(monel.querySelector('[data-wb-chart="m"] [data-z="reset"]'));
  set(document.getElementById('wb-layout'), '2');
  check('更改模块排列后仍保持同一行并排', () => mc.closest('.wb-chart-row').classList.contains('wb-paired') && mc.closest('.wb-chart-row').contains(dcv(monel)));
  set(document.getElementById('wb-layout'), '1');
  const requests=p.calls.filter(c=>c.url.includes('/api/process/wave/'));
  check('请求携带原始路径、周波窗口和口径', () => requests.some(c=>c.url.includes('/rms?') && c.url.includes('agg_cycles=1') && c.url.includes('pt_ratio=4') && decodeURIComponent(c.url).includes(wave)));
  const saved=JSON.parse(window.localStorage.getItem(KEY));
  check('原始文件及周波数保存在模块本地配置', () => saved.modules.find(x=>x.id===monel.dataset.wbId).monitor.raw_path===wave && saved.modules.find(x=>x.id===monel.dataset.wbId).detail.cycles==='10');
  set(field(monel,'detail-cycles'),'1001'); ctx(mc); await choose('show-window2');
  check('周波数上限生效', () => !detail(monel));
  set(field(monel,'detail-cycles'),'10');
  set(field(monel,'mon-raw-path'),path.join(temp,'missing.csv')); ctx(mc); await choose('show-window2');
  check('错误文件有明确失败提示，错误在画布之后且两图仍同高', () => /读取失败/.test(monel.querySelector('.wb-detail-status').textContent) && monel.querySelector('.wb-detail-chart').nextElementSibling === monel.querySelector('.wb-detail-status') && dcv(monel).style.height === mc.style.height);
  set(field(monel,'mon-raw-path'),wave);
  const savedChart = mc.__chart; mc.__chart = Object.assign({}, savedChart, {opt: Object.assign({}, savedChart.opt, {tbase: WAVE_T0 + 100})}); ctx(mc); await choose('show-window'); mc.__chart = savedChart;
  check('监测时刻超出原始文件范围时拒绝读取而不是错配', () => /不在原始波形文件时间范围内/.test(monel.querySelector('.wb-detail-status').textContent));
  const rawFetch=window.fetch; window.fetch=async (url,opts)=>{if(String(url).includes('/api/process/wave/info?')) await sleep(300); return rawFetch(url,opts);};
  ctx(mc); const item=document.querySelector('#ctxmenu [data-key="show-window"]'); click(item); await sleep(40);
  check('周波加载中没有说明占位并与主图等高', () => !monel.querySelector('.wb-detail-status').textContent && dcv(monel).style.height === mc.style.height);
  click(act(monel,'detail-close')); await window.WB.chain;
  check('关闭期间晚到的响应不会重新显示', () => monel.querySelector('.wb-detail').hidden && !detail(monel));
  check('无修改类请求、无脚本错误', () => !p.calls.some(c=>c.method!=='GET') && p.errors.length===0, () => p.errors.join(';'));
 } finally { p.window.close(); fs.rmSync(temp,{recursive:true,force:true}); }
 console.log(`PASS ${pass} FAIL ${fail}`); if(fail) process.exitCode=1;
}
main().catch(e=>{console.error(e.stack || e); process.exitCode=2;});
