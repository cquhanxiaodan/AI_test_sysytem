from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, Text, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.admin.service import get_config
from app.modules.ai.service import run_json_task
from app.modules.documents.repository import get_document
from app.modules.parsing.service import list_chunks
from app.modules.test_items.schemas import SplitResult, TestItemAsset, TestItemUpdate

TEST_ITEMS: dict[str, TestItemAsset] = {}

DEFAULT_SECTION_LABELS = {
    "objective": ["测试目的/测试标准", "测试目的", "测试标准"],
    "method": ["测试方法/原理", "测试方法", "测试原理"],
    "tools": ["测试工具"],
    "steps": ["测试步骤"],
    "connection_media": ["测试连接图或照片"],
    "record_template": ["测试记录", "记录模板"],
    "compliance_bug_info": ["需求符合性和BUG信息", "需求符合性结果", "测试发现的BUG信息表"],
}


@dataclass
class ExtractedTestSection:
    title: str
    objective: str = ""
    method: str = ""
    tools: list[str] | None = None
    steps: list[str] | None = None
    connection_media: str = ""
    record_template: str = ""
    compliance_bug_info: str = ""
    source_section_text: str = ""


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
    connection_media: Mapped[str] = mapped_column(Text, default="")
    record_template: Mapped[str] = mapped_column(Text)
    compliance_bug_info: Mapped[str] = mapped_column(Text, default="")
    source_section_text: Mapped[str] = mapped_column(Text, default="")
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


def split_document_to_items(document_id: str, use_ai: bool = True) -> SplitResult | None:
    document = get_document(document_id)
    if document is None:
        return None

    chunks = list_chunks(document_id)
    text = "\n".join(chunk.text for chunk in chunks) or document.filename
    extracted_sections = extract_test_sections(text)
    titles = [section.title for section in extracted_sections] or infer_test_titles(text)
    section_by_title = {section.title: section for section in extracted_sections}
    items = [build_test_item(document.project_id, document_id, document.filename, title, section_by_title.get(title)) for title in titles]
    if use_ai:
        items = split_items_with_ai(document.project_id, document_id, document.filename, text, items) or items
    items = [prefer_local_extracted_fields(item, document.filename, section_by_title.get(item.title)) for item in items]
    saved_items = upsert_split_items(document_id, items)
    return SplitResult(document_id=document_id, items=saved_items)


def upsert_split_items(document_id: str, items: list[TestItemAsset]) -> list[TestItemAsset]:
    existing_by_title = {normalize_test_item_title(item.title): item for item in list_test_items() if item.source_document_id == document_id}
    saved_items: list[TestItemAsset] = []
    for item in deduplicate_items_by_title(items):
        existing = existing_by_title.get(normalize_test_item_title(item.title))
        if existing is not None:
            item = item.model_copy(update={"id": existing.id, "status": existing.status, "created_at": existing.created_at})
        _save_item(item)
        saved_items.append(item)
    return saved_items


def deduplicate_items_by_title(items: list[TestItemAsset]) -> list[TestItemAsset]:
    deduplicated: list[TestItemAsset] = []
    seen: set[str] = set()
    for item in items:
        key = normalize_test_item_title(item.title)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(item)
    return deduplicated


def normalize_test_item_title(title: str) -> str:
    return "".join(title.lower().split())


