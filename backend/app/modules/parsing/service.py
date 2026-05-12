from datetime import UTC, datetime
from uuid import uuid4

from app.modules.documents.repository import get_document, get_document_content, update_labels
from app.modules.parsing.schemas import DocumentChunk, ParsingTaskRead

TASKS: dict[str, ParsingTaskRead] = {}
CHUNKS: dict[str, list[DocumentChunk]] = {}


def run_parse_task(document_id: str) -> ParsingTaskRead | None:
    document = get_document(document_id)
    content = get_document_content(document_id)
    if document is None or content is None:
        return None

    text = extract_text(document.filename, content)
    chunks = build_chunks(document_id, text)
    CHUNKS[document_id] = chunks
    task = ParsingTaskRead(
        id=f"task-{uuid4()}",
        document_id=document_id,
        task_type="parse_and_chunk",
        status="succeeded",
        message=f"已生成 {len(chunks)} 个文档切片",
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        chunks=chunks,
    )
    TASKS[task.id] = task
    return task


def run_label_extraction_task(document_id: str) -> ParsingTaskRead | None:
    document = get_document(document_id)
    if document is None:
        return None

    labels = dict(document.labels)
    for suggestion in document.label_suggestions:
        if suggestion.confidence >= 0.85:
            labels.setdefault(suggestion.label_key, suggestion.label_value)
    update_labels(document_id, labels)
    task = ParsingTaskRead(
        id=f"task-{uuid4()}",
        document_id=document_id,
        task_type="document_label_extraction",
        status="succeeded",
        message="已根据高置信度建议更新资料标签",
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        chunks=[],
    )
    TASKS[task.id] = task
    return task


def get_task(task_id: str) -> ParsingTaskRead | None:
    return TASKS.get(task_id)


def list_chunks(document_id: str) -> list[DocumentChunk]:
    return CHUNKS.get(document_id, [])


def extract_text(filename: str, content: bytes) -> str:
    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError:
        decoded = ""

    if decoded.strip():
        return decoded
    return f"{filename}\n该资料已上传，真实解析器接入后将提取 Word/PDF/Excel 正文、表格和章节结构。"


def build_chunks(document_id: str, text: str) -> list[DocumentChunk]:
    paragraphs = [paragraph.strip() for paragraph in text.splitlines() if paragraph.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]
    return [
        DocumentChunk(
            id=f"chunk-{uuid4()}",
            document_id=document_id,
            sequence=index + 1,
            heading=paragraph if index == 0 else None,
            page_number=None,
            text=paragraph,
        )
        for index, paragraph in enumerate(paragraphs)
    ]
