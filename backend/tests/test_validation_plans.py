from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.modules.documents.repository import DOCUMENTS
from app.modules.parsing.service import CHUNKS, TASKS
from app.modules.requirements.service import ANALYSES
from app.modules.risks.service import RISKS
from app.modules.test_items.service import TEST_ITEMS
from app.modules.test_packages.service import TEST_PACKAGES
from app.modules.validation_plans.service import EXPORTS, PLANS


client = TestClient(app)


def setup_function() -> None:
    DOCUMENTS.clear()
    TASKS.clear()
    CHUNKS.clear()
    TEST_ITEMS.clear()
    TEST_PACKAGES.clear()
    RISKS.clear()
    ANALYSES.clear()
    PLANS.clear()
    EXPORTS.clear()


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


def create_analysis(headers: dict[str, str]) -> str:
    response = client.post(
        "/api/requirement-analyses",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_create_plan_from_project_batches_all_analyses() -> None:
    headers = auth_headers()
    seed_assets(headers)
    create_analysis(headers)
    create_analysis(headers)

    created = client.post("/api/validation-plans", headers=headers, json={"project_id": "project-g99-rfid"})

    assert created.status_code == 200
    plan = created.json()
    assert plan["template_version"] == "validation-plan-v1"
    assert len(plan["requirement_analysis_ids"]) == 2
    assert len(plan["items"]) > 0

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


def test_create_plan_from_single_analysis_still_works() -> None:
    headers = auth_headers()
    seed_assets(headers)
    analysis_id = create_analysis(headers)

    created = client.post("/api/validation-plans", headers=headers, json={"requirement_analysis_id": analysis_id})

    assert created.status_code == 200
    plan = created.json()
    assert len(plan["requirement_analysis_ids"]) == 1


def test_validation_plan_check_merges_ai_messages(monkeypatch) -> None:
    headers = auth_headers()
    seed_assets(headers)
    create_analysis(headers)
    created = client.post("/api/validation-plans", headers=headers, json={"project_id": "project-g99-rfid"})
    plan_id = created.json()["id"]

    def fake_run_json_task(*args, **kwargs):
        return {"blocking": [], "warnings": ["AI 提示需确认 RFID DUT 批次。"], "suggestions": ["AI 建议补充异常恢复记录。"]}

    monkeypatch.setattr("app.modules.validation_plans.service.run_json_task", fake_run_json_task)

    checked = client.post(f"/api/validation-plans/{plan_id}/check", headers=headers)

    assert checked.status_code == 200
    result = checked.json()
    assert "AI 提示需确认 RFID DUT 批次。" in result["warnings"]
    assert "AI 建议补充异常恢复记录。" in result["suggestions"]
