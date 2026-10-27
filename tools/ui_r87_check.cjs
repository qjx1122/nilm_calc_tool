// v0.87 实录检查：负荷辨识页「启用自适应算法参数」勾选（总线侧有、分路侧隐藏）、灰显、载荷、推导参数展示。
// 用法：JSDOM_DIR=/tmp/uitest node tools/ui_r87_check.cjs http://127.0.0.1:8037
const {JSDOM}=require(process.env.JSDOM_DIR+'/node_modules/jsdom');
(async()=>{
 const [base]=process.argv.slice(2);
 const html=await (await fetch(base+'/static/index.html')).text();
 const dom=new JSDOM(html,{url:base+'/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window; w.fetch=(u,o)=>fetch(String(u).startsWith('/')?base+u:u,o); w.HTMLCanvasElement.prototype.getContext=()=>new Proxy({},{get:()=>()=>({})});
 let js=await (await fetch(base+'/static/app.js')).text(); js+='\nwindow.__$=$;window.init=init;window.__collect=collectNilmPayload;window.__E=E;window.__NLs=NLs;window.__dim=nilmDimUnits;window.__render=renderNilm;';
 w.eval(js); try{w.init();}catch(e){console.log('init err',e.message)} await new Promise(r=>setTimeout(r,1500));
 const $=w.__$, E=w.__E, ok=[];
 try { w.location.hash='#nilm'; w.__render(); } catch(e) {}
 await new Promise(r=>setTimeout(r,800));
 ok.push(['总线侧有勾选且默认不勾', !!$('#nilm-auto_params') && $('#nilm-auto_params').checked===false]);
 ok.push(['分路侧克隆存在且可见（v0.88）', !!E('branch','nilm-auto_params') && E('branch','nilm-auto_params-lbl').style.display!=='none']);
 ok.push(['默认无灰显、推导面板隐藏', !$('#nilm-algos').querySelector('.nilm-auto-off') && $('#nilm-auto-out').style.display==='none']);
 ok.push(['总线侧载荷含 auto_params=false', w.__collect('bus').auto_params===false]);
 $('#nilm-auto_params').checked=true; $('#nilm-auto_params').dispatchEvent(new w.Event('change'));
 const offs=$('#nilm-algos').querySelectorAll('label.nilm-auto-off').length, chk=$('#nilm-algos').querySelectorAll('label.nilm-auto-off input[type=checkbox]').length;
 ok.push(['勾选后数值项灰显、算法启停勾选不灰显', offs>20 && chk===0]);
 ok.push(['相对门槛灰显', $('#nilm-rel_tol_pct').closest('label').classList.contains('nilm-auto-off')]);
 ok.push(['推导面板显示等待文案', $('#nilm-auto-out').style.display==='' && /等待周波窗数据/.test($('#nilm-auto-out').textContent)]);
 ok.push(['总线侧载荷 auto_params=true', w.__collect('bus').auto_params===true]);
 ok.push(['总线侧数值项 disabled（v0.88.1）', $('#nilm-algos').querySelectorAll('label.nilm-auto-off input:not([disabled]), label.nilm-auto-off select:not([disabled])').length===0 && $('#nilm-algos').querySelectorAll('label.nilm-auto-off input[disabled]').length>20 && $('#nilm-rel_tol_pct').disabled && $('#nilm-min_delta_pct').disabled]);
 ok.push(['总线侧算法启停勾选仍可用', [...$('#nilm-algos').querySelectorAll('input[type=checkbox]')].every(c=>!c.disabled)]);
 E('branch','nilm-auto_params').checked=true; E('branch','nilm-auto_params').dispatchEvent(new w.Event('change'));
 ok.push(['分路侧载荷 auto_params=true（v0.88）', w.__collect('branch').auto_params===true]);
 const bh=E('branch','nilm-algos');
 ok.push(['分路侧勾选后数值项灰显 + disabled、与总线侧数量一致', bh.querySelectorAll('label.nilm-auto-off').length===offs && bh.querySelectorAll('label.nilm-auto-off input:not([disabled]), label.nilm-auto-off select:not([disabled])').length===0 && E('branch','nilm-rel_tol_pct').disabled && E('branch','nilm-min_delta_pct').disabled]);
 ok.push(['分路侧算法启停勾选仍可用', [...bh.querySelectorAll('input[type=checkbox]')].every(c=>!c.disabled)]);
 ok.push(['分路侧推导面板显示等待文案', E('branch','nilm-auto-out').style.display==='' && /等待周波窗数据/.test(E('branch','nilm-auto-out').textContent)]);
 E('branch','nilm-auto_params').checked=false; E('branch','nilm-auto_params').dispatchEvent(new w.Event('change'));
 ok.push(['分路侧取消勾选 → false 且数值项恢复可编辑', w.__collect('branch').auto_params===false && bh.querySelectorAll('label.nilm-auto-off').length===0 && bh.querySelectorAll('input[disabled], select[disabled]').length===0]);
 // 模拟 summary.auto_last → 渲染推导参数表
 w.__NLs('bus').summary={auto_params:true,auto_params_effective:true,algorithm_names:{steady_state:'稳态分段(Hart)'},auto_last:{total:{quantity:'p',unit:'W',stats:{sigma:83.4,hold:1,settle:5,min_steady:10,transient:20,k:5.53,min_delta:333.8,n:1200},algorithms:{steady_state:{tol_w:603.4,min_steady_cycles:10,min_delta_w:333.8,max_transient_cycles:20}}}}};
 w.__dim('bus');
 const txt=$('#nilm-auto-out').textContent;
 ok.push(['推导参数表：公共统计量', /σ=83\.40 W/.test(txt) && /最长暂态=20/.test(txt) && /最小幅值=334 W/.test(txt)]);
 ok.push(['推导参数表：算法行', /稳态分段\(Hart\)/.test(txt) && /tol=603/.test(txt) && /max_transient_cycles=20/.test(txt)]);
 ok.forEach(([n,v])=>console.log(v?'PASS':'FAIL',n)); console.log(ok.every(x=>x[1])?'ALL PASS':'FAIL'); process.exit(0);
})();
