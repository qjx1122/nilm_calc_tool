// v0.85 实录检查：分路侧「离线文件播放倍速随总线侧」勾选（默认勾选→倍速下拉禁用；取消→可单独设置并随保存写入 source.file_speed_follow）。
// 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r85_check.cjs http://127.0.0.1:8036
const {JSDOM}=require(process.env.JSDOM_DIR+'/node_modules/jsdom');
(async()=>{
 const [base]=process.argv.slice(2);
 const html=await (await fetch(base+'/static/index.html')).text();
 const dom=new JSDOM(html,{url:base+'/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window; w.fetch=(u,o)=>fetch(String(u).startsWith('/')?base+u:u,o); w.HTMLCanvasElement.prototype.getContext=()=>new Proxy({},{get:()=>()=>({})});
 let js=await (await fetch(base+'/static/app.js')).text(); js+='\nwindow.__$=$;window.init=init;window.__S=S;window.__BR=BR;window.__collect=collectSourceFields;window.__sync=syncSourceForm;';
 w.eval(js); try{w.init();}catch(e){console.log('init err',e.message)} await new Promise(r=>setTimeout(r,1500));
 const $=w.__$, ok=[], sleep=ms=>new Promise(r=>setTimeout(r,ms));
 const put=(u,b)=>fetch(base+u,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}).then(r=>r.json());
 await put('/api/config',{source:{kind:'csv_file',path:'data/sample.csv'}}); await put('/api/branch/config',{source:{kind:'csv_file',path:'data/sample.csv',file_speed:1,file_speed_follow:true}});
 $('#src-kind').value='csv_file'; $('#br-kind').value='csv_file'; $('#br-path').value='data/sample.csv'; $('#br-file-speed-follow').checked=true; w.__sync();
 ok.push(['默认勾选「随总线侧」', $('#br-file-speed-follow').checked===true]);
 ok.push(['随总线侧时分路侧倍速下拉禁用、提示显示', $('#br-file-speed').disabled===true && $('#br-file-speed-note').style.display==='']);
 ok.push(['总线侧倍速下拉可用', $('#src-file-speed').disabled===false]);
 $('#br-file-speed-follow').checked=false; $('#br-file-speed-follow').dispatchEvent(new w.Event('change'));
 ok.push(['取消勾选后分路侧倍速下拉可用、提示隐藏', $('#br-file-speed').disabled===false && $('#br-file-speed-note').style.display==='none']);
 $('#br-file-speed').value='5'; $('#br-file-speed').dispatchEvent(new w.Event('change'));
 const p=w.__collect('br-');
 ok.push(['分路侧 payload 含 file_speed_follow=false 与 file_speed=5', p.file_speed_follow===false && p.file_speed===5]);
 ok.push(['总线侧 payload 不含 file_speed_follow', !('file_speed_follow' in w.__collect('src-'))]);
 $('#btn-br-save').click(); await sleep(1200);
 const bc=await (await fetch(base+'/api/branch/config')).json();
 ok.push(['保存分路侧配置后 source.file_speed_follow=false / file_speed=5', bc.source.file_speed_follow===false && bc.source.file_speed===5]);
 $('#src-kind').value='simulator'; w.__sync();
 ok.push(['总线侧非离线文件时勾选框禁用、分路侧倍速可用', $('#br-file-speed-follow').disabled===true && $('#br-file-speed').disabled===false]);
 await put('/api/branch/config',{source:{file_speed_follow:true,file_speed:1}});
 ok.forEach(([n,v])=>console.log(v?'PASS':'FAIL',n)); console.log(ok.every(x=>x[1])?'ALL PASS':'FAIL'); process.exit(0);
})();
