from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.modules.documents.repository import DOCUMENTS, get_document_content
from app.modules.parsing.service import CHUNKS, TASKS
from app.modules.risks.service import RISKS
from app.modules.test_items.service import TEST_ITEMS
from app.modules.test_packages.service import TEST_PACKAGES


client = TestClient(app)


def auth_headers(username: str = "admin", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def setup_function() -> None:
    from app.modules.admin import service as admin_service
    from app.modules.documents.router import RUNTIME_IMPORT_CONFIG

    admin_service.CONFIG = admin_service.DEFAULT_CONFIG.model_copy(deep=True)
    admin_service.get_settings().repository_backend = "memory"
    admin_service.get_settings().system_config_path = f"/tmp/monkeycode-test-system-config-{uuid4()}.json"
    RUNTIME_IMPORT_CONFIG.clear()
    DOCUMENTS.clear()
    TASKS.clear()
    CHUNKS.clear()
    TEST_ITEMS.clear()
    TEST_PACKAGES.clear()
    RISKS.clear()


def test_upload_document_suggests_labels() -> None:
    response = client.post(
        "/api/documents/upload",
        headers=auth_headers(),
        data={"project_id": "project-g99-rfid"},
        files={"file": ("DNBSEQ-G99 RFID验证方案.docx", b"demo", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert response.status_code == 200
    document = response.json()["document"]
    assert document["status"] == "pending_label"
    assert document["storage_path"]
    assert get_document_content(document["id"]) == b"demo"
    assert {item["label_key"] for item in document["label_suggestions"]} >= {"product_model", "subsystem", "document_type"}
    labels = {item["label_key"]: item["label_value"] for item in document["label_suggestions"]}
    assert labels["subsystem"] == "电子子系统"
    assert labels["module"] == "RFID"


def test_document_label_suggestions_use_system_config_options() -> None:
    headers = auth_headers()
    config = client.put(
        "/api/admin/config",
        headers=headers,
        json={"subsystem_catalog": ["电子子系统", "液路系统"], "change_types": ["供应商变更", "软件变更"]},
    )
    assert config.status_code == 200

    response = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("DNBSEQ-G99 康奈特RFID二供验证方案.docx", b"demo", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert response.status_code == 200
    labels = {item["label_key"]: item["label_value"] for item in response.json()["document"]["label_suggestions"]}
    assert labels["subsystem"] == "电子子系统"
    assert labels["module"] == "RFID"
    assert labels["change_type"] == "供应商变更"


def test_batch_upload_documents() -> None:
    response = client.post(
        "/api/documents/upload-batch",
        headers=auth_headers(),
        data={"project_id": "project-g99-rfid"},
        files=[
            ("files", ("DNBSEQ-G99 RFID验证方案.docx", b"demo-1", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ("files", ("jira-rfid.csv", "title\nRFID读取失败\n".encode("utf-8"), "text/csv")),
        ],
    )

    assert response.status_code == 200
    documents = response.json()["documents"]
    assert len(documents) == 2
    assert documents[0]["status"] == "pending_label"
    assert documents[1]["status"] == "pending_label"


def test_scan_import_directory_imports_new_files(tmp_path) -> None:
    headers = auth_headers()
    import_dir = tmp_path / "imports"
    import_dir.mkdir()
    (import_dir / "DNBSEQ-G99 RFID验证方案.txt").write_bytes(b"RFID validation")
    (import_dir / "jira-rfid.csv").write_text("title\nRFID读取失败\n", encoding="utf-8")

    config_response = client.put(
        "/api/documents/import-config",
        headers=headers,
        json={"import_directory": str(import_dir)},
    )
    assert config_response.status_code == 200
    assert config_response.json()["configured"] is True

    first_scan = client.post(
        "/api/documents/scan-import-directory",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
    )

    assert first_scan.status_code == 200
    assert len(first_scan.json()["imported"]) == 2
    assert first_scan.json()["skipped"] == []

    second_scan = client.post(
        "/api/documents/scan-import-directory",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
    )

    assert second_scan.status_code == 200
    assert second_scan.json()["imported"] == []
    assert set(second_scan.json()["skipped"]) == {"DNBSEQ-G99 RFID验证方案.txt", "jira-rfid.csv"}


def test_tester_cannot_update_import_directory() -> None:
    response = client.put(
        "/api/documents/import-config",
        headers=auth_headers("tester", "tester123"),
        json={"import_directory": "/data/imports"},
    )

    assert response.status_code == 403


def test_import_directory_persists_to_settings_file(tmp_path) -> None:
    from app.modules.admin import service as admin_service
    from app.modules.documents.router import RUNTIME_IMPORT_CONFIG

    admin_service.get_settings().system_config_path = str(tmp_path / "system-config.json")
    import_dir = tmp_path / "imports"
    import_dir.mkdir()

    response = client.put(
        "/api/documents/import-config",
        headers=auth_headers(),
        json={"import_directory": str(import_dir)},
    )
    assert response.status_code == 200

    RUNTIME_IMPORT_CONFIG.clear()
    persisted = client.get("/api/documents/import-config", headers=auth_headers())

    assert persisted.status_code == 200
    assert persisted.json() == {"import_directory": str(import_dir), "configured": True}


def test_bulk_delete_removes_unpublished_documents() -> None:
    headers = auth_headers()
    first = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("keep-out.txt", b"ignore me", "text/plain")},
    ).json()["document"]
    second = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("also-ignore.txt", b"ignore me too", "text/plain")},
    ).json()["document"]

    response = client.post(
        "/api/documents/bulk-delete",
        headers=headers,
        json={"document_ids": [first["id"], second["id"]]},
    )

    assert response.status_code == 200
    assert set(response.json()["deleted_ids"]) == {first["id"], second["id"]}
    remaining = client.get("/api/documents", headers=headers, params={"project_id": "project-g99-rfid"})
    assert remaining.json() == []


def test_bulk_delete_allows_published_documents_for_flow_retest() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.docx", b"demo", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    document_id = upload.json()["document"]["id"]
    client.patch(
        f"/api/documents/{document_id}/labels",
        headers=headers,
        json={"labels": {"product_model": "DNBSEQ-G99", "subsystem": "电子子系统", "module": "RFID", "document_type": "验证方案"}},
    )
    client.post(f"/api/documents/{document_id}/review", headers=headers, json={"action": "publish"})

    response = client.post(
        "/api/documents/bulk-delete",
        headers=headers,
        json={"document_ids": [document_id]},
    )

    assert response.status_code == 200
    assert response.json()["deleted_ids"] == [document_id]
    assert response.json()["skipped"] == []
    assert document_id not in DOCUMENTS


def test_document_label_update_moves_to_review() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.docx", b"demo", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    document_id = upload.json()["document"]["id"]

    response = client.patch(
        f"/api/documents/{document_id}/labels",
        headers=headers,
        json={"labels": {"product_model": "DNBSEQ-G99", "subsystem": "电子子系统", "module": "RFID", "document_type": "验证方案"}},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending_review"


def test_admin_can_publish_document() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.docx", b"demo", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    document_id = upload.json()["document"]["id"]

    response = client.post(
        f"/api/documents/{document_id}/review",
        headers=headers,
        json={"action": "publish", "comment": "通过"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "published"


def test_publish_validation_plan_auto_generates_test_assets() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("DNBSEQ-G99 RFID验证方案.txt", b"RFID supplier change validation", "text/plain")},
    )
    document_id = upload.json()["document"]["id"]
    client.patch(
        f"/api/documents/{document_id}/labels",
        headers=headers,
        json={"labels": {"product_model": "DNBSEQ-G99", "subsystem": "电子子系统", "module": "RFID", "document_type": "验证方案"}},
    )

    response = client.post(f"/api/documents/{document_id}/review", headers=headers, json={"action": "publish"})

    assert response.status_code == 200
    assert len(TEST_ITEMS) == 5
    assert len(TEST_PACKAGES) == 1


def test_publish_validation_plan_infers_type_from_filename() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("DNBSEQ-G99 RFID验证方案.txt", b"RFID supplier change validation", "text/plain")},
    )
    document_id = upload.json()["document"]["id"]

    response = client.post(f"/api/documents/{document_id}/review", headers=headers, json={"action": "publish"})

    assert response.status_code == 200
    assert len(TEST_ITEMS) == 5
    assert len(TEST_PACKAGES) == 1


def test_publish_jira_document_auto_parses_risks() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("jira-rfid.csv", "title,description\nRFID读取失败,供应商变更后偶发失败\n".encode("utf-8"), "text/csv")},
    )
    document_id = upload.json()["document"]["id"]
    client.patch(
        f"/api/documents/{document_id}/labels",
        headers=headers,
        json={"labels": {"document_type": "Jira导出", "subsystem": "RFID"}},
    )

    response = client.post(f"/api/documents/{document_id}/review", headers=headers, json={"action": "publish"})

    assert response.status_code == 200
    assert len(RISKS) == 1


def test_tester_cannot_access_unassigned_project_upload() -> None:
    response = client.post(
        "/api/documents/upload",
        headers=auth_headers("tester", "tester123"),
        data={"project_id": "project-mgi-platform"},
        files={"file": ("platform.docx", b"demo", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert response.status_code == 403


def test_document_pool_list_is_global_when_project_filter_omitted() -> None:
    headers = auth_headers()
    first = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("g99.txt", b"g99", "text/plain")},
    ).json()["document"]
    second = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-mgi-platform"},
        files={"file": ("platform.txt", b"platform", "text/plain")},
    ).json()["document"]

    response = client.get("/api/documents", headers=headers)

    assert response.status_code == 200
    assert {document["id"] for document in response.json()} == {first["id"], second["id"]}
