#!/usr/bin/env node
/* v0.16 界面检查：数据源与控制页左右两列布局 / 分路侧 4 种输入方式 / 曲线分线显示开关 / 总览分路侧曲线状态栏。
 * jsdom 驱动真实 index.html + app.js，打真实服务端（需先 serve 在 8000，data/sample_6400hz.csv、data/nilm_steps.csv 存在）。
 *
 *   L1 布局：同类配置左右同行（4 行 × 2 列）；未启用分路侧只显示左列；启用后右列出现
 *   L2 分路侧输入方式 4 种，字段启用/禁用联动与总线侧同构；保存后 /api/branch/config 写入 kind/host/port 等
 *   L3 分路侧 tcp/模拟器 与总线侧离线文件 同时启动；分路侧单独启动/停止按钮
 *   L4 曲线分线显示开关：取消 Ub → 图上不画、PUT /api/config output.series_hidden 持久化；重载页面仍隐藏
 *   L5 总览分路侧曲线标题栏：有「保存曲线」勾选 + 点数/时长文本（与总线侧一致），勾选写分路侧配置
 *
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r16_check.cjs [baseUrl]
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
  try { window.localStorage.removeItem('elec_side'); } catch (e) {}
  window.eval(js + '\n;window.__S = () => S;');
  if (typeof window.init === 'function') window.init();
  return dom;
}

async function main() {
  const api = async (u, o) => (await fetch(BASE + u, o)).json();
  const put = (u, body) => api(u, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  await api('/api/engine/stop', { method: 'POST' });
  await api('/api/branch/engine/stop', { method: 'POST' });
  await put('/api/config', { branch: { enabled: false, common_window: false, common_start: '' }, output: { series_hidden: { 'ov-u': [], 'ov-p': [] } } });
  await put('/api/branch/config', { source: { kind: 'simulator', path: '' } });

  const calls = [];
  const dom = makeDom(calls);
  const { window } = dom, { document } = window;
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(700); };
  const visible = (el) => !!el && window.getComputedStyle(el).display !== 'none';

  console.log('L1 布局：左列总线侧 / 右列分路侧，同类配置同行');
  await nav('source');
  const grid = $('srcgrid');
  const busCols = [...grid.querySelectorAll(':scope > .col-bus')], brCols = [...grid.querySelectorAll(':scope > .col-br')];
  check('网格 4 行 × 2 列（总线侧 4 块 / 分路侧 4 块，交替排列）', busCols.length === 4 && brCols.length === 4 &&
    [...grid.children].filter(el => !el.classList.contains('col-full')).every((el, i) => el.classList.contains(i % 2 === 0 ? 'col-bus' : 'col-br')), `${busCols.length}/${brCols.length}`);
  const titles = (cols) => cols.map(c => c.querySelector('h3').textContent.replace(/\s+/g, ''));
  check('同类配置左右同行：数据源 / 量纲与口径 / 列映射 / 数据源状态', titles(busCols).every((t, i) => t.replace('总线侧', '') .split(' ')[0].slice(0, 4) === titles(brCols)[i].replace('分路侧', '').split(' ')[0].slice(0, 4)), titles(busCols).join(',') + ' | ' + titles(brCols).join(','));
  // jsdom 不加载外部样式表：右列隐藏由 .srcgrid.no-branch .col-br{display:none} 完成，这里查类名 + 样式规则文本
  const css = fs.readFileSync(path.join(ROOT, 'app/static/style.css'), 'utf8');
  check('未启用分路侧：右列隐藏、只显示左列', grid.classList.contains('no-branch') && /\.srcgrid\.no-branch \.col-br\{display:none\}/.test(css) && !visible($('br-link-fields')));
  $('br-enabled').checked = true; change($('br-enabled')); await sleep(600);
  check('启用分路侧：右列出现、联动字段出现', !grid.classList.contains('no-branch') && visible($('br-link-fields')));
  check('右列有与总线侧同样的 4 种输入方式', [...$('br-kind').options].map(o => o.value).join(',') === [...$('src-kind').options].map(o => o.value).join(','), [...$('br-kind').options].map(o => o.value).join(','));

  console.log('L2 分路侧输入方式与总线侧同构');
  const pairs = ['path', 'host', 'port', 'frame', 'fmt', 'fields', 'customtime', 'utc', 'customstart', 'playmode', 'playvalue', 'tailend', 'newest', 'block', 'speed', 'file-speed'];
  check('分路侧每个数据源字段都存在（br-*）', pairs.every(n => !!$('br-' + n)), pairs.filter(n => !$('br-' + n)).join(','));
  const stateOf = (pre) => pairs.map(n => ($(pre + n).disabled ? '0' : '1')).join('');
  const same = [];
  for (const k of ['csv_file', 'csv_tail', 'tcp', 'simulator']) {
    $('src-kind').value = k; change($('src-kind')); $('br-kind').value = k; change($('br-kind')); await sleep(50);
    if (k === 'tcp') { $('src-frame').value = 'binary'; change($('src-frame')); $('br-frame').value = 'binary'; change($('br-frame')); }
    same.push(k + ':' + (stateOf('src-') === stateOf('br-')));
  }
  check('4 种输入方式下字段启用/禁用状态两侧一致（csv_file 时分路侧倍速随总线侧→禁用，属预期差异）', same.filter(x => /true$/.test(x)).length >= 3, same.join(' '));
  // 配置并保存 tcp
  $('src-kind').value = 'csv_file'; change($('src-kind'));
  $('br-kind').value = 'tcp'; change($('br-kind'));
  $('br-host').value = '10.1.2.3'; change($('br-host')); $('br-port').value = '9123'; change($('br-port'));
  $('br-frame').value = 'binary'; change($('br-frame')); $('br-fmt').value = '<7d'; change($('br-fmt'));
  click($('btn-br-save')); await sleep(900);
  let bcfg = await api('/api/branch/config');
  check('保存分路侧 tcp 配置 → kind/host/port/frame/struct_fmt 写入 /api/branch/config', bcfg.source.kind === 'tcp' && bcfg.source.host === '10.1.2.3' && bcfg.source.port === 9123 && bcfg.source.frame === 'binary' && bcfg.source.struct_fmt === '<7d', JSON.stringify([bcfg.source.kind, bcfg.source.host, bcfg.source.port, bcfg.source.frame]));
  check('联动提示：两侧不都是离线文件时显示', visible($('br-mode-note')));
  // csv_tail
  $('br-kind').value = 'csv_tail'; change($('br-kind')); $('br-path').value = 'data'; change($('br-path'));
  $('br-tailend').checked = true; change($('br-tailend')); $('br-newest').checked = true; change($('br-newest'));
  click($('btn-br-save')); await sleep(900);
  bcfg = await api('/api/branch/config');
  check('保存分路侧 csv_tail 配置 → tail_from_end / watch_dir_newest', bcfg.source.kind === 'csv_tail' && bcfg.source.tail_from_end === true && bcfg.source.watch_dir_newest === true && bcfg.source.path.endsWith('data'));
  // csv_file + 播放起点
  $('br-kind').value = 'csv_file'; change($('br-kind')); $('br-path').value = 'data/nilm_steps.csv'; change($('br-path'));
  $('br-playmode').value = 'seconds'; change($('br-playmode')); $('br-playvalue').value = '2'; change($('br-playvalue'));
  click($('btn-br-save')); await sleep(900);
  bcfg = await api('/api/branch/config');
  check('保存分路侧 csv_file + 播放起点（seconds=2）', bcfg.source.kind === 'csv_file' && bcfg.source.play_start_mode === 'seconds' && bcfg.source.play_start_value === '2', JSON.stringify([bcfg.source.play_start_mode, bcfg.source.play_start_value]));
  check('两侧都是离线文件：联动提示隐藏、分路侧倍速禁用并提示随总线侧', !visible($('br-mode-note')) && $('br-file-speed').disabled && visible($('br-file-speed-note')));
  // 总线侧播放起点也应随「启动」发送（修复：旧版只在 csv_tail 下送 play_start_mode）
  $('src-path').value = 'data/sample_6400hz.csv'; $('src-playmode').value = 'seconds'; change($('src-playmode')); $('src-playvalue').value = '1'; change($('src-playvalue'));
  $('src-file-speed').value = '1'; change($('src-file-speed'));     // 1× 真实速率：检查期间两侧都还在播放
  click($('btn-start2')); await sleep(2500);
  const st = await api('/api/state'), bst = await api('/api/branch/state');
  check('总线侧按「跳过开头 1 s」启动（播放起点随启动载荷发送）', st.source && st.source.play_start_mode === 'seconds' && st.source.play_seek && st.source.play_seek.skipped_rows === 6400, JSON.stringify(st.source && st.source.play_seek));
  check('分路侧按「跳过开头 2 s」同时启动', bst.source && bst.source.play_start_mode === 'seconds' && bst.source.play_seek && bst.source.play_seek.skipped_rows === 12800, JSON.stringify(bst.source && bst.source.play_seek));
  check('分路侧数据源状态栏与总线侧同格式（运行状态/数据源/已摄入/播放起点）', /运行状态/.test($('br-status').textContent) && /数据源/.test($('br-status').textContent) && /已摄入/.test($('br-status').textContent) && /播放起点/.test($('br-status').textContent), $('br-status').textContent.slice(0, 80));
  await api('/api/engine/stop', { method: 'POST' }); await sleep(500);

  console.log('L3 分路侧模拟器 + 总线侧离线文件同时启动；分路侧单独启动/停止');
  $('br-kind').value = 'simulator'; change($('br-kind')); click($('btn-br-save')); await sleep(900);
  $('src-playmode').value = 'begin'; change($('src-playmode')); $('src-file-speed').value = '1'; change($('src-file-speed'));
  click($('btn-start2')); await sleep(1800);
  const st3 = await api('/api/state'), bst3 = await api('/api/branch/state');
  check('总线侧离线文件 + 分路侧模拟器 同时运行', st3.running && bst3.running && bst3.engine.source_kind === 'simulator', `${st3.running}/${bst3.running} ${bst3.engine.source_kind}`);
  click($('btn-stop2')); await sleep(600);
  check('总线侧停止 → 分路侧也停止', !(await api('/api/state')).running && !(await api('/api/branch/state')).running);
  click($('btn-br-start')); await sleep(1200);
  check('「单独启动分路侧」只启动分路侧', (await api('/api/branch/state')).running && !(await api('/api/state')).running);
  click($('btn-br-stop')); await sleep(600);
  check('「停止分路侧」', !(await api('/api/branch/state')).running);

  console.log('L4 曲线分线显示开关（可选、可保存）');
  // 回到离线文件 + 不限速播完，让总览有多条曲线
  $('br-kind').value = 'csv_file'; change($('br-kind')); $('br-path').value = 'data/nilm_steps.csv'; change($('br-path'));
  $('br-playmode').value = 'begin'; change($('br-playmode')); click($('btn-br-save')); await sleep(800);
  $('src-file-speed').value = '0'; change($('src-file-speed')); click($('btn-start2'));
  for (let i = 0; i < 40; i++) { await sleep(500); const s = await api('/api/state'); const b = await api('/api/branch/state'); if (!s.running && !b.running) break; }
  await nav('overview'); await sleep(2500);
  const legend = document.querySelector('.serlegend[data-chart="ov-u"]');
  check('多条曲线的图下方有图例勾选（Ua/Ub/Uc）', !!legend && legend.querySelectorAll('input.ser-vis').length === 3, legend ? legend.textContent : '无');
  const cbUb = legend && legend.querySelector('input.ser-vis[data-name="Ub"]');
  const before = ($('ov-u').__chart || {}).pts || [];
  cbUb.checked = false; change(cbUb); await sleep(800);
  const after = ($('ov-u').__chart || {}).pts || [];
  const putSer = calls.filter(c => c.method === 'PUT' && c.url === '/api/config' && /series_hidden/.test(c.body || ''));
  check('取消 Ub → 图上只剩 Ua/Uc', before.length === 3 && after.length === 2 && after.every(p => p.name !== 'Ub'), `${before.map(p => p.name)} → ${after.map(p => p.name)}`);
  check('勾选状态 PUT /api/config output.series_hidden', putSer.length >= 1 && /"ov-u":\["Ub"\]/.test(putSer[putSer.length - 1].body), putSer.length ? putSer[putSer.length - 1].body : '无');
  const cfgH = await api('/api/config');
  check('服务端配置已保存 series_hidden["ov-u"]=["Ub"]', JSON.stringify((cfgH.output.series_hidden || {})['ov-u']) === '["Ub"]', JSON.stringify(cfgH.output.series_hidden));
  check('图例中 Ub 标为 off', legend.querySelector('label.off') && /Ub/.test(legend.querySelector('label.off').textContent));
  // 重新加载页面：仍隐藏
  const dom2 = makeDom([]); await sleep(1500);
  const d2 = dom2.window.document; const $2 = (id) => d2.getElementById(id);
  dom2.window.document.querySelector('.navitem[data-view="overview"]').dispatchEvent(new dom2.window.Event('click', { bubbles: true })); await sleep(2500);
  const pts2 = ($2('ov-u').__chart || {}).pts || [];
  const leg2 = d2.querySelector('.serlegend[data-chart="ov-u"]');
  check('重新打开页面：Ub 仍隐藏（配置持久化）', pts2.length === 2 && pts2.every(p => p.name !== 'Ub') && leg2 && !leg2.querySelector('input.ser-vis[data-name="Ub"]').checked, pts2.map(p => p.name).join(','));
  // 恢复（图例在隐藏后已重建，需重新取元素）
  const cbUb2 = document.querySelector('.serlegend[data-chart="ov-u"] input.ser-vis[data-name="Ub"]');
  cbUb2.checked = true; change(cbUb2); await sleep(800);
  const cfgH2 = await api('/api/config');
  check('重新勾选 Ub → 配置中该图的隐藏列表清空、图上 3 条', !(cfgH2.output.series_hidden || {})['ov-u'] && (($('ov-u').__chart || {}).pts || []).length === 3);
  check('单条曲线的图不出现图例勾选（频率趋势）', !document.querySelector('.serlegend[data-chart="f-trend"]'));

  console.log('L5 总览分路侧曲线状态栏与总线侧一致');
  const brHdr = $('ov-u-br').parentNode.querySelector('h3');
  const busHdr = $('ov-u').parentNode.querySelector('h3');
  check('分路侧曲线标题栏有「保存曲线」勾选与点数文本（结构与总线侧一致）', !!brHdr.querySelector('input.curve-save[data-side="branch"]') && !!brHdr.querySelector('.curvespan[data-side="branch"]') && !!busHdr.querySelector('input.curve-save') && !!busHdr.querySelector('.curvespan'));
  const spanBr = brHdr.querySelector('.curvespan').textContent, spanBus = busHdr.querySelector('.curvespan').textContent;
  check('分路侧点数/时长文本已填写（格式同总线侧「最近 … · N 点」）', /点/.test(spanBr) && /点/.test(spanBus) && /最近/.test(spanBr), `${spanBus} | ${spanBr}`);
  const cbBr = brHdr.querySelector('input.curve-save[data-side="branch"]');
  const was = cbBr.checked;
  cbBr.checked = !was; change(cbBr); await sleep(800);
  const bcfg5 = await api('/api/branch/config'), cfg5 = await api('/api/config');
  check('分路侧「保存曲线」勾选写分路侧配置 output.curve_save.voltage，总线侧不受影响', bcfg5.output.curve_save.voltage === !was && cfg5.output.curve_save.voltage === true, `br=${bcfg5.output.curve_save.voltage} bus=${cfg5.output.curve_save.voltage}`);
  cbBr.checked = was; change(cbBr); await sleep(600);
  check('分路侧状态文本与总线侧口径一致（已播放完毕）', /已播放完毕/.test(brHdr.querySelector('.ov-br-note').textContent) && /已播放完毕/.test($('ov-br-hint').textContent), brHdr.querySelector('.ov-br-note').textContent);

  // 还原
  await put('/api/config', { branch: { enabled: false } });
  await put('/api/branch/config', { source: { play_start_mode: 'begin', play_start_value: '' } });
  console.log(`\n结果：${pass} 通过，${fail} 失败${fail ? '：' + fails.join('；') : ''}`);
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
