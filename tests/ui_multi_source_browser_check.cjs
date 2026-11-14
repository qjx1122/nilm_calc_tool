#!/usr/bin/env node
// Optional: NODE_PATH=/path/to/browser-deps/node_modules node tests/ui_multi_source_browser_check.cjs http://127.0.0.1:8778
const assert = require('node:assert/strict');
const chromiumPkg = require('@sparticuz/chromium').default;
const {chromium} = require('playwright-core');
const base = process.argv[2] || 'http://127.0.0.1:8778';
(async () => {
  const browser = await chromium.launch({executablePath:await chromiumPkg.executablePath(), args:chromiumPkg.args, headless:true});
  const page = await browser.newPage({viewport:{width:1440,height:900}});
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  const calls = [];
  await page.route('**/api/process/nilm_profile_multi', async route => {
    const p=route.request().postDataJSON(); calls.push(p);
    await route.fulfill({json:{ok:true,revision:'rev',startup:{n:1},shutdown:null,notes:['请复核'],events:[{event_id:'source-1:100:START',source_id:'source-1',direction:'START',t_start_local:'time',onset:100,end:101,vec:{d_ia:5}}]}});
  });
  try {
    await page.goto(base+'/', {waitUntil:'domcontentloaded'});
    await page.locator('.navitem[data-view="process"]').click();
    await page.locator('[data-subview="profile-extract"]').click();
    await page.locator('#btn-npm-add').click(); await page.locator('#btn-npm-add').click();
    const modules=page.locator('.npm-module'), a=modules.nth(0), b=modules.nth(1);
    const fa=k=>a.locator(`[data-field="${k}"]`), fb=k=>b.locator(`[data-field="${k}"]`);
    await fa('device_id').fill('风机 A'); await fb('device_id').fill('水泵 B');
    await fa('path').fill('fan.csv'); await fb('path').fill('pump.csv');
    assert.match(await a.locator('.npm-device-name').innerText(),/风机 A/);
    const geom=await page.evaluate(() => {
      const [a,b]=document.querySelectorAll('.npm-module'); const r=e=>e.getBoundingClientRect();
      return {bottom:r(a).bottom, top:r(b).top, aLeft:r(a.querySelector('.npm-params')).left, aRight:r(a.querySelector('.npm-params')).right,
              resultLeft:r(a.querySelector('.npm-result-panel')).left, border:getComputedStyle(a).borderLeftWidth,
              panel:getComputedStyle(a.querySelector('.npm-params')).backgroundColor,
              oldPanel:getComputedStyle(document.querySelector('#np-form').closest('.panel')).backgroundColor};
    });
    assert(geom.top-geom.bottom >= 10 && geom.resultLeft >= geom.aRight && parseFloat(geom.border)>=3);
    assert.equal(geom.panel,geom.oldPanel);
    await a.locator('[data-action="preview"]').click();
    await a.locator('[data-event]').waitFor(); assert.equal(calls.length,1); assert.equal(calls[0].device_id,'风机 A');
    assert(await a.locator('[data-action="save"]').isEnabled());
    await a.locator('.npm-module-summary').click();
    assert(!await a.evaluate(e=>e.open) && await b.evaluate(e=>e.open));
    assert(!await a.locator('.npm-params').isVisible());
    await a.locator('.npm-module-summary').focus(); await page.keyboard.press('Enter');
    assert(await a.evaluate(e=>e.open) && await b.evaluate(e=>e.open));
    assert.equal(await fa('path').inputValue(),'fan.csv'); assert(await a.locator('[data-action="save"]').isEnabled());
    for (const width of [900,600]) {
      await page.setViewportSize({width,height:900});
      const layout=await a.evaluate(el=>{
        const box=el.getBoundingClientRect(), p=el.querySelector('.npm-params').getBoundingClientRect(), r=el.querySelector('.npm-result-panel').getBoundingClientRect();
        return {client:el.clientWidth,scroll:el.scrollWidth,stacked:r.top >= p.bottom-1,box:box.width};
      });
      assert(layout.stacked,`width ${width}: panels should stack`);
      assert(layout.scroll <= layout.client+1, `width ${width}: module must not overflow (${JSON.stringify(layout)})`);
    }
    await page.setViewportSize({width:1440,height:900});
    await page.screenshot({path:'/tmp/nilm-multi-profile-ui.png',fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('multi-source browser layout, collapse, keyboard and state: passed');
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1});
