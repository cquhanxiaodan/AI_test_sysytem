from app.modules.ai.service import run_json_task
from app.modules.free_chat.schemas import FreeChatMessage, FreeChatResponse, FreeChatSource
from app.modules.knowledge.service import search_project_knowledge


def answer_free_chat(
    project_id: str,
    question: str,
    use_project_knowledge: bool,
    use_external_model: bool,
    messages: list[FreeChatMessage] | None = None,
) -> FreeChatResponse:
    history = normalize_history(messages or [])
    query = build_context_query(question, history)
    sources = search_project_knowledge(project_id, query)[:8] if use_project_knowledge else []
    source_reads = [FreeChatSource(**source.model_dump()) for source in sources]
    if use_external_model:
        ai_answer = answer_with_ai(question, source_reads, history)
        if ai_answer:
            return FreeChatResponse(answer=ai_answer, used_model=True, sources=source_reads)
    return FreeChatResponse(answer=build_local_answer(question, source_reads, history), used_model=False, sources=source_reads)


def answer_with_ai(question: str, sources: list[FreeChatSource], history: list[FreeChatMessage]) -> str | None:
    output = run_json_task(
        "free_chat",
        "你是基因测序仪测试知识问答助手。只输出 JSON，不输出解释。",
        (
            "基于当前对话上下文、用户最新问题和项目资料库命中内容回答。输出 answer 字段。"
            "回答需要标注依据来自资料库命中；资料不足时说明需要补充资料。"
            f"\n最近对话：{[message.model_dump() for message in history[-8:]]}"
            f"\n问题：{question}"
            f"\n资料库命中：{[source.model_dump() for source in sources]}"
        ),
    )
    if output is None or not isinstance(output.get("answer"), str):
        return None
    return output["answer"]


def build_local_answer(question: str, sources: list[FreeChatSource], history: list[FreeChatMessage]) -> str:
    if not sources:
        if history:
            return "已读取当前对话上下文，但当前项目资料库没有命中相关内容。请补充资料，或在系统设置中配置 AI 模型后继续追问。"
        return "当前项目资料库没有命中相关内容。请先上传并发布资料，或在系统设置中配置 AI 模型后再提问。"
    prefix = "结合当前对话上下文和项目资料库" if history else "基于当前项目资料库"
    lines = [f"{prefix}，问题“{question}”命中了以下内容："]
    for index, source in enumerate(sources[:5], start=1):
        lines.append(f"{index}. [{source.source_type}] {source.title}：{source.text[:180]}")
    lines.append("可基于这些来源继续追问，或配置 AI 模型生成综合回答。")
    return "\n".join(lines)


def normalize_history(messages: list[FreeChatMessage]) -> list[FreeChatMessage]:
    normalized = []
    for message in messages[-12:]:
        role = message.role if message.role in {"user", "assistant"} else "user"
        content = message.content.strip()
        if content:
            normalized.append(FreeChatMessage(role=role, content=content[:1000]))
    return normalized


def build_context_query(question: str, history: list[FreeChatMessage]) -> str:
    recent_user_context = " ".join(message.content for message in history[-6:] if message.role == "user")
    return f"{recent_user_context} {question}".strip()
