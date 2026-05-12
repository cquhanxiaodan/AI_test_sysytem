from fastapi.testclient import TestClient

from app.main import app
from app.modules.documents.repository import DOCUMENTS, DOCUMENT_CONTENTS
from app.modules.parsing.service import CHUNKS, TASKS
from app.modules.test_items.service import TEST_ITEMS


client = TestClient(app)


def setup_function() -> None:
    DOCUMENTS.clear()
    DOCUMENT_CONTENTS.clear()
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
