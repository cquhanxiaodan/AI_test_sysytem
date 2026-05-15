from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AiValidationRequest(BaseModel):
    task_type: str
    output: dict[str, Any]


class AiValidationResponse(BaseModel):
    valid: bool
    errors: list[str]


class AiConfigRead(BaseModel):
    provider: str
    base_url: str
    model: str
    timeout_seconds: int
    configured: bool
    external_reference_enabled: bool
    api_key_configured: bool
    api_key_masked: str | None


class AiConfigUpdate(BaseModel):
    provider: str
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout_seconds: int = 20


class AiRunRecord(BaseModel):
    id: str
    task_type: str
    model_name: str
    prompt_version: str
    output: dict[str, Any]
    valid: bool
    errors: list[str]
    created_at: datetime


class AiTaskResult(BaseModel):
    output: dict[str, Any] | None
    status: str
    message: str
