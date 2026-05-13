from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.requirements.schemas import (
    RequirementAnalysisRead,
    RequirementParseResult,
    RequirementRecommendation,
)
from app.modules.risks.service import list_risks
from app.modules.test_packages.service import list_packages

ANALYSES: dict[str, RequirementAnalysisRead] = {}

STANDARD_REQUIREMENT_SECTIONS = {
    "需求标题",
    "产品型号",
    "变更对象",
    "所属子系统",
    "变更类型",
    "变更背景",
    "变更内容",
    "影响范围",
    "验收标准",
    "已知风险",
}


class RequirementAnalysisRecord(Base):
    __tablename__ = "requirement_analyses"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str] = mapped_column(Text)
    parse_result: Mapped[dict] = mapped_column(JSON)
    recommendations: Mapped[list[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


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
    _save_analysis(analysis)
    return analysis


def extract_requirement_description(filename: str, content: bytes) -> str:
    text = decode_requirement_content(content)
    normalized = normalize_requirement_text(text)
    if normalized:
        return normalized
    return f"需求标题：{filename}\n产品型号：待确认\n变更对象：待确认\n所属子系统：待确认\n变更类型：待确认\n变更背景：待补充\n变更内容：待补充\n影响范围：待补充\n验收标准：待补充\n已知风险：待补充"


def decode_requirement_content(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""


def normalize_requirement_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    lines = [line for line in lines if line]
    if not lines:
        return ""
    structured_lines = [line for line in lines if "：" in line or ":" in line]
    matched_sections = {line.split("：", 1)[0].split(":", 1)[0].strip() for line in structured_lines}
    if STANDARD_REQUIREMENT_SECTIONS.intersection(matched_sections):
        return "\n".join(lines)
    return "\n".join(["需求标题：待确认", *lines])


def get_analysis(analysis_id: str) -> RequirementAnalysisRead | None:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.get(RequirementAnalysisRecord, analysis_id)
            return _record_to_analysis(record) if record is not None else None
    return ANALYSES.get(analysis_id)


def parse_requirement(description: str) -> RequirementParseResult:
    lowered = description.lower()
    product_model = "DNBSEQ-G99" if "g99" in lowered or "dnbseq-g99" in lowered else None
    test_object = "RFID" if "rfid" in lowered else "待确认对象"
    change_type = parse_change_type(description)
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


def parse_change_type(description: str) -> str:
    for line in description.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        normalized = line.strip()
        if normalized.startswith("变更类型：") or normalized.startswith("变更类型:"):
            value = normalized.split("：", 1)[-1] if "：" in normalized else normalized.split(":", 1)[-1]
            return value.strip() or "待确认变更类型"
    if "供应商" in description or "二供" in description:
        return "供应商变更"
    return "待确认变更类型"


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


def _use_sqlalchemy() -> bool:
    return get_settings().repository_backend == "sqlalchemy"


def _save_analysis(analysis: RequirementAnalysisRead) -> None:
    if _use_sqlalchemy():
        with session_scope() as session:
            session.merge(
                RequirementAnalysisRecord(
                    id=analysis.id,
                    project_id=analysis.project_id,
                    description=analysis.description,
                    parse_result=analysis.parse_result.model_dump(),
                    recommendations=[recommendation.model_dump() for recommendation in analysis.recommendations],
                    status=analysis.status,
                    created_at=analysis.created_at,
                )
            )
        return
    ANALYSES[analysis.id] = analysis


def _record_to_analysis(record: RequirementAnalysisRecord) -> RequirementAnalysisRead:
    return RequirementAnalysisRead(
        id=record.id,
        project_id=record.project_id,
        description=record.description,
        parse_result=RequirementParseResult(**record.parse_result),
        recommendations=[RequirementRecommendation(**recommendation) for recommendation in (record.recommendations or [])],
        status=record.status,
        created_at=record.created_at,
    )
