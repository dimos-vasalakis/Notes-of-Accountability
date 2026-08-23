from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import UserCreate


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
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not security.verify_password(password, user.hashed_password):
        return None
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
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash, RefreshToken.revoked.is_(False)
        )
    )
    if stored is None or stored.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
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
