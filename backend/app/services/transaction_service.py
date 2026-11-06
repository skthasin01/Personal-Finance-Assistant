"""Transaction ledger rules: income, expense, refund, transfer, account balances.

Ledger sign rules (amount is always positive):
    income        +amount   counts as income
    expense       -amount   counts as expense
    refund        +amount   reduces expense (never counted as income)
    transfer out  -amount   excluded from income/expense
    transfer in   +amount   excluded from income/expense

Account balance = opening + income - expense + refunds + transfers_in - transfers_out
"""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ValidationAppError
from app.models.account import Account
from app.models.bill import Bill
from app.models.category import Category
from app.models.savings_goal import GoalContribution
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.common import Page, page_count
from app.schemas.transaction import TransactionCreate, TransactionOut, TransactionUpdate, TransferCreate
from app.services.common import clamp_page, get_owned
from app.utils.financial_utils import ZERO, money

SIGNED_AMOUNT = case(
    (Transaction.transaction_type == "income", Transaction.amount),
    (Transaction.transaction_type == "refund", Transaction.amount),
    (Transaction.transaction_type == "expense", -Transaction.amount),
    (and_(Transaction.transaction_type == "transfer", Transaction.direction == "in"), Transaction.amount),
    (and_(Transaction.transaction_type == "transfer", Transaction.direction == "out"), -Transaction.amount),
    else_=0,
)

SORTS = {
    "date_desc": (Transaction.transaction_date.desc(), Transaction.created_at.desc()),
    "date_asc": (Transaction.transaction_date.asc(), Transaction.created_at.asc()),
    "amount_desc": (Transaction.amount.desc(), Transaction.transaction_date.desc()),
    "amount_asc": (Transaction.amount.asc(), Transaction.transaction_date.desc()),
}


# ---------------------------------------------------------------- balances
def account_balances(db: Session, user_id: uuid.UUID) -> dict[uuid.UUID, Decimal]:
    """Current balance of every account of the user, computed from the ledger."""
    movement = (
        select(Transaction.account_id, func.coalesce(func.sum(SIGNED_AMOUNT), 0).label("movement"))
        .where(Transaction.user_id == user_id)
        .group_by(Transaction.account_id)
        .subquery()
    )
    rows = db.execute(
        select(Account.id, Account.opening_balance, movement.c.movement)
        .outerjoin(movement, movement.c.account_id == Account.id)
        .where(Account.user_id == user_id)
    ).all()
    return {r.id: money(Decimal(r.opening_balance) + money(r.movement or 0)) for r in rows}


def refunded_total(db: Session, expense_id: uuid.UUID, exclude_id: uuid.UUID | None = None) -> Decimal:
    stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.related_transaction_id == expense_id, Transaction.transaction_type == "refund"
    )
    if exclude_id:
        stmt = stmt.where(Transaction.id != exclude_id)
    return money(db.scalar(stmt))


# ---------------------------------------------------------------- validation helpers
def _active_account(db: Session, user: User, account_id: uuid.UUID) -> Account:
    account = get_owned(db, Account, account_id, user.id, "Account")
    if not account.is_active:
        raise ValidationAppError("This account is inactive", [{"field": "account_id", "message": "Account is inactive"}])
    return account


def _category_for(db: Session, user: User, category_id: uuid.UUID, tx_type: str) -> Category:
    category = get_owned(db, Category, category_id, user.id, "Category")
    expected = "income" if tx_type == "income" else "expense"
    if category.type != expected:
        raise ValidationAppError(
            f"A {tx_type} must use a {expected} category",
            [{"field": "category_id", "message": f"Category type must be {expected}"}],
        )
    if not category.is_active:
        raise ValidationAppError("This category is inactive", [{"field": "category_id", "message": "Category is inactive"}])
    return category


def _validate_refund(db: Session, user: User, original_id: uuid.UUID, amount: Decimal, refund_date: date,
                     exclude_id: uuid.UUID | None = None) -> Transaction:
    original = get_owned(db, Transaction, original_id, user.id, "Original transaction")
    if original.transaction_type != "expense":
        raise ValidationAppError("Only expenses can be refunded",
                                 [{"field": "related_transaction_id", "message": "Must reference an expense"}])
    already = refunded_total(db, original.id, exclude_id)
    remaining = money(original.amount) - already
    if amount > remaining:
        raise ValidationAppError(
            f"Refund exceeds the refundable amount ({remaining})",
            [{"field": "amount", "message": f"At most {remaining} can still be refunded"}],
        )
    if refund_date < original.transaction_date:
        raise ValidationAppError("A refund cannot be dated before the original expense",
                                 [{"field": "transaction_date", "message": "Must be on or after the expense date"}])
    return original


