#!/usr/bin/env node
/* 第 7 轮界面功能端到端检查（jsdom 驱动真实 index.html + app.js，打真实服务端）。
 *
 * 检查什么：
 *   E1 实时落盘：导出页有开关/目录/应用按钮；应用 → PUT /api/config output.realtime_save；
 *      跑一遍离线文件后 GET /api/realtime 列出 <曲线>_<日期>.csv 且文件行数 == 本次写入行数 + 表头；
 *      取消某曲线「保存曲线」勾选后该曲线不再落盘；关闭开关后不再新增文件
 *   E2 播放起点：csv_file 下「播放起点」下拉框可用、取值框只在非 begin 时放开，其它源下禁用；
 *      5 种模式逐个选中 → 启动载荷带 play_start_mode/value → 服务端摄入样本数符合预期
 *      （row/seconds 精确、percent 近似、time 精确、超范围 → 引擎错误可见）；非法取值 → 400
 *   E3 曲线悬停取值：每个 drawLine 画过的 canvas 绑定 mousemove；派发 mousemove 后
 *      cv.__hoverInfo 给出最近点的 x 文本与各曲线数值，且与 S.histCache 中的真实数据一致；
 *      mouseleave 清除；实时推送 render() 后悬停仍在（不被刷新抹掉）
 *
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r7_check.cjs [baseUrl]
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

function makeCsv(seconds = 4) {
  // 无表头、0/00/00 当天时刻写法、6400Hz；起始 00:12:40 → t=760s
  const fp = path.join(os.tmpdir(), 'ui_r7_play.csv');
  const fs6400 = 6400, n = fs6400 * seconds, lines = [];
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
  return { fp, rows: n };
}

async function main() {
  const { fp: csvPath, rows: CSV_ROWS } = makeCsv(4);
  const rtDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ui_r7_rt_'));
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
  const clrDirty = () => { const s = Sobj(); s.formDirty = false; s.srcDirty = false; s.cfgDirty = false; s.rtDirty = false; };
  if (typeof window.init === 'function') window.init();
  await sleep(1800);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(500); };
  const bodies = (urlPart, method) => calls.filter((c) => c.url.includes(urlPart) && (!method || c.method === method) && c.body).map((c) => JSON.parse(c.body));
  const getJson = async (u) => (await fetch(BASE + u)).json();
  const putCfg = async (b) => fetch(BASE + '/api/config', { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(b) });
  const allSave = { voltage: true, current: true, power: true, power_factor: true, fundamental: true, harmonic: true };
  const waitFinished = async (ms = 6000) => {
    const t0 = Date.now(); let st;
    while (Date.now() - t0 < ms) { st = await getJson('/api/state'); if (st.finished || st.error) break; await sleep(200); }
    await sleep(600);          // finished 置位后运行线程还会做一次 flush_all（收尾强算 + 落盘），等它写完再数行
    return await getJson('/api/state');
  };
  const csvLines = (p) => fs.readFileSync(p, 'utf8').split('\n').filter((l) => l.trim()).length;

  // 起点：先停掉预览里常驻的模拟器（否则它会往测试目录里写当天日期的文件），再把落盘目录指到临时目录
  await fetch(BASE + '/api/engine/stop', { method: 'POST' });
  await sleep(300);
  await putCfg({ output: { curve_save: allSave, realtime_save: true, realtime_dir: rtDir }, source: { play_start_mode: 'begin', play_start_value: '' } });
  Sobj().state = await getJson('/api/state');

  console.log('\n=== E1. 实时落盘 ===');
  await nav('export'); await sleep(400);
  check('导出页有「实时落盘」开关/目录/应用按钮', $('rt-enable') && $('rt-dir') && $('btn-rt-save') && $('btn-rt-refresh'));
  check('开关与目录回填服务端配置', $('rt-enable').checked === true && $('rt-dir').value === rtDir, `checked=${$('rt-enable').checked} dir=${$('rt-dir').value}`);
  // 跑一遍离线文件
  await fetch(BASE + '/api/engine/start', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ kind: 'csv_file', path: csvPath, play_start_mode: 'begin' }) });
  let st = await waitFinished();
  check('离线文件跑完（无错误）', st && st.finished && !st.error, `finished=${st && st.finished} err=${st && st.error}`);
  click($('btn-rt-refresh')); await sleep(600);
  let rt = await getJson('/api/realtime');
  const files = fs.existsSync(rtDir) ? fs.readdirSync(rtDir).filter((f) => f.endsWith('.csv')) : [];
  check('目录下出现 <曲线>_<日期>.csv（8 条曲线各 1 个）', files.length === 8 && files.every((f) => /^(voltage|current|power|power_factor|fundamental|harmonic|interharmonic|dc)_\d{8}\.csv$/.test(f)), files.join(','));
  const vFile = files.find((f) => f.startsWith('voltage_'));
  const vRows = vFile ? csvLines(path.join(rtDir, vFile)) - 1 : -1;
  check('voltage 文件行数 == 本次写入行数（含 flush）', rt.rows_written && rt.rows_written.voltage > 0 && vRows === rt.rows_written.voltage, `file=${vRows} written=${rt.rows_written && rt.rows_written.voltage}`);
  const hv = await getJson('/api/history/voltage?max_points=100000');
  check('voltage 文件行数 == 趋势历史点数（同一提取规则）', vRows === hv.count_total, `file=${vRows} history=${hv.count_total}`);
  const head = vFile ? fs.readFileSync(path.join(rtDir, vFile), 'utf8').split('\n')[0] : '';
  check('表头 = t_epoch_s,time_local,window_s,Ua,…（UTF-8 BOM）', head.charCodeAt(0) === 0xfeff && /^\uFEFFt_epoch_s,time_local,window_s,Ua,Ub,Uc/.test(head), head.slice(0, 60));
  const outTxt = $('rt-out').textContent || '';
  check('面板列出本次写入文件与行数', /voltage_\d{8}\.csv/.test(outTxt) && /已写 \d+ 行/.test(outTxt), outTxt.slice(0, 100));
  // 取消 current 勾选 → 再跑一遍 → current 文件行数不变、voltage 继续追加
  const before = { v: vRows, c: csvLines(path.join(rtDir, files.find((f) => f.startsWith('current_')))) - 1 };
  await putCfg({ output: { curve_save: { current: false } } });
  await fetch(BASE + '/api/engine/start', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ kind: 'csv_file', path: csvPath }) });
  st = await waitFinished();
  const after = { v: csvLines(path.join(rtDir, vFile)) - 1, c: csvLines(path.join(rtDir, files.find((f) => f.startsWith('current_')))) - 1 };
  check('未勾选「保存曲线」的 current 不再落盘，voltage 续写同一文件（追加不重写表头）', after.c === before.c && after.v === before.v * 2, JSON.stringify({ before, after }));
  await putCfg({ output: { curve_save: allSave } });
  // 关闭开关 → 再跑 → 行数不变
  clrDirty(); await nav('export'); await sleep(300);
  $('rt-enable').checked = false; change($('rt-enable'));
  calls.length = 0; click($('btn-rt-save')); await sleep(800);
  const put = calls.find((c) => c.url === '/api/config' && c.method === 'PUT');
  check('点「应用」→ PUT /api/config output.realtime_save=false', put && put.status === 200 && JSON.parse(put.body).output.realtime_save === false, put ? put.body : '未捕获');
  await fetch(BASE + '/api/engine/start', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ kind: 'csv_file', path: csvPath }) });
  st = await waitFinished();
  check('关闭后再跑一遍：文件行数不变', csvLines(path.join(rtDir, vFile)) - 1 === after.v, `rows=${csvLines(path.join(rtDir, vFile)) - 1}`);
  rt = await getJson('/api/realtime');
  check('/api/realtime 回显 enabled=false、仍列出目录现有文件', rt.enabled === false && rt.dir_files.length === 8, JSON.stringify({ enabled: rt.enabled, n: rt.dir_files.length }));
  await putCfg({ output: { realtime_save: true } });

  console.log('\n=== E2. 离线文件：播放起点 ===');
  clrDirty(); await nav('source');
  const setKind = async (k) => { $('src-kind').value = k; change($('src-kind')); await sleep(150); };
  await setKind('simulator');
  check('simulator 下「播放起点」下拉框与取值框禁用', $('src-playmode').disabled && $('src-playvalue').disabled);
  await setKind('csv_file');
  check('csv_file 下下拉框可用；模式=开头时取值框禁用', !$('src-playmode').disabled && $('src-playvalue').disabled);
  const opts = [...$('src-playmode').options].map((o) => o.value);
  check('下拉框 5 个选项 = begin/row/seconds/percent/time', JSON.stringify(opts) === JSON.stringify(['begin', 'row', 'seconds', 'percent', 'time']), opts.join(','));
  $('src-playmode').value = 'row'; change($('src-playmode')); await sleep(100);
  check('选「第 N 行」后取值框放开且占位说明随模式变化', !$('src-playvalue').disabled && /行/.test($('src-playvalue').placeholder), $('src-playvalue').placeholder);
  const run = async (mode, value) => {
    clrDirty(); await nav('source'); await setKind('csv_file');
    $('src-path').value = csvPath;
    $('src-playmode').value = mode; change($('src-playmode'));
    $('src-playvalue').value = value;
    calls.length = 0; click($('btn-start2'));
    await sleep(300);
    const body = bodies('/api/engine/start', 'POST').pop();
    const start = calls.find((c) => c.url.includes('/api/engine/start'));
    const s = await waitFinished();
    return { body, status: start && start.status, st: s };
  };
  let r = await run('row', String(6400 * 1 + 1));
  check('row=6401：载荷带 play_start_mode/value', r.body && r.body.play_start_mode === 'row' && r.body.play_start_value === '6401', JSON.stringify(r.body));
  check('row=6401：摄入样本 = 总行数 − 6400', r.st.engine.samples_in === CSV_ROWS - 6400, `samples_in=${r.st.engine.samples_in}`);
  check('摘要显示「播放起点」与跳过行数', /播放起点/.test($('src-summary').textContent) && /跳过 6400 行/.test($('src-summary').textContent));
  r = await run('seconds', '2');
  check('seconds=2：摄入样本 = 总行数 − 12800', r.st.engine.samples_in === CSV_ROWS - 12800, `samples_in=${r.st.engine.samples_in}`);
  r = await run('percent', '50');
  check('percent=50：摄入样本 ≈ 一半（±2 块）', Math.abs(r.st.engine.samples_in - CSV_ROWS / 2) <= 1300, `samples_in=${r.st.engine.samples_in}`);
  r = await run('time', '00:12:43');
  check('time=00:12:43（只填时刻，匹配 0/00/00 写法）：摄入样本 = 最后 1 s', r.st.engine.samples_in === 6400, `samples_in=${r.st.engine.samples_in}`);
  check('曲线起点 ≥ 763 s（t=00:12:43）', r.st.history.voltage.t_first >= 763 - 1e-6 && r.st.history.voltage.t_first < 765, `t_first=${r.st.history.voltage.t_first}`);
  r = await run('time', '23:59:00');
  check('time 超出文件范围：引擎错误可见（播放起点超出文件范围）', r.st && /播放起点超出文件范围/.test(r.st.error || ''), (r.st.error || '').slice(0, 80));
  r = await run('row', 'abc');
  check('非法取值：服务端 400 拒绝', r.status === 400, `status=${r.status}`);
  const toastTxt = (document.getElementById('toast') || document.body).textContent || '';
  check('界面给出「播放起点」错误提示', /播放起点/.test(toastTxt), toastTxt.slice(-80));
  r = await run('begin', '');
  check('选回「文件开头」：全量摄入', r.st.engine.samples_in === CSV_ROWS && r.body.play_start_mode === 'begin', `samples_in=${r.st.engine.samples_in}`);

  console.log('\n=== E3. 曲线悬停取值 ===');
  await nav('overview');
  if (typeof window.refreshHistory === 'function') await window.refreshHistory();
  await sleep(300);
  const cv = $('ov-u');
  check('趋势图 canvas 已挂图表元数据并绑定悬停', cv.__chart && cv.__hoverBound && cv.style.cursor === 'crosshair');
  const c = cv.__chart;
  check('图表元数据含 3 条曲线（Ua/Ub/Uc）与坐标映射', c && c.pts.length === 3 && typeof c.X === 'function' && typeof c.Y === 'function', c && c.pts.map((p) => p.name).join(','));
  const hist = Sobj().histCache.voltage || [];
  check('曲线数据来自 S.histCache.voltage（≥2 点）', hist.length >= 2, `n=${hist.length}`);
  // 把鼠标放到最后一个点的像素位置
  const lastX = c.pts[0].data[c.pts[0].data.length - 1][0];
  const px = c.X(lastX);
  cv.dispatchEvent(new window.MouseEvent('mousemove', { clientX: px, clientY: 50, bubbles: true }));
  await sleep(50);
  let hi = cv.__hoverInfo;
  check('mousemove 后给出悬停信息（3 项）', hi && hi.items.length === 3, hi && JSON.stringify(hi.items.map((i) => i.name)));
  const lastRec = hist[hist.length - 1];
  check('悬停值 == 最近点的真实数据（Ua/Ub/Uc）', hi && Math.abs(hi.items[0].y - lastRec.Ua) < 1e-9 && Math.abs(hi.items[1].y - lastRec.Ub) < 1e-9 && Math.abs(hi.items[2].y - lastRec.Uc) < 1e-9,
    hi && `${hi.items[0].y} vs ${lastRec.Ua}`);
  check('悬停 x 文本为完整时刻（含毫秒）', hi && /\d{2}:\d{2}:\d{2}\.\d{3}/.test(hi.xText), hi && hi.xText);
  // 中间点：取第 1 个点与最后一个点中点偏左 → 应吸附到最近点
  const firstX = c.pts[0].data[0][0];
  const midPx = c.X(firstX) + 1;
  cv.dispatchEvent(new window.MouseEvent('mousemove', { clientX: midPx, clientY: 50, bubbles: true }));
  await sleep(50);
  hi = cv.__hoverInfo;
  check('靠近第 1 个点时吸附到第 1 个点', hi && hi.items[0].idx === 0 && Math.abs(hi.items[0].y - hist[0].Ua) < 1e-9, hi && `idx=${hi.items[0].idx}`);
  // 实时推送 render() 后悬停仍在
  Sobj().state = await getJson('/api/state');
  if (typeof window.render === 'function') window.render();
  await sleep(50);
  check('render()（实时推送重绘）后悬停信息仍在', cv.__hoverInfo && cv.__hoverInfo.items.length === 3);
  cv.dispatchEvent(new window.MouseEvent('mouseleave', { bubbles: true }));
  await sleep(50);
  check('mouseleave 清除悬停', !cv.__hoverInfo && !cv.__hover);
  // 绘图区外不给信息
  cv.dispatchEvent(new window.MouseEvent('mousemove', { clientX: 5, clientY: 50, bubbles: true }));
  await sleep(50);
  check('鼠标在绘图区外（y 轴刻度区）不显示取值', !cv.__hoverInfo);
  cv.dispatchEvent(new window.MouseEvent('mouseleave', { bubbles: true }));
  // 频谱/波形页同样可用
  Sobj().result = await getJson('/api/result?full=true');
  await nav('spectrum'); await sleep(300);
  const sp = $('sp-chart');
  check('频谱图同样绑定悬停', sp.__hoverBound && sp.__chart && sp.__chart.pts.length >= 1);
  if (sp.__chart && sp.__chart.pts.length) {
    const d = sp.__chart.pts[0].data; const i50 = d.reduce((b, p, i) => (Math.abs(p[0] - 50) < Math.abs(d[b][0] - 50) ? i : b), 0);
    sp.dispatchEvent(new window.MouseEvent('mousemove', { clientX: sp.__chart.X(d[i50][0]), clientY: 40, bubbles: true }));
    await sleep(50);
    check('频谱图悬停到 50Hz 给出 Hz 文本与幅值', sp.__hoverInfo && /Hz/.test(sp.__hoverInfo.xText) && Math.abs(sp.__hoverInfo.items[0].x - 50) < 1.01, sp.__hoverInfo && sp.__hoverInfo.xText);
  }

  // 收尾
  await putCfg({ output: { curve_save: allSave, realtime_save: true, realtime_dir: 'output/realtime' }, source: { play_start_mode: 'begin', play_start_value: '' } });
  await fetch(BASE + '/api/engine/start', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ kind: 'simulator', play_start_mode: 'begin' }) });
  try { fs.rmSync(rtDir, { recursive: true, force: true }); } catch (e) { /* ignore */ }

  console.log(`\n=== 结果：PASS ${pass} / FAIL ${fail} ===`);
  if (fails.length) { console.log('失败项：'); fails.forEach((f) => console.log('  - ' + f)); }
  process.exit(fail ? 1 : 0);
}

main().catch((e) => { console.error('脚本异常：', e); process.exit(2); });
