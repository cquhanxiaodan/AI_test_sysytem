from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import DateTime, Integer, JSON, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.core.storage import get_storage_backend
from app.modules.documents.schemas import (
    DocumentDuplicateResult,
    DocumentLabelSuggestion,
    DocumentRead,
)

DOCUMENTS: dict[str, DocumentRead] = {}


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(120), index=True)
    filename: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(200))
    size_bytes: Mapped[int] = mapped_column(Integer)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    storage_path: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(80), index=True)
    labels: Mapped[dict[str, str]] = mapped_column(JSON)
    label_suggestions: Mapped[list[dict]] = mapped_column(JSON)
    duplicate_results: Mapped[list[dict]] = mapped_column(JSON)
    uploaded_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def create_document(
    *,
    project_id: str,
    filename: str,
    content_type: str,
    content: bytes,
    uploaded_by: str,
) -> DocumentRead:
    file_hash = sha256(content).hexdigest()
    duplicate_results = find_duplicates(file_hash)
    document_id = f"doc-{uuid4()}"
    storage_path = get_storage_backend().put_bytes(f"documents/{document_id}/{filename}", content)
    document = DocumentRead(
        id=document_id,
        project_id=project_id,
        filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        file_hash=file_hash,
        storage_path=storage_path,
        status="pending_label" if duplicate_results == [] else "pending_duplicate_confirmation",
        labels={},
        label_suggestions=infer_label_suggestions(filename),
        duplicate_results=duplicate_results,
        uploaded_by=uploaded_by,
        created_at=datetime.now(UTC),
    )
    _save_document(document)
    return document


def find_document_by_hash(file_hash: str, project_id: str | None = None) -> DocumentRead | None:
    for document in list_documents(project_id):
        if document.file_hash == file_hash:
            return document
    return None


def list_documents(project_id: str | None = None) -> list[DocumentRead]:
    if _use_sqlalchemy():
        with session_scope() as session:
            statement = select(DocumentRecord)
            if project_id is not None:
                statement = statement.where(DocumentRecord.project_id == project_id)
            records = session.scalars(statement).all()
            documents = [_record_to_read(record) for record in records]
            return sorted(documents, key=lambda document: document.created_at, reverse=True)
    documents = list(DOCUMENTS.values())
    if project_id is not None:
        documents = [document for document in documents if document.project_id == project_id]
    return sorted(documents, key=lambda document: document.created_at, reverse=True)


def get_document(document_id: str) -> DocumentRead | None:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.get(DocumentRecord, document_id)
            return _record_to_read(record) if record is not None else None
    return DOCUMENTS.get(document_id)


def get_document_content(document_id: str) -> bytes | None:
    document = get_document(document_id)
    if document is None:
        return None
    return get_storage_backend().get_bytes(document.storage_path)


def update_labels(document_id: str, labels: dict[str, str]) -> DocumentRead | None:
    document = get_document(document_id)
    if document is None:
        return None
    updated = document.model_copy(update={"labels": labels, "status": "pending_review"})
    _save_document(updated)
    return updated


def review_document(document_id: str, action: str) -> DocumentRead | None:
    document = get_document(document_id)
    if document is None:
        return None
    status_by_action = {
        "publish": "published",
        "request_changes": "pending_label",
        "reject": "rejected",
        "mark_duplicate": "rejected_duplicate",
    }
    updated = document.model_copy(update={"status": status_by_action.get(action, document.status)})
    _save_document(updated)
    return updated


def find_duplicates(file_hash: str) -> list[DocumentDuplicateResult]:
    documents = list_documents() if _use_sqlalchemy() else list(DOCUMENTS.values())
    return [
        DocumentDuplicateResult(
            document_id=document.id,
            duplicate_type="exact_hash",
            similarity=1.0,
            suggestion="文件 hash 完全一致，建议标记为重复或合并为新版本。",
        )
        for document in documents
        if document.file_hash == file_hash
    ]


def _use_sqlalchemy() -> bool:
    return get_settings().repository_backend == "sqlalchemy"


def _save_document(document: DocumentRead) -> None:
    if _use_sqlalchemy():
        with session_scope() as session:
            session.merge(_read_to_record(document))
        return
    DOCUMENTS[document.id] = document


def _read_to_record(document: DocumentRead) -> DocumentRecord:
    return DocumentRecord(
        id=document.id,
        project_id=document.project_id,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        file_hash=document.file_hash,
        storage_path=document.storage_path,
        status=document.status,
        labels=document.labels,
        label_suggestions=[suggestion.model_dump() for suggestion in document.label_suggestions],
        duplicate_results=[duplicate.model_dump() for duplicate in document.duplicate_results],
        uploaded_by=document.uploaded_by,
        created_at=document.created_at,
    )


def _record_to_read(record: DocumentRecord) -> DocumentRead:
    return DocumentRead(
        id=record.id,
        project_id=record.project_id,
        filename=record.filename,
        content_type=record.content_type,
        size_bytes=record.size_bytes,
        file_hash=record.file_hash,
        storage_path=record.storage_path,
        status=record.status,
        labels=record.labels or {},
        label_suggestions=[DocumentLabelSuggestion(**suggestion) for suggestion in (record.label_suggestions or [])],
        duplicate_results=[DocumentDuplicateResult(**duplicate) for duplicate in (record.duplicate_results or [])],
        uploaded_by=record.uploaded_by,
        created_at=record.created_at,
    )


def infer_label_suggestions(filename: str) -> list[DocumentLabelSuggestion]:
    suggestions: list[DocumentLabelSuggestion] = []
    lowered = filename.lower()
    if "g99" in lowered or "dnbseq-g99" in lowered:
        suggestions.append(DocumentLabelSuggestion(label_key="product_model", label_value="DNBSEQ-G99", confidence=0.92, evidence="文件名包含 G99"))
    if "rfid" in lowered:
        suggestions.append(DocumentLabelSuggestion(label_key="subsystem", label_value="RFID", confidence=0.96, evidence="文件名包含 RFID"))
    if "验证方案" in filename:
        suggestions.append(DocumentLabelSuggestion(label_key="document_type", label_value="验证方案", confidence=0.9, evidence="文件名包含验证方案"))
    if "jira" in lowered:
        suggestions.append(DocumentLabelSuggestion(label_key="document_type", label_value="Jira导出", confidence=0.9, evidence="文件名包含 Jira"))
    if "dfmea" in lowered:
        suggestions.append(DocumentLabelSuggestion(label_key="document_type", label_value="DFMEA", confidence=0.9, evidence="文件名包含 DFMEA"))
    if "供应商" in filename or "二供" in filename:
        suggestions.append(DocumentLabelSuggestion(label_key="change_type", label_value="供应商变更", confidence=0.82, evidence="文件名包含供应商或二供"))
    return suggestions
