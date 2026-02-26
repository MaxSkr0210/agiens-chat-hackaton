"""Application configuration from environment."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "agiens-api"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 3001

    # CORS (comma-separated origins, e.g. http://localhost:3000,http://127.0.0.1:3000)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # LLM: OpenRouter (default provider)
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # LLM: optional overrides per provider (for future providers)
    # OPENAI_API_KEY, ANTHROPIC_API_KEY, etc. can be added here when needed

    # PostgreSQL (primary DB for chats, agents, tickets)
    database_url: str = "postgresql+asyncpg://agiens:agiens@localhost:5432/agiens"

    # Redis (optional: sessions, cache, rate limit)
    redis_url: Optional[str] = None

    # ElevenLabs: STT/TTS
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel (default)
    elevenlabs_tts_model: str = "eleven_multilingual_v2"
    elevenlabs_stt_model: str = "scribe_v2"
    # Отключить проверку SSL к API (например за корп. прокси с самоподписанным сертификатом)
    elevenlabs_verify_ssl: bool = True
    # Прокси для запросов к ElevenLabs (чтобы трафик шёл через VPN). Пример: http://127.0.0.1:1080 или socks5://127.0.0.1:1080
    elevenlabs_http_proxy: Optional[str] = None

    # MCP: Zapier (global fallback; per-account in DB)
    zapier_mcp_server_url: Optional[str] = None
    zapier_mcp_secret: Optional[str] = None

    # Telegram bot (for widget verification and bot)
    telegram_bot_token: Optional[str] = None

    # Auth: Telegram Login Widget + JWT (same bot token verifies widget hash)
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 30 * 24 * 3600  # 30 days

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if not origins:
            return ["http://localhost:3000", "http://127.0.0.1:3000", "https://0e75-2a12-bec4-1bb0-1325-00-2.ngrok-free.app"]
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
