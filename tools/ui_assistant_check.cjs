#!/usr/bin/env node
/* 智能问答前端行为检查：加载真实 HTML + app.js 中的 assistant 模块，mock 同源 API，不访问模型网络。
 * 用法：node tools/ui_assistant_check.cjs（需 npm ci / jsdom） */
'use strict';
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const ROOT = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'app/static/index.html'), 'utf8');
const source = fs.readFileSync(path.join(ROOT, 'app/static/app.js'), 'utf8');
const start = source.indexOf('/* ------------------------------------------------------------------ 智能问答');
const end = source.indexOf('async function init() {', start);
if (start < 0 || end < 0) throw new Error('未找到智能问答模块代码');

const dom = new JSDOM(html, { url: 'http://localhost/', runScripts: 'dangerously', pretendToBeVisual: true });
const { window } = dom;
window.S = { view: 'overview' };
window.TextDecoder = TextDecoder;
window.TextEncoder = TextEncoder;
window.ReadableStream = ReadableStream;
window.AbortController = AbortController;
window.confirm = () => true;

let config = {
  enabled: true, default_model_type: 'local',
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
let lastImportedDocuments = null;
let knowledgeDocuments = [];
window.fetch = async (url, options = {}) => {
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
  if (url === '/api/assistant/chat') {
    const payload = JSON.parse(options.body);
    if (!payload.stream || payload.model_type !== 'local') throw new Error('聊天请求参数不符合预期');
    const frames = [
      { type: 'sources', sources: [{ name: 'guide.md', score: 0.91 }] },
      { type: 'delta', text: '## 结论\n\n支持 **Markdown**、`代码`。\n\n```js\nalert(1)\n```\n\n<img src=x onerror=alert(1)>\n\n[坏链接](javascript:alert(1))' },
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
const check = (ok, message) => { if (!ok) throw new Error(message); };
check($('assistant-launcher').hidden, '配置读取前问答入口应默认隐藏');

(async () => {
  // 等待首次配置读取。
  for (let i = 0; i < 50 && !window.__assistantState.config; i++) await new Promise(resolve => setTimeout(resolve, 10));
  check(!!window.__assistantState.config, '配置未加载');
  check(!$('assistant-launcher').hidden, '总览页应显示入口');
  window.S.view = 'nilm'; window.assistantSyncLauncher();
  check($('assistant-launcher').hidden, 'visible_views 未控制入口显隐');
  window.S.view = 'overview'; window.assistantSyncLauncher();

  // 实际跑一次 SSE 聊天；Markdown 安全渲染不能创建原始 HTML 或 javascript: 链接。
  $('assistant-prompt').value = '如何查看画像参数？';
  await window.assistantSubmit();
  const messages = $('assistant-messages');
  check(messages.querySelectorAll('.assistant-message').length === 2, '会话没有显示用户与助手消息');
  check(!!messages.querySelector('h2') && !!messages.querySelector('strong') && !!messages.querySelector('pre code'), 'Markdown 标题/强调/代码块未渲染');
  check(!messages.querySelector('img, a[href^="javascript:"]'), '不可信 Markdown 被解释成活动 HTML');
  check(messages.textContent.includes('<img src=x onerror=alert(1)>'), '原始 HTML 应作为普通文本展示');
  check(messages.textContent.includes('引用：guide.md'), '缺少知识库引用标记');

  // 切换本地/云端模型必须先确认并创建新会话，旧会话仍然保留。
  const model = $('assistant-model-type'); model.value = 'cloud'; model.dispatchEvent(new window.Event('change'));
  check(window.__assistantState.conversations.length === 2, '切换模型未新建会话');
  check(window.__assistantState.conversations[0].backend === 'cloud', '新会话未采用所选模型');
  check(window.__assistantState.conversations[1].messages.length === 2, '旧会话没有保留');

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
  config = { ...config, enabled: false };
  await window.assistantLoadConfig();
  check($('assistant-launcher').hidden, 'enabled=false 时问答入口仍然可见');

  console.log('PASS 21 checks — launcher scope/disabled state, SSE chunk parsing, safe Markdown/XSS, RAG citations, model-switch sessions, admin config, local file import');
  dom.window.close();
})().catch(error => {
  console.error('FAIL:', error && error.stack || error);
  dom.window.close();
  process.exitCode = 1;
});
