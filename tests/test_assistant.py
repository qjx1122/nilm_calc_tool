"""智能问答服务单元测试：密钥边界、配置校验、RAG 与模型适配。"""
from __future__ import annotations

import base64
import json

import pytest

from app.assistant import (AssistantError, AssistantService, DEFAULT_CONFIG,
                           _explicit_offline_source_start, _explicit_tool_command, _number)
from app.assistant_docs import PLATFORM_PARAMETER_DOC_ID
from app.assistant_tools import TOOL_CATALOG, TOOL_NAMES, openai_tool_schemas, validate_tool_arguments


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
        ("请马上开始离线数据源", True),
        ("马上开始离线数据源", True),
        ("立即播放离线数据源CSV文件", True),
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
    assert "启动当前侧数据源检测" in "".join(service.stream(plan, threading.Event()))

    incorrect_code = "000001" if proposal["confirmation_code"] != "000001" else "000002"
    with pytest.raises(AssistantError, match="二次确认码不匹配"):
        service.claim_tool_proposal(proposal["id"], operator, "branch", incorrect_code)


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
