// v0.89 实录检查：负荷辨识页「标注全部事件」勾选——默认不勾＝曲线只标注最近 1000 条，勾选＝全部；两侧独立。
// 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r89_check.cjs http://127.0.0.1:8037
const {JSDOM}=require(process.env.JSDOM_DIR+'/node_modules/jsdom');
(async()=>{
 const [base]=process.argv.slice(2);
 const html=await (await fetch(base+'/static/index.html')).text();
 const dom=new JSDOM(html,{url:base+'/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window; const calls=[]; w.fetch=(u,o)=>{calls.push(String(u)); return fetch(String(u).startsWith('/')?base+u:u,o);}; w.HTMLCanvasElement.prototype.getContext=()=>new Proxy({},{get:()=>()=>({})});
 let js=await (await fetch(base+'/static/app.js')).text(); js+='\nwindow.__$=$;window.init=init;window.__E=E;window.__NLs=NLs;window.__pool=nilmMarkPool;window.__all=nilmMarkAll;window.__render=renderNilm;window.__refresh=refreshNilm;';
 w.eval(js); try{w.init();}catch(e){console.log('init err',e.message)} await new Promise(r=>setTimeout(r,1500));
 const $=w.__$, E=w.__E, ok=[];
 try { w.location.hash='#nilm'; w.__render(); } catch(e) {}
 await new Promise(r=>setTimeout(r,800));
 ok.push(['总线侧有勾选且默认不勾', !!$('#nilm-mark-all') && $('#nilm-mark-all').checked===false]);
 ok.push(['分路侧克隆存在且默认不勾', !!E('branch','nilm-mark-all') && E('branch','nilm-mark-all').checked===false]);
 ok.push(['默认拉取 limit=1000', calls.some(u=>/\/api\/nilm\/events\?limit=1000/.test(u))]);
 const nl=w.__NLs('bus'); nl.events=Array.from({length:1200},(_,k)=>({id:1200-k,algorithm:'threshold',channel:'total',direction:'up',t_start:1e9+k,magnitude_w:100,unit:'W'}));
 ok.push(['默认标注池=最近 1000 条', w.__pool(nl,'bus').length===1000 && w.__pool(nl,'bus')[0].id===1200]);
 ok.push(['标注范围文案=最近 1000 条', (()=>{try{w.__render();}catch(e){} return /最近 1000 条/.test($('#nilm-pqs-pool').textContent);})()]);
 $('#nilm-mark-all').checked=true; calls.length=0; $('#nilm-mark-all').dispatchEvent(new w.Event('change')); await new Promise(r=>setTimeout(r,600));
 ok.push(['勾选后重新拉取 limit=0', calls.some(u=>/\/api\/nilm\/events\?limit=0(&|$)/.test(u))]);
 nl.events=Array.from({length:1200},(_,k)=>({id:1200-k,algorithm:'threshold',channel:'total',direction:'up',t_start:1e9+k,magnitude_w:100,unit:'W'}));
 ok.push(['勾选后标注池=全部 1200 条', w.__all('bus')===true && w.__pool(nl,'bus').length===1200]);
 ok.push(['标注范围文案=全部 1200 条', (()=>{try{w.__render();}catch(e){} return /全部 1200 条/.test($('#nilm-pqs-pool').textContent);})()]);
 ok.push(['分路侧不受总线侧勾选影响', w.__all('branch')===false && w.__pool({events:Array.from({length:1200},(_,k)=>({id:1200-k}))},'branch').length===1000]);
 $('#nilm-mark-all').checked=false; $('#nilm-mark-all').dispatchEvent(new w.Event('change')); await new Promise(r=>setTimeout(r,400));
 const fake=Array.from({length:1200},(_,k)=>({id:1200-k})); ok.push(['取消勾选 → 回到 1000', w.__all('bus')===false && w.__pool({events:fake},'bus').length===1000]);
 ok.forEach(([n,p])=>console.log((p?'PASS ':'FAIL ')+n)); console.log(ok.every(x=>x[1])?'ALL PASS':'HAS FAIL'); process.exit(ok.every(x=>x[1])?0:1);
})().catch(e=>{console.error(e);process.exit(2);});
