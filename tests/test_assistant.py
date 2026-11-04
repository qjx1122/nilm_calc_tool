"""智能问答服务单元测试：密钥边界、配置校验、RAG 与模型适配。"""
from __future__ import annotations

import json

import pytest

from app.assistant import AssistantError, AssistantService, DEFAULT_CONFIG, _number


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


def test_builtin_demo_channel_is_zero_configuration_and_retrieves_excerpts(tmp_path, monkeypatch):
    monkeypatch.delenv("ELEC_TOOL_ASSISTANT_BACKEND", raising=False)
    monkeypatch.delenv("ELEC_TOOL_ASSISTANT_ENABLED", raising=False)
    monkeypatch.delenv("ELEC_TOOL_ASSISTANT_LOCAL_API_KEY", raising=False)
    monkeypatch.delenv("ELEC_TOOL_ASSISTANT_CLOUD_API_KEY", raising=False)
    service = AssistantService(data_dir=str(tmp_path))
    assert service.public_config()["default_model_type"] == "builtin"

    plan = service.prepare_chat({"prompt": "设备画像匹配"})
    assert plan["model_type"] == "builtin"
    assert plan["sources"] and plan["sources"][0]["name"] == "demo_profile_matching.md"
    assert "无需配置或调用模型" in plan["answer"]
    assert "pre_cycles" in plan["answer"]
    assert "base_url" not in plan and "api_key" not in plan

    def no_model_request(*args, **kwargs):
        raise AssertionError("builtin demo mode must not contact a model endpoint")
    monkeypatch.setattr(service, "_open_request", no_model_request)
    assert service.complete(plan) == plan["answer"]
    import threading
    assert "".join(service.stream(plan, threading.Event())) == plan["answer"]


def test_local_knowledge_import_search_and_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", "kb-admin")
    service = AssistantService(data_dir=str(tmp_path))
    imported = service.import_documents({"documents": [{
        "name": "nilm-guide.md", "content": "负荷辨识画像匹配需要设置 pre_cycles、post_cycles 和 window_cycles。"
    }]}, "kb-admin")
    assert imported["count"] == 1
    assert imported["documents"][0]["name"] == "nilm-guide.md"
    matches = service.search_knowledge("负荷辨识画像匹配 post_cycles", 4, 0.0)
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
