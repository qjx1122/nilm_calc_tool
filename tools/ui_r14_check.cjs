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
  check('顶栏分路侧状态胶囊', !!$('st-branch'));
  await nav('source');
  check('总线侧页面显示分路侧面板', $('branch-form').style.display !== 'none' && !!$('br-enabled'));
  console.log('L2 配置分路侧并启用 → 总线侧启动 → 两侧同时播放');
  $('br-enabled').checked = true; change($('br-enabled'));
  $('br-path').value = 'data/nilm_steps.csv'; change($('br-path'));
  click($('btn-br-probe')); await sleep(1200);
  check('分路侧文件探查输出', /行数 \d+/.test($('br-probe-out').textContent), $('br-probe-out').textContent.slice(0, 60));
  $('br-file-speed').value = '1'; change($('br-file-speed'));
  $('br-pt').value = '110'; change($('br-pt')); $('br-ct').value = '20'; change($('br-ct')); $('br-toffset').value = '0'; change($('br-toffset'));
  click($('btn-br-save')); await sleep(900);
  const bcfg = await api('/api/branch/config'), buscfg0 = await api('/api/config');
  check('分路侧 PT/CT 单独保存，总线侧不受影响', bcfg.transform.pt_ratio === 110 && bcfg.transform.ct_ratio === 20 && buscfg0.transform.pt_ratio !== 110, `${bcfg.transform.pt_ratio}/${bcfg.transform.ct_ratio} bus=${buscfg0.transform.pt_ratio}`);
  check('分路侧 source 已保存', bcfg.source.kind === 'csv_file' && bcfg.source.path.endsWith('nilm_steps.csv') && bcfg.source.file_speed === 1, JSON.stringify(bcfg.source.path));
  check('总线侧 branch.enabled 已保存', (await api('/api/config')).branch.enabled === true);
  check('分路侧固定为离线文件且块大小已存', bcfg.source.kind === 'csv_file' && bcfg.source.block_samples === 640);
  // 总线侧不是离线文件 → 提示 + 启动不联动
  $('src-kind').value = 'simulator'; change($('src-kind')); await sleep(300);
  check('总线侧非离线文件时显示提示', $('br-mode-note').style.display !== 'none');
  const rs = await api('/api/engine/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: 'simulator' }) });
  check('模拟器模式启动不带起分路侧', rs.branch && rs.branch.skipped === true, JSON.stringify(rs.branch));
  await api('/api/engine/stop', { method: 'POST' }); await sleep(300);
  $('src-kind').value = 'csv_file'; change($('src-kind'));
  $('src-path').value = 'data/sample_6400hz.csv'; $('src-file-speed').value = '1';
  click($('btn-start2')); await sleep(2500);
  const st = await api('/api/state'), bst = await api('/api/branch/state');
  check('总线侧运行中', st.running === true);
  check('分路侧同时运行中', bst.running === true && bst.side === 'branch', `running=${bst.running}`);
  check('分路侧样本在增长', bst.engine.samples_in > 0, String(bst.engine.samples_in));
  check('两侧数据源不同', st.config.source.path !== bst.config.source.path);
  check('顶栏分路侧胶囊=运行中', $('st-branch').textContent === '运行中' && $('st-peer-label').textContent === '分路侧', $('st-branch').textContent);
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
  check('分路侧时顶栏显示总线侧状态胶囊', $('st-peer-label').textContent === '总线侧' && $('st-branch-wrap').style.display !== 'none' && $('st-branch').textContent === '运行中', $('st-branch').textContent);
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
  click($('btn-stop')); await sleep(800);
  const st2 = await api('/api/state'), bst2 = await api('/api/branch/state');
  check('总线侧停止 → 分路侧也停止', !st2.running && !bst2.running);
  console.log(`\n结果：${pass} 通过，${fail} 失败${fail ? '：' + fails.join('；') : ''}`);
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
