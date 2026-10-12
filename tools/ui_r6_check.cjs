#!/usr/bin/env node
/* 第 6 轮界面功能端到端检查（jsdom 驱动真实 index.html + app.js，打真实服务端）。
 *
 * 检查什么：
 *   D1 离线文件「自定义播放时间」：勾选框/起始时间框只在 csv_file 下可用；起始时间框只在勾选后放开；
 *      启动载荷带 custom_time / custom_time_start；用用户格式文件（0/00/00 00:12:40.0000，无表头）
 *      真跑一遍 → 服务端 source.custom_time=true、曲线时间落在自定义起始时间上
 *   D2 「保存曲线」勾选：6 条曲线面板各一个 + 导出页 6 个列表项，与 config.output.curve_save 同步；
 *      点一下 → PUT /api/config → 服务端回显改变；实时推送（render）不得把勾选翻回去；
 *      点「保存曲线数据」→ POST /api/curves/save → 未勾选曲线出现在 skipped、文件只含勾选项
 *   D3 曲线数据请求：不再 n=400，而是 max_points=…（服务端默认 24h 窗）；面板标题处有跨度说明；
 *      概览有「最近 24 小时」说明
 *
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r6_check.cjs [baseUrl] [userFormatCsv]
 * 退出码：0 全通过；1 有失败项；2 脚本自身异常。
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const { JSDOM } = require(path.join(process.env.JSDOM_DIR || '/tmp/uitest', 'node_modules/jsdom'));

const BASE = process.argv[2] || 'http://127.0.0.1:8000';
const ROOT = path.resolve(__dirname, '..');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let pass = 0, fail = 0;
const fails = [];
function check(name, ok, detail = '') {
  if (ok) { pass++; console.log(`  ✓ ${name}${detail ? '　' + detail : ''}`); }
  else { fail++; fails.push(name); console.log(`  ✗ ${name}　${detail}`); }
}

function makeUserFormatCsv() {
  // 与用户给的三行同一写法：日期段 0/00/00、当天时刻、小数 4 位（0.1ms 截断）、无表头、6400Hz、3s
  const fp = path.join(os.tmpdir(), 'ui_r6_user_fmt.csv');
  const fs6400 = 6400, n = fs6400 * 3, lines = [];
  for (let k = 0; k < n; k++) {
    const tsec = 760 + k / fs6400;
    const hh = Math.floor(tsec / 3600), mm = Math.floor((tsec % 3600) / 60), ss = tsec % 60;
    const frac = Math.floor((ss - Math.floor(ss)) * 10000);
    const stamp = `0/00/00 ${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:${String(Math.floor(ss)).padStart(2, '0')}.${String(frac).padStart(4, '0')}`;
    const w = 2 * Math.PI * 50 * k / fs6400;
    const v = [300 * Math.sin(w), 0.7 * Math.sin(w - 0.5), 300 * Math.sin(w - 2.094), 0.7 * Math.sin(w - 2.594),
      300 * Math.sin(w + 2.094), 0.7 * Math.sin(w + 1.594)].map((x) => x.toFixed(6));
    lines.push([stamp, ...v].join(','));
  }
  fs.writeFileSync(fp, lines.join('\n') + '\n');
  return fp;
}

async function main() {
  const userCsv = process.argv[3] || makeUserFormatCsv();
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const calls = [];
  const dom = new JSDOM(html, {
    url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true,
    beforeParse(window) {
      window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, {
        get: (t, p) => (p === 'measureText' ? () => ({ width: 8 })
          : p === 'createLinearGradient' ? () => ({ addColorStop() {} }) : () => {}),
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
  const Sobj = () => window.__S();
  const clrDirty = () => { const s = Sobj(); s.formDirty = false; s.srcDirty = false; s.cfgDirty = false; };
  if (typeof window.init === 'function') window.init();
  await sleep(1800);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(500); };
  const bodies = (urlPart, method) => calls.filter((c) => c.url.includes(urlPart) && (!method || c.method === method) && c.body).map((c) => JSON.parse(c.body));
  const getJson = async (u) => (await fetch(BASE + u)).json();
  const putCfg = async (b) => fetch(BASE + '/api/config', { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(b) });

  // 起点：全部勾选
  await putCfg({ output: { curve_save: { voltage: true, current: true, power: true, power_factor: true, fundamental: true, harmonic: true } } });

  console.log('\n=== D1. 离线文件：自定义播放时间 ===');
  await nav('source');
  clrDirty();
  const setKind = async (k) => { $('src-kind').value = k; change($('src-kind')); await sleep(150); };
  await setKind('simulator');
  check('simulator 下「自定义播放时间」勾选框禁用', $('src-customtime').disabled && $('src-customstart').disabled);
  await setKind('csv_file');
  if ($('src-customtime').checked) { $('src-customtime').checked = false; change($('src-customtime')); await sleep(100); }   // 服务端配置可能残留 custom_time=true
  check('csv_file 下勾选框可用、起始时间框在未勾选时禁用', !$('src-customtime').disabled && $('src-customstart').disabled,
    `customtime.disabled=${$('src-customtime').disabled} customstart.disabled=${$('src-customstart').disabled}`);
  $('src-customtime').checked = true; change($('src-customtime')); await sleep(100);
  check('勾选后起始时间框放开', !$('src-customstart').disabled);
  // 先不勾选自定义时间启动：载荷 custom_time=false
  $('src-customtime').checked = false; change($('src-customtime')); await sleep(100);
  $('src-path').value = userCsv;
  calls.length = 0; click($('btn-start2')); await sleep(2500);
  let body = bodies('/api/engine/start', 'POST').pop();
  check('未勾选：载荷 custom_time=false 且仍带 custom_time_start 字段', body && body.custom_time === false && 'custom_time_start' in body, JSON.stringify(body));
  let st = await getJson('/api/state');
  check('用户格式文件（无表头、0/00/00 时刻）能被服务端跑完', (st.finished || st.running) && !st.error && st.engine.samples_in >= 19200,
    `finished=${st.finished} samples_in=${st.engine.samples_in} err=${st.error || ''}`);
  check('未勾选时源按文件时标播放（1970-01-01 00:12:40 → t≈760s）', st.source.custom_time === false && Math.abs((st.engine.t_last || st.history.voltage.t_last) - 763) < 5,
    `custom_time=${st.source.custom_time} t_last=${st.history.voltage.t_last}`);
  // 勾选 + 指定起始时间
  clrDirty(); await nav('source'); await setKind('csv_file');
  $('src-path').value = userCsv;
  $('src-customtime').checked = true; change($('src-customtime')); await sleep(100);
  $('src-customstart').value = '2026-10-12 08:00:00';
  calls.length = 0; click($('btn-start2')); await sleep(2500);
  body = bodies('/api/engine/start', 'POST').pop();
  check('勾选：载荷 custom_time=true 且带起始时间', body && body.custom_time === true && body.custom_time_start === '2026-10-12 08:00:00', JSON.stringify(body));
  st = await getJson('/api/state');
  const t0 = new Date('2026-10-12T08:00:00').getTime() / 1000;
  check('服务端 source.custom_time=true、起始来源＝配置起始时间', st.source.custom_time === true && st.source.custom_time_start_source === '配置起始时间',
    JSON.stringify({ custom_time: st.source.custom_time, src: st.source.custom_time_start_source }));
  check('曲线时间落在自定义起始时间之后 3s 内', st.history.voltage.t_first >= t0 && st.history.voltage.t_last <= t0 + 3.5,
    `t_first-t0=${(st.history.voltage.t_first - t0).toFixed(3)} t_last-t0=${(st.history.voltage.t_last - t0).toFixed(3)}`);
  check('数据源状态摘要显示「自定义播放时间」', ($('src-summary').textContent || '').includes('自定义播放时间'));
  // 勾选但起始留空 → 用文件第 1 条
  clrDirty(); await nav('source'); await setKind('csv_file');
  $('src-path').value = userCsv; $('src-customtime').checked = true; change($('src-customtime')); $('src-customstart').value = '';
  click($('btn-start2')); await sleep(2500);
  st = await getJson('/api/state');
  check('起始留空：起始来源＝文件第 1 条数据时间（760.0s）', st.source.custom_time_start_source === '文件第 1 条数据时间' && Math.abs(st.source.custom_time_start - 760) < 1e-6,
    `src=${st.source.custom_time_start_source} t0=${st.source.custom_time_start}`);
  // 非法起始时间 → 400 且界面提示
  clrDirty(); await nav('source'); await setKind('csv_file');
  $('src-path').value = userCsv; $('src-customtime').checked = true; change($('src-customtime')); $('src-customstart').value = '昨天';
  calls.length = 0; click($('btn-start2')); await sleep(1500);
  const bad = calls.find((c) => c.url.includes('/api/engine/start'));
  check('非法起始时间：服务端 400 拒绝', bad && bad.status === 400, `status=${bad && bad.status}`);
  const toastTxt = (document.getElementById('toast') || document.body).textContent || '';
  check('界面给出起始时间解析失败提示', /起始时间/.test(toastTxt), toastTxt.slice(-80));

  console.log('\n=== D3. 曲线数据请求与 24h 说明 ===');
  calls.length = 0;
  await nav('overview');
  if (typeof window.refreshHistory === 'function') await window.refreshHistory();
  await sleep(300);
  const histCalls = calls.filter((c) => c.url.includes('/api/history/'));
  check('曲线请求不再 n=400、改为 max_points（服务端默认 24h 窗）', histCalls.length >= 6 && histCalls.every((c) => /max_points=\d+/.test(c.url) && !/[?&]n=/.test(c.url)),
    histCalls.slice(0, 2).map((c) => c.url).join(' '));
  check('概览给出「最近 24 小时」说明', /最近 24 小时/.test($('ov-histnote').textContent || ''));
  const spans = [...document.querySelectorAll('.curvespan')].map((e) => e.textContent || '');
  check('曲线面板标题处标注数据跨度与点数', spans.some((s) => /点/.test(s) && /保留窗 24h/.test(s)), spans.filter(Boolean)[0]);
  const hv = await getJson('/api/history/voltage?max_points=1500');
  check('history 接口返回 24h 窗元数据', hv.hours === 24 && typeof hv.count_total === 'number' && typeof hv.span_s === 'number', JSON.stringify({ hours: hv.hours, count: hv.count, total: hv.count_total }));

  console.log('\n=== D2. 「保存曲线」勾选 ===');
  const panelBoxes = () => [...document.querySelectorAll('.panel h3 .curve-save')];
  const listBoxes = () => [...document.querySelectorAll('#curve-save-list .curve-save')];
  check('6 条趋势曲线面板各有一个「保存曲线」勾选框', panelBoxes().length === 6 && new Set(panelBoxes().map((b) => b.dataset.curve)).size === 6,
    panelBoxes().map((b) => b.dataset.curve).join(','));
  check('初始全部勾选（与服务端 curve_save 一致）', panelBoxes().every((b) => b.checked));
  // 在概览页取消「三相电流」
  const curBox = panelBoxes().find((b) => b.dataset.curve === 'current');
  calls.length = 0; curBox.checked = false; change(curBox); await sleep(800);
  const put = calls.find((c) => c.url === '/api/config' && c.method === 'PUT');
  check('取消勾选 → PUT /api/config 带 output.curve_save.current=false', put && put.status === 200 && JSON.parse(put.body).output.curve_save.current === false, put ? put.body : '未捕获 PUT');
  let cfg = await getJson('/api/config');
  check('服务端回显 current=false、其余不变', cfg.output.curve_save.current === false && cfg.output.curve_save.voltage === true);
  // 模拟实时推送触发 render：勾选不得翻回
  Sobj().state = await getJson('/api/state');
  if (typeof window.render === 'function') window.render();
  await sleep(100);
  check('实时推送 render 后勾选仍为未选（不被翻回）', !panelBoxes().find((b) => b.dataset.curve === 'current').checked);
  // 在功率因数页取消 PF
  await nav('power_factor');
  const pfBox = document.querySelector('#view-power_factor .curve-save');
  check('功率因数页有 power_factor 勾选框', pfBox && pfBox.dataset.curve === 'power_factor');
  pfBox.checked = false; change(pfBox); await sleep(800);
  cfg = await getJson('/api/config');
  check('PF 取消后服务端 power_factor=false', cfg.output.curve_save.power_factor === false);
  // 导出页列表同步 + 保存
  await nav('export');
  check('导出页列表 6 项且与面板勾选同步（current/power_factor 未选）', listBoxes().length === 6
    && !listBoxes().find((b) => b.dataset.curve === 'current').checked && !listBoxes().find((b) => b.dataset.curve === 'power_factor').checked
    && listBoxes().find((b) => b.dataset.curve === 'voltage').checked);
  check('下载链接文案显示勾选数 4/6', /4\/6/.test($('lnk-curves-dl').textContent || ''), $('lnk-curves-dl').textContent);
  calls.length = 0; click($('btn-save-curves')); await sleep(1500);
  const saveCall = calls.find((c) => c.url === '/api/curves/save');
  check('点「保存曲线数据」→ POST /api/curves/save 200', saveCall && saveCall.status === 200, `status=${saveCall && saveCall.status}`);
  const outTxt = $('curves-out').textContent || '';
  check('结果列出已保存文件与「未勾选，已跳过」', /voltage\.csv/.test(outTxt) && /未勾选，已跳过/.test(outTxt) && !/current\.csv/.test(outTxt), outTxt.slice(0, 120));
  // 在导出页重新勾选 current → 面板同步
  const cl = listBoxes().find((b) => b.dataset.curve === 'current');
  cl.checked = true; change(cl); await sleep(800);
  await nav('overview');
  check('导出页重新勾选 current → 概览面板勾选同步为选中', panelBoxes().find((b) => b.dataset.curve === 'current').checked);
  cfg = await getJson('/api/config');
  check('服务端 current=true', cfg.output.curve_save.current === true);

  // 收尾：恢复全勾选、清理生成的 curves 目录、回到模拟器
  await putCfg({ output: { curve_save: { voltage: true, current: true, power: true, power_factor: true, fundamental: true, harmonic: true } } });
  await fetch(BASE + '/api/engine/start', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ kind: 'simulator' }) });

  console.log(`\n=== 结果：PASS ${pass} / FAIL ${fail} ===`);
  if (fails.length) { console.log('失败项：'); fails.forEach((f) => console.log('  - ' + f)); }
  process.exit(fail ? 1 : 0);
}

main().catch((e) => { console.error('脚本异常：', e); process.exit(2); });
