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
