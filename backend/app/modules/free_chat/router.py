from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.free_chat.schemas import FreeChatRequest, FreeChatResponse
from app.modules.free_chat.service import answer_free_chat
from app.modules.projects.service import get_project_for_user

router = APIRouter(prefix="/free-chat", tags=["free-chat"])


@router.post("/ask", response_model=FreeChatResponse)
def ask(payload: FreeChatRequest, current_user: SeedUser = Depends(get_current_user)) -> FreeChatResponse:
    if get_project_for_user(payload.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return answer_free_chat(
        payload.project_id,
        payload.question,
        payload.use_project_knowledge,
        payload.use_external_model,
        payload.messages,
    )
