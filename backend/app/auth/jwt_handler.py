"""JWT create and verify for account auth."""
import time
from typing import Any

import jwt

from app.config import get_settings


def create_token(account_id: str) -> str:
    settings = get_settings()
    return jwt.encode(
        {"sub": account_id, "exp": int(time.time()) + settings.jwt_expire_seconds},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        settings = get_settings()
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except Exception:
        return None
