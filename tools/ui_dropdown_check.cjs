#!/usr/bin/env node
/* Web 界面下拉框可用性端到端检查（jsdom 驱动真实 index.html + app.js，打真实服务端）。
 *
 * 检查什么：
 *   A  数据源下拉框 #src-kind 的 4 种输入方式能否逐个选中 → 无关字段是否联动禁用 →
 *      填字段 → 点「启动数据源」→ 服务端是否真的以该 kind 跑起来（csv_file 允许读完即结束）
 *   A2 TCP 帧格式下拉框 #src-frame：选 binary 才放开 struct 两项，且载荷不带无关/空字段
 *   A3 脏值保护：用户选完/输到一半时，实时推送（0.2s 一次）不得把表单改回服务端配置
 *   B  口径下拉框 #cfg-uin/#cfg-apparent/#cfg-reactive：选中 → 点「保存配置（热更新）」
 *      → PUT /api/config（深合并）→ 服务端回显是否生效；空数字框不得导致 400
 *   C  频谱下拉框 #sp-chan/#sp-scale/#sp-limit：change 是否真的触发重绘
 *
 * 用法：node tools/ui_dropdown_check.cjs [baseUrl]
 *   依赖：node ≥18、jsdom（npm install jsdom，或用 JSDOM_DIR 指定安装目录）
 *   会自动在 9000 端口拉起 tools/tcp_feeder.py 扮演采集装置（若该端口空闲），结束时清理。
 * 退出码：0 全通过；1 有失败项；2 脚本自身异常。
 */
const fs = require('fs');
const path = require('path');
const net = require('net');
const { spawn } = require('child_process');
const { JSDOM } = require(path.join(process.env.JSDOM_DIR || '/tmp/uitest', 'node_modules/jsdom'));

const BASE = process.argv[2] || 'http://127.0.0.1:8000';
const ROOT = path.resolve(__dirname, '..');
const PY = path.join(ROOT, '.venv/bin/python');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let pass = 0, fail = 0;
const fails = [];
function check(name, ok, detail = '') {
  if (ok) { pass++; console.log(`  ✓ ${name}${detail ? '　' + detail : ''}`); }
  else { fail++; fails.push(name); console.log(`  ✗ ${name}　${detail}`); }
}
function portFree(port) {
  return new Promise((res) => {
    const s = net.createServer();
    s.once('error', () => res(false));
    s.once('listening', () => s.close(() => res(true)));
    s.listen(port, '127.0.0.1');
  });
}

