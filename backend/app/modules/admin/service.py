from datetime import UTC, datetime
from uuid import uuid4

from app.modules.admin.schemas import AcceptanceStatus, AuditEvent, SystemConfig

AUDIT_EVENTS: dict[str, AuditEvent] = {}

CONFIG = SystemConfig(
    subsystem_catalog=["RFID", "液路系统", "光学系统", "温控系统", "运动控制", "整机系统"],
    document_types=["验证方案", "测试规范", "测试报告", "Jira导出", "DFMEA"],
    test_types=["功能测试", "性能测试", "装配兼容性", "安规 EMC", "回归测试"],
    change_types=["供应商变更", "设计变更", "软件变更", "工艺变更"],
    ai_external_reference_enabled=False,
    validation_template_version="validation-plan-v1",
)


def get_config() -> SystemConfig:
    return CONFIG


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
    AUDIT_EVENTS[event.id] = event
    return event


def list_audit_events() -> list[AuditEvent]:
    return sorted(AUDIT_EVENTS.values(), key=lambda event: event.created_at, reverse=True)


def get_acceptance_status() -> AcceptanceStatus:
    return AcceptanceStatus(
        completed_stages=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12"],
        backend_test_count=23,
        frontend_build="passed",
        remaining_risks=["Docker Compose 未在当前环境验证", "真实 Word 渲染仍为接口占位", "Ant Design 首包后续需要路由懒加载优化"],
    )
