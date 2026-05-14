from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.test_items.service import list_test_items
from app.modules.test_packages.schemas import TestPackageAsset, TestPackageItem

TEST_PACKAGES: dict[str, TestPackageAsset] = {}


class TestPackageRecord(Base):
    __tablename__ = "test_packages"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(500))
    package_type: Mapped[str] = mapped_column(String(120), index=True)
    test_object: Mapped[str] = mapped_column(String(120), index=True)
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
    _save_package(package)
    return package


def publish_package(package_id: str) -> TestPackageAsset | None:
    package = get_package(package_id)
    if package is None:
        return None
    updated = package.model_copy(update={"status": "published"})
    _save_package(updated)
    return updated


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
        change_type=record.change_type,
        applicable_scope=record.applicable_scope,
        items=[TestPackageItem(**item) for item in (record.items or [])],
        recommendation_level=record.recommendation_level,
        status=record.status,
        evidence=record.evidence,
        created_at=record.created_at,
    )
