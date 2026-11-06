"""Authoritative financial calculations (the LLM never computes these).

Definitions used everywhere (dashboard, budgets, reports, AI context):
    income         = sum of income transactions in the period
    gross expense  = sum of expense transactions in the period
    refunds        = sum of refunds dated in the period (they reduce expense)
    expense (net)  = gross expense - refunds
    net cash flow  = income - net expense      (transfers excluded)
    savings rate   = net cash flow / income * 100, or None when income is 0
"""
import csv
import io
import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationAppError
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.analytics import (
    AccountFlow, CashFlowOut, CategoriesOut, CategorySlice, PeriodTotals, SummaryOut, TrendPoint, TrendsOut,
)
from app.services.transaction_service import account_balances
from app.utils.date_utils import month_bounds, previous_period, today_for, week_start
from app.utils.financial_utils import ZERO, change_percent, money, percent, savings_rate

MAX_RANGE_DAYS = 366 * 5


def resolve_period(user: User, start: date | None, end: date | None) -> tuple[date, date]:
    """Default period: the current calendar month in the user's timezone."""
    if start is None and end is None:
        today = today_for(user.timezone)
        return month_bounds(today.year, today.month)
    if start is None or end is None:
        raise ValidationAppError("Provide both start_date and end_date")
    if end < start:
        raise ValidationAppError("end_date must be on or after start_date")
    if (end - start).days > MAX_RANGE_DAYS:
        raise ValidationAppError("Date range is too large (max 5 years)")
    return start, end


def _type_sums(db: Session, user_id: uuid.UUID, start: date, end: date) -> dict[str, tuple[Decimal, int]]:
    rows = db.execute(
        select(Transaction.transaction_type, func.coalesce(func.sum(Transaction.amount), 0), func.count())
        .where(Transaction.user_id == user_id, Transaction.transaction_date.between(start, end),
               Transaction.transaction_type != "transfer")
        .group_by(Transaction.transaction_type)
    ).all()
    return {t: (money(s), c) for t, s, c in rows}


def period_totals(db: Session, user_id: uuid.UUID, start: date, end: date) -> PeriodTotals:
    sums = _type_sums(db, user_id, start, end)
    income = sums.get("income", (ZERO, 0))[0]
    gross = sums.get("expense", (ZERO, 0))[0]
    refunds = sums.get("refund", (ZERO, 0))[0]
    expense = money(gross - refunds)
    return PeriodTotals(
        start_date=start, end_date=end, income=income, gross_expense=gross, refunds=refunds, expense=expense,
        net_cash_flow=money(income - expense), savings_rate=savings_rate(income, expense),
        transaction_count=sum(c for _, c in sums.values()),
    )


def net_expense_by_category(db: Session, user_id: uuid.UUID, start: date, end: date) -> dict[uuid.UUID | None, Decimal]:
    rows = db.execute(
        select(Transaction.category_id, Transaction.transaction_type, func.sum(Transaction.amount))
        .where(Transaction.user_id == user_id, Transaction.transaction_date.between(start, end),
               Transaction.transaction_type.in_(("expense", "refund")))
        .group_by(Transaction.category_id, Transaction.transaction_type)
    ).all()
    result: dict = defaultdict(lambda: ZERO)
    for cat_id, tx_type, total in rows:
        result[cat_id] += money(total) if tx_type == "expense" else -money(total)
    return dict(result)


def income_by_category(db: Session, user_id: uuid.UUID, start: date, end: date) -> dict[uuid.UUID | None, Decimal]:
    rows = db.execute(
        select(Transaction.category_id, func.sum(Transaction.amount))
        .where(Transaction.user_id == user_id, Transaction.transaction_date.between(start, end),
               Transaction.transaction_type == "income")
        .group_by(Transaction.category_id)
    ).all()
    return {cat_id: money(total) for cat_id, total in rows}


