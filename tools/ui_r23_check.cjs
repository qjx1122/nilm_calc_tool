#!/usr/bin/env node
/* v0.23 界面检查：电气量子界面合并为「左：总线侧 / 右：分路侧」，分路侧未启用时右列与导航分组隐藏。
 * jsdom 驱动真实 index.html + app.js，打真实服务端（需先 serve 在 8000，data/sample_6400hz.csv、data/nilm_steps.csv 存在）。
 *
 *   D1 导航：电气量 9 项只剩一组（data-side=bus）；分路侧分组只剩 事件/负荷辨识/窗口/导出；未启用时分组隐藏
 *   D2 结构：9 个 section 内有 .dual > .dual-bus + .dual-br，右列所有 id 带 -br、radio name 带 -br
 *   D3 未启用分路侧：.dual.no-branch、右列不显示；左列照常有总线侧数据
 *   D4 启用并播放两侧：右列卡片/表格/画布有分路侧数据（与 /api/branch/result 一致），左列仍是总线侧
 *   D5 右列的下拉/单选变化只影响右列；左右两列数值不同（两份不同文件）
 *   D6 关闭分路侧：右列隐藏、导航分组隐藏
 *
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r23_check.cjs [baseUrl]
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
  window.eval(js + '\n;window.__S = () => S; window.__render = render; window.__renderTop = renderTop; window.__BRD = BRD;');
  return dom;
}

const VIEWS = ['voltage', 'current', 'power', 'power_factor', 'fundamental', 'harmonic', 'interharmonic', 'dc', 'spectrum'];
const CARD = { voltage: 'v-cards', current: 'i-cards', power: 'p-cards', power_factor: 'pf-cards', fundamental: 'f-cards', harmonic: 'h-cards', interharmonic: 'ih-cards', dc: 'dc-cards', spectrum: 'sp-info' };

async function main() {
  const api = async (u, o) => (await fetch(BASE + u, o)).json();
  const post = (u, body) => api(u, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
  const put = (u, body) => api(u, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  await post('/api/engine/stop'); await post('/api/branch/engine/stop');
  await put('/api/config', { branch: { enabled: false, common_window: false, common_start: '' } });

  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  console.log('D1 导航结构');
  check('电气量 9 项只在一组且 data-side=bus', VIEWS.every(v => html.includes(`data-view="${v}" data-side="bus"`) && !html.includes(`data-view="${v}" data-side="branch"`)));
  check('分路侧分组只剩 事件/负荷辨识/窗口/导出', ['events', 'nilm', 'windows', 'export'].every(v => html.includes(`data-view="${v}" data-side="branch"`)) && (html.match(/navitem" data-view="\w+" data-side="branch"/g) || []).length === 4);

  const calls = [];
  const dom = makeDom(calls);
  const { window } = dom, { document } = window;
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"][data-side="bus"]`)); await sleep(900); };
  const sync = async () => { window.__S().state = await api('/api/state'); const r = await fetch(BASE + '/api/result?full=true'); window.__S().result = r.ok ? await r.json() : null; window.__renderTop(); await window.__render(); };
  // jsdom 不加载外链 style.css，可见性以类名 + 样式表规则共同判定
  const css = fs.readFileSync(path.join(ROOT, 'app/static/style.css'), 'utf8');
  check('style.css 含 .dual.no-branch 与 body.no-branch-nav 隐藏规则', /\.dual\.no-branch[^{]*\.dual-br[^{]*\{[^}]*display:\s*none/.test(css) && /body\.no-branch-nav[^{]*\.navgroup-branch[^{]*\{[^}]*display:\s*none/.test(css));
  const visible = (el) => !!el && window.getComputedStyle(el).display !== 'none';

  console.log('D2 双列结构');
  check('9 个 section 都有 .dual > .dual-bus + .dual-br', VIEWS.every(v => $(`view-${v}`).querySelector('.dual > .dual-bus') && $(`view-${v}`).querySelector('.dual > .dual-br')));
  check('右列所有 id 以 -br 结尾、左列不含 -br', VIEWS.every(v => {
    const br = Array.from($(`view-${v}`).querySelectorAll('.dual-br [id]')), bus = Array.from($(`view-${v}`).querySelectorAll('.dual-bus [id]'));
    return br.length > 0 && br.every(e => e.id.endsWith('-br')) && bus.every(e => !e.id.endsWith('-br'));
  }));
  check('右列 radio name 带 -br（与左列不互斥）', !!document.querySelector('.dual-br input[name="hmode-u-br"]') && !!document.querySelector('.dual-bus input[name="hmode-u"]') &&
    !document.querySelector('.dual-br input[name="hmode-u"]'));
  check('右列曲线标题「保存曲线」勾选 data-side=branch', !!document.querySelector('#view-power_factor .dual-br input.curve-save[data-side="branch"][data-curve="power_factor"]'));

  console.log('D3 未启用分路侧');
  await nav('voltage'); await sync();
  if (process.env.DBG) console.log('DBG', document.body.className, JSON.stringify(((window.__S().state||{}).branch||{})).slice(0,60), window.__S().view, $('view-voltage').querySelector('.dual').className);
  check('导航「分路侧」分组隐藏', document.body.classList.contains('no-branch-nav'));
  check('.dual 带 no-branch，右列隐藏', $('view-voltage').querySelector('.dual').classList.contains('no-branch'));

  // 启动总线侧（sample）+ 分路侧（nilm_steps）：两份不同文件
  await put('/api/config', { branch: { enabled: true, common_window: false } });
  await put('/api/branch/config', { source: { kind: 'csv_file', path: 'data/nilm_steps.csv', file_speed: 1, custom_time: false } });
  const st = await post('/api/engine/start', { kind: 'csv_file', path: 'data/sample_6400hz.csv', file_speed: 1, custom_time: false });
  check('两侧启动成功', st.ok && st.branch && st.branch.ok, JSON.stringify(st.branch || {}).slice(0, 120));
  await sleep(2500);
  // 轮询在 jsdom 里走 setInterval；手动触发一次状态刷新
  await sync(); await sleep(1200); await sync();

  console.log('D4 启用并播放两侧');
  check('导航「分路侧」分组显示', !document.body.classList.contains('no-branch-nav'));
  check('.dual 去掉 no-branch，右列显示', !$('view-voltage').querySelector('.dual').classList.contains('no-branch'));
  const brRes = window.__BRD.result;
  check('BRD 已取得分路侧结果（/api/branch/result）', !!(brRes && brRes.quantities && brRes.quantities.voltage), calls.filter(c => c.url.startsWith('/api/branch/result')).length + ' 次');
  const num = (txt) => { const m = String(txt).replace(/,/g, '').match(/-?\d+(\.\d+)?/); return m ? +m[0] : NaN; };
  for (const v of VIEWS) {
    await nav(v);
    await window.__render();
    const busEl = $(CARD[v]), brEl = $(CARD[v] + '-br');
    const ok = busEl && brEl && busEl.textContent.trim().length > 0 && brEl.textContent.trim().length > 0 && !/尚无结果/.test(brEl.textContent);
    check(`${v}：左列有总线侧内容、右列有分路侧内容`, ok, ok ? '' : `bus=${(busEl || {}).textContent}`.slice(0, 80) + ` br=${(brEl || {}).textContent}`.slice(0, 80));
  }
  // 数值确实来自不同侧：A 相电压有效值 总线 ≈ 57.7×PT（样例 100）… vs 分路 nilm_steps 57.74 V 二次侧 ×PT
  await nav('voltage'); await window.__render();
  const firstV = (txt) => { const m = String(txt).match(/(-?\d+(?:\.\d+)?)\s*(k?)V/); return m ? +m[1] * (m[2] ? 1000 : 1) : NaN; };
  const busShown = firstV($('v-cards').textContent), brShown = firstV($('v-cards-br').textContent);
  const brApi = brRes.quantities.voltage.values.rms.A, busApi = window.__S().result.quantities.voltage.values.rms.A;
  check('左列 A 相电压 = /api/result、右列 = /api/branch/result（两侧数值不同）', Math.abs(busApi - brApi) > 1 && Math.abs(busShown - busApi) / busApi < 0.01 && Math.abs(brShown - brApi) / brApi < 0.01,
    `bus api=${busApi.toFixed(1)} shown=${busShown}；branch api=${brApi.toFixed(1)} shown=${brShown}`);

  console.log('D5 右列控件只影响右列');
  await nav('harmonic'); await window.__render();
  const rRms = document.querySelector('.dual-br input[name="hmode-u-br"][value="rms"]');
  rRms.checked = true; change(rRms); await sleep(300);
  check('右列切到「幅值 V」后左列 radio 仍为含有率', document.querySelector('.dual-bus input[name="hmode-u"][value="hr"]').checked && rRms.checked);
  await nav('spectrum'); await window.__render();
  $('sp-chan-br').value = 'Ia'; change($('sp-chan-br')); await sleep(300);
  check('右列频谱通道切到 Ia，左列仍 Ua', $('sp-chan').value === 'Ua' && /Ia/.test($('view-spectrum').querySelector('.dual-br .legend, .dual-br').textContent) && !/Ia 幅值谱/.test($('view-spectrum').querySelector('.dual-bus').textContent));

  console.log('D6 关闭分路侧');
  await post('/api/engine/stop'); await post('/api/branch/engine/stop');
  await put('/api/config', { branch: { enabled: false } });
  await nav('voltage'); await sync(); await sleep(300);
  check('右列隐藏、导航分组隐藏', $('view-voltage').querySelector('.dual').classList.contains('no-branch') && document.body.classList.contains('no-branch-nav'));

  console.log(`\n结果：${pass} 通过，${fail} 失败${fail ? '：' + fails.join('；') : ''}`);
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
