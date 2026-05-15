from fastapi import APIRouter, Depends, HTTPException, status

from pydantic import BaseModel

from app.modules.admin.schemas import AcceptanceStatus, AuditEvent, AuditEventCreate, SystemConfig, SystemConfigUpdate, ValidationPlanExportConfig
from app.modules.admin.service import create_audit_event, get_acceptance_status, get_config, get_validation_export_config, list_audit_events, restore_config_backup, save_validation_export_directory, update_config
from app.modules.auth.dependencies import get_current_user, require_admin
from app.modules.auth.seed_data import SeedUser

router = APIRouter(prefix="/admin", tags=["admin"])


class ValidationPlanExportConfigUpdate(BaseModel):
    export_directory: str = ""


@router.get("/config", response_model=SystemConfig)
def config(current_user: SeedUser = Depends(get_current_user)) -> SystemConfig:
    return get_config()


@router.put("/config", response_model=SystemConfig)
def update_system_config(payload: SystemConfigUpdate, current_user: SeedUser = Depends(require_admin)) -> SystemConfig:
    return update_config(payload)


@router.post("/config/restore-backup", response_model=SystemConfig)
def restore_system_config_backup(current_user: SeedUser = Depends(require_admin)) -> SystemConfig:
    restored = restore_config_backup()
    if restored is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System config backup not found")
    return restored


@router.get("/audits", response_model=list[AuditEvent])
def audits(current_user: SeedUser = Depends(require_admin)) -> list[AuditEvent]:
    return list_audit_events()


@router.post("/audits", response_model=AuditEvent)
def create_audit(payload: AuditEventCreate, current_user: SeedUser = Depends(get_current_user)) -> AuditEvent:
    return create_audit_event(current_user.id, payload.action, payload.target_type, payload.target_id, payload.detail)


@router.get("/acceptance-status", response_model=AcceptanceStatus)
def acceptance_status(current_user: SeedUser = Depends(get_current_user)) -> AcceptanceStatus:
    return get_acceptance_status()


@router.get("/validation-plan-export-config", response_model=ValidationPlanExportConfig)
def validation_export_config(current_user: SeedUser = Depends(get_current_user)) -> ValidationPlanExportConfig:
    return get_validation_export_config()


@router.put("/validation-plan-export-config", response_model=ValidationPlanExportConfig)
def update_validation_export_config(payload: ValidationPlanExportConfigUpdate, current_user: SeedUser = Depends(require_admin)) -> ValidationPlanExportConfig:
    return save_validation_export_directory(payload.export_directory)
