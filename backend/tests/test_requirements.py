from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.modules.ai.schemas import AiTaskResult
from app.modules.documents.repository import DOCUMENTS
from app.modules.parsing.service import CHUNKS, TASKS
from app.modules.requirements.service import ANALYSES
from app.modules.risks.service import RISKS
from app.modules.test_items.service import list_test_items
from app.modules.test_items.service import TEST_ITEMS
from app.modules.test_packages.service import TEST_PACKAGES, list_packages


client = TestClient(app)


def setup_function() -> None:
    from app.modules.admin import service as admin_service
    from app.modules.ai.service import RUNTIME_AI_CONFIG

    admin_service.CONFIG = admin_service.DEFAULT_CONFIG.model_copy(deep=True)
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


def test_latest_requirement_analysis_returns_project_latest() -> None:
    headers = auth_headers()
    seed_assets(headers)

    first = client.post(
        "/api/requirement-analyses/local",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    )
    second = client.post(
        "/api/requirement-analyses/local",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 再次引入二供供应商康奈特 RFID"},
    )
    latest = client.get("/api/requirement-analyses/latest?project_id=project-g99-rfid", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert latest.status_code == 200
    assert latest.json()["id"] == second.json()["id"]


def test_list_requirement_analyses_returns_project_history() -> None:
    headers = auth_headers()
    seed_assets(headers)
    first = client.post(
        "/api/requirement-analyses/local",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    )
    second = client.post(
        "/api/requirement-analyses/local",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 再次引入二供供应商康奈特 RFID"},
    )

    history = client.get("/api/requirement-analyses?project_id=project-g99-rfid", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert history.status_code == 200
    assert [item["id"] for item in history.json()] == [second.json()["id"], first.json()["id"]]


def test_delete_requirement_analysis_removes_history_item() -> None:
    headers = auth_headers()
    seed_assets(headers)
    created = client.post(
        "/api/requirement-analyses/local",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    )

    deleted = client.delete(f"/api/requirement-analyses/{created.json()['id']}", headers=headers)
    detail = client.get(f"/api/requirement-analyses/{created.json()['id']}", headers=headers)
    history = client.get("/api/requirement-analyses?project_id=project-g99-rfid", headers=headers)

    assert created.status_code == 200
    assert deleted.status_code == 204
    assert detail.status_code == 404
    assert history.json() == []


def test_requirement_analysis_deduplicates_recommendations_by_title(monkeypatch) -> None:
    headers = auth_headers()
    seed_assets(headers)

    def fake_search_project_knowledge(project_id, query):
        from app.modules.knowledge.schemas import SearchResult

        return [
            SearchResult(
                source_type="document_chunk",
                source_id="chunk-duplicate",
                title="RFID 在机读取测试",
                text="重复命中的 RFID 在机读取测试",
                score=1,
            )
        ]

    monkeypatch.setattr("app.modules.requirements.service.search_project_knowledge", fake_search_project_knowledge)

    response = client.post(
        "/api/requirement-analyses/local",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    )

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["recommendations"]]
    assert titles.count("RFID 在机读取测试") == 1


def test_requirement_analysis_skips_package_knowledge_and_merges_similar_titles(monkeypatch) -> None:
    headers = auth_headers()
    seed_assets(headers)

    def fake_search_project_knowledge(project_id, query):
        from app.modules.knowledge.schemas import SearchResult

        return [
            SearchResult(
                source_type="test_package",
                source_id="pkg-duplicate",
                title="RFID测试归口包",
                text="整个归口包命中",
                score=1,
            ),
            SearchResult(
                source_type="document_chunk",
                source_id="chunk-assembly",
                title="整机装配测试",
                text="同类装配测试命中",
                score=1,
            ),
            SearchResult(
                source_type="test_item",
                source_id="test-item-install",
                title="整机安装适配测试",
                text="整机安装适配测试 检验RFID结构适配安装至整机是否存在异常。",
                score=1,
            ),
        ]

    monkeypatch.setattr("app.modules.requirements.service.search_project_knowledge", fake_search_project_knowledge)

    response = client.post(
        "/api/requirement-analyses/local",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    )

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["recommendations"]]
    assert "RFID测试归口包" not in titles
    assert "整机装配测试" not in titles
    assert "整机安装适配测试" not in titles
    assert "RFID 在机装配测试" in titles


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
            return AiTaskResult(output={
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
            }, status="succeeded", message="AI 调用成功。")
        return AiTaskResult(output=None, status="not_configured", message="AI 未配置。")

    monkeypatch.setattr("app.modules.requirements.service.run_json_task_detailed", fake_run_json_task)

    response = client.post(
        "/api/requirement-analyses",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    )

    assert response.status_code == 200
    titles = {item["title"] for item in response.json()["recommendations"]}
    assert "AI 补充 RFID 供应商变更回归测试" in titles


