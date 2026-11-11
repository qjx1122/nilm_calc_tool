#!/usr/bin/env node
/* 第 122 轮（v0.90）界面检查：数据处理页「设备画像提取」区 + 负荷辨识页「设备画像匹配」算法面板。
 *   P1 数据处理页存在 np-* 控件；填入设备侧文件 + 标签 → 提取 → 结果区出现「画像已写出」与启动/停止画像表
 *   P2 「填入总线侧画像路径」→ 总线侧 nilm-profile_path 被填、profile 勾选被勾上；分路侧同理（-br）
 *   P3 负荷辨识页：算法面板含 profile（两侧），v0.90 的 6 个参数都在；collectNilmPayload 带 profile_path（字符串）与 algorithms.profile
 *   P4 自适应勾选时 profile 参数不灰显
 * 用法：TZ=Asia/Shanghai JSDOM_DIR=<含 node_modules/jsdom 的目录> node tools/ui_r90_check.cjs [baseUrl] [设备侧csv] [标签文件]
 * 输入文件：设备侧录波（一台设备启停 3 次）和对应的标签文件。可以用 tests/test_r90_nilm_profile.py 里的
 *   _wave(_dev, 20.0) / _write_csv / _labels 生成。录波的时间戳只有时分秒，标签按本地时间写，
 *   所以生成文件、服务端、本脚本三者要在同一时区。
 * 2026-11-11（v0.99.50，补-B5）更新：
 *   - 数据处理页自 2026-11-09 起分成 5 个子界面，进入页面后要先点「设备画像提取」；
 *   - 画像提取现在有自己的文件路径和基准配置（np-path / np-base-*），不再借用调参面板的 nt-path；
 *   - v0.99.23 起没有「启用 PT/CT」开关（出厂变比 1 / 1 即不换算），去掉取消勾选那一步；
 *   - 算法面板的数值参数已不止 6 个，P3 改为要求 v0.90 的 6 个参数都在，不再钉总数；
 *   - init 只调一次（原来手动调用加上 DOMContentLoaded 会跑两遍）。
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
  // app.js 自己注册了 DOMContentLoaded → init，而 jsdom 在构造函数返回之后才派发这个事件：
  // 这里再手动调一次的话 init 会跑两遍，所有匿名函数绑定的事件都多绑一次。先去掉那个监听，只调一次。
  document.removeEventListener('DOMContentLoaded', window.init);
  window.init();
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(600); };

  await nav('process');
  // 数据处理页自 2026-11-09 起分成 5 个子界面；画像提取子界面的文件列表、基准配置在第一次打开时才加载
  click(document.querySelector('#sub-nav-process .sub-navitem[data-subview="profile-extract"]')); await sleep(1200);
  check('P1 np-* 控件存在', ['np-form', 'np-device', 'np-labels', 'np-pre', 'np-post', 'np-tol', 'np-name', 'btn-np-run', 'btn-np-fill-bus', 'btn-np-fill-branch', 'np-status', 'np-result'].every((i) => $(i)));
  // 画像提取现在有自己的文件路径和基准配置（np-*），不再借用调参面板的 nt-path。
  // 原来这里还会取消勾选「启用 PT/CT」让画像按二次侧计算；v0.99.23 起没有这个开关，出厂变比 1 / 1 本身就是不换算。
  $('np-path').value = DEV;
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
  // v0.90 时面板正好 6 个数值参数；之后各版本陆续加了相序映射、多尺度、分阶段等参数，所以不再钉总数，只要求当初的 6 个都在
  const first6 = ['d2_max', 'min_confidence', 'k_sigma', 'margin', 'lambda_rel', 'state_check'];
  check('P3 总线侧 profile 面板存在、含 v0.90 的 6 个参数', !!panel && first6.every((k) => { const el = $('nilm-profile-' + k); return !!el && panel.contains(el); }) && panel.querySelectorAll('input[type=number]').length >= 6 && /设备画像匹配/.test(panel.textContent),
    panel ? `数值输入框 ${panel.querySelectorAll('input[type=number]').length} 个；缺 ${first6.filter((k) => !$('nilm-profile-' + k)).join(',') || '无'}` : '面板不存在');
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
