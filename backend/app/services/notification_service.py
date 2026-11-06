"""Notification generation with de-duplication.

Notifications are generated on demand (when the user loads notifications or the
dashboard). Each event has a deterministic dedupe_key; UNIQUE(user_id, dedupe_key)
guarantees the same event is never notified twice, even under concurrency.
"""
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.models.budget import Budget
from app.models.notification import Notification
from app.models.savings_goal import SavingsGoal
from app.models.user import User
from app.schemas.common import Page, page_count
from app.services import budget_service, savings_service
from app.services.common import clamp_page, get_owned
from app.utils.financial_utils import fmt_money
from app.utils.date_utils import today_for

GOAL_MILESTONES = (25, 50, 75, 100)


def _add(db: Session, user: User, *, key: str, title: str, message: str, ntype: str,
         record_type: str | None = None, record_id: uuid.UUID | None = None) -> bool:
    if db.scalar(select(Notification.id).where(Notification.user_id == user.id, Notification.dedupe_key == key)):
        return False
    try:
        with db.begin_nested():
            db.add(Notification(user_id=user.id, dedupe_key=key, title=title[:160], message=message[:500],
                                notification_type=ntype, related_record_type=record_type, related_record_id=record_id))
        return True
    except IntegrityError:
        return False  # created concurrently by another request


def generate(db: Session, user: User) -> int:
    created = 0
    today = today_for(user.timezone)

    if user.notify_bills:
        bills = db.scalars(select(Bill).where(Bill.user_id == user.id, Bill.status == "pending")).all()
        for b in bills:
            days = (b.due_date - today).days
            if days < 0:
                created += _add(db, user, key=f"bill_overdue:{b.id}:{b.due_date}", ntype="bill_overdue",
                                title=f"Overdue: {b.title}",
                                message=f"{b.title} was due on {b.due_date.isoformat()} and is not marked paid.",
                                record_type="bill", record_id=b.id)
            elif days <= user.bill_reminder_days:
                when = "today" if days == 0 else f"in {days} day(s)"
                created += _add(db, user, key=f"bill_due:{b.id}:{b.due_date}", ntype="bill_due",
                                title=f"Bill due {when}: {b.title}",
                                message=f"{b.title} ({fmt_money(b.amount, user.currency_code)}) is due on {b.due_date.isoformat()}.",
                                record_type="bill", record_id=b.id)

    if user.notify_budgets:
        budgets = db.scalars(select(Budget).where(Budget.user_id == user.id, Budget.month == today.month,
                                                  Budget.year == today.year)).all()
        for out in budget_service.build_outputs(db, user, list(budgets)):
            name = "Overall budget" if out.is_overall else f"{out.category_name} budget"
            period = f"{out.year}-{out.month:02d}"
            if out.status == "exceeded":
                created += _add(db, user, key=f"budget_exceeded:{out.id}:{period}", ntype="budget_exceeded",
                                title=f"{name} exceeded",
                                message=f"You have spent {fmt_money(out.spent_amount, user.currency_code)} of {fmt_money(out.limit_amount, user.currency_code)} "
                                        f"({out.utilization_percent}%) for {period}.",
                                record_type="budget", record_id=out.id)
            if out.status in ("warning", "exceeded"):
                created += _add(db, user, key=f"budget_warning:{out.id}:{period}:{user.budget_warning_threshold}",
                                ntype="budget_warning", title=f"{name} at {out.utilization_percent}%",
                                message=f"You reached your {user.budget_warning_threshold}% warning threshold "
                                        f"({fmt_money(out.spent_amount, user.currency_code)} of {fmt_money(out.limit_amount, user.currency_code)}).",
                                record_type="budget", record_id=out.id)

    if user.notify_goals:
        goals = db.scalars(select(SavingsGoal).where(SavingsGoal.user_id == user.id,
                                                     SavingsGoal.status.in_(("active", "completed")))).all()
        for g in savings_service.to_out(db, user, list(goals)):
            pct = g.progress_percent or Decimal(0)
            for m in GOAL_MILESTONES:
                if pct >= m:
                    created += _add(db, user, key=f"goal_milestone:{g.id}:{m}", ntype="goal_milestone",
                                    title=f"{g.title}: {m}% reached" if m < 100 else f"Goal reached: {g.title}",
                                    message=f"You have saved {fmt_money(g.saved_amount, user.currency_code)} of {fmt_money(g.target_amount, user.currency_code)}.",
                                    record_type="savings_goal", record_id=g.id)
    db.commit()
    return created


def list_notifications(db: Session, user: User, *, unread_only: bool = False, page: int = 1,
                       page_size: int = 20) -> tuple[Page, int]:
    generate(db, user)
    page, page_size = clamp_page(page, page_size)
    conds = [Notification.user_id == user.id]
    if unread_only:
        conds.append(Notification.is_read.is_(False))
    total = db.scalar(select(func.count()).select_from(Notification).where(*conds)) or 0
    unread = db.scalar(select(func.count()).select_from(Notification).where(
        Notification.user_id == user.id, Notification.is_read.is_(False))) or 0
    items = db.scalars(select(Notification).where(*conds).order_by(Notification.created_at.desc())
                       .offset((page - 1) * page_size).limit(page_size)).all()
    return Page(items=list(items), page=page, page_size=page_size, total=total, pages=page_count(total, page_size)), unread


def mark(db: Session, user: User, notification_id: uuid.UUID, is_read: bool) -> Notification:
    n = get_owned(db, Notification, notification_id, user.id, "Notification")
    n.is_read = is_read
    db.commit()
    db.refresh(n)
    return n


def mark_all_read(db: Session, user: User) -> None:
    for n in db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False))):
        n.is_read = True
    db.commit()
