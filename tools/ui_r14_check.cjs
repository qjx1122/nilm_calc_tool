#!/usr/bin/env node
/* 第 14 轮界面检查：总线侧 + 分路侧设备 双数据源（侧别切换 / 分路侧面板 / 联动播放 / 子界面按侧显示）。
 * jsdom 驱动真实 index.html + app.js，打真实服务端（需先 serve 在 8000，data/sample_6400hz.csv 存在）。
 *
 *   L1 导航含「负荷辨识」；参数表单按 6 个算法生成并回填服务端配置
 *   L2 播放 data/nilm_steps.csv 后：卡片计数、事件表含 6 算法、方向 ↑/↓、幅值、起止时间；周波窗曲线有点
 *   L3 过滤算法 → 表格只剩该算法；改 GLR 门限 → 保存 → PUT /api/config 载荷含 nilm.algorithms.glr.threshold；服务端生效
 *   L4 清空 → 表格为空；徽标归零
 *
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r12_check.cjs [baseUrl]
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

async function main() {
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const calls = [];
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
  const { window } = dom, { document } = window;
  // localStorage 在 jsdom 可用；先清掉上次的侧别
  try { window.localStorage.removeItem('elec_side'); } catch (e) {}
  window.eval(js + '\n;window.__S = () => S;window.__setSide = setSide;');
  if (typeof window.init === 'function') window.init();
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const api = async (u, o) => (await fetch(BASE + u, o)).json();
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(700); };

  await api('/api/engine/stop', { method: 'POST' });
  await api('/api/branch/engine/stop', { method: 'POST' });
  console.log('L1 侧别切换器与分路侧面板');
  const navs = (side) => [...document.querySelectorAll(`.navitem[data-side="${side}"]`)].map(b => b.dataset.view);
  check('导航分三组：总览(overview,source,compare) / 总线侧 / 分路侧', navs('bus').includes('overview') && navs('bus').includes('source') && navs('bus').includes('compare') && navs('bus').includes('voltage') && navs('branch').includes('voltage') && navs('branch').includes('nilm') && !navs('branch').includes('overview') && !navs('branch').includes('source'));
  check('顶栏不再有侧别切换按钮', !$('side-bus') && !$('side-branch'));
  check('顶栏分两行：总线侧 / 分路侧', !!$('topstats-bus') && !!$('topstats-branch') && !!$('st-br-running') && !$('st-branch'));
  await nav('source');
  check('总线侧页面显示分路侧面板', $('branch-form').style.display !== 'none' && !!$('br-enabled'));
  console.log('L2 配置分路侧并启用 → 总线侧启动 → 两侧同时播放');
  $('br-enabled').checked = true; change($('br-enabled'));
  $('br-path').value = 'data/nilm_steps.csv'; change($('br-path'));
  click($('btn-br-probe')); await sleep(1200);
  check('分路侧文件探查输出', /行数 \d+/.test($('br-probe-out').textContent), $('br-probe-out').textContent.slice(0, 60));
  $('src-file-speed').value = '1'; change($('src-file-speed'));
  $('br-pt').value = '110'; change($('br-pt')); $('br-ct').value = '20'; change($('br-ct')); $('br-toffset').value = '0'; change($('br-toffset'));
  click($('btn-br-save')); await sleep(900);
  const bcfg = await api('/api/branch/config'), buscfg0 = await api('/api/config');
  // 列映射：两侧独立
  $('br-mapen').checked = true; change($('br-mapen'));
  click($('btn-br-map-fromprobe')); await sleep(200);
  click($('btn-br-map-save')); await sleep(800);
  const bcfg2 = await api('/api/branch/config'), buscfg2 = await api('/api/config');
  check('分路侧列映射独立保存（启用 + 按表头填入），总线侧列映射不受影响', bcfg2.columns.mapping_enabled === true && !!bcfg2.columns.mapping.ua && buscfg2.columns.mapping_enabled === false, JSON.stringify(bcfg2.columns.mapping));
  check('分路侧 PT/CT 单独保存，总线侧不受影响', bcfg.transform.pt_ratio === 110 && bcfg.transform.ct_ratio === 20 && buscfg0.transform.pt_ratio !== 110, `${bcfg.transform.pt_ratio}/${bcfg.transform.ct_ratio} bus=${buscfg0.transform.pt_ratio}`);
  check('分路侧 source 已保存，倍速随总线侧（1×）', bcfg.source.kind === 'csv_file' && bcfg.source.path.endsWith('nilm_steps.csv') && bcfg.source.file_speed === 1, JSON.stringify(bcfg.source.path));
  check('总线侧 branch.enabled 已保存', (await api('/api/config')).branch.enabled === true);
  check('分路侧固定为离线文件且块大小已存', bcfg.source.kind === 'csv_file' && bcfg.source.block_samples === 640);
  // 总线侧不是离线文件 → 提示 + 启动不联动
  $('src-kind').value = 'simulator'; change($('src-kind')); await sleep(300);
  check('总线侧非离线文件时显示提示', $('br-mode-note').style.display !== 'none');
  const rs = await api('/api/engine/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: 'simulator' }) });
  check('模拟器模式启动不带起分路侧', rs.branch && rs.branch.skipped === true, JSON.stringify(rs.branch));
  await api('/api/engine/stop', { method: 'POST' }); await sleep(300);
  $('src-kind').value = 'csv_file'; change($('src-kind'));
  $('src-path').value = 'data/sample_6400hz.csv'; $('src-file-speed').value = '0.5';   // v0.15.1 起节拍精确：5 s 文件 1× 会在 L2–L4 检查途中播完，改 0.5×
  click($('btn-start2')); await sleep(2500);
  const st = await api('/api/state'), bst = await api('/api/branch/state');
  check('总线侧运行中', st.running === true);
  check('分路侧同时运行中', bst.running === true && bst.side === 'branch', `running=${bst.running}`);
  check('分路侧样本在增长', bst.engine.samples_in > 0, String(bst.engine.samples_in));
  check('两侧数据源不同', st.config.source.path !== bst.config.source.path);
  check('顶栏分路侧行=运行中且有 fs/PT-CT/样本', $('st-br-running').textContent === '运行中' && /Hz/.test($('st-br-fs').textContent) && /\//.test($('st-br-ptct').textContent) && /\d/.test($('st-br-samples').textContent), `${$('st-br-running').textContent} ${$('st-br-fs').textContent} ${$('st-br-samples').textContent}`);
  check('顶栏总线侧行=运行中', $('st-running').textContent === '运行中');
  check('分路侧行不可点击切侧', !$('st-br-running').onclick && !$('topstats-branch').onclick);
  console.log('L3 联动暂停/恢复/停止');
  click($('btn-pause')); await sleep(600);
  const p1 = await api('/api/branch/state'); await sleep(800); const p2 = await api('/api/branch/state');
  check('总线侧暂停 → 分路侧也暂停', p1.paused === true && p1.engine.samples_in === p2.engine.samples_in, `${p1.paused} ${p1.engine.samples_in}→${p2.engine.samples_in}`);
  click($('btn-pause')); await sleep(900);
  check('恢复 → 分路侧继续', (await api('/api/branch/state')).engine.samples_in > p2.engine.samples_in);
  console.log('L4 切到分路侧：子界面显示分路侧结果');
  click(document.querySelector('.navitem[data-view="voltage"][data-side="branch"]')); await sleep(1800);
  const S = window.__S();
  check('S.side=branch 且 state.side=branch', S.side === 'branch' && S.state && S.state.side === 'branch');
  check('顶栏数据源=分路侧文件', $('st-source').textContent === 'csv_file' && document.body.classList.contains('side-branch'));
  check('切到分路侧后顶栏两行仍各显各的（总线行来自摘要）', $('st-running').textContent === '运行中' && $('st-br-running').textContent === '运行中' && /Hz/.test($('st-fs').textContent), `${$('st-running').textContent}/${$('st-br-running').textContent}`);
  check('分路侧时总线侧徽标仍随摘要刷新（nilm 徽标元素存在且按对侧计数）', !!$('nav-nilm-badge') && !!$('nav-nilm-badge-br'));
  check('分路侧导航项高亮、总线侧同名项不高亮', document.querySelector('.navitem[data-view="voltage"][data-side="branch"]').classList.contains('active') && !document.querySelector('.navitem[data-view="voltage"][data-side="bus"]').classList.contains('active'));
  const bres = await api('/api/branch/result?full=false');
  check('总览结果来自分路侧（P 量级≈1.5~2.85 MW）', S.result && Math.abs(S.result.t_ref - bres.t_ref) < 5, `${S.result && S.result.t_ref} vs ${bres.t_ref}`);
  click(document.querySelector('.navitem[data-view="nilm"][data-side="branch"]')); await sleep(1500);
  check('分路侧负荷辨识页有周波数据', (window.__S().state.engine.nilm_cycles || 0) > 0 && window.__S().side === 'branch');
  click(document.querySelector('.navitem[data-view="overview"]')); await sleep(1500);
  check('点总览 → 回到总线侧', window.__S().side === 'bus' && window.__S().state.side === 'bus');
  check('总览有两侧状态卡', /总线侧数据源/.test($('ov-sides').textContent) && /分路侧设备数据源/.test($('ov-sides').textContent) && /运行中/.test($('ov-sides').textContent), $('ov-sides').textContent.slice(0, 80));
  check('分路侧分组标题徽标=运行中', $('nav-br-state').textContent === '运行中', $('nav-br-state').textContent);
  await sleep(5000);   // 0.5× 下分路侧 voltage 首次出结果 ≈3 s 墙钟 + 总览分路刷新节流
  check('总览曲线两侧分开：分路侧四张独立画布可见且已绘制（不与总线侧同轴）', !$('ov-curves').classList.contains('no-branch') && ['ov-u-br', 'ov-i-br', 'ov-p-br', 'ov-thd-br'].every(id => $(id) && $(id).closest('.ov-br-panel')) && !!($('ov-p-br').__chart) && !!($('ov-p').__chart) && $('ov-p').__chart.pts.every(s => !/分路/.test(s.name)), `${$('ov-p-br').__chart ? '分路 P 图 ' + $('ov-p-br').__chart.pts.length + ' 条' : '分路 P 图未绘制'}`);
  check('分路侧未启用时分路曲线列隐藏（CSS 类）', /\.ov-curves\.no-branch \.ov-br-panel\{display:none\}/.test(require('fs').readFileSync(path.join(ROOT, 'app/static/style.css'), 'utf8')));
  check('总览卡片两侧放一起（总线/分路标签 + 总线−分路）', /总线/.test($('ov-cards').textContent) && /分路/.test($('ov-cards').textContent) && /总线−分路/.test($('ov-cards').textContent) && !$('ov-br-cards'), $('ov-cards').textContent.slice(0, 80));
  // 增量刷新：相同内容不触碰 DOM
  const probeEl = $('ov-cards'); const before = probeEl.firstElementChild; const html0 = probeEl.innerHTML;
  probeEl.innerHTML = html0;
  check('增量刷新：相同 innerHTML 不重建节点', probeEl.firstElementChild === before);
  const sig0 = $('ov-p').__sig; window.__S().view = 'overview'; const chart0 = $('ov-p').__chart; probeEl.innerHTML = html0;
  check('增量刷新：曲线签名机制存在', typeof sig0 === 'string' && sig0.length > 0 && chart0 !== undefined);
  console.log('L5 跨侧对比');
  const cmp0 = await api('/api/compare/power');
  check('两份样例文件起点不同 → 默认偏移 0 无对齐点，但给出建议偏移', cmp0.aligned_count === 0 && Math.abs(cmp0.offset_suggest_s) > 1000, `suggest=${cmp0.offset_suggest_s}`);
  const cmp = await api('/api/compare/power?offset_s=' + cmp0.offset_suggest_s);
  check('按起点对齐后 /api/compare/power 有对齐点、差值=总线−分路', cmp.aligned_count > 0 && cmp.latest && Math.abs(cmp.latest.diff.P - (cmp.latest.bus.P - cmp.latest.branch.P)) < 1e-6, `aligned=${cmp.aligned_count} bus=${cmp.bus_count} br=${cmp.branch_count}`);
  check('占比 = 分路/总线×100', cmp.latest && Math.abs(cmp.latest.ratio_pct.P - cmp.latest.branch.P / cmp.latest.bus.P * 100) < 1e-6);
  const cmpOff = await api('/api/compare/power?offset_s=9999');
  check('偏移 9999 s → 无对齐点', cmpOff.aligned_count === 0);
  await nav('compare'); await sleep(1500);
  check('跨侧对比页：元信息与表格', /已对齐/.test($('cmp-meta').textContent) && /总线侧/.test($('cmp-table').textContent) && $('cmp-key').options.length > 0, $('cmp-meta').textContent.slice(0, 60));
  click($('btn-cmp-suggest')); await sleep(1200);
  check('「按起点对齐」后页面有对齐点且表格有差值', /已对齐 [1-9]\d* 对/.test($('cmp-meta').textContent) && /W/.test($('cmp-table').textContent), $('cmp-meta').textContent.slice(0, 120));
  $('cmp-offset').value = '0.25'; click($('btn-cmp-save')); await sleep(800);
  check('保存偏移到 config.branch.time_offset_s', (await api('/api/config')).branch.time_offset_s === 0.25);
  $('cmp-offset').value = '0'; click($('btn-cmp-save')); await sleep(500);
  console.log('L6 公共时间段');
  await api('/api/engine/stop', { method: 'POST' }); await sleep(500);
  await nav('source'); await sleep(800);
  // 两份样例起点不同步 → 先给分路侧自定义时间轴：起点 = 总线侧起点 + 1 s
  const pb = await api('/api/probe?path=data/sample_6400hz.csv');
  const brStart = new Date((pb.t_first + 1) * 1000);
  const pad2 = (n) => String(n).padStart(2, '0');
  const txt = `${brStart.getFullYear()}-${pad2(brStart.getMonth() + 1)}-${pad2(brStart.getDate())} ${pad2(brStart.getHours())}:${pad2(brStart.getMinutes())}:${pad2(brStart.getSeconds())}`;
  $('br-customtime').checked = true; change($('br-customtime')); $('br-customstart').value = txt; change($('br-customstart'));
  $('br-common').checked = true; change($('br-common')); $('br-common-start').value = ''; change($('br-common-start'));
  click($('btn-br-save')); await sleep(900);
  check('公共时间段开关已保存', (await api('/api/config')).branch.common_window === true);
  click($('btn-br-common-preview')); await sleep(1500);
  check('预览公共时间段输出', /公共时间段：/.test($('br-common-out').textContent) && /总时长/.test($('br-common-out').textContent), $('br-common-out').textContent.slice(0, 100));
  const pv = await api('/api/common_window?preview=1');
  // 公共段 = 总线终点 − 分路起点；分路起点 = floor(总线起点 + 1)（起始文本按秒取整），与样例文件的秒内相位有关
  const cwExpect = (pb.t_first + 5.0) - Math.floor(pb.t_first + 1);
  check('公共时间段 = 总线终点 − 分路起点（起始文本按秒取整）', pv.ok && Math.abs(pv.duration_s - cwExpect) < 0.15, `${pv.duration_s} vs 期望 ${cwExpect.toFixed(3)}`);
  $('src-file-speed').value = '0'; change($('src-file-speed'));
  const rs2 = await api('/api/engine/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: 'csv_file', path: 'data/sample_6400hz.csv', file_speed: 0 }) });
  check('联动启动返回公共时间段且分路侧启动', rs2.ok && rs2.common_window && rs2.common_window.enabled && rs2.branch && rs2.branch.ok, JSON.stringify(rs2.branch));
  const waitDone = async () => { let a, b; for (let k = 0; k < 40; k++) { await sleep(600); a = await api('/api/state'); b = await api('/api/branch/state'); if (!a.running && !b.running) break; } return [a, b]; };
  let [st3, bst3] = await waitDone();
  check('顶栏显示公共时间段（起止/总时长/播放起点）', $('topstats-common').style.display !== 'none' && /s$/.test($('st-cw-dur').textContent) && $('st-cw-start').textContent !== '—', $('st-cw-dur').textContent);
  const expect = Math.round(pv.duration_s * 6400);
  check('两侧都只播放公共时间段（样本数 ≈ 4 s×6400，容差 1 块）', Math.abs(st3.engine.samples_in - expect) <= 640 && Math.abs(bst3.engine.samples_in - expect) <= 640, `bus=${st3.engine.samples_in} br=${bst3.engine.samples_in} expect=${expect}`);
  check('分路侧倍速与总线侧一致（不限速）', bst3.config.source.file_speed === 0 && st3.config.source.file_speed === 0);
  // 自定义起始时间：公共起点 + 2 s
  const cs = new Date((pv.t_start + 2) * 1000);
  const txt2 = `${cs.getFullYear()}-${pad2(cs.getMonth() + 1)}-${pad2(cs.getDate())} ${pad2(cs.getHours())}:${pad2(cs.getMinutes())}:${pad2(cs.getSeconds())}`;
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ branch: { common_start: txt2 } }) });
  const rs3 = await api('/api/engine/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: 'csv_file', path: 'data/sample_6400hz.csv', file_speed: 0 }) });
  const [st4, bst4] = await waitDone();
  check('自定义播放起始时间生效（两侧样本 ≈ 2 s×6400）', rs3.common_window && rs3.common_window.play_start_source === '自定义播放起始时间' && Math.abs(st4.engine.samples_in - (expect - 12800)) <= 1300 && Math.abs(bst4.engine.samples_in - (expect - 12800)) <= 1300, `bus=${st4.engine.samples_in} br=${bst4.engine.samples_in}`);
  // L7（v0.15.1）：坐标轴固定为公共时间段；两侧严格同步；先播完的一侧停止刷新
  console.log('L7 公共时间段：坐标轴/同步/完成侧停刷');
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ branch: { common_start: '' } }) });
  const rs5 = await api('/api/engine/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: 'csv_file', path: 'data/sample_6400hz.csv', file_speed: 4 }) });
  check('4 倍速联动启动（公共时间段）', rs5.ok && rs5.branch && rs5.branch.ok, JSON.stringify(rs5.branch || rs5.error));
  await nav('overview'); await sleep(300);
  let worst = 0, nBoth = 0;
  for (let k = 0; k < 12; k++) {
    await sleep(150);
    const a = await api('/api/state'), b = await api('/api/branch/state');
    if (a.running && b.running && a.source && b.source && a.source.t_end && b.source.t_end) { nBoth++; worst = Math.max(worst, Math.abs(a.source.t_end - b.source.t_end)); }
  }
  check('两侧播放数据时刻严格同步（共享节拍钟+互锁，|Δ| ≤ 容差 0.2 s）', nBoth >= 2 && worst <= 0.25, `样本点 ${nBoth}，最大偏差 ${worst.toFixed(3)} s`);
  await sleep(900);
  const ch = ($('ov-p') || {}).__chart;
  const cw5 = rs5.common_window;
  check('总览 P/Q/S 趋势图坐标轴固定为公共时间段整段', !!ch && Math.abs((ch.xmax - ch.xmin) - cw5.duration_s) < 0.2 && ch.pts.every(sr => sr.data.every(([x]) => x >= ch.xmin - 1e-3 && x <= ch.xmax + 1e-3)), ch ? `轴宽 ${(ch.xmax - ch.xmin).toFixed(2)} s vs 公共段 ${cw5.duration_s} s` : '无图');
  await waitDone(); await nav('overview'); await sleep(1200);
  check('两侧播完后总览提示「已播放完毕（数据停在终值）」且分路侧不再请求', /已播放完毕/.test($('ov-br-hint').textContent) && window.OVB && window.OVB.doneFetched === true, $('ov-br-hint').textContent);
  // 还原
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ branch: { common_window: false, common_start: '' } }) });
  await api('/api/branch/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source: { custom_time: false, custom_time_start: '' } }) });
  $('src-file-speed').value = '1';
  click($('btn-stop')); await sleep(800);
  const st2 = await api('/api/state'), bst2 = await api('/api/branch/state');
  check('总线侧停止 → 分路侧也停止', !st2.running && !bst2.running);
  console.log(`\n结果：${pass} 通过，${fail} 失败${fail ? '：' + fails.join('；') : ''}`);
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
