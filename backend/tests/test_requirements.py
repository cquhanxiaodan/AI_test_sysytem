from fastapi.testclient import TestClient

from app.main import app
from app.modules.documents.repository import DOCUMENTS
from app.modules.parsing.service import CHUNKS, TASKS
from app.modules.requirements.service import ANALYSES
from app.modules.risks.service import RISKS
from app.modules.test_items.service import TEST_ITEMS
from app.modules.test_packages.service import TEST_PACKAGES


client = TestClient(app)


def setup_function() -> None:
    DOCUMENTS.clear()
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


def test_upload_requirement_document_extracts_standard_description() -> None:
    headers = auth_headers()

    response = client.post(
        "/api/requirement-analyses/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={
            "file": (
                "rfid-requirement.txt",
                "需求标题：RFID 二供导入\n产品型号：DNBSEQ-G99\n变更对象：RFID\n变更背景：降低供应风险\n变更内容：引入二供供应商\n".encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["filename"] == "rfid-requirement.txt"
    assert "变更对象：RFID" in result["description"]


def test_requirement_analysis_accepts_standard_format() -> None:
    headers = auth_headers()
    seed_assets(headers)

    response = client.post(
        "/api/requirement-analyses",
        headers=headers,
        json={
            "project_id": "project-g99-rfid",
            "description": "需求标题：RFID 二供导入\n产品型号：DNBSEQ-G99\n变更对象：RFID\n变更背景：降低供应风险，引入二供供应商\n变更内容：导入二供供应商",
        },
    )

    assert response.status_code == 200
    analysis = response.json()
    assert analysis["parse_result"]["test_object"] == "RFID"
    assert analysis["parse_result"]["change_type"] == "供应商变更"


def test_requirement_template_download_available() -> None:
    headers = auth_headers()

    response = client.get("/api/requirement-analyses/template/download", headers=headers)

    assert response.status_code == 200
    content = response.content.decode("utf-8-sig")
    assert "需求标题,产品型号,变更对象,变更背景,变更内容,所属子系统,变更类型" in content


def test_upload_requirement_table_batch_analyzes_valid_rows() -> None:
    headers = auth_headers()
    seed_assets(headers)
    content = (
        "需求标题,产品型号,变更对象,变更背景,变更内容,所属子系统,变更类型,影响范围,验收标准,已知风险\n"
        "RFID 二供导入,DNBSEQ-G99,RFID,降低供应风险,同步引入康奈特 RFID,RFID,供应商变更,,,\n"
        "缺字段需求,DNBSEQ-G99,RFID,降低供应风险,,RFID,供应商变更,,,\n"
    )

    response = client.post(
        "/api/requirement-analyses/upload-table",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("requirements.csv", content.encode("utf-8-sig"), "text/csv")},
    )

    assert response.status_code == 200
    result = response.json()
    assert len(result["items"]) == 2
    assert result["items"][0]["analysis"] is not None
    assert result["items"][1]["analysis"] is None
    assert "变更内容" in result["items"][1]["missing_fields"]


def test_requirement_recommendations_merge_ai_with_local_sources(monkeypatch) -> None:
    headers = auth_headers()
    seed_assets(headers)

    def fake_run_json_task(task_type, *args, **kwargs):
        if task_type == "requirement_recommendation":
            package_id = next(iter(TEST_PACKAGES.values())).id
            return {
                "required": [
                    {
                        "title": "AI 补充 RFID 供应商变更回归测试",
                        "source_type": "test_package",
                        "source_id": package_id,
                        "reason": "匹配本地 RFID 归口包",
                        "evidence": "本地归口包命中",
                    }
                ],
                "suggested": [],
                "conditional": [],
                "evidence": "本地归口包命中",
            }
        return None

    monkeypatch.setattr("app.modules.requirements.service.run_json_task", fake_run_json_task)

    response = client.post(
        "/api/requirement-analyses",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    )

    assert response.status_code == 200
    titles = {item["title"] for item in response.json()["recommendations"]}
    assert "AI 补充 RFID 供应商变更回归测试" in titles
