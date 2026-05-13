from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.admin.schemas import AcceptanceStatus, AuditEvent, SystemConfig

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
        completed_stages=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12"],
        backend_test_count=23,
        frontend_build="passed",
        remaining_risks=["Docker Compose 未在当前环境验证", "真实 Word 渲染仍为接口占位", "Ant Design 首包后续需要路由懒加载优化"],
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
