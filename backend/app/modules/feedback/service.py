from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base, session_scope
from app.modules.auth.seed_data import SeedUser
from app.modules.feedback.schemas import FeedbackAdminUpdate, FeedbackCreate, FeedbackItem

FEEDBACK_ITEMS: dict[str, FeedbackItem] = {}


class FeedbackRecord(Base):
    __tablename__ = "feedback_items"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    submitter_id: Mapped[str] = mapped_column(String(80), index=True)
    submitter_name: Mapped[str] = mapped_column(String(120), index=True)
    submit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    feedback_type: Mapped[str] = mapped_column(String(80), index=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(80), index=True)
    admin_reply: Mapped[str] = mapped_column(Text, default="")
    replied_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def list_feedback(current_user: SeedUser) -> list[FeedbackItem]:
    items = _list_feedback()
    if "admin" not in current_user.roles:
        items = [item for item in items if item.submitter_id == current_user.id]
    return sorted(items, key=lambda item: item.submit_date, reverse=True)


def create_feedback(payload: FeedbackCreate, current_user: SeedUser) -> FeedbackItem:
    now = datetime.now(UTC)
    item = FeedbackItem(
        id=f"feedback-{uuid4()}",
        submitter_id=current_user.id,
        submitter_name=current_user.display_name,
        submit_date=now,
        feedback_type=payload.feedback_type,
        content=payload.content,
        status="pending",
        admin_reply="",
        replied_by=None,
        replied_at=None,
        updated_at=now,
    )
    _save_feedback(item)
    return item


def update_feedback(feedback_id: str, payload: FeedbackAdminUpdate, current_user: SeedUser) -> FeedbackItem | None:
    item = get_feedback(feedback_id)
    if item is None:
        return None
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return item
    now = datetime.now(UTC)
    if "admin_reply" in updates:
        updates["admin_reply"] = updates["admin_reply"] or ""
        updates["replied_by"] = current_user.display_name
        updates["replied_at"] = now
    updated = item.model_copy(update={**updates, "updated_at": now})
    _save_feedback(updated)
    return updated


def get_feedback(feedback_id: str) -> FeedbackItem | None:
    if _use_sqlalchemy():
        with session_scope() as session:
            record = session.get(FeedbackRecord, feedback_id)
            return _record_to_feedback(record) if record is not None else None
    return FEEDBACK_ITEMS.get(feedback_id)


def _list_feedback() -> list[FeedbackItem]:
    if _use_sqlalchemy():
        with session_scope() as session:
            records = session.scalars(select(FeedbackRecord)).all()
            return [_record_to_feedback(record) for record in records]
    return list(FEEDBACK_ITEMS.values())


def _save_feedback(item: FeedbackItem) -> None:
    if _use_sqlalchemy():
        with session_scope() as session:
            session.merge(_feedback_to_record(item))
        return
    FEEDBACK_ITEMS[item.id] = item


def _feedback_to_record(item: FeedbackItem) -> FeedbackRecord:
    return FeedbackRecord(
        id=item.id,
        submitter_id=item.submitter_id,
        submitter_name=item.submitter_name,
        submit_date=item.submit_date,
        feedback_type=item.feedback_type,
        content=item.content,
        status=item.status,
        admin_reply=item.admin_reply,
        replied_by=item.replied_by,
        replied_at=item.replied_at,
        updated_at=item.updated_at,
    )


def _record_to_feedback(record: FeedbackRecord) -> FeedbackItem:
    return FeedbackItem(
        id=record.id,
        submitter_id=record.submitter_id,
        submitter_name=record.submitter_name,
        submit_date=record.submit_date,
        feedback_type=record.feedback_type,
        content=record.content,
        status=record.status,
        admin_reply=record.admin_reply or "",
        replied_by=record.replied_by,
        replied_at=record.replied_at,
        updated_at=record.updated_at,
    )


def _use_sqlalchemy() -> bool:
    return get_settings().repository_backend == "sqlalchemy"
