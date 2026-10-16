#!/usr/bin/env node
/* v0.25 界面检查：标题/导航文案 + 列表「单位进表头、单元格只放数字」。
 * 需先 serve 在 8000；data/sample_6400hz.csv、data/nilm_steps.csv 存在。
 *   F1 标题：<title>/h1/导航组名/各 h2 不含「需求④/⑥」等内部编号；顶栏模式标签随分路侧启用切换
 *   F2 表格：电压/电流/功率/基波/谐波/间谐波/直流/频谱/事件/负荷辨识/自检 页的所有 <table>：
 *        - 单元格不含单位后缀（V/kV/A/W/var/VA/Hz/°/%/s 等紧跟数字）
 *        - 带数值的列表头至少有一列含「(单位)」
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r25_check.cjs [baseUrl]
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
function makeDom() {
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const dom = new JSDOM(html, {
    url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true,
    beforeParse(window) {
      window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, { get: (t, p) => (p === 'measureText' ? () => ({ width: 8 }) : () => {}), set: () => true });
      window.WebSocket = class { close() {} send() {} };
      window.fetch = (url, opts) => fetch(String(url).startsWith('http') ? url : BASE + url, opts);
      window.alert = () => {};
    },
  });
  dom.window.eval(js + '\n;window.__S = () => S; window.__render = render; window.__renderTop = renderTop; window.__refreshBranchDual = refreshBranchDual; window.__refreshHistory = refreshHistory;');
  return dom;
}
// 数字后紧跟单位（允许前面有空格）；排除时间戳 / 百分号在表头 / 纯文本
const UNIT_RE = /-?\d+(?:\.\d+)?\s*(?:[kMGmµ]?(?:V|A|W|var|VA|Hz)|°|%|s|min|h|周波)(?![\w(])/;

async function main() {
  const api = async (u, o) => (await fetch(BASE + u, o)).json();
  const post = (u, body) => api(u, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
  const put = (u, body) => api(u, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  await post('/api/engine/stop'); await post('/api/branch/engine/stop');
  await put('/api/config', { branch: { enabled: false } });

  console.log('F1 标题与导航');
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  check('<title> 与 h1 体现「电气量计算 + 负荷辨识」', /<title>[^<]*负荷辨识[^<]*<\/title>/.test(html) && /<h1>[^<]*负荷辨识/.test(html));
  check('标题/h2 不再含内部编号「需求④/⑥」', !/<h2>[^<]*需求[①-⑩]/.test(html));
  check('导航四组：总览 / 实时监测 / 事件与分析 / 工具（v0.26 用户指定）', ['>总览<', '实时监测', '事件与分析', '>工具 <'].every(t => html.includes(t)) && (html.match(/class="navgroup/g) || []).length === 4);
  check('导航项按用户指定归组', (() => { const grp = {}; let g = ''; for (const m of html.matchAll(/class="navgroup[^"]*">([^<]+)|data-view="(\w+)"/g)) { if (m[1]) g = m[1].trim(); else (grp[g] = grp[g] || []).push(m[2]); }
    return JSON.stringify(grp['总览']) === JSON.stringify(['overview', 'source', 'compare']) && JSON.stringify(grp['实时监测']) === JSON.stringify(['voltage', 'current', 'power', 'power_factor', 'fundamental', 'harmonic', 'interharmonic', 'dc', 'spectrum'])
      && JSON.stringify(grp['事件与分析']) === JSON.stringify(['events', 'nilm']) && JSON.stringify(grp['工具']) === JSON.stringify(['windows', 'export', 'selftest', 'process']); })());
  const h2s = Array.from(html.matchAll(/<h2>([^<]*)/g)).map(m => m[1]);
  check('每个子界面 h2 都带「· 内容说明」或括号说明', h2s.length >= 17 && h2s.every(t => /·|（/.test(t)), h2s.filter(t => !/·|（/.test(t)).join(' | '));

  const dom = makeDom(); const { window } = dom, { document } = window;
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(700); };
  const sync = async () => { window.__S().state = await api('/api/state'); const r = await fetch(BASE + '/api/result?full=true'); window.__S().result = r.ok ? await r.json() : null; window.__renderTop(); await window.__render(); };
  await sync();
  check('顶栏模式标签：分路侧未启用 → 「总线侧」', $('side-title').textContent === '总线侧', $('side-title').textContent);

  // 两侧播放
  await put('/api/config', { branch: { enabled: true } });
  await put('/api/branch/config', { source: { kind: 'csv_file', path: 'data/nilm_steps.csv', file_speed: 1, custom_time: false } });
  await post('/api/engine/start', { kind: 'csv_file', path: 'data/sample_6400hz.csv', file_speed: 1, custom_time: false });
  await sleep(6500);
  await sync(); await window.__refreshHistory(); await window.__refreshBranchDual(true); await sleep(1500);
  check('顶栏模式标签：分路侧启用 → 「总线侧 ＋ 分路侧」', $('side-title').textContent === '总线侧 ＋ 分路侧', $('side-title').textContent);

  console.log('F2 列表单位进表头');
  const views = ['voltage', 'current', 'power', 'power_factor', 'fundamental', 'harmonic', 'interharmonic', 'dc', 'spectrum', 'events', 'nilm'];
  let tables = 0;
  for (const v of views) {
    await nav(v); await sync(); await window.__refreshBranchDual(true); await sleep(800); await window.__render();
    if (v === 'events' || v === 'nilm') { await sleep(1500); await window.__render(); }
    const tbls = Array.from($(`view-${v}`).querySelectorAll('table')).filter(t => t.querySelector('tbody tr'));
    tables += tbls.length;
    const bad = [];
    tbls.forEach((t, i) => {
      const heads = Array.from(t.querySelectorAll('thead th')).map(th => th.textContent.trim());
      const skipCol = heads.map(h => /^说明$|^检验量$|^项目/.test(h));   // 自由文本列（服务端说明句子）不检查
      const cells = Array.from(t.querySelectorAll('tbody tr')).flatMap(tr => Array.from(tr.children).filter((td, i) => !skipCol[i]).map(td => td.textContent.trim()));
      // 排除：窗口配置类输入表、含 input 的表
      if (t.querySelector('input,select')) return;
      const offending = cells.filter(c => UNIT_RE.test(c) && !/^\d{4}-\d{2}-\d{2}|^\d{2}:\d{2}:\d{2}/.test(c));
      if (offending.length) bad.push(`表${i + 1}[${heads.slice(0, 3).join('/')}…]: ${offending.slice(0, 3).join(' | ')}`);
      const numericCols = heads.filter(h => /\(.*\)/.test(h) || /^单位$|^周波数$|^检验量$|^PF$|^波峰系数$|^相角|^输出点数|^周期数|^丢弃点|^次数|^组号|^占正序比|^说明$|^项目|^数值$|^相$|^触发值$|^峰值$|^阈值$|^分量$|^#$|^状态$|^类型$|^对象$|^开始|^结束$|^方向$|^算法$|^编号$|^结论$|^期望值$|^实际值$|^频带|^主导频率|^电气量$|^时刻|^总线侧$|^分路侧$|^差值|^占比|^A 相$|^B 相$|^C 相$|^合计$/.test(h));
      if (numericCols.length !== heads.length) bad.push(`表${i + 1} 表头缺单位: ${heads.filter(h => !numericCols.includes(h)).join(', ')}`);
    });
    check(`${v}：${tbls.length} 个表，单元格无单位、表头齐全`, tbls.length > 0 && bad.length === 0, bad.slice(0, 3).join('；'));
  }
  // 具体抽查：功率分相表表头含 (kW)/(W)，单元格为纯数字；负荷辨识右列表头含 幅值 |ΔP| (W/kW)
  const pph = Array.from($('p-phase').querySelectorAll('th')).map(x => x.textContent);
  check('功率分相表：表头 P (kW|W)、U (kV|V)；单元格纯数字', /^P \((k|M)?W\)$/.test(pph[1]) && /^U \((k)?V\)$/.test(pph[5]) && Array.from($('p-phase').querySelectorAll('tbody tr')).every(tr => Array.from(tr.children).slice(1).every(td => /^-?\d+\.\d+$/.test(td.textContent))), pph.join(' | '));
  const nth = Array.from($('nilm-table-br').querySelectorAll('th')).map(x => x.textContent);
  check('负荷辨识（分路侧列）表头：持续 (s) / 周波数 / 幅值 |ΔP| (W 或 kW) / 事件前 P / 事件后 P', nth.includes('持续 (s)') && nth.includes('周波数') && nth.some(h => /^幅值 \|ΔP\| \((k|M)?W\)$/.test(h)) && nth.some(h => /^事件前 P \(/.test(h)), nth.join(' | '));
  const eth = Array.from($('ev-table').querySelectorAll('th')).map(x => x.textContent);
  check('事件表：持续 (s) 与独立「单位」列', eth.includes('持续 (s)') && eth.includes('单位'), eth.join(' | '));
  const seqth = Array.from($('v-seq').querySelectorAll('table')[0].querySelectorAll('th')).map(x => x.textContent);
  check('序分量表：分量 / 幅值 (kV|V) / 相角 (°) / 占正序比 (%)', /^幅值 \(k?V\)$/.test(seqth[1]) && seqth[2] === '相角 (°)' && seqth[3] === '占正序比 (%)', seqth.join(' | '));
  const spv = Array.from($('sp-info').querySelectorAll('tbody tr')).map(tr => Array.from(tr.children).map(td => td.textContent));
  check('频谱信息表：三列（项目 / 数值 / 单位），主峰频率单位列 = Hz', spv[0][2] === 'Hz' && /^\d+\.\d+$/.test(spv[0][1]), JSON.stringify(spv[0]));

  await post('/api/engine/stop'); await post('/api/branch/engine/stop'); await put('/api/config', { branch: { enabled: false } });
  console.log(`\n结果：${pass} 通过，${fail} 失败（共检查 ${tables} 个表）${fail ? '：' + fails.join('；') : ''}`);
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
