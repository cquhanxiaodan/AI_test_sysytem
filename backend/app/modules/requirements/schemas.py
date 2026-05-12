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


class RequirementAnalysisRead(BaseModel):
    id: str
    project_id: str
    description: str
    parse_result: RequirementParseResult
    recommendations: list[RequirementRecommendation]
    status: str
    created_at: datetime
