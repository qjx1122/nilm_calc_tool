"""智能问答服务单元测试：密钥边界、配置校验、RAG 与模型适配。"""
from __future__ import annotations

import base64
import json
import re

import pytest

from app.assistant import (AssistantError, AssistantService, DEFAULT_CONFIG,
                           _explicit_offline_source_start, _explicit_tool_command, _number)
from app.assistant_docs import PLATFORM_PARAMETER_DOC_ID
from app.assistant_tools import TOOL_CATALOG, TOOL_NAMES, openai_tool_schemas, validate_tool_arguments


def _fake_model_reply(message=None, deltas=(), on_stream_end=None):
    """Stand-in for ``AssistantService._open_request``: one canned reply for each mode.

    ``message`` is the non-streaming reply; ``deltas`` are the streamed chunks.
    ``on_stream_end`` runs once the model has handed over its last chunk.
    """

    class Completion:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, _limit):
            return json.dumps({"choices": [{"message": message}]}).encode("utf-8")

    class Stream:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def __iter__(self):
            for delta in deltas:
                yield ("data: " + json.dumps({"choices": [{"delta": delta}]}) + "\n").encode("utf-8")
            if on_stream_end:
                on_stream_end()
            yield b"data: [DONE]\n"

    return lambda _plan, stream: Stream() if stream else Completion()


def _tool_call(name, arguments, index=0):
    return {"index": index, "id": f"call-{index}", "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments)}}


def _tool_gate_service(tmp_path, monkeypatch, enabled_tools, scopes):
    """A service whose single operator may use ``enabled_tools``; returns ``(service, operator_token)``."""
    admin = "tool-gate-admin-token"
    operator = "tool-gate-operator-token-secret"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "tool-gate-operator", "token": operator, "scopes": list(scopes)},
    ]))
    service = AssistantService(data_dir=str(tmp_path))
    service.update_config({"tools_enabled": True, "enabled_tools": list(enabled_tools)}, admin)
    return service, operator


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
        "local_model": "legacy-model-that-must-be-ignored",
    }), encoding="utf-8")
    service = AssistantService(data_dir=str(tmp_path))
    cfg = service.public_config()
    assert cfg["rag_top_k"] == DEFAULT_CONFIG["rag_top_k"]
    assert cfg["timeout_s"] == DEFAULT_CONFIG["timeout_s"]
    assert cfg["max_tokens"] == DEFAULT_CONFIG["max_tokens"]
    assert cfg["enabled"] is True
    assert cfg["rag_enabled"] is True
    assert cfg["local_base_url"] == DEFAULT_CONFIG["local_base_url"]
    assert "local_model" not in DEFAULT_CONFIG and "local_model" not in cfg
    assert "local_model" not in json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))


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
    with pytest.raises(AssistantError, match="本地模型名称由问答窗口"):
        service.update_config({"local_model": "retired-config-value"}, "test-admin-token")
    assert "local_model" not in service.public_config()
    with pytest.raises(AssistantError, match="API Key"):
        service.update_config({"cloud_api_key": {"unexpected": "object"}}, "test-admin-token")
    with pytest.raises(AssistantError, match="4096"):
        service.update_config({"cloud_api_key": "x" * 4097}, "test-admin-token")
    with pytest.raises(AssistantError, match="敏感词"):
        service.update_config({"sensitive_terms": [123]}, "test-admin-token")


def test_named_cloud_profiles_keep_keys_memory_only_and_route_by_server_id(tmp_path, monkeypatch):
    admin = "cloud-profile-admin-token"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    service = AssistantService(data_dir=str(tmp_path))
    profile = {"id": "provider-alt", "name": "备用服务", "base_url": "https://api.alt.example/v1", "model": "reasoner-32k"}
    default_secret = "default-cloud-secret-value"
    profile_secret = "profile-cloud-secret-value"

    public = service.update_config({
        "cloud_base_url": "https://api.default.example/v1", "cloud_model": "default-chat",
        "cloud_api_key": default_secret, "cloud_api_profiles": [profile],
        "cloud_api_profile_secrets": {"provider-alt": profile_secret},
    }, admin)
    assert public["cloud_model"] == "default-chat"  # 旧的单一云端配置继续兼容
    assert public["cloud_api_key_set"] is True
    assert public["cloud_api_profiles"] == [{**profile, "api_key_set": True}]
    assert profile_secret not in json.dumps(public) and default_secret not in json.dumps(public)
    persisted = (tmp_path / "config.json").read_text(encoding="utf-8")
    assert profile_secret not in persisted and default_secret not in persisted
    saved_profiles = json.loads(persisted)["cloud_api_profiles"]
    assert saved_profiles == [profile] and "api_key" not in json.dumps(saved_profiles)

    default_plan = service.prepare_chat({"prompt": "解释配置范围", "model_type": "cloud", "rag_enabled": False})
    assert (default_plan["base_url"], default_plan["model"], default_plan["api_key"]) == (
        "https://api.default.example/v1", "default-chat", default_secret)
    profile_plan = service.prepare_chat({"prompt": "解释配置范围", "model_type": "cloud",
                                         "cloud_profile_id": "provider-alt", "rag_enabled": False})
    assert (profile_plan["base_url"], profile_plan["model"], profile_plan["api_key"]) == (
        profile["base_url"], profile["model"], profile_secret)
    assert profile_secret not in json.dumps(public)

    local_plan = service.prepare_chat({"prompt": "解释配置范围", "model_type": "local",
                                       "model_name": "qwen2.5:14b", "rag_enabled": False})
    assert local_plan["model"] == "qwen2.5:14b"
    with pytest.raises(AssistantError, match="云端模型只能"):
        service.prepare_chat({"prompt": "测试", "model_type": "cloud", "model_name": "client-chosen",
                              "rag_enabled": False})
    with pytest.raises(AssistantError, match="不存在"):
        service.prepare_chat({"prompt": "测试", "model_type": "cloud", "cloud_profile_id": "unknown",
                              "rag_enabled": False})
    with pytest.raises(AssistantError, match="ID 格式"):
        service.update_config({"cloud_api_profiles": [{**profile, "id": "bad\\nprofile"}]}, admin)
    with pytest.raises(AssistantError, match="HTTPS"):
        service.update_config({"cloud_api_profiles": [{**profile, "base_url": "http://example.com/v1"}]}, admin)
    with pytest.raises(AssistantError, match="必须通过独立字段"):
        service.update_config({"cloud_api_profiles": [{**profile, "api_key": profile_secret}]}, admin)

    service.update_config({"cloud_api_profiles": [profile], "cloud_api_profile_secrets": {}}, admin)
    assert service.public_config()["cloud_api_profiles"][0]["api_key_set"] is True  # 空输入保留内存 Key
    service.update_config({"cloud_api_profile_secrets": {}, "clear_cloud_api_profile_secrets": ["provider-alt"]}, admin)
    assert service.public_config()["cloud_api_profiles"][0]["api_key_set"] is False
    with pytest.raises(AssistantError, match="尚未设置 API Key"):
        service.prepare_chat({"prompt": "测试", "model_type": "cloud", "cloud_profile_id": "provider-alt",
                              "rag_enabled": False})
    reloaded = AssistantService(data_dir=str(tmp_path))
    assert reloaded.public_config()["cloud_api_profiles"] == [{**profile, "api_key_set": False}]
    service.update_config({"cloud_api_profiles": []}, admin)
    assert service.public_config()["cloud_api_profiles"] == []
    assert not service._cloud_profile_secrets


def test_local_model_catalog_parses_openai_response_and_bypasses_proxies(tmp_path, monkeypatch):
    import urllib.request

    admin = "local-model-admin-token"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    service = AssistantService(data_dir=str(tmp_path / "openai-catalog"))
    service.update_config({"local_api_key": "local-catalog-key"}, admin)
    calls = []

    class FakeResponse:
        def __init__(self, data):
            self.data = json.dumps(data).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, limit):
            return self.data[:limit]

    class FakeOpener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            return FakeResponse({"data": [
                {"id": "qwen2.5:7b"}, {"id": "qwen2.5:7b"}, {"name": " llama3.2:latest "},
                {"id": "bad\nname"}, {"id": "x" * 161}, None,
            ]})

    def fake_build_opener(*handlers):
        assert len(handlers) == 1 and isinstance(handlers[0], urllib.request.ProxyHandler)
        assert handlers[0].proxies == {}, "本地模型发现必须绕过 HTTP_PROXY / HTTPS_PROXY"
        return FakeOpener()

    monkeypatch.setattr(urllib.request, "build_opener", fake_build_opener)
    refreshed = service.refresh_local_models(admin)
    assert refreshed["status"] == "ready"
    assert refreshed["models"] == ["qwen2.5:7b", "llama3.2:latest"]
    assert len(calls) == 1
    request, timeout = calls[0]
    assert request.full_url == "http://127.0.0.1:11434/v1/models"
    assert request.get_method() == "GET" and request.get_header("Authorization") == "Bearer local-catalog-key"
    assert timeout == 5.0
    assert service.local_model_catalog()["models"] == refreshed["models"]


def test_local_model_catalog_falls_back_to_ollama_tags_and_keeps_cache_on_error(tmp_path, monkeypatch):
    import urllib.error
    import urllib.request

    admin = "local-model-admin-token"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    service = AssistantService(data_dir=str(tmp_path / "ollama-catalog"))
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return b'{"models":[{"name":"llama3.2:latest"},{"model":"qwen2.5:7b"}]}'

    class FakeOpener:
        def open(self, request, timeout):
            calls.append((request.full_url, timeout))
            if request.full_url.endswith("/v1/models"):
                raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, None)
            return FakeResponse()

    monkeypatch.setattr(urllib.request, "build_opener", lambda *_handlers: FakeOpener())
    refreshed = service.refresh_local_models(admin)
    assert calls == [
        ("http://127.0.0.1:11434/v1/models", 5.0),
        ("http://127.0.0.1:11434/api/tags", 5.0),
    ]
    assert refreshed["status"] == "ready" and refreshed["models"] == ["llama3.2:latest", "qwen2.5:7b"]

    monkeypatch.setattr(service, "_fetch_local_models", lambda _url: (_ for _ in ()).throw(
        AssistantError(502, "读取本地模型列表失败；请检查本地服务地址、服务状态和 API Key")))
    with pytest.raises(AssistantError, match="读取本地模型列表失败"):
        service.refresh_local_models(admin)
    after_error = service.local_model_catalog()
    assert after_error["status"] == "error"
    assert after_error["models"] == ["llama3.2:latest", "qwen2.5:7b"], "刷新失败不应清除上次候选"


def test_local_model_catalog_requires_admin_and_startup_prefetch_is_nonblocking(tmp_path, monkeypatch):
    import threading
    import time

    admin = "local-model-admin-token"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    service = AssistantService(data_dir=str(tmp_path / "startup-catalog"))
    with pytest.raises(AssistantError) as denied:
        service.refresh_local_models("wrong-token")
    assert denied.value.status_code == 403
    with pytest.raises(AssistantError) as unsafe:
        service.update_config({"local_base_url": "http://8.8.8.8/v1"}, admin)
    assert unsafe.value.status_code == 400
    with pytest.raises(TypeError):
        service.refresh_local_models(admin, "http://8.8.8.8/v1")
    with pytest.raises(AssistantError, match="本地模型名称由问答窗口"):
        service.update_config({"local_model": "manual-custom-model"}, admin)
    assert service.prepare_chat({"prompt": "默认本地模型", "model_type": "local"})["model"] == "qwen2.5:7b"
    assert service.prepare_chat({"prompt": "选择本地模型", "model_type": "local",
                                 "model_name": "startup-model"})["model"] == "startup-model"

    completed = threading.Event()
    calls = []
    def fake_fetch(base_url):
        calls.append(base_url)
        completed.set()
        return ["startup-model"]
    monkeypatch.setattr(service, "_fetch_local_models", fake_fetch)
    service.start_local_model_discovery()
    assert completed.wait(2), "启动预取线程未完成"
    deadline = time.monotonic() + 2
    while service.local_model_catalog()["status"] == "loading" and time.monotonic() < deadline:
        time.sleep(0.005)
    service.start_local_model_discovery()
    assert calls == ["http://127.0.0.1:11434/v1"]
    assert service.local_model_catalog()["status"] == "ready"
    assert service.local_model_catalog()["models"] == ["startup-model"]


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
    assert any("软件部署说明文档" == hit["name"] for hit in service.search_knowledge("Linux 离线部署 安装", 10, 0.08))


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


def test_assistant_manual_explains_admin_and_controlled_tool_setup(tmp_path):
    from app.assistant_tools import TOOL_CATALOG

    service = AssistantService(data_dir=str(tmp_path))
    docs = {doc["id"]: doc for doc in service.document_library()["documents"]}
    guide = docs["builtin-assistant-guide"]["content"]
    usage = docs["builtin-software-usage"]["content"]
    deployment = docs["builtin-software-deployment"]["content"]
    assert "ELEC_TOOL_ASSISTANT_ADMIN_TOKEN" in guide
    assert "ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS" in guide
    assert "管理员口令本身不授予工具执行权限" in guide
    assert "### 6.1 实施工程师" in guide
    assert "### 6.2 交付工程师" in guide
    assert "### 6.4 现场运维" in guide
    assert '"recordings.read","profiles.read"' in guide
    assert r".\.venv\Scripts\python.exe" in guide
    assert "Markdown 链接" in guide
    assert "operator_tokens_configured" in guide
    assert "至少有一条格式有效记录" in guide
    assert "cloud_tools_enabled=true" in guide
    assert "#### 全局工具复选框与操作员 `scopes` 的配对" in guide
    assert "全局 allow-list 保存的是工具 ID，操作员 JSON 保存的是 scope 值" in guide
    assert "操作员 `scopes[]` 必须包含的 scope" in guide
    for item in TOOL_CATALOG:
        assert f"`{item['name']}` | `{item['scope']}`" in guide

    assert "$env:OPERATOR_TOKEN = $operator" in usage
    assert "field-readonly-1" in usage
    assert "scope 必须是**原样纯文本**" in usage
    assert "当前 shell 的 `export` / PowerShell `$env:`" in deployment
    assert "operator_tokens_configured" in deployment
    assert "### 3.6 智能问答模块" in deployment


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


