from datetime import datetime
from pydantic import BaseModel


class SystemConfig(BaseModel):
    subsystem_catalog: list[str]
    document_types: list[str]
    test_types: list[str]
    change_types: list[str]
    ai_external_reference_enabled: bool
    validation_template_version: str


class AuditEvent(BaseModel):
    id: str
    actor_id: str
    action: str
    target_type: str
    target_id: str
    detail: str
    created_at: datetime


class AuditEventCreate(BaseModel):
    action: str
    target_type: str
    target_id: str
    detail: str


class AcceptanceStatus(BaseModel):
    completed_stages: list[str]
    backend_test_count: int
    frontend_build: str
    remaining_risks: list[str]
