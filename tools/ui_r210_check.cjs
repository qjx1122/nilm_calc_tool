#!/usr/bin/env node
/* 第 210 轮（v0.99.51）界面检查：数据处理页「波形预览」子界面（内部标识 wave-board）。
 * jsdom 驱动真实 index.html + app.js，打真实服务端。
 *
 *   N  页内导航：6 个子界面按钮，「波形预览」排在「波形分析」后面，两者互不影响
 *   M  预览模块可以动态增加、复制、移动、删除、切换数据源类型；每个模块有自己的配置和画布；最多 12 个
 *   O  离线波形 CSV 模块：文件路径、显示的时间段、每个点的周波数都可以配置，电压 / 电流曲线的数值与文件一致
 *   R  实时监测输出模块：文件路径可以配置（下拉选择或手填），能显示电压 / 电流 / 有功 / 无功 / 功率因数；
 *      数据来源、运行批次、只看最近、自动刷新；正在写入的半行不显示
 *   L  模块清单和配置保存在浏览器本地：重新打开页面后恢复并自动加载曲线；图例勾选也保存在本地，不写运行配置
 *   X  整个过程中页面没有发出任何修改类请求（只读）；没有脚本错误
 *
 * 用法：JSDOM_DIR=<含 node_modules/jsdom 的目录> node tools/ui_r210_check.cjs [baseUrl]
 * 前提：
 *   - 服务已启动（python cli.py serve），并且与本脚本在同一台机器上：脚本在系统临时目录生成一份 6 秒的录波文件和一份
 *     按实时落盘格式手写的曲线文件，把绝对路径交给服务端读取，结束时删除；
 *   - 请对着临时服务跑，不要对着正在用的服务：R 段会在总线侧把那份录波文件播放一遍（约 1 秒，用默认的最快速度），
 *     让工具自己写出一组实时监测输出文件，开始前会先停止两侧的数据源。除此之外不改任何配置。
 * 退出码：0 全通过；1 有失败项；2 脚本自身异常。
 */
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
const MON_T0 = 1790000000, RUN_A = 1790000100111, RUN_B = 1790000200222, RUN_C = 1790000150333;
const MON_HEAD = 't_epoch_s,time_local,source_id,window_s,Ua,Ub,Uc,Uab,Ubc,Uca,unbalance_pct,U1,run_id';
const monRow = (k, sid, base, run) => `${MON_T0 + k}.0,2026-09-21 00:00:00.000,${sid},1.0,${base + k},${base + 100 + k},${base + 200 + k},1,2,3,0.1,,${run}`;
function writeMonitorCsv(file) {
  const rows = [];
  for (let k = 0; k < 20; k++) rows.push(monRow(k, 0, 100, RUN_A));
  for (let k = 0; k < 10; k++) rows.push(monRow(k, 1, 500, RUN_C));
  for (let k = 0; k < 30; k++) rows.push(monRow(k, 0, 110, RUN_B));
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
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ui_r210_'));
  const wave = path.join(tmp, 'wave_6s.csv'), mon = path.join(tmp, 'voltage_20260921.csv');
  writeWaveCsv(wave); writeMonitorCsv(mon);
  try {
    await run(wave, mon);
  } finally {
    await real('/api/engine/stop', 'POST').catch(() => {});
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

async function run(wave, mon) {
  // 跨段用到的东西放在最前面；页面重新打开后 window / document 等会换成新页面的
  let page, window, document, click, set, idle, mods, field, act, status, lastToast, curveCalls;
  let produced = [], subButtons = [], boardBtn = null, off = null, rt = null, m = [], d = null, n0 = 0, url = '';
  const mutating = [], errs = [];                          // 各个页面发出的修改类请求、脚本错误（X 段汇总）
  const $ = (id) => document.getElementById(id);
  const byKind = (kind) => produced.find((f) => f.kind === kind);
  const cv = (el, key) => document.getElementById(`wb-cv-${el.dataset.wbId}-${key}`);
  const seriesOf = (canvas) => (canvas && canvas.__chart ? canvas.__chart.pts.map((x) => x.name) : []);
  const dataOf = (el) => window.WB.rt[el.dataset.wbId].data;
  const modelOf = (el) => window.WB.modules.find((x) => x.id === el.dataset.wbId);
  const offData = () => dataOf(off), rtData = () => dataOf(rt), offMod = () => modelOf(off);
  const canvasIds = () => Array.from(document.querySelectorAll('#wb-modules canvas')).map((c) => c.id);
  const open = async (seed) => {
    page = await boot(seed);
    ({ window, document, click, set, idle, mods, field, act, status, lastToast, curveCalls } = page);
  };
  const close = () => {
    mutating.push(...page.calls.filter((c) => c.method !== 'GET')); errs.push(...page.errors);
    page.window.close();
  };

  // ------------------------------------------------------------------ 准备：让工具自己写出一组实时监测输出文件
  console.log('— 准备：在总线侧把 6 秒的录波文件播放一遍，生成实时监测输出文件');
  await real('/api/engine/stop', 'POST'); await real('/api/branch/engine/stop', 'POST');
  const before = (await real('/api/process/monitor/files')).files.map((f) => f.path);
  const started = await real('/api/engine/start', 'POST', { kind: 'csv_file', path: wave, block_samples: 1280, play_start_mode: 'begin', with_branch: false });
  let st = null;
  for (let k = 0; k < 400; k++) { st = await real('/api/state'); if (st.finished || st.error) break; await sleep(50); }
  await sleep(600);                                        // 播完之后运行线程还会把缓冲写一次盘
  produced = (await real('/api/process/monitor/files')).files.filter((f) => !before.includes(f.path));
  check('准备 播放完成，工具写出了电压 / 电流 / 功率 / 功率因数四种监测输出文件', () => started.ok !== false && st && st.finished && !st.error
    && ['voltage', 'current', 'power', 'power_factor'].every(byKind), () => `新文件：${produced.map((f) => f.path).join('、') || '无'}`);
  if (!['voltage', 'current', 'power', 'power_factor'].every(byKind)) throw new Error('没有生成监测输出文件，后面的检查无法进行');

  await open(null);

  // ------------------------------------------------------------------ N：页内导航
  await section('N 页内导航', async () => {
    click(document.querySelector('.navitem[data-view="process"]')); await sleep(500);
    subButtons = Array.from(document.querySelectorAll('#sub-nav-process .sub-navitem'));
    const order = subButtons.map((b) => b.dataset.subview);
    check('N1 页内导航有 6 个子界面按钮，「波形预览」排在「波形分析」后面', () => order.join(',') === 'rsample,nilm-tune,profile-extract,wave-preview,wave-board,ct-estimate', () => order.join(','));
    boardBtn = subButtons.find((b) => b.dataset.subview === 'wave-board');
    check('N2 新按钮显示「波形预览」，原来的子界面仍显示「波形分析」', () => !!boardBtn && boardBtn.textContent.includes('波形预览')
      && subButtons.find((b) => b.dataset.subview === 'wave-preview').textContent.includes('波形分析'));
    click(boardBtn); await sleep(500);
    const active = Array.from(document.querySelectorAll('#view-process .subview.active')).map((s) => s.id);
    check('N3 点「波形预览」只显示这一个子界面，标题是「波形预览」', () => active.join() === 'view-process-wave-board'
      && $('view-process-wave-board').querySelector('h2').textContent.trim() === '波形预览' && boardBtn.classList.contains('active'), () => active.join());
    check('N4 助手里两个子界面的名称各是各的', () => window.__labels['wave-board'] === '波形预览' && window.__labels['wave-preview'] === '波形分析');
    check('N5 一开始没有模块：显示空白提示，计数为 0', () => mods().length === 0 && $('wb-empty').style.display !== 'none'
      && $('wb-count').textContent.includes('共 0 个模块'), () => $('wb-count').textContent);
    check('N6 「波形分析」子界面的标题和控件没有变', () => $('view-process-wave-preview').querySelector('h2').textContent.trim() === '波形分析'
      && !!$('wp-path') && !!$('btn-wp-rms') && !$('view-process-wave-preview').textContent.includes('波形预览'));
  });

  // ------------------------------------------------------------------ M：模块的增删、复制、移动、类型切换
  await section('M 预览模块可以动态配置', async () => {
    click($('btn-wb-add-offline')); await sleep(150);
    m = mods();
    check('M1 点「＋ 离线波形 CSV 模块」出现 1 个模块：有文件路径、起止时刻、每个点的周波数', () => m.length === 1 && m[0].classList.contains('wb-offline')
      && ['off-file', 'off-path', 'off-tstart', 'off-tend', 'off-cycles', 'off-show'].every((f) => field(m[0], f)) && $('wb-empty').style.display === 'none'
      && field(m[0], 'off-cycles').value === '10', () => `模块数 ${m.length}`);
    click($('btn-wb-add-monitor')); await sleep(150);
    m = mods();
    const quantityTexts = m[1] ? Array.from(field(m[1], 'mon-quantity').options).map((o) => o.textContent) : [];
    check('M2 点「＋ 实时监测输出模块」出现第 2 个模块：有文件路径；可选电压 / 电流 / 有功功率 / 无功功率 / 功率因数', () => m.length === 2 && m[1].classList.contains('wb-monitor')
      && ['mon-file', 'mon-path', 'mon-quantity', 'mon-refresh'].every((f) => field(m[1], f))
      && ['电压', '电流', '有功功率', '无功功率', '功率因数'].every((q) => quantityTexts.includes(q)), () => quantityTexts.join('/'));
    check('M3 每个模块有自己的画布（离线模块电压、电流各一张，监测模块一张），id 互不相同', () => canvasIds().length === 3 && new Set(canvasIds()).size === 3, () => canvasIds().join(','));
    check('M4 模块标题带序号和数据源类型，计数随之更新', () => m[0].querySelector('.wb-tag').textContent === '模块 1 · 离线波形 CSV'
      && m[1].querySelector('.wb-tag').textContent === '模块 2 · 实时监测输出' && $('wb-count').textContent.includes('共 2 个模块'));
    // 每个模块各自的配置：给两个模块填不同的内容
    field(m[0], 'off-path').value = 'data/__a__.csv'; page.change(field(m[0], 'off-path'));
    field(m[0], 'off-cycles').value = '25'; page.change(field(m[0], 'off-cycles'));
    field(m[0], 'title').value = '甲'; page.change(field(m[0], 'title'));
    const saved1 = JSON.parse(window.localStorage.getItem(KEY));
    check('M5 改一个模块的配置只影响它自己，并立即保存到浏览器本地', () => saved1.modules.length === 2 && saved1.modules[0].offline.path === 'data/__a__.csv'
      && saved1.modules[0].offline.cycles === '25' && saved1.modules[0].title === '甲' && saved1.modules[1].monitor.path === '' && saved1.modules[1].offline.cycles === '10');
    // 复制
    click(act(m[0], 'copy')); await idle();
    m = mods();
    check('M6 「复制」在原模块后面多出一个配置相同的模块', () => m.length === 3 && field(m[1], 'off-path').value === 'data/__a__.csv' && field(m[1], 'off-cycles').value === '25'
      && field(m[1], 'title').value === '甲（副本）' && m[2].classList.contains('wb-monitor') && new Set(canvasIds()).size === canvasIds().length, () => `模块数 ${m.length}`);
    // 移动
    const idsBefore = m.map((e) => e.dataset.wbId);
    click(act(m[2], 'up')); await sleep(100);
    m = mods();
    check('M7 「上移」把模块往前挪一位，序号随之更新；第一个不能再上移、最后一个不能再下移', () => m.map((e) => e.dataset.wbId).join() === [idsBefore[0], idsBefore[2], idsBefore[1]].join()
      && window.WB.modules.map((x) => x.id).join() === m.map((e) => e.dataset.wbId).join() && m[1].querySelector('.wb-tag').textContent.startsWith('模块 2')
      && act(m[0], 'up').disabled && !act(m[0], 'down').disabled && act(m[2], 'down').disabled, () => m.map((e) => e.dataset.wbId).join());
    click(act(m[0], 'down')); await sleep(100);
    m = mods();
    check('M8 「下移」同理', () => m.map((e) => e.dataset.wbId).join() === [idsBefore[2], idsBefore[0], idsBefore[1]].join(), () => m.map((e) => e.dataset.wbId).join());
    // 切换数据源类型：两种类型的配置各自保留
    const sw = m[1];                                         // 这是最初的离线模块（甲）
    set(field(sw, 'type'), 'monitor'); await idle();
    const asMonitor = sw.classList.contains('wb-monitor') && !!field(sw, 'mon-path') && !field(sw, 'off-path') && sw.querySelectorAll('canvas').length === 1;
    set(field(sw, 'type'), 'offline'); await idle();
    check('M9 模块内可以切换数据源类型：表单和画布随之更换，切回来时原来的配置还在', () => asMonitor && sw.classList.contains('wb-offline')
      && field(sw, 'off-path').value === 'data/__a__.csv' && field(sw, 'off-cycles').value === '25' && sw.querySelectorAll('canvas').length === 2);
    // 收起配置
    click(act(sw, 'collapse')); await sleep(60);
    const collapsed = sw.classList.contains('wb-collapsed') && act(sw, 'collapse').textContent === '展开配置';
    click(act(sw, 'collapse')); await sleep(60);
    check('M10 「收起配置 / 展开配置」可以来回切换', () => collapsed && !sw.classList.contains('wb-collapsed') && act(sw, 'collapse').textContent === '收起配置');
    // 排列
    set($('wb-layout'), '2');
    const twoCols = $('wb-modules').classList.contains('wb-cols-2') && JSON.parse(window.localStorage.getItem(KEY)).layout === 2;
    set($('wb-layout'), '1');
    check('M11 排列方式可以在每行 1 个 / 每行 2 个之间切换，并保存', () => twoCols && !$('wb-modules').classList.contains('wb-cols-2'));
    // 删除单个（有路径的模块会先确认）
    page.confirms.length = 0;
    click(act(sw, 'remove')); await sleep(100);
    check('M12 「删除」去掉这一个模块（填了文件的模块删除前要确认）', () => mods().length === 2 && !mods().some((e) => e.dataset.wbId === sw.dataset.wbId)
      && page.confirms.length === 1 && page.confirms[0].includes('甲') && window.WB.modules.length === 2, () => page.confirms.join('|'));
    // 上限
    for (let k = 0; k < 12; k++) { click($('btn-wb-add-monitor')); }
    await sleep(200);
    check('M13 最多 12 个模块：超出时提示，不再增加', () => mods().length === 12 && lastToast().includes('最多 12 个预览模块'), () => `模块数 ${mods().length}；提示：${lastToast()}`);
    // 全部删除
    page.confirms.length = 0;
    click($('btn-wb-clear')); await sleep(200);
    check('M14 「全部删除」确认后清空，回到空白提示，本地存储里也清空', () => mods().length === 0 && $('wb-empty').style.display !== 'none' && page.confirms.length === 1
      && JSON.parse(window.localStorage.getItem(KEY)).modules.length === 0 && document.querySelectorAll('#wb-modules canvas').length === 0);
  });

  // ------------------------------------------------------------------ O：离线波形 CSV
  await section('O 离线波形 CSV 模块：文件路径、时间段、每个点的周波数', async () => {
    // 上一段如果中途出错，可能留下模块：先清空，保证这一段从空白开始
    if (mods().length) { click($('btn-wb-clear')); await sleep(200); }
    click($('btn-wb-add-offline')); await sleep(300);
    off = mods()[0];
    const fileOptions = Array.from(field(off, 'off-file').options).map((o) => o.value).filter(Boolean);
    check('O1 文件下拉列出服务端 data 目录下的 CSV', () => fileOptions.length > 0 && fileOptions.every((v) => v.startsWith('data/') && v.endsWith('.csv')), () => `${fileOptions.length} 个：${fileOptions.slice(0, 3).join('、')}`);
    n0 = curveCalls().length;
    set(field(off, 'off-file'), fileOptions[0]); await sleep(1500);
    check('O2 从下拉里选文件：填入路径并显示文件信息，不自动加载曲线', () => field(off, 'off-path').value === fileOptions[0] && status(off).startsWith('文件信息：采样率')
      && status(off).includes('Hz') && curveCalls().length === n0, () => status(off).slice(0, 60));
    // 手填路径 + 每个点 10 个周波
    field(off, 'off-path').value = wave; field(off, 'off-cycles').value = '10';
    n0 = curveCalls().length;
    click(act(off, 'load')); await idle();
    d = offData();
    url = decodeURIComponent((curveCalls()[n0] || {}).url || '');
    check('O3 手填文件路径后点「加载曲线」：请求带着这个路径和每个点 10 个周波', () => curveCalls().length === n0 + 1 && url.startsWith('/api/process/wave/rms?') && url.includes('path=' + wave)
      && url.includes('agg_cycles=10') && !url.includes('t_start=') && !url.includes('t_end='), () => url.slice(0, 110));
    check('O4 整个文件 6 秒、每个点 10 个周波 → 30 个点，点与点相隔 0.2 秒', () => !!d && d.n === 30 && d.agg_cycles === 10 && d.t.length === 30
      && d.t.slice(1).every((t, i) => Math.abs(t - d.t[i] - 0.2) < 1e-6) && Math.abs(d.t[0] - WAVE_T0) < 1e-3, () => d ? `n=${d.n}，首点 ${d.t[0]}` : '无数据');
    check('O5 电压曲线：三相有效值都是 57.7 V', () => !!d && ['Ua', 'Ub', 'Uc'].every((c) => allNear(d.channels[c], U_RMS, 0.005)), () => d ? `Ua[0]=${d.channels.Ua[0]}` : '');
    check('O6 电流曲线：前 3 秒 5 A，3 秒以后 10 A', () => !!d && ['Ia', 'Ib', 'Ic'].every((c) => allNear(d.channels[c].slice(0, 15), I_RMS, 0.005) && allNear(d.channels[c].slice(15), 2 * I_RMS, 0.005)), () => d ? `Ia[0]=${d.channels.Ia[0]}，Ia[29]=${d.channels.Ia[29]}` : '');
    check('O7 电压、电流各画一张图，每张三条曲线', () => seriesOf(cv(off, 'u')).join() === 'Ua,Ub,Uc' && seriesOf(cv(off, 'i')).join() === 'Ia,Ib,Ic'
      && cv(off, 'u').__chart.pts[0].data.length === 30, () => `${seriesOf(cv(off, 'u')).join()} | ${seriesOf(cv(off, 'i')).join()}`);
    check('O8 模块下方说明点数、每个点的周波数、采样率和时间范围；标题行显示文件名', () => status(off).startsWith('已加载 30 个点：每个点 10 个周波（0.2 s）')
      && status(off).includes('采样率 6400 Hz') && status(off).includes('共 300 个周波') && off.querySelector('.wb-sub').textContent.includes('每 10 个周波一个点 · 30 点')
      && off.querySelector('.wb-title').placeholder === '离线波形 · wave_6s.csv', () => status(off).slice(0, 90));
    // 每个点的周波数可配置
    field(off, 'off-cycles').value = '1'; click(act(off, 'load')); await idle(); d = offData();
    const n1 = d ? d.n : -1, step1 = d ? d.t[1] - d.t[0] : 0;
    field(off, 'off-cycles').value = '50'; click(act(off, 'load')); await idle(); d = offData();
    check('O9 每个点的周波数可配置：1 → 300 个点（相隔 0.02 秒），50 → 6 个点（相隔 1 秒）', () => n1 === 300 && Math.abs(step1 - 0.02) < 1e-6 && !!d && d.n === 6
      && Math.abs(d.t[1] - d.t[0] - 1) < 1e-6 && allNear(d.channels.Ia.slice(0, 3), I_RMS, 0.005) && allNear(d.channels.Ia.slice(3), 2 * I_RMS, 0.005), () => `1 → ${n1} 点；50 → ${d ? d.n : '无'} 点`);
    // 时间段可配置
    field(off, 'off-cycles').value = '10';
    field(off, 'off-tstart').value = String(WAVE_T0 + 3.5); field(off, 'off-tend').value = String(WAVE_T0 + 5.5);
    n0 = curveCalls().length;
    click(act(off, 'load')); await idle(); d = offData();
    url = decodeURIComponent((curveCalls()[n0] || {}).url || '');
    check('O10 显示的时间段可配置：只取 3.5 秒到 5.5 秒 → 约 10 个点，都落在这一段里，电流都是 10 A', () => url.includes('t_start=' + (WAVE_T0 + 3.5)) && url.includes('t_end=' + (WAVE_T0 + 5.5))
      && !!d && d.n >= 9 && d.n <= 10 && d.t.every((t) => t >= WAVE_T0 + 3.5 - 1e-6 && t <= WAVE_T0 + 5.5 + 1e-6) && allNear(d.channels.Ia, 2 * I_RMS, 0.005), () => d ? `n=${d.n}，${d.t[0]} → ${d.t[d.n - 1]}` : '无数据');
    field(off, 'off-tend').value = '';
    click(act(off, 'load')); await idle(); d = offData();
    check('O11 只填起始时刻：从 3.5 秒到文件末尾', () => !!d && d.n >= 12 && d.n <= 13 && Math.abs(d.t[0] - (WAVE_T0 + 3.5)) < 0.021, () => d ? `n=${d.n}` : '无数据');
    field(off, 'off-tstart').value = '';
    click(act(off, 'load')); await idle();
    // 两侧播放启用了「公共时间段」时，跟随播放的趋势图把时间轴固定在那一段；预览模块显示的是另选的文件，不能跟着被截掉。
    // 这里直接改页面里的状态来模拟“已启用公共时间段”（真的启用需要两侧各配一份录波），改完立刻重画，再改回去。
    const keepCommon = window.__S.state.common_window;
    window.__S.state.common_window = { enabled: true, t_start: 100, t_end: 200 };
    window.wbDrawAll();
    const underCommon = seriesOf(cv(off, 'u')).join() + '|' + (cv(off, 'u').__chart ? cv(off, 'u').__chart.pts[0].data.length : 0);
    window.__S.state.common_window = keepCommon;
    window.wbDrawAll();
    check('O11b 启用「公共时间段」不影响预览模块：曲线仍按文件自己的时间范围完整显示', () => underCommon === 'Ua,Ub,Uc|30', () => underCommon);
    // 只看电压 / 只看电流：不重新读文件
    n0 = curveCalls().length;
    set(field(off, 'off-show'), 'u'); await sleep(100);
    const onlyU = off.querySelectorAll('canvas').length === 1 && seriesOf(cv(off, 'u')).join() === 'Ua,Ub,Uc' && !cv(off, 'i');
    set(field(off, 'off-show'), 'i'); await sleep(100);
    const onlyI = off.querySelectorAll('canvas').length === 1 && seriesOf(cv(off, 'i')).join() === 'Ia,Ib,Ic' && !cv(off, 'u');
    set(field(off, 'off-show'), 'both'); await sleep(100);
    check('O12 「显示」可选只看电压 / 只看电流 / 两张都看，切换时不重新读文件', () => onlyU && onlyI && off.querySelectorAll('canvas').length === 2
      && seriesOf(cv(off, 'u')).join() === 'Ua,Ub,Uc' && seriesOf(cv(off, 'i')).join() === 'Ia,Ib,Ic' && curveCalls().length === n0);
    // 更多选项：PT 变比
    click(act(off, 'more')); await sleep(50);
    const moreOpen = !off.querySelector('.wb-more').hidden && offMod().more === true;
    field(off, 'off-pt').value = '100'; click(act(off, 'load')); await idle(); d = offData();
    check('O13 「更多选项」里填 PT 变比 100：电压按 100 倍显示，电流不变', () => moreOpen && !!d && allNear(d.channels.Ua, 100 * U_RMS, 0.005) && allNear(d.channels.Ia.slice(0, 15), I_RMS, 0.005), () => d ? `Ua[0]=${d.channels.Ua[0]}` : '无数据');
    field(off, 'off-pt').value = '';
    // 点数上限
    field(off, 'off-cycles').value = '1'; field(off, 'off-maxpts').value = '10';
    click(act(off, 'load')); await idle(); d = offData();
    check('O14 点数超过上限时服务端自动加大每个点的周波数，模块下方用提醒色写明配置值和实际值', () => !!d && d.n <= 10 && d.agg_cycles === 30
      && status(off).includes('每个点 30 个周波') && status(off).includes('配置的是 1 个') && off.querySelector('.wb-status .warn') !== null, () => status(off).slice(0, 80));
    field(off, 'off-maxpts').value = ''; field(off, 'off-cycles').value = '10';
    // 写错的配置：不发请求，给出说明
    n0 = curveCalls().length;
    field(off, 'off-cycles').value = '0'; click(act(off, 'load')); await idle();
    const bad0 = status(off);
    field(off, 'off-cycles').value = '2.5'; click(act(off, 'load')); await idle();
    check('O15 每个点的周波数填 0 或小数：不发请求，说明要填不小于 1 的整数', () => curveCalls().length === n0 && bad0.includes('「每个点的周波数」要填不小于 1 的整数')
      && status(off).includes('当前“2.5”') && off.querySelector('.wb-status .bad') !== null, () => bad0);
    field(off, 'off-cycles').value = '10';
    // 文件不存在
    field(off, 'off-path').value = 'data/__ui_r210_no_such_file__.csv'; click(act(off, 'load')); await idle();
    check('O16 文件不存在：模块下方显示服务端给的原因，画布回到空白', () => status(off).startsWith('读取失败：') && status(off).includes('文件不存在') && cv(off, 'u').__chart === null
      && offData() === null && lastToast().includes('文件不存在'), () => status(off));
    // 回车加载
    field(off, 'off-path').value = wave;
    field(off, 'off-path').dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); await idle(); d = offData();
    check('O17 在输入框里按回车也能加载', () => !!d && d.n === 30 && status(off).startsWith('已加载 30 个点'), () => status(off).slice(0, 40));
    // 引擎运行时整个页面每 0.2 秒重画一次（render）：预览模块不能跟着把几万个点重新整理一遍，也不能跟着去列文件
    const drawnSeries = cv(off, 'u').__series;
    const boardCalls = () => page.calls.filter((c) => c.url.includes('/api/process/') || c.url.includes('/api/files')).length;
    const callsBeforeRender = boardCalls();
    for (let k = 0; k < 20; k++) window.render();
    await sleep(300);
    check('O18 页面反复重画时，预览模块不重新整理曲线数据，也不发请求', () => drawnSeries.length === 3 && cv(off, 'u').__series === drawnSeries
      && boardCalls() === callsBeforeRender, () => `期间请求 ${boardCalls() - callsBeforeRender} 次；曲线数据${cv(off, 'u').__series === drawnSeries ? '没有' : '被'}重新整理`);
  });

  // ------------------------------------------------------------------ R：实时监测输出文件
  await section('R 实时监测输出模块：文件路径可配置，电压 / 电流 / 有功 / 无功 / 功率因数', async () => {
    click($('btn-wb-add-monitor')); await sleep(300);
    rt = mods()[mods().length - 1];
    click(act(rt, 'files')); await sleep(800);
    const listed = Array.from(field(rt, 'mon-file').options).map((o) => o.value).filter(Boolean);
    check('R1 文件下拉列出工具刚写出的监测输出文件', () => produced.every((f) => listed.includes(f.path)), () => `下拉 ${listed.length} 个；本次新文件 ${produced.length} 个`);
    // 从下拉选电压文件 → 自动加载
    n0 = curveCalls().length;
    set(field(rt, 'mon-file'), byKind('voltage').path); await idle(); d = rtData();
    url = decodeURIComponent((curveCalls()[n0] || {}).url || '');
    check('R2 选中电压文件：路径填入并立即加载，显示三相电压', () => field(rt, 'mon-path').value === byKind('voltage').path && url.startsWith('/api/process/monitor/curve?')
      && url.includes('path=' + byKind('voltage').path) && !!d && d.quantity === 'voltage' && d.fields.join() === 'Ua,Ub,Uc' && seriesOf(cv(rt, 'm')).join() === 'Ua,Ub,Uc', () => d ? `${d.label} ${d.n} 点` : url);
    check('R3 电压数值与录波文件一致（57.7 V）', () => !!d && d.n >= 4 && ['Ua', 'Ub', 'Uc'].every((c) => allNear(d.series[c], U_RMS, 0.01)), () => d ? `Ua=${d.series.Ua.slice(0, 3).join(',')}` : '');
    check('R4 模块下方说明读到的量、来源、运行批次、时间范围', () => status(rt).startsWith(`已读取 ${d ? d.n : '?'} 个点：电压（V）`) && status(rt).includes('总线侧') && status(rt).includes('最近一次运行')
      && rt.querySelector('.wb-title').placeholder.startsWith('实时监测 · 电压 · voltage_') && rt.querySelector('.wb-chart-title').textContent.startsWith('电压（V）'), () => status(rt).slice(0, 80));
    // 电流文件
    set(field(rt, 'mon-file'), byKind('current').path); await idle(); d = rtData();
    check('R5 换成电流文件：显示三相电流，前半段 5 A、后半段 10 A', () => !!d && d.quantity === 'current' && d.fields.join() === 'Ia,Ib,Ic' && near(Math.min(...d.series.Ia), I_RMS, 0.01)
      && near(Math.max(...d.series.Ia), 2 * I_RMS, 0.01) && seriesOf(cv(rt, 'm')).join() === 'Ia,Ib,Ic', () => d ? `Ia=${d.series.Ia.join(',')}` : '');
    // 功率文件：自动＝有功
    const P1 = 3 * U_RMS * I_RMS * Math.cos(PHI), Q1 = 3 * U_RMS * I_RMS * Math.sin(PHI);
    set(field(rt, 'mon-file'), byKind('power').path); await idle(); d = rtData();
    check('R6 换成功率文件：默认显示有功功率（总 P 和分相 Pa / Pb / Pc），数值与录波一致', () => !!d && d.quantity === 'p' && d.fields.join() === 'P,Pa,Pb,Pc' && near(Math.min(...d.series.P), P1, 0.02)
      && near(Math.max(...d.series.P), 2 * P1, 0.02) && near(Math.min(...d.series.Pa), P1 / 3, 0.02) && seriesOf(cv(rt, 'm')).join() === 'P,Pa,Pb,Pc', () => d ? `P=${d.series.P.join(',')}（期望 ${P1.toFixed(1)} / ${(2 * P1).toFixed(1)}）` : '');
    set(field(rt, 'mon-quantity'), 'q'); await idle(); d = rtData();
    check('R7 「显示的量」选无功功率：显示 Q 和分相 Qa / Qb / Qc，数值与录波一致', () => !!d && d.quantity === 'q' && d.fields.join() === 'Q,Qa,Qb,Qc' && near(Math.min(...d.series.Q), Q1, 0.03)
      && near(Math.max(...d.series.Q), 2 * Q1, 0.03) && rt.querySelector('.wb-chart-title').textContent.startsWith('无功功率（var）'), () => d ? `Q=${d.series.Q.join(',')}（期望 ${Q1.toFixed(1)} / ${(2 * Q1).toFixed(1)}）` : '');
    // 功率因数文件：原来选的“无功”在这个文件里没有 → 自动改回“按文件自动选择”
    set(field(rt, 'mon-file'), byKind('power_factor').path); await idle(); d = rtData();
    check('R8 换成功率因数文件：显示 PF 和分相 PF，数值是 cos(0.3)=0.955', () => field(rt, 'mon-quantity').value === '' && !!d && d.quantity === 'pf' && d.fields[0] === 'PF'
      && allNear(d.series.PF, Math.cos(PHI), 0.01) && rt.querySelector('.wb-chart-title').textContent.startsWith('功率因数'), () => d ? `PF=${d.series.PF.join(',')}` : '');
    // 量与文件不匹配
    set(field(rt, 'mon-quantity'), 'p'); await idle();
    check('R9 文件里没有所选的量：说明这个文件能显示什么', () => status(rt).includes('这个文件里没有「有功功率」的列') && status(rt).includes('功率因数') && rtData() === null && cv(rt, 'm').__chart === null, () => status(rt));
    set(field(rt, 'mon-quantity'), ''); await idle();
    // 数据来源：真实文件里只有总线侧
    click(act(rt, 'more')); await sleep(50);
    set(field(rt, 'mon-source'), '1'); await idle();
    url = decodeURIComponent(curveCalls()[curveCalls().length - 1].url);
    check('R10 「数据来源」选分路侧而文件里只有总线侧：请求带 source_id=1，模块下方说明文件里有哪一侧', () => url.includes('source_id=1') && status(rt).includes('文件里没有分路侧的数据') && status(rt).includes('总线侧'), () => status(rt));
    set(field(rt, 'mon-source'), ''); await idle();

    // 手填路径：按实时落盘格式手写的文件（总线侧两次运行 + 分路侧一次运行）
    n0 = curveCalls().length;
    set(field(rt, 'mon-path'), mon); await idle(); d = rtData();
    url = decodeURIComponent((curveCalls()[n0] || {}).url || '');
    check('R11 文件路径可以手填：读取这个路径的文件', () => url.includes('path=' + mon) && !!d && d.quantity === 'voltage' && field(rt, 'mon-file').value === '', () => url.slice(0, 100));
    check('R12 文件里有两次运行时默认只显示最近一次（30 个点，Ua 从 110 起），并说明可以切换', () => !!d && d.n === 30 && d.series.Ua[0] === 110 && d.series.Ua[29] === 139 && d.run_mode === 'latest'
      && d.run_id === RUN_B && status(rt).includes('文件里有 2 次运行的数据') && status(rt).includes('文件里有总线侧、分路侧的数据'), () => d ? `n=${d.n} Ua[0]=${d.series.Ua[0]}` : '');
    const runOptions = Array.from(field(rt, 'mon-run').options).map((o) => o.value);
    check('R13 读取后「运行批次」下拉列出文件里的两次运行', () => runOptions.join() === ['latest', 'all', String(RUN_A), String(RUN_B)].join(), () => runOptions.join());
    set(field(rt, 'mon-run'), String(RUN_A)); await idle(); d = rtData();
    check('R14 选第一次运行：20 个点，Ua 从 100 起', () => !!d && d.n === 20 && d.series.Ua[0] === 100 && d.run_mode === 'one' && d.run_id === RUN_A && field(rt, 'mon-run').value === String(RUN_A), () => d ? `n=${d.n} Ua[0]=${d.series.Ua[0]}` : '');
    set(field(rt, 'mon-run'), 'all'); await idle(); d = rtData();
    check('R15 选全部：两次运行合在一起，时间不倒退，同一时刻只留最后写入的点', () => !!d && d.n === 30 && d.run_mode === 'all' && d.t.slice(1).every((t, i) => t > d.t[i]) && d.series.Ua[0] === 110, () => d ? `n=${d.n}` : '');
    set(field(rt, 'mon-run'), 'latest'); await idle();
    set(field(rt, 'mon-source'), '1'); await idle(); d = rtData();
    check('R16 「数据来源」选分路侧：显示分路侧的 10 个点（Ua 从 500 起）', () => !!d && d.n === 10 && d.source_id === 1 && d.series.Ua[0] === 500 && status(rt).includes('分路侧'), () => d ? `n=${d.n} Ua[0]=${d.series.Ua[0]}` : status(rt));
    set(field(rt, 'mon-source'), '0'); await idle();
    // 只看最近
    set(field(rt, 'mon-last'), '0.25'); await idle(); d = rtData();
    url = decodeURIComponent(curveCalls()[curveCalls().length - 1].url);
    check('R17 「只看最近」0.25 分钟：请求带 last_s=15，只剩最后 16 个点', () => url.includes('last_s=15') && !!d && d.n === 16 && d.t[0] === MON_T0 + 14 && d.t[15] === MON_T0 + 29, () => d ? `n=${d.n}` : status(rt));
    set(field(rt, 'mon-last'), ''); await idle();
    // 起止时刻
    set(field(rt, 'mon-tstart'), String(MON_T0 + 5)); await idle();
    set(field(rt, 'mon-tend'), String(MON_T0 + 9)); await idle(); d = rtData();
    check('R18 起止时刻：只显示这一段里的 5 个点', () => !!d && d.n === 5 && d.t[0] === MON_T0 + 5 && d.t[4] === MON_T0 + 9, () => d ? `n=${d.n}` : status(rt));
    set(field(rt, 'mon-tstart'), ''); await idle(); set(field(rt, 'mon-tend'), ''); await idle();
    d = rtData();
    const baseN = d ? d.n : -1;

    // 自动刷新：文件追加了新行，不点按钮曲线也会更新
    set(field(rt, 'mon-refresh'), '2');
    await sleep(400);
    const more = []; for (let k = 30; k < 35; k++) more.push(monRow(k, 0, 110, RUN_B));
    fs.appendFileSync(mon, more.join('\r\n') + '\r\n', 'utf8');
    n0 = curveCalls().length;
    let grew = false;
    for (let k = 0; k < 60 && !grew; k++) { await sleep(100); const x = rtData(); grew = !!x && x.n === 35; }
    d = rtData();
    check('R19 打开自动刷新后，文件里追加的 5 个点不用点按钮就显示出来', () => baseN === 30 && grew && d.series.Ua[34] === 144 && curveCalls().length > n0 && rt.querySelector('.wb-sub').textContent.includes('每 2 秒自动刷新'), () => `原 ${baseN} 点 → ${d ? d.n : '?'} 点；自动请求 ${curveCalls().length - n0} 次`);
    check('R20 自动刷新不禁用「加载曲线」按钮', () => !act(rt, 'load').disabled && act(rt, 'load').textContent === '加载曲线');
    // 正在写入的半行（没有换行符，run_id 被截断）不显示
    fs.appendFileSync(mon, `${MON_T0 + 35}.0,2026-09-21 00:00:00.000,0,1.0,145,245,345,1,2,3,0.1,,17900002`, 'utf8');
    n0 = curveCalls().length;
    for (let k = 0; k < 45 && curveCalls().length < n0 + 1; k++) await sleep(100);
    await idle(); d = rtData();
    check('R21 文件末尾有一行还没写完：这一行不显示，曲线不受影响', () => curveCalls().length > n0 && !!d && d.n === 35 && d.run_id === RUN_B && d.run_ids.length === 2, () => d ? `n=${d.n}，运行批次 ${d.run_ids.length} 个` : status(rt));
    // 不在本子界面时不刷新
    click(subButtons.find((b) => b.dataset.subview === 'rsample')); await sleep(300); await idle();
    n0 = curveCalls().length;
    await sleep(5200);
    const quiet = curveCalls().length === n0;
    const listCalls = () => page.calls.filter((c) => c.url.includes('/api/process/monitor/files')).length;
    const lists0 = listCalls();
    click(boardBtn); await sleep(300);
    for (let k = 0; k < 45 && curveCalls().length < n0 + 1; k++) await sleep(100);
    await idle();
    check('R22 切到别的子界面时停止自动刷新，切回来后继续', () => quiet && curveCalls().length > n0, () => `离开期间请求 ${quiet ? 0 : '有'} 次；回来后 ${curveCalls().length - n0} 次`);
    check('R22b 回到本子界面时重新列一次监测输出文件（新的一次运行写出的文件会出现在下拉里）', () => listCalls() === lists0 + 1, () => `列文件请求 ${listCalls() - lists0} 次`);
    set(field(rt, 'mon-refresh'), '0'); await idle();
    n0 = curveCalls().length; await sleep(3200);
    check('R23 自动刷新改成「关」后不再读取', () => curveCalls().length === n0 && !rt.querySelector('.wb-sub').textContent.includes('自动刷新'));
  });

  // ------------------------------------------------------------------ L：保存在浏览器本地，重新打开后恢复
  await section('L 模块清单和配置保存在浏览器本地', async () => {
    // 图例：取消勾选离线模块电压图里的 Ub
    const callsBeforeLegend = page.calls.length;
    const legendBox = Array.from(off.querySelectorAll('input.ser-vis')).find((b) => b.dataset.chart === cv(off, 'u').id && b.dataset.name === 'Ub');
    if (legendBox) { legendBox.checked = false; page.change(legendBox); }
    await sleep(300);
    const legendCalls = page.calls.slice(callsBeforeLegend);
    check('L1 取消勾选图例里的 Ub：这条曲线不画，勾选状态存在模块自己的配置里，不向运行配置发请求', () => !!legendBox && seriesOf(cv(off, 'u')).join() === 'Ua,Uc' && legendCalls.length === 0
      && JSON.stringify(offMod().hidden.u) === '["Ub"]' && seriesOf(cv(off, 'i')).join() === 'Ia,Ib,Ic', () => `图：${seriesOf(cv(off, 'u')).join()}；期间请求 ${legendCalls.length} 次`);
    // 给两个模块留下各不相同的配置
    field(off, 'title').value = '总线录波'; page.change(field(off, 'title'));
    field(off, 'off-cycles').value = '5'; field(off, 'off-tstart').value = String(WAVE_T0 + 1); field(off, 'off-tend').value = String(WAVE_T0 + 4);
    click(act(off, 'load')); await idle();
    set(field(rt, 'mon-run'), String(RUN_A)); await idle();
    click(act(rt, 'collapse')); await sleep(50);
    const stored = window.localStorage.getItem(KEY);
    const saved = JSON.parse(stored);
    check('L2 浏览器本地保存了两个模块各自的配置', () => saved.v === 1 && saved.modules.length === 2 && saved.modules[0].type === 'offline' && saved.modules[0].title === '总线录波'
      && saved.modules[0].offline.path === wave && saved.modules[0].offline.cycles === '5' && saved.modules[0].offline.t_start === String(WAVE_T0 + 1) && saved.modules[0].offline.t_end === String(WAVE_T0 + 4)
      && saved.modules[0].more === true && saved.modules[1].type === 'monitor' && saved.modules[1].monitor.path === mon && saved.modules[1].monitor.run === String(RUN_A)
      && saved.modules[1].monitor.source === '0' && saved.modules[1].collapsed === true, () => stored.slice(0, 120));
    close();

    // 重新打开页面
    await open(stored);
    await page.openBoard();
    m = mods();
    off = m[0]; rt = m[1];
    check('L3 重新打开页面：两个模块按原来的顺序恢复，表单里是保存的配置', () => m.length === 2 && !!off && !!rt && off.classList.contains('wb-offline') && rt.classList.contains('wb-monitor')
      && field(off, 'title').value === '总线录波' && field(off, 'off-path').value === wave && field(off, 'off-cycles').value === '5' && field(off, 'off-tstart').value === String(WAVE_T0 + 1)
      && !off.querySelector('.wb-more').hidden && field(rt, 'mon-path').value === mon && rt.classList.contains('wb-collapsed') && $('wb-count').textContent.includes('共 2 个模块'), () => `模块数 ${m.length}`);
    const dOff = off ? dataOf(off) : null, dRt = rt ? dataOf(rt) : null;
    check('L4 恢复后自动按保存的配置加载曲线：离线模块 1 秒到 4 秒、每个点 5 个周波；监测模块显示第一次运行', () => curveCalls().length === 2 && !!dOff && dOff.agg_cycles === 5 && dOff.n >= 29 && dOff.n <= 30
      && Math.abs(dOff.t[0] - (WAVE_T0 + 1)) < 0.021 && !!dRt && dRt.run_id === RUN_A && dRt.n === 20 && field(rt, 'mon-run').value === String(RUN_A), () => `离线 ${dOff ? dOff.n : '无'} 点；监测 ${dRt ? dRt.n : '无'} 点`);
    check('L5 图例里取消的 Ub 在重新打开后仍然不画', () => off && seriesOf(cv(off, 'u')).join() === 'Ua,Uc' && seriesOf(cv(off, 'i')).join() === 'Ia,Ib,Ic', () => off ? seriesOf(cv(off, 'u')).join() : '');
    // 新加的模块编号不与恢复出来的冲突
    click($('btn-wb-add-offline')); await sleep(200);
    const ids = mods().map((e) => e.dataset.wbId);
    check('L6 恢复之后再添加模块：编号不与已有模块重复', () => ids.length === 3 && new Set(ids).size === 3 && new Set(Array.from(document.querySelectorAll('#wb-modules canvas')).map((c) => c.id)).size === 5, () => ids.join(','));
    // 存储内容损坏时不报错，按没有模块处理
    close();
    await open('{"v":1,"modules":[{"type":"monitor","monitor":{"path":123,"refresh_s":"7","quantity":"x"},"hidden":"oops"},null,"bad"],"layout":"9"');   // 少了结尾的花括号
    await page.openBoard();
    const brokenOk = page.mods().length === 0 && page.errors.length === 0;
    close();
    await open('{"v":1,"seq":"abc","layout":"9","modules":[{"id":"m7","type":"monitor","monitor":{"path":123,"refresh_s":"7","quantity":"x"},"hidden":"oops"},null,{"id":"m7","type":"zzz"}]}');
    await page.openBoard();
    const odd = page.window.WB.modules;
    check('L7 本地存储的内容损坏或取值不合法时不报错：不能解析就按没有模块处理；能解析的，不是模块的条目丢掉，其余逐项修正', () => brokenOk && page.errors.length === 0
      && odd.map((x) => x.id + ':' + x.type).join() === 'm7:monitor,m8:offline' && odd[0].monitor.path === '123' && odd[0].monitor.refresh_s === '0' && odd[0].monitor.quantity === ''
      && JSON.stringify(odd[0].hidden) === '{}' && page.window.WB.layout === 1 && page.mods().length === 2, () => `模块 ${odd.map((x) => x.id + ':' + x.type).join(',')}；错误 ${page.errors.join('|')}`);
  });
  close();

  // ------------------------------------------------------------------ X：只读、无脚本错误
  await section('X 只读与脚本错误', async () => {
    check('X1 整个过程中页面没有发出任何修改类请求（只有 GET）', () => mutating.length === 0, () => mutating.map((c) => c.method + ' ' + c.url).join('、'));
    check('X2 没有脚本错误', () => errs.length === 0, () => errs.join(' | '));
    const cfg = await real('/api/config');
    const hiddenKeys = Object.keys(((cfg.output || {}).series_hidden) || {}).filter((k) => k.startsWith('wb-'));
    check('X3 运行配置里没有留下任何波形预览的内容', () => hiddenKeys.length === 0, () => hiddenKeys.join(','));
  });
}

main().then(() => {
  console.log(fail ? `\nFAIL：通过 ${pass} 项，失败 ${fail} 项\n  - ${fails.join('\n  - ')}` : `\nPASS：通过 ${pass} 项，失败 0 项`);
  process.exit(fail ? 1 : 0);
}).catch((e) => { console.error('脚本异常：', e); process.exit(2); });
