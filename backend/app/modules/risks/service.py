import csv
from datetime import UTC, datetime
from io import StringIO
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.ai.service import run_json_task
from app.modules.risks.schemas import RiskItem, RiskUpdate

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
    items = enrich_risks_with_ai(project_id, source_type, content, items)
    for item in items:
        _save_risk(item)
    return items


def parse_risks_with_ai(project_id: str, source_type: str, content: str, fallback_items: list[RiskItem]) -> list[RiskItem] | None:
    output = run_json_task(
        "risk_parse",
        "你是基因测序仪风险知识解析助手。只输出 JSON，不输出解释。",
        (
            "从 Jira 导出或 DFMEA 内容中解析风险项，输出 items 数组。"
            "每项包含 source_id、title、description、product_model、test_object、subsystem、severity、rpn、failure_mode、failure_effect、root_cause、control_measure、suggested_test、status。"
            "优先保留原始编号和本地证据，无法确认的字段使用 null 或待确认。"
            f"\n来源类型：{source_type}"
            f"\n本地候选：{[item.model_dump() for item in fallback_items[:5]]}"
            f"\n原始内容：\n{content[:8000]}"
        ),
    )
    if output is None or not isinstance(output.get("items"), list):
        return None
    items: list[RiskItem] = []
    normalized_source_type = "jira" if source_type.lower() == "jira" else "dfmea"
    for raw_item in output["items"]:
        if not isinstance(raw_item, dict) or not raw_item.get("title"):
            continue
        try:
            items.append(
                RiskItem(
                    id=f"risk-{uuid4()}",
                    project_id=project_id,
                    source_type=normalized_source_type,
                    source_id=str(raw_item.get("source_id") or f"{normalized_source_type}-unknown"),
                    title=str(raw_item.get("title") or "风险项"),
                    description=str(raw_item.get("description") or raw_item.get("title") or "风险项"),
                    product_model=raw_item.get("product_model") if raw_item.get("product_model") else None,
                    test_object=str(raw_item.get("test_object") or "待确认对象"),
                    subsystem=str(raw_item.get("subsystem") or "待确认子系统"),
                    severity=str(raw_item.get("severity")) if raw_item.get("severity") is not None else None,
                    rpn=parse_int(str(raw_item.get("rpn"))) if raw_item.get("rpn") is not None else None,
                    failure_mode=str(raw_item.get("failure_mode")) if raw_item.get("failure_mode") else None,
                    failure_effect=str(raw_item.get("failure_effect")) if raw_item.get("failure_effect") else None,
                    root_cause=str(raw_item.get("root_cause")) if raw_item.get("root_cause") else None,
                    control_measure=str(raw_item.get("control_measure")) if raw_item.get("control_measure") else None,
                    suggested_test=str(raw_item.get("suggested_test") or "根据风险项补充对应子系统功能、性能或回归测试。"),
                    status=str(raw_item.get("status") or "active"),
                    created_at=datetime.now(UTC),
                )
            )
        except (TypeError, ValueError):
            continue
    return items or None


def enrich_risks_with_ai(project_id: str, source_type: str, content: str, fallback_items: list[RiskItem]) -> list[RiskItem]:
    ai_items = parse_risks_with_ai(project_id, source_type, content, fallback_items)
    if not ai_items:
        return fallback_items
    enriched: list[RiskItem] = []
    used_ai_ids: set[str] = set()
    for fallback in fallback_items:
        match = find_matching_ai_risk(fallback, ai_items)
        if match is None:
            enriched.append(fallback)
            continue
        used_ai_ids.add(match.id)
        enriched.append(
            fallback.model_copy(
                update={
                    "description": match.description or fallback.description,
                    "product_model": match.product_model or fallback.product_model,
                    "test_object": match.test_object if match.test_object != "待确认对象" else fallback.test_object,
                    "subsystem": match.subsystem if match.subsystem != "待确认子系统" else fallback.subsystem,
                    "severity": match.severity or fallback.severity,
                    "rpn": match.rpn if match.rpn is not None else fallback.rpn,
                    "failure_mode": match.failure_mode or fallback.failure_mode,
                    "failure_effect": match.failure_effect or fallback.failure_effect,
                    "root_cause": match.root_cause or fallback.root_cause,
                    "control_measure": match.control_measure or fallback.control_measure,
                    "suggested_test": match.suggested_test or fallback.suggested_test,
                }
            )
        )
    enriched.extend(item for item in ai_items if item.id not in used_ai_ids and not has_equivalent_risk(item, enriched))
    return enriched


def find_matching_ai_risk(fallback: RiskItem, ai_items: list[RiskItem]) -> RiskItem | None:
    for item in ai_items:
        if item.source_id == fallback.source_id or item.title == fallback.title:
            return item
    return None


def has_equivalent_risk(candidate: RiskItem, risks: list[RiskItem]) -> bool:
    return any(risk.source_id == candidate.source_id or risk.title == candidate.title for risk in risks)


def get_risk(risk_id: str) -> RiskItem | None:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.get(RiskRecord, risk_id)
            return _record_to_risk(record) if record is not None else None
    return RISKS.get(risk_id)


def update_risk(risk_id: str, payload: RiskUpdate) -> RiskItem | None:
    risk = get_risk(risk_id)
    if risk is None:
        return None
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return risk
    updated = risk.model_copy(update=updates)
    _save_risk(updated)
    return updated


def publish_risk(risk_id: str) -> RiskItem | None:
    risk = get_risk(risk_id)
    if risk is None:
        return None
    updated = risk.model_copy(update={"status": "published"})
    _save_risk(updated)
    return updated


def delete_risk(risk_id: str) -> bool:
    if _use_sqlalchemy():
        with session_scope() as session:
            result = session.execute(delete(RiskRecord).where(RiskRecord.id == risk_id))
            return (result.rowcount or 0) > 0
    return RISKS.pop(risk_id, None) is not None


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
