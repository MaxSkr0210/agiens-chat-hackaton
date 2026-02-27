"""Verify Telegram Login Widget hash (https://core.telegram.org/widgets/login)."""
import hashlib
import hmac
import time
from typing import Any


def verify_telegram_login(
    bot_token: str,
    received_hash: str,
    auth_date: int,
    **fields: Any,
) -> bool:
    """
    Verify that the login data came from Telegram.
    fields: id, first_name, last_name, username, photo_url (as sent by widget).
    auth_date must be within 24 hours.
    """
    if not bot_token or not received_hash:
        return False
    if abs(time.time() - auth_date) > 86400:  # 24h
        return False
    data = {k: v for k, v in fields.items() if v is not None and k != "hash"}
    data["auth_date"] = str(auth_date)
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, received_hash)


def verify_telegram_login_from_payload(bot_token: str, payload: dict[str, Any]) -> bool:
    """
    Проверка по сырому payload от виджета: в data-check-string входят только те поля,
    которые реально присланы (документация Telegram: "all received fields").
    """
    if not bot_token:
        return False
    received_hash = payload.get("hash")
    if not received_hash:
        return False
    auth_date = payload.get("auth_date")
    if auth_date is None:
        return False
    try:
        auth_date_int = int(auth_date)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - auth_date_int) > 86400:
        return False
    data = {k: str(v) if v is not None else "" for k, v in payload.items() if k != "hash"}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, received_hash)
