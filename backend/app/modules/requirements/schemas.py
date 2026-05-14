from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RequirementParseResult(BaseModel):
    test_object: str
    change_type: str
    product_model: str | None
    subsystem: str
    missing_fields: list[str]


class RequirementRecommendation(BaseModel):
    id: str
    group: str
    title: str
    source_type: str
    source_id: str
    reason: str
    evidence: str
    review_status: str = "pending"


class RequirementRecommendationUpdate(BaseModel):
    group: str | None = None
    title: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    reason: str | None = None
    evidence: str | None = None
    review_status: str | None = None


class RequirementRecommendationCreate(BaseModel):
    group: str
    title: str
    source_type: str = "manual"
    source_id: str = "manual"
    reason: str = "人工新增"
    evidence: str = "人工新增推荐项"
    review_status: str = "confirmed"


class RequirementAnalysisRequest(BaseModel):
    project_id: str
    description: str


class RequirementDocumentUploadResponse(BaseModel):
    filename: str
    description: str


class RequirementTemplateField(BaseModel):
    name: str
    required: bool
    description: str


class RequirementTemplateRead(BaseModel):
    fields: list[RequirementTemplateField]
    sample_rows: list[dict[str, str]]


class RequirementBatchItem(BaseModel):
    row_number: int
    description: str
    missing_fields: list[str]
    analysis: RequirementAnalysisRead | None


class RequirementBatchUploadResponse(BaseModel):
    filename: str
    items: list[RequirementBatchItem]


class RequirementAnalysisRead(BaseModel):
    id: str
    project_id: str
    description: str
    parse_result: RequirementParseResult
    recommendations: list[RequirementRecommendation]
    status: str
    created_at: datetime