def test_assistant_waveform_images_are_bounded_and_sent_as_openai_vision_parts(tmp_path, monkeypatch):
    from app import assistant as assistant_module

    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_CLOUD_API_KEY", "cloud-image-test-key")
    service = AssistantService(data_dir=str(tmp_path))
    png_bytes = bytes([0x89]) + b"PNG" + bytes([0x0d, 0x0a, 0x1a, 0x0a]) + b"small waveform image bytes"
    png = {"mime_type": "image/png", "data": base64.b64encode(png_bytes).decode("ascii")}

    for backend in ("local", "cloud"):
        plan = service.prepare_chat({"prompt": "请分析波形截图", "model_type": backend, "images": [png]})
        content = plan["messages"][-1]["content"]
        assert content[0] == {"type": "text", "text": "请分析波形截图"}
        assert content[1]["type"] == "image_url"
        assert content[1]["image_url"]["url"] == "data:image/png;base64," + png["data"]

    with pytest.raises(AssistantError, match="需选择支持视觉输入"):
        service.prepare_chat({"prompt": "请分析波形截图", "model_type": "builtin", "images": [png]})
    with pytest.raises(AssistantError, match="只支持 PNG"):
        service.prepare_chat({"prompt": "说明", "model_type": "local", "images": [{"mime_type": "image/gif", "data": png["data"]}]})
    with pytest.raises(AssistantError, match="Base64"):
        service.prepare_chat({"prompt": "说明", "model_type": "local", "images": [{"mime_type": "image/png", "data": "%%%"}]})
    with pytest.raises(AssistantError, match="内容与声明"):
        service.prepare_chat({"prompt": "说明", "model_type": "local", "images": [{
            "mime_type": "image/png", "data": base64.b64encode(b"not a png").decode("ascii")
        }]})
    with pytest.raises(AssistantError, match="最多附加 3 张"):
        service.prepare_chat({"prompt": "说明", "model_type": "local", "images": [png] * 4})
    with pytest.raises(AssistantError) as oversize:
        service.prepare_chat({"prompt": "说明", "model_type": "local", "images": [{
            "mime_type": "image/png", "data": "A" * (4 * ((assistant_module.MAX_ASSISTANT_IMAGE_BYTES + 2) // 3) + 4)
        }]})
    assert oversize.value.status_code == 413
    monkeypatch.setattr(assistant_module, "MAX_ASSISTANT_IMAGE_TOTAL_BYTES", len(png_bytes))
    with pytest.raises(AssistantError, match="总大小"):
        service.prepare_chat({"prompt": "说明", "model_type": "local", "images": [png, png]})


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
        service.claim_tool_proposal(proposal["id"], "other-operator-secret-123", proposal["confirmation_code"])
    saved_tokens = json.dumps([
        {"id": "field-operator", "token": operator, "scopes": []},
        {"id": "other-operator", "token": "other-operator-secret-123", "scopes": ["data.export"]},
    ])
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", saved_tokens)
    with pytest.raises(AssistantError, match="已无该工具权限"):
        service.claim_tool_proposal(proposal["id"], operator, proposal["confirmation_code"])
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "field-operator", "token": operator, "scopes": ["config.wiring.write"]},
        {"id": "other-operator", "token": "other-operator-secret-123", "scopes": ["data.export"]},
    ]))
    service.update_config({"tools_enabled": False}, admin)
    with pytest.raises(AssistantError, match="关闭该工具"):
        service.claim_tool_proposal(proposal["id"], operator, proposal["confirmation_code"])
    service.update_config({"tools_enabled": True}, admin)
    with pytest.raises(AssistantError, match="不匹配"):
        service.claim_tool_proposal(proposal["id"], operator, "000000" if proposal["confirmation_code"] != "000000" else "000001")
    claimed = service.claim_tool_proposal(proposal["id"], operator, proposal["confirmation_code"])
    assert claimed["name"] == "set_wiring_mode" and claimed["side"] == "branch"
    with pytest.raises(AssistantError, match="不存在"):
        service.claim_tool_proposal(proposal["id"], operator, proposal["confirmation_code"])
    service.record_tool_result(claimed, "success", {"message": "updated"})

    from app import assistant as assistant_module
    old_ttl = assistant_module.PENDING_TOOL_TTL_S
    monkeypatch.setattr(assistant_module, "PENDING_TOOL_TTL_S", -1.0)
    expired = service.create_tool_proposal(plan, [{"function": {
        "name": "set_wiring_mode", "arguments": {"wiring": "3p3w"}
    }}])
    with pytest.raises(AssistantError) as expired_error:
        service.claim_tool_proposal(expired["id"], operator, expired["confirmation_code"])
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
        service.claim_tool_proposal(cloud_proposal["id"], operator, cloud_proposal["confirmation_code"])
    assert (tmp_path / "tool_audit.jsonl").exists()


def test_finite_intent_contracts_cover_all_46_tools_and_examples():
    from app.assistant_intents import TOOL_INTENT_CONTRACTS, find_tool_intent_candidates, validate_intent_catalog

    validate_intent_catalog()
    assert set(TOOL_INTENT_CONTRACTS) == set(TOOL_NAMES)
    for tool, contract in TOOL_INTENT_CONTRACTS.items():
        assert contract.intent and contract.action_terms and contract.target_terms
        assert len(contract.positive_examples) >= 2 and len(contract.negative_examples) >= 2
        assert set(contract.parameter_rules) == set(TOOL_CATALOG[[item["name"] for item in TOOL_CATALOG].index(tool)]["parameters"].get("properties", {}))
        for example in contract.positive_examples:
            candidates = find_tool_intent_candidates(example)
            assert candidates and candidates[0][0] == tool, (tool, example, candidates)
            assert len(candidates) == 1 or candidates[0][1] - candidates[1][1] >= 10, (tool, example, candidates)
        for example in contract.negative_examples:
            candidates = find_tool_intent_candidates(example)
            assert all(candidate != tool for candidate, _score in candidates), (tool, example, candidates)


def test_server_intent_gate_clarifies_ambiguity_missing_and_wrong_slots():
    from app.assistant_intents import validate_model_tool_result

    assert validate_model_tool_result(
        "将离线播放速度设置为2倍", "set_playback_speed", {"speed": 2}
    ) == {"ok": True, "arguments": {"speed": 2.0}}

    rejected = (
        ("为什么输入‘启动当前侧数据源检测’会查询设备画像？", "start_current_source", {}),
        ("不要启动当前侧数据源", "start_current_source", {}),
        ("启动数据源，然后暂停数据源", "start_current_source", {}),
        ("切换接线模式", "set_wiring_mode", {}),
        ("将离线播放速度调整快一点", "set_playback_speed", {"speed": 2}),
        ("查询电压和电流的趋势", "get_history", {"quantity": "voltage"}),
        ("查询最近24小时取20个点的电压趋势", "get_history",
         {"quantity": "voltage", "hours": 100, "max_points": 20}),
        ("把接线模式从3p3w改为3p4w", "set_wiring_mode", {"wiring": "3p3w"}),
        ("查看当前侧最新功率因数结果", "get_electrical_result", {"quantity": "power"}),
    )
    for prompt, tool, arguments in rejected:
        result = validate_model_tool_result(prompt, tool, arguments)
        assert result["ok"] is False and "暂未创建操作预览" in result["clarification"], (prompt, result)

    file_a, file_b = "a" * 24, "b" * 24
    resources = {"recordings": [
        {"file_id": file_a, "name": "capture-a.csv"},
        {"file_id": file_b, "name": "capture-b.csv"},
    ]}
    selected = validate_model_tool_result(
        "把受控录波文件capture-a.csv设为当前数据源", "select_recording_source",
        {"file_id": file_a}, resources,
    )
    assert selected == {"ok": True, "arguments": {"file_id": file_a}}
    ambiguous_resource = validate_model_tool_result(
        "把受控录波文件capture-a.csv和capture-b.csv设为当前数据源", "select_recording_source",
        {"file_id": file_a}, resources,
    )
    assert ambiguous_resource["ok"] is False and "参数" in ambiguous_resource["clarification"]


def test_intent_gate_rejections_carry_a_fixed_reason_code():
    from app.assistant_intents import validate_model_tool_result

    cases = (
        ("今天天气怎么样", "get_runtime_status", {}, "no_intent_match"),
        ("启动数据源，然后暂停数据源", "start_current_source", {}, "compound_request"),
        ("停止暂停数据源", "pause_current_source", {}, "ambiguous_intent"),
        ("切换接线模式到3p4w", "get_runtime_status", {}, "intent_mismatch"),
        ("切换接线模式到3p4w", "set_wiring_mode", "{wiring", "arguments_not_json"),
        ("切换接线模式到3p4w", "set_wiring_mode", [1], "arguments_not_object"),
        ("切换接线模式到3p4w", "set_wiring_mode", {"wiring": "3p4w", "path": "/etc/passwd"}, "unknown_argument_field"),
        ("查询电压和电流的趋势", "get_history", {"quantity": "voltage"}, "ambiguous_parameter_value"),
        ("把接线模式从3p3w改为3p4w", "set_wiring_mode", {"wiring": "3p3w"}, "parameter_not_grounded"),
        ("切换接线模式", "set_wiring_mode", {}, "missing_required_parameter"),
        ("将离线播放速度设置为1000倍", "set_playback_speed", {"speed": 1000}, "schema_validation"),
    )
    for prompt, tool, arguments, reason in cases:
        result = validate_model_tool_result(prompt, tool, arguments)
        assert result["ok"] is False and result["reason"] == reason, (prompt, result)
        assert "暂未创建操作预览" in result["clarification"]
        # 原因码只供服务端日志使用：固定词表，不带用户原话或参数值
        assert re.fullmatch(r"[a-z_]+", result["reason"])
    accepted = validate_model_tool_result("切换接线模式到3p4w", "set_wiring_mode", {"wiring": "3p4w"})
    assert accepted == {"ok": True, "arguments": {"wiring": "3p4w"}}


def test_normalised_tool_arguments_pass_validation_again_unchanged():
    # 门控把核验后的参数交给 create_tool_proposal，后者会再校验一次；归一化后的结果必须能原样通过。
    samples = (
        ("set_playback_speed", {"speed": 2}, {"speed": 2.0}),
        ("set_harmonic_parameters", {"order_max": 50.0, "include_interharmonic": True},
         {"order_max": 50, "include_interharmonic": True}),
        ("derive_profile_stages", {"profile_id": "0123456789abcdef", "scales": [1, 2], "q_mode": "const"},
         {"profile_id": "0123456789abcdef", "scales": [1.0, 2.0], "q_mode": "const"}),
        ("get_history", {"quantity": "voltage", "hours": 24, "max_points": 20},
         {"quantity": "voltage", "hours": 24.0, "max_points": 20}),
        ("set_wiring_mode", {"wiring": "3p4w"}, {"wiring": "3p4w"}),
        # 这三个工具的 schema 没有 side：模型多传的 side 被忽略，其余工具照常拒绝未注册字段
        ("list_recordings", {"folder": "data", "side": "branch"}, {"folder": "data"}),
        ("get_runtime_status", {"side": "bus"}, {}),
        ("get_runtime_settings", {"side": "分路侧"}, {}),
    )
    for name, arguments, normalised in samples:
        assert validate_tool_arguments(name, arguments) == normalised, name
        assert validate_tool_arguments(name, normalised) == normalised, name
        assert validate_tool_arguments(name, json.dumps(normalised)) == normalised, name
    with pytest.raises(ValueError, match="未注册字段"):
        validate_tool_arguments("get_event_list", {"side": "bus"})


def test_model_tool_gate_checks_this_turns_message_not_the_history(tmp_path, monkeypatch):
    import threading

    service, operator = _tool_gate_service(tmp_path, monkeypatch, ["set_wiring_mode"], ["config.wiring.write"])
    call = _tool_call("set_wiring_mode", {"wiring": "3p4w"})
    monkeypatch.setattr(service, "_open_request", _fake_model_reply(
        {"content": "", "tool_calls": [call]}, [{"tool_calls": [call]}]))

    # 上一轮说过要切换接线，本轮只说“好的”：本轮原话里没有操作意图，不创建预览。
    payload = {"prompt": "好的", "model_type": "local", "history": [
        {"role": "user", "content": "切换接线模式到3p4w"}, {"role": "assistant", "content": "请确认。"}]}
    plan = service.prepare_chat(dict(payload), operator_token=operator)
    assert [message["role"] for message in plan["messages"]] == ["system", "user", "assistant", "user"]
    assert "暂未创建操作预览" in service.complete(plan)
    assert plan.get("_tool_proposal") is None and plan["_tool_clarification"]
    stream_plan = service.prepare_chat(dict(payload), operator_token=operator)
    tokens = list(service.stream(stream_plan, threading.Event()))
    assert len(tokens) == 1 and "暂未创建操作预览" in tokens[0]
    assert stream_plan.get("_tool_proposal") is None and stream_plan["_tool_clarification"]
    assert not service._pending_tools

    # 本轮明确提出操作，历史里是别的话题：按本轮原话创建预览。
    payload = {"prompt": "切换接线模式到3p4w", "model_type": "local", "history": [
        {"role": "user", "content": "列出data目录里的可用录波文件"}, {"role": "assistant", "content": "好的。"}]}
    plan = service.prepare_chat(dict(payload), operator_token=operator)
    assert "请核对操作摘要" in service.complete(plan)
    assert plan["_tool_proposal"]["arguments"] == {"wiring": "3p4w"} and not plan.get("_tool_clarification")
    stream_plan = service.prepare_chat(dict(payload), operator_token=operator)
    assert "请核对操作摘要" in "".join(service.stream(stream_plan, threading.Event()))
    assert stream_plan["_tool_proposal"]["tool"] == "set_wiring_mode"
    assert len(service._pending_tools) == 2


