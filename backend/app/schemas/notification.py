import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class NotificationOut(ORMModel):
    id: uuid.UUID
    title: str
    message: str
    notification_type: str
    related_record_type: str | None
    related_record_id: uuid.UUID | None
    is_read: bool
    created_at: datetime


class NotificationUpdate(BaseModel):
    is_read: bool


class InsightOut(ORMModel):
    id: uuid.UUID
    insight_type: str
    title: str
    content: str
    severity: str
    generated_at: datetime
    is_dismissed: bool


class InsightUpdate(BaseModel):
    is_dismissed: bool