async function main() {
  // ---- 采集侧：9000 端口空闲就自己拉一个 TCP 喂数器，让 tcp 用例真能跑起来 ----
  let feeder = null;
  if (await portFree(9000)) {
    feeder = spawn(fs.existsSync(PY) ? PY : 'python3',
      [path.join(ROOT, 'tools/tcp_feeder.py'), '--port', '9000', '--mode', 'text_csv',
       '--header', '--rate', '4', '--duration', '120'],
      { cwd: ROOT, stdio: 'ignore' });
    for (let i = 0; i < 40 && !(await (async () => !(await portFree(9000)))()); i++) await sleep(250);
    console.log('● 已拉起 TCP 喂数器（9000，text_csv）扮演采集装置');
  } else {
    console.log('● 9000 端口已有服务，直接复用为 TCP 采集侧');
  }

  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const calls = [];
  let drawCalls = 0;

  const dom = new JSDOM(html, {
    url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true,
    beforeParse(window) {
      window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, {
        get: (t, p) => (p === 'measureText' ? () => ({ width: 8 })
          : p === 'createLinearGradient' ? () => ({ addColorStop() {} })
            : () => { drawCalls++; }),
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
  // const 声明不会进入后续 eval 可见的作用域（实测），用闭包把内部状态导出来供断言读取
  window.eval(js + '\n;window.__S = () => S;');
  const Sobj = () => window.__S();
  const clrDirty = () => { const st0 = Sobj(); st0.formDirty = false; st0.srcDirty = false; st0.cfgDirty = false; };
  if (typeof window.init === 'function') window.init();
  await sleep(1800);

  const $ = (id) => document.getElementById(id);
  const setSel = async (id, value) => {
    const el = $(id); el.value = value;
    el.dispatchEvent(new window.Event('change', { bubbles: true }));
    await sleep(150);
    return el.value;
  };
  const bodies = (urlPart, method) => calls
    .filter((c) => c.url.includes(urlPart) && (!method || c.method === method) && c.body)
    .map((c) => JSON.parse(c.body));
  const disabled = (id) => !!$(id).disabled;

  // 像真实用户一样先点导航进入「数据源与控制」子界面（否则该页的渲染函数不会执行）
  document.querySelector('.navitem[data-view="source"]').dispatchEvent(new window.Event('click', { bubbles: true }));
  await sleep(600);

  console.log('\n=== A. 数据源输入方式下拉框 #src-kind（对真实服务端逐个实测）===');
  const opts = [...$('src-kind').options].map((o) => o.value);
  check('有 4 个选项且值与后端 SOURCE_KINDS 一致',
    JSON.stringify(opts) === JSON.stringify(['csv_file', 'csv_tail', 'tcp', 'simulator']), JSON.stringify(opts));
  check('进入该子界面后表单已从服务端配置回填（PT/fs 不为空）',
    $('cfg-pt').value !== '' && $('cfg-fs').value !== '' && $('src-host').value !== '',
    `cfg-pt=${$('cfg-pt').value} cfg-fs=${$('cfg-fs').value} src-host=${$('src-host').value}`);
  check('选中源后给出该源的填写说明（#src-hint）', ($('src-hint').textContent || '').length > 20,
    ($('src-hint').textContent || '').slice(0, 40) + '…');

  const cases = [
    { kind: 'csv_file', fill: { 'src-path': 'data/sample_6400hz.csv' }, off: ['src-host', 'src-port', 'src-frame', 'src-fmt', 'src-speed', 'src-tailend'], offline: true },
    { kind: 'csv_tail', fill: { 'src-path': 'data/sample_6400hz.csv' }, off: ['src-host', 'src-port', 'src-frame', 'src-fmt', 'src-speed'] },
    { kind: 'tcp', fill: { 'src-host': '127.0.0.1', 'src-port': '9000' }, off: ['src-path', 'src-speed', 'src-tailend'] },
    { kind: 'simulator', fill: { 'src-speed': '4' }, off: ['src-path', 'src-host', 'src-port', 'src-frame', 'src-tailend'] },
  ];
  for (const c of cases) {
    clrDirty();                                                     // 每个用例从干净状态开始
    const got = await setSel('src-kind', c.kind);
    check(`${c.kind}：可选中`, got === c.kind, `value=${got}`);
    const stillOn = c.off.filter((id) => !disabled(id));
    check(`${c.kind}：无关字段已联动禁用`, stillOn.length === 0, stillOn.length ? '仍可编辑：' + stillOn.join('/') : '');
    check(`${c.kind}：说明文案已切换`, ($('src-hint').textContent || '').includes(c.kind === 'tcp' ? 'TCP' : c.kind === 'simulator' ? '模拟器' : c.kind === 'csv_tail' ? '目录' : '离线'),
      ($('src-hint').textContent || '').slice(0, 24) + '…');
    for (const [id, v] of Object.entries(c.fill)) { $(id).value = v; }
    calls.length = 0;
    $('btn-start2').dispatchEvent(new window.Event('click', { bubbles: true }));
    await sleep(2500);
    const body = bodies('/api/engine/start', 'POST').pop();
    check(`${c.kind}：POST 载荷 kind 正确`, body && body.kind === c.kind, body ? 'kind=' + body.kind : '未捕获 POST');
    const irrelevant = body ? Object.keys(body).filter((k) => (c.kind === 'simulator' && ['path', 'host', 'port', 'frame'].includes(k))
      || (c.kind === 'tcp' && ['path', 'sim_speed'].includes(k))
      || (c.kind !== 'tcp' && ['frame', 'struct_fmt', 'struct_fields'].includes(k))
      || (c.kind !== 'csv_tail' && ['tail_from_end', 'watch_dir_newest'].includes(k))) : [];
    check(`${c.kind}：载荷只含该源相关字段`, irrelevant.length === 0, irrelevant.join(',') || JSON.stringify(body));
    const empties = body ? Object.keys(body).filter((k) => body[k] === '' || body[k] === null || body[k] === 0) : [];
    check(`${c.kind}：载荷无空值/0 覆盖服务端配置`, empties.length === 0, empties.join(','));
    const st = await (await fetch(BASE + '/api/state')).json();
    const runKind = ((st.source || {}).kind) || ((st.engine || {}).source_kind);
    const alive = c.offline ? (st.running === true || st.finished === true) : st.running === true;
    check(`${c.kind}：服务端确实以该源运行`, alive && runKind === c.kind,
      `running=${st.running} finished=${st.finished} source.kind=${runKind} samples_in=${(st.engine || {}).samples_in} err=${st.error || '—'}`);
  }

  console.log('\n=== A2. TCP 帧格式下拉框 #src-frame 与 binary 专属字段 ===');
  clrDirty();
  await setSel('src-kind', 'tcp');
  check('frame=text_csv 时 struct 两项禁用', disabled('src-fmt') && disabled('src-fields'));
  const f1 = await setSel('src-frame', 'binary');
  check('可选中 binary', f1 === 'binary');
  check('选 binary 后 struct 格式/字段顺序放开', !disabled('src-fmt') && !disabled('src-fields'));
  $('src-fmt').value = '>7f'; $('src-fields').value = 't,ua,ia,ub,ib,uc,ic';
  calls.length = 0;
  $('btn-start2').dispatchEvent(new window.Event('click', { bubbles: true }));
  await sleep(1500);
  let b = bodies('/api/engine/start', 'POST').pop() || {};
  check('binary：struct_fmt/struct_fields 进入载荷',
    b.frame === 'binary' && b.struct_fmt === '>7f' && b.struct_fields === 't,ua,ia,ub,ib,uc,ic', JSON.stringify(b));
  const f2 = await setSel('src-frame', 'text_csv');
  check('可切回 text_csv 且 struct 两项重新禁用', f2 === 'text_csv' && disabled('src-fmt') && disabled('src-fields'));
  calls.length = 0;
  $('btn-start2').dispatchEvent(new window.Event('click', { bubbles: true }));
  await sleep(1200);
  b = bodies('/api/engine/start', 'POST').pop() || {};
  check('text_csv：载荷不带 struct_fmt/struct_fields（避免覆盖默认帧格式）',
    b.struct_fmt === undefined && b.struct_fields === undefined, JSON.stringify(b));

  console.log('\n=== A3. 脏值保护：实时推送不得覆盖用户正在编辑的表单 ===');
  clrDirty();
  await setSel('src-kind', 'csv_tail');
  $('src-path').value = 'data/我正在输入的一半路径';
  $('src-path').dispatchEvent(new window.Event('input', { bubbles: true }));
  const stNow = await (await fetch(BASE + '/api/state')).json();
  const push = JSON.stringify({ type: 'state', data: Object.assign({}, stNow, { config: Object.assign({}, stNow.config, { source: Object.assign({}, stNow.config.source, { kind: 'simulator', path: '' }) }) }) });
  const s0 = Sobj();
  check('页面已建立 WS 连接（脏值保护的前提）', !!(s0 && s0.ws && typeof s0.ws.onmessage === 'function'));
  if (s0 && s0.ws && typeof s0.ws.onmessage === 'function') s0.ws.onmessage({ data: push });
  await sleep(400);
  check('推送后 #src-kind 仍是用户选的 csv_tail（未被改回 simulator）', $('src-kind').value === 'csv_tail', 'value=' + $('src-kind').value);
  check('推送后正在输入的路径未被清空', $('src-path').value === 'data/我正在输入的一半路径', $('src-path').value);
  check('给出「已暂停自动回填」的明确提示', ($('src-formnote').textContent || '').includes('未保存'),
    ($('src-formnote').textContent || '').slice(0, 30));
  $('btn-refresh').dispatchEvent(new window.Event('click', { bubbles: true }));
  await sleep(900);
  check('点「刷新」后丢弃修改并重新回填服务端配置',
    Sobj().formDirty === false && ($('src-formnote').textContent || '') === '',
    `formDirty=${Sobj().formDirty}，src-kind=${$('src-kind').value}`);

  console.log('\n=== B. 口径下拉框（PUT /api/config 深合并后服务端是否回显生效）===');
  for (const c of [
    { id: 'cfg-uin', values: ['line', 'phase'], probe: (o) => o.transform.voltage_input },
    { id: 'cfg-apparent', values: ['vector', 'arithmetic'], probe: (o) => o.power.apparent },
    { id: 'cfg-reactive', values: ['quadrature', 'harmonic_sum'], probe: (o) => o.power.reactive },
  ]) {
    for (const v of c.values) {
      const got = await setSel(c.id, v);
      check(`#${c.id} 可选中 ${v}`, got === v, 'value=' + got);
      calls.length = 0;
      $('btn-savecfg').dispatchEvent(new window.Event('click', { bubbles: true }));
      await sleep(1000);
      const put = calls.find((x) => x.method === 'PUT' && x.url.includes('/api/config'));
      const cfg = await (await fetch(BASE + '/api/config')).json();
      check(`#${c.id}=${v}：PUT 已发出且未被 400 拒`, !!put && put.status === 200, put ? 'HTTP ' + put.status : '未捕获 PUT');
      check(`#${c.id}=${v}：服务端配置已生效`, c.probe(cfg) === v, `回显 ${c.probe(cfg)}`);
      const sent = put ? JSON.parse(put.body) : {};
      const zeros = JSON.stringify(sent).match(/":0[,}]/g);
      check(`#${c.id}=${v}：载荷不含 0 值（空输入框应跳过而非送 0）`, !zeros, zeros ? JSON.stringify(sent).slice(0, 120) : '');
    }
  }

  console.log('\n=== C. 频谱面板下拉框（change 是否真的触发重绘）===');
  document.querySelector('.navitem[data-view="spectrum"]').dispatchEvent(new window.Event('click', { bubbles: true }));
  await sleep(500);
  for (const [id, values] of [['sp-chan', ['Ub', 'Ia', 'Ua']], ['sp-scale', ['db', 'lin']], ['sp-limit', ['500', '2600', '0']]]) {
    for (const v of values) {
      const before = drawCalls;
      const got = await setSel(id, v);
      check(`#${id} 可选中 ${v} 且触发重绘`, got === v && drawCalls > before, `value=${got}，绘制 ${drawCalls - before} 次`);
    }
  }

  // 收尾：把预览恢复到 simulator 源
  try { await fetch(BASE + '/api/engine/stop', { method: 'POST' }); } catch (e) { /* 忽略 */ }
  await sleep(300);
  try {
    await fetch(BASE + '/api/engine/start', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind: 'simulator', sim_speed: 1 }),
    });
  } catch (e) { /* 忽略 */ }

  console.log(`\n=== 结果：PASS ${pass} / FAIL ${fail} ===`);
  if (fail) console.log('失败项：\n  - ' + fails.join('\n  - '));
  if (feeder) { try { feeder.kill('SIGTERM'); } catch (e) { /* 忽略 */ } }
  window.close();
  process.exit(fail ? 1 : 0);
}

main().catch((e) => { console.error('检查脚本自身异常：', e); process.exit(2); });
