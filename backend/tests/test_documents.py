from fastapi.testclient import TestClient

from app.main import app
from app.modules.documents.repository import DOCUMENTS


client = TestClient(app)


def auth_headers(username: str = "admin", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def setup_function() -> None:
    DOCUMENTS.clear()


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
    assert {item["label_key"] for item in document["label_suggestions"]} >= {"product_model", "subsystem", "document_type"}


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


def test_tester_cannot_access_unassigned_project_upload() -> None:
    response = client.post(
        "/api/documents/upload",
        headers=auth_headers("tester", "tester123"),
        data={"project_id": "project-mgi-platform"},
        files={"file": ("platform.docx", b"demo", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert response.status_code == 403
