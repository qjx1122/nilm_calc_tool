#!/usr/bin/env node
/* ui_r61_check.cjs —— v0.61 数据处理页「波形预览」检查（需服务在跑；用法 TZ=Asia/Shanghai JSDOM_DIR=/tmp/uitest node tools/ui_r61_check.cjs http://127.0.0.1:8000） */
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
function makeDom(calls) {
  const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
  const js = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
  const dom = new JSDOM(html, {
    url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true,
    beforeParse(window) {
      window.HTMLCanvasElement.prototype.getContext = () => new Proxy({}, {
        get: (t, p) => (p === 'measureText' ? () => ({ width: 8 }) : p === 'createLinearGradient' ? () => ({ addColorStop() {} }) : () => {}),
        set: () => true,
      });
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
  window.eval(js + '\n;window.__S = () => S; window.__render = render; window.__hoverInfo = hoverInfo; window.__ZOOM = ZOOM; window.__wpLoad = wpLoad; window.__wpRms = wpRms; window.__wpInfo = wpInfo; window.__zoomAxis = zoomAxis; window.__zoomReset = zoomReset; window.__fmtLocalInput = fmtLocalInput;');
  return dom;
}
async function main() {
  const calls = [];
  const dom = makeDom(calls); const { window } = dom; const $ = (s) => window.document.querySelector(s);
  await sleep(1500);
  window.document.querySelector('.navitem[data-view="process"]').click();
  await sleep(300);
  check('数据处理页有波形预览面板（路径 / 基准配置 / 重采样率 / 起止 / 点数 / 6 通道勾选 / 3 张画布）',
    !!$('#wp-path') && !!$('#wp-side') && !!$('#wp-fs') && !!$('#wp-tstart') && !!$('#wp-tend') && !!$('#wp-n') && window.document.querySelectorAll('#wp-chans .wp-ch').length === 6 && !!$('#wp-wave') && !!$('#wp-rms') && !!$('#wp-cyc'));
  check('默认值：点数 1000、重采样率空（原始）、全部通道勾选、周波窗周波数 1000', $('#wp-n').value === '1000' && $('#wp-fs').value === '' && Array.from(window.document.querySelectorAll('#wp-chans .wp-ch')).every(c => c.checked) && $('#wp-cyc-n').value === '1000');
  await sleep(500);
  check('文件下拉已列出 data/ 下的 CSV', $('#wp-files').options.length > 1, `${$('#wp-files').options.length - 1} 个`);
  // 1) 文件信息
  $('#wp-path').value = 'data/nilm_bus_mixed.csv';
  $('#btn-wp-info').click(); await sleep(1500);
  const infoTxt = $('#wp-info').textContent;
  check('文件信息表：通道数 6、采样率 6400 Hz、时长、起始 / 结束时间', /通道数\s*6/.test(infoTxt) && /6400/.test(infoTxt) && /时长/.test(infoTxt) && /起始时间\s*2026-10-13 16:00:00/.test(infoTxt) && /结束时间\s*2026-10-13 16:00:09/.test(infoTxt), infoTxt.replace(/\s+/g, ' ').slice(0, 160));
  // 2) 默认加载波形：1000 点、原采样率、全部通道
  $('#btn-wp-load').click(); await sleep(2500);
  let c = $('#wp-wave').__chart;
  check('默认加载：波形曲线 6 条、每条 1000 点、原采样率 6400', !!c && c.pts.length === 6 && c.pts.every(s => s.data.length === 1000) && /6400/.test($('#wp-wave-sub').textContent), $('#wp-wave-sub').textContent);
  const loadCall = calls.filter(x => x.url.includes('/api/process/wave/load')).pop();
  check('请求参数：n=1000、未传 fs / t_end、channels 全 6 个', !!loadCall && /n=1000/.test(loadCall.url) && !/fs=/.test(loadCall.url) && !/t_end=/.test(loadCall.url) && /channels=Ua%2CUb%2CUc%2CIa%2CIb%2CIc/.test(loadCall.url), loadCall && loadCall.url);
  // 3) 指定重采样率 + 通道 + 时间段
  $('#wp-fs').value = '1600'; $('#wp-tstart').value = '2026-10-13 16:00:02.000'; $('#wp-tend').value = '2026-10-13 16:00:02.500';
  window.document.querySelectorAll('#wp-chans .wp-ch').forEach(cb => { cb.checked = cb.value === 'Ia' || cb.value === 'Ub'; });
  $('#btn-wp-load').click(); await sleep(2500);
  c = $('#wp-wave').__chart;
  check('重采样 1600 Hz + 时间段 0.5 s + 通道 Ub/Ia：2 条曲线、各 800 点', !!c && c.pts.length === 2 && c.pts.every(s => s.data.length === 800) && c.pts.map(s => s.name.split(' ')[0]).sort().join() === 'Ia,Ub', c && c.pts.map(s => s.name + ':' + s.data.length).join(' '));
  check('曲线横轴标签＝时刻（fmtX）、提示＝本地毫秒时间', c && /^\d\d:\d\d:\d\d\.\d{3}$/.test(c.opt.fmtX(0)) && /^2026-10-13 16:00:02/.test(c.opt.fmtTip(0)), c && c.opt.fmtX(0) + ' / ' + c.opt.fmtTip(0));
  // 4) 点数为空 + 结束时刻为空 ⇒ 整段（传 n=）
  $('#wp-tend').value = ''; $('#wp-n').value = ''; $('#wp-fs').value = '400';
  $('#btn-wp-load').click(); await sleep(3000);
  const lc2 = calls.filter(x => x.url.includes('/api/process/wave/load')).pop();
  c = $('#wp-wave').__chart;
  check('点数与结束时刻都为空 ⇒ 请求 n=（不限）→ 从起点到文件末尾（8 s × 400 Hz ≈ 3200 点）', !!lc2 && /[?&]n=(&|$)/.test(lc2.url) && !!c && c.pts[0].data.length >= 3190 && c.pts[0].data.length <= 3201, lc2 && lc2.url + ' n=' + (c && c.pts[0].data.length));
  // 5) 缩放 / 平移 / 复位（与负荷辨识页同一 drawLine 机制）
  const cv = $('#wp-wave');
  window.__zoomAxis(cv, 'x', 0.5);
  check('波形曲线可缩放（X 轴放大后 ZOOM 记录存在、视窗缩小）', !!window.__ZOOM['wp-wave'] && cv.__chart.xmax - cv.__chart.xmin < (cv.__chart.xfull[1] - cv.__chart.xfull[0]) * 0.6);
  const before = cv.__chart.xmin;
  window.zoomPanFrac(cv, 'x', 0.25);
  check('波形曲线可移动（平移后视窗左端右移）', cv.__chart.xmin > before);
  window.__zoomReset(cv);
  check('波形曲线可复位（ZOOM 清除、恢复全图）', !window.__ZOOM['wp-wave'] && Math.abs(cv.__chart.xmin - cv.__chart.xfull[0]) < 1e-9);
  check('波形曲线有缩放按钮条（X＋/X－/Y＋/Y－/复位 + 移动）', !!cv.__zoombar && cv.__zoombar.querySelectorAll('button.zoom-btn').length >= 9);
  // 6) 有效值曲线
  $('#wp-rms-tstart').value = '2026-10-13 16:00:01.000'; $('#wp-rms-dur').value = '3';
  $('#btn-wp-rms').click(); await sleep(3000);
  const rc = $('#wp-rms').__chart;
  check('有效值曲线：按时间段（3 s → 150 周波）、通道随勾选（Ub/Ia）、逐周波', !!rc && rc.pts.length === 2 && rc.pts.every(s => s.data.length === 150) && /逐周波/.test($('#wp-rms-sub').textContent), $('#wp-rms-sub').textContent);
  window.__zoomAxis($('#wp-rms'), 'x', 0.5);
  check('有效值曲线可缩放', !!window.__ZOOM['wp-rms']);
  window.__zoomReset($('#wp-rms'));
  check('有效值曲线可复位', !window.__ZOOM['wp-rms']);
  // 7) 右键菜单：原生三项 + 显示周波窗 + 复位缩放；点「显示周波窗」→ 周波窗画布装载以该时刻为中心 N 个周波
  $('#wp-cyc-n').value = '50';
  const rcv = $('#wp-rms'); const r = rcv.getBoundingClientRect();
  const mx = rc.pad.l + (rc.w - rc.pad.l - rc.pad.r) * 0.5;
  rcv.dispatchEvent(new window.MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX: r.left + mx, clientY: r.top + 50, button: 2 }));
  await sleep(100);
  const menu = window.document.getElementById('ctxmenu');
  const keys = menu ? Array.from(menu.querySelectorAll('.mi')).map(d => d.dataset.key) : [];
  check('有效值曲线右键菜单：复制图片 / 另存为 / 新标签页 + 显示周波窗 + 复位缩放', keys.includes('copy-image') && keys.includes('save-image') && keys.includes('open-image') && keys.includes('show-window') && keys.includes('zoom-reset'), keys.join(','));
  const sw = menu && Array.from(menu.querySelectorAll('.mi')).find(d => d.dataset.key === 'show-window');
  check('「显示周波窗」可用且标签含鼠标所指时刻', !!sw && !sw.classList.contains('disabled') && /2026-10-13 16:00:0[12]/.test(sw.textContent), sw && sw.textContent);
  sw.click(); await sleep(3000);
  const cc = $('#wp-cyc').__chart;
  const centerTxt = $('#wp-cyc-sub').textContent;
  check('周波窗画布（单独曲线）已装载：2 通道 × 50 周波 × 128 点 = 6400 点、原采样率', !!cc && cc.pts.length === 2 && cc.pts.every(s => s.data.length === 6400) && /6400 Hz/.test(centerTxt) && /50 个周波/.test(centerTxt), centerTxt);
  const cycCall = calls.filter(x => x.url.includes('/api/process/wave/load')).pop();
  const m = cycCall && cycCall.url.match(/t_start=([\d.]+).*t_end=([\d.]+)/);
  check('周波窗请求区间＝中心 ± 25 周波（1.0 s）', !!m && Math.abs((+m[2]) - (+m[1]) - 1.0) < 1e-3, cycCall && cycCall.url);
  const hv = window.__hoverInfo(rcv, mx);
  check('右键时刻 ≈ 周波窗中心（提示中心时刻与悬停取值时刻一致）', hv && new RegExp(window.__fmtLocalInput(hv.x + rc.opt.tbase).slice(0, 19)).test(centerTxt), centerTxt);
  // 8) 波形画布右键菜单：原生三项 + 复位缩放（无「显示周波窗」）
  window.closeCtxMenu && window.closeCtxMenu();
  cv.dispatchEvent(new window.MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX: 300, clientY: 50, button: 2 }));
  await sleep(100);
  const m2 = window.document.getElementById('ctxmenu'); const k2 = m2 ? Array.from(m2.querySelectorAll('.mi')).map(d => d.dataset.key) : [];
  check('波形曲线右键菜单：原生三项 + 复位缩放', k2.includes('copy-image') && k2.includes('zoom-reset') && !k2.includes('show-window'), k2.join(','));
  // 9) 错误提示
  $('#wp-path').value = 'data/not_exist.csv'; $('#btn-wp-info').click(); await sleep(800);
  check('文件不存在 → 错误提示、不崩溃', /文件不存在/.test($('#toast').textContent) || /填写路径/.test($('#wp-info').textContent), $('#toast').textContent);
  console.log(`\nPASS ${pass} / FAIL ${fail}` + (fail ? '\n  失败：' + fails.join('；') : ''));
  process.exit(fail ? 1 : 0);
}
main().catch(e => { console.error(e); process.exit(2); });
