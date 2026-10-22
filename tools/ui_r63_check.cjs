#!/usr/bin/env node
/* ui_r63_check.cjs —— v0.63 数据源页「保存总线侧配置」+ 配置落盘只更新改动键（需服务在跑且 ELEC_TOOL_PERSIST_CONFIG=1；
   用法 TZ=Asia/Shanghai JSDOM_DIR=/tmp/uitest CFG_FILE=<服务的 runtime 配置文件> node tools/ui_r63_check.cjs http://127.0.0.1:8000） */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require(path.join(process.env.JSDOM_DIR || '/tmp/uitest', 'node_modules/jsdom'));
const BASE = process.argv[2] || 'http://127.0.0.1:8000';
const CFG_FILE = process.env.CFG_FILE || '';
const ROOT = path.resolve(__dirname, '..');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let pass = 0, fail = 0; const fails = [];
function check(name, ok, detail = '') {
  if (ok) { pass++; console.log(`  ✓ ${name}${detail ? '　' + detail : ''}`); }
  else { fail++; fails.push(name); console.log(`  ✗ ${name}　${detail}`); }
}
function flat(d, p = '', out = {}) { for (const k of Object.keys(d)) { const v = d[k]; if (v && typeof v === 'object' && !Array.isArray(v)) flat(v, p + k + '.', out); else out[p + k] = JSON.stringify(v); } return out; }
function diffKeys(a, b) { const fa = flat(a), fb = flat(b); const ks = new Set([...Object.keys(fa), ...Object.keys(fb)]); return [...ks].filter(k => fa[k] !== fb[k]).sort(); }
function makeDom(calls) {
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const dom = new JSDOM(html, {
    url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true,
    beforeParse(window) {
      window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, { get: (t, p) => (p === 'measureText' ? () => ({ width: 8 }) : p === 'createLinearGradient' ? () => ({ addColorStop() {} }) : () => {}), set: () => true });
      window.HTMLCanvasElement.prototype.toDataURL = () => 'data:image/png;base64,';
      Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', { get() { return 900; } });
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
  window.eval(js + '\n;window.__S = () => S; window.__saveBusSource = saveBusSource; window.__startEngine = startEngine; window.__collectBusSavePayload = collectBusSavePayload;');
  return dom;
}
async function main() {
  const calls = [];
  const dom = makeDom(calls); const { window } = dom; const $ = (s) => window.document.querySelector(s);
  await sleep(1500);
  await fetch(BASE + '/api/engine/stop', { method: 'POST' });
  window.document.querySelector('.navitem[data-view="source"]').click();
  await sleep(300);
  const btn = $('#btn-src-save');
  check('总线侧「数据源」分组有「保存总线侧配置」按钮（在「启动数据源」同一行）', !!btn && btn.textContent.includes('保存总线侧配置') && btn.parentElement === $('#btn-start2').parentElement);
  const readCfg = () => (CFG_FILE && fs.existsSync(CFG_FILE)) ? JSON.parse(fs.readFileSync(CFG_FILE, 'utf8')) : null;
  const before = readCfg();
  check('CFG_FILE 已给出且可读（用于核对落盘）', !!before, CFG_FILE);
  // 1) 启动数据源（离线文件）不写配置文件
  $('#src-kind').value = 'csv_file'; $('#src-kind').dispatchEvent(new window.Event('change'));
  $('#src-path').value = 'data/nilm_steps.csv'; $('#src-file-speed').value = '0';
  await window.__startEngine(); await sleep(500);
  const after1 = readCfg();
  check('「启动数据源」后配置文件未改动', before && JSON.stringify(after1) === JSON.stringify(before));
  check('启动提示说明启动不写配置文件、要保留请点「保存总线侧配置」', /保存总线侧配置/.test($('#toast').textContent), $('#toast').textContent.slice(0, 120));
  await fetch(BASE + '/api/engine/stop', { method: 'POST' }); await sleep(200);
  // 2) 保存总线侧配置：source + 量纲 + 列映射
  const payload = window.__collectBusSavePayload().payload;
  check('保存载荷含 source（kind/path/file_speed…）+ transform + sampling + harmonic + power + columns', payload.source && payload.source.kind === 'csv_file' && /data\/nilm_steps\.csv$/.test(payload.source.path) && 'transform' in payload && 'sampling' in payload && 'power' in payload && 'columns' in payload, Object.keys(payload).join(','));
  $('#src-file-speed').value = '2';
  await window.__saveBusSource(); await sleep(500);
  const put = calls.filter(x => x.url === '/api/config' && x.method === 'PUT').pop();
  check('点击后发 PUT /api/config（总线侧，非 /api/branch/config）且 200', put && put.status === 200, put && put.url);
  const after2 = readCfg();
  check('文件里 source 已更新为 csv_file / data/nilm_steps.csv / 倍速 2', after2 && after2.source.kind === 'csv_file' && after2.source.path === 'data/nilm_steps.csv' && after2.source.file_speed === 2, after2 && JSON.stringify(after2.source).slice(0, 120));
  const dk = diffKeys(before, after2);
  check('除 source / transform / sampling / harmonic / power / columns 外其它键原样保留（含自定义键）', dk.every(k => /^(source|transform|sampling|harmonic|power|columns)\./.test(k)) && (!('my_custom_note' in before) || after2.my_custom_note === before.my_custom_note), '变化键：' + dk.join(','));
  check('nilm 等未参与保存的节不变', JSON.stringify(after2.nilm) === JSON.stringify(before.nilm) && JSON.stringify(after2.output) === JSON.stringify(before.output));
  check('提示含写入的文件路径', /已写入/.test($('#toast').textContent) && /runtime|json/.test($('#toast').textContent), $('#toast').textContent.slice(0, 120));
  // 3) 文件方式路径为空 → 前端拦截、不发请求
  const n0 = calls.filter(x => x.url === '/api/config' && x.method === 'PUT').length;
  $('#src-path').value = ''; await window.__saveBusSource(); await sleep(200);
  check('文件方式路径为空 → 前端提示、不发请求', calls.filter(x => x.url === '/api/config' && x.method === 'PUT').length === n0 && /路径/.test($('#toast').textContent), $('#toast').textContent.slice(0, 80));
  console.log(`\nPASS ${pass} / FAIL ${fail}` + (fail ? '\n  失败：' + fails.join('；') : ''));
  process.exit(fail ? 1 : 0);
}
main().catch(e => { console.error(e); process.exit(2); });
