from datetime import datetime

from pydantic import BaseModel


class TestItemAsset(BaseModel):
    id: str
    project_id: str
    source_document_id: str
    title: str
    test_object: str
    primary_subsystem: str
    module: str = ""
    related_subsystems: list[str]
    test_level: str
    test_type: str
    risk_tags: list[str]
    objective: str
    method: str
    tools: list[str]
    steps: list[str]
    connection_media: str = ""
    record_template: str
    compliance_bug_info: str = ""
    source_section_text: str = ""
    evidence: str
    status: str
    created_at: datetime


class TestItemUpdate(BaseModel):
    title: str | None = None
    test_object: str | None = None
    primary_subsystem: str | None = None
    module: str | None = None
    related_subsystems: list[str] | None = None
    test_level: str | None = None
    test_type: str | None = None
    risk_tags: list[str] | None = None
    objective: str | None = None
    method: str | None = None
    tools: list[str] | None = None
    steps: list[str] | None = None
    connection_media: str | None = None
    record_template: str | None = None
    compliance_bug_info: str | None = None


class TestItemBulkDeleteRequest(BaseModel):
    item_ids: list[str]


class TestItemBulkDeleteResponse(BaseModel):
    deleted_ids: list[str]
    skipped: list[dict[str, str]]


class TestItemBulkPublishRequest(BaseModel):
    item_ids: list[str]


class TestItemBulkPublishResponse(BaseModel):
    published_ids: list[str]
    skipped: list[dict[str, str]]


class SplitResult(BaseModel):
    document_id: str
    items: list[TestItemAsset]
