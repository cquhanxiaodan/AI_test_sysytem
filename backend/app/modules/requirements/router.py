from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.projects.service import get_project_for_user
from app.modules.requirements.schemas import RequirementAnalysisRead, RequirementAnalysisRequest
from app.modules.requirements.service import create_analysis, get_analysis

router = APIRouter(prefix="/requirement-analyses", tags=["requirement-analyses"])


@router.post("", response_model=RequirementAnalysisRead)
def create(payload: RequirementAnalysisRequest, current_user: SeedUser = Depends(get_current_user)) -> RequirementAnalysisRead:
    if get_project_for_user(payload.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return create_analysis(payload.project_id, payload.description)


@router.get("/{analysis_id}", response_model=RequirementAnalysisRead)
def detail(analysis_id: str, current_user: SeedUser = Depends(get_current_user)) -> RequirementAnalysisRead:
    analysis = get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if get_project_for_user(analysis.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return analysis