def summary(db: Session, user: User, start: date | None, end: date | None) -> SummaryOut:
    start, end = resolve_period(user, start, end)
    current = period_totals(db, user.id, start, end)
    p_start, p_end = previous_period(start, end)
    previous = period_totals(db, user.id, p_start, p_end)
    balances = account_balances(db, user.id)
    active_ids = set(db.scalars(select(Account.id).where(Account.user_id == user.id, Account.is_active)))
    total_balance = money(sum((b for a, b in balances.items() if a in active_ids), ZERO))
    return SummaryOut(
        current=current, previous=previous,
        income_change_percent=change_percent(current.income, previous.income),
        expense_change_percent=change_percent(current.expense, previous.expense),
        total_balance=total_balance, currency_code=user.currency_code,
        has_data=current.transaction_count > 0,
    )


def _bucket(d: date, granularity: str, period_start: date) -> tuple[str, date]:
    """Bucket label/start for a date. Partial first buckets are clamped to the
    period start so no label falls outside the requested range."""
    if granularity == "day":
        return d.isoformat(), d
    if granularity == "week":
        ws = max(week_start(d), period_start)
        return f"Week of {ws.isoformat()}", ws
    ms = max(date(d.year, d.month, 1), period_start)
    return f"{d.year}-{d.month:02d}", ms


def trends(db: Session, user: User, start: date | None, end: date | None, granularity: str = "month",
           months: int = 6) -> TrendsOut:
    if granularity not in ("day", "week", "month"):
        raise ValidationAppError("granularity must be day, week or month")
    if start is None and end is None:
        today = today_for(user.timezone)
        if granularity == "month":
            first = date(today.year, today.month, 1)
            for _ in range(max(months, 1) - 1):
                first = (first - timedelta(days=1)).replace(day=1)
            start, end = first, month_bounds(today.year, today.month)[1]
        else:
            days = 30 if granularity == "day" else 84
            start, end = today - timedelta(days=days - 1), today
    start, end = resolve_period(user, start, end)

    rows = db.execute(
        select(Transaction.transaction_date, Transaction.transaction_type, func.sum(Transaction.amount))
        .where(Transaction.user_id == user.id, Transaction.transaction_date.between(start, end),
               Transaction.transaction_type != "transfer")
        .group_by(Transaction.transaction_date, Transaction.transaction_type)
    ).all()

    # Pre-create every bucket so the chart has continuous points (zeros included).
    buckets: dict[str, dict] = {}
    cursor = start
    while cursor <= end:
        label, b_start = _bucket(cursor, granularity, start)
        buckets.setdefault(label, {"start": b_start, "income": ZERO, "expense": ZERO})
        cursor += timedelta(days=1)
    for d, tx_type, total in rows:
        label, _ = _bucket(d, granularity, start)
        if tx_type == "income":
            buckets[label]["income"] += money(total)
        elif tx_type == "expense":
            buckets[label]["expense"] += money(total)
        elif tx_type == "refund":
            buckets[label]["expense"] -= money(total)
    points = [
        TrendPoint(period=label, start_date=v["start"], income=money(v["income"]), expense=money(v["expense"]),
                   net=money(v["income"] - v["expense"]))
        for label, v in buckets.items()
    ]
    return TrendsOut(granularity=granularity, points=points)


def categories(db: Session, user: User, start: date | None, end: date | None, tx_type: str = "expense") -> CategoriesOut:
    if tx_type not in ("income", "expense"):
        raise ValidationAppError("type must be income or expense")
    start, end = resolve_period(user, start, end)
    p_start, p_end = previous_period(start, end)
    fn = net_expense_by_category if tx_type == "expense" else income_by_category
    current = fn(db, user.id, start, end)
    previous = fn(db, user.id, p_start, p_end)
    cats = {c.id: c for c in db.scalars(select(Category).where(Category.user_id == user.id))}
    total = money(sum((v for v in current.values() if v > 0), ZERO))
    slices = []
    for cat_id, amount in current.items():
        if amount <= 0:
            continue
        cat = cats.get(cat_id)
        prev = previous.get(cat_id, ZERO)
        slices.append(CategorySlice(
            category_id=cat_id, name=cat.name if cat else "Uncategorized", color=cat.color if cat else "#94a3b8",
            amount=money(amount), percent=percent(amount, total), previous_amount=money(max(prev, ZERO)),
            change_percent=change_percent(amount, prev),
        ))
    slices.sort(key=lambda s: s.amount, reverse=True)
    return CategoriesOut(type=tx_type, start_date=start, end_date=end, total=total, categories=slices)