def test_model_tool_gate_handles_several_calls_unlisted_tools_and_a_stray_side_argument(tmp_path, monkeypatch):
    import queue
    import threading

    from app.assistant import run_stream_to_queue

    service, operator = _tool_gate_service(tmp_path, monkeypatch,
                                           ["set_wiring_mode", "get_runtime_status", "list_recordings"],
                                           ["config.wiring.write", "state.read", "recordings.read"])

    def ask(prompt):
        return service.prepare_chat({"prompt": prompt, "model_type": "local"}, operator_token=operator)

    def sse_frames(plan):
        out, cancel = queue.Queue(), threading.Event()
        service.acquire_request("tool-gate-test")  # run_stream_to_queue 结束时归还这个名额
        run_stream_to_queue(service, plan, out, cancel)
        frames = []
        while True:
            item = out.get_nowait()
            if item is None:
                return frames
            frames.append(item)

    # 模型一次提出两个工具调用：不创建任何预览，返回澄清；模型的话不外发。
    calls = [_tool_call("set_wiring_mode", {"wiring": "3p4w"}), _tool_call("get_runtime_status", {}, index=1)]
    monkeypatch.setattr(service, "_open_request", _fake_model_reply(
        {"content": "两项都已完成。", "tool_calls": calls},
        [{"content": "两项都已完成。"}, {"tool_calls": calls[:1]}, {"tool_calls": calls[1:]}]))
    plan = ask("切换接线模式到3p4w")
    answer = service.complete(plan)
    assert "一次只能处理一个受控动作" in answer and "两项都已完成" not in answer
    assert plan.get("_tool_proposal") is None and plan["_tool_clarification"] == answer
    plan = ask("切换接线模式到3p4w")
    frames = sse_frames(plan)
    assert [frame["type"] for frame in frames] == ["sources", "delta", "clarification", "done"]
    assert frames[1]["text"] == answer and frames[2]["message"] == answer
    assert not service._pending_tools

    # 工具名为空、未注册，或已注册但不在本轮授权清单中：按未授权拒绝（403），不是澄清。
    for name in ("", "run_shell", "start_current_source"):
        call = _tool_call(name, {})
        monkeypatch.setattr(service, "_open_request", _fake_model_reply(
            {"content": "已完成。", "tool_calls": [call]}, [{"content": "已完成。"}, {"tool_calls": [call]}]))
        plan = ask("切换接线模式到3p4w")
        with pytest.raises(AssistantError, match="未在本轮授权清单中") as blocked:
            service.complete(plan)
        assert blocked.value.status_code == 403
        assert plan.get("_tool_proposal") is None and not plan.get("_tool_clarification")
        frames = sse_frames(ask("切换接线模式到3p4w"))
        assert [frame["type"] for frame in frames] == ["sources", "error"], (name, frames)
        assert "未在本轮授权清单中" in frames[1]["error"]
    assert not service._pending_tools

    # list_recordings 的 schema 没有 side；模型多传的 side 被忽略（与 validate_tool_arguments 一致），
    # 不因此返回澄清。其余未注册字段仍然返回澄清。
    call = _tool_call("list_recordings", {"folder": "data", "side": "branch"})
    monkeypatch.setattr(service, "_open_request", _fake_model_reply({"content": "", "tool_calls": [call]}))
    plan = ask("列出data目录里的可用录波文件")
    assert "请核对操作摘要" in service.complete(plan)
    assert plan["_tool_proposal"]["tool"] == "list_recordings"
    assert plan["_tool_proposal"]["arguments"] == {"folder": "data"}
    call = _tool_call("list_recordings", {"folder": "data", "path": "/etc"})
    monkeypatch.setattr(service, "_open_request", _fake_model_reply({"content": "", "tool_calls": [call]}))
    plan = ask("列出data目录里的可用录波文件")
    assert "参数超出该操作允许范围" in service.complete(plan)
    assert plan.get("_tool_proposal") is None and plan["_tool_clarification"]
    assert len(service._pending_tools) == 1


def test_model_text_is_replaced_for_accepted_tool_calls_and_held_until_the_model_finishes(tmp_path, monkeypatch):
    import threading

    service, operator = _tool_gate_service(tmp_path, monkeypatch, ["set_wiring_mode"], ["config.wiring.write"])
    call = _tool_call("set_wiring_mode", {"wiring": "3p4w"})
    monkeypatch.setattr(service, "_open_request", _fake_model_reply(
        {"content": "操作已经完成。", "tool_calls": [call]},
        [{"content": "操作已经完成。"}, {"tool_calls": [call]}]))
    payload = {"prompt": "切换接线模式到3p4w", "model_type": "local"}

    # 工具调用通过门控：回答只有服务端写的预览提示。模型说的“操作已经完成”不显示——确认前什么都没有执行。
    plan = service.prepare_chat(dict(payload), operator_token=operator)
    answer = service.complete(plan)
    assert answer == "已识别为「切换当前侧接线模式」。请核对操作摘要与影响，再确认执行。"
    assert plan["_tool_proposal"]["tool"] == "set_wiring_mode" and not plan.get("_tool_clarification")
    stream_plan = service.prepare_chat(dict(payload), operator_token=operator)
    assert list(service.stream(stream_plan, threading.Event())) == [answer]
    assert stream_plan["_tool_proposal"]["arguments"] == {"wiring": "3p4w"}
    assert len(service._pending_tools) == 2

    # 向模型提供了工具、模型只回文字：文字等模型输出结束后才放出，分片与顺序不变。
    progress = []
    monkeypatch.setattr(service, "_open_request", _fake_model_reply(
        deltas=[{"content": "画像"}, {"content": "匹配是……"}],
        on_stream_end=lambda: progress.append("model finished")))
    question = {"prompt": "介绍一下画像匹配的原理", "model_type": "local"}
    text_plan = service.prepare_chat(dict(question), operator_token=operator)
    assert text_plan["tools"]
    tokens = service.stream(text_plan, threading.Event())
    assert next(tokens) == "画像" and progress == ["model finished"]
    assert list(tokens) == ["匹配是……"]
    assert text_plan.get("_tool_proposal") is None and not text_plan.get("_tool_clarification")

    # 没有向模型提供工具（未带操作员令牌）：无需等待，文字照旧边到边发。
    progress.clear()
    plain_plan = service.prepare_chat(dict(question))
    assert not plain_plan.get("tools")
    tokens = service.stream(plain_plan, threading.Event())
    assert next(tokens) == "画像" and progress == []
    assert list(tokens) == ["匹配是……"] and progress == ["model finished"]


def test_model_tool_calls_are_gated_and_stream_text_is_buffered_until_validation(tmp_path, monkeypatch):
    import threading

    admin = "intent-gate-admin-token"
    operator = "intent-gate-operator-token-secret"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "intent-operator", "token": operator, "scopes": ["config.wiring.write", "state.read"]},
    ]))
    service = AssistantService(data_dir=str(tmp_path))
    service.update_config({"tools_enabled": True,
                           "enabled_tools": ["set_wiring_mode", "get_runtime_status"]}, admin)
    prompt = "切换接线模式到3p4w"

    class FakeCompletionResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, _limit):
            return json.dumps({"choices": [{"message": {
                "content": "操作已经完成。", "tool_calls": [{"id": "call-1", "type": "function",
                    "function": {"name": "get_runtime_status", "arguments": "{}"}}]}}]}).encode("utf-8")

    monkeypatch.setattr(service, "_open_request", lambda _plan, stream: FakeCompletionResponse())
    plan = service.prepare_chat({"prompt": prompt, "model_type": "local"}, operator_token=operator)
    answer = service.complete(plan)
    assert "暂未创建操作预览" in answer
    assert "操作已经完成" not in answer
    assert plan.get("_tool_proposal") is None and plan.get("_tool_clarification")
    assert not service._pending_tools

    class FakeStreamResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def __iter__(self):
            yield 'data: {"choices":[{"delta":{"content":"操作已经完成。"}}]}\n'.encode("utf-8")
            yield 'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call-2","function":{"name":"get_runtime_status","arguments":"{}"}}]}}]}\n'.encode("utf-8")
            yield b'data: [DONE]\n'

    monkeypatch.setattr(service, "_open_request", lambda _plan, stream: FakeStreamResponse())
    stream_plan = service.prepare_chat({"prompt": prompt, "model_type": "local"}, operator_token=operator)
    tokens = list(service.stream(stream_plan, threading.Event()))
    assert len(tokens) == 1 and "暂未创建操作预览" in tokens[0]
    assert "操作已经完成" not in "".join(tokens)
    assert stream_plan.get("_tool_proposal") is None and stream_plan.get("_tool_clarification")
    assert not service._pending_tools


def test_exact_catalog_titles_route_every_empty_argument_tool_deterministically():
    from app.assistant_tools import TOOL_BY_NAME

    eligible = []
    for item in TOOL_CATALOG:
        try:
            validate_tool_arguments(item["name"], {})
        except ValueError:
            continue
        eligible.append(item["name"])
        assert _explicit_tool_command(item["title"]) == item["name"]

    assert eligible
    assert _explicit_tool_command("启动当前侧数据源检测，不要查询或更换录波文件") == "start_current_source"
    assert _explicit_tool_command("请启动当前离线数据源播放") == "start_current_source"
    reported_phrases = (
        ("播放离线数据源CSV文件", True),
        ("播放离线数据源", True),
        ("播放数据源", False),
        ("启动离线数据源CSV文件", True),
        ("播放数据源与控制中的离线数据源CSV文件", True),
        ("启动数据源与控制中的离线数据源CSV文件", True),
    )
    for prompt, is_offline in reported_phrases:
        assert _explicit_tool_command(prompt) == "start_current_source", prompt
        assert _explicit_offline_source_start(prompt) is is_offline, prompt
    assert _explicit_tool_command("将离线播放速度设置为 2 倍") is None
    assert _explicit_tool_command("为什么输入‘启动当前侧数据源检测’会查询设备画像？") is None
    assert _explicit_tool_command("启动当前侧数据源检测，然后告诉我为什么") is None
    assert TOOL_BY_NAME["start_current_source"]["scope"] == "engine.start"


def test_explicit_source_start_bypasses_model_selection_but_keeps_confirmation(tmp_path, monkeypatch):
    import threading

    admin = "explicit-route-admin-token"
    operator = "explicit-route-operator-secret"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "field-operator", "token": operator, "scopes": ["engine.start"]},
    ]))
    service = AssistantService(data_dir=str(tmp_path))
    service.update_config({
        "tools_enabled": True,
        "enabled_tools": ["start_current_source", "list_recordings", "list_profiles"],
    }, admin)
    monkeypatch.setattr(service, "_open_request", lambda *args, **kwargs: pytest.fail("direct command must not call the model"))

    reported_phrases = (
        "播放离线数据源CSV文件",
        "播放离线数据源",
        "播放数据源",
        "启动离线数据源CSV文件",
        "播放数据源与控制中的离线数据源CSV文件",
        "启动数据源与控制中的离线数据源CSV文件",
    )
    plans = [service.prepare_chat({
        "prompt": prompt,
        "model_type": "local",
        "model_name": "qwen3:8b",
        "rag_enabled": False,
    }, operator_token=operator, side="branch", tool_context={
        "side": "branch",
        "source": {"kind": "csv_file", "name": "", "has_path": True, "running": False},
    }) for prompt in reported_phrases]

    assert len(service._pending_tools) == len(reported_phrases)
    assert all(plan["_available_tools"] == ["start_current_source"] for plan in plans)
    assert all(plan["_tool_proposal"]["tool"] == "start_current_source" for plan in plans)
    assert all(plan["_tool_proposal"]["side"] == "branch" for plan in plans)
    assert all(plan["_tool_proposal"]["requires_second_confirmation"] is True for plan in plans)
    plan = plans[-1]
    proposal = plan["_tool_proposal"]
    assert proposal["title"] == "启动当前侧数据源检测"
    assert proposal["confirmation_code"]
    assert "不会执行" in service.complete(plan)
    assert "启动分路侧数据源检测" in "".join(service.stream(plan, threading.Event()))

    incorrect_code = "000001" if proposal["confirmation_code"] != "000001" else "000002"
    with pytest.raises(AssistantError, match="二次确认码不匹配"):
        service.claim_tool_proposal(proposal["id"], operator, incorrect_code)


