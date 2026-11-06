"""One-click demo workspaces.

Each click on "Try the demo" creates a NEW private user with a random email and an
unguessable random password (never shown or stored in plain text), seeds sample
data labelled "[Demo]", and signs them in. Visitors never share or see each
other's data. Demo users older than DEMO_TTL_HOURS are purged automatically.
Disabled unless DEMO_MODE=true.
"""
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.security import hash_password
from app.models.category import Category
from app.models.user import User
from app.schemas.account import AccountCreate
from app.schemas.bill import BillCreate, BillPay
from app.schemas.budget import BudgetCreate
from app.schemas.savings_goal import ContributionCreate, GoalCreate
from app.schemas.transaction import TransactionCreate, TransferCreate
from app.services import account_service, auth_service, bill_service, budget_service, savings_service, transaction_service
from app.utils.date_utils import add_months, today_for

D = Decimal


def demo_enabled() -> bool:
    return get_settings().demo_mode


def purge_expired_demo_users(db: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=get_settings().demo_ttl_hours)
    ids = list(db.scalars(select(User.id).where(User.is_demo.is_(True), User.created_at < cutoff)))
    for uid in ids:
        auth_service.purge_user(db, uid)
    return len(ids)


def create_demo_user(db: Session) -> User:
    if not demo_enabled():
        raise NotFoundError("Demo mode is not available")
    purge_expired_demo_users(db)
    user = auth_service.register_user(
        db, full_name="Demo User", email=f"demo-{secrets.token_hex(8)}@demo.invalid",
        password_hash=hash_password(secrets.token_urlsafe(32)), is_demo=True,
    )
    seed_demo_data(db, user)
    db.refresh(user)
    return user


def seed_demo_data(db: Session, user: User) -> None:
    """Add sample records, all prefixed with [Demo], to the given user."""
    cats = {c.name: c.id for c in db.scalars(select(Category).where(Category.user_id == user.id))}
    today = today_for(user.timezone)

    bank = account_service.create_account(db, user, AccountCreate(name="[Demo] City Bank", account_type="bank",
                                                                  opening_balance=D("40000")))
    bkash = account_service.create_account(db, user, AccountCreate(name="[Demo] bKash", account_type="bkash",
                                                                   opening_balance=D("3000")))
    savings = account_service.create_account(db, user, AccountCreate(name="[Demo] Savings", account_type="savings"))

    def tx(kind, acc, cat, amount, d, desc):
        return transaction_service.create_transaction(db, user, TransactionCreate(
            transaction_type=kind, account_id=acc.id, category_id=cats[cat], amount=D(amount),
            transaction_date=d, description=f"[Demo] {desc}"))

    # Three previous months plus the current month (never dated in the future)
    for back in range(3, -1, -1):
        m = add_months(today.replace(day=1), -back)
        month_end = add_months(m, 1) - timedelta(days=1)
        last_day = min(today, month_end)
        day = lambda n: min(m.replace(day=n), last_day)  # noqa: E731
        tx("income", bank, "Salary", "60000", day(1), "Monthly salary")
        tx("expense", bank, "Rent & Housing", "18000", day(2), "House rent")
        tx("expense", bkash, "Groceries", str(7000 + back * 400), day(5), "Monthly groceries")
        tx("expense", bkash, "Food & Dining", str(4500 + (3 - back) * 1200), day(6), "Restaurants and delivery")
        tx("expense", bkash, "Transport", "3200", day(7), "Ride sharing")
        if back == 0:
            shopping = tx("expense", bank, "Shopping", "4500", day(3), "Eid shopping")
            transaction_service.create_transaction(db, user, TransactionCreate(
                transaction_type="refund", account_id=bank.id, amount=D("1200"), transaction_date=day(4),
                related_transaction_id=shopping.id, description="[Demo] Returned one item"))
            transaction_service.create_transfer(db, user, TransferCreate(
                from_account_id=bank.id, to_account_id=bkash.id, amount=D("5000"), transaction_date=day(2),
                description="[Demo] Top up bKash"))

    budget_service.create_budget(db, user, BudgetCreate(limit_amount=D("40000"), month=today.month, year=today.year))
    budget_service.create_budget(db, user, BudgetCreate(category_id=cats["Food & Dining"], limit_amount=D("8000"),
                                                        month=today.month, year=today.year))
    budget_service.create_budget(db, user, BudgetCreate(category_id=cats["Groceries"], limit_amount=D("9000"),
                                                        month=today.month, year=today.year))

    prev_elec = bill_service.create_bill(db, user, BillCreate(title="[Demo] DESCO Electricity", bill_type="electricity",
                                                              amount=D("1850"), due_date=add_months(today, -1)))
    bill_service.pay_bill(db, user, prev_elec.id, BillPay(account_id=bkash.id, paid_date=add_months(today, -1)))
    bill_service.create_bill(db, user, BillCreate(title="[Demo] DESCO Electricity", bill_type="electricity",
                                                  amount=D("2240"), due_date=today + timedelta(days=2),
                                                  recurrence_rule="monthly"))
    bill_service.create_bill(db, user, BillCreate(title="[Demo] Home internet", bill_type="internet", amount=D("1200"),
                                                  due_date=today - timedelta(days=1), recurrence_rule="monthly"))

    goal = savings_service.create_goal(db, user, GoalCreate(title="[Demo] Emergency fund", target_amount=D("150000"),
                                                            target_date=add_months(today, 10)))
    for back in (2, 1, 0):
        savings_service.add_contribution(db, user, goal.id, ContributionCreate(
            amount=D("8000"), contribution_date=add_months(today, -back), from_account_id=bank.id,
            to_account_id=savings.id, note="[Demo] Monthly saving"))
