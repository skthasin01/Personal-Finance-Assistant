import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import NonNegativeMoney, ORMModel

AccountType = Literal["cash", "bank", "bkash", "nagad", "rocket", "card", "savings", "other"]


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    account_type: AccountType
    opening_balance: NonNegativeMoney = Decimal("0.00")
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    account_type: AccountType | None = None
    opening_balance: NonNegativeMoney | None = None
    is_active: bool | None = None


class AccountOut(ORMModel):
    id: uuid.UUID
    name: str
    account_type: str
    currency_code: str
    opening_balance: Decimal
    is_active: bool
    created_at: datetime
    current_balance: Decimal = Decimal("0.00")
