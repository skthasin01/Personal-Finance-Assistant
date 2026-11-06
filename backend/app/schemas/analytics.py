import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class PeriodTotals(BaseModel):
    start_date: date
    end_date: date
    income: Decimal
    gross_expense: Decimal
    refunds: Decimal
    expense: Decimal  # net expense = gross expense - refunds
    net_cash_flow: Decimal
    savings_rate: Decimal | None
    transaction_count: int


class SummaryOut(BaseModel):
    current: PeriodTotals
    previous: PeriodTotals
    income_change_percent: Decimal | None
    expense_change_percent: Decimal | None
    total_balance: Decimal
    currency_code: str
    has_data: bool


class TrendPoint(BaseModel):
    period: str
    start_date: date
    income: Decimal
    expense: Decimal
    net: Decimal


class TrendsOut(BaseModel):
    granularity: str
    points: list[TrendPoint]


class CategorySlice(BaseModel):
    category_id: uuid.UUID | None
    name: str
    color: str
    amount: Decimal
    percent: Decimal | None
    previous_amount: Decimal
    change_percent: Decimal | None


class CategoriesOut(BaseModel):
    type: str
    start_date: date
    end_date: date
    total: Decimal
    categories: list[CategorySlice]


class AccountFlow(BaseModel):
    account_id: uuid.UUID
    account_name: str
    inflow: Decimal
    outflow: Decimal
    transfers_in: Decimal
    transfers_out: Decimal
    net: Decimal


class CashFlowOut(BaseModel):
    start_date: date
    end_date: date
    income: Decimal
    expense: Decimal
    net_cash_flow: Decimal
    accounts: list[AccountFlow]
