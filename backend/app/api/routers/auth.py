from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.db import get_db
from app.core.exceptions import NotFoundError, TooManyRequestsError
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserPublic
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = settings.cookie_secure if settings.cookie_secure is not None else settings.environment != "development"
    samesite = settings.cookie_samesite
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        httponly=True,
        samesite=samesite,
        secure=secure,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        httponly=True,
        samesite=samesite,
        secure=secure,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")


@router.post("/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def signup(
    data: UserCreate, response: Response, db: AsyncSession = Depends(get_db)
) -> User:
    user = await auth_service.register_user(db, data)
    access_token, refresh_token = await auth_service.issue_tokens(db, user)
    _set_auth_cookies(response, access_token, refresh_token)
    return user


@router.post("/login", response_model=UserPublic)
async def login(
    data: UserLogin, response: Response, db: AsyncSession = Depends(get_db)
) -> User:
    try:
        user = await auth_service.authenticate_user(db, data.email, data.password)
    except TooManyRequestsError as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc

    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    access_token, refresh_token = await auth_service.issue_tokens(db, user)
    _set_auth_cookies(response, access_token, refresh_token)
    return user


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> None:
    if refresh_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")

    try:
        new_access, new_refresh = await auth_service.refresh_access_token(
            db, refresh_token
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    _set_auth_cookies(response, new_access, new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> None:
    if refresh_token is not None:
        await auth_service.revoke_refresh_token(db, refresh_token)
    _clear_auth_cookies(response)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke every refresh token for the current user, signing out all devices."""
    await auth_service.revoke_all_refresh_tokens(db, current_user.id)
    _clear_auth_cookies(response)


@router.get("/me", response_model=UserPublic)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
