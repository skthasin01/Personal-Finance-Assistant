import uuid
from typing import Literal

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import Message
from app.services import account_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(user: CurrentUser, db: DbSession, type: Literal["income", "expense"] | None = None,
                    include_inactive: bool = False):
    return account_service.list_categories(db, user, type, include_inactive)


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, user: CurrentUser, db: DbSession):
    return account_service.create_category(db, user, data)


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(category_id: uuid.UUID, data: CategoryUpdate, user: CurrentUser, db: DbSession):
    return account_service.update_category(db, user, category_id, data)


@router.delete("/{category_id}", response_model=Message)
def delete_category(category_id: uuid.UUID, user: CurrentUser, db: DbSession):
    return Message(message=account_service.delete_category(db, user, category_id))
