from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings
from app.core.database import Base, get_engine, init_database
from app.modules.documents.repository import create_document, get_document, get_document_content, list_documents
from app.modules.requirements.schemas import RequirementAnalysisRead, RequirementParseResult, RequirementRecommendation
from app.modules.requirements.service import ANALYSES
from app.modules.validation_plans.service import create_plan, export_plan, get_export, get_plan, list_plans


def configure_sqlite(tmp_path: Path) -> None:
    settings = get_settings()
    settings.repository_backend = "sqlalchemy"
    settings.storage_backend = "local"
    settings.database_url = f"sqlite:///{tmp_path / 'test.db'}"
    settings.local_storage_root = str(tmp_path / "storage")
    settings.validation_plan_template_path = str(tmp_path / "templates" / "validation-plan-v1.docx")
    Base.metadata.drop_all(bind=get_engine())
    init_database()


def restore_defaults() -> None:
    settings = get_settings()
    settings.repository_backend = "memory"
    settings.storage_backend = "local"
    settings.database_url = "postgresql+psycopg://app:app@postgres:5432/gene_test"
    settings.local_storage_root = "storage"
    settings.validation_plan_template_path = "templates/validation-plan-v1.docx"
    ANALYSES.clear()


def test_sqlalchemy_document_repository_round_trip(tmp_path: Path) -> None:
    configure_sqlite(tmp_path)
    try:
        document = create_document(
            project_id="project-g99-rfid",
            filename="RFID验证方案.txt",
            content_type="text/plain",
            content=b"RFID content",
            uploaded_by="user-admin",
        )

        persisted_document = get_document(document.id)
        assert persisted_document is not None
        assert persisted_document.id == document.id
        assert persisted_document.filename == "RFID验证方案.txt"
        assert list_documents("project-g99-rfid")[0].id == document.id
        assert get_document_content(document.id) == b"RFID content"
    finally:
        restore_defaults()


def test_sqlalchemy_validation_plan_repository_round_trip(tmp_path: Path) -> None:
    configure_sqlite(tmp_path)
    try:
        analysis = RequirementAnalysisRead(
            id="analysis-1",
            project_id="project-g99-rfid",
            description="DNBSEQ-G99 引入二供供应商康奈特 RFID",
            parse_result=RequirementParseResult(
                test_object="RFID",
                change_type="供应商变更",
                product_model="DNBSEQ-G99",
                subsystem="RFID",
                missing_fields=[],
            ),
            recommendations=[
                RequirementRecommendation(
                    group="必测",
                    title="RFID 在机读取测试",
                    source_type="test_item",
                    source_id="item-1",
                    reason="覆盖读取功能",
                    evidence="历史验证方案",
                )
            ],
            status="draft",
            created_at=datetime.now(UTC),
        )
        ANALYSES[analysis.id] = analysis

        plan = create_plan(analysis.id)
        assert plan is not None
        persisted_plan = get_plan(plan.id)
        assert persisted_plan is not None
        assert persisted_plan.id == plan.id
        assert persisted_plan.items[0].title == "RFID 在机读取测试"
        assert list_plans("project-g99-rfid")[0].id == plan.id

        export = export_plan(plan.id)
        assert export is not None
        persisted_export = get_export(export.id)
        assert persisted_export is not None
        assert persisted_export.id == export.id
        assert Path(export.storage_path).exists()
    finally:
        restore_defaults()
