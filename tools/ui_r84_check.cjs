// v0.84 实录检查：数据源页总线侧「列出 data 目录」与分路侧一致（只列 CSV、可点击填入路径）。用法：JSDOM_DIR=. node tools/ui_r84_check.cjs http://127.0.0.1:8036
const {JSDOM}=require(process.env.JSDOM_DIR+'/node_modules/jsdom');
(async()=>{
 const [base]=process.argv.slice(2);
 const html=await (await fetch(base+'/static/index.html')).text();
 const dom=new JSDOM(html,{url:base+'/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window; w.fetch=(u,o)=>fetch(String(u).startsWith('/')?base+u:u,o); w.HTMLCanvasElement.prototype.getContext=()=>new Proxy({},{get:()=>()=>({})});
 let js=await (await fetch(base+'/static/app.js')).text(); js+='\nwindow.__$=$;window.init=init;window.__S=S;window.__BR=BR;';
 w.eval(js); try{w.init();}catch(e){console.log('init err',e.message)} await new Promise(r=>setTimeout(r,1500));
 const $=w.__$, ok=[], sleep=ms=>new Promise(r=>setTimeout(r,ms));
 $('#btn-listfiles').click(); $('#btn-br-pick').click(); await sleep(1500);
 const a=[...$('#files-out').querySelectorAll('a[data-srcfile]')], b=[...$('#br-files-out').querySelectorAll('a[data-brfile]')];
 ok.push(['总线侧列出可点击 CSV 项', a.length>0]);
 ok.push(['两侧列出项数与文本一致', a.length===b.length && a.every((x,i)=>x.textContent===b[i].textContent)]);
 ok.push(['两侧每项都只含 .csv', [...a,...b].every(x=>/\.csv$/i.test(x.textContent))]);
 ok.push(['两侧每项显示大小 MB', $('#files-out').textContent.includes('MB') && $('#br-files-out').textContent.includes('MB')]);
 w.__S.formDirty=false; w.__S.srcDirty=false; a[0].click(); b[0].click();
 ok.push(['点击总线侧项填入 #src-path', $('#src-path').value===a[0].dataset.srcfile]);
 ok.push(['点击分路侧项填入 #br-path', $('#br-path').value===b[0].dataset.brfile]);
 ok.push(['总线侧标记表单已改（不被推送覆盖）', w.__S.formDirty===true && w.__S.srcDirty===true]);
 ok.push(['分路侧标记 dirty', w.__BR.dirty===true]);
 ok.forEach(([n,v])=>console.log(v?'PASS':'FAIL',n)); console.log(ok.every(x=>x[1])?'ALL PASS':'FAIL'); process.exit(0);
})();
