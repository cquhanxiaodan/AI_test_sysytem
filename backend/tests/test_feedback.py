from fastapi.testclient import TestClient

from app.main import app
from app.modules.feedback.service import FEEDBACK_ITEMS

client = TestClient(app)


def setup_function() -> None:
    from app.modules.admin import service as admin_service

    admin_service.get_settings().repository_backend = "memory"
    FEEDBACK_ITEMS.clear()


def auth_headers(username: str = "tester", password: str = "tester123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_user_can_submit_feedback() -> None:
    response = client.post(
        "/api/feedback",
        headers=auth_headers(),
        json={"feedback_type": "bug", "content": "导出验证方案时目录没有刷新。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submitter_name"] == "测试工程师"
    assert payload["feedback_type"] == "bug"
    assert payload["status"] == "pending"
    assert payload["content"] == "导出验证方案时目录没有刷新。"
    assert payload["submit_date"]


def test_user_only_sees_own_feedback_and_admin_sees_all() -> None:
    tester_headers = auth_headers()
    admin_headers = auth_headers("admin", "admin123")
    client.post("/api/feedback", headers=tester_headers, json={"feedback_type": "requirement", "content": "增加批量审核。"})
    client.post("/api/feedback", headers=admin_headers, json={"feedback_type": "bug", "content": "管理员提交的问题。"})

    tester_list = client.get("/api/feedback", headers=tester_headers)
    admin_list = client.get("/api/feedback", headers=admin_headers)

    assert tester_list.status_code == 200
    assert len(tester_list.json()) == 1
    assert tester_list.json()[0]["submitter_name"] == "测试工程师"
    assert len(admin_list.json()) == 2


def test_admin_can_reply_and_update_status() -> None:
    create_response = client.post(
        "/api/feedback",
        headers=auth_headers(),
        json={"feedback_type": "requirement", "content": "新增需求反馈入口。"},
    )
    feedback_id = create_response.json()["id"]

    response = client.patch(
        f"/api/feedback/{feedback_id}",
        headers=auth_headers("admin", "admin123"),
        json={"status": "processing", "admin_reply": "已纳入版本计划。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "processing"
    assert payload["admin_reply"] == "已纳入版本计划。"
    assert payload["replied_by"] == "管理员"
    assert payload["replied_at"]


def test_tester_cannot_reply_feedback() -> None:
    create_response = client.post(
        "/api/feedback",
        headers=auth_headers(),
        json={"feedback_type": "bug", "content": "普通用户提交的问题。"},
    )

    response = client.patch(
        f"/api/feedback/{create_response.json()['id']}",
        headers=auth_headers(),
        json={"status": "resolved", "admin_reply": "自行关闭。"},
    )

    assert response.status_code == 403
