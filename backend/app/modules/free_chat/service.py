from app.modules.ai.service import run_json_task
from app.modules.free_chat.schemas import FreeChatResponse, FreeChatSource
from app.modules.knowledge.service import search_project_knowledge


def answer_free_chat(project_id: str, question: str, use_project_knowledge: bool, use_external_model: bool) -> FreeChatResponse:
    sources = search_project_knowledge(project_id, question)[:8] if use_project_knowledge else []
    source_reads = [FreeChatSource(**source.model_dump()) for source in sources]
    if use_external_model:
        ai_answer = answer_with_ai(question, source_reads)
        if ai_answer:
            return FreeChatResponse(answer=ai_answer, used_model=True, sources=source_reads)
    return FreeChatResponse(answer=build_local_answer(question, source_reads), used_model=False, sources=source_reads)


def answer_with_ai(question: str, sources: list[FreeChatSource]) -> str | None:
    output = run_json_task(
        "free_chat",
        "你是基因测序仪测试知识问答助手。只输出 JSON，不输出解释。",
        (
            "基于用户问题和项目资料库命中内容回答。输出 answer 字段。"
            "回答需要标注依据来自资料库命中；资料不足时说明需要补充资料。"
            f"\n问题：{question}"
            f"\n资料库命中：{[source.model_dump() for source in sources]}"
        ),
    )
    if output is None or not isinstance(output.get("answer"), str):
        return None
    return output["answer"]


def build_local_answer(question: str, sources: list[FreeChatSource]) -> str:
    if not sources:
        return "当前项目资料库没有命中相关内容。请先上传并发布资料，或在系统设置中配置 AI 模型后再提问。"
    lines = [f"基于当前项目资料库，问题“{question}”命中了以下内容："]
    for index, source in enumerate(sources[:5], start=1):
        lines.append(f"{index}. [{source.source_type}] {source.title}：{source.text[:180]}")
    lines.append("可基于这些来源继续追问，或配置 AI 模型生成综合回答。")
    return "\n".join(lines)