# ---------------------------------------------------------------- output
def to_out(db: Session, txs: list[Transaction]) -> list[TransactionOut]:
    """Attach display fields (names, transfer counterpart, refunded amount)."""
    if not txs:
        return []
    account_ids = {t.account_id for t in txs}
    category_ids = {t.category_id for t in txs if t.category_id}
    group_ids = {t.transfer_group_id for t in txs if t.transfer_group_id}
    expense_ids = [t.id for t in txs if t.transaction_type == "expense"]
    tx_ids = [t.id for t in txs]

    counterparts: dict[tuple, Transaction] = {}
    if group_ids:
        for leg in db.scalars(select(Transaction).where(Transaction.transfer_group_id.in_(group_ids))):
            counterparts[(leg.transfer_group_id, leg.direction)] = leg
            account_ids.add(leg.account_id)

    accounts = {a.id: a.name for a in db.scalars(select(Account).where(Account.id.in_(account_ids)))}
    categories = {c.id: c for c in db.scalars(select(Category).where(Category.id.in_(category_ids)))} if category_ids else {}
    refunds: dict[uuid.UUID, Decimal] = {}
    if expense_ids:
        for rid, total in db.execute(
            select(Transaction.related_transaction_id, func.sum(Transaction.amount))
            .where(Transaction.related_transaction_id.in_(expense_ids), Transaction.transaction_type == "refund")
            .group_by(Transaction.related_transaction_id)
        ):
            refunds[rid] = money(total)
    bill_paid = set(db.scalars(select(Bill.payment_transaction_id).where(Bill.payment_transaction_id.in_(tx_ids))))

    out = []
    for t in txs:
        item = TransactionOut.model_validate(t)
        item.amount = money(t.amount)
        item.account_name = accounts.get(t.account_id)
        if t.category_id and t.category_id in categories:
            item.category_name = categories[t.category_id].name
            item.category_color = categories[t.category_id].color
        if t.transfer_group_id:
            other = counterparts.get((t.transfer_group_id, "in" if t.direction == "out" else "out"))
            if other:
                item.counterpart_account_id = other.account_id
                item.counterpart_account_name = accounts.get(other.account_id)
        if t.transaction_type == "expense":
            item.refunded_amount = refunds.get(t.id, ZERO)
        item.is_bill_payment = t.id in bill_paid
        out.append(item)
    return out


# ---------------------------------------------------------------- queries
def list_transactions(db: Session, user: User, *, page: int = 1, page_size: int = 20, sort: str = "date_desc",
                      search: str | None = None, start_date: date | None = None, end_date: date | None = None,
                      account_id: uuid.UUID | None = None, category_id: uuid.UUID | None = None,
                      transaction_type: str | None = None) -> Page[TransactionOut]:
    page, page_size = clamp_page(page, page_size)
    if sort not in SORTS:
        raise ValidationAppError(f"sort must be one of {list(SORTS)}")
    conditions = [Transaction.user_id == user.id]
    if search:
        conditions.append(Transaction.description.ilike(f"%{search.strip()}%"))
    if start_date:
        conditions.append(Transaction.transaction_date >= start_date)
    if end_date:
        conditions.append(Transaction.transaction_date <= end_date)
    if account_id:
        conditions.append(Transaction.account_id == account_id)
    if category_id:
        conditions.append(Transaction.category_id == category_id)
    if transaction_type:
        conditions.append(Transaction.transaction_type == transaction_type)

    total = db.scalar(select(func.count()).select_from(Transaction).where(*conditions)) or 0
    rows = list(db.scalars(
        select(Transaction).where(*conditions).order_by(*SORTS[sort]).offset((page - 1) * page_size).limit(page_size)
    ))
    return Page[TransactionOut](items=to_out(db, rows), page=page, page_size=page_size, total=total,
                                pages=page_count(total, page_size))


def get_transaction(db: Session, user: User, tx_id: uuid.UUID) -> TransactionOut:
    return to_out(db, [get_owned(db, Transaction, tx_id, user.id, "Transaction")])[0]


# ---------------------------------------------------------------- commands
def create_transaction(db: Session, user: User, data: TransactionCreate, commit: bool = True) -> Transaction:
    _active_account(db, user, data.account_id)
    category_id = data.category_id
    if data.transaction_type == "refund":
        original = _validate_refund(db, user, data.related_transaction_id, data.amount, data.transaction_date)
        category_id = original.category_id  # refunds net against the original expense category
    else:
        _category_for(db, user, data.category_id, data.transaction_type)

    tx = Transaction(
        user_id=user.id,
        account_id=data.account_id,
        category_id=category_id,
        transaction_type=data.transaction_type,
        amount=money(data.amount),
        transaction_date=data.transaction_date,
        description=(data.description or "").strip() or None,
        related_transaction_id=data.related_transaction_id,
    )
    db.add(tx)
    if commit:
        db.commit()
        db.refresh(tx)
    else:
        db.flush()
    return tx


