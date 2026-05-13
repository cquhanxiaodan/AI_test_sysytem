from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.documents.repository import (
    create_document,
    get_document_content,
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
from app.modules.parsing.service import run_label_extraction_task, run_parse_task
from app.modules.projects.service import get_project_for_user
from app.modules.risks.service import parse_risks
from app.modules.test_items.service import split_document_to_items
from app.modules.test_packages.service import generate_rfid_supplier_change_package

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
    if updated.status == "published":
        run_published_document_pipeline(updated)
    return updated


def run_published_document_pipeline(document: DocumentRead) -> None:
    document_type = document.labels.get("document_type") or next(
        (suggestion.label_value for suggestion in document.label_suggestions if suggestion.label_key == "document_type"),
        "",
    )
    if document_type in {"Jira导出", "DFMEA"}:
        content = get_document_content(document.id)
        if content is not None:
            parse_risks(document.project_id, "jira" if document_type == "Jira导出" else "dfmea", decode_content(content))
        return

    run_parse_task(document.id)
    run_label_extraction_task(document.id)
    if document_type in {"验证方案", "测试规范", "测试报告"}:
        split_document_to_items(document.id)
        if (document.labels.get("subsystem") == "RFID") or any(suggestion.label_value == "RFID" for suggestion in document.label_suggestions):
            generate_rfid_supplier_change_package(document.project_id)


def decode_content(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return ""
