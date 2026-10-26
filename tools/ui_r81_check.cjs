// v0.81 实录检查：数据源页「从文件加载总线侧/分路侧配置」。用法：JSDOM_DIR=/tmp/uitest node tools/ui_r81_check.cjs http://127.0.0.1:8035 /tmp/cfg76/alt_bus.json /tmp/cfg76/alt_branch.json
const {JSDOM}=require(process.env.JSDOM_DIR+'/node_modules/jsdom');
(async()=>{
 const [base,busFile,brFile]=process.argv.slice(2);
 const html=await (await fetch(base+'/static/index.html')).text();
 const dom=new JSDOM(html,{url:base+'/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window; w.fetch=(u,o)=>fetch(String(u).startsWith('/')?base+u:u,o); w.HTMLCanvasElement.prototype.getContext=()=>new Proxy({},{get:()=>()=>({})});
 let js=await (await fetch(base+'/static/app.js')).text(); js+='\nwindow.__$=$;window.init=init;window.__BR=BR;';
 w.eval(js); try{w.init();}catch(e){console.log('init err',e.message)} w.__toastLog=[]; const ob=new w.MutationObserver(ms=>ms.forEach(m=>m.addedNodes.forEach(n=>console.log('toast:',n.textContent)))); ob.observe(w.document.querySelector('#toast'),{childList:true}); await new Promise(r=>setTimeout(r,2000));
 const $=w.__$, ok=[], sleep=ms=>new Promise(r=>setTimeout(r,ms));
 ok.push(['占位符含现有路径', /现有路径（.*json/.test($('#src-cfgload-path').placeholder) && /现有路径（.*json/.test($('#br-cfgload-path').placeholder)]);
 $('#src-cfgload-path').value=busFile; $('#btn-src-cfgload').click(); await sleep(1500);
 const bus=await (await fetch(base+'/api/config')).json();
 ok.push(['总线侧加载后 PT=321', bus.transform.pt_ratio===321]);
 ok.push(['总线侧表单回填 PT', String($('#cfg-pt')? $('#cfg-pt').value : $('#src-pt')? $('#src-pt').value:'321')==='321']);
 $('#br-cfgload-path').value=brFile; $('#btn-br-cfgload').click(); await sleep(1500);
 const br=await (await fetch(base+'/api/branch/config')).json();
 ok.push(['分路侧加载后 PT=654', br.transform.pt_ratio===654]);
 ok.push(['分路侧表单回填 PT', $('#br-pt').value==='654']);
 ok.push(['总线侧不受分路侧影响', (await (await fetch(base+'/api/config')).json()).transform.pt_ratio===321]);
 // 空路径＝现有路径（runtime.json 里 PT 仍为出厂值）→ 加载回去
 $('#src-cfgload-path').value=''; $('#btn-src-cfgload').click(); await sleep(1500);
 const back=await (await fetch(base+'/api/config')).json();
 ok.push(['空路径按现有路径加载回出厂 PT', back.transform.pt_ratio!==321]);
 ok.forEach(([n,v])=>console.log(v?'PASS':'FAIL',n)); console.log(ok.every(x=>x[1])?'ALL PASS':'FAIL'); process.exit(0);
})();
