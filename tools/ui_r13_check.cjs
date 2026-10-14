#!/usr/bin/env node
/* 第 13 轮界面检查：离线文件暂停/恢复按钮端到端（真实 index.html + app.js 打真实服务端）。
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
  window.eval(js + '\n;window.__S = () => S;');
  if (typeof window.init === 'function') window.init();
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const api = async (u, o) => (await fetch(BASE + u, o)).json();
  const samples = async () => (await api('/api/state')).engine.samples_in;

  await api('/api/engine/stop', { method: 'POST' });
  console.log('L1 启动前');
  await sleep(1200);
  check('暂停按钮存在', !!$('btn-pause') && !!$('btn-pause2'));
  check('未运行时置灰', $('btn-pause').disabled === true);
  console.log('L2 启动离线文件 → 点暂停');
  click(document.querySelector('.navitem[data-view="source"]')); await sleep(800);
  $('src-kind').value = 'csv_file'; $('src-kind').dispatchEvent(new window.Event('change', { bubbles: true }));
  $('src-path').value = 'data/sample_6400hz.csv';
  check('倍速默认 1×', $('src-file-speed').value === '1', $('src-file-speed').value);
  click($('btn-start2'));
  await sleep(2500);
  const st0 = await api('/api/state');
  check('启动载荷带 file_speed=1（5 s 文件 2.5 s 后仍在播）', st0.running && !st0.finished && st0.config.source.file_speed === 1, `running=${st0.running} finished=${st0.finished} speed=${st0.config.source.file_speed}`);
  check('运行后按钮可用', $('btn-pause').disabled === false, 'disabled=' + $('btn-pause').disabled);
  click($('btn-pause'));
  await sleep(600);
  const s1 = await samples();
  await sleep(1500);
  const s2 = await samples();
  const st = await api('/api/state');
  check('点击后服务端 paused', st.paused === true);
  check('暂停后样本冻结', s1 === s2, `${s1} → ${s2}`);
  check('暂停期间数据时刻不走', (await api('/api/state')).engine.data_t_end === st.engine.data_t_end);
  check('顶栏显示已暂停', $('st-running').textContent === '已暂停', $('st-running').textContent);
  check('按钮文案变恢复', $('btn-pause').textContent === '恢复', $('btn-pause').textContent);
  console.log('L3 点恢复');
  click($('btn-pause'));
  await sleep(1500);
  const s3 = await samples();
  check('恢复后样本增长', s3 > s2, `${s2} → ${s3}`);
  check('按钮文案变暂停', $('btn-pause').textContent === '暂停', $('btn-pause').textContent);
  await api('/api/engine/stop', { method: 'POST' });
  console.log(`\n结果：${pass} 通过，${fail} 失败${fail ? '：' + fails.join('；') : ''}`);
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
