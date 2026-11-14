const fs = require('fs'), assert = require('assert');
const {JSDOM} = require('../node_modules/jsdom');
const html = fs.readFileSync('app/static/index.html','utf8');
const js = fs.readFileSync('app/static/app.js','utf8');
const dom = new JSDOM(html, {url:'http://localhost/',runScripts:'outside-only'});
const w = dom.window, doc = w.document;
let pending = [], calls = [];
w.fetch = (url, opt) => {
  if (!opt || !opt.method || opt.method === 'GET') return Promise.resolve({ok:true,json:async()=>({ok:true,files:[]})});
  return new Promise(resolve => { calls.push(JSON.parse(opt.body)); pending.push(resolve); });
};
w.confirm = () => true;
w.eval(js + '\n;window._npmTest = {npmBind, npmPayload, nilmProfileCell};');
doc.removeEventListener('DOMContentLoaded',w.init);
const click = el => el.dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
const input = (el,v) => { el.value=v; el.dispatchEvent(new w.Event('input',{bubbles:true})); };
const field = (m,k) => m.querySelector(`[data-field="${k}"]`);
const action = (m,k) => m.querySelector(`[data-action="${k}"]`);
const data = {ok:true,revision:'rev',startup:{n:1},shutdown:null,notes:['来源提醒'],events:[{event_id:'source-1:100:START',source_id:'source-1',direction:'START',t_start_local:'time',onset:100,end:101,vec:{d_ia:5},source:'label'}]};
const resolveNext = (value=data) => pending.shift()({ok:true,json:async()=>value});
const tick = () => new Promise(r=>setTimeout(r,0));
(async () => {
  w._npmTest.npmBind(); click(doc.querySelector('#btn-npm-add')); click(doc.querySelector('#btn-npm-add'));
  const [a,b] = doc.querySelectorAll('.npm-module'); assert(a && b);
  assert.equal(a.tagName, 'DETAILS'); assert(a.open && b.open);
  assert(a.querySelector('.npm-params.form') === null && a.querySelector('.npm-params .form'));
  assert(a.querySelector('.npm-result-panel') && a.querySelector('.npm-source .colmap-row'));
  input(field(a,'device_id'),'A<script>'); input(field(b,'device_id'),'B');
  assert.equal(a.querySelector('.npm-device-name').textContent,'A<script>');
  assert(!a.querySelector('.npm-device-name script'));
  input(field(a,'device_id'),'A');
  click(a.querySelector('.npm-module-summary')); assert(!a.open && b.open);
  assert.equal(field(a,'device_id').value,'A');
  click(a.querySelector('.npm-module-summary')); assert(a.open && b.open);
  for (const id of ['np-source-group','np-base','np-cm-group','np-device-group','np-locate-group','np-window-group','np-stage-group','np-result-group']) {
    const group=doc.getElementById(id); assert(group && group.tagName==='DETAILS' && group.open, id);
    click(group.querySelector(':scope > summary')); assert(!group.open, id); click(group.querySelector(':scope > summary')); assert(group.open, id);
  }
  for (const cls of ['npm-device-group','npm-window-group','npm-source','npm-map-group','npm-result-group']) {
    const group=a.querySelector('.'+cls); assert(group && group.open, cls);
    click(group.querySelector(':scope > summary')); assert(!group.open, cls); click(group.querySelector(':scope > summary')); assert(group.open, cls);
  }
  assert(!a.querySelector('.npm-base').open); click(a.querySelector('.npm-base > summary')); assert(a.querySelector('.npm-base').open);
  click(a.querySelector('.npm-base > summary')); assert(!a.querySelector('.npm-base').open);
  input(field(a.querySelector('.npm-source'),'path'),'a.csv'); input(field(b.querySelector('.npm-source'),'path'),'b.csv');
  click(action(a,'add-source')); const sa=a.querySelectorAll('.npm-source'); assert.equal(sa.length,2); assert.match(a.querySelector('.npm-source-count').textContent,/2 个文件/); input(field(sa[1],'path'),'a2.csv');
  field(a,'single_phase_mode').value='current'; field(a,'single_phase_mode').dispatchEvent(new w.Event('change',{bubbles:true}));
  assert(field(a,'phases').disabled && !field(a,'branch_phase').disabled);
  input(field(a,'branch_phase'),'A'); input(field(a,'bus_phase'),'B');
  click(action(a,'preview'));
  click(a.querySelector('.npm-source > summary')); assert(!a.querySelector('.npm-source').open);
  click(a.querySelector('.npm-result-group > summary')); assert(!a.querySelector('.npm-result-group').open);
  click(a.querySelector('.npm-module-summary')); assert(!a.open); click(action(b,'preview')); assert.equal(calls.length,2);
  assert.deepEqual(calls.map(c=>c.device_id),['A','B']); assert.equal(calls[0].sources.length,2);
  resolveNext(); resolveNext(); await tick(); await tick();
  assert(!a.open && b.open); click(a.querySelector('.npm-module-summary')); assert(a.open);
  assert(!a.querySelector('.npm-source').open && !a.querySelector('.npm-result-group').open);
  click(a.querySelector('.npm-source > summary')); click(a.querySelector('.npm-result-group > summary'));
  assert(!action(a,'save').disabled && !action(b,'save').disabled); assert(a.querySelector('[data-event]'));
  for (const cls of ['npm-device-group','npm-window-group','npm-source','npm-result-group']) {
    const group=a.querySelector('.'+cls); click(group.querySelector(':scope > summary')); assert(!group.open,cls);
    assert(!action(a,'save').disabled && a.querySelector('[data-event]').checked); click(group.querySelector(':scope > summary'));
  }
  field(a,'allow_single_direction').checked=true; click(action(a,'save'));
  assert(calls[2].allow_single_direction && calls[2].selected.length===1);
  input(field(a,'device_id'),'new'); resolveNext(); await tick(); await tick();
  assert(action(a,'save').disabled && /重新预览/.test(a.querySelector('.npm-status').textContent));
  assert(!action(b,'save').disabled); assert.equal(w._npmTest.npmPayload(b).device_id,'B');
  click(action(sa[1],'remove-source')); assert.match(a.querySelector('.npm-source-count').textContent,/1 个文件/);
  click(action(a,'remove-module')); assert(!a.isConnected && b.isConnected && b.open);
  const cell=w._npmTest.nilmProfileCell({status:'ambiguous',candidate_devices:[{device_id:'A<script>',direction:'START'},{device_id:'B',direction:'STOP'}]});
  assert(/归因不确定/.test(cell) && /A&lt;script&gt;/.test(cell) && !/D²=/.test(cell));
  const box=doc.querySelector('#npm-bundle'), bf=k=>box.querySelector(`[data-bundle="${k}"]`), ba=k=>box.querySelector(`[data-bundle-action="${k}"]`);
  input(bf('paths'),'a.json\nb.json'); click(ba('preview')); assert.equal(calls[3].paths.length,2);
  resolveNext({ok:true,revision:'bundle-rev',members:[{device_id:'A',sha256:'aaa',summary:{phases:'A'}}]});
  await tick(); await tick(); assert(!ba('save').disabled && /验收/.test(bf('status').textContent));
  click(ba('save')); assert.equal(calls[4].revision,'bundle-rev');
  resolveNext({ok:true,saved_to:'pack.json'}); await tick(); await tick();
  assert(ba('save').disabled && /试运行/.test(bf('status').textContent)); assert(!ba('fill-bus').disabled && !ba('fill-branch').disabled);
  console.log('multi-source and bundle UI: passed'); w.close();
})().catch(e=>{ console.error(e); w.close(); process.exitCode=1; });
