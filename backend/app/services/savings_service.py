"""Savings goals. Progress is ALWAYS derived from the contribution ledger.

goal progress % = sum(contributions) / target * 100, displayed capped at 100,
while saved_amount keeps the real (possibly larger) total.
"""
import math
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.savings_goal import GoalContribution, SavingsGoal
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.savings_goal import (
    ContributionCreate, ContributionOut, GoalCreate, GoalDetailOut, GoalOut, GoalProjection, GoalUpdate,
)
from app.schemas.transaction import TransferCreate
from app.services.common import get_owned
from app.services.transaction_service import create_transfer
from app.utils.date_utils import today_for
from app.utils.financial_utils import ZERO, money, percent


def saved_totals(db: Session, user_id: uuid.UUID, goal_ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[Decimal, int]]:
    if not goal_ids:
        return {}
    rows = db.execute(
        select(GoalContribution.goal_id, func.coalesce(func.sum(GoalContribution.amount), 0), func.count())
        .where(GoalContribution.user_id == user_id, GoalContribution.goal_id.in_(goal_ids))
        .group_by(GoalContribution.goal_id)
    ).all()
    return {gid: (money(total), count) for gid, total, count in rows}


def _months_between(start: date, end: date) -> int:
    """Whole months remaining, rounding a partial month up (at least 1 if end is in the future)."""
    if end <= start:
        return 0
    return max(1, math.ceil((end - start).days / 30.4375))


def projection(db: Session, goal: SavingsGoal, saved: Decimal, today: date) -> GoalProjection:
    remaining = money(max(Decimal(goal.target_amount) - saved, ZERO))
    window_start = today - timedelta(days=90)
    recent = money(db.scalar(
        select(func.coalesce(func.sum(GoalContribution.amount), 0))
        .where(GoalContribution.goal_id == goal.id, GoalContribution.contribution_date > window_start)
    ))
    first = db.scalar(select(func.min(GoalContribution.contribution_date)).where(GoalContribution.goal_id == goal.id))
    avg_monthly = None
    if first is not None:
        months_observed = max(1, min(3, math.ceil((today - max(first, window_start)).days / 30.4375) or 1))
        avg_monthly = money(recent / months_observed)

    if remaining == 0:
        return GoalProjection(remaining_amount=remaining, months_left=0, required_monthly=ZERO,
                              average_monthly_contribution=avg_monthly, on_track=True,
                              explanation="Target reached. Contributions above the target are kept in the total.")
    if goal.target_date is None:
        expl = "No target date set, so a required monthly amount cannot be calculated."
        if avg_monthly and avg_monthly > 0:
            months = math.ceil(remaining / avg_monthly)
            expl += f" At your recent average of {avg_monthly} per month, you would reach it in about {months} month(s)."
        return GoalProjection(remaining_amount=remaining, months_left=None, required_monthly=None,
                              average_monthly_contribution=avg_monthly, on_track=None, explanation=expl)

    months_left = _months_between(today, goal.target_date)
    if months_left == 0:
        return GoalProjection(remaining_amount=remaining, months_left=0, required_monthly=remaining,
                              average_monthly_contribution=avg_monthly, on_track=False,
                              explanation="The target date has passed and the goal is not yet reached.")
    required = money(remaining / months_left)
    if avg_monthly is None:
        on_track, expl = None, (f"You need about {required} per month for {months_left} month(s). "
                                "No contributions yet, so on-track status is not available.")
    else:
        on_track = avg_monthly >= required
        expl = (f"You need about {required} per month for {months_left} month(s). Your average over the last "
                f"3 months (or since your first contribution) is {avg_monthly} per month. "
                "Assumes equal monthly contributions from today until the target date.")
    return GoalProjection(remaining_amount=remaining, months_left=months_left, required_monthly=required,
                          average_monthly_contribution=avg_monthly, on_track=on_track, explanation=expl)


def to_out(db: Session, user: User, goals: list[SavingsGoal]) -> list[GoalOut]:
    totals = saved_totals(db, user.id, [g.id for g in goals])
    today = today_for(user.timezone)
    out = []
    for g in goals:
        saved, count = totals.get(g.id, (ZERO, 0))
        pct = percent(saved, Decimal(g.target_amount))
        out.append(GoalOut(
            id=g.id, title=g.title, target_amount=money(g.target_amount), target_date=g.target_date, status=g.status,
            saved_amount=saved, progress_percent=min(pct, Decimal("100.0")) if pct is not None else None,
            contribution_count=count, projection=projection(db, g, saved, today), created_at=g.created_at,
        ))
    return out


