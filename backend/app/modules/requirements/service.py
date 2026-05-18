from datetime import UTC, datetime
import csv
import io
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, Text, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.ai.service import run_json_task, run_json_task_detailed
from app.modules.knowledge.service import search_project_knowledge
from app.modules.requirements.schemas import (
    RequirementAnalysisRead,
    RequirementParseResult,
    RequirementRecommendationCreate,
    RequirementRecommendation,
    RequirementRecommendationUpdate,
)
from app.modules.risks.service import list_risks
from app.modules.test_items.service import create_item_from_fields
from app.modules.test_packages.service import list_packages

ANALYSES: dict[str, RequirementAnalysisRead] = {}
ALLOWED_RECOMMENDATION_STATUSES = {"pending", "confirmed", "excluded"}

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
    ai_status: Mapped[str] = mapped_column(String(80), default="not_configured")
    ai_message: Mapped[str] = mapped_column(String(1000), default="AI 未配置，已使用本地规则推荐。")
    status: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def create_analysis(project_id: str, description: str) -> RequirementAnalysisRead:
    analysis = create_local_analysis(project_id, description)
    return run_ai_recommendation(analysis.id) or analysis


def create_local_analysis(project_id: str, description: str) -> RequirementAnalysisRead:
    parse_result = parse_requirement_locally(description)
    recommendations = build_local_recommendations(project_id, parse_result)
    analysis = RequirementAnalysisRead(
        id=f"analysis-{uuid4()}",
        project_id=project_id,
        description=description,
        parse_result=parse_result,
        recommendations=recommendations,
        ai_status="pending",
        ai_message="本地分析完成，等待 AI 补充分析。",
        status="ready_for_review",
        created_at=datetime.now(UTC),
    )
    _save_analysis(analysis)
    return analysis


def run_ai_recommendation(analysis_id: str) -> RequirementAnalysisRead | None:
    analysis = get_analysis(analysis_id)
    if analysis is None:
        return None
    recommendations, ai_status, ai_message = enrich_recommendations_with_ai(
        analysis.project_id,
        analysis.parse_result,
        analysis.recommendations,
    )
    analysis.recommendations = recommendations
    analysis.ai_status = ai_status
    analysis.ai_message = ai_message
    analysis.status = "ready_for_review"
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


def get_latest_analysis(project_id: str) -> RequirementAnalysisRead | None:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.scalars(
                select(RequirementAnalysisRecord)
                .where(RequirementAnalysisRecord.project_id == project_id)
                .order_by(RequirementAnalysisRecord.created_at.desc())
                .limit(1)
            ).first()
            return _record_to_analysis(record) if record is not None else None
    analyses = [analysis for analysis in ANALYSES.values() if analysis.project_id == project_id]
    if not analyses:
        return None
    return max(analyses, key=lambda analysis: analysis.created_at)


def add_recommendation(analysis_id: str, payload: RequirementRecommendationCreate) -> RequirementAnalysisRead | None:
    analysis = get_analysis(analysis_id)
    if analysis is None:
        return None
    recommendation = RequirementRecommendation(id=f"rec-{uuid4()}", **payload.model_dump())
    if recommendation.review_status not in ALLOWED_RECOMMENDATION_STATUSES:
        recommendation.review_status = "confirmed"
    analysis.recommendations.append(recommendation)
    analysis.status = "ready_for_review"
    _save_analysis(analysis)
    return analysis


def update_recommendation(
    analysis_id: str,
    recommendation_id: str,
    payload: RequirementRecommendationUpdate,
) -> RequirementAnalysisRead | None:
    analysis = get_analysis(analysis_id)
    if analysis is None:
        return None
    for index, recommendation in enumerate(analysis.recommendations):
        if recommendation.id != recommendation_id:
            continue
        updates = payload.model_dump(exclude_unset=True)
        if "review_status" in updates and updates["review_status"] not in ALLOWED_RECOMMENDATION_STATUSES:
            raise ValueError("Invalid recommendation review_status")
        updated = recommendation.model_copy(update=updates)
        analysis.recommendations[index] = updated
        analysis.status = "ready_for_review"
        _save_analysis(analysis)
        return analysis
    return None


def delete_recommendation(analysis_id: str, recommendation_id: str) -> RequirementAnalysisRead | None:
    analysis = get_analysis(analysis_id)
    if analysis is None:
        return None
    original_count = len(analysis.recommendations)
    analysis.recommendations = [item for item in analysis.recommendations if item.id != recommendation_id]
    if len(analysis.recommendations) == original_count:
        return None
    analysis.status = "ready_for_review"
    _save_analysis(analysis)
    return analysis