def test_offline_source_playback_diagnostics_log_route_and_rejected_tool_without_values(tmp_path, monkeypatch, caplog):
    import logging

    admin = "route-diagnostic-admin-secret"
    operator = "route-diagnostic-operator-secret"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "diagnostic-operator", "token": operator,
         "scopes": ["engine.start", "config.source.write"]},
    ]))
    service = AssistantService(data_dir=str(tmp_path))
    service.update_config({"tools_enabled": True,
                           "enabled_tools": ["start_current_source", "set_playback_speed"]}, admin)
    caplog.set_level(logging.INFO, logger="elec_tool.assistant")
    prompt = "播放离线数据源"
    plan = service.prepare_chat({"prompt": prompt, "model_type": "local"},
                                operator_token=operator, tool_context={
                                    "source": {"kind": "csv_file", "has_path": True, "running": False},
                                })
    assert plan["_tool_proposal"]["tool"] == "start_current_source"
    trace_id = plan["_trace_id"]
    assert len(trace_id) == 16 and all(char in "0123456789abcdef" for char in trace_id)

    rejected_plan = dict(plan)
    rejected_plan["_tool_call_origin"] = "model"
    result = service._accept_tool_calls(rejected_plan, [{
        "function": {"name": "set_playback_speed", "arguments": {"speed": 2}},
    }])
    assert result is None and rejected_plan.get("_tool_proposal") is None
    assert rejected_plan.get("_tool_clarification")

    records = caplog.text
    assert "assistant_route_diagnostic" in records and "decision=deterministic_direct" in records
    assert "direct_tool=start_current_source" in records and f"trace_id={trace_id}" in records
    assert "assistant_tool_candidate" in records and "candidate=set_playback_speed" in records
    assert "intent_candidates=start_current_source:47" in records
    assert "outcome=clarification reason=intent_mismatch" in records
    assert "argument_fields=speed" in records
    assert prompt not in records and admin not in records and operator not in records
    assert "speed=2" not in records and "Authorization" not in records and "api_key" not in records.lower()


def test_route_and_gate_logs_follow_the_request_trace_id_and_carry_no_user_text_or_values(tmp_path, monkeypatch, caplog):
    import logging

    service, operator = _tool_gate_service(
        tmp_path, monkeypatch,
        ["set_wiring_mode", "get_event_list", "start_current_source"],
        ["config.wiring.write", "events.read", "engine.start"])
    admin = "tool-gate-admin-token"
    caplog.set_level(logging.INFO, logger="elec_tool.assistant")
    seen = []

    def logged():
        """Return the log text written since the last call, and keep it for the final leak check."""
        text = caplog.text
        seen.append(text)
        caplog.clear()
        return text

    prompt = "切换接线模式到3p4w"
    call = _tool_call("set_wiring_mode", {"wiring": "3p4w"})
    monkeypatch.setattr(service, "_open_request", _fake_model_reply({"content": "好。", "tool_calls": [call]}))

    # /api/assistant/chat 生成请求号并放进 payload；日志沿用它，才能和响应头 X-Assistant-Trace-ID 对上。
    plan = service.prepare_chat({"prompt": prompt, "model_type": "local", "_assistant_trace_id": "0123456789abcdef"},
                                operator_token=operator)
    assert plan["_trace_id"] == "0123456789abcdef" and plan["_tool_call_origin"] == "model"
    service.complete(plan)
    records = logged()
    assert "assistant_route_decision trace_id=0123456789abcdef" in records
    assert "decision=model_fallback" in records and "intent_tier=high" in records
    assert "assistant_tool_candidate trace_id=0123456789abcdef origin=model candidate=set_wiring_mode" in records
    assert "argument_fields=wiring" in records
    assert ("assistant_tool_decision trace_id=0123456789abcdef origin=model "
            "outcome=proposal_created tool=set_wiring_mode") in records

    # 格式不对的请求号不采用，由服务端另行生成。
    for bad in ("0123456789ABCDEF", "abc", "0123456789abcdef0", "../../etc/passwd\n", 12345):
        other = service.prepare_chat({"prompt": prompt, "model_type": "local", "_assistant_trace_id": bad},
                                     operator_token=operator)["_trace_id"]
        assert re.fullmatch(r"[0-9a-f]{16}", other) and other != "0123456789abcdef"
    assert "passwd" not in logged()

    # 其余路由结果各有固定的 decision 值。
    png_bytes = bytes([0x89]) + b"PNG" + bytes([0x0d, 0x0a, 0x1a, 0x0a]) + b"small waveform image bytes"
    service.prepare_chat({"prompt": prompt, "model_type": "local", "images": [
        {"mime_type": "image/png", "data": base64.b64encode(png_bytes).decode("ascii")}]}, operator_token=operator)
    records = logged()
    assert "decision=images_attached" in records and "image_count=1" in records
    service.prepare_chat({"prompt": prompt, "model_type": "builtin"}, operator_token=operator)
    records = logged()
    assert "decision=backend_not_tool_capable" in records and "backend=builtin" in records
    intent_plan = service.prepare_chat({"prompt": "列出当前电能质量事件", "model_type": "local"},
                                       operator_token=operator, side="branch")
    records = logged()
    assert intent_plan["_tool_call_origin"] == "intent" and intent_plan["_tool_proposal"]["tool"] == "get_event_list"
    assert "decision=intent_direct direct_tool=get_event_list intent_tier=high" in records
    assert "side=branch target_side=branch" in records
    assert f"assistant_tool_decision trace_id={intent_plan['_trace_id']} origin=intent outcome=proposal_created" in records
    direct_plan = service.prepare_chat({"prompt": "启动分路侧数据源", "model_type": "local"}, operator_token=operator,
                                       side="bus", tool_context={"source": {"kind": "simulator", "running": False}})
    records = logged()
    assert direct_plan["_tool_call_origin"] == "deterministic"
    assert "decision=deterministic_direct direct_tool=start_current_source" in records
    assert "side=bus target_side=branch" in records and "source_kind=simulator" in records
    assert (f"assistant_tool_decision trace_id={direct_plan['_trace_id']} origin=deterministic "
            "outcome=proposal_created tool=start_current_source") in records

    # 直达路由拒绝请求时写明所在路由和原因码；来源类型只落固定词表，不落路径或文件名。
    with pytest.raises(AssistantError, match="不会重复启动"):
        service.prepare_chat({"prompt": "启动当前侧数据源检测", "model_type": "local"}, operator_token=operator,
                             tool_context={"source": {"kind": "csv_file", "running": True, "has_path": True,
                                                      "path": "/private/absolute/secret_recording.csv"}})
    records = logged()
    assert "assistant_route_blocked" in records
    assert "route=deterministic reason=source_already_running tool=start_current_source" in records
    assert "source_kind=csv_file" in records
    with pytest.raises(AssistantError, match="系统不支持延时执行"):
        service.prepare_chat({"prompt": "15秒过后启动当前侧数据源检测", "model_type": "local"}, operator_token=operator,
                             tool_context={"source": {"kind": "weird-kind", "running": False}})
    records = logged()
    assert "reason=delayed_execution_unsupported" in records and "source_kind=other" in records
    with pytest.raises(AssistantError, match="系统不支持延时执行"):
        service.prepare_chat({"prompt": "5分钟后列出当前电能质量事件", "model_type": "local"}, operator_token=operator)
    assert "route=intent reason=delayed_execution_unsupported tool=get_event_list" in logged()
    service.update_config({"enabled_tools": ["set_wiring_mode", "get_event_list"]}, admin)
    with pytest.raises(AssistantError, match="allow-list 未包含该工具"):
        service.prepare_chat({"prompt": "启动当前侧数据源检测", "model_type": "local"}, operator_token=operator,
                             tool_context={"source": {"kind": "simulator", "running": False}})
    records = logged()
    assert "reason=tool_unavailable tool=start_current_source" in records
    assert "operator_authenticated=True" in records and "tools_enabled=True" in records
    assert "allowlisted=False" in records and "scope_granted=True" in records

    # 模型只回文字、或什么都没回，也各有一条结果日志。
    monkeypatch.setattr(service, "_open_request", _fake_model_reply({"content": "画像匹配是……"}))
    text_plan = service.prepare_chat({"prompt": "介绍一下画像匹配的原理", "model_type": "local"}, operator_token=operator)
    service.complete(text_plan)
    assert f"assistant_model_result trace_id={text_plan['_trace_id']} outcome=plain_text" in logged()
    monkeypatch.setattr(service, "_open_request", _fake_model_reply({"content": ""}))
    with pytest.raises(AssistantError, match="空回答"):
        service.complete(text_plan)
    assert f"assistant_model_result trace_id={text_plan['_trace_id']} outcome=empty" in logged()

    # 以上全部日志里都没有问题原文、参数值、令牌或文件路径。
    everything = "".join(seen)
    assert everything.count("assistant_route_") >= 12
    for secret in (prompt, "3p4w", "列出当前电能质量事件", "介绍一下画像匹配", "5分钟后", "15秒过后", operator, admin,
                   "secret_recording", "/private/absolute", "weird-kind", "Authorization"):
        assert secret not in everything, secret
    assert "api_key" not in everything.lower()


def test_model_request_log_has_metadata_only(tmp_path, monkeypatch, caplog):
    import logging
    import urllib.request

    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_LOCAL_API_KEY", "local-request-log-key")
    service, operator = _tool_gate_service(tmp_path, monkeypatch, ["set_wiring_mode"], ["config.wiring.write"])

    class FakeOpener:
        def open(self, request, timeout):
            return object()

    monkeypatch.setattr(urllib.request, "build_opener", lambda *args: FakeOpener())
    caplog.set_level(logging.INFO, logger="elec_tool.assistant")
    plan = service.prepare_chat({"prompt": "切换接线模式到3p4w", "model_type": "local"}, operator_token=operator)
    caplog.clear()
    service._open_request(plan, stream=True)
    assert (f"assistant_model_request trace_id={plan['_trace_id']} backend=local stream=True "
            "tool_count=1 tool_choice=auto") in caplog.text
    plain = service.prepare_chat({"prompt": "解释画像匹配", "model_type": "local"})
    caplog.clear()
    service._open_request(plain, stream=False)
    assert "backend=local stream=False tool_count=0 tool_choice=none" in caplog.text
    for secret in ("local-request-log-key", plan["base_url"], plan["model"], "切换接线模式", "解释画像匹配", operator):
        assert secret not in caplog.text, secret


def test_explicit_source_start_does_not_fall_back_when_authorization_is_missing(tmp_path, monkeypatch):
    admin = "explicit-denied-admin-token"
    operator = "explicit-readonly-operator-secret"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "read-only", "token": operator, "scopes": ["recordings.read", "profiles.read"]},
    ]))
    service = AssistantService(data_dir=str(tmp_path))
    service.update_config({
        "tools_enabled": True,
        "enabled_tools": ["start_current_source", "list_recordings", "list_profiles"],
    }, admin)
    available = service.operator_tools(service.authenticate_operator(operator), "local")
    assert "start_current_source" not in available
    assert "list_recordings" in available and "list_profiles" in available
    ordinary_plan = service.prepare_chat({
        "prompt": "请说明当前可用的受控查询工具",
        "model_type": "local",
        "model_name": "qwen3:8b",
    }, operator_token=operator, tool_context={
        "source": {"kind": "csv_file", "has_path": True, "running": False},
    })
    offered = {tool["function"]["name"] for tool in ordinary_plan["tools"]}
    assert offered == set(available)
    assert "start_current_source" not in offered

    reported_phrases = (
        "播放离线数据源CSV文件", "播放离线数据源", "播放数据源",
        "启动离线数据源CSV文件", "播放数据源与控制中的离线数据源CSV文件",
        "启动数据源与控制中的离线数据源CSV文件",
    )
    for prompt in reported_phrases:
        with pytest.raises(AssistantError) as denied:
            service.prepare_chat({
                "prompt": prompt,
                "model_type": "local",
                "model_name": "qwen3:8b",
            }, operator_token=operator, tool_context={
                "source": {"kind": "csv_file", "has_path": True, "running": False},
            })
        assert denied.value.status_code == 403
        assert "engine.start" in denied.value.message
        assert "操作员令牌缺少精确 scope" in denied.value.message
        assert "不会改用相似查询工具代替" in denied.value.message

    # Now grant the operator's start scope but remove the tool from the admin allow-list.
    start_operator = "explicit-start-allowlist-operator"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "start-operator", "token": start_operator, "scopes": ["engine.start"]},
    ]))
    service.update_config({"enabled_tools": ["list_recordings", "list_profiles"]}, admin)
    with pytest.raises(AssistantError) as allowlist_denied:
        service.prepare_chat({
            "prompt": "启动当前侧数据源检测，不要查询或更换录波文件",
            "model_type": "local",
            "model_name": "qwen3:8b",
        }, operator_token=start_operator, tool_context={
            "source": {"kind": "csv_file", "has_path": True, "running": False},
        })
    assert allowlist_denied.value.status_code == 403
    assert "管理员 allow-list 未包含该工具" in allowlist_denied.value.message
    assert "操作员令牌缺少精确 scope" not in allowlist_denied.value.message
    assert not service._pending_tools


