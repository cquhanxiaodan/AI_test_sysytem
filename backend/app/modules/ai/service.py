from datetime import UTC, datetime
from contextvars import ContextVar
import json
from typing import Any
from urllib import error, request
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.admin.schemas import AiSettingsConfig
from app.modules.admin.service import get_persisted_ai_config, save_ai_settings
from app.modules.ai.schemas import AiConfigRead, AiConfigUpdate, AiRunRecord, AiTaskResult

AI_RUNS: dict[str, AiRunRecord] = {}
RUNTIME_AI_CONFIG: dict[str, Any] = {}
RUNTIME_USER_AI_CONFIGS: dict[str, dict[str, Any]] = {}
CURRENT_AI_USER_ID: ContextVar[str | None] = ContextVar("current_ai_user_id", default=None)


class AiRunRecordModel(Base):
    __tablename__ = "ai_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(120), index=True)
    model_name: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(80))
    output: Mapped[dict[str, Any]] = mapped_column(JSON)
    valid: Mapped[bool] = mapped_column(Boolean, index=True)
    errors: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

REQUIRED_FIELDS = {
    "document_label_extraction": ["labels", "confidence", "evidence"],
    "requirement_parse": ["test_object", "change_type", "product_model", "subsystem", "missing_fields"],
    "requirement_recommendation": ["required", "suggested", "conditional", "evidence"],
    "test_item_split": ["items", "evidence"],
    "risk_parse": ["items", "evidence"],
    "validation_plan_check": ["blocking", "warnings", "suggestions"],
    "free_chat": ["answer"],
}


