#!/usr/bin/env node
/* 第 209 轮（v0.99.50）界面检查：jsdom 驱动真实 index.html + app.js，打真实服务端。
 *
 *   N  数据处理页内导航：5 个子界面逐个可切换；原「波形预览」子界面现在叫「波形分析」（内部标识 wave-preview 不变）
 *   B3 「估计 CT」子界面的事件只绑定一次：点一次「加载逐周波 RMS 曲线」只发一次请求
 *   B1 顶栏对侧一行的频率取自对侧摘要的 f_used，不再恒为「—」
 *   B2 顶栏「暂停」「停止」的提示：侧别说对、用中文名称、服务端报错时提示失败
 *
 * 用法：JSDOM_DIR=<含 node_modules/jsdom 的目录> node tools/ui_r209_check.cjs [baseUrl]
 *   服务需已启动（python cli.py serve），并且与本脚本在同一台机器上。请对着临时服务跑，不要对着正在用的服务：
 *   - B1、B2 的实测段会启动、暂停、恢复、停止两侧的数据源（B1 用模拟器；B2 在系统临时目录生成一份 12 秒的
 *     录波文件，把绝对路径交给服务端按 0.25 倍速播放，跑完删除）；
 *   - B2 另有一段用假响应替换两侧的 engine / state 接口，用来稳定地重现“服务端返回 400 / 500”，这一段不碰服务端。
 * 退出码：0 全通过；1 有失败项；2 脚本自身异常。
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const { JSDOM } = require(path.join(process.env.JSDOM_DIR || ROOT, 'node_modules/jsdom'));
const BASE = process.argv[2] || 'http://127.0.0.1:8000';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let pass = 0, fail = 0;
const fails = [];
function check(name, ok, detail = '') {
  if (ok) { pass++; console.log(`  ✓ ${name}${detail ? '　' + detail : ''}`); }
  else { fail++; fails.push(name); console.log(`  ✗ ${name}　${detail}`); }
}

/* 生成一份三相录波文件（50 Hz 正弦，电压有效值约 57.7 V、电流约 5 A），列名与工具的离线文件格式一致 */
function writeWaveCsv(file, seconds, fsHz = 6400) {
  const n = Math.round(seconds * fsHz), lines = ['时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流'];
  for (let k = 0; k < n; k++) {
    const t = k / fsHz, w = 2 * Math.PI * 50 * t, row = [(1700000000 + t).toFixed(6)];
    for (const ph of [0, -2.0944, 2.0944]) row.push((81.65 * Math.sin(w + ph)).toFixed(4), (7.07 * Math.sin(w + ph - 0.3)).toFixed(5));
    lines.push(row.join(','));
  }
  fs.writeFileSync(file, lines.join('\n') + '\n', 'utf8');
}

