from fastapi import APIRouter, Depends

from app.modules.ai.schemas import AiConfigRead, AiConfigUpdate, AiRunRecord, AiValidationRequest, AiValidationResponse
from app.modules.ai.service import get_ai_config, record_ai_run, update_ai_config, validate_output
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/config", response_model=AiConfigRead)
def config(current_user: SeedUser = Depends(get_current_user)) -> AiConfigRead:
    return get_ai_config(current_user.id)


@router.put("/config", response_model=AiConfigRead)
def update_config(payload: AiConfigUpdate, current_user: SeedUser = Depends(get_current_user)) -> AiConfigRead:
    return update_ai_config(payload, current_user.id)


@router.post("/validate", response_model=AiValidationResponse)
def validate(payload: AiValidationRequest, current_user: SeedUser = Depends(get_current_user)) -> AiValidationResponse:
    valid, errors = validate_output(payload.task_type, payload.output)
    return AiValidationResponse(valid=valid, errors=errors)


@router.post("/runs", response_model=AiRunRecord)
def create_run(payload: AiValidationRequest, current_user: SeedUser = Depends(get_current_user)) -> AiRunRecord:
    return record_ai_run(payload.task_type, payload.output)
