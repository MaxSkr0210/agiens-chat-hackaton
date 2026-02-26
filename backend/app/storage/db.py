"""Async database engine and session. PostgreSQL via DATABASE_URL."""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)

# SQLAlchemy 2.0 style
class Base(DeclarativeBase):
    pass


def _get_engine_url() -> str:
    return get_settings().database_url


_engine = create_async_engine(
    _get_engine_url(),
    echo=get_settings().debug,
    future=True,
)

async_session_factory = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def _run_migrations(conn) -> None:
    """Create accounts table if missing; move Zapier to account level (drop from chats)."""
    await conn.execute(text(
        "CREATE TABLE IF NOT EXISTS accounts ("
        "id VARCHAR(36) PRIMARY KEY, "
        "channel VARCHAR(64) NOT NULL, "
        "external_id VARCHAR(255) NOT NULL, "
        "zapier_mcp_server_url VARCHAR(2048), "
        "zapier_mcp_secret VARCHAR(512), "
        "created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'), "
        "updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'), "
        "CONSTRAINT uq_accounts_channel_external UNIQUE (channel, external_id))"
    ))
    for sql in (
        "ALTER TABLE chats DROP COLUMN IF EXISTS zapier_mcp_server_url",
        "ALTER TABLE chats DROP COLUMN IF EXISTS zapier_mcp_secret",
    ):
        await conn.execute(text(sql))


async def init_db() -> None:
    """Create tables if they don't exist; run migrations for new columns. Retries on connection errors."""
    logger.info("Initializing database: %s", _get_engine_url())
    last_error = None
    for attempt in range(1, 6):
        try:
            async with _engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await _run_migrations(conn)
            return
        except Exception as e:
            last_error = e
            err_name = type(e).__name__
            if "InvalidPassword" in err_name or "password authentication" in str(e).lower():
                logger.error(
                    "PostgreSQL authentication failed. Check POSTGRES_USER/POSTGRES_PASSWORD in .env "
                    "match the credentials used when the DB was first created. "
                    "If you changed the password, run: docker compose down -v (then up again)."
                )
                raise
            logger.warning("DB init attempt %s/5 failed: %s", attempt, err_name)
            if attempt < 5:
                await asyncio.sleep(2.0 * attempt)
    raise last_error


async def close_db() -> None:
    await _engine.dispose()
