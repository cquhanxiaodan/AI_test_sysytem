from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.documents.repository import get_document
from app.modules.parsing.schemas import DocumentChunk, ParsingTaskRead
from app.modules.parsing.service import get_task, list_chunks, run_label_extraction_task, run_parse_task
from app.modules.projects.service import get_project_for_user

router = APIRouter(prefix="/parsing", tags=["parsing"])


@router.post("/documents/{document_id}/parse", response_model=ParsingTaskRead)
def parse_document(document_id: str, current_user: SeedUser = Depends(get_current_user)) -> ParsingTaskRead:
    ensure_document_access(document_id, current_user)
    task = run_parse_task(document_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return task


@router.post("/documents/{document_id}/extract-labels", response_model=ParsingTaskRead)
def extract_labels(document_id: str, current_user: SeedUser = Depends(get_current_user)) -> ParsingTaskRead:
    ensure_document_access(document_id, current_user)
    task = run_label_extraction_task(document_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return task


@router.get("/tasks/{task_id}", response_model=ParsingTaskRead)
def task_status(task_id: str, current_user: SeedUser = Depends(get_current_user)) -> ParsingTaskRead:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    ensure_document_access(task.document_id, current_user)
    return task


@router.get("/documents/{document_id}/chunks", response_model=list[DocumentChunk])
def document_chunks(document_id: str, current_user: SeedUser = Depends(get_current_user)) -> list[DocumentChunk]:
    ensure_document_access(document_id, current_user)
    return list_chunks(document_id)


def ensure_document_access(document_id: str, user: SeedUser) -> None:
    document = get_document(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if get_project_for_user(document.project_id, user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
