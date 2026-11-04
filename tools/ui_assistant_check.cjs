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
  local_base_url: 'http://127.0.0.1:11434/v1', local_model: 'qwen-local',
  cloud_base_url: 'https://api.example.test/v1', cloud_model: 'cloud-model',
  cloud_api_profiles: [{ id: 'cloud-alt', name: '备用云端', base_url: 'https://api.alt.example/v1', model: 'alt-chat', api_key_set: true }],
  timeout_s: 90, temperature: 0.2, max_tokens: 2048,
  rag_enabled: true, rag_top_k: 4, rag_similarity_threshold: 0.08,
  log_queries: false, sensitive_terms_configured: true, sensitive_terms_count: 1, visible_views: ['overview'],
  cloud_api_key_set: false, local_api_key_set: false, admin_configurable: true,
};
const views = [{ id: 'overview', label: '总览面板' }, { id: 'nilm', label: '负荷辨识事件' }];
const encoder = new TextEncoder();
const jsonResponse = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'content-type': 'application/json' },
});
let lastConfigPayload = null;
let lastChatPayload = null;
let lastConfirmPayload = null;
let lastConfirmHeaders = null;
let emitProposal = false;
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
    return jsonResponse({ ok: true, config, views });
  }
  if (url === '/api/assistant/local-models' && (!options.method || options.method === 'GET')) {
    return jsonResponse({ ok: true, status: 'ready', models: ['qwen2.5:7b', 'llama3.2:latest'], error: '', updated_at: 1 });
  }
  if (url === '/api/assistant/local-models/refresh' && options.method === 'POST') {
    if (options.headers['X-Assistant-Admin-Token'] !== 'admin') throw new Error('刷新本地模型列表时缺少管理员口令');
    lastLocalModelRefresh = { body: JSON.parse(options.body), headers: options.headers };
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
  if (url === '/api/assistant/tools/confirm' && options.method === 'POST') {
    lastConfirmPayload = JSON.parse(options.body); lastConfirmHeaders = options.headers;
    return jsonResponse({ ok: true, result: { message: '接线模式已切换为 3p4w', side: 'bus' } });
  }
  if (url === '/api/assistant/chat') {
    const payload = JSON.parse(options.body); lastChatPayload = payload;
    if (!payload.stream || !['builtin', 'local', 'cloud'].includes(payload.model_type)) throw new Error('聊天请求参数不符合预期');
    const frames = [
      { type: 'sources', sources: [{ name: payload.model_type === 'builtin' ? '平台参数清单' : 'guide.md', score: 0.91 }] },
      { type: 'delta', text: payload.model_type === 'builtin' ? '### 内置知识库｜本地文档检索\n\n平台参数清单摘录：`pre_cycles` 与 `window_cycles` 的代码默认值须与当前配置核对。' : '## 结论\n\n支持 **Markdown**、`代码`。\n\n```js\nalert(1)\n```\n\n<img src=x onerror=alert(1)>\n\n[坏链接](javascript:alert(1))' },
      ...(emitProposal ? [{ type: 'proposal', proposal: {
        id: 'proposal-jsdom-1', tool: 'set_wiring_mode', title: '切换当前侧接线模式',
        summary: '将当前侧接线模式切换为 3p4w', impact: '只改当前侧接线模式。',
        arguments: { wiring: '3p4w' }, side: 'bus', status: 'pending',
        requires_second_confirmation: true, confirmation_code: '123456', expires_at: Date.now() / 1000 + 300,
      } }] : []),
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
  check(!$('assistant-launcher').hidden, '总览页应显示入口');
  check($('assistant-model-type').value === 'builtin', '未配置模型时应默认选择内置文档通道');
  check($('assistant-privacy-note').textContent.includes('本地文档模式'), '内置通道隐私说明未显示本地文档语义');
  check(window.__assistantState.documents.length === 2, '启动时未加载文档目录');
  check(window.__assistantState.localModels.length === 2, '配置加载后未读取本地模型候选');
  const localModelSelect = $('assistant-local-model-select'), localModelInput = $('assistant-local-model');
  check(localModelInput.value === config.local_model, '初始模型列表加载覆盖了服务端保存的模型名');
  check(Array.from(localModelSelect.querySelectorAll('option')).map(option => option.value).filter(Boolean).join(',') === 'qwen2.5:7b,llama3.2:latest', '本地模型候选没有填入显式下拉框');
  check(localModelSelect.value === '', '列表外的手动模型名不应被下拉框覆盖');
  localModelSelect.value = 'llama3.2:latest'; localModelSelect.dispatchEvent(new window.Event('change'));
  check(localModelInput.value === 'llama3.2:latest', '选择下拉候选后没有填入模型名称');
  localModelInput.value = 'my-manual-model'; localModelInput.dispatchEvent(new window.Event('input'));
  check(localModelSelect.value === '', '手动输入列表外模型名后，下拉框应清除不匹配选择');
  localModelInput.value = config.local_model; localModelInput.dispatchEvent(new window.Event('input'));
  check($('assistant-doc-content').textContent.includes('sampling.fs'), '默认参数清单没有渲染为完整文档');
  $('assistant-doc-search').value = '设计'; $('assistant-doc-search').dispatchEvent(new window.Event('input'));
  check($('assistant-doc-list').querySelectorAll('button').length === 1, '文档搜索没有按标题和摘要过滤');
  $('assistant-doc-list').querySelector('button').click();
  check($('assistant-doc-content').textContent.includes('平台模块说明'), '选择本地文档后没有渲染完整正文');
  $('assistant-doc-search').value = ''; $('assistant-doc-search').dispatchEvent(new window.Event('input'));
  check($('assistant-doc-list').querySelectorAll('button').length === 2, '清除搜索后文档目录未恢复');
  check(style.includes('.assistant-panel{position:fixed;inset:0 0 0 auto;'), '助手 CSS 未定位到当前页面固定侧栏');
  check(style.includes('.assistant-workspace{display:grid;grid-template-columns:260px minmax(0,1fr)'), '双栏会话 / 问答布局缺失');
  check(style.includes('@media(max-width:680px)') && style.includes('.assistant-session-toggle{display:inline-flex'), '窄屏会话栏切换样式缺失');
  check(style.includes('.assistant-session-title{display:block;width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'), '长会话标题省略样式缺失');
  const cssRule = selector => { const start = style.indexOf(selector + '{'); return start < 0 ? '' : style.slice(start, style.indexOf('}', start)); };
  const messageScrollCss = cssRule('.assistant-messages');
  check(messageScrollCss.includes('overflow-y:auto') && messageScrollCss.includes('scroll-behavior:auto') && !messageScrollCss.includes('scroll-behavior:smooth'), '消息区必须有独立纵向滚轮且不能以平滑自动滚动抢占操作');
  check(cssRule('.assistant-conversation-list').includes('overflow-y:auto') && cssRule('.assistant-settings-body').includes('overflow-y:auto'), '会话栏与设置内容区必须可纵向滚动');
  check(html.includes('<aside id="assistant-panel"') && !html.includes('<dialog id="assistant-dialog"'), '助手必须使用同页侧栏而不是旧 dialog');

  const panel = $('assistant-panel'); $('assistant-launcher').click();
  check(!panel.hidden && panel.getAttribute('aria-hidden') === 'false', '点击入口没有打开固定侧栏');
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
  $('assistant-session-toggle').click();
  check(panel.classList.contains('sessions-collapsed'), '窄屏会话列表未折叠');
  $('assistant-session-toggle').click();
  check(!panel.classList.contains('sessions-collapsed'), '窄屏会话按钮无法重新展开');
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1024 });
  $('assistant-close').click();
  check(panel.hidden && panel.getAttribute('aria-hidden') === 'true', '关闭按钮没有收起侧栏');
  window.S.view = 'nilm'; window.assistantSyncLauncher();
  check($('assistant-launcher').hidden, 'visible_views 未控制入口显隐');
  window.S.view = 'overview'; window.assistantSyncLauncher();

  // 默认本地文档通道不调用模型，返回平台文档摘录和引用。
  $('assistant-prompt').value = '设备画像匹配有哪些注意事项？';
  await window.assistantSubmit();
  let messages = $('assistant-messages');
  check(lastChatPayload && lastChatPayload.model_type === 'builtin', '首次聊天没有使用内置文档后端');
  check(messages.textContent.includes('内置知识库｜本地文档检索') && messages.textContent.includes('pre_cycles'), '内置本地文档摘录未渲染');
  check(messages.textContent.includes('引用：平台参数清单'), '平台参数清单引用未显示');

  // 切换到本地模型后验证 SSE 分片解析与安全 Markdown/XSS。
  const model = $('assistant-model-type'); model.value = 'local'; model.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations.length === 2, '切换模型未新建会话');
  check(window.__assistantState.conversations[0].backend === 'local', '新会话未采用所选模型');
  check(window.__assistantState.conversations[1].messages.length === 2, '内置文档会话没有保留');
  const modelName = $('assistant-model-name');
  check(Array.from(modelName.options).some(option => option.value === 'qwen-local'), '具体模型下拉没有包含管理员配置的本地模型');
  check(Array.from(modelName.options).some(option => option.value === 'llama3.2:latest'), '具体模型下拉没有包含本地发现模型');
  modelName.value = 'llama3.2:latest'; modelName.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations[0].modelName === 'llama3.2:latest', '本地模型名称选择没有写入当前会话');
  $('assistant-prompt').value = '如何查看画像参数？';
  await window.assistantSubmit();
  messages = $('assistant-messages');
  check(messages.querySelectorAll('.assistant-message').length === 2, '本地模型会话没有显示用户与助手消息');
  check(lastChatPayload.model_name === 'llama3.2:latest', '本地聊天请求没有携带所选模型名称');
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
  modelName.value = 'qwen-local'; modelName.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations.length === 3, '切换具体本地模型未创建独立会话');
  check(window.__assistantState.conversations[0].modelName === 'qwen-local' && !window.__assistantState.conversations[0].messages.length, '新模型会话未使用所选模型或不为空');
  check(window.__assistantState.conversations[1].modelName === 'llama3.2:latest' && window.__assistantState.conversations[1].messages.length === 2, '切换具体模型破坏或更改了旧会话');
  $('assistant-prompt').value = '使用另一个模型继续提问'; await window.assistantSubmit();
  check(lastChatPayload.model_name === 'qwen-local', '新模型会话请求没有路由到所选模型');
  const sessionScroll = mockScrollArea($('assistant-conversation-list'), 900, 300, 40);
  const sessionWheel = new window.WheelEvent('wheel', { deltaY: 60, bubbles: true, cancelable: true });
  check(!window.document.querySelector('.assistant-session-heading').dispatchEvent(sessionWheel) && sessionScroll.top === 100, '在会话标题 / 空白区使用滚轮没有转发到会话列表');

  $('assistant-settings-open').click();
  const settingsScroll = mockScrollArea(window.document.querySelector('.assistant-settings-body'), 1000, 300, 100);
  mockScrollArea($('assistant-doc-content'), 600, 200, 400);
  const settingsWheel = new window.WheelEvent('wheel', { deltaY: 80, bubbles: true, cancelable: true });
  check(!$('assistant-doc-content').dispatchEvent(settingsWheel) && settingsScroll.top === 180, '嵌套文档滚动到底后，滚轮没有继续滚动设置面板');
  mockScrollArea($('assistant-doc-content'), 200, 200, 0);
  const noInnerOverflowWheel = new window.WheelEvent('wheel', { deltaY: 80, bubbles: true, cancelable: true });
  check(!$('assistant-doc-content').dispatchEvent(noInnerOverflowWheel) && settingsScroll.top === 260, '内层文档没有溢出时，滚轮没有滚动外层设置面板');
  $('assistant-settings-close').click();

  // 切换云端后端会创建独立会话；右侧具体模型列表包含默认模型和命名云端档案。
  model.value = 'cloud'; model.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations.length === 4, '切换后端未新建独立会话');
  check(window.__assistantState.conversations[0].backend === 'cloud', '新会话未采用所选后端');
  check(window.__assistantState.conversations[1].backend === 'local' && window.__assistantState.conversations[1].modelName === 'qwen-local' && window.__assistantState.conversations[1].messages.length === 2, '本地模型会话没有保留');
  check(window.__assistantState.conversations[2].backend === 'local' && window.__assistantState.conversations[2].modelName === 'llama3.2:latest' && window.__assistantState.conversations[2].messages.length === 2, '旧本地模型会话没有保留');
  check(window.__assistantState.conversations[3].backend === 'builtin' && window.__assistantState.conversations[3].messages.length === 2, '内置文档会话没有保留');
  check(Array.from(modelName.options).some(option => option.value === '__default__' && option.textContent.includes('cloud-model')), '云端模型列表没有默认模型名称');
  check(Array.from(modelName.options).some(option => option.value === 'cloud-alt' && option.textContent.includes('alt-chat')), '云端模型列表没有命名档案');
  modelName.value = 'cloud-alt'; modelName.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations[0].cloudProfileId === 'cloud-alt', '云端档案选择没有写入当前会话');

  // 配置保存必须带管理员口令，且密钥输入只作为 POST/PUT 参数，不回填页面。
  $('assistant-admin-token').value = 'admin'; $('assistant-admin-token').dispatchEvent(new window.Event('input'));
  const refreshModelsButton = $('assistant-refresh-local-models');
  localModelSelect.value = 'qwen2.5:7b'; localModelSelect.dispatchEvent(new window.Event('change'));
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
  check(lastConfigPayload.local_model === 'qwen2.5:7b', '下拉选中的本地模型未沿用既有配置保存字段');
  check(lastConfigPayload.cloud_api_profiles.length === 2, '动态添加的云端档案没有一起保存');
  const addedProfile = lastConfigPayload.cloud_api_profiles.find(profile => profile.name === 'Test provider');
  check(!!addedProfile && addedProfile.model === 'test-model-v2' && addedProfile.base_url === 'https://api.test-provider.example/v1', '动态档案的名称 / endpoint / 模型 ID 保存错误');
  check(lastConfigPayload.cloud_api_profile_secrets[addedProfile.id] === addedProfileSecret, '动态云端 API Key 没有单独提交');
  check(!JSON.stringify(lastConfigPayload.cloud_api_profiles).includes(addedProfileSecret), '云端 API Key 错误地放进档案元数据');
  check(!JSON.stringify(config).includes(addedProfileSecret), '配置返回值回显了云端 API Key');
  const savedProfileCard = Array.from($('assistant-cloud-profiles').querySelectorAll('.assistant-cloud-profile'))
    .find(card => card.textContent.includes('Test provider'));
  check(!!savedProfileCard && !savedProfileCard.querySelector('[data-cloud-profile-field="api_key"]').value, '保存后动态档案的 API Key 输入框未清空');
  localModelInput.value = 'my-custom-local-model'; localModelInput.dispatchEvent(new window.Event('input'));
  const waitForLocalRefresh = async () => {
    for (let i = 0; i < 100 && refreshModelsButton.disabled; i++) await new Promise(resolve => setTimeout(resolve, 10));
  };
  refreshModelsButton.click(); await waitForLocalRefresh();
  check(lastLocalModelRefresh && lastLocalModelRefresh.headers['X-Assistant-Admin-Token'] === 'admin', '刷新模型列表没有携带管理员口令');
  check(lastLocalModelRefresh.body.base_url === config.local_base_url, '刷新列表没有使用本地服务地址输入值');
  check(localModelInput.value === 'my-custom-local-model', '刷新候选覆盖了手动填写的模型名称');
  check(Array.from($('assistant-local-model-select').querySelectorAll('option')).map(option => option.value).filter(Boolean).join(',') === 'refreshed-local-model', '刷新后的候选没有更新');
  check($('assistant-local-model-select').value === '', '刷新候选覆盖了列表外的手动模型名');
  nextLocalModelRefresh = { status: 'empty', models: [] };
  refreshModelsButton.click(); await waitForLocalRefresh();
  check(localModelInput.value === 'my-custom-local-model', '空模型列表意外清除了手动填写值');
  check($('assistant-local-model-select').options.length === 1 && !$('assistant-local-model-select').options[0].value, '空响应后下拉仍显示过期候选');
  nextLocalModelRefresh = { fail: true };
  refreshModelsButton.click(); await waitForLocalRefresh();
  check(localModelInput.value === 'my-custom-local-model', '刷新失败意外清除了手动填写值');
  check($('assistant-local-models-status').textContent.includes('本地服务暂不可用'), '刷新失败状态未显示');
  nextLocalModelRefresh = { status: 'ready', models: ['refreshed-local-model'] };
  $('assistant-enabled').checked = true;
  $('assistant-cloud-key').value = 'temporary-cloud-secret';
  await window.assistantSaveConfig();
  check(!!lastConfigPayload && lastConfigPayload.cloud_api_key === 'temporary-cloud-secret', '配置保存载荷缺密钥');
  check(lastConfigPayload.local_model === 'my-custom-local-model', '手动模型名称未沿用既有配置保存流程');
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

  // 受控操作只显示预览；确认必须携带页面内存中的操作员令牌和二次确认码。
  model.value = 'local'; model.dispatchEvent(new window.Event('change'));
  $('assistant-operator-token').value = 'memory-only-operator-token';
  $('assistant-operator-token').dispatchEvent(new window.Event('input'));
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

  model.value = 'cloud'; model.dispatchEvent(new window.Event('change'));
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
  $('assistant-session-search').value = '手动命名'; $('assistant-session-search').dispatchEvent(new window.Event('input'));
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

  console.log(`PASS ${checkCount} checks — two-column fixed assistant sidebar, session search/groups/time/rename/delete/drag, bundled docs in settings, responsive sessions, builtin retrieval, safe Markdown/XSS, citations, editable local-model discovery, admin config, image upload/preview/cloud confirmation, local import, operator-token proposal confirmation`);
  dom.window.close();
})().catch(error => {
  console.error('FAIL:', error && error.stack || error);
  dom.window.close();
  process.exitCode = 1;
});