def list_goals(db: Session, user: User, status: str | None = None) -> list[GoalOut]:
    stmt = select(SavingsGoal).where(SavingsGoal.user_id == user.id)
    if status:
        stmt = stmt.where(SavingsGoal.status == status)
    return to_out(db, user, list(db.scalars(stmt.order_by(SavingsGoal.created_at.desc()))))


def get_goal_detail(db: Session, user: User, goal_id: uuid.UUID) -> GoalDetailOut:
    goal = get_owned(db, SavingsGoal, goal_id, user.id, "Savings goal")
    base = to_out(db, user, [goal])[0]
    contributions = db.scalars(
        select(GoalContribution).where(GoalContribution.goal_id == goal.id)
        .order_by(GoalContribution.contribution_date.desc(), GoalContribution.created_at.desc())
    ).all()
    return GoalDetailOut(**base.model_dump(), contributions=[ContributionOut.model_validate(c) for c in contributions])


def create_goal(db: Session, user: User, data: GoalCreate) -> SavingsGoal:
    goal = SavingsGoal(user_id=user.id, title=data.title.strip(), target_amount=money(data.target_amount),
                       target_date=data.target_date, status="active")
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def update_goal(db: Session, user: User, goal_id: uuid.UUID, data: GoalUpdate) -> SavingsGoal:
    goal = get_owned(db, SavingsGoal, goal_id, user.id, "Savings goal")
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None and field in ("title", "target_amount", "status"):
            continue
        setattr(goal, field, money(value) if field == "target_amount" else value)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, user: User, goal_id: uuid.UUID) -> None:
    """Deleting a goal removes its contribution records. Linked transfers stay in the
    ledger (the money really moved), so account balances are unaffected."""
    goal = get_owned(db, SavingsGoal, goal_id, user.id, "Savings goal")
    for c in db.scalars(select(GoalContribution).where(GoalContribution.goal_id == goal.id)):
        db.delete(c)
    db.delete(goal)
    db.commit()


def add_contribution(db: Session, user: User, goal_id: uuid.UUID, data: ContributionCreate) -> GoalContribution:
    goal = get_owned(db, SavingsGoal, goal_id, user.id, "Savings goal")
    if goal.status != "active":
        raise ConflictError("Contributions can only be added to an active goal")
    related_id = None
    if data.from_account_id and data.to_account_id:
        out_leg, _ = create_transfer(db, user, TransferCreate(
            from_account_id=data.from_account_id, to_account_id=data.to_account_id, amount=data.amount,
            transaction_date=data.contribution_date, description=f"Savings: {goal.title}"[:255],
        ), commit=False)
        related_id = out_leg.id
    c = GoalContribution(user_id=user.id, goal_id=goal.id, amount=money(data.amount),
                         contribution_date=data.contribution_date, note=(data.note or "").strip() or None,
                         related_transaction_id=related_id)
    db.add(c)
    db.flush()
    saved, _ = saved_totals(db, user.id, [goal.id]).get(goal.id, (ZERO, 0))
    if saved >= Decimal(goal.target_amount):
        goal.status = "completed"
    db.commit()
    db.refresh(c)
    return c


def delete_contribution(db: Session, user: User, goal_id: uuid.UUID, contribution_id: uuid.UUID) -> None:
    """Removes the contribution and, if it created a transfer, both transfer legs."""
    goal = get_owned(db, SavingsGoal, goal_id, user.id, "Savings goal")
    c = get_owned(db, GoalContribution, contribution_id, user.id, "Contribution")
    if c.goal_id != goal.id:
        raise NotFoundError("Contribution not found")
    linked = db.get(Transaction, c.related_transaction_id) if c.related_transaction_id else None
    db.delete(c)
    db.flush()
    if linked is not None:
        for leg in db.scalars(select(Transaction).where(Transaction.transfer_group_id == linked.transfer_group_id)):
            db.delete(leg)
    saved, _ = saved_totals(db, user.id, [goal.id]).get(goal.id, (ZERO, 0))
    if goal.status == "completed" and saved < Decimal(goal.target_amount):
        goal.status = "active"
    db.commit()