def delete_analysis(analysis_id: str) -> bool:
    if _use_sqlalchemy():
        with session_scope() as session:
            result = session.execute(delete(RequirementAnalysisRecord).where(RequirementAnalysisRecord.id == analysis_id))
            return (result.rowcount or 0) > 0
    return ANALYSES.pop(analysis_id, None) is not None


def include_recommendation_in_local_items(analysis_id: str, recommendation_id: str) -> RequirementAnalysisRead | None:
    analysis = get_analysis(analysis_id)
    if analysis is None:
        return None
    for index, recommendation in enumerate(analysis.recommendations):
        if recommendation.id != recommendation_id:
            continue
        local_item = create_item_from_fields(
            project_id=analysis.project_id,
            title=recommendation.title,
            test_object=analysis.parse_result.test_object,
            subsystem=analysis.parse_result.subsystem,
            objective=recommendation.objective or f"验证{recommendation.title}满足变更需求。",
            method=recommendation.method or "按既有验证方案模板执行测试步骤并记录结果。",
            record_template=recommendation.record_template or "记录样本编号、测试条件、实际结果、判定结论和关联 BUG。",
            evidence=f"需求分析纳入本地：{recommendation.evidence}",
            source_type="ai_generated",
            status="draft",
        )
        analysis.recommendations[index] = recommendation.model_copy(
            update={
                "source_type": "test_item",
                "source_id": local_item.id,
                "reason": f"已纳入本地测试条目资产草稿：{local_item.title}",
                "review_status": "pending",
            }
        )
        _save_analysis(analysis)
        return analysis
    return None


def list_analyses(project_id: str) -> list[RequirementAnalysisRead]:
    if _use_sqlalchemy():
        with session_scope() as session:
            statement = select(RequirementAnalysisRecord).where(RequirementAnalysisRecord.project_id == project_id)
            records = session.scalars(statement).all()
            analyses = [_record_to_analysis(record) for record in records]
            return sorted(analyses, key=lambda analysis: analysis.created_at, reverse=True)
    analyses = [analysis for analysis in ANALYSES.values() if analysis.project_id == project_id]
    return sorted(analyses, key=lambda analysis: analysis.created_at, reverse=True)


def parse_requirement(description: str) -> RequirementParseResult:
    ai_result = parse_requirement_with_ai(description)
    if ai_result is not None:
        return ai_result
    return parse_requirement_locally(description)


def parse_requirement_locally(description: str) -> RequirementParseResult:
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


def build_recommendations(project_id: str, parse_result: RequirementParseResult) -> tuple[list[RequirementRecommendation], str, str]:
    recommendations = build_local_recommendations(project_id, parse_result)
    enriched, ai_status, ai_message = enrich_recommendations_with_ai(project_id, parse_result, recommendations)
    return enriched, ai_status, ai_message


def build_local_recommendations(project_id: str, parse_result: RequirementParseResult) -> list[RequirementRecommendation]:
    recommendations: list[RequirementRecommendation] = []
    query = build_requirement_search_query(parse_result)
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
                    id=f"rec-{uuid4()}",
                    group=group,
                    title=item.title,
                    source_type="test_package",
                    source_id=package.id,
                    reason=f"匹配归口包：{package.name}",
                    evidence=package.evidence,
                    objective=f"验证{item.title}满足归口包要求。",
                    method=item.trigger_condition or "按归口包要求执行测试并记录结果。",
                    record_template="记录测试条件、实际结果、判定结论和关联 BUG。",
                    review_status="pending",
                )
            )

    for risk in list_risks(project_id=project_id, subsystem=parse_result.subsystem):
            recommendations.append(
                RequirementRecommendation(
                    id=f"rec-{uuid4()}",
                    group="风险补充",
                    title=risk.suggested_test,
                    source_type=risk.source_type,
                    source_id=risk.id,
                    reason=f"风险项：{risk.title}",
                    evidence=risk.description,
                    objective=f"验证{risk.suggested_test}在该风险场景下的表现。",
                    method="按风险场景执行针对性验证并记录异常表现。",
                    record_template="记录风险场景、触发条件、实际表现、判定结论和关联 BUG。",
                    review_status="pending",
                )
            )

    for knowledge in search_project_knowledge(project_id, query)[:10]:
        if knowledge.source_type == "test_package":
            continue
        recommendations.append(
            RequirementRecommendation(
                id=f"rec-{uuid4()}",
                group="知识库补充",
                title=knowledge.title,
                source_type=knowledge.source_type,
                source_id=knowledge.source_id,
                reason="项目知识库检索命中",
                evidence=knowledge.text,
                objective="验证项目知识库命中内容对应的测试风险和覆盖项。",
                method="结合知识库命中内容执行补充验证。",
                record_template="记录知识库命中来源、验证场景、实际结果、判定结论和关联 BUG。",
                review_status="pending",
            )
        )

    recommendations = deduplicate_recommendations(recommendations)
    return recommendations


