from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, Text, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.admin.service import get_config
from app.modules.test_items.service import build_test_item_deduplication_key, list_test_items
from app.modules.test_packages.schemas import TestPackageAsset, TestPackageItem, TestPackageUpdate

TEST_PACKAGES: dict[str, TestPackageAsset] = {}
RFID_SUPPLIER_PACKAGE_NAME = "RFID测试归口包"


class TestPackageRecord(Base):
    __tablename__ = "test_packages"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(500))
    package_type: Mapped[str] = mapped_column(String(120), index=True)
    test_object: Mapped[str] = mapped_column(String(120), index=True)
    subsystem: Mapped[str] = mapped_column(String(120), default="", index=True)
    module: Mapped[str] = mapped_column(String(120), default="", index=True)
    change_type: Mapped[str] = mapped_column(String(120), index=True)
    applicable_scope: Mapped[str] = mapped_column(String(1000))
    items: Mapped[list[dict]] = mapped_column(JSON)
    recommendation_level: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(80), index=True)
    evidence: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def list_packages(project_id: str | None = None) -> list[TestPackageAsset]:
    if _use_sqlalchemy():
        with session_scope() as session:
            statement = select(TestPackageRecord)
            if project_id is not None:
                statement = statement.where(TestPackageRecord.project_id == project_id)
            records = session.scalars(statement).all()
            packages = [_record_to_package(record) for record in records]
            return sorted(packages, key=lambda package: package.created_at, reverse=True)
    packages = list(TEST_PACKAGES.values())
    if project_id is not None:
        packages = [package for package in packages if package.project_id == project_id]
    return sorted(packages, key=lambda package: package.created_at, reverse=True)


def generate_rfid_supplier_change_package(project_id: str) -> TestPackageAsset:
    items = [item for item in list_test_items(project_id) if is_rfid_related_item(item)]
    package_items = deduplicate_package_items(
        [
            TestPackageItem(
                test_item_id=item.id,
                title=item.title,
                module=item.module,
                relation_type=relation_type_for_title(item.title),
                trigger_condition="涉及供应商、结构、标签材料或整机 EMC 风险变化时触发" if "安规" in item.title else None,
            )
            for item in items
        ]
    )
    package = TestPackageAsset(
        id=f"pkg-{uuid4()}",
        project_id=project_id,
        name=RFID_SUPPLIER_PACKAGE_NAME,
        package_type="变更归口",
        test_object="RFID",
        subsystem=normalize_package_subsystem("电子子系统"),
        module="RFID",
        change_type="供应商变更",
        applicable_scope="DNBSEQ-G99 RFID 二供或供应商切换验证",
        items=package_items,
        recommendation_level="high",
        status="draft",
        evidence="由 RFID 验证方案拆分条目自动归并生成。",
        created_at=datetime.now(UTC),
    )
    existing = find_rfid_package_for_project(project_id)
    if existing is not None:
        package = package.model_copy(update={"id": existing.id, "status": existing.status, "created_at": existing.created_at})
    _save_package(package)
    return package


def assign_item_to_package(item) -> TestPackageAsset:
    package_name = package_name_for_item(item)
    package = find_suitable_package_for_item(item, package_name)
    package_item = TestPackageItem(
        test_item_id=item.id,
        title=item.title,
        module=item.module or "",
        relation_type=relation_type_for_title(item.title),
        trigger_condition="涉及供应商、结构、标签材料或整机 EMC 风险变化时触发" if "安规" in item.title else None,
    )
    if package is None:
        package = create_package_for_item(item, package_name, package_item)
    else:
        package = package.model_copy(update={"items": upsert_package_item(package.items, package_item)})
    _save_package(package)
    return package


def package_name_for_item(item) -> str:
    if item.module:
        return f"{item.module}测试归口包"
    subsystem = item.primary_subsystem or "待确认子系统"
    return f"{subsystem}测试归口包"


