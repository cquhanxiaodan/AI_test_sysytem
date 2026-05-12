from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.documents.repository import (
    create_document,
    get_document,
    list_documents,
    review_document,
    update_labels,
)
from app.modules.documents.schemas import (
    DocumentLabelUpdate,
    DocumentRead,
    DocumentReviewRequest,
    DocumentUploadResponse,
)
from app.modules.projects.service import get_project_for_user

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: SeedUser = Depends(get_current_user),
) -> DocumentUploadResponse:
    if get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")

    content = await file.read()
    document = create_document(
        project_id=project_id,
        filename=file.filename or "uploaded-file",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        uploaded_by=current_user.id,
    )
    return DocumentUploadResponse(document=document)


@router.get("", response_model=list[DocumentRead])
def documents(
    project_id: str | None = None,
    current_user: SeedUser = Depends(get_current_user),
) -> list[DocumentRead]:
    if project_id is not None and get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return list_documents(project_id)


@router.get("/{document_id}", response_model=DocumentRead)
def document_detail(document_id: str, current_user: SeedUser = Depends(get_current_user)) -> DocumentRead:
    document = get_document(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if get_project_for_user(document.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return document


@router.patch("/{document_id}/labels", response_model=DocumentRead)
def update_document_labels(
    document_id: str,
    payload: DocumentLabelUpdate,
    current_user: SeedUser = Depends(get_current_user),
) -> DocumentRead:
    document = document_detail(document_id, current_user)
    updated = update_labels(document.id, payload.labels)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return updated


@router.post("/{document_id}/review", response_model=DocumentRead)
def review(
    document_id: str,
    payload: DocumentReviewRequest,
    current_user: SeedUser = Depends(get_current_user),
) -> DocumentRead:
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    document = get_document(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    updated = review_document(document.id, payload.action)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return updated
