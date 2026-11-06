"""Accounts and categories (CRUD with ledger-safe deletion)."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.account import Account
from app.models.bill import Bill
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.account import AccountCreate, AccountOut, AccountUpdate
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.common import get_owned
from app.services.transaction_service import account_balances
from app.utils.financial_utils import ZERO, money


# ---------------------------------------------------------------- accounts
def account_out(db: Session, user: User, accounts: list[Account]) -> list[AccountOut]:
    balances = account_balances(db, user.id)
    out = []
    for a in accounts:
        item = AccountOut.model_validate(a)
        item.opening_balance = money(a.opening_balance)
        item.current_balance = balances.get(a.id, ZERO)
        out.append(item)
    return out


def list_accounts(db: Session, user: User, include_inactive: bool = True) -> list[AccountOut]:
    stmt = select(Account).where(Account.user_id == user.id)
    if not include_inactive:
        stmt = stmt.where(Account.is_active)
    return account_out(db, user, list(db.scalars(stmt.order_by(Account.is_active.desc(), Account.name))))


def _name_taken(db: Session, user: User, name: str, exclude: uuid.UUID | None = None) -> bool:
    stmt = select(Account.id).where(Account.user_id == user.id, func.lower(Account.name) == name.lower())
    if exclude:
        stmt = stmt.where(Account.id != exclude)
    return db.scalar(stmt) is not None


def create_account(db: Session, user: User, data: AccountCreate) -> Account:
    name = data.name.strip()
    if _name_taken(db, user, name):
        raise ConflictError("You already have an account with this name")
    acc = Account(user_id=user.id, name=name, account_type=data.account_type,
                  opening_balance=money(data.opening_balance),
                  currency_code=(data.currency_code or user.currency_code).upper())
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


def update_account(db: Session, user: User, account_id: uuid.UUID, data: AccountUpdate) -> Account:
    acc = get_owned(db, Account, account_id, user.id, "Account")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("name"):
        name = changes["name"].strip()
        if _name_taken(db, user, name, exclude=acc.id):
            raise ConflictError("You already have an account with this name")
        acc.name = name
    if changes.get("account_type"):
        acc.account_type = changes["account_type"]
    if changes.get("opening_balance") is not None:
        acc.opening_balance = money(changes["opening_balance"])
    if changes.get("is_active") is not None:
        acc.is_active = changes["is_active"]
    db.commit()
    db.refresh(acc)
    return acc


def delete_account(db: Session, user: User, account_id: uuid.UUID) -> str:
    """Accounts with transactions are deactivated (history and reports stay correct);
    unused accounts are deleted."""
    acc = get_owned(db, Account, account_id, user.id, "Account")
    used = db.scalar(select(func.count()).select_from(Transaction).where(Transaction.account_id == acc.id))
    if used:
        acc.is_active = False
        db.commit()
        return "Account has transactions, so it was deactivated instead of deleted."
    db.delete(acc)
    db.commit()
    return "Account deleted."


# ---------------------------------------------------------------- categories
def list_categories(db: Session, user: User, cat_type: str | None = None, include_inactive: bool = False) -> list[Category]:
    stmt = select(Category).where(Category.user_id == user.id)
    if cat_type:
        stmt = stmt.where(Category.type == cat_type)
    if not include_inactive:
        stmt = stmt.where(Category.is_active)
    return list(db.scalars(stmt.order_by(Category.type, Category.name)))


def _cat_name_taken(db, user, name, cat_type, exclude=None) -> bool:
    stmt = select(Category.id).where(Category.user_id == user.id, Category.type == cat_type,
                                     func.lower(Category.name) == name.lower())
    if exclude:
        stmt = stmt.where(Category.id != exclude)
    return db.scalar(stmt) is not None


def create_category(db: Session, user: User, data: CategoryCreate) -> Category:
    name = data.name.strip()
    if _cat_name_taken(db, user, name, data.type):
        raise ConflictError(f"You already have an {data.type} category named '{name}'")
    cat = Category(user_id=user.id, name=name, type=data.type, icon=data.icon, color=data.color)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def update_category(db: Session, user: User, category_id: uuid.UUID, data: CategoryUpdate) -> Category:
    cat = get_owned(db, Category, category_id, user.id, "Category")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("name"):
        name = changes["name"].strip()
        if _cat_name_taken(db, user, name, cat.type, exclude=cat.id):
            raise ConflictError(f"You already have an {cat.type} category named '{name}'")
        cat.name = name
    for field in ("icon", "color", "is_active"):
        if field in changes and changes[field] is not None:
            setattr(cat, field, changes[field])
    db.commit()
    db.refresh(cat)
    return cat


def delete_category(db: Session, user: User, category_id: uuid.UUID) -> str:
    cat = get_owned(db, Category, category_id, user.id, "Category")
    used = db.scalar(select(func.count()).select_from(Transaction).where(Transaction.category_id == cat.id)) or 0
    used += db.scalar(select(func.count()).select_from(Budget).where(Budget.category_id == cat.id)) or 0
    used += db.scalar(select(func.count()).select_from(Bill).where(Bill.category_id == cat.id)) or 0
    if used:
        cat.is_active = False
        db.commit()
        return "Category is in use, so it was deactivated instead of deleted."
    db.delete(cat)
    db.commit()
    return "Category deleted."


