from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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
