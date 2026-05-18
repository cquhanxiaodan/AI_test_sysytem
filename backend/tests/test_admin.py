from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.modules.admin.service import AUDIT_EVENTS, DEFAULT_CONFIG


client = TestClient(app)


def setup_function() -> None:
    AUDIT_EVENTS.clear()
    from app.modules.admin import service

    service.CONFIG = DEFAULT_CONFIG.model_copy(deep=True)
    settings = service.get_settings()
    settings.repository_backend = "memory"
    settings.system_config_path = f"/tmp/monkeycode-test-system-config-{uuid4()}.json"


def auth_headers(username: str = "admin", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_get_system_config() -> None:
    response = client.get("/api/admin/config", headers=auth_headers())

    assert response.status_code == 200
    assert "电子子系统" in response.json()["subsystem_catalog"]
    assert "RFID" in response.json()["subsystem_modules"]["电子子系统"]


def test_admin_can_update_system_dictionary_options() -> None:
    response = client.put(
        "/api/admin/config",
        headers=auth_headers(),
        json={
            "subsystem_catalog": ["RFID", "流体系统", "RFID"],
            "subsystem_modules": {"RFID": ["读写模块", "读写模块", "天线"], "流体系统": ["泵"]},
            "test_levels": ["部件级", "整机级"],
            "test_types": ["功能测试", "可靠性测试"],
        },
    )

    assert response.status_code == 200
    assert response.json()["subsystem_catalog"] == ["RFID", "流体系统"]
    assert response.json()["subsystem_modules"] == {"RFID": ["读写模块", "天线"], "流体系统": ["泵"]}
    assert response.json()["test_levels"] == ["部件级", "整机级"]
    assert response.json()["test_types"] == ["功能测试", "可靠性测试"]


def test_admin_can_update_template_section_aliases() -> None:
    response = client.put(
        "/api/admin/config",
        headers=auth_headers(),
        json={"template_section_aliases": {"objective": ["验证目的", "验收准则", "验证目的"], "steps": ["执行步骤"]}},
    )

    assert response.status_code == 200
    assert response.json()["template_section_aliases"]["objective"] == ["验证目的", "验收准则"]
    assert response.json()["template_section_aliases"]["steps"] == ["执行步骤"]


def test_tester_cannot_update_system_config() -> None:
    response = client.put(
        "/api/admin/config",
        headers=auth_headers("tester", "tester123"),
        json={"test_types": ["可靠性测试"]},
    )

    assert response.status_code == 403


def test_memory_system_config_persists_to_file(tmp_path) -> None:
    from app.modules.admin import service

    service.get_settings().system_config_path = str(tmp_path / "system-config.json")
    response = client.put(
        "/api/admin/config",
        headers=auth_headers(),
        json={"test_levels": ["部件级", "整机级"]},
    )

    assert response.status_code == 200
    service.CONFIG = DEFAULT_CONFIG.model_copy(deep=True)
    persisted = client.get("/api/admin/config", headers=auth_headers())
    assert persisted.json()["test_levels"] == ["部件级", "整机级"]


def test_old_system_config_file_format_still_loads(tmp_path) -> None:
    from app.modules.admin import service

    config_path = tmp_path / "system-config.json"
    config_path.write_text('{"test_types": ["旧格式类型"]}', encoding="utf-8")
    service.get_settings().system_config_path = str(config_path)

    response = client.get("/api/admin/config", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["test_types"] == ["旧格式类型"]
    assert "验证目的" in response.json()["template_section_aliases"]["objective"]


def test_saving_system_config_preserves_other_settings(tmp_path) -> None:
    from app.modules.admin import service
    from app.modules.admin.schemas import AiSettingsConfig

    service.get_settings().system_config_path = str(tmp_path / "system-config.json")
    service.save_ai_settings(AiSettingsConfig(provider="openai-compatible", base_url="https://model.example.com/v1", api_key="secret", model="model-a", timeout_seconds=25))
    service.save_import_directory("/data/imports")

    response = client.put("/api/admin/config", headers=auth_headers(), json={"test_types": ["保留验证类型"]})

    assert response.status_code == 200
    settings_file = service.load_settings_file()
    assert settings_file is not None
    assert settings_file.ai_config.model == "model-a"
    assert settings_file.document_import_directory == "/data/imports"


def test_memory_system_config_can_restore_backup(tmp_path) -> None:
    from app.modules.admin import service

    service.get_settings().system_config_path = str(tmp_path / "system-config.json")
    headers = auth_headers()
    client.put("/api/admin/config", headers=headers, json={"test_types": ["功能测试", "可靠性测试"]})
    client.put("/api/admin/config", headers=headers, json={"test_types": ["误保存类型"]})

    response = client.post("/api/admin/config/restore-backup", headers=headers)

    assert response.status_code == 200
    assert response.json()["test_types"] == ["功能测试", "可靠性测试"]


def test_ai_save_does_not_overwrite_dictionary_backup(tmp_path) -> None:
    from app.modules.admin import service
    from app.modules.admin.schemas import AiSettingsConfig

    service.get_settings().system_config_path = str(tmp_path / "system-config.json")
    headers = auth_headers()
    client.put("/api/admin/config", headers=headers, json={"test_types": ["用户配置类型"]})
    client.put("/api/admin/config", headers=headers, json={"test_types": ["误覆盖类型"]})
    service.save_ai_settings(AiSettingsConfig(provider="openai-compatible", base_url="https://model.example.com/v1", api_key="secret", model="model-a", timeout_seconds=25))

    response = client.post("/api/admin/config/restore-backup", headers=headers)

    assert response.status_code == 200
    assert response.json()["test_types"] == ["用户配置类型"]


def test_restore_system_config_backup_returns_404_when_missing(tmp_path) -> None:
    from app.modules.admin import service

    service.get_settings().system_config_path = str(tmp_path / "system-config.json")

    response = client.post("/api/admin/config/restore-backup", headers=auth_headers())

    assert response.status_code == 404


def test_create_and_list_audit_event() -> None:
    headers = auth_headers()
    created = client.post(
        "/api/admin/audits",
        headers=headers,
        json={"action": "publish", "target_type": "document", "target_id": "doc-1", "detail": "发布资料"},
    )

    assert created.status_code == 200

    listed = client.get("/api/admin/audits", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["action"] == "publish"


def test_acceptance_status_available() -> None:
    response = client.get("/api/admin/acceptance-status", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["frontend_build"] == "passed"
