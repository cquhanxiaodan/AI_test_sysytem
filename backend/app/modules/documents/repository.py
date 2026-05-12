from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from app.modules.documents.schemas import (
    DocumentDuplicateResult,
    DocumentLabelSuggestion,
    DocumentRead,
)

DOCUMENTS: dict[str, DocumentRead] = {}
DOCUMENT_CONTENTS: dict[str, bytes] = {}


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
    document = DocumentRead(
        id=f"doc-{uuid4()}",
        project_id=project_id,
        filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        file_hash=file_hash,
        status="pending_label" if duplicate_results == [] else "pending_duplicate_confirmation",
        labels={},
        label_suggestions=infer_label_suggestions(filename),
        duplicate_results=duplicate_results,
        uploaded_by=uploaded_by,
        created_at=datetime.now(UTC),
    )
    DOCUMENTS[document.id] = document
    DOCUMENT_CONTENTS[document.id] = content
    return document


def list_documents(project_id: str | None = None) -> list[DocumentRead]:
    documents = list(DOCUMENTS.values())
    if project_id is not None:
        documents = [document for document in documents if document.project_id == project_id]
    return sorted(documents, key=lambda document: document.created_at, reverse=True)


def get_document(document_id: str) -> DocumentRead | None:
    return DOCUMENTS.get(document_id)


def get_document_content(document_id: str) -> bytes | None:
    return DOCUMENT_CONTENTS.get(document_id)


def update_labels(document_id: str, labels: dict[str, str]) -> DocumentRead | None:
    document = DOCUMENTS.get(document_id)
    if document is None:
        return None
    updated = document.model_copy(update={"labels": labels, "status": "pending_review"})
    DOCUMENTS[document_id] = updated
    return updated


def review_document(document_id: str, action: str) -> DocumentRead | None:
    document = DOCUMENTS.get(document_id)
    if document is None:
        return None
    status_by_action = {
        "publish": "published",
        "request_changes": "pending_label",
        "reject": "rejected",
        "mark_duplicate": "rejected_duplicate",
    }
    updated = document.model_copy(update={"status": status_by_action.get(action, document.status)})
    DOCUMENTS[document_id] = updated
    return updated


def find_duplicates(file_hash: str) -> list[DocumentDuplicateResult]:
    return [
        DocumentDuplicateResult(
            document_id=document.id,
            duplicate_type="exact_hash",
            similarity=1.0,
            suggestion="文件 hash 完全一致，建议标记为重复或合并为新版本。",
        )
        for document in DOCUMENTS.values()
        if document.file_hash == file_hash
    ]


def infer_label_suggestions(filename: str) -> list[DocumentLabelSuggestion]:
    suggestions: list[DocumentLabelSuggestion] = []
    lowered = filename.lower()
    if "g99" in lowered or "dnbseq-g99" in lowered:
        suggestions.append(DocumentLabelSuggestion(label_key="product_model", label_value="DNBSEQ-G99", confidence=0.92, evidence="文件名包含 G99"))
    if "rfid" in lowered:
        suggestions.append(DocumentLabelSuggestion(label_key="subsystem", label_value="RFID", confidence=0.96, evidence="文件名包含 RFID"))
    if "验证方案" in filename:
        suggestions.append(DocumentLabelSuggestion(label_key="document_type", label_value="验证方案", confidence=0.9, evidence="文件名包含验证方案"))
    if "供应商" in filename or "二供" in filename:
        suggestions.append(DocumentLabelSuggestion(label_key="change_type", label_value="供应商变更", confidence=0.82, evidence="文件名包含供应商或二供"))
    return suggestions
