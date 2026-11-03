#!/usr/bin/env node
/* 第 186 轮：负荷辨识事件界面算法配置「两层布局」行为级检查（jsdom 驱动真实 index.html + app.js，打真实服务端）。
 *
 * 布局（v0.99.33）：
 *   大模块① 7 个算法公共配置（#nilm-common7 > #nilm-form）＝ 启用 / 落盘 / 检测量 / 周波窗长 / 最小事件间隔
 *   大模块② 7 个算法配置（#nilm-algos）
 *     ②-1 前 6 个算法配置（#nilm-scalar-group > #nilm-scalar-algos 动态 6 面板
 *                         + #nilm-scalar-common > #nilm-form-scalar 检测对象/自适应/rel_tol/min_delta + #nilm-auto-out）
 *     ②-2 基于设备画像匹配算法配置（#nilm-profile-group > #nilm-profile-algo 动态 profile 面板）
 *
 * 检查什么：
 *   A 结构：6+1 分容器填充、①/前6公共 字段互斥完整、总线/分路两列一致
 *   B 回填：fillNilmForm 按 id 回填 9 个公共字段 + 7 算法 enabled/参数（跨新容器）
 *   C 自适应：勾选后 rel_tol/min_delta 灰显+disabled、算法启停勾选不灰显、①组 5 项不被灰显
 *   D 脏标记：改 #nilm-form-scalar（前6公共）与 #nilm-form（①组）都能置脏
 *   E 载荷：collectNilmPayload 仍含 9 字段 + 7 算法
 *   F stage_free 联动（第 185 轮）在 profile 面板迁入 #nilm-profile-algo 后仍工作
 *
 * 用法：node tools/ui_r186_check.cjs [baseUrl]
 *   依赖：node ≥18、jsdom（npm install jsdom，或用 JSDOM_DIR 指定安装目录，如 /tmp/r186js/node_modules）
 *   需要服务端已启动（静态文件每请求读盘，改完刷新即可）。
 * 退出码：0 全通过；1 有失败项；2 脚本自身异常。
 */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require(path.join(process.env.JSDOM_DIR || '/tmp/r186js/node_modules', 'jsdom'));

const BASE = process.argv[2] || 'http://127.0.0.1:8000';
const ROOT = path.resolve(__dirname, '..');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let pass = 0, fail = 0;
const fails = [];
function check(name, ok, detail = '') {
  if (ok) { pass++; console.log(`  ✓ ${name}${detail ? '　' + detail : ''}`); }
  else { fail++; fails.push(name); console.log(`  ✗ ${name}　${detail}`); }
}

