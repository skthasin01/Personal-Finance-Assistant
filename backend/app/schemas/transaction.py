import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel, PositiveMoney


class TransactionCreate(BaseModel):
    """Create an income, expense, or refund. Transfers use TransferCreate."""

    transaction_type: Literal["income", "expense", "refund"]
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    amount: PositiveMoney
    transaction_date: date
    description: str | None = Field(default=None, max_length=255)
    # Required for refunds: the original expense being refunded
    related_transaction_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def check_shape(self):
        if self.transaction_type == "refund":
            if self.related_transaction_id is None:
                raise ValueError("A refund must reference the original expense (related_transaction_id)")
        else:
            if self.category_id is None:
                raise ValueError("category_id is required for income and expense")
            if self.related_transaction_id is not None:
                raise ValueError("Only refunds can reference another transaction")
        return self


class TransactionUpdate(BaseModel):
    """Type and transfer linkage cannot change; delete and recreate instead."""

    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    amount: PositiveMoney | None = None
    transaction_date: date | None = None
    description: str | None = Field(default=None, max_length=255)


class TransferCreate(BaseModel):
    from_account_id: uuid.UUID
    to_account_id: uuid.UUID
    amount: PositiveMoney
    transaction_date: date
    description: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def different_accounts(self):
        if self.from_account_id == self.to_account_id:
            raise ValueError("Source and destination accounts must be different")
        return self


class TransactionOut(ORMModel):
    id: uuid.UUID
    account_id: uuid.UUID
    account_name: str | None = None
    category_id: uuid.UUID | None
    category_name: str | None = None
    category_color: str | None = None
    transaction_type: str
    direction: str | None
    amount: Decimal
    description: str | None
    transaction_date: date
    related_transaction_id: uuid.UUID | None
    transfer_group_id: uuid.UUID | None
    counterpart_account_id: uuid.UUID | None = None
    counterpart_account_name: str | None = None
    refunded_amount: Decimal | None = None
    is_bill_payment: bool = False
    created_at: datetime


class TransferOut(BaseModel):
    transfer_group_id: uuid.UUID
    outgoing: TransactionOut
    incoming: TransactionOut