def find_suitable_package_for_item(item, package_name: str) -> TestPackageAsset | None:
    module = item.module or ""
    subsystem = item.primary_subsystem or "待确认子系统"
    test_object = module or subsystem
    packages = list_packages()
    if module:
        matched = next((package for package in packages if package.module == module or package.test_object == module or module in package.name), None)
        if matched is not None:
            return matched
    if test_object == "RFID":
        matched = next((package for package in packages if package.test_object == "RFID" or "RFID" in package.name), None)
        if matched is not None:
            return matched
    return next(
        (
            package
            for package in packages
            if package.subsystem == subsystem or package.test_object == test_object
        ),
        None,
    ) or find_package_by_name(package_name)


def create_package_for_item(item, package_name: str, package_item: TestPackageItem) -> TestPackageAsset:
    test_object = item.module or item.primary_subsystem or "待确认对象"
    change_type = "供应商变更" if "供应商变更" in item.risk_tags or is_rfid_related_item(item) else "变更验证"
    return TestPackageAsset(
        id=f"pkg-{uuid4()}",
        project_id=item.project_id,
        name=package_name,
        package_type="变更归口",
        test_object=test_object,
        subsystem=normalize_package_subsystem(item.primary_subsystem or ""),
        module=item.module or "",
        change_type=change_type,
        applicable_scope=f"{test_object} {change_type}相关测试条目归口",
        items=[package_item],
        recommendation_level="high" if is_rfid_related_item(item) else "medium",
        status="draft",
        evidence="由已发布测试条目自动归并生成。",
        created_at=datetime.now(UTC),
    )


def upsert_package_item(items: list[TestPackageItem], package_item: TestPackageItem) -> list[TestPackageItem]:
    updated: list[TestPackageItem] = []
    replaced = False
    package_item_key = build_package_item_deduplication_key(package_item)
    for item in items:
        if item.test_item_id == package_item.test_item_id or build_package_item_deduplication_key(item) == package_item_key:
            updated.append(package_item)
            replaced = True
        else:
            updated.append(item)
    if not replaced:
        updated.append(package_item)
    return deduplicate_package_items(updated)


def deduplicate_package_items(items: list[TestPackageItem]) -> list[TestPackageItem]:
    deduplicated: list[TestPackageItem] = []
    seen_keys: set[str] = set()
    for item in items:
        item_key = build_package_item_deduplication_key(item)
        if item_key in seen_keys:
            continue
        seen_keys.add(item_key)
        deduplicated.append(item)
    return deduplicated


def build_package_item_deduplication_key(item: TestPackageItem) -> str:
    return build_test_item_deduplication_key(item.title, infer_package_item_module(item))


def infer_package_item_module(item: TestPackageItem) -> str:
    if item.module:
        return item.module
    if "RFID" in item.title.upper():
        return "RFID"
    return ""


def find_package_by_name(name: str) -> TestPackageAsset | None:
    normalized_name = normalize_package_name(name)
    return next((package for package in list_packages() if normalize_package_name(package.name) == normalized_name), None)


def find_package_by_project_and_name(project_id: str, name: str) -> TestPackageAsset | None:
    normalized_name = normalize_package_name(name)
    return next((package for package in list_packages(project_id) if normalize_package_name(package.name) == normalized_name), None)


def find_rfid_package_for_project(project_id: str) -> TestPackageAsset | None:
    packages = list_packages(project_id)
    return next(
        (
            package
            for package in packages
            if package.module == "RFID" or package.test_object == "RFID" or "RFID" in package.name
        ),
        None,
    )


def normalize_package_name(name: str) -> str:
    return "".join(name.lower().split())


def publish_package(package_id: str) -> TestPackageAsset | None:
    package = get_package(package_id)
    if package is None:
        return None
    updated = package.model_copy(update={"status": "published"})
    _save_package(updated)
    return updated


def update_package(package_id: str, payload: TestPackageUpdate) -> TestPackageAsset | None:
    package = get_package(package_id)
    if package is None:
        return None
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return package
    if "items" in updates:
        updates["items"] = [TestPackageItem(**item) for item in updates["items"]]
    if "subsystem" in updates:
        updates["subsystem"] = normalize_package_subsystem(updates["subsystem"] or "")
    if "module" in updates:
        updates["module"] = normalize_package_module(updates["module"] or "", updates.get("subsystem", package.subsystem))
    if "subsystem" in updates or "module" in updates:
        test_object = updates.get("module") or updates.get("subsystem") or package.test_object
        updates["test_object"] = test_object
        updates.setdefault("name", f"{test_object}测试归口包")
    updated = package.model_copy(update={**updates, "status": "draft" if package.status != "draft" else package.status})
    _save_package(updated)
    return updated


