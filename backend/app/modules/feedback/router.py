from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user, require_admin
from app.modules.auth.seed_data import SeedUser
from app.modules.feedback.schemas import FeedbackAdminUpdate, FeedbackCreate, FeedbackItem
from app.modules.feedback.service import create_feedback, list_feedback, update_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.get("", response_model=list[FeedbackItem])
def list_items(current_user: SeedUser = Depends(get_current_user)) -> list[FeedbackItem]:
    return list_feedback(current_user)


@router.post("", response_model=FeedbackItem)
def create_item(payload: FeedbackCreate, current_user: SeedUser = Depends(get_current_user)) -> FeedbackItem:
    return create_feedback(payload, current_user)


@router.patch("/{feedback_id}", response_model=FeedbackItem)
def patch_item(
    feedback_id: str,
    payload: FeedbackAdminUpdate,
    current_user: SeedUser = Depends(require_admin),
) -> FeedbackItem:
    item = update_feedback(feedback_id, payload, current_user)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    return item
