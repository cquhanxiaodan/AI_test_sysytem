import csv
from datetime import UTC, datetime
from io import StringIO
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.risks.schemas import RiskItem

RISKS: dict[str, RiskItem] = {}


class RiskRecord(Base):
    __tablename__ = "risks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(120), index=True)
    source_type: Mapped[str] = mapped_column(String(80), index=True)
    source_id: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    product_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    test_object: Mapped[str] = mapped_column(String(120), index=True)
    subsystem: Mapped[str] = mapped_column(String(120), index=True)
    severity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    rpn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_mode: Mapped[str | None] = mapped_column(String(500), nullable=True)
    failure_effect: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_measure: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_test: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def list_risks(
    project_id: str | None = None,
    test_object: str | None = None,
    subsystem: str | None = None,
    source_type: str | None = None,
) -> list[RiskItem]:
    if _use_sqlalchemy():
        with session_scope() as session:
            statement = select(RiskRecord)
            if project_id is not None:
                statement = statement.where(RiskRecord.project_id == project_id)
            if test_object is not None:
                statement = statement.where(RiskRecord.test_object == test_object)
            if subsystem is not None:
                statement = statement.where(RiskRecord.subsystem == subsystem)
            if source_type is not None:
                statement = statement.where(RiskRecord.source_type == source_type)
            records = session.scalars(statement).all()
            risks = [_record_to_risk(record) for record in records]
            return sorted(risks, key=lambda risk: risk.created_at, reverse=True)
    risks = list(RISKS.values())
    if project_id is not None:
        risks = [risk for risk in risks if risk.project_id == project_id]
    if test_object is not None:
        risks = [risk for risk in risks if risk.test_object == test_object]
    if subsystem is not None:
        risks = [risk for risk in risks if risk.subsystem == subsystem]
    if source_type is not None:
        risks = [risk for risk in risks if risk.source_type == source_type]
    return sorted(risks, key=lambda risk: risk.created_at, reverse=True)


def parse_risks(project_id: str, source_type: str, content: str) -> list[RiskItem]:
    rows = list(csv.DictReader(StringIO(content)))
    if not rows:
        rows = [{"title": line.strip()} for line in content.splitlines() if line.strip()]
    parser = build_jira_risk if source_type.lower() == "jira" else build_dfmea_risk
    items = [parser(project_id, row) for row in rows]
    for item in items:
        _save_risk(item)
    return items


def build_jira_risk(project_id: str, row: dict[str, str]) -> RiskItem:
    title = first_value(row, "title", "标题", "summary", default="Jira 历史问题")
    description = first_value(row, "description", "描述", "复现步骤", default=title)
    subsystem = infer_subsystem(title + description)
    return RiskItem(
        id=f"risk-{uuid4()}",
        project_id=project_id,
        source_type="jira",
        source_id=first_value(row, "key", "Jira编号", "id", default="jira-unknown"),
        title=title,
        description=description,
        product_model=first_value(row, "product_model", "产品型号", default=None),
        test_object="RFID" if subsystem == "RFID" else "待确认对象",
        subsystem=subsystem,
        severity=first_value(row, "severity", "严重程度", default=None),
        rpn=parse_int(first_value(row, "rpn", "RPN", default=None)),
        failure_mode=None,
        failure_effect=None,
        root_cause=first_value(row, "root_cause", "根因", default=None),
        control_measure=first_value(row, "solution", "解决方案", default=None),
        suggested_test=suggest_test(subsystem, title),
        status=first_value(row, "status", "状态", default="open") or "open",
        created_at=datetime.now(UTC),
    )


def build_dfmea_risk(project_id: str, row: dict[str, str]) -> RiskItem:
    failure_mode = first_value(row, "failure_mode", "失效模式", default="潜在失效模式")
    failure_effect = first_value(row, "failure_effect", "失效后果", default=None)
    subsystem = infer_subsystem(failure_mode + (failure_effect or ""))
    return RiskItem(
        id=f"risk-{uuid4()}",
        project_id=project_id,
        source_type="dfmea",
        source_id=first_value(row, "dfmea_id", "DFMEA编号", "id", default="dfmea-unknown"),
        title=failure_mode,
        description=failure_effect or failure_mode,
        product_model=first_value(row, "product_model", "产品型号", default=None),
        test_object="RFID" if subsystem == "RFID" else "待确认对象",
        subsystem=subsystem,
        severity=first_value(row, "severity", "S", default=None),
        rpn=parse_int(first_value(row, "rpn", "RPN", default=None)),
        failure_mode=failure_mode,
        failure_effect=failure_effect,
        root_cause=first_value(row, "failure_cause", "失效原因", default=None),
        control_measure=first_value(row, "control_measure", "控制措施", default=None),
        suggested_test=suggest_test(subsystem, failure_mode),
        status=first_value(row, "status", "状态", default="active") or "active",
        created_at=datetime.now(UTC),
    )


def first_value(row: dict[str, str], *keys: str, default: str | None) -> str | None:
    for key in keys:
        value = row.get(key)
        if value:
            return value
    return default


def parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def infer_subsystem(text: str) -> str:
    return "RFID" if "rfid" in text.lower() else "待确认子系统"


def suggest_test(subsystem: str, title: str) -> str:
    if subsystem == "RFID" and "写" in title:
        return "补充 RFID 在机写入测试和异常恢复验证。"
    if subsystem == "RFID" and "读" in title:
        return "补充 RFID 在机读取测试和多样本一致性验证。"
    if subsystem == "RFID":
        return "关联 RFID 供应商变更验证包，覆盖装配、初始化、读取、写入和条件触发 EMC。"
    return "根据风险项补充对应子系统功能、性能或回归测试。"


def _use_sqlalchemy() -> bool:
    return get_settings().repository_backend == "sqlalchemy"


def _save_risk(risk: RiskItem) -> None:
    if _use_sqlalchemy():
        with session_scope() as session:
            session.merge(_risk_to_record(risk))
        return
    RISKS[risk.id] = risk


def _risk_to_record(risk: RiskItem) -> RiskRecord:
    return RiskRecord(
        id=risk.id,
        project_id=risk.project_id,
        source_type=risk.source_type,
        source_id=risk.source_id,
        title=risk.title,
        description=risk.description,
        product_model=risk.product_model,
        test_object=risk.test_object,
        subsystem=risk.subsystem,
        severity=risk.severity,
        rpn=risk.rpn,
        failure_mode=risk.failure_mode,
        failure_effect=risk.failure_effect,
        root_cause=risk.root_cause,
        control_measure=risk.control_measure,
        suggested_test=risk.suggested_test,
        status=risk.status,
        created_at=risk.created_at,
    )


def _record_to_risk(record: RiskRecord) -> RiskItem:
    return RiskItem(
        id=record.id,
        project_id=record.project_id,
        source_type=record.source_type,
        source_id=record.source_id,
        title=record.title,
        description=record.description,
        product_model=record.product_model,
        test_object=record.test_object,
        subsystem=record.subsystem,
        severity=record.severity,
        rpn=record.rpn,
        failure_mode=record.failure_mode,
        failure_effect=record.failure_effect,
        root_cause=record.root_cause,
        control_measure=record.control_measure,
        suggested_test=record.suggested_test,
        status=record.status,
        created_at=record.created_at,
    )
