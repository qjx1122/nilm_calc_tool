#!/usr/bin/env node
/* 第 8 轮界面功能端到端检查：「数据处理」子界面（离线 CSV 重采样）。
 * jsdom 驱动真实 index.html + app.js，打真实服务端。
 *
 *   E1 导航有「数据处理」项；切入后文件下拉从 /api/files 填充、选中即填路径、输出名预览正确
 *   E2 探查源文件 → 显示行数/推算采样率
 *   E3 开始重采样（用户命名样例「波形_农业排灌_大水泵_80_1.csv」3200Hz→6400）：
 *      POST 载荷无空值；轮询至完成；结果区显示输出名 *_re_6400.csv、行数 N→2N；
 *      文件真实存在于 data/、表头保留、时间戳仍为 0/00/00 写法；文件列表自动刷新含新文件
 *   E4 已存在且未勾选覆盖 → 任务失败并显示错误；勾选覆盖 → 成功
 *   E5 「用重采样文件作为离线播放源」→ 切到数据源页、kind=csv_file、path=输出文件
 *   E6 非法参数（fs<=0 / 路径不存在）→ 服务端 ok:false 且界面显示错误
 *   E7 v0.34 相对误差：时间窗输入改动即保存到配置 processing.error_window_s；重采样 POST 载荷带 err_window_s；
 *      结果含 _err.csv（真实存在、行数=窗数+表头+汇总、列名含 RMS相对误差/NRMSE）；界面显示误差表；
 *      关闭勾选 → 载荷 err_report=false、结果无 err_path；非法窗 → ok:false
 *
 * 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r8_check.cjs [baseUrl]
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

const SRC_NAME = '波形_农业排灌_大水泵_80_1.csv';
const OUT_NAME = '波形_农业排灌_大水泵_80_1_re_6400.csv';
function makeCsv() {
  const fp = path.join(ROOT, 'data', SRC_NAME);
  const fsrc = 3200, n = fsrc * 3, lines = ['时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流'];
  for (let k = 0; k < n; k++) {
    const tsec = 12 * 3600 + 40 * 60 + k / fsrc;
    const hh = Math.floor(tsec / 3600), mm = Math.floor((tsec % 3600) / 60), ss = tsec % 60;
    const frac = Math.round((ss - Math.floor(ss)) * 10000) % 10000;
    const stamp = `0/00/00 ${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:${String(Math.floor(ss)).padStart(2, '0')}.${String(frac).padStart(4, '0')}`;
    const w = 2 * Math.PI * 50 * k / fsrc;
    lines.push([stamp, ...[100 * Math.sin(w), 5 * Math.sin(w - 0.5), 100 * Math.sin(w - 2.094), 5 * Math.sin(w - 2.594),
      100 * Math.sin(w + 2.094), 5 * Math.sin(w + 1.594)].map((x) => x.toFixed(6))].join(','));
  }
  fs.writeFileSync(fp, lines.join('\r\n') + '\r\n');
  return { fp, rows: n };
}

async function main() {
  const outPath = path.join(ROOT, 'data', OUT_NAME);
  try { fs.unlinkSync(outPath); } catch (e) { /* none */ }
  const { rows: N } = makeCsv();
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
  const nav = async (v) => { click(document.querySelector(`.navitem[data-view="${v}"]`)); await sleep(600); };
  let lastStart = null;
  const waitDone = async (ms = 20000) => {
    const t0 = Date.now(); let st;
    while (Date.now() - t0 < ms) {
      st = await (await fetch(BASE + '/api/process/resample')).json();
      if (st.started_at && st.started_at !== lastStart && !st.running && (st.result || st.error)) break;   // 必须是**本次**任务的终态
      await sleep(200);
    }
    lastStart = st && st.started_at;
    await sleep(900);                                  // 让界面轮询再跑一拍
    return st;
  };
  const bodies = (u, m) => calls.filter((c) => c.url.includes(u) && c.method === m && c.body).map((c) => JSON.parse(c.body));

  console.log('\n=== E1. 导航与文件下拉 ===');
  const navBtn = document.querySelector('.navitem[data-view="process"]');
  check('左侧导航有「数据处理」', !!navBtn && /数据处理/.test(navBtn.textContent));
  await nav('process'); await sleep(800);
  check('view-process 激活', $('view-process').classList.contains('active'));
  const opts = [...$('rs-files').options].map((o) => o.value);
  check('下拉框列出 data/ 下 CSV（含样例源）', opts.includes('data/' + SRC_NAME), opts.join(' | '));
  $('rs-files').value = 'data/' + SRC_NAME; change($('rs-files'));
  await sleep(700);
  check('选中即填路径', $('rs-path').value === 'data/' + SRC_NAME, $('rs-path').value);
  check('输出名预览 = 原名_re_6400.csv', $('rs-preview').textContent.includes(OUT_NAME) && !/已存在/.test($('rs-preview').textContent), $('rs-preview').textContent.trim().slice(0, 120));

  console.log('\n=== E2. 探查 ===');
  click($('btn-rs-probe')); await sleep(1500);
  check('探查显示行数与推算采样率≈3200', new RegExp(`${N} 行`).test($('rs-status').textContent) && /3200\.0/.test($('rs-status').textContent), $('rs-status').textContent.trim().slice(0, 160));

  console.log('\n=== E3. 重采样 3200→6400 ===');
  $('rs-fs').value = '6400'; input($('rs-fs'));
  $('rs-method').value = 'linear'; $('rs-overwrite').checked = false;
  click($('btn-rs-run'));
  await sleep(300);
  const b = bodies('/api/process/resample', 'POST').pop();
  check('POST 载荷正确且无空值', b && b.path === 'data/' + SRC_NAME && b.fs_new === 6400 && b.method === 'linear' && !('fs_src' in b), JSON.stringify(b));
  let st = await waitDone();
  check('任务完成无错误', st && st.result && !st.error, st && (st.error || ''));
  const r = st.result || {};
  check('结果：输出名正确', r.out_name === OUT_NAME, r.out_name);
  check('结果：行数 N→2N-1', r.rows_in === N && r.rows_out === 2 * N - 1, `${r.rows_in}→${r.rows_out}`);
  check('结果：原采样率推算 3200、来源 estimated', r.fs_src === 3200 && r.fs_src_source === 'estimated', `${r.fs_src} ${r.fs_src_source}`);
  check('界面结果区显示输出名与行数', $('rs-result').textContent.includes(OUT_NAME) && $('rs-result').textContent.includes(String(2 * N - 1)));
  check('进度条 100% 且 done', $('rs-bar').style.width === '100%' && $('rs-bar').classList.contains('done'), $('rs-bar').style.width);
  check('文件真实写入 data/', fs.existsSync(outPath));
  const lines = fs.readFileSync(outPath, 'utf8').split(/\r?\n/).filter((l) => l.trim());
  check('表头原样保留', lines[0] === '时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流', lines[0]);
  check('行数 = 表头 + 2N-1', lines.length === 2 * N, String(lines.length));
  check('时间戳保持 0/00/00 HH:MM:SS.ffff 写法且从 12:40:00.0000 起', /^0\/00\/00 12:40:00\.0000,/.test(lines[1]) && /^0\/00\/00 12:40:00\.000[12],/.test(lines[2]), lines[1].slice(0, 30) + ' / ' + lines[2].slice(0, 30));
  // 数值：第 2 行（t=1/6400）Ua 应 ≈ 线性插值 (0+100 sin(2π50/3200))/2
  const ua2 = +lines[2].split(',')[1];
  check('插值数值正确（Ua@1/6400 ≈ 中点值）', Math.abs(ua2 - 50 * Math.sin(2 * Math.PI * 50 / 3200)) < 1e-4, String(ua2));
  await sleep(600);
  check('文件下拉自动刷新含新文件', [...$('rs-files').options].some((o) => o.value === 'data/' + OUT_NAME));
  check('预览提示输出已存在', /已存在/.test($('rs-preview').textContent));

  console.log('\n=== E4. 覆盖保护 / v0.35 已存在则跳过重采样只算误差 ===');
  const mtime0 = fs.statSync(outPath).mtimeMs;
  click($('btn-rs-run')); st = await waitDone();
  check('v0.35 未勾选覆盖 + 算误差 → 不失败，resample_skipped=true，steps.resample=skipped', st.result && !st.error && st.result.resample_skipped === true && st.result.steps.resample.status === 'skipped' && st.result.steps.error.status === 'done', st.error || JSON.stringify(st.result && st.result.steps));
  check('v0.35 输出文件未被改写（mtime 不变）', fs.statSync(outPath).mtimeMs === mtime0);
  check('v0.35 界面：第 1 步标签「已跳过」、第 2 步「完成」、状态行提示跳过', /已跳过/.test($('rs-step1-label').textContent) && /完成/.test($('rs-step2-label').textContent) && /已跳过/.test($('rs-status').textContent), $('rs-step1-label').textContent + ' | ' + $('rs-step2-label').textContent);
  check('v0.35 两步进度条都 100%', $('rs-bar').style.width === '100%' && $('rs-bar2').style.width === '100%');
  check('v0.35 状态接口含 step/steps/step_status', st.steps === 2 && st.step === 2 && st.step_status && st.step_status.resample === 'skipped', JSON.stringify([st.step, st.steps, st.step_status]));
  $('rs-err').checked = false; change($('rs-err')); await sleep(400);
  click($('btn-rs-run')); st = await waitDone();
  check('未勾选覆盖且不算误差 → 失败且界面显示「已存在」', st.error && /已存在/.test(st.error) && /已存在/.test($('rs-status').textContent), st.error);
  check('失败时进度条标红', $('rs-bar').classList.contains('err'));
  check('v0.35 不算误差时第 2 步标注未启用', /未启用/.test($('rs-step2-label').textContent), $('rs-step2-label').textContent);
  $('rs-err').checked = true; change($('rs-err')); await sleep(400);
  $('rs-overwrite').checked = true; $('rs-method').value = 'fft';
  click($('btn-rs-run')); st = await waitDone();
  check('勾选覆盖 + fft → 成功，行数 2N（周期语义）', st.result && !st.error && st.result.rows_out === 2 * N && st.result.method === 'fft', st.error || (st.result && st.result.rows_out));
  check('v0.35 两步都完成：标签「✓ 完成 · Ns」、resample_skipped=false', /✓ 完成 · [\d.]+s/.test($('rs-step1-label').textContent) && /✓ 完成 · [\d.]+s/.test($('rs-step2-label').textContent) && st.result.resample_skipped === false, $('rs-step1-label').textContent);

  console.log('\n=== E7. v0.34 相对误差（时间窗可配） ===');
  const ERR_NAME = OUT_NAME.replace(/\.csv$/, '_err.csv');
  const errPath = path.join(ROOT, 'data', ERR_NAME);
  check('E7 结果含 err_path 且默认时间窗来自配置(1s)', st.result.err_path === 'data/' + ERR_NAME && st.result.err_window_s === 1, JSON.stringify([st.result.err_path, st.result.err_window_s]));
  check('E7 _err.csv 真实存在，行数 = 表头 + 3 窗 + 汇总', fs.existsSync(errPath) && fs.readFileSync(errPath, 'utf8').split(/\r?\n/).filter((l) => l.trim()).length === 5, String(fs.existsSync(errPath)));
  const eh = fs.readFileSync(errPath, 'utf8').replace(/^\uFEFF/, '').split(/\r?\n/)[0];
  check('E7 误差 CSV 列名含通道_RMS相对误差 / _波形相对误差NRMSE', /A相电压_RMS相对误差/.test(eh) && /C相电流_波形相对误差NRMSE/.test(eh), eh.slice(0, 120));
  const elast = fs.readFileSync(errPath, 'utf8').trim().split(/\r?\n/).pop();
  check('E7 末行为汇总', /^汇总,/.test(elast), elast.slice(0, 40));
  check('E7 fft 升采样纯正弦：最大 NRMSE < 1%', st.result.err_nrmse_max < 0.01, String(st.result.err_nrmse_max));
  check('E7 界面显示误差文件名与误差表', $('rs-result2').textContent.includes(ERR_NAME) && !!document.getElementById('rs-err-table') && document.getElementById('rs-err-table').querySelectorAll('tbody tr').length === 6);
  $('rs-errwin').value = '0.5'; change($('rs-errwin')); await sleep(500);
  const cfgNow = await (await fetch(BASE + '/api/config')).json();
  check('E7 改时间窗 → PUT 配置 processing.error_window_s=0.5', (cfgNow.config || cfgNow).processing && (cfgNow.config || cfgNow).processing.error_window_s === 0.5, JSON.stringify((cfgNow.config || cfgNow).processing));
  click($('btn-rs-run')); await sleep(300);
  const b7 = bodies('/api/process/resample', 'POST').pop();
  check('E7 POST 载荷带 err_report=true、err_window_s=0.5', b7 && b7.err_report === true && b7.err_window_s === 0.5, JSON.stringify(b7));
  st = await waitDone();
  check('E7 窗 0.5s → 6 窗', st.result && st.result.err_windows === 6, st.error || String(st.result && st.result.err_windows));
  $('rs-err').checked = false; change($('rs-err')); await sleep(400);
  click($('btn-rs-run')); await sleep(300);
  const b8 = bodies('/api/process/resample', 'POST').pop();
  st = await waitDone();
  check('E7 关闭勾选 → 载荷 err_report=false、结果无 err_path、界面提示已关闭', b8 && b8.err_report === false && !('err_window_s' in b8) && st.result && !st.result.err_path && /已关闭/.test($('rs-result2').textContent), JSON.stringify(b8));
  const badw = await (await fetch(BASE + '/api/process/resample', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ path: 'data/' + SRC_NAME, fs_new: 6400, overwrite: true, err_report: true, err_window_s: 0 }) })).json();
  check('E7 err_window_s=0 → ok:false', badw.ok === false && /时间窗/.test(badw.error), badw.error);
  // 还原配置默认值
  $('rs-err').checked = true; $('rs-errwin').value = '1'; change($('rs-errwin')); await sleep(400);
  try { fs.unlinkSync(errPath); } catch (e) { /* ignore */ }

  console.log('\n=== E5. 用作离线播放源 ===');
  check('按钮可用', !$('btn-rs-use').disabled);
  click($('btn-rs-use')); await sleep(500);
  check('切到数据源页、kind=csv_file、path=输出文件', $('view-source').classList.contains('active') && $('src-kind').value === 'csv_file' && $('src-path').value === 'data/' + OUT_NAME, `${$('src-kind').value} ${$('src-path').value}`);

  console.log('\n=== E6. 非法参数 ===');
  const bad1 = await (await fetch(BASE + '/api/process/resample', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ path: 'data/' + SRC_NAME, fs_new: 0 }) })).json();
  check('fs_new=0 → ok:false', bad1.ok === false && /> 0/.test(bad1.error), bad1.error);
  const bad2 = await (await fetch(BASE + '/api/process/resample', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ path: 'data/不存在.csv', fs_new: 6400 }) })).json();
  check('路径不存在 → ok:false', bad2.ok === false && /不存在/.test(bad2.error), bad2.error);
  const bad3 = await (await fetch(BASE + '/api/process/resample', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ path: 'data/' + SRC_NAME, fs_new: 6400, out_dir: '../..' }) })).json();
  check('输出目录越界 → ok:false', bad3.ok === false && /越界/.test(bad3.error), bad3.error);
  await nav('process');
  $('rs-path').value = 'data/不存在.csv'; input($('rs-path')); await sleep(600);
  check('界面预览提示源文件不存在', /不存在/.test($('rs-preview').textContent));

  console.log('\n=== E8. v0.52 负荷辨识调参面板 ===');
  await nav('process'); await sleep(500);
  check('面板控件齐全', ['nt-files', 'nt-path', 'nt-tstart', 'nt-tend', 'nt-duration', 'nt-side', 'nt-quantity', 'nt-channel', 'nt-minw', 'nt-mina', 'nt-save', 'nt-name', 'btn-nt-run', 'btn-nt-apply', 'nt-result'].every((id) => !!$(id)));
  check('文件下拉已从 /api/files 填充且含 nilm_steps.csv', [...$('nt-files').options].some((o) => o.value === 'data/nilm_steps.csv'));
  $('nt-files').value = 'data/nilm_steps.csv'; change($('nt-files'));
  check('选中即填路径', $('nt-path').value === 'data/nilm_steps.csv');
  check('默认：保存未勾选、文件名空、套用按钮禁用', !$('nt-save').checked && $('nt-name').value === '' && $('btn-nt-apply').disabled);
  const cfgBefore = JSON.stringify((await (await fetch(BASE + '/api/config')).json()).nilm);
  $('nt-minw').value = '500'; click($('btn-nt-run')); await sleep(3000);
  let nb = bodies('/api/process/nilm_tune', 'POST').pop();
  check('整文件：载荷 t_start/t_end 空、duration null、save=false', nb && nb.t_start === '' && nb.t_end === '' && nb.duration_s === null && nb.save === false && nb.min_load_w === '500', JSON.stringify(nb));
  check('结果区显示周波 300 / 时间段 整个文件 / 未保存', /周波 300/.test($('nt-status').textContent) && /整个文件/.test($('nt-status').textContent) && /未保存结果文件/.test($('nt-status').textContent), $('nt-status').textContent.slice(0, 160));
  check('建议表含 6 算法且 threshold min_delta_w=250', /threshold/.test($('nt-result').textContent) && /steady_state/.test($('nt-result').textContent) && /min_delta_w=250/.test($('nt-result').textContent));
  check('运行配置未被改动', JSON.stringify((await (await fetch(BASE + '/api/config')).json()).nilm) === cfgBefore);
  check('套用按钮已启用', !$('btn-nt-apply').disabled);
  // 时间段：起始 = 文件开头 + 1 s（取结果里的 t_first），时长 2 s；保存，默认名
  const tFirst = JSON.parse($('nt-json').textContent).t_range.t_first;
  $('nt-tstart').value = String((tFirst + 1).toFixed(3)); $('nt-duration').value = '2'; $('nt-save').checked = true;
  click($('btn-nt-run')); await sleep(3000);
  nb = bodies('/api/process/nilm_tune', 'POST').pop();
  check('时间段载荷：t_start 填、duration_s=2、save=true、name 空', nb && nb.t_start === String((tFirst + 1).toFixed(3)) && nb.duration_s === '2' && nb.save === true && nb.name === '', JSON.stringify(nb));
  const stTxt = $('nt-status').textContent;
  check('结果：周波≈100、已保存到 output/nilm/tune_<时间>.json', /周波 (99|100|101)/.test(stTxt) && /已保存结果到/.test(stTxt) && /output\/nilm\/tune_\d{8}_\d{6}\.json/.test(stTxt), stTxt.slice(0, 200));
  const savedRel = (stTxt.match(/output\/nilm\/tune_\d{8}_\d{6}\.json/) || [])[0];
  check('保存的文件真实存在且含 suggest', !!savedRel && fs.existsSync(path.join(ROOT, savedRel)) && JSON.parse(fs.readFileSync(path.join(ROOT, savedRel), 'utf8')).suggest.algorithms.glr.threshold === 25);
  // 自定义文件名
  $('nt-name').value = 'site_bg'; click($('btn-nt-run')); await sleep(3000);
  check('自定义名 → output/nilm/site_bg.json', /output\/nilm\/site_bg\.json/.test($('nt-status').textContent) && fs.existsSync(path.join(ROOT, 'output/nilm/site_bg.json')));
  // 非法时间 → 界面显示失败
  $('nt-tstart').value = 'abc'; $('nt-save').checked = false; click($('btn-nt-run')); await sleep(1500);
  check('非法起始时间 → 显示失败信息', /失败/.test($('nt-status').textContent) && /无法解析/.test($('nt-status').textContent), $('nt-status').textContent.slice(0, 120));
  // 套用到运行配置（用上次成功结果）
  click($('btn-nt-apply')); await sleep(1500);
  const cfgAfter = (await (await fetch(BASE + '/api/config')).json()).nilm;
  check('套用后运行配置 threshold.min_delta_w=250（热生效）', cfgAfter.algorithms.threshold.min_delta_w === 250 && /已套用 \d+ 项/.test($('nt-status').textContent));
  await fetch(BASE + '/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nilm: JSON.parse(cfgBefore) }) });
  try { if (savedRel) fs.unlinkSync(path.join(ROOT, savedRel)); fs.unlinkSync(path.join(ROOT, 'output/nilm/site_bg.json')); } catch (e) { /* ignore */ }

  // 收尾：删除测试文件
  try { fs.unlinkSync(outPath); fs.unlinkSync(path.join(ROOT, 'data', SRC_NAME)); } catch (e) { /* ignore */ }
  console.log(`\n=== 结果：PASS ${pass} / FAIL ${fail} ===`);
  if (fails.length) { console.log('失败项：'); fails.forEach((f) => console.log('  - ' + f)); }
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error('脚本异常：', e); process.exit(2); });