def build_requirement_search_query(parse_result: RequirementParseResult) -> str:
    return " ".join(
        value
        for value in [parse_result.product_model, parse_result.test_object, parse_result.subsystem, parse_result.change_type]
        if value
    )


def deduplicate_recommendations(recommendations: list[RequirementRecommendation]) -> list[RequirementRecommendation]:
    deduplicated: list[RequirementRecommendation] = []
    seen_titles: set[str] = set()
    for recommendation in recommendations:
        key = recommendation_deduplication_key(recommendation)
        if key in seen_titles:
            continue
        deduplicated.append(recommendation)
        seen_titles.add(key)
    return deduplicated


def recommendation_deduplication_key(recommendation: RequirementRecommendation) -> str:
    if recommendation.group == "风险补充":
        return f"risk:{normalize_exact_title(recommendation.title)}"
    return normalize_recommendation_title(recommendation.title)


def normalize_exact_title(title: str) -> str:
    return "".join(title.lower().split())


def normalize_recommendation_title(title: str) -> str:
    compact = normalize_exact_title(title)
    if "初始化" in compact:
        return "初始化"
    if any(keyword in compact for keyword in ["装配", "安装", "适配"]):
        return "安装装配适配"
    for keyword in ["读取", "写入", "兼容性", "安规emc", "emc"]:
        if keyword in compact:
            return keyword
    return compact


def enrich_recommendations_with_ai(
    project_id: str,
    parse_result: RequirementParseResult,
    local_recommendations: list[RequirementRecommendation],
) -> tuple[list[RequirementRecommendation], str, str]:
    query = build_requirement_search_query(parse_result)
    knowledge = search_project_knowledge(project_id, query)[:10]
    result = run_json_task_detailed(
        "requirement_recommendation",
        "你是基因测序仪测试需求推荐助手。只输出 JSON，不输出解释。",
        (
            "基于本地测试资产、归口包、风险和文档片段，只补充缺失测试项。不要输出本地已有测试项。输出 required、suggested、conditional 三个数组和 evidence。"
            "每个推荐项包含 title、source_type、source_id、reason、evidence。"
            "新增测试项统一使用 source_type=ai_generated，source_id 使用可区分的唯一字符串。"
            "AI 推荐项在结果中统一标注为 AI识别推荐测试项。"
            f"\n需求解析：{parse_result.model_dump()}"
            f"\n本地推荐：{[item.model_dump() for item in local_recommendations]}"
            f"\n知识命中：{[item.model_dump() for item in knowledge]}"
        ),
    )
    output = result.output
    if output is None:
        return local_recommendations, result.status, result.message
    enriched = list(local_recommendations)
    seen_titles = {normalize_recommendation_title(item.title) for item in enriched}
    ai_added_count = 0
    group_mapping = {"required": "必测", "suggested": "建议", "conditional": "条件触发"}
    for raw_group, group in group_mapping.items():
        raw_items = output.get(raw_group, [])
        if not isinstance(raw_items, list):
            continue
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            title = str(raw_item.get("title") or "")
            source_type = "ai_generated"
            source_id = str(raw_item.get("source_id") or f"ai:{uuid4()}")
            title_key = normalize_recommendation_title(title)
            if not title or title_key in seen_titles:
                continue
            enriched.append(
                RequirementRecommendation(
                    id=f"rec-{uuid4()}",
                    group="AI识别推荐测试项",
                    title=title,
                    source_type=source_type,
                    source_id=source_id,
                    reason=str(raw_item.get("reason") or "基于本地资产和知识检索补充的测试项"),
                    evidence=str(raw_item.get("evidence") or output.get("evidence") or "本地知识命中"),
                    objective=str(raw_item.get("objective") or f"验证{title}满足变更需求。"),
                    method=str(raw_item.get("method") or "按既有验证方案模板执行测试步骤并记录结果。"),
                    record_template=str(
                        raw_item.get("record_template")
                        or "记录样本编号、测试条件、实际结果、判定结论和关联 BUG。"
                    ),
                    review_status="pending",
                )
            )
            seen_titles.add(title_key)
            ai_added_count += 1
    if ai_added_count == 0:
        return enriched, "succeeded_no_items", "AI 调用成功，未识别到本地推荐之外的新增测试项。"
    return enriched, "succeeded", f"AI 调用成功，新增 {ai_added_count} 个推荐测试项。"


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
                    ai_status=analysis.ai_status,
                    ai_message=analysis.ai_message,
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
        ai_status=getattr(record, "ai_status", "not_configured"),
        ai_message=getattr(record, "ai_message", "AI 未配置，已使用本地规则推荐。"),
        status=record.status,
        created_at=record.created_at,
    )
