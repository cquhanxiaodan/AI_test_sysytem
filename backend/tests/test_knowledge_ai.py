from fastapi.testclient import TestClient

from app.main import app
from app.modules.ai.service import RUNTIME_AI_CONFIG
from app.modules.risks.service import RISKS
from app.modules.test_items.service import TEST_ITEMS
from app.modules.test_packages.service import TEST_PACKAGES


client = TestClient(app)


def setup_function() -> None:
    RUNTIME_AI_CONFIG.clear()
    RISKS.clear()
    TEST_ITEMS.clear()
    TEST_PACKAGES.clear()


def auth_headers(username: str = "admin", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_knowledge_search_returns_project_scoped_results() -> None:
    headers = auth_headers()
    client.post(
        "/api/risks/parse",
        headers=headers,
        json={"project_id": "project-g99-rfid", "source_type": "jira", "content": "title\nRFID读取失败\n"},
    )

    response = client.post(
        "/api/knowledge/search",
        headers=headers,
        json={"project_id": "project-g99-rfid", "query": "RFID 读取"},
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["source_type"] == "risk"


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


def test_ai_config_reports_local_fallback_by_default() -> None:
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


def test_free_chat_returns_local_knowledge_answer() -> None:
    headers = auth_headers()
    client.post(
        "/api/risks/parse",
        headers=headers,
        json={"project_id": "project-g99-rfid", "source_type": "jira", "content": "title\nRFID读取失败\n"},
    )

    response = client.post(
        "/api/free-chat/ask",
        headers=headers,
        json={"project_id": "project-g99-rfid", "question": "RFID 读取有什么风险", "use_project_knowledge": True, "use_external_model": False},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["used_model"] is False
    assert result["sources"]
    assert "RFID" in result["answer"]
