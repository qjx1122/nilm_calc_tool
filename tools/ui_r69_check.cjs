/* 第 69 轮界面检查（v0.69）：总线侧 / 分路侧配置保存按钮统一命名、顶部侧别「分路侧」。
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r69_check.cjs http://127.0.0.1:8000 */
const { JSDOM } = require(require('path').join(process.env.JSDOM_DIR || '/tmp/uitest', 'node_modules/jsdom'));
(async () => {
  const base = process.argv[2];
  const html = await (await fetch(base + '/')).text();
  const dom = new JSDOM(html, { url: base + '/', runScripts: 'outside-only', pretendToBeVisual: true });
  const w = dom.window, d = w.document;
  w.fetch = (u, o) => fetch(new URL(u, base).toString(), o); w.WebSocket = class { constructor(){ setTimeout(()=>this.onclose&&this.onclose(),0);} close(){} };
  w.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, { get: () => () => ({}) });
  w.ResizeObserver = class { observe(){} disconnect(){} };
  const js = await (await fetch(base + '/static/app.js')).text();
  w.eval(js + '\n;window.__buildDual = typeof buildDualViews === "function" ? buildDualViews : null;');
  await new Promise(r => setTimeout(r, 2500));
  try { w.__buildDual && w.__buildDual(); } catch (e) { console.log('buildDual err', e.message); }
  const t = id => (d.getElementById(id) || {}).textContent;
  let fail = 0; const ck = (n, ok, info) => { console.log((ok ? '  ✓ ' : '  ✗ ') + n + (info ? '　' + info : '')); if (!ok) fail++; };
  ck('顶部侧别标签为「分路侧」（无「设备」）', d.querySelector('#topstats-branch .sidename.branch').textContent === '分路侧');
  const bus = ['btn-src-save','btn-savecfg','btn-map-save','btn-ev-save','btn-nilm-save','btn-save-win','btn-save-cfgfile','btn-rt-save'];
  ck('总线侧 8 个配置保存按钮全部为「保存总线侧配置」', bus.every(id => t(id) === '保存总线侧配置'), bus.map(id => id + '=' + t(id)).join(','));
  const br = ['btn-br-save','btn-br-savecfg','btn-br-map-save','btn-ev-save-br','btn-nilm-save-br','btn-save-win-br','btn-save-cfgfile-br','btn-rt-save-br'];
  ck('分路侧 8 个配置保存按钮全部为「保存分路侧配置」', br.every(id => t(id) === '保存分路侧配置'), br.map(id => id + '=' + t(id)).join(','));
  ck('页面上不再出现「分路侧设备」作为侧别名（只允许「分路侧设备联动/数据源」说明）', !/分路侧设备(?!联动|数据源)/.test(d.body.textContent));
  console.log(fail ? `FAIL ${fail}` : 'ALL PASS'); process.exit(fail ? 1 : 0);
})();
