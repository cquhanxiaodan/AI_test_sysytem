from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.requirements.service import get_analysis
from app.modules.validation_plans.docx_exporter import render_validation_plan_docx
from app.modules.validation_plans.schemas import (
    ExportRecord,
    ValidationPlanCheckResult,
    ValidationPlanItem,
    ValidationPlanRead,
)

PLANS: dict[str, ValidationPlanRead] = {}
EXPORTS: dict[str, ExportRecord] = {}


class ValidationPlanRecord(Base):
    __tablename__ = "validation_plans"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(120), index=True)
    requirement_analysis_id: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(500))
    template_version: Mapped[str] = mapped_column(String(80))
    overview: Mapped[str] = mapped_column(String(2000))
    dut_description: Mapped[str] = mapped_column(String(2000))
    reference_documents: Mapped[list[str]] = mapped_column(JSON)
    items: Mapped[list[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExportRecordModel(Base):
    __tablename__ = "validation_plan_exports"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    validation_plan_id: Mapped[str] = mapped_column(String(120), index=True)
    filename: Mapped[str] = mapped_column(String(500))
    template_version: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(80), index=True)
    storage_path: Mapped[str] = mapped_column(String(1000))
    download_url: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def create_plan(requirement_analysis_id: str) -> ValidationPlanRead | None:
    analysis = get_analysis(requirement_analysis_id)
    if analysis is None:
        return None
    title = f"{analysis.parse_result.product_model or '待确认型号'} {analysis.parse_result.test_object} {analysis.parse_result.change_type}验证方案"
    plan = ValidationPlanRead(
        id=f"plan-{uuid4()}",
        project_id=analysis.project_id,
        requirement_analysis_id=analysis.id,
        title=title,
        template_version="validation-plan-v1",
        overview=f"针对需求：{analysis.description}，生成验证方案草稿。",
        dut_description=f"DUT：{analysis.parse_result.product_model or '待确认'}，测试对象：{analysis.parse_result.test_object}。",
        reference_documents=["测试规范", "历史验证方案", "Jira/DFMEA 风险项"],
        items=[
            ValidationPlanItem(
                sequence=index + 1,
                title=recommendation.title,
                group=recommendation.group,
                objective=f"验证{recommendation.title}满足需求。",
                method="按既有验证方案模板执行测试步骤并记录结果。",
                record_template="记录样本编号、测试条件、实际结果、判定结论和关联 BUG。",
                evidence=recommendation.evidence,
            )
            for index, recommendation in enumerate(analysis.recommendations)
        ],
        status="draft",
        created_at=datetime.now(UTC),
    )
    _save_plan(plan)
    return plan


def get_plan(plan_id: str) -> ValidationPlanRead | None:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.get(ValidationPlanRecord, plan_id)
            return _plan_record_to_read(record) if record is not None else None
    return PLANS.get(plan_id)


def list_plans(project_id: str | None = None) -> list[ValidationPlanRead]:
    if _use_sqlalchemy():
        with session_scope() as session:
            statement = select(ValidationPlanRecord)
            if project_id is not None:
                statement = statement.where(ValidationPlanRecord.project_id == project_id)
            records = session.scalars(statement).all()
            plans = [_plan_record_to_read(record) for record in records]
            return sorted(plans, key=lambda plan: plan.created_at, reverse=True)
    plans = list(PLANS.values())
    if project_id is not None:
        plans = [plan for plan in plans if plan.project_id == project_id]
    return sorted(plans, key=lambda plan: plan.created_at, reverse=True)


def check_plan(plan_id: str) -> ValidationPlanCheckResult | None:
    plan = get_plan(plan_id)
    if plan is None:
        return None
    blocking = []
    warnings = []
    suggestions = []
    if not plan.items:
        blocking.append("验证方案至少需要一个测试项目。")
    if "待确认" in plan.dut_description:
        warnings.append("DUT 信息存在待确认字段。")
    if len(plan.reference_documents) < 2:
        suggestions.append("建议补充参考文档。")
    return ValidationPlanCheckResult(blocking=blocking, warnings=warnings, suggestions=suggestions)


def export_plan(plan_id: str) -> ExportRecord | None:
    plan = get_plan(plan_id)
    if plan is None:
        return None
    export_id = f"export-{uuid4()}"
    settings = get_settings()
    filename = f"{plan.title}.docx"
    output_path = Path(settings.local_storage_root) / "exports" / export_id / filename
    render_validation_plan_docx(plan, Path(settings.validation_plan_template_path), output_path)
    record = ExportRecord(
        id=export_id,
        validation_plan_id=plan_id,
        filename=filename,
        template_version=plan.template_version,
        status="generated",
        storage_path=str(output_path),
        download_url=f"/api/validation-plans/exports/{export_id}/download",
        created_at=datetime.now(UTC),
    )
    _save_export(record)
    return record


def get_export(export_id: str) -> ExportRecord | None:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.get(ExportRecordModel, export_id)
            return _export_record_to_read(record) if record is not None else None
    return EXPORTS.get(export_id)


def _use_sqlalchemy() -> bool:
    return get_settings().repository_backend == "sqlalchemy"


def _save_plan(plan: ValidationPlanRead) -> None:
    if _use_sqlalchemy():
        with session_scope() as session:
            session.merge(_plan_read_to_record(plan))
        return
    PLANS[plan.id] = plan


def _save_export(record: ExportRecord) -> None:
    if _use_sqlalchemy():
        with session_scope() as session:
            session.merge(_export_read_to_record(record))
        return
    EXPORTS[record.id] = record


def _plan_read_to_record(plan: ValidationPlanRead) -> ValidationPlanRecord:
    return ValidationPlanRecord(
        id=plan.id,
        project_id=plan.project_id,
        requirement_analysis_id=plan.requirement_analysis_id,
        title=plan.title,
        template_version=plan.template_version,
        overview=plan.overview,
        dut_description=plan.dut_description,
        reference_documents=plan.reference_documents,
        items=[item.model_dump() for item in plan.items],
        status=plan.status,
        created_at=plan.created_at,
    )


def _plan_record_to_read(record: ValidationPlanRecord) -> ValidationPlanRead:
    return ValidationPlanRead(
        id=record.id,
        project_id=record.project_id,
        requirement_analysis_id=record.requirement_analysis_id,
        title=record.title,
        template_version=record.template_version,
        overview=record.overview,
        dut_description=record.dut_description,
        reference_documents=record.reference_documents or [],
        items=[ValidationPlanItem(**item) for item in (record.items or [])],
        status=record.status,
        created_at=record.created_at,
    )


def _export_read_to_record(record: ExportRecord) -> ExportRecordModel:
    return ExportRecordModel(
        id=record.id,
        validation_plan_id=record.validation_plan_id,
        filename=record.filename,
        template_version=record.template_version,
        status=record.status,
        storage_path=record.storage_path,
        download_url=record.download_url,
        created_at=record.created_at,
    )


def _export_record_to_read(record: ExportRecordModel) -> ExportRecord:
    return ExportRecord(
        id=record.id,
        validation_plan_id=record.validation_plan_id,
        filename=record.filename,
        template_version=record.template_version,
        status=record.status,
        storage_path=record.storage_path,
        download_url=record.download_url,
        created_at=record.created_at,
    )