def split_items_with_ai(project_id: str, document_id: str, filename: str, text: str, fallback_items: list[TestItemAsset]) -> list[TestItemAsset] | None:
    output = run_json_task(
        "test_item_split",
        "你是基因测序仪验证方案拆分助手。只输出 JSON，不输出解释。",
        (
            "从验证方案、测试规范或测试报告中拆分测试条目，输出 items 数组。"
            "每个条目包含 title、test_object、primary_subsystem、related_subsystems、test_level、test_type、risk_tags、objective、method、tools、steps、connection_media、record_template、compliance_bug_info、source_section_text、evidence。"
            "优先按 3.x 测试项目拆分，保留测试项目原始 7 段内容，缺失字段使用待确认。"
            f"\n文件名：{filename}"
            f"\n本地候选：{[item.title for item in fallback_items]}"
            f"\n资料内容：\n{text[:8000]}"
        ),
    )
    if output is None or not isinstance(output.get("items"), list):
        return None
    items: list[TestItemAsset] = []
    for raw_item in output["items"]:
        if not isinstance(raw_item, dict) or not raw_item.get("title"):
            continue
        try:
            items.append(
                TestItemAsset(
                    id=f"item-{uuid4()}",
                    project_id=project_id,
                    source_document_id=document_id,
                    title=str(raw_item.get("title") or "资料来源测试条目"),
                    test_object=str(raw_item.get("test_object") or "待确认对象"),
                    primary_subsystem=str(raw_item.get("primary_subsystem") or raw_item.get("subsystem") or "待确认子系统"),
                    related_subsystems=[str(value) for value in raw_item.get("related_subsystems", []) if isinstance(value, str)],
                    test_level=str(raw_item.get("test_level") or "待确认层级"),
                    test_type=str(raw_item.get("test_type") or "功能测试"),
                    risk_tags=[str(value) for value in raw_item.get("risk_tags", []) if isinstance(value, str)],
                    objective=str(raw_item.get("objective") or f"验证{raw_item.get('title')}满足需求。"),
                    method=str(raw_item.get("method") or "待测试工程师确认方法和标准。"),
                    tools=[str(value) for value in raw_item.get("tools", []) if isinstance(value, str)],
                    steps=[str(value) for value in raw_item.get("steps", []) if isinstance(value, str)],
                    connection_media=str(raw_item.get("connection_media") or "待补充"),
                    record_template=str(raw_item.get("record_template") or "记录测试条件、实际结果、判定结论和关联 BUG。"),
                    compliance_bug_info=str(raw_item.get("compliance_bug_info") or "记录需求符合性结论和关联 BUG 信息。"),
                    source_section_text=str(raw_item.get("source_section_text") or ""),
                    evidence=filename,
                    status="draft",
                    created_at=datetime.now(UTC),
                )
            )
        except (TypeError, ValueError):
            continue
    return items or None


def confirm_item(item_id: str) -> TestItemAsset | None:
    item = get_item(item_id)
    if item is None:
        return None
    updated = item.model_copy(update={"status": "published"})
    _save_item(updated)
    return updated


def update_item(item_id: str, payload: TestItemUpdate) -> TestItemAsset | None:
    item = get_item(item_id)
    if item is None:
        return None
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return item
    updated = item.model_copy(update={**updates, "status": "draft" if item.status != "draft" else item.status})
    _save_item(updated)
    return updated


def delete_item(item_id: str) -> bool:
    if _use_sqlalchemy():
        with session_scope() as session:
            result = session.execute(delete(TestItemRecord).where(TestItemRecord.id == item_id))
            return (result.rowcount or 0) > 0
    return TEST_ITEMS.pop(item_id, None) is not None


def create_item_from_fields(
    project_id: str,
    title: str,
    test_object: str,
    subsystem: str,
    objective: str,
    method: str,
    record_template: str,
    evidence: str,
) -> TestItemAsset:
    existing = find_test_item_by_title(project_id, title)
    if existing is not None:
        updated = existing.model_copy(
            update={
                "test_object": test_object,
                "primary_subsystem": subsystem,
                "objective": objective,
                "method": method,
                "connection_media": "待补充",
                "record_template": record_template,
                "compliance_bug_info": "记录需求符合性结论和关联 BUG 信息。",
                "evidence": evidence,
                "status": "published",
            }
        )
        _save_item(updated)
        return updated
    item = TestItemAsset(
        id=f"item-{uuid4()}",
        project_id=project_id,
        source_document_id="ai-recommendation",
        title=title,
        test_object=test_object,
        primary_subsystem=subsystem,
        related_subsystems=[],
        test_level="待确认层级",
        test_type=infer_test_type(title),
        risk_tags=["AI补充", "需求分析"],
        objective=objective,
        method=method,
        tools=[],
        steps=[f"执行{title}", "记录测试结果并判断是否符合验收标准"],
        connection_media="待补充",
        record_template=record_template,
        compliance_bug_info="记录需求符合性结论和关联 BUG 信息。",
        source_section_text="",
        evidence=evidence,
        status="published",
        created_at=datetime.now(UTC),
    )
    _save_item(item)
    return item


