from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.projects.dependencies import get_current_project
from app.modules.projects.schemas import ProjectCreateRequest, ProjectDeleteRequest, ProjectRead, ProjectWorkspaceStats
from app.modules.projects.service import create_project_for_user, delete_project_for_user, get_project_workspace_stats, list_projects_for_user

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(current_user: SeedUser = Depends(get_current_user)) -> list[ProjectRead]:
    return list_projects_for_user(current_user)


@router.post("", response_model=ProjectRead)
def create_project(payload: ProjectCreateRequest, current_user: SeedUser = Depends(get_current_user)) -> ProjectRead:
    if not payload.code.strip() or not payload.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="项目编码和名称不能为空")
    return create_project_for_user(payload, current_user)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, payload: ProjectDeleteRequest, current_user: SeedUser = Depends(get_current_user)) -> None:
    deleted = delete_project_for_user(project_id, current_user, payload.password)
    if deleted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if deleted is False:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="密码错误或无权删除项目空间")


@router.get("/{project_id}/workspace-stats", response_model=ProjectWorkspaceStats)
def workspace_stats(project_id: str, current_user: SeedUser = Depends(get_current_user)) -> ProjectWorkspaceStats:
    stats = get_project_workspace_stats(project_id, current_user)
    if stats is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return stats


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project: ProjectRead = Depends(get_current_project)) -> ProjectRead:
    return project
