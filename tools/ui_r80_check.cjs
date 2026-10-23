// v0.80 实录检查：调参结果「最小关心负荷估计」分簇显示 + 取值方式三选一 + 拼接告警。用法：JSDOM_DIR=/tmp/uitest node tools/ui_r80_check.cjs http://127.0.0.1:8035
const {JSDOM}=require(process.env.JSDOM_DIR+'/node_modules/jsdom');
(async()=>{
 const base=process.argv[2];
 const html=await (await fetch(base+'/static/index.html')).text();
 const dom=new JSDOM(html,{url:base+'/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window; w.fetch=fetch; w.HTMLCanvasElement.prototype.getContext=()=>new Proxy({},{get:()=>()=>({})});
 let js=await (await fetch(base+'/static/app.js')).text();
 js+='\nwindow.__ntRender=ntRender;window.__NT=NT;window.__$=$;window.init=init;';
 w.eval(js); try{w.init();}catch(e){} await new Promise(r=>setTimeout(r,1500));
 const est={unit:'A',candidate:0.59,candidate_from:'step',min_step:0.59,min_level_gap:0.6,levels:[6.9,7.5,8.1,25.9,26.5],n_steady:11,n_events:8,reliable:false,max_step:19.0,step_ratio:32,primary_step:19.0,secondary_step:0.59,split:true,n_primary:2,n_secondary:6,note:'x'};
 const d={file:'f.csv',channel:'A',unit:'A',quantity:'i',quantity_requested:'auto',voltage_present:false,scaled:false,t_span_s:10,t_range:{whole_file:true,t_first:0,t_last:10},measure:{cycles:500,level:7.5,sigma_cycle:0.02,sigma_cycle_pct:0.3,max_abs_diff:19,has_events_hint:true,range5_p95:0.1,range10_p95:0.1,sigma_mean10:0.01},suggest:{note:'n',quantity:'i',rel_tol_pct:1,min_delta_pct:0,algorithms:{threshold:{min_delta_a:0.3}}},min_load_estimate:est,min_load_source:'none',notes:['⚠ 文件疑似模板拼接'],repetition:{suspected:true}};
 w.__ntRender(d);
 const $=w.__$; const txt=$('#nt-est-text').textContent;
 const ok=[txt.includes('主负荷 ≈19'),txt.includes('最大跳变'),$('#nt-est-pick').value==='primary',$('#nt-est-pick').options[0].textContent.includes('19 A'),$('#nt-status').textContent.includes('模板拼接'),w.__NT.est.primary===19];
 // click fill → primary into nt-mina
 $('#btn-nt-est-fill').click(); ok.push($('#nt-mina').value==='19');
 $('#nt-est-pick').value='min'; $('#btn-nt-est-fill').click(); ok.push($('#nt-mina').value==='0.59');
 $('#nt-est-pick').value='manual'; $('#btn-nt-est-fill').click(); ok.push($('#nt-mina').value==='0.59');
 est.split=false; est.primary_step=null; est.reliable=true; w.__ntRender(d); ok.push($('#nt-est-pick').value==='min' && !$('#nt-est-text').textContent.includes('分两簇'));
 console.log(ok, ok.every(Boolean)?'ALL PASS':'FAIL'); process.exit(0);
})();
