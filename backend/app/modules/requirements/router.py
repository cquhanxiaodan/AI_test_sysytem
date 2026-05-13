from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.projects.service import get_project_for_user
from app.modules.requirements.schemas import (
    RequirementAnalysisRead,
    RequirementAnalysisRequest,
    RequirementBatchItem,
    RequirementBatchUploadResponse,
    RequirementDocumentUploadResponse,
    RequirementTemplateField,
    RequirementTemplateRead,
)
from app.modules.requirements.service import (
    build_requirement_template_csv,
    create_analysis,
    extract_requirement_description,
    get_analysis,
    get_requirement_template_fields,
    get_requirement_template_sample_rows,
    parse_requirement_table,
)

router = APIRouter(prefix="/requirement-analyses", tags=["requirement-analyses"])


@router.get("/template", response_model=RequirementTemplateRead)
def requirement_template(current_user: SeedUser = Depends(get_current_user)) -> RequirementTemplateRead:
    return RequirementTemplateRead(
        fields=[RequirementTemplateField(**field) for field in get_requirement_template_fields()],
        sample_rows=get_requirement_template_sample_rows(),
    )


@router.get("/template/download")
def download_requirement_template(current_user: SeedUser = Depends(get_current_user)) -> Response:
    return Response(
        content=build_requirement_template_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="requirement-analysis-template.csv"'},
    )


@router.post("", response_model=RequirementAnalysisRead)
def create(payload: RequirementAnalysisRequest, current_user: SeedUser = Depends(get_current_user)) -> RequirementAnalysisRead:
    if get_project_for_user(payload.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return create_analysis(payload.project_id, payload.description)


@router.post("/upload", response_model=RequirementDocumentUploadResponse)
async def upload_requirement_document(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: SeedUser = Depends(get_current_user),
) -> RequirementDocumentUploadResponse:
    if get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    content = await file.read()
    return RequirementDocumentUploadResponse(
        filename=file.filename or "requirement-document",
        description=extract_requirement_description(file.filename or "requirement-document", content),
    )


@router.post("/upload-table", response_model=RequirementBatchUploadResponse)
async def upload_requirement_table(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: SeedUser = Depends(get_current_user),
) -> RequirementBatchUploadResponse:
    if get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    content = await file.read()
    items = [
        RequirementBatchItem(
            row_number=row_number,
            description=description,
            missing_fields=missing_fields,
            analysis=None if missing_fields else create_analysis(project_id, description),
        )
        for row_number, description, missing_fields in parse_requirement_table(content)
    ]
    return RequirementBatchUploadResponse(filename=file.filename or "requirement-table.csv", items=items)


@router.get("/{analysis_id}", response_model=RequirementAnalysisRead)
def detail(analysis_id: str, current_user: SeedUser = Depends(get_current_user)) -> RequirementAnalysisRead:
    analysis = get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if get_project_for_user(analysis.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return analysis
