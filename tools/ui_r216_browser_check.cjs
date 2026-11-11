#!/usr/bin/env node
/* 第 216 轮：在隔离测试服务运行（会写浏览器 localStorage；只发只读 API）。
 * 依赖 playwright-core 与 @sparticuz/chromium：通过 NODE_PATH 指向临时安装位置。
 * 示例：NODE_PATH=/tmp/browser-deps/node_modules node tools/ui_r216_browser_check.cjs http://127.0.0.1:8767
 * 服务与本脚本必须位于同一主机，以便服务读取临时合成 CSV；完成后自动删除合成数据。 */
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const BASE = process.argv[2] || 'http://127.0.0.1:8767';
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ui_r216_'));
const wave = path.join(dir, 'wave.csv'), monFile = path.join(dir, 'voltage_20260921.csv');
function writeInputs() {
 const rows = ['时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流'];
 for (let k=0; k<6*6400; k++) { let t=k/6400, row=[(1700000000+t).toFixed(6)];
   for (const p of [0,-2*Math.PI/3,2*Math.PI/3]) row.push((81.65*Math.sin(2*Math.PI*50*t+p)).toFixed(4), (7.07*Math.sin(2*Math.PI*50*t+p-.3)).toFixed(5));
   rows.push(row.join(',')); }
 fs.writeFileSync(wave,rows.join('\n')+'\n');
 const mon=['t_epoch_s,time_local,source_id,window_s,Ua,Ub,Uc,Uab,Ubc,Uca,unbalance_pct,U1,run_id'];
 for (let k=0;k<5;k++) mon.push(`${1700000000+k},2026-09-21 00:00:00.000,0,1,${100+k},${200+k},${300+k},1,2,3,0.1,,1790000200222`);
 fs.writeFileSync(monFile,mon.join('\n')+'\n');
}
writeInputs();
process.on('exit',()=>fs.rmSync(dir,{recursive:true,force:true}));
const chromiumPkg = require('@sparticuz/chromium').default;
const {chromium} = require('playwright-core');
const assert = require('node:assert/strict');
(async()=>{
 const browser = await chromium.launch({executablePath:await chromiumPkg.executablePath(), args:chromiumPkg.args, headless:true});
 const page = await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
 const errors=[], writes=[]; page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if (new URL(r.url()).pathname.startsWith('/api/') && r.method() !== 'GET') writes.push(r.method()+' '+r.url());});
 let n=0; const ok=(name,cond)=>{assert.ok(cond,name);n++;console.log('✓ '+name)};
 async function info(which) {return page.locator(which).evaluate(el=>{
  const row=el.closest('.wb-chart-row'), a=row.querySelector('.wb-chart canvas'), b=row.querySelector('.wb-detail canvas'), t=row.querySelector('.wb-chart-title'), d=row.querySelector('.wb-detail-title');
  const r=x=>{let q=x.getBoundingClientRect();return {top:q.top,bottom:q.bottom,left:q.left,right:q.right,width:q.width,height:q.height}};
  const sty=x=>{let s=getComputedStyle(x);return [s.fontSize,s.fontWeight,s.fontFamily,s.color,s.lineHeight]};
  return {a:r(a),b:r(b),t:r(t),d:r(d),ta:sty(t),tb:sty(d),width:row.clientWidth,scrollWidth:row.scrollWidth,scrollLeft:row.scrollLeft,heightA:a.__chart?.h,heightB:b.__chart?.h,status:row.querySelector('.wb-detail-status').textContent,tip:row.querySelector('.wb-detail .zoomtip').textContent};
 });}
 async function checkAlignment(selector, label) {let x=await info(selector); console.log(label, JSON.stringify(x));
  ok(label+' 画布顶底对齐',Math.abs(x.a.top-x.b.top)<1 && Math.abs(x.a.bottom-x.b.bottom)<1 && x.heightA===x.heightB);
  ok(label+' 标题字体一致',JSON.stringify(x.ta)===JSON.stringify(x.tb) && Math.abs(x.t.top-x.d.top)<1);
  ok(label+' 无拖选和缩放说明',!x.status && !/拖选|缩放|复位/.test(x.tip)); return x; }
 async function open(main,key){let c=page.locator(main);await c.click({button:'right', position:{x:120,y:80}});await page.locator('#ctxmenu [data-key="'+key+'"]').click(); await page.waitForFunction(()=>Object.values(window.WB.rt).some(rt=>Object.values(rt.details || {}).some(d=>d.data)));}
 async function checkBoardHelp(module,label){
  const res = await module.locator('.zoombar').evaluateAll(bars => bars.map(bar => ({label:bar.querySelector('.panlbl')?.textContent, legend:bar.closest('.serlegend')?.innerText||'', tip:bar.querySelector('.zoomtip').textContent, visible:getComputedStyle(bar.querySelector('.zoomtip')).display!=='none', zoom:!!window.ZOOM[bar.dataset.chart], buttons:[...bar.querySelectorAll('.pan-btn')].map(btn=>({title:btn.getAttribute('title'),name:btn.getAttribute('aria-label')}))})));
  ok(label+'无三个文字标签及操作说明，保留悬停提示',res.length>0 && res.every(x=>!x.label && !/(显示|缩放|移动)：/.test(x.legend) && !x.visible && x.tip==='' && x.buttons.length===4 && x.buttons.every(b=>/移动/.test(b.title||'') && /平移/.test(b.name||''))));
 }
 try {
 await page.goto(BASE + '/',{waitUntil:'domcontentloaded'});
 await page.locator('.navitem[data-view="process"]').click(); await page.locator('#sub-nav-process .sub-navitem[data-subview="wave-board"]').click();
 await page.locator('#btn-wb-add-offline').click(); const off=page.locator('#wb-modules .wb-module').first();
 await off.locator('[data-wb-f="off-path"]').fill(wave); await off.locator('[data-wb-f="off-path"]').dispatchEvent('change'); await off.locator('[data-wb-act="load"]').click();
 await page.waitForFunction(()=>{let m=window.WB.modules[0];return window.WB.rt[m.id]?.data && document.querySelector('[data-wb-chart="u"] canvas').__chart});
 await checkBoardHelp(off,'电压、电流未缩放');
 await open('[data-wb-chart="u"] canvas','show-window2'); await checkAlignment('[data-wb-chart="u"]','桌面电压瞬时'); await checkBoardHelp(off,'电压与瞬时');

 // 电压与电流周波窗同时显示：真实布局、缩放与关闭彼此独立。
 await open('[data-wb-chart="i"] canvas','show-window');
 await page.waitForFunction(()=>{let m=window.WB.modules[0];return !!window.WB.rt[m.id]?.details?.i?.data});
 const ud=off.locator('.wb-detail[data-wb-key="u"]'), id=off.locator('.wb-detail[data-wb-key="i"]');
 ok('电压电流周波图同时可见',await ud.isVisible() && await id.isVisible());
 await checkAlignment('[data-wb-chart="i"]','同时显示电流有效值');
 await id.locator('[data-z="x-"]').click();
 ok('电流周波图缩放不影响电压周波图',await page.evaluate(()=>{let m=window.WB.modules[0];return !!window.ZOOM['wb-detail-'+m.id+'-i']?.x && !window.ZOOM['wb-detail-'+m.id+'-u']}));
 await id.locator('[data-wb-act="detail-close"]').click();
 ok('关闭电流周波图不影响电压周波图',await ud.isVisible() && !(await id.isVisible()));
 let u=off.locator('[data-wb-chart="u"]'); let d=off.locator('.wb-detail[data-wb-key="u"]');
 await u.locator('canvas').hover({position:{x:160,y:80}}); await page.mouse.wheel(0,-120);
 await page.waitForFunction(()=>{let m=window.WB.modules[0];return !!window.ZOOM['wb-cv-'+m.id+'-u']?.x});
 await checkBoardHelp(off,'鼠标滚轮缩放后');
 await u.locator('[data-z="reset"]').click();
 const canvas = u.locator('canvas'); await canvas.scrollIntoViewIfNeeded(); const rect=await canvas.boundingBox();
 await page.mouse.move(rect.x+120,rect.y+50); await page.mouse.down(); await page.mouse.move(rect.x+220,rect.y+140,{steps:4}); await page.mouse.up();
 ok('鼠标框选完成后缩放成功',await canvas.evaluate(cv=>!!window.ZOOM[cv.id]?.x)); await checkBoardHelp(off,'鼠标框选缩放后');
 await u.locator('[data-z="reset"]').click();
 await u.locator('[data-z="x-"]').click(); let z=await page.evaluate(()=>{let m=window.WB.modules[0];return {main:window.ZOOM['wb-cv-'+m.id+'-u'], detail:window.ZOOM['wb-detail-'+m.id+'-u']}});
 ok('主图缩放不改变周波图',!!z.main?.x && !z.detail);
 ok('放大后主图不显示移动、拖选或缩放说明',await u.locator('.zoomtip').evaluate(el => getComputedStyle(el).display==='none' && el.textContent===''));
 await u.locator('[data-z="pr"]').click(); let zMoved=await page.evaluate(()=>{let m=window.WB.modules[0];return window.ZOOM['wb-cv-'+m.id+'-u']});
 ok('主图移动按钮仍可用',zMoved.x[0] > z.main.x[0]); z.main=zMoved; await checkBoardHelp(off,'主图缩放移动后');
 await u.locator('[data-z="pr"]').hover(); ok('主图方向按钮悬停说明保留',/向右移动 X 轴（→ 键）/.test(await u.locator('[data-z="pr"]').getAttribute('title')));
 await u.locator('canvas').hover({position:{x:120,y:80}}); ok('主图曲线悬停取值保留',await u.locator('canvas').evaluate(cv=>!!cv.__hoverInfo && cv.__hoverInfo.items.length===3));
 await d.locator('canvas').hover({position:{x:160,y:80}}); await page.mouse.wheel(0,-120);
 await page.waitForFunction(()=>{let m=window.WB.modules[0];return !!window.ZOOM['wb-detail-'+m.id+'-u']?.x}); await checkBoardHelp(off,'周波图鼠标滚轮缩放后');
 await d.locator('[data-z="pr"]').click(); let z2=await page.evaluate(()=>{let m=window.WB.modules[0];return {main:window.ZOOM['wb-cv-'+m.id+'-u'], detail:window.ZOOM['wb-detail-'+m.id+'-u']}});
 ok('周波图缩放移动不改变主图',JSON.stringify(z.main)===JSON.stringify(z2.main) && !!z2.detail?.x);
 await d.locator('[data-z="pr"]').hover(); ok('周波图方向按钮悬停说明保留',/向右移动 X 轴（→ 键）/.test(await d.locator('[data-z="pr"]').getAttribute('title')));
 await d.locator('canvas').hover({position:{x:120,y:80}}); ok('周波图曲线悬停取值保留',await d.locator('canvas').evaluate(cv=>!!cv.__hoverInfo && cv.__hoverInfo.items.length===3));
 ok('放大后周波图不显示移动、拖选或缩放说明',await d.locator('.zoomtip').evaluate(el => getComputedStyle(el).display==='none' && el.textContent===''));
 await d.locator('.ser-vis[data-name="Ua"]').uncheck(); let counts=await page.evaluate(()=>{let m=window.WB.modules[0];return [document.getElementById('wb-cv-'+m.id+'-u').__chart.pts.length,document.getElementById('wb-detail-'+m.id+'-u').__chart.pts.length]});
 ok('图例显示分别操作',counts[0]===3 && counts[1]===2);
 await d.locator('[data-wb-act="detail-close"]').click(); await open('[data-wb-chart="i"] canvas','show-window'); d=off.locator('.wb-detail[data-wb-key="i"]'); await checkAlignment('[data-wb-chart="i"]','桌面电流有效值'); await checkBoardHelp(off,'电流与有效值');
 await d.locator('canvas').hover({position:{x:160,y:80}}); await page.mouse.wheel(0,-120);
 await page.waitForFunction(()=>{let m=window.WB.modules[0];return !!window.ZOOM['wb-detail-'+m.id+'-i']?.x}); await checkBoardHelp(off,'有效值周波图鼠标缩放后');
 await d.locator('[data-z="reset"]').click();
 await off.locator('[data-wb-f="off-show"]').selectOption('i');await checkAlignment('[data-wb-chart="i"]','单电流模式');
 await page.setViewportSize({width:500,height:900});await page.waitForTimeout(300); let narrow=await checkAlignment('[data-wb-chart="i"]','窄屏');
 ok('窄屏保持并排并可横向滚动',narrow.scrollWidth>narrow.width && narrow.b.left>=narrow.a.right);
 let canScroll=await off.locator('[data-wb-chart="i"]').evaluate(el=>{let row=el.closest('.wb-chart-row');row.scrollLeft=200;return row.scrollLeft>0});ok('窄屏横向滚动实际可用',canScroll);
 await page.setViewportSize({width:1600,height:1000});await page.locator('#btn-wb-add-monitor').click();const mon=page.locator('#wb-modules .wb-module').nth(1);
 await mon.locator('[data-wb-f="mon-path"]').fill(monFile);await mon.locator('[data-wb-f="mon-path"]').dispatchEvent('change');
 await mon.locator('[data-wb-act="more"]').click();await mon.locator('[data-wb-f="mon-raw-path"]').fill(wave);await mon.locator('[data-wb-f="mon-raw-path"]').dispatchEvent('change');await mon.locator('[data-wb-act="load"]').click();
 await page.waitForFunction(()=>{let m=window.WB.modules[1];return document.getElementById('wb-cv-'+m.id+'-m')?.__chart});
 await open('[data-wb-chart="m"] canvas','show-window2'); await page.waitForFunction(()=>{let m=window.WB.modules[1];return window.WB.rt[m.id]?.details?.m?.data}); await checkAlignment('[data-wb-chart="m"]','监测瞬时'); await checkBoardHelp(mon,'监测与瞬时');
 await mon.locator('[data-wb-chart="m"] canvas').hover({position:{x:160,y:80}}); await page.mouse.wheel(0,-120);
 await page.waitForFunction(()=>{let m=window.WB.modules[1];return !!window.ZOOM['wb-cv-'+m.id+'-m']?.x});
 await checkBoardHelp(mon,'监测图鼠标缩放后');
 await page.locator('#wb-layout').selectOption('2');await page.waitForTimeout(300);await checkAlignment('[data-wb-chart="m"]','两列模块');
 ok('浏览器未发生脚本错误',errors.length===0);ok('没有修改类 API 请求',writes.length===0);console.log('PASS',n);
 } finally {await browser.close();}
})().catch(e=>{console.error(e.stack);process.exit(1)});
