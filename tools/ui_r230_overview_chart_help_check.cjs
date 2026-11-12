#!/usr/bin/env node
/* 总览页两侧四张曲线：隐藏操作文字但保留缩放、平移、图例和悬停。
 * 对隔离服务运行：JSDOM_DIR=<jsdom目录> node tools/ui_r230_overview_chart_help_check.cjs http://127.0.0.1:8766 */
const assert = require('assert');
const {boot, sleep} = require('./ui_r213_check.cjs');

async function main() {
  let p, n = 0;
  const check = (name, value) => { assert.ok(value, name); n++; console.log(' ✓ ' + name); };
  try {
    p = await boot(null);
    const {window: w, document: d, click, calls, errors} = p;
    click(d.querySelector('.navitem[data-view="overview"]')); await sleep(500);
    // 模拟配置保存响应，验证实际图例切换路径而不修改服务配置。
    const originalFetch = w.fetch, saves = [];
    w.fetch = (url, opts = {}) => {
      if (opts.method === 'PUT' && String(url).includes('/api/config')) {
        saves.push(JSON.parse(opts.body)); return Promise.resolve({ok:true, json:async()=>({ok:true})});
      }
      return originalFetch(url, opts);
    };
    const data = [0,1,2,3,4,5,6,7,8,9].map(x => [x, x * 2]);
    const series = [{name:'甲',color:'#fff',data}, {name:'乙',color:'#f00',data:data.map(([x,y])=>[x,y+2])}];
    const ids = ['ov-u','ov-i','ov-p','ov-thd','ov-u-br','ov-i-br','ov-p-br','ov-thd-br'];
    for (const id of ids) {
      const cv = d.getElementById(id);
      cv.getBoundingClientRect = () => ({left:0,top:0,width:600,height:240});
      w.drawLine(cv, [], {height:240,ownRange:true});
      check(id + ' 空数据无说明', cv.__zoombar && cv.__zoombar.querySelector('.zoomtip').textContent === '');
      w.drawLine(cv, series, {height:240,ownRange:true,force:true});
      const bar = cv.__zoombar, legend = cv.__legend;
      check(id + ' 三项标签和说明均移除', !['显示：','缩放：','移动：'].some(t => legend.textContent.includes(t)) && bar.querySelector('.zoomtip').textContent === '' && !bar.querySelector('.panlbl'));
      check(id + ' 显示图例与按钮悬停提示保留', !legend.textContent.includes('显示：') && legend.querySelectorAll('.ser-vis').length === 2 && bar.querySelectorAll('button.zoom-btn').length === 9 && [...bar.querySelectorAll('button')].every(b => b.title) && [...bar.querySelectorAll('.pan-btn')].every(b => b.getAttribute('aria-label')));
      cv.dispatchEvent(new w.WheelEvent('wheel',{deltaY:-100,clientX:300,clientY:100,bubbles:true,cancelable:true}));
      check(id + ' 滚轮缩放且无说明', !!w.ZOOM[id]?.x && bar.querySelector('.zoomtip').textContent === '' && !bar.querySelector('[data-z="pr"]').disabled);
      const before = w.ZOOM[id].x[0]; click(bar.querySelector('[data-z="pr"]'));
      check(id + ' 平移按钮有效', w.ZOOM[id].x[0] > before);
      cv.dispatchEvent(new w.MouseEvent('mousemove',{clientX:300,clientY:100,bubbles:true}));
      check(id + ' 数据悬停提示仍可用', cv.__hoverInfo && cv.__hoverInfo.items.length === 2);
      cv.dispatchEvent(new w.MouseEvent('dblclick',{bubbles:true,cancelable:true}));
      check(id + ' 双击复位后仍无说明', !w.ZOOM[id] && bar.querySelector('.zoomtip').textContent === '');
      const mouse = (type, x, y, ctrlKey = false) => cv.dispatchEvent(new w.MouseEvent(type, {clientX:x, clientY:y, button:0, bubbles:true, cancelable:true, ctrlKey}));
      const drag = (x1,y1,x2,y2,ctrlKey=false) => { mouse('mousedown',x1,y1,ctrlKey); mouse('mousemove',x2,y2,ctrlKey); mouse('mouseup',x2,y2,ctrlKey); };
      drag(180,100,380,180);
      check(id + ' 图面框选两轴', !!w.ZOOM[id]?.x && !!w.ZOOM[id]?.y);
      const panBefore = w.ZOOM[id].x[0]; drag(300,100,250,100);
      check(id + ' 已放大后拖动图面平移', w.ZOOM[id].x[0] > panBefore);
      const keyBefore = w.ZOOM[id].x[0]; cv.dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true}));
      check(id + ' 方向键平移', w.ZOOM[id].x[0] > keyBefore);
      mouse('dblclick',300,100);
      const chart = cv.__chart; drag(180,chart.h - 10,380,chart.h - 10);
      check(id + ' X 轴刻度带只缩放 X', !!w.ZOOM[id]?.x && !w.ZOOM[id]?.y);
      drag(220,90,350,150,true);
      check(id + ' Ctrl 框选再放大', !!w.ZOOM[id]?.y && bar.querySelector('.zoomtip').textContent === '');
      click(bar.querySelector('[data-z="reset"]'));
      check(id + ' 复位按钮有效', !w.ZOOM[id]);
      let box = cv.__legend.querySelector('.ser-vis'); click(box); await sleep(20);
      check(id + ' 图例隐藏有效并沿用配置保存', !cv.__legend.querySelector('.ser-vis').checked && cv.__chart.pts.length === 1 && saves.some(v => v.output.series_hidden[id]?.includes('甲')));
      box = cv.__legend.querySelector('.ser-vis'); click(box); await sleep(20);
      check(id + ' 图例恢复后无标签且两条线可见', cv.__legend.querySelector('.ser-vis').checked && cv.__chart.pts.length === 2 && !cv.__legend.textContent.includes('显示：'));
    }
    const other = d.createElement('canvas'); other.id = 'r229-other'; d.body.appendChild(other);
    w.drawLine(other, series, {height:240,ownRange:true});
    check('其他界面保留显示、缩放、移动文字与拖选说明', ['显示：','缩放：','移动：'].every(x=>other.__legend.textContent.includes(x)) && /拖选区间/.test(other.__zoombar.textContent));
    other.dispatchEvent(new w.WheelEvent('wheel',{deltaY:-100,clientX:300,clientY:100,bubbles:true,cancelable:true}));
    check('其他界面缩放后保留移动说明', /已缩放 X.*移动坐标轴/.test(other.__zoombar.textContent));
    check('无配置修改请求或脚本错误', !calls.some(c=>c.method !== 'GET') && errors.length === 0);
    other.__legend.remove(); other.remove();
    console.log(`PASS ${n}`);
  } finally { if (p) p.window.close(); }
}
main().catch(e => { console.error(e.stack || e); process.exitCode = 1; });
