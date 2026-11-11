#!/usr/bin/env node
/* 智能问答前端行为检查：加载真实 HTML + app.js 中的 assistant 模块，mock 同源 API，不访问模型网络。
 * 用法：node tools/ui_assistant_check.cjs（需 npm ci / jsdom） */
'use strict';
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const ROOT = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
const style = fs.readFileSync(path.join(ROOT, 'app/static/style.css'), 'utf8');
const source = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
const start = source.indexOf('/* ------------------------------------------------------------------ 智能问答');
const end = source.indexOf('async function init() {', start);
if (start < 0 || end < 0) throw new Error('未找到智能问答模块代码');

const dom = new JSDOM(html, { url: 'http://localhost/', runScripts: 'dangerously', pretendToBeVisual: true });
const { window } = dom;
window.S = { view: 'overview', side: 'bus' };
window.sideOf = () => window.S.side;
window.apiUrl = (path, side = window.sideOf()) => side === 'branch' && typeof path === 'string' && path.startsWith('/api/')
  ? '/api/branch/' + path.slice(5) : path;
window.TextDecoder = TextDecoder;
window.TextEncoder = TextEncoder;
window.ReadableStream = ReadableStream;
window.AbortController = AbortController;
let confirmMessages = [];
let nextPromptValue = null;
window.confirm = message => { confirmMessages.push(String(message || '')); return true; };
window.prompt = (_message, defaultValue) => {
  const result = nextPromptValue === null ? defaultValue : nextPromptValue;
  nextPromptValue = null;
  return result;
};

let config = {
  enabled: true, default_model_type: 'builtin',
  local_base_url: 'http://127.0.0.1:11434/v1',
  cloud_base_url: 'https://api.example.test/v1', cloud_model: 'cloud-model',
  cloud_api_profiles: [{ id: 'cloud-alt', name: '备用云端', base_url: 'https://api.alt.example/v1', model: 'alt-chat', api_key_set: true }],
  timeout_s: 90, temperature: 0.2, max_tokens: 2048,
  rag_enabled: true, rag_top_k: 4, rag_similarity_threshold: 0.08,
  log_queries: false, sensitive_terms_configured: true, sensitive_terms_count: 1, visible_views: ['overview'],
  cloud_api_key_set: false, local_api_key_set: false, admin_configurable: true,
};
const views = [{ id: 'overview', label: '总览面板' }, { id: 'nilm', label: '负荷辨识事件' }];
const tools = [
  { id: 'start_current_source', title: '启动当前侧数据源检测', scope: 'engine.start' },
  { id: 'list_recordings', title: '查询可用录波文件', scope: 'recordings.read' },
  { id: 'list_profiles', title: '查询设备画像', scope: 'profiles.read' },
];
const encoder = new TextEncoder();
const jsonResponse = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'content-type': 'application/json' },
});
let lastConfigPayload = null;
let lastIdentityModel = null;
let lastIdentityToken = null;
let lastChatPayload = null;
let lastConfirmPayload = null;
let lastConfirmHeaders = null;
const exportDownloadUrls = [];
let emitProposal = false;
let emitClarification = false;
const CLARIFICATION_TEXT = '我暂未创建操作预览。你的请求更符合「切换当前侧接线模式」，而不是「查询当前侧运行状态」。请确认希望执行的单一动作。';
let lastImportedDocuments = null;
let lastLocalModelRefresh = null;
let nextLocalModelRefresh = { status: 'ready', models: ['refreshed-local-model'] };
let knowledgeDocuments = [];
const bundledDocuments = [
  { id: 'builtin-platform-parameters', name: '平台参数清单', title: '平台参数清单', category: '平台参数', summary: '代码默认与两侧模板值', content: '# 平台参数清单\n\n| 配置路径 | 代码默认值 | 总线模板值 | 分路模板值 |\n| --- | --- | --- | --- |\n| `sampling.fs` | `6400.0` | `6400.0` | `6400.0` |', characters: 100 },
  { id: 'builtin-software-design', name: '软件设计文档', title: '软件设计文档', category: '设计', summary: '架构与模块说明', content: '# 软件设计文档\n\n平台模块说明。', characters: 30 },
];
window.fetch = async (url, options = {}) => {
  if (url === '/api/assistant/documents') return jsonResponse({ ok: true, count: bundledDocuments.length, characters: 130, documents: bundledDocuments });
  if (url === '/api/assistant/config' && (!options.method || options.method === 'GET')) {
    return jsonResponse({ ok: true, config, views, tools });
  }
  if (url === '/api/assistant/local-models' && (!options.method || options.method === 'GET')) {
    return jsonResponse({ ok: true, status: 'ready', models: ['qwen2.5:7b', 'llama3.2:latest'], error: '', updated_at: 1 });
  }
  if (url === '/api/assistant/local-models/refresh' && options.method === 'POST') {
    if (options.headers['X-Assistant-Admin-Token'] !== 'admin') throw new Error('刷新本地模型列表时缺少管理员口令');
    lastLocalModelRefresh = { body: options.body || null, headers: options.headers };
    if (nextLocalModelRefresh.fail) return jsonResponse({ ok: false, error: '本地服务暂不可用' }, 503);
    return jsonResponse({ ok: true, ...nextLocalModelRefresh, error: '', updated_at: 2 });
  }
  if (url === '/api/assistant/config/private') {
    if (options.headers['X-Assistant-Admin-Token'] !== 'admin') throw new Error('管理员读取敏感词时缺少口令');
    return jsonResponse({ ok: true, config: { ...config, sensitive_terms: ['PROJECT-ALPHA'] } });
  }
  if (url === '/api/assistant/knowledge/import' && options.method === 'POST') {
    if (options.headers['X-Assistant-Admin-Token'] !== 'admin') throw new Error('知识库导入时缺少管理员口令');
    lastImportedDocuments = JSON.parse(options.body).documents;
    knowledgeDocuments = lastImportedDocuments.map((doc, index) => ({ id: 'doc-' + index, name: doc.name, characters: doc.content.length, chunks: 1 }));
    return jsonResponse({ ok: true, count: knowledgeDocuments.length, documents: knowledgeDocuments });
  }
  if (url === '/api/assistant/knowledge') return jsonResponse({ ok: true, count: knowledgeDocuments.length, documents: knowledgeDocuments });
  if (url === '/api/assistant/config' && options.method === 'PUT') {
    if (options.headers['X-Assistant-Admin-Token'] !== 'admin') throw new Error('管理员口令请求头缺失');
    lastConfigPayload = JSON.parse(options.body);
    const safePayload = { ...lastConfigPayload };
    delete safePayload.cloud_api_key; delete safePayload.local_api_key;
    delete safePayload.cloud_api_profile_secrets; delete safePayload.clear_cloud_api_profile_secrets;
    const priorProfiles = Array.isArray(config.cloud_api_profiles) ? config.cloud_api_profiles : [];
    const profileSecrets = lastConfigPayload.cloud_api_profile_secrets || {};
    const profilesToClear = lastConfigPayload.clear_cloud_api_profile_secrets || [];
    const cloudProfiles = (lastConfigPayload.cloud_api_profiles || priorProfiles).map(profile => ({
      ...profile,
      api_key_set: !!profileSecrets[profile.id] || (!profilesToClear.includes(profile.id)
        && !!priorProfiles.find(existing => existing.id === profile.id && existing.api_key_set)),
    }));
    config = { ...config, ...safePayload, cloud_api_profiles: cloudProfiles,
      cloud_api_key_set: lastConfigPayload.cloud_api_key ? true
        : lastConfigPayload.clear_cloud_api_key ? false : config.cloud_api_key_set,
      admin_configurable: true };
    return jsonResponse({ ok: true, config });
  }
  if (url.startsWith('/api/assistant/tools/identity?model_type=')) {
    lastIdentityModel = decodeURIComponent(url.split('model_type=')[1] || '');
    lastIdentityToken = options.headers['X-Assistant-Operator-Token'] || '';
    return jsonResponse({ ok: true, operator_id: 'jsdom-operator', scopes: ['assistant.read'], available_tools: [] });
  }
  if (url.includes('/assistant/tools/export/')) {
    exportDownloadUrls.push(url);
    return new Response('a,b\n1,2\n', { status: 200, headers: { 'content-type': 'text/csv' } });
  }
  if (url === '/api/assistant/tools/confirm' && options.method === 'POST') {
    lastConfirmPayload = JSON.parse(options.body); lastConfirmHeaders = options.headers;
    return jsonResponse({ ok: true, result: { message: '接线模式已切换为 3p4w', side: 'bus' } });
  }
  if (url === '/api/assistant/chat') {
    const payload = JSON.parse(options.body); lastChatPayload = payload;
    if (!payload.stream || !['builtin', 'local', 'cloud'].includes(payload.model_type)) throw new Error('聊天请求参数不符合预期');
    const frames = [
      { type: 'sources', sources: [{ name: payload.model_type === 'builtin' ? '平台参数清单' : 'guide.md', score: 0.91 }] },
      { type: 'delta', text: emitClarification ? CLARIFICATION_TEXT : payload.model_type === 'builtin' ? '### 内置知识库｜本地文档检索\n\n平台参数清单摘录：`pre_cycles` 与 `window_cycles` 的代码默认值须与当前配置核对。' : '## 结论\n\n支持 **Markdown**、`代码`。\n\n```js\nalert(1)\n```\n\n<img src=x onerror=alert(1)>\n\n[坏链接](javascript:alert(1))' },
      ...(emitProposal ? [{ type: 'proposal', proposal: {
        id: 'proposal-jsdom-1', tool: 'set_wiring_mode', title: '切换当前侧接线模式',
        summary: '将当前侧接线模式切换为 3p4w', impact: '只改当前侧接线模式。',
        arguments: { wiring: '3p4w' }, side: 'bus', status: 'pending',
        requires_second_confirmation: true, confirmation_code: '123456', expires_at: Date.now() / 1000 + 300,
      } }] : []),
      // 与服务端一致：澄清文字先走 delta，随后单独发一帧 clarification 标记，不发 proposal。
      ...(emitClarification ? [{ type: 'clarification', message: CLARIFICATION_TEXT }] : []),
      { type: 'done' },
    ].map(frame => 'data: ' + JSON.stringify(frame) + '\n\n').join('');
    const bytes = encoder.encode(frames);
    const body = new ReadableStream({ start(controller) {
      controller.enqueue(bytes.slice(0, 31)); // 特意在 SSE frame 中间切块，覆盖网络分片边界
      controller.enqueue(bytes.slice(31));
      controller.close();
    } });
    return new Response(body, { headers: { 'content-type': 'text/event-stream' } });
  }
  throw new Error('不应访问此 API：' + url);
};

Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1024 });
Object.defineProperty(window, 'innerHeight', { configurable: true, value: 768 });
window.eval(source.slice(start, end) + '\nwindow.__assistantState = ASSISTANT_UI;');
window.assistantInit();
const $ = id => window.document.getElementById(id);
let checkCount = 0;
const check = (ok, message) => { if (!ok) throw new Error(message); checkCount += 1; };
function mockScrollArea(element, height, viewport, initialTop = 0) {
  let top = initialTop;
  const getHeight = typeof height === 'function' ? height : () => height;
  Object.defineProperties(element, {
    scrollHeight: { configurable: true, get: getHeight },
    clientHeight: { configurable: true, value: viewport },
    scrollTop: { configurable: true, get: () => top, set: value => { top = Math.max(0, Math.min(getHeight() - viewport, Number(value) || 0)); } },
  });
  return { get top() { return top; }, set top(value) { top = Math.max(0, Math.min(getHeight() - viewport, Number(value) || 0)); } };
}
check($('assistant-launcher').hidden, '配置读取前问答入口应默认隐藏');

