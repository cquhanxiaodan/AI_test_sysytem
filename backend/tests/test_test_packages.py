from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.modules.documents.repository import DOCUMENTS
from app.modules.parsing.service import CHUNKS, TASKS
from app.modules.test_items.service import TEST_ITEMS, create_item_from_fields
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


def test_generate_rfid_supplier_change_package_reuses_legacy_rfid_package_name() -> None:
    headers = auth_headers()
    seed_rfid_items(headers)
    first = client.post(
        "/api/test-packages/generate-rfid-supplier-change?project_id=project-g99-rfid",
        headers=headers,
    ).json()
    renamed = client.patch(
        f"/api/test-packages/{first['id']}",
        headers=headers,
        json={"name": "RFID测试包"},
    ).json()
    client.post(f"/api/test-packages/{renamed['id']}/publish", headers=headers)

    second = client.post(
        "/api/test-packages/generate-rfid-supplier-change?project_id=project-g99-rfid",
        headers=headers,
    )

    assert second.status_code == 200
    assert second.json()["id"] == first["id"]
    packages = client.get("/api/test-packages?project_id=project-g99-rfid", headers=headers).json()
    assert len(packages) == 1


def test_generate_rfid_supplier_change_package_deduplicates_normalized_titles() -> None:
    headers = auth_headers()
    create_item_from_fields(
        project_id="project-g99-rfid",
        title="RFID 在机读取测试",
        test_object="RFID",
        subsystem="RFID",
        objective="验证 RFID 读取。",
        method="执行 RFID 读取。",
        record_template="记录读取结果。",
        evidence="seed",
        source_type="document",
        status="published",
    )
    create_item_from_fields(
        project_id="project-g99-rfid",
        title="RFID在机读取测试",
        test_object="RFID",
        subsystem="RFID",
        objective="验证 RFID 读取。",
        method="执行 RFID 读取。",
        record_template="记录读取结果。",
        evidence="seed",
        source_type="document",
        status="published",
    )

    response = client.post(
        "/api/test-packages/generate-rfid-supplier-change?project_id=project-g99-rfid",
        headers=headers,
    )

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert len([title for title in titles if title.replace(" ", "") == "RFID在机读取测试"]) == 1


def test_package_deduplication_keeps_same_title_in_different_modules() -> None:
    headers = auth_headers()
    first = create_item_from_fields(
        project_id="project-g99-rfid",
        title="在机读取测试",
        test_object="RFID",
        subsystem="RFID",
        objective="验证 RFID 读取。",
        method="执行 RFID 读取。",
        record_template="记录读取结果。",
        evidence="seed",
        source_type="document",
        status="published",
    )
    second = create_item_from_fields(
        project_id="project-g99-rfid",
        title="在机读取测试",
        test_object="扫码枪",
        subsystem="电子子系统",
        objective="验证扫码枪读取。",
        method="执行扫码枪读取。",
        record_template="记录读取结果。",
        evidence="seed",
        source_type="document",
        status="published",
    )
    client.post(f"/api/test-items/{first.id}/confirm", headers=headers)

    response = client.post(f"/api/test-items/{second.id}/confirm", headers=headers)

    assert response.status_code == 200
    package_items = next(iter(TEST_PACKAGES.values())).items
    assert len(package_items) == 2
    assert {item.test_item_id for item in package_items} == {first.id, second.id}


def test_package_deduplication_replaces_same_title_in_same_module() -> None:
    headers = auth_headers()
    first = create_item_from_fields(
        project_id="project-g99-rfid",
        title="RFID 在机读取测试",
        test_object="RFID",
        subsystem="RFID",
        objective="验证 RFID 读取。",
        method="执行 RFID 读取。",
        record_template="记录读取结果。",
        evidence="seed",
        source_type="document",
        status="published",
    )
    second = create_item_from_fields(
        project_id="project-g99-rfid",
        title="RFID在机读取测试",
        test_object="RFID",
        subsystem="RFID",
        objective="验证 RFID 读取。",
        method="执行 RFID 读取。",
        record_template="记录读取结果。",
        evidence="seed",
        source_type="document",
        status="published",
    )
    client.post(f"/api/test-items/{first.id}/confirm", headers=headers)

    response = client.post(f"/api/test-items/{second.id}/confirm", headers=headers)

    assert response.status_code == 200
    package_items = next(iter(TEST_PACKAGES.values())).items
    assert len(package_items) == 1
    assert package_items[0].test_item_id == second.id
    assert package_items[0].module == "RFID"


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


def test_publish_ai_generated_rfid_item_reuses_existing_rfid_package() -> None:
    headers = auth_headers()
    seed_rfid_items(headers)
    package = client.post(
        "/api/test-packages/generate-rfid-supplier-change?project_id=project-g99-rfid",
        headers=headers,
    ).json()
    item = create_item_from_fields(
        project_id="project-g99-rfid",
        title="RFID 断电重启后读写恢复测试",
        test_object="RFID",
        subsystem="RFID",
        objective="验证 RFID 断电重启后的读写恢复能力。",
        method="执行断电重启后读取和写入 RFID。",
        record_template="记录断电条件、恢复时间、读写结果和异常日志。",
        evidence="AI 补充推荐",
        source_type="ai_generated",
        status="draft",
    )

    response = client.post(f"/api/test-items/{item.id}/confirm", headers=headers)

    assert response.status_code == 200
    packages = client.get("/api/test-packages?project_id=project-g99-rfid", headers=headers).json()
    assert len(packages) == 1
    assert packages[0]["id"] == package["id"]
    assert any(package_item["test_item_id"] == item.id for package_item in packages[0]["items"])
