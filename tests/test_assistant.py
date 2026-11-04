"""智能问答服务单元测试：密钥边界、配置校验、RAG 与模型适配。"""
from __future__ import annotations

import json

import pytest

from app.assistant import AssistantError, AssistantService, DEFAULT_CONFIG, _number
from app.assistant_docs import PLATFORM_PARAMETER_DOC_ID
from app.assistant_tools import TOOL_NAMES, openai_tool_schemas, validate_tool_arguments


def test_integer_settings_reject_fractional_and_boolean_values():
    assert _number(3, "count", 1, 10, integer=True) == 3
    assert _number("3.0", "count", 1, 10, integer=True) == 3
    for value in (1.5, True, "not-a-number"):
        with pytest.raises(AssistantError, match="整数"):
            _number(value, "count", 1, 10, integer=True)


def test_corrupted_persisted_config_falls_back_to_safe_defaults(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({
        "rag_top_k": "broken", "timeout_s": "NaN", "max_tokens": 25.7,
        "enabled": "false", "rag_enabled": "false", "local_base_url": "http://8.8.8.8/v1",
    }), encoding="utf-8")
    service = AssistantService(data_dir=str(tmp_path))
    cfg = service.public_config()
    assert cfg["rag_top_k"] == DEFAULT_CONFIG["rag_top_k"]
    assert cfg["timeout_s"] == DEFAULT_CONFIG["timeout_s"]
    assert cfg["max_tokens"] == DEFAULT_CONFIG["max_tokens"]
    assert cfg["enabled"] is True
    assert cfg["rag_enabled"] is True
    assert cfg["local_base_url"] == DEFAULT_CONFIG["local_base_url"]


def test_malformed_enabled_tools_allowlist_fails_closed(tmp_path, monkeypatch):
    admin = "malformed-tools-admin"
    operator = "malformed-tools-operator-secret"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "operator", "token": operator, "scopes": ["config.wiring.write"]},
    ]))
    (tmp_path / "config.json").write_text(json.dumps({
        "tools_enabled": True, "cloud_tools_enabled": True,
        "enabled_tools": "set_wiring_mode",
    }), encoding="utf-8")

    service = AssistantService(data_dir=str(tmp_path))
    assert service.public_config()["tools_enabled"] is True
    assert service.public_config()["enabled_tools"] == []
    authenticated = service.authenticate_operator(operator)
    assert service.operator_tools(authenticated, "local") == []
    plan = service.prepare_chat({"prompt": "切换接线模式到 3p4w", "model_type": "local"},
                                operator_token=operator, side="bus")
    assert plan["_available_tools"] == []


