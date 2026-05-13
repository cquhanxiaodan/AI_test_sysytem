from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.documents.repository import get_document
from app.modules.parsing.service import list_chunks
from app.modules.test_items.schemas import SplitResult, TestItemAsset

TEST_ITEMS: dict[str, TestItemAsset] = {}


class TestItemRecord(Base):
    __tablename__ = "test_items"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(120), index=True)
    source_document_id: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(500))
    test_object: Mapped[str] = mapped_column(String(120), index=True)
    primary_subsystem: Mapped[str] = mapped_column(String(120), index=True)
    related_subsystems: Mapped[list[str]] = mapped_column(JSON)
    test_level: Mapped[str] = mapped_column(String(120))
    test_type: Mapped[str] = mapped_column(String(120))
    risk_tags: Mapped[list[str]] = mapped_column(JSON)
    objective: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(Text)
    tools: Mapped[list[str]] = mapped_column(JSON)
    steps: Mapped[list[str]] = mapped_column(JSON)
    record_template: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def list_test_items(project_id: str | None = None) -> list[TestItemAsset]:
    if _use_sqlalchemy():
        with session_scope() as session:
            statement = select(TestItemRecord)
            if project_id is not None:
                statement = statement.where(TestItemRecord.project_id == project_id)
            records = session.scalars(statement).all()
            items = [_record_to_item(record) for record in records]
            return sorted(items, key=lambda item: item.created_at, reverse=True)
    items = list(TEST_ITEMS.values())
    if project_id is not None:
        items = [item for item in items if item.project_id == project_id]
    return sorted(items, key=lambda item: item.created_at, reverse=True)


def split_document_to_items(document_id: str) -> SplitResult | None:
    document = get_document(document_id)
    if document is None:
        return None

    chunks = list_chunks(document_id)
    text = "\n".join(chunk.text for chunk in chunks) or document.filename
    titles = infer_test_titles(text)
    items = [build_test_item(document.project_id, document_id, title, text) for title in titles]
    for item in items:
        _save_item(item)
    return SplitResult(document_id=document_id, items=items)


def confirm_item(item_id: str) -> TestItemAsset | None:
    item = get_item(item_id)
    if item is None:
        return None
    updated = item.model_copy(update={"status": "published"})
    _save_item(updated)
    return updated


def get_item(item_id: str) -> TestItemAsset | None:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.get(TestItemRecord, item_id)
            return _record_to_item(record) if record is not None else None
    return TEST_ITEMS.get(item_id)


def infer_test_titles(text: str) -> list[str]:
    lowered = text.lower()
    if "rfid" in lowered:
        return [
            "RFID 在机装配测试",
            "RFID 装配后初始化测试",
            "RFID 在机读取测试",
            "RFID 在机写入测试",
            "安规 EMC 测试",
        ]
    return ["资料来源测试条目"]


def build_test_item(project_id: str, document_id: str, title: str, evidence_text: str) -> TestItemAsset:
    return TestItemAsset(
        id=f"item-{uuid4()}",
        project_id=project_id,
        source_document_id=document_id,
        title=title,
        test_object="RFID" if "RFID" in title else "待确认对象",
        primary_subsystem="RFID" if "RFID" in title else "待确认子系统",
        related_subsystems=["整机系统"] if "安规" in title or "EMC" in title else [],
        test_level="系统级" if "安规" in title or "EMC" in title else "子系统级",
        test_type=infer_test_type(title),
        risk_tags=["供应商变更", "兼容性"],
        objective=f"验证{title}满足需求和风险控制要求。",
        method="基于验证方案章节拆分生成，后续由测试工程师确认方法和标准。",
        tools=["DNBSEQ-G99", "RFID 标签", "测试工装"],
        steps=["准备 DUT 和测试环境", f"执行{title}", "记录结果并判断是否符合验收标准"],
        record_template="记录样本编号、测试步骤、实际结果、判定结论和关联 BUG。",
        evidence=evidence_text[:500],
        status="draft",
        created_at=datetime.now(UTC),
    )


def infer_test_type(title: str) -> str:
    if "读取" in title:
        return "功能-读取"
    if "写入" in title:
        return "功能-写入"
    if "初始化" in title:
        return "功能-初始化"
    if "装配" in title:
        return "装配兼容性"
    if "安规" in title or "EMC" in title:
        return "安规 EMC"
    return "功能测试"


def _use_sqlalchemy() -> bool:
    return get_settings().repository_backend == "sqlalchemy"


def _save_item(item: TestItemAsset) -> None:
    if _use_sqlalchemy():
        with session_scope() as session:
            session.merge(_item_to_record(item))
        return
    TEST_ITEMS[item.id] = item


def _item_to_record(item: TestItemAsset) -> TestItemRecord:
    return TestItemRecord(
        id=item.id,
        project_id=item.project_id,
        source_document_id=item.source_document_id,
        title=item.title,
        test_object=item.test_object,
        primary_subsystem=item.primary_subsystem,
        related_subsystems=item.related_subsystems,
        test_level=item.test_level,
        test_type=item.test_type,
        risk_tags=item.risk_tags,
        objective=item.objective,
        method=item.method,
        tools=item.tools,
        steps=item.steps,
        record_template=item.record_template,
        evidence=item.evidence,
        status=item.status,
        created_at=item.created_at,
    )


def _record_to_item(record: TestItemRecord) -> TestItemAsset:
    return TestItemAsset(
        id=record.id,
        project_id=record.project_id,
        source_document_id=record.source_document_id,
        title=record.title,
        test_object=record.test_object,
        primary_subsystem=record.primary_subsystem,
        related_subsystems=record.related_subsystems or [],
        test_level=record.test_level,
        test_type=record.test_type,
        risk_tags=record.risk_tags or [],
        objective=record.objective,
        method=record.method,
        tools=record.tools or [],
        steps=record.steps or [],
        record_template=record.record_template,
        evidence=record.evidence,
        status=record.status,
        created_at=record.created_at,
    )