async function main() {
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');

  const dom = new JSDOM(html, {
    url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true,
    beforeParse(window) {
      window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, {
        get: (t, p) => (p === 'measureText' ? () => ({ width: 8 })
          : p === 'createLinearGradient' ? () => ({ addColorStop() {} })
            : () => {}),
        set: () => true,
      });
      window.WebSocket = class { constructor() { this.readyState = 0; } close() {} send() {} };
      window.fetch = async (url, opts = {}) => fetch(String(url).startsWith('http') ? String(url) : BASE + url, opts);
      window.alert = () => {};
      window.confirm = () => true;
    },
  });
  const { window } = dom, { document } = window;
  window.eval(js + '\n;window.__collect = (s) => collectNilmPayload(s); window.__NLs = (s) => NLs(s);');
  if (typeof window.init === 'function') window.init();
  await sleep(1800);
  const $ = (id) => document.getElementById(id);
  const E2 = (side, id) => side === 'branch' ? (document.getElementById(id + '-br') || null) : document.getElementById(id);

  console.log('● A 结构：两层布局与 6+1 分容器');
  for (const [side, tag] of [['bus', '总线'], ['branch', '分路']]) {
    const scalar = E2(side, 'nilm-scalar-algos');
    const prof = E2(side, 'nilm-profile-algo');
    const form7 = E2(side, 'nilm-form');
    const formS = E2(side, 'nilm-form-scalar');
    const common7 = E2(side, 'nilm-common7');
    const algos = E2(side, 'nilm-algos');
    const scalarGrp = E2(side, 'nilm-scalar-group');
    const scalarCmn = E2(side, 'nilm-scalar-common');
    const profGrp = E2(side, 'nilm-profile-group');
    check(`${tag}侧 ②-1 容器存在且恰含 6 个算法面板`, scalar && scalar.querySelectorAll('.nilm-algo').length === 6,
      scalar ? `${scalar.querySelectorAll('.nilm-algo').length} 个` : '容器缺失');
    check(`${tag}侧 ②-2 容器存在且恰含 profile 面板`, prof && prof.querySelectorAll('.nilm-algo[data-algo="profile"]').length === 1,
      prof ? `${prof.querySelectorAll('.nilm-algo[data-algo="profile"]').length} 个` : '容器缺失');
    check(`${tag}侧 #nilm-algos 内合计 7 面板（深度查询，旧选择器兼容）`,
      algos && algos.querySelectorAll('.nilm-algo').length === 7,
      algos ? `${algos.querySelectorAll('.nilm-algo').length} 个` : '缺失');
    if (side === 'bus') {
      check('层级：common7 与 algos 是同级两大模块', common7 && algos && common7.parentElement === algos.parentElement,
        common7 && algos ? `parent=${common7.parentElement.id}` : '');
      check('层级：scalar-common 在 scalar-group 内、profile-group 与 scalar-group 同级',
        scalarGrp && scalarCmn && profGrp && scalarCmn.parentElement === scalarGrp && profGrp.parentElement === algos);
      const ids = (host) => host ? new Set([...host.querySelectorAll('input,select')].map(el => el.id)) : new Set();
      const i7 = ids(form7), iS = ids(formS);
      const expect7 = ['nilm-enabled', 'nilm-save', 'nilm-quantity', 'nilm-window_cycles', 'nilm-min_gap_cycles'];
      const expectS = ['nilm-ch-total', 'nilm-ch-A', 'nilm-ch-B', 'nilm-ch-C', 'nilm-auto_params', 'nilm-rel_tol_pct', 'nilm-min_delta_pct'];
      check('①组恰含 5 个全算法公共字段', expect7.every(i => i7.has(i)) && i7.size === 5, [...i7].join(','));
      check('前6公共组恰含 4 项（检测对象4相 + 自适应 + rel_tol + min_delta）', expectS.every(i => iS.has(i)) && iS.size === expectS.length,
        [...iS].join(','));
      check('两组字段互斥（无交叉）', expectS.every(i => !i7.has(i)) && expect7.every(i => !iS.has(i)));
      check('#nilm-auto-out 挂在前6公共组内', !!E2('bus', 'nilm-auto-out') && $('nilm-auto-out').closest('#nilm-scalar-common') != null);
    }
  }

  console.log('● B 回填：fillNilmForm 跨新容器按 id 回填');
  try {
    const cfg = await (await fetch(BASE + '/api/config')).json();
    const nilm = cfg.nilm || {};
    const w = window;
    w.eval('window.__fill = (nc, side) => fillNilmForm(nc, side);');
    w.__fill(nilm, 'bus');
    const get = (id) => { const el = $(id); return el ? (el.type === 'checkbox' ? el.checked : el.value) : undefined; };
    check('回填 检测量=配置值', get('nilm-quantity') === (nilm.quantity || 'auto'), `${get('nilm-quantity')}`);
    check('回填 周波窗长', String(get('nilm-window_cycles')) === String(nilm.window_cycles), `${get('nilm-window_cycles')}`);
    check('回填 rel_tol_pct（前6公共组）', String(get('nilm-rel_tol_pct')) === String(nilm.rel_tol_pct), `${get('nilm-rel_tol_pct')}`);
    const p = (nilm.algorithms || {}).profile || {};
    check('回填 profile.d2_max（②-2 面板）', String(get('nilm-profile-d2_max')) === String(p.d2_max ?? 9), `${get('nilm-profile-d2_max')}`);
    check('回填 threshold.enabled（②-1 面板）', get('nilm-threshold-enabled') === ((nilm.algorithms || {}).threshold || {}).enabled !== false,
      String(get('nilm-threshold-enabled')));
    // 分路侧
    w.__fill(nilm, 'branch');
    check('分路侧回填 rel_tol_pct', String(E2('branch', 'nilm-rel_tol_pct').value) === String(nilm.rel_tol_pct));
    check('分路侧回填 profile.d2_max', String(E2('branch', 'nilm-profile-d2_max').value) === String(p.d2_max ?? 9));
  } catch (e) { check('回填流程', false, e.message); }

  console.log('● C 自适应勾选（nilmDimAuto）行为不变');
  try {
    w0 = window;
    w0.eval('window.__dimAuto = (side) => nilmDimAuto(side);');
    const ap = $('nilm-auto_params');
    check('默认不灰显', document.querySelectorAll('#nilm-algos label.nilm-auto-off').length === 0,
      `${document.querySelectorAll('#nilm-algos label.nilm-auto-off').length}`);
    ap.checked = true; ap.dispatchEvent(new window.Event('change'));
    const offs = document.querySelectorAll('#nilm-algos label.nilm-auto-off').length;
    const offChk = document.querySelectorAll('#nilm-algos label.nilm-auto-off input[type=checkbox]').length;
    check('勾选后数值项灰显（>20）', offs > 20, `offs=${offs}`);
    check('勾选后算法启停/检测对象/自适应勾选框不灰显（chk===0）', offChk === 0, `chk=${offChk}`);
    check('rel_tol 灰显 + disabled（在前6公共组内仍生效）',
      $('nilm-rel_tol_pct').closest('label').classList.contains('nilm-auto-off') && $('nilm-rel_tol_pct').disabled);
    check('min_delta 灰显 + disabled', $('nilm-min_delta_pct').closest('label').classList.contains('nilm-auto-off') && $('nilm-min_delta_pct').disabled);
    check('①组5项不被自适应灰显（在 #nilm-algos 外）',
      ['nilm-quantity', 'nilm-window_cycles', 'nilm-min_gap_cycles'].every(i => { const l = $(i).closest('label'); return l && !l.classList.contains('nilm-auto-off') && !$(i).disabled; }));
    check('算法启停勾选仍可用', [...document.querySelectorAll('#nilm-algos input[type=checkbox]')].every(c => !c.disabled));
    check('推导面板显示（在前6公共组内）', $('nilm-auto-out').style.display === '' && /自适应算法参数/.test($('nilm-auto-out').textContent));
    ap.checked = false; ap.dispatchEvent(new window.Event('change'));
    check('取消后恢复', document.querySelectorAll('#nilm-algos label.nilm-auto-off').length === 0 && !$('nilm-rel_tol_pct').disabled);
  } catch (e) { check('自适应流程', false, e.message); }

  console.log('● D 脏标记（bindNilmForm 覆盖两组）');
  try {
    w2 = window;
    w2.eval('window.__nl = (s) => NLs(s);');
    w2.__nl('bus').dirty = false;
    $('nilm-rel_tol_pct').value = '2.5'; $('nilm-rel_tol_pct').dispatchEvent(new window.Event('input'));
    check('改前6公共 rel_tol → dirty', w2.__nl('bus').dirty === true);
    w2.__nl('bus').dirty = false;
    $('nilm-window_cycles').value = '301'; $('nilm-window_cycles').dispatchEvent(new window.Event('input'));
    check('改①组 周波窗长 → dirty', w2.__nl('bus').dirty === true);
    w2.__nl('bus').dirty = false;
    $('nilm-profile-d2_max').value = '8'; $('nilm-profile-d2_max').dispatchEvent(new window.Event('input'));
    check('改②-2 profile 参数 → dirty', w2.__nl('bus').dirty === true);
  } catch (e) { check('脏标记', false, e.message); }

  console.log('● E 载荷完整性');
  try {
    const pl = window.__collect('bus');
    const need = ['nilm-quantity', 'nilm-window_cycles'];   // ①组
    const ok7 = ['quantity', 'window_cycles', 'min_gap_cycles', 'rel_tol_pct', 'min_delta_pct'].every(k => pl[k] !== undefined);
    const okAlgo = pl.algorithms && Object.keys(pl.algorithms).length === 7 && pl.algorithms.profile && pl.algorithms.threshold;
    check('载荷含 ①组+前6公共 全部字段', ok7, JSON.stringify({ q: pl.quantity, w: pl.window_cycles, r: pl.rel_tol_pct }));
    check('载荷含 7 个算法参数（含 profile）', okAlgo, pl.algorithms ? Object.keys(pl.algorithms).join(',') : '无');
    check('载荷含检测对象 channels', Array.isArray(pl.channels) && pl.channels.length > 0, JSON.stringify(pl.channels));
  } catch (e) { check('载荷', false, e.message); }

  console.log('● F stage_free 联动（第 185 轮，profile 面板迁移后）');
  try {
    w3 = window;
    w3.eval('window.__gate = (s) => nilmStageGate(s);');
    const sf = $('nilm-profile-stage_free');
    const g1 = ['nilm-profile-stage_min_scale', 'nilm-profile-stage_max_scale', 'nilm-profile-stage_dim_max'];
    if (sf) {
      sf.value = '0'; w3.__gate('bus');
      check('stage_free=0 → 三项禁用', g1.every(i => $(i) && $(i).disabled), g1.map(i => $(i) && $(i).disabled).join(','));
      sf.value = '1'; w3.__gate('bus');
      check('stage_free=1 → 三项可用', g1.every(i => $(i) && !$(i).disabled), g1.map(i => $(i) && $(i).disabled).join(','));
      sf.value = '0'; w3.__gate('bus');
    } else { check('stage_free 下拉存在', false, '未找到'); }
  } catch (e) { check('stage_free 联动', false, e.message); }

  console.log(fail ? `\n✗ ${pass} passed, ${fail} FAILED` : `\n✓ ${pass} passed, 0 failed`);
  try { dom.window.close(); } catch (e) {}
  process.exit(fail ? 1 : 0);
}

main().catch((e) => { console.error('脚本异常:', e); process.exit(2); });
