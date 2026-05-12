from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.projects.dependencies import get_current_project
from app.modules.projects.schemas import ProjectRead
from app.modules.projects.service import list_projects_for_user

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(current_user: SeedUser = Depends(get_current_user)) -> list[ProjectRead]:
    return list_projects_for_user(current_user)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project: ProjectRead = Depends(get_current_project)) -> ProjectRead:
    return project
