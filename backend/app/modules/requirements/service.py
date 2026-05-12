from datetime import UTC, datetime
from uuid import uuid4

from app.modules.requirements.schemas import (
    RequirementAnalysisRead,
    RequirementParseResult,
    RequirementRecommendation,
)
from app.modules.risks.service import list_risks
from app.modules.test_packages.service import list_packages

ANALYSES: dict[str, RequirementAnalysisRead] = {}


def create_analysis(project_id: str, description: str) -> RequirementAnalysisRead:
    parse_result = parse_requirement(description)
    recommendations = build_recommendations(project_id, parse_result)
    analysis = RequirementAnalysisRead(
        id=f"analysis-{uuid4()}",
        project_id=project_id,
        description=description,
        parse_result=parse_result,
        recommendations=recommendations,
        status="ready_for_review",
        created_at=datetime.now(UTC),
    )
    ANALYSES[analysis.id] = analysis
    return analysis


def get_analysis(analysis_id: str) -> RequirementAnalysisRead | None:
    return ANALYSES.get(analysis_id)


def parse_requirement(description: str) -> RequirementParseResult:
    lowered = description.lower()
    product_model = "DNBSEQ-G99" if "g99" in lowered or "dnbseq-g99" in lowered else None
    test_object = "RFID" if "rfid" in lowered else "待确认对象"
    change_type = "供应商变更" if "供应商" in description or "二供" in description else "待确认变更类型"
    subsystem = "RFID" if test_object == "RFID" else "待确认子系统"
    missing_fields = []
    if product_model is None:
        missing_fields.append("product_model")
    if change_type == "待确认变更类型":
        missing_fields.append("change_type")
    return RequirementParseResult(
        test_object=test_object,
        change_type=change_type,
        product_model=product_model,
        subsystem=subsystem,
        missing_fields=missing_fields,
    )


def build_recommendations(project_id: str, parse_result: RequirementParseResult) -> list[RequirementRecommendation]:
    recommendations: list[RequirementRecommendation] = []
    for package in list_packages(project_id):
        if package.test_object != parse_result.test_object or package.change_type != parse_result.change_type:
            continue
        for item in package.items:
            group = {
                "required": "必测",
                "suggested": "建议",
                "conditional": "条件触发",
            }.get(item.relation_type, "建议")
            recommendations.append(
                RequirementRecommendation(
                    group=group,
                    title=item.title,
                    source_type="test_package",
                    source_id=package.id,
                    reason=f"匹配归口包：{package.name}",
                    evidence=package.evidence,
                )
            )

    for risk in list_risks(project_id=project_id, subsystem=parse_result.subsystem):
        recommendations.append(
            RequirementRecommendation(
                group="风险补充",
                title=risk.suggested_test,
                source_type=risk.source_type,
                source_id=risk.id,
                reason=f"风险项：{risk.title}",
                evidence=risk.description,
            )
        )

    return recommendations