(async () => {
  // 等待首次配置读取及启动时加载的完整内置文档库。
  for (let i = 0; i < 100 && (!window.__assistantState.config || !window.__assistantState.documents.length || !window.__assistantState.localModels.length); i++) await new Promise(resolve => setTimeout(resolve, 10));
  check(!!window.__assistantState.config, '配置未加载');
  const toolChecks = $('assistant-enabled-tool-checks');
  const startToolInput = Array.from(toolChecks.querySelectorAll('input[data-tool-id]'))
    .find(input => input.dataset.toolId === 'start_current_source');
  const recordingToolInput = Array.from(toolChecks.querySelectorAll('input[data-tool-id]'))
    .find(input => input.dataset.toolId === 'list_recordings');
  check(!!startToolInput && startToolInput.closest('label').querySelector('.assistant-tool-scope').textContent === '所需 scope：engine.start',
    '全局工具清单未显示 start_current_source 的精确操作员 scope');
  check(!!recordingToolInput && recordingToolInput.closest('label').querySelector('.assistant-tool-scope').textContent === '所需 scope：recordings.read',
    '全局工具清单未显示 list_recordings 的精确操作员 scope');
  check($('assistant-tool-scope-help').textContent.includes('不会单独授予操作员权限')
    && $('assistant-tool-scope-help').textContent.includes('ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS'),
  '全局 allow-list 说明未区分操作员 token scopes');
  check(!$('assistant-launcher').hidden, '总览页应显示入口');
  const sessionHeading = $('assistant-session-pane').querySelector('.assistant-session-heading h2');
  check(sessionHeading && sessionHeading.textContent === '智能问答助手', '会话管理侧栏标题应为“智能问答助手”');
  check($('assistant-title').hidden && !$('assistant-title').textContent, '新会话尚无正式问答时，右侧标题应为空');
  const modelControls = window.document.querySelector('.assistant-model-controls');
  const chatHeader = window.document.querySelector('.assistant-chat-header');
  const backendType = $('assistant-model-type'), modelNameControl = $('assistant-model-name');
  const attachButton = $('assistant-attach-image');
  check(!!backendType && html.includes('id="assistant-model-type"'), '问答 composer 底部缺少后端选择器');
  check(modelControls && modelControls.contains(backendType) && modelControls.contains(modelNameControl)
    && modelControls.contains($('assistant-send')) && !chatHeader.contains(modelNameControl), '后端、模型与发送控件应归入底部控制组');
  check(modelControls.children[0] === backendType && modelControls.children[1] === modelNameControl
    && modelControls.children[2] === $('assistant-refresh-local-models') && modelControls.lastElementChild === $('assistant-send'), '底部后端、模型、刷新、发送控件顺序错误');
  check(backendType.value === 'builtin' && modelNameControl.hidden && $('assistant-refresh-local-models').hidden
    && $('assistant-local-models-status').hidden, '内置模式应隐藏模型、刷新与本地发现状态');
  check(modelNameControl.getAttribute('aria-label') === '选择具体模型'
    && !window.document.querySelector('.assistant-model-controls label'), '具体模型下拉应去掉可见标题并保留无障碍名称');
  check($('assistant-default-backend').value === 'builtin', '未配置模型时应从设置默认使用内置文档通道');
  check(!Object.prototype.hasOwnProperty.call(config, 'local_model') && !$('assistant-local-model') && !$('assistant-local-model-select'), '管理员设置不得保留本地模型名称配置');
  check($('assistant-local-url') && $('assistant-local-key'), '本地发现和聊天应共用管理员保存的地址与 API Key');
  check(attachButton.textContent.trim() === '附件' && attachButton.title === '附件'
    && attachButton.getAttribute('aria-label') === '添加附件', '附件按钮的可见文案或无障碍名称不正确');
  check($('assistant-privacy-note').textContent.includes('本地文档模式'), '内置通道隐私说明未显示本地文档语义');
  check(window.__assistantState.documents.length === 2, '启动时未加载文档目录');
  check(window.__assistantState.localModels.length === 2, '配置加载后未读取本地模型候选');
  backendType.value = 'local'; backendType.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations[0].backend === 'local' && !modelNameControl.hidden
    && !$('assistant-refresh-local-models').hidden, '选择本地后端后模型列表与刷新入口未显示');
  check(Array.from(modelNameControl.querySelectorAll('option')).map(option => option.value).filter(Boolean).join(',') === 'qwen2.5:7b,llama3.2:latest'
    && modelNameControl.value === 'qwen2.5:7b', '本地会话没有使用服务发现模型作为候选 / 初始选择');
  modelNameControl.value = 'llama3.2:latest'; modelNameControl.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations[0].modelName === 'llama3.2:latest', '本地模型下拉选择没有写入当前会话');
  backendType.value = 'builtin'; backendType.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations[0].backend === 'builtin' && modelNameControl.hidden, '切回内置知识库后模型列表没有隐藏');
  check($('assistant-doc-content').textContent.includes('sampling.fs'), '默认参数清单没有渲染为完整文档');
  $('assistant-doc-search').value = '设计'; $('assistant-doc-search').dispatchEvent(new window.Event('input'));
  check($('assistant-doc-list').querySelectorAll('button').length === 1, '文档搜索没有按标题和摘要过滤');
  $('assistant-doc-list').querySelector('button').click();
  check($('assistant-doc-content').textContent.includes('平台模块说明'), '选择本地文档后没有渲染完整正文');
  $('assistant-doc-search').value = ''; $('assistant-doc-search').dispatchEvent(new window.Event('input'));
  check($('assistant-doc-list').querySelectorAll('button').length === 2, '清除搜索后文档目录未恢复');
  check(style.includes('.assistant-panel{position:fixed;inset:0 0 0 auto;'), '助手 CSS 未定位到当前页面固定侧栏');
  check(html.includes('id="assistant-shell"') && style.includes('.assistant-shell{position:relative;display:flex;'), '助手缺少外层可滚动面板');
  check(style.includes('overflow-y:auto;overscroll-behavior-y:contain;scrollbar-width:auto;scrollbar-color:#3d527a #111827'), '受限视口时外层滚动条没有启用或对比度不足');
  check(style.includes('.assistant-shell::-webkit-scrollbar{width:10px}'), 'WebKit 浏览器外层滚动条宽度样式缺失');
  check(html.includes('role="region" aria-label="智能问答助手内容，可滚动浏览全部界面" tabindex="0"'), '外层滚动区域缺少键盘可达的无障碍标记');
  check(style.includes('.assistant-shell.settings-open{overflow-y:hidden}'), '设置覆盖层打开时应锁定被覆盖的外层滚动');
  check(style.includes('.assistant-workspace{display:grid;grid-template-columns:260px minmax(0,1fr);flex:1 0 420px;min-height:420px;gap:12px;overflow:visible}'), '短视口下助手主布局会被压缩或裁切');
  check(style.includes('.assistant-workspace{position:relative;display:block;flex-basis:480px;min-height:480px}'), '窄屏布局没有为外层滚动条保留完整高度');
  check(style.includes('.assistant-workspace{flex-basis:540px;min-height:540px}'), '极窄屏布局没有为换行后的控件保留高度');
  check(style.includes('.assistant-workspace{display:grid;grid-template-columns:260px minmax(0,1fr)'), '双栏会话 / 问答布局缺失');
  check(style.includes('.assistant-session-toggle{display:inline-flex;flex:0 0 auto;align-items:center;justify-content:center;gap:4px;padding:6px 8px;font-size:11px;white-space:nowrap}'), '桌面端会话栏切换按钮必须可见且不被挤压');
  check(style.includes('.assistant-panel.sessions-collapsed .assistant-session-pane{display:none}') && style.includes('.assistant-panel.sessions-collapsed .assistant-workspace{grid-template-columns:minmax(0,1fr)}'), '会话栏收起时左栏未隐藏或问答区未占满工作区');
  check(style.includes('@media(max-width:680px)') && style.includes('.assistant-session-pane{position:absolute;inset:0 auto 0 0;'), '窄屏会话栏必须保留覆盖式抽屉布局');
  check(style.includes('.assistant-session-title{display:block;width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'), '长会话标题省略样式缺失');
  const cssRule = selector => { const start = style.indexOf(selector + '{'); return start < 0 ? '' : style.slice(start, style.indexOf('}', start)); };
  check(cssRule('.assistant-launcher').includes('cursor:grab') && cssRule('.assistant-launcher').includes('touch-action:none')
    && cssRule('.assistant-launcher').includes('user-select:none'), '悬浮球拖动的鼠标 / 触屏样式缺失');
  check(style.includes('.assistant-launcher.is-dragging{cursor:grabbing}')
    && html.includes('title="拖动可移动位置，点击打开智能问答助手"'), '悬浮球拖动状态或提示缺失');
  check(cssRule('.assistant-model-controls').includes('display:flex') && cssRule('.assistant-model-controls').includes('align-items:center')
    && cssRule('.assistant-model-controls').includes('flex-wrap:wrap'), '底部后端 / 模型 / 发送控制组未对齐');
  check(style.includes('@media(max-width:420px){\n  .assistant-workspace{flex-basis:540px;min-height:540px}')
    && style.includes('.assistant-model-controls{flex:0 1 auto;justify-content:flex-end;gap:4px}'), '极窄屏附件 / 模型 / 发送区没有自适应布局');
  const messageScrollCss = cssRule('.assistant-messages');
  check(messageScrollCss.includes('overflow-y:auto') && messageScrollCss.includes('scroll-behavior:auto') && !messageScrollCss.includes('scroll-behavior:smooth'), '消息区必须有独立纵向滚轮且不能以平滑自动滚动抢占操作');
  check(cssRule('.assistant-conversation-list').includes('overflow-y:auto'), '会话列表必须可纵向滚动');
  check(cssRule('.assistant-settings[open]').includes('position:absolute') && cssRule('.assistant-settings[open]').includes('overflow:hidden'), '设置覆盖层应裁剪内容并将滚动交给内部独立区域');
  check(cssRule('.assistant-settings-scroll').includes('position:absolute') && cssRule('.assistant-settings-scroll').includes('inset:0') && cssRule('.assistant-settings-scroll').includes('overflow-y:scroll') && cssRule('.assistant-settings-scroll').includes('scrollbar-width:auto') && cssRule('.assistant-settings-scroll').includes('scrollbar-color:#7898c5 #172338'), '设置独立滚动区缺少明确尺寸或高对比强制滚动条');
  check(style.includes('.assistant-settings-scroll:focus-visible{outline:2px solid #4e8de8'), '键盘聚焦设置滚动区时没有焦点指示');
  check(style.includes('.assistant-settings-scroll::-webkit-scrollbar{width:14px}') && style.includes('.assistant-settings-scroll::-webkit-scrollbar-track{background:#172338'), '设置滚动条的 WebKit 轨道 / 尺寸样式缺失');
  check(cssRule('.assistant-settings-header').includes('position:sticky') && cssRule('.assistant-settings-header').includes('top:0'), '设置滚动时标题 / 关闭按钮应保持可见');
  check(html.includes('id="assistant-settings-scroll" class="assistant-settings-scroll" role="region" aria-label="配置与附加知识库，可滚动浏览全部设置" tabindex="0"'), '设置独立滚动区域缺少键盘可达标记');
  check(html.indexOf('id="assistant-settings-scroll"') < html.indexOf('class="assistant-settings-body"') && html.indexOf('class="assistant-settings-body"') < html.indexOf('id="assistant-doc-pane"'), '配置和完整本地文档没有放进实际设置滚动区域');
  check($('assistant-settings-scroll').contains(window.document.querySelector('.assistant-settings-body')) && $('assistant-settings-scroll').contains($('assistant-doc-pane')) && $('assistant-settings-scroll').contains($('assistant-admin-token')) && $('assistant-settings-scroll').contains($('assistant-knowledge-list')), 'HTML 解析后的真实 DOM 中，配置 / 文档 / 附加知识没有统一位于独立滚动区内');
  check(html.includes('<aside id="assistant-panel"') && !html.includes('<dialog id="assistant-dialog"'), '助手必须使用同页侧栏而不是旧 dialog');

  const panel = $('assistant-panel'), launcher = $('assistant-launcher');
  Object.defineProperty(launcher, 'offsetWidth', { configurable: true, value: 120 });
  Object.defineProperty(launcher, 'offsetHeight', { configurable: true, value: 40 });
  launcher.getBoundingClientRect = () => {
    const left = Number.parseFloat(launcher.style.left), top = Number.parseFloat(launcher.style.top);
    const x = Number.isFinite(left) ? left : window.innerWidth - 22 - 120;
    const y = Number.isFinite(top) ? top : window.innerHeight - 82 - 40;
    return { x, y, left: x, top: y, right: x + 120, bottom: y + 40, width: 120, height: 40 };
  };
  const pointer = (type, x, y) => {
    const event = new window.MouseEvent(type, { bubbles: true, cancelable: true, button: 0, clientX: x, clientY: y });
    Object.defineProperty(event, 'pointerId', { configurable: true, value: 7 });
    return event;
  };
  launcher.dispatchEvent(pointer('pointerdown', 900, 666));
  window.document.dispatchEvent(pointer('pointermove', 450, 366));
  window.document.dispatchEvent(pointer('pointerup', 450, 366));
  check(launcher.style.left === '432px' && launcher.style.top === '346px'
    && launcher.style.right === 'auto' && launcher.style.bottom === 'auto', '悬浮球拖动后未跟随指针定位');
  launcher.click();
  check(panel.hidden, '拖动悬浮球时误触打开了助手');
  await new Promise(resolve => window.setTimeout(resolve, 1));
  launcher.dispatchEvent(pointer('pointerdown', 452, 366));
  window.document.dispatchEvent(pointer('pointermove', 2000, 2000));
  window.document.dispatchEvent(pointer('pointerup', 2000, 2000));
  check(launcher.style.left === '904px' && launcher.style.top === '728px', '悬浮球拖动超出当前视口边界');
  await new Promise(resolve => window.setTimeout(resolve, 1));
  launcher.click();
  check(!panel.hidden && panel.getAttribute('aria-hidden') === 'false', '点击入口没有打开固定侧栏');
  check(launcher.hidden && launcher.getAttribute('aria-expanded') === 'true', '助手窗口打开时悬浮球应隐藏且展开状态同步');
  const sessionToggle = $('assistant-session-toggle');
  check(!panel.classList.contains('sessions-collapsed') && sessionToggle.getAttribute('aria-expanded') === 'true', '桌面端打开助手时应默认显示会话管理栏');
  sessionToggle.click();
  check(panel.classList.contains('sessions-collapsed') && sessionToggle.getAttribute('aria-expanded') === 'false', '桌面端按钮未收起会话栏或 aria-expanded 未同步');
  check(sessionToggle.getAttribute('aria-label') === '展开会话管理面板' && sessionToggle.title === '展开会话管理面板' && sessionToggle.textContent.includes('显示会话'), '桌面端收起后按钮提示 / 可访问名称未更新');
  sessionToggle.click();
  check(!panel.classList.contains('sessions-collapsed') && sessionToggle.getAttribute('aria-expanded') === 'true', '桌面端会话栏无法从收起状态恢复');
  window.assistantSetBusy(true);
  check(!$('assistant-thinking').hidden, '请求忙碌时没有显示思考状态');
  window.assistantSetBusy(false);
  check($('assistant-thinking').hidden, '请求结束后思考状态没有隐藏');
  check(window.assistantReadableRequestError(new Error('模型请求超时')).includes('超时设置'), '超时错误没有提供模型 / 超时设置提示');
  $('assistant-settings-open').click();
  check($('assistant-settings').open && $('assistant-settings-open').getAttribute('aria-expanded') === 'true', '配置与附加知识库入口未打开设置区');
  $('assistant-bundled-docs').open = true;
  check($('assistant-doc-pane').textContent.includes('本地文档与参数'), '完整本地文档浏览区未整合进设置 / 知识库区域');
  $('assistant-settings-close').click();
  check(!$('assistant-settings').open, '设置区关闭按钮无效');
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: 390 });
  window.dispatchEvent(new window.Event('resize'));
  check(launcher.style.left === '904px', '助手打开时不应读取隐藏悬浮球的零尺寸');
  window.assistantTogglePanel(false);
  check(launcher.style.left === '270px', '关闭助手后应按新视口尺寸将悬浮球夹回可见范围');
  window.assistantTogglePanel(true);
  check(panel.classList.contains('sessions-collapsed') && sessionToggle.getAttribute('aria-expanded') === 'false', '窄屏打开助手时会话管理栏应默认折叠');
  check(sessionToggle.getAttribute('aria-label') === '展开会话管理面板' && sessionToggle.title === '展开会话管理面板' && sessionToggle.textContent.includes('显示会话'), '窄屏初始折叠状态的按钮提示不正确');
  sessionToggle.click();
  check(!panel.classList.contains('sessions-collapsed') && sessionToggle.getAttribute('aria-expanded') === 'true', '窄屏会话栏无法展开');
  sessionToggle.click();
  check(panel.classList.contains('sessions-collapsed') && sessionToggle.getAttribute('aria-expanded') === 'false', '窄屏会话栏无法再次折叠');
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1024 });
  $('assistant-close').click();
  check(panel.hidden && panel.getAttribute('aria-hidden') === 'true', '关闭按钮没有收起侧栏');
  check(!launcher.hidden && launcher.getAttribute('aria-expanded') === 'false', '关闭助手窗口后悬浮球应恢复显示');
  launcher.click();
  check(launcher.hidden && !panel.hidden, '通过悬浮球再次打开助手时，悬浮球没有隐藏');
  window.document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  check(panel.hidden && !launcher.hidden && window.document.activeElement === launcher, 'Escape 关闭助手后悬浮球未显示 / 焦点未返回');
  window.S.view = 'nilm'; window.assistantSyncLauncher();
  check($('assistant-launcher').hidden, 'visible_views 未控制入口显隐');
  window.S.view = 'overview'; window.assistantSyncLauncher();

  // 默认本地文档通道不调用模型，返回平台文档摘录和引用。
  $('assistant-prompt').value = '设备画像匹配有哪些注意事项？';
  await window.assistantSubmit();
  let messages = $('assistant-messages');
  check(lastChatPayload && lastChatPayload.model_type === 'builtin', '首次聊天没有使用内置文档后端');
  check(!$('assistant-title').hidden && $('assistant-title').textContent === window.__assistantState.conversations[0].title,
    '助手形成有效回答后，右侧标题未显示当前会话名');
  check(messages.textContent.includes('内置知识库｜本地文档检索') && messages.textContent.includes('pre_cycles'), '内置本地文档摘录未渲染');
  check(messages.textContent.includes('引用：平台参数清单'), '平台参数清单引用未显示');

  // 在设置中把默认后端改为 local，再新建会话；原内置会话不应被改写。
  config = { ...config, default_model_type: 'local' }; await window.assistantLoadConfig();
  check(window.__assistantState.conversations[0].backend === 'builtin', '保存默认后端不应更改已有会话的模型通道');
  $('assistant-new').click();
  check(window.__assistantState.conversations.length === 2, '按设置默认后端新建会话失败');
  check($('assistant-title').hidden && !$('assistant-title').textContent, '切换后新建的空会话不应显示右侧标题');
  check(window.__assistantState.conversations[0].backend === 'local', '新会话未采用所选模型');
  check(window.__assistantState.conversations[1].messages.length === 2, '内置文档会话没有保留');
  const modelName = $('assistant-model-name');
  check(!modelName.hidden && modelName.getAttribute('aria-label') === '选择具体模型', 'local 后端应显示无可见标题且可访问的具体模型下拉');
  check(Array.from(modelName.options).some(option => option.value === 'qwen2.5:7b'), '具体模型下拉没有包含服务发现的本地模型');
  check(Array.from(modelName.options).some(option => option.value === 'llama3.2:latest'), '具体模型下拉没有包含本地发现模型');
  modelName.value = 'llama3.2:latest'; modelName.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations[0].modelName === 'llama3.2:latest', '本地模型名称选择没有写入当前会话');
  $('assistant-prompt').value = '如何查看画像参数？';
  await window.assistantSubmit();
  messages = $('assistant-messages');
  check(messages.querySelectorAll('.assistant-message').length === 2, '本地模型会话没有显示用户与助手消息');
  check(lastChatPayload.model_name === 'llama3.2:latest', '本地聊天请求没有携带所选模型名称');
  check(!$('assistant-title').hidden && $('assistant-title').textContent === window.__assistantState.conversations[0].title,
    '本地模型回答完成后右侧标题未与当前会话同步');
  check(!!messages.querySelector('h2') && !!messages.querySelector('strong') && !!messages.querySelector('pre code'), 'Markdown 标题/强调/代码块未渲染');
  check(!messages.querySelector('img, a[href^="javascript:"]'), '不可信 Markdown 被解释成活动 HTML');
  check(messages.textContent.includes('<img src=x onerror=alert(1)>'), '原始 HTML 应作为普通文本展示');
  check(messages.textContent.includes('引用：guide.md'), '缺少知识库引用标记');

  // 流式消息更新与请求结束重绘不能把用户从历史阅读位置强行拉回底部。
  window.assistantTogglePanel(true);
  const activeReply = window.__assistantState.conversations[0].messages[1];
  const messageScroll = mockScrollArea(messages, () => 1100 + activeReply.content.length, 300, 140);
  const headerWheel = new window.WheelEvent('wheel', { deltaY: 80, bubbles: true, cancelable: true });
  check(!window.document.querySelector('.assistant-chat-header').dispatchEvent(headerWheel) && messageScroll.top === 220, '在聊天标题 / 空白区使用滚轮没有转发到消息区');
  messageScroll.top = 140;
  activeReply.content += '\\n用户正在查看较早内容'; window.assistantRefreshMessage(activeReply);
  check(messageScroll.top === 140, '流式增量更新把用户滚动位置抢回底部');
  window.assistantRenderConversation({ preserveScroll: true });
  check(messageScroll.top === 140, '请求结束重绘把用户滚动位置抢回底部');
  messageScroll.top = messages.scrollHeight - messages.clientHeight;
  activeReply.content += '\\n继续生成的尾部内容'; window.assistantRefreshMessage(activeReply);
  check(messageScroll.top === messages.scrollHeight - messages.clientHeight, '用户停留在底部时，流式更新没有继续跟随最新内容');
  messageScroll.top = 180; window.assistantRenderConversation({ preserveScroll: true });
  check(messageScroll.top === 180, '最终重绘未保留非底部阅读位置');
  const shellScroll = mockScrollArea($('assistant-shell'), 1200, 500, 100);
  messageScroll.top = messages.scrollHeight - messages.clientHeight;
  const outerAfterMessages = new window.WheelEvent('wheel', { deltaY: 80, bubbles: true, cancelable: true });
  check(!messages.dispatchEvent(outerAfterMessages) && shellScroll.top === 180, '消息区滚动到底后没有把滚轮交给助手外层面板');
  modelName.value = 'qwen2.5:7b'; modelName.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations.length === 3, '切换具体本地模型未创建独立会话');
  check(window.__assistantState.conversations[0].modelName === 'qwen2.5:7b' && !window.__assistantState.conversations[0].messages.length, '新模型会话未使用所选模型或不为空');
  check($('assistant-title').hidden && !$('assistant-title').textContent, '切换具体模型后空会话显示了右侧标题');
  check(window.__assistantState.conversations[1].modelName === 'llama3.2:latest' && window.__assistantState.conversations[1].messages.length === 2, '切换具体模型破坏或更改了旧会话');
  const qwenConversationId = window.__assistantState.conversations[0].id;
  window.assistantSelectConversation(window.__assistantState.conversations[1].id);
  check(!$('assistant-title').hidden && $('assistant-title').textContent === window.__assistantState.conversations[1].title,
    '切换到已有问答的会话后，右侧标题没有更新');
  window.assistantSelectConversation(qwenConversationId);
  check($('assistant-title').hidden, '切回空会话后右侧标题未清空');
  $('assistant-prompt').value = '使用另一个模型继续提问'; await window.assistantSubmit();
  check(lastChatPayload.model_name === 'qwen2.5:7b', '新模型会话请求没有路由到所选模型');
  check(!$('assistant-title').hidden && $('assistant-title').textContent === window.__assistantState.conversations[0].title,
    '新会话回答完成后，右侧标题未显示当前会话名');
  const sessionScroll = mockScrollArea($('assistant-conversation-list'), 900, 300, 40);
  const sessionWheel = new window.WheelEvent('wheel', { deltaY: 60, bubbles: true, cancelable: true });
  check(!window.document.querySelector('.assistant-session-heading').dispatchEvent(sessionWheel) && sessionScroll.top === 100, '在会话标题 / 空白区使用滚轮没有转发到会话列表');

  $('assistant-settings-open').click();
  check($('assistant-shell').classList.contains('settings-open'), '设置面板打开后没有锁定外层滚动位置');
  $('assistant-bundled-docs').open = true;
  const settingsScroll = mockScrollArea($('assistant-settings-scroll'), 1000, 300, 100);
  mockScrollArea($('assistant-doc-content'), 600, 200, 300);
  const innerCanScrollWheel = new window.WheelEvent('wheel', { deltaY: 80, bubbles: true, cancelable: true });
  check($('assistant-doc-content').dispatchEvent(innerCanScrollWheel) && settingsScroll.top === 100, '文档正文仍可滚动时，滚轮应优先留在内层文档');
  mockScrollArea($('assistant-doc-content'), 600, 200, 400);
  const settingsWheel = new window.WheelEvent('wheel', { deltaY: 80, bubbles: true, cancelable: true });
  check(!$('assistant-doc-content').dispatchEvent(settingsWheel) && settingsScroll.top === 180, '展开本地帮助文档后，文档内层到边界时滚轮没有继续滚动独立设置区');
  mockScrollArea($('assistant-doc-content'), 200, 200, 0);
  const noInnerOverflowWheel = new window.WheelEvent('wheel', { deltaY: 80, bubbles: true, cancelable: true });
  check(!$('assistant-doc-content').dispatchEvent(noInnerOverflowWheel) && settingsScroll.top === 260, '内层文档没有溢出时，滚轮没有滚动独立设置区');
  settingsScroll.top = 700; shellScroll.top = 100;
  const outerAfterSettings = new window.WheelEvent('wheel', { deltaY: 80, bubbles: true, cancelable: true });
  check(!$('assistant-doc-content').dispatchEvent(outerAfterSettings) && shellScroll.top === 100, '设置独立滚动区到边界后不应把被覆盖的助手面板移出视口');
  $('assistant-settings-close').click();
  check(!$('assistant-settings').open && !$('assistant-shell').classList.contains('settings-open'), '设置区关闭按钮无效或外层滚动锁未解除');

  // 在设置中更改默认后端并新建会话；具体模型列表包含默认云端模型和命名档案。
  config = { ...config, default_model_type: 'cloud' }; await window.assistantLoadConfig();
  check(window.__assistantState.conversations[0].backend === 'local', '更改默认后端不应改写已有本地会话');
  $('assistant-new').click();
  check(window.__assistantState.conversations.length === 4, '按新设置默认后端创建会话失败');
  check(window.__assistantState.conversations[0].backend === 'cloud', '新会话未采用所选后端');
  check(window.__assistantState.conversations[1].backend === 'local' && window.__assistantState.conversations[1].modelName === 'qwen2.5:7b' && window.__assistantState.conversations[1].messages.length === 2, '本地模型会话没有保留');
  check(window.__assistantState.conversations[2].backend === 'local' && window.__assistantState.conversations[2].modelName === 'llama3.2:latest' && window.__assistantState.conversations[2].messages.length === 2, '旧本地模型会话没有保留');
  check(window.__assistantState.conversations[3].backend === 'builtin' && window.__assistantState.conversations[3].messages.length === 2, '内置文档会话没有保留');
  check(Array.from(modelName.options).some(option => option.value === '__default__' && option.textContent.includes('cloud-model')), '云端模型列表没有默认模型名称');
  check(Array.from(modelName.options).some(option => option.value === 'cloud-alt' && option.textContent.includes('alt-chat')), '云端模型列表没有命名档案');
  modelName.value = 'cloud-alt'; modelName.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations[0].cloudProfileId === 'cloud-alt', '云端档案选择没有写入当前会话');

  // 配置保存必须带管理员口令，且密钥输入只作为 POST/PUT 参数，不回填页面。
  $('assistant-admin-token').value = 'admin'; $('assistant-admin-token').dispatchEvent(new window.Event('input'));
  const refreshModelsButton = $('assistant-refresh-local-models');
  $('assistant-cloud-profile-add').click();
  const profileCards = Array.from($('assistant-cloud-profiles').querySelectorAll('.assistant-cloud-profile'));
  const addedProfileCard = profileCards[profileCards.length - 1];
  const setProfileField = (fieldName, value) => {
    const input = Array.from(addedProfileCard.querySelectorAll('[data-cloud-profile-field]'))
      .find(item => item.dataset.cloudProfileField === fieldName);
    input.value = value; input.dispatchEvent(new window.Event('input', { bubbles: true }));
  };
  const addedProfileSecret = 'temporary-named-cloud-secret';
  setProfileField('name', 'Test provider');
  setProfileField('base_url', 'https://api.test-provider.example/v1');
  setProfileField('model', 'test-model-v2');
  setProfileField('api_key', addedProfileSecret);
  await window.assistantSaveConfig();
  check(!Object.prototype.hasOwnProperty.call(lastConfigPayload, 'local_model'), '本地模型名称不应再作为管理员设置提交');
  check(lastConfigPayload.cloud_api_profiles.length === 2, '动态添加的云端档案没有一起保存');
  const addedProfile = lastConfigPayload.cloud_api_profiles.find(profile => profile.name === 'Test provider');
  check(!!addedProfile && addedProfile.model === 'test-model-v2' && addedProfile.base_url === 'https://api.test-provider.example/v1', '动态档案的名称 / endpoint / 模型 ID 保存错误');
  check(lastConfigPayload.cloud_api_profile_secrets[addedProfile.id] === addedProfileSecret, '动态云端 API Key 没有单独提交');
  check(!JSON.stringify(lastConfigPayload.cloud_api_profiles).includes(addedProfileSecret), '云端 API Key 错误地放进档案元数据');
  check(!JSON.stringify(config).includes(addedProfileSecret), '配置返回值回显了云端 API Key');
  const savedProfileCard = Array.from($('assistant-cloud-profiles').querySelectorAll('.assistant-cloud-profile'))
    .find(card => card.textContent.includes('Test provider'));
  check(!!savedProfileCard && !savedProfileCard.querySelector('[data-cloud-profile-field="api_key"]').value, '保存后动态档案的 API Key 输入框未清空');
  await window.assistantRefreshLocalModels();
  check(lastLocalModelRefresh && lastLocalModelRefresh.headers['X-Assistant-Admin-Token'] === 'admin', '刷新模型列表没有携带管理员口令');
  check(lastLocalModelRefresh.body === null && lastConfigPayload.local_base_url === config.local_base_url,
    '刷新请求应使用已保存的本地服务地址，而不能提交另一条临时 URL');
  check(window.__assistantState.localModels.join(',') === 'refreshed-local-model', '刷新后的候选没有更新');
  check(!Object.prototype.hasOwnProperty.call(config, 'local_model'), '模型发现结果被写回管理员模型名配置');
  nextLocalModelRefresh = { status: 'empty', models: [] };
  await window.assistantRefreshLocalModels();
  check(window.__assistantState.localModels.length === 0, '空模型响应后本地候选没有清空');
  check($('assistant-local-models-status').textContent.includes('未返回模型'), '空模型发现状态未显示');
  nextLocalModelRefresh = { fail: true };
  await window.assistantRefreshLocalModels();
  check($('assistant-local-models-status').textContent.includes('本地服务暂不可用'), '刷新失败状态未显示');
  nextLocalModelRefresh = { status: 'ready', models: ['refreshed-local-model'] };
  $('assistant-enabled').checked = true;
  $('assistant-cloud-key').value = 'temporary-cloud-secret';
  await window.assistantSaveConfig();
  check(!!lastConfigPayload && lastConfigPayload.cloud_api_key === 'temporary-cloud-secret', '配置保存载荷缺密钥');
  check(lastConfigPayload.enabled_tools.includes('start_current_source')
    && lastConfigPayload.enabled_tools.includes('list_recordings')
    && !lastConfigPayload.enabled_tools.includes('engine.start'),
  '全局 allow-list 保存值必须是工具 ID，不能误写成操作员 scope');
  check(!Object.prototype.hasOwnProperty.call(lastConfigPayload, 'local_model'), '模型名称错误地保存在管理员配置中');
  check(!Object.prototype.hasOwnProperty.call(lastConfigPayload, 'sensitive_terms'), '普通配置保存不应覆盖未读取的敏感词');
  check(!$('assistant-cloud-key').value, '保存后 API Key 输入框未清空');
  check(!$('assistant-config-message').classList.contains('is-error'), '配置保存失败：' + $('assistant-config-message').textContent);

  await window.assistantLoadSensitiveTerms();
  check($('assistant-sensitive-terms').value === 'PROJECT-ALPHA', '管理员读取的拦截词未填入页面');
  $('assistant-clear-sensitive-terms').checked = true;
  $('assistant-clear-sensitive-terms').dispatchEvent(new window.Event('change'));
  await window.assistantSaveConfig();
  check(Array.isArray(lastConfigPayload.sensitive_terms) && lastConfigPayload.sensitive_terms.length === 0, '清空拦截词未生成明确的空列表');

  const files = $('assistant-doc-files');
  Object.defineProperty(files, 'files', { configurable: true, value: [{ name: 'assistant-guide.md', size: 18, text: async () => '画像参数与窗口配置说明' }] });
  await window.assistantImportKnowledge();
  check(lastImportedDocuments && lastImportedDocuments[0].content === '画像参数与窗口配置说明', '本地知识库文件没有读取并提交 UTF-8 文本');
  check($('assistant-knowledge-list').textContent.includes('assistant-guide.md'), '导入后的知识库列表没有更新');

  // 将设置中的默认后端改为 local 并新建会话；受控操作只显示预览，确认仍需令牌与二次码。
  $('assistant-operator-token').value = 'memory-only-operator-token';
  $('assistant-operator-token').dispatchEvent(new window.Event('input'));
  config = { ...config, default_model_type: 'local' }; await window.assistantLoadConfig();
  $('assistant-new').click();
  await new Promise(resolve => setTimeout(resolve, 1));
  check(lastIdentityModel === 'local' && lastIdentityToken === 'memory-only-operator-token', '新会话切换到本地后端后没有用新路由重新验证操作员令牌');
  check(window.__assistantState.conversations[0].backend === 'local', '设置默认本地后端后新会话没有切换到 local');
  emitProposal = true;
  $('assistant-prompt').value = '把当前侧接线模式切换到 3p4w';
  await window.assistantSubmit();
  emitProposal = false;
  check(lastChatPayload.model_type === 'local', '操作提案请求没有走所选本地模型');
  check(lastChatPayload.prompt.includes('接线模式'), '操作提案请求正文丢失');
  let proposalCard = $('assistant-messages').querySelector('.assistant-proposal-pending');
  check(!!proposalCard && proposalCard.textContent.includes('影响：'), 'SSE proposal 预览卡或影响说明未渲染');
  check(proposalCard.textContent.includes('123456'), '高风险操作二次确认码未显示');
  const codeInput = proposalCard.querySelector('input'); codeInput.value = '123456';
  proposalCard.querySelector('button.primary').click();
  for (let i = 0; i < 50 && !$('assistant-messages').querySelector('.assistant-proposal-success'); i++) await new Promise(resolve => setTimeout(resolve, 10));
  proposalCard = $('assistant-messages').querySelector('.assistant-proposal-success');
  check(lastConfirmPayload && lastConfirmPayload.proposal_id === 'proposal-jsdom-1', '确认接口没有携带 proposal id');
  check(lastConfirmPayload.confirmation_code === '123456', '确认接口没有携带二次确认码');
  check(lastConfirmHeaders['X-Assistant-Operator-Token'] === 'memory-only-operator-token', '确认接口没有带操作员令牌');
  check(!!proposalCard && proposalCard.textContent.includes('接线模式已切换为 3p4w'), '确认执行结果未更新到提案卡');

  // 导出文件按生成它的一侧下载（补-A5）：提案可以是另一侧的，下载地址不能按页面当前所在的一侧拼。
  if (!window.URL.createObjectURL) window.URL.createObjectURL = () => 'blob:jsdom-export';
  if (!window.URL.revokeObjectURL) window.URL.revokeObjectURL = () => {};
  window.HTMLAnchorElement.prototype.click = function () {};
  const exportResult = side => ({ message: '已生成', filename: 'x.csv', download_url: '/api/assistant/tools/export/EXPORT-1', side });
  await window.assistantDownloadExport(exportResult('branch'));
  check(exportDownloadUrls.pop() === '/api/branch/assistant/tools/export/EXPORT-1', '总线侧页面下载分路侧的导出文件时，地址没有带分路侧前缀');
  window.S.side = 'branch';
  await window.assistantDownloadExport(exportResult('bus'));
  check(exportDownloadUrls.pop() === '/api/assistant/tools/export/EXPORT-1', '分路侧页面下载总线侧的导出文件时，地址被加上了分路侧前缀');
  await window.assistantDownloadExport(exportResult('branch'));
  check(exportDownloadUrls.pop() === '/api/branch/assistant/tools/export/EXPORT-1', '分路侧页面下载本侧导出文件的地址不对');
  await window.assistantDownloadExport(exportResult(undefined));
  check(exportDownloadUrls.pop() === '/api/branch/assistant/tools/export/EXPORT-1', '结果里没有 side 时应退回页面当前所在的一侧');
  window.S.side = 'bus';
  await window.assistantDownloadExport(exportResult('bus'));
  check(exportDownloadUrls.pop() === '/api/assistant/tools/export/EXPORT-1' && !$('assistant-error').textContent, '总线侧页面下载本侧导出文件的地址不对');

  // 服务端拒绝模型的工具调用时返回澄清：回答带“待澄清”标记，不出现操作预览卡；普通回答不带标记。
  check(!$('assistant-messages').querySelector('.assistant-clarification-note'), '普通回答或操作预览被误标为澄清');
  const pendingCardsBefore = $('assistant-messages').querySelectorAll('.assistant-proposal').length;
  emitClarification = true;
  $('assistant-prompt').value = '切换接线模式到3p4w';
  await window.assistantSubmit();
  emitClarification = false;
  let clarified = Array.from($('assistant-messages').querySelectorAll('.assistant-message.assistant')).pop();
  let clarificationNote = clarified.querySelector('.assistant-clarification-note');
  check(!!clarificationNote && clarificationNote.textContent.includes('未创建操作预览'), 'SSE clarification 帧没有显示澄清标记');
  check(clarified.classList.contains('assistant-message-clarification'), '澄清回答没有加上专用样式类');
  check(clarified.querySelector('.assistant-markdown').textContent.includes('请确认希望执行的单一动作'), '澄清文字没有显示在回答正文');
  check(clarificationNote.compareDocumentPosition(clarified.querySelector('.assistant-markdown')) & window.Node.DOCUMENT_POSITION_FOLLOWING, '澄清标记应显示在回答正文之前');
  check(!clarified.querySelector('.assistant-proposal'), '澄清回答不应带操作预览卡');
  check($('assistant-messages').querySelectorAll('.assistant-proposal').length === pendingCardsBefore, '澄清回答新增了操作预览卡');
  check($('assistant-messages').querySelectorAll('.assistant-clarification-note').length === 1, '澄清标记数量不对');
  const clarifiedMessage = window.__assistantState.conversations[0].messages[window.__assistantState.conversations[0].messages.length - 1];
  check(clarifiedMessage.clarification === true && !clarifiedMessage.proposal, '澄清状态没有记在该条回答上');
  // 整个会话重画（例如切换侧栏后）标记仍在；下一条普通回答不带标记。
  $('assistant-prompt').value = '解释一下画像匹配';
  await window.assistantSubmit();
  const assistantBubbles = Array.from($('assistant-messages').querySelectorAll('.assistant-message.assistant'));
  check(!assistantBubbles[assistantBubbles.length - 1].querySelector('.assistant-clarification-note'), '普通回答被误标为澄清');
  check(!!assistantBubbles[assistantBubbles.length - 2].querySelector('.assistant-clarification-note'), '会话重画后澄清标记丢失');
  // 非流式 JSON 响应用 clarification=true 表示同一状态。
  const nativeFetchForClarification = window.fetch;
  window.fetch = async (url, options = {}) => (String(url).endsWith('/api/assistant/chat')
    ? jsonResponse({ ok: true, answer: CLARIFICATION_TEXT, sources: [], proposal: null, clarification: true })
    : nativeFetchForClarification(url, options));
  $('assistant-prompt').value = '切换接线模式到3p4w';
  await window.assistantSubmit();
  window.fetch = nativeFetchForClarification;
  clarified = Array.from($('assistant-messages').querySelectorAll('.assistant-message.assistant')).pop();
  check(!!clarified.querySelector('.assistant-clarification-note') && !clarified.querySelector('.assistant-proposal'), 'JSON clarification=true 没有显示澄清标记');
  check($('assistant-messages').querySelectorAll('.assistant-clarification-note').length === 2, 'JSON 澄清后标记数量不对');

  // 图片仅保存在页面内存；文件选择 / 粘贴 / 拖放共用同一条受限图片管线。
  const png = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x01]);
  const screenshot = new window.File([png], 'waveform.png', { type: 'image/png' });
  const pasteEvent = new window.Event('paste', { bubbles: true, cancelable: true });
  Object.defineProperty(pasteEvent, 'clipboardData', { value: { items: [{ kind: 'file', type: 'image/png', getAsFile: () => screenshot }] } });
  $('assistant-prompt').dispatchEvent(pasteEvent);
  for (let i = 0; i < 50 && window.__assistantState.pendingImages.length < 1; i++) await new Promise(resolve => setTimeout(resolve, 5));
  check(window.__assistantState.pendingImages.length === 1 && $('assistant-image-previews').querySelector('img'), '粘贴截图后没有生成页面内存预览');
  const jpeg = new window.File([new Uint8Array([0xff, 0xd8, 0xff, 0x00])], 'waveform-drop.jpg', { type: 'image/jpeg' });
  const dropEvent = new window.Event('drop', { bubbles: true, cancelable: true });
  Object.defineProperty(dropEvent, 'dataTransfer', { value: { types: ['Files'], files: [jpeg] } });
  $('assistant-chat-pane').dispatchEvent(dropEvent);
  for (let i = 0; i < 50 && window.__assistantState.pendingImages.length < 2; i++) await new Promise(resolve => setTimeout(resolve, 5));
  check(window.__assistantState.pendingImages.length === 2, '拖放截图没有加入待发附件');
  $('assistant-prompt').value = '请分析波形的启动暂态';
  await window.assistantSubmit();
  check(lastChatPayload.model_type === 'local' && lastChatPayload.images.length === 2 && lastChatPayload.images[0].mime_type === 'image/png' && lastChatPayload.images[1].mime_type === 'image/jpeg', '粘贴 / 拖放截图未随本地视觉模型请求发送');
  check($('assistant-messages').querySelectorAll('.assistant-message-images img').length === 2, '已发送截图没有显示在用户消息中');
  check(window.__assistantState.pendingImages.length === 0, '发送后待发截图没有从 composer 清除');

  config = { ...config, default_model_type: 'cloud' }; await window.assistantLoadConfig();
  $('assistant-new').click();
  check(window.__assistantState.conversations[0].backend === 'cloud' && !modelName.hidden, '默认云端后端的新会话没有显示云端模型选择器');
  check(Array.from(modelName.options).some(option => option.textContent.includes('Test provider') && option.textContent.includes('test-model-v2')), '保存后的动态云端档案没有进入问答模型选择器');
  modelName.value = addedProfile.id; modelName.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations[0].cloudProfileId === addedProfile.id, '动态云端档案切换没有生效');
  const cloudJpeg = new window.File([new Uint8Array([0xff, 0xd8, 0xff, 0x00])], 'waveform.jpg', { type: 'image/jpeg' });
  await window.assistantAddImageFiles([cloudJpeg]);
  $('assistant-prompt').value = '请分析截图中的电流变化';
  await window.assistantSubmit();
  check(lastChatPayload.model_type === 'cloud' && lastChatPayload.cloud_profile_id === addedProfile.id
    && lastChatPayload.images[0].mime_type === 'image/jpeg', '云端截图请求未携带所选云端档案或截图');
  check(confirmMessages.some(message => message.includes('截图内容不经过文本敏感词扫描')), '云端截图发送前没有二次确认 / 隐私提示');
  const namedCloudConversation = window.__assistantState.conversations[0];
  modelName.value = '__default__'; modelName.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations[0].backend === 'cloud'
    && window.__assistantState.conversations[0].cloudProfileId === '__default__'
    && !window.__assistantState.conversations[0].messages.length, '切换云端档案后没有建立默认模型独立会话');
  check(window.__assistantState.conversations[1].id === namedCloudConversation.id
    && window.__assistantState.conversations[1].cloudProfileId === addedProfile.id
    && window.__assistantState.conversations[1].messages.length === 2, '切换云端档案破坏或修改了旧会话');

  // 会话列表按当前顺序分最近 / 历史，支持搜索、重命名、右键菜单、删除和拖拽排序。
  for (let i = 0; i < 4; i++) window.assistantNewConversation('builtin');
  const conversationList = $('assistant-conversation-list');
  check(conversationList.querySelectorAll('.assistant-session-group-title').length === 2, '超过 5 条后未分为最近会话与历史会话');
  check(Array.from(conversationList.querySelectorAll('time')).every(time => time.textContent), '会话列表未显示更新时间');
  const renameTarget = conversationList.querySelector('.assistant-session-row');
  const renameId = renameTarget.dataset.conversationId;
  renameTarget.dispatchEvent(new window.MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX: 80, clientY: 90 }));
  check(!$('assistant-session-context-menu').hidden, '会话右键菜单未打开');
  nextPromptValue = '手动命名的会话标题'; $('assistant-rename-conversation').click();
  check(window.__assistantState.conversations.find(conv => conv.id === renameId).title === '手动命名的会话标题', '会话重命名未生效');
  check($('assistant-title').hidden, '尚无正式问答的空会话不应仅因重命名就显示右侧标题');
  $('assistant-prompt').value = '验证命名后的会话标题'; await window.assistantSubmit();
  check(!$('assistant-title').hidden && $('assistant-title').textContent === '手动命名的会话标题', '问答完成后右侧没有显示手动会话名');
  nextPromptValue = '问答完成后的手动标题'; window.assistantRenameConversation();
  check($('assistant-title').textContent === '问答完成后的手动标题', '重命名已有问答的会话后右侧标题未同步');
  window.assistantClearContext();
  check($('assistant-title').hidden && !$('assistant-title').textContent, '清空问答后右侧标题没有隐藏');
  $('assistant-session-search').value = '手动标题'; $('assistant-session-search').dispatchEvent(new window.Event('input'));
  check(conversationList.querySelectorAll('.assistant-session-row').length === 1, '会话标题搜索未过滤列表');
  $('assistant-session-search').value = ''; $('assistant-session-search').dispatchEvent(new window.Event('input'));
  const beforeDrag = window.__assistantState.conversations.map(conv => conv.id);
  const dragRows = conversationList.querySelectorAll('.assistant-session-row');
  const transfer = { value: '', effectAllowed: '', setData(_type, value) { this.value = value; }, getData() { return this.value; } };
  const dragStart = new window.Event('dragstart', { bubbles: true, cancelable: true }); Object.defineProperty(dragStart, 'dataTransfer', { value: transfer });
  dragRows[0].dispatchEvent(dragStart);
  const drop = new window.Event('drop', { bubbles: true, cancelable: true }); Object.defineProperty(drop, 'dataTransfer', { value: transfer });
  dragRows[2].dispatchEvent(drop);
  check(window.__assistantState.conversations[0].id !== beforeDrag[0], '拖拽排序未改变会话顺序');
  const deleteId = window.__assistantState.conversations[window.__assistantState.conversations.length - 1].id;
  window.assistantShowSessionContextMenu(deleteId, 20, 20); $('assistant-delete-conversation').click();
  check(!window.__assistantState.conversations.some(conv => conv.id === deleteId), '上下文菜单删除没有移除目标会话');

  config = { ...config, enabled: false };
  await window.assistantLoadConfig();
  check($('assistant-launcher').hidden, 'enabled=false 时问答入口仍然可见');
  check($('assistant-panel').hidden && $('assistant-panel').getAttribute('aria-hidden') === 'true'
    && $('assistant-launcher').getAttribute('aria-expanded') === 'false', '助手被禁用后仍保持打开或展开状态');

  console.log(`PASS ${checkCount} checks — draggable assistant launcher, launcher visibility, current-session titles, simplified bottom controls and attachment label, two-column sidebar, desktop/mobile collapsible sessions, session search/groups/time/rename/delete/drag, bundled docs, builtin retrieval, safe Markdown/XSS, citations, editable local-model discovery, admin config, image upload/preview/cloud confirmation, local import, operator-token proposal confirmation`);
  dom.window.close();
})().catch(error => {
  console.error('FAIL:', error && error.stack || error);
  dom.window.close();
  process.exitCode = 1;
});
