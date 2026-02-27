"""FastAPI application: universal chat API with pluggable LLM."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api import accounts, agents, auth, chats, tickets, voice_temp
from app.config import get_settings
from app.llm.openrouter import OpenRouterProvider
from app.llm.registry import llm_registry
from app.redis_client import close_redis, init_redis
from app.storage.db import close_db, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Register LLM providers (add more here for new backends)
    openrouter = OpenRouterProvider(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )
    llm_registry.register(openrouter)
    # PostgreSQL
    await init_db()
    # Redis (optional: sessions, cache)
    await init_redis(settings.redis_url)
    try:
        yield
    finally:
        await close_redis()
        await close_db()


app = FastAPI(
    title="Agiens API",
    description="Universal chat backend with pluggable LLM",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()

print(settings.cors_origin_list)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return 500 as JSON so CORS middleware adds headers; let HTTPException through."""
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(agents.router)
app.include_router(chats.router)
app.include_router(tickets.router)
app.include_router(voice_temp.router)


@app.get("/health")
def health():
    from app.mcp.playwright_client import is_playwright_mcp_available
    return {
        "status": "ok",
        "playwright_mcp_enabled": get_settings().playwright_mcp_enabled,
        "playwright_mcp_available": is_playwright_mcp_available(),
    }
