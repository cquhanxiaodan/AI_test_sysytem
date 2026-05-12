from fastapi.testclient import TestClient

from app.main import app
from app.modules.documents.repository import DOCUMENTS, DOCUMENT_CONTENTS
from app.modules.parsing.service import CHUNKS, TASKS
from app.modules.test_items.service import TEST_ITEMS
from app.modules.test_packages.service import TEST_PACKAGES


client = TestClient(app)


def setup_function() -> None:
    DOCUMENTS.clear()
    DOCUMENT_CONTENTS.clear()
    TASKS.clear()
    CHUNKS.clear()
    TEST_ITEMS.clear()
    TEST_PACKAGES.clear()


def auth_headers() -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def seed_rfid_items(headers: dict[str, str]) -> None:
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.txt", b"RFID", "text/plain")},
    )
    document_id = upload.json()["document"]["id"]
    client.post(f"/api/test-items/split/{document_id}", headers=headers)


def test_generate_rfid_supplier_change_package() -> None:
    headers = auth_headers()
    seed_rfid_items(headers)

    response = client.post(
        "/api/test-packages/generate-rfid-supplier-change?project_id=project-g99-rfid",
        headers=headers,
    )

    assert response.status_code == 200
    package = response.json()
    assert package["name"] == "RFID 供应商变更验证包"
    assert {item["relation_type"] for item in package["items"]} == {"required", "suggested", "conditional"}


def test_publish_test_package() -> None:
    headers = auth_headers()
    seed_rfid_items(headers)
    package = client.post(
        "/api/test-packages/generate-rfid-supplier-change?project_id=project-g99-rfid",
        headers=headers,
    ).json()

    response = client.post(f"/api/test-packages/{package['id']}/publish", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "published"
