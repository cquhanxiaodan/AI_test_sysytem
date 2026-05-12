from fastapi.testclient import TestClient

from app.main import app
from app.modules.admin.service import AUDIT_EVENTS


client = TestClient(app)


def setup_function() -> None:
    AUDIT_EVENTS.clear()


def auth_headers(username: str = "admin", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_get_system_config() -> None:
    response = client.get("/api/admin/config", headers=auth_headers())

    assert response.status_code == 200
    assert "RFID" in response.json()["subsystem_catalog"]


def test_create_and_list_audit_event() -> None:
    headers = auth_headers()
    created = client.post(
        "/api/admin/audits",
        headers=headers,
        json={"action": "publish", "target_type": "document", "target_id": "doc-1", "detail": "发布资料"},
    )

    assert created.status_code == 200

    listed = client.get("/api/admin/audits", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["action"] == "publish"


def test_acceptance_status_available() -> None:
    response = client.get("/api/admin/acceptance-status", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["frontend_build"] == "passed"
