from fastapi import Depends, HTTPException, Path, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.projects.schemas import ProjectRead
from app.modules.projects.service import get_project_for_user


def get_current_project(
    project_id: str = Path(...),
    current_user: SeedUser = Depends(get_current_user),
) -> ProjectRead:
    project = get_project_for_user(project_id, current_user)
    if project is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return project
