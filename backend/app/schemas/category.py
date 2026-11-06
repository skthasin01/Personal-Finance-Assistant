import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    type: Literal["income", "expense"]
    icon: str | None = Field(default=None, max_length=40)
    color: str = Field(default="#64748b", pattern=HEX_COLOR)


class CategoryUpdate(BaseModel):
    """Type cannot be changed: existing transactions depend on it."""

    name: str | None = Field(default=None, min_length=1, max_length=60)
    icon: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, pattern=HEX_COLOR)
    is_active: bool | None = None


class CategoryOut(ORMModel):
    id: uuid.UUID
    name: str
    type: str
    icon: str | None
    color: str
    is_default: bool
    is_active: bool
