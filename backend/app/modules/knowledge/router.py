from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.knowledge.schemas import SearchRequest, SearchResponse
from app.modules.knowledge.service import search_project_knowledge
from app.modules.projects.service import get_project_for_user

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, current_user: SeedUser = Depends(get_current_user)) -> SearchResponse:
    if get_project_for_user(payload.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return SearchResponse(results=search_project_knowledge(payload.project_id, payload.query))
