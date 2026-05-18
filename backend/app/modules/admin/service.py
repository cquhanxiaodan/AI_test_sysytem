import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.admin.schemas import AcceptanceStatus, AiSettingsConfig, AuditEvent, SystemConfig, SystemConfigUpdate, SystemSettingsFile

AUDIT_EVENTS: dict[str, AuditEvent] = {}


class AuditEventRecord(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(120), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    target_type: Mapped[str] = mapped_column(String(120), index=True)
    target_id: Mapped[str] = mapped_column(String(120), index=True)
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SystemConfigRecord(Base):
    __tablename__ = "system_configs"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)

CONFIG = SystemConfig(
    subsystem_catalog=["电子子系统", "液路系统", "光学系统", "温控系统", "运动控制", "整机系统"],
    document_types=["验证方案", "测试规范", "测试报告", "Jira导出", "DFMEA"],
    test_levels=["部件级", "子系统级", "系统级", "整机级", "回归验证"],
    test_types=["功能测试", "性能测试", "装配兼容性", "安规 EMC", "回归测试"],
    change_types=["供应商变更", "设计变更", "软件变更", "工艺变更"],
    template_section_aliases={
        "objective": ["测试目的/测试标准", "测试目的", "测试标准", "验证目的", "测试目标", "目的", "判定标准", "验收准则"],
        "method": ["测试方法/原理", "测试方法", "测试原理", "验证方法", "测试过程", "方法原理"],
        "tools": ["测试工具", "测试设备", "仪器设备", "工装夹具", "物料清单"],
        "steps": ["测试步骤", "操作步骤", "执行步骤", "测试流程", "验证步骤"],
        "connection_media": ["测试连接图或照片", "连接图", "测试照片", "测试连接图", "示意图", "图片记录"],
        "record_template": ["测试记录", "记录模板", "记录表", "结果记录", "测试结果"],
        "compliance_bug_info": ["需求符合性和BUG信息", "需求符合性结果", "测试发现的BUG信息表", "符合性判定", "BUG信息", "缺陷记录"],
    },
    ai_external_reference_enabled=False,
    validation_template_version="validation-plan-v1",
)
DEFAULT_CONFIG = CONFIG.model_copy(deep=True)


def get_config() -> SystemConfig:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.get(SystemConfigRecord, "default")
            if record is not None:
                return SystemConfig(**{**CONFIG.model_dump(), **(record.value or {})})
    settings_file = load_settings_file()
    if settings_file is not None:
        return settings_file.system_config
    return CONFIG


def update_config(payload: SystemConfigUpdate) -> SystemConfig:
    global CONFIG
    updates = payload.model_dump(exclude_unset=True)
    cleaned_updates = {}
    for key, value in updates.items():
        if value is None:
            continue
        cleaned_updates[key] = normalize_template_section_aliases(value) if key == "template_section_aliases" else normalize_options(value)
    updated = get_config().model_copy(update=cleaned_updates)
    if _use_sqlalchemy():
        with session_scope() as session:
            existing = session.get(SystemConfigRecord, "default")
            if existing is not None:
                session.merge(SystemConfigRecord(key="default.backup", value=existing.value))
                session.merge(SystemConfigRecord(key="system_config.backup", value=(existing.value or {}).get("system_config", existing.value)))
            session.merge(SystemConfigRecord(key="default", value=updated.model_dump()))
        return updated
    CONFIG = updated
    backup_current_system_config()
    save_system_settings(system_config=updated)
    return updated


def restore_config_backup() -> SystemConfig | None:
    global CONFIG
    if _use_sqlalchemy():
        with session_scope() as session:
            backup = session.get(SystemConfigRecord, "default.backup")
            dictionary_backup = session.get(SystemConfigRecord, "system_config.backup")
            if dictionary_backup is not None:
                current = session.get(SystemConfigRecord, "default")
                if current is not None and "system_config" in (current.value or {}):
                    merged = {**(current.value or {}), "system_config": dictionary_backup.value}
                else:
                    merged = dictionary_backup.value
                session.merge(SystemConfigRecord(key="default", value=merged))
                return SystemConfig(**{**CONFIG.model_dump(), **(dictionary_backup.value or {})})
            if backup is None:
                return None
            session.merge(SystemConfigRecord(key="default", value=backup.value))
            return SystemConfig(**{**CONFIG.model_dump(), **(backup.value or {})})
    dictionary_backup = load_system_config_backup()
    if dictionary_backup is not None:
        settings_file = load_settings_file() or SystemSettingsFile(system_config=CONFIG)
        restored = settings_file.model_copy(update={"system_config": dictionary_backup})
        save_settings_file(restored, create_backup=False)
        CONFIG = dictionary_backup
        return dictionary_backup
    backup_file = load_settings_file(backup=True)
    if backup_file is None:
        return None
    CONFIG = backup_file.system_config
    save_settings_file(backup_file, create_backup=False)
    return backup_file.system_config


def get_persisted_ai_config() -> AiSettingsConfig:
    settings_file = load_settings_file()
    if settings_file is None:
        settings = get_settings()
        return AiSettingsConfig(
            provider=settings.ai_provider,
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            timeout_seconds=settings.ai_timeout_seconds,
        )
    return settings_file.ai_config