def test_explicit_source_start_rejects_running_or_unconfigured_source(tmp_path, monkeypatch):
    admin = "explicit-source-state-admin"
    operator = "explicit-source-state-operator"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "field-operator", "token": operator, "scopes": ["engine.start"]},
    ]))
    service = AssistantService(data_dir=str(tmp_path))
    service.update_config({"tools_enabled": True, "enabled_tools": ["start_current_source"]}, admin)
    payload = {"prompt": "启动当前侧数据源检测", "model_type": "local", "model_name": "qwen3:8b"}

    for source, expected in (({"kind": "csv_file", "has_path": True, "running": True}, "不会重复启动"),
                             ({"kind": "csv_file", "has_path": False, "running": False}, "未配置可用文件"),
                             ({"kind": "", "has_path": False, "running": False}, "没有可用的数据源配置")):
        with pytest.raises(AssistantError, match=expected) as blocked:
            service.prepare_chat(payload, operator_token=operator, tool_context={"source": source})
        if expected != "不会重复启动":
            assert "数据源与控制" in blocked.value.message
            assert "后重试" in blocked.value.message
    offline_prompts = (
        "播放离线数据源CSV文件", "播放离线数据源", "启动离线数据源CSV文件",
        "播放数据源与控制中的离线数据源CSV文件",
        "启动数据源与控制中的离线数据源CSV文件",
        "启动当前离线数据源播放",
    )
    for prompt in offline_prompts:
        offline_payload = {**payload, "prompt": prompt}
        with pytest.raises(AssistantError, match="不是离线文件数据源") as blocked:
            service.prepare_chat(offline_payload, operator_token=operator,
                                 tool_context={"source": {"kind": "simulator", "has_path": False, "running": False}})
        assert "数据源与控制" in blocked.value.message
        assert "不会自动切换当前来源" in blocked.value.message
    generic_plan = service.prepare_chat({**payload, "prompt": "播放数据源"}, operator_token=operator,
                                        tool_context={"source": {"kind": "simulator", "has_path": False, "running": False}})
    assert generic_plan["_tool_proposal"]["tool"] == "start_current_source"
    assert not service._pending_tools or all(item["name"] == "start_current_source"
                                             for item in service._pending_tools.values())


def test_offline_source_playback_regression_corpus(tmp_path, monkeypatch):
    """回归语料：离线数据源启动意图的确定性路由边界，覆盖正/负/易混淆/复合/状态五类。"""
    from app.assistant import _explicit_tool_command, _explicit_offline_source_start

    # ---- 1. 正例：礼貌表达、口语表达、不同语序、省略、UI 位置词 ----
    positive = (
        # 礼貌表达
        "请帮我播放离线数据源",
        "麻烦启动当前侧数据源检测",
        "请开始离线数据源CSV文件",
        # 口语表达
        "马上开始离线数据源",
        "立即播放离线数据源CSV文件",
        # 不同语序（动词开头的变体）
        "播放当前侧离线数据源",
        # 省略（含“离线”的核心表达）
        "播放离线数据源",
        # UI 位置词
        "播放数据源与控制中的离线数据源CSV文件",
        "启动数据源与控制中的离线数据源CSV文件",
    )
    for prompt in positive:
        name = _explicit_tool_command(prompt)
        assert name == "start_current_source", f"正例未命中: {prompt!r} -> {name}"
    # 明确含“离线”的标记为离线启动；省略“离线”的通用表达不标记为离线
    assert _explicit_offline_source_start("播放离线数据源") is True
    assert _explicit_offline_source_start("播放数据源") is False

    # ---- 2. 负例：疑问句、否定句、过去时陈述、引用命令 ----
    negative = (
        # 疑问句
        "能否播放离线数据源？",
        "为什么播放离线数据源会启动？",
        # 否定句
        "不要播放离线数据源",
        "不需要启动当前侧数据源",
        # 过去时陈述
        "已经播放过离线数据源了",
        "已启动了当前侧数据源",
        # 引用命令（非本轮执行意图）
        "系统说明里说“播放离线数据源”会启动数据源",
    )
    for prompt in negative:
        assert _explicit_tool_command(prompt) is None, f"负例不应命中: {prompt!r}"

    # ---- 3. 易混淆例：启动 vs 调速、选择文件 vs 播放当前文件 ----
    assert _explicit_tool_command("将离线播放速度设置为 2 倍") is None
    assert _explicit_tool_command("把离线数据源速度调快一点") is None
    assert _explicit_tool_command("选择录波文件 capture-a.csv") is None
    assert _explicit_tool_command("把受控录波文件设为当前数据源") is None

    # ---- 4. 复合例：同时要求启动和调速（含速度意图，不应直接路由） ----
    compound = (
        "启动离线数据源并把速度调成2倍",
        "播放离线数据源，速度设为1.5倍",
        "开始播放离线数据源且倍速设为 2",
    )
    for prompt in compound:
        assert _explicit_tool_command(prompt) is None, f"复合例不应直接路由: {prompt!r}"

    # ---- 5. 状态例：通过 prepare_chat 验证服务端前置条件 ----
    admin = "regression-admin"
    operator = "regression-operator"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "regression-operator", "token": operator, "scopes": ["engine.start"]},
    ]))
    service = AssistantService(data_dir=str(tmp_path))
    service.update_config({"tools_enabled": True, "enabled_tools": ["start_current_source"]}, admin)

    base_payload = {"prompt": "播放离线数据源", "model_type": "local", "model_name": "qwen3:8b"}

    # 5.1 无来源
    with pytest.raises(AssistantError, match="没有可用的数据源配置"):
        service.prepare_chat(base_payload, operator_token=operator, tool_context={"source": {}})

    # 5.2 来源已运行
    with pytest.raises(AssistantError, match="不会重复启动"):
        service.prepare_chat(base_payload, operator_token=operator,
                             tool_context={"source": {"kind": "csv_file", "has_path": True, "running": True}})

    # 5.3 非离线来源（simulator/tcp）
    with pytest.raises(AssistantError, match="不是离线文件数据源"):
        service.prepare_chat(base_payload, operator_token=operator,
                             tool_context={"source": {"kind": "simulator", "has_path": False, "running": False}})

    # 5.4 文件不可用（离线来源但无路径）
    with pytest.raises(AssistantError, match="未配置可用文件"):
        service.prepare_chat(base_payload, operator_token=operator,
                             tool_context={"source": {"kind": "csv_file", "has_path": False, "running": False}})

    # 5.5 缺少 scope（engine.start） -> 403，不回退到调速或查询工具
    readonly_operator = "regression-readonly"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "regression-readonly", "token": readonly_operator, "scopes": ["recordings.read"]},
    ]))
    with pytest.raises(AssistantError, match="engine.start"):
        service.prepare_chat(base_payload, operator_token=readonly_operator,
                             tool_context={"source": {"kind": "csv_file", "has_path": True, "running": False}})

    # 5.6 状态正常时应直接命中确定性路由，不调用模型
    monkeypatch.setattr(service, "_open_request", lambda *args, **kwargs: pytest.fail("direct route must not call model"))
    service.update_config({"enabled_tools": ["start_current_source"]}, admin)
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "regression-operator", "token": operator, "scopes": ["engine.start"]},
    ]))
    plan = service.prepare_chat(base_payload, operator_token=operator,
                                tool_context={"source": {"kind": "csv_file", "has_path": True, "running": False}})
    assert plan["_tool_proposal"]["tool"] == "start_current_source"
    assert plan["_tool_call_origin"] == "deterministic"


def test_offline_source_stop_resume_pause_regression_corpus(tmp_path, monkeypatch):
    """回归语料：离线数据源停止/暂停/恢复意图的确定性路由边界。

    覆盖五类语料：
    1. 正例：礼貌表达、口语表达、不同语序、省略、UI 位置词
    2. 负例：疑问句、否定句、过去时陈述、引用命令
    3. 易混淆例：启动 vs 停止、暂停 vs 恢复、选择文件 vs 停止当前文件
    4. 复合例：同时要求停止和调速/启动等
    5. 状态例：无来源、来源已运行、非离线来源、文件不可用、缺少 scope
    """
    from app.assistant import _explicit_tool_command

    # ---- 1. 正例：stop / pause / resume ----
    stop_positive = (
        # 礼貌表达
        "请帮我停止当前侧数据源",
        "麻烦停止当前侧离线数据源",
        # 口语表达（修饰语）
        "马上停止当前侧离线数据源",
        "立即停止当前侧离线播放",
        "先结束当前侧源",
        # 不同语序 / 表达
        "停止当前侧离线数据源",
        "停止当前离线数据源",
        "停止当前侧来源",
        "停止当前侧源",
        "停止当前侧离线播放",
        # UI 位置词
        "停止数据源与控制中的离线数据源",
        "关闭当前侧数据源",
    )
    for prompt in stop_positive:
        assert _explicit_tool_command(prompt) == "stop_current_source", f"stop 正例未命中: {prompt!r}"

    pause_positive = (
        "请帮我暂停当前侧离线播放",
        "麻烦暂停当前侧数据源",
        "马上暂停当前侧离线播放",
        "暂停当前侧离线播放",
        "暂停当前侧数据源",
        "暂停数据源与控制中的离线播放",
    )
    for prompt in pause_positive:
        assert _explicit_tool_command(prompt) == "pause_current_source", f"pause 正例未命中: {prompt!r}"

    resume_positive = (
        "请帮我恢复当前侧离线播放",
        "麻烦恢复当前侧数据源",
        "马上恢复当前侧离线播放",
        "恢复当前侧离线播放",
        "恢复当前侧数据源",
        "继续数据源与控制中的离线播放",
    )
    for prompt in resume_positive:
        assert _explicit_tool_command(prompt) == "resume_current_source", f"resume 正例未命中: {prompt!r}"

    # ---- 2. 负例：疑问句、否定句、过去时陈述、引用命令 ----
    negative = (
        # 疑问句
        "能否停止当前侧数据源？",
        "怎么暂停当前侧离线播放？",
        # 否定句
        "不要停止当前侧数据源",
        "不需要暂停当前侧离线播放",
        # 过去时陈述
        "已经停止了当前侧数据源",
        "已暂停了当前侧离线播放",
        # 引用命令（非本轮执行意图）
        "系统说明里说“停止当前侧数据源”会停止数据源",
    )
    for prompt in negative:
        assert _explicit_tool_command(prompt) is None, f"负例不应命中: {prompt!r}"

    # ---- 3. 易混淆例：启动 vs 停止、暂停 vs 恢复、选择文件 vs 停止当前文件 ----
    assert _explicit_tool_command("播放离线数据源") == "start_current_source"
    assert _explicit_tool_command("停止当前侧数据源") == "stop_current_source"
    assert _explicit_tool_command("暂停当前侧离线播放") == "pause_current_source"
    assert _explicit_tool_command("恢复当前侧离线播放") == "resume_current_source"
    # 选择文件 vs 停止当前文件
    assert _explicit_tool_command("选择录波文件 capture-a.csv") is None
    assert _explicit_tool_command("把受控录波文件设为当前数据源") is None

    # ---- 4. 复合例：同时要求停止和其他操作（含速度/启动意图，不应直接路由） ----
    compound = (
        "停止当前侧数据源并把速度调成2倍",
        "暂停当前侧离线播放，然后恢复",
        "启动当前侧数据源并停止当前侧数据源",
    )
    for prompt in compound:
        assert _explicit_tool_command(prompt) is None, f"复合例不应直接路由: {prompt!r}"

    # ---- 5. 状态例：通过 prepare_chat 验证服务端前置条件 ----
    admin = "stop-resume-pause-admin"
    operator = "stop-resume-pause-operator"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "stop-resume-pause-operator", "token": operator,
         "scopes": ["engine.start", "engine.pause", "engine.resume", "engine.stop"]},
    ]))
    service = AssistantService(data_dir=str(tmp_path))
    service.update_config({
        "tools_enabled": True,
        "enabled_tools": ["start_current_source", "pause_current_source",
                          "resume_current_source", "stop_current_source"],
    }, admin)

    base_payload = {"prompt": "停止当前侧数据源", "model_type": "local", "model_name": "qwen3:8b"}

    # 5.1 无来源
    with pytest.raises(AssistantError, match="没有可用的数据源配置"):
        service.prepare_chat(base_payload, operator_token=operator, tool_context={"source": {}})

    # 5.2 来源未运行（无法暂停/停止）
    with pytest.raises(AssistantError, match="未在运行，无法暂停"):
        service.prepare_chat({**base_payload, "prompt": "暂停当前侧离线播放"},
                             operator_token=operator,
                             tool_context={"source": {"kind": "csv_file", "has_path": True, "running": False}})
    with pytest.raises(AssistantError, match="未在运行，无法停止"):
        service.prepare_chat(base_payload, operator_token=operator,
                             tool_context={"source": {"kind": "csv_file", "has_path": True, "running": False}})

    # 5.3 来源在播放、没有暂停（无需恢复）；来源未运行（无法恢复）
    with pytest.raises(AssistantError, match="正在运行，无需恢复"):
        service.prepare_chat({**base_payload, "prompt": "恢复当前侧离线播放"},
                             operator_token=operator,
                             tool_context={"source": {"kind": "csv_file", "has_path": True, "running": True}})
    with pytest.raises(AssistantError, match="未在运行，无法恢复"):
        service.prepare_chat({**base_payload, "prompt": "恢复当前侧离线播放"},
                             operator_token=operator,
                             tool_context={"source": {"kind": "csv_file", "has_path": True, "running": False}})

    # 5.4 非离线来源（simulator/tcp）用于 stop 时的前置检查（stop 不限制种类，只检查运行状态）
    # 此处仅验证非离线来源在运行时可被 stop
    plan = service.prepare_chat(base_payload, operator_token=operator,
                                tool_context={"source": {"kind": "simulator", "has_path": False, "running": True}})
    assert plan["_tool_proposal"]["tool"] == "stop_current_source"

    # 5.5 缺少 scope（engine.stop） -> 403，不回退到调速或查询工具
    readonly_operator = "stop-resume-pause-readonly"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "stop-resume-pause-readonly", "token": readonly_operator, "scopes": ["recordings.read"]},
    ]))
    with pytest.raises(AssistantError, match="engine.stop"):
        service.prepare_chat(base_payload, operator_token=readonly_operator,
                             tool_context={"source": {"kind": "csv_file", "has_path": True, "running": True}})

    # 5.6 状态正常时应直接命中确定性路由，不调用模型
    monkeypatch.setattr(service, "_open_request",
                        lambda *args, **kwargs: pytest.fail("direct route must not call model"))
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "stop-resume-pause-operator", "token": operator,
         "scopes": ["engine.start", "engine.pause", "engine.resume", "engine.stop"]},
    ]))
    service.update_config({
        "tools_enabled": True,
        "enabled_tools": ["start_current_source", "pause_current_source",
                          "resume_current_source", "stop_current_source"],
    }, admin)

    # stop 正常路径
    plan = service.prepare_chat(base_payload, operator_token=operator,
                                tool_context={"source": {"kind": "csv_file", "has_path": True, "running": True}})
    assert plan["_tool_proposal"]["tool"] == "stop_current_source"

    # pause 正常路径
    plan = service.prepare_chat({**base_payload, "prompt": "暂停当前侧离线播放"},
                                operator_token=operator,
                                tool_context={"source": {"kind": "csv_file", "has_path": True, "running": True}})
    assert plan["_tool_proposal"]["tool"] == "pause_current_source"

    # resume 正常路径：数据源已暂停。暂停期间 running 仍为 True，要靠 paused 区分
    #（2026-11-10 补-A11：此前这里用 running=False 当作“可恢复”，与实际执行的条件相反）
    plan = service.prepare_chat({**base_payload, "prompt": "恢复当前侧离线播放"},
                                operator_token=operator,
                                tool_context={"source": {"kind": "csv_file", "has_path": True,
                                                         "running": True, "paused": True}})
    assert plan["_tool_proposal"]["tool"] == "resume_current_source"

    # 新增：带“执行”动词的启动表达（问题1：请执行当前离线数据源播放）
    assert _explicit_tool_command("请执行当前离线数据源播放") == "start_current_source"
    assert _explicit_tool_command("执行当前离线数据源播放") == "start_current_source"
    assert _explicit_tool_command("开始当前离线数据源播放") == "start_current_source"

    # 新增：英文单字动词（问题2：stop / start / pause / resume）
    assert _explicit_tool_command("stop") == "stop_current_source"
    assert _explicit_tool_command("STOP") == "stop_current_source"
    assert _explicit_tool_command("start") == "start_current_source"
    assert _explicit_tool_command("pause") == "pause_current_source"
    assert _explicit_tool_command("resume") == "resume_current_source"


