import uuid

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentUser, DbSession, rate_limit_ai
from app.schemas.ai_assistant import (
    AIStatusOut, ChatReplyOut, ConversationCreate, ConversationDetailOut, ConversationOut, MessageCreate, MessageOut,
)
from app.schemas.common import Message
from app.services import ai_service as svc

router = APIRouter(prefix="/ai", tags=["ai assistant"])


@router.get("/status", response_model=AIStatusOut)
def ai_status(user: CurrentUser):
    """Which provider is active, whether consent is needed, and what data is shared."""
    return svc.ai_status(user)


@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(data: ConversationCreate, user: CurrentUser, db: DbSession):
    return svc.create_conversation(db, user, data.title)


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(user: CurrentUser, db: DbSession):
    return svc.list_conversations(db, user)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(conversation_id: uuid.UUID, user: CurrentUser, db: DbSession):
    conv, msgs = svc.get_conversation(db, user, conversation_id)
    return ConversationDetailOut(id=conv.id, title=conv.title, created_at=conv.created_at, updated_at=conv.updated_at,
                                 messages=[MessageOut.model_validate(m) for m in msgs])


@router.post("/conversations/{conversation_id}/messages", response_model=ChatReplyOut,
             dependencies=[Depends(rate_limit_ai)])
def send_message(conversation_id: uuid.UUID, data: MessageCreate, user: CurrentUser, db: DbSession):
    result = svc.send_message(db, user, conversation_id, data.content)
    return ChatReplyOut(
        user_message=MessageOut.model_validate(result["user_message"]),
        assistant_message=MessageOut.model_validate(result["assistant_message"]),
        disclaimer=result["disclaimer"], data_used=result["data_used"], provider=result["provider"],
    )


@router.delete("/conversations/{conversation_id}", response_model=Message)
def delete_conversation(conversation_id: uuid.UUID, user: CurrentUser, db: DbSession):
    svc.delete_conversation(db, user, conversation_id)
    return Message(message="Conversation deleted")
