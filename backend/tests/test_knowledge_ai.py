from fastapi.testclient import TestClient

from app.main import app
from app.modules.risks.service import RISKS
from app.modules.test_items.service import TEST_ITEMS
from app.modules.test_packages.service import TEST_PACKAGES


client = TestClient(app)


def setup_function() -> None:
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