def test_expanded_tool_allowlist_is_closed_and_model_context_contains_only_safe_resource_ids(tmp_path, monkeypatch):
    from app.assistant_tools import TOOL_BY_NAME, TOOL_CATALOG

    admin = "expanded-tool-admin-token"
    operator = "expanded-tool-operator-token-1234"
    file_id = "0123456789abcdef01234567"
    profile_id = "0123456789abcdef"
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_ADMIN_TOKEN", admin)
    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS", json.dumps([
        {"id": "expanded-operator", "token": operator,
         "scopes": ["recordings.inspect", "profile.load", "engine.stop"]}
    ]))
    service = AssistantService(data_dir=str(tmp_path / "assistant-data"))
    tool_names = {item["name"] for item in TOOL_CATALOG}
    expected = {"get_runtime_status", "get_runtime_settings", "get_history", "compare_sides",
                "select_recording_source", "inspect_recording", "analyze_recording_rms",
                "set_window_parameters", "set_event_parameter", "set_nilm_parameter",
                "extract_device_profile", "derive_profile_stages", "stop_current_source"}
    assert expected <= tool_names
    assert set(TOOL_NAMES) == set(TOOL_BY_NAME)
    assert all(item["parameters"].get("additionalProperties") is False for item in TOOL_CATALOG)
    for name in expected:
        schema = next(item["function"]["parameters"] for item in openai_tool_schemas([name]))
        assert schema.get("additionalProperties") is False

    assert validate_tool_arguments("set_nilm_parameter", {
        "algorithm": "profile", "parameter": "d2_max", "value": 9
    }) == {"algorithm": "profile", "parameter": "d2_max", "value": 9.0}
    assert validate_tool_arguments("set_electrical_parameters", {
        "fs": 12800, "pt_ratio": 110, "invert_phases": ""
    }) == {"fs": 12800.0, "pt_ratio": 110.0, "invert_phases": ""}
    assert validate_tool_arguments("set_harmonic_parameters", {
        "order_max": 25, "include_interharmonic": False
    }) == {"order_max": 25, "include_interharmonic": False}
    assert validate_tool_arguments("set_power_calculation_mode", {"apparent": "vector"}) == {"apparent": "vector"}
    assert validate_tool_arguments("set_compare_alignment", {"offset_s": -2.5}) == {"offset_s": -2.5}
    assert validate_tool_arguments("set_playback_speed", {"speed": 0}) == {"speed": 0.0}
    assert validate_tool_arguments("set_file_time_utc", {"use_utc": True}) == {"use_utc": True}
    assert validate_tool_arguments("set_event_detection_enabled", {"enabled": False}) == {"enabled": False}
    for tool in ("set_electrical_parameters", "set_harmonic_parameters", "set_power_calculation_mode", "set_compare_alignment"):
        with pytest.raises(ValueError, match="至少提供"):
            validate_tool_arguments(tool, {})
    with pytest.raises(ValueError, match="未注册字段"):
        validate_tool_arguments("set_electrical_parameters", {"fs": 12800, "path": "/tmp/unsafe.csv"})
    with pytest.raises(ValueError, match="JSON 布尔值"):
        validate_tool_arguments("set_file_time_utc", {"use_utc": 1})
    with pytest.raises(ValueError, match="不属于"):
        validate_tool_arguments("set_nilm_parameter", {
            "algorithm": "threshold", "parameter": "d2_max", "value": 9
        })
    with pytest.raises(ValueError, match="布尔"):
        validate_tool_arguments("set_nilm_algorithm_enabled", {"algorithm": "threshold", "enabled": 1})
    with pytest.raises(ValueError, match="未注册字段"):
        validate_tool_arguments("inspect_recording", {"file_id": file_id, "path": "/private/capture.csv"})
    with pytest.raises(ValueError, match="缺少必需字段"):
        validate_tool_arguments("analyze_recording_rms", {"file_id": file_id})
    assert validate_tool_arguments("analyze_recording_rms", {"file_id": file_id, "channel": "Ia"}) == {
        "file_id": file_id, "channel": "Ia",
    }
    assert validate_tool_arguments("extract_device_profile", {
        "file_id": file_id, "device_id": "motor-1", "labels": "08:00:00,start\\n08:00:05,stop"
    })["labels"].startswith("08:00:00")

    service.update_config({"tools_enabled": True, "cloud_tools_enabled": True,
                           "enabled_tools": ["inspect_recording", "load_profile_by_id", "stop_current_source"]}, admin)
    context = {
        "side": "bus",
        "source": {"kind": "csv_file", "name": "private_recording.csv", "has_path": True, "running": False,
                   "path": "/private/absolute/source.csv"},
        "recordings": [{"file_id": file_id, "folder": "data", "name": "private_recording.csv",
                        "path": "/private/absolute/private_recording.csv", "size_bytes": 123}],
        "profiles": [{"id": profile_id, "name": "secret_profile.json", "side": "bus", "size_bytes": 456}],
        "profile_files": [{"id": profile_id, "path": "/private/absolute/secret_profile.json"}],
    }
    local_plan = service.prepare_chat({"prompt": "检查当前录波", "model_type": "local"},
                                      operator_token=operator, tool_context=context)
    local_system = local_plan["messages"][0]["content"]
    assert file_id in local_system and profile_id in local_system
    assert "/private/absolute" not in local_system

    monkeypatch.setenv("ELEC_TOOL_ASSISTANT_CLOUD_API_KEY", "cloud-expanded-tool-test-key")
    cloud_plan = service.prepare_chat({"prompt": "检查文件 ID " + file_id, "model_type": "cloud"},
                                      operator_token=operator, tool_context=context)
    cloud_system = cloud_plan["messages"][0]["content"]
    assert file_id in cloud_system and profile_id in cloud_system
    assert "private_recording.csv" not in cloud_system and "secret_profile.json" not in cloud_system
    assert "/private/absolute" not in cloud_system
    assert service.operator_tools(service.authenticate_operator(operator), "builtin") == []

    with pytest.raises(AssistantError, match="资源清单"):
        service.create_tool_proposal(local_plan, [{"function": {
            "name": "inspect_recording", "arguments": {"file_id": "ffffffffffffffffffffffff"}
        }}])


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


def test_intent_config_loaded_from_csv_covers_all_controlled_tools():
    """意图配置应从 CSV 加载，并覆盖全部 46 个受控工具。"""
    from app.assistant_intents import _INTENT_DATA, TOOL_INTENT_CONTRACTS
    from app.assistant_tools import TOOL_NAMES

    assert len(_INTENT_DATA) == len(TOOL_NAMES) == 46
    assert len(TOOL_INTENT_CONTRACTS) == 46
    for tool in TOOL_NAMES:
        assert tool in _INTENT_DATA, f"缺少意图配置：{tool}"
        contract = TOOL_INTENT_CONTRACTS[tool]
        assert contract.action_terms, f"{tool} 缺少动作词（actions）"
        assert contract.target_terms, f"{tool} 缺少目标词（targets）"
        assert contract.parameter_policy, f"{tool} 缺少参数策略（policy）"


def test_intent_config_csv_get_runtime_status_includes_获取():
    """get_runtime_status 的 actions 应包含“获取”，以识别“获取分路侧离线数据源状态”。"""
    from app.assistant_intents import _INTENT_DATA, recognize_intent

    assert "获取" in _INTENT_DATA["get_runtime_status"]["actions"]

    result = recognize_intent("获取分路侧离线数据源状态", top_k=8, use_cache=False)
    assert result["ok"] is True
    assert result["tier"] == "high"
    assert result["result"]["intent_code"] == "get_runtime_status"


def test_intent_config_csv_required_any_parsed_correctly():
    """required_any 字段应从 CSV 中正确解析为嵌套元组。"""
    from app.assistant_intents import _INTENT_DATA

    # set_profile_parameters: required_any = (("d2_max", "min_confidence"),)
    assert _INTENT_DATA["set_profile_parameters"]["required_any"] == (("d2_max", "min_confidence"),)
    # 无 required_any 的工具应为空元组
    assert _INTENT_DATA["get_runtime_status"]["required_any"] == ()


def test_intent_config_csv_missing_required_column_raises(tmp_path, monkeypatch):
    """CSV 缺少必要列时应抛出明确错误。"""
    import csv

    bad_csv = tmp_path / "bad_intent.csv"
    with open(bad_csv, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["tool", "intent", "mode"])  # 缺少 actions 等列
        writer.writerow(["get_runtime_status", "查询当前侧运行状态", "read"])

    from app.assistant_intents import load_intent_data_from_csv

    with pytest.raises(ValueError, match="缺少必要列"):
        load_intent_data_from_csv(str(bad_csv))


def test_intent_config_csv_in_the_repository_has_a_utf8_bom():
    """补-A8：入库的 configs/intent_actions.csv 带 UTF-8 BOM（中文 Excel 靠它识别编码），读入后不残留 BOM。"""
    from pathlib import Path

    from app.assistant_intents import _INTENT_DATA

    raw = (Path(__file__).resolve().parents[1] / "configs" / "intent_actions.csv").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "configs/intent_actions.csv 应带 UTF-8 BOM"
    assert not raw[3:].startswith(b"\xef\xbb\xbf")           # 只有一个
    assert raw.count(b"\r\n") == 47 and b"\n" not in raw.replace(b"\r\n", b"")   # 表头 + 46 行，CRLF
    assert next(iter(_INTENT_DATA)) == "get_runtime_status"
    assert not any(key.startswith("\ufeff") for key in _INTENT_DATA)


def test_intent_config_csv_saved_as_gbk_still_loads(tmp_path):
    """补-A8：Excel 的“CSV（逗号分隔）”把文件存成 GBK；登记时这样的文件让服务无法启动（UnicodeDecodeError）。"""
    from pathlib import Path

    from app.assistant_intents import _INTENT_DATA, load_intent_data_from_csv

    text = (Path(__file__).resolve().parents[1] / "configs" / "intent_actions.csv").read_bytes().decode("utf-8-sig")
    for name, encoding in (("gbk.csv", "gbk"), ("gb18030.csv", "gb18030"), ("utf8_no_bom.csv", "utf-8"),
                           ("utf8_bom.csv", "utf-8-sig")):
        copy = tmp_path / name
        copy.write_bytes(text.encode(encoding))
        assert load_intent_data_from_csv(str(copy)) == _INTENT_DATA, name

    # 其它编码不猜，给出明确错误（UTF-16 是 Excel “Unicode 文本”的编码）
    utf16 = tmp_path / "utf16.csv"
    utf16.write_bytes(text.encode("utf-16"))
    with pytest.raises(ValueError, match="编码无法识别"):
        load_intent_data_from_csv(str(utf16))


# ---------------------------------------------------------------------------
# 2026-11-10 第三项任务：补-A1～A7、补-A9～A11 的回归用例（REPORT_TEST.md T-023）
# 跨侧用例一律让两侧处于不同的运行状态；真实接口上的同类用例在 tests/test_assistant_cross_side.py。
# ---------------------------------------------------------------------------

_ALL_SOURCE_TOOLS = ["start_current_source", "pause_current_source", "resume_current_source", "stop_current_source"]
_ALL_SOURCE_SCOPES = ["engine.start", "engine.pause", "engine.resume", "engine.stop"]


def _side_contexts(bus_source, branch_source, **extra):
    """A ``tool_context_for`` provider whose two sides are in different states, and the calls it received."""
    contexts = {"bus": {"side": "bus", "source": dict(bus_source), **extra.get("bus", {})},
                "branch": {"side": "branch", "source": dict(branch_source), **extra.get("branch", {})}}
    asked = []

    def provider(side):
        asked.append(side)
        return contexts[side]

    return contexts, provider, asked


