"""Unit tests for the core money/percentage rules (written before AI features)."""
from datetime import date
from decimal import Decimal

from app.utils.date_utils import add_months, previous_period
from app.utils.financial_utils import change_percent, money, percent, savings_rate


def test_money_quantizes_half_up():
    assert money("10.005") == Decimal("10.01")
    assert money(Decimal("2")) == Decimal("2.00")
    assert money(None) == Decimal("0.00")


def test_savings_rate_zero_income_is_none():
    assert savings_rate(Decimal("0"), Decimal("500")) is None
    assert savings_rate(Decimal("1000"), Decimal("750")) == Decimal("25.0")
    assert savings_rate(Decimal("1000"), Decimal("1200")) == Decimal("-20.0")


def test_percent_zero_denominator_is_none():
    assert percent(Decimal("10"), Decimal("0")) is None
    assert percent(Decimal("1"), Decimal("3")) == Decimal("33.3")


def test_change_percent_needs_previous():
    assert change_percent(Decimal("120"), None) is None
    assert change_percent(Decimal("120"), Decimal("0")) is None
    assert change_percent(Decimal("120"), Decimal("100")) == Decimal("20.0")


def test_previous_period_month_and_custom():
    assert previous_period(date(2026, 3, 1), date(2026, 3, 31)) == (date(2026, 2, 1), date(2026, 2, 28))
    assert previous_period(date(2026, 1, 10), date(2026, 1, 19)) == (date(2025, 12, 31), date(2026, 1, 9))


def test_add_months_clamps_day():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 11, 15), 3) == date(2027, 2, 15)
