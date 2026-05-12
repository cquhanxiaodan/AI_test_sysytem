from datetime import datetime

from pydantic import BaseModel


class DocumentChunk(BaseModel):
    id: str
    document_id: str
    sequence: int
    heading: str | None
    page_number: int | None
    text: str


class ParsingTaskRead(BaseModel):
    id: str
    document_id: str
    task_type: str
    status: str
    message: str
    created_at: datetime
    completed_at: datetime | None
    chunks: list[DocumentChunk] = []
