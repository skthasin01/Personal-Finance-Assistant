"""Shared schema types.

Money is exposed as Decimal; in JSON it is serialized as a string such as "1250.50"
so no precision is lost through floating point on the way to the browser.
"""
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# Positive money input with at most 12 integer digits and 2 decimal places (NUMERIC(14,2)).
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
NonNegativeMoney = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    pages: int


class Message(BaseModel):
    message: str


def page_count(total: int, page_size: int) -> int:
    return (total + page_size - 1) // page_size if total else 0
