from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.ai.schemas import AiRunRecord

AI_RUNS: dict[str, AiRunRecord] = {}


class AiRunRecordModel(Base):
    __tablename__ = "ai_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(120), index=True)
    model_name: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(80))
    output: Mapped[dict[str, Any]] = mapped_column(JSON)
    valid: Mapped[bool] = mapped_column(Boolean, index=True)
    errors: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

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
    _save_ai_run(record)
    return record


def get_ai_run(record_id: str) -> AiRunRecord | None:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.get(AiRunRecordModel, record_id)
            return _model_to_record(record) if record is not None else None
    return AI_RUNS.get(record_id)


def _use_sqlalchemy() -> bool:
    return get_settings().repository_backend == "sqlalchemy"


def _save_ai_run(record: AiRunRecord) -> None:
    if _use_sqlalchemy():
        with session_scope() as session:
            session.merge(
                AiRunRecordModel(
                    id=record.id,
                    task_type=record.task_type,
                    model_name=record.model_name,
                    prompt_version=record.prompt_version,
                    output=record.output,
                    valid=record.valid,
                    errors=record.errors,
                    created_at=record.created_at,
                )
            )
        return
    AI_RUNS[record.id] = record


def _model_to_record(model: AiRunRecordModel) -> AiRunRecord:
    return AiRunRecord(
        id=model.id,
        task_type=model.task_type,
        model_name=model.model_name,
        prompt_version=model.prompt_version,
        output=model.output or {},
        valid=model.valid,
        errors=model.errors or [],
        created_at=model.created_at,
    )
