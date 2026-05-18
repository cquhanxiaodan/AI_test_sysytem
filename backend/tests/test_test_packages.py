from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.modules.documents.repository import DOCUMENTS
from app.modules.parsing.service import CHUNKS, TASKS
from app.modules.test_items.service import TEST_ITEMS
from app.modules.test_packages.service import TEST_PACKAGES


client = TestClient(app)


def setup_function() -> None:
    from app.modules.admin import service as admin_service
    from app.modules.ai.service import RUNTIME_AI_CONFIG

    admin_service.get_settings().repository_backend = "memory"
    admin_service.get_settings().system_config_path = f"/tmp/monkeycode-test-system-config-{uuid4()}.json"
    RUNTIME_AI_CONFIG.clear()
    DOCUMENTS.clear()
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
    assert package["name"] == "RFID测试归口包"
    assert len(package["items"]) == 5
    assert {item["relation_type"] for item in package["items"]} == {"required", "suggested", "conditional"}


def test_generate_rfid_supplier_change_package_reuses_existing_package() -> None:
    headers = auth_headers()
    seed_rfid_items(headers)
    first = client.post(
        "/api/test-packages/generate-rfid-supplier-change?project_id=project-g99-rfid",
        headers=headers,
    ).json()
    client.post(f"/api/test-packages/{first['id']}/publish", headers=headers)

    second = client.post(
        "/api/test-packages/generate-rfid-supplier-change?project_id=project-g99-rfid",
        headers=headers,
    )

    assert second.status_code == 200
    assert second.json()["id"] == first["id"]
    assert second.json()["status"] == "published"
    packages = client.get("/api/test-packages?project_id=project-g99-rfid", headers=headers).json()
    assert len(packages) == 1


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


def test_update_test_package_returns_to_draft() -> None:
    headers = auth_headers()
    seed_rfid_items(headers)
    package = client.post(
        "/api/test-packages/generate-rfid-supplier-change?project_id=project-g99-rfid",
        headers=headers,
    ).json()
    client.post(f"/api/test-packages/{package['id']}/publish", headers=headers)

    response = client.patch(
        f"/api/test-packages/{package['id']}",
        headers=headers,
        json={"name": "RFID测试归口包 V2", "recommendation_level": "medium"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "RFID测试归口包 V2"
    assert response.json()["recommendation_level"] == "medium"
    assert response.json()["status"] == "draft"


def test_delete_test_package() -> None:
    headers = auth_headers()
    seed_rfid_items(headers)
    package = client.post(
        "/api/test-packages/generate-rfid-supplier-change?project_id=project-g99-rfid",
        headers=headers,
    ).json()

    response = client.delete(f"/api/test-packages/{package['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["deleted_id"] == package["id"]
    assert client.get("/api/test-packages", headers=headers).json() == []


def test_bulk_publish_test_packages() -> None:
    headers = auth_headers()
    seed_rfid_items(headers)
    first = client.post(
        "/api/test-packages/generate-rfid-supplier-change?project_id=project-g99-rfid",
        headers=headers,
    ).json()
    second_upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-mgi-platform"},
        files={"file": ("RFID验证方案.txt", b"RFID", "text/plain")},
    )
    client.post(f"/api/test-items/split/{second_upload.json()['document']['id']}", headers=headers)
    second = client.post(
        "/api/test-packages/generate-rfid-supplier-change?project_id=project-mgi-platform",
        headers=headers,
    ).json()

    response = client.post("/api/test-packages/bulk-publish", headers=headers, json={"package_ids": [first["id"], second["id"]]})

    assert response.status_code == 200
    assert set(response.json()["published_ids"]) == {first["id"], second["id"]}
    statuses = {package["id"]: package["status"] for package in client.get("/api/test-packages", headers=headers).json()}
    assert {statuses[first["id"]], statuses[second["id"]]} == {"published"}
