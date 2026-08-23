import uuid

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.db import get_db
from app.models.user import User


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    access_token: str | None = Cookie(default=None),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    if access_token is None:
        raise credentials_exception

    try:
        payload = security.decode_token(access_token)
    except jwt.PyJWTError as exc:
        raise credentials_exception from exc

    if payload.get("type") != "access":
        raise credentials_exception

    try:
        user_id = uuid.UUID(payload.get("sub"))
    except (TypeError, ValueError) as exc:
        raise credentials_exception from exc

    user = await db.get(User, user_id)
    if user is None:
        raise credentials_exception

    return user
