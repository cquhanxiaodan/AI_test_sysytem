from fastapi.testclient import TestClient

from app.main import app
from app.modules.documents.repository import DOCUMENTS
from app.modules.parsing.service import CHUNKS, TASKS


client = TestClient(app)


def setup_function() -> None:
    DOCUMENTS.clear()
    TASKS.clear()
    CHUNKS.clear()


def auth_headers() -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def upload_demo(headers: dict[str, str]) -> str:
    response = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("DNBSEQ-G99 RFID验证方案.txt", b"3.1 RFID read test\nstep one", "text/plain")},
    )
    assert response.status_code == 200
    return response.json()["document"]["id"]


def test_parse_document_creates_chunks() -> None:
    headers = auth_headers()
    document_id = upload_demo(headers)

    response = client.post(f"/api/parsing/documents/{document_id}/parse", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert len(response.json()["chunks"]) == 2


def test_label_extraction_updates_high_confidence_labels() -> None:
    headers = auth_headers()
    document_id = upload_demo(headers)

    response = client.post(f"/api/parsing/documents/{document_id}/extract-labels", headers=headers)

    assert response.status_code == 200

    document = client.get(f"/api/documents/{document_id}", headers=headers).json()
    assert document["labels"]["product_model"] == "DNBSEQ-G99"
    assert document["labels"]["subsystem"] == "RFID"