def _ask(service, operator, prompt, side, contexts, provider, **kwargs):
    return service.prepare_chat({"prompt": prompt, "model_type": "local", "model_name": "qwen3:8b"},
                                operator_token=operator, side=side, tool_context=contexts[side],
                                tool_context_for=provider, **kwargs)


def test_delay_refusal_needs_a_delay_phrase_not_a_bare_hou_character(tmp_path, monkeypatch):
    """补-A1：单个“后”字不算延时；“后台”“最后 10 条”这类立即执行的请求不再被 400 拒绝。"""
    from app.assistant import _has_delay_intent

    immediate = (
        "查看后台重采样任务状态", "取消后台重采样", "查询最后10条电能质量事件", "列出最后5条负荷辨识事件",
        "以后台方式重采样", "启动后台重采样", "停止后台任务", "查询8点以后的事件", "查看10:00之后的电能质量事件",
        "查询10:00之后发生的事件", "查看之后的事件", "对比事件前后电流", "事件前后对比", "把滞后设置为0.02",
        "把最后查询的结果导出", "最后设置的阈值是多少", "分析最后一次事件", "提取前窗300后窗300的画像",
        "查询持续超过5分钟的事件", "查询不超过5秒的事件", "把窗口长度设为0.2秒", "把窗口设为10s", "把步长设为5秒",
        "导出最近2小时的历史", "加载最近 3 天的历史数据", "通过1秒窗口计算谐波", "查看经过3秒滤波的波形",
        "查询今晚8小时内的事件", "把电压等级设置为10kV", "A、B、C等3个通道", "列出等待确认的操作",
        "总线侧相对分路侧延迟0.5秒", "启动分路侧数据源", "重新启动数据源", "start", "stop",
    )
    for prompt in immediate:
        assert not _has_delay_intent(prompt), f"不是延时指令：{prompt!r}"
    delayed = (
        "15秒过后启动当前侧数据源检测", "5分钟后列出当前电能质量事件", "半小时后停止数据源", "两分钟之后启动",
        "两个小时后停止", "30 秒以后暂停", "10s后启动", "5 min后停止", "１５秒后启动", "1.5小时后停止",
        "过10秒启动数据源", "等5分钟再启动", "等待10秒启动", "推迟10分钟启动", "晚5分钟启动",
        "定时启动数据源", "延时启动", "稍后查看运行状态", "等一下再暂停", "待会启动数据源", "过一会再停止",
        "一会儿再启动", "晚点停止数据源", "回头再清空事件", "片刻后启动",
        "播放完之后停止数据源", "然后停止数据源", "加载完成之后再启动数据源",
        "启动后暂停数据源", "启动后立即暂停", "播放完后停止数据源", "播放完成后暂停", "停止后重新启动数据源",
        "等播放完再停止数据源", "等数据源播放结束再暂停",
    )
    for prompt in delayed:
        assert _has_delay_intent(prompt), f"应识别为延时指令：{prompt!r}"

    service, operator = _tool_gate_service(
        tmp_path, monkeypatch, ["get_resample_status", "cancel_resample", "get_event_list", "start_current_source"],
        ["recordings.resample.read", "recordings.resample.cancel", "events.read", "engine.start"])
    monkeypatch.setattr(service, "_open_request",
                        lambda *args, **kwargs: pytest.fail("a direct route must not call the model"))
    context = {"source": {"kind": "simulator", "running": False}}
    # 登记时被 400 拒绝的三句话：现在各自得到对应工具的提案
    for prompt, tool in (("查看后台重采样任务状态", "get_resample_status"), ("取消后台重采样", "cancel_resample"),
                         ("查询最后10条电能质量事件", "get_event_list")):
        plan = service.prepare_chat({"prompt": prompt, "model_type": "local"}, operator_token=operator,
                                    tool_context=context)
        assert plan["_tool_proposal"]["tool"] == tool, prompt
    # 真正的延时指令在两条直达路由上仍被拒绝
    for prompt in ("15秒过后启动当前侧数据源检测", "5分钟后列出当前电能质量事件", "稍后查看后台重采样任务状态",
                   "等5分钟再启动当前侧数据源检测"):
        with pytest.raises(AssistantError, match="系统不支持延时执行") as refused:
            service.prepare_chat({"prompt": prompt, "model_type": "local"}, operator_token=operator,
                                 tool_context=context)
        assert refused.value.status_code == 400, prompt


def test_side_words_are_whole_words_and_two_named_sides_are_never_guessed(tmp_path, monkeypatch):
    """补-A2：bus / branch 只认独立单词（“Modbus”不算总线侧）；两侧都点名时不取先出现的一侧。"""
    from app.assistant import _resolve_target_side

    table = (
        # 话，提问页面 -> (目标侧, 是否两侧都点名)
        ("查看 Modbus 运行状态", "branch", ("branch", False)),
        ("查看 Modbus 运行状态", "bus", ("bus", False)),
        ("busbar 电压是多少", "branch", ("branch", False)),
        ("列出 branches", "bus", ("bus", False)),
        ("停止bus侧数据源", "branch", ("bus", False)),
        ("查看 BRANCH 状态", "bus", ("branch", False)),
        ("查看 Ｂｕｓ 侧状态", "branch", ("bus", False)),
        ("暂停分路侧离线播放", "bus", ("branch", False)),
        ("查看总侧数据源", "branch", ("bus", False)),
        ("区分侧别查看状态", "bus", ("bus", False)),
        ("启动当前侧数据源", "branch", ("branch", False)),
        ("启动数据源", "branch", ("branch", False)),
        ("对比总线侧和分路侧", "bus", ("bus", True)),
        ("对比分路侧和总线侧", "branch", ("branch", True)),
        ("启动当前侧分路侧数据源", "bus", ("bus", True)),
        ("启动当前侧分路侧数据源", "branch", ("branch", False)),
    )
    for prompt, page, expected in table:
        assert _resolve_target_side(prompt, page) == expected, (prompt, page)

    service, operator = _tool_gate_service(
        tmp_path, monkeypatch, ["get_runtime_status", "set_wiring_mode", "compare_sides", *_ALL_SOURCE_TOOLS],
        ["state.read", "config.wiring.write", "compare.read", *_ALL_SOURCE_SCOPES])
    running = {"kind": "csv_file", "has_path": True, "running": True, "paused": False}
    stopped = {"kind": "simulator", "has_path": False, "running": False, "paused": False}
    contexts, provider, _asked = _side_contexts(bus_source=running, branch_source=stopped)
    reads = []

    def executor(tool, side):
        reads.append((tool, side))
        return {"side": side}

    # 登记时的现象：在分路侧页面问“Modbus”，返回的是总线侧状态
    plan = _ask(service, operator, "查看 Modbus 运行状态", "branch", contexts, provider, read_tool_executor=executor)
    assert reads == [("get_runtime_status", "branch")] and plan["_side"] == "branch"
    assert "查询分路侧运行状态" in plan["_direct_tool_response"]

    # 确定性路由：两侧都点名 -> 400，不替用户选；同一句话在分路侧页面只指分路侧
    for prompt, page in (("停止总线侧 分路侧数据源", "bus"), ("停止分路侧总线侧数据源", "bus"),
                         ("启动当前侧分路侧数据源", "bus")):
        with pytest.raises(AssistantError, match="同时提到了总线侧和分路侧") as refused:
            _ask(service, operator, prompt, page, contexts, provider)
        assert refused.value.status_code == 400, prompt
    plan = _ask(service, operator, "启动当前侧分路侧数据源", "branch", contexts, provider)
    assert plan["_tool_proposal"]["side"] == "branch"
    assert not any(item["name"] == "stop_current_source" for item in service._pending_tools.values())

    # 模型路径：单侧工具在两侧都点名时返回澄清，不创建提案
    call = _tool_call("set_wiring_mode", {"wiring": "3p4w"})
    monkeypatch.setattr(service, "_open_request", _fake_model_reply({"content": "", "tool_calls": [call]}))
    pending_before = len(service._pending_tools)
    plan = _ask(service, operator, "切换总线侧和分路侧接线模式到3p4w", "bus", contexts, provider)
    answer = service.complete(plan)
    assert "同时提到了总线侧和分路侧" in answer and plan.get("_tool_clarification")
    assert "_tool_proposal" not in plan and len(service._pending_tools) == pending_before

    # 本身就跨两侧的工具不受影响：仍绑定提问页面所在的一侧
    call = _tool_call("compare_sides", {"quantity": "power"})
    monkeypatch.setattr(service, "_open_request", _fake_model_reply({"content": "", "tool_calls": [call]}))
    plan = _ask(service, operator, "对比总线侧和分路侧的有功功率", "branch", contexts, provider)
    service.complete(plan)
    assert plan["_tool_proposal"]["tool"] == "compare_sides" and plan["_tool_proposal"]["side"] == "branch"


def test_exclusive_wording_adds_a_linkage_warning_and_no_unread_plan_keys(tmp_path, monkeypatch):
    """补-A3：“只 / 仅 / 单独”不改变执行内容；总线侧的联动操作在卡片上提示“不能只作用于总线侧”。"""
    from app.assistant import _has_exclusive_limit

    for prompt in ("只启动总线侧数据源", "仅暂停总线侧", "单独停止总线侧", "仅仅停止总线侧数据源"):
        assert _has_exclusive_limit(prompt), prompt
    for prompt in ("启动数据源", "查看只读配置", "只要启动就行", "不只停止总线侧", "不仅如此", "只是看看状态"):
        assert not _has_exclusive_limit(prompt), prompt

    service, operator = _tool_gate_service(tmp_path, monkeypatch, [*_ALL_SOURCE_TOOLS, "load_last_history"],
                                           [*_ALL_SOURCE_SCOPES, "history.load"])
    stopped = {"kind": "csv_file", "has_path": True, "running": False, "paused": False}
    running = {"kind": "csv_file", "has_path": True, "running": True, "paused": False}
    paused = {"kind": "csv_file", "has_path": True, "running": True, "paused": True}
    warning = "系统不支持只作用于总线侧"

    def proposal(prompt, side, bus_source, branch_source):
        contexts, provider, _asked = _side_contexts(bus_source=bus_source, branch_source=branch_source)
        plan = _ask(service, operator, prompt, side, contexts, provider)
        # 两个键曾经写进计划却没有代码读取；_parsed_side 与 _side 重复，已删除
        assert "_parsed_side" not in plan and plan["_exclusive_limit"] is _has_exclusive_limit(prompt)
        return plan["_tool_proposal"]

    # 总线侧 + 限定词 + 联动操作：四个启停操作各有一句说明连带效果的提示（确定性路由与意图识别直达都有）
    for prompt, bus_source, effect in (
            ("只启动总线侧数据源", stopped, "分路侧已启用时会一起启动"),
            ("只暂停总线侧离线播放", running, "分路侧正在播放的离线文件会一起暂停"),
            ("单独恢复总线侧离线播放", paused, "分路侧暂停中的离线文件会一起恢复"),
            ("仅停止总线侧数据源", running, "分路侧会一起停止")):
        item = proposal(prompt, "branch", bus_source, stopped)
        assert item["side"] == "bus" and warning in item["impact"] and effect in item["impact"], prompt
    # 在总线侧页面不点名侧别也一样（“当前侧”就是总线侧）
    assert warning in proposal("只暂停当前侧离线播放", "bus", running, stopped)["impact"]
    # 没有限定词、或操作落在分路侧（不联动总线侧）：不加提示
    assert warning not in proposal("暂停总线侧离线播放", "bus", running, stopped)["impact"]
    assert warning not in proposal("只启动分路侧数据源", "bus", running, stopped)["impact"]
    assert warning not in proposal("只暂停当前侧离线播放", "branch", stopped, running)["impact"]


def test_intent_route_start_requires_a_file_source_only_for_offline_wording(tmp_path, monkeypatch):
    """补-A4：意图识别直达与确定性路由用同一条规则——只有话里明确说到离线 / CSV / 文件时才要求文件数据源。"""
    service, operator = _tool_gate_service(tmp_path, monkeypatch, ["start_current_source"], ["engine.start"])
    monkeypatch.setattr(service, "_open_request",
                        lambda *args, **kwargs: pytest.fail("a direct route must not call the model"))
    simulator = {"kind": "simulator", "has_path": False, "running": False, "paused": False}
    contexts, provider, _asked = _side_contexts(bus_source=simulator, branch_source=simulator)

    # 同一个意思，两条路由结果一致（登记时：前一句 409，后一句生成提案）
    for prompt, origin in (("启动分路侧数据源检测", "intent"), ("启动分路侧数据源", "deterministic")):
        plan = _ask(service, operator, prompt, "bus", contexts, provider)
        assert plan["_tool_call_origin"] == origin and plan["_tool_proposal"]["side"] == "branch", prompt
    # 话里说了离线 / CSV：数据源不是文件时两条路由都拒绝
    for prompt, origin in (("启动分路侧离线数据源检测", "intent"), ("启动分路侧CSV数据源检测", "intent"),
                           ("播放离线数据源", "deterministic")):
        with pytest.raises(AssistantError, match="不是离线文件数据源") as refused:
            _ask(service, operator, prompt, "bus", contexts, provider)
        assert refused.value.status_code == 409, prompt
    # 文件数据源没有配置路径：意图识别直达同样拒绝
    no_file = {"kind": "csv_file", "has_path": False, "running": False, "paused": False}
    contexts, provider, _asked = _side_contexts(bus_source=simulator, branch_source=no_file)
    with pytest.raises(AssistantError, match="分路侧离线数据源未配置可用文件"):
        _ask(service, operator, "启动分路侧数据源检测", "bus", contexts, provider)


