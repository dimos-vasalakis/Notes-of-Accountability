import time
import uuid
from collections import OrderedDict, deque
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core import security
from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, TooManyRequestsError
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import UserCreate

# In-memory per-account failed-login tracker: after MAX_FAILED_ATTEMPTS
# failures for the same (normalized) email within WINDOW_SECONDS, further
# login attempts for that email are locked out for LOCKOUT_SECONDS. This is
# a defense-in-depth layer on top of the IP-based RateLimitMiddleware: it
# stops credential-stuffing against one account from many IPs, which the IP
# limiter can't catch. Per-process only, same caveat as RateLimitMiddleware
# (backend/app/core/middleware.py) -- swap for a shared store (e.g. Redis)
# if this ever needs to hold across multiple workers/instances exactly.
_MAX_FAILED_ATTEMPTS = 5
_WINDOW_SECONDS = 15 * 60
_LOCKOUT_SECONDS = 15 * 60
_MAX_TRACKED_EMAILS = 10_000

_failed_attempts: OrderedDict[str, deque[float]] = OrderedDict()


def _check_and_record_lockout(email: str) -> None:
    now = time.monotonic()
    window_start = now - _WINDOW_SECONDS

    attempts = _failed_attempts.get(email)
    if attempts is not None:
        while attempts and attempts[0] < window_start:
            attempts.popleft()
        if not attempts:
            del _failed_attempts[email]
            attempts = None

    if attempts is not None and len(attempts) >= _MAX_FAILED_ATTEMPTS:
        retry_after = max(0.0, attempts[-1] + _LOCKOUT_SECONDS - now)
        if retry_after > 0:
            raise TooManyRequestsError(
                "Too many failed login attempts. Try again later.",
                retry_after_seconds=int(retry_after) + 1,
            )
        del _failed_attempts[email]


def _record_failed_attempt(email: str) -> None:
    attempts = _failed_attempts.get(email)
    if attempts is None:
        attempts = deque()
        _failed_attempts[email] = attempts
        if len(_failed_attempts) > _MAX_TRACKED_EMAILS:
            _failed_attempts.popitem(last=False)
    else:
        _failed_attempts.move_to_end(email)
    attempts.append(time.monotonic())


def _clear_failed_attempts(email: str) -> None:
    _failed_attempts.pop(email, None)


async def register_user(db: AsyncSession, data: UserCreate) -> User:
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing is not None:
        raise ConflictError("A user with this email already exists")

    user = User(email=data.email, hashed_password=security.hash_password(data.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    normalized_email = email.strip().lower()
    _check_and_record_lockout(normalized_email)

    user = await db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        # Pay the same bcrypt cost as a real check so response time doesn't
        # reveal whether the email exists.
        security.verify_password_timing_safe(password)
        _record_failed_attempt(normalized_email)
        return None

    if not security.verify_password(password, user.hashed_password):
        _record_failed_attempt(normalized_email)
        return None

    _clear_failed_attempts(normalized_email)
    return user


async def issue_tokens(db: AsyncSession, user: User) -> tuple[str, str]:
    access_token = security.create_access_token(str(user.id))
    refresh_token = security.create_refresh_token(str(user.id))

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=security.hash_token(refresh_token),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await db.commit()
    return access_token, refresh_token


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> tuple[str, str]:
    try:
        payload = security.decode_token(refresh_token)
    except Exception as exc:
        raise NotFoundError("Invalid refresh token") from exc

    if payload.get("type") != "refresh":
        raise NotFoundError("Invalid refresh token")

    token_hash = security.hash_token(refresh_token)
    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if stored is None:
        raise NotFoundError("Invalid refresh token")

    if stored.revoked:
        # This token was already rotated away. Seeing it again means either
        # a replayed request or a stolen refresh token being used after the
        # legitimate client already rotated it -- either way, the whole
        # session family is now suspect, so kill every session for this
        # user and force a fresh login.
        await revoke_all_refresh_tokens(db, stored.user_id)
        raise NotFoundError("Invalid refresh token")

    if stored.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise NotFoundError("Invalid refresh token")

    user = await db.get(User, stored.user_id)
    if user is None:
        raise NotFoundError("Invalid refresh token")

    stored.revoked = True
    await db.flush()

    return await issue_tokens(db, user)


async def revoke_refresh_token(db: AsyncSession, refresh_token: str) -> None:
    token_hash = security.hash_token(refresh_token)
    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if stored is not None:
        stored.revoked = True
        await db.commit()


async def revoke_all_refresh_tokens(db: AsyncSession, user_id: uuid.UUID) -> None:
    result = await db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False)
        )
    )
    for token in result:
        token.revoked = True
    await db.commit()