def cash_flow(db: Session, user: User, start: date | None, end: date | None) -> CashFlowOut:
    start, end = resolve_period(user, start, end)
    totals = period_totals(db, user.id, start, end)
    rows = db.execute(
        select(Transaction.account_id, Transaction.transaction_type, Transaction.direction, func.sum(Transaction.amount))
        .where(Transaction.user_id == user.id, Transaction.transaction_date.between(start, end))
        .group_by(Transaction.account_id, Transaction.transaction_type, Transaction.direction)
    ).all()
    flows: dict = defaultdict(lambda: {"inflow": ZERO, "outflow": ZERO, "tin": ZERO, "tout": ZERO})
    for acc_id, tx_type, direction, total in rows:
        f = flows[acc_id]
        amt = money(total)
        if tx_type in ("income", "refund"):
            f["inflow"] += amt
        elif tx_type == "expense":
            f["outflow"] += amt
        elif direction == "in":
            f["tin"] += amt
        else:
            f["tout"] += amt
    accounts = db.scalars(select(Account).where(Account.user_id == user.id).order_by(Account.name)).all()
    out = []
    for a in accounts:
        f = flows.get(a.id)
        if not f and not a.is_active:
            continue
        f = f or {"inflow": ZERO, "outflow": ZERO, "tin": ZERO, "tout": ZERO}
        out.append(AccountFlow(
            account_id=a.id, account_name=a.name, inflow=money(f["inflow"]), outflow=money(f["outflow"]),
            transfers_in=money(f["tin"]), transfers_out=money(f["tout"]),
            net=money(f["inflow"] - f["outflow"] + f["tin"] - f["tout"]),
        ))
    return CashFlowOut(start_date=start, end_date=end, income=totals.income, expense=totals.expense,
                       net_cash_flow=totals.net_cash_flow, accounts=out)


def _safe_csv(value) -> str:
    """Neutralize spreadsheet formula injection (=, +, -, @ at the start)."""
    s = "" if value is None else str(value)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def export_csv(db: Session, user: User, start: date | None, end: date | None) -> str:
    start, end = resolve_period(user, start, end)
    totals = period_totals(db, user.id, start, end)
    accounts = {a.id: a.name for a in db.scalars(select(Account).where(Account.user_id == user.id))}
    cats = {c.id: c.name for c in db.scalars(select(Category).where(Category.user_id == user.id))}
    txs = db.scalars(
        select(Transaction).where(Transaction.user_id == user.id, Transaction.transaction_date.between(start, end))
        .order_by(Transaction.transaction_date, Transaction.created_at)
    ).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Report", "Personal finance summary"])
    w.writerow(["Period", start.isoformat(), end.isoformat()])
    w.writerow(["Currency", user.currency_code])
    w.writerow(["Income", totals.income])
    w.writerow(["Gross expense", totals.gross_expense])
    w.writerow(["Refunds", totals.refunds])
    w.writerow(["Net expense", totals.expense])
    w.writerow(["Net cash flow", totals.net_cash_flow])
    w.writerow(["Savings rate %", totals.savings_rate if totals.savings_rate is not None else "n/a"])
    w.writerow([])
    w.writerow(["Date", "Type", "Direction", "Account", "Category", "Amount", "Description"])
    for t in txs:
        w.writerow([t.transaction_date.isoformat(), t.transaction_type, t.direction or "", _safe_csv(accounts.get(t.account_id)),
                    _safe_csv(cats.get(t.category_id, "")), money(t.amount), _safe_csv(t.description)])
    return buf.getvalue()
