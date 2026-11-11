#!/usr/bin/env node
/* 波形预览模块列映射：真实 API + jsdom；通过 b5_run.sh 在隔离副本运行。 */
const fs = require('fs'), os = require('os'), path = require('path'), assert = require('assert');
const {boot, sleep} = require('./ui_r213_check.cjs');
const KEY = 'elec_tool.wave_board.v1';
async function main() {
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'wb222-')), file=path.join(dir,'reordered.csv');
 const rows=['c1,c2,c3,c4,c5,c6,c7'];
 for(let k=0;k<12800;k++) { const w=2*Math.PI*50*k/6400, u=81.65*Math.sin(w), i=7.071*Math.sin(w); rows.push([i.toFixed(5),(1700000000+k/6400).toFixed(6),u.toFixed(5),u.toFixed(5),i.toFixed(5),u.toFixed(5),i.toFixed(5)].join(',')); }
 fs.writeFileSync(file,rows.join('\n')+'\n');
 let p; let n=0; const check=(name, f)=>{assert.ok(f(),name); n++; console.log(' ✓ '+name);};
 try {
  p=await boot(null); await p.openBoard(); const {window,document,click,set,change,idle,mods,field,act}=p;
  click(document.getElementById('btn-wb-add-offline')); click(document.getElementById('btn-wb-add-offline'));
  const [a,b]=mods(), model=()=>window.WB.modules.find(m=>m.id===a.dataset.wbId), rt=()=>window.WB.rt[a.dataset.wbId];
  check('旧模块默认映射关闭',()=>!field(a,'off-map-enabled').checked && a.querySelector('.wb-colmap-row').hidden);
  set(field(a,'off-path'),file); click(act(a,'more'));
  field(a,'off-map-enabled').checked=true; change(field(a,'off-map-enabled'));
  set(field(a,'off-map-timestamp'),'2'); set(field(a,'off-map-ua'),'3'); set(field(a,'off-map-ia'),'1');
  check('映射控件展开且模块隔离',()=>!a.querySelector('.wb-colmap-row').hidden && !field(b,'off-map-enabled').checked);
  click(act(a,'info')); await sleep(1000);
  check('文件信息使用重排列时标及通道',()=>rt().info && Math.abs(rt().info.t_start-1700000000)<0.01 && rt().info.columns.Ua===2 && rt().info.columns.Ia===0);
  click(act(a,'load')); await idle();
  check('主曲线读取重排列电压电流',()=>rt().data && Math.abs(rt().data.channels.Ua[0]-57.735)<1 && Math.abs(rt().data.channels.Ia[0]-5)<0.2);
  set(field(a,'off-map-ua'),'1'); set(field(a,'off-map-ia'),'3');
  check('修改未加载配置不覆盖主曲线快照',()=>JSON.parse(rt().loadedOffline.col_map).ua==='3');
  const center=rt().data.t[Math.floor(rt().data.t.length/2)];
  await window.wbLoadDetail(model(),'u',center,'wave');
  check('瞬时周波用加载快照读取电压',()=>rt().details.u?.data && Math.max(...rt().details.u.data.data.channels.Ua)>80);
  await window.wbLoadDetail(model(),'i',center,'rms');
  check('有效值周波用加载快照读取电流',()=>rt().details.i?.data && Math.abs(rt().details.i.data.data.channels.Ia[0]-5)<0.2);
  const last = p.calls.filter(x=>x.url.includes('/api/process/wave/')).slice(-4);
  check('详情两个接口均携带旧映射',()=>last.every(x=>JSON.parse(new URL(x.url, 'http://localhost').searchParams.get('col_map')).ua==='3'));
  click(act(a,'load')); await idle();
  check('重新加载采用新映射',()=>Math.abs(rt().data.channels.Ua[0]-5)<0.2);
  set(field(a,'off-map-ia'),'1'); click(act(a,'load')); await idle();
  check('重复列号拒绝且保留原图',()=>/重复/.test(p.status(a)) && rt().data && Math.abs(rt().data.channels.Ua[0]-5)<0.2);
  set(field(a,'off-map-ia'),'0'); click(act(a,'info')); await sleep(100);
  check('非法列号文件信息明确报错',()=>/从 1 开始/.test(p.status(a)));
  set(field(a,'off-map-ia'),'3'); set(field(a,'off-map-ub'),'99'); click(act(a,'info')); await sleep(800);
  check('超出实际列数时报错',()=>/超出文件列数/.test(p.status(a)));
  set(field(a,'off-map-ub'),''); set(field(a,'off-map-ib'),''); set(field(a,'off-map-uc'),''); set(field(a,'off-map-ic'),'');
  click(act(a,'load')); await idle();
  check('部分映射仅加载指定通道',()=>rt().data && Object.keys(rt().data.channels).join(',')==='Ua,Ia');
  const origFetch=window.fetch; let release; const gate=new Promise(r=>release=r);
  window.fetch=async (url,opts)=>{if(String(url).includes('/api/process/wave/info?')) await gate; return origFetch(url,opts);};
  click(act(a,'info')); await sleep(30); set(field(a,'off-map-ua'),'3'); release(); await sleep(1000);
  check('映射变更使旧文件信息响应失效',()=>rt().info===null);
  window.fetch=origFetch; click(act(a,'copy')); await idle();
  check('复制模块独立保存映射',()=>mods().length===3 && field(mods()[1],'off-map-ua').value==='3' && field(mods()[1],'off-map-enabled').checked);
  set(field(a,'off-map-ua'),'1'); check('修改原模块不影响副本',()=>field(mods()[1],'off-map-ua').value==='3');
  const saved=window.localStorage.getItem(KEY); check('localStorage 保存模块配置',()=>JSON.parse(saved).modules[0].offline.col_ua==='1');
  p.window.close(); p=await boot(saved); await p.openBoard();
  check('刷新恢复启用状态及列号',()=>p.field(p.mods()[0],'off-map-enabled').checked && p.field(p.mods()[0],'off-map-ua').value==='1' && p.field(p.mods()[1],'off-map-ua').value==='3');
  check('无运行配置修改请求或脚本错误',()=>!p.calls.some(c=>c.method!=='GET') && !p.errors.length);
  console.log(`PASS ${n}`);
 } finally {if(p) p.window.close(); fs.rmSync(dir,{recursive:true,force:true});}
}
main().catch(e=>{console.error(e.stack || e); process.exitCode=1;});
