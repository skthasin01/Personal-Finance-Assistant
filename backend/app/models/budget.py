import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPkMixin, utcnow


class Budget(UUIDPkMixin, Base):
    """Monthly budget. category_id NULL = the overall budget.

    The overall budget is an independent limit compared against ALL net expenses
    of the month; it is never added to category budgets in totals.

    NULL-category uniqueness: a normal UNIQUE constraint treats NULLs as distinct,
    so a partial unique index enforces one overall budget per user/month/year.
    """

    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "month", "year", name="uq_budgets_user_category_period"),
        Index(
            "uq_budgets_user_overall_period",
            "user_id",
            "month",
            "year",
            unique=True,
            postgresql_where=text("category_id IS NULL"),
            sqlite_where=text("category_id IS NULL"),
        ),
        CheckConstraint("limit_amount > 0", name="limit_positive"),
        CheckConstraint("month BETWEEN 1 AND 12", name="month_range"),
        CheckConstraint("year BETWEEN 2000 AND 2100", name="year_range"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True)
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
