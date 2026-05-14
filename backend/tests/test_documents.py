from fastapi.testclient import TestClient

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
        json={"labels": {"product_model": "DNBSEQ-G99", "subsystem": "RFID", "document_type": "验证方案"}},
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
        json={"labels": {"product_model": "DNBSEQ-G99", "subsystem": "RFID", "document_type": "验证方案"}},
    )

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
