/* 第 93 轮界面检查（v0.72）：数据处理页「负荷辨识调参」基准配置独立于总线侧 / 分路侧运行配置，各配置可单独修改。
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r72_check.cjs http://127.0.0.1:8033   （需 data/nilm_bus_mixed.csv） */
const fs = require('fs'), path = require('path');
const { JSDOM } = require(path.join(process.env.JSDOM_DIR || '/tmp/uitest', 'node_modules/jsdom'));
const ROOT = path.join(__dirname, '..'); const BASE = (process.argv[2] || 'http://127.0.0.1:8000').replace(/\/$/, '');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function main() {
  const J = async (u, o) => (await fetch(BASE + u, o)).json();
  const put = (u, b) => J(u, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
  await J('/api/engine/stop', { method: 'POST' }); await J('/api/branch/engine/stop', { method: 'POST' });
  // 两侧运行配置故意不同：总线侧 PT=123，分路侧 PT=100 CT=5
  await put('/api/config', { transform: { enabled: true, pt_ratio: 123, ct_ratio: 15 } });
  await put('/api/branch/config', { transform: { enabled: true, pt_ratio: 100, ct_ratio: 5 }, nilm: { quantity: 'p', channels: ['B'] } });
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8'); const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const calls = []; const store = {};
  const dom = new JSDOM(html, { url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true, beforeParse(window) {
    window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, { get: (t, p) => (p === 'measureText' ? () => ({ width: 8 }) : p === 'createLinearGradient' ? () => ({ addColorStop() {} }) : () => {}), set: () => true });
    window.WebSocket = class { constructor() { this.readyState = 0; } close() {} send() {} };
    window.fetch = async (url, opts = {}) => { const abs = String(url).startsWith('http') ? String(url) : BASE + url; const r = await fetch(abs, opts); calls.push({ url: String(url), method: opts.method || 'GET', status: r.status, body: opts.body || null }); return r; };
    window.alert = () => {};
  } });
  const { window } = dom, { document } = window;
  window.__toasts = [];
  window.eval(js + '\n;window.__S = () => S; window.__NT = NT; const __toast0 = toast; toast = function (m, k) { window.__toasts.push([String(m), k]); return __toast0(m, k); };');
  if (typeof window.init === 'function') window.init();
  await sleep(1500);
  const $ = (id) => document.getElementById(id);
  const click = (el) => el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const change = (el) => el.dispatchEvent(new window.Event('change', { bubbles: true }));
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(1200); };
  let fail = 0; const check = (n, ok, info) => { console.log((ok ? '  ✓ ' : '  ✗ ') + n + (info ? '　' + info : '')); if (!ok) fail++; };
  const lastPost = () => calls.filter((c) => /\/api\/(branch\/)?process\/nilm_tune$/.test(c.url) && c.method === 'POST').pop();
  await nav('process'); await sleep(1500);

  console.log('— 独立基准配置（默认）');
  check('基准配置下拉默认＝独立基准配置', $('nt-side').value === 'custom', $('nt-side').value);
  check('独立基准配置分组可见，含 fs / f_nom / PT·CT / UTC / PT / CT（检测量不重复出现）', $('nt-base').style.display !== 'none' && ['nt-base-fs', 'nt-base-fnom', 'nt-base-ptct', 'nt-base-utc', 'nt-base-pt', 'nt-base-ct'].every((i) => !!$(i)));
  check('独立基准分组内没有第二个检测量 / 检测对象控件（只在下方各一处）', !document.getElementById('nt-base-q') && document.querySelectorAll('#nt-form select[id^="nt-quantity"]').length === 1 && document.querySelectorAll('#nt-form select[id^="nt-channel"]').length === 1 && /出厂缺省 auto/.test($('nt-quantity-follow').textContent));
  check('初值＝出厂配置（PT=100 CT=15 fs=6400），不是总线侧运行配置的 PT=123', $('nt-base-pt').value === '100' && $('nt-base-ct').value === '15' && $('nt-base-fs').value === '6400', `${$('nt-base-pt').value}/${$('nt-base-ct').value}/${$('nt-base-fs').value}`);
  // 单独修改：PT=77，去掉 PT/CT
  $('nt-base-pt').value = '77'; change($('nt-base-pt')); $('nt-base-ptct').checked = false; change($('nt-base-ptct'));
  let saved = null; try { saved = JSON.parse(window.localStorage.getItem('elec_tool.nilm_tune.base')); } catch (e) {}
  check('修改后自动保存到浏览器本地（PT=77、PT/CT 关闭）', saved && saved.pt_ratio === '77' && saved.pt_ct_enabled === '0', JSON.stringify(saved));
  $('nt-path').value = 'data/nilm_bus_mixed.csv'; $('nt-duration').value = '2';
  click($('btn-nt-run')); await sleep(4000);
  let c = lastPost(); let b = c && JSON.parse(c.body);
  check('调参请求 base_mode=custom 且 base 为界面值（PT=77、PT/CT 关）', b && b.base_mode === 'custom' && b.base && b.base.pt_ratio === '77' && b.base.pt_ct_enabled === '0', c && c.body.slice(0, 200));
  let d = window.__NT.last;
  check('结果按独立基准配置计算：scaled=false（二次侧口径），base.pt_ratio=77', d && d.scaled === false && d.base && d.base.pt_ratio === 77 && d.base_mode === 'custom', d && JSON.stringify(d.base));
  check('结果区显示「独立基准配置」与落盘文件 nilm_tune_base.json', /独立基准配置/.test($('nt-status').textContent) && /nilm_tune_base\.json/.test($('nt-status').textContent));
  check('等价命令 --config 指向 nilm_tune_base.json', /--config \S*nilm_tune_base\.json/.test(d.command), d.command);
  const bus = await J('/api/config'); const br = await J('/api/branch/config');
  check('两侧运行配置未被改动（总线侧 PT 仍 123、分路侧 CT 仍 5）', bus.transform.pt_ratio === 123 && bus.transform.enabled === true && br.transform.ct_ratio === 5, `${bus.transform.pt_ratio}/${br.transform.ct_ratio}`);

  console.log('— 填入 / 恢复');
  click($('btn-nt-base-bus')); await sleep(800);
  check('「填入总线侧值」→ PT=123、PT/CT 开（走 /api/process/nilm_tune/base?source=running）', $('nt-base-pt').value === '123' && $('nt-base-ptct').checked && calls.some((x) => /^\/api\/process\/nilm_tune\/base\?source=running/.test(x.url)), $('nt-base-pt').value);
  click($('btn-nt-base-branch')); await sleep(800);
  check('「填入分路侧值」→ CT=5（走 /api/branch/process/nilm_tune/base）', $('nt-base-ct').value === '5' && calls.some((x) => /^\/api\/branch\/process\/nilm_tune\/base\?source=running/.test(x.url)), $('nt-base-ct').value);
  $('nt-base-ct').value = '9'; change($('nt-base-ct'));
  const br2 = await J('/api/branch/config');
  check('改独立基准 CT=9 不影响分路侧运行配置（仍 5）', br2.transform.ct_ratio === 5);
  click($('btn-nt-base-default')); await sleep(800);
  check('「恢复出厂」→ PT=100 CT=15', $('nt-base-pt').value === '100' && $('nt-base-ct').value === '15');

  console.log('— 检测量 / 检测对象：独立基准可单独改，沿用某侧时随该侧且不可改');
  check('独立基准下「检测量 / 检测对象」可编辑', !$('nt-quantity').disabled && !$('nt-channel').disabled);
  $('nt-quantity').value = 'i'; $('nt-channel').value = 'C';
  click($('btn-nt-run')); await sleep(4000);
  c = lastPost(); b = JSON.parse(c.body); d = window.__NT.last;
  check('独立基准：请求带 quantity=i channel=C，结果按之计算', b.quantity === 'i' && b.channel === 'C' && d.quantity === 'i' && d.channel === 'C', `${d.quantity}/${d.channel}`);
  console.log('— 沿用某侧运行配置（旧行为仍可选）');
  $('nt-side').value = 'branch'; change($('nt-side')); await sleep(1000);
  check('选「沿用分路侧运行配置」后独立基准分组隐藏', $('nt-base').style.display === 'none');
  check('检测量 / 检测对象被禁用并显示分路侧配置值（p / B）', $('nt-quantity').disabled && $('nt-channel').disabled && $('nt-quantity').value === 'p' && $('nt-channel').value === 'B', `${$('nt-quantity').value}/${$('nt-channel').value}`);
  click($('btn-nt-run')); await sleep(4000);
  c = lastPost(); b = JSON.parse(c.body); d = window.__NT.last;
  check('请求走 /api/branch/process/nilm_tune，base_mode=running，不上送 quantity/channel，结果 base.ct_ratio=5、按分路侧 p / B 计算', /^\/api\/branch\//.test(c.url) && b.base_mode === 'running' && !b.base && b.quantity === null && b.channel === null && d.base && d.base.ct_ratio === 5 && d.quantity === 'p' && d.channel === 'B', c.url + ' ' + d.quantity + '/' + d.channel);
  $('nt-side').value = 'custom'; change($('nt-side')); await sleep(300);
  check('切回独立基准：检测量 / 检测对象恢复可编辑并还原用户选择（i / C）', !$('nt-quantity').disabled && $('nt-quantity').value === 'i' && $('nt-channel').value === 'C', `${$('nt-quantity').value}/${$('nt-channel').value}`);
  $('nt-quantity').value = ''; $('nt-channel').value = '';

  console.log('— 套用目标独立于基准配置');
  check('有「套用目标」下拉（总线侧 / 分路侧）', !!$('nt-apply-side') && $('nt-apply-side').options.length === 2);
  click($('btn-nt-run')); await sleep(4000);
  $('nt-apply-side').value = 'branch';
  click($('btn-nt-apply')); await sleep(2500);
  const ap = calls.filter((x) => /nilm\/tune\/apply$/.test(x.url)).pop();
  const br3 = await J('/api/branch/config'); const bus3 = await J('/api/config');
  check('独立基准配置 + 套用目标＝分路侧 → 请求 /api/branch/nilm/tune/apply，分路侧 nilm 参数已更新、总线侧未变', ap && /^\/api\/branch\//.test(ap.url) && br3.nilm.quantity === d.quantity && bus3.transform.pt_ratio === 123, ap && ap.url);
  check('分路侧 PT/CT 未被套用改动（仍 CT=5）', br3.transform.ct_ratio === 5);

  // 还原两侧运行配置（不留状态给其它检查脚本）
  await put('/api/config', { transform: { enabled: true, pt_ratio: 100, ct_ratio: 15 } });
  await put('/api/branch/config', { transform: { enabled: true, pt_ratio: 100, ct_ratio: 15 }, nilm: { quantity: 'auto', channels: ['total'] } });
  console.log(fail ? `FAIL ${fail}` : 'ALL PASS');
  window.close(); process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
