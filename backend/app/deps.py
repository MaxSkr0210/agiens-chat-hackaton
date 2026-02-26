"""Shared FastAPI dependencies."""
from typing import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import decode_token
from app.storage.db import get_session
from app.storage.models import AccountModel
from app.storage.repositories import account_get


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session() as session:
        yield session


async def get_current_account(
    authorization: str | None = Header(None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> AccountModel:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization")
    token = authorization[7:].strip()
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    account = await account_get(session, payload["sub"])
    if not account:
        raise HTTPException(status_code=401, detail="Account not found")
    return account


async def get_optional_account(
    authorization: str | None = Header(None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> AccountModel | None:
    """Return account if valid JWT present, else None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        return None
    return await account_get(session, payload["sub"])
