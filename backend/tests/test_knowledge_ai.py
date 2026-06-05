from fastapi.testclient import TestClient
import json
import time
from urllib import error
from uuid import uuid4

from app.main import app
from app.modules.ai.service import AI_RUNS, RUNTIME_AI_CONFIG, RUNTIME_USER_AI_CONFIGS, run_json_task_detailed
from app.modules.parsing.schemas import DocumentChunk
from app.modules.parsing.service import CHUNKS
from app.modules.risks.service import RISKS
from app.modules.test_items.service import TEST_ITEMS
from app.modules.test_packages.service import TEST_PACKAGES


client = TestClient(app)


def setup_function() -> None:
    from app.modules.admin import service as admin_service

    admin_service.get_settings().repository_backend = "memory"
    admin_service.get_settings().system_config_path = f"/tmp/monkeycode-test-system-config-{uuid4()}.json"
    RUNTIME_AI_CONFIG.clear()
    RUNTIME_USER_AI_CONFIGS.clear()
    AI_RUNS.clear()
    CHUNKS.clear()
    RISKS.clear()
    TEST_ITEMS.clear()
    TEST_PACKAGES.clear()


def auth_headers(username: str = "admin", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_knowledge_search_returns_project_scoped_results() -> None:
    headers = auth_headers()
    risks = client.post(
        "/api/risks/parse",
        headers=headers,
        json={"project_id": "project-g99-rfid", "source_type": "jira", "content": "title\nRFID读取失败\n"},
    ).json()["items"]
    client.post("/api/risks/bulk-publish", headers=headers, json={"risk_ids": [item["id"] for item in risks]})

    response = client.post(
        "/api/knowledge/search",
        headers=headers,
        json={"project_id": "project-g99-rfid", "query": "RFID 读取"},
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["source_type"] == "risk"


def test_knowledge_search_excludes_document_chunks() -> None:
    headers = auth_headers()
    CHUNKS["doc-1"] = [
        DocumentChunk(
            id="chunk-1",
            document_id="doc-1",
            sequence=1,
            heading="RFID 文档",
            page_number=None,
            text="RFID 文档切片不参与需求分析知识库检索",
        )
    ]

    response = client.post(
        "/api/knowledge/search",
        headers=headers,
        json={"project_id": "project-g99-rfid", "query": "RFID 文档切片"},
    )

    assert response.status_code == 200
    assert all(item["source_type"] != "document_chunk" for item in response.json()["results"])


def test_knowledge_search_denies_unassigned_project() -> None:
    response = client.post(
        "/api/knowledge/search",
        headers=auth_headers("tester", "tester123"),
        json={"project_id": "project-mgi-platform", "query": "RFID"},
    )

    assert response.status_code == 403


def test_ai_validation_reports_missing_fields() -> None:
    response = client.post(
        "/api/ai/validate",
        headers=auth_headers(),
        json={"task_type": "document_label_extraction", "output": {"labels": []}},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert "缺少字段: confidence" in response.json()["errors"]


def test_ai_config_reports_local_fallback_by_default(tmp_path) -> None:
    from app.modules.admin import service as admin_service

    admin_service.get_settings().system_config_path = str(tmp_path / "system-config.json")
    response = client.get("/api/ai/config", headers=auth_headers())

    assert response.status_code == 200
    config = response.json()
    assert config["provider"] == "local"
    assert config["configured"] is False
    assert config["api_key_configured"] is False


def test_admin_can_update_ai_config() -> None:
    response = client.put(
        "/api/ai/config",
        headers=auth_headers(),
        json={
            "provider": "openai-compatible",
            "base_url": "https://model.example.com/v1",
            "api_key": "sk-test-secret",
            "model": "test-model",
            "timeout_seconds": 30,
        },
    )

    assert response.status_code == 200
    config = response.json()
    assert config["configured"] is True
    assert config["base_url"] == "https://model.example.com/v1"
    assert config["model"] == "test-model"
    assert config["timeout_seconds"] == 30
    assert config["api_key_configured"] is True
    assert config["api_key_masked"] == "sk-t****cret"


def test_ai_config_persists_to_settings_file(tmp_path) -> None:
    from app.modules.admin import service as admin_service

    admin_service.get_settings().system_config_path = str(tmp_path / "system-config.json")
    response = client.put(
        "/api/ai/config",
        headers=auth_headers(),
        json={
            "provider": "openai-compatible",
            "base_url": "https://model.example.com/v1",
            "api_key": "sk-persisted-secret",
            "model": "persisted-model",
            "timeout_seconds": 35,
        },
    )
    assert response.status_code == 200

    RUNTIME_AI_CONFIG.clear()
    persisted = client.get("/api/ai/config", headers=auth_headers())

    assert persisted.status_code == 200
    assert persisted.json()["configured"] is True
    assert persisted.json()["base_url"] == "https://model.example.com/v1"
    assert persisted.json()["model"] == "persisted-model"
    assert persisted.json()["timeout_seconds"] == 35
    assert persisted.json()["api_key_configured"] is True


def test_non_admin_can_update_ai_config() -> None:
    response = client.put(
        "/api/ai/config",
        headers=auth_headers("tester", "tester123"),
        json={
            "provider": "openai-compatible",
            "base_url": "https://tester-model.example.com/v1",
            "api_key": "tester-secret",
            "model": "tester-model",
            "timeout_seconds": 20,
        },
    )

    assert response.status_code == 200
    assert response.json()["configured"] is True
    assert response.json()["model"] == "tester-model"


def test_ai_config_is_scoped_to_current_user(tmp_path) -> None:
    from app.modules.admin import service as admin_service

    admin_service.get_settings().system_config_path = str(tmp_path / "system-config.json")
    RUNTIME_AI_CONFIG.clear()

    admin_response = client.put(
        "/api/ai/config",
        headers=auth_headers(),
        json={
            "provider": "openai-compatible",
            "base_url": "https://admin-model.example.com/v1",
            "api_key": "admin-secret",
            "model": "admin-model",
            "timeout_seconds": 30,
        },
    )
    tester_response = client.put(
        "/api/ai/config",
        headers=auth_headers("tester", "tester123"),
        json={
            "provider": "openai-compatible",
            "base_url": "https://tester-model.example.com/v1",
            "api_key": "tester-secret",
            "model": "tester-model",
            "timeout_seconds": 20,
        },
    )

    assert admin_response.status_code == 200
    assert tester_response.status_code == 200
    assert client.get("/api/ai/config", headers=auth_headers()).json()["model"] == "admin-model"
    assert client.get("/api/ai/config", headers=auth_headers("tester", "tester123")).json()["model"] == "tester-model"


def test_ai_json_task_retries_without_response_format_on_502(monkeypatch) -> None:
    RUNTIME_AI_CONFIG.update(
        {
            "provider": "openai-compatible",
            "base_url": "https://model.example.com/v1",
            "api_key": "sk-test-secret",
            "model": "test-model",
            "timeout_seconds": 30,
        }
    )
    calls: list[dict] = []

    def fake_urlopen(req, timeout):
        payload = json.loads(req.data.decode("utf-8"))
        calls.append(payload)
        if "response_format" in payload:
            raise error.HTTPError(req.full_url, 502, "Bad Gateway", hdrs=None, fp=None)

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps({"choices": [{"message": {"content": '{"answer":"ok"}'}}]}).encode("utf-8")

        return Response()

    monkeypatch.setattr("app.modules.ai.service.request.urlopen", fake_urlopen)

    result = run_json_task_detailed("free_chat", "system", "user")

    assert result.status == "succeeded"
    assert result.output == {"answer": "ok"}
    assert "response_format" in calls[0]
    assert "response_format" not in calls[1]


def test_free_chat_returns_local_knowledge_answer() -> None:
    headers = auth_headers()
    risks = client.post(
        "/api/risks/parse",
        headers=headers,
        json={"project_id": "project-g99-rfid", "source_type": "jira", "content": "title\nRFID读取失败\n"},
    ).json()["items"]
    client.post("/api/risks/bulk-publish", headers=headers, json={"risk_ids": [item["id"] for item in risks]})

    response = client.post(
        "/api/free-chat/ask",
        headers=headers,
        json={"project_id": "project-g99-rfid", "question": "RFID 读取有什么风险", "use_project_knowledge": True, "use_external_model": False},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["used_model"] is False
    assert result["ai_status"] == "not_requested"
    assert result["ai_message"] == "未请求 AI 模型。"
    assert result["sources"]
    assert "RFID" in result["answer"]


def test_free_chat_reports_ai_not_configured() -> None:
    headers = auth_headers()

    response = client.post(
        "/api/free-chat/ask",
        headers=headers,
        json={"project_id": "project-g99-rfid", "question": "RFID 读取有什么风险", "use_project_knowledge": False, "use_external_model": True},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["used_model"] is False
    assert result["ai_status"] == "not_configured"
    assert "AI 未配置" in result["ai_message"]


def test_free_chat_reports_ai_success(monkeypatch) -> None:
    headers = auth_headers()
    config_response = client.put(
        "/api/ai/config",
        headers=headers,
        json={
            "provider": "openai-compatible",
            "base_url": "https://model.example.com/v1",
            "api_key": "secret",
            "model": "test-model",
            "timeout_seconds": 20,
        },
    )
    assert config_response.status_code == 200

    def fake_urlopen(req, timeout):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps({"choices": [{"message": {"content": '{"answer":"AI 已响应"}'}}]}).encode("utf-8")

        return Response()

    monkeypatch.setattr("app.modules.ai.service.request.urlopen", fake_urlopen)

    response = client.post(
        "/api/free-chat/ask",
        headers=headers,
        json={"project_id": "project-g99-rfid", "question": "RFID 读取有什么风险", "use_project_knowledge": False, "use_external_model": True},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["used_model"] is True
    assert result["ai_status"] == "succeeded"
    assert result["ai_message"] == "AI 调用成功。"
    assert result["answer"] == "AI 已响应"


def test_free_chat_uses_configured_ai_timeout(monkeypatch) -> None:
    headers = auth_headers()
    config_response = client.put(
        "/api/ai/config",
        headers=headers,
        json={
            "provider": "openai-compatible",
            "base_url": "https://model.example.com/v1",
            "api_key": "secret",
            "model": "test-model",
            "timeout_seconds": 120,
        },
    )
    assert config_response.status_code == 200
    timeouts: list[int] = []

    def fake_urlopen(req, timeout):
        timeouts.append(timeout)

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps({"choices": [{"message": {"content": '{"answer":"AI 已响应"}'}}]}).encode("utf-8")

        return Response()

    monkeypatch.setattr("app.modules.ai.service.request.urlopen", fake_urlopen)

    response = client.post(
        "/api/free-chat/ask",
        headers=headers,
        json={"project_id": "project-g99-rfid", "question": "RFID 读取有什么风险", "use_project_knowledge": False, "use_external_model": True},
    )

    assert response.status_code == 200
    assert response.json()["ai_status"] == "succeeded"
    assert timeouts == [120]


def test_free_chat_without_project_knowledge_allows_general_ai_answer(monkeypatch) -> None:
    headers = auth_headers()
    config_response = client.put(
        "/api/ai/config",
        headers=headers,
        json={
            "provider": "openai-compatible",
            "base_url": "https://model.example.com/v1",
            "api_key": "secret",
            "model": "test-model",
            "timeout_seconds": 20,
        },
    )
    assert config_response.status_code == 200
    prompts: list[str] = []

    def fake_urlopen(req, timeout):
        payload = json.loads(req.data.decode("utf-8"))
        prompts.append(payload["messages"][1]["content"])

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps({"choices": [{"message": {"content": '{"answer":"可基于通用测试知识回答"}'}}]}).encode("utf-8")

        return Response()

    monkeypatch.setattr("app.modules.ai.service.request.urlopen", fake_urlopen)

    response = client.post(
        "/api/free-chat/ask",
        headers=headers,
        json={"project_id": "project-g99-rfid", "question": "如何扩展 RFID 测试？", "use_project_knowledge": False, "use_external_model": True},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["used_model"] is True
    assert result["sources"] == []
    assert "通用知识" in prompts[0]
    assert "资料不足时说明需要补充资料" not in prompts[0]


def test_free_chat_returns_when_ai_call_hangs(monkeypatch) -> None:
    headers = auth_headers()
    config_response = client.put(
        "/api/ai/config",
        headers=headers,
        json={
            "provider": "openai-compatible",
            "base_url": "https://model.example.com/v1",
            "api_key": "secret",
            "model": "test-model",
            "timeout_seconds": 20,
        },
    )
    assert config_response.status_code == 200
    monkeypatch.setattr("app.modules.free_chat.service.get_ai_runtime_values", lambda user_id=None: ("openai-compatible", "https://model.example.com/v1", "secret", "test-model", 0.01))

    def fake_run_json_task_detailed(*args, **kwargs):
        time.sleep(0.1)

    monkeypatch.setattr("app.modules.free_chat.service.run_json_task_detailed", fake_run_json_task_detailed)

    response = client.post(
        "/api/free-chat/ask",
        headers=headers,
        json={"project_id": "project-g99-rfid", "question": "如何扩展 RFID 测试？", "use_project_knowledge": False, "use_external_model": True},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["used_model"] is False
    assert result["ai_status"] == "failed"
    assert "AI 调用超时" in result["ai_message"]
    assert "未启用项目资料库参考" in result["answer"]
    assert "项目资料库没有命中" not in result["answer"]


def test_free_chat_uses_conversation_history_for_follow_up() -> None:
    headers = auth_headers()
    risks = client.post(
        "/api/risks/parse",
        headers=headers,
        json={"project_id": "project-g99-rfid", "source_type": "jira", "content": "title\nRFID读取失败\n"},
    ).json()["items"]
    client.post("/api/risks/bulk-publish", headers=headers, json={"risk_ids": [item["id"] for item in risks]})

    response = client.post(
        "/api/free-chat/ask",
        headers=headers,
        json={
            "project_id": "project-g99-rfid",
            "question": "这些风险要怎么验证",
            "use_project_knowledge": True,
            "use_external_model": False,
            "messages": [
                {"role": "user", "content": "RFID 读取有什么风险"},
                {"role": "assistant", "content": "资料库命中 RFID 读取失败风险"},
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["sources"]
    assert "结合当前对话上下文" in result["answer"]
