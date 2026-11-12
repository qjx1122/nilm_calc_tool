#!/usr/bin/env node
/* 画像提取口径与相别控件联动；对隔离服务运行，不改配置或用户数据。
 * JSDOM_DIR=<jsdom 所在目录> node tools/ui_r228_profile_phase_gate_check.cjs http://127.0.0.1:8766 */
const assert = require('assert');
const {boot, sleep} = require('./ui_r213_check.cjs');

async function main() {
  let p, count = 0;
  const check = (label, condition) => { assert.ok(condition, label); count++; console.log(' ✓ ' + label); };
  try {
    p = await boot(null);
    const {document, window, click, set, calls, errors} = p;
    const el = id => document.getElementById(id);
    click(document.querySelector('.navitem[data-view="process"]')); await sleep(400);
    click(document.querySelector('#sub-nav-process .sub-navitem[data-subview="profile-extract"]')); await sleep(800);
    const mode = el('np-single-mode'), branch = el('np-branch-phase'), bus = el('np-bus-phase'), phases = el('np-phases');
    const off = input => input.closest('label').classList.contains('off');
    check('默认原有口径', mode.value === 'legacy');
    check('原有口径禁用两侧相并置灰', branch.disabled && bus.disabled && off(branch) && off(bus));
    check('原有口径设备相别可用', !phases.disabled && !off(phases));
    set(phases, 'AC');
    set(mode, 'current');
    check('纯电流允许选择两侧相', !branch.disabled && !bus.disabled && !off(branch) && !off(bus));
    check('纯电流禁用设备相别并置灰', phases.disabled && off(phases));
    set(branch, 'A'); set(bus, 'C');
    const current = window.npPayload();
    check('纯电流载荷按两侧相', current.single_phase_mode === 'current' && current.branch_phase === 'A' && current.bus_phase === 'C');
    set(mode, 'voltage_current');
    check('电压＋电流同样仅启用两侧相', !branch.disabled && !bus.disabled && phases.disabled);
    check('两种单相间切换保留两侧选择', branch.value === 'A' && bus.value === 'C');
    set(mode, 'legacy');
    check('切回原有口径状态正确', branch.disabled && bus.disabled && !phases.disabled);
    check('切回原有口径保留设备相别', phases.value === 'AC');
    const legacy = window.npPayload();
    check('原有口径载荷保留原有设备相别', legacy.single_phase_mode === 'legacy' && legacy.phases === 'AC');
    set(mode, 'current');
    check('再次进入单相仍保留两侧选择', branch.value === 'A' && bus.value === 'C');
    click(document.querySelector('#sub-nav-process .sub-navitem[data-subview="nilm-tune"]')); await sleep(100);
    click(document.querySelector('#sub-nav-process .sub-navitem[data-subview="profile-extract"]')); await sleep(100);
    check('离开再进入后状态未变', mode.value === 'current' && !branch.disabled && !bus.disabled && phases.disabled);
    check('切换不修改运行配置且无脚本错误', !calls.some(c => c.method !== 'GET') && errors.length === 0);
    console.log(`PASS ${count}`);
  } finally { if (p) p.window.close(); }
}
main().catch(e => { console.error(e.stack || e); process.exitCode = 1; });
