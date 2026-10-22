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
  check('数据处理页有波形预览面板（路径 / 独立基准配置 6 项 / 重采样率 + 方式 / 起止 / 周波数 / 6 通道勾选 / 3 张画布）',
    !!$('#wp-path') && !$('#wp-side') && !!$('#wp-base-fs') && !!$('#wp-base-fnom') && !!$('#wp-base-ptct') && !!$('#wp-base-pt') && !!$('#wp-base-ct') && !!$('#wp-base-utc') && !!$('#wp-fs') && !!$('#wp-method') && !!$('#wp-tstart') && !!$('#wp-tend') && !!$('#wp-ncyc') && window.document.querySelectorAll('#wp-chans .wp-ch').length === 6 && !!$('#wp-wave') && !!$('#wp-rms') && !!$('#wp-cyc'));
  check('默认值：周波数 300、重采样率空（原始）、方式 linear、全部通道勾选、周波窗周波数 300', $('#wp-ncyc').value === '300' && $('#wp-fs').value === '' && $('#wp-method').value === 'linear' && Array.from(window.document.querySelectorAll('#wp-chans .wp-ch')).every(c => c.checked) && $('#wp-cyc-n').value === '300');
  check('重采样方式含「重采样」功能的 linear / nearest / fft', Array.from($('#wp-method').options).map(o => o.value).join() === 'linear,nearest,fft');
  await sleep(500);
  check('基准配置初始值＝出厂配置（f_nom 50 / PT 100 / CT 15 / PT·CT 启用）；采样率框只读且获取信息前为空（v0.65）', $('#wp-base-fs').readOnly && $('#wp-base-fs').value === '' && $('#wp-base-fnom').value === '50' && $('#wp-base-pt').value === '100' && $('#wp-base-ct').value === '15' && $('#wp-base-ptct').checked, [$('#wp-base-fs').value, $('#wp-base-fnom').value, $('#wp-base-pt').value, $('#wp-base-ct').value].join('/'));
  check('v0.65：三组配置分区存在且各自包含对应控件（公共：路径 / f_nom / PT·CT / 自定义时间；波形：重采样 / 周波数 / 通道 / 最多点数；有效值：时长 / 统计窗 / 周波窗周波数）',
    !!$('#wp-sec-common') && !!$('#wp-sec-wave') && !!$('#wp-sec-rms') && $('#wp-sec-common').contains($('#wp-path')) && $('#wp-sec-common').contains($('#wp-base-fnom')) && $('#wp-sec-common').contains($('#wp-base-custom')) && $('#wp-sec-common').contains($('#wp-base-fs'))
    && $('#wp-sec-wave').contains($('#wp-fs')) && $('#wp-sec-wave').contains($('#wp-ncyc')) && $('#wp-sec-wave').contains($('#wp-chans')) && $('#wp-sec-wave').contains($('#wp-maxpts')) && $('#wp-sec-wave').contains($('#btn-wp-load'))
    && $('#wp-sec-rms').contains($('#wp-rms-dur')) && $('#wp-sec-rms').contains($('#wp-rms-agg')) && $('#wp-sec-rms').contains($('#wp-cyc-n')) && $('#wp-sec-rms').contains($('#btn-wp-rms'))
    && !!$('#wp-cyc2') && $('#wp-sec-common').classList.contains('wp-common') && $('#wp-sec-wave').classList.contains('wp-wave') && $('#wp-sec-rms').classList.contains('wp-rmsg') && /\.wp-common\{border-left-color/.test(fs.readFileSync(path.join(ROOT, 'app/static/style.css'), 'utf8')));
  check('文件下拉已列出 data/ 下的 CSV', $('#wp-files').options.length > 1, `${$('#wp-files').options.length - 1} 个`);
  // 1) 文件信息
  $('#wp-path').value = 'data/nilm_bus_mixed.csv';
  $('#btn-wp-info').click(); await sleep(1500);
  const infoTxt = $('#wp-info').textContent;
  check('文件信息表：通道数 6、采样率 6400 Hz、时长 10.000 s（=64000/6400）、起始 / 结束时间（结束＝起始+(行数−1)/fs）', /通道数\s*6/.test(infoTxt) && /6400/.test(infoTxt) && /10\.000 s/.test(infoTxt) && /起始时间\s*2026-10-13 16:00:00\.000/.test(infoTxt) && /结束时间\s*2026-10-13 16:00:09\.999/.test(infoTxt), infoTxt.replace(/\s+/g, ' ').slice(0, 200));
  check('v0.64：获取信息后起止时刻保持为空（空＝文件数据起止时间），占位提示显示实际数据起止时间（波形与有效值两组）', $('#wp-tstart').value === '' && $('#wp-tend').value === '' && $('#wp-rms-tstart').value === '' && $('#wp-rms-tend').value === '' && $('#wp-tstart').placeholder === '空＝2026-10-13 16:00:00.000' && $('#wp-tend').placeholder.startsWith('空＝2026-10-13 16:00:09.99') && $('#wp-rms-tend').placeholder === $('#wp-tend').placeholder, $('#wp-tstart').placeholder + ' → ' + $('#wp-tend').placeholder);
  check('v0.64：最多加载点数输入框默认 20000000；自定义时间开关默认关、起止输入行隐藏', $('#wp-maxpts').value === '20000000' && !$('#wp-base-custom').checked && $('#wp-custom-row').style.display === 'none');
  const infoCall = calls.filter(x => x.url.includes('/api/process/wave/info')).pop();
  check('v0.65：获取信息后采样率框显示按文件数据时间计算的 6400（只读）', $('#wp-base-fs').value === '6400' && $('#wp-base-fs').readOnly, $('#wp-base-fs').value);
  check('信息请求带公共配置参数（f_nom/pt_ct_enabled/pt_ratio/ct_ratio/file_time_utc），不带 fs、不带 side', !/[?&]fs=/.test(infoCall.url) && /f_nom=50/.test(infoCall.url) && /pt_ct_enabled=1/.test(infoCall.url) && /pt_ratio=100/.test(infoCall.url) && /ct_ratio=15/.test(infoCall.url) && /file_time_utc=0/.test(infoCall.url) && !/side=/.test(infoCall.url), infoCall.url);
  // 2) 默认加载波形：300 周波 × 128 = 38400 点、原采样率、全部通道（起止时刻已填满整文件，取先到者＝周波数）
  $('#btn-wp-load').click(); await sleep(4000);
  let c = $('#wp-wave').__chart;
  check('默认加载：波形曲线 6 条、每条 300 周波 × 128 = 38400 点、原采样率 6400', !!c && c.pts.length === 6 && c.pts.every(s => s.data.length === 38400) && /6400/.test($('#wp-wave-sub').textContent), $('#wp-wave-sub').textContent);
  const loadCall = calls.filter(x => x.url.includes('/api/process/wave/load')).pop();
  check('请求参数：n_cycles=300、method=linear、未传 fs_out、channels 全 6 个、带基准配置、max_points=20000000、custom_time=0', !!loadCall && /n_cycles=300/.test(loadCall.url) && /method=linear/.test(loadCall.url) && !/fs_out=/.test(loadCall.url) && /channels=Ua%2CUb%2CUc%2CIa%2CIb%2CIc/.test(loadCall.url) && /pt_ratio=100/.test(loadCall.url) && /max_points=20000000/.test(loadCall.url) && /custom_time=0/.test(loadCall.url), loadCall && loadCall.url);
  // 2b) 基准配置独立：改 PT=1（关掉一次侧换算）→ 幅值变为二次侧；运行配置不变
  const cfgBefore = JSON.stringify((await (await fetch(BASE + '/api/config')).json()).transform);
  $('#wp-base-ptct').checked = false; $('#wp-base-ptct').dispatchEvent(new window.Event('change', { bubbles: true }));
  $('#wp-ncyc').value = '10';
  $('#btn-wp-load').click(); await sleep(2500);
  c = $('#wp-wave').__chart;
  const uaMax = c ? Math.max(...c.pts[0].data.map(p => Math.abs(p[1]))) : 0;
  check('关闭 PT/CT 后再加载：Ua 峰值≈二次侧 81.6 V（独立基准配置生效）', uaMax > 70 && uaMax < 95, 'Ua max=' + uaMax.toFixed(1));
  const cfgAfter = JSON.stringify((await (await fetch(BASE + '/api/config')).json()).transform);
  check('总线侧运行配置 transform 未被改动', cfgBefore === cfgAfter);
  check('基准配置改动保存在 localStorage', /"pt_ct_enabled":"0"/.test(window.localStorage.getItem('elec_tool.wave_preview.base') || ''));
  $('#wp-base-ptct').checked = true; $('#wp-base-ptct').dispatchEvent(new window.Event('change', { bubbles: true }));
  // 3) 指定重采样率 + 方式 + 通道 + 时间段（时间段 0.5 s 先于周波数 300 到）
  $('#wp-ncyc').value = '300';
  $('#wp-fs').value = '1600'; $('#wp-method').value = 'fft'; $('#wp-tstart').value = '2026-10-13 16:00:02.000'; $('#wp-tend').value = '2026-10-13 16:00:02.500';
  window.document.querySelectorAll('#wp-chans .wp-ch').forEach(cb => { cb.checked = cb.value === 'Ia' || cb.value === 'Ub'; });
  $('#btn-wp-load').click(); await sleep(2500);
  c = $('#wp-wave').__chart;
  check('重采样 1600 Hz（fft）+ 时间段 0.5 s + 通道 Ub/Ia：2 条曲线、各 800 点、副标题含 fft', !!c && c.pts.length === 2 && c.pts.every(s => s.data.length === 800) && c.pts.map(s => s.name.split(' ')[0]).sort().join() === 'Ia,Ub' && /fft/.test($('#wp-wave-sub').textContent), c && c.pts.map(s => s.name + ':' + s.data.length).join(' '));
  const fftCall = calls.filter(x => x.url.includes('/api/process/wave/load')).pop();
  check('请求含 method=fft、fs_out=1600', /method=fft/.test(fftCall.url) && /fs_out=1600/.test(fftCall.url), fftCall.url);
  $('#wp-method').value = 'nearest'; $('#btn-wp-load').click(); await sleep(2500);
  c = $('#wp-wave').__chart;
  check('nearest 方式同样 800 点', !!c && c.pts.every(s => s.data.length === 800));
  $('#wp-method').value = 'linear';
  check('曲线横轴标签＝时刻（fmtX）、提示＝本地毫秒时间', c && /^\d\d:\d\d:\d\d\.\d{3}$/.test(c.opt.fmtX(0)) && /^2026-10-13 16:00:02/.test(c.opt.fmtTip(0)), c && c.opt.fmtX(0) + ' / ' + c.opt.fmtTip(0));
  // 4) 周波数为空 + 结束时刻为空 ⇒ 整段（不传 n / n_cycles）
  $('#wp-tend').value = ''; $('#wp-ncyc').value = ''; $('#wp-fs').value = '400';
  $('#btn-wp-load').click(); await sleep(3000);
  const lc2 = calls.filter(x => x.url.includes('/api/process/wave/load')).pop();
  c = $('#wp-wave').__chart;
  check('周波数与结束时刻都为空 ⇒ 不传点数 → 从起点到文件末尾（8 s × 400 Hz ≈ 3200 点）', !!lc2 && !/n_cycles=/.test(lc2.url) && !/[?&]n=/.test(lc2.url) && !!c && c.pts[0].data.length >= 3190 && c.pts[0].data.length <= 3201, lc2 && lc2.url + ' n=' + (c && c.pts[0].data.length));
  // 4b) v0.64：最多加载点数可配（设 1000 → 截断提示）
  $('#wp-maxpts').value = '1000'; $('#wp-maxpts').dispatchEvent(new window.Event('change'));
  $('#btn-wp-load').click(); await sleep(2500);
  c = $('#wp-wave').__chart;
  const lc3 = calls.filter(x => x.url.includes('/api/process/wave/load')).pop();
  check('最多加载点数改为 1000 ⇒ 请求 max_points=1000、返回 1000 点并提示截断', /max_points=1000(&|$)/.test(lc3.url) && c.pts[0].data.length === 1000 && /超过单次上限 1000/.test($('#wp-status').textContent), $('#wp-status').textContent.slice(0, 80));
  $('#wp-maxpts').value = '20000000'; $('#wp-maxpts').dispatchEvent(new window.Event('change'));
  // 4c) v0.64：自定义时间：起始 2026-01-01 00:00:00、结束空 ⇒ 结束＝起始+(行数−1)/fs；信息表显示时间模式；加载按自定义轴定位
  $('#wp-base-custom').checked = true; $('#wp-base-custom').dispatchEvent(new window.Event('change'));
  check('勾选「启用自定义时间」后显示自定义起止输入行，默认为空', $('#wp-custom-row').style.display !== 'none' && $('#wp-base-cstart').value === '' && $('#wp-base-cend').value === '');
  $('#wp-base-cstart').value = '2026-01-01 00:00:00'; $('#wp-base-cstart').dispatchEvent(new window.Event('change'));
  $('#btn-wp-info').click(); await sleep(1500);
  const it2 = $('#wp-info').textContent;
  check('自定义时间信息表：时间模式＝自定义、起始 2026-01-01 00:00:00.000、结束 2026-01-01 00:00:09.999（＝起始+(64000−1)/6400）', /自定义时间/.test(it2) && /起始时间\s*2026-01-01 00:00:00\.000/.test(it2) && /结束时间\s*2026-01-01 00:00:09\.999/.test(it2), it2.replace(/\s+/g, ' ').slice(0, 220));
  $('#wp-tstart').value = '2026-01-01 00:00:02'; $('#wp-tend').value = '2026-01-01 00:00:02.5'; $('#wp-ncyc').value = ''; $('#wp-fs').value = '';
  $('#btn-wp-load').click(); await sleep(2500);
  c = $('#wp-wave').__chart;
  const lc4 = calls.filter(x => x.url.includes('/api/process/wave/load')).pop();
  check('自定义时间模式按自定义轴定位：2 s→2.5 s 取 3200 点、提示时刻 2026-01-01 00:00:02；请求带 custom_time=1 与 custom_time_start', /custom_time=1/.test(lc4.url) && /custom_time_start=2026-01-01/.test(lc4.url) && c.pts[0].data.length === 3200 && /^2026-01-01 00:00:02/.test(c.opt.fmtTip(0)), lc4.url.slice(-120) + ' n=' + c.pts[0].data.length);
  $('#wp-base-cend').value = '2026-01-01 00:00:04'; $('#wp-base-cend').dispatchEvent(new window.Event('change'));
  $('#wp-tstart').value = ''; $('#wp-tend').value = '';
  $('#btn-wp-load').click(); await sleep(3000);
  c = $('#wp-wave').__chart;
  check('自定义结束时间 00:00:04 且起止为空 ⇒ 整段＝起始→自定义结束（4 s × 6400 = 25600 点）', c.pts[0].data.length === 25600 && /^2026-01-01 00:00:03\.999/.test(c.opt.fmtTip(c.pts[0].data[c.pts[0].data.length - 1][0])), 'n=' + c.pts[0].data.length);
  // 4d) v0.64/v0.65：低采样率文件不再因 harmonic.order_max=50 ≥ Nyquist 失败（采样率按文件时标推算，界面不可改 → 直接打 REST 用 1000 Hz 文件验证）
  $('#wp-base-custom').checked = false; $('#wp-base-custom').dispatchEvent(new window.Event('change'));
  {
    const rr = await (await fetch(BASE + '/api/process/wave/info?path=' + encodeURIComponent(process.env.LOW_FS_FILE || 'data/nilm_bus_mixed.csv'))).json();
    check('低采样率文件（LOW_FS_FILE）信息：采样率按时标推算、不报 Nyquist', rr.ok && !/Nyquist/.test(JSON.stringify(rr)), 'fs=' + rr.fs + (process.env.LOW_FS_FILE ? '' : '（未设 LOW_FS_FILE，用默认文件）'));
  }
  $('#wp-ncyc').value = '10';
  $('#wp-tstart').value = ''; $('#wp-tend').value = ''; $('#wp-ncyc').value = ''; $('#wp-fs').value = '400';
  window.document.querySelectorAll('#wp-chans .wp-ch').forEach(cb => { cb.checked = cb.value === 'Ia' || cb.value === 'Ub'; });   // 上面「获取文件信息」会把通道勾回全部，恢复用例 3 的选择
  $('#btn-wp-load').click(); await sleep(3000);
  c = $('#wp-wave').__chart;
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
  check('周波窗周波数默认 300', $('#wp-cyc-n').value === '300');
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
  // v0.65：显示周波窗 2（瞬时值）
  check('v0.65：有效值曲线右键菜单含「显示周波窗 2」（原有「显示周波窗」保留）', keys.includes('show-window2') && keys.indexOf('show-window2') > keys.indexOf('show-window'), keys.join(','));
  window.closeCtxMenu && window.closeCtxMenu();
  rcv.dispatchEvent(new window.MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX: r.left + mx, clientY: r.top + 50, button: 2 }));
  await sleep(100);
  const sw2 = Array.from(window.document.getElementById('ctxmenu').querySelectorAll('.mi')).find(d => d.dataset.key === 'show-window2');
  check('「显示周波窗 2」可用、标签含「瞬时值」与鼠标所指时刻', !!sw2 && !sw2.classList.contains('disabled') && /瞬时值/.test(sw2.textContent) && /2026-10-13 16:00:0[12]/.test(sw2.textContent), sw2 && sw2.textContent);
  sw2.click(); await sleep(3000);
  const cc2 = $('#wp-cyc2').__chart; const c2txt = $('#wp-cyc2-sub').textContent;
  check('周波窗 2 画布（单独曲线）已装载采样瞬时值：2 通道 × 6400 点、标注「采样瞬时值」；周波窗 1 不受影响', !!cc2 && cc2.pts.length === 2 && cc2.pts.every(s => s.data.length === 6400) && /采样瞬时值/.test(c2txt) && $('#wp-cyc').__chart.pts.length === 2, c2txt);
  check('周波窗 2 为瞬时值（同一周波内有正有负、峰值≈√2×有效值），而非有效值', (() => { const a = cc2.pts.find(s => /Ia/.test(s.name)).data.slice(0, 128).map(p => p[1]); const mx = Math.max(...a), mn = Math.min(...a); const rms = Math.sqrt(a.reduce((q, v) => q + v * v, 0) / a.length); return mn < 0 && mx > 0 && Math.abs(mx / rms - Math.SQRT2) < 0.1; })());
  const cycCall = calls.filter(x => x.url.includes('/api/process/wave/load')).pop();
  const m = cycCall && cycCall.url.match(/t_start=([\d.]+).*t_end=([\d.]+)/);
  check('周波窗请求区间＝中心 ± 25 周波（1.0 s），不带点数参数', !!m && Math.abs((+m[2]) - (+m[1]) - 1.0) < 1e-3 && !/n_cycles=/.test(cycCall.url), cycCall && cycCall.url);
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
  window.localStorage.removeItem('elec_tool.wave_preview.base');
  check('文件不存在 → 错误提示、不崩溃', /文件不存在/.test($('#toast').textContent) || /填写路径/.test($('#wp-info').textContent), $('#toast').textContent);
  console.log(`\nPASS ${pass} / FAIL ${fail}` + (fail ? '\n  失败：' + fails.join('；') : ''));
  process.exit(fail ? 1 : 0);
}
main().catch(e => { console.error(e); process.exit(2); });
