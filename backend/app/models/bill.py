import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPkMixin

BILL_TYPES = ("electricity", "water", "gas", "internet", "rent", "mobile", "subscription", "custom")
RECURRENCE_RULES = ("monthly", "quarterly", "yearly")


class Bill(UUIDPkMixin, TimestampMixin, Base):
    """A bill. Stored status is pending | paid | cancelled; 'overdue' is derived
    (pending and due_date before today in the user's timezone).

    Paying a bill creates exactly one expense transaction and links it through
    payment_transaction_id (UNIQUE), so a bill can never be double-counted.
    """

    __tablename__ = "bills"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("status IN ('pending','paid','cancelled')", name="status_valid"),
        CheckConstraint(
            "bill_type IN ('electricity','water','gas','internet','rent','mobile','subscription','custom')",
            name="bill_type_valid",
        ),
        CheckConstraint(
            "recurrence_rule IS NULL OR recurrence_rule IN ('monthly','quarterly','yearly')", name="recurrence_valid"
        ),
        CheckConstraint("status <> 'paid' OR payment_transaction_id IS NOT NULL", name="paid_has_transaction"),
        Index("ix_bills_user_due", "user_id", "due_date"),
        Index("ix_bills_user_status", "user_id", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    bill_type: Mapped[str] = mapped_column(String(20), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    billing_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="pending", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True, nullable=True
    )
    recurrence_rule: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
