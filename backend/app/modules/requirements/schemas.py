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
    group: str
    title: str
    source_type: str
    source_id: str
    reason: str
    evidence: str


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
