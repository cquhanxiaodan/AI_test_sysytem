from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.projects.service import get_project_for_user
from app.modules.risks.schemas import RiskItem, RiskParseRequest, RiskParseResponse
from app.modules.risks.service import list_risks, parse_risks

router = APIRouter(prefix="/risks", tags=["risks"])


@router.get("", response_model=list[RiskItem])
def risks(
    project_id: str | None = None,
    test_object: str | None = None,
    subsystem: str | None = None,
    source_type: str | None = None,
    current_user: SeedUser = Depends(get_current_user),
) -> list[RiskItem]:
    if project_id is not None and get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return list_risks(project_id, test_object, subsystem, source_type)


@router.post("/parse", response_model=RiskParseResponse)
def parse(payload: RiskParseRequest, current_user: SeedUser = Depends(get_current_user)) -> RiskParseResponse:
    if get_project_for_user(payload.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    items = parse_risks(payload.project_id, payload.source_type, payload.content)
    return RiskParseResponse(items=items)
