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
    from uuid import uuid4

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
        "/api/requirement-analyses/local",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def update_recommendation_status(headers: dict[str, str], analysis_id: str, index: int, review_status: str) -> dict:
    analysis = client.get(f"/api/requirement-analyses/{analysis_id}", headers=headers).json()
    recommendation_id = analysis["recommendations"][index]["id"]
    response = client.patch(
        f"/api/requirement-analyses/{analysis_id}/recommendations/{recommendation_id}",
        headers=headers,
        json={"review_status": review_status},
    )
    assert response.status_code == 200
    return response.json()["recommendations"][index]


def test_create_plan_from_project_batches_all_analyses(monkeypatch) -> None:
    monkeypatch.setattr("app.modules.validation_plans.service.run_json_task", lambda *args, **kwargs: None)
    headers = auth_headers()
    seed_assets(headers)
    first_analysis_id = create_analysis(headers)
    second_analysis_id = create_analysis(headers)
    update_recommendation_status(headers, first_analysis_id, 0, "confirmed")
    update_recommendation_status(headers, second_analysis_id, 0, "confirmed")

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
    update_recommendation_status(headers, analysis_id, 0, "confirmed")

    created = client.post("/api/validation-plans", headers=headers, json={"requirement_analysis_id": analysis_id})

    assert created.status_code == 200
    plan = created.json()
    assert len(plan["requirement_analysis_ids"]) == 1


def test_validation_plan_check_merges_ai_messages(monkeypatch) -> None:
    headers = auth_headers()
    seed_assets(headers)
    analysis_id = create_analysis(headers)
    update_recommendation_status(headers, analysis_id, 0, "confirmed")
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


def test_validation_plan_uses_only_confirmed_recommendations() -> None:
    headers = auth_headers()
    seed_assets(headers)
    analysis_id = create_analysis(headers)
    confirmed_item = update_recommendation_status(headers, analysis_id, 0, "confirmed")
    excluded_item = update_recommendation_status(headers, analysis_id, 1, "excluded")

    created = client.post("/api/validation-plans", headers=headers, json={"project_id": "project-g99-rfid"})

    assert created.status_code == 200
    titles = {item["title"] for item in created.json()["items"]}
    assert confirmed_item["title"] in titles
    assert excluded_item["title"] not in titles
    assert len(titles) == 1


def test_validation_plan_excludes_all_pending_recommendations() -> None:
    headers = auth_headers()
    seed_assets(headers)
    create_analysis(headers)

    created = client.post("/api/validation-plans", headers=headers, json={"project_id": "project-g99-rfid"})

    assert created.status_code == 200
    assert created.json()["items"] == []


def test_validation_plan_items_carry_requirement_fields() -> None:
    headers = auth_headers()
    seed_assets(headers)
    analysis_id = create_analysis(headers)
    update_recommendation_status(headers, analysis_id, 0, "confirmed")

    created = client.post("/api/validation-plans", headers=headers, json={"project_id": "project-g99-rfid"})

    assert created.status_code == 200
    item = created.json()["items"][0]
    assert item["objective"]
    assert item["method"]
    assert item["record_template"]


def test_validation_plan_status_can_be_updated_and_export_marks_exported() -> None:
    headers = auth_headers()
    seed_assets(headers)
    analysis_id = create_analysis(headers)
    update_recommendation_status(headers, analysis_id, 0, "confirmed")
    created = client.post("/api/validation-plans", headers=headers, json={"project_id": "project-g99-rfid"})
    plan_id = created.json()["id"]

    updated = client.patch(f"/api/validation-plans/{plan_id}/status", headers=headers, json={"status": "reviewing"})

    assert updated.status_code == 200
    assert updated.json()["status"] == "reviewing"

    exported = client.post(f"/api/validation-plans/{plan_id}/export", headers=headers)
    assert exported.status_code == 200
    detail = client.get(f"/api/validation-plans/{plan_id}", headers=headers)
    assert detail.json()["status"] == "exported"


def test_validation_plan_rejects_unknown_status() -> None:
    headers = auth_headers()
    seed_assets(headers)
    analysis_id = create_analysis(headers)
    update_recommendation_status(headers, analysis_id, 0, "confirmed")
    created = client.post("/api/validation-plans", headers=headers, json={"project_id": "project-g99-rfid"})

    updated = client.patch(f"/api/validation-plans/{created.json()['id']}/status", headers=headers, json={"status": "unknown"})

    assert updated.status_code == 400


def test_validation_plan_can_be_deleted() -> None:
    headers = auth_headers()
    seed_assets(headers)
    analysis_id = create_analysis(headers)
    update_recommendation_status(headers, analysis_id, 0, "confirmed")
    created = client.post("/api/validation-plans", headers=headers, json={"project_id": "project-g99-rfid"})
    plan_id = created.json()["id"]

    deleted = client.delete(f"/api/validation-plans/{plan_id}", headers=headers)

    assert deleted.status_code == 204
    detail = client.get(f"/api/validation-plans/{plan_id}", headers=headers)
    assert detail.status_code == 404


def test_validation_plans_can_be_bulk_deleted() -> None:
    headers = auth_headers()
    seed_assets(headers)
    first_analysis_id = create_analysis(headers)
    second_analysis_id = create_analysis(headers)
    update_recommendation_status(headers, first_analysis_id, 0, "confirmed")
    update_recommendation_status(headers, second_analysis_id, 0, "confirmed")
    first_plan = client.post("/api/validation-plans", headers=headers, json={"requirement_analysis_id": first_analysis_id}).json()
    second_plan = client.post("/api/validation-plans", headers=headers, json={"requirement_analysis_id": second_analysis_id}).json()

    deleted = client.post(
        "/api/validation-plans/bulk-delete",
        headers=headers,
        json={"plan_ids": [first_plan["id"], second_plan["id"], "missing-plan"]},
    )

    assert deleted.status_code == 200
    result = deleted.json()
    assert set(result["deleted_ids"]) == {first_plan["id"], second_plan["id"]}
    assert result["skipped"] == [{"plan_id": "missing-plan", "reason": "方案不存在或无访问权限"}]
    remaining = client.get("/api/validation-plans?project_id=project-g99-rfid", headers=headers)
    assert remaining.json() == []


def test_validation_plan_export_directory_config_is_used(tmp_path, monkeypatch) -> None:
    headers = auth_headers()
    config_path = tmp_path / "settings.json"
    export_directory = tmp_path / "exports"
    monkeypatch.setenv("SYSTEM_CONFIG_PATH", str(config_path))
    seed_assets(headers)
    analysis_id = create_analysis(headers)
    update_recommendation_status(headers, analysis_id, 0, "confirmed")
    saved = client.put(
        "/api/admin/validation-plan-export-config",
        headers=headers,
        json={"export_directory": str(export_directory)},
    )
    created = client.post("/api/validation-plans", headers=headers, json={"project_id": "project-g99-rfid"})

    exported = client.post(f"/api/validation-plans/{created.json()['id']}/export", headers=headers)

    assert saved.status_code == 200
    assert exported.status_code == 200
    assert Path(exported.json()["storage_path"]).is_relative_to(export_directory)
    assert Path(exported.json()["storage_path"]).exists()
