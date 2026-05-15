from datetime import datetime
from pydantic import BaseModel, Field


class SystemConfig(BaseModel):
    subsystem_catalog: list[str]
    document_types: list[str]
    test_levels: list[str]
    test_types: list[str]
    change_types: list[str]
    ai_external_reference_enabled: bool
    validation_template_version: str


class AiSettingsConfig(BaseModel):
    provider: str = "local"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout_seconds: int = 20


class SystemSettingsFile(BaseModel):
    system_config: SystemConfig
    ai_config: AiSettingsConfig = Field(default_factory=AiSettingsConfig)
    document_import_directory: str = ""
    validation_plan_export_directory: str = ""


class ValidationPlanExportConfig(BaseModel):
    export_directory: str
    configured: bool


class SystemConfigUpdate(BaseModel):
    subsystem_catalog: list[str] | None = None
    document_types: list[str] | None = None
    test_levels: list[str] | None = None
    test_types: list[str] | None = None
    change_types: list[str] | None = None


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
