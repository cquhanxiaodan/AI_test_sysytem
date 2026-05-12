from datetime import UTC, datetime
from uuid import uuid4

from app.modules.documents.repository import get_document
from app.modules.parsing.service import list_chunks
from app.modules.test_items.schemas import SplitResult, TestItemAsset

TEST_ITEMS: dict[str, TestItemAsset] = {}


def list_test_items(project_id: str | None = None) -> list[TestItemAsset]:
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
        TEST_ITEMS[item.id] = item
    return SplitResult(document_id=document_id, items=items)


def confirm_item(item_id: str) -> TestItemAsset | None:
    item = TEST_ITEMS.get(item_id)
    if item is None:
        return None
    updated = item.model_copy(update={"status": "published"})
    TEST_ITEMS[item_id] = updated
    return updated


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
