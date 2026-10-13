#!/usr/bin/env node
/* 第 9 轮界面功能端到端检查：「间谐波」「直流偏置」「事件」三个子界面。
 * jsdom 驱动真实 index.html + app.js，打真实服务端（需先 serve 在 8000，data/sample_6400hz.csv 存在）。
 *
 *   N1 导航含三项；离线播放样例 CSV 后，间谐波页卡片/表格/趋势有值；直流页卡片/表格有值且中性线直流存在
 *   N2 窗口配置页出现 interharmonic / dc 两行且为 FFT 类（策略禁用）
 *   N3 事件页：汇总卡片、历史表（样例含 3/5 次谐波 → 谐波相量超限事件）、类型过滤只剩所选类型
 *   N4 阈值表单回填服务端配置；改 THD_U 上限 → 保存 → PUT /api/config 载荷含 events；
 *      抬高到 50% 后活动事件复归（表中出现「已结束」）；再改回 5%
 *   N5 清空 → 历史表为空
 *
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r9_check.cjs [baseUrl]
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

  // 还原阈值、清空事件，启动离线播放样例
  await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ events: { thd_u_limit_pct: 5, hr_u_limit_pct: 5, thd_i_limit_pct: 10, enabled: true } }) });
  await api('/api/events/clear', { method: 'POST' });
  await api('/api/engine/start', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source: { kind: 'csv_file', path: 'data/sample_6400hz.csv', realtime: false } }) });
  await sleep(5000);
  // 轮询拉结果（WebSocket 已桩掉，走 startPolling 需要 ws 关闭事件；这里手动灌入）
  window.__S().result = await api('/api/result?full=true');
  window.__S().state = await api('/api/state');

  console.log('\n=== N1. 间谐波 / 直流偏置 子界面 ===');
  for (const [v, label] of [['interharmonic', '间谐波'], ['dc', '直流偏置'], ['events', '事件']]) {
    const b = document.querySelector(`.navitem[data-view="${v}"]`);
    check(`导航含「${label}」`, !!b && b.textContent.includes(label));
  }
  await nav('interharmonic'); await sleep(1500);
  check('view-interharmonic 激活', $('view-interharmonic').classList.contains('active'));
  check('间谐波卡片含 TIHD_U/TIHD_I 与最大组', /TIHD_U A 相/.test($('ih-cards').textContent) && /最大电流间谐波组/.test($('ih-cards').textContent), $('ih-cards').textContent.slice(0, 120));
  check('间谐波相量表有行（相/组/主导频率/相角）', $('ih-table-u').querySelectorAll('tbody tr').length >= 3 && /主导相角/.test($('ih-table-u').textContent));
  check('窗口口径注记含整数周期与分辨率', /整数周期/.test($('ih-win').textContent));
  check('TIHD 趋势已请求 /api/history/interharmonic', calls.some((c) => c.url.includes('/api/history/interharmonic')));
  await nav('dc'); await sleep(1200);
  check('view-dc 激活', $('view-dc').classList.contains('active'));
  check('直流卡片含三相电压/电流直流与中性线', /A 相电压直流/.test($('dc-cards').textContent) && /中性线直流/.test($('dc-cards').textContent));
  check('电流直流表含 N (Ia+Ib+Ic) 行', /N \(Ia\+Ib\+Ic\)/.test($('dc-table-i').textContent));
  check('直流趋势已请求 /api/history/dc', calls.some((c) => c.url.includes('/api/history/dc')));

  console.log('\n=== N2. 窗口配置页 ===');
  await nav('windows'); await sleep(500);
  const selIh = document.querySelector('select[data-w="interharmonic"][data-f="policy"]');
  const selDc = document.querySelector('select[data-w="dc"][data-f="policy"]');
  check('窗口表含 interharmonic/dc 两行且策略锁定为整周期（FFT 类）', !!selIh && !!selDc && selIh.disabled && selDc.disabled);
  const dcRm = document.querySelector('input[data-w="dc"][data-f="remove_dc"]');
  check('dc 行默认不去直流', !!dcRm && !dcRm.checked);

  console.log('\n=== N3. 事件页 ===');
  await nav('events'); await sleep(1500);
  check('view-events 激活', $('view-events').classList.contains('active'));
  check('汇总卡片含 6 类事件名', ['基波相量超限', '谐波相量超限', '间谐波相量超限', '频率超限', '频率变化率超限', '功率振荡'].every((n) => $('ev-cards').textContent.includes(n)));
  check('基波有效阈值卡片显示 PT/CT 折算（×100/×15）', /×100\/×15/.test($('ev-cards').textContent), $('ev-cards').textContent.match(/折算[^）]*/)?.[0]);
  const rows = () => [...$('ev-table').querySelectorAll('tbody tr')];
  check('历史表出现谐波相量超限事件（样例含 3/5 次谐波）', rows().some((r) => /谐波相量超限/.test(r.textContent) && /HR_U-A-h3|THD_U-A/.test(r.textContent)), `${rows().length} 行`);
  check('活动事件表有行且状态为「活动」', $('ev-active').querySelectorAll('tbody tr').length > 0 && /活动/.test($('ev-active').textContent));
  check('导航徽标显示活动事件数', $('nav-ev-badge').style.display !== 'none' && +$('nav-ev-badge').textContent > 0, $('nav-ev-badge').textContent);
  $('ev-filter').value = 'freq'; change($('ev-filter')); await sleep(900);
  check('类型过滤=频率超限 → 表中无其他类型', rows().every((r) => /频率超限/.test(r.textContent)), `${rows().length} 行`);
  $('ev-filter').value = ''; change($('ev-filter')); await sleep(900);

  console.log('\n=== N4. 阈值表单 ===');
  const cfg = await api('/api/config');
  check('表单回填 THD_U 上限 = 服务端值', +$('ev-thd_u_limit_pct').value === cfg.events.thd_u_limit_pct, `${$('ev-thd_u_limit_pct').value} vs ${cfg.events.thd_u_limit_pct}`);
  check('表单回填 f_high / 二次侧勾选', +$('ev-f_high').value === cfg.events.f_high && $('ev-limits_secondary').checked === cfg.events.limits_secondary);
  $('ev-thd_u_limit_pct').value = '50'; input($('ev-thd_u_limit_pct'));
  $('ev-hr_u_limit_pct').value = '50'; input($('ev-hr_u_limit_pct'));
  $('ev-thd_i_limit_pct').value = '50'; input($('ev-thd_i_limit_pct'));
  click($('btn-ev-save')); await sleep(1200);
  const put = bodies('/api/config', 'PUT').pop();
  check('保存 → PUT /api/config 载荷含 events.thd_u_limit_pct=50', !!put && put.events && put.events.thd_u_limit_pct === 50, JSON.stringify(put && put.events).slice(0, 100));
  check('服务端配置已热更新', (await api('/api/config')).events.thd_u_limit_pct === 50);
  await sleep(2500); click($('btn-ev-refresh')); await sleep(900);
  check('阈值抬高后谐波事件复归（表中出现「已结束」且无活动）', rows().some((r) => /已结束/.test(r.textContent)) && $('ev-active').querySelectorAll('tbody tr').length === 0, `${rows().length} 行`);
  $('ev-thd_u_limit_pct').value = '5'; input($('ev-thd_u_limit_pct'));
  $('ev-hr_u_limit_pct').value = '5'; input($('ev-hr_u_limit_pct'));
  $('ev-thd_i_limit_pct').value = '10'; input($('ev-thd_i_limit_pct'));
  click($('btn-ev-save')); await sleep(800);
  check('阈值改回 5/5/10', (await api('/api/config')).events.thd_u_limit_pct === 5);

  console.log('\n=== N5. 清空 ===');
  click($('btn-ev-clear')); await sleep(1200);
  check('清空后历史表为空', rows().length === 0 && calls.some((c) => c.url.includes('/api/events/clear') && c.method === 'POST'));

  await api('/api/engine/stop', { method: 'POST' });
  console.log(`\n结果：${pass} 通过，${fail} 失败${fail ? '：' + fails.join('；') : ''}`);
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