async function main() {
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const calls = [];
  const errors = [];
  let fake = null;                       // (url, method) => { status, body } | null：替换某些接口的响应
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
        const canned = fake ? fake(u, method) : null;
        if (canned) return new Response(JSON.stringify(canned.body), { status: canned.status, headers: { 'content-type': 'application/json' } });
        return fetch(u.startsWith('http') ? u : BASE + u, opts);
      };
      window.alert = () => {};
      window.addEventListener('error', (e) => errors.push(String(e.message)));
    },
  });
  const { window } = dom, { document } = window;
  window.eval(js + '\n;window.__S = S; window.__labels = ASSISTANT_VIEW_LABELS;');
  // app.js 末尾写着 document.addEventListener('DOMContentLoaded', init)，而 jsdom 在构造函数返回之后才派发这个事件：
  // 这里如果再手动调一次 init()，它会跑两遍，所有用匿名函数绑定的事件都多绑一次（B3 数出的请求次数会比浏览器里多 1）。
  // 所以先去掉那个监听，再只调一次。
  document.removeEventListener('DOMContentLoaded', window.init);
  window.init();
  await sleep(1500);
  const S = window.__S;
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  const real = async (p, method = 'GET', body) => {
    const r = await fetch(BASE + p, { method, headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined });
    return r.json();
  };

  // ------------------------------------------------------------------ N：页内导航与「波形分析」
  console.log('— N 数据处理页内导航与子界面名称');
  click(document.querySelector('.navitem[data-view="process"]')); await sleep(600);
  const subButtons = Array.from(document.querySelectorAll('#sub-nav-process .sub-navitem'));
  check('N1 页内导航有 5 个子界面按钮', subButtons.length === 5, subButtons.map((b) => b.dataset.subview).join(','));
  const waveBtn = subButtons.find((b) => b.dataset.subview === 'wave-preview');
  check('N2 第 4 个按钮显示「波形分析」，内部标识仍是 wave-preview', !!waveBtn && waveBtn.textContent.trim() === '📈 波形分析');
  for (const btn of subButtons) {
    click(btn); await sleep(400);
    const active = Array.from(document.querySelectorAll('#view-process .subview.active')).map((s) => s.id);
    check(`N3 点「${btn.textContent.trim()}」只显示对应子界面`, active.length === 1 && active[0] === 'view-process-' + btn.dataset.subview
      && btn.classList.contains('active') && subButtons.filter((b) => b.classList.contains('active')).length === 1, active.join(','));
  }
  click(waveBtn); await sleep(400);
  const waveSection = $('view-process-wave-preview');
  check('N4 子界面标题是「波形分析」', !!waveSection && waveSection.querySelector('h2').textContent.trim() === '波形分析');
  const processView = $('view-process');
  const titles = Array.from(processView.querySelectorAll('[title]')).map((el) => el.getAttribute('title')).join('\n');
  check('N5 数据处理页的文字和提示里不再出现「波形预览」', !processView.textContent.includes('波形预览') && !titles.includes('波形预览'));
  check('N6 其他子界面的提示改称「波形分析」', (titles.match(/与波形分析同一套自定义时间/g) || []).length === 2);
  check('N7 助手里该子界面的名称是「波形分析」', window.__labels['wave-preview'] === '波形分析');

  // ------------------------------------------------------------------ B3：「估计 CT」只绑定一次
  console.log('— B3 「估计 CT」子界面的事件只绑定一次');
  click(subButtons.find((b) => b.dataset.subview === 'ct-estimate')); await sleep(600);
  for (const pre of ['ct-bus', 'ct-br']) {
    $(pre + '-path').value = 'data/__ui_r209_no_such_file__.csv';
    const before = calls.filter((c) => c.url.includes('/api/process/wave/rms')).length;
    click($(pre + '-btn-rms')); await sleep(800);
    const sent = calls.filter((c) => c.url.includes('/api/process/wave/rms')).length - before;
    check(`B3 点一次 ${pre}「加载逐周波 RMS 曲线」只发 1 次请求`, sent === 1, `实际 ${sent} 次`);
  }
  // 再走一遍两个调用点（页面初始化的 bindProcess、首次打开子界面的 renderProcess 都会调 initCtEstimate）
  window.eval('initCtEstimate(); initCtEstimate();');
  {
    const before = calls.filter((c) => c.url.includes('/api/process/wave/rms')).length;
    click($('ct-bus-btn-rms')); await sleep(800);
    const sent = calls.filter((c) => c.url.includes('/api/process/wave/rms')).length - before;
    check('B3 再调用两次 initCtEstimate 之后仍只发 1 次请求', sent === 1, `实际 ${sent} 次`);
  }
  click(document.querySelector('.navitem[data-view="overview"]')); await sleep(400);

  // ------------------------------------------------------------------ B1：顶栏对侧频率
  console.log('— B1 顶栏对侧一行的频率');
  const busReal = await real('/api/state'), brReal = await real('/api/branch/state');
  const withFreq = (state, key, f) => ({ ...state, [key]: { ...(state[key] || {}), f_used: f } });
  S.side = 'bus'; S.state = withFreq(busReal, 'branch', 49.987); S.branchFullState = brReal;
  window.eval('renderTop()');
  check('B1 总线侧视图、已取到分路侧完整状态：分路侧一行显示对侧摘要的频率', $('st-br-freq').textContent === '49.987 Hz', $('st-br-freq').textContent);
  S.branchFullState = null; window.eval('renderTop()');
  check('B1 总线侧视图、只有对侧摘要：同样显示', $('st-br-freq').textContent === '49.987 Hz', $('st-br-freq').textContent);
  S.state = withFreq(busReal, 'branch', null); window.eval('renderTop()');
  check('B1 对侧还没有结果时显示「—」', $('st-br-freq').textContent === '—', $('st-br-freq').textContent);
  S.side = 'branch'; S.state = withFreq(brReal, 'bus', 50.012); window.eval('renderTop()');
  check('B1 分路侧视图：总线侧一行显示对侧摘要的频率', $('st-freq').textContent === '50.012 Hz', $('st-freq').textContent);
  S.side = 'bus'; S.state = busReal;

  // 实测：两侧各起一个模拟器，等分路侧出结果后看顶栏
  await real('/api/engine/stop', 'POST'); await real('/api/branch/engine/stop', 'POST');
  const startedBus = await real('/api/engine/start', 'POST', { kind: 'simulator', with_branch: false });
  const startedBr = await real('/api/branch/engine/start', 'POST', { kind: 'simulator' });
  let liveFreq = '—';
  for (let i = 0; i < 60 && !/^\d+\.\d{3} Hz$/.test(liveFreq); i++) {
    await sleep(500);
    S.state = await real('/api/state'); S.branchFullState = await real('/api/branch/state');
    window.eval('renderTop()');
    liveFreq = $('st-br-freq').textContent;
  }
  check('B1 实测：两侧模拟器运行时，总线侧视图的分路侧一行显示频率', startedBus.ok && startedBr.ok && /^\d+\.\d{3} Hz$/.test(liveFreq), liveFreq);
  check('B1 实测：总线侧一行仍显示频率或等待首个结果', /^(\d+\.\d{3} Hz|—)$/.test($('st-freq').textContent), $('st-freq').textContent);
  await real('/api/branch/engine/stop', 'POST'); await real('/api/engine/stop', 'POST');

  // ------------------------------------------------------------------ B2：顶栏「暂停」「停止」的提示
  console.log('— B2 顶栏「暂停」「停止」的提示');
  const idleBus = await real('/api/state'), idleBr = await real('/api/branch/state');
  const running = (state, over = {}) => ({ ...state, running: true, finished: false, paused: false, pausable: true, error: null, ...over,
    engine: { ...(state.engine || {}), running: true, finished: false } });
  /* 在给定的视图和两侧状态下调用 togglePause() / stopEngine()：
   *   side        当前视图所在的一侧
   *   state       当前视图所在一侧的状态（即 S.state）
   *   branchState 总线侧视图下分路侧的完整状态（即 S.branchFullState）
   *   responses   { 'POST 的地址': { status, body } }，没列出的 engine 请求一律 200
   * 返回发出的 engine 请求地址、提示文字、提示是否为错误样式。 */
  async function act(fn, { side, state, branchState = null, responses = {} }) {
    const posts = [];
    fake = (u, method) => {
      if (method === 'POST' && /\/engine\/(pause|resume|stop)$/.test(u)) {
        posts.push(u);
        return responses[u] || { status: 200, body: { ok: true, paused: /pause$/.test(u), state } };
      }
      if (method === 'GET' && u === '/api/state') return { status: 200, body: side === 'bus' ? state : idleBus };
      if (method === 'GET' && u === '/api/branch/state') return { status: 200, body: side === 'branch' ? state : (branchState || idleBr) };
      return null;
    };
    S.side = side; S.state = state; S.branchFullState = side === 'bus' ? branchState : null;
    // 不能用 innerHTML = ''：app.js 给 innerHTML 加了“内容相同就不重写”的补丁，第二次赋同一个值不会清空
    while ($('toast').firstChild) $('toast').firstChild.remove();
    await window.eval(fn + '()');
    const toasts = Array.from($('toast').children);
    fake = null;
    return { posts, text: toasts.map((t) => t.textContent).join(' | '), err: toasts.some((t) => t.classList.contains('err')) };
  }
  const show = (r) => `请求 ${r.posts.join(', ') || '无'}；提示「${r.text}」${r.err ? '（错误样式）' : ''}`;
  const refuse = (status, error) => ({ status, body: { ok: false, error } });
  let r;

  // ① 分路侧视图：请求发到分路侧，提示也要说分路侧
  r = await act('togglePause', { side: 'branch', state: running(idleBr) });
  check('B2-① 分路侧视图暂停：提示「分路侧已暂停」', r.posts.join() === '/api/branch/engine/pause' && r.text === '分路侧已暂停' && !r.err, show(r));
  r = await act('togglePause', { side: 'branch', state: running(idleBr, { paused: true }) });
  check('B2-① 分路侧视图恢复：提示「分路侧已恢复」', r.posts.join() === '/api/branch/engine/resume' && r.text === '分路侧已恢复' && !r.err, show(r));
  r = await act('stopEngine', { side: 'branch', state: running(idleBr) });
  check('B2-① 分路侧视图停止：提示「分路侧已停止」', r.posts.join() === '/api/branch/engine/stop' && r.text === '分路侧已停止' && !r.err, show(r));
  r = await act('stopEngine', { side: 'branch', state: running(idleBr), responses: { '/api/branch/engine/stop': refuse(500, '内部错误') } });
  check('B2-① 分路侧视图停止失败：提示「分路侧停止失败：…」', r.text === '分路侧停止失败：内部错误' && r.err, show(r));

  // ② 总线侧视图操作分路侧：服务端报错时不能提示成功
  r = await act('togglePause', { side: 'bus', state: idleBus, branchState: running(idleBr),
    responses: { '/api/branch/engine/pause': refuse(400, '数据源已播放完毕') } });
  check('B2-② 总线侧视图暂停分路侧被拒：提示失败并带上服务端原因', r.posts.join() === '/api/branch/engine/pause'
    && r.text === '分路侧暂停失败：数据源已播放完毕' && r.err, show(r));
  r = await act('stopEngine', { side: 'bus', state: running(idleBus), branchState: running(idleBr),
    responses: { '/api/branch/engine/stop': refuse(500, '内部错误') } });
  check('B2-② 两侧都在运行、分路侧停止出错：总线侧报成功、分路侧报失败', r.posts.join() === '/api/engine/stop,/api/branch/engine/stop'
    && r.text === '总线侧已停止，分路侧停止失败：内部错误' && r.err, show(r));
  r = await act('togglePause', { side: 'bus', state: running(idleBus), branchState: running(idleBr),
    responses: { '/api/engine/pause': refuse(400, '暂停/恢复仅支持离线文件（csv_file）源') } });
  check('B2-② 总线侧自己被拒时同样提示失败', r.text === '总线侧暂停失败：暂停/恢复仅支持离线文件（csv_file）源，分路侧已暂停' && r.err, show(r));

  // ③ 侧别用中文名称
  r = await act('togglePause', { side: 'bus', state: running(idleBus), branchState: running(idleBr) });
  check('B2-③ 两侧都暂停：「总线侧已暂停，分路侧已暂停」', r.posts.join() === '/api/engine/pause,/api/branch/engine/pause'
    && r.text === '总线侧已暂停，分路侧已暂停' && !r.err, show(r));
  r = await act('togglePause', { side: 'bus', state: running(idleBus, { paused: true }) });
  check('B2-③ 总线侧恢复：「总线侧已恢复」', r.posts.join() === '/api/engine/resume' && r.text === '总线侧已恢复' && !r.err, show(r));
  r = await act('stopEngine', { side: 'bus', state: running(idleBus), branchState: running(idleBr) });
  check('B2-③ 两侧都停止：「总线侧已停止，分路侧已停止」', r.text === '总线侧已停止，分路侧已停止' && !r.err, show(r));
  r = await act('togglePause', { side: 'bus', state: idleBus, branchState: running(idleBr) });
  check('B2-③ 只有分路侧在运行：只操作分路侧', r.posts.join() === '/api/branch/engine/pause' && r.text === '分路侧已暂停' && !r.err, show(r));
  S.side = 'bus'; S.state = idleBus; S.branchFullState = null;

  // ------------------------------------------------------------------ B2 实测：不替换任何接口
  console.log('— B2 实测：两侧各自慢速播放一份录波文件');
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ui_r209_'));
  try {
    const wave = path.join(tmpDir, 'wave.csv');
    writeWaveCsv(wave, 12);                               // 12 秒的数据按 0.25 倍速播放，约 48 秒播完
    const source = { kind: 'csv_file', path: wave, block_samples: 640, file_speed: 0.25 };
    const runState = (st) => (st.running && !st.finished ? (st.paused ? '已暂停' : '运行中') : '未运行');
    const both = async () => {
      const [b, br] = await Promise.all([real('/api/state'), real('/api/branch/state')]);
      return `总线侧${runState(b)}、分路侧${runState(br)}`;
    };
    /* 用服务端此刻的真实状态调用 togglePause() / stopEngine()。
     * staleBranch：总线侧视图下，让页面手里的分路侧状态停留在这份旧状态上（模拟“页面还没来得及刷新”）。 */
    async function live(fn, { staleBranch = null } = {}) {
      if (S.side === 'bus') { S.state = await real('/api/state'); S.branchFullState = staleBranch || await real('/api/branch/state'); }
      else { S.state = await real('/api/branch/state'); S.branchFullState = null; }
      const mark = calls.length;
      while ($('toast').firstChild) $('toast').firstChild.remove();
      await window.eval(fn + '()');
      const toasts = Array.from($('toast').children);
      const posts = calls.slice(mark).filter((c) => c.method === 'POST' && /\/engine\/(pause|resume|stop)$/.test(c.url)).map((c) => c.url);
      return { posts, text: toasts.map((t) => t.textContent).join(' | '), err: toasts.some((t) => t.classList.contains('err')), now: await both() };
    }
    const showLive = (x) => `${show(x)}；服务端：${x.now}`;

    const sb = await real('/api/engine/start', 'POST', { ...source, with_branch: false });
    const sr = await real('/api/branch/engine/start', 'POST', { ...source, file_speed_follow: false });
    let started = '';
    for (let i = 0; i < 40 && started !== '总线侧运行中、分路侧运行中'; i++) { await sleep(250); started = await both(); }
    check('B2 实测准备：两侧都在播放录波文件', sb.ok && sr.ok && started === '总线侧运行中、分路侧运行中', started);

    r = await live('togglePause');
    check('B2 实测 总线侧视图、两侧都在播放：点「暂停」两侧都暂停', r.posts.join() === '/api/engine/pause,/api/branch/engine/pause'
      && r.text === '总线侧已暂停，分路侧已暂停' && !r.err && r.now === '总线侧已暂停、分路侧已暂停', showLive(r));
    r = await live('togglePause');
    check('B2 实测 总线侧视图、两侧都已暂停：点「恢复」两侧都恢复', r.posts.join() === '/api/engine/resume,/api/branch/engine/resume'
      && r.text === '总线侧已恢复，分路侧已恢复' && !r.err && r.now === '总线侧运行中、分路侧运行中', showLive(r));

    await window.eval("setSide('branch', { silent: true })");
    r = await live('togglePause');
    check('B2 实测 分路侧视图：点「暂停」只暂停分路侧，提示说分路侧', r.posts.join() === '/api/branch/engine/pause'
      && r.text === '分路侧已暂停' && !r.err && r.now === '总线侧运行中、分路侧已暂停', showLive(r));
    r = await live('togglePause');
    check('B2 实测 分路侧视图：点「恢复」只恢复分路侧', r.posts.join() === '/api/branch/engine/resume'
      && r.text === '分路侧已恢复' && !r.err && r.now === '总线侧运行中、分路侧运行中', showLive(r));
    const branchWhileRunning = await real('/api/branch/state');
    r = await live('stopEngine');
    check('B2 实测 分路侧视图：点「停止」只停分路侧，总线侧继续播放', r.posts.join() === '/api/branch/engine/stop'
      && r.text === '分路侧已停止' && !r.err && r.now === '总线侧运行中、分路侧未运行', showLive(r));

    await window.eval("setSide('bus', { silent: true })");
    r = await live('togglePause', { staleBranch: branchWhileRunning });
    check('B2 实测 总线侧视图、页面上的分路侧状态已过时（服务端已停）：分路侧如实报失败', r.posts.join() === '/api/engine/pause,/api/branch/engine/pause'
      && r.text === '总线侧已暂停，分路侧暂停失败：数据源未在运行' && r.err && r.now === '总线侧已暂停、分路侧未运行', showLive(r));
    r = await live('stopEngine');
    check('B2 实测 总线侧视图、只有总线侧在运行：点「停止」只操作总线侧', r.posts.join() === '/api/engine/stop'
      && r.text === '总线侧已停止' && !r.err && r.now === '总线侧未运行、分路侧未运行', showLive(r));
  } finally {
    await real('/api/branch/engine/stop', 'POST').catch(() => {});
    await real('/api/engine/stop', 'POST').catch(() => {});
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }

  check('页面没有未捕获的脚本错误', errors.length === 0, errors.slice(0, 3).join(' | '));
  console.log(`\n${fail === 0 ? 'PASS' : 'FAIL'}：通过 ${pass} 项，失败 ${fail} 项${fail ? '（' + fails.join('；') + '）' : ''}`);
  dom.window.close();
  process.exit(fail === 0 ? 0 : 1);
}

main().catch((e) => { console.error('脚本异常：', e && e.stack || e); process.exit(2); });
