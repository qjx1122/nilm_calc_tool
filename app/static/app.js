// v0.93：分相电流极性反转（"A"/"AC"…）↔ 三个勾选框
function setInvPhases(pre, v) { const s = String(v || '').toUpperCase(); for (const ch of 'abc') { const el = document.querySelector('#' + pre + '-inv-' + ch); if (el) el.checked = s.includes(ch.toUpperCase()); } }
function getInvPhases(pre) { let out = ''; for (const ch of 'abc') { const el = document.querySelector('#' + pre + '-inv-' + ch); if (el && el.checked) out += ch.toUpperCase(); } return out; }
/* app.js —— 电力电气量计算与负荷辨识工具 前端（原生 JS + Canvas，无外部 CDN 依赖）
 *
 * 结构：导航条切换子界面（需求③）；每个电气量一个子界面（需求②）；
 *       WebSocket 实时推送，失败自动降级为轮询（保证代理环境下也能用）。
 */
'use strict';

/* v0.23：渲染上下文。电气量子界面合并为「左：总线侧 / 右：分路侧」——同一套 render 函数跑两遍，
   分路侧那遍 RC.side='branch'：$ 选择器自动落到克隆列里带 -br 后缀的元素，q()/curHist() 等取分路侧数据（BRD）。 */
const RC = { side: 'bus' };
/* 当前生效的侧别：整页切到分路侧（旧 setSide 路径）或右列渲染中 → 'branch' */
function sideOf() { return S.side === 'branch' ? 'branch' : RC.side; }
/* 按侧别取元素（分路侧 → id 加 -br 后缀；不存在则退回原元素）。异步函数 await 之后 RC.side 已复位，必须用它而不是 $() */
function E(side, id) {
  if (side === 'branch') { const el = document.getElementById(id + '-br'); if (el) return el; }
  return document.getElementById(id);
}
/* v0.24：事件 / 负荷辨识 / 实时落盘 等按侧别各自一份状态（左列总线侧、右列分路侧） */
function _sideStore() {
  return { events: [], evSummary: null, evLoaded: false, evDirty: false, realtime: null, rtDirty: false,
           nl: { events: [], summary: null, cycles: null, loaded: false, dirty: false, formBuilt: false, winFile: null },
           ew: { voltage: { cyc: null, wave: null }, current: { cyc: null, wave: null }, power: { cyc: null, wave: null } } };   // v0.71：实时监测三页的周波窗
}
const SD = { bus: _sideStore(), branch: _sideStore() };
window.SD = SD;
function sd(side) { return SD[side || sideOf()]; }
function $(sel) {
  if (RC.side === 'branch' && typeof sel === 'string' && sel[0] === '#' && !/[\s>.\[:]/.test(sel)) {
    const el = document.querySelector(sel + '-br');
    if (el) return el;
  }
  return document.querySelector(sel);
}
const $$ = (s) => Array.from(document.querySelectorAll(s));
function curResult() { return RC.side === 'branch' ? BRD.result : S.result; }
function curState() { return (RC.side === 'branch' ? BRD.state : S.state) || {}; }
function curHist(key) { return (RC.side === 'branch' ? BRD.histCache : S.histCache)[key] || []; }
function radioVal(name, dflt) {
  const el = document.querySelector(`input[name=${name}${RC.side === 'branch' ? '-br' : ''}]:checked`);
  return (el && el.value) || dflt;
}
const PH = ['A', 'B', 'C'];
const COLORS = { A: '#4ea1ff', B: '#3ddc97', C: '#ffb648', P: '#ff7ac6', Q: '#9d7bff', S: '#5ee0d0' };

const S = {
  side: 'bus',                 // 侧别由左侧导航的分组决定（总览/数据源＝总线侧；「总线侧」「分路侧」分组各自切换）
  state: null, result: null, view: 'overview',
  ws: null, wsOk: false, poll: null, histCache: {}, histAt: {},
  // 表单脏标记：用户一旦动手编辑，就暂停自动回填。
  // 不做这层保护时，快量 0.2s 一次的 result 推送会触发 render()→renderSource()，
  // 把用户刚选的下拉框、刚输入一半的路径**改回服务端配置**（实测可复现）。
  formDirty: false, srcDirty: false, cfgDirty: false,
  // 趋势曲线元数据（/api/history 返回的 count_total/span_s/hours 等）与「保存曲线」勾选的本地镜像
  histMeta: {}, curveLocal: null, curvePending: false,
  // 实时落盘 / 事件 / 负荷辨识的列表与脏标记按侧别放在 SD.bus / SD.branch（v0.24）
};
window.S = S;   // 自检脚本可读（tools/ui_r12_check.cjs 等）
/* ------------------------------------------------------------------ 增量刷新（v0.15）
 * 界面每秒收到 state/result 推送；大多数区域内容并未变化。这里让 innerHTML / textContent 的写入
 * 在「字符串与上次写入相同」时直接跳过（不触碰 DOM、不重排、不打断用户选择/滚动）。
 * 画布同理：drawLine 按数据签名跳过无变化的重绘（见 drawLine 开头）。 */
(function installIncrementalDom() {
  const patch = (proto, prop) => {
    const d = Object.getOwnPropertyDescriptor(proto, prop);
    if (!d || !d.set) return;
    Object.defineProperty(proto, prop, {
      configurable: true, enumerable: d.enumerable, get: d.get,
      set(v) {
        v = v == null ? '' : String(v);
        if (this.__inc && this.__inc[prop] === v) return;        // 未变化 → 不刷新
        (this.__inc || (this.__inc = {}))[prop] = v;
        d.set.call(this, v);
      },
    });
  };
  if (typeof Element !== 'undefined') patch(Element.prototype, 'innerHTML');
  if (typeof Node !== 'undefined') patch(Node.prototype, 'textContent');
})();
/* 手动改过子节点（appendChild / insertAdjacentHTML）的元素，调用它让下一次 innerHTML 写入强制生效 */
function domTouched(el) { if (el) el.__inc = null; }

const CURVE_KEYS = ['voltage', 'current', 'power', 'power_factor', 'fundamental', 'harmonic', 'interharmonic', 'dc'];
const CURVE_NAME = { voltage: '三相电压', current: '三相电流', power: 'P/Q/S', power_factor: 'PF/DPF', fundamental: '频率', harmonic: 'THD',
                     interharmonic: 'TIHD', dc: '直流分量' };
const EVENT_NAME = { fund_phasor: '基波相量超限', harm_phasor: '谐波相量超限', interharm: '间谐波相量超限',
                     freq: '频率超限', rocof: '频率变化率超限', power_osc: '功率振荡' };
const EV_FIELDS = ['enabled', 'save', 'hysteresis', 'limits_secondary', 'u_nom', 'u1_high_pct', 'u1_low_pct', 'i1_high', 'hr_u_limit_pct', 'hr_i_limit_pct',
                   'thd_u_limit_pct', 'thd_i_limit_pct', 'ih_u_limit_pct', 'ih_i_limit_pct', 'f_low', 'f_high', 'rocof_limit',
                   'osc_window_s', 'osc_f_min', 'osc_f_max', 'osc_limit_pct', 'osc_min_w', 'osc_min_points'];
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
function spanOf(key) { const m = (RC.side === 'branch' ? BRD.histMeta : S.histMeta)[key]; return m && isNum(m.span_s) ? m.span_s : 0; }
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

/* v0.26.2：落盘状态副文本——行数一行、文件/目录路径单独一行且允许任意位置换行（长路径不再超出卡片） */
function writerSub(w) {
  if (!w) return '';
  const p = w.current_file || w.dir || '';
  if (!p) return '';
  const head = w.current_file ? `${w.rows_written} 行 → ` : '目录：';
  return `${head}<span class="path" title="${esc(p)}">${esc(p)}</span>`;
}
function card(k, v, unit, sub) {
  return `<div class="card"><div class="k">${k}</div><div class="v">${v}${unit ? `<span class="u">${unit}</span>` : ''}</div>${sub ? `<div class="s">${sub}</div>` : ''}</div>`;
}

/* v0.25：列表单位统一放表头、单元格只放数字。unitScale 按整列最大值选一个 SI 前缀，返回表头单位与格式函数 */
function unitScale(vals, unit = '', d = 4) {
  const m = Math.max(0, ...(vals || []).filter(v => isNum(+v)).map(v => Math.abs(+v)));
  const [k, pfx] = m >= 1e9 ? [1e9, 'G'] : m >= 1e6 ? [1e6, 'M'] : m >= 1e3 ? [1e3, 'k'] : (m > 0 && m < 1e-3) ? [1e-3, 'm'] : [1, ''];
  const u = pfx + unit;
  return { u, hdr: (name) => (u ? `${name} (${u})` : name), f: (v, dd = d) => (v === null || v === undefined || !isNum(+v)) ? '—' : (+v / k).toFixed(dd) };
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
  const r = curResult();
  if (!r || !r.quantities) return null;
  const o = r.quantities[key];
  return (o && o.ok) ? o : null;
}

function qwin(key) {
  const r = curResult();
  return (r && r.quantities && r.quantities[key]) ? r.quantities[key].window : null;
}

function winNotes(key) {
  const w = qwin(key);
  if (!w) return '<div class="notes">该量本窗未计算（缓冲数据不足或已停止）</div>';
  const mine = curResult().quantities[key];
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

/* 曲线缩放（v0.17，需求②）：每张折线图独立的 X / Y 缩放状态（X 存绝对坐标：x + tbase，趋势图数据滚动时视窗不漂移）。
   操作：滚轮＝X 轴缩放（以光标为中心）；Shift+滚轮＝Y 轴缩放；拖选矩形＝只显示框选区间（宽 >6px 取 X 区间，高 >6px 取 Y 区间）；
   双击＝复位；图例行的 X＋/X－/Y＋/Y－/复位 按钮同义。只影响显示。 */
const ZOOM = {};
window.ZOOM = ZOOM;
function zoomOf(cv) { return (cv && cv.id && ZOOM[cv.id]) || null; }
function setZoom(cv, z) {
  if (!cv || !cv.id) return;
  if (!z || (!z.x && !z.y)) delete ZOOM[cv.id]; else ZOOM[cv.id] = z;
  if (cv.__redraw) cv.__redraw();
}
function zoomAxis(cv, axis, factor, center) {
  // factor <1 放大、>1 缩小；center＝缩放中心（数据坐标，绝对 X 或 Y），缺省取当前视窗中点
  const c = cv.__chart; if (!c) return;
  const z = Object.assign({ x: null, y: null }, zoomOf(cv) || {});
  const tb = isNum(c.opt.tbase) ? c.opt.tbase : 0;
  const cur = axis === 'x' ? [c.xmin + tb, c.xmax + tb] : [c.ymin, c.ymax];
  const full = axis === 'x' ? [c.xfull[0] + tb, c.xfull[1] + tb] : c.yfull;
  const mid = isNum(center) ? center : (cur[0] + cur[1]) / 2;
  let lo = mid - (mid - cur[0]) * factor, hi = mid + (cur[1] - mid) * factor;
  if (factor > 1 && lo <= full[0] && hi >= full[1]) { z[axis] = null; setZoom(cv, z); return; }   // 缩回全图 → 复位该轴
  if (hi - lo <= 0) return;
  z[axis] = [lo, hi];
  setZoom(cv, z);
}
function zoomReset(cv) { setZoom(cv, null); }
/* v0.29：放大后平移坐标轴。axis='x'|'y'，delta＝数据坐标位移（X 为绝对坐标差）；视窗整体平移、不改变缩放倍率，边界夹在全图范围内。
   frac 形式（zoomPanFrac）＝按当前视窗宽度的比例平移（按钮 / 方向键用）。 */
function zoomPan(cv, axis, delta, chart) {
  const c = chart || cv.__chart; if (!c) return false;
  const z = Object.assign({ x: null, y: null }, zoomOf(cv) || {});
  if (!z[axis] || !isNum(delta) || delta === 0) return false;           // 该轴未放大 ⇒ 已是全图，无可平移
  const tb = isNum(c.opt.tbase) ? c.opt.tbase : 0;
  const full = axis === 'x' ? [c.xfull[0] + tb, c.xfull[1] + tb] : c.yfull;
  let [lo, hi] = z[axis]; const w = hi - lo;
  if (!(w > 0) || !(full[1] - full[0] > w)) return false;
  lo += delta; hi += delta;
  if (lo < full[0]) { lo = full[0]; hi = lo + w; }
  if (hi > full[1]) { hi = full[1]; lo = hi - w; }
  if (Math.abs(lo - z[axis][0]) < 1e-12 * Math.max(1, Math.abs(lo))) return false;
  z[axis] = [lo, hi];
  setZoom(cv, z);
  return true;
}
function zoomPanFrac(cv, axis, frac) {
  const z = zoomOf(cv); if (!z || !z[axis]) return false;
  return zoomPan(cv, axis, (z[axis][1] - z[axis][0]) * frac);
}
window.zoomPan = zoomPan; window.zoomPanFrac = zoomPanFrac;
function bindHover(cv) {
  if (cv.__hoverBound) return;
  cv.__hoverBound = true;
  const pos = (e) => { const r = cv.getBoundingClientRect(); return { mx: e.clientX - r.left, my: e.clientY - r.top }; };
  // v0.31：坐标轴区域（左侧 Y 轴刻度带 / 底部 X 轴刻度带）＝拖选缩放该轴，不论是否已放大；绘图区内：已放大＝平移、未放大或 Ctrl＝框选
  const axisZone = (p) => { const c = cv.__chart; if (!c || !p) return null; const inY = p.my >= c.pad.t && p.my <= c.h - c.pad.b, inX = p.mx >= c.pad.l && p.mx <= c.w - c.pad.r;
    if (p.mx < c.pad.l && inY) return 'y'; if (p.my > c.h - c.pad.b && inX) return 'x'; return null; };
  cv.__axisZone = axisZone;
  const setCursor = () => {
    if (cv.__pan) { cv.style.cursor = 'grabbing'; return; }
    if (cv.__drag && cv.__drag.axis) { cv.style.cursor = cv.__drag.axis === 'x' ? 'ew-resize' : 'ns-resize'; return; }
    const az = axisZone(cv.__hover);
    cv.style.cursor = az === 'x' ? 'ew-resize' : az === 'y' ? 'ns-resize' : (zoomOf(cv) ? 'grab' : 'crosshair');
  };
  cv.__setCursor = setCursor;
  cv.addEventListener('mousemove', (e) => {
    cv.__hover = pos(e);
    if (cv.__pan) {                                          // v0.29：放大后按住左键拖动＝平移视窗（捕获拖动起点时的坐标系，边拖边重绘）
      const pn = cv.__pan, c = pn.c, p = cv.__hover;
      const z = Object.assign({ x: null, y: null }, pn.z);
      const tb = isNum(c.opt.tbase) ? c.opt.tbase : 0;
      const full = { x: [c.xfull[0] + tb, c.xfull[1] + tb], y: c.yfull };
      const clamp = (axis, lo, hi) => { const w = hi - lo; if (lo < full[axis][0]) { lo = full[axis][0]; hi = lo + w; } if (hi > full[axis][1]) { hi = full[axis][1]; lo = hi - w; } return [lo, hi]; };
      if (z.x) { const d = c.xAt(pn.x0) - c.xAt(p.mx); z.x = clamp('x', pn.z.x[0] + d, pn.z.x[1] + d); }
      if (z.y) { const d = c.yAt(pn.y0) - c.yAt(p.my); z.y = clamp('y', pn.z.y[0] + d, pn.z.y[1] + d); }
      pn.moved = pn.moved || Math.abs(p.mx - pn.x0) > 2 || Math.abs(p.my - pn.y0) > 2;
      if (pn.moved) { setZoom(cv, z); return; }
    }
    if (cv.__drag) { cv.__drag.x1 = cv.__hover.mx; cv.__drag.y1 = cv.__hover.my; }
    if (!cv.__drag && !cv.__pan) setCursor();
    if (cv.__redraw) cv.__redraw();
  });
  cv.addEventListener('mouseleave', () => { cv.__hover = null; cv.__hoverInfo = null; cv.__drag = null; cv.__pan = null; setCursor(); if (cv.__redraw) cv.__redraw(); });
  cv.addEventListener('mousedown', (e) => {
    if (e.button !== 0 || !cv.__chart) return;
    const p = pos(e);
    const az = axisZone(p);
    if (az) {                                                // v0.31：在坐标轴刻度带上拖动 ⇒ 只对该轴拖选缩放（放大状态下也可用）
      cv.__drag = { x0: p.mx, y0: p.my, x1: p.mx, y1: p.my, axis: az }; setCursor(); e.preventDefault(); return;
    }
    // v0.29：已放大且未按 Ctrl ⇒ 左键拖动平移；未放大或 Ctrl+拖动 ⇒ 框选放大（原行为）
    if (zoomOf(cv) && !e.ctrlKey) { cv.__pan = { x0: p.mx, y0: p.my, c: cv.__chart, z: JSON.parse(JSON.stringify(zoomOf(cv))), moved: false }; setCursor(); e.preventDefault(); return; }
    cv.__drag = { x0: p.mx, y0: p.my, x1: p.mx, y1: p.my };
    e.preventDefault();
  });
  const finish = (e) => {
    if (cv.__pan) { cv.__pan = null; setCursor(); if (cv.__redraw) cv.__redraw(); return; }
    const d = cv.__drag, c = cv.__chart; cv.__drag = null;
    if (!d || !c) { setCursor(); return; }
    const clampPx = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
    // 轴带拖选：把像素夹到绘图区，只取该轴
    if (d.axis === 'x') { d.x0 = clampPx(d.x0, c.pad.l, c.w - c.pad.r); d.x1 = clampPx(d.x1, c.pad.l, c.w - c.pad.r); }
    if (d.axis === 'y') { d.y0 = clampPx(d.y0, c.pad.t, c.h - c.pad.b); d.y1 = clampPx(d.y1, c.pad.t, c.h - c.pad.b); }
    const dx = d.axis === 'y' ? 0 : Math.abs(d.x1 - d.x0), dy = d.axis === 'x' ? 0 : Math.abs(d.y1 - d.y0);
    if (dx < 6 && dy < 6) { setCursor(); if (cv.__redraw) cv.__redraw(); return; }
    const tb = isNum(c.opt.tbase) ? c.opt.tbase : 0;
    const xa = c.xAt(Math.min(d.x0, d.x1)), xb = c.xAt(Math.max(d.x0, d.x1));
    const ya = c.yAt(Math.max(d.y0, d.y1)), yb = c.yAt(Math.min(d.y0, d.y1));
    const z = Object.assign({ x: null, y: null }, zoomOf(cv) || {});
    if (dx >= 6) z.x = [xa + tb, xb + tb];
    if (dy >= 6) z.y = [ya, yb];
    setZoom(cv, z); setCursor();
  };
  cv.addEventListener('mouseup', finish);
  cv.addEventListener('dblclick', (e) => { e.preventDefault(); zoomReset(cv); });
  cv.addEventListener('wheel', (e) => {
    const c = cv.__chart; if (!c) return;
    e.preventDefault();
    const p = pos(e), f = e.deltaY > 0 ? 1.25 : 0.8;
    // v0.29：Alt+滚轮＝左右平移、Alt+Shift+滚轮＝上下平移；触控板横向滚动（deltaX）＝左右平移
    if (e.altKey && zoomOf(cv)) { zoomPanFrac(cv, e.shiftKey ? 'y' : 'x', (e.deltaY > 0 ? 1 : -1) * (e.shiftKey ? -0.15 : 0.15)); return; }
    if (!e.shiftKey && Math.abs(e.deltaX) > Math.abs(e.deltaY) && zoomOf(cv)) { zoomPanFrac(cv, 'x', e.deltaX > 0 ? 0.15 : -0.15); return; }
    if (e.shiftKey) zoomAxis(cv, 'y', f, c.yAt(p.my));
    else zoomAxis(cv, 'x', f, c.xAt(p.mx) + (isNum(c.opt.tbase) ? c.opt.tbase : 0));
  }, { passive: false });
  // v0.29：鼠标悬停在图上时方向键平移（←→ X 轴、↑↓ Y 轴；Shift 加速）
  cv.tabIndex = 0;
  cv.addEventListener('keydown', (e) => {
    if (!zoomOf(cv)) return;
    const k = e.key, step = e.shiftKey ? 0.5 : 0.15;
    const m = { ArrowLeft: ['x', -step], ArrowRight: ['x', step], ArrowUp: ['y', step], ArrowDown: ['y', -step] }[k];
    if (!m) return;
    e.preventDefault(); zoomPanFrac(cv, m[0], m[1]);
  });
  cv.addEventListener('mouseenter', () => { try { if (document.activeElement && /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)) return; cv.focus({ preventScroll: true }); } catch (e) {} });
  setCursor();
}
function renderZoomBar(cv) {
  // 图例行末尾的缩放按钮（每张图一个，动态插入；无图例时单独一行）
  if (!cv || !cv.id || !cv.parentNode) return;
  let bar = cv.__zoombar;
  if (!bar) {
    bar = document.createElement('span'); bar.className = 'zoombar'; bar.dataset.chart = cv.id;
    bar.innerHTML = '<span class="muted">缩放：</span>' + [['x-', 'X＋', '放大 X 轴（滚轮）'], ['x+', 'X－', '缩小 X 轴'], ['y-', 'Y＋', '放大 Y 轴（Shift+滚轮）'], ['y+', 'Y－', '缩小 Y 轴'], ['reset', '复位', '恢复全图（双击图面）']]
      .map(([a, t, tip]) => `<button type="button" class="zoom-btn" data-z="${a}" title="${tip}">${t}</button>`).join('') +
      '<span class="muted panlbl">移动：</span>' + [['pl', '◀', '向左移动 X 轴（放大后拖动图面 / ← 键 / Alt+滚轮）'], ['pr', '▶', '向右移动 X 轴（→ 键）'], ['pu', '▲', '向上移动 Y 轴（↑ 键 / Alt+Shift+滚轮）'], ['pd', '▼', '向下移动 Y 轴（↓ 键）']]
      .map(([a, t, tip]) => `<button type="button" class="zoom-btn pan-btn" data-z="${a}" title="${tip}">${t}</button>`).join('') +
      '<span class="zoomtip muted">拖选区间＝只显示该区间</span>';
    bar.addEventListener('click', (ev) => {
      const b = ev.target.closest('button.zoom-btn'); if (!b) return;
      const a = b.dataset.z;
      if (a === 'reset') zoomReset(cv);
      else if (a[0] === 'p') zoomPanFrac(cv, (a === 'pl' || a === 'pr') ? 'x' : 'y', (a === 'pl' || a === 'pd') ? -0.25 : 0.25);   // v0.29：平移 1/4 视窗
      else zoomAxis(cv, a[0], a[1] === '-' ? 0.5 : 2);
    });
    cv.__zoombar = bar;
  }
  const host = cv.__legend || null;
  if (host) { if (bar.parentNode !== host) host.appendChild(bar); }
  else if (!bar.parentNode || !bar.parentNode.isConnected) {
    const d = document.createElement('div'); d.className = 'serlegend'; d.appendChild(bar);
    cv.insertAdjacentElement('afterend', d);
  }
  const z = zoomOf(cv);
  bar.classList.toggle('active', !!z);
  bar.querySelectorAll('.pan-btn').forEach(b => { const ax = (b.dataset.z === 'pl' || b.dataset.z === 'pr') ? 'x' : 'y'; b.disabled = !(z && z[ax]); });
  if (cv.__setCursor && !cv.__pan) cv.__setCursor();
  const tip = bar.querySelector('.zoomtip');
  if (tip) tip.textContent = z ? ('已缩放' + (z.x ? ' X' : '') + (z.y ? ' Y' : '') + '：拖动图面 / 方向键 / ◀▶▲▼ 移动坐标轴；在 X / Y 轴刻度带上拖选或 Ctrl+拖选再放大；双击复位') : '拖选区间＝只显示该区间（在 X / Y 轴刻度带上拖选＝只缩放该轴）';
}

/* 公共时间段模式：时间轴固定为 [公共起点, 公共终点]（相对 tbase），段外的点不画 —— 两侧、各子界面坐标轴一致 */
function commonWindowX(opt) {
  const cw = (S.state || {}).common_window;
  if (!cw || !cw.enabled || opt.tbase === undefined || !isNum(opt.tbase)) return null;
  return [cw.t_start - opt.tbase, (isNum(cw.play_end) ? cw.play_end : cw.t_end) - opt.tbase];
}

function chartSig(cv, series, opt) {
  // 数据签名：每条线的名字/点数/首末点/中点 + 画布宽度 + 关键选项；相同 → 画面不可能变化
  const xf = commonWindowX(opt);
  const parts = [cv.clientWidth, opt.height || cv.dataset.h, !!opt.zero, opt.empty || '', (opt.marks || []).length, xf ? xf.join('~') : ''];
  series.forEach(s => {
    if (!s || !s.data) { parts.push('-'); return; }
    const d = s.data, n = d.length, f = d[0], l = d[n - 1], m = d[n >> 1];
    parts.push(s.name, s.color, n, f && f[0], f && f[1], l && l[0], l && l[1], m && m[1]);
  });
  (opt.marks || []).forEach(mk => parts.push(mk.x, mk.label));
  return parts.join('|');
}

/* 曲线分线显示开关（v0.16，需求⑤）：多条曲线的图在画布下方给出图例勾选，取消＝该线不画（不影响计算/保存）。
   勾选状态按「图表 id → 隐藏曲线名列表」存入 config.output.series_hidden（随配置持久化，重开页面仍保持）。 */
/* v0.19：曲线可带 defaultHidden:true（如总览 P/Q/S 图的分相曲线）——配置里没有该图的记录时默认不画；
   用户一旦勾选过，以配置为准；「全部显示」用哨兵 SER_NONE 记录（空列表会被配置清洗掉，否则又回到默认隐藏）。 */
const SER_NONE = '*none*';
function seriesHiddenSet(cv, series) {
  const id = cv && cv.id; if (!id) return new Set();
  const ser = series || (cv && cv.__series) || [];
  const local = S.seriesLocal && S.seriesLocal[id];
  const m = ((((S.state || {}).config || {}).output || {}).series_hidden) || {};
  const saved = local || m[id];
  if (!saved) return new Set(ser.filter(s => s && s.defaultHidden).map(s => s.name));
  return new Set(saved.filter(n => n !== SER_NONE));
}
function renderSeriesLegend(cv, series, hidden) {
  if (!cv || !cv.id || !cv.parentNode) return;
  const names = series.filter(s => s && s.name).map(s => s.name);
  if (names.length < 2) { if (cv.__legend) { cv.__legend.remove(); cv.__legend = null; } return; }
  const key = names.join('|') + '#' + [...hidden].join('|');
  if (cv.__legend && cv.__legendKey === key) return;
  if (!cv.__legend) {
    const d = document.createElement('div'); d.className = 'serlegend'; d.dataset.chart = cv.id;
    cv.insertAdjacentElement('afterend', d); cv.__legend = d;
  }
  cv.__legendKey = key;
  cv.__legend.innerHTML = '<span class="muted">显示：</span>' + series.filter(s => s && s.name).map(s =>
    `<label class="${hidden.has(s.name) ? 'off' : ''}" title="勾选＝显示该曲线；取消＝隐藏（已保存到配置）"><input type="checkbox" class="ser-vis" data-chart="${esc(cv.id)}" data-name="${esc(s.name)}" ${hidden.has(s.name) ? '' : 'checked'}><i style="background:${s.color || '#4ea1ff'}"></i>${esc(s.name)}</label>`).join('');
  if (cv.__zoombar) cv.__legend.appendChild(cv.__zoombar);
}
async function setSeriesVisible(chartId, name, on) {
  const cv = document.getElementById(chartId); if (!cv) return;
  const cur = seriesHiddenSet(cv);
  if (on) cur.delete(name); else cur.add(name);
  const list = [...cur];
  if (!list.length && (cv.__series || []).some(s => s && s.defaultHidden)) list.push(SER_NONE);
  S.seriesLocal = S.seriesLocal || {}; S.seriesLocal[chartId] = list;
  if (cv.__redraw) cv.__redraw();
  try {
    await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
                               body: JSON.stringify({ output: { series_hidden: { [chartId]: list } } }) });
    if (S.state && S.state.config) {
      S.state.config.output = S.state.config.output || {};
      const m = { ...(S.state.config.output.series_hidden || {}) };
      if (list.length) m[chartId] = list; else delete m[chartId];
      S.state.config.output.series_hidden = m;
    }
  } catch (e) { toast('保存曲线显示开关失败：' + e.message, 'err'); }
  finally { if (S.seriesLocal) delete S.seriesLocal[chartId]; if (cv.__redraw) cv.__redraw(); }
}

function drawLine(cv, series, opt = {}) {
  cv.__series = series;
  const hidden = seriesHiddenSet(cv, series);
  const zoom = zoomOf(cv);
  const sig = chartSig(cv, series, opt) + '#' + [...hidden].join(',') + '#' + JSON.stringify(zoom);
  renderSeriesLegend(cv, series, hidden);
  renderZoomBar(cv);
  if (!opt.force && cv.__sig === sig && cv.__chart !== undefined) return;    // 无变化 → 不重绘
  cv.__sig = sig;
  const { ctx, w, h } = prep(cv, opt.height);
  const pad = { l: 62, r: 12, t: 12, b: 26 };
  const xfix = commonWindowX(opt);
  let pts = series.filter(s => s && s.data && s.data.length && !hidden.has(s.name));
  if (xfix) pts = pts.map(s => Object.assign({}, s, { data: s.data.filter(([x]) => x >= xfix[0] - 1e-6 && x <= xfix[1] + 1e-6) })).filter(s => s.data.length);
  cv.__chart = null;
  cv.__redraw = () => drawLine(cv, series, Object.assign({}, opt, { force: true }));
  bindHover(cv);
  ctx.strokeStyle = '#1e2740'; ctx.lineWidth = 1;
  ctx.strokeRect(pad.l + .5, pad.t + .5, w - pad.l - pad.r, h - pad.t - pad.b);
  if (!pts.length) {
    ctx.fillStyle = '#5f6f92'; ctx.font = '12px sans-serif'; ctx.textAlign = 'center';
    const allHidden = hidden.size && series.some(s => s && s.data && s.data.length);
    ctx.fillText(allHidden ? '所有曲线已隐藏（在下方图例勾选显示）' : xfix ? (opt.empty || '公共时间段内暂无数据') : (opt.empty || '暂无数据（等待计算结果…）'), w / 2, h / 2);
    return;
  }
  let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
  pts.forEach(s => s.data.forEach(([x, y]) => {
    if (!isNum(y)) return;
    if (x < xmin) xmin = x; if (x > xmax) xmax = x;
    if (y < ymin) ymin = y; if (y > ymax) ymax = y;
  }));
  if (!isFinite(ymin)) return;
  if (xfix) { xmin = xfix[0]; xmax = xfix[1]; }          // 公共时间段：坐标轴固定为整段，曲线随播放逐步填满
  if (opt.zero) { ymin = Math.min(ymin, 0); ymax = Math.max(ymax, 0); }
  const pad2 = (ymax - ymin) * 0.08 || Math.abs(ymax) * 0.05 || 1;
  ymin -= pad2; ymax += pad2;
  let yt = niceTicks(ymin, ymax, 5);
  ymin = Math.min(yt[0], ymin); ymax = Math.max(yt[yt.length - 1], ymax);
  const xfull = [xmin, xmax], yfull = [ymin, ymax];      // 全图范围（缩放复位 / 判断是否已缩回全图）
  const tbz = isNum(opt.tbase) ? opt.tbase : 0;
  if (zoom && zoom.x) { xmin = zoom.x[0] - tbz; xmax = zoom.x[1] - tbz; }
  if (zoom && zoom.y) { ymin = zoom.y[0]; ymax = zoom.y[1]; yt = niceTicks(ymin, ymax, 5).filter(t => t >= ymin && t <= ymax); }
  const X = x => pad.l + (xmax === xmin ? 0.5 : (x - xmin) / (xmax - xmin)) * (w - pad.l - pad.r);
  const Y = y => h - pad.b - (y - ymin) / (ymax - ymin) * (h - pad.t - pad.b);
  const xAt = px => xmin + (px - pad.l) / Math.max(1e-9, (w - pad.l - pad.r)) * (xmax - xmin);
  const yAt = py => ymin + (h - pad.b - py) / Math.max(1e-9, (h - pad.t - pad.b)) * (ymax - ymin);
  ctx.font = '10.5px sans-serif'; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
  yt.forEach(t => {
    if (t < ymin || t > ymax) return;
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
  if (zoom) {                                              // 缩放后：曲线裁剪到绘图区，区间外不画
    ctx.save(); ctx.beginPath(); ctx.rect(pad.l, pad.t, w - pad.l - pad.r, h - pad.t - pad.b); ctx.clip();
  }
  pts.forEach(s => {
    ctx.strokeStyle = s.color || '#4ea1ff'; ctx.lineWidth = s.width || 1.4; ctx.beginPath();
    ctx.setLineDash(s.dash || []);
    let started = false;
    s.data.forEach(([x, y]) => {
      if (!isNum(y)) { started = false; return; }
      const px = X(x), py = Y(y);
      if (!started) { ctx.moveTo(px, py); started = true; } else ctx.lineTo(px, py);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  });
  if (zoom) ctx.restore();
  if (opt.marks && opt.marks.length) {
    ctx.save();
    opt.marks.forEach(mk => {
      if (!isNum(mk.x) || mk.x < xmin || mk.x > xmax) return;
      const px = X(mk.x);
      ctx.strokeStyle = mk.color || '#ff6b6b'; ctx.lineWidth = 1; ctx.setLineDash([4, 3]);
      ctx.beginPath(); ctx.moveTo(px, pad.t); ctx.lineTo(px, h - pad.b); ctx.stroke();
      if (mk.label) {
        ctx.setLineDash([]); ctx.fillStyle = mk.color || '#ff6b6b'; ctx.font = '10px sans-serif';
        ctx.textAlign = 'left'; ctx.textBaseline = 'top';
        ctx.fillText(mk.label, px + 3, pad.t + 16 + (mk.row || 0) * 12);
      }
    });
    ctx.restore();
  }
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
  cv.__chart = { ctx, w, h, pad, pts, xmin, xmax, ymin, ymax, xfull, yfull, X, Y, xAt, yAt, opt, zoom };
  if (cv.__drag) {                                         // 拖选框（v0.31：轴带拖选＝贯穿整个绘图区的竖带 / 横带）
    const d = cv.__drag;
    let x0 = Math.min(d.x0, d.x1), y0 = Math.min(d.y0, d.y1), bw = Math.abs(d.x1 - d.x0), bh = Math.abs(d.y1 - d.y0);
    if (d.axis === 'x') { y0 = pad.t; bh = h - pad.t - pad.b; }
    if (d.axis === 'y') { x0 = pad.l; bw = w - pad.l - pad.r; }
    ctx.save(); ctx.fillStyle = 'rgba(78,161,255,0.15)'; ctx.strokeStyle = '#4ea1ff'; ctx.setLineDash([4, 3]);
    ctx.fillRect(x0, y0, bw, bh);
    ctx.strokeRect(x0 + .5, y0 + .5, bw, bh);
    ctx.restore();
  }
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
    S.ws = new WebSocket(proto + location.host + (S.side === 'branch' ? '/ws/branch' : '/ws'));
  } catch (e) { startPolling(); return; }
  S.ws.onopen = () => { S.wsOk = true; if (S.poll) { clearInterval(S.poll); S.poll = null; } setNavFoot('实时推送已连接'); startStateWatch(); };
  S.ws.onmessage = (ev) => {
    let m; try { m = JSON.parse(ev.data); } catch (e) { return; }
    if (m.type === 'hello' || m.type === 'state') {
      S.state = m.data; renderTop(); if (S.view === 'source' || S.view === 'export' || S.view === 'windows' || S.view === 'nilm') render();   // v0.46：nilm 页按运行状态启停「装载周波窗」
      if (S.view === 'compare' && Date.now() - CMP.at > 3000) refreshCompare();
      if (S.view === 'overview') refreshOverviewBranch(false);
      if (DUAL_VIEWS.includes(S.view)) { const a = branchDualActive(); if (a !== BRD.lastActive) { BRD.lastActive = a; render(); refreshBranchDual(true); } }
    }
    else if (m.type === 'result' || m.type === 'snapshot') { S.result = mergeResult(S.result, m.data); renderTop(); render(); }
    else if (m.type === 'error') { toast('服务端错误：' + m.message, 'err'); }
    else if (m.type === 'event') { onEventPush(m.data || []); }
    else if (m.type === 'events_cleared') { SD.bus.events = []; SD.bus.evSummary = null; if (S.view === 'events') refreshEvents('bus'); }
    else if (m.type === 'nilm_event') { onNilmPush(m.data || []); }
    else if (m.type === 'nilm_cleared') { SD.bus.nl.events = []; SD.bus.nl.summary = null; if (S.view === 'nilm') refreshNilm('bus'); }
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
      S.state = await (await fetch(apiUrl('/api/state'))).json();
      const r = await fetch(apiUrl('/api/result?full=false'));
      if (r.ok) S.result = await r.json();
      renderTop(); render();
    } catch (e) { /* 服务未就绪，忽略本轮 */ }
  }, 1500);
}

/* 侧别前缀（第 14 轮）：分路侧时 /api/xxx → /api/branch/xxx、/ws → /ws/branch；其余代码不感知侧别 */
function apiUrl(path, side = sideOf()) {
  if (side === 'branch' && typeof path === 'string' && path.startsWith('/api/') && !path.startsWith('/api/branch/') && !path.startsWith('/api/sides')) {
    return '/api/branch/' + path.slice(5);
  }
  return path;
}

async function setSide(side, opts = {}) {
  side = side === 'branch' ? 'branch' : 'bus';
  if (side === S.side) return;
  S.side = side;
  // 丢弃另一侧的所有缓存，重新连接推送
  S.state = null; S.result = null; S.histCache = {}; S.histAt = {};
  Object.assign(SD.bus, { events: [], evSummary: null, evLoaded: false, realtime: null });
  Object.assign(SD.bus.nl, { events: [], summary: null, cycles: null, loaded: false });
  S.formDirty = false; S.srcDirty = false; S.cfgDirty = false;
  if (S.ws) { try { S.ws.onclose = null; S.ws.close(); } catch (e) { /* ignore */ } S.ws = null; S.wsOk = false; }
  applySideUI();
  try { S.state = await api('/api/state'); } catch (e) { toast('无法获取' + sideLabel() + '状态：' + e.message, 'err'); }
  try { const r = await fetch(apiUrl('/api/result?full=true')); if (r.ok) S.result = await r.json(); } catch (e) { /* 尚无结果 */ }
  connectWS();
  renderTop(); render();
  setTimeout(refreshHistory, 300);
  if (!opts.silent) toast('已切换到' + sideLabel(), 'ok');
}

function sideLabel() { return S.side === 'branch' ? '分路侧' : '总线侧'; }

function applySideUI() {
  document.body.classList.toggle('side-branch', S.side === 'branch');
  renderModeTag();
}

async function api(path, opt, side = sideOf()) {
  const res = await fetch(apiUrl(path, side), opt);
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
  // 顶栏按总线侧 / 分路侧两行分开显示：当前侧用完整 state，对侧用 state 里的对侧摘要（每秒随 WS 刷新）
  const cur = {
    status: st.error ? ['错误', 'pill err'] : st.paused ? ['已暂停', 'pill warn'] : eng.running ? ['运行中', 'pill on'] : eng.finished ? ['已完成', 'pill off'] : ['未启动', 'pill'],
    source: (cfg.source && cfg.source.kind) || '—', time: r ? ts(r.t_ref) : '—', freq: r ? num(r.f_used, 3) + ' Hz' : '—',
    fs: cfg.sampling ? cfg.sampling.fs + ' Hz' : '—', ptct: cfg.transform ? `${cfg.transform.pt_ratio} / ${cfg.transform.ct_ratio}` : '—',
    samples: eng.samples_in !== undefined ? `${eng.samples_in} (${num(eng.data_duration_s, 1)}s)` : '—', error: st.error,
  };
  const ps = peerSummary(st) || {};
  const peer = {
    status: ps.error ? ['错误', 'pill err'] : (ps.side === 'branch' && !ps.enabled && !ps.running && !ps.finished) ? ['未启用', 'pill']
          : ps.paused ? ['已暂停', 'pill warn'] : ps.running ? ['运行中', 'pill on'] : ps.finished ? ['已完成', 'pill off'] : ['未启动', 'pill'],
    source: ps.source_kind || '—', time: ps.t_ref ? ts(ps.t_ref) : '—', freq: isNum(ps.f_used) ? num(ps.f_used, 3) + ' Hz' : '—',
    fs: isNum(ps.fs) ? ps.fs + ' Hz' : '—', ptct: isNum(ps.pt_ratio) ? `${ps.pt_ratio} / ${ps.ct_ratio}` : '—',
    samples: ps.samples_in !== undefined ? `${ps.samples_in} (${num(ps.data_duration_s, 1)}s)` : '—', error: ps.error,
  };
  const bus = S.side === 'bus' ? cur : peer, br = S.side === 'bus' ? peer : cur;
  const fill = (pre, d) => {
    const pill = $('#' + pre + 'running'); pill.textContent = d.status[0]; pill.className = d.status[1]; pill.title = d.error || '';
    $('#' + pre + 'source').textContent = d.source; $('#' + pre + 'time').textContent = d.time; $('#' + pre + 'freq').textContent = d.freq;
    $('#' + pre + 'fs').textContent = d.fs; $('#' + pre + 'ptct').textContent = d.ptct; $('#' + pre + 'samples').textContent = d.samples;
  };
  fill('st-', bus); fill('st-br-', br);
  const cw = S.side === 'bus' ? st.common_window : (st.common_window || null);
  const cwEl = $('#topstats-common');
  if (cwEl) {
    cwEl.style.display = cw && cw.enabled ? '' : 'none';
    if (cw && cw.enabled) {
      $('#st-cw-start').textContent = ts(cw.t_start); $('#st-cw-end').textContent = ts(cw.t_end);
      $('#st-cw-dur').textContent = num(cw.duration_s, 3) + ' s';
      $('#st-cw-play').textContent = ts(cw.play_start) + (cw.play_start_source === '自定义播放起始时间' ? '（自定义）' : '');
    }
  }
  $('#subtitle').textContent = `三相 U/I · 功率 · 谐波 · 电能质量事件 · 负荷辨识　|　v${st.version || '?'} · ${S.wsOk ? 'WebSocket 实时' : '轮询'} · 缓冲 ${eng.buffer_fill || 0}/${eng.buffer_capacity || 0}`;
  $('#btn-start').disabled = !!eng.running;
  $('#btn-stop').disabled = !eng.running;
  ['#btn-load-last', '#btn-load-last2'].forEach(sel => { const b = $(sel); if (b) b.disabled = !!eng.running; });
  renderLoadedLast(st, eng);
  renderPauseButtons(st, eng);
  renderNavBranchState(S.side === 'bus' ? st.branch : null);
  renderBadges(st);
}

/* 对侧摘要：总线侧 state 带 branch，分路侧 state 带 bus */
function peerSummary(st) { return S.side === 'bus' ? (st && st.branch) : (st && st.bus); }

/* 两侧徽标都实时刷新：当前侧用 engine 计数，对侧用摘要里的计数（随每秒 state 推送更新） */
function renderBadges(st) {
  const eng = (st && st.engine) || {};
  setEventBadge(eng.events_active || 0, S.side);
  const peer = peerSummary(st), other = S.side === 'bus' ? 'branch' : 'bus';
  setEventBadge(peer ? (peer.events_active || 0) : 0, other);
  setNilmBadge(peer ? (peer.nilm_events_total || 0) : 0, other);
}

/* 暂停/恢复按钮：只在离线文件源运行且未播完时可用；文案随状态切换（v0.12） */
function renderPauseButtons(st, eng) {
  const can = !!(st.pausable && eng.running && !eng.finished);
  const label = st.paused ? '恢复播放' : '暂停播放';
  [['#btn-pause', st.paused ? '恢复' : '暂停'], ['#btn-pause2', label]].forEach(([sel, txt]) => {
    const b = $(sel); if (!b) return;
    b.disabled = !can; b.textContent = txt;
    b.className = st.paused ? 'primary' : '';
    if (!can) b.title = st.pausable ? '离线文件未在播放' : '暂停/恢复仅支持离线文件（csv_file）源';
    else b.title = st.paused ? '从暂停处继续播放（不重读、不跳过）' : '暂停：不再读文件、不计算，数据时刻原地不动';
  });
}

async function togglePause() {
  const st = S.state || {}, eng = st.engine || {};
  if (!(st.pausable && eng.running && !eng.finished)) {
    toast(st.pausable ? '离线文件未在播放，无法暂停' : '暂停/恢复仅支持离线文件（csv_file）源', 'err'); return;
  }
  const paused = !!st.paused;
  try {
    const r = await api(paused ? '/api/engine/resume' : '/api/engine/pause', { method: 'POST' });
    S.state = r.state || S.state;
    toast(paused ? '已恢复播放' : '已暂停播放（数据时刻停在 ' + ($('#st-time').textContent || '—') + '）', 'ok');
  } catch (e) { toast((paused ? '恢复' : '暂停') + '失败：' + e.message, 'err'); S.state = await api('/api/state'); }
  renderTop(); if (S.view === 'source') render();
}

/* 运行状态看门狗（F-41 兜底）：引擎运行/暂停期间每 2 s 校对一次 /api/state，
   推送丢失或断线也能自动翻到「已完成 / 已停止」；空闲时不请求。 */
function startStateWatch() {
  if (S.stateWatch) return;
  S.stateWatch = setInterval(async () => {
    const st = S.state || {}, eng = st.engine || {};
    // 不以本地认知的「是否运行」为前提（F-42：若本地状态是旧的/服务端被别处启动，永远不会开始校对）；
    // /api/state 很小，2 s 一次可以接受。
    try {
      const fresh = await api('/api/state');
      const was = !!(st.running || eng.running), now = !!(fresh.running || (fresh.engine || {}).running);
      S.state = fresh;
      if (was !== now || !!st.paused !== !!fresh.paused || !!st.finished !== !!fresh.finished || !!st.pausable !== !!fresh.pausable) {
        renderTop(); if (S.view === 'source' || S.view === 'export') render();
        if (was && !now && fresh.finished) toast('离线文件播放完毕', 'ok');
      } else if (now || fresh.paused) renderTop();
    } catch (e) { /* 服务不可达时由 WS onclose 处理 */ }
  }, 2000);
}

function sideStatusText(x) {
  if (!x) return '—';
  if (x.error) return '错误';
  if (x.paused) return '已暂停';
  if (x.running) return '运行中';
  if (x.finished) return '已完成';
  return x.enabled === false ? '未启用' : '未启动';
}

/* 顶栏模式标签：分路侧启用 → 「总线侧 ＋ 分路侧」，否则「总线侧」 */
function renderModeTag() {
  const t = document.getElementById('side-title'); if (!t) return;
  if (S.side === 'branch') { t.textContent = '分路侧'; return; }
  const br = (S.state || {}).branch || {};
  t.textContent = (br.enabled || br.running) ? '总线侧 ＋ 分路侧' : '总线侧';
}

function renderNavBranchState(br) {
  renderModeTag();
  const b = $('#nav-br-state'); if (!b) return;
  if (S.side === 'branch') { br = S.state || null; if (br) br = { error: br.error, paused: br.paused, running: br.running, finished: br.finished, enabled: true }; }
  // v0.23：分路侧数据源未启用 → 导航里的「分路侧」分组整体隐藏（正在分路侧子界面时不隐藏，避免当前页消失）
  document.body.classList.toggle('no-branch-nav', S.side === 'bus' && (!(br && (br.enabled || br.running)) || !!(br && br.hide_ui)));   // v0.33：hide_ui 时「实时监测」组的分路侧徽标也隐藏
  if (!br) { b.style.display = 'none'; return; }
  const t = sideStatusText(br);
  b.textContent = t; b.style.display = '';
  b.className = 'badge' + (br.error ? ' bad' : br.running ? ' ok' : '');
}

function renderOverviewSides() {
  const el = $('#ov-sides'); if (!el) return;
  const st = S.state || {}, eng = st.engine || {}, cfg = st.config || {};
  if (S.side !== 'bus') { el.innerHTML = ''; return; }
  const br = st.branch || {};
  const busTxt = st.error ? '错误' : st.paused ? '已暂停' : eng.running ? '运行中' : eng.finished ? '已完成' : '未启动';
  const busSrc = (cfg.source && cfg.source.kind) || '—';
  const busPath = (cfg.source && cfg.source.path) ? String(cfg.source.path).split(/[\\/]/).pop() : '';
  const brPath = br.source_path ? String(br.source_path).split(/[\\/]/).pop() : '';
  const brOn = !!(br.enabled || br.running || br.finished || br.error);
  el.innerHTML = [
    card('总线侧数据源', busTxt, '', `${busSrc} ${busPath}　样本 ${eng.samples_in || 0}　事件 ${eng.events_total || 0}　负荷事件 ${eng.nilm_events_total || 0}`),
    card('分路侧设备数据源', brOn ? sideStatusText(br) : '未启用', '',
      brOn ? `${br.source_kind || 'csv_file'} ${brPath}　样本 ${br.samples_in || 0}　事件 ${br.events_total || 0}　负荷事件 ${br.nilm_events_total || 0}` : '在「数据源与控制」页启用并配置分路侧文件'),
  ].join('');
}

function setEventBadge(n, side) {
  const badge = document.getElementById((side || sideOf()) === 'branch' ? 'nav-ev-badge-br' : 'nav-ev-badge');
  if (!badge) return;
  badge.textContent = String(n); badge.style.display = n ? '' : 'none'; badge.classList.toggle('bad', !!n);
}

async function switchView(v, side) {
  // 导航分组决定侧别：总览/数据源与控制/工具 → 总线侧；「总线侧」「分路侧」分组下的子界面 → 对应侧
  const want = side || 'bus';
  if (want !== S.side) await setSide(want, { silent: true });
  const prevView = S.view; S.view = v;
  $$('.navitem').forEach(b => b.classList.toggle('active', b.dataset.view === v && (b.dataset.side || 'bus') === S.side));
  $$('.view').forEach(s => s.classList.toggle('active', s.id === 'view-' + v));
  if (prevView !== v) window.scrollTo(0, 0);                                  // v0.99.9：切换页面回到顶部（原来保留上一页的滚动位置，短页面会看到空白）
  render();
  if (['overview', 'power_factor', 'fundamental', 'harmonic', 'interharmonic', 'dc', 'nilm'].includes(v)) refreshHistory();
  if (v === 'events') refreshEvents('bus');
  if (v === 'nilm') refreshNilm('bus');
  if (['events', 'nilm'].includes(v)) { BRD.evAt = 0; BRD.nlAt = 0; }
  if (v === 'compare') refreshCompare();
  if (v === 'overview') refreshOverviewBranch(true);
  if (DUAL_VIEWS.includes(v)) refreshBranchDual(true);
}

/* ------------------------------------------------------------------ 总览：分路侧数据（第 15 轮补充） */

/* v0.19：总览 P/Q/S 趋势 = 三相总 P/Q/S（默认显示）+ 分相 Pa/Pb/Pc、Qa/Qb/Qc、Sa/Sb/Sc（默认隐藏，图例勾选显示）。
   v0.20.1：分相线一律**实线**。此前 Q 用 [5,3]、S 用 [2,2] 虚线且线宽 1.1，三相值几乎重合时三条短虚线叠在一起、
   再加上 0.2 s 一点的高密度采样，屏幕上看起来像一串散点（用户反馈「三相无功 / 视在功率曲线为散点」）。
   现在按量取基色（P 粉 / Q 紫 / S 青），A/B/C 相分别用基色的亮 / 原 / 暗三档区分。 */
function shadeColor(hex, amt) {       // amt>0 变亮、<0 变暗（-1..1）
  const n = parseInt(hex.slice(1), 16);
  const ch = (v) => Math.max(0, Math.min(255, Math.round(amt >= 0 ? v + (255 - v) * amt : v * (1 + amt))));
  const r = ch((n >> 16) & 255), g = ch((n >> 8) & 255), bl = ch(n & 255);
  return '#' + ((1 << 24) | (r << 16) | (g << 8) | bl).toString(16).slice(1);
}
const PQS_PHASE_SHADE = { A: 0.45, B: 0, C: -0.4 };
function pqsSeries(hp, t0) {
  const out = [{ name: 'P', color: COLORS.P, data: hp.map(p => [p.t - t0, p.P]) },
               { name: 'Q', color: COLORS.Q, data: hp.map(p => [p.t - t0, p.Q]) },
               { name: 'S', color: COLORS.S, data: hp.map(p => [p.t - t0, p.S]) }];
  ['P', 'Q', 'S'].forEach(k => ['A', 'B', 'C'].forEach(ph => {
    const f = k + ph.toLowerCase();
    out.push({ name: f, color: shadeColor(COLORS[k], PQS_PHASE_SHADE[ph]), width: 1.3, defaultHidden: true, data: hp.map(p => [p.t - t0, p[f]]) });
  }));
  return out;
}

const OVB = { result: null, hist: {}, meta: {}, at: 0, busy: false, keys: ['voltage', 'current', 'power', 'harmonic'] };
window.OVB = OVB;   // 调试/自检脚本可读（tools/ui_r14_check.cjs）

async function refreshOverviewBranch(force) {
  // 总览页在总线侧上下文；分路侧数据直接走 /api/branch/*（不切侧），每 ≥2 s 刷一次
  if (S.side !== 'bus' || S.view !== 'overview') return;
  if (OVB.busy || (!force && Date.now() - OVB.at < 2000)) return;
  OVB.busy = true;
  try {
    const br = (S.state || {}).branch || {};
    const active = !!(br.enabled || br.running || br.finished);
    if (!active) { OVB.result = null; OVB.hist = {}; OVB.doneFetched = false; return; }
    // 分路侧已播放完毕：取最后一次完整数据后不再请求（曲线与数据停在终值；总线侧未播完则继续各自刷新）
    if (br.running) OVB.doneFetched = false;
    else if (OVB.doneFetched) return;
    const [res, ...hs] = await Promise.all([
      fetch('/api/branch/result?full=false').then(r => r.ok ? r.json() : null).catch(() => null),
      ...OVB.keys.map(k => fetch(`/api/branch/history/${k}?max_points=${HIST_MAX_POINTS}`).then(r => r.ok ? r.json() : null).catch(() => null)),
    ]);
    // /api/branch/result?full=false 给的是「最近一次发射」（可能只含基波/谐波几项）→ 与上次合并，
    // 否则卡片里分路侧值会在"有/—"之间闪烁（v0.15.1）；分路重新启动（数据时间倒退）时清空
    if (res && OVB.result && isNum(res.t_ref) && isNum(OVB.result.t_ref) && res.t_ref < OVB.result.t_ref - 0.5) OVB.result = null;
    OVB.result = res && res.quantities ? mergeResult(OVB.result, res) : OVB.result;
    OVB.keys.forEach((k, i) => {
      OVB.hist[k] = (hs[i] && hs[i].points) || [];
      const d = hs[i] || {};
      OVB.meta[k] = { count: d.count, count_total: d.count_total, span_s: d.span_s, hours: d.hours, decimated: !!d.decimated };
    });
    if (!BR.loaded) loadBranchForm(false);      // 分路侧 config.output.curve_save（曲线标题栏「保存曲线」勾选）
    OVB.at = Date.now();
    if (!br.running && (br.finished || br.error)) OVB.doneFetched = true;
    if (S.view === 'overview') renderOverview();
  } finally { OVB.busy = false; }
}

/* ------------------------------------------------------------------ v0.23：电气量子界面双列（左总线 / 右分路） */
const ELEC_VIEWS = ['voltage', 'current', 'power', 'power_factor', 'fundamental', 'harmonic', 'interharmonic', 'dc', 'spectrum'];
/* v0.24：事件 / 负荷辨识 / 窗口配置 / 导出与日志 也合并为双列 */
const DUAL_VIEWS = ELEC_VIEWS.concat(['events', 'nilm', 'windows', 'export']);
const BRD = { result: null, state: null, histCache: {}, histMeta: {}, at: 0, histAt: 0, busy: false, built: false };
window.BRD = BRD;

function branchDualActive() {
  // 分路侧数据源未启用 → 右列整体隐藏；启用（或仍在运行/已播完有数据）→ 显示；
  // v0.33：配置 branch.hide_ui（「隐藏分路侧数据」）为真时无论是否启用都隐藏右列（只影响实时监测 / 事件与分析页）
  const br = (S.state || {}).branch || {};
  if (br.hide_ui) return false;
  return !!(br.enabled || br.running);
}

async function refreshBranchDual(force) {
  if (S.side !== 'bus' || !DUAL_VIEWS.includes(S.view)) return;
  if (!branchDualActive()) { if (BRD.result || BRD.state) { BRD.result = null; BRD.state = null; BRD.histCache = {}; BRD.histMeta = {}; SD.branch = _sideStore(); SD.branch.nl.formBuilt = true; } return; }
  if (BRD.busy || (!force && Date.now() - BRD.at < 900)) return;
  BRD.busy = true;
  try {
    const wantHist = force || Date.now() - BRD.histAt > 3000;
    const [st, res, ...hs] = await Promise.all([
      fetch('/api/branch/state').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/branch/result?full=false').then(r => r.ok ? r.json() : null).catch(() => null),
      ...(wantHist ? CURVE_KEYS.map(k => fetch(`/api/branch/history/${k}?max_points=${HIST_MAX_POINTS}`).then(r => r.ok ? r.json() : null).catch(() => null)) : []),
    ]);
    if (st) BRD.state = st;
    if (res && BRD.result && isNum(res.t_ref) && isNum(BRD.result.t_ref) && res.t_ref < BRD.result.t_ref - 0.5) BRD.result = null;   // 分路侧重启
    if (res && res.quantities) BRD.result = mergeResult(BRD.result, res);
    if (wantHist) {
      CURVE_KEYS.forEach((k, i) => {
        const d = hs[i]; if (!d) return;
        BRD.histCache[k] = d.points || [];
        BRD.histMeta[k] = { count: d.count, count_total: d.count_total, span_s: d.span_s, hours: d.hours, t_first: d.t_first, t_last: d.t_last, decimated: !!d.decimated };
      });
      BRD.histAt = Date.now();
    }
    if (!BR.loaded) loadBranchForm(false);
    BRD.at = Date.now();
    if (S.view === 'events' && Date.now() - (BRD.evAt || 0) > 2500) { BRD.evAt = Date.now(); refreshEvents('branch'); }
    if (S.view === 'nilm' && Date.now() - (BRD.nlAt || 0) > 2500) { BRD.nlAt = Date.now(); refreshNilm('branch'); }
    if (DUAL_VIEWS.includes(S.view)) render();
  } finally { BRD.busy = false; }
}

/* 把 9 个电气量 section 的内容包成两列：左列原 DOM（总线侧），右列克隆（id/name/for 加 -br 后缀，分路侧） */
function buildDualViews() {
  if (BRD.built) return; BRD.built = true;
  DUAL_VIEWS.forEach(v => {
    if (v === 'nilm') buildNilmForm('bus');          // 动态表单先建好再克隆，右列才有同样的控件
    const sec = document.querySelector('#view-' + v); if (!sec) return;
    const kids = Array.from(sec.children).filter(el => el.tagName !== 'H2');
    const wrap = document.createElement('div'); wrap.className = 'dual'; wrap.dataset.view = v;
    const left = document.createElement('div'); left.className = 'dual-col dual-bus';
    const right = document.createElement('div'); right.className = 'dual-col dual-br';
    left.innerHTML = '<div class="dual-hdr"><span class="sidename bus">总线侧</span><span class="navhint dual-hint" data-side="bus"></span></div>';
    right.innerHTML = '<div class="dual-hdr"><span class="sidename branch">分路侧</span><span class="navhint dual-hint" data-side="branch"></span></div>';
    kids.forEach(el => {
      const c = el.cloneNode(true);
      [c, ...c.querySelectorAll('[id],[name],[for]')].forEach(n => {
        if (n.id) n.id += '-br';
        if (n.getAttribute && n.getAttribute('name')) n.setAttribute('name', n.getAttribute('name') + '-br');
        if (n.getAttribute && n.getAttribute('for')) n.setAttribute('for', n.getAttribute('for') + '-br');
      });
      c.querySelectorAll('.curve-save,.curvespan').forEach(n => { n.dataset.side = 'branch'; });
      // v0.69：右列（分路侧）的配置保存按钮统一叫「保存分路侧配置」
      c.querySelectorAll('.savecfg-side').forEach(n => { n.textContent = n.textContent.replace('总线侧', '分路侧'); if (n.title) n.title = n.title.replace('本侧', '分路侧'); });
      // 导出页的下载链接：右列指向分路侧 API
      c.querySelectorAll('a[href^="/api/"]').forEach(a => { a.setAttribute('href', a.getAttribute('href').replace(/^\/api\//, '/api/branch/')); });
      right.appendChild(c); left.appendChild(el);
    });
    // 电气量页右列的下拉/单选变化 → 重画（克隆不带监听器；用委托）。事件/负荷辨识/窗口/导出页按钮由 bindSideViews('branch') 单独绑定
    if (ELEC_VIEWS.includes(v)) right.addEventListener('change', (ev) => { const t = ev.target; if (t && !t.classList.contains('curve-save') && !t.classList.contains('ser-vis')) render(); });
    wrap.appendChild(left); wrap.appendChild(right); sec.appendChild(wrap);
  });
  SD.branch.nl.formBuilt = true;                    // 克隆已带上算法参数表单
  bindSideViews('branch');
}

function renderDual(fn) {
  const wrap = document.querySelector(`#view-${S.view} .dual`);
  const act = S.side === 'bus' && branchDualActive();
  if (wrap) wrap.classList.toggle('no-branch', !act);
  RC.side = 'bus';
  try { fn(); } finally { RC.side = 'bus'; }
  const hintBus = wrap && wrap.querySelector('.dual-hint[data-side="bus"]');
  if (hintBus) hintBus.textContent = sideStatusText(Object.assign({ enabled: true }, (S.state || {}).engine || {}, { error: (S.state || {}).error, paused: (S.state || {}).paused }));
  if (!act) return;
  RC.side = 'branch';
  try { fn(); } catch (e) { console.error('branch render', e); } finally { RC.side = 'bus'; }
  const hintBr = wrap && wrap.querySelector('.dual-hint[data-side="branch"]');
  if (hintBr) {
    const br = (S.state || {}).branch || {};
    hintBr.textContent = sideStatusText(br) + (BRD.result ? '' : '（尚无结果）');
  }
}

function qb(key) { const r = OVB.result; const o = r && r.quantities && r.quantities[key]; return (o && o.ok) ? o : null; }

function ovBranchActive() {
  const br = (S.state || {}).branch || {};
  return !!(br.enabled || br.running || br.finished);
}


/* ------------------------------------------------------------------ 历史曲线 */

async function refreshHistory() {
  await Promise.all(CURVE_KEYS.map(async k => {
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

function curveSpanText(key, side) {
  const m = side === 'branch' ? (BRD.histMeta[key] || OVB.meta[key]) : S.histMeta[key];
  if (!m || !m.count_total) return '';
  return `最近 ${fmtDur(m.span_s)} · ${m.count_total} 点` + (m.decimated ? `（显示抽稀至 ${m.count}）` : '') +
    `（保留窗 ${m.hours}h）`;
}

/* 「保存曲线」勾选：各曲线面板右上角 + 导出页列表 共用 config.output.curve_save */
function curveSaveMap(side) {
  if (side === 'branch') {
    if (S.curvePendingBr && S.curveLocalBr) return S.curveLocalBr;
    const c = ((BR.cfg || {}).output || {});
    const mb = {};
    CURVE_KEYS.forEach(k => { mb[k] = c.curve_save ? c.curve_save[k] !== false : true; });
    return mb;
  }
  if (S.curvePending && S.curveLocal) return S.curveLocal;
  const cfg = ((S.state || {}).config || {}).output || {};
  const m = {};
  CURVE_KEYS.forEach(k => { m[k] = cfg.curve_save ? cfg.curve_save[k] !== false : true; });
  return m;
}

function renderCurveSave() {
  const m = curveSaveMap(), mb = curveSaveMap('branch');
  $$('.curve-save').forEach(el => { const mm = el.dataset.side === 'branch' ? mb : m; if (el.dataset.curve in mm) el.checked = !!mm[el.dataset.curve]; });
  $$('.curvespan').forEach(el => { el.textContent = curveSpanText(el.dataset.curve, el.dataset.side); });
  const list = $('#curve-save-list');
  if (list && !list.children.length) {
    const br = sideOf() === 'branch';
    list.innerHTML = CURVE_KEYS.map(k =>
      `<label><input type="checkbox" class="curve-save" data-curve="${k}"${br ? ' data-side="branch"' : ''}> ${CURVE_NAME[k]}（${k}）</label>`).join('');
    list.querySelectorAll('.curve-save').forEach(el => { el.checked = !!(br ? mb : m)[el.dataset.curve]; });
  }
  const on = CURVE_KEYS.filter(k => (sideOf() === 'branch' ? mb : m)[k]);
  const lnk = $('#lnk-curves-dl');
  if (lnk) lnk.textContent = `下载已勾选曲线（${on.length}/${CURVE_KEYS.length}，合并 CSV）`;
}

async function setCurveSave(key, on, side) {
  if (side === 'branch') {
    // 总览页分路侧曲线标题栏：写分路侧配置 config.output.curve_save（与总线侧同一语义，需求⑥）
    const mb = { ...curveSaveMap('branch'), [key]: !!on };
    S.curveLocalBr = mb; S.curvePendingBr = true;
    renderCurveSave();
    try {
      const r = await fetch('/api/branch/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
                                                   body: JSON.stringify({ output: { curve_save: { [key]: !!on } } }) });
      if (!r.ok) throw new Error((await r.json()).error || 'HTTP ' + r.status);
      BR.cfg = BR.cfg || {}; BR.cfg.output = BR.cfg.output || {};
      BR.cfg.output.curve_save = { ...(BR.cfg.output.curve_save || {}), ...mb };
      toast(`分路侧曲线「${CURVE_NAME[key]}」${on ? '已加入' : '已排除出'}保存项（已写入分路侧配置）`, 'ok');
    } catch (e) { toast('保存分路侧曲线勾选失败：' + e.message, 'err'); }
    finally { S.curvePendingBr = false; S.curveLocalBr = null; renderCurveSave(); }
    return;
  }
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

async function saveCurves(side = sideOf()) {
  const out = E(side, 'curves-out');
  try {
    const d = await api('/api/curves/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }, side);
    // notes() 会转义 HTML（告警文本来自服务端，必须转义），这里是纯文本列表即可
    const lines = d.files.map(f => `✓ ${CURVE_NAME[f.quantity] || f.quantity}：${f.path}（${f.rows} 点${f.rows_branch ? `＝总线 ${f.rows_bus} + 分路 ${f.rows_branch}，同一文件按 source_id 区分` : ''}，${ts(f.t_first)} → ${ts(f.t_last)}）`);
    (d.skipped || []).forEach(k => lines.push(`－ ${CURVE_NAME[k] || k}：未勾选，已跳过`));
    (d.empty || []).forEach(k => lines.push(`－ ${CURVE_NAME[k] || k}：已勾选但暂无数据`));
    out.innerHTML = notes([`已保存到目录 ${d.dir}（最近 ${d.hours}h）`].concat(lines));
    toast(`曲线数据已保存：${d.files.length} 个文件`, 'ok');
  } catch (e) { out.innerHTML = notes(['✗ ' + e.message]); toast('保存曲线数据失败：' + e.message, 'err'); }
}

function hseries(key, field) {
  const pts = curHist(key);
  const t0 = pts.length ? pts[0].t : 0;
  return pts.filter(p => isNum(p.t)).map(p => [p.t - t0, p[field]]);
}

/* ------------------------------------------------------------------ 跨侧对比（第 15 轮） */

const CMP = { key: 'power', field: 'P', data: null, summary: null, at: 0, busy: false };
const CMP_UNIT = { P: 'W', Q: 'var', S: 'VA', Ia: 'A', Ib: 'A', Ic: 'A', In: 'A', I1: 'A', Ua: 'V', Ub: 'V', Uc: 'V', U1: 'V',
                   Uab: 'V', Ubc: 'V', Uca: 'V', PF: '', DPF: '', f: 'Hz', THD_U: '%', THD_I: '%', TIHD_U: '%', TIHD_I: '%' };

function cmpOffsetInput() {
  const v = parseFloat($('#cmp-offset').value);
  return Number.isFinite(v) ? v : null;
}

async function refreshCompare() {
  if (CMP.busy) return; CMP.busy = true;
  try {
    const off = cmpOffsetInput();
    const qs = off === null ? '' : `offset_s=${off}`;
    const [d, sm] = await Promise.all([
      api(`/api/compare/${CMP.key}?max_points=${HIST_MAX_POINTS}` + (qs ? '&' + qs : '')),
      api('/api/compare' + (qs ? '?' + qs : '')),
    ]);
    CMP.data = d; CMP.summary = sm; CMP.at = Date.now();
    if (off === null) $('#cmp-offset').value = d.offset_s;
    renderCompare();
  } catch (e) { $('#cmp-meta').innerHTML = notes(['✗ ' + e.message]); }
  finally { CMP.busy = false; }
}

function renderCompare() {
  const ks = $('#cmp-key');
  if (!ks.options.length) {
    ks.innerHTML = CURVE_KEYS.map(k => `<option value="${k}">${CURVE_NAME[k]}</option>`).join(''); ks.value = CMP.key;
  }
  const d = CMP.data;
  if (!d) { $('#cmp-meta').textContent = '加载中…'; return; }
  const fs = $('#cmp-field');
  const fields = d.fields || [];
  if (fs.dataset.key !== CMP.key || fs.options.length !== fields.length) {
    fs.innerHTML = fields.map(f => `<option value="${f}">${f}</option>`).join(''); fs.dataset.key = CMP.key;
    if (!fields.includes(CMP.field)) CMP.field = fields[0] || '';
    fs.value = CMP.field;
  }
  const meta = [
    `总线侧 ${d.bus_count} 点（${d.bus_t_first ? ts(d.bus_t_first) + ' → ' + ts(d.bus_t_last) : '—'}）　分路侧 ${d.branch_count} 点（${d.branch_t_first ? ts(d.branch_t_first) + ' → ' + ts(d.branch_t_last) : '—'}）`,
    `已对齐 ${d.aligned_count} 对（未配对：总线 ${d.unmatched_bus} / 分路 ${d.unmatched_branch}）　偏移 ${num(d.offset_s, 3)} s　容差 ${num(d.tol_s, 3)} s（步长 ${num(d.step_s, 2)} s）` +
      (d.dt_abs_mean_s !== null && d.dt_abs_mean_s !== undefined ? `　平均时差 ${num(d.dt_abs_mean_s * 1000, 1)} ms` : '') +
      (d.offset_suggest_s !== null && d.offset_suggest_s !== undefined ? `　按起点对齐建议偏移 ${num(d.offset_suggest_s, 3)} s` : ''),
  ];
  if (!d.bus_count || !d.branch_count) meta.push('⚠ 某一侧尚无历史点：请在「数据源与控制」启用分路侧并启动总线侧（两侧同时播放）');
  else if (!d.aligned_count) meta.push('⚠ 两侧时间轴没有交集或步长不一致：点「按起点对齐」试试，或把两侧窗口配置设成一致');
  $('#cmp-meta').innerHTML = notes(meta);

  // 表格：各量最新一组
  const sm = CMP.summary;
  if (sm) {
    const rows = [];
    CURVE_KEYS.forEach(k => {
      const q = sm.quantities[k]; const L = q && q.latest;
      if (!L) { rows.push(`<tr><td>${CURVE_NAME[k]}</td><td colspan="6" class="muted">无对齐点（已对齐 ${q ? q.aligned_count : 0}）</td></tr>`); return; }
      Object.keys(L.bus).forEach(f => {
        const u = CMP_UNIT[f] || '';
        const b = L.bus[f], r = L.branch[f], df = L.diff[f], rt = L.ratio_pct ? L.ratio_pct[f] : undefined;
        const sc = unitScale([b, r, df], u);
        rows.push(`<tr><td>${CURVE_NAME[k]} · ${f}</td><td>${ts(L.t)}</td><td>${sc.f(b)}</td><td>${sc.f(r)}</td>` +
          `<td>${sc.f(df)}</td><td>${sc.u || '—'}</td><td>${isNum(rt) ? num(rt, 2) : ''}</td></tr>`);
      });
    });
    $('#cmp-table').innerHTML = `<table class="cmptbl"><thead><tr><th>电气量</th><th>时刻（总线）</th><th>总线侧</th><th>分路侧</th><th>差值 总线−分路</th><th>单位</th><th>占比 分路/总线 (%)</th></tr></thead><tbody>${rows.join('')}</tbody></table>`;
  }

  // 曲线
  const f = CMP.field, u = CMP_UNIT[f] || '';
  const pts = d.points || [];
  const t0 = pts.length ? pts[0].t : 0;
  $('#cmp-title-abs').textContent = `${CURVE_NAME[CMP.key]} · ${f}：两侧曲线`;
  const hasRatio = !!(pts.length && pts[0].ratio_pct && f in pts[0].ratio_pct);
  const showRatio = hasRatio && $('#cmp-ratio').checked;
  $('#cmp-ratio').disabled = !hasRatio;
  $('#cmp-title-diff').textContent = showRatio ? `${f}：占比（分路 / 总线 × 100%）` : `${f}：差值（总线 − 分路）`;
  const span = pts.length ? pts[pts.length - 1].t - t0 : 0;
  drawLine($('#cmp-abs'), [
    { name: '总线侧', color: COLORS.A, data: pts.map(p => [p.t - t0, p.bus[f]]) },
    { name: '分路侧', color: COLORS.C, data: pts.map(p => [p.t - t0, p.branch[f]]) },
  ], { ylabel: u, fmtX: x => tsX(x + t0, span), fmtTip: x => ts(x + t0), tbase: t0, empty: '暂无对齐点' });
  drawLine($('#cmp-diff'), [showRatio
    ? { name: '占比 %', color: COLORS.Q, data: pts.map(p => [p.t - t0, p.ratio_pct[f]]) }
    : { name: '差值', color: COLORS.P, data: pts.map(p => [p.t - t0, p.diff[f]]) }],
    { ylabel: showRatio ? '%' : u, fmtX: x => tsX(x + t0, span), fmtTip: x => ts(x + t0), tbase: t0, empty: '暂无对齐点' });
}

async function saveCompareOffset() {
  const off = cmpOffsetInput();
  if (off === null) { toast('偏移必须是数字', 'err'); return; }
  try {
    await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ branch: { time_offset_s: off } }) });
    const tf = $('#br-toffset'); if (tf) tf.value = off;
    toast(`分路侧时标偏移已保存：${off} s`, 'ok'); refreshCompare();
  } catch (e) { toast('保存失败：' + e.message, 'err'); }
}

/* ------------------------------------------------------------------ 各子界面渲染 */

function renderOverview() {
  const v = q('voltage'), i = q('current'), p = q('power'), pf = q('power_factor'),
        f = q('fundamental'), h = q('harmonic');
  const act = ovBranchActive();
  const bv = act ? qb('voltage') : null, bi = act ? qb('current') : null, bp = act ? qb('power') : null,
        bpf = act ? qb('power_factor') : null, bf = act ? qb('fundamental') : null, bh = act ? qb('harmonic') : null;
  // v0.28：多行卡片——每行「标签：总线数据 / 分路数据」（分路侧未启用时只显示总线数据）
  const g = (o, fn) => { try { const x = o ? fn(o) : null; return x === null || x === undefined ? '—' : x; } catch (e) { return '—'; } };
  const row = (lab, busV, brV, unit) => `<tr><td class="l">${lab}</td><td class="v"><span class="bus">${busV}</span>${act ? `<span class="sep"> / </span><span class="br">${brV}</span>` : ''}${unit ? `<span class="u">${unit}</span>` : ''}</td></tr>`;
  const mcard = (title, rows, sub) => `<div class="card ovc"><div class="k">${title}${act ? '<span class="fmt">总线 / 分路</span>' : ''}</div><table class="ovrows">${rows.join('')}</table>${sub ? `<div class="s">${sub}</div>` : ''}</div>`;
  const cards = [];
  if (v || bv) cards.push(mcard('电压（有效值）', PH.map(k => row(`${k} 相`, g(v, o => si(o.values.rms[k], 'V')), g(bv, o => si(o.values.rms[k], 'V'))))));
  if (i || bi) cards.push(mcard('电流（有效值）', PH.map(k => row(`${k} 相`, g(i, o => si(o.values.rms[k], 'A')), g(bi, o => si(o.values.rms[k], 'A')))),
    `零线 ${g(i, o => si(o.values.neutral_rms, 'A'))}` + (act ? ` / ${g(bi, o => si(o.values.neutral_rms, 'A'))}` : '')));
  if (p || bp) {
    const dP = (p && bp && isNum(p.values.p_total) && isNum(bp.values.p_total)) ? p.values.p_total - bp.values.p_total : null;
    const rP = (dP !== null && Math.abs(p.values.p_total) > 1e-9) ? bp.values.p_total / p.values.p_total * 100 : null;
    const pq = (title, key, tot, unit, sub) => mcard(title, [
      ...PH.map(k => row(`${k} 相`, g(p, o => si(o.values[key][k], unit)), g(bp, o => si(o.values[key][k], unit)))),
      row('总', g(p, o => si(o.values[tot], unit)), g(bp, o => si(o.values[tot], unit)))], sub);
    cards.push(pq('有功 P', 'p_per_phase', 'p_total', 'W', dP === null ? '' : `总线−分路 ${si(dP, 'W')}${rP === null ? '' : '　分路占 ' + num(rP, 2) + ' %'}（最新值）`));
    cards.push(pq('无功 Q', 'q_per_phase', 'q_total', 'var', g(p, o => o.values.quadrant ? o.values.quadrant.q_sign : '')));
    cards.push(pq('视在 S', 's_per_phase', 's_total', 'VA', g(p, o => o.values.modes ? o.values.modes.apparent_note : '')));
  }
  if (pf || bpf) cards.push(mcard('功率因数 PF', [
    ...PH.map(k => row(`${k} 相`, g(pf, o => num(o.values.pf_per_phase[k], 4)), g(bpf, o => num(o.values.pf_per_phase[k], 4)))),
    row('总', g(pf, o => num(o.values.pf_total, 4)), g(bpf, o => num(o.values.pf_total, 4)))],
    `DPF ${g(pf, o => num(o.values.dpf, 4))}` + (act ? ` / ${g(bpf, o => num(o.values.dpf, 4))}` : '')));
  if (f || bf) cards.push(mcard('频率', [row('f', g(f, o => num(o.values.freq_hz, 3)), g(bf, o => num(o.values.freq_hz, 3)), 'Hz')],
    g(f, o => `${o.values.phase_sequence || ''} · 来源 ${o.values.freq_source}`)));
  if (h || bh) {
    cards.push(mcard('THD_U（最劣相）', [row('THD_U', g(h, o => num(o.values.thd_u_worst_pct, 2)), g(bh, o => num(o.values.thd_u_worst_pct, 2)), '%')],
      `最劣相 ${g(h, o => o.values.worst_phase_u || '—')}` + (act ? ` / ${g(bh, o => o.values.worst_phase_u || '—')}` : '')));
    cards.push(mcard('THD_I（最劣相）', [row('THD_I', g(h, o => num(o.values.thd_i_worst_pct, 2)), g(bh, o => num(o.values.thd_i_worst_pct, 2)), '%')],
      `最劣相 ${g(h, o => o.values.worst_phase_i || '—')}` + (act ? ` / ${g(bh, o => o.values.worst_phase_i || '—')}` : '')));
  }
  if (!cards.length) cards.push(card('状态', '尚无结果', '', '请到「数据源与控制」启动数据源'));
  const hint = $('#ov-br-hint');
  if (hint) {
    const br = (S.state || {}).branch || {}, st = S.state || {};
    const busTxt = st.running ? '播放中' : st.finished ? '已播放完毕（数据停在终值）' : '未启动';
    hint.textContent = act ? `　· 总线侧 ${busTxt}　· 分路侧 ${br.running ? '播放中' : br.finished ? '已播放完毕（数据停在终值）' : sideStatusText(br)}，样本 ${br.samples_in || 0}` : '';
  }
  $('#ov-cards').innerHTML = cards.join('');
  renderOverviewSides();

  const hv = S.histCache.voltage || [], hi = S.histCache.current || [], hp = S.histCache.power || [], hh = S.histCache.harmonic || [];
  const tref = (arr) => arr.length ? arr[0].t : 0;
  // 分路侧曲线（虚线）叠加到同一张图
  // v0.15.2：总线侧与分路侧曲线**分开**画（左列总线、右列分路），各用各的时间轴，不再叠在同一坐标系里
  const bhv = act ? (OVB.hist.voltage || []) : [], bhi = act ? (OVB.hist.current || []) : [], bhp = act ? (OVB.hist.power || []) : [], bhh = act ? (OVB.hist.harmonic || []) : [];
  const grid = $('#ov-curves');
  if (grid) grid.classList.toggle('no-branch', !act);
  const br = (S.state || {}).branch || {};
  const brNote = !act ? '' : br.paused ? '已暂停' : br.running ? '播放中' : br.finished ? '已播放完毕（数据停在终值）' : (br.error ? '错误' : '未启动');
  document.querySelectorAll('#ov-curves .ov-br-note').forEach(el => { el.textContent = brNote; });
  const t0u = tref(hv), t0i = tref(hi), t0p = tref(hp), t0h = tref(hh);
  drawLine($('#ov-u'), [{ name: 'Ua', color: COLORS.A, data: hv.map(p => [p.t - t0u, p.Ua]) },
                        { name: 'Ub', color: COLORS.B, data: hv.map(p => [p.t - t0u, p.Ub]) },
                        { name: 'Uc', color: COLORS.C, data: hv.map(p => [p.t - t0u, p.Uc]) }],
           { ylabel: 'V', fmtX: x => tsX(x + t0u, spanOf('voltage')), fmtTip: x => ts(x + t0u), tbase: t0u, empty: '暂无电压趋势（需累计 ≥2 个窗）' });
  drawLine($('#ov-i'), [{ name: 'Ia', color: COLORS.A, data: hi.map(p => [p.t - t0i, p.Ia]) },
                        { name: 'Ib', color: COLORS.B, data: hi.map(p => [p.t - t0i, p.Ib]) },
                        { name: 'Ic', color: COLORS.C, data: hi.map(p => [p.t - t0i, p.Ic]) }],
           { ylabel: 'A', fmtX: x => tsX(x + t0i, spanOf('current')), fmtTip: x => ts(x + t0i), tbase: t0i });
  drawLine($('#ov-p'), pqsSeries(hp, t0p),
           { ylabel: 'W/var/VA', fmtX: x => tsX(x + t0p, spanOf('power')), fmtTip: x => ts(x + t0p), tbase: t0p });
  drawLine($('#ov-thd'), [{ name: 'THD_U', color: COLORS.A, data: hh.map(p => [p.t - t0h, p.THD_U]) },
                          { name: 'THD_I', color: COLORS.C, data: hh.map(p => [p.t - t0h, p.THD_I]) }],
           { ylabel: '%', fmtX: x => tsX(x + t0h, spanOf('harmonic')), fmtTip: x => ts(x + t0h), tbase: t0h, zero: true });
  if (act) {
    const brEmpty = br.running ? '分路侧暂无趋势（等待计算结果…）' : '分路侧暂无数据（启动数据源后显示）';
    const b0u = tref(bhv), b0i = tref(bhi), b0p = tref(bhp), b0h = tref(bhh);
    const bspan = (pts) => pts.length > 1 ? pts[pts.length - 1].t - pts[0].t : 0;
    drawLine($('#ov-u-br'), [{ name: 'Ua', color: COLORS.A, data: bhv.map(p => [p.t - b0u, p.Ua]) },
                             { name: 'Ub', color: COLORS.B, data: bhv.map(p => [p.t - b0u, p.Ub]) },
                             { name: 'Uc', color: COLORS.C, data: bhv.map(p => [p.t - b0u, p.Uc]) }],
             { ylabel: 'V', fmtX: x => tsX(x + b0u, bspan(bhv)), fmtTip: x => ts(x + b0u), tbase: b0u, empty: brEmpty });
    drawLine($('#ov-i-br'), [{ name: 'Ia', color: COLORS.A, data: bhi.map(p => [p.t - b0i, p.Ia]) },
                             { name: 'Ib', color: COLORS.B, data: bhi.map(p => [p.t - b0i, p.Ib]) },
                             { name: 'Ic', color: COLORS.C, data: bhi.map(p => [p.t - b0i, p.Ic]) }],
             { ylabel: 'A', fmtX: x => tsX(x + b0i, bspan(bhi)), fmtTip: x => ts(x + b0i), tbase: b0i, empty: brEmpty });
    drawLine($('#ov-p-br'), pqsSeries(bhp, b0p),
             { ylabel: 'W/var/VA', fmtX: x => tsX(x + b0p, bspan(bhp)), fmtTip: x => ts(x + b0p), tbase: b0p, empty: brEmpty });
    drawLine($('#ov-thd-br'), [{ name: 'THD_U', color: COLORS.A, data: bhh.map(p => [p.t - b0h, p.THD_U]) },
                               { name: 'THD_I', color: COLORS.C, data: bhh.map(p => [p.t - b0h, p.THD_I]) }],
             { ylabel: '%', fmtX: x => tsX(x + b0h, bspan(bhh)), fmtTip: x => ts(x + b0h), tbase: b0h, zero: true, empty: brEmpty });
  }
  renderCurveSave();
  refreshOverviewBranch(false);
  const hn = $('#ov-histnote');
  if (hn) {
    const hrs = ((((S.state || {}).config || {}).output || {}).history_hours) || 24;
    const ovn = act ? '总线侧与分路侧曲线分列显示（左总线、右分路），各用各的时间轴；两侧按时标对齐与差值见「跨侧对比」页。' : '';
    hn.innerHTML = notes([...(ovn ? [ovn] : []), `趋势曲线显示<b>最近 ${hrs} 小时</b>的数据（按数据时间计；不足 ${hrs} 小时则显示全部）。` +
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
  const sc = unitScale(PH.flatMap(k => [(pc[k] || {}).mean, (pc[k] || {}).max, (pc[k] || {}).min]), unit);
  return table(['相', '周期数', sc.hdr('均值'), sc.hdr('最大'), sc.hdr('最小'), sc.hdr('标准差'), '丢弃点'],
    PH.map(k => {
      const s = pc[k] || {};
      return [k, num(s.n_cycles, 0), sc.f(s.mean), sc.f(s.max), sc.f(s.min), sc.f(s.std), num(s.n_dropped, 0)];
    }));
}

function seqTable(s, unit) {
  if (!s) return '<div class="notes">无序分量数据</div>';
  const sc = unitScale([s.U1, s.U2, s.U0], unit);
  const X = unit === 'V' ? 'U' : 'I';
  return table(['分量', sc.hdr('幅值'), '相角 (°)', '占正序比 (%)', '说明'], [
    [`正序 ${X}1`, sc.f(s.U1), num(s.U1_angle_deg, 2), '100', '对称分量法（基波相量）'],
    [`负序 ${X}2`, sc.f(s.U2), num(s.U2_angle_deg, 2), num(s.negative_seq_pct, 3), '不平衡度'],
    [`零序 ${X}0`, sc.f(s.U0), '—', num(s.zero_seq_pct, 3), '零序含量'],
  ]);
}

/* ------------------------------------------------------------------ v0.71：实时监测（三相电压 / 三相电流 / P·Q·S）子界面的
 * 趋势图 + 周波窗（有效值）+ 周波窗（瞬时值）——曲线功能、右键菜单与风格与负荷辨识事件页一致：
 *   趋势图：history 曲线（同总览；v0.76 起不画负荷辨识事件竖线）；右键：复制 / 保存 / 打开图片、显示周波窗（有效值）、显示周波窗（瞬时值）、复位缩放
 *   周波窗（有效值）：/api/elec/cycles_file（以该时刻为中心 N 个周波的逐周波 Urms / Irms / P·Q·S，从本侧离线文件读取；也可手动装载）
 *   周波窗（瞬时值）：/api/nilm/wave_file（同一段的采样瞬时值；功率页由 u·i 算 p(t)）
 * 两个周波窗都只来自本侧配置的离线文件（csv_file）；实时源下菜单项灰显（同 v0.66 规则）。 */
const EW_DEF = {
  voltage: { pre: 'v', hist: 'voltage', chans: ['Ua', 'Ub', 'Uc'], unit: 'V', label: '三相电压' },
  current: { pre: 'i', hist: 'current', chans: ['Ia', 'Ib', 'Ic'], unit: 'A', label: '三相电流' },
  power:   { pre: 'p', hist: 'power',   chans: ['Ua', 'Ub', 'Uc', 'Ia', 'Ib', 'Ic'], unit: 'W', label: 'P / Q / S' },
};
function EWs(side, key) { return SD[side || sideOf()].ew[key]; }
function ewIsFile(side) { const stx = (side === 'branch' ? BRD.state : S.state) || {}; return (((stx.config || {}).source || {}).kind || '') === 'csv_file'; }
function ewSrcKind(side) { const stx = (side === 'branch' ? BRD.state : S.state) || {}; return ((stx.config || {}).source || {}).kind || ''; }
function ewN(side, pre) { const el = E(side, pre + '-win-count'); return Math.max(1, Math.min(20000, parseInt((el && el.value) || '300', 10) || 300)); }
function ewTrendSeries(key, h, t0) {
  if (key === 'power') return pqsSeries(h, t0);
  const f = key === 'voltage' ? 'U' : 'I';
  return ['A', 'B', 'C'].map(ph => ({ name: f + ph.toLowerCase(), color: COLORS[ph], data: h.map(pt => [pt.t - t0, pt[f + ph.toLowerCase()]]) }));
}
function ewEventMarks(side, t0, tEnd) {
  const evs = (NLs(side).events || []).filter(e => isNum(e.t_start) && e.t_start >= t0 && e.t_start <= tEnd);
  return evs.map(e => ({ x: e.t_start - t0, color: NILM_COLORS[e.algorithm], row: Object.keys(NILM_ALGOS).indexOf(e.algorithm),
                         label: `${e.direction === 'up' ? '↑' : '↓'}${si(nilmMag(e), e.unit || 'W', 3)} ${e.channel}` }));
}
async function ewLoadCycles(side, key, tEpoch, nCycles) {
  const d0 = EW_DEF[key], st = EWs(side, key);
  const tEl = E(side, d0.pre + '-win-t');
  let tTxt = (tEpoch !== undefined && tEpoch !== null) ? String(tEpoch) : ((tEl && tEl.value) || '').trim();
  const n = Math.max(1, Math.min(20000, parseInt(String(nCycles !== undefined && nCycles !== null ? nCycles : ewN(side, d0.pre)), 10) || 300));
  if (tEpoch !== undefined && tEpoch !== null && tEl) tEl.value = fmtLocalInput(tEpoch);
  try {
    const d = await api(`/api/elec/cycles_file?n=${n}${tTxt ? '&t=' + encodeURIComponent(tTxt) : ''}`, undefined, side);
    st.cyc = d;
    const sname = (d.source && d.source.path) ? d.source.path.split(/[\\/]/).pop() : '';
    toast(`${side === 'branch' ? '分路侧' : '总线侧'}${d0.label}周波窗（有效值）已装载 ${d.n_cycles} 个周波（${sname}${d.source.mode === 'center' ? '，中心 ' + fmtLocalInput(d.source.t_center) : '，数据起点起'}）`, 'ok');
    if (S.view === key) render();
    return true;
  } catch (e) { toast('装载周波窗（有效值）失败：' + e.message, 'err'); return false; }
}
async function ewLoadWave(side, key, tEpoch, nCycles) {
  const d0 = EW_DEF[key], st = EWs(side, key);
  const n = Math.max(1, Math.min(20000, parseInt(String(nCycles || ewN(side, d0.pre)), 10) || 300));
  try {
    const d = await api(`/api/nilm/wave_file?n=${n}&channels=${d0.chans.join(',')}${isNum(tEpoch) ? '&t=' + encodeURIComponent(String(tEpoch)) : ''}`, undefined, side);
    d.cyc_center = tEpoch; d.cyc_n = n; st.wave = d;
    const sname = (d.source && d.source.path) ? d.source.path.split(/[\\/]/).pop() : '';
    toast(`${side === 'branch' ? '分路侧' : '总线侧'}${d0.label}周波窗（瞬时值）已装载 ${d.n} 点 × ${(d.channels_loaded || []).length} 通道（${sname}${isNum(tEpoch) ? '，中心 ' + fmtLocalInput(tEpoch) : '，数据起点起'}，${n} 个周波）`, 'ok');
    if (S.view === key) { render(); try { E(side, d0.pre + '-wave2').scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } catch (e) { /* jsdom */ } }
    return true;
  } catch (e) { toast('装载周波窗（瞬时值）失败：' + e.message, 'err'); return false; }
}
function ewCtxItems(cv, side, key) {
  return (xEpoch) => {
    const d0 = EW_DEF[key]; const n = ewN(side, d0.pre); const noX = !isNum(xEpoch);
    const isFile = ewIsFile(side), srcKind = ewSrcKind(side);
    const why = !isFile ? `当前输入方式为 ${srcKind || '—'}：周波窗只能从离线文件（csv_file）读取，实时源不可用` : noX ? '趋势曲线有数据后，在曲线上右键' : '';
    return canvasNativeItems(cv).concat([                   // 原生三项在前（与负荷辨识页一致），业务项追加在后
      { key: 'sep', sep: true },
      { key: 'show-window', label: `显示周波窗（有效值，${noX ? '暂无曲线' : fmtLocalInput(xEpoch)}）`, disabled: noX || !isFile,
        hint: why || `以该时刻为中心从本侧离线文件读取 ${n} 个周波的逐周波有效值，显示在下方「周波窗（有效值）」`,
        onClick: () => ewLoadCycles(side, key, xEpoch, n) },
      { key: 'show-window2', label: `显示周波窗（瞬时值，${noX ? '暂无曲线' : fmtLocalInput(xEpoch)}）`, disabled: noX || !isFile,
        hint: why || `以该时刻为中心从本侧离线文件读取 ${n} 个周波的采样瞬时值（${d0.chans.join('/')}），显示在下方「周波窗（瞬时值）」`,
        onClick: () => ewLoadWave(side, key, xEpoch, n) },
      { key: 'zoom-reset', label: '复位缩放', onClick: () => zoomReset(cv) },
      { key: 'native', label: '浏览器原生菜单（Shift + 右键）', disabled: true },
    ]);
  };
}
function ewWinSourceText(st) {
  if (!st.cyc) return '在趋势图上右键「显示周波窗（有效值）」，或填时刻 / 周波数手动装载（留空＝数据起点起）；数据来自本侧配置的离线文件';
  const sr = st.cyc.source || {};
  return `已装载：${(sr.path || '').split(/[\\/]/).pop()} · ${sr.mode === 'center' ? '中心 ' + fmtLocalInput(sr.t_center) : '数据起点起'} · ${sr.n_loaded} 个周波（${ts(sr.t_start)} ~ ${ts(sr.t_end)}）`;
}
function renderElecWindows(key) {
  const d0 = EW_DEF[key], side = sideOf(), st = EWs(side, key), pre = d0.pre;
  // ① 趋势图（同总览 / 负荷辨识趋势；v0.76 起不画负荷辨识事件竖线）
  const cvT = $('#' + pre + '-trend');
  if (cvT) {
    const h = curHist(d0.hist); const t0 = h.length ? h[0].t : 0, tEnd = h.length ? h[h.length - 1].t : 0;
    drawLine(cvT, ewTrendSeries(key, h, t0), { ylabel: key === 'power' ? 'W/var/VA' : d0.unit, fmtX: x => tsX(x + t0, spanOf(d0.hist)), fmtTip: x => ts(x + t0), tbase: t0, height: 260,
                                               empty: `暂无${d0.label}趋势（需累计 ≥2 个 ${d0.hist} 窗）` });   // v0.76：电气量页三曲线不再画负荷辨识事件竖线
    bindCtxMenu(cvT, ewCtxItems(cvT, side, key));
  }
  // ② 周波窗（有效值）
  const cvC = $('#' + pre + '-cyc');
  const isFile = ewIsFile(side);
  [`btn-${pre}-win-load`, `${pre}-win-t`, `${pre}-win-count`].forEach(id => { const el = $('#' + id); if (el) el.disabled = !isFile; });
  { const el = $(`#btn-${pre}-win-clear`); if (el) el.disabled = !st.cyc && !st.wave; }
  { const el = $('#' + pre + '-win-src'); if (el) el.textContent = isFile ? ewWinSourceText(st) : `当前输入方式为 ${ewSrcKind(side) || '—'}：周波窗只能从离线文件（csv_file）读取`; }
  if (cvC) {
    const c = st.cyc; const sub = $('#' + pre + '-cyc-sub');
    if (!c || !c.t || !c.t.length) {
      drawLine(cvC, [], { height: 240, empty: '在趋势图上右键「显示周波窗（有效值）」或用上方「装载周波窗」后显示（以该时刻为中心 N 个周波的逐周波有效值，从本侧离线文件读取）' });
      if (sub) sub.textContent = '';                                         // v0.76：标题只留数据说明，操作提示在曲线空态里
    } else {
      const t0 = c.t[0]; let ser = [], ylabel = d0.unit;
      if (key === 'power') {
        const chSel = $('#p-cyc-ch'); const ch = (chSel && chSel.value) || 'total'; const lab = ch === 'total' ? '三相总' : ch + ' 相';
        ser = ['P', 'Q', 'S'].filter(k => Array.isArray((c[k] || {})[ch])).map(k => ({ name: `${k}（${lab}，逐周波）`, color: COLORS[k], data: c.t.map((x, i) => [x - t0, c[k][ch][i]]) }));
        ylabel = 'W/var/VA';
      } else {
        const f = key === 'voltage' ? 'U' : 'I';
        ser = ['A', 'B', 'C'].filter(ph => Array.isArray((c[f] || {})[ph])).map(ph => ({ name: `${f}${ph.toLowerCase()}（逐周波有效值）`, color: COLORS[ph], data: c.t.map((x, i) => [x - t0, c[f][ph][i]]) }));
      }
      drawLine(cvC, ser, { ylabel, fmtX: x => ts(x + t0), fmtTip: x => fmtLocalInput(x + t0), tbase: t0, height: 240, legend: true,
                           empty: key === 'power' ? '该文件没有电压通道，算不出 P / Q / S' : `该文件没有${d0.label}通道` });
      if (sub) sub.textContent = `（${c.n_cycles} 个周波 × ${ser.length} 条 · 每周波 ${c.n_cycle_samples} 点 · ${fmtLocalInput(t0)} → ${fmtLocalInput(c.t[c.t.length - 1])}` + (c.source && c.source.mode === 'center' ? `，中心 ${fmtLocalInput(c.source.t_center)}` : '') + ` · ${(c.source || {}).path || ''}）`;
      bindCtxMenu(cvC, () => canvasNativeItems(cvC).concat([{ key: 'sep', sep: true }, { key: 'zoom-reset', label: '复位缩放', onClick: () => zoomReset(cvC) }, { key: 'native', label: '浏览器原生菜单（Shift + 右键）', disabled: true }]));
    }
  }
  // ③ 周波窗（瞬时值）
  const cvW = $('#' + pre + '-wave2');
  if (cvW) {
    const d = st.wave; const sub = $('#' + pre + '-wave2-sub');
    if (!d || !d.t || !d.t.length) {
      drawLine(cvW, [], { height: 240, empty: '在趋势图上右键「显示周波窗（瞬时值）」后显示（以该时刻为中心 N 个周波的采样瞬时值，从本侧离线文件读取）' });
      if (sub) sub.textContent = '';
    } else {
      const t0 = d.t[0]; const chans = d.channels_loaded || Object.keys(d.channels || {}); let ser = [], ylabel = d0.unit;
      if (key === 'power') {
        const ph = ['a', 'b', 'c'].filter(k => d.channels['U' + k] && d.channels['I' + k]);
        const pph = ph.map(k => d.channels['U' + k].map((u, i) => (u === null || d.channels['I' + k][i] === null) ? null : u * d.channels['I' + k][i]));
        if (pph.length) ser.push({ name: 'p(t) 总瞬时功率', color: COLORS.P, data: d.t.map((x, i) => [x - t0, pph.reduce((a, arr) => a + (arr[i] === null ? 0 : arr[i]), 0)]) });
        ph.forEach((k, j) => ser.push({ name: `p${k.toUpperCase()}(t) ${k.toUpperCase()} 相`, color: COLORS[k.toUpperCase()], width: 1.3, defaultHidden: true, data: d.t.map((x, i) => [x - t0, pph[j][i]]) }));
      } else {
        ser = chans.map(ch => ({ name: `${ch} (${(d.units || {})[ch] || ''})`, color: WP_COLORS[ch] || COLORS[ch.slice(-1).toUpperCase()] || '#4ea1ff', data: d.t.map((x, i) => [x - t0, d.channels[ch][i]]) }));
      }
      drawLine(cvW, ser, { ylabel, fmtX: x => ts(x + t0), fmtTip: x => fmtLocalInput(x + t0), tbase: t0, height: 240, zero: true, legend: key === 'power',
                           empty: key === 'power' ? '该文件没有电压 + 电流通道，算不出 p(t)' : `该文件没有${d0.label}通道` });
      if (sub) sub.textContent = `（${d.n} 点 × ${chans.length} 通道 · ${d.fs} Hz · ${fmtLocalInput(t0)} → ${fmtLocalInput(d.t[d.t.length - 1])}` + (isNum(d.cyc_center) ? `，中心 ${fmtLocalInput(d.cyc_center)}` : '') + `，${d.cyc_n} 个周波 · 采样瞬时值 · ${(d.source || {}).path || ''}）`;
      bindCtxMenu(cvW, () => canvasNativeItems(cvW).concat([{ key: 'sep', sep: true }, { key: 'zoom-reset', label: '复位缩放', onClick: () => zoomReset(cvW) }, { key: 'native', label: '浏览器原生菜单（Shift + 右键）', disabled: true }]));
    }
  }
}
function bindElecWindows(side) {
  const on = (id, ev, fn) => { const el = E(side, id); if (el) el.addEventListener(ev, fn); };
  Object.keys(EW_DEF).forEach(key => {
    const pre = EW_DEF[key].pre;
    on('btn-' + pre + '-win-load', 'click', () => ewLoadCycles(side, key));
    on('btn-' + pre + '-win-clear', 'click', () => { const st = EWs(side, key); st.cyc = null; st.wave = null; render(); });
    on('btn-' + pre + '-wave2-clear', 'click', () => { EWs(side, key).wave = null; render(); });
    on(pre + '-win-t', 'keydown', (e) => { if (e.key === 'Enter') ewLoadCycles(side, key); });
  });
  on('p-cyc-ch', 'change', render);
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
  $('#v-seq').innerHTML = v ? seqTable(v.values.sequence, 'V') + (() => { const sc = unitScale(PH.map(k => v.values.fundamental_rms[k]), 'V'); return table(['相', sc.hdr('基波有效值')], PH.map(k => [k, sc.f(v.values.fundamental_rms[k])])); })() : '';
  $('#v-win').innerHTML = winNotes('voltage');
  renderElecWindows('voltage');
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
  $('#i-seq').innerHTML = i ? seqTable(i.values.sequence, 'A') + (() => { const sc = unitScale(PH.map(k => i.values.fundamental_rms[k]), 'A'); return table(['相', sc.hdr('基波有效值'), '波峰系数'],
    PH.map(k => [k, sc.f(i.values.fundamental_rms[k]), num(i.values.crest_factor[k], 3)])); })() : '';
  $('#i-win').innerHTML = winNotes('current');
  renderElecWindows('current');
}

/* v0.76：「有功 / 无功 / 视在功率瞬时波形」——原「瞬时功率波形」+「分相瞬时功率波形」合并为一张图，
   图例复选框（同趋势图）选 总 / A / B / C 相 × P / Q / S。p=u·i；q=u(t−T/4)·i（服务端 series.q_*）；s=√(p²+q²) */
const PW_STYLE = { P: { unit: 'W' }, Q: { unit: 'var' }, S: { unit: 'VA' } };
function renderPowerWave(p) {
  const cv = $('#p-wave'); if (!cv) return;
  const sr = (p && p.series) || {};
  const fsP = ((curState().config || {}).sampling || {}).fs || 6400, stP = sr.stride || 1;
  // v0.78：12 条全部交给 drawLine，用与趋势图一致的图例复选框选曲线（总 P/Q/S 默认显示，分相默认隐藏；勾选状态随 output.series_hidden 保存）
  const ser = [];
  ['total', 'A', 'B', 'C'].forEach(ph => ['P', 'Q', 'S'].forEach(k => {
    const arr = ph === 'total' ? sr[k.toLowerCase() + '_total'] : ((sr[k.toLowerCase() + '_per_phase'] || {})[ph]);
    if (!Array.isArray(arr) || !arr.length) return;
    // v0.79：图例名称 / 颜色与「P / Q / S 趋势」完全一致：P Q S（总）、Pa Pb Pc Qa … Sc（分相，同色系深浅）
    ser.push({ name: ph === 'total' ? k : k + ph.toLowerCase(), unit: PW_STYLE[k].unit,
               color: ph === 'total' ? COLORS[k] : shadeColor(COLORS[k], PQS_PHASE_SHADE[ph]), width: ph === 'total' ? 1.8 : 1.3,
               defaultHidden: ph !== 'total', data: arr.map((v2, j) => [j * stP / fsP, v2]) });
  }));
  drawLine(cv, ser, { ylabel: 'W/var/VA', zero: true, fmtX: x => x.toFixed(3) + 's', height: 240, legend: true,
                      empty: sr.q_total ? '暂无瞬时功率波形（请先启动数据源）' : '暂无瞬时功率波形（无功 / 视在瞬时波形需服务端 v0.76+ 结果）' });
  const sub = $('#p-wave-sub');
  if (sub) sub.textContent = ser.length ? `（${ser.length} 条可选 · ${(sr.p_total || []).length} 点 · 抽稀 ${stP}:1 · q(t) 电压滞后 ${sr.q_lag_samples || 0} 点＝T/4）` : '';
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
    // v0.79：分相实时数据卡片（每相一张：P 为主值，Q / S / PF 在副行）
    PH.forEach(k => cards.push(card(`${k} 相 P / Q / S`, si((v.p_per_phase || {})[k], 'W'), '',
      `Q ${si((v.q_per_phase || {})[k], 'var')} · S ${si((v.s_per_phase || {})[k], 'VA')} · PF ${num((v.pf_per_phase || {})[k], 3)}`)));
  }
  $('#p-cards').innerHTML = cards.join('') || card('状态', '尚无结果', '', '请先启动数据源');
  renderPowerWave(p);
  $('#p-phase').innerHTML = p ? (() => {
    const pv = p.values, col = (o, u) => unitScale(PH.map(k => (o || {})[k]), u);
    const sP = col(pv.p_per_phase, 'W'), sQ = col(pv.q_per_phase, 'var'), sS = col(pv.s_per_phase, 'VA'), sU = col(pv.u_rms, 'V'), sI = col(pv.i_rms, 'A');
    return table(['相', sP.hdr('P'), sQ.hdr('Q'), sS.hdr('S'), 'PF', sU.hdr('U'), sI.hdr('I')],
      PH.map(k => [k, sP.f(pv.p_per_phase[k]), sQ.f(pv.q_per_phase[k]), sS.f(pv.s_per_phase[k]), num(pv.pf_per_phase[k], 4), sU.f(pv.u_rms[k]), sI.f(pv.i_rms[k])]));
  })() : '';
  $('#p-fund').innerHTML = p && p.values.fundamental && p.values.fundamental.enabled ? (() => {
    const fd = p.values.fundamental;
    // 行标题带单位（每行一个量），单元格只放数字；同一行共用一个前缀
    const row = (name, unit, per, total) => { const sc = unitScale([...PH.map(k => per[k]), total], unit); return [`${name} (${sc.u})`, ...PH.map(k => sc.f(per[k])), total === undefined ? '—' : sc.f(total)]; };
    return table(['项目 (单位)', 'A 相', 'B 相', 'C 相', '合计'], [
      row('基波有功 P1', 'W', fd.p1_per_phase, fd.p1_total),
      row('基波无功 Q1', 'var', fd.q1_per_phase, fd.q1_total),
      row('基波视在 S1', 'VA', fd.s1_per_phase, fd.s1_total),
      row('基波电压 U1', 'V', fd.u1_rms),
      row('基波电流 I1', 'A', fd.i1_rms),
      ['位移因数 DPF', '—', '—', '—', num(fd.dpf, 4)],
      ['φ1 (°)', '—', '—', '—', num(fd.phi1_deg, 2)],
    ]) + notes(p.values.notes);
  })() : '';
  $('#p-win').innerHTML = winNotes('power');
  renderElecWindows('power');
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
  const hp = curHist('power_factor');
  const t0 = hp.length ? hp[0].t : 0;
  // v0.27：分相 PFa/PFb/PFc 默认隐藏，图例勾选显示
  drawLine($('#pf-trend'), [{ name: 'PF', color: COLORS.P, data: hp.map(x => [x.t - t0, x.PF]) },
                            { name: 'DPF', color: COLORS.B, data: hp.map(x => [x.t - t0, x.DPF]) },
                            ...PH.map(ph => ({ name: 'PF' + ph.toLowerCase(), color: shadeColor(COLORS.P, PQS_PHASE_SHADE[ph]), width: 1.3, defaultHidden: true, data: hp.map(x => [x.t - t0, x['PF' + ph.toLowerCase()]]) }))],
           { ylabel: '', fmtX: x => tsX(x + t0, spanOf('power_factor')), fmtTip: x => ts(x + t0), tbase: t0, height: 220 });
  renderCurveSave();
  drawQuadrant($('#pf-quad'), p ? p.values.p_total : NaN, p ? p.values.q_total : NaN);
  $('#pf-quadtxt').innerHTML = p && p.values.quadrant ? notes([`${p.values.quadrant.name}：${p.values.quadrant.meaning}`]) : '';
  $('#pf-phase').innerHTML = pf ? table(['相', 'PF', '说明'], PH.map(k => [k, num(pf.values.pf_per_phase[k], 4), '分相 P/S'])) : '';
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
  $('#f-phasor').innerHTML = f ? (() => {
    const sU = unitScale(PH.map(k => f.values.u1_rms[k]), 'V'), sI = unitScale(PH.map(k => f.values.i1_rms[k]), 'A');
    return table(['相', sU.hdr('U1'), '∠U1 (°)', sI.hdr('I1'), '∠I1 (°)', 'φ=∠U−∠I (°)'],
      PH.map(k => [k, sU.f(f.values.u1_rms[k]), num(f.values.u1_angle_deg[k], 2), sI.f(f.values.i1_rms[k]), num(f.values.i1_angle_deg[k], 2), num(f.values.phi_deg[k], 2)]));
  })() : '';
  $('#f-seq').innerHTML = f ? `<h3 style="margin-top:6px">电压序分量</h3>${seqTable(f.values.u_sequence, 'V')}<h3 style="margin-top:10px">电流序分量</h3>${seqTable(f.values.i_sequence, 'A')}` : '';
  const hf = curHist('fundamental');
  const t0 = hf.length ? hf[0].t : 0;
  drawLine($('#f-trend'), [{ name: '频率 (Hz)', color: COLORS.A, data: hf.map(x => [x.t - t0, x.f]) }],
           { ylabel: 'Hz', fmtX: x => tsX(x + t0, spanOf('fundamental')), fmtTip: x => ts(x + t0), tbase: t0, height: 200 });
  // v0.28：基波有效值分相趋势（总量默认显示，分相默认隐藏、图例勾选）
  const phSer = (tot, pre, unit) => [{ name: `${tot} 三相`, color: COLORS.P, data: hf.map(x => [x.t - t0, x[tot]]) },
    ...PH.map(k => ({ name: `${pre}${k.toLowerCase()}`, color: COLORS[k], width: 1.3, defaultHidden: true, data: hf.map(x => [x.t - t0, x[`${pre}${k.toLowerCase()}`]]) }))];
  drawLine($('#f-u1-trend'), phSer('U1', 'U1', 'V'), { ylabel: 'V', fmtX: x => tsX(x + t0, spanOf('fundamental')), fmtTip: x => ts(x + t0), tbase: t0, height: 200, legend: true });
  drawLine($('#f-i1-trend'), phSer('I1', 'I1', 'A'), { ylabel: 'A', fmtX: x => tsX(x + t0, spanOf('fundamental')), fmtTip: x => ts(x + t0), tbase: t0, height: 200, legend: true });
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
    const modeU = radioVal('hmode-u', 'hr');
    const modeI = radioVal('hmode-i', 'hr');
    const srcU = modeU === 'hr' ? h.series.hr_u_pct : h.series.rms_u;
    const srcI = modeI === 'hr' ? h.series.hr_i_pct : h.series.rms_i;
    drawBars($('#h-bar-u'), orders, PH.map(k => ({ name: k + ' 相', color: COLORS[k], data: srcU[k] || [] })),
             { xlabel: '谐波次数', ylabel: modeU === 'hr' ? '含有率 %' : '幅值 V', height: 230 });
    drawBars($('#h-bar-i'), orders, PH.map(k => ({ name: k + ' 相', color: COLORS[k], data: srcI[k] || [] })),
             { xlabel: '谐波次数', ylabel: modeI === 'hr' ? '含有率 %' : '幅值 A', height: 230 });
    const sU = unitScale(PH.flatMap(k => h.series.rms_u[k] || []), 'V'), sI = unitScale(PH.flatMap(k => h.series.rms_i[k] || []), 'A');
    const rowsU = orders.map((o, idx) => [o, ...PH.map(k => sU.f((h.series.rms_u[k] || [])[idx])),
                                          ...PH.map(k => num((h.series.hr_u_pct[k] || [])[idx], 3))]);
    $('#h-table-u').innerHTML = table(['次数', sU.hdr('UA'), sU.hdr('UB'), sU.hdr('UC'), 'HR A (%)', 'HR B (%)', 'HR C (%)'], rowsU);
    const rowsI = orders.map((o, idx) => [o, ...PH.map(k => sI.f((h.series.rms_i[k] || [])[idx])),
                                          ...PH.map(k => num((h.series.hr_i_pct[k] || [])[idx], 3))]);
    $('#h-table-i').innerHTML = table(['次数', sI.hdr('IA'), sI.hdr('IB'), sI.hdr('IC'), 'HR A (%)', 'HR B (%)', 'HR C (%)'], rowsI);
  }
  // v0.28：THD 趋势（最劣相 THD_U/THD_I 默认显示；分相 THD_Ua..Ic 默认隐藏、图例勾选）
  const hh = curHist('harmonic'); const t0h = hh.length ? hh[0].t : 0;
  drawLine($('#h-trend'), [{ name: 'THD_U 最劣相 (%)', color: COLORS.P, data: hh.map(x => [x.t - t0h, x.THD_U]) },
                           { name: 'THD_I 最劣相 (%)', color: COLORS.B, data: hh.map(x => [x.t - t0h, x.THD_I]) },
                           ...PH.map(k => ({ name: `THD_U${k.toLowerCase()}`, color: COLORS[k], width: 1.3, defaultHidden: true, data: hh.map(x => [x.t - t0h, x[`THD_U${k.toLowerCase()}`]]) })),
                           ...PH.map(k => ({ name: `THD_I${k.toLowerCase()}`, color: shadeColor(COLORS[k], 0.55), width: 1.3, dash: [4, 3], defaultHidden: true, data: hh.map(x => [x.t - t0h, x[`THD_I${k.toLowerCase()}`]]) }))],
           { ylabel: '%', fmtX: x => tsX(x + t0h, spanOf('harmonic')), fmtTip: x => ts(x + t0h), tbase: t0h, height: 220, legend: true });
  renderCurveSave();
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
  const sA = unitScale([pk.amp_rms], ch[0] === 'U' ? 'V' : 'A');
  $('#sp-info').innerHTML = table(['项目', '数值', '单位'], [
    ['主峰频率', num(pk.freq_hz, 3), 'Hz'],
    ['主峰幅值 (RMS)', sA.f(pk.amp_rms), sA.u],
    ['约当次数', num(pk.order_approx, 2), '次'],
    ['频率分辨率', num(sp.values.freq_resolution_hz, 4), 'Hz'],
    ['Nyquist', num(sp.values.nyquist_hz, 0), 'Hz'],
    ['窗函数', sp.values.window_fn, ''],
    ['输出点数', (c.freqs || []).length, '点'],
  ]);
  $('#sp-notes').innerHTML = notes(sp.values.notes);
}

function renderWindows() {
  const cfg = curState().config;
  if (!cfg) { $('#w-table').innerHTML = ''; return; }
  const rows = Object.keys(cfg.windows).map(k => {
    const w = cfg.windows[k];
    const fft = ['fundamental', 'harmonic', 'interharmonic', 'dc', 'spectrum'].includes(k);
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
  const emits = (curState().engine || {}).emits || {};
  $('#w-emits').innerHTML = table(['电气量', '窗长 (s)', '步长 (s)', '本次运行输出次数'],
    Object.keys(cfg.windows).map(k => [k, num(cfg.windows[k].length_s, 3),
      num(cfg.windows[k].step_s === null ? cfg.windows[k].length_s : cfg.windows[k].step_s, 3), emits[k] || 0]));
}

/* 数据源表单（v0.16 两侧同构）：总线侧 id 前缀 src-，分路侧 br-；字段名相同、功能相同 */
function srcEl(pre, name) { return document.getElementById(pre + name); }
function fillSourceFields(pre, src) {
  if (!src) return;
  const set = (n, v) => { const el = srcEl(pre, n); if (el) el.value = v; };
  const chk = (n, v) => { const el = srcEl(pre, n); if (el) el.checked = !!v; };
  set('kind', src.kind || 'csv_file');
  set('path', src.path || '');
  set('host', src.host || '');
  set('port', src.port || (pre === 'br-' ? 9001 : 9000));
  set('frame', src.frame || 'text_csv');
  set('fmt', src.struct_fmt || '');
  set('fields', src.struct_fields || '');
  set('block', src.block_samples || 640);
  set('speed', src.sim_speed !== undefined ? src.sim_speed : 1);
  // 离线倍速：配置里 0（不限速）是 CLI/批处理默认；界面上默认按 1× 真实速率播放——这才是「播放/暂停」语义
  const chosen = pre === 'src-' ? S.fileSpeedChosen : BR.fileSpeedChosen;
  set('file-speed', String(src.file_speed !== undefined && src.file_speed > 0 ? src.file_speed : (chosen === 0 ? 0 : 1)));
  chk('tailend', src.tail_from_end);
  chk('file-speed-follow', src.file_speed_follow !== false);
  chk('newest', src.watch_dir_newest);
  chk('customtime', src.custom_time);
  chk('utc', src.file_time_utc);
  set('customstart', src.custom_time_start || '');
  set('playmode', src.play_start_mode || 'begin');
  set('playvalue', src.play_start_value || '');
  chk('window', src.play_window);
  set('winstart', src.play_window_start || '');
  set('winend', src.play_window_end || '');
}

function fillSourceForm(cfg) {
  if (cfg.source) fillSourceFields('src-', cfg.source);

  if (cfg.columns) {
    fillColumnsForm('bus', cfg.columns);
    syncColmapForm();
  }
  if (cfg.transform) {
    $('#cfg-pt').value = cfg.transform.pt_ratio;
    $('#cfg-ct').value = cfg.transform.ct_ratio;
    $('#cfg-scale').checked = !!cfg.transform.enabled;
    $('#cfg-inv').checked = !!cfg.transform.invert_current;
    setInvPhases('cfg', cfg.transform.invert_phases); $('#cfg-wiring').value = cfg.transform.wiring || '3p4w'; $('#cfg-recon3w').checked = !!cfg.transform.reconstruct_3w;
    $('#cfg-uin').value = cfg.transform.voltage_input || 'phase';
    ptctSync('cfg-scale', 'cfg-pt', 'cfg-ct'); wiringSync('cfg-wiring', 'cfg-recon3w');   // v0.99.8
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

function syncSourceFields(pre) {
  // 下拉框联动：只启用与当前源相关的字段，其余置灰禁用（填了也不生效＝最坏的用户体验）
  const kindEl = srcEl(pre, 'kind'); if (!kindEl) return;
  const kind = kindEl.value, frame = (srcEl(pre, 'frame') || {}).value;
  const bin = kind === 'tcp' && frame === 'binary';
  const ct = !!(srcEl(pre, 'customtime') || {}).checked;
  const bothFile = pre === 'br-' && kind === 'csv_file' && ($('#src-kind') || {}).value === 'csv_file';
  const followBus = bothFile && !!($('#br-file-speed-follow') || {}).checked;   // v0.85：默认随总线侧，可取消单独设置
  const on = {
    'path': kind === 'csv_file' || kind === 'csv_tail',
    'host': kind === 'tcp',
    'port': kind === 'tcp',
    'frame': kind === 'tcp',
    'fmt': bin,
    'fields': bin,
    'tailend': kind === 'csv_tail',
    'newest': kind === 'csv_tail',
    'customtime': kind === 'csv_file',
    'customstart': kind === 'csv_file' && ct,
    'utc': (kind === 'csv_file' && !ct) || kind === 'csv_tail',
    'playmode': kind === 'csv_file',
    'playvalue': kind === 'csv_file' && (srcEl(pre, 'playmode') || {}).value !== 'begin',
    'speed': kind === 'simulator',
    'window': kind === 'csv_file',
    'winstart': kind === 'csv_file' && !!(srcEl(pre, 'window') || {}).checked,
    'winend': kind === 'csv_file' && !!(srcEl(pre, 'window') || {}).checked,
    'file-speed': kind === 'csv_file' && !followBus,
    'file-speed-follow': bothFile,
    'block': true,
  };
  Object.keys(on).forEach((n) => {
    const el = srcEl(pre, n);
    if (!el) return;
    el.disabled = !on[n];
    const lab = el.closest('label');
    if (lab) lab.classList.toggle('off', !on[n]);
  });
  const hint = srcEl(pre, 'hint');
  if (hint) hint.textContent = SRC_HINT[kind] || '';
  const pv = srcEl(pre, 'playvalue');
  if (pv) pv.placeholder = PLAY_PLACEHOLDER[(srcEl(pre, 'playmode') || {}).value] || '';
  if (pre === 'br-') { const n = $('#br-file-speed-note'); if (n) n.style.display = followBus ? '' : 'none'; }
}

function syncSourceForm() {
  syncSourceFields('src-');
  syncSourceFields('br-');
  syncBranchColumns();
}

/* 分路侧列：只有启用分路侧时才显示右列（需求②）；联动提示按两侧输入方式即时刷新 */
function syncBranchColumns() {
  const en = !!($('#br-enabled') || {}).checked;
  const g = $('#srcgrid'); if (g) g.classList.toggle('no-branch', !en);
  const lf = $('#br-link-fields'); if (lf) lf.style.display = en ? '' : 'none';
  const busKind = ($('#src-kind') || {}).value, brKind = ($('#br-kind') || {}).value;
  const n = $('#br-mode-note'); if (n) n.style.display = (en && (busKind !== 'csv_file' || brKind !== 'csv_file')) ? '' : 'none';
}

/* 分路侧列（v0.16）：开关/公共时间段/对齐 存总线侧 config.branch；数据源/量纲/列映射 存分路侧 /api/branch/config。
   分路侧输入方式与总线侧同样 4 种，字段 id 前缀 br-，与总线侧 src- 一一对应。 */
const BR = { loaded: false, dirty: false, cfg: null, state: null, stateAt: 0, fileSpeedChosen: undefined };
async function loadBranchForm(force) {
  if (BR.loaded && !force) return;
  try {
    const cfg = await (await fetch('/api/branch/config')).json();
    BR.cfg = cfg; BR.loaded = true;
    if (!BR.dirty) {
      fillSourceFields('br-', cfg.source);
      const tr = cfg.transform || {}, sp = cfg.sampling || {}, hm = cfg.harmonic || {}, pw = cfg.power || {};
      $('#br-pt').value = tr.pt_ratio ?? ''; $('#br-ct').value = tr.ct_ratio ?? '';
      $('#br-scale').checked = tr.enabled !== false; $('#br-uin').value = tr.voltage_input || 'phase'; $('#br-inv').checked = !!tr.invert_current;
      setInvPhases('br', tr.invert_phases); $('#br-wiring').value = tr.wiring || '3p4w'; $('#br-recon3w').checked = !!tr.reconstruct_3w;
      ptctSync('br-scale', 'br-pt', 'br-ct'); wiringSync('br-wiring', 'br-recon3w');   // v0.99.8
      $('#br-fs').value = sp.fs ?? ''; $('#br-fnom').value = sp.f_nom ?? ''; $('#br-adaptive').checked = !!sp.adaptive_freq;
      $('#br-hmax').value = hm.order_max ?? '';
      $('#br-apparent').value = pw.apparent || 'arithmetic'; $('#br-reactive').value = pw.reactive || 'harmonic_sum';
      fillColumnsForm('branch', cfg.columns);
      syncColmapForm('branch');
      const bb = (S.state && S.state.config && S.state.config.branch) || {};
      $('#br-toffset').value = bb.time_offset_s ?? 0; $('#br-tol').value = bb.align_tol_s ?? 0;
      $('#br-common').checked = !!bb.common_window; $('#br-common-start').value = bb.common_start || '';
      const hu = $('#br-hide-ui'); if (hu && !BR.dirty) hu.checked = !!bb.hide_ui;
      $('#br-common-end').value = bb.common_end || '';
      syncSourceFields('br-');
    }
  } catch (e) { /* 分路侧不可用 */ }
}
async function refreshBranchState(force) {
  // 分路侧完整 state（数据源状态栏用）：每 ≥2 s 取一次 /api/branch/state；总线侧 state 里只有摘要
  if (!force && Date.now() - BR.stateAt < 2000) return;
  BR.stateAt = Date.now();
  try { BR.state = await (await fetch('/api/branch/state')).json(); } catch (e) { /* ignore */ }
  if (S.view === 'source') renderBranchStatus();
}
function renderBranchPanel(st) {
  const cfg = st.config || {};
  if (!BR.dirty && cfg.branch) $('#br-enabled').checked = !!cfg.branch.enabled;
  if (cfg.branch && $('#br-hide-ui')) $('#br-hide-ui').checked = !!cfg.branch.hide_ui;     // v0.33：独立开关，总随配置回填
  loadBranchForm(false);
  syncBranchColumns();
  renderBranchStatus();
  if ($('#br-enabled').checked) refreshBranchState(false);
}
function sourceSummaryLines(st, cfg, sideName) {
  const e = st.engine || {}, src = st.source || {};
  const emits = e.emits || {};
  return [
    `运行状态：<b>${st.running ? (st.paused ? '已暂停' : '运行中') : (st.finished ? '已结束' : '已停止')}</b>` +
      (st.error ? `　✗ ${esc(st.error)}` : ''),
    `数据源：<b>${esc(src.kind || e.source_kind || '—')}</b>` +
      (src.path ? `　文件 ${esc(src.path)}` : '') +
      (src.endpoint ? `　${esc(src.endpoint)}` : '') +
      (src.kind === 'csv_file' && !src.custom_time && src.tz_offset_h !== undefined ?
        `　时标解释：${src.file_time_utc ? 'UTC（显示换算为本地）' : '与文件一致（本地 UTC' + (src.tz_offset_h >= 0 ? '+' : '') + src.tz_offset_h + '）'}` : '') +
      (src.custom_time ? `　<b>自定义播放时间</b>：起始 ${esc(src.custom_time_start_source || '')} ` +
        (isNum(src.custom_time_start) ? new Date(src.custom_time_start * 1000).toLocaleString() : '') : '') +
      (src.play_start_mode && src.play_start_mode !== 'begin'
        ? `　<b>播放起点</b>：${esc(src.play_start_mode)}=${esc(src.play_start_value || '')}` +
          (src.play_seek && isNum(src.play_seek.skipped_rows) ? `（跳过 ${src.play_seek.skipped_rows} 行）` : '') +
          (src.play_seek && isNum(src.play_seek.start_byte) ? `（字节 ${src.play_seek.start_byte}/${src.play_seek.file_size}）` : '')
        : '') +
      (isNum(src.play_end_time) ? `　<b>播放终点</b>：${ts(src.play_end_time)}` : ''),
    `已摄入 ${num(e.samples_in, 0)} 点（${num(e.blocks_in, 0)} 块），数据时长 ${num(e.data_duration_s, 2)}s，` +
      `速率 ${num(e.rate_samples_per_s, 1)} 点/s（配置采样率 ${num((cfg.sampling || {}).fs, 0)}）`,
    `环形缓冲 ${num(e.buffer_fill, 0)} / ${num(e.buffer_capacity, 0)} 点（各量窗长按需自动扩容），` +
      `调度 tick ${num(e.ticks, 0)} 次`,
    '本次运行各量输出次数：' + (Object.keys(emits).length
      ? Object.keys(emits).map(k => `${k}=${emits[k]}`).join('，')
      : '（尚无输出）'),
    `当前配置生效文件：<code>${esc(e.config_path || st.config_path || '—')}</code>`,
  ];
}
function sourceNotes(st) {
  const e = st.engine || {}, src = st.source || {};
  const arr = [];
  (e.notes || []).forEach(n => arr.push(n));
  (src.notes || []).forEach(n => arr.push('源：' + n));
  (e.gaps || []).forEach(g => arr.push(`⚠ 数据缺口 t=${ts(g.t)} 时长 ${num(g.gap_s * 1000, 1)}ms（约 ${num(g.missing_samples, 0)} 点）`));
  return arr;
}
function renderBranchStatus() {
  const box = $('#br-status'); if (!box) return;
  const sum = (S.state || {}).branch || {};
  const bst = BR.state;
  if (!bst) {
    const lines = [`状态：<b>${sum.error ? '错误' : sum.paused ? '已暂停' : sum.running ? '运行中' : sum.finished ? '已完成' : (sum.enabled ? '已启用·未启动' : '未启用')}</b>`];
    if (sum.error) lines.push(`<span class="bad">${esc(sum.error)}</span>`);
    lines.push(`配置文件：<code>${esc(sum.config_path || '—')}</code>`);
    box.innerHTML = lines.join('<br>');
    return;
  }
  const lines = sourceSummaryLines(bst, bst.config || BR.cfg || {}, '分路侧');
  if (!(bst.running || bst.finished) && !sum.enabled) lines[0] += '　（分路侧未启用：总线侧启动不会带起它，可「单独启动分路侧」）';
  box.innerHTML = lines.map(x => `<div>${x}</div>`).join('') + notes(sourceNotes(bst));
  const pre = $('#br-state'); if (pre) pre.textContent = JSON.stringify({ engine: bst.engine, source: bst.source, error: bst.error }, null, 2);
  renderBranchButtons(bst);
}
function renderBranchButtons(bst) {
  const eng = (bst && bst.engine) || {};
  const can = !!(bst && bst.pausable && eng.running && !eng.finished);
  const b = $('#btn-br-pause'); if (!b) return;
  b.disabled = !can; b.textContent = bst && bst.paused ? '恢复播放' : '暂停播放';
  b.className = bst && bst.paused ? 'primary' : '';
}
function collectBranchConfigPayload() {
  const src = collectSourceFields('br-');
  // 分路侧量纲与口径：空输入框跳过（保留服务端原值），与总线侧 collectConfigPayload 同规则
  const posv = (id) => { const v = parseFloat($('#' + id).value); return Number.isFinite(v) && v > 0 ? v : null; };
  const transform = { enabled: $('#br-scale').checked, voltage_input: $('#br-uin').value, invert_current: $('#br-inv').checked, invert_phases: getInvPhases('br'), wiring: $('#br-wiring').value, reconstruct_3w: $('#br-recon3w').checked };
  const pt = posv('br-pt'), ct = posv('br-ct');
  if (!transform.enabled) { transform.pt_ratio = 1; transform.ct_ratio = 1; }      // v0.99.8：未启用 PT/CT 变换 ⇒ PT、CT 均为 1
  else { if (pt !== null) transform.pt_ratio = pt; if (ct !== null) transform.ct_ratio = ct; }
  const sampling = { adaptive_freq: $('#br-adaptive').checked };
  const fs = posv('br-fs'), fnom = posv('br-fnom'); if (fs !== null) sampling.fs = fs; if (fnom !== null) sampling.f_nom = fnom;
  const harmonic = {}; const hmax = posv('br-hmax'); if (hmax !== null) harmonic.order_max = Math.max(2, Math.round(hmax));
  return { source: src, transform, sampling, harmonic, power: { apparent: $('#br-apparent').value, reactive: $('#br-reactive').value },
           columns: collectColumnsPayload('branch') };
}
async function saveBranchSource() {
  try {
    const enabled = $('#br-enabled').checked;
    const brTop = { enabled, time_offset_s: parseFloat($('#br-toffset').value) || 0, align_tol_s: Math.max(0, parseFloat($('#br-tol').value) || 0),
                    common_window: $('#br-common').checked, common_start: $('#br-common-start').value.trim(),
                    common_end: $('#br-common-end').value.trim(), hide_ui: !!($('#br-hide-ui') || {}).checked };
    const r1 = await fetch('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ branch: brTop }) });
    if (!r1.ok) throw new Error((await r1.json()).error || 'HTTP ' + r1.status);
    const body = collectBranchConfigPayload();
    if (enabled && (body.source.kind === 'csv_file' || body.source.kind === 'csv_tail') && !body.source.path && !((BR.cfg || {}).source || {}).path) {
      throw new Error('启用分路侧且输入方式为文件时必须填写分路侧文件路径');
    }
    const r2 = await fetch('/api/branch/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r2.ok) throw new Error('分路侧：' + ((await r2.json()).error || 'HTTP ' + r2.status));
    BR.dirty = false; BR.loaded = false;
    toast((enabled ? '分路侧配置已保存并启用：总线侧「启动」时将同时播放' : '分路侧配置已保存（未启用）') + `（输入方式 ${body.source.kind} + 量纲口径 + 列映射 + 联动参数）`, 'ok');
    S.state = await api('/api/state'); renderTop(); render();
  } catch (e) { toast('保存分路侧失败：' + e.message, 'err'); }
}
async function startBranchAlone() {
  try {
    const payload = collectSourceFields('br-');
    const r = await fetch('/api/branch/engine/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.error || 'HTTP ' + r.status);
    toast(`已单独启动分路侧数据源：${d.config.source.kind}` + (d.run_dir ? `；本次输出目录 ${d.run_dir}` : '') + (BR.dirty ? '（提示：量纲/列映射的修改请点「保存分路侧配置」）' : ''), 'ok');
    BR.loaded = false;
    S.state = await api('/api/state'); renderTop(); render(); refreshBranchState(true);
  } catch (e) { toast('分路侧启动失败：' + e.message, 'err'); }
}
async function stopBranchAlone() {
  try { await fetch('/api/branch/engine/stop', { method: 'POST' }); toast('分路侧已停止', 'ok'); }
  catch (e) { toast('分路侧停止失败：' + e.message, 'err'); }
  S.state = await api('/api/state'); renderTop(); render(); refreshBranchState(true);
}
async function toggleBranchPause() {
  const bst = BR.state || {}, eng = bst.engine || {};
  if (!(bst.pausable && eng.running && !eng.finished)) { toast('分路侧离线文件未在播放，无法暂停', 'err'); return; }
  const paused = !!bst.paused;
  try {
    const r = await fetch(paused ? '/api/branch/engine/resume' : '/api/branch/engine/pause', { method: 'POST' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    toast(paused ? '分路侧已恢复播放' : '分路侧已暂停播放', 'ok');
  } catch (e) { toast((paused ? '恢复' : '暂停') + '失败：' + e.message, 'err'); }
  refreshBranchState(true);
}

async function previewCommonWindow() {
  const out = $('#br-common-out');
  out.innerHTML = '<div class="notes">计算中…（按已保存的两侧配置；若刚改了路径/自定义时间请先保存）</div>';
  try {
    // v0.70：按界面当前值预览（总线侧 source + 分路侧联动参数 + 分路侧数据源），与「启动」一致；不写配置
    const body = Object.assign({}, collectSourcePayload(), {
      branch: { enabled: $('#br-enabled').checked, common_window: $('#br-common').checked, common_start: $('#br-common-start').value.trim(), common_end: $('#br-common-end').value.trim() },
      branch_source: collectSourceFields('br-') });
    const w = await (await fetch('/api/common_window/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })).json();
    if (!w.ok) { out.innerHTML = notes(['✗ ' + w.error]); return; }
    out.innerHTML = notes([
      `✓ 公共时间段：${ts(w.t_start)} → ${ts(w.t_end)}　总时长 ${num(w.duration_s, 3)} s`,
      `总线侧文件：${ts(w.bus.t0)} → ${ts(w.bus.t1)}（${w.bus.rows} 行${w.bus.custom_time ? '，自定义时间轴' : ''}）`,
      `分路侧文件：${ts(w.branch.t0)} → ${ts(w.branch.t1)}（${w.branch.rows} 行${w.branch.custom_time ? '，自定义时间轴' : ''}）`,
      `播放起点：${ts(w.play_start)}（${w.play_start_source}）　播放终点：${ts(w.play_end)}（${w.play_end_source}）　可播放 ${num(w.play_duration_s, 3)} s`,
    ]);
  } catch (e) { out.innerHTML = notes(['✗ ' + e.message]); }
}

async function probeBranch() {
  const p = $('#br-path').value.trim();
  if (!p) { toast('请先填写分路侧文件路径', 'err'); return; }
  $('#br-probe-out').innerHTML = '<div class="notes">探查中…</div>';
  try {
    const r = await (await fetch('/api/branch/probe?path=' + encodeURIComponent(p))).json();
    if (!r.ok) { $('#br-probe-out').innerHTML = notes(['✗ ' + r.error]); return; }
    BR.lastProbe = r;
    const cols = r.header || r.first_row || [];
    $('#br-probe-out').innerHTML = notes([
      `✓ ${r.path}`, `大小 ${r.size_mb} MB · 编码 ${r.encoding} · 行数 ${r.rows} · 时长约 ${num(r.duration_s, 2)}s`,
      `${r.header ? '表头' : '首行即数据'}（${cols.length} 列）：` + cols.map((h, i) => `[${i + 1}] ${h}`).join('  '),
      `时间戳模式 ${r.ts_mode} · 推算 fs ${num(r.fs_est, 3)} Hz（分路侧配置 ${r.fs_configured} Hz，偏差 ${num(r.fs_deviation_pct, 4)}%）` +
        (Math.abs(r.fs_deviation_pct || 0) > 1 ? '　⚠ 请把下方「分路侧采样率 fs」改成文件实际值' : ''),
      ...(r.notes || []),
    ]);
  } catch (e) { $('#br-probe-out').innerHTML = notes(['✗ ' + e.message]); }
}

async function pickBranchFile() {
  // 与总线侧「列出 data 目录」同构：列出 data/ 下 CSV，点击填入分路侧路径
  const out = $('#br-files-out');
  try {
    const r = await (await fetch('/api/files?sub=data')).json();
    const files = (r.files || []).filter(f => /\.csv$/i.test(f.name || f));
    if (!files.length) { out.innerHTML = notes(['data/ 下没有 CSV 文件']); return; }
    out.innerHTML = '<div class="notes">' + files.map(f => {
      const pth = f.path || f.name || f;
      return `<div><a href="#" data-brfile="${esc(pth)}">${esc(pth)}</a>${isNum(f.size_mb) ? `　${f.size_mb} MB` : ''}</div>`;
    }).join('') + '</div>';
    out.querySelectorAll('a[data-brfile]').forEach(a => a.addEventListener('click', (ev) => {
      ev.preventDefault(); $('#br-path').value = a.dataset.brfile; BR.dirty = true;
    }));
  } catch (e) { out.innerHTML = notes(['✗ 读取 data/ 失败：' + e.message]); }
}

function renderSource() {
  if (!S._rawRangeAt || Date.now() - S._rawRangeAt > 15000) { S._rawRangeAt = Date.now(); refreshRawRange('bus'); refreshRawRange('branch'); }
  const st = S.state || {}, cfg = st.config || {};
  if (S.formDirty) {
    setFormNote('⚠ 界面有未保存的修改：已暂停自动回填（实时推送不会覆盖你正在输入的内容）。' +
      '点「刷新」可丢弃修改并重新载入服务端配置。', true);
  } else {
    fillSourceForm(cfg);
    setFormNote('');
  }
  syncSourceForm();
  renderBranchPanel(st);
  const summary = sourceSummaryLines(st, cfg, '总线侧');
  summary[summary.length - 1] += '（界面里保存的配置写入该文件；出厂模板 configs/default.json 保持干净）';
  $('#src-summary').innerHTML = summary.map(x => `<div>${x}</div>`).join('') + notes(sourceNotes(st));
  $('#src-state').textContent = JSON.stringify({ engine: st.engine, source: st.source, error: st.error }, null, 2);
}

/* 实时落盘面板：开关/目录 走 PUT /api/config（热更新即时生效），状态来自 GET /api/realtime */
async function refreshRealtime(side = sideOf()) {
  const out = E(side, 'rt-out');
  if (!out) return;
  try {
    const d = await api('/api/realtime', undefined, side);
    SD[side].realtime = d;
    const total = Object.values(d.rows_written || {}).reduce((a, b) => a + (b || 0), 0);
    const lines = [`状态：${d.enabled ? '已启用' : '未启用'}　目录：${d.dir_display || d.dir}　本次会话已写 ${total} 行`];
    (d.files || []).forEach(f => lines.push(`✓ ${CURVE_NAME[f.quantity] || f.quantity}：${f.path}（本次 ${f.rows_this_session} 行）`));
    CURVE_KEYS.filter(k => d.curve_save && d.curve_save[k] === false).forEach(k => lines.push(`－ ${CURVE_NAME[k]}：未勾选「保存曲线」，不落盘`));
    (d.dir_files || []).forEach(f => lines.push(`· 目录现有 ${f.name}（${(f.size_bytes / 1024).toFixed(1)} KB，${new Date(f.mtime * 1000).toLocaleString()}）`));
    (d.errors || []).forEach(e => lines.push('✗ ' + e));
    out.innerHTML = notes(lines);
  } catch (e) { out.innerHTML = notes(['✗ ' + e.message]); }
}

async function saveRealtime(side = sideOf()) {
  const on = !!E(side, 'rt-enable').checked, dir = (E(side, 'rt-dir').value || '').trim();
  const body = { output: { realtime_save: on } };
  if (dir) body.output.realtime_dir = dir;
  try {
    await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, side);
    SD[side].rtDirty = false;
    if (side === 'branch') BR.loaded = false;
    toast(`${side === 'branch' ? '分路侧' : '总线侧'}实时落盘已${on ? '启用' : '关闭'}（已写入配置）`, 'ok');
    refreshRealtime(side);
  } catch (e) { toast('实时落盘设置失败：' + e.message, 'err'); }
}

function renderExport() {
  const st = curState();
  renderCurveSave();
  const outCfg = (st.config || {}).output;
  if (outCfg && !sd().rtDirty) {              // 开关/目录回填服务端配置；用户正在编辑（rtDirty）时不覆盖
    if ($('#rt-enable')) $('#rt-enable').checked = outCfg.realtime_save !== false;
    if ($('#rt-dir')) $('#rt-dir').value = outCfg.realtime_dir || 'output/realtime';
  }
  if (!sd().realtime) refreshRealtime();
  $('#ex-state').textContent = JSON.stringify(st.engine || {}, null, 2);
  const notesArr = [];
  ((st.engine || {}).notes || []).forEach(n => notesArr.push(n));
  ((st.engine || {}).errors || []).forEach(n => notesArr.push('✗ ' + n));
  ((st.engine || {}).gaps || []).forEach(g => notesArr.push(`⚠ 数据缺口 t=${ts(g.t)} 时长 ${num(g.gap_s * 1000, 1)}ms（约 ${num(g.missing_samples, 0)} 点）`));
  if (st.error) notesArr.push('✗ ' + st.error);
  $('#ex-notes').innerHTML = notes(notesArr);
  const cr = curResult();
  $('#ex-json').textContent = cr ? JSON.stringify(cr, null, 1).split('\n').slice(0, 200).join('\n') : '（无结果）';
}

/* ------------------------------------------------------------------ 间谐波 / 直流偏置 / 事件（第 9 轮） */

function renderInterharmonic() {
  const h = q('interharmonic');
  const cards = [];
  if (h) {
    const v = h.values;
    PH.forEach(k => cards.push(card(`TIHD_U ${k} 相`, num(v.tihd_u_pct[k], 3), '%', `最劣相 ${v.worst_phase_u || '—'}`)));
    PH.forEach(k => cards.push(card(`TIHD_I ${k} 相`, num(v.tihd_i_pct[k], 3), '%', `最劣相 ${v.worst_phase_i || '—'}`)));
    const gu = v.max_group_u, gi = v.max_group_i;
    cards.push(card('最大电压间谐波组', gu ? `${gu.phase} 相 第${gu.h}组` : '—', '', gu ? `${num(gu.f_lo, 0)}~${num(gu.f_hi, 0)}Hz · 主导 ${num(gu.dom_freq_hz, 1)}Hz · ${num(gu.pct, 3)}%` : ''));
    cards.push(card('最大电流间谐波组', gi ? `${gi.phase} 相 第${gi.h}组` : '—', '', gi ? `${num(gi.f_lo, 0)}~${num(gi.f_hi, 0)}Hz · 主导 ${num(gi.dom_freq_hz, 1)}Hz · ${num(gi.pct, 3)}%` : ''));
    cards.push(card('频率分辨率', num(v.freq_resolution_hz, 3), 'Hz', `整数周期 ${num(v.n_cycles, 0)} 个 · 每组 ${v.n_bins_per_group} 个谱线`));
  }
  $('#ih-cards').innerHTML = cards.join('') || card('状态', '尚无结果', '', '请先启动数据源');
  if (h && h.series) {
    const groups = h.series.groups || [];
    const modeU = radioVal('ihmode-u', 'pct');
    const modeI = radioVal('ihmode-i', 'pct');
    const srcU = modeU === 'pct' ? h.series.pct_u : h.series.rms_u;
    const srcI = modeI === 'pct' ? h.series.pct_i : h.series.rms_i;
    drawBars($('#ih-bar-u'), groups, PH.map(k => ({ name: k + ' 相', color: COLORS[k], data: srcU[k] || [] })),
             { xlabel: '间谐波组号（第 h 组 = h 次与 h+1 次谐波之间）', ylabel: modeU === 'pct' ? '含有率 %' : '组有效值 V', height: 230 });
    drawBars($('#ih-bar-i'), groups, PH.map(k => ({ name: k + ' 相', color: COLORS[k], data: srcI[k] || [] })),
             { xlabel: '间谐波组号', ylabel: modeI === 'pct' ? '含有率 %' : '组有效值 A', height: 230 });
    const ihTable = (top, unit) => {
      const all = PH.flatMap(k => top[k] || []);
      const sc = unitScale(all.flatMap(g => [g.dom_rms, g.rms, g.subgroup_rms]), unit);
      const out = [];
      PH.forEach(k => (top[k] || []).forEach(g => out.push([k, g.h, `${num(g.f_lo, 0)}~${num(g.f_hi, 0)}`,
        num(g.dom_freq_hz, 1), sc.f(g.dom_rms), num(g.dom_angle_deg, 2), sc.f(g.rms), sc.f(g.subgroup_rms), num(g.pct, 3)])));
      return table(['相', '组号', '频带 (Hz)', '主导频率 (Hz)', sc.hdr('主导幅值 RMS'), '主导相角 (°)', sc.hdr('组有效值'), sc.hdr('中心子组'), '含有率 (%)'], out);
    };
    $('#ih-table-u').innerHTML = ihTable(h.values.top_u || {}, 'V');
    $('#ih-table-i').innerHTML = ihTable(h.values.top_i || {}, 'A');
  }
  const hh = curHist('interharmonic');
  const t0 = hh.length ? hh[0].t : 0;
  drawLine($('#ih-trend'), [{ name: 'TIHD_U (%)', color: COLORS.A, data: hh.map(x => [x.t - t0, x.TIHD_U]) },
                            { name: 'TIHD_I (%)', color: COLORS.B, data: hh.map(x => [x.t - t0, x.TIHD_I]) },
                            // v0.28：分相 TIHD 默认隐藏、图例勾选
                            ...PH.map(k => ({ name: `TIHD_U${k.toLowerCase()}`, color: COLORS[k], width: 1.3, defaultHidden: true, data: hh.map(x => [x.t - t0, x[`TIHD_U${k.toLowerCase()}`]]) })),
                            ...PH.map(k => ({ name: `TIHD_I${k.toLowerCase()}`, color: shadeColor(COLORS[k], 0.55), width: 1.3, dash: [4, 3], defaultHidden: true, data: hh.map(x => [x.t - t0, x[`TIHD_I${k.toLowerCase()}`]]) }))],
           { ylabel: '%', fmtX: x => tsX(x + t0, spanOf('interharmonic')), fmtTip: x => ts(x + t0), tbase: t0, height: 200, legend: true });
  renderCurveSave();
  $('#ih-win').innerHTML = winNotes('interharmonic');
}

function renderDC() {
  const d = q('dc');
  const cards = [];
  if (d) {
    const v = d.values;
    PH.forEach(k => cards.push(card(`${k} 相电压直流`, si(v.u_dc[k], 'V'), '', `${num(v.u_dc_pct[k], 3)}% of U1=${si(v.u1_rms[k], 'V')}`)));
    PH.forEach(k => cards.push(card(`${k} 相电流直流`, si(v.i_dc[k], 'A'), '', `${num(v.i_dc_pct[k], 3)}% of I1=${si(v.i1_rms[k], 'A')}`)));
    cards.push(card('中性线直流 (Ia+Ib+Ic)', si(v.in_dc, 'A'), '', '三相电流直流之和'));
    cards.push(card('最大 |DC|', `${si(v.u_dc_max_abs, 'V')} / ${si(v.i_dc_max_abs, 'A')}`, '', '电压 / 电流'));
  }
  $('#dc-cards').innerHTML = cards.join('') || card('状态', '尚无结果', '', '请先启动数据源');
  if (d) {
    const v = d.values;
    const g = (o, k) => (o && o[k]) || {};
    const sDu = unitScale(PH.flatMap(k => [v.u_dc[k], g(v.u_dc_drift, k).min, g(v.u_dc_drift, k).max]), 'V'), sU1 = unitScale(PH.map(k => v.u1_rms[k]), 'V');
    $('#dc-table-u').innerHTML = table(['相', sDu.hdr('DC'), '相对 U1 (%)', sU1.hdr('U1'), sDu.hdr('逐周期均值 最小'), sDu.hdr('最大'), sDu.hdr('σ')],
      PH.map(k => [k, sDu.f(v.u_dc[k]), num(v.u_dc_pct[k], 3), sU1.f(v.u1_rms[k]), sDu.f(g(v.u_dc_drift, k).min), sDu.f(g(v.u_dc_drift, k).max), sDu.f(g(v.u_dc_drift, k).std)]));
    const sDi = unitScale([...PH.flatMap(k => [v.i_dc[k], g(v.i_dc_drift, k).min, g(v.i_dc_drift, k).max]), v.in_dc], 'A'), sI1 = unitScale(PH.map(k => v.i1_rms[k]), 'A');
    $('#dc-table-i').innerHTML = table(['相', sDi.hdr('DC'), '相对 I1 (%)', sI1.hdr('I1'), sDi.hdr('逐周期均值 最小'), sDi.hdr('最大'), sDi.hdr('σ')],
      [...PH.map(k => [k, sDi.f(v.i_dc[k]), num(v.i_dc_pct[k], 3), sI1.f(v.i1_rms[k]), sDi.f(g(v.i_dc_drift, k).min), sDi.f(g(v.i_dc_drift, k).max), sDi.f(g(v.i_dc_drift, k).std)]),
       ['N (Ia+Ib+Ic)', sDi.f(v.in_dc), '—', '—', '—', '—', '—']]);
    const cyc = (d.series && d.series.cycle) || [];
    drawLine($('#dc-cyc-u'), PH.map(k => ({ name: k + ' 相', color: COLORS[k], data: cyc.map((c, i) => [c, (d.series.u_per_cycle[k] || [])[i]]) })),
             { ylabel: 'V', fmtX: x => '#' + x.toFixed(0), fmtTip: x => '第 ' + x.toFixed(0) + ' 周期', height: 200, legend: true });
    drawLine($('#dc-cyc-i'), PH.map(k => ({ name: k + ' 相', color: COLORS[k], data: cyc.map((c, i) => [c, (d.series.i_per_cycle[k] || [])[i]]) })),
             { ylabel: 'A', fmtX: x => '#' + x.toFixed(0), fmtTip: x => '第 ' + x.toFixed(0) + ' 周期', height: 200, legend: true });
  }
  const mode = radioVal('dcmode', 'u');
  const hh = curHist('dc');
  const t0 = hh.length ? hh[0].t : 0;
  const pre = mode === 'u' ? 'U' : 'I';
  drawLine($('#dc-trend'), PH.map(k => ({ name: `${pre}${k.toLowerCase()} DC`, color: COLORS[k], data: hh.map(x => [x.t - t0, x[`${pre}${k.toLowerCase()}_dc`]]) })),
           { ylabel: mode === 'u' ? 'V' : 'A', fmtX: x => tsX(x + t0, spanOf('dc')), fmtTip: x => ts(x + t0), tbase: t0, height: 200, legend: true });
  renderCurveSave();
  $('#dc-win').innerHTML = winNotes('dc');
}

function onEventPush(list, side = 'bus') {
  const st = SD[side];
  list.forEach(e => {
    const idx = st.events.findIndex(x => x.id === e.id);
    if (idx >= 0) st.events[idx] = e; else st.events.unshift(e);
    // 不再逐条弹 toast（事件多时右下角被刷屏）：活动数走导航徽标，明细进「事件」页表格
  });
  if (st.events.length > 2000) st.events.length = 2000;
  setEventBadge(st.events.filter(x => x.active).length, side);
  if (S.view === 'events') render();
}

async function refreshEvents(side = sideOf()) {
  const st = SD[side];
  try {
    const typ = E(side, 'ev-filter').value;
    const act = E(side, 'ev-only-active').checked;
    const d = await api(`/api/events?limit=1000${act ? '&active=1' : ''}${typ ? '&types=' + typ : ''}`, undefined, side);
    st.events = d.events || []; st.evSummary = d.summary || null; st.evLoaded = true;
  } catch (e) { toast((side === 'branch' ? '分路侧' : '') + '事件列表获取失败：' + e.message, 'err'); }
  if (S.view === 'events') render();
}

async function clearEvents(side = sideOf()) {
  try { await api('/api/events/clear', { method: 'POST' }, side); toast((side === 'branch' ? '分路侧' : '总线侧') + '事件列表已清空', 'ok'); SD[side].events = []; await refreshEvents(side); }
  catch (e) { toast(e.message, 'err'); }
}

function fillEventForm(ev) {
  if (!ev || sd().evDirty) return;
  EV_FIELDS.forEach(f => {
    const el = $(`#ev-${f}`); if (!el) return;
    if (el.type === 'checkbox') el.checked = !!ev[f]; else el.value = ev[f];
  });
}

async function saveEventConfig(side = sideOf()) {
  const payload = {};
  EV_FIELDS.forEach(f => { const el = E(side, `ev-${f}`); if (!el) return; payload[f] = el.type === 'checkbox' ? el.checked : +el.value; });
  const note = E(side, 'ev-form-note');
  try {
    const d = await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ events: payload }) }, side);
    SD[side].evDirty = false; note.textContent = '已保存并热生效 ' + new Date().toLocaleTimeString();
    toast((side === 'branch' ? '分路侧' : '总线侧') + '事件阈值已保存', 'ok');
    if (d && d.config) { if (side === 'branch') { if (BRD.state) BRD.state.config = d.config; BR.loaded = false; } else if (S.state) S.state.config = d.config; }
    refreshEvents(side);
  } catch (e) { note.textContent = '保存失败：' + e.message; toast(e.message, 'err'); }
}

function evRow(e) {
  // v0.25：持续时间统一为秒；触发值 / 峰值 / 阈值 不带单位，单位单列（各类事件单位不同：V / A / % / Hz / Hz/s / W）
  const dur = e.duration_s === null || e.duration_s === undefined ? '进行中' : num(e.duration_s, 1);
  return [e.id, `<span class="badge ${e.active ? 'bad' : ''}">${e.active ? '活动' : '已结束'}</span>`, EVENT_NAME[e.type] || e.type, esc(e.subject),
          ts(e.start_t), e.end_t ? ts(e.end_t) : '—', dur,
          fmtVal(e.value_start), fmtVal(e.value_peak), `${e.direction === 'low' ? '<' : '>'} ${fmtVal(e.limit)}`, esc(e.unit), esc(e.detail || '')];
}

function renderEvents() {
  const st = sd();
  if (!st.evLoaded) { st.evLoaded = true; refreshEvents(); return; }
  const sm = st.evSummary || {};
  const counts = sm.counts || {};
  const abt = sm.active_by_type || {};
  const cards = Object.keys(EVENT_NAME).map(k => card(EVENT_NAME[k], String(counts[k] || 0), '次', `活动 ${abt[k] || 0}`));
  cards.unshift(card('事件检测', sm.enabled === false ? '已禁用' : '启用', '', `活动 ${sm.active || 0} / 累计 ${sm.total || 0}`));
  const el = sm.effective_limits;
  if (el) cards.push(card('基波有效阈值', `${si(el.u1_low_v, 'V')} ~ ${si(el.u1_high_v, 'V')}`, '', `I1 ≤ ${si(el.i1_high_a, 'A')}（折算 ×${sm.limit_scale.u}/×${sm.limit_scale.i}）`));
  const w = sm.writer || {};
  cards.push(card('事件落盘', w.enabled ? '开' : '关', '', writerSub(w)));
  const osc = sm.osc || {};
  cards.push(card('功率振荡评估', isNum(osc.amp_pp_pct) ? num(osc.amp_pp_pct, 2) : '—', isNum(osc.amp_pp_pct) ? '%' : '',
                  isNum(osc.dom_freq_hz) ? `主导 ${num(osc.dom_freq_hz, 3)} Hz · 峰峰 ${si(osc.amp_pp, 'W')} · ${osc.points} 点` : (osc.note || `${osc.points || 0} 点`)));
  $('#ev-cards').innerHTML = cards.join('');
  if (isNum(sm.active)) setEventBadge(sm.active);
  const hdr = ['#', '状态', '类型', '对象', '开始（数据时间）', '结束', '持续 (s)', '触发值', '峰值', '阈值', '单位', '说明'];
  const active = st.events.filter(e => e.active);
  $('#ev-active').innerHTML = active.length ? table(hdr, active.map(evRow)) : '<div class="notes ok">当前无活动事件</div>';
  $('#ev-total').textContent = String(sm.total || st.events.length);
  $('#ev-table').innerHTML = table(hdr, st.events.map(evRow));
  const cfg = curState().config || {};
  fillEventForm(cfg.events);
  $('#ev-notes').innerHTML = notes(sm.notes || [], [
    '口径：基波相量＝U1 相对 U_nom 的百分比上下限、I1 绝对上限；谐波相量＝单次含有率 HR_h 或 THD；间谐波相量＝IEC 61000-4-7 间谐波组含有率；' +
    '频率＝fundamental 窗所估频率；ROCOF＝相邻两次频率之差 / 数据时间差；功率振荡＝最近评估窗内 P 总的去趋势频谱主导分量（峰峰值 / |P̄|）。',
    '所有时刻均为数据时间（离线回放同样成立）；同一类型同一对象只保留一个活动事件，回到滞回带内才结束。',
  ]);
}

function render() {
  try {
    switch (S.view) {
      case 'overview': renderOverview(); break;
      case 'compare': renderCompare(); break;
      case 'voltage': renderDual(renderVoltage); break;
      case 'current': renderDual(renderCurrent); break;
      case 'power': renderDual(renderPower); break;
      case 'power_factor': renderDual(renderPF); break;
      case 'fundamental': renderDual(renderFundamental); break;
      case 'harmonic': renderDual(renderHarmonic); break;
      case 'interharmonic': renderDual(renderInterharmonic); break;
      case 'dc': renderDual(renderDC); break;
      case 'events': renderDual(renderEvents); break;
      case 'nilm': renderDual(renderNilm); break;
      case 'spectrum': renderDual(renderSpectrum); break;
      case 'windows': renderDual(renderWindows); break;
      case 'source': renderSource(); break;
      case 'export': renderDual(renderExport); break;
      case 'process': renderProcess(); break;
      default: break;
    }
  } catch (e) {
    console.error(e);
  }
}

/* ------------------------------------------------------------------ 交互 */

function collectSourceFields(pre) {
  // 只送**与当前源相关**且**用户确实填了**的字段：
  // 空字符串/空数字会覆盖服务端已保存的配置（例如把 host 抹成 ''、path 抹成 ''），
  // 而 /api/engine/start 与 PUT /api/config 是深合并语义，不送＝保留原值，这才是期望行为。
  const kind = srcEl(pre, 'kind').value;
  const p = { kind };
  const txt = (n) => ((srcEl(pre, n) || {}).value || '').trim();
  const chk = (n) => !!(srcEl(pre, n) || {}).checked;
  const numOr = (n, dflt) => {
    const v = parseFloat((srcEl(pre, n) || {}).value);
    return Number.isFinite(v) ? v : dflt;
  };
  if (kind === 'csv_file' || kind === 'csv_tail') {
    const path = txt('path');
    if (path) p.path = path;                 // 留空则不送：由服务端校验并给出「需要 source.path」
  }
  if (kind === 'csv_file') {
    // 自定义播放时间：布尔必送（取消勾选要能关掉）；起始时间**空串也送**——空＝「用文件第 1 条数据时间」是有效语义
    p.custom_time = chk('customtime');
    p.custom_time_start = txt('customstart');
    if (!p.custom_time) p.file_time_utc = chk('utc');   // 自定义时间关闭时才有意义
    // 播放起点：模式必送（选回「开头」要能关掉）；取值只在非 begin 时送（begin 不读取值，旧值留着无害）
    p.play_start_mode = (srcEl(pre, 'playmode') || {}).value || 'begin';
    if (p.play_start_mode !== 'begin') p.play_start_value = txt('playvalue');
    p.file_speed = parseFloat((srcEl(pre, 'file-speed') || {}).value) || 0;
    if (pre === 'br-') p.file_speed_follow = chk('file-speed-follow');   // v0.85：分路侧倍速是否随总线侧
    // 指定时间段播放（v0.17）：布尔必送；起止文本空串也送（空＝数据起点/终点是有效语义）
    p.play_window = chk('window');
    p.play_window_start = txt('winstart');
    p.play_window_end = txt('winend');
  }
  if (kind === 'csv_tail') {
    p.file_time_utc = chk('utc');
    p.tail_from_end = chk('tailend');
    p.watch_dir_newest = chk('newest');
  }
  if (kind === 'tcp') {
    const host = txt('host');
    if (host) p.host = host;
    p.port = numOr('port', 0);           // 0 会被服务端拒（port 非法），比静默用默认更好排查
    p.frame = (srcEl(pre, 'frame') || {}).value || 'text_csv';
    if (p.frame === 'binary') {
      const fmt = txt('fmt'), flds = txt('fields');
      if (fmt) p.struct_fmt = fmt;
      if (flds) p.struct_fields = flds;
    }
  }
  if (kind === 'simulator') {
    const sp = numOr('speed', null);
    if (sp !== null && sp > 0) p.sim_speed = sp;
  }
  const bs = numOr('block', null);
  if (bs !== null && bs > 0) p.block_samples = bs;
  return p;
}
function collectSourcePayload() { return collectSourceFields('src-'); }

const MAP_FIELDS = ['timestamp', 'ua', 'ia', 'ub', 'ib', 'uc', 'ic'];
const MAP_ALIAS = { timestamp: ['时间戳', '时间', '时标', 'timestamp', 'time', 'ts', 'datetime'],
  ua: ['a相电压', 'ua', 'u_a', 'va'], ia: ['a相电流', 'ia', 'i_a'], ub: ['b相电压', 'ub', 'u_b', 'vb'],
  ib: ['b相电流', 'ib', 'i_b'], uc: ['c相电压', 'uc', 'u_c', 'vc'], ic: ['c相电流', 'ic', 'i_c'] };

/* 列映射表单：总线侧 id 前缀 cfg-map / 分路侧 br-map（第 15 轮补充：两侧独立配置、独立保存） */
const MAP_UI = {
  bus:    { en: 'cfg-mapen', pre: 'cfg-map-', btns: ['btn-map-default', 'btn-map-fromprobe', 'btn-map-save'], probe: () => S.lastProbe },
  branch: { en: 'br-mapen',  pre: 'br-map-',  btns: ['btn-br-map-default', 'btn-br-map-fromprobe', 'btn-br-map-save'], probe: () => BR.lastProbe },
};
function mapEl(side, k) { return document.getElementById(MAP_UI[side].pre + k); }

function syncColmapForm(side) {
  if (!side) { syncColmapForm('bus'); syncColmapForm('branch'); return; }
  const u = MAP_UI[side], on = $('#' + u.en).checked;
  MAP_FIELDS.forEach(k => { const el = mapEl(side, k); el.disabled = !on; const lab = el.closest('label'); if (lab) lab.classList.toggle('off', !on); });
  u.btns.slice(0, 2).forEach(id => { $('#' + id).disabled = !on; });
}

function collectColumnsPayload(side = 'bus') {
  const mapping = {};
  MAP_FIELDS.forEach(k => { mapping[k] = mapEl(side, k).value.trim(); });
  return { mapping_enabled: $('#' + MAP_UI[side].en).checked, mapping };
}

function fillColumnsForm(side, columns) {
  columns = columns || {};
  $('#' + MAP_UI[side].en).checked = !!columns.mapping_enabled;
  MAP_FIELDS.forEach(k => { mapEl(side, k).value = (columns.mapping || {})[k] || ''; });
  syncColmapForm(side);
}

function markMapDirty(side) { if (side === 'branch') BR.dirty = true; else { S.formDirty = true; S.cfgDirty = true; } }

function fillColmapDefault(side = 'bus') {
  MAP_FIELDS.forEach((k, i) => { mapEl(side, k).value = String(i + 1); });
  markMapDirty(side);
}

function fillColmapFromProbe(side = 'bus') {
  const pr = MAP_UI[side].probe();
  const hdr = pr && pr.header;
  if (!hdr || !hdr.length) { toast(side === 'branch' ? '请先「探查分路侧文件」且文件需有表头' : '请先「探查数据」且文件需有表头', 'err'); return; }
  const norm = (x) => String(x).replace(/[\s_\-]/g, '').toLowerCase();
  const found = [];
  MAP_FIELDS.forEach(k => {
    const i = hdr.findIndex(h => MAP_ALIAS[k].includes(norm(h)));
    mapEl(side, k).value = i >= 0 ? hdr[i] : '';
    if (i >= 0) found.push(k);
  });
  markMapDirty(side);
  toast(`已按${side === 'branch' ? '分路侧' : '总线侧'}表头填入 ${found.length}/7 个字段${found.length < 7 ? '，其余留空＝不播放' : ''}`, 'ok');
}

async function saveColumns(side) {
  try {
    const url = side === 'branch' ? '/api/branch/config' : '/api/config';
    const r = await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ columns: collectColumnsPayload(side) }) });
    if (!r.ok) throw new Error((await r.json()).error || 'HTTP ' + r.status);
    if (side === 'branch') { BR.dirty = false; BR.loaded = false; } else { S.formDirty = false; S.cfgDirty = false; }
    toast(`${side === 'branch' ? '分路侧' : '总线侧'}列映射已保存（下一块数据 / 下次启动生效）`, 'ok');
    S.state = await api('/api/state'); renderTop(); render();
  } catch (e) { toast('保存列映射失败：' + e.message, 'err'); }
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
  const transform = { enabled: $('#cfg-scale').checked, voltage_input: $('#cfg-uin').value, invert_current: $('#cfg-inv').checked, invert_phases: getInvPhases('cfg'), wiring: $('#cfg-wiring').value, reconstruct_3w: $('#cfg-recon3w').checked };
  const pt = pos('cfg-pt', 'PT 变比'), ct = pos('cfg-ct', 'CT 变比');
  if (!transform.enabled) { transform.pt_ratio = 1; transform.ct_ratio = 1; }      // v0.99.8：未启用 PT/CT 变换 ⇒ PT、CT 均为 1
  else { if (pt !== null) transform.pt_ratio = pt; if (ct !== null) transform.ct_ratio = ct; }
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
      columns: collectColumnsPayload(),
    },
    skipped,
  };
}

function collectWindowPayload(side = sideOf()) {
  const out = {};
  E(side, 'w-table').querySelectorAll('[data-w]').forEach(el => {
    const k = el.dataset.w, f = el.dataset.f;
    out[k] = out[k] || {};
    if (el.type === 'checkbox') out[k][f] = el.checked;
    else if (el.tagName === 'SELECT') out[k][f] = el.value;
    else out[k][f] = el.value === '' ? null : +el.value;
  });
  // v0.75：表格里「步长」显示的是有效值（null ⇒ 等于窗长）；用户没改时仍按原配置的 null 回送，避免把文件里的 null 改写成数字
  const cw = (((side === 'branch' ? BRD.state : S.state) || {}).config || {}).windows || {};
  Object.keys(out).forEach(k => { if (cw[k] && cw[k].step_s === null && out[k].step_s === out[k].length_s) out[k].step_s = null; });
  return { windows: out };
}

// v0.18：不播放时把上次播放落盘的曲线 / 事件 / 负荷辨识事件读回界面（服务端按本侧 source_id 过滤）
let _loadingLast = false;
async function loadLastData() {
  if (_loadingLast) return;
  _loadingLast = true;
  ['#btn-load-last', '#btn-load-last2'].forEach(sel => { const b = $(sel); if (b) b.disabled = true; });
  try {
    const r = await api('/api/history/load_last', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
    const parts = [];
    const fmt = x => {
      const pts = Object.values(x.curves || {}).reduce((a, b) => a + (b || 0), 0);
      return `曲线点 ${pts}、事件 ${x.events || 0}、负荷辨识事件 ${x.nilm_events || 0}、最新电气量${x.result ? '有' : '无'}` +
        (x.t_first_local ? `，${x.t_first_local} ~ ${x.t_last_local}` : '（无数据）');
    };
    parts.push(`${r.side === 'branch' ? '分路侧' : '总线侧'}：${fmt(r)}`);
    if (r.branch && r.branch.ok) parts.push(`分路侧：${fmt(r.branch)}`);
    else if (r.branch && r.branch.error) parts.push(`分路侧：${r.branch.error}`);
    toast('已加载上次播放数据 — ' + parts.join('；'), 'ok');
    S.histCache = {}; S.histAt = {}; S.histMeta = {}; OVB.hist = {}; OVB.meta = {}; OVB.at = 0; OVB.doneFetched = false; SD.bus.events = []; SD.bus.nl.events = []; SD.branch.events = []; SD.branch.nl.events = [];
    await Promise.all([refreshHistory(), refreshEvents('bus'), refreshNilm('bus'), refreshOverviewBranch(true), refreshBranchDual(true)]);
    try {
      S.state = await api('/api/state');
      if (r.result) { const rr = await fetch(apiUrl('/api/result?full=false')); if (rr.ok) S.result = await rr.json(); }
      renderTop(); render(); refreshBranchState(true);
    } catch (e) { /* 快照刷新失败不影响已加载数据 */ }
  } catch (e) { toast('加载上次数据失败：' + e.message, 'err'); }
  finally { _loadingLast = false; }
}

function renderLoadedLast(st, eng) {
  const ll = st.loaded_last;
  const al = $('#autoload-last');
  if (al && !S.autoloadDirty) al.checked = ((((st.config || {}).output) || {}).autoload_last) !== false;
  const el = $('#src-loaded-last');
  if (!el) return;
  if (!ll || eng.running) { el.textContent = ''; el.style.display = 'none'; return; }
  const pts = Object.values(ll.curves || {}).reduce((a, b) => a + (b || 0), 0);
  el.style.display = '';
  el.textContent = `${ll.auto ? '软件启动时已自动加载' : '已加载'}上次运行数据（${ll.loaded_at_local || ''}）：曲线点 ${pts}、事件 ${ll.events || 0}、负荷辨识事件 ${ll.nilm_events || 0}` +
    (ll.t_first_local ? `，数据时间 ${ll.t_first_local} ~ ${ll.t_last_local}` : '，CSV 中无本侧数据') +
    (ll.result ? `；最新电气量取自 ${ll.result_saved_at_local || ''} 保存的结果（${ll.result_source || ''}）` : '；无保存的最新电气量');
}

/* v0.21：离线文件指定时间段原始数据重新导出 */
function tsFull(v) {      // "YYYY-MM-DD HH:MM:SS.fff"（本地时间；可直接回填给服务端 parse_time_text）
  if (!isNum(+v)) return '';
  const d = new Date(+v * 1000), p = (n, w = 2) => String(n).padStart(w, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${p(d.getMilliseconds(), 3)}`;
}
/* v0.21.1：两侧各自独立的原始数据导出；side = 'bus' | 'branch'，显式走各自前缀，不随页面侧别切换 */
const RAW_EXP = {
  bus:    { pre: '',    url: '/api/source',        label: '总线侧' },
  branch: { pre: 'br-', url: '/api/branch/source', label: '分路侧' },
};
async function rawApi(url, opt) {
  const res = await fetch(url, opt);
  let data = null;
  try { data = await res.json(); } catch (e) { data = { ok: false, error: 'HTTP ' + res.status }; }
  if (!res.ok) throw new Error((data && data.error) || ('HTTP ' + res.status));
  return data;
}
async function refreshRawRange(side = 'bus') {
  const cfg = RAW_EXP[side]; const el = $('#' + cfg.pre + 'raw-exp-range'); if (!el) return null;
  try {
    const d = await rawApi(cfg.url + '/raw_range');
    const r = (d.ranges || {})[side];
    el.textContent = r ? (r.error ? '✗ ' + r.error : `${r.t0_local} ~ ${r.t1_local}（${r.rows} 行）`) : ((d.notes || []).join('；') || '无离线文件数据源');
    return d;
  } catch (e) { el.textContent = '文件范围获取失败：' + e.message; return null; }
}
async function fillRawRange(side = 'bus') {
  const cfg = RAW_EXP[side]; const d = await refreshRawRange(side);
  const r = ((d || {}).ranges || {})[side];
  if (!r || r.error) { toast(`${cfg.label}没有可用的离线文件时间范围`, 'err'); return; }
  $('#' + cfg.pre + 'raw-exp-from').value = tsFull(r.t0);
  $('#' + cfg.pre + 'raw-exp-to').value = tsFull(r.t1);
}
async function exportRawRange(side = 'bus') {
  const cfg = RAW_EXP[side]; const g = (id) => $('#' + cfg.pre + id);
  const body = { t_from: (g('raw-exp-from').value || '').trim(), t_to: (g('raw-exp-to').value || '').trim(), name: (g('raw-exp-name').value || '').trim() };
  const note = g('raw-exp-note'); const btn = g('btn-raw-export');
  btn.disabled = true; btn.textContent = '导出中…';
  try {
    const r = await rawApi(cfg.url + '/export_range', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const v = (r.sides || {})[side] || {};
    toast(`${cfg.label}已导出 ${r.rows} 行 → ${r.path}`, 'ok');
    if (note) note.innerHTML = notes([`✓ ${r.path}（${(r.size_bytes / 1024 / 1024).toFixed(2)} MB）`, `${cfg.label} ${r.rows} 行，source_id=${r.source_ids.join('/')}，源文件 ${v.path || ''}`,
                                      `数据时间 ${r.t_first_local} ~ ${r.t_last_local}`, r.header ? `列：${r.header.join(', ')}` : '无表头（与源文件一致）', ...(r.notes || []).map(n => 'ℹ ' + n)]);
  } catch (e) {
    toast(`${cfg.label}导出原始数据失败：` + e.message, 'err');
    if (note) note.innerHTML = notes(['✗ ' + e.message]);
  } finally { btn.disabled = false; btn.textContent = '导出到新 CSV'; }
}

async function startEngine(payloadExtra = {}) {
  try {
    // 只送 source（+ 可选 windows）：/api/engine/start 的白名单只有 source 键与 windows，
    // 夹带 transform/sampling/harmonic/power 会被服务端**静默忽略**——用户改了 PT/CT 再点
    // 「启动数据源」以为生效了，其实没有。口径/变比一律走「保存配置（热更新）」。
    const payload = Object.assign(collectSourcePayload(), payloadExtra);
    // v0.70：总线侧启动同时带上界面当前的分路侧联动参数与分路侧数据源字段（与总线侧 source 同规则：按界面当前值启动、
    // 不写配置文件）。否则取消勾选「只播放公共时间段」但没保存时，服务端仍按旧配置算公共时间段并报错。
    if (sideOf() === 'bus' && $('#br-enabled') && BR.loaded && payload.branch === undefined) {   // 面板已按保存值填充后才按界面值
      payload.branch = { enabled: $('#br-enabled').checked, common_window: $('#br-common').checked,
                         common_start: $('#br-common-start').value.trim(), common_end: $('#br-common-end').value.trim(),
                         time_offset_s: parseFloat($('#br-toffset').value) || 0, align_tol_s: Math.max(0, parseFloat($('#br-tol').value) || 0) };
      try { payload.branch_source = collectSourceFields('br-'); } catch (e) { /* 分路侧面板未就绪则按已保存配置 */ }
    }
    const r = await api('/api/engine/start', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    S.formDirty = false; S.srcDirty = false;
    let brMsg = '';
    if (r.branch && !r.branch.skipped) brMsg = r.branch.ok ? `；分路侧已同时启动（${r.branch.source_kind}${r.branch.synced_pace ? '，倍速随总线侧' : (r.branch.file_speed !== undefined ? `，分路侧倍速 ${r.branch.file_speed > 0 ? r.branch.file_speed + '×' : '不限速'}` : '')}）` : `；⚠ 分路侧启动失败：${r.branch.error}`;
    if (r.common_window && r.common_window.enabled === false && r.common_window.reason) brMsg += `；ℹ ${r.common_window.reason}`;
    toast(`已启动${sideLabel()}数据源：${r.config.source.kind}` + brMsg + (r.run_dir ? `；本次输出目录 ${r.run_dir}（实时数据 / 事件 / 两侧配置）` : '') +
      (S.cfgDirty ? '（提示：口径/变比的修改请点「保存总线侧配置」）' : '') + '（启动不写配置文件；要保留数据源设置请点「保存总线侧配置」）', r.branch && r.branch.error ? 'err' : 'ok');
    S.cfgDirty = false;
    S.state = await api('/api/state');
    renderTop(); render();
    setTimeout(refreshHistory, 800);
    setTimeout(() => refreshBranchState(true), 600);
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

// v0.81：「从文件加载本侧配置」——POST /api(/branch)/config/load_file {path, persist}；path 空＝本侧现有配置文件
async function loadCfgFromFile(side) {
  const pre = side === 'branch' ? 'br-' : 'src-';
  const inp = $('#' + pre + 'cfgload-path'), chk = $('#' + pre + 'cfgload-persist');
  const btn = side === 'branch' ? $('#btn-br-cfgload') : $('#btn-src-cfgload');
  const path = (inp && inp.value || '').trim(), persist = !!(chk && chk.checked);
  const name = side === 'branch' ? '分路侧' : '总线侧';
  if (btn) btn.disabled = true;
  try {
    const r = await api('/api/config/load_file', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path, persist }) }, side);
    if (side === 'branch') { BR.dirty = false; BR.loaded = false; BR.fileSpeedChosen = undefined; }
    else { S.formDirty = false; S.cfgDirty = false; S.srcDirty = false; }
    const where = r.config_file_updated ? `，并已写入 ${r.config_file}（${(r.config_file_changes || []).length} 项变化）`
      : (persist ? '（配置文件内容无变化或服务端未启用回写）' : '（只加载到运行配置，未写配置文件）');
    toast(`已从 ${r.loaded_from} 加载${name}配置并热更新${where}` + (r.warning ? '；⚠ ' + r.warning : ''), r.warning ? 'err' : 'ok');
    S.state = await api('/api/state'); renderTop(); render();
    if (side === 'branch') { await loadBranchForm(true); refreshBranchState(true); }
    else if (S.state && S.state.config) { try { fillSourceForm(S.state.config); syncSourceForm(); } catch (e2) { /* 不在数据源页时忽略 */ } }
  } catch (e) { toast(`从文件加载${name}配置失败：` + e.message, 'err'); }
  finally { if (btn) btn.disabled = false; }
}
async function initCfgLoadRows() {
  // 占位符填本侧现有配置文件路径（GET /api(/branch)/config/file）；输入框本身留空＝按现有路径加载
  for (const side of ['bus', 'branch']) {
    const inp = $('#' + (side === 'branch' ? 'br-' : 'src-') + 'cfgload-path');
    if (!inp) continue;
    try { const r = await api('/api/config/file', undefined, side); if (r && r.path) inp.placeholder = `空＝现有路径（${r.path}${r.exists ? '' : '，尚不存在'}）`; }
    catch (e) { /* 保留 HTML 占位符 */ }
  }
}

// v0.63：总线侧「保存总线侧配置」——数据源 + 量纲口径 + 列映射一起写入 configs/runtime.json（服务端只更新这些键）
function collectBusSavePayload() {
  const { payload, skipped } = collectConfigPayload();
  return { payload: Object.assign({ source: collectSourcePayload() }, payload), skipped };
}
async function saveBusSource() {
  try {
    const { payload, skipped } = collectBusSavePayload();
    const src = payload.source || {};
    if ((src.kind === 'csv_file' || src.kind === 'csv_tail') && !src.path) throw new Error('输入方式为文件时必须填写文件路径');
    const r = await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }, 'bus');
    S.formDirty = false; S.cfgDirty = false; S.srcDirty = false;
    const where = r.config_file_updated ? `已写入 ${r.config_file}` : '已热更新（服务端未启用配置文件回写）';
    toast(`总线侧配置${where}：数据源 ${src.kind} + 量纲口径 + 列映射` + (skipped.length ? `；${skipped.join('、')} 为空 → 保留原值` : ''), 'ok');
    S.state = await api('/api/state'); renderTop(); render();
  } catch (e) { toast('保存总线侧配置失败：' + e.message, 'err'); }
}

async function saveWindows(side = sideOf()) {
  try {
    await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
                               body: JSON.stringify(collectWindowPayload(side)) }, side);
    toast((side === 'branch' ? '分路侧' : '总线侧') + '窗口配置已保存（各量按新时间段计算）', 'ok');
    if (side === 'branch') { BRD.state = await api('/api/state', undefined, 'branch'); BR.loaded = false; }
    else S.state = await api('/api/state', undefined, 'bus');
    render();
  } catch (e) { toast('保存失败：' + e.message, 'err'); }
}

function applyPreset(sec, side = sideOf()) {
  E(side, 'w-table').querySelectorAll('[data-w][data-f=length_s],[data-w][data-f=step_s]').forEach(el => { el.value = sec; });
}

async function probe() {
  const p = $('#src-path').value.trim();
  if (!p) { toast('请先填写 CSV 路径或目录', 'err'); return; }
  $('#probe-out').innerHTML = '<div class="notes">探查中…</div>';
  try {
    const r = await api('/api/probe?path=' + encodeURIComponent(p));
    if (!r.ok) { $('#probe-out').innerHTML = notes(['✗ ' + r.error]); return; }
    S.lastProbe = r;
    const cols = r.header || r.first_row || [];
    $('#probe-out').innerHTML = notes([
      `✓ ${r.path}`, `大小 ${r.size_mb} MB · 编码 ${r.encoding} · 行数 ${r.rows} · 时长约 ${num(r.duration_s, 2)}s`,
      (r.header ? '表头' : '首行即数据（无表头）') + `（${cols.length} 列）：` + cols.map((h, i) => `[${i + 1}] ${h}`).join('  '),
      `列映射（${r.mapping_enabled ? '启用 columns.mapping' : '默认：表头/默认列序'}）：${JSON.stringify(r.columns)}` +
        ((r.unmapped || []).length ? `；未映射不播放：${r.unmapped.join('、')}` : ''),
      `时间戳模式 ${r.ts_mode} · 推算 fs ${num(r.fs_est, 3)} Hz（配置 ${r.fs_configured} Hz，偏差 ${num(r.fs_deviation_pct, 4)}%）`,
      ...(r.notes || []),
    ]);
  } catch (e) { $('#probe-out').innerHTML = notes(['✗ ' + e.message]); }
}

async function listFiles() {
  // v0.84：与分路侧「列出 data 目录」（pickBranchFile）一致：只列 CSV，每项可点击填入本侧「CSV 路径 / 目录」
  const out = $('#files-out');
  try {
    const r = await (await fetch('/api/files?sub=data')).json();
    if (r.ok === false) { out.innerHTML = notes(['✗ ' + r.error]); return; }
    const files = (r.files || []).filter(f => /\.csv$/i.test(f.name || f));
    if (!files.length) { out.innerHTML = notes(['data/ 下没有 CSV 文件']); return; }
    out.innerHTML = '<div class="notes">' + files.map(f => {
      const pth = f.path || f.name || f;
      return `<div><a href="#" data-srcfile="${esc(pth)}">${esc(pth)}</a>${isNum(f.size_mb) ? `　${f.size_mb} MB` : ''}</div>`;
    }).join('') + '</div>';
    out.querySelectorAll('a[data-srcfile]').forEach(a => a.addEventListener('click', (ev) => {
      ev.preventDefault(); $('#src-path').value = a.dataset.srcfile; S.srcDirty = true; S.formDirty = true;
    }));
  } catch (e) { out.innerHTML = notes(['✗ 读取 data/ 失败：' + e.message]); }
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
    $('#self-table').innerHTML = table(['编号', '项目', '期望值', '实际值', '单位', '相对误差 (%)', '容差 (%)', '结论'],
      r.checks.map(c => [c.id, c.name, num(c.expected, 6), num(c.actual, 6), c.unit,
        (c.rel_err * 100).toFixed(5), (c.tol_rel * 100).toFixed(3),
        c.ok ? '<span class="badge ok">PASS</span>' : '<span class="badge bad">FAIL</span>']));
    toast(r.all_ok ? '算法自检全部通过' : '自检存在失败项，请查看明细', r.all_ok ? 'ok' : 'err');
  } catch (e) {
    $('#self-summary').innerHTML = notes(['✗ 自检执行失败：' + e.message]);
  }
}

async function saveCfgFile(side = sideOf()) {
  try {
    const cfg = await api('/api/config', undefined, side);
    // v0.75：整份送回，但服务端只把与原文件不同的键写入（原文件其它内容不动）；回显实际改了哪些键
    const d = await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cfg) }, side);
    const cp = d.config_file || (side === 'branch' ? 'configs/branch_runtime.json' : 'configs/runtime.json');
    const ch = d.config_file_changes || [];
    E(side, 'exp-out').innerHTML = notes([ch.length ? `✓ ${side === 'branch' ? '分路侧' : '总线侧'}配置文件 ${cp} 在原文件基础上更新了 ${ch.length} 项：${ch.join('、')}（其它内容未动；出厂模板 configs/default.json 未被改动）`
                                                    : `✓ ${side === 'branch' ? '分路侧' : '总线侧'}配置文件 ${cp} 与当前运行配置一致，无需改动`]);
    toast('配置已持久化', 'ok');
  } catch (e) { E(side, 'exp-out').innerHTML = notes(['✗ ' + e.message]); }
}

/* v0.24：事件 / 负荷辨识 / 窗口配置 / 导出页的按钮与过滤器——左右两列各绑一份（side 固定在闭包里） */
function bindSideViews(side) {
  const on = (id, ev, fn) => { const el = E(side, id); if (el) el.addEventListener(ev, fn); };
  bindElecWindows(side);                        // v0.71：三相电压 / 电流 / 功率页的周波窗按钮
  // 窗口配置
  on('btn-save-win', 'click', () => saveWindows(side));
  on('btn-preset-fast', 'click', () => applyPreset(0.2, side));
  on('btn-preset-std', 'click', () => applyPreset(1, side));
  on('btn-preset-slow', 'click', () => applyPreset(5, side));
  // 导出与日志
  on('btn-save-cfgfile', 'click', () => saveCfgFile(side));
  on('btn-save-curves', 'click', () => saveCurves(side));
  on('btn-rt-save', 'click', () => saveRealtime(side));
  on('btn-rt-refresh', 'click', () => refreshRealtime(side));
  ['rt-enable', 'rt-dir'].forEach(id => { on(id, 'input', () => { SD[side].rtDirty = true; }); on(id, 'change', () => { SD[side].rtDirty = true; }); });
  // 事件
  on('btn-ev-refresh', 'click', () => refreshEvents(side));
  on('btn-ev-clear', 'click', () => clearEvents(side));
  on('btn-ev-save', 'click', () => saveEventConfig(side));
  on('ev-filter', 'change', () => refreshEvents(side));
  on('ev-only-active', 'change', () => refreshEvents(side));
  const evf = E(side, 'ev-form');
  if (evf) evf.querySelectorAll('input').forEach(el => { const mark = () => { SD[side].evDirty = true; }; el.addEventListener('input', mark); el.addEventListener('change', mark); });
  // 负荷辨识
  bindNilm(side);
}

/* ------------------------------------------------------------------ 初始化 */

function bind() {
  bindProcess();
  $$('.navitem').forEach(b => b.addEventListener('click', () => switchView(b.dataset.view, b.dataset.side)));
  $('#btn-start').addEventListener('click', () => startEngine());
  $('#btn-stop').addEventListener('click', stopEngine);
  $('#btn-pause').addEventListener('click', togglePause);
  $('#btn-refresh').addEventListener('click', async () => {
    try {
      S.formDirty = false; S.srcDirty = false; S.cfgDirty = false;   // 刷新＝丢弃未保存修改并重新回填
      S.result = await api('/api/result?full=true');
      S.state = await api('/api/state');
      renderTop(); render(); toast('已刷新快照', 'ok');
    } catch (e) { toast(e.message, 'err'); }
  });
  $('#btn-start2').addEventListener('click', () => startEngine());
  $('#btn-src-save').addEventListener('click', saveBusSource);
  $('#btn-stop2').addEventListener('click', stopEngine);
  $('#btn-pause2').addEventListener('click', togglePause);
  $('#btn-load-last').addEventListener('click', loadLastData);
  $('#btn-raw-export').addEventListener('click', () => exportRawRange('bus'));
  $('#btn-raw-exp-fill').addEventListener('click', () => fillRawRange('bus'));
  $('#br-btn-raw-export').addEventListener('click', () => exportRawRange('branch'));
  $('#br-btn-raw-exp-fill').addEventListener('click', () => fillRawRange('branch'));
  $('#autoload-last').addEventListener('change', async (e) => {
    const on = !!e.target.checked; S.autoloadDirty = true;
    try {
      await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ output: { autoload_last: on } }) });
      if (S.state && S.state.config) { S.state.config.output = S.state.config.output || {}; S.state.config.output.autoload_last = on; }
      toast(`软件启动时自动加载上次数据：已${on ? '开启' : '关闭'}（已写入配置）`, 'ok');
    } catch (err) { toast('设置失败：' + err.message, 'err'); }
    finally { S.autoloadDirty = false; }
  });
  $('#btn-load-last2').addEventListener('click', loadLastData);
  if ($('#btn-src-cfgload')) $('#btn-src-cfgload').addEventListener('click', () => loadCfgFromFile('bus'));
  if ($('#btn-br-cfgload')) $('#btn-br-cfgload').addEventListener('click', () => loadCfgFromFile('branch'));
  initCfgLoadRows();

  $('#btn-br-save').addEventListener('click', saveBranchSource);
  $('#btn-br-savecfg').addEventListener('click', saveBranchSource);
  $('#btn-br-start').addEventListener('click', startBranchAlone);
  $('#btn-br-stop').addEventListener('click', stopBranchAlone);
  $('#btn-br-pause').addEventListener('click', toggleBranchPause);
  $('#btn-br-common-preview').addEventListener('click', previewCommonWindow);
  ['br-pt', 'br-ct', 'br-inv', 'br-fs', 'br-fnom', 'br-adaptive', 'br-scale', 'br-uin', 'br-hmax', 'br-apparent', 'br-reactive', 'br-toffset', 'br-tol']
    .forEach(id => { const el = $('#' + id); if (el) el.addEventListener('input', () => { BR.dirty = true; }); });
  $('#cmp-key').addEventListener('change', e => { CMP.key = e.target.value; CMP.data = null; refreshCompare(); });
  $('#cmp-field').addEventListener('change', e => { CMP.field = e.target.value; renderCompare(); });
  $('#btn-cmp-refresh').addEventListener('click', refreshCompare);
  $('#cmp-ratio').addEventListener('change', renderCompare);
  $('#btn-cmp-suggest').addEventListener('click', () => {
    const d = CMP.data; if (!d || d.offset_suggest_s === null || d.offset_suggest_s === undefined) { toast('两侧都需要有历史点才能按起点对齐', 'err'); return; }
    $('#cmp-offset').value = Math.round(d.offset_suggest_s * 1000) / 1000; refreshCompare();
  });
  $('#btn-cmp-save').addEventListener('click', saveCompareOffset);
  $('#btn-br-goto').addEventListener('click', () => switchView('voltage', 'branch'));
  $('#btn-br-probe').addEventListener('click', probeBranch);
  $('#btn-br-pick').addEventListener('click', pickBranchFile);
  // 分路侧列所有输入：置脏（BR.dirty）；输入方式/帧格式/自定义时间/播放起点 变化时联动字段启用状态
  $$('#view-source input, #view-source select').forEach((el) => {
    if (!el.id.startsWith('br-')) return;
    const mark = () => { BR.dirty = true; };
    el.addEventListener('input', mark); el.addEventListener('change', mark);
  });
  ['br-kind', 'br-frame', 'br-customtime', 'br-playmode', 'br-window'].forEach(id => $('#' + id).addEventListener('change', () => syncSourceFields('br-')));
  $('#src-window').addEventListener('change', () => { S.srcDirty = true; S.formDirty = true; syncSourceForm(); });
  $('#br-kind').addEventListener('change', syncBranchColumns);
  $('#br-file-speed').addEventListener('change', () => { BR.fileSpeedChosen = parseFloat($('#br-file-speed').value) || 0; });
  $('#br-file-speed-follow').addEventListener('change', () => { BR.dirty = true; syncSourceForm(); });
  $('#br-enabled').addEventListener('change', () => { syncBranchColumns(); if ($('#br-enabled').checked) { loadBranchForm(false); refreshBranchState(true); } });
  // v0.33：「隐藏分路侧数据」即时生效并持久化（只存总线侧 config.branch.hide_ui）
  const hu = $('#br-hide-ui'); if (hu) hu.addEventListener('change', async () => {
    try {
      const r = await fetch('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ branch: { hide_ui: hu.checked } }) });
      if (!r.ok) throw new Error((await r.json()).error || 'HTTP ' + r.status);
      S.state = await (await fetch('/api/state')).json(); renderTop();
      toast(hu.checked ? '已隐藏分路侧数据：实时监测 / 事件与分析 各子界面右侧的分路侧内容不再显示' : '已显示分路侧数据：分路侧启用时各子界面右侧显示分路侧内容', 'ok');
    } catch (e) { toast('保存失败：' + e.message, 'err'); }
  });
  $('#btn-probe').addEventListener('click', probe);
  $('#btn-listfiles').addEventListener('click', listFiles);
  $('#btn-savecfg').addEventListener('click', saveConfig);
  $('#cfg-mapen').addEventListener('change', () => { syncColmapForm('bus'); markMapDirty('bus'); });
  $('#btn-map-default').addEventListener('click', () => fillColmapDefault('bus'));
  $('#btn-map-fromprobe').addEventListener('click', () => fillColmapFromProbe('bus'));
  $('#btn-map-save').addEventListener('click', () => saveColumns('bus'));
  $('#br-mapen').addEventListener('change', () => { syncColmapForm('branch'); BR.dirty = true; });
  MAP_FIELDS.forEach(k => mapEl('branch', k).addEventListener('input', () => { BR.dirty = true; }));
  $('#btn-br-map-default').addEventListener('click', () => fillColmapDefault('branch'));
  $('#btn-br-map-fromprobe').addEventListener('click', () => fillColmapFromProbe('branch'));
  $('#btn-br-map-save').addEventListener('click', () => saveColumns('branch'));
  $('#btn-selftest').addEventListener('click', runSelftest);
  ['sp-chan', 'sp-scale', 'sp-limit'].forEach(id => $('#' + id).addEventListener('change', render));
  // 数据源下拉框联动：选 kind 切换可用字段与填写说明；选 frame=binary 才放开 struct 两项
  $('#src-kind').addEventListener('change', () => { S.srcDirty = true; S.formDirty = true; syncSourceForm(); });
  $('#src-frame').addEventListener('change', () => { S.srcDirty = true; S.formDirty = true; syncSourceForm(); });
  $('#src-customtime').addEventListener('change', () => { S.srcDirty = true; S.formDirty = true; syncSourceForm(); });
  // 「保存曲线」勾选（面板标题处 + 导出页列表，动态生成 → 事件委托）
  document.addEventListener('change', (ev) => {
    const el = ev.target;
    if (el && el.classList && el.classList.contains('curve-save')) setCurveSave(el.dataset.curve, el.checked, el.dataset.side);
    if (el && el.classList && el.classList.contains('ser-vis')) setSeriesVisible(el.dataset.chart, el.dataset.name, el.checked);
  });
  $('#src-playmode').addEventListener('change', () => { S.srcDirty = true; S.formDirty = true; syncSourceForm(); });
  $('#src-file-speed').addEventListener('change', () => { S.fileSpeedChosen = parseFloat($('#src-file-speed').value) || 0; });
  // 任何用户输入都置脏：否则 0.2s 一次的推送会把正在编辑的字段改回服务端配置
  $$('#view-source input, #view-source select').forEach((el) => {
    if (el.id.startsWith('br-')) return;                       // 分路侧面板有自己的脏标记（BR.dirty）
    const mark = () => { S.formDirty = true; if (el.id.startsWith('cfg-')) S.cfgDirty = true; else S.srcDirty = true; };
    el.addEventListener('input', mark);
    el.addEventListener('change', mark);
  });
  $$('input[name=hmode-u],input[name=hmode-i]').forEach(el => el.addEventListener('change', render));
  $$('input[name=ihmode-u],input[name=ihmode-i]').forEach(el => el.addEventListener('change', render));
  $$('input[name=dcmode]').forEach(el => el.addEventListener('change', render));
  // 事件子界面
  bindSideViews('bus');
  window.addEventListener('resize', () => { clearTimeout(window._rz); window._rz = setTimeout(render, 180); });
  setInterval(() => { refreshBranchDual(false); }, 1000);
  setInterval(() => {
    if (['overview', 'power_factor', 'fundamental', 'harmonic', 'interharmonic', 'dc'].includes(S.view)) refreshHistory();
    if (S.view === 'events') refreshEvents('bus');     // 摘要（计数/振荡评估/落盘行数）随数据刷新；分路侧列由 refreshBranchDual 刷新
    if (S.view === 'source' && ($('#br-enabled') || {}).checked) refreshBranchState(true);   // 分路侧数据源状态栏
    if (S.view === 'nilm') { refreshNilm('bus'); refreshHistory(); }   // 周波窗、事件与 P/Q/S 趋势随数据刷新
  }, 3000);
}



/* ------------------------------------------------------------------ 负荷辨识（第 12 轮） */

/* NL：当前侧别的负荷辨识状态（SD[side].nl 的别名，随 sideOf() 变化） */
function NLs(side) { return SD[side || sideOf()].nl; }
const NILM_ALGOS = {
  threshold:    { name: '阈值差分', desc: '相邻周波 Δ ≥ 门槛为起点；随后 settle 个周波极差 ≤ 容差为终点',
                  params: { min_delta_w: '最小幅值 (W · P口径)', min_delta_a: '最小幅值 (A · I口径)', settle_cycles: '稳定周波数', settle_tol_w: '稳定容差 (W · P口径)', settle_tol_a: '稳定容差 (A · I口径)', max_rise_cycles: '最长暂态 (周波)' } },
  two_window:   { name: '双滑窗均值差', desc: '|mean(后窗) − mean(前窗)| 的局部极大值 ≥ 门槛且 ≥ k×前窗σ',
                  params: { pre_cycles: '前窗 (周波)', post_cycles: '后窗 (周波)', min_delta_w: '最小幅值 (W · P口径)', min_delta_a: '最小幅值 (A · I口径)', k_sigma: 'k×σ 倍数' } },
  cusum:        { name: 'CUSUM 累积和', desc: '双侧 Page CUSUM：相对参考均值的累积偏差 > h 触发；起点＝累积量最后归零处',
                  params: { drift_w: '允许漂移 k (W · P口径)', drift_a: '允许漂移 k (A · I口径)', threshold_w: '触发门限 h (W · P口径)', threshold_a: '触发门限 h (A · I口径)', min_delta_w: '最小幅值 (W · P口径)', min_delta_a: '最小幅值 (A · I口径)', settle_cycles: '稳定周波数' } },
  glr:          { name: 'GLR 广义似然比', desc: '高斯均值突变的对数似然比 n/4·(m1−m0)²/σ² ≥ 门限',
                  params: { window_cycles: '单侧窗 (周波)', threshold: '似然比门限', min_delta_w: '最小幅值 (W · P口径)', min_delta_a: '最小幅值 (A · I口径)', noise_w: '噪声 σ 下限 (W · P口径)', noise_a: '噪声 σ 下限 (A · I口径)', settle_cycles: '终点偏移 (周波)' } },
  steady_state: { name: '稳态分段 (Hart)', desc: '连续 ≥ N 个周波极差 ≤ 容差为稳态；相邻稳态均值差 ≥ 门槛即事件',
                  params: { tol_w: '稳态容差 (W · P口径)', tol_a: '稳态容差 (A · I口径)', min_steady_cycles: '最少稳态周波', min_delta_w: '最小幅值 (W · P口径)', min_delta_a: '最小幅值 (A · I口径)', max_transient_cycles: '最长暂态 (周波)' } },
  median_diff:  { name: '中值滤波差分', desc: '先 N 点中值滤波去尖峰，再做阈值差分（对单周波尖峰/缺口不敏感）',
                  params: { median_cycles: '中值窗 (周波)', min_delta_w: '最小幅值 (W · P口径)', min_delta_a: '最小幅值 (A · I口径)', settle_cycles: '稳定周波数', settle_tol_w: '稳定容差 (W · P口径)', settle_tol_a: '稳定容差 (A · I口径)', max_rise_cycles: '最长暂态 (周波)' } },
  // v0.90：设备画像匹配（多特征；对象固定为三相合成；画像文件由数据处理页「设备画像提取」生成）
  profile:      { name: '设备画像匹配', desc: '稳健双滑窗找候选 → 事件前后 ΔIa/ΔIb/ΔIc/ΔP/ΔQ/峰值比/持续周波 与启动/停止画像的对角马氏距离 D² → 置信度 exp(−D²/2d)，低于门槛拒识；设备状态机（OFF→启动 / ON→停止）；输出设备 ID、方向、观测幅值、置信度，不估计设备贡献幅值',
                  params: { d2_max: 'D² 上限 (每维均值)', min_confidence: '最低置信度 (0~1)', k_sigma: '候选门槛 k×σ', margin: '最优/次优 D² 比下限', lambda_rel: '协方差收缩系数', state_check: '状态机 (1 启用 / 0 关闭)', phase_map: '相序映射 (1 ABC·2 ACB·3 BAC·4 BCA·5 CAB·6 CBA·0 自动)' } },
};
const NILM_COLORS = { threshold: '#ff6b6b', two_window: '#ffa94d', cusum: '#ffd43b', glr: '#69db7c', steady_state: '#4dabf7', median_diff: '#da77f2', profile: '#63e6be' };
const NILM_FIELDS = ['enabled', 'save', 'quantity', 'window_cycles', 'min_gap_cycles', 'rel_tol_pct', 'min_delta_pct', 'auto_params', 'profile_path'];   // v0.87：auto_params；v0.90：profile_path（文本）
const NILM_CH = ['total', 'A', 'B', 'C'];

function buildNilmForm(side = sideOf()) {
  const nl = NLs(side);
  if (nl.formBuilt) return;
  nl.formBuilt = true;
  const host = E(side, 'nilm-algos');
  host.innerHTML = Object.keys(NILM_ALGOS).map(a => {
    const sp = NILM_ALGOS[a];
    const inputs = Object.keys(sp.params).map(k =>
      `<label class="${k.endsWith('_w') ? 'nilm-unit-w' : (k.endsWith('_a') ? 'nilm-unit-a' : '')}">${sp.params[k]}<input type="number" step="any" min="0" id="nilm-${a}-${k}"></label>`).join('');
    // v0.90：画像匹配额外有画像文件路径（文本，nilm.profile_path）与加载状态
    // v0.99.3：画像匹配的检测对象 / 检测量不可指定——对象固定为三相合成 total（候选按 ΣP 或三相电流合成量搜索，事件 channel=total），检测量随画像文件口径（p/i），须与本侧 nilm.quantity 一致；此处以只读项固定展示
    const extra = a === 'profile' ? `<div class="row2"><label class="f" style="grid-column:1/-1"><span class="lbl">画像文件路径</span><input type="text" id="nilm-profile_path" placeholder="output/nilm/profile_<设备>_<时间>.json"><span class="note">nilm.profile_path；相对仓库根；数据处理页「设备画像提取」生成</span></label>
      <label class="f nilm-fixed" title="画像匹配不支持按相检测：候选按三相合成量（P 口径＝ΣP，I 口径＝三相电流合成）搜索，事件对象固定为 total；上方「检测对象」勾选对本算法不生效"><span class="lbl">检测对象（固定）</span><input type="text" value="三相总 total（固定，不可选）" disabled><span class="note">上方「检测对象」勾选只作用于其它算法</span></label>
      <label class="f nilm-fixed" title="画像匹配的检测量由画像文件决定（提取时的 quantity：p 有功 / i 电流），且必须与本侧「检测量」实际口径一致，否则 ΔP/ΔI 不可比、画像匹配不运行"><span class="lbl">检测量（固定）</span><input type="text" id="nilm-profile-qty" value="随画像文件（加载后显示）" disabled><span class="note">须与本侧「检测量」实际口径一致，不一致时不运行并在状态行提示</span></label></div><div id="nilm-profile-state" class="mut" style="font-size:12px"></div>` : '';
    // v0.26.1：标题行＝色块 + 勾选框 + 算法名（紧挨），算法说明单独一行
    return `<div class="panel nilm-algo" data-algo="${a}" style="margin-top:8px"><h3 class="algohdr"><label class="check"><input type="checkbox" id="nilm-${a}-enabled"><span class="sw" style="color:${NILM_COLORS[a]}">■</span>${sp.name}</label></h3>
      <div class="algodesc mut">${sp.desc}</div>
      ${extra}<div class="row2">${inputs}</div></div>`;
  }).join('');
  normalizeConfigForms(host);
  const opts = Object.keys(NILM_ALGOS).map(a => `<option value="${a}">${NILM_ALGOS[a].name}</option>`).join('');
  E(side, 'nilm-filter').insertAdjacentHTML('beforeend', opts); domTouched(E(side, 'nilm-filter'));
  E(side, 'nilm-mark').insertAdjacentHTML('beforeend', opts); domTouched(E(side, 'nilm-mark'));
  // P/Q/S 趋势图的「标注算法」多选：默认全部勾选
  const pa = E(side, 'nilm-pqs-algos');
  if (pa) { pa.innerHTML = Object.keys(NILM_ALGOS).map(a => `<label title="${NILM_ALGOS[a].desc}"><input type="checkbox" class="nilm-pqs-algo" data-algo="${a}" checked> <span style="color:${NILM_COLORS[a]}">■</span>${NILM_ALGOS[a].name}</label>`).join(''); domTouched(pa); }
  bindNilmForm(side);
}

function bindNilmForm(side) {
  [E(side, 'nilm-form'), E(side, 'nilm-algos')].forEach(h => h && h.querySelectorAll('input, select').forEach(el => {
    const mark = () => { NLs(side).dirty = true; }; el.addEventListener('input', mark); el.addEventListener('change', mark);
  }));
  const q = E(side, 'nilm-quantity'); if (q) q.addEventListener('change', () => nilmDimUnits(side));
  const ap = E(side, 'nilm-auto_params'); if (ap) ap.addEventListener('change', () => nilmDimUnits(side));
  // v0.88：自适应参数两侧均可启用（v0.87 曾隐藏分路侧勾选）
}

/* v0.87：自适应模式下灰显会被自动推导覆盖的数值项（算法启停勾选保持可用），并显示最近一次推导出的参数 */
function nilmDimAuto(side = sideOf()) {
  const ap = E(side, 'nilm-auto_params'); const host = E(side, 'nilm-algos'); if (!host) return;
  const on = !!(ap && ap.checked);                                      // v0.88.1：两侧一致（v0.87 曾排除分路侧）
  // 被自适应覆盖的数值项：灰显 + disabled（不可手动设置；值仍随表单保存，仅检测时不参与）
  const dim = l => { l.classList.toggle('nilm-auto-off', on); l.querySelectorAll('input, select').forEach(el => { el.disabled = on; }); };
  host.querySelectorAll('label').forEach(l => { const pa = l.closest('.nilm-algo'); if (!l.querySelector('input[type=checkbox]') && !(pa && pa.dataset.algo === 'profile')) dim(l); });   // v0.90：画像匹配参数不由自适应推导
  ['nilm-rel_tol_pct', 'nilm-min_delta_pct'].forEach(id => { const el = E(side, id); const l = el && el.closest('label'); if (l) dim(l); });
  const out = E(side, 'nilm-auto-out'); if (!out) return;
  const sm = NLs(side).summary || {};
  const al = sm.auto_last || {};
  if (!on || !Object.keys(al).length) { out.style.display = on ? '' : 'none'; out.innerHTML = on ? '自适应算法参数已启用：等待周波窗数据（窗内不足 60 个有效周波时暂不评估；逐位重复数据需 ≥ 60×保持长度）' : ''; return; }
  const names = sm.algorithm_names || {};
  const f = v => (typeof v === 'number' ? (Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 1 ? v.toFixed(2) : v.toPrecision(3)) : v);
  const SHOW = { threshold: ['min_delta_w', 'settle_cycles', 'settle_tol_w', 'max_rise_cycles'], two_window: ['pre_cycles', 'post_cycles', 'min_delta_w', 'k_sigma'],
                 cusum: ['drift_w', 'threshold_w', 'min_delta_w', 'settle_cycles'], glr: ['window_cycles', 'threshold', 'min_delta_w', 'noise_w', 'settle_cycles'],
                 steady_state: ['tol_w', 'min_steady_cycles', 'min_delta_w', 'max_transient_cycles'], median_diff: ['median_cycles', 'min_delta_w', 'settle_cycles', 'settle_tol_w', 'max_rise_cycles'] };
  let h = '<b>自适应算法参数（最近一次评估，由当前周波窗数据推导）</b>';
  Object.keys(al).forEach(ch => {
    const a = al[ch] || {}; const st = a.stats || {}; const u = a.unit || 'W';
    h += `<div style="margin-top:4px"><b>${ch === 'total' ? '三相总' : ch + ' 相'}</b>（${a.quantity === 'i' ? 'I' : 'P'}，${u}）：σ=${f(st.sigma)} ${u} · 保持长度=${st.hold || 1} · 稳定周波=${st.settle} · 最短稳态=${st.min_steady} · 最长暂态=${st.transient} · k=${f(st.k)} · 最小幅值=${f(st.min_delta)} ${u} · 窗=${st.n} 周波</div>`;
    h += '<table style="margin-top:2px"><tbody>' + Object.keys(a.algorithms || {}).map(al2 => {
      const prm = a.algorithms[al2] || {};
      return `<tr><td>${names[al2] || al2}</td><td>${(SHOW[al2] || Object.keys(prm)).filter(k => prm[k] !== undefined).map(k => `${k.replace(/_w$/, '')}=${f(prm[k])}`).join('  ')}</td></tr>`;
    }).join('') + '</tbody></table>';
  });
  out.style.display = ''; out.innerHTML = h;
}

/* v0.37：按检测量灰显不参与的那套阈值（auto 时按服务端 summary.quantity_effective；未知时两套都亮） */
function nilmDimUnits(side = sideOf(), effective) {
  const host = E(side, 'nilm-algos'); const sel = E(side, 'nilm-quantity'); if (!host) return;
  let q = sel ? sel.value : 'auto';
  if (q === 'auto') q = effective || (NLs(side).summary && NLs(side).summary.quantity_effective) || '';
  host.querySelectorAll('.nilm-unit-w').forEach(el => el.classList.toggle('nilm-inactive', q === 'i'));
  host.querySelectorAll('.nilm-unit-a').forEach(el => el.classList.toggle('nilm-inactive', q === 'p'));
  // v0.39：I 口径没有跨相合并，只能单相检测——「三相总」灰显（仍可勾选保存，检测器忽略）
  const tl = E(side, 'nilm-ch-total-lbl'); if (tl) tl.classList.toggle('nilm-inactive', q === 'i');
  nilmDimAuto(side);
}

function fillNilmForm(nc, side = sideOf()) {
  if (!nc || NLs(side).dirty) { nilmDimUnits(side); return; }
  NILM_FIELDS.forEach(f => {
    const el = E(side, `nilm-${f}`); if (!el) return;
    if (el.type === 'checkbox') el.checked = !!nc[f]; else el.value = nc[f];
  });
  NILM_CH.forEach(c => { const el = E(side, `nilm-ch-${c}`); if (el) el.checked = (nc.channels || []).includes(c); });
  const algos = nc.algorithms || {};
  Object.keys(NILM_ALGOS).forEach(a => {
    const prm = algos[a] || {};
    const en = E(side, `nilm-${a}-enabled`); if (en) en.checked = prm.enabled !== false;
    Object.keys(NILM_ALGOS[a].params).forEach(k => { const el = E(side, `nilm-${a}-${k}`); if (el && prm[k] !== undefined) el.value = prm[k]; });
  });
  nilmDimUnits(side);
  nilmProfileState(side);
}

/* v0.90：画像匹配面板下的加载状态行（来自 summary.profile） */
function nilmProfileState(side = sideOf()) {
  const el = E(side, 'nilm-profile-state'); if (!el) return;
  const pf = (NLs(side).summary || {}).profile;
  const qel = E(side, 'nilm-profile-qty');   // v0.99.3：固定检测量展示＝画像文件口径
  if (qel) { const s0 = (pf && pf.loaded && pf.summary) || null; qel.value = s0 ? (s0.quantity === 'p' ? 'p 有功功率 P（画像文件口径，固定）' : s0.quantity === 'i' ? 'i 电流有效值 I（画像文件口径，固定）' : `${s0.quantity || s0.unit || '?'}（画像文件口径，固定）`) : '随画像文件（加载后显示）'; }
  if (!pf) { el.textContent = ''; return; }
  if (!pf.path) { el.textContent = '未设置画像文件路径。'; return; }
  if (pf.error) { el.innerHTML = `<span class="bad">${esc(pf.error)}</span>`; return; }
  if (!pf.loaded) { el.textContent = `画像未加载（${esc(pf.path)}）`; return; }
  const s = pf.summary || {}; const g = k => (s[k] ? `${s[k].n} 次` : '无');
  el.innerHTML = `已加载：设备 <b>${esc(s.device_id || '')}</b>（${esc(s.unit || '')} 口径，启动样本 ${g('startup')} / 停止样本 ${g('shutdown')}，前后窗 ${s.pre_cycles}/${s.post_cycles} 周波，${esc(s.created || '')}）· 设备状态 ${esc(pf.device_state || 'unknown')}`
    + ((pf.last || []).length ? `<br>最近候选：${pf.last.slice(-5).map(c => `${esc(c.t_start_local || '')} ${c.direction} D²/d=${c.d2_per_dim} 置信 ${(c.confidence * 100).toFixed(0)}% ${c.status}${c.flags && c.flags.length ? '[' + c.flags.join(',') + ']' : ''}`).join('；')}` : '');
}

function collectNilmPayload(side = sideOf()) {
  const p = { algorithms: {} };
  NILM_FIELDS.forEach(f => { const el = E(side, `nilm-${f}`); if (!el) return; p[f] = el.type === 'checkbox' ? el.checked : ((el.tagName === 'SELECT' || el.type === 'text') ? el.value : +el.value); });
  p.channels = NILM_CH.filter(c => { const el = E(side, `nilm-ch-${c}`); return el && el.checked; });
  Object.keys(NILM_ALGOS).forEach(a => {
    const prm = { enabled: !!E(side, `nilm-${a}-enabled`).checked };
    Object.keys(NILM_ALGOS[a].params).forEach(k => { const v = parseFloat(E(side, `nilm-${a}-${k}`).value); if (Number.isFinite(v)) prm[k] = v; });
    p.algorithms[a] = prm;
  });
  return p;
}

async function saveNilmConfig(side = sideOf()) {
  const payload = collectNilmPayload(side);
  const note = E(side, 'nilm-form-note');
  if (!payload.channels.length) { toast('至少勾选一个检测对象', 'err'); return; }
  const lim = { rel_tol_pct: [0, 50], min_delta_pct: [0, 100], window_cycles: [30, 1e9], min_gap_cycles: [0, 1e9] };
  for (const [k, [lo, hi]] of Object.entries(lim)) {
    const v = payload[k];
    if (!isNum(v) || v < lo || v > hi) {
      const msg = `${k} 必须在 ${lo}~${hi === 1e9 ? '∞' : hi}（当前 ${v}）；` + (k.endsWith('_pct') ? '它是「占窗内 |P| 中位数的百分比」，不是 W；只用绝对值请填 0' : '');
      note.textContent = '保存失败：' + msg; toast(msg, 'err');
      const el = E(side, `nilm-${k}`); if (el) el.focus();
      return;
    }
  }
  try {
    const d = await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nilm: payload }) }, side);
    NLs(side).dirty = false; note.textContent = '已保存并热生效 ' + new Date().toLocaleTimeString();
    toast((side === 'branch' ? '分路侧' : '总线侧') + '负荷辨识参数已保存', 'ok');
    if (d && d.config) {
      if (side === 'branch') { if (BRD.state) BRD.state.config = d.config; BR.loaded = false; } else if (S.state) S.state.config = d.config;
      fillNilmForm(d.config.nilm, side);
    }
    refreshNilm(side);
  } catch (e) { note.textContent = '保存失败：' + e.message; toast(e.message, 'err'); }
}

async function applyNilmTune(side = sideOf()) {
  // v0.50：把 nilm_tune.py --json 的输出叠加到当前运行配置（POST /api/nilm/tune/apply）；默认不写配置文件
  const fi = E(side, 'nilm-tune-file'), note = E(side, 'nilm-tune-note');
  const f = fi && fi.files && fi.files[0];
  if (!f) { toast('请先选择 nilm_tune.py --json 输出的 JSON 文件', 'err'); return; }
  let params;
  try { params = JSON.parse(await f.text()); } catch (e) { note.textContent = '不是合法 JSON：' + e.message; toast(note.textContent, 'err'); return; }
  const persist = !!(E(side, 'nilm-tune-persist') || {}).checked;
  try {
    const d = await api('/api/nilm/tune/apply', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ params, hot: true, persist }) }, side);
    if (d && d.config) {
      if (side === 'branch') { if (BRD.state) BRD.state.config = d.config; BR.loaded = false; } else if (S.state) S.state.config = d.config;
      fillNilmForm(d.config.nilm, side);
    }
    NLs(side).dirty = false;
    note.textContent = `已套用 ${d.changes.length} 项并热生效，配置已保存到 ${d.saved_to}` + (d.config_file_updated ? '（配置文件已回写）' : '（配置文件未改动）');
    toast((side === 'branch' ? '分路侧' : '总线侧') + '已套用调参结果', 'ok');
    refreshNilm(side);
  } catch (e) { note.textContent = '套用失败：' + e.message; toast(e.message, 'err'); }
}

function onNilmPush(list, side = 'bus') {
  const nl = NLs(side);
  list.forEach(e => { if (!nl.events.some(x => x.id === e.id)) nl.events.unshift(e); });
  if (!nilmMarkAll(side) && nl.events.length > 5000) nl.events.length = 5000;   // v0.89：标注全部事件时不截断
  setNilmBadge(nl.summary ? (nl.summary.total || 0) + list.length : nl.events.length, side);
  if (S.view === 'nilm') render();
}

function setNilmBadge(n, side) {
  const b = document.getElementById((side || sideOf()) === 'branch' ? 'nav-nilm-badge-br' : 'nav-nilm-badge'); if (!b) return;
  b.textContent = String(n); b.style.display = n > 0 ? '' : 'none';
}

async function refreshNilm(side = sideOf()) {
  const nl = NLs(side);
  try {
    // v0.48：事件始终全量拉取；事件列表的「算法 / 对象」筛选只在渲染表格时做（nl.events 同时供趋势图与周波窗画事件竖线，
    // 以前按筛选条件拉取会让列表筛选连带改变另外两个面板的竖线）
    const [d, c] = await Promise.all([
      api(`/api/nilm/events?limit=${nilmMarkAll(side) ? 0 : NILM_MARK_LIMIT}`, undefined, side),   // v0.89：标注全部事件时拉取全部
      api('/api/nilm/cycles?n=2000', undefined, side),
    ]);
    nl.events = d.events || []; nl.summary = d.summary || null; nl.cycles = c; nl.loaded = true;
  } catch (e) { toast((side === 'branch' ? '分路侧' : '') + '负荷辨识数据获取失败：' + e.message, 'err'); }
  if (S.view === 'nilm') render();
}

async function clearNilm(side = sideOf()) {
  try { await api('/api/nilm/clear', { method: 'POST' }, side); toast((side === 'branch' ? '分路侧' : '总线侧') + '负荷事件列表已清空', 'ok'); NLs(side).events = []; await refreshNilm(side); }
  catch (e) { toast(e.message, 'err'); }
}

/* v0.25：整表共用一组单位（按全部事件的最大值选前缀），表头带单位、单元格只放数字 */
/* v0.36：事件幅值按检测量口径——全部为电流口径（unit=A）时幅值列为 |ΔI|（A），否则 |ΔP|（W） */
function nilmMag(e) { return isNum(e.magnitude) && e.unit ? e.magnitude : e.magnitude_w; }
function nilmAllCurrent(events) { return events.length > 0 && events.every(e => e.unit === 'A'); }
function nilmScales(events) {
  const cur = nilmAllCurrent(events);
  return { cur, D: unitScale(events.map(nilmMag), cur ? 'A' : 'W', 3), P: unitScale(events.flatMap(e => [e.pre_p_w, e.post_p_w]), 'W', 3),
           Q: unitScale(events.map(e => e.delta_q_var), 'var', 3), I: unitScale(events.map(e => e.delta_i_a), 'A', 3) };
}
function nilmHeader(sc) {
  return ['#', '算法', '对象', '开始（数据时间）', '结束', '持续 (s)', '周波数', '方向', sc.D.hdr(sc.cur ? '幅值 |ΔI|' : '幅值 |ΔP|'), sc.Q.hdr('ΔQ'), sc.I.hdr('ΔI'), sc.P.hdr('事件前 P'), sc.P.hdr('事件后 P'), '检验量'];
}
function nilmRow(e, sc) {
  const dir = e.direction === 'up' ? '<span class="badge bad">↑ 投入</span>' : '<span class="badge">↓ 切除</span>';
  return [e.id, `<span style="color:${NILM_COLORS[e.algorithm] || '#fff'}">■</span> ${esc(e.algorithm_name || e.algorithm)}`, esc(e.channel),
          ts(e.t_start), ts(e.t_end), num(e.duration_s || 0, 2), e.cycles, dir,
          sc.D.f(nilmMag(e)), sc.Q.f(e.delta_q_var), sc.I.f(e.delta_i_a), sc.P.f(e.pre_p_w), sc.P.f(e.post_p_w),
          e.algorithm === 'profile' ? nilmProfileCell(e) : (isNum(e.score) ? num(e.score, 3) : '')];
}
/* v0.90：画像匹配事件的「检验量」列＝设备 ID · 置信度（D²，状态，质量标记） */
function nilmProfileCell(e) {
  const fl = e.quality_flags ? `，${esc(e.quality_flags)}` : '';
  const st = e.status === 'low_confidence' ? '<span class="badge">低置信</span>' : '';
  return `${esc(e.device_id || '?')} · ${isNum(e.confidence) ? (e.confidence * 100).toFixed(1) + '%' : ''} ${st}<span class="mut" title="D²=${isNum(e.d2) ? num(e.d2, 3) : ''}${fl}">(D²=${isNum(e.d2) ? num(e.d2, 2) : ''}${fl})</span>`;
}

/* v0.24：P/Q/S 趋势（与总览同一数据 /api/history/power、同一 pqsSeries）+ 各算法事件竖线 */
/* ------------------------------------------------------------------ v0.46：通用右键菜单（画布） */
const CTX_MENU_ID = 'ctxmenu';   // 动态创建、挂在 body 下的右键菜单（不在 index.html 里）
function closeCtxMenu() { const m = document.getElementById(CTX_MENU_ID); if (m) m.remove(); }
function showCtxMenu(x, y, items) {
  closeCtxMenu();
  const m = document.createElement('div'); m.id = CTX_MENU_ID; m.className = 'ctxmenu';
  items.forEach(it => {
    if (it.sep) { const hr = document.createElement('div'); hr.className = 'sep'; m.appendChild(hr); return; }
    const d = document.createElement('div'); d.className = 'mi' + (it.disabled ? ' disabled' : '');
    d.innerHTML = esc(it.label) + (it.hint ? `<small>${esc(it.hint)}</small>` : '');
    d.title = it.title || '';
    d.dataset.key = it.key || '';
    if (!it.disabled) d.addEventListener('click', (e) => { e.stopPropagation(); closeCtxMenu(); try { it.onClick(); } catch (err) { console.error(err); } });
    m.appendChild(d);
  });
  document.body.appendChild(m);
  const vw = window.innerWidth || 1200, vh = window.innerHeight || 800;
  const r = m.getBoundingClientRect();
  m.style.left = Math.max(0, Math.min(x, vw - (r.width || 220) - 4)) + 'px';
  m.style.top = Math.max(0, Math.min(y, vh - (r.height || 80) - 4)) + 'px';
  setTimeout(() => {
    const off = (e) => { if (!m.contains(e.target)) { closeCtxMenu(); document.removeEventListener('mousedown', off); } };
    document.addEventListener('mousedown', off);
  }, 0);
  document.addEventListener('keydown', function esc_(e) { if (e.key === 'Escape') { closeCtxMenu(); document.removeEventListener('keydown', esc_); } });
  return m;
}
/* 画布右键：itemsFn(epochX, info) → 菜单项；只绑定一次 */
function bindCtxMenu(cv, itemsFn) {
  if (!cv || cv.__ctxBound) return;
  cv.__ctxBound = true;
  cv.addEventListener('contextmenu', (e) => {
    if (e.shiftKey) return;                                  // v0.47：Shift+右键 ⇒ 不拦截，弹浏览器原生菜单
    e.preventDefault();
    const c = cv.__chart;
    let xEpoch = null, info = null;
    if (c) {
      const r = cv.getBoundingClientRect(); const mx = e.clientX - r.left;
      const tb = isNum(c.opt.tbase) ? c.opt.tbase : 0;
      info = hoverInfo(cv, mx);
      xEpoch = (info ? info.x : c.xAt(mx)) + tb;
    }
    const items = itemsFn(xEpoch, info, e) || [];
    if (items.length) showCtxMenu(e.clientX, e.clientY, items);
  });
}
window.showCtxMenu = showCtxMenu; window.closeCtxMenu = closeCtxMenu;
/* v0.47：画布右键菜单保留浏览器原生菜单对图片的三项功能（复制图片 / 图片另存为 / 在新标签页打开），再追加业务项；
   网页无法往浏览器原生菜单里加项，所以这里把原生功能复现在自定义菜单中，需要完整原生菜单时按 Shift+右键。 */
function canvasPngBlob(cv) { return new Promise((res) => { try { cv.toBlob((b) => res(b), 'image/png'); } catch (e) { res(null); } }); }
async function copyCanvasImage(cv) {
  const b = await canvasPngBlob(cv);
  if (!b) { toast('复制图片失败：画布为空', 'err'); return; }
  try {
    if (navigator.clipboard && window.ClipboardItem) { await navigator.clipboard.write([new window.ClipboardItem({ 'image/png': b })]); toast('图片已复制到剪贴板', 'ok'); return; }
  } catch (e) { /* 回退到下载 */ }
  saveCanvasImage(cv); toast('浏览器不支持直接复制图片，已改为下载 PNG', '');
}
function saveCanvasImage(cv, name) {
  try {
    const a = document.createElement('a'); a.href = cv.toDataURL('image/png');
    a.download = (name || cv.id || 'chart') + '_' + fmtLocalInput(Date.now() / 1000).replace(/[^\d]/g, '').slice(0, 14) + '.png';
    document.body.appendChild(a); a.click(); a.remove();
  } catch (e) { toast('保存图片失败：' + e.message, 'err'); }
}
function openCanvasImage(cv) {
  try { const w = window.open(); if (w) { w.document.write(`<title>${esc(cv.id || 'chart')}</title><img src="${cv.toDataURL('image/png')}" style="max-width:100%">`); w.document.close(); } else { toast('浏览器拦截了新标签页', 'err'); } }
  catch (e) { toast('打开图片失败：' + e.message, 'err'); }
}
function canvasNativeItems(cv) {
  return [
    { key: 'copy-image', label: '复制图片', onClick: () => copyCanvasImage(cv) },
    { key: 'save-image', label: '图片另存为…', onClick: () => saveCanvasImage(cv) },
    { key: 'open-image', label: '在新标签页中打开图片', onClick: () => openCanvasImage(cv) },
  ];
}

/* v0.46：周波窗手动装载（非运行状态；从当前侧配置的离线文件读） */
function curRunning(side = sideOf()) { const st = (side === 'branch' ? BRD.state : S.state) || {}; return !!st.running; }
function fmtLocalInput(t) {
  const d = new Date(t * 1000); const p = (n, w = 2) => String(n).padStart(w, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${p(d.getMilliseconds(), 3)}`;
}
async function loadNilmWindow(side = sideOf(), tEpoch, nCycles) {
  const nl = NLs(side);
  if (curRunning(side)) { toast('引擎运行中：请先停止数据源，再装载周波窗（运行中周波窗显示实时数据）', 'err'); return false; }
  const tEl = E(side, 'nilm-win-t'), nEl = E(side, 'nilm-win-count');
  let tTxt = tEpoch !== undefined && tEpoch !== null ? String(tEpoch) : ((tEl && tEl.value) || '').trim();
  const n = Math.max(1, Math.min(20000, parseInt((nCycles !== undefined ? nCycles : (nEl && nEl.value)) || '300', 10) || 300));
  if (tEpoch !== undefined && tEpoch !== null && tEl) tEl.value = fmtLocalInput(tEpoch);
  try {
    const d = await api(`/api/nilm/cycles_file?n=${n}${tTxt ? '&t=' + encodeURIComponent(tTxt) : ''}`, undefined, side);
    nl.winFile = d; nl.winFileAt = Date.now();
    const sname = (d.source && d.source.path) ? d.source.path.split(/[\\/]/).pop() : '';
    toast(`${side === 'branch' ? '分路侧' : '总线侧'}已装载 ${d.source.n_loaded} 个周波（${sname}${d.source.mode === 'center' ? '，中心 ' + ts(d.source.t_center) : '，数据起点起'}）` + (d.source.note ? '；' + d.source.note : ''), 'ok');
    if (S.view === 'nilm') render();
    return true;
  } catch (e) { toast('装载周波窗失败：' + e.message, 'err'); return false; }
}
function clearNilmWindow(side = sideOf()) { const nl = NLs(side); nl.winFile = null; if (S.view === 'nilm') render(); }
/* v0.65：周波窗 2（瞬时值）——趋势曲线右键，从本侧配置的离线文件读取以 tEpoch 为中心 n 个周波的原始采样，画到单独的「周波窗 2」曲线 */
async function loadNilmWave2(side = sideOf(), tEpoch, nCycles) {
  const nl = NLs(side);
  const n = Math.max(1, Math.min(20000, parseInt(nCycles || '300', 10) || 300));
  try {
    const d = await api(`/api/nilm/wave_file?n=${n}${isNum(tEpoch) ? '&t=' + encodeURIComponent(String(tEpoch)) : ''}`, undefined, side);
    d.cyc_center = tEpoch; d.cyc_n = n; nl.wave2 = d;
    const sname = (d.source && d.source.path) ? d.source.path.split(/[\\/]/).pop() : '';
    toast(`${side === 'branch' ? '分路侧' : '总线侧'}周波窗 2 已装载 ${d.n} 点 × ${(d.channels_loaded || []).length} 通道（${sname}，中心 ${fmtLocalInput(tEpoch)}，${n} 个周波，采样瞬时值）`, 'ok');
    if (S.view === 'nilm') { render(); try { $('#nilm-wave2').scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } catch (e) { /* jsdom */ } }
    return true;
  } catch (e) { toast('装载周波窗 2 失败：' + e.message, 'err'); return false; }
}
function renderNilmWave2(nl) {
  const cv = $('#nilm-wave2'); if (!cv) return;
  const sub = $('#nilm-wave2-sub'); const d = nl.wave2;
  if (!d || !d.t || !d.t.length) {
    drawLine(cv, [], { empty: '在上方趋势曲线上右键「显示周波窗 2」后显示（以该时刻为中心的 N 个周波采样瞬时值，从本侧离线文件读取）', height: 240 });
    if (sub) sub.textContent = '（在趋势曲线上右键「显示周波窗 2」后显示：以该时刻为中心的 N 个周波采样瞬时值，而不是逐周波计算值）';
    return;
  }
  const t0 = d.t[0]; const chans = d.channels_loaded || Object.keys(d.channels || {});
  const hasU = chans.some(c => c[0] === 'U'), hasI = chans.some(c => c[0] === 'I');
  drawLine(cv, chans.map(ch => ({ name: `${ch} (${(d.units || {})[ch] || ''})`, color: WP_COLORS[ch] || '#4ea1ff', data: d.t.map((x, i) => [x - t0, d.channels[ch][i]]) })),
    { ylabel: hasU && hasI ? 'V / A' : hasU ? 'V' : 'A', fmtX: x => ts(x + t0), fmtTip: x => fmtLocalInput(x + t0), tbase: t0, height: 240, zero: true });
  if (sub) sub.textContent = `（${d.n} 点 × ${chans.length} 通道 · ${d.fs} Hz · ${fmtLocalInput(t0)} → ${fmtLocalInput(d.t[d.t.length - 1])}，中心 ${fmtLocalInput(d.cyc_center)}，${d.cyc_n} 个周波 · 采样瞬时值 · ${(d.source || {}).path || ''}）`;
  bindCtxMenu(cv, () => canvasNativeItems(cv).concat([{ key: 'sep', sep: true }, { key: 'zoom-reset', label: '复位缩放', onClick: () => zoomReset(cv) },
    { key: 'native', label: '浏览器原生菜单（Shift + 右键）', disabled: true }]));
}
function nilmWinSourceText(nl, running) {
  if (running) return nl.winFile ? '引擎运行中：显示实时周波窗（手动装载的数据已暂存，停止后恢复显示）' : '';
  if (!nl.winFile) return '当前显示引擎最近一次运行的周波窗；可装载离线文件任意时刻的周波数据（或在趋势曲线上右键「显示周波窗」）';
  const sr = nl.winFile.source || {};
  return `已装载：${(sr.path || '').split(/[\\/]/).pop()} · ${sr.mode === 'center' ? '中心 ' + fmtLocalInput(sr.t_center) : '数据起点起'} · ${sr.n_loaded} 个周波（${ts(sr.t_start)} ~ ${ts(sr.t_end)}）` + (sr.note ? ' · ' + sr.note : '');
}

/* v0.39：趋势图可切换为三相电流（Ia/Ib/Ic 可选）；auto = 按检测量（I 口径画电流） */
function nilmPqsKind(nl) {
  const sel = $('#nilm-pqs-kind'); const v = sel ? sel.value : 'auto';
  if (v !== 'auto') return v;
  return (nl.summary && nl.summary.quantity_effective === 'i') ? 'i' : 'pqs';
}
/* v0.40：三相的显示/隐藏统一用曲线下方的图例勾选（与其它趋势图一致），不再在标题栏重复放一组勾选框 */
function nilmCurrentSeries(hi, t0) {
  return ['A', 'B', 'C'].map(ph => ({ name: 'I' + ph.toLowerCase(), color: COLORS[ph], data: hi.map(p => [p.t - t0, p['I' + ph.toLowerCase()]]) }));
}
/* v0.89：曲线上标注的事件条数限制——默认只标注最近 NILM_MARK_LIMIT 条；勾选「标注全部事件」则全部标注 */
const NILM_MARK_LIMIT = 1000;
function nilmMarkAll(side = sideOf()) { const el = E(side, 'nilm-mark-all'); return !!(el && el.checked); }
function nilmMarkPool(nl, side = sideOf()) { const evs = nl.events || []; return nilmMarkAll(side) || evs.length <= NILM_MARK_LIMIT ? evs : evs.slice(0, NILM_MARK_LIMIT); }   // 事件按 id 倒序＝最近在前
function renderNilmPqs(nl) {
  const cv = $('#nilm-pqs'); if (!cv) return;
  const kind = nilmPqsKind(nl); const isI = kind === 'i';
  const hp = isI ? curHist('current') : curHist('power'); const t0 = hp.length ? hp[0].t : 0;
  const ttl = $('#nilm-pqs-title'); if (ttl) ttl.textContent = isI ? '三相电流 I 趋势' : 'P / Q / S 趋势';
  const sp = cv.parentElement && cv.parentElement.querySelector('.curvespan'); if (sp) { sp.dataset.curve = isI ? 'current' : 'power'; sp.textContent = curveSpanText(sp.dataset.curve, sp.dataset.side); }
  const box = $('#nilm-pqs-algos');
  const chosen = box ? Array.from(box.querySelectorAll('.nilm-pqs-algo')).filter(c => c.checked).map(c => c.dataset.algo) : Object.keys(NILM_ALGOS);
  const chSel = $('#nilm-pqs-ch'); const ch = chSel ? chSel.value : '';
  const tEnd = hp.length ? hp[hp.length - 1].t : 0;
  const evs = nilmMarkPool(nl).filter(e => chosen.includes(e.algorithm) && (!ch || e.channel === ch) && isNum(e.t_start) && e.t_start >= t0 && e.t_start <= tEnd);
  const marks = evs.map(e => ({ x: e.t_start - t0, color: NILM_COLORS[e.algorithm], row: Object.keys(NILM_ALGOS).indexOf(e.algorithm),
                                label: `${e.direction === 'up' ? '↑' : '↓'}${si(nilmMag(e), e.unit || 'W', 3)}${ch ? '' : ' ' + e.channel}` }));
  const nEl = $('#nilm-pqs-n'); if (nEl) nEl.textContent = String(marks.length);
  const pEl = $('#nilm-pqs-pool'); if (pEl) pEl.textContent = nilmMarkAll() ? `全部 ${(nl.events || []).length} 条` : `最近 ${NILM_MARK_LIMIT} 条`;
  drawLine(cv, isI ? nilmCurrentSeries(hp, t0) : pqsSeries(hp, t0),
           { ylabel: isI ? 'A' : 'W/var/VA', fmtX: x => tsX(x + t0, spanOf(isI ? 'current' : 'power')), fmtTip: x => ts(x + t0), tbase: t0, height: 260, marks,
             empty: isI ? '暂无电流趋势（需累计 ≥2 个 current 窗）' : '暂无 P/Q/S 趋势（需累计 ≥2 个 power 窗）' });
  const side = sideOf();
  bindCtxMenu(cv, (xEpoch) => {
    const running = curRunning(side);
    const nEl = E(side, 'nilm-win-count'); const n = parseInt((nEl && nEl.value) || '300', 10) || 300;
    const noX = !isNum(xEpoch);
    const stx = (side === 'branch' ? BRD.state : S.state) || {}; const srcKind = ((stx.config || {}).source || {}).kind || '';
    const isFile = srcKind === 'csv_file';                    // v0.66：周波窗 2 只对离线文件源可选
    return canvasNativeItems(cv).concat([                   // v0.47：原生菜单项在前、保持不变，业务项追加在后
      { key: 'sep', sep: true },
      { key: 'show-window', label: `显示周波窗（${noX ? '暂无曲线' : fmtLocalInput(xEpoch)}）`, disabled: running || noX,
        hint: running ? '引擎运行中不可用：请先停止数据源' : noX ? '趋势曲线有数据后，在曲线上右键' : `以该时刻为中心装载 ${n} 个周波（离线文件）`,
        onClick: () => loadNilmWindow(side, xEpoch, n) },
      { key: 'show-window2', label: `显示周波窗 2（瞬时值，${noX ? '暂无曲线' : fmtLocalInput(xEpoch)}）`, disabled: noX || !isFile,     // v0.65 / v0.66：仅离线文件源可选
        hint: !isFile ? `当前输入方式为 ${srcKind || '—'}：周波窗 2 只能从离线文件（csv_file）读取瞬时值，实时源不可用` : noX ? '趋势曲线有数据后，在曲线上右键' : `以该时刻为中心从本侧离线文件读取 ${n} 个周波的采样瞬时值曲线（Ua/Ub/Uc/Ia/Ib/Ic），显示在下方「周波窗 2」`,
        onClick: () => loadNilmWave2(side, xEpoch, n) },
      { key: 'zoom-reset', label: '复位缩放', onClick: () => zoomReset(cv) },
      { key: 'native', label: '浏览器原生菜单（Shift + 右键）', disabled: true },
    ]);
  });
}

function renderNilm() {
  buildNilmForm();
  const NL = NLs();
  if (!NL.loaded) { NL.loaded = true; refreshNilm(); return; }
  const sm = NL.summary || {};
  const counts = sm.counts || {};
  const names = sm.algorithm_names || {};
  const cards = [card('负荷辨识', sm.enabled === false ? '已禁用' : (sm.auto_params_effective ? '启用 · 自适应参数' : '启用'), '', `累计 ${sm.total || 0} 条 · ↑${(sm.by_direction || {}).up || 0} / ↓${(sm.by_direction || {}).down || 0}`)];
  Object.keys(NILM_ALGOS).forEach(a => cards.push(card(names[a] || NILM_ALGOS[a].name, String(counts[a] || 0), '次',
    (sm.algorithms_enabled || []).includes(a) ? '启用' : '<span class="bad">已停用</span>')));
  cards.push(card('周波窗', `${sm.window_fill || 0} / ${sm.window_cycles || 0}`, '周波', `每周波 ${sm.n_cycle_samples || 0} 点 · 累计 ${sm.cycles_total || 0} 周波 · 对象 ${(sm.channels_effective || sm.channels || []).join('/')}`));
  const w = sm.writer || {};
  cards.push(card('事件落盘', w.enabled ? '开' : '关', '', writerSub(w)));
  $('#nilm-cards').innerHTML = cards.join('');
  if (isNum(sm.total)) setNilmBadge(sm.total);
  renderNilmPqs(NL);
  renderNilmWave2(NL);
  // 周波窗曲线 + 事件竖线
  const running = curRunning();
  const useFile = !running && !!NL.winFile;
  const c = (useFile ? NL.winFile : NL.cycles) || {}; const chn = $('#nilm-ch').value, qty = $('#nilm-qty').value, mk = $('#nilm-mark').value;
  ['btn-nilm-win-load', 'btn-nilm-win-live', 'nilm-win-t', 'nilm-win-count'].forEach(id => { const el = $('#' + id); if (el) el.disabled = running; });
  { const el = $('#btn-nilm-win-live'); if (el) el.disabled = running || !NL.winFile; }
  { const el = $('#nilm-win-src'); if (el) el.textContent = nilmWinSourceText(NL, running); }
  const chd = ((c.channels || {})[chn] || {})[qty] || [];
  const tt = c.t || []; const t0 = tt.length ? tt[0] : 0;
  $('#nilm-win-n').textContent = String(tt.length);
  const unit = qty === 'p' ? 'W' : qty === 'q' ? 'var' : 'A';
  const marks = nilmMarkPool(NL).filter(e => e.channel === chn && (!mk || e.algorithm === mk) && e.t_start >= t0 && tt.length && e.t_start <= tt[tt.length - 1])
    .map((e, i) => ({ x: e.t_start - t0, color: NILM_COLORS[e.algorithm], row: Object.keys(NILM_ALGOS).indexOf(e.algorithm),
                     label: `${e.direction === 'up' ? '↑' : '↓'}${si(nilmMag(e), e.unit || 'W', 3)}` }));
  drawLine($('#nilm-chart'), [{ name: `${chn === 'total' ? '三相总' : chn + ' 相'} ${qty.toUpperCase()}（逐周波${useFile ? '，离线装载' : ''}）`, color: useFile ? '#f2b84b' : '#4ea1ff', data: tt.map((x, i) => [x - t0, chd[i]]) }],
           { ylabel: unit, fmtX: x => ts(x + t0), fmtTip: x => ts(x + t0), height: 240, marks,
             empty: (curState().loaded_last && !tt.length) ? '周波窗是内存数据，软件重启后不恢复（上次播放的事件已加载：见事件表与上方 P/Q/S 趋势的事件竖线）；可用上方「装载周波窗」从离线文件读取任意时刻的周波数据' : '暂无周波数据（启动数据源后显示，或非运行状态下用「装载周波窗」从离线文件读取）' });
  const nsc = nilmScales(NL.events);   // 单位按全部事件选，筛选切换时列单位不跳
  const fAlgo = $('#nilm-filter').value, fCh = $('#nilm-chfilter').value;
  const listEv = NL.events.filter(e => (!fAlgo || e.algorithm === fAlgo) && (!fCh || e.channel === fCh));
  $('#nilm-total').textContent = String((fAlgo || fCh) ? `${listEv.length} / ${sm.total || NL.events.length}` : (sm.total || NL.events.length));
  $('#nilm-table').innerHTML = listEv.length ? table(nilmHeader(nsc), listEv.map(e => nilmRow(e, nsc))) : `<div class="notes">${NL.events.length ? '当前筛选下无事件' : '暂无事件'}</div>`;
  const cfg = curState().config || {};
  fillNilmForm(cfg.nilm);
  nilmProfileState();
  const ll = curState().loaded_last;
  $('#nilm-notes').innerHTML = notes((sm.notes || []).concat(sm.errors || []), [
    ...(ll && !tt.length ? [`已加载上次播放（${ll.t_anchor_local || ll.t_last_local || ''} 前 ${ll.hours || 24} h）的负荷事件 ${ll.nilm_events || 0} 条与 P/Q/S 趋势；周波窗（逐周波 P/Q/I 序列）是内存数据，重启后不恢复，重新播放后显示。`] : []),
    '口径：每周波 P=mean(u·i)，Q=基波单频 DFT 无功，I=周波有效值；各算法在最近 window_cycles 个周波的窗上评估，同算法同对象按终点序号去重，终点之后需再看到足够周波才确认（所以事件会滞后几个周波出现）。',
    '阈值单位为 W，按计算口径（启用 PT/CT 时为一次侧）填写；rel_tol_pct / min_delta_pct 把门槛按窗内 |P| 中位数折算成相对值，同一套默认值在 W 级与 MW 级都能用。',
    '检测量 auto/p/i（v0.36）：数据源只有三相电流（无电压）时选 auto 或 i，按逐周波电流有效值检测，六种算法均可用；此时事件幅值为 |ΔI|（A），ΔP/ΔQ 恒为 0。',
    'v0.39：I 口径不存在跨相合并（三相电流有效值不能像有功那样相加），只能单相检测——检测对象「三相总」被忽略，只配了三相总时按 A/B/C 各自检测；上方趋势图「曲线」可选三相电流（显示哪几相用曲线下方图例勾选），auto 时 I 口径自动画电流。',
    'v0.37：每个算法的绝对阈值分 W（P 口径）与 A（I 口径）两套，检测器只用当前口径那一套，另一套不参与（表单中灰显）；相对门槛 rel_tol_pct / min_delta_pct 对两种口径都按窗内中位数折算。',
    'v0.46：非运行状态下可在趋势曲线上右键「显示周波窗」查看鼠标所指时刻为中心的周波数据，或在周波窗面板填时刻/周波数手动装载（留空＝数据起点起 300 个周波）；数据来自当前侧配置的离线文件，运行中不可用。',
    'v0.65：趋势曲线右键「显示周波窗 2」：以该时刻为中心、周波数同上，显示的是「采样瞬时值曲线」（Ua/Ub/Uc/Ia/Ib/Ic 原始波形，按本侧配置的 PT/CT / 时标 / 自定义时间解释），而不是逐周波计算的 P/Q/I；从本侧离线文件读取。v0.66：只有输入方式为离线文件（csv_file）时可选，模拟器 / TCP / 文件追加等实时源下菜单项灰显。',
    '双滑窗均值差与 CUSUM 对单周波尖峰较敏感（会按均值摊成小事件）；需要抗尖峰请看中值滤波差分 / 稳态分段，或抬高 min_delta_pct。',
  ]);
}

function bindNilm(side) {
  const on = (id, ev, fn) => { const el = E(side, id); if (el) el.addEventListener(ev, fn); };
  on('btn-nilm-refresh', 'click', () => refreshNilm(side));
  on('btn-nilm-clear', 'click', () => clearNilm(side));
  on('btn-nilm-save', 'click', () => saveNilmConfig(side));
  on('btn-nilm-tune-apply', 'click', () => applyNilmTune(side));
  on('btn-nilm-win-load', 'click', () => loadNilmWindow(side));
  on('btn-nilm-win-live', 'click', () => clearNilmWindow(side));
  on('btn-nilm-wave2-clear', 'click', () => { NLs(side).wave2 = null; render(); });
  on('nilm-win-t', 'keydown', (e) => { if (e.key === 'Enter') loadNilmWindow(side); });
  on('nilm-filter', 'change', render);          // v0.48：列表筛选只影响列表（客户端过滤），不再重新拉取
  on('nilm-chfilter', 'change', render);
  ['nilm-ch', 'nilm-qty', 'nilm-mark', 'nilm-pqs-ch', 'nilm-pqs-kind'].forEach(id => on(id, 'change', render));
  const pa = E(side, 'nilm-pqs-algos'); if (pa) pa.addEventListener('change', render);
  on('nilm-mark-all', 'change', () => refreshNilm(side));          // v0.89：切换后按新限制重新拉取并重画
  if (side === 'branch') bindNilmForm('branch');   // 克隆列的表单输入 → 分路侧脏标记
}

/* ------------------------------------------------------------------ 数据处理：离线 CSV 重采样 */

const RS = { files: [], status: null, timer: null, loaded: false };

function renderProcess() {
  if (!RS.loaded) { RS.loaded = true; rsListFiles(); rsPoll(); }
  rsPreview();
  renderWavePreview();     // v0.61：切回本页时按当前画布宽度重绘三张预览曲线
}

// v0.34：误差统计参数默认值来自配置 processing（状态接口 defaults），只在用户未改动时回填
function rsApplyDefaults(d) {
  if (!d || RS.errTouched) return;
  const w = $('#rs-errwin'), e = $('#rs-err');
  if (w && isNum(d.err_window_s)) w.value = d.err_window_s;
  if (e && typeof d.err_report === 'boolean') e.checked = d.err_report;
}

async function rsSaveErrCfg() {
  RS.errTouched = true;
  const w = +$('#rs-errwin').value, on = $('#rs-err').checked;
  if (!(w > 0)) { toast('误差统计时间窗必须 > 0 秒', 'err'); return; }
  try {
    const r = await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ processing: { error_window_s: w, error_report: on } }) });
    if (r && r.ok === false) { toast(r.error, 'err'); return; }
    toast(`误差统计：${on ? '开启' : '关闭'} · 时间窗 ${w} s 已保存到配置`);
  } catch (e) { toast(e.message, 'err'); }
}

async function rsListFiles() {
  const sel = $('#rs-files');
  if (!sel) return;
  try {
    const r = await api('/api/files?sub=data');
    RS.files = (r.files || []).filter(f => !f.dir && f.name.toLowerCase().endsWith('.csv'));
    const cur = sel.value;
    sel.innerHTML = '<option value="">— 选择 data/ 下的 CSV —</option>' +
      RS.files.map(f => `<option value="${esc(f.name)}">${esc(f.name)} (${f.size_mb} MB)</option>`).join('');
    if (cur && RS.files.some(f => f.name === cur)) sel.value = cur;
  } catch (e) { toast('读取文件列表失败：' + e.message, 'err'); }
}

let _rsPrevT = null;
function rsPreview() {
  clearTimeout(_rsPrevT);
  _rsPrevT = setTimeout(async () => {
    const out = $('#rs-preview'); if (!out) return;
    const path = $('#rs-path').value.trim(), fs = +$('#rs-fs').value;
    if (!path || !(fs > 0)) { out.innerHTML = ''; return; }
    try {
      const r = await api('/api/process/resample/preview?' + new URLSearchParams({ path, fs_new: fs }));
      out.innerHTML = notes([
        (r.src_exists ? '✓ 源文件存在' : '✗ 源文件不存在：' + esc(path)),
        `输出：<code>${esc(r.out_path)}</code>` + (r.exists ? '　<b>（已存在，需勾选覆盖）</b>' : ''),
      ]);
    } catch (e) { out.innerHTML = notes(['✗ ' + e.message]); }
  }, 250);
}

async function rsProbe() {
  const path = $('#rs-path').value.trim();
  if (!path) { toast('请先填写源文件路径', 'err'); return; }
  $('#rs-status').innerHTML = '<div>探查中…</div>';
  try {
    const r = await api('/api/probe?path=' + encodeURIComponent(path));
    if (!r.ok) { $('#rs-status').innerHTML = notes(['✗ ' + r.error]); return; }
    $('#rs-status').innerHTML = notes([
      `文件 ${esc(r.path)}（${r.size_mb} MB，编码 ${r.encoding}，${r.has_header ? '有表头' : '无表头'}，${r.rows} 行，约 ${num(r.duration_s, 2)}s）`,
      `首个时间戳 ${esc(r.t_first_text || '')}（模式 ${r.ts_mode}）· 推算采样率 <b>${num(r.fs_est, 3)} Hz</b>（配置 ${r.fs_configured} Hz）`,
      ...(r.notes || []),
    ]);
    if (isNum(r.fs_est) && !$('#rs-fssrc').value) $('#rs-fssrc').placeholder = '自动 ≈ ' + num(r.fs_est, 2);
  } catch (e) { $('#rs-status').innerHTML = notes(['✗ ' + e.message]); }
}

/* v0.86：数据处理页三功能（重采样 / 负荷辨识调参 / 波形预览）共用的「离线文件列映射」：
   默认不启用＝各列依次为 时间, A相电压, A相电流, B相电压, B相电流, C相电压, C相电流；启用后按 7 个列号取列 */

/* v0.99.8：PT/CT 与 3P3W 门控（数据源页两侧 + 数据处理各基准配置共用）
   ptctGate：未勾选「启用 PT/CT 变换」→ PT、CT 输入框禁用并显示 1（原值暂存 data-prev，勾回时恢复）；
   wiringGate：接线方式不是三相三线 → 「3P3W 虚拟中性点重构」取消勾选并禁用。 */
function ptctSync(chkId, ptId, ctId) {
  const chk = document.getElementById(chkId); if (!chk) return;
  const on = chk.checked;
  [ptId, ctId].forEach(id => {
    const el = document.getElementById(id); if (!el) return;
    if (!on) {
      if (!el.disabled && el.value !== '' && el.value !== '1') el.dataset.prev = el.value;
      el.value = '1'; el.disabled = true; el.title = '未启用 PT/CT 变换：固定为 1';
    } else {
      if (el.disabled) { el.disabled = false; el.title = ''; if (el.dataset.prev) { el.value = el.dataset.prev; } }
    }
  });
}
function ptctGate(chkId, ptId, ctId, onChange) {
  const chk = document.getElementById(chkId); if (!chk) return;
  chk.addEventListener('change', () => { ptctSync(chkId, ptId, ctId); if (onChange) onChange(); });
  ptctSync(chkId, ptId, ctId);
}
function wiringSync(selId, reconId) {
  const sel = document.getElementById(selId), rc = document.getElementById(reconId); if (!sel || !rc) return;
  const three = sel.value === '3p3w';
  if (!three) rc.checked = false;
  rc.disabled = !three; rc.title = three ? '' : '仅三相三线两表法接线下可选';
  const lab = rc.closest('label'); if (lab) lab.classList.toggle('nilm-auto-off', !three);
}
function wiringGate(selId, reconId, onChange) {
  const sel = document.getElementById(selId); if (!sel) return;
  sel.addEventListener('change', () => { wiringSync(selId, reconId); if (onChange) onChange(); });
  wiringSync(selId, reconId);
}
/* 一次性把所有门控组同步（在表单回填后调用） */
function syncAllGates() {
  [['cfg-scale', 'cfg-pt', 'cfg-ct'], ['br-scale', 'br-pt', 'br-ct'], ['nt-base-ptct', 'nt-base-pt', 'nt-base-ct'],
   ['np-base-ptct', 'np-base-pt', 'np-base-ct'], ['wp-base-ptct', 'wp-base-pt', 'wp-base-ct']].forEach(a => ptctSync(...a));
  [['cfg-wiring', 'cfg-recon3w'], ['br-wiring', 'br-recon3w'], ['nt-base-wiring', 'nt-base-recon3w'], ['np-base-wiring', 'np-base-recon3w'],
   ['wp-base-wiring', 'wp-base-recon3w'], ['ct-bus-wiring', 'ct-bus-recon3w'], ['ct-br-wiring', 'ct-br-recon3w']].forEach(a => wiringSync(...a));
}

const CM_FIELDS = [['ts', 'timestamp'], ['ua', 'ua'], ['ia', 'ia'], ['ub', 'ub'], ['ib', 'ib'], ['uc', 'uc'], ['ic', 'ic']];
function cmEnabled(pre) { const el = $('#' + pre + '-on'); return !!(el && el.checked); }
function cmMap(pre) { const m = {}; CM_FIELDS.forEach(([sfx, key]) => { const el = $('#' + pre + '-' + sfx); m[key] = el ? String(el.value || '').trim() : ''; }); return m; }
function cmPayload(pre) { return cmEnabled(pre) ? { col_map_enabled: true, col_map: cmMap(pre) } : { col_map_enabled: false }; }
function cmQuery(pre) { return cmEnabled(pre) ? { col_map_enabled: '1', col_map: JSON.stringify(cmMap(pre)) } : { col_map_enabled: '0' }; }
function cmSync(pre) { const row = $('#' + pre + '-row'); if (row) row.style.display = cmEnabled(pre) ? '' : 'none'; }
function cmSet(pre, enabled, map) {
  const on = $('#' + pre + '-on'); if (on) on.checked = !!enabled;
  if (map && typeof map === 'object') CM_FIELDS.forEach(([sfx, key]) => { const el = $('#' + pre + '-' + sfx); if (el && map[key] !== undefined) el.value = String(map[key] ?? ''); });
  cmSync(pre);
}
function cmBind(pre, onChange) {
  const on = $('#' + pre + '-on'); if (on) on.addEventListener('change', () => { cmSync(pre); if (onChange) onChange(); });
  CM_FIELDS.forEach(([sfx]) => { const el = $('#' + pre + '-' + sfx); if (el && onChange) el.addEventListener('change', onChange); });
  cmSync(pre);
}
function cmText(enabled, map) {
  if (!enabled) return '不启用（各列依次为 时间, A相电压, A相电流, B相电压, B相电流, C相电压, C相电流）';
  const names = { timestamp: '时间', ua: 'A相电压', ia: 'A相电流', ub: 'B相电压', ib: 'B相电流', uc: 'C相电压', ic: 'C相电流' };
  return '启用：' + CM_FIELDS.map(([, k]) => `${names[k]}=${(map || {})[k] || '—'}`).join(' ');
}

function rsPayload() {
  const p = { path: $('#rs-path').value.trim(), fs_new: +$('#rs-fs').value, method: $('#rs-method').value,
              overwrite: $('#rs-overwrite').checked };
  const fsrc = $('#rs-fssrc').value.trim();
  if (fsrc) p.fs_src = +fsrc;                       // 留空不送 → 服务端自动推算（载荷无空值纪律）
  p.err_report = $('#rs-err').checked;              // v0.34：相对误差统计
  const ew = $('#rs-errwin').value.trim();
  if (p.err_report && ew) p.err_window_s = +ew;
  Object.assign(p, cmPayload('rs-cm'));            // v0.86：离线文件列映射
  return p;
}

async function rsRun() {
  const p = rsPayload();
  if (!p.path) { toast('请填写源文件路径', 'err'); return; }
  if (!(p.fs_new > 0)) { toast('目标采样率必须 > 0', 'err'); return; }
  try {
    const r = await api('/api/process/resample', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) });
    if (!r.ok) { toast(r.error, 'err'); $('#rs-status').innerHTML = notes(['✗ ' + esc(r.error)]); return; }
    toast('重采样任务已启动');
    $('#rs-result').innerHTML = ''; $('#rs-result2').innerHTML = ''; $('#rs-json').textContent = ''; $('#btn-rs-use').disabled = true;
    const es = $('#rs-err-summary'); if (es) es.innerHTML = '';
    rsPoll(true);
  } catch (e) { toast(e.message, 'err'); }
}

async function rsCancel() {
  try { await api('/api/process/resample/cancel', { method: 'POST' }); toast('已请求取消'); } catch (e) { toast(e.message, 'err'); }
}

async function rsPoll(loop) {
  clearTimeout(RS.timer);
  try {
    const st = await api('/api/process/resample');
    RS.status = st; rsApplyDefaults(st.defaults); rsRenderStatus(st);
    if (st.running || loop) RS.timer = setTimeout(() => rsPoll(st.running), 500);
  } catch (e) { $('#rs-status').innerHTML = notes(['✗ ' + e.message]); }
}

function rsRenderStatus(st) {
  const bar = $('#rs-bar'); if (!bar) return;
  const bar2 = $('#rs-bar2'), l1 = $('#rs-step1-label'), l2 = $('#rs-step2-label');
  const p = st.params || {};
  const ss = st.step_status || {};
  const steps = st.steps || 1;
  const sp = Math.round((st.step_progress || 0) * 100);
  const r = st.result;
  // v0.35：两步各自的进度条与状态标签
  const stepPct = (name, idx) => {
    const stt = ss[name] || 'pending';
    if (stt === 'done' || stt === 'skipped') return 100;
    if (stt === 'running') return sp;
    return 0;
  };
  const stepCls = (name) => {
    const stt = ss[name] || 'pending';
    if (st.error && (stt === 'running' || (stt === 'pending' && st.step === (name === 'error' ? 2 : 1)))) return 'progress-bar err';
    return 'progress-bar' + (stt === 'done' ? ' done' : '');
  };
  const label = (name) => {
    const stt = ss[name] || 'pending';
    if (st.error && stt === 'running') return '✗ 失败';
    return { pending: '等待', running: `进行中 ${sp}%`, done: '✓ 完成' + (r && r.steps && r.steps[name] ? ` · ${r.steps[name].elapsed_s}s` : ''), skipped: '⤼ 已跳过（输出已存在）' }[stt] || stt;
  };
  bar.style.width = stepPct('resample') + '%'; bar.className = stepCls('resample');
  if (l1) l1.textContent = label('resample');
  $('#rs-step1').className = 'rs-step ' + (ss.resample || 'pending');
  const hasErrStep = steps >= 2 || 'error' in ss || (r && r.err_path);
  if (bar2) { bar2.style.width = (hasErrStep ? stepPct('error') : 0) + '%'; bar2.className = hasErrStep ? stepCls('error') : 'progress-bar'; }
  if (l2) l2.textContent = hasErrStep ? label('error') : '未启用（未勾选计算相对误差）';
  $('#rs-step2').className = 'rs-step ' + (hasErrStep ? (ss.error || 'pending') : 'pending');
  $('#btn-rs-run').disabled = !!st.running;
  $('#btn-rs-cancel').disabled = !st.running;
  if (st.running) {
    $('#rs-status').innerHTML = notes([`运行中 · 第 ${st.step || 1}/${steps} 步 · 阶段 ${esc(st.stage)} · 本步 ${sp}% · 总 ${Math.round((st.progress || 0) * 100)}% · 已读 ${num(st.rows_in, 0)} 行 → 已写 ${num(st.rows_out, 0)} 行 · ${num(st.elapsed_s, 1)}s`,
      `源 ${esc(p.path || '')} → ${p.fs_new} Hz（${esc(p.method || 'linear')}）`]);
    return;
  }
  if (st.error) {
    $('#rs-status').innerHTML = notes([`✗ 失败（第 ${st.step || 1} 步）：${esc(st.error)}`]);
    return;
  }
  if (!r) { if (!st.params || !st.params.path) $('#rs-status').innerHTML = notes(['尚未运行任务']); return; }
  $('#rs-status').innerHTML = notes([`✓ 完成 · 总耗时 ${r.elapsed_s}s` + (r.resample_skipped ? ' · 第 1 步已跳过（输出已存在，只计算了相对误差）' : '')]);
  $('#rs-result').innerHTML = notes([
    (r.resample_skipped ? `已存在的输出文件：<b><code>${esc(r.out_path)}</code></b>（${r.out_size_mb} MB）——未重新重采样` : `输出文件：<b><code>${esc(r.out_path)}</code></b>（${r.out_size_mb} MB）`),
    `行数 ${num(r.rows_in, 0)} → <b>${num(r.rows_out, 0)}</b>；原采样率 <b>${num(r.fs_src, 4)} Hz</b>（${r.fs_src_source === 'user' ? '用户指定' : '时间戳推算'}）→ 目标 <b>${num(r.fs_new, 4)} Hz</b>；方法 ${esc(r.method)}；数据时长 ${num(r.duration_s, 3)}s`,
    `时间戳：输入首 <code>${esc(r.ts_first_in)}</code> → 输出首 <code>${esc(r.ts_first_out)}</code> / 末 <code>${esc(r.ts_last_out)}</code>（模式 ${esc(r.ts_mode)}，${r.header_kept ? '表头保留' : '无表头'}，编码 ${esc(r.encoding)}）`,
    ...((r.notes || []).filter(n => !/^相对误差：/.test(n))),
  ]);
  $('#rs-result2').innerHTML = notes(r.err_path
    ? [`相对误差文件：<b><code>${esc(r.err_path)}</code></b>（时间窗 ${num(r.err_window_s, 3)} s × ${num(r.err_windows, 0)} 窗）`,
       `各通道最大 RMS 相对误差 <b>${(r.err_rms_rel_max * 100).toExponential(2)}%</b>，最大波形相对误差 NRMSE <b>${(r.err_nrmse_max * 100).toExponential(2)}%</b>`]
    : ['未计算相对误差（已关闭）']);
  const es = $('#rs-err-summary'); if (es) es.innerHTML = r.err_path ? rsErrTable(r) : '';
  $('#rs-json').textContent = JSON.stringify(r, null, 2);
  const useBtn = $('#btn-rs-use'); useBtn.disabled = false; useBtn.dataset.path = r.out_path; useBtn.dataset.fs = r.fs_new;
  rsListFiles(); rsPreview();
}

function rsErrTable(r) {
  const sm = r.err_summary || {};
  const pct = (v) => isNum(v) ? (v * 100).toExponential(2) + '%' : '—';
  const rows = Object.keys(sm).map(k => `<tr><td>${esc(k)}</td><td>${pct(sm[k].rms_rel_mean)}</td><td>${pct(sm[k].rms_rel_max)}</td>` +
    `<td>${pct(sm[k].nrmse_mean)}</td><td>${pct(sm[k].nrmse_max)}</td></tr>`).join('');
  return `<table id="rs-err-table"><thead><tr><th>通道</th><th>RMS 相对误差·均值</th><th>RMS 相对误差·最大</th><th>NRMSE·均值</th><th>NRMSE·最大</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function rsUseAsSource() {
  const b = $('#btn-rs-use'); const path = b.dataset.path; if (!path) return;
  switchView('source');
  $('#src-kind').value = 'csv_file'; $('#src-path').value = path;
  S.srcDirty = true; S.formDirty = true; syncSourceForm();
  toast(`已填入离线源 ${path}；请确认配置采样率 fs=${b.dataset.fs} 后点「启动」`);
}

/* v0.52：数据处理 · 负荷辨识调参（POST /api/process/nilm_tune） */
const NT = { last: null, side: 'bus', command: '', est: null, userBase: null, runningQC: null };
/* v0.99.5：调参（nt）与画像提取（np）各自独立一套公共配置（文件 / 起止 / 自定义时间 / 基准配置 / 列映射 / 检测量）；下列函数按前缀 P 工作 */
const NTS = { nt: NT, np: { userBase: null, runningQC: null } };
const NT_BASE_KEYS = { nt: 'elec_tool.nilm_tune.base', np: 'elec_tool.nilm_profile.base' };
async function ntListFiles(P = 'nt') {
  if (P === 'nt') ntListFiles('nt-dev');          // v0.99.11：第 ① 步设备侧文件下拉一并刷新
  const sel = $('#' + P + '-files'); if (!sel) return;
  try {
    const r = await api('/api/files?sub=data');
    const files = (r.files || []).filter(f => !f.dir && f.name.toLowerCase().endsWith('.csv'));
    const cur = sel.value;
    sel.innerHTML = '<option value="">— 选择 data/ 下的 CSV —</option>' + files.map(f => `<option value="${esc(f.name)}">${esc(f.name)} (${f.size_mb} MB)</option>`).join('');
    if (cur && files.some(f => f.name === cur)) sel.value = cur;
  } catch (e) { toast('读取文件列表失败：' + e.message, 'err'); }
}
/* v0.72：负荷辨识调参「独立基准配置」——出厂配置 + 本页各项，与两侧运行配置互不关联；存浏览器本地 */
function ntBaseMode(P = 'nt') { const el = $('#' + P + '-side'); return (el && el.value) || 'custom'; }
function ntBase(P = 'nt') {
  const v = id => { const el = $('#' + id); return el ? (el.value || '').trim() : ''; };
  const c = id => { const el = $('#' + id); return el && el.checked ? '1' : '0'; };
  return { fs: v(P + '-base-fs'), f_nom: v(P + '-base-fnom'), pt_ct_enabled: c(P + '-base-ptct'), pt_ratio: v(P + '-base-pt'),
           ct_ratio: v(P + '-base-ct'), file_time_utc: c(P + '-base-utc'),   // 检测量只在「检测量」下拉填一处（v0.72.1 去重）
           wiring: v(P + '-base-wiring') || '3p4w', reconstruct_3w: c(P + '-base-recon3w'), invert_current: c(P + '-base-inv'), invert_phases: getInvPhases(P + '-base'),   // v0.95
           col_map_enabled: cmEnabled(P + '-cm'), col_map: cmMap(P + '-cm') };   // v0.86：列映射随基准配置存浏览器本地（服务端按顶层 col_map* 读取）
}
function ntSetBase(b, P = 'nt') {
  if (!b || typeof b !== 'object') return;
  const set = (id, val) => { const el = $('#' + id); if (el && val !== undefined && val !== null) el.value = String(val); };
  const on = x => (x === true || x === '1' || x === 1 || x === 'true');
  set(P + '-base-fs', b.fs); set(P + '-base-fnom', b.f_nom); set(P + '-base-pt', b.pt_ratio); set(P + '-base-ct', b.ct_ratio);
  if ($('#' + P + '-base-ptct') && b.pt_ct_enabled !== undefined) $('#' + P + '-base-ptct').checked = on(b.pt_ct_enabled);
  if ($('#' + P + '-base-utc') && b.file_time_utc !== undefined) $('#' + P + '-base-utc').checked = on(b.file_time_utc);
  if (b.wiring !== undefined) set(P + '-base-wiring', b.wiring || '3p4w');
  if ($('#' + P + '-base-recon3w') && b.reconstruct_3w !== undefined) $('#' + P + '-base-recon3w').checked = on(b.reconstruct_3w);
  if ($('#' + P + '-base-inv') && b.invert_current !== undefined) $('#' + P + '-base-inv').checked = on(b.invert_current);
  if (b.invert_phases !== undefined) setInvPhases(P + '-base', b.invert_phases);
  if (b.col_map_enabled !== undefined) cmSet(P + '-cm', on(b.col_map_enabled), b.col_map);
  ptctSync(P + '-base-ptct', P + '-base-pt', P + '-base-ct'); wiringSync(P + '-base-wiring', P + '-base-recon3w');   // v0.99.8
}
function ntSaveBase(P = 'nt') { if (ntBaseMode(P) !== 'custom') return; try { localStorage.setItem(NT_BASE_KEYS[P], JSON.stringify(ntBase(P))); } catch (e) { /* 隐私模式 */ } }
function ntSyncCustomTime(P = 'nt') {
  const on = !!($('#' + P + '-custom') && $('#' + P + '-custom').checked);
  const row = $('#' + P + '-custom-row'); if (row) row.style.display = on ? '' : 'none';
  const fmtS = '2026-10-12 08:00:00 / epoch 秒 / 08:00:00', fmtE = '2026-10-12 08:10:00 / epoch 秒 / 08:10:00';
  if ($('#' + P + '-tstart')) $('#' + P + '-tstart').placeholder = (on ? '空＝自定义起始时间' : '空＝文件开头') + '；' + fmtS;
  if ($('#' + P + '-tend')) $('#' + P + '-tend').placeholder = (on ? '空＝起始 + 点数/采样率' : '空＝文件结尾') + '；' + fmtE;
  const n = $('#' + P + '-custom-note'); if (n) n.textContent = on ? '已启用：时间轴＝自定义起始时间 + 行号/采样率；起止都空＝整个文件，时长＝数据点数 / 采样率' : '未启用：按文件内数据时间';
}
function ntSyncBaseUI(P = 'nt') {
  const ST = NTS[P];
  const custom = ntBaseMode(P) === 'custom';
  const sideName = ntBaseMode(P) === 'branch' ? '分路侧' : '总线侧';
  // v0.73：基准配置分组始终显示；独立＝可编辑；沿用某侧＝全部字段显示该侧运行配置值并禁用（检测量 / 检测对象也在分组内）
  const t = $('#' + P + '-base-title'); if (t) t.textContent = custom ? '独立基准配置（与两侧运行配置互不关联，可单独修改）' : `基准配置（沿用${sideName}运行配置，不可修改）`;
  const fo = $('#' + P + '-quantity-follow'); if (fo) fo.textContent = custom ? '默认（出厂缺省 auto：无电压→I）' : '跟随配置 nilm.quantity';
  [P + '-base-fs', P + '-base-fnom', P + '-base-pt', P + '-base-ct', P + '-base-ptct', P + '-base-utc', P + '-quantity', P + '-channel',
   P + '-base-wiring', P + '-base-recon3w', P + '-base-inv', P + '-base-inv-a', P + '-base-inv-b', P + '-base-inv-c'].forEach(id => { const el = $('#' + id); if (el) el.disabled = !custom; });
  if (custom) { ptctSync(P + '-base-ptct', P + '-base-pt', P + '-base-ct'); wiringSync(P + '-base-wiring', P + '-base-recon3w'); }   // v0.99.8：独立模式下再套门控
  ['btn-nt-base-default', 'btn-nt-base-bus', 'btn-nt-base-branch'].forEach(id => { const el = $('#' + id); if (el) el.style.display = custom ? '' : 'none'; });
  const q = $('#' + P + '-quantity'), ch = $('#' + P + '-channel');   // np 无 channel（检测对象固定 total）
  if (q) {
    if (custom) {
      if (ST.userBase) { ntSetBase(ST.userBase, P); q.value = ST.userBase.q; if (ch) ch.value = ST.userBase.ch; ST.userBase = null; }
    } else {
      if (!ST.userBase) ST.userBase = Object.assign(ntBase(P), { q: q.value, ch: ch ? ch.value : '' });   // 记住独立模式下的值，切回时恢复
      ntFillQCFromRunning(ntBaseMode(P), P);
    }
  }
  const n = $('#' + P + '-base-note');
  if (n) n.textContent = custom ? `独立基准配置只用于本页${P === 'np' ? '画像提取' : '调参'}，不改动总线侧 / 分路侧运行配置；修改自动保存在浏览器本地。`
                                : `基准配置沿用${ntBaseMode(P) === 'branch' ? '分路侧' : '总线侧'}当前运行配置（PT/CT、列映射、缺省检测量）。`;
}
async function ntFillQCFromRunning(side, P = 'nt') {
  const ST = NTS[P];
  const q = $('#' + P + '-quantity'), ch = $('#' + P + '-channel'); if (!q) return;
  try {
    const d = await api('/api/process/nilm_tune/base?source=running', undefined, side);
    if (ntBaseMode(P) !== side) return;                                   // 期间用户又切换了
    ntSetBase(d.base, P);                                                   // 显示该侧 fs / f_nom / PT·CT / UTC（禁用态，不存本地）
    q.value = d.base.quantity || 'auto'; if (q.value !== (d.base.quantity || 'auto')) q.value = '';
    if (ch) { ch.value = d.base.channel || 'total'; if (ch.value !== (d.base.channel || 'total')) ch.value = ''; }
    ST.runningQC = { side, q: d.base.quantity, ch: d.base.channel };
  } catch (e) { /* 服务不可用时保留当前显示 */ }
}
async function ntLoadBase(source, side, P = 'nt') {
  const d = await api('/api/process/nilm_tune/base?source=' + encodeURIComponent(source), undefined, side || 'bus');
  ntSetBase(d.base, P); ntSaveBase(P);
  return d;
}
async function ntInitBase(P = 'nt') {
  if (!$('#' + P + '-base')) return;
  try {
    const d = await api('/api/process/nilm_tune/base?source=default', undefined, 'bus');
    ntSetBase(d.base, P);                                         // 出厂值
    let saved = null; try { saved = JSON.parse(localStorage.getItem(NT_BASE_KEYS[P]) || 'null'); } catch (e) { saved = null; }
    if (saved && typeof saved === 'object') ntSetBase(saved, P);   // 浏览器本地保存的改动优先
  } catch (e) { /* 服务不可用时保留 HTML 默认 */ }
  ntSyncBaseUI(P);
}
function ntPayload(P = 'nt') {
  const v = id => { const el = $('#' + id); return el ? (el.value || '').trim() : ''; };   // v0.99.5：np 无 channel 等控件时取空
  const mode = ntBaseMode(P);
  return { path: v(P + '-path'), t_start: v(P + '-tstart'), t_end: v(P + '-tend'), duration_s: (P === 'nt' ? (v(P + '-duration') || null) : null),
           quantity: mode === 'custom' ? (v(P + '-quantity') || null) : null,   // v0.72.2：沿用某侧运行配置时随该侧，不单独上送
           channel: mode === 'custom' ? (v(P + '-channel') || null) : null,
           ...(P === 'nt' ? { min_load_w: v(P + '-minw') || null, min_load_a: v(P + '-mina') || null, min_load_auto: !!$('#' + P + '-minauto').checked,
                              save: !!$('#' + P + '-save').checked, name: v(P + '-name') } : {}),
           custom_time: !!($('#' + P + '-custom') && $('#' + P + '-custom').checked),            // v0.73：自定义时间（同波形预览）
           custom_time_start: ($('#' + P + '-custom') && $('#' + P + '-custom').checked) ? v(P + '-cstart') : '',
           custom_time_end: ($('#' + P + '-custom') && $('#' + P + '-custom').checked) ? v(P + '-cend') : '',
           base_mode: mode === 'custom' ? 'custom' : 'running', base: mode === 'custom' ? ntBase(P) : undefined,
           ...cmPayload(P + '-cm') };                                                   // v0.86：离线文件列映射
}
function ntFmt(x) { return (typeof x === 'number') ? (Number.isInteger(x) ? String(x) : (+x.toPrecision(4)).toString()) : String(x); }
function ntRender(d) {
  const m = d.measure, sg = d.suggest, u = d.unit, tr = d.t_range || {};
  const st = $('#nt-status');
  const rng = tr.whole_file ? '整个文件' : `${tr.start || '文件开头'} → ${tr.end || (tr.duration_s ? '+' + tr.duration_s + ' s' : '文件结尾')}`;
  st.innerHTML = `<div>文件 <code>${esc(d.file)}</code> · 对象 <b>${esc(d.channel)}</b> · 周波 ${m.cycles} · 时长 ${(+d.t_span_s).toFixed(1)} s · 口径 ${d.scaled ? '一次侧(PT/CT)' : '二次侧'} · 检测量 <b>${d.quantity === 'p' ? '有功 P' : '电流有效值 I'}</b>（${esc(d.quantity_requested)}${d.quantity === 'i' && !d.voltage_present ? '，数据源无电压 → I' : ''}）</div>`
    + `<div>时间段 ${esc(rng)} · 实际 ${esc(fmtLocalInput(tr.t_first))} → ${esc(fmtLocalInput(tr.t_last))}${tr.custom_time ? ` · <b>自定义时间</b>（起始 ${esc(tr.custom_time_start || '文件数据起始')}，文件 ${tr.file_rows} 点 / ${ntFmt(tr.fs_used)} Hz ＝ 时长 ${(+tr.file_duration_s).toFixed(3)} s：${esc(fmtLocalInput(tr.file_t_start))} → ${esc(fmtLocalInput(tr.file_t_end))}）` : ''}</div>`
    + (d.base_mode === 'custom' && d.base ? `<div>基准配置：<b>独立基准配置</b>（fs ${ntFmt(d.base.fs)} Hz · f_nom ${ntFmt(d.base.f_nom)} Hz · PT/CT ${d.base.pt_ct_enabled ? '启用 PT=' + ntFmt(d.base.pt_ratio) + ' CT=' + ntFmt(d.base.ct_ratio) : '关闭'} · 时标 ${d.base.file_time_utc ? 'UTC' : '本地'}）${d.base_file ? '，已写到 <code>' + esc(d.base_file) + '</code>' : ''}；两侧运行配置未改动</div>`
                                        : `<div>基准配置：${d.side === 'branch' ? '分路侧' : '总线侧'}当前运行配置</div>`)
    + (d.saved_to ? `<div>已保存到 <code>${esc(d.saved_to)}</code>：以 <code>${esc(d.base_config || '')}</code> 为基准只更新算法参数（${(d.changes || []).length} 项）、其它参数不变的完整配置；原配置文件未改动</div>` : '<div class="muted">未保存配置文件（默认）</div>')
    + (d.notes || []).map(n => `<div class="muted">提示：${esc(n)}</div>`).join('')
;
  const er = $('#nt-estrow'), est = d.min_load_estimate;
  if (er) {
    if (est) {
      er.style.display = '';
      const src = d.min_load_source === 'estimated' ? '（本次已采用）' : (d.min_load_source === 'manual' ? `（本次按手填 ${ntFmt(d.min_load_used)} ${u} 计算，估计仅供参考）` : '（本次未采用：按 max(6σ, 2%×基荷)）');
      // v0.80：显示台阶列表 / 最小 / 最大跳变；分簇时标出主负荷 + 二级波动，并由「取值方式」三选一决定填入值
      const lv = (est.levels || []).map(ntFmt).join(', ');
      const facts = est.candidate === null ? '' : `<br>台阶 [${esc(lv)}] ${u} · 最小跳变 <b>${ntFmt(est.min_step)}</b> · 最大跳变 <b>${ntFmt(est.max_step)}</b> · 最小台阶间距 ${ntFmt(est.min_level_gap)}`
        + (est.split ? ` · <b class="err">⚠ 分两簇：主负荷 ≈${ntFmt(est.primary_step)} ${u}（${est.n_primary} 次）+ 二级波动 ≈${ntFmt(est.secondary_step)} ${u}（${est.n_secondary} 次，相差 ${Math.round(est.step_ratio)} 倍）</b>，请在下方选择取值方式` : '');
      $('#nt-est-text').innerHTML = est.candidate === null ? `无法估计：${esc(est.note)}`
        : `候选 <b>${ntFmt(est.candidate)} ${u}</b> ${est.reliable ? '✓ 可靠' : '⚠ 不可靠'} ${esc(src)}${facts}<br><span class="muted">${esc(est.note)}</span>`;
      $('#btn-nt-est-fill').disabled = est.candidate === null;
      const pick = $('#nt-est-pick');
      if (pick) {
        pick.options[0].textContent = `按最大台阶（主负荷${est.max_step != null ? ' ' + ntFmt(est.split ? est.primary_step : est.max_step) + ' ' + u : ''}）`;
        pick.options[1].textContent = `按最小台阶（候选${est.candidate != null ? ' ' + ntFmt(est.candidate) + ' ' + u : ''}）`;
        pick.value = est.split ? 'primary' : 'min';
      }
      NT.est = { value: est.candidate, unit: u, primary: est.split ? est.primary_step : est.max_step };
    } else { er.style.display = 'none'; NT.est = null; }
  }
  const cr = $('#nt-cmdrow');
  if (cr) { cr.style.display = d.command ? '' : 'none'; $('#nt-cmd').textContent = d.command || ''; NT.command = d.command || ''; }
  { const cmEl = $('#nt-cm-blk'); if (cmEl && d.col_map_enabled !== undefined) cmEl.title = '本次：' + cmText(d.col_map_enabled, d.col_map); }
  let h = `<table><thead><tr><th colspan="3">噪声统计（${u}）</th></tr></thead><tbody>`
    + `<tr><td>基荷 |${d.quantity === 'p' ? 'P' : 'I'}| 中位数 level</td><td>${ntFmt(m.level)}</td><td></td></tr>`
    + `<tr><td>单周波噪声 σ sigma</td><td>${ntFmt(m.sigma_cycle)}</td><td>${(+m.sigma_cycle_pct).toFixed(3)} % 基荷${m.sigma_method === 'block' ? '（段间跳变尺度）' : ''}</td></tr>`
    + (m.repeated_cycles ? `<tr><td>⚠ 分段恒定 / 周波复制</td><td>每段 ≈${Math.round(+m.repeat_run_cycles)} 周波</td><td>段内周波几乎相同（相邻逐位相等 ${(100 * +m.repeat_frac).toFixed(1)} %，相邻差分 σ=${ntFmt(m.sigma_raw)}），段间跳变 σ=${ntFmt(m.sigma_cycle)}：相邻差分口径失真，σ / 极差 / 均值差 / 暂态 / 最小负荷估计已按段间跳变尺度重量${m.sigma_lags ? '；各滞后 σ：' + Object.entries(m.sigma_lags).map(([k, v]) => k + '→' + ntFmt(v)).join(' ') : ''}</td></tr>` : '')
    + `<tr><td>相邻周波最大 |Δ|</td><td>${ntFmt(m.max_abs_diff)}</td><td>${m.has_events_hint ? '⚠ >10σ：段内含事件/尖峰，统计已用稳健口径' : ''}</td></tr>`
    + `<tr><td>5 周波极差 95 分位 range5</td><td>${ntFmt(m.range5_p95)}</td><td>→ settle_tol 的依据</td></tr>`
    + `<tr><td>10 周波极差 95 分位 range10</td><td>${ntFmt(m.range10_p95)}</td><td>→ steady_state.tol 的依据</td></tr>`
    + `<tr><td>10 周波均值差 σ sigma_m10</td><td>${ntFmt(m.sigma_mean10)}</td><td>→ 双滑窗/GLR 的噪声尺度</td></tr>`
    + `</tbody></table>`;
  h += `<table style="margin-top:8px"><thead><tr><th colspan="2">建议参数（起点）</th></tr></thead><tbody>`
    + `<tr><td colspan="2">${esc(sg.note)}</td></tr>`
    + `<tr><td>nilm</td><td>quantity=${esc(sg.quantity)}  rel_tol_pct=${sg.rel_tol_pct}  min_delta_pct=${sg.min_delta_pct}${sg.window_cycles ? '  window_cycles=' + sg.window_cycles : ''}</td></tr>`
    + (sg.transient ? `<tr><td>暂态</td><td>最长 ${sg.transient.longest} 周波（${(sg.transient.longest / 50).toFixed(1)} s @50Hz）· 暂态 ${sg.transient.n_transients} 次 · 锚点稳态 ${sg.transient.n_steady} 段${sg.transient.longest > 100 ? ' · ⚠ 慢启动：steady_state.max_transient_cycles / min_steady_cycles 已按暂态放大' : ''}</td></tr>` : '')
    + Object.entries(sg.algorithms).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${Object.entries(v).map(([kk, vv]) => `${esc(kk)}=${ntFmt(vv)}`).join('  ')}</td></tr>`).join('')
    + `</tbody></table>`;
  $('#nt-result').innerHTML = h;
  $('#nt-json').textContent = JSON.stringify(d, null, 2);

}
/* v0.99.11：两步法第 ① 步——用设备侧含启停文件估计最小关心负荷（min_load_auto），自动填入第 ② 步输入框 */
function ntStep2Hint() {   // 第 ② 步与第 ① 步选了同一个文件 → 提醒（噪声要用总线侧背景）
  const a = ($('#nt-path').value || '').trim() || $('#nt-files').value, b = ($('#nt-dev-path').value || '').trim() || $('#nt-dev-files').value;
  const el = $('#nt-step2-src'); if (!el) return;
  el.innerHTML = (a && b && a === b) ? '<span class="err">⚠ 第 ② 步选的是与第 ① 步相同的设备侧文件：量出的噪声是设备侧的，套到总线侧会误报。请改选总线侧稳态背景文件</span>' : '';
}
async function ntEstimateFromDevice() {
  const path = ($('#nt-dev-path').value || '').trim() || $('#nt-dev-files').value;
  if (!path) { toast('请先选择设备侧波形文件', 'err'); return; }
  const p = Object.assign(ntPayload('nt'), { path, t_start: ($('#nt-dev-tstart').value || '').trim(), t_end: ($('#nt-dev-tend').value || '').trim(),
                                            duration_s: null, custom_time: false, custom_time_start: '', custom_time_end: '',   // 自定义时间是第 ② 步文件专属，不带到设备侧文件
                                            min_load_w: null, min_load_a: null, min_load_auto: true, save: false, name: '' });
  const mode = ntBaseMode('nt'); const side = mode === 'custom' ? 'bus' : mode;
  const btn = $('#btn-nt-est-dev'), out = $('#nt-dev-est'); btn.disabled = true; out.textContent = '正在从设备侧文件估计…';
  try {
    const d = await api('/api/process/nilm_tune', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) }, side);
    const est = d.min_load_estimate, u = d.unit || (d.quantity_effective === 'i' ? 'A' : 'W');
    if (!est || est.candidate === null) { out.innerHTML = `<span class="err">无法估计：${esc((est && est.note) || '文件里没有可辨识的投切台阶')}</span>`; return; }
    const pick = $('#nt-dev-pick').value;
    const val = (pick === 'primary') ? (est.split ? est.primary_step : est.max_step) : est.candidate;
    const tgt = u === 'A' ? $('#nt-mina') : $('#nt-minw');
    tgt.value = ntFmt(val); $('#nt-minauto').checked = false;
    const lv = (est.levels || []).map(ntFmt).join(', ');
    out.innerHTML = `已填入第 ② 步：<b>${ntFmt(val)} ${u}</b>（${pick === 'primary' ? '主负荷 / 最大台阶' : '最小台阶候选'}${est.reliable ? '，✓ 可靠' : '，⚠ 不可靠，请核对'}）`
      + `<br><span class="muted">台阶 [${esc(lv)}] ${u} · 最小跳变 ${ntFmt(est.min_step)} · 最大跳变 ${ntFmt(est.max_step)}${est.split ? ` · 分两簇：主负荷 ≈${ntFmt(est.primary_step)}（${est.n_primary} 次）+ 二级 ≈${ntFmt(est.secondary_step)}（${est.n_secondary} 次）` : ''} · ${esc(est.note || '')}</span>`;
    tgt.classList.add('flash'); setTimeout(() => tgt.classList.remove('flash'), 1500);
    toast(`最小关心负荷 ${ntFmt(val)} ${u} 已填入第 ② 步`, 'ok');
  } catch (e) { out.innerHTML = `<span class="err">失败：${esc(e.message)}</span>`; toast(e.message, 'err'); }
  finally { btn.disabled = false; }
}
async function ntRun() {
  const p = ntPayload();
  if (!p.path) { toast('请填写波形文件路径', 'err'); return; }
  const mode = ntBaseMode();
  const side = mode === 'custom' ? 'bus' : mode;               // v0.72：独立基准配置与侧别无关，请求走总线侧路由即可
  const btn = $('#btn-nt-run'); btn.disabled = true; $('#nt-status').textContent = '正在读取并统计…';
  try {
    const d = await api('/api/process/nilm_tune', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) }, side);
    NT.last = d; NT.side = side; NT.baseMode = mode; $('#btn-nt-apply').disabled = false;
    ntRender(d);
    const n3 = $('#nt-step3-note'); if (n3) n3.textContent = `第 ② 步已完成（文件 ${p.path.split(/[\\/]/).pop()}，噪声 / 容差类参数来自该文件；最小关心负荷 ${d.min_load_source === 'manual' ? '按手填 / 第 ① 步填入值' : d.min_load_source === 'estimated' ? '按本文件估计' : '按 max(6σ, 2%×基荷)'}）→ 可套用`;
    const s2 = $('#nt-step2-src'); if (s2) s2.textContent = '';
    toast('调参完成' + (d.saved_to ? '，结果已保存 ' + d.saved_to : ''), 'ok');
  } catch (e) { $('#nt-status').innerHTML = `<span class="err">失败：${esc(e.message)}</span>`; toast(e.message, 'err'); }
  finally { btn.disabled = false; }
}
async function ntApply() {
  if (!NT.last) return;
  const sel = $('#nt-apply-side');
  const side = (sel && sel.value) || NT.side || 'bus';          // v0.72：套用目标侧由「套用目标」下拉决定，与基准配置无关
  try {
    const d = await api('/api/nilm/tune/apply', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ params: NT.last, hot: true, persist: false }) }, side);
    if (d && d.config) {
      if (side === 'branch') { if (BRD.state) BRD.state.config = d.config; BR.loaded = false; } else if (S.state) S.state.config = d.config;
      if (NLs(side).formBuilt) fillNilmForm(d.config.nilm, side);
    }
    $('#nt-status').insertAdjacentHTML('beforeend', `<div>已套用 ${d.changes.length} 项到${side === 'branch' ? '分路侧' : '总线侧'}运行配置并热生效，更新后的完整配置保存到 <code>${esc(d.saved_to)}</code>（配置文件未改动）</div>`);
    toast('已套用到' + (side === 'branch' ? '分路侧' : '总线侧') + '运行配置', 'ok');
  } catch (e) { toast('套用失败：' + e.message, 'err'); }
}

/* v0.61：数据处理 · 波形预览（GET /api/process/wave/info|load|rms） */
const WP = { info: null, wave: null, rms: null, cyc: null, files: [], defaults: null };
window.WP = WP;
const WP_COLORS = { Ua: '#4ea1ff', Ub: '#3ddc97', Uc: '#ffb648', Ia: '#ff7ac6', Ib: '#9d7bff', Ic: '#5ee0d0' };
const WP_BASE_KEY = 'elec_tool.wave_preview.base';   // v0.62：基准配置存浏览器本地（独立于运行配置）
function wpVal(id) { const el = $('#' + id); return el ? String(el.value || '').trim() : ''; }
/* v0.62：基准配置（fs / f_nom / PT·CT / UTC）——独立字段，随每次请求以查询参数传给服务端 */
function wpBase() {
  const chk = (id) => ($('#' + id) ? ($('#' + id).checked ? '1' : '0') : '');
  const custom = chk('wp-base-custom');
  // v0.65：采样率由文件数据时间推算、不可改 ⇒ 不再作为基准配置上送（wp-base-fs 只显示）
  return { f_nom: wpVal('wp-base-fnom'), pt_ct_enabled: chk('wp-base-ptct'),
           pt_ratio: wpVal('wp-base-pt'), ct_ratio: wpVal('wp-base-ct'), file_time_utc: chk('wp-base-utc'),
           wiring: wpVal('wp-base-wiring') || '3p4w', reconstruct_3w: chk('wp-base-recon3w'), invert_current: chk('wp-base-inv'), invert_phases: getInvPhases('wp-base'),   // v0.95
           // v0.64：自定义时间（启用时：时间轴＝自定义起始(空＝文件数据起始) + 行号/fs；结束空＝按采样率计算）
           custom_time: custom, custom_time_start: custom === '1' ? wpVal('wp-base-cstart') : '', custom_time_end: custom === '1' ? wpVal('wp-base-cend') : '',
           ...cmQuery('wp-cm') };                                                     // v0.86：离线文件列映射
}
function wpMaxPoints() { const v = parseInt(wpVal('wp-maxpts'), 10); return Number.isFinite(v) && v > 0 ? v : ((WP.defaults || {}).max_points_default || 20000000); }
function wpSyncCustom() {
  const on = !!($('#wp-base-custom') && $('#wp-base-custom').checked);
  const row = $('#wp-custom-row'); if (row) row.style.display = on ? '' : 'none';
  // 起止时刻输入框的占位提示随模式变化（空＝数据起止时间）
  const i = WP.info;
  // v0.68：写法提示与数据源页「指定时间段播放」一致（完整日期时间 / epoch 秒 / 只写 HH:MM:SS）
  const fmtS = '2026-10-12 08:00:00 / epoch 秒 / 08:00:00', fmtE = '2026-10-12 08:10:00 / epoch 秒 / 08:10:00';
  const ps = (on ? '空＝自定义起始时间' : '空＝数据起始时间') + '；' + fmtS, pe = (on ? '空＝按采样率计算的结束时间' : '空＝数据结束时间') + '；' + fmtE;
  ['wp-tstart', 'wp-rms-tstart'].forEach(id => { const el = $('#' + id); if (el) el.placeholder = (i && i.t_start_local) ? `空＝${i.t_start_local}；${fmtS}` : ps; });
  ['wp-tend', 'wp-rms-tend'].forEach(id => { const el = $('#' + id); if (el) el.placeholder = (i && i.t_end_local) ? `空＝${i.t_end_local}；${fmtE}` : pe; });
}
function wpSetBase(b) {
  if (!b) return;
  const set = (id, v) => { const el = $('#' + id); if (el && v !== undefined && v !== null) el.value = v; };
  set('wp-base-fnom', b.f_nom); set('wp-base-pt', b.pt_ratio); set('wp-base-ct', b.ct_ratio);
  if ($('#wp-base-ptct')) $('#wp-base-ptct').checked = !!(b.pt_ct_enabled === true || b.pt_ct_enabled === '1' || b.pt_ct_enabled === 1);
  if ($('#wp-base-utc')) $('#wp-base-utc').checked = !!(b.file_time_utc === true || b.file_time_utc === '1' || b.file_time_utc === 1);
  const on1 = x => (x === true || x === '1' || x === 1 || x === 'true');
  if (b.wiring !== undefined) set('wp-base-wiring', b.wiring || '3p4w');
  if ($('#wp-base-recon3w') && b.reconstruct_3w !== undefined) $('#wp-base-recon3w').checked = on1(b.reconstruct_3w);
  ptctSync('wp-base-ptct', 'wp-base-pt', 'wp-base-ct'); wiringSync('wp-base-wiring', 'wp-base-recon3w');   // v0.99.8
  if ($('#wp-base-inv') && b.invert_current !== undefined) $('#wp-base-inv').checked = on1(b.invert_current);
  if (b.invert_phases !== undefined) setInvPhases('wp-base', b.invert_phases);
  if ($('#wp-base-custom') && b.custom_time !== undefined) $('#wp-base-custom').checked = !!(b.custom_time === true || b.custom_time === '1' || b.custom_time === 1);
  set('wp-base-cstart', b.custom_time_start); set('wp-base-cend', b.custom_time_end);
  if (b.max_points !== undefined && b.max_points !== null && b.max_points !== '') set('wp-maxpts', b.max_points);
  if (b.col_map_enabled !== undefined) { let m = b.col_map; if (typeof m === 'string') { try { m = JSON.parse(m); } catch (e) { m = null; } } cmSet('wp-cm', b.col_map_enabled === '1' || b.col_map_enabled === true, m); }
  wpSyncCustom();
}
function wpSaveBase() { try { localStorage.setItem(WP_BASE_KEY, JSON.stringify(Object.assign(wpBase(), { custom_time_start: wpVal('wp-base-cstart'), custom_time_end: wpVal('wp-base-cend'), max_points: wpVal('wp-maxpts') }))); } catch (e) { /* 隐私模式 */ } }
async function wpLoadDefaults() {
  try {
    const d = await api('/api/process/wave/defaults', undefined, 'bus');
    WP.defaults = d;
    wpSetBase(d.base);                                   // 出厂值
    let saved = null; try { saved = JSON.parse(localStorage.getItem(WP_BASE_KEY) || 'null'); } catch (e) { saved = null; }
    if (saved && typeof saved === 'object') wpSetBase(saved);   // 浏览器本地保存的改动优先
    if ($('#wp-ncyc') && !$('#wp-ncyc').value) $('#wp-ncyc').value = d.default_cycles || 300;
    if ($('#wp-cyc-n') && !$('#wp-cyc-n').value) $('#wp-cyc-n').value = d.default_cycles || 300;
  } catch (e) { /* 服务不可用时保留 HTML 默认 */ }
}
function wpChans() { return Array.from(document.querySelectorAll('#wp-chans .wp-ch')).filter(c => c.checked).map(c => c.value); }
function wpQuery(params) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') q.set(k, String(v)); });
  return q.toString();
}
async function wpListFiles() {
  const sel = $('#wp-files'); if (!sel) return;
  try {
    const r = await api('/api/files?sub=data', undefined, 'bus');
    WP.files = (r.files || []).filter(f => !f.dir && f.name.toLowerCase().endsWith('.csv'));
    const cur = sel.value;
    sel.innerHTML = '<option value="">— 选择 data/ 下的 CSV —</option>' + WP.files.map(f => `<option value="${esc(f.name)}">${esc(f.name)} (${f.size_mb} MB)</option>`).join('');
    if (cur && WP.files.some(f => f.name === cur)) sel.value = cur;
  } catch (e) { toast('读取文件列表失败：' + e.message, 'err'); }
}
function wpStatus(html, cls) { const el = $('#wp-status'); if (el) el.innerHTML = html ? `<div class="${cls || ''}">${html}</div>` : ''; }
function wpFmtT(t) { return isNum(t) ? fmtLocalInput(t) : '—'; }
function wpFs(v) { return isNum(v) ? (Number.isInteger(+v) ? String(v) : (+v).toFixed(2)) : '—'; }
function wpRenderInfo(d) {
  const box = $('#wp-info'); if (!box) return;
  if (!d) { box.innerHTML = '<div class="notes">填写路径后点「获取文件信息」</div>'; return; }
  const rows = [
    ['文件', esc(d.path_display || d.path)], ['大小', `${d.size_mb} MB · ${d.rows} 行 · 编码 ${esc(d.encoding)}${d.has_header ? '' : '（无表头）'}`],
    ['通道数', `${d.n_channels}（${(d.channels || []).join(' / ')}）`],
    ['采样率', `${wpFs(d.fs)} Hz${isNum(d.fs_est) ? `（按文件数据时间计算：推算值 ${(+d.fs_est).toFixed(2)} Hz）` : `（文件无时标：按出厂配置 ${d.fs_configured} Hz）`} · 每周波 ${d.samples_per_cycle} 点（f_nom ${d.f_nom} Hz）`],
    ['时长', `${fmtDur(d.duration_s)}（${(+d.duration_s).toFixed(3)} s）`],
    ['时间模式', d.custom_time ? `自定义时间（起始＝${d.custom_time_start ? esc(d.custom_time_start) : '文件数据起始时间'}；结束＝${d.custom_time_end ? esc(d.custom_time_end) : '起始 + (行数−1)/fs'}）` : '文件数据时间'],
    ['起始时间', wpFmtT(d.t_start)], ['结束时间', wpFmtT(d.t_end) + (isNum(d.t_end_custom) ? '（自定义结束时间）' : '')],
    ['口径', d.pt_ct && d.pt_ct.enabled ? `一次侧（PT ${d.pt_ct.pt_ratio} / CT ${d.pt_ct.ct_ratio}）` : '二次侧（PT/CT 未启用）'],
  ];
  box.innerHTML = `<table><tbody>${rows.map(([k, v]) => `<tr><th style="text-align:left;white-space:nowrap">${k}</th><td>${v}</td></tr>`).join('')}</tbody></table>` +
    ((d.notes || []).length ? `<div class="notes">${d.notes.map(n => `<div>ℹ ${esc(n)}</div>`).join('')}</div>` : '');
}
async function wpInfo(silent) {
  const path = wpVal('wp-path');
  if (!path) { if (!silent) toast('请先填写波形文件路径', 'err'); return null; }
  try {
    const d = await api('/api/process/wave/info?' + wpQuery(Object.assign({ path }, wpBase())), undefined, 'bus');
    WP.info = d; wpRenderInfo(d);
    { const fsEl = $('#wp-base-fs'); if (fsEl) fsEl.value = isNum(d.fs) ? wpFs(d.fs) : ''; }     // v0.65：采样率只显示（按文件数据时间计算）
    // v0.64：起止时刻默认为空＝文件数据起止时间（自定义时间启用时＝自定义起始 / 按采样率计算的结束）；不再自动填入，只把实际时间写进占位提示
    wpSyncCustom();
    // 通道勾选框：文件里没有的通道置灰；静默刷新不改动已有勾选
    document.querySelectorAll('#wp-chans .wp-ch').forEach(c => { const has = (d.channels || []).includes(c.value); c.disabled = !has; c.parentElement.classList.toggle('off', !has); if (!has) c.checked = false; else if (!silent && !WP.chTouched) c.checked = true; });
    if (!silent) toast(`文件信息：${d.n_channels} 通道 · ${wpFs(d.fs)} Hz · ${fmtDur(d.duration_s)}`, 'ok');
    return d;
  } catch (e) { WP.info = null; wpRenderInfo(null); toast('获取文件信息失败：' + e.message, 'err'); return null; }
}
function wpSeries(d, t0) {
  return (d.channels_loaded || Object.keys(d.channels || {})).map(ch => ({ name: `${ch} (${(d.units || {})[ch] || ''})`, color: WP_COLORS[ch] || '#4ea1ff',
    data: d.t.map((x, i) => [x - t0, d.channels[ch][i]]) }));
}
function wpDrawWave(cv, d, subId, label) {
  if (!cv) return;
  const sub = $('#' + subId);
  if (!d || !d.t || !d.t.length) {
    drawLine(cv, [], { empty: label === 'cyc' ? '在有效值曲线上右键「显示周波窗」后显示' : label === 'cyc2' ? '在有效值曲线上右键「显示周波窗 2」后显示（采样瞬时值曲线）' : '点「加载波形曲线」后显示', height: label === 'wave' ? 260 : 240 });
    if (sub) sub.textContent = label === 'cyc' ? '（在有效值曲线上右键「显示周波窗」后显示：以该时刻为中心的 N 个周波原始波形）' : label === 'cyc2' ? '（在有效值曲线上右键「显示周波窗 2」后显示：以该时刻为中心的 N 个周波采样瞬时值曲线）' : '（未加载）';
    return;
  }
  const isCyc = label === 'cyc' || label === 'cyc2';
  const t0 = d.t[0];
  const hasU = (d.channels_loaded || []).some(c => c[0] === 'U'), hasI = (d.channels_loaded || []).some(c => c[0] === 'I');
  drawLine(cv, wpSeries(d, t0), { ylabel: hasU && hasI ? 'V / A' : hasU ? 'V' : 'A', fmtX: x => ts(x + t0), fmtTip: x => fmtLocalInput(x + t0), tbase: t0,
    height: isCyc ? 240 : 260, zero: true });
  if (sub) {
    const span = d.t[d.t.length - 1] - t0;
    sub.textContent = `（${d.n} 点 × ${(d.channels_loaded || []).length} 通道 · ${wpFs(d.fs)} Hz${d.resampled ? '（由 ' + wpFs(d.fs_src) + ' Hz ' + (d.method || '') + ' 重采样）' : ''} · ${wpFmtT(t0)} → ${wpFmtT(d.t[d.t.length - 1])}，${span.toFixed(3)} s${isCyc && d.cyc_center ? '，中心 ' + wpFmtT(d.cyc_center) + '，' + d.cyc_n + ' 个周波' : ''}${label === 'cyc2' ? '，采样瞬时值' : ''}${d.truncated ? '，已截断' : ''}）`;
  }
  bindCtxMenu(cv, () => canvasNativeItems(cv).concat([{ key: 'sep', sep: true }, { key: 'zoom-reset', label: '复位缩放', onClick: () => zoomReset(cv) },
    { key: 'native', label: '浏览器原生菜单（Shift + 右键）', disabled: true }]));
}
async function wpLoad() {
  const path = wpVal('wp-path');
  if (!path) { toast('请先填写波形文件路径', 'err'); return; }
  const chans = wpChans();
  const params = Object.assign({ path, t_start: wpVal('wp-tstart'), t_end: wpVal('wp-tend'), n_cycles: wpVal('wp-ncyc'), fs_out: wpVal('wp-fs'),
                                 method: wpVal('wp-method') || 'linear', channels: chans.join(','), max_points: wpMaxPoints() }, wpBase());
  const btn = $('#btn-wp-load'); if (btn) btn.disabled = true;
  wpStatus('加载波形中…');
  try {
    // 周波数为空 ⇒ 不传 n / n_cycles ＝ 起止时刻之间全部（服务端按 max_points 截断）
    const d = await api('/api/process/wave/load?' + wpQuery(params), undefined, 'bus');
    WP.wave = d; zoomReset($('#wp-wave'));
    wpDrawWave($('#wp-wave'), d, 'wp-wave-sub', 'wave');
    wpStatus(`已加载波形 ${d.n} 点 × ${d.channels_loaded.length} 通道（${wpFs(d.fs)} Hz）` + ((d.notes || []).length ? '；' + d.notes.map(esc).join('；') : ''), d.truncated ? 'bad' : 'ok');
    if (!WP.info) wpInfo(true);
  } catch (e) { wpStatus('加载波形失败：' + esc(e.message), 'bad'); toast('加载波形失败：' + e.message, 'err'); }
  finally { if (btn) btn.disabled = false; }
}
function wpDrawRms(d) {
  const cv = $('#wp-rms'); if (!cv) return;
  const sub = $('#wp-rms-sub');
  if (!d || !d.t || !d.t.length) { drawLine(cv, [], { empty: '点「加载有效值曲线」后显示', height: 260 }); if (sub) sub.textContent = '（未加载；右键曲线可「显示周波窗」）'; return; }
  const t0 = d.t[0];
  const chans = Object.keys(d.channels || {});
  const hasU = chans.some(c => c[0] === 'U'), hasI = chans.some(c => c[0] === 'I');
  const span = d.t[d.t.length - 1] - t0;
  drawLine(cv, chans.map(ch => ({ name: `${ch} RMS (${(d.units || {})[ch] || ''})`, color: WP_COLORS[ch] || '#4ea1ff', data: d.t.map((x, i) => [x - t0, d.channels[ch][i]]) })),
    { ylabel: hasU && hasI ? 'V / A' : hasU ? 'V' : 'A', fmtX: x => tsX(x + t0, span), fmtTip: x => fmtLocalInput(x + t0), tbase: t0, height: 260 });
  if (sub) sub.textContent = `（${d.n} 点 · ${d.agg_cycles > 1 ? '每 ' + d.agg_cycles + ' 个周波一点' : '逐周波'} · 共 ${d.cycles_total} 周波 · ${wpFmtT(t0)} → ${wpFmtT(d.t[d.t.length - 1])}，${fmtDur(span)}；右键曲线可「显示周波窗」）`;
  bindCtxMenu(cv, (xEpoch) => {
    const nEl = $('#wp-cyc-n'); const n = Math.max(1, Math.min(20000, parseInt((nEl && nEl.value) || '300', 10) || 300));
    const noX = !isNum(xEpoch);
    return canvasNativeItems(cv).concat([
      { key: 'sep', sep: true },
      { key: 'show-window', label: `显示周波窗（${noX ? '暂无曲线' : fmtLocalInput(xEpoch)}）`, disabled: noX,
        hint: noX ? '有效值曲线有数据后，在曲线上右键' : `以该时刻为中心取 ${n} 个周波的逐周波有效值到下方「周波窗」`,
        onClick: () => wpLoadCycleWindow(xEpoch, n) },
      { key: 'show-window2', label: `显示周波窗 2（瞬时值，${noX ? '暂无曲线' : fmtLocalInput(xEpoch)}）`, disabled: noX,     // v0.65
        hint: noX ? '有效值曲线有数据后，在曲线上右键' : `以该时刻为中心加载 ${n} 个周波的采样瞬时值曲线（不是有效值）到下方「周波窗 2」`,
        onClick: () => wpLoadCycleWindow(xEpoch, n, 2) },
      { key: 'zoom-reset', label: '复位缩放', onClick: () => zoomReset(cv) },
      { key: 'native', label: '浏览器原生菜单（Shift + 右键）', disabled: true },
    ]);
  });
}
async function wpRms() {
  const path = wpVal('wp-path');
  if (!path) { toast('请先填写波形文件路径', 'err'); return; }
  const params = Object.assign({ path, t_start: wpVal('wp-rms-tstart') || wpVal('wp-tstart'), t_end: wpVal('wp-rms-tend'), duration_s: wpVal('wp-rms-dur'),
                                 agg_cycles: wpVal('wp-rms-agg') || 1, channels: wpChans().join(',') }, wpBase());
  const btn = $('#btn-wp-rms'); if (btn) btn.disabled = true;
  wpStatus('计算有效值曲线中…');
  try {
    const d = await api('/api/process/wave/rms?' + wpQuery(params), undefined, 'bus');
    WP.rms = d; zoomReset($('#wp-rms'));
    wpDrawRms(d);
    wpStatus(`有效值曲线 ${d.n} 点（共 ${d.cycles_total} 周波${d.agg_cycles > 1 ? '，每 ' + d.agg_cycles + ' 周波一点' : ''}）` + ((d.notes || []).length ? '；' + d.notes.map(esc).join('；') : ''), 'ok');
    if (!WP.info) wpInfo(true);
  } catch (e) { wpStatus('有效值曲线失败：' + esc(e.message), 'bad'); toast('加载有效值曲线失败：' + e.message, 'err'); }
  finally { if (btn) btn.disabled = false; }
}
/* 有效值曲线右键 → 以 tEpoch 为中心的 n 个周波原始波形，画到单独的「周波窗」曲线（原采样率、当前勾选通道） */
async function wpLoadCycleWindow(tEpoch, n, which = 1) {
  const path = wpVal('wp-path');
  if (!path || !isNum(tEpoch)) return false;
  const cvId = which === 2 ? 'wp-cyc2' : 'wp-cyc', subId = which === 2 ? 'wp-cyc2-sub' : 'wp-cyc-sub', lbl = which === 2 ? '周波窗 2（瞬时值）' : '周波窗';
  const fnom = (+wpVal('wp-base-fnom')) || (WP.info && WP.info.f_nom) || (WP.rms && WP.rms.f_nom) || 50;
  const half = (n / 2) / fnom;
  let tA = tEpoch - half, tB = tEpoch + half;
  if (WP.info && isNum(WP.info.t_start) && isNum(WP.info.t_end)) {       // 靠近文件两端时整体平移，保证仍是 n 个周波
    const dur = n / fnom;
    if (tA < WP.info.t_start) { tA = WP.info.t_start; tB = tA + dur; }
    if (tB > WP.info.t_end) { tB = WP.info.t_end; tA = Math.max(WP.info.t_start, tB - dur); }
  }
  wpStatus(`装载${lbl}：中心 ${fmtLocalInput(tEpoch)}，${n} 个周波…`);
  try {
    const q = Object.assign({ path, t_start: tA.toFixed(6), t_end: tB.toFixed(6), channels: wpChans().join(',') }, wpBase());
    if (which === 2) {
      // 周波窗 2：采样瞬时值（原始波形）
      const d = await api('/api/process/wave/load?' + wpQuery(q), undefined, 'bus');
      d.cyc_center = tEpoch; d.cyc_n = n; WP.cyc2 = d;
      zoomReset($('#' + cvId)); wpDrawWave($('#' + cvId), d, subId, 'cyc2');
      wpStatus(`${lbl}已装载：${d.n} 点 × ${d.channels_loaded.length} 通道，中心 ${fmtLocalInput(tEpoch)}，${n} 个周波（${wpFs(d.fs)} Hz，采样瞬时值）`, 'ok');
    } else {
      // v0.66：周波窗（1）＝该段的逐周波有效值（统计窗 1 周波/点）
      const d = await api('/api/process/wave/rms?' + wpQuery(Object.assign(q, { agg_cycles: 1 })), undefined, 'bus');
      d.cyc_center = tEpoch; d.cyc_n = n; WP.cyc = d;
      zoomReset($('#' + cvId)); wpDrawCycRms(d);
      wpStatus(`${lbl}已装载：${d.n} 个周波的有效值 × ${Object.keys(d.channels || {}).length} 通道，中心 ${fmtLocalInput(tEpoch)}，${n} 个周波（每周波 ${d.samples_per_cycle} 点）`, 'ok');
    }
    try { $('#' + cvId).scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } catch (e) { /* jsdom */ }
    return true;
  } catch (e) { wpStatus(`装载${lbl}失败：` + esc(e.message), 'bad'); toast(`装载${lbl}失败：` + e.message, 'err'); return false; }
}
window.wpLoadCycleWindow = wpLoadCycleWindow;
/* v0.66：周波窗（1）画布：该段逐周波有效值（风格同有效值曲线） */
function wpDrawCycRms(d) {
  const cv = $('#wp-cyc'); if (!cv) return;
  const sub = $('#wp-cyc-sub');
  if (!d || !d.t || !d.t.length) {
    drawLine(cv, [], { empty: '在有效值曲线上右键「显示周波窗」后显示（该段的逐周波有效值）', height: 240 });
    if (sub) sub.textContent = '（在有效值曲线上右键「显示周波窗」后显示：以该时刻为中心 N 个周波的逐周波有效值）';
    return;
  }
  const t0 = d.t[0]; const chans = Object.keys(d.channels || {});
  const hasU = chans.some(c => c[0] === 'U'), hasI = chans.some(c => c[0] === 'I');
  const span = d.t[d.t.length - 1] - t0;
  drawLine(cv, chans.map(ch => ({ name: `${ch} RMS (${(d.units || {})[ch] || ''})`, color: WP_COLORS[ch] || '#4ea1ff', data: d.t.map((x, i) => [x - t0, d.channels[ch][i]]) })),
    { ylabel: hasU && hasI ? 'V / A' : hasU ? 'V' : 'A', fmtX: x => ts(x + t0), fmtTip: x => fmtLocalInput(x + t0), tbase: t0, height: 240 });
  if (sub) sub.textContent = `（${d.n} 个周波的有效值 × ${chans.length} 通道 · 逐周波 · ${wpFmtT(t0)} → ${wpFmtT(d.t[d.t.length - 1])}，${span.toFixed(3)} s${d.cyc_center ? '，中心 ' + wpFmtT(d.cyc_center) + '，' + d.cyc_n + ' 个周波' : ''}）`;
  bindCtxMenu(cv, () => canvasNativeItems(cv).concat([{ key: 'sep', sep: true }, { key: 'zoom-reset', label: '复位缩放', onClick: () => zoomReset(cv) },
    { key: 'native', label: '浏览器原生菜单（Shift + 右键）', disabled: true }]));
}
function renderWavePreview() {
  if (!$('#wp-wave')) return;
  wpDrawWave($('#wp-wave'), WP.wave, 'wp-wave-sub', 'wave');
  wpDrawRms(WP.rms);
  wpDrawCycRms(WP.cyc);
  wpDrawWave($('#wp-cyc2'), WP.cyc2, 'wp-cyc2-sub', 'cyc2');
}
function bindWavePreview() {
  if (!$('#wp-form')) return;
  $('#wp-files').addEventListener('change', () => { if ($('#wp-files').value) { $('#wp-path').value = $('#wp-files').value; WP.info = null; wpInfo(true); } });
  $('#wp-path').addEventListener('change', () => { WP.info = null; const fsEl = $('#wp-base-fs'); if (fsEl) fsEl.value = ''; });
  ['wp-base-fnom', 'wp-base-pt', 'wp-base-ct', 'wp-base-ptct', 'wp-base-utc', 'wp-base-custom', 'wp-base-cstart', 'wp-base-cend',
   'wp-base-wiring', 'wp-base-recon3w', 'wp-base-inv', 'wp-base-inv-a', 'wp-base-inv-b', 'wp-base-inv-c'].forEach(id => $('#' + id).addEventListener('change', () => { WP.info = null; wpSaveBase(); wpSyncCustom(); }));
  $('#btn-wp-cyc2-clear') && $('#btn-wp-cyc2-clear').addEventListener('click', () => { WP.cyc2 = null; renderWavePreview(); });
  $('#wp-maxpts').addEventListener('change', wpSaveBase);
  cmBind('wp-cm', () => { WP.info = null; wpSaveBase(); });   // v0.86：离线文件列映射（波形预览公共配置）
  $('#btn-wp-info').addEventListener('click', () => wpInfo(false));
  $('#btn-wp-load').addEventListener('click', wpLoad);
  $('#btn-wp-rms').addEventListener('click', wpRms);
  $('#btn-wp-refresh').addEventListener('click', wpListFiles);
  document.querySelectorAll('#wp-chans .wp-ch').forEach(c => c.addEventListener('change', () => { WP.chTouched = true; }));
  ['wp-tstart', 'wp-tend', 'wp-ncyc', 'wp-fs'].forEach(id => $('#' + id).addEventListener('keydown', (e) => { if (e.key === 'Enter') wpLoad(); }));
  ['wp-rms-tstart', 'wp-rms-tend', 'wp-rms-dur'].forEach(id => $('#' + id).addEventListener('keydown', (e) => { if (e.key === 'Enter') wpRms(); }));
  wpLoadDefaults();
  wpListFiles();
  renderWavePreview();
  initCtEstimate();   // v0.96
}

/* v0.96 / v0.97：数据处理 · 估计 CT（POST /api/process/ct_estimate；每侧逐周波 RMS 曲线 GET /api/process/wave/rms） */
const CT = { files: [], rms: { 'ct-bus': null, 'ct-br': null } };
const CT_SIDES = [['ct-bus', 'bus', '总线侧'], ['ct-br', 'branch', '分路侧']];
function ctV(id) { const el = $('#' + id); return el ? String(el.value || '').trim() : ''; }
function ctC(id) { const el = $('#' + id); return (el && el.checked) ? '1' : '0'; }
function ctBase(pre) {   // 本侧接线 / 极性（PT/CT 关闭，量二次侧）+ 波形预览公共列映射
  return { pt_ct_enabled: '0', wiring: ctV(pre + '-wiring') || '3p4w', reconstruct_3w: ctC(pre + '-recon3w'), invert_current: ctC(pre + '-inv'),
           invert_phases: getInvPhases(pre), ...cmQuery(pre + '-cm') };   // v0.99：本侧列映射（与其它功能同一套 cm-* 控件）
}
function ctSide(pre) {
  return { path: ctV(pre + '-path') || ctV(pre + '-files'), event: ctV(pre + '-event') || 'start', t_begin: ctV(pre + '-tbegin'), t_end: ctV(pre + '-tend'),
           phase: ctV(pre + '-phase') || 'A', win_cycles: ctV(pre + '-win') || '50', known: ctC(pre + '-known'), ct: ctV(pre + '-ct'), ...ctBase(pre) };
}
async function ctListFiles() {
  try {
    const r = await api('/api/files?sub=data', undefined, 'bus');
    CT.files = (r.files || []).filter(f => !f.dir && f.name.toLowerCase().endsWith('.csv'));
    CT_SIDES.forEach(([pre]) => { const sel = $('#' + pre + '-files'); if (!sel) return; const cur = sel.value;
      sel.innerHTML = '<option value="">— 选择 data/ 下的 CSV —</option>' + CT.files.map(f => `<option value="${esc(f.name)}">${esc(f.name)} (${f.size_mb} MB)</option>`).join('');
      if (cur && CT.files.some(f => f.name === cur)) sel.value = cur; });
  } catch (e) { toast('读取文件列表失败：' + e.message, 'err'); }
}
function ctStatus(html, cls) { const el = $('#ct-status'); if (el) el.innerHTML = html ? `<div class="${cls || ''}">${html}</div>` : ''; }
async function ctFillDefaults() {
  for (const [url, id] of [['/api/config', 'ct-bus-ct'], ['/api/branch/config', 'ct-br-ct']]) {
    try { const el = $('#' + id); if (!el || el.value) continue; const r = await (await fetch(url)).json(); const c = r && (r.config || r); if (c && c.transform && c.transform.ct_ratio != null) el.value = c.transform.ct_ratio; } catch (e) { /* 忽略 */ }
  }
}
/* 曲线上的事件时间段标线 */
function ctMarks(pre) {
  const ev = ctV(pre + '-event'); const nm = ev === 'stop' ? '停机' : '启动'; const marks = [];
  const d = CT.rms[pre]; if (!d || !d.t || !d.t.length) return marks;
  const t0 = d.t[0];
  const toEpoch = (txt) => { if (!txt) return null; if (/^\d+(\.\d+)?$/.test(txt)) return parseFloat(txt);
    const m = txt.match(/^(\d{1,2}):(\d{2}):(\d{2}(?:\.\d+)?)$/); if (m) { const dd = new Date(t0 * 1000); dd.setHours(+m[1], +m[2], 0, 0); return dd.getTime() / 1000 + parseFloat(m[3]); }
    const ms = Date.parse(txt.replace(' ', 'T')); return Number.isFinite(ms) ? ms / 1000 : null; };
  const a = toEpoch(ctV(pre + '-tbegin')), b = toEpoch(ctV(pre + '-tend'));
  if (isNum(a)) marks.push({ x: a - t0, label: nm + '开始', color: '#3ddc97', row: 0 });
  if (isNum(b)) marks.push({ x: b - t0, label: nm + '结束', color: '#ff6b6b', row: 1 });
  return marks;
}
function ctDrawRms(pre) {
  const cv = $('#' + pre + '-rms'); if (!cv) return;
  const sub = $('#' + pre + '-rms-sub'); const d = CT.rms[pre];
  if (!d || !d.t || !d.t.length) { drawLine(cv, [], { empty: '点「加载逐周波 RMS 曲线」后显示；右键曲线可设置启动 / 停机的开始、结束时刻', height: 240 }); if (sub) sub.textContent = '（未加载）'; return; }
  const t0 = d.t[0], span = d.t[d.t.length - 1] - t0; const ch = Object.keys(d.channels || {})[0];
  const side = d.ct_scaled ? `A·一次(CT ${d.ct_ratio_used})` : 'A·二次';
  drawLine(cv, [{ name: `${ch} RMS (${side})`, color: WP_COLORS[ch] || '#4ea1ff', data: d.t.map((x, i) => [x - t0, d.channels[ch][i]]) }],
    { ylabel: 'A', fmtX: x => tsX(x + t0, span), fmtTip: x => fmtLocalInput(x + t0), tbase: t0, height: 240, marks: ctMarks(pre), force: true });
  const ctNow = (ctC(pre + '-known') === '1' && parseFloat(ctV(pre + '-ct')) > 0) ? parseFloat(ctV(pre + '-ct')) : null;
  const ctStale = (d.ct_scaled ? d.ct_ratio_used : null) !== ctNow;
  if (sub) sub.textContent = `（${ch} · ${d.ct_scaled ? `一次侧安培，已按 CT ${d.ct_ratio_used} 换算` : '二次侧安培（CT 未知 / 未启用）'}${ctStale ? '（CT 设置已改，请重新加载）' : ''} · ${d.n} 点 · 每点＝${d.agg_cycles} 个周波的有效值${d.agg_cycles !== parseInt(ctV(pre + '-win') || '50', 10) ? '（计算周波数已改，请重新加载）' : ''} · ${wpFmtT(t0)} → ${wpFmtT(d.t[d.t.length - 1])}，${fmtDur(span)}；右键曲线设置事件时刻）`;
  bindCtxMenu(cv, (xEpoch) => {
    const noX = !isNum(xEpoch); const tTxt = noX ? '暂无曲线' : fmtLocalInput(xEpoch);
    const set = (ev, which) => () => { $('#' + pre + '-event').value = ev; $('#' + pre + (which === 'begin' ? '-tbegin' : '-tend')).value = fmtLocalInput(xEpoch); ctDrawRms(pre); toast(`${ev === 'start' ? '启动' : '停机'}${which === 'begin' ? '开始' : '结束'}时刻 → ${fmtLocalInput(xEpoch)}`); };
    return canvasNativeItems(cv).concat([
      { key: 'sep', sep: true },
      { key: 'start-begin', label: `设置启动开始时刻（${tTxt}）`, disabled: noX, hint: '事件类型→启动，开始时刻→该点', onClick: set('start', 'begin') },
      { key: 'start-end', label: `设置启动结束时刻（${tTxt}）`, disabled: noX, hint: '事件类型→启动，结束时刻→该点', onClick: set('start', 'end') },
      { key: 'stop-begin', label: `设置停机开始时刻（${tTxt}）`, disabled: noX, hint: '事件类型→停机，开始时刻→该点', onClick: set('stop', 'begin') },
      { key: 'stop-end', label: `设置停机结束时刻（${tTxt}）`, disabled: noX, hint: '事件类型→停机，结束时刻→该点', onClick: set('stop', 'end') },
      { key: 'sep2', sep: true },
      { key: 'zoom-reset', label: '复位缩放', onClick: () => zoomReset(cv) },
      { key: 'native', label: '浏览器原生菜单（Shift + 右键）', disabled: true },
    ]);
  });
}
async function ctLoadRms(pre) {
  const path = ctV(pre + '-path') || ctV(pre + '-files');
  if (!path) { toast('请先选择本侧文件', 'err'); return; }
  const phase = ctV(pre + '-phase') || 'A';
  if ((ctV(pre + '-wiring') === '3p3w') && phase === 'B' && ctC(pre + '-recon3w') !== '1') { toast('三相三线没有 B 相电流：请改选 A / C 相或勾选 3P3W 重构', 'err'); return; }
  const win = Math.max(1, parseInt(ctV(pre + '-win') || '50', 10) || 50);   // v0.98.1：曲线每点＝「计算周波数」个周波的有效值
  const params = Object.assign({ path, t_start: ctV(pre + '-cstart'), t_end: ctV(pre + '-cend'), agg_cycles: win, channels: 'I' + phase.toLowerCase() }, ctBase(pre));
  // v0.99.2：本侧「CT 已知」且 CT>0 → 曲线按该 CT 换算为一次侧安培（PT 置 1，只量电流）；否则仍为二次侧。估计本身仍强制二次侧（后端固定关闭 PT/CT）
  const ctKnown = ctC(pre + '-known') === '1', ctVal = parseFloat(ctV(pre + '-ct'));
  const useCt = ctKnown && isNum(ctVal) && ctVal > 0;
  if (useCt) Object.assign(params, { pt_ct_enabled: '1', pt_ratio: '1', ct_ratio: String(ctVal) });
  const btn = $('#' + pre + '-btn-rms'); if (btn) btn.disabled = true;
  try {
    const d = await api('/api/process/wave/rms?' + wpQuery(params), undefined, 'bus');
    d.ct_scaled = useCt; d.ct_ratio_used = useCt ? ctVal : null;
    CT.rms[pre] = d; zoomReset($('#' + pre + '-rms')); ctDrawRms(pre);
  } catch (e) { toast('加载逐周波 RMS 曲线失败：' + e.message, 'err'); }
  finally { if (btn) btn.disabled = false; }
}
async function ctRun() {
  const body = { bus: ctSide('ct-bus'), branch: ctSide('ct-br') };
  if (!body.bus.path || !body.branch.path) { ctStatus('请先选择两侧文件', 'bad'); return; }
  for (const [pre, , nm] of CT_SIDES) { const sd = body[pre === 'ct-bus' ? 'bus' : 'branch']; if (!sd.t_begin || !sd.t_end) { ctStatus(`${nm}：请填写事件开始 / 结束时刻（可在曲线上右键设置）`, 'bad'); return; } if (sd.known === '1' && !sd.ct) { ctStatus(`${nm}：勾选了「本侧 CT 已知」但未填写 CT 变比`, 'bad'); return; } }
  ctStatus('正在估计…'); $('#ct-result').innerHTML = ''; $('#ct-cmdrow').style.display = 'none';
  try {
    const r = await api('/api/process/ct_estimate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, 'bus');
    const dirTxt = m => m.direction === 'up' ? '↑ 上升' : m.direction === 'down' ? '↓ 下降' : '— 无';
    const row = (m, name) => `<tr><td>${name}</td><td title="${esc(m.path)}">${esc(m.path.split(/[\\/]/).pop())}</td><td class="c">${m.event_name}</td><td>${esc(m.t_begin_local)}</td><td>${esc(m.t_end_local)}</td><td class="c">${m.phase}</td><td class="c">${m.wiring}${m.reconstruct_3w ? '+重构' : ''}</td><td class="c">${m.invert_current ? '全部' : (m.invert_phases || '无')}</td><td class="n">${num(m.pre_a, 4)}</td><td class="n">${num(m.post_a, 4)}</td><td class="n">${num(m.delta_a, 4)}</td><td class="c">${dirTxt(m)}</td><td class="n">${m.snr == null ? '∞' : num(m.snr, 1)}</td><td class="n">${m.n_pre}/${m.n_post}</td></tr>`;
    const card = (sd, nm) => { const e = r.estimates && r.estimates[sd]; if (!e) return ''; const dev = e.deviation_pct == null ? '' : `；填写值 ${num(e.configured, 3)}，偏差 ${num(e.deviation_pct, 1)}%`;
      return `<div class="card"><div class="k">估计 ${nm} CT 变比</div><div class="v">${num(e.ct, 2)}</div><div class="s">由${e.from === 'bus' ? '总线侧' : '分路侧'} CT = ${num(e.known_ct, 3)} 推得${dev}${e.nominal ? '<br>' + esc(e.nominal) : ''}</div></div>`; };
    $('#ct-result').innerHTML = `<table class="ct-tbl"><thead><tr><th>侧</th><th>文件</th><th class="c">事件</th><th>开始时刻</th><th>结束时刻</th><th class="c">相</th><th class="c">接线</th><th class="c">极性反转</th><th class="n">前 (A)</th><th class="n">后 (A)</th><th class="n">ΔI (A·二次)</th><th class="c">方向</th><th class="n">信噪比</th><th class="n">周波 前/后</th></tr></thead><tbody>${row(r.bus, '总线侧')}${row(r.branch, '分路侧')}</tbody></table>
      <div class="ct-est"><div class="card"><div class="k">台阶比值 ΔI<sub>分路</sub> / ΔI<sub>总线</sub></div><div class="v">${r.ratio_branch_over_bus == null ? '—' : num(r.ratio_branch_over_bus, 4)}</div><div class="s">${esc(r.formula)}</div></div>${card('bus', '总线侧')}${card('branch', '分路侧')}</div>
      <div class="notes" style="margin-top:6px">${(r.notes || []).map(n => `<div class="warn">⚠ ${esc(n)}</div>`).join('')}<div>要采用估计值，请到「配置」页对应侧「量纲与口径」填入 CT 电流变比并点「保存该侧配置」（本功能不改运行配置）。</div></div>`;
    if (r.command) { $('#ct-cmd').textContent = r.command; $('#ct-cmdrow').style.display = ''; }
    ctStatus('');
  } catch (e) { ctStatus('估计失败：' + esc(e.message), 'bad'); }
}
function initCtEstimate() {
  if (!$('#btn-ct-run')) return;
  $('#btn-ct-run').addEventListener('click', ctRun);
  $('#btn-ct-refresh').addEventListener('click', ctListFiles);
  $('#btn-ct-copy').addEventListener('click', () => { navigator.clipboard && navigator.clipboard.writeText($('#ct-cmd').textContent || ''); toast('已复制'); });
  CT_SIDES.forEach(([pre]) => {
    $('#' + pre + '-files').addEventListener('change', () => { if ($('#' + pre + '-files').value) { $('#' + pre + '-path').value = $('#' + pre + '-files').value; CT.rms[pre] = null; ctDrawRms(pre); } });
    $('#' + pre + '-btn-rms').addEventListener('click', () => ctLoadRms(pre));
    ['-event', '-tbegin', '-tend'].forEach(sfx => $('#' + pre + sfx).addEventListener('change', () => ctDrawRms(pre)));
    ['-phase', '-wiring', '-recon3w', '-inv', '-inv-a', '-inv-b', '-inv-c'].forEach(sfx => $('#' + pre + sfx).addEventListener('change', () => { CT.rms[pre] = null; ctDrawRms(pre); }));
    $('#' + pre + '-win').addEventListener('change', () => { if (CT.rms[pre]) ctLoadRms(pre); });   // 计算周波数改了 → 按新周波数重算曲线
    cmBind(pre + '-cm', () => { CT.rms[pre] = null; ctDrawRms(pre); });   // v0.99：离线文件列映射（本侧）
    $('#' + pre + '-known').addEventListener('change', () => { const on = $('#' + pre + '-known').checked; $('#' + pre + '-ct').style.opacity = on ? '' : '.6'; if (CT.rms[pre]) ctLoadRms(pre); });   // v0.99.2：CT 已知状态改 → 重算曲线口径
    $('#' + pre + '-ct').addEventListener('change', () => { if (CT.rms[pre] && ctC(pre + '-known') === '1') ctLoadRms(pre); });   // v0.99.2：CT 值改 → 重算曲线
    ctDrawRms(pre);
  });
  ctListFiles(); ctFillDefaults();
}

/* v0.90：数据处理 · 设备画像提取（POST /api/process/nilm_profile；公共配置沿用 nt-* 调参区） */
const NP = { last: null };
function npPayload() {
  const v = id => ($('#' + id).value || '').trim();
  const t = ntPayload('np');   // v0.99.5：画像提取独立公共配置
  return { path: t.path, t_start: t.t_start, t_end: t.t_end, quantity: t.quantity, custom_time: t.custom_time,
           custom_time_start: t.custom_time_start, custom_time_end: t.custom_time_end, base_mode: t.base_mode, base: t.base,
           col_map_enabled: t.col_map_enabled, col_map: t.col_map,
           device_id: v('np-device'), labels: $('#np-labels').value, label_tol_s: v('np-tol') || null,
           pre_cycles: v('np-pre') || null, post_cycles: v('np-post') || null, merge_gap_s: ($('#np-merge') && $('#np-merge').value !== '') ? parseFloat($('#np-merge').value) : null, name: v('np-name') };
}
function npRender(d) {
  const p = d.profile || {}; const F = d.features || [];
  const nS = d.startup ? d.startup.n : 0, nD = d.shutdown ? d.shutdown.n : 0;
  const cards = [['设备', esc(p.device_id || '—')], ['口径', esc(p.unit || '—')], ['标签方式', p.label_mode === 'labels' ? '人工标签' : '自动定位'],
                 ['前 / 后窗 (周波)', `${p.pre_cycles} / ${p.post_cycles}`], ['启动 / 停止样本', `${nS} / ${nD}`]];
  $('#np-summary').innerHTML = cards.map(([k, v]) => `<div class="card"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');
  $('#np-status').innerHTML = `<div>画像已写出 <code>${esc(d.saved_to)}</code></div>` + (d.notes || []).map(n => `<div class="warn">提示：${esc(n)}</div>`).join('');
  const cr = $('#np-cmdrow'); cr.style.display = d.command ? '' : 'none'; $('#np-cmd').textContent = d.command || '';
  const f = x => (typeof x === 'number' ? (Number.isInteger(x) ? String(x) : (+x.toPrecision(4)).toString()) : String(x));
  const FN = { d_ia: 'ΔIa (A)', d_ib: 'ΔIb (A)', d_ic: 'ΔIc (A)', d_p: 'ΔP (W)', d_q: 'ΔQ (var)', peak_ratio: '峰值比', dur_cycles: '持续 (周波)' };
  let h = `<table class="np-tbl"><thead><tr><th>事件 / 统计</th>${F.map(x => `<th>${esc(FN[x] || x)}</th>`).join('')}</tr></thead><tbody>`;
  [['startup', '启动画像'], ['shutdown', '停止画像']].forEach(([k, name]) => {
    const g = d[k];
    h += `<tr><th class="cap" colspan="${F.length + 1}">${name}${g ? `：${g.n} 次事件 · 持续 ${f(g.dur_cycles.min)}~${f(g.dur_cycles.max)} 周波` : '：无样本'}</th></tr>`;
    if (!g) return;
    h += `<tr class="stat"><td>均值 μ</td>${g.mu.map(x => `<td class="n">${f(x)}</td>`).join('')}</tr><tr class="stat"><td>标准差 σ</td>${g.sigma.map(x => `<td class="n">${f(x)}</td>`).join('')}</tr>`
       + g.events.map(e => `<tr><td>${esc(e.t_start_local)}<span class="src">${esc(e.source)}</span></td>${F.map(x => `<td class="n">${f(e.vec[x])}</td>`).join('')}</tr>`).join('');
  });
  h += '</tbody></table>';
  $('#np-result').innerHTML = h;
  $('#np-json').textContent = JSON.stringify(d, null, 2);
}
async function npRun() {
  const p = npPayload();
  if (!p.path) { toast('请先在上方负荷辨识调参区填写设备侧波形文件路径', 'err'); return; }
  const mode = ntBaseMode('np'); const side = mode === 'custom' ? 'bus' : mode;
  const btn = $('#btn-np-run'); btn.disabled = true; $('#np-status').textContent = '正在回放设备侧文件并提取画像…';
  try {
    const d = await api('/api/process/nilm_profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) }, side);
    NP.last = d; npRender(d);
    $('#btn-np-fill-bus').disabled = false; $('#btn-np-fill-branch').disabled = false;
    toast('画像已写出 ' + d.saved_to, 'ok');
  } catch (e) { $('#np-status').innerHTML = `<span class="err">失败：${esc(e.message)}</span>`; toast(e.message, 'err'); }
  finally { btn.disabled = false; }
}
function npFill(side) {
  if (!NP.last) return;
  if (!NLs(side).formBuilt) buildNilmForm(side);
  // 表单可能尚未按该侧配置回填（未进过负荷辨识页）：先回填再改，避免之后保存时其它算法参数为空
  const st = side === 'branch' ? BRD.state : S.state;
  if (!NLs(side).dirty && st && st.config) fillNilmForm(st.config.nilm, side);
  const el = E(side, 'nilm-profile_path'); if (!el) { toast('负荷辨识表单尚未建立', 'err'); return; }
  el.value = NP.last.saved_to; NLs(side).dirty = true;
  const en = E(side, 'nilm-profile-enabled'); if (en && !en.checked) en.checked = true;
  toast(`已填入${side === 'branch' ? '分路侧' : '总线侧'}画像路径并勾选「设备画像匹配」；请到负荷辨识页点「保存${side === 'branch' ? '分路侧' : '总线侧'}配置」生效`, 'ok');
}

function bindProcess() {
  if (!$('#view-process')) return;
  bindWavePreview();
  if ($('#np-form')) {                                            // v0.90：设备画像提取
    $('#btn-np-run').addEventListener('click', npRun);
    // v0.99.5：画像提取独立公共配置（与调参 nt-* 同构，前缀 np-）
    $('#np-files').addEventListener('change', () => { if ($('#np-files').value) $('#np-path').value = $('#np-files').value; });
    if ($('#np-side')) $('#np-side').addEventListener('change', () => ntSyncBaseUI('np'));
    if ($('#np-custom')) { $('#np-custom').addEventListener('change', () => ntSyncCustomTime('np')); ntSyncCustomTime('np'); }
    cmBind('np-cm', () => ntSaveBase('np'));
    ['np-base-fs', 'np-base-fnom', 'np-base-pt', 'np-base-ct', 'np-base-ptct', 'np-base-utc', 'np-base-wiring', 'np-base-recon3w', 'np-base-inv', 'np-base-inv-a', 'np-base-inv-b', 'np-base-inv-c'].forEach(id => { const el = document.getElementById(id); if (el) el.addEventListener('change', () => ntSaveBase('np')); });
    if ($('#btn-np-base-default')) $('#btn-np-base-default').addEventListener('click', async () => { try { await ntLoadBase('default', 'bus', 'np'); toast('画像提取基准配置已恢复为出厂值', 'ok'); } catch (e) { toast(e.message, 'err'); } });
    if ($('#btn-np-base-bus')) $('#btn-np-base-bus').addEventListener('click', async () => { try { await ntLoadBase('running', 'bus', 'np'); toast('已填入总线侧运行配置的值（可再修改，不影响总线侧）', 'ok'); } catch (e) { toast(e.message, 'err'); } });
    if ($('#btn-np-base-branch')) $('#btn-np-base-branch').addEventListener('click', async () => { try { await ntLoadBase('running', 'branch', 'np'); toast('已填入分路侧运行配置的值（可再修改，不影响分路侧）', 'ok'); } catch (e) { toast(e.message, 'err'); } });
    ntInitBase('np'); ntListFiles('np');
    if ($('#btn-np-refresh')) $('#btn-np-refresh').addEventListener('click', () => ntListFiles('np'));
    $('#btn-np-fill-bus').addEventListener('click', () => npFill('bus'));
    $('#btn-np-fill-branch').addEventListener('click', () => npFill('branch'));
    $('#btn-np-copy').addEventListener('click', () => { navigator.clipboard && navigator.clipboard.writeText($('#np-cmd').textContent || ''); toast('已复制', 'ok'); });
  }
  if ($('#nt-form')) {
    $('#nt-files').addEventListener('change', () => { if ($('#nt-files').value) $('#nt-path').value = $('#nt-files').value; ntStep2Hint(); });
    $('#nt-path').addEventListener('change', ntStep2Hint);
    // v0.99.11：第 ① 步（设备侧估计最小关心负荷）
    $('#nt-dev-files').addEventListener('change', () => { if ($('#nt-dev-files').value) $('#nt-dev-path').value = $('#nt-dev-files').value; ntStep2Hint(); });
    $('#btn-nt-est-dev').addEventListener('click', ntEstimateFromDevice);
    $('#btn-nt-run').addEventListener('click', ntRun);
    // v0.72：独立基准配置
    if ($('#nt-side')) $('#nt-side').addEventListener('change', () => ntSyncBaseUI('nt'));
    if ($('#nt-custom')) { $('#nt-custom').addEventListener('change', () => ntSyncCustomTime('nt')); ntSyncCustomTime('nt'); }
    cmBind('nt-cm', () => ntSaveBase('nt'));                     // v0.86：离线文件列映射（调参，随基准配置存浏览器本地）
    ['nt-base-fs', 'nt-base-fnom', 'nt-base-pt', 'nt-base-ct', 'nt-base-ptct', 'nt-base-utc',
     'nt-base-wiring', 'nt-base-recon3w', 'nt-base-inv', 'nt-base-inv-a', 'nt-base-inv-b', 'nt-base-inv-c'].forEach(id => { const el = $('#' + id); if (el) el.addEventListener('change', () => ntSaveBase('nt')); });
    if ($('#btn-nt-base-default')) $('#btn-nt-base-default').addEventListener('click', async () => { try { await ntLoadBase('default'); toast('基准配置已恢复为出厂值', 'ok'); } catch (e) { toast(e.message, 'err'); } });
    if ($('#btn-nt-base-bus')) $('#btn-nt-base-bus').addEventListener('click', async () => { try { await ntLoadBase('running', 'bus'); toast('已填入总线侧运行配置的值（可再修改，不影响总线侧）', 'ok'); } catch (e) { toast(e.message, 'err'); } });
    if ($('#btn-nt-base-branch')) $('#btn-nt-base-branch').addEventListener('click', async () => { try { await ntLoadBase('running', 'branch'); toast('已填入分路侧运行配置的值（可再修改，不影响分路侧）', 'ok'); } catch (e) { toast(e.message, 'err'); } });
    ntInitBase();
    $('#btn-nt-refresh').addEventListener('click', () => ntListFiles('nt'));
    $('#btn-nt-apply').addEventListener('click', ntApply);
    $('#btn-nt-est-fill').addEventListener('click', () => {
      if (!NT.est || NT.est.value === null) return;
      const pk = $('#nt-est-pick') ? $('#nt-est-pick').value : 'min';
      if (pk === 'manual') { (NT.est.unit === 'A' ? $('#nt-mina') : $('#nt-minw')).focus(); toast('请在「最小关心负荷」输入框手填', 'ok'); return; }
      const raw = pk === 'primary' && NT.est.primary != null ? NT.est.primary : NT.est.value;
      const v = +(+raw).toPrecision(4);
      if (NT.est.unit === 'A') { $('#nt-mina').value = v; $('#nt-minw').value = ''; } else { $('#nt-minw').value = v; $('#nt-mina').value = ''; }
      $('#nt-minauto').checked = false;
      toast(`已填入最小关心负荷 ${v} ${NT.est.unit}，再点「量噪声并给出参数」按此值计算`, 'ok');
    });
    $('#btn-nt-copy').addEventListener('click', async () => {
      if (!NT.command) return;
      try { await navigator.clipboard.writeText(NT.command); toast('命令已复制', 'ok'); }
      catch (e) { toast('复制失败：' + e.message, 'err'); }
    });
    ntListFiles();
  }
  $('#rs-files').addEventListener('change', () => { if ($('#rs-files').value) { $('#rs-path').value = $('#rs-files').value; rsPreview(); } });
  ['rs-path', 'rs-fs'].forEach(id => $('#' + id).addEventListener('input', rsPreview));
  $('#btn-rs-probe').addEventListener('click', rsProbe);
  $('#btn-rs-run').addEventListener('click', rsRun);
  $('#btn-rs-cancel').addEventListener('click', rsCancel);
  $('#btn-rs-refresh').addEventListener('click', rsListFiles);
  $('#btn-rs-use').addEventListener('click', rsUseAsSource);
  $('#rs-errwin').addEventListener('change', rsSaveErrCfg);
  $('#rs-err').addEventListener('change', rsSaveErrCfg);
  cmBind('rs-cm');                                   // v0.86：离线文件列映射（重采样）
}


/* 配置表单排版规范化（v0.17.3）：
 *  ① 勾选框与标题顶部对齐（.chk/.check → flex，勾选框固定在第一列）；
 *  ② 标签文字里的说明部分（「：…」或尾部「（…）」）拆成 .note 单独一行、缩进到输入框列下，与正式配置项区分；
 *     「csv_file：」「csv_tail：」这类适用范围前缀渲染成小标签 .scope；
 *  ③ 普通配置项统一为「左标签 + 右输入框」两列网格（.f）。
 *  只改 DOM 结构不改 id / 文本内容：textContent、按 id 取元素、disabled、label.off 等既有约定全部保持。 */
function splitLabelText(raw) {
  let text = raw.replace(/\s+/g, ' ').trim();
  let scope = '';
  const m = text.match(/^([a-z_]+(?:\s*\/\s*[a-z_]+)*)：/);
  if (m) { scope = m[1].replace(/\s*\/\s*/g, ' / '); text = text.slice(m[0].length).trim(); }
  let title = text, note = '';
  const c = text.indexOf('：');
  if (c > 0) { title = text.slice(0, c).trim(); note = text.slice(c + 1).trim(); }
  else {
    const o = text.indexOf('（');
    if (o > 0 && text.endsWith('）')) {
      const inner = text.slice(o + 1, -1).trim();
      if (inner.length > 10) { title = text.slice(0, o).trim(); note = inner; }
    }
  }
  return { scope, title, note };
}
function normalizeConfigForms(root = document) {
  root.querySelectorAll('.form label, .row2 label').forEach((lab) => {
    if (lab.dataset.norm || lab.closest('.toggle') || lab.closest('.curvehdr') || lab.closest('.stat') || lab.closest('.colmap-blk')) return;
    if (lab.classList.contains('f') && lab.querySelector(':scope > .lbl')) { lab.dataset.norm = '1'; return; }   // v0.99.3：HTML 已按 label.f（.lbl + 控件 + .note）编排的标签不再二次包装   // v0.86.1：列映射块自带布局，不做规范化拆分
    const nodes = [...lab.childNodes];
    const ctrl = nodes.find(n => n.nodeType === 1 && /^(INPUT|SELECT|TEXTAREA)$/.test(n.tagName));
    if (!ctrl) return;
    const isChk = ctrl.tagName === 'INPUT' && (ctrl.type === 'checkbox' || ctrl.type === 'radio');
    const textNodes = nodes.filter(n => n.nodeType === 3 || (n.nodeType === 1 && n !== ctrl && !n.querySelector('input,select')));
    if (!textNodes.length) return;
    const html = textNodes.map(n => n.nodeType === 3 ? n.textContent : n.outerHTML).join('');
    const plain = textNodes.map(n => n.textContent).join('');
    const { scope, title, note } = splitLabelText(plain);
    const hasMarkup = /<\w+/.test(html);
    textNodes.forEach(n => n.remove());
    const head = document.createElement('span'); head.className = 'lbl';
    if (scope) { const sc = document.createElement('span'); sc.className = 'scope'; sc.textContent = scope; head.appendChild(sc); }
    const ttl = document.createElement('span'); ttl.className = 'ttl';
    if (hasMarkup && !note) ttl.innerHTML = html.replace(/^\s*[a-z_ \/]+：/, '').trim(); else ttl.textContent = title;
    head.appendChild(ttl);
    let noteEl = null;
    if (note) { noteEl = document.createElement('small'); noteEl.className = 'note'; noteEl.textContent = note; }
    lab.dataset.norm = '1';
    if (isChk) {
      lab.classList.add('chk');
      if (noteEl) head.appendChild(noteEl);
      lab.insertBefore(head, ctrl.nextSibling);
    } else {
      lab.classList.add('f');
      lab.insertBefore(head, lab.firstChild);
      if (noteEl) lab.appendChild(noteEl);
    }
  });
}
window.normalizeConfigForms = normalizeConfigForms;

async function init() {
  normalizeConfigForms();
  buildDualViews();
  bind();
  // v0.99.9：顶栏高度 → CSS 变量 --topbar-h（导航条 sticky top / 高度随之变化；窗口缩放、状态行换行时实时更新）
  const syncTopbar = () => { const tb = $('#topbar'); if (tb) document.documentElement.style.setProperty('--topbar-h', Math.ceil(tb.getBoundingClientRect().height) + 'px'); };
  syncTopbar(); window.addEventListener('resize', syncTopbar);
  if (window.ResizeObserver && $('#topbar')) new ResizeObserver(syncTopbar).observe($('#topbar'));
  // 导航条：切换页面后把当前激活项滚入可视区（导航项多于视口高度时）
  document.querySelectorAll('#navbar .navitem').forEach(b => b.addEventListener('click', () => { try { b.scrollIntoView({ block: 'nearest' }); } catch (e) { /* 老浏览器 */ } }));
  // v0.99.8：PT/CT 门控 + 3P3W 门控（数据源两侧 / 调参 / 画像 / 波形预览 / 估计 CT）
  ptctGate('cfg-scale', 'cfg-pt', 'cfg-ct'); ptctGate('br-scale', 'br-pt', 'br-ct');
  ptctGate('nt-base-ptct', 'nt-base-pt', 'nt-base-ct', () => ntSaveBase('nt')); ptctGate('np-base-ptct', 'np-base-pt', 'np-base-ct', () => ntSaveBase('np'));
  ptctGate('wp-base-ptct', 'wp-base-pt', 'wp-base-ct', () => { if (typeof wpSaveBase === 'function') wpSaveBase(); });
  wiringGate('cfg-wiring', 'cfg-recon3w'); wiringGate('br-wiring', 'br-recon3w');
  wiringGate('nt-base-wiring', 'nt-base-recon3w', () => ntSaveBase('nt')); wiringGate('np-base-wiring', 'np-base-recon3w', () => ntSaveBase('np'));
  wiringGate('wp-base-wiring', 'wp-base-recon3w', () => { if (typeof wpSaveBase === 'function') wpSaveBase(); });
  wiringGate('ct-bus-wiring', 'ct-bus-recon3w'); wiringGate('ct-br-wiring', 'ct-br-recon3w');
  try {
    S.state = await api('/api/state');
  } catch (e) { toast('无法获取服务状态：' + e.message, 'err'); }
  try {
    const r = await fetch(apiUrl('/api/result?full=true'));
    if (r.ok) S.result = await r.json();
  } catch (e) { /* 尚无结果 */ }
  applySideUI();
  connectWS(); startStateWatch();
  renderTop(); render();
  setNavFoot('就绪 · 左侧导航切换子界面');
  setTimeout(refreshHistory, 500);
}

document.addEventListener('DOMContentLoaded', init);
