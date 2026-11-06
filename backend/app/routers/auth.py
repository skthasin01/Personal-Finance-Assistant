"""Auth endpoints.

Token strategy:
* access token  -> JSON response body; frontend keeps it in memory only.
* refresh token -> HttpOnly + SameSite=Strict cookie limited to /api/v1/auth
  (Secure in production). JavaScript can never read it.
* CSRF: refresh/logout additionally require the custom header
  `X-Requested-With: XMLHttpRequest`, which cross-site forms cannot send.
"""
from fastapi import APIRouter, Depends, Request, Response, status

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, DbSession, rate_limit_auth
from app.core.exceptions import ForbiddenError
from app.schemas.auth import LoginIn, RegisterIn, TokenOut
from app.schemas.common import Message
from app.schemas.user import UserOut
from app.services import auth_service, demo_service

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE, token, httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_days * 86400, path=f"{settings.api_prefix}/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=f"{settings.api_prefix}/auth", httponly=True,
                           secure=settings.cookie_secure, samesite=settings.cookie_samesite)


def _require_csrf_header(request: Request) -> None:
    if request.headers.get("x-requested-with", "").lower() != "xmlhttprequest":
        raise ForbiddenError("Missing CSRF header")


def _token_out(user, access: str) -> TokenOut:
    return TokenOut(access_token=access, expires_in=settings.access_token_minutes * 60,
                    user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit_auth)])
def register(data: RegisterIn, response: Response, db: DbSession):
    user = auth_service.register(db, data)
    access, refresh = auth_service.issue_tokens(db, user)
    _set_refresh_cookie(response, refresh)
    return _token_out(user, access)


@router.post("/login", response_model=TokenOut, dependencies=[Depends(rate_limit_auth)])
def login(data: LoginIn, response: Response, db: DbSession):
    user = auth_service.authenticate(db, data.email, data.password)
    access, refresh = auth_service.issue_tokens(db, user)
    _set_refresh_cookie(response, refresh)
    return _token_out(user, access)


@router.get("/demo")
def demo_status():
    """Tells the login page whether to show the 'Try the demo' button."""
    return {"enabled": demo_service.demo_enabled(), "ttl_hours": settings.demo_ttl_hours}


@router.post("/demo", response_model=TokenOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit_auth)])
def demo_login(response: Response, db: DbSession):
    """Create a fresh private demo workspace with sample data and sign in to it.
    Returns 404 when DEMO_MODE is off."""
    user = demo_service.create_demo_user(db)
    access, refresh = auth_service.issue_tokens(db, user)
    _set_refresh_cookie(response, refresh)
    return _token_out(user, access)


@router.post("/refresh", response_model=TokenOut, dependencies=[Depends(rate_limit_auth)])
def refresh(request: Request, response: Response, db: DbSession):
    _require_csrf_header(request)
    try:
        user, access, new_refresh = auth_service.rotate_refresh(db, request.cookies.get(REFRESH_COOKIE))
    except Exception:
        _clear_refresh_cookie(response)
        raise
    _set_refresh_cookie(response, new_refresh)
    return _token_out(user, access)


@router.post("/logout", response_model=Message)
def logout(request: Request, response: Response, db: DbSession):
    _require_csrf_header(request)
    auth_service.revoke_refresh(db, request.cookies.get(REFRESH_COOKIE))
    _clear_refresh_cookie(response)
    return Message(message="Logged out")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
