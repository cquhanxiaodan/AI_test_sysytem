from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.projects.service import get_project_for_user
from app.modules.risks.schemas import RiskBulkPublishRequest, RiskBulkPublishResponse, RiskItem, RiskParseRequest, RiskParseResponse, RiskUpdate
from app.modules.risks.service import delete_risk, get_risk, list_risks, parse_risks, publish_risk, update_risk

router = APIRouter(prefix="/risks", tags=["risks"])


@router.get("", response_model=list[RiskItem])
def risks(
    project_id: str | None = None,
    test_object: str | None = None,
    subsystem: str | None = None,
    source_type: str | None = None,
    current_user: SeedUser = Depends(get_current_user),
) -> list[RiskItem]:
    if project_id is not None and get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return list_risks(project_id, test_object, subsystem, source_type)


@router.post("/parse", response_model=RiskParseResponse)
def parse(payload: RiskParseRequest, current_user: SeedUser = Depends(get_current_user)) -> RiskParseResponse:
    if get_project_for_user(payload.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    items = parse_risks(payload.project_id, payload.source_type, payload.content)
    return RiskParseResponse(items=items)


@router.post("/bulk-publish", response_model=RiskBulkPublishResponse)
def bulk_publish_risks(payload: RiskBulkPublishRequest, current_user: SeedUser = Depends(get_current_user)) -> RiskBulkPublishResponse:
    published_ids: list[str] = []
    skipped: list[dict[str, str]] = []
    for risk_id in dict.fromkeys(payload.risk_ids):
        risk = get_risk(risk_id)
        if risk is None:
            skipped.append({"risk_id": risk_id, "reason": "风险知识项不存在"})
            continue
        if get_project_for_user(risk.project_id, current_user) is None:
            skipped.append({"risk_id": risk_id, "reason": "无项目访问权限"})
            continue
        if risk.status == "published":
            skipped.append({"risk_id": risk_id, "reason": "风险知识项已发布"})
            continue
        published = publish_risk(risk.id)
        if published is not None:
            published_ids.append(published.id)
    return RiskBulkPublishResponse(published_ids=published_ids, skipped=skipped)


@router.patch("/{risk_id}", response_model=RiskItem)
def update(risk_id: str, payload: RiskUpdate, current_user: SeedUser = Depends(get_current_user)) -> RiskItem:
    risk = get_risk(risk_id)
    if risk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk not found")
    if get_project_for_user(risk.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    updated = update_risk(risk_id, payload)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk not found")
    return updated


@router.delete("/{risk_id}")
def delete(risk_id: str, current_user: SeedUser = Depends(get_current_user)) -> dict[str, str]:
    risk = get_risk(risk_id)
    if risk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk not found")
    if get_project_for_user(risk.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    delete_risk(risk_id)
    return {"deleted_id": risk_id}