def test_admin_config_keeps_api_keys_out_of_json_and_public_view(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", "test-admin-token")
    service = AssistantService(data_dir=str(tmp_path))
    with pytest.raises(AssistantError) as denied:
        service.update_config({"enabled": False}, "wrong-token")
    assert denied.value.status_code == 403

    secret = "cloud-test-secret-value"
    config = service.update_config({"cloud_api_key": secret, "enabled": False, "rag_top_k": 3,
                                    "sensitive_terms": ["INTERNAL-PROJECT-ALPHA"]}, "test-admin-token")
    assert config["cloud_api_key_set"] is True
    assert "cloud_api_key" not in config and "sensitive_terms" not in config and secret not in json.dumps(config)
    assert service.admin_config("test-admin-token")["sensitive_terms"] == ["INTERNAL-PROJECT-ALPHA"]
    persisted = (tmp_path / "config.json").read_text(encoding="utf-8")
    assert secret not in persisted
    assert json.loads(persisted)["rag_top_k"] == 3
    service.update_config({"enabled": True}, "test-admin-token")
    assert service.admin_config("test-admin-token")["sensitive_terms"] == ["INTERNAL-PROJECT-ALPHA"]

    with pytest.raises(AssistantError, match="整数"):
        service.update_config({"rag_top_k": 2.5}, "test-admin-token")
    with pytest.raises(AssistantError, match="布尔"):
        service.update_config({"enabled": "false"}, "test-admin-token")
    with pytest.raises(AssistantError, match="本地模型地址"):
        service.update_config({"local_base_url": "http://8.8.8.8/v1"}, "test-admin-token")
    with pytest.raises(AssistantError, match="API Key"):
        service.update_config({"cloud_api_key": {"unexpected": "object"}}, "test-admin-token")
    with pytest.raises(AssistantError, match="4096"):
        service.update_config({"cloud_api_key": "x" * 4097}, "test-admin-token")
    with pytest.raises(AssistantError, match="敏感词"):
        service.update_config({"sensitive_terms": [123]}, "test-admin-token")


def test_builtin_channel_is_zero_configuration_and_retrieves_bundled_docs(tmp_path, monkeypatch):
    monkeypatch.delenv("ELEC_TOOL_ASSISTANT_BACKEND", raising=False)
    monkeypatch.delenv("ELEC_TOOL_ASSISTANT_ENABLED", raising=False)
    monkeypatch.delenv("ELEC_TOOL_ASSISTANT_LOCAL_API_KEY", raising=False)
    monkeypatch.delenv("ELEC_TOOL_ASSISTANT_CLOUD_API_KEY", raising=False)
    service = AssistantService(data_dir=str(tmp_path))
    assert service.public_config()["default_model_type"] == "builtin"

    plan = service.prepare_chat({"prompt": "设备画像匹配的 pre_cycles 与 window_cycles 参数默认值是什么？"})
    assert plan["model_type"] == "builtin"
    assert plan["sources"] and plan["sources"][0]["name"] == "平台参数清单"
    assert "无需配置或调用模型" in plan["answer"]
    assert "pre_cycles" in plan["answer"] and "window_cycles" in plan["answer"]
    assert "demo_profile_matching.md" not in plan["answer"]
    assert "base_url" not in plan and "api_key" not in plan

    def no_model_request(*args, **kwargs):
        raise AssertionError("builtin local-doc mode must not contact a model endpoint")
    monkeypatch.setattr(service, "_open_request", no_model_request)
    assert service.complete(plan) == plan["answer"]
    import threading
    assert "".join(service.stream(plan, threading.Event())) == plan["answer"]


def test_bundled_library_has_required_manuals_and_parameter_provenance(tmp_path):
    service = AssistantService(data_dir=str(tmp_path))
    library = service.document_library()
    docs = {doc["id"]: doc for doc in library["documents"]}
    assert library["count"] >= 7
    assert library["characters"] == sum(doc["characters"] for doc in library["documents"])
    assert {
        "builtin-software-design", "builtin-software-usage", "builtin-software-deployment",
        "builtin-algorithm-tuning-validation", PLATFORM_PARAMETER_DOC_ID,
        "builtin-assistant-guide", "builtin-data-dictionary",
    } <= docs.keys()
    assert all(doc["content"] and doc["characters"] == len(doc["content"]) for doc in docs.values())

    catalog = docs[PLATFORM_PARAMETER_DOC_ID]["content"]
    assert "| 配置路径 | 代码默认值 | 总线模板值 | 分路模板值 |" in catalog
    assert "`sampling.fs` | `6400.0` | `6400.0` | `6400.0`" in catalog
    assert "`nilm.algorithms.profile.enabled` | `false`" in catalog
    assert "`nilm.algorithms.threshold.min_delta_w` | `50.0` | `未显式配置` | `50.0`" in catalog
    assert "实际有效值" in catalog

    matches = service.search_knowledge("sampling.fs 参数默认值", 4, 0.08)
    assert matches and matches[0]["id"] == PLATFORM_PARAMETER_DOC_ID
    assert any("软件部署说明文档" == hit["name"] for hit in service.search_knowledge("如何部署软件？", 4, 0.08))


def test_bundled_assistant_loads_generated_markdown_files(monkeypatch):
    from pathlib import Path
    from app import assistant_docs

    root = Path(__file__).resolve().parents[1]
    def unexpected_fallback(_root):
        raise AssertionError("generated Markdown files should be the normal assistant corpus source")
    monkeypatch.setattr(assistant_docs, "build_project_documents", unexpected_fallback)

    docs = {doc["id"]: doc for doc in assistant_docs.load_bundled_documents(root)}
    for doc_id, title, _category, relative_path, _summary in assistant_docs.GENERATED_DOCUMENTS:
        expected = (root / relative_path).read_text(encoding="utf-8").strip()
        assert docs[doc_id]["name"] == title
        assert docs[doc_id]["content"] == expected
        assert docs[doc_id]["characters"] == len(expected)


def test_local_and_cloud_rag_context_uses_bundled_platform_catalog(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_CLOUD_API_KEY", "cloud-test-key")
    service = AssistantService(data_dir=str(tmp_path))
    for backend in ("local", "cloud"):
        plan = service.prepare_chat({"prompt": "sampling.fs 参数默认值是多少？", "model_type": backend})
        assert plan["model_type"] == backend
        assert plan["sources"] and plan["sources"][0]["id"] == PLATFORM_PARAMETER_DOC_ID
        assert "sampling.fs" in plan["sources"][0]["snippet"]
        assert "sampling.fs" in plan["messages"][0]["content"]
        assert plan["messages"][-1] == {"role": "user", "content": "sampling.fs 参数默认值是多少？"}


def test_local_knowledge_import_search_and_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", "kb-admin")
    service = AssistantService(data_dir=str(tmp_path))
    imported = service.import_documents({"documents": [{
        "name": "nilm-guide.md", "content": "现场专属标识 ZetaLab503：负荷辨识画像匹配验证记录。"
    }]}, "kb-admin")
    assert imported["count"] == 1
    assert imported["documents"][0]["name"] == "nilm-guide.md"
    matches = service.search_knowledge("ZetaLab503 画像验证", 4, 0.0)
    assert matches and matches[0]["name"] == "nilm-guide.md"
    result = service.delete_document(imported["documents"][0]["id"], "kb-admin")
    assert result["removed"] == 1 and result["count"] == 0


def test_hidden_source_filenames_are_redacted_from_context_citations_and_answers(tmp_path, monkeypatch):
    import threading

    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", "redaction-admin")
    service = AssistantService(data_dir=str(tmp_path))
    filename = "confidential-site-report.md"
    service.import_documents({"documents": [{
        "name": filename,
        "content": f"设备画像匹配参数说明；原始支撑文件名为 {filename}，前后窗口需要保持一致。",
    }]}, "redaction-admin")
    plan = service.prepare_chat({
        "prompt": f"请说明设备画像匹配，参考 {filename}",
        "history": [{"role": "user", "content": f"上次提到 {filename}"}],
        "model_type": "local",
    }, redact_source_names=True)

    assert plan["sources"][0]["name"] == "已脱敏资料 1"
    exposed_context = json.dumps({"sources": plan["sources"], "messages": plan["messages"]}, ensure_ascii=False)
    assert filename not in exposed_context
    assert filename in plan["_redact_names"]  # original name remains private service-side only

    class FakeCompletionResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, limit):
            return json.dumps({"choices": [{"message": {"content": f"答案引用 {filename}。"}}]}, ensure_ascii=False).encode("utf-8")

    class FakeStreamResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def __iter__(self):
            for piece in ("回答：引用 ", "confidential-site-", "report.md，建议复核。"):
                frame = {"choices": [{"delta": {"content": piece}}]}
                yield ("data: " + json.dumps(frame, ensure_ascii=False) + "\n").encode("utf-8")
            yield b"data: [DONE]\n"

    monkeypatch.setattr(service, "_open_request", lambda request_plan, stream: FakeStreamResponse() if stream else FakeCompletionResponse())
    complete = service.complete(plan)
    assert filename not in complete and "已脱敏资料" in complete
    streamed = "".join(service.stream(plan, threading.Event()))
    assert filename not in streamed and "已脱敏资料" in streamed


def test_knowledge_total_limit_counts_utf8_bytes(tmp_path, monkeypatch):
    from app import assistant as assistant_module

    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", "kb-size-admin")
    monkeypatch.setattr(assistant_module, "MAX_KB_BYTES", 5)
    service = AssistantService(data_dir=str(tmp_path))
    with pytest.raises(AssistantError, match="20 MB"):
        service.import_documents({"documents": [{"name": "unicode.txt", "content": "中文"}]}, "kb-size-admin")


def test_cloud_mode_blocks_sensitive_prompt_history_and_retrieved_context(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", "safety-admin")
    service = AssistantService(data_dir=str(tmp_path))
    service.update_config({
        "cloud_api_key": "cloud-key-for-test", "sensitive_terms": ["CUSTOMER-ALPHA"],
        "rag_similarity_threshold": 0.0,
    }, "safety-admin")

    with pytest.raises(AssistantError, match="敏感词") as blocked:
        service.prepare_chat({"prompt": "请分析 CUSTOMER-ALPHA 的数据", "model_type": "cloud"})
    assert "CUSTOMER-ALPHA" not in blocked.value.message
    with pytest.raises(AssistantError, match="疑似 API Key"):
        service.prepare_chat({"prompt": "普通问题", "history": [
            {"role": "user", "content": "api_key=abcdef0123456789"}
        ], "model_type": "cloud"})

    service.import_documents({"documents": [{
        "name": "confidential.txt", "content": "负荷辨识参数说明 CUSTOMER-ALPHA 为内部项目代号。"
    }]}, "safety-admin")
    with pytest.raises(AssistantError, match="敏感词") as blocked_snippet:
        service.prepare_chat({"prompt": "负荷辨识参数说明", "model_type": "cloud"})
    assert "CUSTOMER-ALPHA" not in blocked_snippet.value.message

    # 本地模式不会经过云端敏感内容拦截；模型请求本身仍只会由路由发起。
    local = service.prepare_chat({"prompt": "请分析 CUSTOMER-ALPHA 的数据", "model_type": "local"})
    assert local["model_type"] == "local"
    assert "127.0.0.1" in local["base_url"]


def test_request_rate_limit_releases_active_slot(tmp_path):
    service = AssistantService(data_dir=str(tmp_path))
    for _ in range(12):
        service.acquire_request("client-A")
        service.release_request()
    with pytest.raises(AssistantError) as limited:
        service.acquire_request("client-A")
    assert limited.value.status_code == 429


def test_openai_compatible_request_headers_payload_and_proxy_policy(tmp_path, monkeypatch):
    import json as json_module
    import urllib.request

    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_LOCAL_API_KEY", "local-env-key")
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_CLOUD_API_KEY", "cloud-env-key")
    service = AssistantService(data_dir=str(tmp_path))
    calls = []

    class FakeOpener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            return object()

    handlers = []
    def fake_build_opener(*args):
        handlers.append(args)
        return FakeOpener()

    monkeypatch.setattr(urllib.request, "build_opener", fake_build_opener)
    for backend, key, is_local in (("local", "local-env-key", True), ("cloud", "cloud-env-key", False)):
        plan = service.prepare_chat({"prompt": "解释画像匹配", "model_type": backend})
        assert plan["api_key"] == key
        service._open_request(plan, stream=True)
        request, timeout = calls[-1]
        assert request.full_url.endswith("/chat/completions")
        assert request.get_header("Authorization") == "Bearer " + key
        assert timeout == plan["timeout_s"]
        body = json_module.loads(request.data.decode("utf-8"))
        assert body["model"] == plan["model"] and body["stream"] is True
        assert body["messages"][-1] == {"role": "user", "content": "解释画像匹配"}
        assert request.get_header("Content-type") == "application/json"
        if is_local:
            assert len(handlers[-1]) == 1 and isinstance(handlers[-1][0], urllib.request.ProxyHandler)
            assert handlers[-1][0].proxies == {}
        else:
            assert handlers[-1] == ()  # 云端仅使用系统代理配置


def test_upstream_sse_parsing_and_friendly_http_error(tmp_path, monkeypatch):
    import threading
    import urllib.error

    service = AssistantService(data_dir=str(tmp_path))
    plan = service.prepare_chat({"prompt": "说明电能质量事件", "model_type": "local"})

    class FakeStreamResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def __iter__(self):
            yield 'data: {"choices":[{"delta":{"content":"第一段"}}]}\n'.encode("utf-8")
            yield 'data: {"choices":[{"delta":{"content":"第二段"}}]}\n'.encode("utf-8")
            yield b'data: [DONE]\n'

    monkeypatch.setattr(service, "_open_request", lambda request_plan, stream: FakeStreamResponse())
    assert list(service.stream(plan, threading.Event())) == ["第一段", "第二段"]

    class FakeCompletionResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, limit): return '{"choices":[{"message":{"content":"普通回答"}}]}'.encode("utf-8")
    def completion_response(request_plan, stream):
        assert stream is False
        return FakeCompletionResponse()
    monkeypatch.setattr(service, "_open_request", completion_response)
    assert service.complete(plan) == "普通回答"

    def unauthorized(*args, **kwargs):
        raise urllib.error.HTTPError("http://127.0.0.1/v1/chat/completions", 401, "unauthorized", {}, None)
    monkeypatch.setattr(service, "_open_request", unauthorized)
    with pytest.raises(AssistantError) as error:
        service.complete(plan)
    assert error.value.status_code == 502
    assert "鉴权失败" in error.value.message and "local" not in error.value.message


def test_tool_catalog_validation_and_closed_scope_proposal(tmp_path, monkeypatch):
    import threading

    admin = "tool-admin-test-token"
    operator = "tool-operator-secret-12345"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "field-operator", "token": operator, "scopes": ["config.wiring.write"]},
        {"id": "other-operator", "token": "other-operator-secret-123", "scopes": ["data.export"]},
    ]))
    service = AssistantService(data_dir=str(tmp_path))
    assert service.public_config()["tools_enabled"] is False
    assert service.public_config()["cloud_tools_enabled"] is False
    assert set(TOOL_NAMES) == {item["function"]["name"] for item in openai_tool_schemas(TOOL_NAMES)}
    assert validate_tool_arguments("set_wiring_mode", '{"wiring":"3p4w"}') == {"wiring": "3p4w"}
    with pytest.raises(ValueError, match="未注册字段"):
        validate_tool_arguments("set_wiring_mode", {"wiring": "3p4w", "path": "/etc/passwd"})
    with pytest.raises(ValueError, match="JSON 数字"):
        validate_tool_arguments("set_profile_parameters", {"d2_max": "9"})
    with pytest.raises(ValueError):
        validate_tool_arguments("export_csv", {"dataset": ["curves"]})

    service.update_config({"tools_enabled": True, "enabled_tools": ["set_wiring_mode"]}, admin)
    assert service.verify_operator(operator, "local")["available_tools"] == ["set_wiring_mode"]
    assert service.verify_operator(operator, "cloud")["available_tools"] == []  # cloud tools default off
    plan = service.prepare_chat({"prompt": "请切换接线模式为 3p4w", "model_type": "local"},
                                operator_token=operator, side="branch",
                                tool_context={"source": {"kind": "csv_file"}})
    assert plan["_available_tools"] == ["set_wiring_mode"]

    class FakeCompletionResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, limit):
            return json.dumps({"choices": [{"message": {
                "content": "", "tool_calls": [{"id": "call-1", "type": "function", "function": {
                    "name": "set_wiring_mode", "arguments": '{"wiring":"3p4w"}'}}]}}]}).encode("utf-8")
    monkeypatch.setattr(service, "_open_request", lambda request_plan, stream: FakeCompletionResponse())
    answer = service.complete(plan)
    proposal = plan["_tool_proposal"]
    assert "请核对操作摘要" in answer
    assert proposal["status"] == "pending" and proposal["side"] == "branch"
    assert proposal["requires_second_confirmation"] and proposal["confirmation_code"]
    with pytest.raises(AssistantError, match="另一位操作员"):
        service.claim_tool_proposal(proposal["id"], "other-operator-secret-123", "branch", proposal["confirmation_code"])
    with pytest.raises(AssistantError, match="预览时不同"):
        service.claim_tool_proposal(proposal["id"], operator, "bus", proposal["confirmation_code"])
    saved_tokens = json.dumps([
        {"id": "field-operator", "token": operator, "scopes": []},
        {"id": "other-operator", "token": "other-operator-secret-123", "scopes": ["data.export"]},
    ])
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", saved_tokens)
    with pytest.raises(AssistantError, match="已无该工具权限"):
        service.claim_tool_proposal(proposal["id"], operator, "branch", proposal["confirmation_code"])
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "field-operator", "token": operator, "scopes": ["config.wiring.write"]},
        {"id": "other-operator", "token": "other-operator-secret-123", "scopes": ["data.export"]},
    ]))
    service.update_config({"tools_enabled": False}, admin)
    with pytest.raises(AssistantError, match="关闭该工具"):
        service.claim_tool_proposal(proposal["id"], operator, "branch", proposal["confirmation_code"])
    service.update_config({"tools_enabled": True}, admin)
    with pytest.raises(AssistantError, match="不匹配"):
        service.claim_tool_proposal(proposal["id"], operator, "branch", "000000" if proposal["confirmation_code"] != "000000" else "000001")
    claimed = service.claim_tool_proposal(proposal["id"], operator, "branch", proposal["confirmation_code"])
    assert claimed["name"] == "set_wiring_mode" and claimed["side"] == "branch"
    with pytest.raises(AssistantError, match="不存在"):
        service.claim_tool_proposal(proposal["id"], operator, "branch", proposal["confirmation_code"])
    service.record_tool_result(claimed, "success", {"message": "updated"})

    from app import assistant as assistant_module
    old_ttl = assistant_module.PENDING_TOOL_TTL_S
    monkeypatch.setattr(assistant_module, "PENDING_TOOL_TTL_S", -1.0)
    expired = service.create_tool_proposal(plan, [{"function": {
        "name": "set_wiring_mode", "arguments": {"wiring": "3p3w"}
    }}])
    with pytest.raises(AssistantError) as expired_error:
        service.claim_tool_proposal(expired["id"], operator, "branch", expired["confirmation_code"])
    assert expired_error.value.status_code == 410
    monkeypatch.setattr(assistant_module, "PENDING_TOOL_TTL_S", old_ttl)

    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_CLOUD_API_KEY", "cloud-tool-test-key")
    service.update_config({"cloud_tools_enabled": True}, admin)
    cloud_plan = service.prepare_chat({"prompt": "切换接线模式到 3p3w", "model_type": "cloud"},
                                      operator_token=operator, side="branch")
    cloud_proposal = service.create_tool_proposal(cloud_plan, [{"function": {
        "name": "set_wiring_mode", "arguments": {"wiring": "3p3w"}
    }}])
    service.update_config({"cloud_tools_enabled": False}, admin)
    with pytest.raises(AssistantError, match="关闭云端工具执行"):
        service.claim_tool_proposal(cloud_proposal["id"], operator, "branch", cloud_proposal["confirmation_code"])
    assert (tmp_path / "tool_audit.jsonl").exists()


def test_cloud_mode_blocks_local_file_references_but_allows_api_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_CLOUD_API_KEY", "cloud-test-key")
    service = AssistantService(data_dir=str(tmp_path))
    blocked = [r"C:\data\capture.csv", r"\\server\share\capture.csv", "/data/session/capture.csv",
               "Please inspect capture.csv", "recording.dat", "recording.txt", "notes.md", "file:///tmp/recording.json"]
    for prompt in blocked:
        with pytest.raises(AssistantError, match="文件路径或录波文件名"):
            service.prepare_chat({"prompt": prompt, "model_type": "cloud"})
    allowed = service.prepare_chat({"prompt": "How does /api/assistant/chat work?", "model_type": "cloud"})
    assert allowed["model_type"] == "cloud"
