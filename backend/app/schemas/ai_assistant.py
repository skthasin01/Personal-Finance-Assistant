import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class MessageOut(ORMModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ConversationOut(ORMModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]


class ChatReplyOut(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    disclaimer: str
    data_used: list[str]
    provider: str


class AIStatusOut(BaseModel):
    provider: str
    external: bool
    consent_required: bool
    has_consent: bool
    data_shared_description: list[str]
