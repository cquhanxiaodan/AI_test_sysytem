from datetime import datetime

from pydantic import BaseModel, Field


class DocumentLabelSuggestion(BaseModel):
    label_key: str
    label_value: str
    confidence: float = Field(ge=0, le=1)
    evidence: str


class DocumentDuplicateResult(BaseModel):
    document_id: str
    duplicate_type: str
    similarity: float
    suggestion: str


class DocumentRead(BaseModel):
    id: str
    project_id: str
    filename: str
    content_type: str
    size_bytes: int
    file_hash: str
    status: str
    labels: dict[str, str]
    label_suggestions: list[DocumentLabelSuggestion]
    duplicate_results: list[DocumentDuplicateResult]
    uploaded_by: str
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    document: DocumentRead


class DocumentLabelUpdate(BaseModel):
    labels: dict[str, str]


class DocumentReviewRequest(BaseModel):
    action: str
    comment: str | None = None
