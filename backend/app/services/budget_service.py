"""Monthly budgets.

* Category budget: compared with net expenses (expenses - refunds) of that category.
* Overall budget (category_id NULL): an INDEPENDENT limit compared with net
  expenses of ALL categories. It is never summed with category budgets.
* utilization = spent / limit * 100 (limit is always > 0 by constraint).
* status: ok < threshold <= warning < 100% <= exceeded
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ValidationAppError
from app.models.budget import Budget
from app.models.category import Category
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetOut, BudgetUpdate
from app.services.analytics_service import net_expense_by_category
from app.services.common import get_owned
from app.utils.date_utils import month_bounds
from app.utils.financial_utils import ZERO, money, percent


def budget_status(utilization, threshold: int) -> str:
    if utilization is None:
        return "ok"
    if utilization >= 100:
        return "exceeded"
    if utilization >= threshold:
        return "warning"
    return "ok"


def build_outputs(db: Session, user: User, budgets: list[Budget]) -> list[BudgetOut]:
    cats = {c.id: c for c in db.scalars(select(Category).where(Category.user_id == user.id))}
    cache: dict[tuple[int, int], dict] = {}
    out = []
    for b in budgets:
        key = (b.year, b.month)
        if key not in cache:
            start, end = month_bounds(b.year, b.month)
            cache[key] = net_expense_by_category(db, user.id, start, end)
        by_cat = cache[key]
        if b.category_id is None:
            spent = sum(by_cat.values(), ZERO)
        else:
            spent = by_cat.get(b.category_id, ZERO)
        spent = money(max(spent, ZERO))
        limit = money(b.limit_amount)
        util = percent(spent, limit)
        cat = cats.get(b.category_id) if b.category_id else None
        out.append(BudgetOut(
            id=b.id, category_id=b.category_id, category_name=cat.name if cat else None,
            category_color=cat.color if cat else None, is_overall=b.category_id is None, month=b.month, year=b.year,
            limit_amount=limit, spent_amount=spent, remaining_amount=money(limit - spent),
            utilization_percent=util, status=budget_status(util, user.budget_warning_threshold),
            warning_threshold=user.budget_warning_threshold,
        ))
    return out


def list_budgets(db: Session, user: User, month: int | None, year: int | None) -> list[BudgetOut]:
    stmt = select(Budget).where(Budget.user_id == user.id)
    if month:
        stmt = stmt.where(Budget.month == month)
    if year:
        stmt = stmt.where(Budget.year == year)
    budgets = list(db.scalars(stmt.order_by(Budget.year.desc(), Budget.month.desc(), Budget.created_at)))
    # Overall budget first within each month
    budgets.sort(key=lambda b: (-b.year, -b.month, b.category_id is not None))
    return build_outputs(db, user, budgets)


def get_budget(db: Session, user: User, budget_id: uuid.UUID) -> BudgetOut:
    return build_outputs(db, user, [get_owned(db, Budget, budget_id, user.id, "Budget")])[0]


def create_budget(db: Session, user: User, data: BudgetCreate) -> BudgetOut:
    if data.category_id:
        cat = get_owned(db, Category, data.category_id, user.id, "Category")
        if cat.type != "expense":
            raise ValidationAppError("Budgets can only use expense categories",
                                     [{"field": "category_id", "message": "Choose an expense category"}])
    existing = db.scalar(select(Budget.id).where(
        Budget.user_id == user.id, Budget.month == data.month, Budget.year == data.year,
        Budget.category_id.is_(None) if data.category_id is None else Budget.category_id == data.category_id,
    ))
    if existing:
        what = "an overall budget" if data.category_id is None else "a budget for this category"
        raise ConflictError(f"You already have {what} for {data.month:02d}/{data.year}")
    b = Budget(user_id=user.id, category_id=data.category_id, limit_amount=money(data.limit_amount),
               month=data.month, year=data.year)
    db.add(b)
    db.commit()
    db.refresh(b)
    return build_outputs(db, user, [b])[0]


def update_budget(db: Session, user: User, budget_id: uuid.UUID, data: BudgetUpdate) -> BudgetOut:
    b = get_owned(db, Budget, budget_id, user.id, "Budget")
    b.limit_amount = money(data.limit_amount)
    db.commit()
    return build_outputs(db, user, [b])[0]


def delete_budget(db: Session, user: User, budget_id: uuid.UUID) -> None:
    db.delete(get_owned(db, Budget, budget_id, user.id, "Budget"))
    db.commit()
