import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import PositiveMoney


class BudgetCreate(BaseModel):
    category_id: uuid.UUID | None = Field(default=None, description="Omit for the overall monthly budget")
    limit_amount: PositiveMoney
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)


class BudgetUpdate(BaseModel):
    limit_amount: PositiveMoney


class BudgetOut(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID | None
    category_name: str | None
    category_color: str | None
    is_overall: bool
    month: int
    year: int
    limit_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    utilization_percent: Decimal | None
    status: str  # ok | warning | exceeded
    warning_threshold: int
