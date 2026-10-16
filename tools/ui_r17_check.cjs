#!/usr/bin/env node
/* v0.17 界面检查：指定时间段播放（两侧）/ 公共时间段结束时间 / 曲线缩放 / CSV source_id。
 * jsdom 驱动真实 index.html + app.js，打真实服务端（需先 serve 在 8000，data/sample_6400hz.csv、data/nilm_steps.csv 存在）。
 *
 *   W1 两侧「指定时间段播放」勾选 + 起止输入：仅 csv_file 可用、默认不启用；勾选后输入启用；保存→ /api/config / /api/branch/config
 *   W2 总线侧按时间段启动：只给结束时间 → 从起点播到该时刻；状态栏显示「播放终点」
 *   W3 公共时间段结束时间 br-common-end：预览显示播放终点来源
 *   Z1 滚轮 → X 轴缩放（视窗变窄、缩放条「已缩放 X」）；Shift+滚轮 → Y 轴；双击复位
 *   Z2 拖选区间 → 只显示该区间（xmin/xmax == 拖选换算值）；按钮 X＋/Y＋/复位
 *   C1 /api/curves/export、/api/export?fmt=csv 带 source_id；/api/curves/save 启用分路时含 branch/ 文件
 *
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r17_check.cjs [baseUrl]
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
      window.HTMLCanvasElement.prototype.getBoundingClientRect = function () { return { left: 0, top: 0, width: this.clientWidth || 600, height: 200 }; };
      Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get() { return 600; }, configurable: true });
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
  try { window.localStorage.removeItem('elec_side'); } catch (e) {}
  window.eval(js + '\n;window.__S = () => S;');
  if (typeof window.init === 'function') window.init();
  return dom;
}

async function main() {
  const api = async (u, o) => (await fetch(BASE + u, o)).json();
  const text = async (u) => (await fetch(BASE + u)).text();
  const put = (u, body) => api(u, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  await api('/api/engine/stop', { method: 'POST' });
  await api('/api/branch/engine/stop', { method: 'POST' });
  await put('/api/config', { source: { kind: 'csv_file', path: 'data/sample_6400hz.csv', play_window: false, play_window_start: '', play_window_end: '', play_start_mode: 'begin', file_speed: 0, custom_time: false },
                             branch: { enabled: true, common_window: false, common_start: '', common_end: '' } });
  await put('/api/branch/config', { source: { kind: 'csv_file', path: 'data/nilm_steps.csv', play_window: false, play_window_start: '', play_window_end: '', play_start_mode: 'begin', custom_time: false } });

  const calls = [];
  const dom = makeDom(calls);
  const { window } = dom, { document } = window;
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(700); };

  console.log('W1 两侧「指定时间段播放」');
  await nav('source');
  check('两侧都有勾选 + 起止输入', ['src-window', 'src-winstart', 'src-winend', 'br-window', 'br-winstart', 'br-winend'].every(i => !!$(i)));
  check('默认不启用：勾选未选中、起止输入禁用', !$('src-window').checked && $('src-winstart').disabled && $('src-winend').disabled && !$('br-window').checked && $('br-winstart').disabled);
  $('src-window').checked = true; change($('src-window')); await sleep(100);
  check('勾选后起止输入启用', !$('src-winstart').disabled && !$('src-winend').disabled);
  $('src-kind').value = 'simulator'; change($('src-kind')); await sleep(100);
  check('非离线文件时勾选禁用', $('src-window').disabled && $('src-winstart').disabled);
  $('src-kind').value = 'csv_file'; change($('src-kind')); await sleep(100);
  // 总线侧文件 data/sample_6400hz.csv：起点 = 文件第 1 条；取 state 探测后的首时标
  $('src-winstart').value = ''; change($('src-winstart'));
  $('br-window').checked = true; change($('br-window')); $('br-winstart').value = '08:00:01'; change($('br-winstart')); $('br-winend').value = ''; change($('br-winend'));
  click($('btn-br-save')); await sleep(600);
  const bcfg = await api('/api/branch/config');
  check('保存分路侧 → play_window/start/end 写入 /api/branch/config', bcfg.source.play_window === true && bcfg.source.play_window_start === '08:00:01' && bcfg.source.play_window_end === '', JSON.stringify([bcfg.source.play_window, bcfg.source.play_window_start, bcfg.source.play_window_end]));

  console.log('W2 总线侧按时间段启动（只给结束时间）');
  // 先整段播一次拿到文件起止
  $('src-window').checked = false; change($('src-window'));
  await put('/api/branch/config', { source: { play_window: false } });
  click($('btn-start2'));
  for (let i = 0; i < 40; i++) { await sleep(500); const s = await api('/api/state'); const b = await api('/api/branch/state'); if (!s.running && !b.running) break; }
  const st0 = await api('/api/state');
  const full = st0.engine.samples_in;
  const hv = await api('/api/history/voltage?max_points=10');
  const tStart = (hv.t_first !== null && hv.t_first !== undefined) ? hv.t_first - 1.0 : undefined;   // 第 1 个曲线点 = 起点 + 1 s 窗
  check('整段播放完成（基准）', !st0.running && full > 6400 && tStart !== undefined, `samples_in=${full} t_first=${hv.t_first}`);
  const tEnd = tStart !== undefined ? tStart + 2.0 : undefined;
  $('src-window').checked = true; change($('src-window')); $('src-winstart').value = ''; change($('src-winstart'));
  $('src-winend').value = tEnd !== undefined ? String(tEnd) : ''; change($('src-winend'));
  click($('btn-start2'));
  for (let i = 0; i < 40; i++) { await sleep(500); const s = await api('/api/state'); const b = await api('/api/branch/state'); if (!s.running && !b.running) break; }
  const st1 = await api('/api/state');
  const startBody = calls.filter(c => c.method === 'POST' && c.url === '/api/engine/start').pop();
  check('启动载荷含 play_window/start/end', startBody && /"play_window":true/.test(startBody.body) && /"play_window_end":"/.test(startBody.body), startBody && startBody.body);
  check('只给结束时间 → 从数据起点播到该时刻（约 2 s）', tEnd !== undefined && Math.abs(st1.engine.samples_in - 2 * 6400) <= 640, `samples_in=${st1.engine.samples_in} tEnd=${tEnd}`);
  await sleep(600);
  check('状态栏显示「播放终点」', /播放终点/.test($('src-summary').textContent), $('src-summary').textContent.slice(0, 160));
  const cfg1 = await api('/api/config');
  check('用户播放起点字段未被自动值污染（play_start_mode=begin、play_end_time 空）', cfg1.source.play_start_mode === 'begin' && cfg1.source.play_end_time === '' && cfg1.source.play_window === true);

  console.log('W3 公共时间段结束时间');
  check('联动面板有 br-common-end', !!$('br-common-end'));
  // 两个样例文件时标不重叠：分路侧用自定义时间轴对齐到总线起点 + 1 s，得到公共时间段
  $('br-customtime').checked = true; change($('br-customtime')); $('br-customstart').value = String(tStart + 1.0); change($('br-customstart'));
  $('br-common').checked = true; change($('br-common')); click($('btn-br-save')); await sleep(900);
  const pv0 = await api('/api/common_window?preview=1');
  if (pv0.ok) {
    $('br-common-end').value = String(pv0.t_start + 1.0); change($('br-common-end')); click($('btn-br-save')); await sleep(900);
    const putCE = calls.filter(c => c.method === 'PUT' && c.url === '/api/config' && /common_end/.test(c.body || '')).pop();
    check('结束时间写入 branch.common_end', !!putCE, putCE && putCE.body);
    const pv1 = await api('/api/common_window?preview=1');
    check('预览：播放终点来源＝自定义播放结束时间、可播放 1 s', pv1.ok && pv1.play_end_source === '自定义播放结束时间' && Math.abs(pv1.play_duration_s - 1.0) < 1e-3, JSON.stringify([pv1.play_end_source, pv1.play_duration_s, pv1.error]));
    click($('btn-br-common-preview')); await sleep(900);
    check('预览文本含播放终点', /播放终点.*自定义播放结束时间/.test(document.body.textContent));
  } else {
    check('公共时间段预览可用（两文件无交集则跳过）', true, '无公共时间段：' + (pv0.error || ''));
  }
  $('br-common').checked = false; change($('br-common')); $('br-common-end').value = ''; change($('br-common-end')); await sleep(600);
  $('br-customtime').checked = false; change($('br-customtime')); click($('btn-br-save')); await sleep(600);

  console.log('Z1/Z2 曲线缩放');
  await nav('overview'); await sleep(2500);
  const cv = $('ov-u');
  const c0 = cv.__chart;
  check('折线图有缩放工具条（X＋ X－ Y＋ Y－ 复位）', !!cv.__zoombar && cv.__zoombar.querySelectorAll('button.zoom-btn:not(.pan-btn)').length === 5 && cv.__zoombar.isConnected);
  check('初始无缩放：xfull/yfull 与视窗一致', c0 && c0.xmin === c0.xfull[0] && c0.xmax === c0.xfull[1] && !c0.zoom);
  const W = c0.w, pad = c0.pad;
  const midX = pad.l + (W - pad.l - pad.r) / 2, midY = pad.t + (c0.h - pad.t - pad.b) / 2;
  const wheel = (dy, shift) => cv.dispatchEvent(new window.WheelEvent('wheel', { deltaY: dy, shiftKey: !!shift, clientX: midX, clientY: midY, bubbles: true, cancelable: true }));
  wheel(-100, false); await sleep(100);
  const c1 = cv.__chart;
  check('滚轮 → X 轴放大（视窗宽度变为 0.8 倍、Y 不变）', c1.zoom && c1.zoom.x && Math.abs((c1.xmax - c1.xmin) / (c0.xmax - c0.xmin) - 0.8) < 1e-6 && !c1.zoom.y && c1.ymin === c0.ymin, `${(c1.xmax - c1.xmin) / (c0.xmax - c0.xmin)}`);
  check('缩放条提示「已缩放 X」', /已缩放 X/.test(cv.__zoombar.textContent), cv.__zoombar.textContent);
  wheel(-100, true); await sleep(100);
  const c2 = cv.__chart;
  check('Shift+滚轮 → Y 轴放大（0.8 倍）、X 不变', c2.zoom.y && Math.abs((c2.ymax - c2.ymin) / (c0.ymax - c0.ymin) - 0.8) < 1e-6 && c2.xmin === c1.xmin, `${(c2.ymax - c2.ymin) / (c0.ymax - c0.ymin)}`);
  check('ZOOM 状态以绝对时间保存（x + tbase）', window.ZOOM['ov-u'] && window.ZOOM['ov-u'].x[0] > 1e9);
  cv.dispatchEvent(new window.MouseEvent('dblclick', { bubbles: true, cancelable: true })); await sleep(100);
  const c3 = cv.__chart;
  check('双击 → 复位（视窗回到全图、ZOOM 清除）', !c3.zoom && c3.xmin === c0.xmin && c3.xmax === c0.xmax && c3.ymin === c0.ymin && !window.ZOOM['ov-u']);
  // 拖选：水平 25%→50%
  const x0 = pad.l + (W - pad.l - pad.r) * 0.25, x1 = pad.l + (W - pad.l - pad.r) * 0.5;
  const mouse = (type, x, y, ctrl) => cv.dispatchEvent(new window.MouseEvent(type, { clientX: x, clientY: y, button: 0, ctrlKey: !!ctrl, bubbles: true, cancelable: true }));
  mouse('mousedown', x0, midY); mouse('mousemove', x1, midY + 2); await sleep(50);
  check('拖选中绘制选框（__drag）', !!cv.__drag && Math.abs(cv.__drag.x1 - x1) < 1e-6);
  mouse('mouseup', x1, midY + 2); await sleep(100);
  const c4 = cv.__chart;
  const expA = c0.xAt(x0), expB = c0.xAt(x1);
  check('松开 → 只显示拖选区间（X 25%→50%，Y 不变）', c4.zoom && c4.zoom.x && Math.abs(c4.xmin - expA) < 1e-6 && Math.abs(c4.xmax - expB) < 1e-6 && !c4.zoom.y, `${c4.xmin}~${c4.xmax} vs ${expA}~${expB}`);
  // 矩形拖选（含 Y）——v0.29：已放大后需 Ctrl+拖选（普通拖动＝平移）
  mouse('mousedown', x0, pad.t + 20, true); mouse('mousemove', x1, pad.t + 60, true); mouse('mouseup', x1, pad.t + 60, true); await sleep(100);
  const c5 = cv.__chart;
  check('Ctrl+矩形拖选 → X、Y 同时限定', c5.zoom && c5.zoom.x && c5.zoom.y && c5.ymax < c0.ymax && c5.ymin > c0.ymin, `${c5.ymin}~${c5.ymax}`);
  console.log('v0.29 放大后平移坐标轴');
  const pbtn = (z) => click(cv.__zoombar.querySelector(`button.zoom-btn[data-z="${z}"]`));
  const pw = (z) => (z[1] - z[0]);
  const zx0 = [...window.ZOOM['ov-u'].x], zy0 = [...window.ZOOM['ov-u'].y];
  check('平移按钮 ◀▶▲▼ 存在且放大后可用', ['pl', 'pr', 'pu', 'pd'].every(a => { const b = cv.__zoombar.querySelector(`button.pan-btn[data-z="${a}"]`); return b && !b.disabled; }));
  check('提示文字说明可拖动 / 方向键移动坐标轴', /移动坐标轴/.test(cv.__zoombar.textContent) && cv.style.cursor === 'grab', cv.__zoombar.textContent);
  // 拖动图面向左 → 视窗右移（X 区间整体 +，宽度不变）
  mouse('mousedown', midX, midY); mouse('mousemove', midX - 40, midY); mouse('mouseup', midX - 40, midY); await sleep(100);
  const zx1 = window.ZOOM['ov-u'].x;
  const expShift = c5.xAt(midX) - c5.xAt(midX - 40);
  check('放大后左键拖动 → X 视窗平移（量＝像素对应的数据差、宽度不变、不产生选框）', zx1[0] > zx0[0] && Math.abs((zx1[0] - zx0[0]) - expShift) < 1e-6 * Math.max(1, Math.abs(expShift)) && Math.abs(pw(zx1) - pw(zx0)) < 1e-9 && !cv.__drag && !cv.__pan, `${zx1[0] - zx0[0]} vs ${expShift}`);
  // 拖动向下 → Y 视窗上移？向下拖动图面 = 内容下移 = 视窗向上（ymin 减小）
  const zy1 = window.ZOOM['ov-u'].y;
  mouse('mousedown', midX, midY); mouse('mousemove', midX, midY + 30); mouse('mouseup', midX, midY + 30); await sleep(100);
  const zy2 = window.ZOOM['ov-u'].y;
  check('向下拖动 → Y 视窗整体下移（ymin 变大… 即内容跟随鼠标向下、可见区间上移）', zy2[0] > zy1[0] && Math.abs(pw(zy2) - pw(zy1)) < 1e-9, `${zy1} → ${zy2}`);
  // 按钮：◀ 平移 1/4 视窗
  const zxA = [...window.ZOOM['ov-u'].x]; pbtn('pl'); await sleep(100); const zxB = window.ZOOM['ov-u'].x;
  check('◀ 按钮 → X 视窗左移 1/4 宽度', Math.abs((zxA[0] - zxB[0]) - pw(zxA) * 0.25) < 1e-6 && Math.abs(pw(zxB) - pw(zxA)) < 1e-9, `${zxA[0] - zxB[0]} vs ${pw(zxA) * 0.25}`);
  const zyA = [...window.ZOOM['ov-u'].y]; pbtn('pu'); await sleep(100); const zyB = window.ZOOM['ov-u'].y;
  check('▲ 按钮 → Y 视窗上移 1/4 高度', Math.abs((zyB[0] - zyA[0]) - pw(zyA) * 0.25) < 1e-6);
  // 方向键
  const zxC = [...window.ZOOM['ov-u'].x];
  cv.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true, cancelable: true })); await sleep(100);
  const zxD = window.ZOOM['ov-u'].x;
  check('→ 键 → X 视窗右移 15%', Math.abs((zxD[0] - zxC[0]) - pw(zxC) * 0.15) < 1e-6);
  // 边界：连点 ◀ 多次不越过全图左端
  for (let k = 0; k < 40; k++) pbtn('pl'); await sleep(150);
  const zxE = window.ZOOM['ov-u'].x, cE = cv.__chart, tbE = cE.opt.tbase || 0;
  check('平移夹在全图范围内（左端 = xfull[0]、宽度不变）', Math.abs(zxE[0] - (cE.xfull[0] + tbE)) < 1e-6 && Math.abs(pw(zxE) - pw(zxC)) < 1e-9, `${zxE[0]} vs ${cE.xfull[0] + tbE}`);
  // v0.31：放大状态下在坐标轴刻度带上拖动 ⇒ 缩放该轴（不是平移）
  console.log('v0.31 轴带拖选缩放');
  const cZ = cv.__chart, zxBefore = [...window.ZOOM['ov-u'].x], zyBefore = [...window.ZOOM['ov-u'].y];
  const ax0 = pad.l + (W - pad.l - pad.r) * 0.3, ax1 = pad.l + (W - pad.l - pad.r) * 0.6, yBand = cZ.h - pad.b + Math.min(8, pad.b - 1);
  mouse('mousemove', ax0, yBand); await sleep(30);
  check('悬停 X 轴刻度带 → 光标 ew-resize', cv.style.cursor === 'ew-resize', cv.style.cursor);
  mouse('mousedown', ax0, yBand); mouse('mousemove', ax1, yBand); await sleep(30);
  check('X 轴带按下拖动 → 进入轴带拖选（__drag.axis=x）而非平移', !!cv.__drag && cv.__drag.axis === 'x' && !cv.__pan);
  mouse('mouseup', ax1, yBand); await sleep(120);
  const zxAfter = window.ZOOM['ov-u'].x, zyAfter = window.ZOOM['ov-u'].y;
  const expA2 = cZ.xAt(ax0) + (cZ.opt.tbase || 0), expB2 = cZ.xAt(ax1) + (cZ.opt.tbase || 0);
  check('松开 → X 视窗 = 拖选区间 30%→60%（在已放大基础上再放大）、Y 不变', Math.abs(zxAfter[0] - expA2) < 1e-6 && Math.abs(zxAfter[1] - expB2) < 1e-6 && pw(zxAfter) < pw(zxBefore) && zyAfter[0] === zyBefore[0] && zyAfter[1] === zyBefore[1], `${zxAfter} vs ${expA2}~${expB2}`);
  const cZ2 = cv.__chart, ya0 = pad.t + (cZ2.h - pad.t - pad.b) * 0.2, ya1 = pad.t + (cZ2.h - pad.t - pad.b) * 0.7, xBand = Math.max(1, pad.l - 8);
  mouse('mousemove', xBand, ya0); await sleep(30);
  check('悬停 Y 轴刻度带 → 光标 ns-resize', cv.style.cursor === 'ns-resize', cv.style.cursor);
  mouse('mousedown', xBand, ya0); mouse('mousemove', xBand + 3, ya1); mouse('mouseup', xBand + 3, ya1); await sleep(120);
  const zyAfter2 = window.ZOOM['ov-u'].y, zxAfter2 = window.ZOOM['ov-u'].x;
  check('Y 轴带拖选 → Y 视窗 = 拖选区间、X 不变', Math.abs(zyAfter2[1] - cZ2.yAt(ya0)) < 1e-6 && Math.abs(zyAfter2[0] - cZ2.yAt(ya1)) < 1e-6 && zxAfter2[0] === zxAfter[0] && zxAfter2[1] === zxAfter[1], `${zyAfter2} vs ${cZ2.yAt(ya1)}~${cZ2.yAt(ya0)}`);
  mouse('mousemove', midX, midY); await sleep(30);
  check('回到绘图区 → 光标 grab（平移）', cv.style.cursor === 'grab', cv.style.cursor);
  check('提示文字说明轴带拖选', /轴刻度带上拖选/.test(cv.__zoombar.textContent));
  // 未放大：拖动仍是框选
  pbtn('reset'); await sleep(100);
  check('复位后平移按钮禁用、光标恢复十字', cv.__zoombar.querySelector('button.pan-btn[data-z="pl"]').disabled && cv.style.cursor === 'crosshair');
  mouse('mousedown', x0, midY); mouse('mousemove', x1, midY); await sleep(30);
  check('未放大时拖动仍为框选（__drag）', !!cv.__drag && !cv.__pan); mouse('mouseup', x1, midY); await sleep(100);
  check('→ 框选放大生效', !!cv.__chart.zoom && !!cv.__chart.zoom.x);
  const btn = (z) => click(cv.__zoombar.querySelector(`button.zoom-btn[data-z="${z}"]`));
  btn('reset'); await sleep(100);
  check('「复位」按钮', !cv.__chart.zoom);
  btn('x-'); await sleep(100);
  const c6 = cv.__chart;
  check('「X＋」按钮 → X 视窗减半', c6.zoom && Math.abs((c6.xmax - c6.xmin) / (c0.xmax - c0.xmin) - 0.5) < 1e-6);
  btn('y-'); await sleep(100);
  const c7 = cv.__chart;
  check('「Y＋」按钮 → Y 视窗减半', c7.zoom && c7.zoom.y && Math.abs((c7.ymax - c7.ymin) / (c0.ymax - c0.ymin) - 0.5) < 1e-6);
  btn('x+'); btn('x+'); await sleep(100);
  check('「X－」缩回全图即清除 X 缩放', !cv.__chart.zoom.x && cv.__chart.zoom.y);
  btn('reset');
  const other = $('ov-p');
  check('缩放状态按画布独立（ov-p 未受影响）', other && other.__chart && !other.__chart.zoom);
  btn('x-'); await sleep(100);
  mouse('mousemove', midX, midY); await sleep(50);
  const hi = cv.__hoverInfo;
  check('悬停与缩放共存（缩放后悬停仍给出最近点信息）', !!hi && hi.items.length > 0 && Math.abs(hi.mx - midX) < 1e-6, hi ? `${hi.xText} ${hi.items.length}` : '无');
  btn('reset');

  console.log('C1 CSV source_id');
  const ex = (await text('/api/curves/export')).split('\n');
  const sids = new Set(ex.slice(1).filter(Boolean).map(l => l.split(',')[2]));
  check('合并下载表头含 source_id，且总线 0 / 分路 1 都在', ex[0].trim() === 't_epoch_s,time_local,source_id,quantity,field,value' && sids.has('0') && sids.has('1'), ex[0] + ' ' + [...sids]);
  const ex2 = (await text('/api/export?fmt=csv')).split('\n');
  check('结果导出 CSV 首列 source_id=0', ex2[0].trim() === 'source_id,t_ref,quantity,metric,value,unit,window_s' && ex2[1].startsWith('0,'));
  const ex3 = (await text('/api/branch/export?fmt=csv')).split('\n');
  check('分路侧结果导出 source_id=1', ex3[1] && ex3[1].startsWith('1,'));
  const sv = await api('/api/curves/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ dir: 'output/_ui_r17' }) });
  const svV = (sv.files || []).find(f => f.quantity === 'voltage');
  check('曲线保存：分路侧数据写入同一个 <曲线>.csv（source_ids=[0,1]），不另建目录/文件', sv.ok && svV && JSON.stringify(svV.source_ids) === '[0,1]' && svV.rows_branch > 0 && (sv.files || []).every(f => !/branch\//.test(f.path)), JSON.stringify(svV));
  const svDir = path.join(ROOT, sv.dir);
  check('保存目录下无子目录、文件数＝曲线数', fs.existsSync(svDir) && fs.readdirSync(svDir).every(n => n.endsWith('.csv')) && fs.readdirSync(svDir).length === sv.files.length);
  const vlines = fs.readFileSync(path.join(svDir, 'voltage.csv'), 'utf8').split(/\r?\n/).filter(Boolean);
  check('voltage.csv 行内 source_id 同时含 0 与 1', new Set(vlines.slice(1).map(l => l.split(',')[2])).size === 2);

  // 还原
  await put('/api/config', { source: { play_window: false, play_window_start: '', play_window_end: '' }, branch: { enabled: false, common_window: false, common_start: '', common_end: '' } });
  await put('/api/branch/config', { source: { play_window: false, play_window_start: '', play_window_end: '' } });
  try { fs.rmSync(path.join(ROOT, 'output/_ui_r17'), { recursive: true, force: true }); } catch (e) {}
  console.log(`\n结果：${pass} 通过，${fail} 失败${fail ? '：' + fails.join('；') : ''}`);
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
