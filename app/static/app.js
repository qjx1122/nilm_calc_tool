/* app.js —— 电力系统电气量计算工具 前端（原生 JS + Canvas，无外部 CDN 依赖）
 *
 * 结构：导航条切换子界面（需求③）；每个电气量一个子界面（需求②）；
 *       WebSocket 实时推送，失败自动降级为轮询（保证代理环境下也能用）。
 */
'use strict';

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const PH = ['A', 'B', 'C'];
const COLORS = { A: '#4ea1ff', B: '#3ddc97', C: '#ffb648', P: '#ff7ac6', Q: '#9d7bff', S: '#5ee0d0' };

const S = {
  state: null, result: null, view: 'overview',
  ws: null, wsOk: false, poll: null, histCache: {}, histAt: {},
  // 表单脏标记：用户一旦动手编辑，就暂停自动回填。
  // 不做这层保护时，快量 0.2s 一次的 result 推送会触发 render()→renderSource()，
  // 把用户刚选的下拉框、刚输入一半的路径**改回服务端配置**（实测可复现）。
  formDirty: false, srcDirty: false, cfgDirty: false,
  // 趋势曲线元数据（/api/history 返回的 count_total/span_s/hours 等）与「保存曲线」勾选的本地镜像
  histMeta: {}, curveLocal: null, curvePending: false,
  // 实时落盘面板（/api/realtime 快照 + 表单脏标记）
  realtime: null, rtDirty: false,
};
const CURVE_KEYS = ['voltage', 'current', 'power', 'power_factor', 'fundamental', 'harmonic'];
const CURVE_NAME = { voltage: '三相电压', current: '三相电流', power: 'P/Q/S', power_factor: 'PF/DPF', fundamental: '频率', harmonic: 'THD' };
const HIST_MAX_POINTS = 1500;   // 浏览器侧每条曲线最多接收的点数（服务端按峰谷保形抽稀）

/* 数据源表单：每种源的填写说明与「哪些字段该启用」的单一事实来源 */
const SRC_HINT = {
  csv_file: '离线文件：填 CSV 路径（相对仓库根或绝对路径）。文件读完自动结束；建议先点「探查数据」核对编码/表头/推算采样率。支持无表头、时间戳只有当天时刻的采集器格式（如 0/00/00 00:12:40.0000）。「自定义播放时间」勾选后时间轴＝起始时间＋样本序号/采样率，起始时间留空＝文件第 1 条数据时间。',
  csv_tail: '实时·文件追加：路径可填单个文件，也可填目录（目录模式自动跟 mtime 最新的 CSV，采集器分片轮转时用）。「从文件末尾开始」＝只算启动之后新写入的数据，不补算历史。',
  tcp: '实时·TCP 流：本工具作客户端连接采集装置。text_csv＝每行一条 CSV（可带中文表头，自动识别）；binary＝定长帧，需填 struct 格式与字段顺序（默认 <7d＝7 个 double 小端，56 字节/帧）。连不上/帧格式不匹配都会在下方「运行状态与告警」里给出排查项。',
  simulator: '实时·内置模拟器：无需任何硬件，用于联调与算法自证（与 cli.py selftest 同一信号模型，可与解析解对账）。速率倍数 >1 加速产出。',
};

const PLAY_PLACEHOLDER = {
  begin: '（从文件开头播放，无需填写）',
  row: '例：120001（第几条数据行，1 起算，不含表头）',
  seconds: '例：30（跳过开头 30 s 的数据，按采样率换算成行数）',
  percent: '例：50（从文件 50% 处开始，按字节定位到行首）',
  time: '例：2026-10-12 08:00:00 或 08:00:00（只填时刻＝与文件时标的当天时刻比较）',
};

/* ------------------------------------------------------------------ 工具 */

function isNum(v) { return typeof v === 'number' && isFinite(v); }

