#!/usr/bin/env node
/* 第 11 轮界面检查：数据源页「文件时标按 UTC 解释」开关（source.file_time_utc）。
 * jsdom 驱动真实 index.html + app.js，打真实服务端（需先 serve 在 8000，data/sample_6400hz.csv 存在）。
 *
 *   T1 勾选框存在并回填服务端值；csv_file 且未启用自定义时间时可用；勾选自定义时间后灰显
 *   T2 取消勾选 → 启动 csv_file → POST /api/engine/start 载荷 file_time_utc=false；状态 tz_offset_h=本机偏移；摘要显示「与文件一致」
 *   T3 勾选 → 启动 → 载荷 file_time_utc=true；状态 tz_offset_h=0；t_start 相差 偏移×3600
 *
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r11_check.cjs [baseUrl]
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

  await api('/api/engine/stop', { method: 'POST' });
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source: { file_time_utc: true, custom_time: false } }) });
  await nav('source'); click($('btn-refresh')); await sleep(800);
  console.log('T1 勾选框');
  check('存在且回填服务端值 true', !!$('src-utc') && $('src-utc').checked === true);
  $('src-kind').value = 'csv_file'; change($('src-kind'));
  check('csv_file 且未自定义时间 → 可用', !$('src-utc').disabled);
  $('src-customtime').checked = true; change($('src-customtime'));
  check('启用自定义时间 → 灰显', $('src-utc').disabled);
  $('src-customtime').checked = false; change($('src-customtime'));
  check('关闭自定义时间 → 恢复可用', !$('src-utc').disabled);

  const run = async (utc) => {
    $('src-utc').checked = utc;
    $('src-path').value = 'data/clock_0000.csv';
    click($('btn-start2')); await sleep(3500);
    const b = bodies('/api/engine/start', 'POST'); const last = b[b.length - 1] || {};
    const st = await api('/api/state');
    await api('/api/engine/stop', { method: 'POST' });
    return { last, st };
  };
  console.log('T2 不按 UTC（与文件一致）');
  let r = await run(false);
  check('start 载荷 file_time_utc=false', r.last.file_time_utc === false, JSON.stringify(r.last));
  check('状态 tz_offset_h=本机偏移 (8)', r.st.source.tz_offset_h === 8, String(r.st.source.tz_offset_h));
  check('摘要显示「与文件一致」', ($('src-summary').textContent || '').includes('与文件一致'));
  const tA = r.st.source.t_start;
  console.log('T3 按 UTC');
  r = await run(true);
  check('start 载荷 file_time_utc=true', r.last.file_time_utc === true);
  check('状态 tz_offset_h=0', r.st.source.tz_offset_h === 0);
  check('t_start 相差 8 h', Math.abs((r.st.source.t_start - tA) - 8 * 3600) < 1e-3, String(r.st.source.t_start - tA));
  check('配置回显 file_time_utc=true', r.st.config.source.file_time_utc === true);
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source: { file_time_utc: false } }) });

  console.log(`\n结果：${pass} 通过 / ${fail} 失败${fail ? '：' + fails.join('；') : ''}`);
  window.close();
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
