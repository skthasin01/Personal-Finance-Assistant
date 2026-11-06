import uuid

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.common import Message
from app.schemas.notification import NotificationOut, NotificationUpdate
from app.services import notification_service as svc

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    page: int
    page_size: int
    total: int
    pages: int
    unread_count: int


@router.get("", response_model=NotificationPage)
def list_notifications(user: CurrentUser, db: DbSession, unread_only: bool = False,
                       page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    result, unread = svc.list_notifications(db, user, unread_only=unread_only, page=page, page_size=page_size)
    return NotificationPage(items=[NotificationOut.model_validate(n) for n in result.items], page=result.page,
                            page_size=result.page_size, total=result.total, pages=result.pages, unread_count=unread)


@router.post("/mark-all-read", response_model=Message)
def mark_all_read(user: CurrentUser, db: DbSession):
    svc.mark_all_read(db, user)
    return Message(message="All notifications marked as read")


@router.patch("/{notification_id}", response_model=NotificationOut)
def update_notification(notification_id: uuid.UUID, data: NotificationUpdate, user: CurrentUser, db: DbSession):
    return svc.mark(db, user, notification_id, data.is_read)
