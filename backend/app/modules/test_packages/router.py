from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.seed_data import SeedUser
from app.modules.projects.service import get_project_for_user
from app.modules.test_packages.schemas import TestPackageAsset, TestPackageBulkPublishRequest, TestPackageBulkPublishResponse, TestPackageUpdate
from app.modules.test_packages.service import delete_package, generate_rfid_supplier_change_package, get_package, list_packages, publish_package, update_package

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


@router.post("/bulk-publish", response_model=TestPackageBulkPublishResponse)
def bulk_publish_packages(payload: TestPackageBulkPublishRequest, current_user: SeedUser = Depends(get_current_user)) -> TestPackageBulkPublishResponse:
    published_ids: list[str] = []
    skipped: list[dict[str, str]] = []
    for package_id in dict.fromkeys(payload.package_ids):
        package = get_package(package_id)
        if package is None:
            skipped.append({"package_id": package_id, "reason": "测试归口包不存在"})
            continue
        if get_project_for_user(package.project_id, current_user) is None:
            skipped.append({"package_id": package_id, "reason": "无项目访问权限"})
            continue
        if package.status == "published":
            skipped.append({"package_id": package_id, "reason": "测试归口包已发布"})
            continue
        published = publish_package(package.id)
        if published is not None:
            published_ids.append(published.id)
    return TestPackageBulkPublishResponse(published_ids=published_ids, skipped=skipped)


@router.post("/{package_id}/publish", response_model=TestPackageAsset)
def publish(package_id: str, current_user: SeedUser = Depends(get_current_user)) -> TestPackageAsset:
    package = publish_package(package_id)
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test package not found")
    if get_project_for_user(package.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    return package


@router.patch("/{package_id}", response_model=TestPackageAsset)
def update(package_id: str, payload: TestPackageUpdate, current_user: SeedUser = Depends(get_current_user)) -> TestPackageAsset:
    package = get_package(package_id)
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test package not found")
    if get_project_for_user(package.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    updated = update_package(package_id, payload)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test package not found")
    return updated


@router.delete("/{package_id}")
def delete(package_id: str, current_user: SeedUser = Depends(get_current_user)) -> dict[str, str]:
    package = get_package(package_id)
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test package not found")
    if get_project_for_user(package.project_id, current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
    delete_package(package_id)
    return {"deleted_id": package_id}
