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
  const height = h || cv.getAttribute('height') || 200;
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

function drawLine(cv, series, opt = {}) {
  const { ctx, w, h } = prep(cv, opt.height);
  const pad = { l: 62, r: 12, t: 12, b: 26 };
  const pts = series.filter(s => s && s.data && s.data.length);
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
      const d = await api(`/api/history/${k}?n=400`);
      S.histCache[k] = d.points || []; S.histAt[k] = Date.now();
    } catch (e) { S.histCache[k] = S.histCache[k] || []; }
  }));
  render();
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
           { ylabel: 'V', fmtX: x => ts(x + tref(hv)), empty: '暂无电压趋势（需累计 ≥2 个窗）' });
  drawLine($('#ov-i'), [{ name: 'Ia', color: COLORS.A, data: hi.map(p => [p.t - tref(hi), p.Ia]) },
                        { name: 'Ib', color: COLORS.B, data: hi.map(p => [p.t - tref(hi), p.Ib]) },
                        { name: 'Ic', color: COLORS.C, data: hi.map(p => [p.t - tref(hi), p.Ic]) }],
           { ylabel: 'A', fmtX: x => ts(x + tref(hi)) });
  drawLine($('#ov-p'), [{ name: 'P', color: COLORS.P, data: hp.map(p => [p.t - tref(hp), p.P]) },
                        { name: 'Q', color: COLORS.Q, data: hp.map(p => [p.t - tref(hp), p.Q]) },
                        { name: 'S', color: COLORS.S, data: hp.map(p => [p.t - tref(hp), p.S]) }],
           { ylabel: 'W/var/VA', fmtX: x => ts(x + tref(hp)) });
  drawLine($('#ov-thd'), [{ name: 'THD_U', color: COLORS.A, data: hh.map(p => [p.t - tref(hh), p.THD_U]) },
                          { name: 'THD_I', color: COLORS.C, data: hh.map(p => [p.t - tref(hh), p.THD_I]) }],
           { ylabel: '%', fmtX: x => ts(x + tref(hh)), zero: true });

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
  drawLine($('#v-wave'), waveData(v), { ylabel: 'V', zero: true, fmtX: x => x.toFixed(3) + 's', height: 240 });
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
  drawLine($('#i-wave'), waveData(i), { ylabel: 'A', zero: true, fmtX: x => x.toFixed(3) + 's', height: 240 });
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
  drawLine($('#p-wave'), ser, { ylabel: 'W', zero: true, fmtX: x => x.toFixed(3) + 's', height: 220 });
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
           { ylabel: '', fmtX: x => ts(x + t0), height: 220 });
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
           { ylabel: 'Hz', fmtX: x => ts(x + t0), height: 200 });
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
           { ylabel: scale === 'db' ? 'dB' : (ch[0] === 'U' ? 'V' : 'A'), fmtX: x => x.toFixed(0) + 'Hz', height: 300, legend: true });
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

function renderSource() {
  const st = S.state || {}, cfg = st.config || {};
  if (cfg.source) {
    $('#src-kind').value = cfg.source.kind;
    $('#src-path').value = cfg.source.path || '';
    $('#src-host').value = cfg.source.host || '';
    $('#src-port').value = cfg.source.port || 9000;
    $('#src-frame').value = cfg.source.frame || 'text_csv';
    $('#src-block').value = cfg.source.block_samples || 640;
    $('#src-speed').value = cfg.source.sim_speed !== undefined ? cfg.source.sim_speed : 1;
    $('#src-tailend').checked = !!cfg.source.tail_from_end;
    $('#src-newest').checked = !!cfg.source.watch_dir_newest;
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
  const e = st.engine || {}, src = st.source || {};
  const emits = e.emits || {};
  const summary = [
    `运行状态：<b>${st.running ? '运行中' : (st.finished ? '已结束' : '已停止')}</b>` +
      (st.error ? `　✗ ${esc(st.error)}` : ''),
    `数据源：<b>${esc(src.kind || e.source_kind || '—')}</b>` +
      (src.path ? `　文件 ${esc(src.path)}` : '') +
      (src.endpoint ? `　${esc(src.endpoint)}` : ''),
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

function renderExport() {
  const st = S.state || {};
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
  return {
    kind: $('#src-kind').value,
    path: $('#src-path').value.trim(),
    host: $('#src-host').value.trim(),
    port: +$('#src-port').value,
    frame: $('#src-frame').value,
    block_samples: +$('#src-block').value,
    sim_speed: +$('#src-speed').value,
    tail_from_end: !!$('#src-tailend').checked,
    watch_dir_newest: !!$('#src-newest').checked,
  };
}

function collectConfigPayload() {
  return {
    transform: { pt_ratio: +$('#cfg-pt').value, ct_ratio: +$('#cfg-ct').value,
                 enabled: $('#cfg-scale').checked, voltage_input: $('#cfg-uin').value },
    sampling: { fs: +$('#cfg-fs').value, f_nom: +$('#cfg-fnom').value, adaptive_freq: $('#cfg-adaptive').checked },
    harmonic: { order_max: +$('#cfg-hmax').value },
    power: { apparent: $('#cfg-apparent').value, reactive: $('#cfg-reactive').value },
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
    const payload = Object.assign(collectSourcePayload(), collectConfigPayload(), payloadExtra);
    const r = await api('/api/engine/start', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    toast(`已启动数据源：${r.config.source.kind}`, 'ok');
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
    const r = await api('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
                                         body: JSON.stringify(collectConfigPayload()) });
    toast('配置已保存并热更新', 'ok');
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
