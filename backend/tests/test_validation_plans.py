from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.modules.requirements.service import ANALYSES
from app.modules.validation_plans.service import EXPORTS, PLANS


client = TestClient(app)


def setup_function() -> None:
    ANALYSES.clear()
    PLANS.clear()
    EXPORTS.clear()


def auth_headers() -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_analysis(headers: dict[str, str]) -> str:
    response = client.post(
        "/api/requirement-analyses",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_create_check_and_export_validation_plan() -> None:
    headers = auth_headers()
    analysis_id = create_analysis(headers)

    created = client.post("/api/validation-plans", headers=headers, json={"requirement_analysis_id": analysis_id})

    assert created.status_code == 200
    plan = created.json()
    assert plan["template_version"] == "validation-plan-v1"

    checked = client.post(f"/api/validation-plans/{plan['id']}/check", headers=headers)
    assert checked.status_code == 200
    assert "blocking" in checked.json()

    exported = client.post(f"/api/validation-plans/{plan['id']}/export", headers=headers)
    assert exported.status_code == 200
    export_record = exported.json()
    assert export_record["filename"].endswith(".docx")
    assert Path(export_record["storage_path"]).exists()

    downloaded = client.get(export_record["download_url"], headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"PK")
