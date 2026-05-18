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


class RiskUpdate(BaseModel):
    source_type: str | None = None
    source_id: str | None = None
    title: str | None = None
    description: str | None = None
    product_model: str | None = None
    test_object: str | None = None
    subsystem: str | None = None
    severity: str | None = None
    rpn: int | None = None
    failure_mode: str | None = None
    failure_effect: str | None = None
    root_cause: str | None = None
    control_measure: str | None = None
    suggested_test: str | None = None
    status: str | None = None


class RiskBulkPublishRequest(BaseModel):
    risk_ids: list[str]


class RiskBulkPublishResponse(BaseModel):
    published_ids: list[str]
    skipped: list[dict[str, str]]


class RiskBulkDeleteRequest(BaseModel):
    risk_ids: list[str]


class RiskBulkDeleteResponse(BaseModel):
    deleted_ids: list[str]
    skipped: list[dict[str, str]]


class RiskParseRequest(BaseModel):
    project_id: str
    source_type: str
    content: str


class RiskParseResponse(BaseModel):
    items: list[RiskItem]
