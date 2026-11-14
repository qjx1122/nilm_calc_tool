// jsdom regression: shared file listing, per-source selection and refresh races.
const fs=require('fs'), assert=require('assert');
const {JSDOM}=require('../node_modules/jsdom');
const dom=new JSDOM(fs.readFileSync('app/static/index.html','utf8'),{url:'http://localhost/',runScripts:'outside-only'});
const w=dom.window, doc=w.document, listings=[], posts=[];
w.fetch=(url,opt)=>new Promise((resolve,reject)=>{
  const call={url:String(url),resolve,reject};
  if (!opt || !opt.method || opt.method==='GET') listings.push(call);
  else {call.payload=JSON.parse(opt.body); posts.push(call);}
});
w.confirm=()=>true;
w.eval(fs.readFileSync('app/static/app.js','utf8')+'\n;window._filesTest={npmBind,npmPayload};');
doc.removeEventListener('DOMContentLoaded',w.init);
const click=e=>e.dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
const change=(e,v)=>{e.value=v;e.dispatchEvent(new w.Event('input',{bubbles:true}));e.dispatchEvent(new w.Event('change',{bubbles:true}));};
const field=(e,k)=>e.querySelector(`[data-field="${k}"]`), action=(e,k)=>e.querySelector(`[data-action="${k}"]`);
const answer=(request,value,ok=true)=>request.resolve({ok,status:ok?200:500,json:async()=>value});
const tick=()=>new Promise(r=>setTimeout(r,0));
const listing=files=>({ok:true,files});
const files=[{name:'data/a.csv',size_mb:1},{name:'data/b.CSV',size_mb:2},{name:'data/<tag>.csv',size_mb:3},{name:'data/folder/',dir:true},{name:'data/readme.txt',size_mb:1}];
const profile={ok:true,revision:'rev',startup:{n:1},shutdown:null,notes:[],events:[{event_id:'source-1:10:START',source_id:'source-1',direction:'START',onset:10,end:11,vec:{}}]};
(async()=>{
  w._filesTest.npmBind(); click(doc.querySelector('#btn-npm-add')); click(doc.querySelector('#btn-npm-add'));
  const [a,b]=doc.querySelectorAll('.npm-module'), sa=a.querySelector('.npm-source'), sb=b.querySelector('.npm-source');
  assert.equal(listings.length,1); assert.match(listings[0].url,/\/api\/files\?sub=data/);
  change(field(a,'device_id'),'A'); change(field(b,'device_id'),'B');
  change(field(sa,'path'),'/manual/a.csv'); change(field(sb,'path'),'b-manual.csv');
  answer(listings[0],listing(files)); await tick(); await tick();
  assert.equal(field(sa,'path').value,'/manual/a.csv'); assert.equal(field(sb,'path').value,'b-manual.csv');
  assert.deepEqual([...field(sa,'files').options].map(o=>o.value),['','data/a.csv','data/b.CSV','data/<tag>.csv']);
  assert(!sa.querySelector('select script') && field(sa,'files').options[3].textContent.includes('<tag>'));
  change(field(sa,'files'),'data/a.csv'); assert.equal(field(sa,'path').value,'data/a.csv');
  assert.equal(field(sb,'path').value,'b-manual.csv');
  change(field(sa,'path'),'/other/manual.csv'); assert.equal(field(sa,'files').value,'');
  change(field(sa,'files'),'data/a.csv'); assert.equal(field(sa,'path').value,'data/a.csv');
  click(action(a,'add-source')); const second=a.querySelectorAll('.npm-source')[1];
  assert.equal(listings.length,1); assert.equal(field(second,'files').options.length,4);
  change(field(second,'files'),'data/b.CSV'); assert.equal(field(second,'path').value,'data/b.CSV');
  click(action(a,'preview')); assert.equal(posts.length,1);
  assert.deepEqual(posts[0].payload.sources.map(s=>s.path),['data/a.csv','data/b.CSV']);
  answer(posts[0],profile); await tick(); await tick(); assert(!action(a,'save').disabled);
  click(action(sb,'refresh-files')); assert.equal(listings.length,2);
  // A refresh of B's list must not invalidate A's preview or change manual paths.
  answer(listings[1],listing([{name:'data/new.csv',size_mb:5},{name:'data/b.CSV',size_mb:2}])); await tick(); await tick();
  assert.equal(field(sa,'path').value,'data/a.csv'); assert.equal(field(sa,'files').value,'');
  assert.equal(field(second,'files').value,'data/b.CSV'); assert.equal(field(sb,'path').value,'b-manual.csv');
  assert(!action(a,'save').disabled);
  click(action(sa,'refresh-files')); assert.equal(listings.length,3);
  answer(listings[2],{error:'读取失败'},false); await tick(); await tick();
  assert.match(sa.querySelector('.npm-files-status').textContent,/读取文件列表失败/);
  assert.equal(field(sa,'path').value,'data/a.csv'); assert(!action(a,'save').disabled);
  click(action(sa,'refresh-files')); assert.equal(listings.length,4);
  answer(listings[3],listing(files)); await tick(); await tick();
  change(field(sa,'files'),'data/b.CSV'); assert(action(a,'save').disabled);
  assert.equal(field(second,'path').value,'data/b.CSV'); assert.equal(field(sb,'path').value,'b-manual.csv');
  // Empty lists are explicit and manual paths remain usable.
  click(action(sa,'refresh-files')); answer(listings[4],listing([])); await tick(); await tick();
  assert.match(sa.querySelector('.npm-files-status').textContent,/没有 CSV/); assert.equal(field(sa,'path').value,'data/b.CSV');
  change(field(sa,'path'),'/manual/still-works.csv'); assert.equal(field(sa,'path').value,'/manual/still-works.csv');
  // A pending list refresh cannot overwrite a later edit or the frozen preview request.
  click(action(sa,'refresh-files')); change(field(sa,'path'),'/edited-during-refresh.csv'); click(action(a,'preview'));
  assert.equal(posts[1].payload.sources[0].path,'/edited-during-refresh.csv');
  answer(listings[5],listing(files)); await tick(); await tick();
  assert.equal(field(sa,'path').value,'/edited-during-refresh.csv'); assert(field(sa,'files').disabled);
  answer(posts[1],profile); await tick(); await tick(); assert(!action(a,'save').disabled && !field(sa,'files').disabled);
  console.log('multi-source file selectors: passed'); w.close();
})().catch(e=>{console.error(e);w.close();process.exitCode=1});
