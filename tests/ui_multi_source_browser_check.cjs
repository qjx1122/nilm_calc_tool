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
  const calls = [], oldCalls = [], stageCalls = []; let fileCalls = 0;
  let available = [{name:'data/fan.csv',size_mb:1},{name:'data/fan-stop.CSV',size_mb:2},{name:'data/folder/',dir:true},{name:'data/other.txt',size_mb:3}];
  await page.route('**/api/files?sub=data', async route => { fileCalls++; await route.fulfill({json:{ok:true,files:available}}); });
  await page.route('**/api/process/nilm_profile_stage', async route => {
    stageCalls.push(route.request().postDataJSON());
    await route.fulfill({json:{ok:true,base:{device_id:'legacy',window:{}},rows:[],paths:'stage.json',notes:[]}});
  });
  await page.route('**/api/process/nilm_profile', async route => {
    oldCalls.push(route.request().postDataJSON());
    await route.fulfill({json:{ok:true,saved_to:'old-profile.json',profile:{device_id:'legacy',pre_cycles:10,post_cycles:50},features:[],startup:null,shutdown:null,notes:[]}});
  });
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
    const first=a.locator('.npm-source').first();
    await first.locator('[data-field="files"] option[value="data/fan.csv"]').waitFor({state:'attached'});
    assert.equal(await first.locator('[data-field="files"] option').count(),3);
    await first.locator('[data-field="files"]').selectOption('data/fan.csv');
    assert.equal(await first.locator('[data-field="path"]').inputValue(),'data/fan.csv');
    await fb('path').fill('/manual/pump.csv');
    await a.locator('[data-action="add-source"]').click();
    const second=a.locator('.npm-source').nth(1);
    await second.locator('[data-field="files"]').selectOption('data/fan-stop.CSV');
    assert.equal(await second.locator('[data-field="path"]').inputValue(),'data/fan-stop.CSV');
    assert.equal(await fb('path').inputValue(),'/manual/pump.csv');
    for (const selector of ['.npm-device-group','.npm-window-group','.npm-source','.npm-map-group']) {
      const group=a.locator(selector).first();
      await group.locator(':scope > summary').click(); assert(!await group.evaluate(e=>e.open),selector);
      if (selector !== '.npm-map-group') assert(await b.locator(selector).first().evaluate(e=>e.open),`other device ${selector}`);
      await group.locator(':scope > summary').click(); assert(await group.evaluate(e=>e.open),selector);
    }
    await a.locator('.npm-base > summary').click(); assert(await a.locator('.npm-base').evaluate(e=>e.open));
    await a.locator('.npm-base > summary').click(); assert(!await a.locator('.npm-base').evaluate(e=>e.open));
    await a.locator('.npm-source').first().locator(':scope > summary').click();
    assert(!await a.locator('.npm-source').first().evaluate(e=>e.open));
    assert(await a.locator('.npm-source').nth(1).evaluate(e=>e.open));
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
    await a.locator('[data-event]').waitFor(); assert.equal(calls.length,1); assert.equal(calls[0].device_id,'风机 A'); assert.deepEqual(calls[0].sources.map(x=>x.path),['data/fan.csv','data/fan-stop.CSV']);
    assert(await a.locator('[data-action="save"]').isEnabled());
    available=[{name:'data/updated.csv',size_mb:4}];
    await first.locator(':scope > summary').click();
    const before=fileCalls; await first.locator('[data-action="refresh-files"]').click();
    await page.waitForFunction(n=>document.querySelector('.npm-source [data-field="files"] option[value="data/updated.csv"]'),before);
    assert(fileCalls>before); assert.equal(await first.locator('[data-field="path"]').inputValue(),'data/fan.csv');
    assert.equal(await second.locator('[data-field="path"]').inputValue(),'data/fan-stop.CSV');
    assert.equal(await fb('path').inputValue(),'/manual/pump.csv'); assert(await a.locator('[data-action="save"]').isEnabled());
    await first.locator(':scope > summary').click();
    await a.locator('.npm-result-group > summary').click(); assert(!await a.locator('.npm-result-group').evaluate(e=>e.open));
    assert(await a.locator('.npm-status').isVisible());
    await a.locator('.npm-result-group > summary').click();
    assert(await a.locator('[data-event]').isChecked() && await a.locator('[data-action="save"]').isEnabled());
    await a.locator('.npm-module-summary').click();
    assert(!await a.evaluate(e=>e.open) && await b.evaluate(e=>e.open));
    assert(!await a.locator('.npm-params').isVisible());
    await a.locator('.npm-module-summary').focus(); await page.keyboard.press('Enter');
    assert(await a.evaluate(e=>e.open) && await b.evaluate(e=>e.open));
    assert.equal(await a.locator('.npm-source').first().locator('[data-field="path"]').inputValue(),'data/fan.csv'); assert(await a.locator('[data-action="save"]').isEnabled());
    // 旧入口的每个分组独立折叠，输入不丢失，折叠时也用于原 API 载荷。
    const legacyGroups=['np-source-group','np-base','np-cm-group','np-device-group','np-locate-group','np-window-group','np-stage-group','np-result-group'];
    await page.locator('#np-path').fill('legacy.csv'); await page.locator('#np-device').fill('legacy');
    await page.locator('#np-labels').fill('1700000002,开');
    await page.locator('#np-cm-on').check(); await page.locator('#np-cm-ia').fill('3');
    for (const id of legacyGroups) {
      const group=page.locator('#'+id); assert(await group.evaluate(e=>e.open),id);
      await group.locator(':scope > summary').click(); assert(!await group.evaluate(e=>e.open),id);
      await group.locator(':scope > summary').focus(); await page.keyboard.press('Enter'); assert(await group.evaluate(e=>e.open),id);
    }
    await page.locator('#np-source-group > summary').click();
    await page.locator('#np-cm-group > summary').click();
    await page.locator('#np-base > summary').click();
    await page.locator('#np-locate-group > summary').click();
    await page.locator('#np-result-group > summary').click();
    await page.locator('#btn-np-run').click();
    await page.waitForFunction(()=>document.querySelector('#np-status').textContent.includes('old-profile.json'));
    assert.equal(oldCalls.length,1); assert.equal(oldCalls[0].path,'legacy.csv'); assert.equal(oldCalls[0].device_id,'legacy');
    assert.equal(oldCalls[0].labels,'1700000002,开'); assert(oldCalls[0].col_map_enabled);
    assert(!await page.locator('#np-result-group').evaluate(e=>e.open));
    assert(await page.locator('#np-status').isVisible());
    await page.locator('#np-result-group > summary').click();
    assert.match(await page.locator('#np-status').innerText(),/old-profile.json/);
    assert(await page.locator('#btn-np-stage').isEnabled());
    await page.locator('#np-stage-scales').fill('0.7');
    await page.locator('#np-result-group > summary').click();
    await page.locator('#btn-np-stage').click();
    await page.waitForFunction(()=>document.querySelector('#np-stage-pathstr').textContent === 'stage.json');
    assert.equal(stageCalls.length,1); assert.equal(stageCalls[0].profile,'old-profile.json'); assert.equal(stageCalls[0].scales,'0.7');
    assert(await page.locator('#np-stage-status').isVisible() && !await page.locator('#np-result-group').evaluate(e=>e.open));
    await page.locator('#np-result-group > summary').click(); assert(await page.locator('#btn-np-stage-copy').isEnabled());
    await page.locator('#np-base > summary').click(); await page.locator('#np-cm-group > summary').click();
    assert(await page.locator('#np-cm-on').isChecked()); assert.equal(await page.locator('#np-cm-ia').inputValue(),'3');
    await page.locator('#np-side').selectOption('bus');
    assert.match(await page.locator('#np-base > summary').innerText(),/总线侧/);
    await page.locator('#np-base > summary').click(); assert(!await page.locator('#np-base').evaluate(e=>e.open));
    await page.locator('#np-base > summary').click(); await page.locator('#np-side').selectOption('custom');
    assert.match(await page.locator('#np-base > summary').innerText(),/独立基准配置/);
    await page.locator('#np-source-group > summary').click(); await page.locator('#np-locate-group > summary').click();
    assert.equal(await page.locator('#np-path').inputValue(),'legacy.csv'); assert.equal(await page.locator('#np-labels').inputValue(),'1700000002,开');
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