def find_test_item_by_title(project_id: str, title: str) -> TestItemAsset | None:
    normalized_title = normalize_test_item_title(title)
    return next((item for item in list_test_items(project_id) if normalize_test_item_title(item.title) == normalized_title), None)


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


def extract_test_sections(text: str) -> list[ExtractedTestSection]:
    lines = normalize_lines(text)
    section_labels = get_section_labels()
    boundary_labels = get_boundary_labels(section_labels)
    titles = infer_project_table_titles(lines, section_labels, boundary_labels)
    sections: list[ExtractedTestSection] = []
    for index, title in enumerate(titles):
        start = find_detail_line_index(lines, title)
        if start is None:
            continue
        next_start = find_next_title_index(lines, titles, start + 1)
        section_lines = lines[start + 1 : next_start]
        sections.append(
            ExtractedTestSection(
                title=title,
                objective=extract_labeled_text(section_lines, section_labels["objective"], boundary_labels),
                method=extract_labeled_text(section_lines, section_labels["method"], boundary_labels),
                tools=split_list_text(extract_labeled_text(section_lines, section_labels["tools"], boundary_labels)),
                steps=split_list_text(extract_labeled_text(section_lines, section_labels["steps"], boundary_labels)),
                connection_media=extract_labeled_text(section_lines, section_labels["connection_media"], boundary_labels),
                record_template=extract_labeled_text(section_lines, section_labels["record_template"], boundary_labels),
                compliance_bug_info=extract_labeled_text(section_lines, section_labels["compliance_bug_info"], boundary_labels),
                source_section_text="\n".join([title, *section_lines]).strip(),
            )
        )
    return sections


def normalize_lines(text: str) -> list[str]:
    normalized = text.replace("\r", "\n").replace("；", "；\n")
    return [line.strip() for line in normalized.splitlines() if line.strip()]


def get_section_labels() -> dict[str, list[str]]:
    configured = get_config().template_section_aliases
    labels = {key: list(values) for key, values in DEFAULT_SECTION_LABELS.items()}
    for key, values in configured.items():
        if key in labels and values:
            labels[key] = values
    return labels


def get_boundary_labels(section_labels: dict[str, list[str]]) -> set[str]:
    return {label for labels in section_labels.values() for label in labels}


def infer_project_table_titles(lines: list[str], section_labels: dict[str, list[str]], boundary_labels: set[str]) -> list[str]:
    detail_titles = infer_detail_titles(lines, section_labels, boundary_labels)
    if detail_titles:
        return detail_titles
    titles: list[str] = []
    in_project_list = False
    for line in lines:
        if line == "测试项目列表":
            in_project_list = True
            continue
        if in_project_list and line in {"测试项目", "测试项目详情"}:
            continue
        if in_project_list:
            if line in boundary_labels:
                break
            if line.endswith("测试") and line not in titles:
                titles.append(line)
                continue
            if titles and line == titles[0]:
                break
    if titles:
        return titles
    return [line for line in lines if line.endswith("测试") and line not in boundary_labels]


def infer_detail_titles(lines: list[str], section_labels: dict[str, list[str]], boundary_labels: set[str]) -> list[str]:
    titles: list[str] = []
    objective_labels = set(section_labels["objective"])
    for index, line in enumerate(lines):
        if not line.endswith("测试") or line in boundary_labels:
            continue
        lookahead = lines[index + 1 : index + 5]
        if any(value in objective_labels for value in lookahead) and line not in titles:
            titles.append(line)
    return titles


