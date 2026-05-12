from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.documents.repository import get_document
from app.modules.projects.service import get_project_for_user
from app.modules.test_items.schemas import SplitResult, TestItemAsset
from app.modules.test_items.service import confirm_item, list_test_items, split_document_to_items

router = APIRouter(prefix="/test-items", tags=["test-items"])


@router.get("", response_model=list[TestItemAsset])
def items(project_id: str | None = None, current_user: SeedUser = Depends(get_current_user)) -> list[TestItemAsset]:
    if project_id is not None and get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return list_test_items(project_id)


@router.post("/split/{document_id}", response_model=SplitResult)
def split_document(document_id: str, current_user: SeedUser = Depends(get_current_user)) -> SplitResult:
    document = get_document(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if get_project_for_user(document.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    result = split_document_to_items(document_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return result


@router.post("/{item_id}/confirm", response_model=TestItemAsset)
def confirm(item_id: str, current_user: SeedUser = Depends(get_current_user)) -> TestItemAsset:
    item = confirm_item(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test item not found")
    if get_project_for_user(item.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return item
