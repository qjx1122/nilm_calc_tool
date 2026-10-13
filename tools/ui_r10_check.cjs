#!/usr/bin/env node
/* 第 10 轮界面检查：数据源页「离线文件列映射」面板。
 * jsdom 驱动真实 index.html + app.js，打真实服务端（需先 serve 在 8000，data/sample_6400hz.csv 存在）。
 *
 *   M1 面板存在：开关 + 7 个字段输入；未启用时输入禁用并回填服务端 mapping
 *   M2 勾选启用 → 输入可用；「填入默认列序」→ 1..7；探查样例 → 「按探查表头填入」→ 表头名
 *   M3 清空 B/C 四项并保存 → PUT /api/config 载荷 columns.mapping_enabled=true 且 ub==''；服务端配置生效
 *   M4 探查输出显示「启用 columns.mapping」与「未映射不播放：B相电压…」
 *   M5 启动离线播放 → 数据源状态 notes 含「未映射」；B 相电压 rms=0；还原禁用
 *
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r10_check.cjs [baseUrl]
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
  window.eval(js + '\n;window.__S = () => S;');
  if (typeof window.init === 'function') window.init();
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const input = (el) => el.dispatchEvent(new window.Event('input', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(700); };
  const api = async (u, o) => (await fetch(BASE + u, o)).json();
  const bodies = (u, m) => calls.filter((c) => c.url.includes(u) && c.method === m && c.body).map((c) => JSON.parse(c.body));

  // 复位：禁用映射、停止引擎
  await api('/api/engine/stop', { method: 'POST' });
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ columns: { mapping_enabled: false, mapping: { timestamp: '1', ua: '2', ia: '3', ub: '4', ib: '5', uc: '6', ic: '7' } } }) });
  await nav('source'); click($('btn-refresh')); await sleep(800);
  const F = ['timestamp', 'ua', 'ia', 'ub', 'ib', 'uc', 'ic'];
  console.log('M1 面板与回填');
  check('开关与 7 个输入存在', !!$('cfg-mapen') && F.every((k) => !!$('cfg-map-' + k)));
  check('未启用：开关未勾选且输入禁用', !$('cfg-mapen').checked && $('cfg-map-ua').disabled);
  check('回填服务端 mapping（ic=7）', $('cfg-map-ic').value === '7', $('cfg-map-ic').value);

  console.log('M2 启用与填充');
  $('cfg-mapen').checked = true; change($('cfg-mapen'));
  check('启用后输入可用', !$('cfg-map-ua').disabled && !$('btn-map-fromprobe').disabled);
  F.forEach((k) => { $('cfg-map-' + k).value = ''; });
  click($('btn-map-default'));
  check('填入默认列序', F.map((k) => $('cfg-map-' + k).value).join(',') === '1,2,3,4,5,6,7');
  $('src-path').value = 'data/sample_6400hz.csv'; click($('btn-probe')); await sleep(2500);
  click($('btn-map-fromprobe'));
  check('按探查表头填入（ua 为表头名）', /电压|ua/i.test($('cfg-map-ua').value), $('cfg-map-ua').value);
  check('探查输出带列号 [1]', /\[1\]/.test($('probe-out').textContent));

  console.log('M3 保存');
  ['ub', 'ib', 'uc', 'ic'].forEach((k) => { $('cfg-map-' + k).value = ''; });
  click($('btn-savecfg')); await sleep(1500);
  const puts = bodies('/api/config', 'PUT');
  const last = puts[puts.length - 1] || {};
  check('PUT 载荷含 columns.mapping_enabled=true', last.columns && last.columns.mapping_enabled === true);
  check('PUT 载荷 ub 为空串', last.columns && last.columns.mapping.ub === '');
  const cfg = (await api('/api/state')).config.columns;
  check('服务端配置已启用且 ub 空', cfg.mapping_enabled === true && cfg.mapping.ub === '', JSON.stringify(cfg.mapping));

  console.log('M4 探查显示');
  const nProbe = calls.filter((c) => c.url.includes('/api/probe')).length;
  click($('btn-probe'));
  for (let i = 0; i < 40 && calls.filter((c) => c.url.includes('/api/probe')).length <= nProbe; i++) await sleep(250);
  await sleep(1500);
  const po = $('probe-out').textContent;
  check('显示启用 columns.mapping', po.includes('启用 columns.mapping'));
  check('显示未映射不播放 B相电压', po.includes('未映射不播放') && po.includes('B相电压'), po.slice(0, 200));

  console.log('M5 播放');
  $('src-kind').value = 'csv_file'; change($('src-kind'));
  $('src-path').value = 'data/sample_6400hz.csv'; click($('btn-start2')); await sleep(5000);
  const st = await api('/api/state');
  check('数据源 notes 含「未映射」', (st.source.notes || []).some((n) => n.includes('未映射')), JSON.stringify(st.source.notes || []).slice(0, 200));
  const res = await api('/api/result?full=true');
  const v = res.quantities.voltage.values.rms;
  check('B/C 相电压 rms=0，A 相>0', v.A > 0 && v.B === 0 && v.C === 0, JSON.stringify(v));
  click($('btn-refresh')); await sleep(800);
  check('刷新后开关勾选且 ub 空', $('cfg-mapen').checked && $('cfg-map-ub').value === '');
  await api('/api/engine/stop', { method: 'POST' });
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ columns: { mapping_enabled: false, mapping: { timestamp: '1', ua: '2', ia: '3', ub: '4', ib: '5', uc: '6', ic: '7' } } }) });

  console.log(`\n结果：${pass} 通过 / ${fail} 失败${fail ? '：' + fails.join('；') : ''}`);
  window.close();
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
