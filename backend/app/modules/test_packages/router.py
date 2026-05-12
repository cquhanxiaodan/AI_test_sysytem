from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.projects.service import get_project_for_user
from app.modules.test_packages.schemas import TestPackageAsset
from app.modules.test_packages.service import generate_rfid_supplier_change_package, list_packages, publish_package

router = APIRouter(prefix="/test-packages", tags=["test-packages"])


@router.get("", response_model=list[TestPackageAsset])
def packages(project_id: str | None = None, current_user: SeedUser = Depends(get_current_user)) -> list[TestPackageAsset]:
    if project_id is not None and get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return list_packages(project_id)


@router.post("/generate-rfid-supplier-change", response_model=TestPackageAsset)
def generate_package(project_id: str, current_user: SeedUser = Depends(get_current_user)) -> TestPackageAsset:
    if get_project_for_user(project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return generate_rfid_supplier_change_package(project_id)


@router.post("/{package_id}/publish", response_model=TestPackageAsset)
def publish(package_id: str, current_user: SeedUser = Depends(get_current_user)) -> TestPackageAsset:
    package = publish_package(package_id)
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test package not found")
    if get_project_for_user(package.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return package
