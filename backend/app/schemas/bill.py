import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import PositiveMoney

BillType = Literal["electricity", "water", "gas", "internet", "rent", "mobile", "subscription", "custom"]
Recurrence = Literal["monthly", "quarterly", "yearly"]


class BillCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    bill_type: BillType
    category_id: uuid.UUID | None = None
    amount: PositiveMoney
    billing_period_start: date | None = None
    billing_period_end: date | None = None
    due_date: date
    recurrence_rule: Recurrence | None = None
    notes: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def period_order(self):
        if self.billing_period_start and self.billing_period_end and self.billing_period_end < self.billing_period_start:
            raise ValueError("billing_period_end must be on or after billing_period_start")
        return self


class BillUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    bill_type: BillType | None = None
    category_id: uuid.UUID | None = None
    amount: PositiveMoney | None = None
    billing_period_start: date | None = None
    billing_period_end: date | None = None
    due_date: date | None = None
    recurrence_rule: Recurrence | None = None
    notes: str | None = Field(default=None, max_length=255)
    status: Literal["pending", "cancelled"] | None = None


class BillPay(BaseModel):
    account_id: uuid.UUID
    paid_date: date | None = None
    category_id: uuid.UUID | None = None
    amount: PositiveMoney | None = Field(default=None, description="Defaults to the bill amount")


class BillComparison(BaseModel):
    previous_bill_id: uuid.UUID | None
    previous_amount: Decimal | None
    change_amount: Decimal | None
    change_percent: Decimal | None
    message: str


class BillOut(BaseModel):
    id: uuid.UUID
    title: str
    bill_type: str
    category_id: uuid.UUID | None
    amount: Decimal
    billing_period_start: date | None
    billing_period_end: date | None
    due_date: date
    status: str
    display_status: str  # pending | paid | overdue | cancelled
    days_until_due: int | None
    paid_at: datetime | None
    payment_transaction_id: uuid.UUID | None
    recurrence_rule: str | None
    notes: str | None
    comparison: BillComparison | None = None
