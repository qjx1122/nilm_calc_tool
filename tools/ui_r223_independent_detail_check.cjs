#!/usr/bin/env node
/* 电压/电流周波图独立性：隔离服务 + 真实 CSV，b5_run.sh ui_r223_independent_detail_check.cjs */
const fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert');
const {boot,sleep}=require('./ui_r213_check.cjs');
async function main(){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'wb223-')), file=path.join(dir,'wave.csv');
 const lines=['时间戳,A相电压,A相电流,B相电压,B相电流,C相电压,C相电流'];
 for(let k=0;k<19200;k++){let t=k/6400,w=2*Math.PI*50*t, row=[(1700000000+t).toFixed(6)];for(let p of [0,-2*Math.PI/3,2*Math.PI/3])row.push((81.65*Math.sin(w+p)).toFixed(5),(7.071*Math.sin(w+p)).toFixed(5));lines.push(row.join(','));}fs.writeFileSync(file,lines.join('\n')+'\n');
 let p,n=0;const ok=(name,fn)=>{assert.ok(fn(),name);n++;console.log(' ✓ '+name)};
 try{p=await boot(null);await p.openBoard();const {window,document,click,set,change,idle,mods,field,act}=p;
 click(document.querySelector('#btn-wb-add-offline')); const el=mods()[0],m=()=>window.WB.modules[0],rt=()=>window.WB.rt[m().id];
 set(field(el,'off-path'),file);click(act(el,'load'));await idle();let center=rt().data.t[5];
 const box=k=>el.querySelector('.wb-detail[data-wb-key="'+k+'"]'),cv=k=>document.getElementById('wb-detail-'+m().id+'-'+k),detail=k=>rt().details?.[k]?.data;
 const load=(k,c=center,kind='rms')=>window.wbLoadDetail(m(),k,c,kind);
 const pendingU=load('u',center,'wave'), pendingI=load('i',center+0.4,'rms'); await Promise.all([pendingU,pendingI]);
 ok('电压与电流同时显示不同周波类型与时刻',()=>detail('u')?.kind==='wave' && detail('i')?.kind==='rms' && detail('i').center>detail('u').center);
 ok('电压与电流分别属于各自主图的同排容器',()=>['u','i'].every(k=>box(k).parentElement.dataset.wbRow===k && box(k).parentElement.classList.contains('wb-paired')));
 ok('电压电流数据数值及通道正确',()=>Math.max(...detail('u').data.channels.Ua)>80 && Math.abs(detail('i').data.channels.Ia[0]-5)<0.2 && Object.keys(detail('u').data.channels).every(k=>k[0]==='U') && Object.keys(detail('i').data.channels).every(k=>k[0]==='I'));
 const ci=cv('i'),cu=cv('u'); click(box('u').querySelector('[data-z="x-"]'));
 const z=JSON.stringify(window.ZOOM[cu.id]);ok('电压周波缩放不影响电流周波',()=>!!window.ZOOM[cu.id]?.x&&!window.ZOOM[ci.id]);
 const toggle=box('u').querySelector('.ser-vis[data-name=Ua]');toggle.checked=false;change(toggle);
 ok('图例状态分别保存',()=>m().hidden.detail_u.includes('Ua')&&!m().hidden.detail_i);
 await load('i',center+0.5,'wave');
 ok('替换电流周波类型不影响电压周波数据与缩放',()=>detail('i').kind==='wave' && detail('u').kind==='wave' && JSON.stringify(window.ZOOM[cu.id])===z);
 set(field(el,'detail-cycles'),'20');ok('修改周波数不关闭已显示的两条曲线',()=>!!detail('u') && !!detail('i'));
 await load('i',center,'rms');ok('新周波数仅影响重新请求的一侧',()=>detail('i').data.n>=19&&detail('i').data.n<=20&&detail('u').data.n>6000);
 click(box('i').querySelector('[data-wb-act=detail-close]'));
 ok('关闭电流不关闭或复位电压',()=>box('i').hidden&&!detail('i')&&!box('u').hidden&&!!detail('u')&&JSON.stringify(window.ZOOM[cu.id])===z);
 await load('i'); const ci2=cv('i'); click(box('i').querySelector('[data-z="x-"]'));const zi=JSON.stringify(window.ZOOM[ci2.id]);
 set(field(el,'off-show'),'i');ok('隐藏电压只关闭电压周波，电流数据和缩放保持',()=>box('u').hidden&&!detail('u')&&!!detail('i')&&JSON.stringify(window.ZOOM[ci2.id])===zi);
 set(field(el,'off-show'),'both');ok('恢复双图保留电流周波不自动恢复已隐藏电压',()=>!box('i').hidden&&box('i').parentElement.dataset.wbRow==='i'&&box('u').hidden);
 const rawFetch=window.fetch;let release;const gate=new Promise(r=>release=r);
 window.fetch=async (url,opts)=>{if(String(url).includes('/api/process/wave/info?'))await gate;return rawFetch(url,opts)};
 const uJob=load('u');await sleep(30);const iJob=load('i',center,'wave');click(box('u').querySelector('[data-wb-act=detail-close]'));release();await Promise.all([uJob,iJob]);window.fetch=rawFetch;
 ok('关闭电压时旧请求作废，不取消电流请求',()=>box('u').hidden&&!detail('u')&&detail('i')?.kind==='wave'&&!box('i').hidden);
 const savedI=detail('i');await load('u',1700000100,'rms');
 ok('电压读取失败只影响电压状态',()=>/不在原始波形文件时间范围/.test(box('u').querySelector('.wb-detail-status').textContent)&&detail('i')===savedI&&!box('i').hidden);
 click(act(el,'load'));await idle();ok('主图重新加载后清除两条旧周波',()=>!detail('u')&&!detail('i')&&box('u').hidden&&box('i').hidden);
 ok('页面无脚本错误或修改类请求',()=>!p.errors.length&&!p.calls.some(c=>c.method!=='GET'));
 console.log('PASS '+n);
 }finally{if(p)p.window.close();fs.rmSync(dir,{recursive:true,force:true});}
}main().catch(e=>{console.error(e.stack||e);process.exitCode=1});
