from datetime import datetime

from pydantic import BaseModel


class RiskItem(BaseModel):
    id: str
    project_id: str
    source_type: str
    source_id: str
    title: str
    description: str
    product_model: str | None
    test_object: str
    subsystem: str
    severity: str | None
    rpn: int | None
    failure_mode: str | None
    failure_effect: str | None
    root_cause: str | None
    control_measure: str | None
    suggested_test: str
    status: str
    created_at: datetime


class RiskParseRequest(BaseModel):
    project_id: str
    source_type: str
    content: str


class RiskParseResponse(BaseModel):
    items: list[RiskItem]
