from datetime import datetime

from pydantic import BaseModel


class ValidationPlanItem(BaseModel):
    sequence: int
    title: str
    group: str
    objective: str
    method: str
    tools: list[str] = []
    steps: list[str] = []
    connection_media: str = ""
    record_template: str
    compliance_bug_info: str = ""
    source_section_text: str = ""
    source_blocks: list[dict] = []
    evidence: str


class ValidationPlanRead(BaseModel):
    id: str
    project_id: str
    requirement_analysis_ids: list[str]
    title: str
    template_version: str
    overview: str
    dut_description: str
    reference_documents: list[str]
    items: list[ValidationPlanItem]
    status: str
    created_at: datetime


class ValidationPlanCreateRequest(BaseModel):
    requirement_analysis_id: str | None = None
    project_id: str | None = None


class ValidationPlanExportRequest(BaseModel):
    export_directory: str = ""


class ValidationPlanStatusUpdate(BaseModel):
    status: str


class ValidationPlanBulkDeleteRequest(BaseModel):
    plan_ids: list[str]


class ValidationPlanBulkDeleteResponse(BaseModel):
    deleted_ids: list[str]
    skipped: list[dict[str, str]]


class ValidationPlanCheckResult(BaseModel):
    blocking: list[str]
    warnings: list[str]
    suggestions: list[str]


class ExportRecord(BaseModel):
    id: str
    validation_plan_id: str
    filename: str
    template_version: str
    status: str
    storage_path: str
    download_url: str
    created_at: datetime