def save_ai_settings(config: AiSettingsConfig) -> None:
    save_system_settings(ai_config=config)


def get_persisted_import_directory() -> str:
    settings_file = load_settings_file()
    if settings_file is None:
        return get_settings().document_import_directory.strip()
    return settings_file.document_import_directory.strip()


def save_import_directory(import_directory: str) -> None:
    save_system_settings(document_import_directory=import_directory.strip())


def save_system_settings(
    *,
    system_config: SystemConfig | None = None,
    ai_config: AiSettingsConfig | None = None,
    document_import_directory: str | None = None,
) -> SystemSettingsFile:
    current = load_settings_file() or SystemSettingsFile(system_config=CONFIG)
    updated = current.model_copy(
        update={
            key: value
            for key, value in {
                "system_config": system_config,
                "ai_config": ai_config,
                "document_import_directory": document_import_directory,
            }.items()
            if value is not None
        }
    )
    save_settings_file(updated)
    return updated


def load_settings_file(backup: bool = False) -> SystemSettingsFile | None:
    path = get_config_path(backup=backup)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if "system_config" in data:
        return SystemSettingsFile(**data)
    settings = get_settings()
    return SystemSettingsFile(
        system_config=SystemConfig(**{**CONFIG.model_dump(), **data}),
        ai_config=AiSettingsConfig(
            provider=settings.ai_provider,
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            timeout_seconds=settings.ai_timeout_seconds,
        ),
        document_import_directory=settings.document_import_directory.strip(),
    )


def save_settings_file(settings_file: SystemSettingsFile, create_backup: bool = True) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if create_backup and path.exists():
        backup_path = get_config_path(backup=True)
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(json.dumps(settings_file.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")


def backup_current_system_config() -> None:
    current = load_settings_file()
    if current is None:
        return
    path = get_system_config_backup_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current.system_config.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")


def load_system_config_backup() -> SystemConfig | None:
    path = get_system_config_backup_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return SystemConfig(**{**CONFIG.model_dump(), **data})


def load_file_config(backup: bool = False) -> SystemConfig | None:
    settings_file = load_settings_file(backup=backup)
    return settings_file.system_config if settings_file is not None else None


def save_file_config(config: SystemConfig, create_backup: bool = True) -> None:
    current = load_settings_file() or SystemSettingsFile(system_config=CONFIG)
    save_settings_file(current.model_copy(update={"system_config": config}), create_backup=create_backup)


def get_config_path(backup: bool = False) -> Path:
    path = Path(get_settings().system_config_path)
    if not backup:
        return path
    return path.with_name(f"{path.stem}.backup{path.suffix}")


def get_system_config_backup_path() -> Path:
    path = Path(get_settings().system_config_path)
    return path.with_name(f"{path.stem}.dictionary.backup{path.suffix}")


def normalize_options(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        item = value.strip()
        if item and item not in normalized:
            normalized.append(item)
    return normalized


def normalize_template_section_aliases(values: dict[str, list[str]]) -> dict[str, list[str]]:
    return {key: normalize_options(items) for key, items in values.items() if isinstance(items, list)}


def create_audit_event(actor_id: str, action: str, target_type: str, target_id: str, detail: str) -> AuditEvent:
    event = AuditEvent(
        id=f"audit-{uuid4()}",
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        created_at=datetime.now(UTC),
    )
    _save_audit_event(event)
    return event


def list_audit_events() -> list[AuditEvent]:
    if _use_sqlalchemy():
        with session_scope() as session:
            records = session.scalars(select(AuditEventRecord)).all()
            events = [_record_to_audit_event(record) for record in records]
            return sorted(events, key=lambda event: event.created_at, reverse=True)
    return sorted(AUDIT_EVENTS.values(), key=lambda event: event.created_at, reverse=True)


def get_acceptance_status() -> AcceptanceStatus:
    return AcceptanceStatus(
        completed_stages=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"],
        backend_test_count=33,
        frontend_build="passed",
        remaining_risks=["Docker Compose 未在当前环境验证", "真实 Word/PDF/Excel 深度解析后续需要替换轻量启发式解析", "Celery 异步任务和 pgvector 检索后续需要接入"],
    )


def _use_sqlalchemy() -> bool:
    return get_settings().repository_backend == "sqlalchemy"


def _save_audit_event(event: AuditEvent) -> None:
    if _use_sqlalchemy():
        with session_scope() as session:
            session.merge(
                AuditEventRecord(
                    id=event.id,
                    actor_id=event.actor_id,
                    action=event.action,
                    target_type=event.target_type,
                    target_id=event.target_id,
                    detail=event.detail,
                    created_at=event.created_at,
                )
            )
        return
    AUDIT_EVENTS[event.id] = event


def _record_to_audit_event(record: AuditEventRecord) -> AuditEvent:
    return AuditEvent(
        id=record.id,
        actor_id=record.actor_id,
        action=record.action,
        target_type=record.target_type,
        target_id=record.target_id,
        detail=record.detail,
        created_at=record.created_at,
    )
