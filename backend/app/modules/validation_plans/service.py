from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.ai.service import run_json_task
from app.modules.requirements.service import get_analysis, list_analyses
from app.modules.validation_plans.docx_exporter import render_validation_plan_docx
from app.modules.validation_plans.schemas import (
    ExportRecord,
    ValidationPlanBulkDeleteResponse,
    ValidationPlanCheckResult,
    ValidationPlanItem,
    ValidationPlanRead,
)

PLANS: dict[str, ValidationPlanRead] = {}
EXPORTS: dict[str, ExportRecord] = {}
VALIDATION_PLAN_STATUSES = {"draft", "reviewing", "approved", "exported", "archived"}


class ValidationPlanRecord(Base):
    __tablename__ = "validation_plans"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(120), index=True)
    requirement_analysis_ids: Mapped[list[str]] = mapped_column(JSON)
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


def create_plan(requirement_analysis_id: str | None = None, project_id: str | None = None) -> ValidationPlanRead | None:
    if project_id is not None:
        return create_plan_from_project(project_id)
    if requirement_analysis_id is not None:
        return create_plan_from_single_analysis(requirement_analysis_id)
    return None


def create_plan_from_single_analysis(requirement_analysis_id: str) -> ValidationPlanRead | None:
    analysis = get_analysis(requirement_analysis_id)
    if analysis is None:
        return None
    return _build_plan(analysis.project_id, [analysis])


def create_plan_from_project(project_id: str) -> ValidationPlanRead | None:
    analyses = list_analyses(project_id)
    if not analyses:
        return None
    return _build_plan(project_id, analyses)


def _build_plan(project_id: str, analyses: list) -> ValidationPlanRead:
    analysis_ids = [analysis.id for analysis in analyses]
    product_models = {analysis.parse_result.product_model for analysis in analyses if analysis.parse_result.product_model}
    test_objects = {analysis.parse_result.test_object for analysis in analyses if analysis.parse_result.test_object != "待确认对象"}
    change_types = {analysis.parse_result.change_type for analysis in analyses if analysis.parse_result.change_type != "待确认变更类型"}
    title_parts = []
    if product_models:
        title_parts.append("/".join(sorted(product_models)))
    if test_objects:
        title_parts.append("/".join(sorted(test_objects)))
    if change_types:
        title_parts.append("/".join(sorted(change_types)))
    title = " ".join(title_parts) + "验证方案" if title_parts else "综合验证方案"
    all_items: list[ValidationPlanItem] = []
    seen_titles: set[str] = set()
    for analysis in analyses:
        recommendations = select_plan_recommendations(analysis.recommendations)
        for recommendation in recommendations:
            if recommendation.title in seen_titles:
                continue
            seen_titles.add(recommendation.title)
            all_items.append(
                ValidationPlanItem(
                    sequence=len(all_items) + 1,
                    title=recommendation.title,
                    group=recommendation.group,
                    objective=recommendation.objective or f"验证{recommendation.title}满足需求。",
                    method=recommendation.method or "按既有验证方案模板执行测试步骤并记录结果。",
                    record_template=recommendation.record_template or "记录样本编号、测试条件、实际结果、判定结论和关联 BUG。",
                    evidence=recommendation.evidence,
                )
            )
    overview_prefix = f"针对 {len(analyses)} 条需求分析" if len(analyses) > 1 else f"针对需求：{analyses[0].description}"
    plan = ValidationPlanRead(
        id=f"plan-{uuid4()}",
        project_id=project_id,
        requirement_analysis_ids=analysis_ids,
        title=title,
        template_version="validation-plan-v1",
        overview=f"{overview_prefix}，生成验证方案草稿。",
        dut_description=f"DUT：{'/'.join(sorted(product_models)) if product_models else '待确认'}，测试对象：{'/'.join(sorted(test_objects)) if test_objects else '待确认'}。",
        reference_documents=["测试规范", "历史验证方案", "Jira/DFMEA 风险项"],
        items=all_items,
        status="draft",
        created_at=datetime.now(UTC),
    )
    _save_plan(plan)
    return plan


def select_plan_recommendations(recommendations: list) -> list:
    return [item for item in recommendations if item.review_status == "confirmed"]


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


def update_plan_status(plan_id: str, status: str) -> ValidationPlanRead | None:
    if status not in VALIDATION_PLAN_STATUSES:
        raise ValueError(f"Unsupported validation plan status: {status}")
    plan = get_plan(plan_id)
    if plan is None:
        return None
    updated = plan.model_copy(update={"status": status})
    _save_plan(updated)
    return updated


def delete_plan(plan_id: str) -> bool:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.get(ValidationPlanRecord, plan_id)
            if record is None:
                return False
            session.delete(record)
            return True
    return PLANS.pop(plan_id, None) is not None


def bulk_delete_plans(plan_ids: list[str]) -> ValidationPlanBulkDeleteResponse:
    deleted_ids: list[str] = []
    skipped: list[dict[str, str]] = []
    seen: set[str] = set()
    for plan_id in plan_ids:
        if plan_id in seen:
            continue
        seen.add(plan_id)
        if delete_plan(plan_id):
            deleted_ids.append(plan_id)
        else:
            skipped.append({"plan_id": plan_id, "reason": "方案不存在"})
    return ValidationPlanBulkDeleteResponse(deleted_ids=deleted_ids, skipped=skipped)


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
    local_result = ValidationPlanCheckResult(blocking=blocking, warnings=warnings, suggestions=suggestions)
    return check_plan_with_ai(plan, local_result) or local_result


def check_plan_with_ai(plan: ValidationPlanRead, local_result: ValidationPlanCheckResult) -> ValidationPlanCheckResult | None:
    output = run_json_task(
        "validation_plan_check",
        "你是基因测序仪验证方案完整性检查助手。只输出 JSON，不输出解释。",
        (
            "基于验证方案 JSON 和本地检查结果补充 blocking、warnings、suggestions 三个数组。"
            "blocking 仅用于会导致方案不可执行的问题，warnings 用于需人工确认的问题，suggestions 用于优化建议。"
            f"\n本地检查：{local_result.model_dump()}"
            f"\n验证方案：{plan.model_dump()}"
        ),
    )
    if output is None:
        return None
    try:
        return ValidationPlanCheckResult(
            blocking=merge_messages(local_result.blocking, output.get("blocking", [])),
            warnings=merge_messages(local_result.warnings, output.get("warnings", [])),
            suggestions=merge_messages(local_result.suggestions, output.get("suggestions", [])),
        )
    except (TypeError, ValueError):
        return None


def merge_messages(local_messages: list[str], ai_messages: object) -> list[str]:
    merged = list(local_messages)
    if not isinstance(ai_messages, list):
        return merged
    for message in ai_messages:
        if isinstance(message, str) and message and message not in merged:
            merged.append(message)
    return merged


def export_plan(plan_id: str, export_directory: str = "") -> ExportRecord | None:
    plan = get_plan(plan_id)
    if plan is None:
        return None
    export_id = f"export-{uuid4()}"
    settings = get_settings()
    filename = f"{plan.title}.docx"
    output_root = Path(export_directory.strip()) if export_directory.strip() else Path(settings.local_storage_root) / "exports"
    output_path = output_root / export_id / filename
    render_validation_plan_docx(plan, Path(settings.validation_plan_template_path), output_path)
    update_plan_status(plan_id, "exported")
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
        requirement_analysis_ids=plan.requirement_analysis_ids,
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
        requirement_analysis_ids=record.requirement_analysis_ids or [],
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
