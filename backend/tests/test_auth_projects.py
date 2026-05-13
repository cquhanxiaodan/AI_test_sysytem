from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.seed_data import PROJECTS


client = TestClient(app)


def setup_function() -> None:
    for project_id in list(PROJECTS):
        if project_id not in {"project-g99-rfid", "project-mgi-platform"}:
            PROJECTS.pop(project_id)


def login(username: str = "admin", password: str = "admin123") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_login_and_me() -> None:
    token = login()

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["roles"] == ["admin"]


def test_login_rejects_invalid_password() -> None:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})

    assert response.status_code == 401


def test_project_list_is_filtered_by_membership() -> None:
    token = login("tester", "tester123")

    response = client.get("/api/projects", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    project_ids = {project["id"] for project in response.json()}
    assert project_ids == {"project-g99-rfid"}


def test_project_detail_denies_unassigned_user() -> None:
    token = login("tester", "tester123")

    response = client.get(
        "/api/projects/project-mgi-platform",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_create_project_space_for_tester() -> None:
    token = login("tester", "tester123")

    response = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "code": "TEST-G99-RFID",
            "name": "测试项目空间",
            "description": "用于验证项目创建",
        },
    )

    assert response.status_code == 200
    project = response.json()
    assert project["role"] == "owner"
    assert project["document_rules"] == []


def test_delete_project_requires_current_password() -> None:
    token = login("tester", "tester123")
    created = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "TEST-DELETE", "name": "待删除项目空间"},
    )
    project_id = created.json()["id"]

    rejected = client.request(
        "DELETE",
        f"/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": "bad-password"},
    )
    assert rejected.status_code == 403

    deleted = client.request(
        "DELETE",
        f"/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": "tester123"},
    )
    assert deleted.status_code == 204


def test_project_workspace_stats_returns_next_steps() -> None:
    token = login("tester", "tester123")
    created = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "TEST-STATS", "name": "统计项目空间"},
    )
    project_id = created.json()["id"]

    response = client.get(f"/api/projects/{project_id}/workspace-stats", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    stats = response.json()
    assert stats["published_documents"] == 0
    assert stats["test_items"] == 0
    assert stats["next_steps"]
