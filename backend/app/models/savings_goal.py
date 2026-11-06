import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPkMixin, utcnow


class SavingsGoal(UUIDPkMixin, TimestampMixin, Base):
    """Savings goal. There is deliberately NO current_amount column: progress is
    always derived from the goal_contributions ledger (single source of truth)."""

    __tablename__ = "savings_goals"
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="target_positive"),
        CheckConstraint("status IN ('active','completed','cancelled')", name="status_valid"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="active", nullable=False)


class GoalContribution(UUIDPkMixin, Base):
    """Money set aside for a goal. A contribution is NOT an expense. If the user
    physically moved money (e.g. bank -> savings account) the contribution links
    to that transfer via related_transaction_id; the transfer itself is already
    excluded from income/expense, so nothing is counted twice."""

    __tablename__ = "goal_contributions"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    goal_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("savings_goals.id", ondelete="CASCADE"), index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    contribution_date: Mapped[date] = mapped_column(Date, nullable=False)
    related_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True, nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
