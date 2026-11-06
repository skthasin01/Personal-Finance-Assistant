import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPkMixin, utcnow


class User(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("budget_warning_threshold BETWEEN 1 AND 100", name="budget_threshold_range"),
        CheckConstraint("bill_reminder_days BETWEEN 0 AND 30", name="bill_reminder_range"),
        Index("ix_users_is_demo_created", "is_demo", "created_at"),
    )

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), default="BDT", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Dhaka", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Temporary one-click demo workspace (auto-deleted after DEMO_TTL_HOURS)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)

    # Notification preferences
    notify_bills: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_budgets: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_goals: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    budget_warning_threshold: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
    bill_reminder_days: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Consent to send minimized financial context to an external AI provider
    ai_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefreshToken(UUIDPkMixin, Base):
    """Server-side record of issued refresh tokens (only a SHA-256 hash is stored).

    Enables rotation (each refresh issues a new token and revokes the old one)
    and revocation on logout. Re-use of a revoked token revokes the whole family.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
