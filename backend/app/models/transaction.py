import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPkMixin

TRANSACTION_TYPES = ("income", "expense", "transfer", "refund")


class Transaction(UUIDPkMixin, TimestampMixin, Base):
    """Ledger entry. Amounts are always positive; type + direction give the sign.

    * income   : +amount to account, counts as income
    * expense  : -amount from account, counts as expense
    * refund   : +amount to account, references the original expense through
                 related_transaction_id and REDUCES expense totals (not income)
    * transfer : stored as two rows sharing transfer_group_id; direction='out' on
                 the source account and direction='in' on the destination account.
                 Transfers never count as income or expense.

    All recorded transactions are "posted" (the MVP has no pending state).
    transaction_date is the calendar date in the user's own timezone.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("transaction_type IN ('income','expense','transfer','refund')", name="type_valid"),
        CheckConstraint(
            "(transaction_type = 'transfer' AND direction IN ('in','out') AND transfer_group_id IS NOT NULL "
            "AND category_id IS NULL) OR (transaction_type <> 'transfer' AND direction IS NULL)",
            name="transfer_shape",
        ),
        CheckConstraint(
            "transaction_type <> 'refund' OR related_transaction_id IS NOT NULL", name="refund_has_original"
        ),
        Index("ix_transactions_user_date", "user_id", "transaction_date"),
        Index("ix_transactions_user_type_date", "user_id", "transaction_type", "transaction_date"),
        Index("ix_transactions_user_category", "user_id", "category_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id", ondelete="RESTRICT"), index=True, nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True
    )
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    direction: Mapped[str | None] = mapped_column(String(3), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    related_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    transfer_group_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
