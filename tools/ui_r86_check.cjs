// v0.86 实录检查：数据处理页 重采样 / 负荷辨识调参 / 波形预览 三处「离线文件列映射」块（默认不启用、启用显示 7 列号、载荷 / 查询参数带列映射）。
// 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r86_check.cjs http://127.0.0.1:8036
const {JSDOM}=require(process.env.JSDOM_DIR+'/node_modules/jsdom');
(async()=>{
 const [base]=process.argv.slice(2);
 const html=await (await fetch(base+'/static/index.html')).text();
 const dom=new JSDOM(html,{url:base+'/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window; w.fetch=(u,o)=>fetch(String(u).startsWith('/')?base+u:u,o); w.HTMLCanvasElement.prototype.getContext=()=>new Proxy({},{get:()=>()=>({})});
 let js=await (await fetch(base+'/static/app.js')).text(); js+='\nwindow.__$=$;window.init=init;window.__rs=rsPayload;window.__nt=ntPayload;window.__wp=wpBase;';
 w.eval(js); try{w.init();}catch(e){console.log('init err',e.message)} await new Promise(r=>setTimeout(r,1500));
 const $=w.__$, ok=[];
 const F=['ts','ua','ia','ub','ib','uc','ic'];
 for (const pre of ['rs-cm','nt-cm','wp-cm']) {
   ok.push([pre+' 块存在且默认不启用、列号行隐藏', !!$('#'+pre+'-blk') && $('#'+pre+'-on').checked===false && $('#'+pre+'-row').style.display==='none']);
   ok.push([pre+' 默认列号 1..7', F.every((f,i)=>$('#'+pre+'-'+f).value===String(i+1))]);
   ok.push([pre+' 勾选文案含默认列序说明', /启用离线文件列映射/.test($('#'+pre+'-blk').textContent) && /各列依次为 时间, A相电压, A相电流, B相电压, B相电流, C相电压, C相电流/.test($('#'+pre+'-blk').textContent)]);
 }
 ok.push(['重采样载荷默认 col_map_enabled=false 且无 col_map', w.__rs().col_map_enabled===false && !('col_map' in w.__rs())]);
 ok.push(['调参载荷默认 col_map_enabled=false', w.__nt().col_map_enabled===false]);
 ok.push(['波形预览查询默认 col_map_enabled=0', w.__wp().col_map_enabled==='0' && !('col_map' in w.__wp())]);
 for (const pre of ['rs-cm','nt-cm','wp-cm']) { $('#'+pre+'-on').checked=true; $('#'+pre+'-on').dispatchEvent(new w.Event('change')); $('#'+pre+'-ua').value='3'; $('#'+pre+'-ia').value='2'; $('#'+pre+'-ia').dispatchEvent(new w.Event('change')); }
 ok.push(['勾选后三处列号行显示', ['rs-cm','nt-cm','wp-cm'].every(p=>$('#'+p+'-row').style.display==='')]);
 const rs=w.__rs(), nt=w.__nt(), wp=w.__wp();
 ok.push(['重采样载荷 col_map ua=3 ia=2 timestamp=1', rs.col_map_enabled===true && rs.col_map.ua==='3' && rs.col_map.ia==='2' && rs.col_map.timestamp==='1']);
 ok.push(['调参载荷 col_map ua=3 ia=2', nt.col_map_enabled===true && nt.col_map.ua==='3' && nt.col_map.ia==='2']);
 ok.push(['波形预览查询 col_map JSON', wp.col_map_enabled==='1' && JSON.parse(wp.col_map).ua==='3']);
 ok.push(['调参列映射随基准配置存本地', (()=>{try{const b=JSON.parse(w.localStorage.getItem('elec_tool.nilm_tune.base')||'null'); return b && b.col_map_enabled===true && b.col_map.ua==='3';}catch(e){return false;}})()]);
 ok.push(['波形预览列映射存本地', (()=>{try{const b=JSON.parse(w.localStorage.getItem('elec_tool.wave_preview.base')||'null'); return b && b.col_map_enabled==='1';}catch(e){return false;}})()]);
 ok.forEach(([n,v])=>console.log(v?'PASS':'FAIL',n)); console.log(ok.every(x=>x[1])?'ALL PASS':'FAIL'); process.exit(0);
})();
