"""Bills: tracking, derived overdue status, comparison, and safe payment.

Payment rule (prevents double counting): paying a bill creates exactly ONE expense
transaction and stores its id in bills.payment_transaction_id (UNIQUE). A bill
that is already paid cannot be paid again. Deleting the payment transaction puts
the bill back to 'pending'.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ValidationAppError
from app.models.bill import Bill
from app.models.category import Category
from app.models.user import User
from app.schemas.bill import BillComparison, BillCreate, BillOut, BillPay, BillUpdate
from app.schemas.common import Page, page_count
from app.schemas.transaction import TransactionCreate
from app.services.common import clamp_page, get_owned
from app.services.transaction_service import create_transaction
from app.utils.date_utils import add_months, today_for
from app.utils.financial_utils import change_percent, money

RECURRENCE_MONTHS = {"monthly": 1, "quarterly": 3, "yearly": 12}
BILL_CATEGORY_NAME = "Bills & Utilities"


def display_status(bill: Bill, today: date) -> str:
    if bill.status == "pending" and bill.due_date < today:
        return "overdue"
    return bill.status


def compare_with_previous(db: Session, bill: Bill) -> BillComparison:
    prev = db.scalars(
        select(Bill).where(Bill.user_id == bill.user_id, Bill.bill_type == bill.bill_type, Bill.id != bill.id,
                           Bill.status != "cancelled", Bill.due_date < bill.due_date)
        .order_by(Bill.due_date.desc()).limit(1)
    ).first()
    if prev is None:
        return BillComparison(previous_bill_id=None, previous_amount=None, change_amount=None, change_percent=None,
                              message="No previous bill of this type to compare with yet.")
    current, previous = money(bill.amount), money(prev.amount)
    pct = change_percent(current, previous)
    diff = money(current - previous)
    if pct is None:
        msg = "Previous bill amount is zero, so a percentage change is not available."
    elif diff > 0:
        msg = f"{pct}% higher than the previous {bill.bill_type} bill."
    elif diff < 0:
        msg = f"{abs(pct)}% lower than the previous {bill.bill_type} bill."
    else:
        msg = f"Same amount as the previous {bill.bill_type} bill."
    return BillComparison(previous_bill_id=prev.id, previous_amount=previous, change_amount=diff,
                          change_percent=pct, message=msg)


def to_out(db: Session, user: User, bill: Bill, with_comparison: bool = False) -> BillOut:
    today = today_for(user.timezone)
    return BillOut(
        id=bill.id, title=bill.title, bill_type=bill.bill_type, category_id=bill.category_id, amount=money(bill.amount),
        billing_period_start=bill.billing_period_start, billing_period_end=bill.billing_period_end,
        due_date=bill.due_date, status=bill.status, display_status=display_status(bill, today),
        days_until_due=(bill.due_date - today).days if bill.status == "pending" else None,
        paid_at=bill.paid_at, payment_transaction_id=bill.payment_transaction_id,
        recurrence_rule=bill.recurrence_rule, notes=bill.notes,
        comparison=compare_with_previous(db, bill) if with_comparison else None,
    )


def _check_category(db: Session, user: User, category_id: uuid.UUID | None) -> None:
    if category_id:
        cat = get_owned(db, Category, category_id, user.id, "Category")
        if cat.type != "expense":
            raise ValidationAppError("Bills must use an expense category",
                                     [{"field": "category_id", "message": "Choose an expense category"}])


def list_bills(db: Session, user: User, *, status: str | None = None, page: int = 1, page_size: int = 50,
               start_date: date | None = None, end_date: date | None = None) -> Page[BillOut]:
    page, page_size = clamp_page(page, page_size)
    today = today_for(user.timezone)
    conds = [Bill.user_id == user.id]
    if status == "overdue":
        conds += [Bill.status == "pending", Bill.due_date < today]
    elif status == "upcoming":
        conds += [Bill.status == "pending", Bill.due_date >= today]
    elif status in ("pending", "paid", "cancelled"):
        conds.append(Bill.status == status)
    elif status:
        raise ValidationAppError("status must be pending, paid, overdue, upcoming or cancelled")
    if start_date:
        conds.append(Bill.due_date >= start_date)
    if end_date:
        conds.append(Bill.due_date <= end_date)
    total = db.scalar(select(func.count()).select_from(Bill).where(*conds)) or 0
    order = Bill.due_date.desc() if status == "paid" else Bill.due_date.asc()
    bills = db.scalars(select(Bill).where(*conds).order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
    return Page[BillOut](items=[to_out(db, user, b, with_comparison=True) for b in bills], page=page,
                         page_size=page_size, total=total, pages=page_count(total, page_size))


def create_bill(db: Session, user: User, data: BillCreate) -> Bill:
    _check_category(db, user, data.category_id)
    bill = Bill(user_id=user.id, status="pending", **data.model_dump())
    bill.amount = money(bill.amount)
    bill.title = bill.title.strip()
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


def update_bill(db: Session, user: User, bill_id: uuid.UUID, data: BillUpdate) -> Bill:
    bill = get_owned(db, Bill, bill_id, user.id, "Bill")
    changes = data.model_dump(exclude_unset=True)
    if bill.status == "paid" and changes.keys() - {"title", "notes", "recurrence_rule"}:
        raise ConflictError("A paid bill can only have its title, notes or recurrence changed. "
                            "Delete the payment transaction first to edit other fields.")
    if "category_id" in changes:
        _check_category(db, user, changes["category_id"])
    for field, value in changes.items():
        setattr(bill, field, money(value) if field == "amount" and value is not None else value)
    if bill.billing_period_start and bill.billing_period_end and bill.billing_period_end < bill.billing_period_start:
        raise ValidationAppError("billing_period_end must be on or after billing_period_start")
    db.commit()
    db.refresh(bill)
    return bill


def delete_bill(db: Session, user: User, bill_id: uuid.UUID) -> None:
    bill = get_owned(db, Bill, bill_id, user.id, "Bill")
    if bill.status == "paid":
        raise ConflictError("A paid bill is part of your financial history. Delete its payment transaction first, "
                            "or keep the bill.")
    db.delete(bill)
    db.commit()


def _default_bill_category(db: Session, user: User) -> uuid.UUID:
    cat = db.scalars(select(Category).where(Category.user_id == user.id, Category.type == "expense",
                                            Category.name == BILL_CATEGORY_NAME)).first()
    if cat is None:
        cat = Category(user_id=user.id, name=BILL_CATEGORY_NAME, type="expense", color="#f59e0b", is_default=True)
        db.add(cat)
        db.flush()
    return cat.id


def pay_bill(db: Session, user: User, bill_id: uuid.UUID, data: BillPay) -> tuple[Bill, Bill | None]:
    """Mark a bill paid: one expense transaction + link, in one DB transaction.
    The row lock (SELECT ... FOR UPDATE on PostgreSQL) and the UNIQUE constraint on
    payment_transaction_id stop concurrent double payments."""
    bill = get_owned(db, Bill, bill_id, user.id, "Bill", for_update=True)
    if bill.status == "paid" or bill.payment_transaction_id is not None:
        raise ConflictError("This bill has already been paid")
    if bill.status == "cancelled":
        raise ConflictError("A cancelled bill cannot be paid")

    category_id = data.category_id or bill.category_id or _default_bill_category(db, user)
    paid_date = data.paid_date or today_for(user.timezone)
    tx = create_transaction(db, user, TransactionCreate(
        transaction_type="expense", account_id=data.account_id, category_id=category_id,
        amount=data.amount or bill.amount, transaction_date=paid_date, description=f"Bill payment: {bill.title}"[:255],
    ), commit=False)

    bill.status = "paid"
    bill.paid_at = datetime.now(timezone.utc)
    bill.payment_transaction_id = tx.id

    next_bill = None
    if bill.recurrence_rule:
        months = RECURRENCE_MONTHS[bill.recurrence_rule]
        next_due = add_months(bill.due_date, months)
        exists = db.scalar(select(Bill.id).where(Bill.user_id == user.id, Bill.title == bill.title,
                                                 Bill.due_date == next_due))
        if not exists:
            next_bill = Bill(
                user_id=user.id, title=bill.title, bill_type=bill.bill_type, category_id=bill.category_id,
                amount=bill.amount, due_date=next_due, status="pending", recurrence_rule=bill.recurrence_rule,
                notes=bill.notes,
                billing_period_start=add_months(bill.billing_period_start, months) if bill.billing_period_start else None,
                billing_period_end=add_months(bill.billing_period_end, months) if bill.billing_period_end else None,
            )
            db.add(next_bill)
    db.commit()
    db.refresh(bill)
    return bill, next_bill
