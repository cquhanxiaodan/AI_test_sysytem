from fastapi.testclient import TestClient

from app.main import app
from app.modules.risks.service import RISKS


client = TestClient(app)


def setup_function() -> None:
    RISKS.clear()


def auth_headers() -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_parse_jira_risk() -> None:
    response = client.post(
        "/api/risks/parse",
        headers=auth_headers(),
        json={
            "project_id": "project-g99-rfid",
            "source_type": "jira",
            "content": "key,title,description,severity\nG99-1,RFID读取失败,更换供应商后偶发读取失败,High\n",
        },
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["source_type"] == "jira"
    assert item["subsystem"] == "RFID"
    assert "读取" in item["suggested_test"]


def test_parse_dfmea_risk() -> None:
    response = client.post(
        "/api/risks/parse",
        headers=auth_headers(),
        json={
            "project_id": "project-g99-rfid",
            "source_type": "dfmea",
            "content": "dfmea_id,failure_mode,failure_effect,rpn\nD-1,RFID写入失败,样本信息无法绑定,120\n",
        },
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["source_type"] == "dfmea"
    assert item["rpn"] == 120
    assert "写入" in item["suggested_test"]


def test_list_risks_filters_by_project() -> None:
    headers = auth_headers()
    client.post(
        "/api/risks/parse",
        headers=headers,
        json={"project_id": "project-g99-rfid", "source_type": "jira", "content": "title\nRFID读取失败\n"},
    )

    response = client.get("/api/risks?project_id=project-g99-rfid&subsystem=RFID", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_parse_risks_uses_ai_items(monkeypatch) -> None:
    def fake_run_json_task(*args, **kwargs):
        return {
            "items": [
                {
                    "source_id": "AI-1",
                    "title": "RFID 初始化异常",
                    "description": "供应商变更后初始化偶发失败",
                    "test_object": "RFID",
                    "subsystem": "RFID",
                    "severity": "High",
                    "rpn": 96,
                    "failure_mode": "初始化失败",
                    "suggested_test": "补充 RFID 初始化异常恢复测试。",
                    "status": "active",
                }
            ],
            "evidence": "初始化偶发失败",
        }

    monkeypatch.setattr("app.modules.risks.service.run_json_task", fake_run_json_task)

    response = client.post(
        "/api/risks/parse",
        headers=auth_headers(),
        json={"project_id": "project-g99-rfid", "source_type": "jira", "content": "title\nRFID 初始化异常\n"},
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["source_id"] == "jira-unknown"
    assert item["rpn"] == 96


def test_update_risk() -> None:
    headers = auth_headers()
    created = client.post(
        "/api/risks/parse",
        headers=headers,
        json={"project_id": "project-g99-rfid", "source_type": "jira", "content": "title\nRFID读取失败\n"},
    ).json()["items"][0]

    response = client.patch(
        f"/api/risks/{created['id']}",
        headers=headers,
        json={"title": "RFID 读取稳定性风险", "rpn": 88, "status": "reviewed"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "RFID 读取稳定性风险"
    assert response.json()["rpn"] == 88
    assert response.json()["status"] == "reviewed"


def test_delete_risk() -> None:
    headers = auth_headers()
    created = client.post(
        "/api/risks/parse",
        headers=headers,
        json={"project_id": "project-g99-rfid", "source_type": "jira", "content": "title\nRFID读取失败\n"},
    ).json()["items"][0]

    response = client.delete(f"/api/risks/{created['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["deleted_id"] == created["id"]
    assert client.get("/api/risks", headers=headers).json() == []


def test_bulk_publish_risks() -> None:
    headers = auth_headers()
    created = client.post(
        "/api/risks/parse",
        headers=headers,
        json={"project_id": "project-g99-rfid", "source_type": "jira", "content": "title\nRFID读取失败\nRFID写入失败\n"},
    ).json()["items"]
    risk_ids = [item["id"] for item in created]

    response = client.post("/api/risks/bulk-publish", headers=headers, json={"risk_ids": risk_ids})

    assert response.status_code == 200
    assert set(response.json()["published_ids"]) == set(risk_ids)
    statuses = {risk["id"]: risk["status"] for risk in client.get("/api/risks", headers=headers).json()}
    assert {statuses[risk_id] for risk_id in risk_ids} == {"published"}