def validate_output(task_type: str, output: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS.get(task_type, []):
        if field not in output:
            errors.append(f"缺少字段: {field}")
    confidence = output.get("confidence")
    if confidence is not None and (not isinstance(confidence, int | float) or confidence < 0 or confidence > 1):
        errors.append("confidence 必须在 0 到 1 之间")
    return len(errors) == 0, errors


def get_ai_config(user_id: str | None = None) -> AiConfigRead:
    provider, base_url, api_key, model, timeout_seconds = get_ai_runtime_values(user_id)
    configured = provider == "openai-compatible" and bool(base_url and api_key and model)
    return AiConfigRead(
        provider=provider,
        base_url=base_url,
        model=model or "local-rule-engine",
        timeout_seconds=timeout_seconds,
        configured=configured,
        external_reference_enabled=configured,
        api_key_configured=bool(api_key),
        api_key_masked=mask_secret(api_key),
    )


def update_ai_config(payload: AiConfigUpdate, user_id: str | None = None) -> AiConfigRead:
    provider = payload.provider if payload.provider in {"local", "openai-compatible"} else "local"
    current_provider, current_base_url, current_api_key, current_model, current_timeout = get_ai_runtime_values(user_id)
    timeout_seconds = payload.timeout_seconds if payload.timeout_seconds > 0 else current_timeout
    runtime_config = RUNTIME_USER_AI_CONFIGS.setdefault(user_id, {}) if user_id else RUNTIME_AI_CONFIG
    runtime_config.update(
        {
            "provider": provider,
            "base_url": payload.base_url.strip(),
            "model": payload.model.strip(),
            "timeout_seconds": timeout_seconds,
        }
    )
    if payload.api_key.strip():
        runtime_config["api_key"] = payload.api_key.strip()
    elif "api_key" not in runtime_config and current_api_key:
        runtime_config["api_key"] = current_api_key
    if provider == "local":
        runtime_config.update({"base_url": "", "model": "", "api_key": ""})
    save_ai_settings(
        AiSettingsConfig(
            provider=str(runtime_config.get("provider", provider)),
            base_url=str(runtime_config.get("base_url", "")),
            api_key=str(runtime_config.get("api_key", "")),
            model=str(runtime_config.get("model", "")),
            timeout_seconds=int(runtime_config.get("timeout_seconds", timeout_seconds)),
        ),
        user_id=user_id,
    )
    return get_ai_config(user_id)


def get_ai_runtime_values(user_id: str | None = None) -> tuple[str, str, str, str, int]:
    if user_id is None:
        user_id = CURRENT_AI_USER_ID.get()
    persisted = get_persisted_ai_config(user_id)
    runtime_config = RUNTIME_USER_AI_CONFIGS.get(user_id, {}) if user_id else RUNTIME_AI_CONFIG
    return (
        str(runtime_config.get("provider", persisted.provider)),
        str(runtime_config.get("base_url", persisted.base_url)),
        str(runtime_config.get("api_key", persisted.api_key)),
        str(runtime_config.get("model", persisted.model)),
        int(runtime_config.get("timeout_seconds", persisted.timeout_seconds)),
    )


def mask_secret(secret: str) -> str | None:
    if not secret:
        return None
    if len(secret) <= 8:
        return "****"
    return f"{secret[:4]}****{secret[-4:]}"


def run_json_task(
    task_type: str,
    system_prompt: str,
    user_prompt: str,
    user_id: str | None = None,
    timeout_seconds_override: int | None = None,
) -> dict[str, Any] | None:
    return run_json_task_detailed(
        task_type,
        system_prompt,
        user_prompt,
        user_id=user_id,
        timeout_seconds_override=timeout_seconds_override,
    ).output


def run_json_task_detailed(
    task_type: str,
    system_prompt: str,
    user_prompt: str,
    user_id: str | None = None,
    timeout_seconds_override: int | None = None,
) -> AiTaskResult:
    provider, base_url, api_key, model, timeout_seconds = get_ai_runtime_values(user_id)
    effective_timeout = timeout_seconds
    if timeout_seconds_override is not None and timeout_seconds_override > 0:
        effective_timeout = min(timeout_seconds, timeout_seconds_override)
    if provider != "openai-compatible" or not (base_url and api_key and model):
        return AiTaskResult(output=None, status="not_configured", message="AI 未配置，已使用本地规则推荐。")
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    try:
        data = request_chat_completion(url, api_key, payload, effective_timeout)
    except TimeoutError:
        return AiTaskResult(output=None, status="failed", message="AI 调用超时，已使用本地规则推荐。")
    except error.HTTPError as exc:
        if exc.code in {400, 422, 500, 502} and "response_format" in payload:
            fallback_payload = {key: value for key, value in payload.items() if key != "response_format"}
            try:
                data = request_chat_completion(url, api_key, fallback_payload, effective_timeout)
            except TimeoutError:
                return AiTaskResult(output=None, status="failed", message="AI 调用超时，已使用本地规则推荐。")
            except error.HTTPError as fallback_exc:
                return AiTaskResult(output=None, status="failed", message=f"AI 调用失败，HTTP 状态码 {fallback_exc.code}。")
            except error.URLError as fallback_exc:
                return AiTaskResult(output=None, status="failed", message=f"AI 调用失败：{fallback_exc.reason}")
            except json.JSONDecodeError:
                return AiTaskResult(output=None, status="failed", message="AI 服务返回内容无法解析。")
        else:
            return AiTaskResult(output=None, status="failed", message=f"AI 调用失败，HTTP 状态码 {exc.code}。")
    except error.URLError as exc:
        return AiTaskResult(output=None, status="failed", message=f"AI 调用失败：{exc.reason}")
    except json.JSONDecodeError:
        return AiTaskResult(output=None, status="failed", message="AI 服务返回内容无法解析。")

    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not isinstance(content, str):
        return AiTaskResult(output=None, status="failed", message="AI 服务响应中缺少文本内容。")
    try:
        output = json.loads(content)
    except json.JSONDecodeError:
        return AiTaskResult(output=None, status="failed", message="AI 输出不是合法 JSON。")
    if isinstance(output, dict):
        record_ai_run(task_type, output, model_name=model)
        return AiTaskResult(output=output, status="succeeded", message="AI 调用成功。")
    return AiTaskResult(output=None, status="failed", message="AI 输出结构不是对象。")


def request_chat_completion(url: str, api_key: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def record_ai_run(task_type: str, output: dict[str, Any], model_name: str | None = None) -> AiRunRecord:
    valid, errors = validate_output(task_type, output)
    record = AiRunRecord(
        id=f"ai-run-{uuid4()}",
        task_type=task_type,
        model_name=model_name or get_ai_runtime_values()[3] or "local-mock",
        prompt_version="v1",
        output=output,
        valid=valid,
        errors=errors,
        created_at=datetime.now(UTC),
    )
    _save_ai_run(record)
    return record


def get_ai_run(record_id: str) -> AiRunRecord | None:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.get(AiRunRecordModel, record_id)
            return _model_to_record(record) if record is not None else None
    return AI_RUNS.get(record_id)


def _use_sqlalchemy() -> bool:
    return get_settings().repository_backend == "sqlalchemy"


def _save_ai_run(record: AiRunRecord) -> None:
    if _use_sqlalchemy():
        with session_scope() as session:
            session.merge(
                AiRunRecordModel(
                    id=record.id,
                    task_type=record.task_type,
                    model_name=record.model_name,
                    prompt_version=record.prompt_version,
                    output=record.output,
                    valid=record.valid,
                    errors=record.errors,
                    created_at=record.created_at,
                )
            )
        return
    AI_RUNS[record.id] = record


def _model_to_record(model: AiRunRecordModel) -> AiRunRecord:
    return AiRunRecord(
        id=model.id,
        task_type=model.task_type,
        model_name=model.model_name,
        prompt_version=model.prompt_version,
        output=model.output or {},
        valid=model.valid,
        errors=model.errors or [],
        created_at=model.created_at,
    )
