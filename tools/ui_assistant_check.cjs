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
window.confirm = () => true;

let config = {
  enabled: true, default_model_type: 'builtin',
  local_base_url: 'http://127.0.0.1:11434/v1', local_model: 'qwen-local',
  cloud_base_url: 'https://api.example.test/v1', cloud_model: 'cloud-model',
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
    config = { ...config, ...lastConfigPayload, cloud_api_key_set: !!lastConfigPayload.cloud_api_key, admin_configurable: true };
    return jsonResponse({ ok: true, config });
  }
  if (url === '/api/assistant/tools/confirm' && options.method === 'POST') {
    lastConfirmPayload = JSON.parse(options.body); lastConfirmHeaders = options.headers;
    return jsonResponse({ ok: true, result: { message: '接线模式已切换为 3p4w', side: 'bus' } });
  }
  if (url === '/api/assistant/chat') {
    const payload = JSON.parse(options.body); lastChatPayload = payload;
    if (!payload.stream || !['builtin', 'local'].includes(payload.model_type)) throw new Error('聊天请求参数不符合预期');
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
check($('assistant-launcher').hidden, '配置读取前问答入口应默认隐藏');

(async () => {
  // 等待首次配置读取及启动时加载的完整内置文档库。
  for (let i = 0; i < 100 && (!window.__assistantState.config || !window.__assistantState.documents.length); i++) await new Promise(resolve => setTimeout(resolve, 10));
  check(!!window.__assistantState.config, '配置未加载');
  check(!$('assistant-launcher').hidden, '总览页应显示入口');
  check($('assistant-model-type').value === 'builtin', '未配置模型时应默认选择内置文档通道');
  check($('assistant-privacy-note').textContent.includes('本地文档模式'), '内置通道隐私说明未显示本地文档语义');
  check(window.__assistantState.documents.length === 2, '启动时未加载文档目录');
  check($('assistant-doc-content').textContent.includes('sampling.fs'), '默认参数清单没有渲染为完整文档');
  $('assistant-doc-search').value = '设计'; $('assistant-doc-search').dispatchEvent(new window.Event('input'));
  check($('assistant-doc-list').querySelectorAll('button').length === 1, '文档搜索没有按标题和摘要过滤');
  $('assistant-doc-list').querySelector('button').click();
  check($('assistant-doc-content').textContent.includes('平台模块说明'), '选择本地文档后没有渲染完整正文');
  $('assistant-doc-search').value = ''; $('assistant-doc-search').dispatchEvent(new window.Event('input'));
  check($('assistant-doc-list').querySelectorAll('button').length === 2, '清除搜索后文档目录未恢复');
  check(style.includes('.assistant-panel{box-sizing:border-box;position:fixed;inset:0 0 0 auto;'), '助手 CSS 未定位到当前页面固定侧栏');
  check(style.includes('@media(max-width:760px)') && style.includes('.assistant-mode-tabs{display:flex'), '移动端文档 / 问答标签样式缺失');
  check(html.includes('<aside id="assistant-panel"') && !html.includes('<dialog id="assistant-dialog"'), '助手必须使用同页侧栏而不是旧 dialog');

  const panel = $('assistant-panel'); $('assistant-launcher').click();
  check(!panel.hidden && panel.getAttribute('aria-hidden') === 'false', '点击入口没有打开固定侧栏');
  $('assistant-tab-docs').click();
  check($('assistant-doc-pane').classList.contains('is-active') && $('assistant-tab-docs').getAttribute('aria-selected') === 'true', '窄屏文档标签未切换到文档栏');
  $('assistant-tab-chat').click();
  check($('assistant-chat-pane').classList.contains('is-active') && $('assistant-tab-chat').getAttribute('aria-selected') === 'true', '窄屏问答标签未切换到问答栏');
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
  $('assistant-prompt').value = '如何查看画像参数？';
  await window.assistantSubmit();
  messages = $('assistant-messages');
  check(messages.querySelectorAll('.assistant-message').length === 2, '本地模型会话没有显示用户与助手消息');
  check(!!messages.querySelector('h2') && !!messages.querySelector('strong') && !!messages.querySelector('pre code'), 'Markdown 标题/强调/代码块未渲染');
  check(!messages.querySelector('img, a[href^="javascript:"]'), '不可信 Markdown 被解释成活动 HTML');
  check(messages.textContent.includes('<img src=x onerror=alert(1)>'), '原始 HTML 应作为普通文本展示');
  check(messages.textContent.includes('引用：guide.md'), '缺少知识库引用标记');

  // 切换云端模型必须先确认并创建新会话，内置和本地会话均保留。
  model.value = 'cloud'; model.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations.length === 3, '切换模型未新建独立会话');
  check(window.__assistantState.conversations[0].backend === 'cloud', '新会话未采用所选模型');
  check(window.__assistantState.conversations[1].backend === 'local' && window.__assistantState.conversations[1].messages.length === 2, '本地模型会话没有保留');
  check(window.__assistantState.conversations[2].backend === 'builtin' && window.__assistantState.conversations[2].messages.length === 2, '内置文档会话没有保留');

  // 配置保存必须带管理员口令，且密钥输入只作为 POST/PUT 参数，不回填页面。
  $('assistant-admin-token').value = 'admin'; $('assistant-admin-token').dispatchEvent(new window.Event('input'));
  $('assistant-enabled').checked = true;
  $('assistant-cloud-key').value = 'temporary-cloud-secret';
  await window.assistantSaveConfig();
  check(!!lastConfigPayload && lastConfigPayload.cloud_api_key === 'temporary-cloud-secret', '配置保存载荷缺密钥');
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

  config = { ...config, enabled: false };
  await window.assistantLoadConfig();
  check($('assistant-launcher').hidden, 'enabled=false 时问答入口仍然可见');

  console.log(`PASS ${checkCount} checks — fixed document/chat sidebar, bundled docs, mobile tabs, builtin retrieval, safe Markdown/XSS, citations, model sessions, admin config, local import, operator-token proposal confirmation`);
  dom.window.close();
})().catch(error => {
  console.error('FAIL:', error && error.stack || error);
  dom.window.close();
  process.exitCode = 1;
});
