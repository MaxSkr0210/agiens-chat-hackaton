"""Auth API: Telegram Login Widget -> JWT."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import create_token
from app.auth.telegram_verify import verify_telegram_login_from_payload
from app.config import get_settings
from app.deps import get_db
from app.storage.repositories import account_get_or_create

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthOut(BaseModel):
    token: str
    accountId: str
    channel: str
    externalId: str


@router.post("/telegram", response_model=AuthOut)
async def login_telegram(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """
    Verify Telegram Login Widget data and return JWT.
    Body — сырой JSON от виджета (id, first_name, last_name?, username?, photo_url?, auth_date, hash).
    Проверка hash делается только по полям, которые реально пришли (как в документации Telegram).
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")
    settings = get_settings()
    bot_token = settings.telegram_bot_token or ""
    if not bot_token:
        raise HTTPException(
            status_code=503,
            detail="Telegram login not configured (TELEGRAM_BOT_TOKEN)",
        )
    if not verify_telegram_login_from_payload(bot_token, payload):
        raise HTTPException(status_code=401, detail="Invalid Telegram login data")
    user_id = payload.get("id")
    if user_id is None:
        raise HTTPException(status_code=400, detail="Missing id in Telegram login data")
    account = await account_get_or_create(
        session,
        channel="telegram",
        external_id=str(user_id),
    )
    token = create_token(account.id)
    return AuthOut(
        token=token,
        accountId=account.id,
        channel=account.channel,
        externalId=account.external_id,
    )
