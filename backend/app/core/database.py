from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def get_engine():
    settings = get_settings()
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
    from app.modules.admin.service import AuditEventRecord
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
    Base.metadata.create_all(bind=get_engine())
