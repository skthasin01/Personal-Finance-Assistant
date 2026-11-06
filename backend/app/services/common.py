"""Ownership-scoped lookups shared by all services.

Every private record is fetched with BOTH its id and the authenticated user's id.
A record that exists but belongs to someone else raises NotFoundError (404), so
the API never reveals that another user's record exists.
"""
import uuid
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError

ModelT = TypeVar("ModelT")


def get_owned(db: Session, model: type[ModelT], record_id: uuid.UUID, user_id: uuid.UUID,
              label: str | None = None, for_update: bool = False) -> ModelT:
    stmt = select(model).where(model.id == record_id, model.user_id == user_id)
    if for_update:
        stmt = stmt.with_for_update()
    obj = db.scalars(stmt).first()
    if obj is None:
        raise NotFoundError(f"{label or model.__name__} not found")
    return obj


def clamp_page(page: int, page_size: int, max_page_size: int = 100) -> tuple[int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), max_page_size)
    return page, page_size
