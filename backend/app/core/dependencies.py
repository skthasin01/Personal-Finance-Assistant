"""FastAPI dependencies: database session, authenticated user, rate limits.

The authenticated user's id always comes from the verified access token, never
from a client-supplied user_id.
"""
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthError
from app.core.rate_limit import RateLimiter
from app.core.security import decode_access_token
from app.database.connection import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)

settings = get_settings()
auth_limiter = RateLimiter(settings.auth_rate_limit_per_minute)
ai_limiter = RateLimiter(settings.ai_rate_limit_per_minute)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthError("Not authenticated")
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise AuthError("Invalid or expired token")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError("Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit_auth(request: Request) -> None:
    auth_limiter.check(f"auth:{client_ip(request)}")


def rate_limit_ai(user: CurrentUser) -> None:
    ai_limiter.check(f"ai:{user.id}")