def test_model_path_proposal_is_bound_to_the_side_named_in_the_prompt(tmp_path, monkeypatch, caplog):
    """补-A5：模型路径的提案绑定到话里点名的一侧，用的是那一侧的资源清单。"""
    import logging

    service, operator = _tool_gate_service(
        tmp_path, monkeypatch, ["set_wiring_mode", "load_profile_by_id", "compare_sides"],
        ["config.wiring.write", "profile.load", "compare.read"])
    source = {"kind": "simulator", "has_path": False, "running": False, "paused": False}
    contexts, provider, asked = _side_contexts(
        bus_source=source, branch_source=source,
        bus={"profiles": [{"id": "00000000000000b1", "name": "profile_bus_device.json", "side": "bus"}]},
        branch={"profiles": [{"id": "00000000000000c9", "name": "profile_branch_device.json", "side": "branch"}]})
    caplog.set_level(logging.INFO, logger="elec_tool.assistant")
    call = _tool_call("set_wiring_mode", {"wiring": "3p4w"})
    monkeypatch.setattr(service, "_open_request", _fake_model_reply({"content": "好。", "tool_calls": [call]}))

    # 登记时的现象：在总线侧页面说“把分路侧……”，得到 side=bus 的提案
    plan = _ask(service, operator, "把分路侧接线模式切换到3p4w", "bus", contexts, provider)
    answer = service.complete(plan)
    proposal = plan["_tool_proposal"]
    assert proposal["side"] == "branch" and proposal["summary"] == "将分路侧接线模式切换为 3p4w"
    # 跨侧提案的标题不再写“当前侧”（那会被读成提问页面所在的一侧）
    assert proposal["title"] == "切换分路侧接线模式" and "切换分路侧接线模式" in answer
    pending = service._pending_tools[proposal["id"]]
    assert pending["side"] == "branch" and pending["context"]["side"] == "branch"
    assert "bound_side=branch" in caplog.text and "side=bus target_side=branch" in caplog.text
    assert asked == ["branch"]  # 另一侧的上下文只读取一次

    # 反方向，以及不点名侧别时仍绑定提问页面所在的一侧（标题保持工具原名）
    plan = _ask(service, operator, "把总线侧接线模式切换到3p4w", "branch", contexts, provider)
    service.complete(plan)
    assert plan["_tool_proposal"]["side"] == "bus" and plan["_tool_proposal"]["title"] == "切换总线侧接线模式"
    plan = _ask(service, operator, "切换接线模式到3p4w", "branch", contexts, provider)
    service.complete(plan)
    assert plan["_tool_proposal"]["side"] == "branch" and plan["_tool_proposal"]["title"] == "切换当前侧接线模式"

    # 模型看到的、以及核对参数用的，都是目标侧的画像清单
    plan = _ask(service, operator, "使用分路侧画像ID为 00000000000000c9", "bus", contexts, provider)
    system_text = plan["messages"][0]["content"]
    assert "00000000000000c9" in system_text and "00000000000000b1" not in system_text
    call = _tool_call("load_profile_by_id", {"profile_id": "00000000000000c9"})
    monkeypatch.setattr(service, "_open_request", _fake_model_reply({"content": "", "tool_calls": [call]}))
    service.complete(plan)
    proposal = plan["_tool_proposal"]
    assert proposal["side"] == "branch" and proposal["arguments"] == {"profile_id": "00000000000000c9"}
    assert service._pending_tools[proposal["id"]]["context"]["profiles"][0]["id"] == "00000000000000c9"
    # 总线侧清单里的画像不属于分路侧：模型给出它时只得到澄清，不创建提案
    pending_before = len(service._pending_tools)
    call = _tool_call("load_profile_by_id", {"profile_id": "00000000000000b1"})
    monkeypatch.setattr(service, "_open_request", _fake_model_reply({"content": "", "tool_calls": [call]}))
    plan = _ask(service, operator, "使用分路侧画像ID为 00000000000000b1", "bus", contexts, provider)
    service.complete(plan)
    assert plan.get("_tool_clarification") and "_tool_proposal" not in plan
    assert len(service._pending_tools) == pending_before


def test_intent_route_leaves_unauthorized_requests_to_the_model_path(tmp_path, monkeypatch, caplog):
    """补-A6：意图识别直达只在工具本轮可用时介入；不可用时不报 403，日志写明识别出的工具不可用。"""
    import logging

    service, operator = _tool_gate_service(tmp_path, monkeypatch, ["get_event_list", "start_current_source"],
                                           ["recordings.read"])  # 令牌没有 events.read / engine.start
    caplog.set_level(logging.INFO, logger="elec_tool.assistant")
    context = {"source": {"kind": "simulator", "running": False}}

    # 知识性问题也会被打成 high tier；工具不可用时必须还能得到普通回答
    for token in (operator, ""):
        for prompt in ("电能质量事件有哪些类型", "列出当前电能质量事件"):
            caplog.clear()
            plan = service.prepare_chat({"prompt": prompt, "model_type": "local", "model_name": "qwen3:8b"},
                                        operator_token=token, tool_context=context)
            assert plan["_tool_call_origin"] == "model" and "messages" in plan and "_tool_proposal" not in plan
            assert "decision=model_fallback" in caplog.text and "intent_tier=high" in caplog.text
            assert "intent_tool=get_event_list intent_tool_available=False" in caplog.text
            assert "assistant_route_blocked" not in caplog.text
    # 确定性路由（话与工具标题、启停短命令完全对上）在工具不可用时仍报 403
    with pytest.raises(AssistantError, match="操作员令牌缺少精确 scope engine.start") as denied:
        service.prepare_chat({"prompt": "启动当前侧数据源检测", "model_type": "local"}, operator_token=operator,
                             tool_context=context)
    assert denied.value.status_code == 403
    assert not service._pending_tools


def test_direct_reads_skip_the_low_tier_and_leave_an_audit_record(tmp_path, monkeypatch):
    """补-A7：两个只读查询 low 档位不直接执行；直接执行时写一条审计记录；摘要由注入的服务端函数生成。"""
    service, operator = _tool_gate_service(tmp_path, monkeypatch, ["get_runtime_status", "get_runtime_settings"],
                                           ["state.read", "config.read"])
    source = {"kind": "simulator", "has_path": False, "running": False, "paused": False}
    contexts, provider, _asked = _side_contexts(bus_source=source, branch_source=source)
    audit_path = tmp_path / "tool_audit.jsonl"
    reads = []

    def audit():
        return ([json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
                if audit_path.exists() else [])

    def executor(tool, side):
        reads.append((tool, side))
        return {"side": side, "marker": f"{tool}@{side}"}

    monkeypatch.setattr(service, "_open_request",
                        lambda *args, **kwargs: pytest.fail("a direct read must not call the model"))
    plan = _ask(service, operator, "查询当前运行状态", "bus", contexts, provider, read_tool_executor=executor)
    assert reads == [("get_runtime_status", "bus")]
    assert json.loads(plan["_direct_tool_response"].split("\n", 1)[1]) == {"side": "bus",
                                                                         "marker": "get_runtime_status@bus"}
    assert "_tool_proposal" not in plan and not service._pending_tools
    plan = _ask(service, operator, "查看分路侧计算配置", "bus", contexts, provider, read_tool_executor=executor)
    assert reads[-1] == ("get_runtime_settings", "branch") and "查询分路侧计算配置摘要" in plan["_direct_tool_response"]
    records = audit()
    assert [(row["tool"], row["side"], row["status"]) for row in records] == [
        ("get_runtime_status", "bus", "direct_read"), ("get_runtime_settings", "branch", "direct_read")]
    for row, trace_id in zip(records, (None, plan["_trace_id"])):
        assert row["operator_id"] == "tool-gate-operator" and row["origin"] == "intent" and row["arguments"] == {}
        assert "proposal_id" not in row and re.fullmatch(r"[0-9a-f]{16}", row["trace_id"])
        assert trace_id is None or row["trace_id"] == trace_id

    # low 档位（一句话同时问状态和配置，两个候选同分）：不直接执行，交给模型路径
    plan = _ask(service, operator, "查看当前运行状态和计算配置", "bus", contexts, provider, read_tool_executor=executor)
    assert plan["_tool_call_origin"] == "model" and "messages" in plan and "_direct_tool_response" not in plan
    assert len(reads) == 2 and len(audit()) == 2

    # 取摘要出错：留下 failed 记录，异常照常抛出
    def broken(tool, side):
        raise RuntimeError("summary unavailable")

    with pytest.raises(RuntimeError):
        _ask(service, operator, "查询当前运行状态", "bus", contexts, provider, read_tool_executor=broken)
    assert audit()[-1]["status"] == "failed" and audit()[-1]["tool"] == "get_runtime_status"

    # 调用方没有提供取摘要的函数：退回为一张待确认的提案
    plan = _ask(service, operator, "查询当前运行状态", "bus", contexts, provider)
    assert plan["_tool_proposal"]["tool"] == "get_runtime_status" and len(service._pending_tools) == 1
    assert audit()[-1]["status"] == "pending_confirmation"


def test_cross_side_source_checks_read_the_target_side_state(tmp_path, monkeypatch, caplog):
    """补-A9 / 补-A10 / 补-A11：启动、暂停、恢复、停止的前置检查读目标侧的状态；恢复只在“已暂停”时放行。"""
    import logging

    service, operator = _tool_gate_service(tmp_path, monkeypatch, _ALL_SOURCE_TOOLS, _ALL_SOURCE_SCOPES)
    monkeypatch.setattr(service, "_open_request",
                        lambda *args, **kwargs: pytest.fail("a direct route must not call the model"))
    caplog.set_level(logging.INFO, logger="elec_tool.assistant")
    playing = {"kind": "csv_file", "has_path": True, "running": True, "paused": False}
    paused = {"kind": "csv_file", "has_path": True, "running": True, "paused": True}
    stopped = {"kind": "simulator", "has_path": False, "running": False, "paused": False}

    def outcome(prompt, page, bus_source, branch_source):
        """The proposal's ``(tool, side)``, or the refusal's ``(status, message)``."""
        contexts, provider, _asked = _side_contexts(bus_source=bus_source, branch_source=branch_source)
        try:
            plan = _ask(service, operator, prompt, page, contexts, provider)
        except AssistantError as exc:
            return exc.status_code, exc.message
        return plan["_tool_proposal"]["tool"], plan["_tool_proposal"]["side"]

    # ---- 总线侧在播放、分路侧未运行；在总线侧页面操作分路侧 ----
    # 补-A10：登记时这句话被 409“分路侧数据源已在运行或暂停”误拒（读的是总线侧的状态）
    for prompt in ("启动分路侧数据源", "启动分路侧数据源检测"):  # 确定性路由 / 意图识别直达
        caplog.clear()
        assert outcome(prompt, "bus", playing, stopped) == ("start_current_source", "branch"), prompt
        assert "side=bus target_side=branch" in caplog.text
        assert "source_kind=simulator source_running=False" in caplog.text  # 日志里是目标侧的数据源
    # 补-A9：登记时这三句话照样生成提案，到确认才报错（停止甚至返回成功）
    for prompt, message in (("暂停分路侧离线播放", "分路侧数据源未在运行，无法暂停"),
                            ("恢复分路侧离线播放", "分路侧数据源未在运行，无法恢复"),
                            ("停止分路侧数据源", "分路侧数据源未在运行，无法停止"),
                            ("仅停止分路侧数据源", "分路侧数据源未在运行，无法停止")):  # 最后一句走意图识别直达
        status, text = outcome(prompt, "bus", playing, stopped)
        assert status == 409 and message in text, prompt
    # 同一时刻对总线侧自己的操作不受影响
    assert outcome("暂停当前侧离线播放", "bus", playing, stopped) == ("pause_current_source", "bus")
    assert outcome("停止当前侧数据源", "bus", playing, stopped) == ("stop_current_source", "bus")

    # ---- 同样的状态，在分路侧页面操作总线侧 ----
    # 补-A10 的另一半：目标侧已在运行时，登记时提案照样生成
    status, text = outcome("启动总线侧数据源", "branch", playing, stopped)
    assert status == 409 and "总线侧数据源已在运行或暂停，不会重复启动" in text
    assert outcome("暂停总线侧离线播放", "branch", playing, stopped) == ("pause_current_source", "bus")
    assert outcome("停止总线侧数据源", "branch", playing, stopped) == ("stop_current_source", "bus")
    status, text = outcome("恢复总线侧离线播放", "branch", playing, stopped)
    assert status == 409 and "总线侧数据源正在运行，无需恢复" in text
    assert outcome("启动当前侧数据源检测", "branch", playing, stopped) == ("start_current_source", "branch")

    # ---- 补-A11：总线侧已暂停（running 仍为 True）----
    # 登记时：在总线侧页面说这句话被 409“正在运行，无需恢复”拒绝，暂停后无法从本侧恢复
    for prompt, page in (("恢复当前侧离线播放", "bus"), ("resume", "bus"), ("恢复总线侧离线播放", "branch"),
                         ("单独恢复总线侧离线播放", "branch")):
        assert outcome(prompt, page, paused, stopped) == ("resume_current_source", "bus"), prompt
    # 数据源已停止：登记时反而生成提案，确认时才报“数据源未在运行”
    status, text = outcome("恢复当前侧离线播放", "bus", stopped, playing)
    assert status == 409 and "总线侧数据源未在运行，无法恢复" in text
    # 暂停中的数据源不能再“启动”，要用恢复
    status, text = outcome("启动当前侧数据源检测", "bus", paused, stopped)
    assert status == 409 and "请使用恢复操作" in text
