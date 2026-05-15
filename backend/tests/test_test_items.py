from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.modules.documents.repository import DOCUMENTS
from app.modules.parsing.service import CHUNKS, TASKS
from app.modules.test_items.service import TEST_ITEMS


client = TestClient(app)


def setup_function() -> None:
    from app.modules.admin import service as admin_service
    from app.modules.ai.service import RUNTIME_AI_CONFIG

    admin_service.get_settings().repository_backend = "memory"
    admin_service.get_settings().system_config_path = f"/tmp/monkeycode-test-system-config-{uuid4()}.json"
    RUNTIME_AI_CONFIG.clear()
    DOCUMENTS.clear()
    TASKS.clear()
    CHUNKS.clear()
    TEST_ITEMS.clear()


def auth_headers() -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_split_rfid_document_creates_five_items() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("DNBSEQ-G99 RFID验证方案.txt", b"RFID supplier change validation", "text/plain")},
    )
    document_id = upload.json()["document"]["id"]
    client.post(f"/api/parsing/documents/{document_id}/parse", headers=headers)

    response = client.post(f"/api/test-items/split/{document_id}", headers=headers)

    assert response.status_code == 200
    titles = {item["title"] for item in response.json()["items"]}
    assert titles == {
        "RFID 在机装配测试",
        "RFID 装配后初始化测试",
        "RFID 在机读取测试",
        "RFID 在机写入测试",
        "安规 EMC 测试",
    }


def test_split_same_document_updates_existing_items() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("DNBSEQ-G99 RFID验证方案.txt", b"RFID supplier change validation", "text/plain")},
    )
    document_id = upload.json()["document"]["id"]
    first = client.post(f"/api/test-items/split/{document_id}", headers=headers)
    first_ids = {item["title"]: item["id"] for item in first.json()["items"]}
    client.post(f"/api/test-items/{next(iter(first_ids.values()))}/confirm", headers=headers)

    second = client.post(f"/api/test-items/split/{document_id}", headers=headers)

    assert second.status_code == 200
    second_ids = {item["title"]: item["id"] for item in second.json()["items"]}
    assert second_ids == first_ids
    listed = client.get("/api/test-items?project_id=project-g99-rfid", headers=headers)
    assert len(listed.json()) == 5
    statuses = {item["id"]: item["status"] for item in listed.json()}
    assert "published" in statuses.values()


def test_split_document_prefers_original_word_sections() -> None:
    headers = auth_headers()
    content = """
测试项目列表
测试项目
整机安装适配测试
RFID装配后初始化测试
整机安装适配测试
测试目的/测试标准
检验RFID结构适配安装至整机是否存在异常。
检验标准如下：
RFID结构适配安装至整机无线缆干涉、结构干涉、接头松动等异常问题。
测试方法/原理
整机安装适配。
测试工具
DNBSEQ-G99
RFID 标签
测试步骤
RFID检查；
RFID安装；
整机外壳安装；
测试记录
记录结构干涉、线缆干涉和接头状态。
需求符合性和BUG信息
RFID装配后初始化测试
测试目的/测试标准
评估RFID装机后与整机系统及软件适配情况。
测试方法/原理
有RFID载片试剂盒在位时与无RFID载片试剂盒在位时，EUI/PUI初始化情况。
测试工具
DNBSEQ-G99
测试步骤
无RFID载片试剂盒在位时，打开EU；
有RFID载片试剂盒在位时，打开PUI；
测试记录
记录初始化结果和软件报错。
""".strip()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("DNBSEQ-G99 RFID验证方案.txt", content.encode("utf-8"), "text/plain")},
    )
    document_id = upload.json()["document"]["id"]
    client.post(f"/api/parsing/documents/{document_id}/parse", headers=headers)

    response = client.post(f"/api/test-items/split/{document_id}", headers=headers)

    assert response.status_code == 200
    items = {item["title"]: item for item in response.json()["items"]}
    install_item = items["整机安装适配测试"]
    assert install_item["objective"] == "检验RFID结构适配安装至整机是否存在异常。\n检验标准如下：\nRFID结构适配安装至整机无线缆干涉、结构干涉、接头松动等异常问题。"
    assert install_item["method"] == "整机安装适配。"
    assert install_item["tools"] == ["DNBSEQ-G99", "RFID 标签"]
    assert install_item["steps"] == ["RFID检查", "RFID安装", "整机外壳安装"]
    assert install_item["record_template"] == "记录结构干涉、线缆干涉和接头状态。"
    assert install_item["evidence"] == "DNBSEQ-G99 RFID验证方案.txt"


