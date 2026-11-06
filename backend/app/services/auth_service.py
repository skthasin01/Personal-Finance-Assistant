"""Registration, login, refresh-token rotation, logout and account deletion."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthError, ConflictError
from app.core.security import create_access_token, hash_password, hash_token, new_refresh_token, verify_password
from app.models.account import Account
from app.models.ai_conversation import AIConversation, AIMessage
from app.models.bill import Bill
from app.models.budget import Budget
from app.models.category import Category
from app.models.financial_insight import FinancialInsight
from app.models.notification import Notification
from app.models.savings_goal import GoalContribution, SavingsGoal
from app.models.transaction import Transaction
from app.models.user import RefreshToken, User
from app.schemas.auth import RegisterIn

DEFAULT_CATEGORIES = [
    # (name, type, color, icon)
    ("Salary", "income", "#16a34a", "briefcase"),
    ("Business", "income", "#059669", "store"),
    ("Freelance", "income", "#0d9488", "laptop"),
    ("Gifts", "income", "#65a30d", "gift"),
    ("Investment Returns", "income", "#0891b2", "trending-up"),
    ("Other Income", "income", "#4d7c0f", "plus"),
    ("Food & Dining", "expense", "#ef4444", "utensils"),
    ("Groceries", "expense", "#f97316", "shopping-basket"),
    ("Transport", "expense", "#eab308", "bus"),
    ("Rent & Housing", "expense", "#a855f7", "home"),
    ("Bills & Utilities", "expense", "#f59e0b", "zap"),
    ("Mobile & Internet", "expense", "#3b82f6", "wifi"),
    ("Healthcare", "expense", "#ec4899", "heart"),
    ("Education", "expense", "#6366f1", "book"),
    ("Shopping", "expense", "#d946ef", "bag"),
    ("Entertainment", "expense", "#14b8a6", "film"),
    ("Family Support", "expense", "#8b5cf6", "users"),
    ("Travel", "expense", "#06b6d4", "plane"),
    ("Personal Care", "expense", "#f43f5e", "smile"),
    ("Other Expense", "expense", "#64748b", "more"),
]

GENERIC_LOGIN_ERROR = "Invalid email or password"


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def register(db: Session, data: RegisterIn) -> User:
    email = _normalize_email(data.email)
    if db.scalar(select(User.id).where(User.email == email)):
        raise ConflictError("An account with this email already exists")
    return register_user(db, full_name=data.full_name, email=email, password_hash=hash_password(data.password))


def register_user(db: Session, *, full_name: str, email: str, password_hash: str, is_demo: bool = False) -> User:
    """Create a user with default categories and a Cash account."""
    user = User(full_name=full_name, email=email, password_hash=password_hash, is_demo=is_demo)
    db.add(user)
    db.flush()
    db.add_all([Category(user_id=user.id, name=n, type=t, color=c, icon=i, is_default=True)
                for n, t, c, i in DEFAULT_CATEGORIES])
    db.add(Account(user_id=user.id, name="Cash", account_type="cash", currency_code=user.currency_code))
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalars(select(User).where(User.email == _normalize_email(email))).first()
    # verify_password always runs (dummy hash for unknown emails) to keep timing similar.
    ok = verify_password(password, user.password_hash if user else None)
    if not user or not ok or not user.is_active:
        raise AuthError(GENERIC_LOGIN_ERROR)
    return user


def issue_tokens(db: Session, user: User, family_id: uuid.UUID | None = None) -> tuple[str, str]:
    settings = get_settings()
    refresh = new_refresh_token()
    db.add(RefreshToken(
        user_id=user.id, token_hash=hash_token(refresh), family_id=family_id or uuid.uuid4(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
    ))
    db.commit()
    return create_access_token(user.id), refresh


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def rotate_refresh(db: Session, refresh_token: str | None) -> tuple[User, str, str]:
    """Exchange a valid refresh token for a new pair. The old token is revoked.
    Re-use of an already-revoked token signals theft: the whole family is revoked."""
    if not refresh_token:
        raise AuthError("Session expired. Please log in again.")
    record = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))).first()
    now = datetime.now(timezone.utc)
    if record is None:
        raise AuthError("Session expired. Please log in again.")
    if record.revoked_at is not None:
        db.execute(update(RefreshToken).where(RefreshToken.family_id == record.family_id,
                                              RefreshToken.revoked_at.is_(None)).values(revoked_at=now))
        db.commit()
        raise AuthError("Session expired. Please log in again.")
    if _aware(record.expires_at) <= now:
        raise AuthError("Session expired. Please log in again.")
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise AuthError("Session expired. Please log in again.")
    record.revoked_at = now
    access, refresh = issue_tokens(db, user, family_id=record.family_id)
    return user, access, refresh


def revoke_refresh(db: Session, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    record = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))).first()
    if record and record.revoked_at is None:
        db.execute(update(RefreshToken).where(RefreshToken.family_id == record.family_id,
                                              RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=datetime.now(timezone.utc)))
        db.commit()


def delete_user_and_data(db: Session, user: User, password: str) -> None:
    """Permanently delete the user and ALL their data, in dependency order."""
    if not verify_password(password, user.password_hash):
        raise AuthError("Password is incorrect")
    purge_user(db, user.id)


def purge_user(db: Session, uid: uuid.UUID) -> None:
    """Delete a user and all their rows in dependency order, then commit."""
    conv_ids = select(AIConversation.id).where(AIConversation.user_id == uid)
    db.execute(delete(AIMessage).where(AIMessage.conversation_id.in_(conv_ids)))
    db.execute(delete(AIConversation).where(AIConversation.user_id == uid))
    db.execute(delete(Notification).where(Notification.user_id == uid))
    db.execute(delete(FinancialInsight).where(FinancialInsight.user_id == uid))
    db.execute(delete(GoalContribution).where(GoalContribution.user_id == uid))
    db.execute(delete(SavingsGoal).where(SavingsGoal.user_id == uid))
    db.execute(delete(Bill).where(Bill.user_id == uid))
    db.execute(delete(Budget).where(Budget.user_id == uid))
    db.execute(delete(Transaction).where(Transaction.user_id == uid, Transaction.transaction_type == "refund"))
    db.execute(delete(Transaction).where(Transaction.user_id == uid))
    db.execute(delete(Category).where(Category.user_id == uid))
    db.execute(delete(Account).where(Account.user_id == uid))
    db.execute(delete(RefreshToken).where(RefreshToken.user_id == uid))
    db.execute(delete(User).where(User.id == uid))
    db.commit()
