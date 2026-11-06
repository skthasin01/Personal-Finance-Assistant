import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel, PositiveMoney


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    target_amount: PositiveMoney
    target_date: date | None = None


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    target_amount: PositiveMoney | None = None
    target_date: date | None = None
    status: Literal["active", "completed", "cancelled"] | None = None


class ContributionCreate(BaseModel):
    amount: PositiveMoney
    contribution_date: date
    note: str | None = Field(default=None, max_length=255)
    # Optional: also record the real money movement as a transfer between two
    # of the user's accounts (e.g. bank -> savings). Never recorded as an expense.
    from_account_id: uuid.UUID | None = None
    to_account_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def both_or_neither(self):
        if (self.from_account_id is None) != (self.to_account_id is None):
            raise ValueError("Provide both from_account_id and to_account_id, or neither")
        if self.from_account_id and self.from_account_id == self.to_account_id:
            raise ValueError("Source and destination accounts must be different")
        return self


class ContributionOut(ORMModel):
    id: uuid.UUID
    goal_id: uuid.UUID
    amount: Decimal
    contribution_date: date
    note: str | None
    related_transaction_id: uuid.UUID | None
    created_at: datetime


class GoalProjection(BaseModel):
    remaining_amount: Decimal
    months_left: int | None
    required_monthly: Decimal | None
    average_monthly_contribution: Decimal | None
    on_track: bool | None
    explanation: str


class GoalOut(BaseModel):
    id: uuid.UUID
    title: str
    target_amount: Decimal
    target_date: date | None
    status: str
    saved_amount: Decimal
    progress_percent: Decimal | None  # display value, capped at 100
    contribution_count: int
    projection: GoalProjection
    created_at: datetime


class GoalDetailOut(GoalOut):
    contributions: list[ContributionOut]
