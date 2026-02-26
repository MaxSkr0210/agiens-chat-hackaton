"""Optional Redis client for sessions, cache, rate limit. No-op when REDIS_URL is not set."""
from typing import Optional

from redis.asyncio import Redis

_redis: Optional[Redis] = None


async def init_redis(url: Optional[str]) -> None:
    global _redis
    if url:
        _redis = Redis.from_url(url, decode_responses=True)


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


def get_redis() -> Optional[Redis]:
    return _redis
