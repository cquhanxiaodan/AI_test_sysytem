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
    RequirementRecommendationCreate,
    RequirementRecommendationUpdate,
    RequirementTemplateField,
    RequirementTemplateRead,
)
from app.modules.requirements.service import (
    add_recommendation,
    build_requirement_template_csv,
    create_analysis,
    create_local_analysis,
    delete_analysis,
    delete_recommendation,
    extract_requirement_description,
    get_analysis,
    get_latest_analysis,
    get_requirement_template_fields,
    get_requirement_template_sample_rows,
    include_recommendation_in_local_items,
    parse_requirement_table,
    run_ai_recommendation,
    list_analyses,
    update_recommendation,
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


@router.post("/local", response_model=RequirementAnalysisRead)
def create_local(payload: RequirementAnalysisRequest, current_user: SeedUser = Depends(get_current_user)) -> RequirementAnalysisRead:
    if get_project_for_user(payload.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return create_local_analysis(payload.project_id, payload.description)


@router.get("/latest", response_model=RequirementAnalysisRead | None)
def latest(project_id: str, current_user: SeedUser = Depends(get_current_user)) -> RequirementAnalysisRead | None:
    if get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return get_latest_analysis(project_id)


@router.get("", response_model=list[RequirementAnalysisRead])
def list_project_analyses(project_id: str, current_user: SeedUser = Depends(get_current_user)) -> list[RequirementAnalysisRead]:
    if get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return list_analyses(project_id)


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_analysis(analysis_id: str, current_user: SeedUser = Depends(get_current_user)) -> Response:
    detail(analysis_id, current_user)
    if not delete_analysis(analysis_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{analysis_id}/ai-recommendations", response_model=RequirementAnalysisRead)
def create_ai_recommendations(analysis_id: str, current_user: SeedUser = Depends(get_current_user)) -> RequirementAnalysisRead:
    detail(analysis_id, current_user)
    analysis = run_ai_recommendation(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis


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


@router.post("/{analysis_id}/recommendations", response_model=RequirementAnalysisRead)
def create_recommendation(
    analysis_id: str,
    payload: RequirementRecommendationCreate,
    current_user: SeedUser = Depends(get_current_user),
) -> RequirementAnalysisRead:
    detail(analysis_id, current_user)
    analysis = add_recommendation(analysis_id, payload)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis


@router.patch("/{analysis_id}/recommendations/{recommendation_id}", response_model=RequirementAnalysisRead)
def patch_recommendation(
    analysis_id: str,
    recommendation_id: str,
    payload: RequirementRecommendationUpdate,
    current_user: SeedUser = Depends(get_current_user),
) -> RequirementAnalysisRead:
    detail(analysis_id, current_user)
    try:
        analysis = update_recommendation(analysis_id, recommendation_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    return analysis


@router.post("/{analysis_id}/recommendations/{recommendation_id}/include-local", response_model=RequirementAnalysisRead)
def include_local(
    analysis_id: str,
    recommendation_id: str,
    current_user: SeedUser = Depends(get_current_user),
) -> RequirementAnalysisRead:
    detail(analysis_id, current_user)
    analysis = include_recommendation_in_local_items(analysis_id, recommendation_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    return analysis


@router.delete("/{analysis_id}/recommendations/{recommendation_id}", response_model=RequirementAnalysisRead)
def remove_recommendation(
    analysis_id: str,
    recommendation_id: str,
    current_user: SeedUser = Depends(get_current_user),
) -> RequirementAnalysisRead:
    detail(analysis_id, current_user)
    analysis = delete_recommendation(analysis_id, recommendation_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    return analysis
