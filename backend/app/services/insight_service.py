"""Rule-based financial insights computed from verified backend figures.

Each insight has a dedupe_key scoped to the month, so it is refreshed (not
duplicated) when figures change, and a dismissed insight stays dismissed.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.models.budget import Budget
from app.models.category import Category
from app.models.financial_insight import FinancialInsight
from app.models.user import User
from app.services import analytics_service, budget_service
from app.services.common import get_owned
from app.utils.financial_utils import fmt_money
from app.utils.date_utils import month_bounds, previous_period, today_for

MIN_CHANGE_PERCENT = Decimal("25")


def _upsert(db: Session, user: User, key: str, itype: str, title: str, content: str, severity: str) -> None:
    existing = db.scalars(select(FinancialInsight).where(FinancialInsight.user_id == user.id,
                                                         FinancialInsight.dedupe_key == key)).first()
    if existing:
        if not existing.is_dismissed:
            existing.title, existing.content, existing.severity = title, content, severity
            existing.generated_at = datetime.now(timezone.utc)
        return
    db.add(FinancialInsight(user_id=user.id, dedupe_key=key, insight_type=itype, title=title, content=content,
                            severity=severity))


def generate(db: Session, user: User) -> None:
    today = today_for(user.timezone)
    start, end = month_bounds(today.year, today.month)
    period = f"{today.year}-{today.month:02d}"
    cur = analytics_service.period_totals(db, user.id, start, end)
    active_keys: set[str] = set()

    def put(key, *args):
        active_keys.add(key)
        _upsert(db, user, key, *args)

    if cur.transaction_count == 0:
        put(f"no_data:{period}", "data_quality", "Not enough data yet",
            "No income or expenses are recorded for this month yet. Add transactions to get personalised insights.",
            "info")
    else:
        if cur.savings_rate is None and cur.expense > 0:
            put(f"no_income:{period}", "cash_flow", "No income recorded this month",
                f"You have {fmt_money(cur.expense, user.currency_code)} in expenses but no recorded income this month, so a savings rate "
                "cannot be calculated. If you received income, record it for accurate reports.", "warning")
        elif cur.savings_rate is not None and cur.savings_rate < 0:
            put(f"negative_cash_flow:{period}", "cash_flow", "Spending is higher than income",
                f"This month you spent {fmt_money(cur.expense, user.currency_code)} against {fmt_money(cur.income, user.currency_code)} income "
                f"(net {fmt_money(cur.net_cash_flow, user.currency_code)}). Review your largest categories below.", "critical")
        elif cur.savings_rate is not None and cur.savings_rate >= 20:
            put(f"good_savings:{period}", "savings", f"Savings rate is {cur.savings_rate}%",
                f"You kept {fmt_money(cur.net_cash_flow, user.currency_code)} of {fmt_money(cur.income, user.currency_code)} income this month. Consider moving part of it "
                "to a savings goal.", "positive")

        # Category changes vs previous month (only when previous data exists)
        p_start, p_end = previous_period(start, end)
        current = analytics_service.net_expense_by_category(db, user.id, start, end)
        previous = analytics_service.net_expense_by_category(db, user.id, p_start, p_end)
        cats = {c.id: c.name for c in db.scalars(select(Category).where(Category.user_id == user.id))}
        for cat_id, amount in current.items():
            prev = previous.get(cat_id, Decimal(0))
            if prev > 0 and amount > prev:
                change = (amount - prev) / prev * 100
                if change >= MIN_CHANGE_PERCENT:
                    name = cats.get(cat_id, "Uncategorized")
                    put(f"category_up:{cat_id}:{period}", "spending_change", f"{name} spending is up {change:.0f}%",
                        f"You spent {fmt_money(amount, user.currency_code)} on {name} so far this month vs {fmt_money(prev, user.currency_code)} last month.", "warning")
        if current:
            top_id = max(current, key=lambda k: current[k])
            if current[top_id] > 0 and cur.expense > 0:
                share = current[top_id] / cur.expense * 100
                put(f"top_category:{period}", "spending_pattern", f"Top spending: {cats.get(top_id, 'Uncategorized')}",
                    f"{cats.get(top_id, 'Uncategorized')} is {share:.0f}% of this month's net expenses "
                    f"({fmt_money(current[top_id], user.currency_code)} of {fmt_money(cur.expense, user.currency_code)}).", "info")

    budgets = db.scalars(select(Budget).where(Budget.user_id == user.id, Budget.month == today.month,
                                              Budget.year == today.year)).all()
    for b in budget_service.build_outputs(db, user, list(budgets)):
        name = "overall budget" if b.is_overall else f"{b.category_name} budget"
        if b.status == "exceeded":
            put(f"budget_exceeded:{b.id}", "budget", f"Over your {name}",
                f"Spent {fmt_money(b.spent_amount, user.currency_code)} against a limit of {fmt_money(b.limit_amount, user.currency_code)} ({b.utilization_percent}%).", "critical")
        elif b.status == "warning":
            put(f"budget_warning:{b.id}", "budget", f"{name.capitalize()} at {b.utilization_percent}%",
                f"{fmt_money(b.remaining_amount, user.currency_code)} remains for the rest of the month.", "warning")

    overdue = db.scalars(select(Bill).where(Bill.user_id == user.id, Bill.status == "pending",
                                            Bill.due_date < today)).all()
    if overdue:
        put(f"overdue_bills:{today.isoformat()}", "bills", f"{len(overdue)} overdue bill(s)",
            "Overdue: " + ", ".join(b.title for b in overdue[:5]) + ". Pay or update them to keep reports accurate.",
            "critical")

    # Remove stale, non-dismissed insights for this month that no longer apply.
    for ins in db.scalars(select(FinancialInsight).where(FinancialInsight.user_id == user.id,
                                                         FinancialInsight.is_dismissed.is_(False))):
        if ins.dedupe_key not in active_keys:
            db.delete(ins)
    db.commit()


def list_insights(db: Session, user: User, include_dismissed: bool = False) -> list[FinancialInsight]:
    generate(db, user)
    stmt = select(FinancialInsight).where(FinancialInsight.user_id == user.id)
    if not include_dismissed:
        stmt = stmt.where(FinancialInsight.is_dismissed.is_(False))
    order = {"critical": 0, "warning": 1, "info": 2, "positive": 3}
    return sorted(db.scalars(stmt), key=lambda i: (order.get(i.severity, 9), i.title))


def set_dismissed(db: Session, user: User, insight_id: uuid.UUID, dismissed: bool) -> FinancialInsight:
    ins = get_owned(db, FinancialInsight, insight_id, user.id, "Insight")
    ins.is_dismissed = dismissed
    ins.dismissed_at = datetime.now(timezone.utc) if dismissed else None
    db.commit()
    db.refresh(ins)
    return ins
