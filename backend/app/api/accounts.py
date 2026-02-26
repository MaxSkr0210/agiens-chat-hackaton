"""Accounts API: GET me, PATCH me/mcp (Zapier at account level)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_account, get_db
from app.storage.models import AccountModel
from app.storage.repositories import account_set_mcp

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountMeOut(BaseModel):
    id: str
    channel: str
    externalId: str
    zapierMcpServerUrl: str | None = None


class SetMcpIn(BaseModel):
    serverUrl: str
    secret: str = ""


@router.get("/me", response_model=AccountMeOut)
async def get_me(account: AccountModel = Depends(get_current_account)):
    """Current account (from JWT). Zapier URL shown, secret never returned."""
    return AccountMeOut(
        id=account.id,
        channel=account.channel,
        externalId=account.external_id,
        zapierMcpServerUrl=account.zapier_mcp_server_url,
    )


@router.patch("/me/mcp")
async def set_me_mcp(
    body: SetMcpIn,
    account: AccountModel = Depends(get_current_account),
    session: AsyncSession = Depends(get_db),
):
    """Set Zapier MCP URL and secret for this account. Used by all user's chats (web + Telegram bot)."""
    updated = await account_set_mcp(
        session,
        account.id,
        server_url=body.serverUrl.strip() or None,
        secret=body.secret.strip() or None,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"ok": True}