def delete_package(package_id: str) -> bool:
    if _use_sqlalchemy():
        with session_scope() as session:
            result = session.execute(delete(TestPackageRecord).where(TestPackageRecord.id == package_id))
            return (result.rowcount or 0) > 0
    return TEST_PACKAGES.pop(package_id, None) is not None


def get_package(package_id: str) -> TestPackageAsset | None:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.get(TestPackageRecord, package_id)
            return _record_to_package(record) if record is not None else None
    return TEST_PACKAGES.get(package_id)


def relation_type_for_title(title: str) -> str:
    if "写入" in title:
        return "suggested"
    if "安规" in title or "EMC" in title:
        return "conditional"
    return "required"


def is_rfid_related_item(item) -> bool:
    searchable = " ".join(
        [
            item.title,
            item.test_object,
            item.primary_subsystem,
            *item.related_subsystems,
            *item.risk_tags,
            item.objective,
            item.method,
            " ".join(item.steps),
            item.evidence,
        ]
    ).lower()
    return "rfid" in searchable or "安规" in item.title or "emc" in searchable


def _use_sqlalchemy() -> bool:
    return get_settings().repository_backend == "sqlalchemy"


def _save_package(package: TestPackageAsset) -> None:
    if _use_sqlalchemy():
        with session_scope() as session:
            session.merge(_package_to_record(package))
        return
    TEST_PACKAGES[package.id] = package


def _package_to_record(package: TestPackageAsset) -> TestPackageRecord:
    return TestPackageRecord(
        id=package.id,
        project_id=package.project_id,
        name=package.name,
        package_type=package.package_type,
        test_object=package.test_object,
        subsystem=package.subsystem,
        module=package.module,
        change_type=package.change_type,
        applicable_scope=package.applicable_scope,
        items=[item.model_dump() for item in package.items],
        recommendation_level=package.recommendation_level,
        status=package.status,
        evidence=package.evidence,
        created_at=package.created_at,
    )


def _record_to_package(record: TestPackageRecord) -> TestPackageAsset:
    return TestPackageAsset(
        id=record.id,
        project_id=record.project_id,
        name=record.name,
        package_type=record.package_type,
        test_object=record.test_object,
        subsystem=getattr(record, "subsystem", None) or infer_package_subsystem(record.test_object),
        module=getattr(record, "module", None) or infer_package_module(record.test_object),
        change_type=record.change_type,
        applicable_scope=record.applicable_scope,
        items=[TestPackageItem(**item) for item in (record.items or [])],
        recommendation_level=record.recommendation_level,
        status=record.status,
        evidence=record.evidence,
        created_at=record.created_at,
    )


def normalize_package_subsystem(value: str) -> str:
    config = get_config()
    if value in config.subsystem_catalog:
        return value
    if value in {"RFID", "电子子系统", "电子系统"}:
        return next((subsystem for subsystem in config.subsystem_catalog if "电子" in subsystem), value)
    return value


def normalize_package_module(value: str, subsystem: str = "") -> str:
    if not value:
        return ""
    config = get_config()
    candidates = config.subsystem_modules.get(subsystem, []) if subsystem else []
    all_modules = [module for modules in config.subsystem_modules.values() for module in modules]
    return value if value in candidates or value in all_modules else value


def infer_package_module(test_object: str) -> str:
    if test_object == "RFID":
        return "RFID"
    config = get_config()
    all_modules = [module for modules in config.subsystem_modules.values() for module in modules]
    return test_object if test_object in all_modules else ""


def infer_package_subsystem(test_object: str) -> str:
    config = get_config()
    if test_object in config.subsystem_catalog:
        return test_object
    if test_object == "RFID":
        return normalize_package_subsystem("电子子系统")
    for subsystem, modules in config.subsystem_modules.items():
        if test_object in modules:
            return subsystem
    return ""
