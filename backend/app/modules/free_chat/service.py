from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import logging

from app.modules.ai.service import get_ai_runtime_values, run_json_task_detailed
from app.modules.free_chat.schemas import FreeChatMessage, FreeChatResponse, FreeChatSource
from app.modules.knowledge.service import search_project_knowledge

logger = logging.getLogger("uvicorn.error")
AI_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def answer_free_chat(
    project_id: str,
    question: str,
    use_project_knowledge: bool,
    use_external_model: bool,
    messages: list[FreeChatMessage] | None = None,
    user_id: str | None = None,
) -> FreeChatResponse:
    history = normalize_history(messages or [])
    query = build_context_query(question, history)
    sources = search_project_knowledge(project_id, query)[:8] if use_project_knowledge else []
    source_reads = [FreeChatSource(**source.model_dump()) for source in sources]
    if use_external_model:
        ai_answer, ai_status, ai_message = answer_with_ai(question, source_reads, history, user_id, use_project_knowledge)
        logger.info("free_chat_ai_result status=%s used_model=%s message=%s", ai_status, bool(ai_answer), ai_message)
        if ai_answer:
            return FreeChatResponse(
                answer=ai_answer,
                used_model=True,
                sources=source_reads,
                ai_status=ai_status,
                ai_message=ai_message,
            )
        return FreeChatResponse(
            answer=build_ai_failure_answer(question, source_reads, history, use_project_knowledge),
            used_model=False,
            sources=source_reads,
            ai_status=ai_status,
            ai_message=ai_message,
        )
    return FreeChatResponse(
        answer=build_local_answer(question, source_reads, history),
        used_model=False,
        sources=source_reads,
    )


def answer_with_ai(
    question: str,
    sources: list[FreeChatSource],
    history: list[FreeChatMessage],
    user_id: str | None = None,
    use_project_knowledge: bool = True,
) -> tuple[str | None, str, str]:
    knowledge_prompt = build_ai_knowledge_prompt(sources) if use_project_knowledge else "本次未启用项目资料库检索，请基于当前对话和你的通用知识回答。"
    timeout_seconds = get_ai_runtime_values(user_id)[4]
    future = AI_EXECUTOR.submit(
        run_json_task_detailed,
        "free_chat",
        "你是基因测序仪测试知识问答助手。只输出 JSON，不输出解释。",
        build_ai_prompt(question, history, knowledge_prompt),
        user_id,
    )
    try:
        result = future.result(timeout=timeout_seconds)
    except FutureTimeoutError:
        future.cancel()
        return None, "failed", "AI 调用超时，已使用本地规则推荐。"
    output = result.output
    if output is None or not isinstance(output.get("answer"), str):
        return None, result.status, result.message
    return output["answer"], result.status, result.message


def build_ai_prompt(question: str, history: list[FreeChatMessage], knowledge_prompt: str) -> str:
    return (
        "基于当前对话上下文和用户最新问题回答。输出 answer 字段。"
        "如果提供了项目资料库命中内容，将其作为参考上下文使用；回答可以结合你的通用知识进行扩展。"
        "当资料库没有命中或未启用资料库时，直接基于通用知识给出有帮助的回答。"
        f"\n最近对话：{[message.model_dump() for message in history[-8:]]}"
        f"\n问题：{question}"
        f"\n资料库参考：{knowledge_prompt}"
    )


def build_ai_knowledge_prompt(sources: list[FreeChatSource]) -> str:
    if not sources:
        return "项目资料库没有命中内容，请基于当前对话和你的通用知识回答。"
    return str([source.model_dump() for source in sources])


def build_ai_failure_answer(question: str, sources: list[FreeChatSource], history: list[FreeChatMessage], use_project_knowledge: bool) -> str:
    if use_project_knowledge:
        return build_local_answer(question, sources, history)
    context_note = "已读取当前对话上下文。" if history else ""
    return f"{context_note}本次未启用项目资料库参考，但 AI 模型没有在超时时间内返回结果。请稍后重试，或检查系统设置中的 AI 模型配置。"


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
