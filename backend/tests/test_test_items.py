from fastapi.testclient import TestClient

from app.main import app
from app.modules.documents.repository import DOCUMENTS
from app.modules.parsing.service import CHUNKS, TASKS
from app.modules.test_items.service import TEST_ITEMS


client = TestClient(app)


def setup_function() -> None:
    DOCUMENTS.clear()
    TASKS.clear()
    CHUNKS.clear()
    TEST_ITEMS.clear()


def auth_headers() -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_split_rfid_document_creates_five_items() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("DNBSEQ-G99 RFID验证方案.txt", b"RFID supplier change validation", "text/plain")},
    )
    document_id = upload.json()["document"]["id"]
    client.post(f"/api/parsing/documents/{document_id}/parse", headers=headers)

    response = client.post(f"/api/test-items/split/{document_id}", headers=headers)

    assert response.status_code == 200
    titles = {item["title"] for item in response.json()["items"]}
    assert titles == {
        "RFID 在机装配测试",
        "RFID 装配后初始化测试",
        "RFID 在机读取测试",
        "RFID 在机写入测试",
        "安规 EMC 测试",
    }


def test_confirm_test_item_publishes_asset() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.txt", b"RFID", "text/plain")},
    )
    document_id = upload.json()["document"]["id"]
    split = client.post(f"/api/test-items/split/{document_id}", headers=headers)
    item_id = split.json()["items"][0]["id"]

    response = client.post(f"/api/test-items/{item_id}/confirm", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "published"


def test_split_document_uses_ai_items(monkeypatch) -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.txt", b"3.1 RFID read test", "text/plain")},
    )
    document_id = upload.json()["document"]["id"]
    client.post(f"/api/parsing/documents/{document_id}/parse", headers=headers)

    def fake_run_json_task(*args, **kwargs):
        return {
            "items": [
                {
                    "title": "AI RFID 异常恢复测试",
                    "test_object": "RFID",
                    "primary_subsystem": "RFID",
                    "related_subsystems": ["整机系统"],
                    "test_level": "系统级",
                    "test_type": "异常恢复",
                    "risk_tags": ["供应商变更"],
                    "objective": "验证 RFID 异常恢复能力。",
                    "method": "模拟读取异常后恢复。",
                    "tools": ["DNBSEQ-G99"],
                    "steps": ["触发异常", "执行恢复"],
                    "record_template": "记录异常和恢复结果。",
                    "evidence": "3.1 RFID read test",
                }
            ],
            "evidence": "3.1 RFID read test",
        }

    monkeypatch.setattr("app.modules.test_items.service.run_json_task", fake_run_json_task)

    response = client.post(f"/api/test-items/split/{document_id}", headers=headers)

    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == ["AI RFID 异常恢复测试"]