def find_line_index(lines: list[str], target: str, start: int = 0) -> int | None:
    for index in range(start, len(lines)):
        if lines[index] == target:
            return index
    return None


def find_detail_line_index(lines: list[str], target: str) -> int | None:
    matches = [index for index, line in enumerate(lines) if line == target]
    if len(matches) >= 2:
        return matches[1]
    return matches[0] if matches else None


def find_next_title_index(lines: list[str], titles: list[str], start: int) -> int | None:
    for index in range(start, len(lines)):
        if lines[index] in titles:
            return index
    return None


def extract_labeled_text(lines: list[str], labels: list[str], boundary_labels: set[str]) -> str:
    start = next((index for index, line in enumerate(lines) if line in labels), None)
    if start is None:
        return ""
    collected: list[str] = []
    for line in lines[start + 1 :]:
        if line in boundary_labels:
            break
        collected.append(line)
    return "\n".join(collected).strip()


def split_list_text(text: str) -> list[str]:
    if not text:
        return []
    values: list[str] = []
    for line in text.replace("；", "\n").replace(";", "\n").splitlines():
        item = line.strip(" ；;、")
        if item and item not in values and item != "/":
            values.append(item)
    return values


def build_test_item(project_id: str, document_id: str, filename: str, title: str, section: ExtractedTestSection | None = None) -> TestItemAsset:
    objective = section.objective if section and section.objective else f"验证{title}满足需求和风险控制要求。"
    method = section.method if section and section.method else "基于验证方案章节拆分生成，后续由测试工程师确认方法和标准。"
    tools = section.tools if section and section.tools else ["DNBSEQ-G99", "RFID 标签", "测试工装"]
    steps = section.steps if section and section.steps else ["准备 DUT 和测试环境", f"执行{title}", "记录结果并判断是否符合验收标准"]
    record_template = section.record_template if section and section.record_template else "记录样本编号、测试步骤、实际结果、判定结论和关联 BUG。"
    connection_media = section.connection_media if section and section.connection_media else "待补充"
    compliance_bug_info = section.compliance_bug_info if section and section.compliance_bug_info else "记录需求符合性结论和关联 BUG 信息。"
    source_section_text = section.source_section_text if section and section.source_section_text else ""
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
        objective=objective,
        method=method,
        tools=tools,
        steps=steps,
        connection_media=connection_media,
        record_template=record_template,
        compliance_bug_info=compliance_bug_info,
        source_section_text=source_section_text,
        evidence=filename,
        status="draft",
        created_at=datetime.now(UTC),
    )


def prefer_local_extracted_fields(item: TestItemAsset, filename: str, section: ExtractedTestSection | None) -> TestItemAsset:
    if section is None:
        return item.model_copy(update={"evidence": filename})
    updates = {"evidence": filename}
    if section.objective:
        updates["objective"] = section.objective
    if section.method:
        updates["method"] = section.method
    if section.tools:
        updates["tools"] = section.tools
    if section.steps:
        updates["steps"] = section.steps
    if section.connection_media:
        updates["connection_media"] = section.connection_media
    if section.record_template:
        updates["record_template"] = section.record_template
    if section.compliance_bug_info:
        updates["compliance_bug_info"] = section.compliance_bug_info
    if section.source_section_text:
        updates["source_section_text"] = section.source_section_text
    return item.model_copy(update=updates)


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
        connection_media=item.connection_media,
        record_template=item.record_template,
        compliance_bug_info=item.compliance_bug_info,
        source_section_text=item.source_section_text,
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
        connection_media=getattr(record, "connection_media", None) or "",
        record_template=record.record_template,
        compliance_bug_info=getattr(record, "compliance_bug_info", None) or "",
        source_section_text=getattr(record, "source_section_text", None) or "",
        evidence=record.evidence,
        status=record.status,
        created_at=record.created_at,
    )
