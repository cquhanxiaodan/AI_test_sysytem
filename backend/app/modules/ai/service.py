from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.modules.ai.schemas import AiRunRecord

AI_RUNS: dict[str, AiRunRecord] = {}

REQUIRED_FIELDS = {
    "document_label_extraction": ["labels", "confidence", "evidence"],
    "requirement_recommendation": ["required", "suggested", "conditional", "evidence"],
    "validation_plan_check": ["blocking", "warnings", "suggestions"],
}


def validate_output(task_type: str, output: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS.get(task_type, []):
        if field not in output:
            errors.append(f"缺少字段: {field}")
    confidence = output.get("confidence")
    if confidence is not None and (not isinstance(confidence, int | float) or confidence < 0 or confidence > 1):
        errors.append("confidence 必须在 0 到 1 之间")
    return len(errors) == 0, errors


def record_ai_run(task_type: str, output: dict[str, Any]) -> AiRunRecord:
    valid, errors = validate_output(task_type, output)
    record = AiRunRecord(
        id=f"ai-run-{uuid4()}",
        task_type=task_type,
        model_name="local-mock",
        prompt_version="v1",
        output=output,
        valid=valid,
        errors=errors,
        created_at=datetime.now(UTC),
    )
    AI_RUNS[record.id] = record
    return record