def test_requirement_analysis_accepts_ai_generated_missing_test_items(monkeypatch) -> None:
    headers = auth_headers()
    seed_assets(headers)

    def fake_run_json_task(task_type, *args, **kwargs):
        if task_type == "requirement_recommendation":
            return AiTaskResult(output={
                "required": [
                    {
                        "title": "新增 DNBSEQ-G99 RFID 供应商兼容性测试",
                        "source_type": "ai_generated",
                        "source_id": "ai-missing-rfid-compatibility",
                        "reason": "本地资产未覆盖该补测项",
                        "evidence": "AI 识别缺失测试项",
                    }
                ],
                "suggested": [],
                "conditional": [],
                "evidence": "AI 识别缺失测试项",
            }, status="succeeded", message="AI 调用成功。")
        return AiTaskResult(output=None, status="not_configured", message="AI 未配置。")

    monkeypatch.setattr("app.modules.requirements.service.run_json_task_detailed", fake_run_json_task)

    response = client.post(
        "/api/requirement-analyses",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    )

    assert response.status_code == 200
    recommendations = response.json()["recommendations"]
    assert any(
        item["group"] == "AI识别推荐测试项"
        and item["source_type"] == "ai_generated"
        and item["title"] == "新增 DNBSEQ-G99 RFID 供应商兼容性测试"
        and item["objective"]
        and item["method"]
        and item["record_template"]
        for item in recommendations
    )


def test_include_ai_recommendation_in_local_test_items(monkeypatch) -> None:
    headers = auth_headers()
    seed_assets(headers)

    def fake_run_json_task(task_type, *args, **kwargs):
        if task_type == "requirement_recommendation":
            return AiTaskResult(output={
                "required": [
                    {
                        "title": "新增 RFID 异常断电恢复测试",
                        "source_id": "ai-power-recovery",
                        "reason": "AI 识别缺失测试项",
                        "evidence": "供应商变更可能影响异常恢复",
                        "objective": "验证 RFID 异常断电恢复能力。",
                        "method": "执行异常断电后重新上电读取 RFID。",
                        "record_template": "记录断电条件、恢复结果和异常日志。",
                    }
                ],
                "suggested": [],
                "conditional": [],
                "evidence": "AI 识别缺失测试项",
            }, status="succeeded", message="AI 调用成功。")
        return AiTaskResult(output=None, status="not_configured", message="AI 未配置。")

    monkeypatch.setattr("app.modules.requirements.service.run_json_task_detailed", fake_run_json_task)
    analysis = client.post(
        "/api/requirement-analyses",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    ).json()
    recommendation = next(item for item in analysis["recommendations"] if item["source_type"] == "ai_generated")

    included = client.post(
        f"/api/requirement-analyses/{analysis['id']}/recommendations/{recommendation['id']}/include-local",
        headers=headers,
    )

    assert included.status_code == 200
    updated = next(item for item in included.json()["recommendations"] if item["id"] == recommendation["id"])
    assert updated["source_type"] == "test_item"
    assert updated["review_status"] == "pending"
    local_item = next(item for item in list_test_items("project-g99-rfid") if item.id == updated["source_id"])
    assert local_item.title == "新增 RFID 异常断电恢复测试"
    assert local_item.source_type == "ai_generated"
    assert local_item.status == "draft"
    package = next(package for package in list_packages("project-g99-rfid") if package.name == "RFID测试归口包")
    assert all(item.test_item_id != local_item.id for item in package.items)

    published = client.post(f"/api/test-items/{local_item.id}/confirm", headers=headers)
    assert published.status_code == 200
    package = next(package for package in list_packages("project-g99-rfid") if package.name == "RFID测试归口包")
    assert any(item.test_item_id == local_item.id for item in package.items)
    assert len([package for package in list_packages("project-g99-rfid") if "RFID" in package.name]) == 1


