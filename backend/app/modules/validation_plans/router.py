from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.projects.service import get_project_for_user
from app.modules.validation_plans.schemas import (
    ExportRecord,
    ValidationPlanCheckResult,
    ValidationPlanCreateRequest,
    ValidationPlanRead,
)
from app.modules.validation_plans.service import check_plan, create_plan, export_plan, get_plan, list_plans

router = APIRouter(prefix="/validation-plans", tags=["validation-plans"])


@router.get("", response_model=list[ValidationPlanRead])
def plans(project_id: str | None = None, current_user: SeedUser = Depends(get_current_user)) -> list[ValidationPlanRead]:
    if project_id is not None and get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return list_plans(project_id)


@router.post("", response_model=ValidationPlanRead)
def create(payload: ValidationPlanCreateRequest, current_user: SeedUser = Depends(get_current_user)) -> ValidationPlanRead:
    plan = create_plan(payload.requirement_analysis_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement analysis not found")
    if get_project_for_user(plan.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return plan


@router.get("/{plan_id}", response_model=ValidationPlanRead)
def detail(plan_id: str, current_user: SeedUser = Depends(get_current_user)) -> ValidationPlanRead:
    plan = get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation plan not found")
    if get_project_for_user(plan.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return plan


@router.post("/{plan_id}/check", response_model=ValidationPlanCheckResult)
def check(plan_id: str, current_user: SeedUser = Depends(get_current_user)) -> ValidationPlanCheckResult:
    detail(plan_id, current_user)
    result = check_plan(plan_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation plan not found")
    return result


@router.post("/{plan_id}/export", response_model=ExportRecord)
def export(plan_id: str, current_user: SeedUser = Depends(get_current_user)) -> ExportRecord:
    detail(plan_id, current_user)
    record = export_plan(plan_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation plan not found")
    return record
