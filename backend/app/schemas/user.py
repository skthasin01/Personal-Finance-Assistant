import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel
from app.utils.date_utils import is_valid_timezone

SUPPORTED_CURRENCIES = {"BDT", "USD", "EUR", "GBP", "INR"}


class UserOut(ORMModel):
    id: uuid.UUID
    full_name: str
    email: str
    currency_code: str
    timezone: str
    is_active: bool
    is_demo: bool = False
    notify_bills: bool
    notify_budgets: bool
    notify_goals: bool
    budget_warning_threshold: int
    bill_reminder_days: int
    ai_consent: bool
    ai_consent_at: datetime | None
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    currency_code: str | None = None
    timezone: str | None = None
    notify_bills: bool | None = None
    notify_budgets: bool | None = None
    notify_goals: bool | None = None
    budget_warning_threshold: int | None = Field(default=None, ge=1, le=100)
    bill_reminder_days: int | None = Field(default=None, ge=0, le=30)
    ai_consent: bool | None = None

    @field_validator("currency_code")
    @classmethod
    def check_currency(cls, v):
        if v is not None and v.upper() not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Currency must be one of {sorted(SUPPORTED_CURRENCIES)}")
        return v.upper() if v else v

    @field_validator("timezone")
    @classmethod
    def check_tz(cls, v):
        if v is not None and not is_valid_timezone(v):
            raise ValueError("Unknown timezone")
        return v


class DeleteAccountIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)
