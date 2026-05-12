from datetime import UTC, datetime
from uuid import uuid4

from app.modules.requirements.service import get_analysis
from app.modules.validation_plans.schemas import (
    ExportRecord,
    ValidationPlanCheckResult,
    ValidationPlanItem,
    ValidationPlanRead,
)

PLANS: dict[str, ValidationPlanRead] = {}
EXPORTS: dict[str, ExportRecord] = {}


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
    PLANS[plan.id] = plan
    return plan


def get_plan(plan_id: str) -> ValidationPlanRead | None:
    return PLANS.get(plan_id)


def list_plans(project_id: str | None = None) -> list[ValidationPlanRead]:
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
    record = ExportRecord(
        id=f"export-{uuid4()}",
        validation_plan_id=plan_id,
        filename=f"{plan.title}.docx",
        template_version=plan.template_version,
        status="generated",
        created_at=datetime.now(UTC),
    )
    EXPORTS[record.id] = record
    return record
