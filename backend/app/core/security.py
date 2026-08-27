import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# Fixed hash to check against when no user was found, so login for a
# nonexistent email still pays the bcrypt cost -- keeps response time
# indistinguishable from a wrong-password attempt and avoids leaking
# account existence via timing.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt()).decode("utf-8")


def verify_password_timing_safe(password: str) -> bool:
    bcrypt.checkpw(password.encode("utf-8"), _DUMMY_HASH.encode("utf-8"))
    return False


def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    return _create_token(
        subject,
        timedelta(minutes=settings.access_token_expire_minutes),
        token_type="access",
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject,
        timedelta(days=settings.refresh_token_expire_days),
        token_type="refresh",
    )


# Tolerance for clock skew between minting and validating a token. Without it,
# a backward clock correction (NTP resync, a suspended VM catching up, or two
# app instances a few seconds apart) puts a fresh token's `iat` in the future
# and PyJWT raises ImmatureSignatureError -- surfacing as a spurious 401 that
# logs the user out. 60s is the common default and is negligible against a
# 45-minute access token.
_CLOCK_SKEW_LEEWAY = timedelta(seconds=60)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        leeway=_CLOCK_SKEW_LEEWAY,
    )


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
