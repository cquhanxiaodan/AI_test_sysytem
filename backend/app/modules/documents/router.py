from hashlib import sha256
from mimetypes import guess_type
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.modules.admin.service import get_persisted_import_directory, save_import_directory
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.documents.repository import (
    create_document,
    delete_document,
    find_document_by_hash,
    get_document_content,
    get_document,
    list_documents,
    review_document,
    update_labels,
)
from app.modules.documents.schemas import (
    DocumentBatchUploadResponse,
    DocumentBulkDeleteRequest,
    DocumentBulkDeleteResponse,
    DocumentDirectoryScanResponse,
    DocumentImportConfigRead,
    DocumentImportConfigUpdate,
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
RUNTIME_IMPORT_CONFIG: dict[str, str] = {}


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


@router.post("/upload-batch", response_model=DocumentBatchUploadResponse)
async def upload_documents(
    project_id: str = Form(...),
    files: list[UploadFile] = File(...),
    current_user: SeedUser = Depends(get_current_user),
) -> DocumentBatchUploadResponse:
    if get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    documents = []
    for file in files:
        content = await file.read()
        documents.append(
            create_document(
                project_id=project_id,
                filename=file.filename or "uploaded-file",
                content_type=file.content_type or "application/octet-stream",
                content=content,
                uploaded_by=current_user.id,
            )
        )
    return DocumentBatchUploadResponse(documents=documents)


@router.get("/import-config", response_model=DocumentImportConfigRead)
def get_import_config(current_user: SeedUser = Depends(get_current_user)) -> DocumentImportConfigRead:
    import_directory = get_import_directory()
    return DocumentImportConfigRead(import_directory=import_directory, configured=bool(import_directory))


@router.put("/import-config", response_model=DocumentImportConfigRead)
def update_import_config(
    payload: DocumentImportConfigUpdate,
    current_user: SeedUser = Depends(get_current_user),
) -> DocumentImportConfigRead:
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    RUNTIME_IMPORT_CONFIG["import_directory"] = payload.import_directory.strip()
    save_import_directory(payload.import_directory)
    return get_import_config(current_user)


@router.post("/scan-import-directory", response_model=DocumentDirectoryScanResponse)
def scan_import_directory(
    project_id: str = Form(...),
    current_user: SeedUser = Depends(get_current_user),
) -> DocumentDirectoryScanResponse:
    if get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    import_directory = get_import_directory()
    if not import_directory:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Import directory is not configured")
    base_path = Path(import_directory).expanduser().resolve()
    if not base_path.exists() or not base_path.is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Import directory is not available")

    imported: list[DocumentRead] = []
    skipped: list[str] = []
    errors: list[str] = []
    for path in sorted(base_path.iterdir()):
        if not path.is_file():
            skipped.append(path.name)
            continue
        try:
            content = path.read_bytes()
        except OSError as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        file_hash = sha256(content).hexdigest()
        if find_document_by_hash(file_hash, project_id) is not None:
            skipped.append(path.name)
            continue
        content_type = guess_type(path.name)[0] or "application/octet-stream"
        imported.append(
            create_document(
                project_id=project_id,
                filename=path.name,
                content_type=content_type,
                content=content,
                uploaded_by=current_user.id,
            )
        )
    return DocumentDirectoryScanResponse(import_directory=str(base_path), imported=imported, skipped=skipped, errors=errors)


@router.get("", response_model=list[DocumentRead])
def documents(
    project_id: str | None = None,
    current_user: SeedUser = Depends(get_current_user),
) -> list[DocumentRead]:
    if project_id is not None and get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return list_documents(project_id)


@router.post("/bulk-delete", response_model=DocumentBulkDeleteResponse)
def bulk_delete_documents(
    payload: DocumentBulkDeleteRequest,
    current_user: SeedUser = Depends(get_current_user),
) -> DocumentBulkDeleteResponse:
    deleted_ids: list[str] = []
    skipped: list[dict[str, str]] = []
    for document_id in dict.fromkeys(payload.document_ids):
        document = get_document(document_id)
        if document is None:
            skipped.append({"document_id": document_id, "reason": "资料不存在"})
            continue
        if get_project_for_user(document.project_id, current_user) is None:
            skipped.append({"document_id": document_id, "reason": "无项目访问权限"})
            continue
        if delete_document(document.id):
            deleted_ids.append(document.id)
    return DocumentBulkDeleteResponse(deleted_ids=deleted_ids, skipped=skipped)


def get_import_directory() -> str:
    return RUNTIME_IMPORT_CONFIG.get("import_directory", get_persisted_import_directory()).strip()


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
    document_type = infer_document_type(document)
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


def infer_document_type(document: DocumentRead) -> str:
    document_type = document.labels.get("document_type") or next(
        (suggestion.label_value for suggestion in document.label_suggestions if suggestion.label_key == "document_type"),
        "",
    )
    if document_type:
        return document_type
    filename = document.filename.lower()
    if "jira" in filename:
        return "Jira导出"
    if "dfmea" in filename:
        return "DFMEA"
    if "报告" in document.filename:
        return "测试报告"
    if "规范" in document.filename:
        return "测试规范"
    if "方案" in document.filename or "validation" in filename:
        return "验证方案"
    return ""
