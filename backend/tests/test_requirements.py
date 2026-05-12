from fastapi.testclient import TestClient

from app.main import app
from app.modules.documents.repository import DOCUMENTS, DOCUMENT_CONTENTS
from app.modules.parsing.service import CHUNKS, TASKS
from app.modules.requirements.service import ANALYSES
from app.modules.risks.service import RISKS
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
    RISKS.clear()
    ANALYSES.clear()


def auth_headers() -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def seed_assets(headers: dict[str, str]) -> None:
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.txt", b"RFID", "text/plain")},
    )
    document_id = upload.json()["document"]["id"]
    client.post(f"/api/test-items/split/{document_id}", headers=headers)
    client.post("/api/test-packages/generate-rfid-supplier-change?project_id=project-g99-rfid", headers=headers)
    client.post(
        "/api/risks/parse",
        headers=headers,
        json={"project_id": "project-g99-rfid", "source_type": "jira", "content": "title\nRFID读取失败\n"},
    )


def test_requirement_analysis_recommends_rfid_package_and_risks() -> None:
    headers = auth_headers()
    seed_assets(headers)

    response = client.post(
        "/api/requirement-analyses",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    )

    assert response.status_code == 200
    analysis = response.json()
    assert analysis["parse_result"]["test_object"] == "RFID"
    groups = {item["group"] for item in analysis["recommendations"]}
    assert {"必测", "建议", "条件触发", "风险补充"}.issubset(groups)
