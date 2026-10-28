#!/usr/bin/env node
/* 第 122 轮（v0.90）界面检查：数据处理页「设备画像提取」区 + 负荷辨识页「设备画像匹配」算法面板。
 *   P1 数据处理页存在 np-* 控件；填入设备侧文件 + 标签 → 提取 → 结果区出现「画像已写出」与启动/停止画像表
 *   P2 「填入总线侧画像路径」→ 总线侧 nilm-profile_path 被填、profile 勾选被勾上；分路侧同理（-br）
 *   P3 负荷辨识页：算法面板含 profile（两侧），参数输入 6 个；collectNilmPayload 带 profile_path（字符串）与 algorithms.profile
 *   P4 自适应勾选时 profile 参数不灰显
 * 用法：JSDOM_DIR=<含 node_modules/jsdom 的目录> node tools/ui_r90_check.cjs [baseUrl] [设备侧csv] [标签文件]
 */
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const { JSDOM } = require(path.join(process.env.JSDOM_DIR || ROOT, 'node_modules/jsdom'));
const BASE = process.argv[2] || 'http://127.0.0.1:8000';
const DEV = process.argv[3] || '/tmp/prof/dev.csv';
const LAB = process.argv[4] || '/tmp/prof/lab.csv';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let pass = 0, fail = 0; const fails = [];
function check(name, ok, detail = '') {
  if (ok) { pass++; console.log(`  ✓ ${name}${detail ? '　' + detail : ''}`); }
  else { fail++; fails.push(name); console.log(`  ✗ ${name}　${detail}`); }
}
async function main() {
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const calls = []; const errors = [];
  const dom = new JSDOM(html, {
    url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true,
    beforeParse(window) {
      window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, { get: (t, p) => (p === 'measureText' ? () => ({ width: 8 }) : p === 'createLinearGradient' ? () => ({ addColorStop() {} }) : () => {}), set: () => true });
      window.WebSocket = class { constructor() { this.readyState = 0; } close() {} send() {} };
      window.fetch = async (url, opts = {}) => { const abs = String(url).startsWith('http') ? String(url) : BASE + url; const r = await fetch(abs, opts); calls.push({ url: String(url), method: opts.method || 'GET', status: r.status, body: opts.body || null }); return r; };
      window.alert = () => {}; window.addEventListener('error', (e) => errors.push(String(e.message)));
    },
  });
  const { window } = dom, { document } = window;
  window.eval(js + '\n;window.collectNilmPayload = collectNilmPayload;');
  if (typeof window.init === 'function') window.init();
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(600); };

  await nav('process');
  check('P1 np-* 控件存在', ['np-form', 'np-device', 'np-labels', 'np-pre', 'np-post', 'np-tol', 'np-name', 'btn-np-run', 'btn-np-fill-bus', 'btn-np-fill-branch', 'np-status', 'np-result'].every((i) => $(i)));
  $('nt-path').value = DEV; if ($('nt-base-ptct').checked) { $('nt-base-ptct').checked = false; change($('nt-base-ptct')); }
  $('np-device').value = 'pumpA'; $('np-labels').value = fs.readFileSync(LAB, 'utf8');
  click($('btn-np-run'));
  for (let i = 0; i < 60 && !/画像已写出|失败/.test($('np-status').textContent); i++) await sleep(500);
  check('P1 提取成功', /画像已写出/.test($('np-status').textContent), $('np-status').textContent.slice(0, 120));
  const req = calls.find((c) => c.url.includes('/api/process/nilm_profile') && c.method === 'POST');
  check('P1 请求含 device_id/labels/base/pre/post', !!req && (() => { const b = JSON.parse(req.body); return b.device_id === 'pumpA' && /,开/.test(b.labels) && b.base && b.base_mode === 'custom' && b.pre_cycles === '10' && b.post_cycles === '50'; })());
  check('P1 结果区含启动/停止画像表', /启动画像：3 次事件/.test($('np-result').textContent) && /停止画像：3 次事件/.test($('np-result').textContent));
  check('P1 等价命令显示', /tools\/nilm_profile\.py/.test($('np-cmd').textContent));

  click($('btn-np-fill-bus')); await sleep(200);
  check('P2 总线侧画像路径已填并勾选', /profile_pumpA_.*\.json$/.test($('nilm-profile_path').value) && $('nilm-profile-enabled').checked, $('nilm-profile_path').value);
  click($('btn-np-fill-branch')); await sleep(200);
  check('P2 分路侧画像路径已填并勾选', $('nilm-profile_path-br') && /profile_pumpA_/.test($('nilm-profile_path-br').value) && $('nilm-profile-enabled-br').checked);

  await nav('nilm');
  const panel = document.querySelector('#nilm-algos .nilm-algo[data-algo="profile"]');
  check('P3 总线侧 profile 面板存在、含 6 个数值参数', !!panel && panel.querySelectorAll('input[type=number]').length === 6 && /设备画像匹配/.test(panel.textContent));
  check('P3 分路侧 profile 面板存在', !!document.querySelector('#nilm-algos-br .nilm-algo[data-algo="profile"]') && !!$('nilm-d2_max-br') === false && !!$('nilm-profile-d2_max-br'));
  const pl = window.collectNilmPayload('bus');
  check('P3 collectNilmPayload 含 profile_path 字符串与 algorithms.profile', typeof pl.profile_path === 'string' && pl.profile_path.includes('profile_pumpA') && pl.algorithms.profile && pl.algorithms.profile.enabled === true && pl.algorithms.profile.d2_max === 9 && pl.algorithms.profile.state_check === 1, JSON.stringify(pl.algorithms.profile));
  check('P3 筛选/标注下拉含 profile 选项', !![...$('nilm-filter').options].find((o) => o.value === 'profile') && !![...$('nilm-mark').options].find((o) => o.value === 'profile'));
  $('nilm-auto_params').checked = true; change($('nilm-auto_params')); await sleep(100);
  check('P4 自适应模式下 profile 参数不灰显、two_window 参数灰显', !$('nilm-profile-d2_max').disabled && $('nilm-two_window-k_sigma').disabled);
  $('nilm-auto_params').checked = false; change($('nilm-auto_params'));
  check('无 JS 运行错误', errors.length === 0, errors.join(' | ').slice(0, 200));
  console.log(`\n通过 ${pass} / 失败 ${fail}${fail ? '：' + fails.join('，') : ''}`);
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
