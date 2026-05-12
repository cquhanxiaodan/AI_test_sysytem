from datetime import UTC, datetime
from uuid import uuid4

from app.modules.test_items.service import list_test_items
from app.modules.test_packages.schemas import TestPackageAsset, TestPackageItem

TEST_PACKAGES: dict[str, TestPackageAsset] = {}


def list_packages(project_id: str | None = None) -> list[TestPackageAsset]:
    packages = list(TEST_PACKAGES.values())
    if project_id is not None:
        packages = [package for package in packages if package.project_id == project_id]
    return sorted(packages, key=lambda package: package.created_at, reverse=True)


def generate_rfid_supplier_change_package(project_id: str) -> TestPackageAsset:
    items = [item for item in list_test_items(project_id) if item.test_object == "RFID" or "安规" in item.title]
    package_items = [
        TestPackageItem(
            test_item_id=item.id,
            title=item.title,
            relation_type=relation_type_for_title(item.title),
            trigger_condition="涉及供应商、结构、标签材料或整机 EMC 风险变化时触发" if "安规" in item.title else None,
        )
        for item in items
    ]
    package = TestPackageAsset(
        id=f"pkg-{uuid4()}",
        project_id=project_id,
        name="RFID 供应商变更验证包",
        package_type="变更归口",
        test_object="RFID",
        change_type="供应商变更",
        applicable_scope="DNBSEQ-G99 RFID 二供或供应商切换验证",
        items=package_items,
        recommendation_level="high",
        status="draft",
        evidence="由 RFID 验证方案拆分条目自动归并生成。",
        created_at=datetime.now(UTC),
    )
    TEST_PACKAGES[package.id] = package
    return package


def publish_package(package_id: str) -> TestPackageAsset | None:
    package = TEST_PACKAGES.get(package_id)
    if package is None:
        return None
    updated = package.model_copy(update={"status": "published"})
    TEST_PACKAGES[package_id] = updated
    return updated


def relation_type_for_title(title: str) -> str:
    if "写入" in title:
        return "suggested"
    if "安规" in title or "EMC" in title:
        return "conditional"
    return "required"
