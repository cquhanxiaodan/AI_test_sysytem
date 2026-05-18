from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    feedback_type: str = Field(pattern="^(bug|requirement)$")
    content: str = Field(min_length=1)


class FeedbackAdminUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(pending|processing|resolved|closed)$")
    admin_reply: str | None = None


class FeedbackItem(BaseModel):
    id: str
    submitter_id: str
    submitter_name: str
    submit_date: datetime
    feedback_type: str
    content: str
    status: str
    admin_reply: str
    replied_by: str | None = None
    replied_at: datetime | None = None
    updated_at: datetime
