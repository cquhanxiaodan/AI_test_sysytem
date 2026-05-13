from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.documents.repository import get_document, get_document_content, update_labels
from app.modules.parsing.schemas import DocumentChunk, ParsingTaskRead

TASKS: dict[str, ParsingTaskRead] = {}
CHUNKS: dict[str, list[DocumentChunk]] = {}


class ParsingTaskRecord(Base):
    __tablename__ = "parsing_tasks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(120), index=True)
    task_type: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    message: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentChunkRecord(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(120), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(String(500), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text)


def run_parse_task(document_id: str) -> ParsingTaskRead | None:
    document = get_document(document_id)
    content = get_document_content(document_id)
    if document is None or content is None:
        return None

    text = extract_text(document.filename, content)
    chunks = build_chunks(document_id, text)
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
    _save_chunks(document_id, chunks)
    _save_task(task)
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
    _save_task(task)
    return task


def get_task(task_id: str) -> ParsingTaskRead | None:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.get(ParsingTaskRecord, task_id)
            return _task_record_to_read(record) if record is not None else None
    return TASKS.get(task_id)


def list_chunks(document_id: str) -> list[DocumentChunk]:
    if _use_sqlalchemy():
        with session_scope() as session:
            records = session.scalars(
                select(DocumentChunkRecord).where(DocumentChunkRecord.document_id == document_id).order_by(DocumentChunkRecord.sequence)
            ).all()
            return [_chunk_record_to_read(record) for record in records]
    return CHUNKS.get(document_id, [])


def _use_sqlalchemy() -> bool:
    return get_settings().repository_backend == "sqlalchemy"


def _save_task(task: ParsingTaskRead) -> None:
    if _use_sqlalchemy():
        with session_scope() as session:
            session.merge(
                ParsingTaskRecord(
                    id=task.id,
                    document_id=task.document_id,
                    task_type=task.task_type,
                    status=task.status,
                    message=task.message,
                    created_at=task.created_at,
                    completed_at=task.completed_at,
                )
            )
        return
    TASKS[task.id] = task


def _save_chunks(document_id: str, chunks: list[DocumentChunk]) -> None:
    if _use_sqlalchemy():
        with session_scope() as session:
            session.execute(delete(DocumentChunkRecord).where(DocumentChunkRecord.document_id == document_id))
            for chunk in chunks:
                session.merge(
                    DocumentChunkRecord(
                        id=chunk.id,
                        document_id=chunk.document_id,
                        sequence=chunk.sequence,
                        heading=chunk.heading,
                        page_number=chunk.page_number,
                        text=chunk.text,
                    )
                )
        return
    CHUNKS[document_id] = chunks


def _task_record_to_read(record: ParsingTaskRecord) -> ParsingTaskRead:
    return ParsingTaskRead(
        id=record.id,
        document_id=record.document_id,
        task_type=record.task_type,
        status=record.status,
        message=record.message,
        created_at=record.created_at,
        completed_at=record.completed_at,
        chunks=list_chunks(record.document_id) if record.task_type == "parse_and_chunk" else [],
    )


def _chunk_record_to_read(record: DocumentChunkRecord) -> DocumentChunk:
    return DocumentChunk(
        id=record.id,
        document_id=record.document_id,
        sequence=record.sequence,
        heading=record.heading,
        page_number=record.page_number,
        text=record.text,
    )


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
