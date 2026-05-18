from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def get_engine():
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///"):
        database_path = settings.database_url.removeprefix("sqlite:///")
        if database_path and database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database() -> None:
    from app.modules.documents.repository import DocumentRecord
    from app.modules.admin.service import AuditEventRecord, SystemConfigRecord
    from app.modules.ai.service import AiRunRecordModel
    from app.modules.parsing.service import DocumentChunkRecord, ParsingTaskRecord
    from app.modules.requirements.service import RequirementAnalysisRecord
    from app.modules.risks.service import RiskRecord
    from app.modules.test_items.service import TestItemRecord
    from app.modules.test_packages.service import TestPackageRecord
    from app.modules.validation_plans.service import ExportRecordModel, ValidationPlanRecord

    _ = (
        DocumentRecord,
        AuditEventRecord,
        SystemConfigRecord,
        AiRunRecordModel,
        DocumentChunkRecord,
        ParsingTaskRecord,
        RequirementAnalysisRecord,
        RiskRecord,
        TestItemRecord,
        TestPackageRecord,
        ExportRecordModel,
        ValidationPlanRecord,
    )
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    ensure_requirement_analysis_columns(engine)
    ensure_test_item_columns(engine)


def ensure_requirement_analysis_columns(engine) -> None:
    inspector = inspect(engine)
    if "requirement_analyses" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("requirement_analyses")}
    statements = []
    if "ai_status" not in existing_columns:
        statements.append("ALTER TABLE requirement_analyses ADD COLUMN ai_status VARCHAR(80) DEFAULT 'not_configured'")
    if "ai_message" not in existing_columns:
        statements.append("ALTER TABLE requirement_analyses ADD COLUMN ai_message VARCHAR(1000) DEFAULT 'AI 未配置，已使用本地规则推荐。'")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def ensure_test_item_columns(engine) -> None:
    inspector = inspect(engine)
    if "test_items" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("test_items")}
    statements = []
    if "connection_media" not in existing_columns:
        statements.append("ALTER TABLE test_items ADD COLUMN connection_media TEXT DEFAULT ''")
    if "module" not in existing_columns:
        statements.append("ALTER TABLE test_items ADD COLUMN module VARCHAR(120) DEFAULT ''")
    if "compliance_bug_info" not in existing_columns:
        statements.append("ALTER TABLE test_items ADD COLUMN compliance_bug_info TEXT DEFAULT ''")
    if "source_section_text" not in existing_columns:
        statements.append("ALTER TABLE test_items ADD COLUMN source_section_text TEXT DEFAULT ''")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
