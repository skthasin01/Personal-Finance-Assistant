from datetime import datetime, timezone

from fastapi import APIRouter, Response

from app.core.dependencies import CurrentUser, DbSession
from app.routers.auth import _clear_refresh_cookie
from app.schemas.common import Message
from app.schemas.user import DeleteAccountIn, UserOut, UserUpdate
from app.services import auth_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(data: UserUpdate, user: CurrentUser, db: DbSession):
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is None:
            continue
        if field == "ai_consent":
            user.ai_consent = value
            user.ai_consent_at = datetime.now(timezone.utc) if value else None
        elif field == "full_name":
            user.full_name = value.strip()
        else:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/me", response_model=Message)
def delete_me(data: DeleteAccountIn, response: Response, user: CurrentUser, db: DbSession):
    """Permanently deletes the account and all financial data. Requires the password."""
    auth_service.delete_user_and_data(db, user, data.password)
    _clear_refresh_cookie(response)
    return Message(message="Your account and all associated data have been permanently deleted.")