def create_transfer(db: Session, user: User, data: TransferCreate, commit: bool = True) -> tuple[Transaction, Transaction]:
    source = _active_account(db, user, data.from_account_id)
    dest = _active_account(db, user, data.to_account_id)
    group = uuid.uuid4()
    desc = (data.description or "").strip() or f"Transfer {source.name} → {dest.name}"
    common = dict(user_id=user.id, transaction_type="transfer", amount=money(data.amount),
                  transaction_date=data.transaction_date, description=desc, transfer_group_id=group)
    out_leg = Transaction(account_id=source.id, direction="out", **common)
    in_leg = Transaction(account_id=dest.id, direction="in", **common)
    db.add_all([out_leg, in_leg])
    if commit:
        db.commit()
        db.refresh(out_leg)
        db.refresh(in_leg)
    else:
        db.flush()
    return out_leg, in_leg


def update_transaction(db: Session, user: User, tx_id: uuid.UUID, data: TransactionUpdate) -> Transaction:
    tx = get_owned(db, Transaction, tx_id, user.id, "Transaction")
    changes = data.model_dump(exclude_unset=True)

    if tx.transaction_type == "transfer":
        if "account_id" in changes or "category_id" in changes:
            raise ValidationAppError("To change transfer accounts, delete the transfer and create a new one")
        legs = list(db.scalars(select(Transaction).where(Transaction.transfer_group_id == tx.transfer_group_id)))
        for leg in legs:
            if "amount" in changes and changes["amount"] is not None:
                leg.amount = money(changes["amount"])
            if "transaction_date" in changes and changes["transaction_date"] is not None:
                leg.transaction_date = changes["transaction_date"]
            if "description" in changes:
                leg.description = (changes["description"] or "").strip() or None
        db.commit()
        db.refresh(tx)
        return tx

    if changes.get("account_id"):
        _active_account(db, user, changes["account_id"])
        tx.account_id = changes["account_id"]
    if changes.get("category_id"):
        if tx.transaction_type == "refund":
            raise ValidationAppError("A refund always uses the original expense's category")
        _category_for(db, user, changes["category_id"], tx.transaction_type)
        tx.category_id = changes["category_id"]
    new_amount = money(changes["amount"]) if changes.get("amount") is not None else money(tx.amount)
    new_date = changes.get("transaction_date") or tx.transaction_date

    if tx.transaction_type == "refund":
        _validate_refund(db, user, tx.related_transaction_id, new_amount, new_date, exclude_id=tx.id)
    if tx.transaction_type == "expense":
        refunded = refunded_total(db, tx.id)
        if new_amount < refunded:
            raise ValidationAppError(f"Amount cannot be lower than the amount already refunded ({refunded})")

    tx.amount = new_amount
    tx.transaction_date = new_date
    if "description" in changes:
        tx.description = (changes["description"] or "").strip() or None
    db.commit()
    db.refresh(tx)
    return tx


def delete_transaction(db: Session, user: User, tx_id: uuid.UUID) -> None:
    """Deletes keep the ledger consistent:
    * transfer      -> both legs are deleted together
    * expense       -> blocked while refunds reference it
    * bill payment  -> the bill goes back to 'pending' (payment link removed)
    * goal-linked transfer -> blocked; delete the contribution instead
    """
    tx = get_owned(db, Transaction, tx_id, user.id, "Transaction")
    legs = [tx]
    if tx.transaction_type == "transfer":
        legs = list(db.scalars(select(Transaction).where(Transaction.transfer_group_id == tx.transfer_group_id)))
    leg_ids = [leg.id for leg in legs]

    if db.scalar(select(GoalContribution.id).where(GoalContribution.related_transaction_id.in_(leg_ids))):
        raise ConflictError("This transfer belongs to a savings-goal contribution. Delete the contribution instead.")
    if tx.transaction_type == "expense" and db.scalar(
        select(func.count()).select_from(Transaction).where(Transaction.related_transaction_id == tx.id)
    ):
        raise ConflictError("This expense has refunds. Delete the refunds first.")

    for bill in db.scalars(select(Bill).where(Bill.payment_transaction_id.in_(leg_ids))):
        bill.payment_transaction_id = None
        bill.status = "pending"
        bill.paid_at = None
    db.flush()
    for leg in legs:
        db.delete(leg)
    db.commit()
