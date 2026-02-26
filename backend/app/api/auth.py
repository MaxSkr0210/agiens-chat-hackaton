"""Auth API: Telegram Login Widget -> JWT."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import create_token
from app.auth.telegram_verify import verify_telegram_login
from app.config import get_settings
from app.deps import get_db
from app.storage.repositories import account_get_or_create

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TelegramLoginIn(BaseModel):
    id: int
    first_name: str = ""
    last_name: str = ""
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class AuthOut(BaseModel):
    token: str
    accountId: str
    channel: str
    externalId: str


@router.post("/telegram", response_model=AuthOut)
async def login_telegram(
    body: TelegramLoginIn,
    session: AsyncSession = Depends(get_db),
):
    """
    Verify Telegram Login Widget data and return JWT.
    Frontend: use Telegram Login Widget (data-on-auth callback), then POST here.
    """
    settings = get_settings()
    bot_token = settings.telegram_bot_token or ""
    if not bot_token:
        raise HTTPException(
            status_code=503,
            detail="Telegram login not configured (TELEGRAM_BOT_TOKEN)",
        )
    ok = verify_telegram_login(
        bot_token,
        body.hash,
        body.auth_date,
        id=str(body.id),
        first_name=body.first_name,
        last_name=body.last_name or "",
        username=body.username or "",
        photo_url=body.photo_url or "",
    )
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid Telegram login data")
    account = await account_get_or_create(
        session,
        channel="telegram",
        external_id=str(body.id),
    )
    token = create_token(account.id)
    return AuthOut(
        token=token,
        accountId=account.id,
        channel=account.channel,
        externalId=account.external_id,
    )