/* HTML 转义：文件路径 / 异常文本 / 数据源 info 都会插入 innerHTML */
function esc(v) {
  if (v === null || v === undefined) return '';
  return String(v).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function num(v, d = 3) {
  if (v === null || v === undefined || !isNum(+v)) return '—';
  return (+v).toFixed(d);
}

function si(v, unit = '', d = 4) {
  if (v === null || v === undefined || !isNum(+v)) return '—';
  const a = Math.abs(+v);
  if (a >= 1e9) return (+v / 1e9).toFixed(d) + ' G' + unit;
  if (a >= 1e6) return (+v / 1e6).toFixed(d) + ' M' + unit;
  if (a >= 1e3) return (+v / 1e3).toFixed(d) + ' k' + unit;
  if (a > 0 && a < 1e-3) return (+v * 1e3).toFixed(d) + ' m' + unit;
  return (+v).toFixed(d) + (unit ? ' ' + unit : '');
}

function ts(v) {
  if (!isNum(+v)) return '—';
  const d = new Date(+v * 1000);
  const p = (n, w = 2) => String(n).padStart(w, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${p(d.getMilliseconds(), 3)}`;
}

function tsX(v, spanS) {
  // 趋势曲线横轴：跨度超过 1 小时时不再显示毫秒（24h 曲线上毫秒毫无意义，还挤占刻度）
  if (!isNum(+v)) return '—';
  if (!(spanS > 3600)) return ts(v);
  const d = new Date(+v * 1000);
  const p = (n, w = 2) => String(n).padStart(w, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
function spanOf(key) { const m = S.histMeta[key]; return m && isNum(m.span_s) ? m.span_s : 0; }
function fmtDur(sec) {
  if (!isNum(sec) || sec <= 0) return '0s';
  if (sec < 60) return sec.toFixed(1) + 's';
  if (sec < 3600) return (sec / 60).toFixed(1) + 'min';
  return (sec / 3600).toFixed(2) + 'h';
}

function toast(msg, cls = '') {
  const box = $('#toast'); if (!box) return;
  const el = document.createElement('div');
  el.className = 'toast ' + cls;
  el.textContent = msg;
  box.appendChild(el);
  setTimeout(() => el.remove(), cls === 'err' ? 9000 : 4200);
}

function card(k, v, unit, sub) {
  return `<div class="card"><div class="k">${k}</div><div class="v">${v}${unit ? `<span class="u">${unit}</span>` : ''}</div>${sub ? `<div class="s">${sub}</div>` : ''}</div>`;
}

function table(headers, rows) {
  if (!rows || !rows.length) return '<div class="notes">暂无数据</div>';
  return `<table><thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${
    rows.map(r => `<tr>${r.map(c => `<td>${c === null || c === undefined ? '—' : c}</td>`).join('')}</tr>`).join('')
  }</tbody></table>`;
}

function notes(arr, extra = []) {
  const items = [...(arr || []), ...extra];
  if (!items.length) return '<div class="notes ok">无告警</div>';
  return '<div class="notes">' + items.map(n => {
    const s = String(n);
    const cls = /⚠|失败|异常|错误|不可/.test(s) ? 'bad' : (/退化|风险|参考|插值|抽稀/.test(s) ? 'warn' : '');
    return `<div class="${cls}">${esc(s)}</div>`;
  }).join('') + '</div>';
}

/* 服务端按「各量独立步长」推送分量子集（需求⑥）：只含本次到期的电气量。
 * 前端必须按键合并，保留每个量各自最近一次结果，否则慢窗量会被抹掉（实测踩坑）。 */
function mergeResult(prev, nxt) {
  if (!prev || !prev.quantities) return nxt;
  if (!nxt || !nxt.quantities) return prev;
  const out = Object.assign({}, nxt);
  out.quantities = Object.assign({}, prev.quantities, nxt.quantities);
  out._merged = true;
  return out;
}

function sumVals(o, keys) {
  if (!o) return null;
  let s = 0, any = false;
  keys.forEach(k => { const v = o[k]; if (typeof v === 'number' && isFinite(v)) { s += v; any = true; } });
  return any ? s : null;
}

function q(key) {
  const r = S.result;
  if (!r || !r.quantities) return null;
  const o = r.quantities[key];
  return (o && o.ok) ? o : null;
}

function qwin(key) {
  const r = S.result;
  return (r && r.quantities && r.quantities[key]) ? r.quantities[key].window : null;
}

function winNotes(key) {
  const w = qwin(key);
  if (!w) return '<div class="notes">该量本窗未计算（缓冲数据不足或已停止）</div>';
  const mine = S.result.quantities[key];
  const err = mine.ok ? null : mine.error;
  const v = q(key);
  return notes(w.notes, [
    `本量数据时刻 ${ts(mine.t_ref)}；窗长请求 ${w.length_s_requested}s → 实际 ${num(w.length_s_actual, 4)}s；样本 ${num(w.n_samples, 0)} 点；` +
    (w.n_cycles ? `整数周期 ${w.n_cycles} 个；` : '') +
    `所用频率 ${num(w.f_used, 4)}Hz（来源 ${w.f_source}）；策略 ${w.policy}${w.window_fn !== 'rect' ? ' + ' + w.window_fn : ''}`,
    err ? `✗ ${err}` : null,
    ...(v && v.values && v.values.notes ? v.values.notes : []),
  ].filter(Boolean));
}

/* ------------------------------------------------------------------ Canvas 图表 */

function prep(cv, h) {
  const dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth || cv.parentElement.clientWidth || 600;
  // 逻辑高度（CSS 像素）只从 opt.height 或**首次**读到的 HTML height 属性取，并缓存在 data-h 里。
  // 不能每次回读 getAttribute('height')：下面 `cv.height = height*dpr` 会同步改写该属性，
  // 当 devicePixelRatio≠1（Windows 125% 缩放、或浏览器对某个主机名记忆了 110% 缩放）时，
  // 每次重绘高度都乘一次 dpr → 页面纵向越拉越长（实测 200→250→312→390…）。
  if (!cv.dataset.h) cv.dataset.h = String(h || cv.getAttribute('height') || 200);
  const height = +(h || cv.dataset.h) || 200;
  cv.width = Math.max(200, Math.floor(w * dpr));
  cv.height = Math.floor(height * dpr);
  cv.style.height = height + 'px';
  const ctx = cv.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, height);
  return { ctx, w, h: height };
}

function niceTicks(min, max, n = 5) {
  if (!isFinite(min) || !isFinite(max) || min === max) { min -= 1; max += 1; }
  const span = max - min;
  const step0 = span / n;
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const norm = step0 / mag;
  const step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10) * mag;
  const lo = Math.floor(min / step) * step, hi = Math.ceil(max / step) * step;
  const out = [];
  for (let v = lo; v <= hi + step * 0.5; v += step) out.push(+v.toFixed(10));
  return out;
}

/* ---- 曲线悬停取值：鼠标移到曲线上显示该位置各条曲线的数值 ----
 * drawLine 每次重绘后把坐标映射与数据挂到 canvas 上（cv.__chart），并只绑定一次 mousemove/mouseleave；
 * 悬停位置存在 cv.__hover，重绘（实时推送 0.2s 一次）时在末尾重新叠加十字线与提示框，所以悬停不会被刷新抹掉。
 */
function nearestIdx(data, x) {
  // data 按 x 递增（趋势按时间、波形按秒、频谱按 Hz）→ 二分找最近点；非递增时退化为线性
  let lo = 0, hi = data.length - 1;
  if (hi < 0) return -1;
  if (data[0][0] > data[hi][0]) {
    let best = 0, bd = Infinity;
    data.forEach((p, i) => { const d = Math.abs(p[0] - x); if (d < bd) { bd = d; best = i; } });
    return best;
  }
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (data[m][0] < x) lo = m; else hi = m; }
  return (Math.abs(data[lo][0] - x) <= Math.abs(data[hi][0] - x)) ? lo : hi;
}

function fmtVal(v) {
  if (!isNum(v)) return '—';
  const a = Math.abs(v);
  if (a >= 1e6) return (v / 1e6).toFixed(3) + 'M';
  if (a >= 1e4) return (v / 1e3).toFixed(2) + 'k';
  if (a >= 100) return v.toFixed(2);
  if (a >= 1) return v.toFixed(3);
  return v.toPrecision(4);
}

function hoverInfo(cv, mx) {
  // 纯函数：给定鼠标 x（CSS 像素）返回 {x, xText, items:[{name,color,y,px,py}]}；测试可直接调用
  const c = cv.__chart;
  if (!c || !c.pts.length) return null;
  if (mx < c.pad.l || mx > c.w - c.pad.r) return null;
  const xv = c.xmin + (mx - c.pad.l) / Math.max(1e-9, (c.w - c.pad.l - c.pad.r)) * (c.xmax - c.xmin);
  const items = [];
  let xAt = null;
  c.pts.forEach(s => {
    const i = nearestIdx(s.data, xv);
    if (i < 0) return;
    const [x, y] = s.data[i];
    if (xAt === null) xAt = x;
    items.push({ name: s.name, color: s.color || '#4ea1ff', x, y, px: c.X(x), py: isNum(y) ? c.Y(y) : null, idx: i });
  });
  if (!items.length) return null;
  const fx = c.opt.fmtTip || c.opt.fmtX;
  return { x: xAt, xText: fx ? fx(xAt) : (+xAt.toFixed(3)).toString(), items, mx };
}

function drawHover(cv) {
  const c = cv.__chart, hv = cv.__hover;
  if (!c || !hv) return;
  const info = hoverInfo(cv, hv.mx);
  if (!info) return;
  const { ctx, w, h, pad } = c;
  const px = c.X(info.x);
  ctx.save();
  ctx.setLineDash([3, 3]); ctx.strokeStyle = '#8fa3cc'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(px + .5, pad.t); ctx.lineTo(px + .5, h - pad.b); ctx.stroke();
  ctx.setLineDash([]);
  info.items.forEach(it => {
    if (it.py === null) return;
    ctx.fillStyle = it.color; ctx.beginPath(); ctx.arc(it.px, it.py, 3.2, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = '#0b1020'; ctx.stroke();
  });
  const lines = [info.xText].concat(info.items.map(it => `${it.name}: ${fmtVal(it.y)}${c.opt.unit ? ' ' + c.opt.unit : ''}`));
  ctx.font = '11px sans-serif';
  const bw = Math.max(...lines.map(l => ctx.measureText(l).width)) + 16, bh = lines.length * 15 + 10;
  let bx = px + 12, by = Math.max(pad.t, Math.min(hv.my - bh / 2, h - pad.b - bh));
  if (bx + bw > w - pad.r) bx = px - 12 - bw;
  ctx.fillStyle = 'rgba(12, 17, 32, 0.92)'; ctx.strokeStyle = '#3a4a70';
  ctx.beginPath(); ctx.rect(bx, by, bw, bh); ctx.fill(); ctx.stroke();
  ctx.textAlign = 'left'; ctx.textBaseline = 'top';
  lines.forEach((l, i) => {
    ctx.fillStyle = i === 0 ? '#c9d6f5' : (info.items[i - 1].color || '#c9d6f5');
    ctx.fillText(l, bx + 8, by + 5 + i * 15);
  });
  ctx.restore();
  cv.__hoverInfo = info;         // 供测试/其它面板读取
}

function bindHover(cv) {
  if (cv.__hoverBound) return;
  cv.__hoverBound = true;
  cv.addEventListener('mousemove', (e) => {
    const r = cv.getBoundingClientRect();
    cv.__hover = { mx: e.clientX - r.left, my: e.clientY - r.top };
    if (cv.__redraw) cv.__redraw();
  });
  cv.addEventListener('mouseleave', () => { cv.__hover = null; cv.__hoverInfo = null; if (cv.__redraw) cv.__redraw(); });
  cv.style.cursor = 'crosshair';
}

function drawLine(cv, series, opt = {}) {
  const { ctx, w, h } = prep(cv, opt.height);
  const pad = { l: 62, r: 12, t: 12, b: 26 };
  const pts = series.filter(s => s && s.data && s.data.length);
  cv.__chart = null;
  cv.__redraw = () => drawLine(cv, series, opt);
  bindHover(cv);
  ctx.strokeStyle = '#1e2740'; ctx.lineWidth = 1;
  ctx.strokeRect(pad.l + .5, pad.t + .5, w - pad.l - pad.r, h - pad.t - pad.b);
  if (!pts.length) {
    ctx.fillStyle = '#5f6f92'; ctx.font = '12px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(opt.empty || '暂无数据（等待计算结果…）', w / 2, h / 2);
    return;
  }
  let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
  pts.forEach(s => s.data.forEach(([x, y]) => {
    if (!isNum(y)) return;
    if (x < xmin) xmin = x; if (x > xmax) xmax = x;
    if (y < ymin) ymin = y; if (y > ymax) ymax = y;
  }));
  if (!isFinite(ymin)) return;
  if (opt.zero) { ymin = Math.min(ymin, 0); ymax = Math.max(ymax, 0); }
  const pad2 = (ymax - ymin) * 0.08 || Math.abs(ymax) * 0.05 || 1;
  ymin -= pad2; ymax += pad2;
  const yt = niceTicks(ymin, ymax, 5);
  ymin = Math.min(yt[0], ymin); ymax = Math.max(yt[yt.length - 1], ymax);
  const X = x => pad.l + (xmax === xmin ? 0.5 : (x - xmin) / (xmax - xmin)) * (w - pad.l - pad.r);
  const Y = y => h - pad.b - (y - ymin) / (ymax - ymin) * (h - pad.t - pad.b);
  ctx.font = '10.5px sans-serif'; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
  yt.forEach(t => {
    const y = Y(t);
    ctx.strokeStyle = '#1b2338'; ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
    ctx.fillStyle = '#7b8ab0';
    ctx.fillText(opt.fmtY ? opt.fmtY(t) : (Math.abs(t) >= 1000 ? (t / 1000).toFixed(1) + 'k' : (+t.toFixed(4)).toString()), pad.l - 6, y);
  });
  ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  const xt = niceTicks(xmin, xmax, 6);
  xt.forEach(t => {
    if (t < xmin || t > xmax) return;
    ctx.fillStyle = '#7b8ab0';
    ctx.fillText(opt.fmtX ? opt.fmtX(t) : (+t.toFixed(3)).toString(), X(t), h - pad.b + 6);
  });
  if (opt.zero && ymin < 0 && ymax > 0) {
    ctx.strokeStyle = '#33415f'; ctx.beginPath(); ctx.moveTo(pad.l, Y(0)); ctx.lineTo(w - pad.r, Y(0)); ctx.stroke();
  }
  pts.forEach(s => {
    ctx.strokeStyle = s.color || '#4ea1ff'; ctx.lineWidth = s.width || 1.4; ctx.beginPath();
    let started = false;
    s.data.forEach(([x, y]) => {
      if (!isNum(y)) { started = false; return; }
      const px = X(x), py = Y(y);
      if (!started) { ctx.moveTo(px, py); started = true; } else ctx.lineTo(px, py);
    });
    ctx.stroke();
  });
  if (opt.legend !== false) {
    let lx = pad.l + 8;
    ctx.font = '11px sans-serif'; ctx.textAlign = 'left'; ctx.textBaseline = 'top';
    pts.forEach(s => {
      ctx.fillStyle = s.color || '#4ea1ff';
      ctx.fillRect(lx, pad.t + 4, 12, 3);
      ctx.fillStyle = '#c9d6f5';
      ctx.fillText(s.name, lx + 16, pad.t);
      lx += 26 + ctx.measureText(s.name).width;
    });
  }
  if (opt.ylabel) {
    ctx.save(); ctx.translate(12, h / 2); ctx.rotate(-Math.PI / 2);
    ctx.fillStyle = '#7b8ab0'; ctx.textAlign = 'center'; ctx.fillText(opt.ylabel, 0, 0); ctx.restore();
  }
  cv.__chart = { ctx, w, h, pad, pts, xmin, xmax, ymin, ymax, X, Y, opt };
  drawHover(cv);
}

function drawBars(cv, labels, datasets, opt = {}) {
  const { ctx, w, h } = prep(cv, opt.height);
  const pad = { l: 56, r: 12, t: 14, b: 30 };
  ctx.strokeStyle = '#1e2740'; ctx.strokeRect(pad.l + .5, pad.t + .5, w - pad.l - pad.r, h - pad.t - pad.b);
  const vals = datasets.flatMap(d => d.data).filter(v => isNum(v));
  if (!labels.length || !vals.length) {
    ctx.fillStyle = '#5f6f92'; ctx.font = '12px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('暂无数据', w / 2, h / 2); return;
  }
  const ymax = Math.max(...vals) * 1.12 || 1;
  const yt = niceTicks(0, ymax, 5);
  const top = Math.max(yt[yt.length - 1], ymax);
  const X = i => pad.l + (i + 0.5) / labels.length * (w - pad.l - pad.r);
  const Y = v => h - pad.b - (v / top) * (h - pad.t - pad.b);
  ctx.font = '10.5px sans-serif'; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
  yt.forEach(t => {
    const y = Y(t);
    ctx.strokeStyle = '#1b2338'; ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
    ctx.fillStyle = '#7b8ab0'; ctx.fillText((+t.toFixed(3)).toString(), pad.l - 6, y);
  });
  const bw = Math.max(1.5, (w - pad.l - pad.r) / labels.length / (datasets.length + 0.6));
  labels.forEach((lb, i) => {
    datasets.forEach((d, di) => {
      const v = d.data[i];
      if (!isNum(v)) return;
      const x = X(i) - bw * datasets.length / 2 + di * bw;
      ctx.fillStyle = d.color;
      ctx.fillRect(x, Y(v), bw - 0.6, h - pad.b - Y(v));
    });
    if (labels.length <= 30 || i % Math.ceil(labels.length / 25) === 0) {
      ctx.fillStyle = '#7b8ab0'; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      ctx.fillText(String(lb), X(i), h - pad.b + 6);
    }
  });
  let lx = pad.l + 8;
  ctx.font = '11px sans-serif'; ctx.textAlign = 'left'; ctx.textBaseline = 'top';
  datasets.forEach(d => {
    ctx.fillStyle = d.color; ctx.fillRect(lx, pad.t - 10, 12, 3);
    ctx.fillStyle = '#c9d6f5'; ctx.fillText(d.name, lx + 16, pad.t - 14);
    lx += 30 + ctx.measureText(d.name).width;
  });
  if (opt.xlabel) { ctx.fillStyle = '#7b8ab0'; ctx.textAlign = 'right'; ctx.fillText(opt.xlabel, w - pad.r, h - 14); }
  if (opt.ylabel) { ctx.save(); ctx.translate(12, h / 2); ctx.rotate(-Math.PI / 2); ctx.fillStyle = '#7b8ab0'; ctx.textAlign = 'center'; ctx.fillText(opt.ylabel, 0, 0); ctx.restore(); }
}

function drawQuadrant(cv, P, Q) {
  const { ctx, w, h } = prep(cv, 220);
  const cx = w / 2, cy = h / 2, R = Math.min(w, h) / 2 - 26;
  ctx.strokeStyle = '#26304a'; ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(cx - R, cy); ctx.lineTo(cx + R, cy); ctx.moveTo(cx, cy - R); ctx.lineTo(cx, cy + R); ctx.stroke();
  ctx.fillStyle = '#5f6f92'; ctx.font = '11px sans-serif'; ctx.textAlign = 'center';
  ctx.fillText('Ⅰ 感性吸收', cx + R * 0.55, cy - R * 0.55);
  ctx.fillText('Ⅱ 反送+感性', cx - R * 0.55, cy - R * 0.55);
  ctx.fillText('Ⅲ 反送+容性', cx - R * 0.55, cy + R * 0.62);
  ctx.fillText('Ⅳ 容性补偿', cx + R * 0.55, cy + R * 0.62);
  ctx.fillText('P →', cx + R + 14, cy + 4); ctx.fillText('Q ↑', cx + 4, cy - R - 10);
  if (!isNum(P) || !isNum(Q) || (P === 0 && Q === 0)) {
    ctx.fillStyle = '#5f6f92'; ctx.fillText('暂无 P/Q', cx, cy + R + 18); return;
  }
  const m = Math.max(Math.abs(P), Math.abs(Q)) || 1;
  const x = cx + (P / m) * R * 0.86, y = cy - (Q / m) * R * 0.86;
  ctx.strokeStyle = '#ff7ac6'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(x, y); ctx.stroke();
  ctx.fillStyle = '#ff7ac6'; ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#c9d6f5'; ctx.font = '11px sans-serif';
  ctx.fillText(`P=${si(P, 'W')}  Q=${si(Q, 'var')}`, cx, cy + R + 18);
}

/* ------------------------------------------------------------------ 通信 */

function connectWS() {
  try {
    const proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
    S.ws = new WebSocket(proto + location.host + '/ws');
  } catch (e) { startPolling(); return; }
  S.ws.onopen = () => { S.wsOk = true; if (S.poll) { clearInterval(S.poll); S.poll = null; } setNavFoot('实时推送已连接'); };
  S.ws.onmessage = (ev) => {
    let m; try { m = JSON.parse(ev.data); } catch (e) { return; }
    if (m.type === 'hello' || m.type === 'state') { S.state = m.data; renderTop(); if (S.view === 'source' || S.view === 'export') render(); }
    else if (m.type === 'result' || m.type === 'snapshot') { S.result = mergeResult(S.result, m.data); renderTop(); render(); }
    else if (m.type === 'error') { toast('服务端错误：' + m.message, 'err'); }
  };
  S.ws.onerror = () => { S.wsOk = false; };
  S.ws.onclose = () => {
    S.wsOk = false; setNavFoot('推送断开 → 已降级为轮询');
    startPolling();
    setTimeout(() => { if (!S.wsOk) connectWS(); }, 5000);
  };
}

function startPolling() {
  if (S.poll) return;
  S.poll = setInterval(async () => {
    try {
      S.state = await (await fetch('/api/state')).json();
      const r = await fetch('/api/result?full=false');
      if (r.ok) S.result = await r.json();
      renderTop(); render();
    } catch (e) { /* 服务未就绪，忽略本轮 */ }
  }, 1500);
}

async function api(path, opt) {
  const res = await fetch(path, opt);
  let data = null;
  try { data = await res.json(); } catch (e) { data = { ok: false, error: 'HTTP ' + res.status }; }
  if (!res.ok) throw new Error((data && data.error) || ('HTTP ' + res.status));
  return data;
}

function setNavFoot(t) { const el = $('#nav-foot'); if (el) el.textContent = t; }

/* ------------------------------------------------------------------ 顶栏与导航 */

function renderTop() {
  const st = S.state || {}, r = S.result;
  const eng = st.engine || {}, cfg = st.config || {};
  const pill = $('#st-running');
  if (st.error) { pill.textContent = '错误'; pill.className = 'pill err'; }
  else if (eng.running) { pill.textContent = '运行中'; pill.className = 'pill on'; }
  else if (eng.finished) { pill.textContent = '已完成'; pill.className = 'pill off'; }
  else { pill.textContent = '未启动'; pill.className = 'pill'; }
  $('#st-source').textContent = (cfg.source && cfg.source.kind) || '—';
  $('#st-time').textContent = r ? ts(r.t_ref) : '—';
  $('#st-freq').textContent = r ? num(r.f_used, 3) + ' Hz' : '—';
  $('#st-fs').textContent = cfg.sampling ? cfg.sampling.fs + ' Hz' : '—';
  $('#st-ptct').textContent = cfg.transform ? `${cfg.transform.pt_ratio} / ${cfg.transform.ct_ratio}` : '—';
  $('#st-samples').textContent = eng.samples_in !== undefined ? `${eng.samples_in} (${num(eng.data_duration_s, 1)}s)` : '—';
  $('#subtitle').textContent = `elec_tool v${st.version || '?'} · ${S.wsOk ? 'WebSocket 实时' : '轮询'} · 缓冲 ${eng.buffer_fill || 0}/${eng.buffer_capacity || 0}`;
  $('#btn-start').disabled = !!eng.running;
  $('#btn-stop').disabled = !eng.running;
}

function switchView(v) {
  S.view = v;
  $$('.navitem').forEach(b => b.classList.toggle('active', b.dataset.view === v));
  $$('.view').forEach(s => s.classList.toggle('active', s.id === 'view-' + v));
  render();
  if (['overview', 'power_factor', 'fundamental'].includes(v)) refreshHistory();
}

/* ------------------------------------------------------------------ 历史曲线 */

async function refreshHistory() {
  const keys = ['voltage', 'current', 'power', 'power_factor', 'fundamental', 'harmonic'];
  await Promise.all(keys.map(async k => {
    try {
      // 不再传 n=400：服务端默认返回「最近 output.history_hours（24h）内全部点」，超过 max_points 按峰谷抽稀
      const d = await api(`/api/history/${k}?max_points=${HIST_MAX_POINTS}`);
      S.histCache[k] = d.points || []; S.histAt[k] = Date.now();
      S.histMeta[k] = { count: d.count, count_total: d.count_total, span_s: d.span_s, hours: d.hours,
                        t_first: d.t_first, t_last: d.t_last, decimated: !!d.decimated };
    } catch (e) { S.histCache[k] = S.histCache[k] || []; }
  }));
  render();
}

function curveSpanText(key) {
  const m = S.histMeta[key];
  if (!m || !m.count_total) return '';
  return `最近 ${fmtDur(m.span_s)} · ${m.count_total} 点` + (m.decimated ? `（显示抽稀至 ${m.count}）` : '') +
    `（保留窗 ${m.hours}h）`;
}

/* 「保存曲线」勾选：各曲线面板右上角 + 导出页列表 共用 config.output.curve_save */
function curveSaveMap() {
  if (S.curvePending && S.curveLocal) return S.curveLocal;
  const cfg = ((S.state || {}).config || {}).output || {};
  const m = {};
  CURVE_KEYS.forEach(k => { m[k] = cfg.curve_save ? cfg.curve_save[k] !== false : true; });
  return m;
}

function renderCurveSave() {
  const m = curveSaveMap();
  $$('.curve-save').forEach(el => { if (el.dataset.curve in m) el.checked = !!m[el.dataset.curve]; });
  $$('.curvespan').forEach(el => { el.textContent = curveSpanText(el.dataset.curve); });
  const list = $('#curve-save-list');
  if (list && !list.children.length) {
    list.innerHTML = CURVE_KEYS.map(k =>
      `<label><input type="checkbox" class="curve-save" data-curve="${k}"> ${CURVE_NAME[k]}（${k}）</label>`).join('');
    $$('#curve-save-list .curve-save').forEach(el => { el.checked = !!m[el.dataset.curve]; });
  }
  const on = CURVE_KEYS.filter(k => m[k]);
  const lnk = $('#lnk-curves-dl');
  if (lnk) lnk.textContent = `下载已勾选曲线（${on.length}/${CURVE_KEYS.length}，合并 CSV）`;
}

async function setCurveSave(key, on) {
  const m = { ...curveSaveMap(), [key]: !!on };
  S.curveLocal = m; S.curvePending = true;
  renderCurveSave();
  try {
    await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
                               body: JSON.stringify({ output: { curve_save: { [key]: !!on } } }) });
    if (S.state && S.state.config) {
      S.state.config.output = S.state.config.output || {};
      S.state.config.output.curve_save = { ...(S.state.config.output.curve_save || {}), ...m };
    }
    toast(`曲线「${CURVE_NAME[key]}」${on ? '已加入' : '已排除出'}保存项（已写入配置）`, 'ok');
  } catch (e) {
    toast('保存曲线勾选失败：' + e.message, 'err');
  } finally { S.curvePending = false; S.curveLocal = null; renderCurveSave(); }
}

async function saveCurves() {
  const out = $('#curves-out');
  try {
    const d = await api('/api/curves/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    // notes() 会转义 HTML（告警文本来自服务端，必须转义），这里是纯文本列表即可
    const lines = d.files.map(f => `✓ ${CURVE_NAME[f.quantity] || f.quantity}：${f.path}（${f.rows} 点，${ts(f.t_first)} → ${ts(f.t_last)}）`);
    (d.skipped || []).forEach(k => lines.push(`－ ${CURVE_NAME[k] || k}：未勾选，已跳过`));
    (d.empty || []).forEach(k => lines.push(`－ ${CURVE_NAME[k] || k}：已勾选但暂无数据`));
    out.innerHTML = notes([`已保存到目录 ${d.dir}（最近 ${d.hours}h）`].concat(lines));
    toast(`曲线数据已保存：${d.files.length} 个文件`, 'ok');
  } catch (e) { out.innerHTML = notes(['✗ ' + e.message]); toast('保存曲线数据失败：' + e.message, 'err'); }
}

function hseries(key, field) {
  const pts = S.histCache[key] || [];
  const t0 = pts.length ? pts[0].t : 0;
  return pts.filter(p => isNum(p.t)).map(p => [p.t - t0, p[field]]);
}

/* ------------------------------------------------------------------ 各子界面渲染 */

function renderOverview() {
  const v = q('voltage'), i = q('current'), p = q('power'), pf = q('power_factor'),
        f = q('fundamental'), h = q('harmonic');
  const cards = [];
  if (v) PH.forEach(k => cards.push(card(`${k} 相电压`, si(v.values.rms[k], 'V'), '', `峰值 ${si(v.values.peak[k], 'V')}`)));
  if (i) PH.forEach(k => cards.push(card(`${k} 相电流`, si(i.values.rms[k], 'A'), '', `零线 ${si(i.values.neutral_rms, 'A')}`)));
  if (p) {
    cards.push(card('有功 P', si(p.values.p_total, 'W'), '', `分相和 ${si(sumVals(p.values.p_per_phase, PH), 'W')}`));
    cards.push(card('无功 Q', si(p.values.q_total, 'var'), '', p.values.quadrant ? p.values.quadrant.q_sign : ''));
    cards.push(card('视在 S', si(p.values.s_total, 'VA'), '', p.values.modes ? p.values.modes.apparent_note : ''));
  }
  if (pf) cards.push(card('功率因数 PF', num(pf.values.pf_total, 4), '', `DPF ${num(pf.values.dpf, 4)}`));
  if (f) cards.push(card('频率', num(f.values.freq_hz, 3), 'Hz', `${f.values.phase_sequence || ''} · 来源 ${f.values.freq_source}`));
  if (h) {
    cards.push(card('THD_U（最劣相）', num(h.values.thd_u_worst_pct, 2), '%', `最劣相 ${h.values.worst_phase_u || '—'}`));
    cards.push(card('THD_I（最劣相）', num(h.values.thd_i_worst_pct, 2), '%', `最劣相 ${h.values.worst_phase_i || '—'}`));
  }
  if (!cards.length) cards.push(card('状态', '尚无结果', '', '请到「数据源与控制」启动数据源'));
  $('#ov-cards').innerHTML = cards.join('');

  const hv = S.histCache.voltage || [], hi = S.histCache.current || [], hp = S.histCache.power || [], hh = S.histCache.harmonic || [];
  const tref = (arr) => arr.length ? arr[0].t : 0;
  drawLine($('#ov-u'), hv.map ? [{ name: 'Ua', color: COLORS.A, data: hv.map((p, k) => [p.t - tref(hv), p.Ua]) },
                                 { name: 'Ub', color: COLORS.B, data: hv.map((p, k) => [p.t - tref(hv), p.Ub]) },
                                 { name: 'Uc', color: COLORS.C, data: hv.map((p, k) => [p.t - tref(hv), p.Uc]) }] : [],
           { ylabel: 'V', fmtX: x => tsX(x + tref(hv), spanOf('voltage')), fmtTip: x => ts(x + tref(hv)), empty: '暂无电压趋势（需累计 ≥2 个窗）' });
  drawLine($('#ov-i'), [{ name: 'Ia', color: COLORS.A, data: hi.map(p => [p.t - tref(hi), p.Ia]) },
                        { name: 'Ib', color: COLORS.B, data: hi.map(p => [p.t - tref(hi), p.Ib]) },
                        { name: 'Ic', color: COLORS.C, data: hi.map(p => [p.t - tref(hi), p.Ic]) }],
           { ylabel: 'A', fmtX: x => tsX(x + tref(hi), spanOf('current')), fmtTip: x => ts(x + tref(hi)) });
  drawLine($('#ov-p'), [{ name: 'P', color: COLORS.P, data: hp.map(p => [p.t - tref(hp), p.P]) },
                        { name: 'Q', color: COLORS.Q, data: hp.map(p => [p.t - tref(hp), p.Q]) },
                        { name: 'S', color: COLORS.S, data: hp.map(p => [p.t - tref(hp), p.S]) }],
           { ylabel: 'W/var/VA', fmtX: x => tsX(x + tref(hp), spanOf('power')), fmtTip: x => ts(x + tref(hp)) });
  drawLine($('#ov-thd'), [{ name: 'THD_U', color: COLORS.A, data: hh.map(p => [p.t - tref(hh), p.THD_U]) },
                          { name: 'THD_I', color: COLORS.C, data: hh.map(p => [p.t - tref(hh), p.THD_I]) }],
           { ylabel: '%', fmtX: x => tsX(x + tref(hh), spanOf('harmonic')), fmtTip: x => ts(x + tref(hh)), zero: true });
  renderCurveSave();
  const hn = $('#ov-histnote');
  if (hn) {
    const hrs = ((((S.state || {}).config || {}).output || {}).history_hours) || 24;
    hn.innerHTML = notes([`趋势曲线显示<b>最近 ${hrs} 小时</b>的数据（按数据时间计；不足 ${hrs} 小时则显示全部）。` +
      `每条曲线最多传输 ${HIST_MAX_POINTS} 点（超出按峰谷保形抽稀，面板标题处标注）。` +
      `曲线面板右上角「保存曲线」＝保存曲线数据时是否包含该曲线。`]);
  }

  const allNotes = [];
  Object.keys((S.result || {}).quantities || {}).forEach(k => {
    const o = S.result.quantities[k];
    if (!o.ok) allNotes.push(`[${k}] ${o.error}`);
    (o.window.notes || []).forEach(n => allNotes.push(`[${k}] ${n}`));
    if (o.values && o.values.notes) o.values.notes.forEach(n => allNotes.push(`[${k}] ${n}`));
  });
  ((S.state || {}).engine || {}).notes && (S.state.engine.notes || []).forEach(n => allNotes.push(`[引擎] ${n}`));
  $('#ov-notes').innerHTML = notes(allNotes);
}

function waveData(qq, key) {
  if (!qq || !qq.series || !qq.series.waveform) return [];
  const w = qq.series.waveform;
  return PH.map(k => ({ name: k + ' 相', color: COLORS[k], data: (w.t || []).map((t, idx) => [t, (w[k] || [])[idx]]) }));
}

function perCycleTable(pc, unit) {
  if (!pc) return '<div class="notes">无逐周期数据</div>';
  return table(['相', '周期数', '均值', '最大', '最小', '标准差', '丢弃点'],
    PH.map(k => {
      const s = pc[k] || {};
      return [k + ' 相', num(s.n_cycles, 0), si(s.mean, unit), si(s.max, unit), si(s.min, unit), num(s.std, 4), num(s.n_dropped, 0)];
    }));
}

function seqTable(s, unit) {
  if (!s) return '<div class="notes">无序分量数据</div>';
  return table(['项目', '数值', '说明'], [
    ['正序 ' + (unit === 'V' ? 'U1' : 'I1'), si(s.U1, unit), '对称分量法（基波相量）'],
    ['负序 ' + (unit === 'V' ? 'U2' : 'I2'), si(s.U2, unit), `不平衡度 ${num(s.negative_seq_pct, 3)} %`],
    ['零序 ' + (unit === 'V' ? 'U0' : 'I0'), si(s.U0, unit), `零序含量 ${num(s.zero_seq_pct, 3)} %`],
    ['正序相角', num(s.U1_angle_deg, 2) + '°', ''],
    ['负序相角', num(s.U2_angle_deg, 2) + '°', ''],
  ]);
}

function renderVoltage() {
  const v = q('voltage');
  const cards = [];
  if (v) {
    PH.forEach(k => cards.push(card(`${k} 相电压有效值`, si(v.values.rms[k], 'V'), '', `峰值 ${si(v.values.peak[k], 'V')} · 直流 ${num(v.values.dc_mean[k], 3)} V`)));
    ['Uab', 'Ubc', 'Uca'].forEach(k => cards.push(card(`线电压 ${k}`, si(v.values.line_rms[k], 'V'), '', '')));
    cards.push(card('三相平均', si(v.values.rms_avg, 'V'), '', `最大偏差 ${num(v.values.rms_unbalance_pct, 3)} %`));
    cards.push(card('基波不平衡度', num(v.values.unbalance_pct, 3), '%', '负序/正序'));
    const seq = v.values.sequence || {};
    cards.push(card('零序含量', num(seq.zero_seq_pct, 3), '%', `U0=${si(seq.U0, 'V')}`));
  }
  $('#v-cards').innerHTML = cards.join('') || card('状态', '尚无结果', '', '请先启动数据源');
  drawLine($('#v-wave'), waveData(v), { ylabel: 'V', unit: 'V', zero: true, fmtX: x => x.toFixed(3) + 's', height: 240 });
  $('#v-percycle').innerHTML = v ? perCycleTable(v.values.per_cycle, 'V') : '';
  $('#v-seq').innerHTML = v ? seqTable(v.values.sequence, 'V') + table(['相', '基波有效值'], PH.map(k => [k + ' 相', si(v.values.fundamental_rms[k], 'V')])) : '';
  $('#v-win').innerHTML = winNotes('voltage');
}

function renderCurrent() {
  const i = q('current');
  const cards = [];
  if (i) {
    PH.forEach(k => cards.push(card(`${k} 相电流有效值`, si(i.values.rms[k], 'A'), '', `波峰系数 ${num(i.values.crest_factor[k], 3)}`)));
    cards.push(card('零线电流 In', si(i.values.neutral_rms, 'A'), '', 'In=|ia+ib+ic|（3n 次零序叠加）'));
    cards.push(card('三相平均', si(i.values.rms_avg, 'A'), '', `最大偏差 ${num(i.values.rms_unbalance_pct, 3)} %`));
    cards.push(card('基波不平衡度', num(i.values.unbalance_pct, 3), '%', '负序/正序'));
  }
  $('#i-cards').innerHTML = cards.join('') || card('状态', '尚无结果', '', '请先启动数据源');
  drawLine($('#i-wave'), waveData(i), { ylabel: 'A', unit: 'A', zero: true, fmtX: x => x.toFixed(3) + 's', height: 240 });
  $('#i-percycle').innerHTML = i ? perCycleTable(i.values.per_cycle, 'A') : '';
  $('#i-seq').innerHTML = i ? seqTable(i.values.sequence, 'A') + table(['相', '基波有效值', '波峰系数'],
    PH.map(k => [k + ' 相', si(i.values.fundamental_rms[k], 'A'), num(i.values.crest_factor[k], 3)])) : '';
  $('#i-win').innerHTML = winNotes('current');
}

function renderPower() {
  const p = q('power');
  const cards = [];
  if (p) {
    const v = p.values;
    cards.push(card('有功 P', si(v.p_total, 'W'), '', `谐波和 ${si(v.p_harmonic_sum_total, 'W')}（残差 ${num(v.p_residual_pct, 5)}%）`));
    cards.push(card('无功 Q', si(v.q_total, 'var'), '', v.modes.reactive_note));
    cards.push(card('视在 S', si(v.s_total, 'VA'), '', v.modes.apparent_note));
    cards.push(card('功率因数 PF', num(v.pf_total, 4), '', v.quadrant ? v.quadrant.name : ''));
    if (v.fundamental && v.fundamental.enabled) {
      cards.push(card('基波有功 P1', si(v.fundamental.p1_total, 'W'), '', `占比 ${num(v.fundamental.fundamental_share_pct, 2)} %`));
      cards.push(card('基波无功 Q1', si(v.fundamental.q1_total, 'var'), '', `DPF ${num(v.fundamental.dpf, 4)}`));
    }
  }
  $('#p-cards').innerHTML = cards.join('') || card('状态', '尚无结果', '', '请先启动数据源');
  const ser = (p && p.series && p.series.p_total) ? [{ name: 'p(t) 总瞬时功率', color: COLORS.P, data: p.series.p_total.map((v2, k) => [k * (p.series.stride || 1) / ((S.state.config.sampling || {}).fs || 6400), v2]) }] : [];
  drawLine($('#p-wave'), ser, { ylabel: 'W', unit: 'W', zero: true, fmtX: x => x.toFixed(3) + 's', height: 220 });
  $('#p-phase').innerHTML = p ? table(['相', 'P (W)', 'Q (var)', 'S (VA)', 'PF', 'U (V)', 'I (A)'],
    PH.map(k => [k + ' 相', si(p.values.p_per_phase[k], 'W'), si(p.values.q_per_phase[k], 'var'),
                 si(p.values.s_per_phase[k], 'VA'), num(p.values.pf_per_phase[k], 4),
                 si(p.values.u_rms[k], 'V'), si(p.values.i_rms[k], 'A')])) : '';
  $('#p-fund').innerHTML = p && p.values.fundamental && p.values.fundamental.enabled ? table(['项目', 'A 相', 'B 相', 'C 相', '合计'], [
    ['基波有功 P1 (W)', ...PH.map(k => si(p.values.fundamental.p1_per_phase[k], 'W')), si(p.values.fundamental.p1_total, 'W')],
    ['基波无功 Q1 (var)', ...PH.map(k => si(p.values.fundamental.q1_per_phase[k], 'var')), si(p.values.fundamental.q1_total, 'var')],
    ['基波视在 S1 (VA)', ...PH.map(k => si(p.values.fundamental.s1_per_phase[k], 'VA')), si(p.values.fundamental.s1_total, 'VA')],
    ['基波电压 U1 (V)', ...PH.map(k => si(p.values.fundamental.u1_rms[k], 'V')), '—'],
    ['基波电流 I1 (A)', ...PH.map(k => si(p.values.fundamental.i1_rms[k], 'A')), '—'],
    ['位移因数 DPF', '—', '—', '—', num(p.values.fundamental.dpf, 4)],
    ['φ1 (deg)', '—', '—', '—', num(p.values.fundamental.phi1_deg, 2)],
  ]) + notes(p.values.notes) : '';
  $('#p-win').innerHTML = winNotes('power');
}

function renderPF() {
  const pf = q('power_factor'), p = q('power');
  const cards = [];
  if (pf) {
    const v = pf.values;
    cards.push(card('总功率因数 PF', num(v.pf_total, 4), '', `P=${si(v.p_total_for_reference, 'W')} / S=${si(v.s_total_for_reference, 'VA')}`));
    cards.push(card('位移因数 DPF', num(v.dpf, 4), '', `φ1 = ${num(v.phi1_deg, 2)}°`));
    cards.push(card('PF − DPF 差', num(v.displacement_vs_true_pf_diff, 4), '', '差值大 ⇒ 谐波畸变严重'));
    cards.push(card('无功性质', v.q_sign === 'inductive(positive)' ? '感性 (Q>0)' : (v.q_sign === 'capacitive(negative)' ? '容性 (Q<0)' : '—'), '', v.quadrant ? v.quadrant.name : ''));
  }
  $('#pf-cards').innerHTML = cards.join('') || card('状态', '尚无结果', '', '请先启动数据源');
  const hp = S.histCache.power_factor || [];
  const t0 = hp.length ? hp[0].t : 0;
  drawLine($('#pf-trend'), [{ name: 'PF', color: COLORS.P, data: hp.map(x => [x.t - t0, x.PF]) },
                            { name: 'DPF', color: COLORS.B, data: hp.map(x => [x.t - t0, x.DPF]) }],
           { ylabel: '', fmtX: x => tsX(x + t0, spanOf('power_factor')), fmtTip: x => ts(x + t0), height: 220 });
  renderCurveSave();
  drawQuadrant($('#pf-quad'), p ? p.values.p_total : NaN, p ? p.values.q_total : NaN);
  $('#pf-quadtxt').innerHTML = p && p.values.quadrant ? notes([`${p.values.quadrant.name}：${p.values.quadrant.meaning}`]) : '';
  $('#pf-phase').innerHTML = pf ? table(['相', 'PF', '说明'], PH.map(k => [k + ' 相', num(pf.values.pf_per_phase[k], 4), '分相 P/S'])) : '';
}

function renderFundamental() {
  const f = q('fundamental');
  const cards = [];
  if (f) {
    const v = f.values;
    cards.push(card('基波频率', num(v.freq_hz, 4), 'Hz', `来源 ${v.freq_source}`));
    cards.push(card('相序', v.phase_sequence || '—', '', `Uab 相角差 ${num(v.phase_diff_uab_deg, 2)}°`));
    PH.forEach(k => cards.push(card(`${k} 相基波电压 U1`, si(v.u1_rms[k], 'V'), '', `相角 ${num(v.u1_angle_deg[k], 2)}°`)));
    PH.forEach(k => cards.push(card(`${k} 相基波电流 I1`, si(v.i1_rms[k], 'A'), '', `φ=${num(v.phi_deg[k], 2)}°（U 超前 I）`)));
    cards.push(card('电压不平衡度', num(v.unbalance_u_pct, 3), '%', `负序 U2=${si(v.u_sequence.U2, 'V')}`));
    cards.push(card('电流不平衡度', num(v.unbalance_i_pct, 3), '%', `负序 I2=${si(v.i_sequence.I2, 'V')}`));
  }
  $('#f-cards').innerHTML = cards.join('') || card('状态', '尚无结果', '', '请先启动数据源');
  $('#f-phasor').innerHTML = f ? table(['相', 'U1 (V)', '∠U1 (°)', 'I1 (A)', '∠I1 (°)', 'φ=∠U−∠I (°)'],
    PH.map(k => [k, si(f.values.u1_rms[k], 'V'), num(f.values.u1_angle_deg[k], 2),
                 si(f.values.i1_rms[k], 'A'), num(f.values.i1_angle_deg[k], 2), num(f.values.phi_deg[k], 2)])) : '';
  $('#f-seq').innerHTML = f ? `<h3 style="margin-top:6px">电压序分量</h3>${seqTable(f.values.u_sequence, 'V')}<h3 style="margin-top:10px">电流序分量</h3>${seqTable(f.values.i_sequence, 'A')}` : '';
  const hf = S.histCache.fundamental || [];
  const t0 = hf.length ? hf[0].t : 0;
  drawLine($('#f-trend'), [{ name: '频率 (Hz)', color: COLORS.A, data: hf.map(x => [x.t - t0, x.f]) }],
           { ylabel: 'Hz', fmtX: x => tsX(x + t0, spanOf('fundamental')), fmtTip: x => ts(x + t0), height: 200 });
  renderCurveSave();
  $('#f-win').innerHTML = winNotes('fundamental');
}

function renderHarmonic() {
  const h = q('harmonic');
  const cards = [];
  if (h) {
    const v = h.values;
    PH.forEach(k => cards.push(card(`THD_U ${k} 相`, num(v.thd_u_pct[k], 3), '%', `最劣相 ${v.worst_phase_u}`)));
    PH.forEach(k => cards.push(card(`THD_I ${k} 相`, num(v.thd_i_pct[k], 3), '%', `最劣相 ${v.worst_phase_i}`)));
    cards.push(card('分析次数范围', `${v.order_range[0]}~${v.order_range[1]} 次`, '', `频率分辨率 ${num(v.freq_resolution_hz, 4)} Hz`));
    cards.push(card('整数周期数', num(v.n_cycles, 0), '个周波', '整周期截断 ⇒ 无泄漏'));
  }
  $('#h-cards').innerHTML = cards.join('') || card('状态', '尚无结果', '', '请先启动数据源');
  if (h && h.series) {
    const orders = h.series.orders || [];
    const modeU = (document.querySelector('input[name=hmode-u]:checked') || {}).value || 'hr';
    const modeI = (document.querySelector('input[name=hmode-i]:checked') || {}).value || 'hr';
    const srcU = modeU === 'hr' ? h.series.hr_u_pct : h.series.rms_u;
    const srcI = modeI === 'hr' ? h.series.hr_i_pct : h.series.rms_i;
    drawBars($('#h-bar-u'), orders, PH.map(k => ({ name: k + ' 相', color: COLORS[k], data: srcU[k] || [] })),
             { xlabel: '谐波次数', ylabel: modeU === 'hr' ? '含有率 %' : '幅值 V', height: 230 });
    drawBars($('#h-bar-i'), orders, PH.map(k => ({ name: k + ' 相', color: COLORS[k], data: srcI[k] || [] })),
             { xlabel: '谐波次数', ylabel: modeI === 'hr' ? '含有率 %' : '幅值 A', height: 230 });
    const rowsU = orders.map((o, idx) => [o + ' 次', ...PH.map(k => num((h.series.rms_u[k] || [])[idx], 4)),
                                          ...PH.map(k => num((h.series.hr_u_pct[k] || [])[idx], 3))]);
    $('#h-table-u').innerHTML = table(['次数', 'UA (V)', 'UB (V)', 'UC (V)', 'HR A (%)', 'HR B (%)', 'HR C (%)'], rowsU);
    const rowsI = orders.map((o, idx) => [o + ' 次', ...PH.map(k => num((h.series.rms_i[k] || [])[idx], 4)),
                                          ...PH.map(k => num((h.series.hr_i_pct[k] || [])[idx], 3))]);
    $('#h-table-i').innerHTML = table(['次数', 'IA (A)', 'IB (A)', 'IC (A)', 'HR A (%)', 'HR B (%)', 'HR C (%)'], rowsI);
  }
  $('#h-win').innerHTML = winNotes('harmonic');
}

function renderSpectrum() {
  const sp = q('spectrum');
  if (!sp || !sp.series || !sp.series.channels) {
    drawLine($('#sp-chart'), [], { empty: '暂无频谱数据', height: 300 });
    $('#sp-info').innerHTML = ''; $('#sp-notes').innerHTML = '';
    return;
  }
  const ch = $('#sp-chan').value || 'Ua';
  const scale = $('#sp-scale').value;
  const lim = +($('#sp-limit').value || 0);
  const c = sp.series.channels[ch] || { freqs: [], amp_rms: [], amp_db: [] };
  let idx = c.freqs.map((f, k) => k).filter(k => !lim || c.freqs[k] <= lim);
  const data = idx.map(k => [c.freqs[k], scale === 'db' ? c.amp_db[k] : c.amp_rms[k]]);
  drawLine($('#sp-chart'), [{ name: `${ch} 幅值谱`, color: COLORS.A, data }],
           { ylabel: scale === 'db' ? 'dB' : (ch[0] === 'U' ? 'V' : 'A'), fmtX: x => x.toFixed(0) + 'Hz', fmtTip: x => x.toFixed(2) + ' Hz', height: 300, legend: true });
  const pk = (sp.values.peaks || {})[ch] || {};
  $('#sp-info').innerHTML = table(['项目', '数值'], [
    ['主峰频率', num(pk.freq_hz, 3) + ' Hz'],
    ['主峰幅值(RMS)', si(pk.amp_rms, ch[0] === 'U' ? 'V' : 'A')],
    ['约当次数', num(pk.order_approx, 2) + ' 次'],
    ['频率分辨率', num(sp.values.freq_resolution_hz, 4) + ' Hz'],
    ['Nyquist', num(sp.values.nyquist_hz, 0) + ' Hz'],
    ['窗函数', sp.values.window_fn],
    ['输出点数', (c.freqs || []).length],
  ]);
  $('#sp-notes').innerHTML = notes(sp.values.notes);
}

function renderWindows() {
  const cfg = (S.state || {}).config;
  if (!cfg) { $('#w-table').innerHTML = ''; return; }
  const rows = Object.keys(cfg.windows).map(k => {
    const w = cfg.windows[k];
    const fft = ['fundamental', 'harmonic', 'spectrum'].includes(k);
    return `<tr><td>${k}</td>
      <td><input type="number" step="0.05" min="0.02" data-w="${k}" data-f="length_s" value="${w.length_s}"></td>
      <td><input type="number" step="0.05" min="0.02" data-w="${k}" data-f="step_s" value="${w.step_s === null ? w.length_s : w.step_s}"></td>
      <td><select data-w="${k}" data-f="policy" ${fft ? 'disabled title="FFT 类量强制整周期截断"' : ''}>
             <option value="integer_cycles" ${w.policy === 'integer_cycles' ? 'selected' : ''}>integer_cycles</option>
             <option value="full_window" ${w.policy === 'full_window' ? 'selected' : ''}>full_window</option></select></td>
      <td><select data-w="${k}" data-f="window_fn">
             <option value="rect" ${w.window_fn === 'rect' ? 'selected' : ''}>rect</option>
             <option value="hann" ${w.window_fn === 'hann' ? 'selected' : ''}>hann</option></select></td>
      <td><input type="checkbox" data-w="${k}" data-f="remove_dc" ${w.remove_dc ? 'checked' : ''}></td>
      <td>${num(w.length_s * cfg.sampling.fs, 0)} 点${fft ? ' · FFT类' : ''}</td></tr>`;
  });
  $('#w-table').innerHTML = `<table><thead><tr>${
    ['电气量', '计算时间段 (s)', '输出步长 (s)', '截断策略', '窗函数', '去直流', '样本数'].map(h => `<th>${h}</th>`).join('')
  }</tr></thead><tbody>${rows.join('')}</tbody></table>`;
  const emits = ((S.state || {}).engine || {}).emits || {};
  $('#w-emits').innerHTML = table(['电气量', '窗长 (s)', '步长 (s)', '本次运行输出次数'],
    Object.keys(cfg.windows).map(k => [k, num(cfg.windows[k].length_s, 3),
      num(cfg.windows[k].step_s === null ? cfg.windows[k].length_s : cfg.windows[k].step_s, 3), emits[k] || 0]));
}

function fillSourceForm(cfg) {
  if (cfg.source) {
    $('#src-kind').value = cfg.source.kind;
    $('#src-path').value = cfg.source.path || '';
    $('#src-host').value = cfg.source.host || '';
    $('#src-port').value = cfg.source.port || 9000;
    $('#src-frame').value = cfg.source.frame || 'text_csv';
    $('#src-fmt').value = cfg.source.struct_fmt || '';
    $('#src-fields').value = cfg.source.struct_fields || '';
    $('#src-block').value = cfg.source.block_samples || 640;
    $('#src-speed').value = cfg.source.sim_speed !== undefined ? cfg.source.sim_speed : 1;
    $('#src-tailend').checked = !!cfg.source.tail_from_end;
    $('#src-newest').checked = !!cfg.source.watch_dir_newest;
    $('#src-customtime').checked = !!cfg.source.custom_time;
    $('#src-customstart').value = cfg.source.custom_time_start || '';
    $('#src-playmode').value = cfg.source.play_start_mode || 'begin';
    $('#src-playvalue').value = cfg.source.play_start_value || '';
  }

  if (cfg.transform) {
    $('#cfg-pt').value = cfg.transform.pt_ratio;
    $('#cfg-ct').value = cfg.transform.ct_ratio;
    $('#cfg-scale').checked = !!cfg.transform.enabled;
    $('#cfg-uin').value = cfg.transform.voltage_input || 'phase';
  }
  if (cfg.sampling) {
    $('#cfg-fs').value = cfg.sampling.fs;
    $('#cfg-fnom').value = cfg.sampling.f_nom;
    $('#cfg-adaptive').checked = !!cfg.sampling.adaptive_freq;
  }
  if (cfg.harmonic) $('#cfg-hmax').value = cfg.harmonic.order_max;
  if (cfg.power) {
    $('#cfg-apparent').value = cfg.power.apparent;
    $('#cfg-reactive').value = cfg.power.reactive;
  }
}

function setFormNote(text, bad) {
  const el = $('#src-formnote');
  if (!el) return;
  el.textContent = text || '';
  el.style.color = bad ? 'var(--bad)' : '';
}

function syncSourceForm() {
  // 下拉框联动：只启用与当前源相关的字段，其余置灰禁用（填了也不生效＝最坏的用户体验）
  const kind = $('#src-kind').value, frame = $('#src-frame').value;
  const bin = kind === 'tcp' && frame === 'binary';
  const on = {
    'src-path': kind === 'csv_file' || kind === 'csv_tail',
    'src-host': kind === 'tcp',
    'src-port': kind === 'tcp',
    'src-frame': kind === 'tcp',
    'src-fmt': bin,
    'src-fields': bin,
    'src-tailend': kind === 'csv_tail',
    'src-newest': kind === 'csv_tail',
    'src-customtime': kind === 'csv_file',
    'src-customstart': kind === 'csv_file' && $('#src-customtime').checked,
    'src-playmode': kind === 'csv_file',
    'src-playvalue': kind === 'csv_file' && $('#src-playmode').value !== 'begin',
    'src-speed': kind === 'simulator',
    'src-block': true,
  };
  Object.keys(on).forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.disabled = !on[id];
    const lab = el.closest('label');
    if (lab) lab.classList.toggle('off', !on[id]);
  });
  const hint = $('#src-hint');
  if (hint) hint.textContent = SRC_HINT[kind] || '';
  const pv = $('#src-playvalue');
  if (pv) pv.placeholder = PLAY_PLACEHOLDER[$('#src-playmode').value] || '';
}

function renderSource() {
  const st = S.state || {}, cfg = st.config || {};
  if (S.formDirty) {
    setFormNote('⚠ 界面有未保存的修改：已暂停自动回填（实时推送不会覆盖你正在输入的内容）。' +
      '点「刷新」可丢弃修改并重新载入服务端配置。', true);
  } else {
    fillSourceForm(cfg);
    setFormNote('');
  }
  syncSourceForm();
  const e = st.engine || {}, src = st.source || {};
  const emits = e.emits || {};
  const summary = [
    `运行状态：<b>${st.running ? '运行中' : (st.finished ? '已结束' : '已停止')}</b>` +
      (st.error ? `　✗ ${esc(st.error)}` : ''),
    `数据源：<b>${esc(src.kind || e.source_kind || '—')}</b>` +
      (src.path ? `　文件 ${esc(src.path)}` : '') +
      (src.endpoint ? `　${esc(src.endpoint)}` : '') +
      (src.custom_time ? `　<b>自定义播放时间</b>：起始 ${esc(src.custom_time_start_source || '')} ` +
        (isNum(src.custom_time_start) ? new Date(src.custom_time_start * 1000).toLocaleString() : '') : '') +
      (src.play_start_mode && src.play_start_mode !== 'begin'
        ? `　<b>播放起点</b>：${esc(src.play_start_mode)}=${esc(src.play_start_value || '')}` +
          (src.play_seek && isNum(src.play_seek.skipped_rows) ? `（跳过 ${src.play_seek.skipped_rows} 行）` : '') +
          (src.play_seek && isNum(src.play_seek.start_byte) ? `（字节 ${src.play_seek.start_byte}/${src.play_seek.file_size}）` : '')
        : ''),
    `已摄入 ${num(e.samples_in, 0)} 点（${num(e.blocks_in, 0)} 块），数据时长 ${num(e.data_duration_s, 2)}s，` +
      `速率 ${num(e.rate_samples_per_s, 1)} 点/s（配置采样率 ${num((cfg.sampling || {}).fs, 0)}）`,
    `环形缓冲 ${num(e.buffer_fill, 0)} / ${num(e.buffer_capacity, 0)} 点（各量窗长按需自动扩容），` +
      `调度 tick ${num(e.ticks, 0)} 次`,
    '本次运行各量输出次数：' + (Object.keys(emits).length
      ? Object.keys(emits).map(k => `${k}=${emits[k]}`).join('，')
      : '（尚无输出）'),
    `当前配置生效文件：<code>${esc(e.config_path || '—')}</code>（界面里保存的配置写入该文件；` +
      `出厂模板 configs/default.json 保持干净）`,
  ];
  const notesArr = [];
  (e.notes || []).forEach(n => notesArr.push(n));
  (src.notes || []).forEach(n => notesArr.push('源：' + n));
  (e.gaps || []).forEach(g => notesArr.push(`⚠ 数据缺口 t=${ts(g.t)} 时长 ${num(g.gap_s * 1000, 1)}ms（约 ${num(g.missing_samples, 0)} 点）`));
  $('#src-summary').innerHTML = summary.map(x => `<div>${x}</div>`).join('') + notes(notesArr);
  $('#src-state').textContent = JSON.stringify({ engine: st.engine, source: st.source, error: st.error }, null, 2);
}

/* 实时落盘面板：开关/目录 走 PUT /api/config（热更新即时生效），状态来自 GET /api/realtime */
async function refreshRealtime() {
  const out = $('#rt-out');
  if (!out) return;
  try {
    const d = await api('/api/realtime');
    S.realtime = d;
    const total = Object.values(d.rows_written || {}).reduce((a, b) => a + (b || 0), 0);
    const lines = [`状态：${d.enabled ? '已启用' : '未启用'}　目录：${d.dir_display || d.dir}　本次会话已写 ${total} 行`];
    (d.files || []).forEach(f => lines.push(`✓ ${CURVE_NAME[f.quantity] || f.quantity}：${f.path}（本次 ${f.rows_this_session} 行）`));
    CURVE_KEYS.filter(k => d.curve_save && d.curve_save[k] === false).forEach(k => lines.push(`－ ${CURVE_NAME[k]}：未勾选「保存曲线」，不落盘`));
    (d.dir_files || []).forEach(f => lines.push(`· 目录现有 ${f.name}（${(f.size_bytes / 1024).toFixed(1)} KB，${new Date(f.mtime * 1000).toLocaleString()}）`));
    (d.errors || []).forEach(e => lines.push('✗ ' + e));
    out.innerHTML = notes(lines);
  } catch (e) { out.innerHTML = notes(['✗ ' + e.message]); }
}

async function saveRealtime() {
  const on = !!$('#rt-enable').checked, dir = ($('#rt-dir').value || '').trim();
  const body = { output: { realtime_save: on } };
  if (dir) body.output.realtime_dir = dir;
  try {
    await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    S.rtDirty = false;
    toast(`实时落盘已${on ? '启用' : '关闭'}（已写入配置）`, 'ok');
    refreshRealtime();
  } catch (e) { toast('实时落盘设置失败：' + e.message, 'err'); }
}

function renderExport() {
  const st = S.state || {};
  renderCurveSave();
  const outCfg = (st.config || {}).output;
  if (outCfg && !S.rtDirty) {              // 开关/目录回填服务端配置；用户正在编辑（rtDirty）时不覆盖
    if ($('#rt-enable')) $('#rt-enable').checked = outCfg.realtime_save !== false;
    if ($('#rt-dir')) $('#rt-dir').value = outCfg.realtime_dir || 'output/realtime';
  }
  if (!S.realtime) refreshRealtime();
  $('#ex-state').textContent = JSON.stringify(st.engine || {}, null, 2);
  const notesArr = [];
  ((st.engine || {}).notes || []).forEach(n => notesArr.push(n));
  ((st.engine || {}).errors || []).forEach(n => notesArr.push('✗ ' + n));
  ((st.engine || {}).gaps || []).forEach(g => notesArr.push(`⚠ 数据缺口 t=${ts(g.t)} 时长 ${num(g.gap_s * 1000, 1)}ms（约 ${num(g.missing_samples, 0)} 点）`));
  if (st.error) notesArr.push('✗ ' + st.error);
  $('#ex-notes').innerHTML = notes(notesArr);
  $('#ex-json').textContent = S.result ? JSON.stringify(S.result, null, 1).split('\n').slice(0, 200).join('\n') : '（无结果）';
}

function render() {
  try {
    switch (S.view) {
      case 'overview': renderOverview(); break;
      case 'voltage': renderVoltage(); break;
      case 'current': renderCurrent(); break;
      case 'power': renderPower(); break;
      case 'power_factor': renderPF(); break;
      case 'fundamental': renderFundamental(); break;
      case 'harmonic': renderHarmonic(); break;
      case 'spectrum': renderSpectrum(); break;
      case 'windows': renderWindows(); break;
      case 'source': renderSource(); break;
      case 'export': renderExport(); break;
      default: break;
    }
  } catch (e) {
    console.error(e);
  }
}

/* ------------------------------------------------------------------ 交互 */

function collectSourcePayload() {
  // 只送**与当前源相关**且**用户确实填了**的字段：
  // 空字符串/空数字会覆盖服务端已保存的配置（例如把 host 抹成 ''、path 抹成 ''），
  // 而 /api/engine/start 是深合并语义，不送＝保留原值，这才是期望行为。
  const kind = $('#src-kind').value;
  const p = { kind };
  const txt = (id) => ($('#' + id).value || '').trim();
  const numOr = (id, dflt) => {
    const v = parseFloat($('#' + id).value);
    return Number.isFinite(v) ? v : dflt;
  };
  if (kind === 'csv_file' || kind === 'csv_tail') {
    const path = txt('src-path');
    if (path) p.path = path;                 // 留空则不送：由服务端校验并给出「需要 source.path」
  }
  if (kind === 'csv_file') {
    // 自定义播放时间：布尔必送（取消勾选要能关掉）；起始时间**空串也送**——空＝「用文件第 1 条数据时间」是有效语义
    p.custom_time = !!$('#src-customtime').checked;
    p.custom_time_start = txt('src-customstart');
    // 播放起点：模式必送（选回「开头」要能关掉）；取值只在非 begin 时送（begin 不读取值，旧值留着无害）
    p.play_start_mode = $('#src-playmode').value || 'begin';
    if (p.play_start_mode !== 'begin') p.play_start_value = txt('src-playvalue');
  }
  if (kind === 'csv_tail') {
    p.tail_from_end = !!$('#src-tailend').checked;
    p.watch_dir_newest = !!$('#src-newest').checked;
  }
  if (kind === 'tcp') {
    const host = txt('src-host');
    if (host) p.host = host;
    p.port = numOr('src-port', 0);           // 0 会被服务端拒（port 非法），比静默用默认更好排查
    p.frame = $('#src-frame').value;
    if (p.frame === 'binary') {
      const fmt = txt('src-fmt'), flds = txt('src-fields');
      if (fmt) p.struct_fmt = fmt;
      if (flds) p.struct_fields = flds;
    }
  }
  if (kind === 'simulator') {
    const sp = numOr('src-speed', null);
    if (sp !== null && sp > 0) p.sim_speed = sp;
  }
  const bs = numOr('src-block', null);
  if (bs !== null && bs > 0) p.block_samples = bs;
  return p;
}

function collectConfigPayload() {
  // PUT /api/config 是**深合并**：不送的键保留服务端现值。
  // 所以空输入框必须**跳过**而不是送 0——否则 +'' === 0 会让 fs/PT/CT 变成 0，
  // 服务端校验直接 400「sampling.fs 必须 > 0（当前 0）」（实测可复现）。
  const skipped = [];
  const pos = (id, label) => {
    const v = parseFloat($('#' + id).value);
    if (Number.isFinite(v) && v > 0) return v;
    skipped.push(label);
    return null;
  };
  const transform = { enabled: $('#cfg-scale').checked, voltage_input: $('#cfg-uin').value };
  const pt = pos('cfg-pt', 'PT 变比'), ct = pos('cfg-ct', 'CT 变比');
  if (pt !== null) transform.pt_ratio = pt;
  if (ct !== null) transform.ct_ratio = ct;
  const sampling = { adaptive_freq: $('#cfg-adaptive').checked };
  const fs = pos('cfg-fs', '采样率 fs'), fnom = pos('cfg-fnom', '额定频率');
  if (fs !== null) sampling.fs = fs;
  if (fnom !== null) sampling.f_nom = fnom;
  const harmonic = {};
  const hmax = pos('cfg-hmax', '最高谐波次数');
  if (hmax !== null) harmonic.order_max = Math.max(2, Math.round(hmax));
  return {
    payload: {
      transform, sampling, harmonic,
      power: { apparent: $('#cfg-apparent').value, reactive: $('#cfg-reactive').value },
    },
    skipped,
  };
}

function collectWindowPayload() {
  const out = {};
  $$('[data-w]').forEach(el => {
    const k = el.dataset.w, f = el.dataset.f;
    out[k] = out[k] || {};
    if (el.type === 'checkbox') out[k][f] = el.checked;
    else if (el.tagName === 'SELECT') out[k][f] = el.value;
    else out[k][f] = el.value === '' ? null : +el.value;
  });
  return { windows: out };
}

async function startEngine(payloadExtra = {}) {
  try {
    // 只送 source（+ 可选 windows）：/api/engine/start 的白名单只有 source 键与 windows，
    // 夹带 transform/sampling/harmonic/power 会被服务端**静默忽略**——用户改了 PT/CT 再点
    // 「启动数据源」以为生效了，其实没有。口径/变比一律走「保存配置（热更新）」。
    const payload = Object.assign(collectSourcePayload(), payloadExtra);
    const r = await api('/api/engine/start', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    S.formDirty = false; S.srcDirty = false;
    toast(`已启动数据源：${r.config.source.kind}` +
      (S.cfgDirty ? '（提示：口径/变比的修改请点「保存配置（热更新）」）' : ''), 'ok');
    S.cfgDirty = false;
    S.state = await api('/api/state');
    renderTop(); render();
    setTimeout(refreshHistory, 800);
  } catch (e) { toast('启动失败：' + e.message, 'err'); }
}

async function stopEngine() {
  try { await api('/api/engine/stop', { method: 'POST' }); toast('已停止', 'ok'); }
  catch (e) { toast('停止失败：' + e.message, 'err'); }
  S.state = await api('/api/state'); renderTop(); render();
}

async function saveConfig() {
  try {
    const { payload, skipped } = collectConfigPayload();
    const r = await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
                                         body: JSON.stringify(payload) });
    S.formDirty = false; S.cfgDirty = false; S.srcDirty = false;
    if (skipped.length) {
      toast(`配置已保存并热更新；${skipped.join('、')} 为空 → 保留服务端原值`, 'ok');
    } else { toast('配置已保存并热更新', 'ok'); }
    S.state = await api('/api/state'); renderTop(); render();
  } catch (e) { toast('保存失败：' + e.message, 'err'); }
}

async function saveWindows() {
  try {
    await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
                               body: JSON.stringify(collectWindowPayload()) });
    toast('窗口配置已保存（各量按新时间段计算）', 'ok');
    S.state = await api('/api/state'); render();
  } catch (e) { toast('保存失败：' + e.message, 'err'); }
}

function applyPreset(sec) {
  $$('[data-w][data-f=length_s]').forEach(el => { el.value = sec; });
  $$('[data-w][data-f=step_s]').forEach(el => { el.value = sec; });
}

async function probe() {
  const p = $('#src-path').value.trim();
  if (!p) { toast('请先填写 CSV 路径或目录', 'err'); return; }
  $('#probe-out').innerHTML = '<div class="notes">探查中…</div>';
  try {
    const r = await api('/api/probe?path=' + encodeURIComponent(p));
    if (!r.ok) { $('#probe-out').innerHTML = notes(['✗ ' + r.error]); return; }
    $('#probe-out').innerHTML = notes([
      `✓ ${r.path}`, `大小 ${r.size_mb} MB · 编码 ${r.encoding} · 行数 ${r.rows} · 时长约 ${num(r.duration_s, 2)}s`,
      `表头：${(r.header || []).join(' | ')}`,
      `列映射：${JSON.stringify(r.columns)}`,
      `时间戳模式 ${r.ts_mode} · 推算 fs ${num(r.fs_est, 3)} Hz（配置 ${r.fs_configured} Hz，偏差 ${num(r.fs_deviation_pct, 4)}%）`,
      ...(r.notes || []),
    ]);
  } catch (e) { $('#probe-out').innerHTML = notes(['✗ ' + e.message]); }
}

async function listFiles() {
  try {
    const r = await api('/api/files?sub=data');
    if (!r.ok) { $('#files-out').innerHTML = notes(['✗ ' + r.error]); return; }
    $('#files-out').innerHTML = r.files.length
      ? notes([`data 目录文件：`, ...r.files.map(f => `· ${f.name}${f.dir ? '' : ` (${f.size_mb} MB)`}`)])
      : notes(['data 目录暂无 CSV（可用 cli.py gen-sample 生成样例，或把真实数据放入 data/）']);
  } catch (e) { $('#files-out').innerHTML = notes(['✗ ' + e.message]); }
}

async function runSelftest() {
  $('#self-summary').innerHTML = '<div class="notes">自检运行中（构造解析信号并逐项对账，约 1~3 秒）…</div>';
  $('#self-table').innerHTML = '';
  try {
    const p = new URLSearchParams({ fs: $('#self-fs').value, freq: $('#self-f').value, pt: $('#self-pt').value,
                                    ct: $('#self-ct').value, window: $('#self-win').value });
    const r = await api('/api/selftest?' + p.toString());
    $('#self-summary').innerHTML = notes([
      `${r.all_ok ? '✓ 全部通过' : '✗ 存在失败项'}：共 ${r.total} 项，通过 ${r.passed}，失败 ${r.failed}，` +
      `通过率 ${num(r.pass_rate_pct, 2)}%，最差相对误差 ${r.worst_rel_err.toExponential(3)}，耗时 ${r.duration_s}s`,
      `工况：fs=${r.conditions.fs}Hz，f=${r.conditions.f_nom}Hz，PT=${r.conditions.pt}，CT=${r.conditions.ct}，窗长=${r.conditions.window_s}s`,
    ], (r.failures || []).map(f => `✗ ${f.id} ${f.name}：期望 ${f.expected} 实际 ${f.actual}（相对误差 ${(f.rel_err * 100).toFixed(4)}%）`));
    $('#self-table').innerHTML = table(['编号', '项目', '期望值', '实际值', '相对误差', '容差', '单位', '结论'],
      r.checks.map(c => [c.id, c.name, num(c.expected, 6), num(c.actual, 6),
        (c.rel_err * 100).toFixed(5) + '%', (c.tol_rel * 100).toFixed(3) + '%', c.unit,
        c.ok ? '<span class="badge ok">PASS</span>' : '<span class="badge bad">FAIL</span>']));
    toast(r.all_ok ? '算法自检全部通过' : '自检存在失败项，请查看明细', r.all_ok ? 'ok' : 'err');
  } catch (e) {
    $('#self-summary').innerHTML = notes(['✗ 自检执行失败：' + e.message]);
  }
}

async function saveCfgFile() {
  try {
    const cfg = await api('/api/config');
    await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cfg) });
    const cp = ((S.state || {}).engine || {}).config_path || 'configs/runtime.json';
    $('#exp-out').innerHTML = notes([`✓ 当前配置已写入 ${cp}（下次启动自动加载；出厂模板 configs/default.json 未被改动）`]);
    toast('配置已持久化', 'ok');
  } catch (e) { $('#exp-out').innerHTML = notes(['✗ ' + e.message]); }
}

/* ------------------------------------------------------------------ 初始化 */

function bind() {
  $$('.navitem').forEach(b => b.addEventListener('click', () => switchView(b.dataset.view)));
  $('#btn-start').addEventListener('click', () => startEngine());
  $('#btn-stop').addEventListener('click', stopEngine);
  $('#btn-refresh').addEventListener('click', async () => {
    try {
      S.formDirty = false; S.srcDirty = false; S.cfgDirty = false;   // 刷新＝丢弃未保存修改并重新回填
      S.result = await api('/api/result?full=true');
      S.state = await api('/api/state');
      renderTop(); render(); toast('已刷新快照', 'ok');
    } catch (e) { toast(e.message, 'err'); }
  });
  $('#btn-start2').addEventListener('click', () => startEngine());
  $('#btn-stop2').addEventListener('click', stopEngine);
  $('#btn-probe').addEventListener('click', probe);
  $('#btn-listfiles').addEventListener('click', listFiles);
  $('#btn-savecfg').addEventListener('click', saveConfig);
  $('#btn-save-win').addEventListener('click', saveWindows);
  $('#btn-preset-fast').addEventListener('click', () => applyPreset(0.2));
  $('#btn-preset-std').addEventListener('click', () => applyPreset(1));
  $('#btn-preset-slow').addEventListener('click', () => applyPreset(5));
  $('#btn-selftest').addEventListener('click', runSelftest);
  $('#btn-save-cfgfile').addEventListener('click', saveCfgFile);
  ['sp-chan', 'sp-scale', 'sp-limit'].forEach(id => $('#' + id).addEventListener('change', renderSpectrum));
  // 数据源下拉框联动：选 kind 切换可用字段与填写说明；选 frame=binary 才放开 struct 两项
  $('#src-kind').addEventListener('change', () => { S.srcDirty = true; S.formDirty = true; syncSourceForm(); });
  $('#src-frame').addEventListener('change', () => { S.srcDirty = true; S.formDirty = true; syncSourceForm(); });
  $('#src-customtime').addEventListener('change', () => { S.srcDirty = true; S.formDirty = true; syncSourceForm(); });
  // 「保存曲线」勾选（面板标题处 + 导出页列表，动态生成 → 事件委托）
  document.addEventListener('change', (ev) => {
    const el = ev.target;
    if (el && el.classList && el.classList.contains('curve-save')) setCurveSave(el.dataset.curve, el.checked);
  });
  $('#btn-save-curves').addEventListener('click', saveCurves);
  $('#btn-rt-save').addEventListener('click', saveRealtime);
  $('#btn-rt-refresh').addEventListener('click', refreshRealtime);
  ['rt-enable', 'rt-dir'].forEach(id => { $('#' + id).addEventListener('input', () => { S.rtDirty = true; }); $('#' + id).addEventListener('change', () => { S.rtDirty = true; }); });
  $('#src-playmode').addEventListener('change', () => { S.srcDirty = true; S.formDirty = true; syncSourceForm(); });
  // 任何用户输入都置脏：否则 0.2s 一次的推送会把正在编辑的字段改回服务端配置
  $$('#view-source input, #view-source select').forEach((el) => {
    const mark = () => { S.formDirty = true; if (el.id.startsWith('cfg-')) S.cfgDirty = true; else S.srcDirty = true; };
    el.addEventListener('input', mark);
    el.addEventListener('change', mark);
  });
  $$('input[name=hmode-u],input[name=hmode-i]').forEach(el => el.addEventListener('change', renderHarmonic));
  window.addEventListener('resize', () => { clearTimeout(window._rz); window._rz = setTimeout(render, 180); });
  setInterval(() => { if (S.view === 'overview' || S.view === 'power_factor' || S.view === 'fundamental') refreshHistory(); }, 3000);
}

async function init() {
  bind();
  try {
    S.state = await api('/api/state');
  } catch (e) { toast('无法获取服务状态：' + e.message, 'err'); }
  try {
    const r = await fetch('/api/result?full=true');
    if (r.ok) S.result = await r.json();
  } catch (e) { /* 尚无结果 */ }
  connectWS();
  renderTop(); render();
  setNavFoot('就绪 · 左侧导航切换子界面');
  setTimeout(refreshHistory, 500);
}

document.addEventListener('DOMContentLoaded', init);