def test_include_ai_recommendation_reuses_existing_local_test_item(monkeypatch) -> None:
    headers = auth_headers()
    seed_assets(headers)

    def fake_run_json_task(task_type, *args, **kwargs):
        if task_type == "requirement_recommendation":
            return AiTaskResult(output={
                "required": [
                    {
                        "title": "新增 RFID 异常断电恢复测试",
                        "source_id": "ai-power-recovery",
                        "reason": "AI 识别缺失测试项",
                        "evidence": "供应商变更可能影响异常恢复",
                        "objective": "验证 RFID 异常断电恢复能力。",
                        "method": "执行异常断电后重新上电读取 RFID。",
                        "record_template": "记录断电条件、恢复结果和异常日志。",
                    }
                ],
                "suggested": [],
                "conditional": [],
                "evidence": "AI 识别缺失测试项",
            }, status="succeeded", message="AI 调用成功。")
        return AiTaskResult(output=None, status="not_configured", message="AI 未配置。")

    monkeypatch.setattr("app.modules.requirements.service.run_json_task_detailed", fake_run_json_task)
    analysis = client.post(
        "/api/requirement-analyses",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    ).json()
    recommendation = next(item for item in analysis["recommendations"] if item["source_type"] == "ai_generated")

    first = client.post(
        f"/api/requirement-analyses/{analysis['id']}/recommendations/{recommendation['id']}/include-local",
        headers=headers,
    )
    second = client.post(
        f"/api/requirement-analyses/{analysis['id']}/recommendations/{recommendation['id']}/include-local",
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    matching_items = [item for item in list_test_items("project-g99-rfid") if item.title == "新增 RFID 异常断电恢复测试"]
    assert len(matching_items) == 1
    updated = next(item for item in second.json()["recommendations"] if item["id"] == recommendation["id"])
    assert updated["source_id"] == matching_items[0].id


def test_requirement_recommendation_review_crud() -> None:
    headers = auth_headers()
    seed_assets(headers)
    created = client.post(
        "/api/requirement-analyses",
        headers=headers,
        json={"project_id": "project-g99-rfid", "description": "DNBSEQ-G99 引入二供供应商康奈特 RFID"},
    )
    assert created.status_code == 200
    analysis = created.json()
    recommendation_id = analysis["recommendations"][0]["id"]

    confirmed = client.patch(
        f"/api/requirement-analyses/{analysis['id']}/recommendations/{recommendation_id}",
        headers=headers,
        json={"review_status": "confirmed"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["recommendations"][0]["review_status"] == "confirmed"

    edited = client.patch(
        f"/api/requirement-analyses/{analysis['id']}/recommendations/{recommendation_id}",
        headers=headers,
        json={"title": "已编辑 RFID 测试项", "reason": "人工修订"},
    )
    assert edited.status_code == 200
    assert edited.json()["recommendations"][0]["title"] == "已编辑 RFID 测试项"

    added = client.post(
        f"/api/requirement-analyses/{analysis['id']}/recommendations",
        headers=headers,
        json={"group": "人工补充", "title": "人工新增 RFID 兼容性测试"},
    )
    assert added.status_code == 200
    manual_item = added.json()["recommendations"][-1]
    assert manual_item["source_type"] == "manual"
    assert manual_item["review_status"] == "confirmed"

    excluded = client.patch(
        f"/api/requirement-analyses/{analysis['id']}/recommendations/{manual_item['id']}",
        headers=headers,
        json={"review_status": "excluded"},
    )
    assert excluded.status_code == 200
    assert excluded.json()["recommendations"][-1]["review_status"] == "excluded"

    deleted = client.delete(
        f"/api/requirement-analyses/{analysis['id']}/recommendations/{manual_item['id']}",
        headers=headers,
    )
    assert deleted.status_code == 200
    ids = {item["id"] for item in deleted.json()["recommendations"]}
    assert manual_item["id"] not in ids
