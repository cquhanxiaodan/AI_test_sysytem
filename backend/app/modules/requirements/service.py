from datetime import UTC, datetime
import csv
import io
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.ai.service import run_json_task
from app.modules.requirements.schemas import (
    RequirementAnalysisRead,
    RequirementParseResult,
    RequirementRecommendation,
)
from app.modules.risks.service import list_risks
from app.modules.test_packages.service import list_packages

ANALYSES: dict[str, RequirementAnalysisRead] = {}

REQUIRED_REQUIREMENT_FIELDS = ["需求标题", "产品型号", "变更对象", "变更背景", "变更内容"]
OPTIONAL_REQUIREMENT_FIELDS = ["所属子系统", "变更类型", "影响范围", "验收标准", "已知风险"]
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


def get_requirement_template_fields() -> list[dict[str, str | bool]]:
    descriptions = {
        "需求标题": "用于区分每条需求的短标题",
        "产品型号": "适用产品型号，例如 DNBSEQ-G99",
        "变更对象": "本次变更涉及的对象，例如 RFID",
        "所属子系统": "可选，对象所属子系统，例如 RFID；系统可根据变更对象推断",
        "变更类型": "可选，供应商变更、设计变更、工艺变更等；系统可根据背景和内容推断",
        "变更背景": "说明为什么需要这次变更",
        "变更内容": "说明具体变化点",
        "影响范围": "可选，说明可能影响的测试范围",
        "验收标准": "可选，说明通过标准",
        "已知风险": "可选，说明已知问题或风险点",
    }
    return [
        {"name": field, "required": field in REQUIRED_REQUIREMENT_FIELDS, "description": descriptions[field]}
        for field in [*REQUIRED_REQUIREMENT_FIELDS, *OPTIONAL_REQUIREMENT_FIELDS]
    ]


def get_requirement_template_sample_rows() -> list[dict[str, str]]:
    return [
        {
            "需求标题": "DNBSEQ-G99 RFID 二供供应商导入验证",
            "产品型号": "DNBSEQ-G99",
            "变更对象": "RFID",
            "所属子系统": "RFID",
            "变更类型": "供应商变更",
            "变更背景": "现有 RFID 物料需引入二供供应商以降低供应风险",
            "变更内容": "同步引入康奈特 RFID，保持功能规格和接口定义一致",
            "影响范围": "在机装配、初始化、读取、写入、整机兼容性、安规 EMC 风险评估",
            "验收标准": "RFID 可稳定完成在机装配、初始化、读取和写入，测试结果满足既有验证方案要求",
            "已知风险": "二供物料可能存在读取失败、初始化异常、装配兼容性或 EMC 差异",
        }
    ]


def build_requirement_template_csv() -> bytes:
    output = io.StringIO()
    fields = [*REQUIRED_REQUIREMENT_FIELDS, *OPTIONAL_REQUIREMENT_FIELDS]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(get_requirement_template_sample_rows())
    return output.getvalue().encode("utf-8-sig")


def parse_requirement_table(content: bytes) -> list[tuple[int, str, list[str]]]:
    text = decode_requirement_content(content)
    reader = csv.DictReader(io.StringIO(text))
    items: list[tuple[int, str, list[str]]] = []
    for index, row in enumerate(reader, start=2):
        normalized = {normalize_field_name(key): (value or "").strip() for key, value in row.items() if key is not None}
        if not any(normalized.values()):
            continue
        missing_fields = [field for field in REQUIRED_REQUIREMENT_FIELDS if not normalized.get(field)]
        description = build_requirement_description(normalized)
        items.append((index, description, missing_fields))
    return items


def normalize_field_name(field: str) -> str:
    return field.replace("\ufeff", "").strip()


def build_requirement_description(row: dict[str, str]) -> str:
    fields = [*REQUIRED_REQUIREMENT_FIELDS, *OPTIONAL_REQUIREMENT_FIELDS]
    return "\n".join(f"{field}：{row.get(field, '').strip()}" for field in fields if row.get(field, "").strip())


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
    ai_result = parse_requirement_with_ai(description)
    if ai_result is not None:
        return ai_result
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


def parse_requirement_with_ai(description: str) -> RequirementParseResult | None:
    output = run_json_task(
        "requirement_parse",
        "你是基因测序仪测试需求分析助手。只输出 JSON，不输出解释。",
        (
            "从需求文本中抽取 test_object、change_type、product_model、subsystem、missing_fields。"
            "字段含义：test_object 为变更对象，change_type 为变更类型，product_model 为产品型号，subsystem 为所属子系统。"
            "缺失字段只允许使用 product_model、test_object、change_type、subsystem。"
            "无法确定时使用待确认对象、待确认变更类型、待确认子系统，product_model 使用 null。"
            f"\n需求文本：\n{description}"
        ),
    )
    if output is None:
        return None
    try:
        return RequirementParseResult(
            test_object=str(output.get("test_object") or "待确认对象"),
            change_type=str(output.get("change_type") or "待确认变更类型"),
            product_model=output.get("product_model") if output.get("product_model") else None,
            subsystem=str(output.get("subsystem") or "待确认子系统"),
            missing_fields=[str(field) for field in output.get("missing_fields", []) if isinstance(field, str)],
        )
    except (TypeError, ValueError):
        return None


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
