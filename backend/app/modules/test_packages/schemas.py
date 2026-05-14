from datetime import datetime

from pydantic import BaseModel


class TestPackageItem(BaseModel):
    test_item_id: str
    title: str
    relation_type: str
    trigger_condition: str | None = None


class TestPackageAsset(BaseModel):
    id: str
    project_id: str
    name: str
    package_type: str
    test_object: str
    change_type: str
    applicable_scope: str
    items: list[TestPackageItem]
    recommendation_level: str
    status: str
    evidence: str
    created_at: datetime


class TestPackageUpdate(BaseModel):
    name: str | None = None
    package_type: str | None = None
    test_object: str | None = None
    change_type: str | None = None
    applicable_scope: str | None = None
    items: list[TestPackageItem] | None = None
    recommendation_level: str | None = None
    evidence: str | None = None


class TestPackageBulkPublishRequest(BaseModel):
    package_ids: list[str]


class TestPackageBulkPublishResponse(BaseModel):
    published_ids: list[str]
    skipped: list[dict[str, str]]
