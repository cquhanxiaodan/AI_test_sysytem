from datetime import datetime

from pydantic import BaseModel


class TestItemAsset(BaseModel):
    id: str
    project_id: str
    source_document_id: str
    title: str
    test_object: str
    primary_subsystem: str
    related_subsystems: list[str]
    test_level: str
    test_type: str
    risk_tags: list[str]
    objective: str
    method: str
    tools: list[str]
    steps: list[str]
    record_template: str
    evidence: str
    status: str
    created_at: datetime


class SplitResult(BaseModel):
    document_id: str
    items: list[TestItemAsset]