def test_confirm_test_item_publishes_asset() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.txt", b"RFID", "text/plain")},
    )
    document_id = upload.json()["document"]["id"]
    split = client.post(f"/api/test-items/split/{document_id}", headers=headers)
    item_id = split.json()["items"][0]["id"]

    response = client.post(f"/api/test-items/{item_id}/confirm", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "published"


def test_update_test_item_allows_engineer_corrections() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.txt", b"RFID", "text/plain")},
    )
    document_id = upload.json()["document"]["id"]
    split = client.post(f"/api/test-items/split/{document_id}", headers=headers)
    item_id = split.json()["items"][0]["id"]

    response = client.patch(
        f"/api/test-items/{item_id}",
        headers=headers,
        json={
            "test_object": "RFID 读写模块",
            "primary_subsystem": "RFID",
            "related_subsystems": ["整机系统"],
            "test_level": "系统级",
            "test_type": "回归测试",
            "method": "按工程师修订后的测试方法执行。",
        },
    )

    assert response.status_code == 200
    assert response.json()["test_object"] == "RFID 读写模块"
    assert response.json()["related_subsystems"] == ["整机系统"]
    assert response.json()["test_type"] == "回归测试"


def test_update_published_test_item_returns_to_draft() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.txt", b"RFID", "text/plain")},
    )
    document_id = upload.json()["document"]["id"]
    split = client.post(f"/api/test-items/split/{document_id}", headers=headers)
    item_id = split.json()["items"][0]["id"]
    client.post(f"/api/test-items/{item_id}/confirm", headers=headers)

    response = client.patch(
        f"/api/test-items/{item_id}",
        headers=headers,
        json={"test_level": "整机级"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "draft"


def test_bulk_delete_test_items() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.txt", b"RFID", "text/plain")},
    )
    split = client.post(f"/api/test-items/split/{upload.json()['document']['id']}", headers=headers)
    item_ids = [item["id"] for item in split.json()["items"][:2]]

    response = client.post("/api/test-items/bulk-delete", headers=headers, json={"item_ids": item_ids})

    assert response.status_code == 200
    assert set(response.json()["deleted_ids"]) == set(item_ids)
    remaining = client.get("/api/test-items", headers=headers)
    assert not set(item_ids) & {item["id"] for item in remaining.json()}


def test_bulk_publish_test_items() -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.txt", b"RFID", "text/plain")},
    )
    split = client.post(f"/api/test-items/split/{upload.json()['document']['id']}", headers=headers)
    item_ids = [item["id"] for item in split.json()["items"][:2]]

    response = client.post("/api/test-items/bulk-publish", headers=headers, json={"item_ids": item_ids})

    assert response.status_code == 200
    assert set(response.json()["published_ids"]) == set(item_ids)
    remaining = client.get("/api/test-items", headers=headers)
    statuses = {item["id"]: item["status"] for item in remaining.json()}
    assert {statuses[item_id] for item_id in item_ids} == {"published"}


def test_split_document_uses_ai_items(monkeypatch) -> None:
    headers = auth_headers()
    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.txt", b"3.1 RFID read test", "text/plain")},
    )
    document_id = upload.json()["document"]["id"]
    client.post(f"/api/parsing/documents/{document_id}/parse", headers=headers)

    def fake_run_json_task(*args, **kwargs):
        return {
            "items": [
                {
                    "title": "AI RFID 异常恢复测试",
                    "test_object": "RFID",
                    "primary_subsystem": "RFID",
                    "related_subsystems": ["整机系统"],
                    "test_level": "系统级",
                    "test_type": "异常恢复",
                    "risk_tags": ["供应商变更"],
                    "objective": "验证 RFID 异常恢复能力。",
                    "method": "模拟读取异常后恢复。",
                    "tools": ["DNBSEQ-G99"],
                    "steps": ["触发异常", "执行恢复"],
                    "record_template": "记录异常和恢复结果。",
                    "evidence": "3.1 RFID read test",
                }
            ],
            "evidence": "3.1 RFID read test",
        }

    monkeypatch.setattr("app.modules.test_items.service.run_json_task", fake_run_json_task)

    response = client.post(f"/api/test-items/split/{document_id}", headers=headers)

    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == ["AI RFID 异常恢复测试"]


def test_test_item_list_is_global_when_project_filter_omitted() -> None:
    headers = auth_headers()
    first_upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-g99-rfid"},
        files={"file": ("RFID验证方案.txt", b"RFID", "text/plain")},
    )
    second_upload = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"project_id": "project-mgi-platform"},
        files={"file": ("platform验证方案.txt", b"platform", "text/plain")},
    )
    client.post(f"/api/test-items/split/{first_upload.json()['document']['id']}", headers=headers)
    client.post(f"/api/test-items/split/{second_upload.json()['document']['id']}", headers=headers)

    response = client.get("/api/test-items", headers=headers)

    assert response.status_code == 200
    assert {item["project_id"] for item in response.json()} == {"project-g99-rfid", "project-mgi-platform"}
