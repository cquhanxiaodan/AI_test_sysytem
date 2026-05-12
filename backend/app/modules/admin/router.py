from fastapi import APIRouter, Depends

from app.modules.admin.schemas import AcceptanceStatus, AuditEvent, AuditEventCreate, SystemConfig
from app.modules.admin.service import create_audit_event, get_acceptance_status, get_config, list_audit_events
from app.modules.auth.dependencies import get_current_user, require_admin
from app.modules.auth.seed_data import SeedUser

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/config", response_model=SystemConfig)
def config(current_user: SeedUser = Depends(get_current_user)) -> SystemConfig:
    return get_config()


@router.get("/audits", response_model=list[AuditEvent])
def audits(current_user: SeedUser = Depends(require_admin)) -> list[AuditEvent]:
    return list_audit_events()


@router.post("/audits", response_model=AuditEvent)
def create_audit(payload: AuditEventCreate, current_user: SeedUser = Depends(get_current_user)) -> AuditEvent:
    return create_audit_event(current_user.id, payload.action, payload.target_type, payload.target_id, payload.detail)


@router.get("/acceptance-status", response_model=AcceptanceStatus)
def acceptance_status(current_user: SeedUser = Depends(get_current_user)) -> AcceptanceStatus:
    return get_acceptance_status()
