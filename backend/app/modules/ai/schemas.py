from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AiValidationRequest(BaseModel):
    task_type: str
    output: dict[str, Any]


class AiValidationResponse(BaseModel):
    valid: bool
    errors: list[str]


class AiRunRecord(BaseModel):
    id: str
    task_type: str
    model_name: str
    prompt_version: str
    output: dict[str, Any]
    valid: bool
    errors: list[str]
    created_at: datetime
