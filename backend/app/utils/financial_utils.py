"""Money helpers. All money is Decimal, quantized to 2 places with ROUND_HALF_UP.

Rounding rule (documented): amounts are stored with 2 decimal places; computed
percentages are rounded to 1 decimal place; both use ROUND_HALF_UP.
"""
from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")
ONE_PLACE = Decimal("0.1")
ZERO = Decimal("0.00")


def money(value) -> Decimal:
    if value is None:
        return ZERO
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def percent(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    """numerator / denominator * 100, or None when denominator <= 0 (never infinity)."""
    if denominator is None or denominator <= 0:
        return None
    return (Decimal(numerator) / Decimal(denominator) * 100).quantize(ONE_PLACE, rounding=ROUND_HALF_UP)


def savings_rate(income: Decimal, expenses: Decimal) -> Decimal | None:
    """(income - expenses) / income * 100 when income > 0, else None."""
    if income <= 0:
        return None
    return percent(income - expenses, income)


def change_percent(current: Decimal, previous: Decimal | None) -> Decimal | None:
    """(current - previous) / previous * 100 when previous > 0, else None."""
    if previous is None or previous <= 0:
        return None
    return percent(current - previous, previous)


CURRENCY_SYMBOLS = {"BDT": "৳", "USD": "$", "EUR": "€", "GBP": "£", "INR": "₹"}


def fmt_money(value, currency: str = "BDT") -> str:
    """Human-readable money for server-generated text (insights, notifications)."""
    amount = money(value)
    sign = "-" if amount < 0 else ""
    return f"{sign}{CURRENCY_SYMBOLS.get(currency, currency + ' ')}{abs(amount):,.2f}"
