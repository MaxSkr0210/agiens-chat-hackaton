"""ElevenLabs STT and TTS. Uses official SDK (sync calls run in thread pool)."""
import asyncio
import base64
import io
import logging
import threading
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Один общий HTTP-клиент для всех запросов к ElevenLabs через прокси — иначе Privoxy выдаёт "503 Too many open connections"
# Lock вокруг вызова API: один общий клиент не должен использоваться из двух потоков одновременно
_shared_httpx_client: Optional[httpx.Client] = None
_shared_httpx_client_lock = threading.Lock()
_elevenlabs_call_lock = threading.Lock()


def _httpx_client_kwargs() -> dict:
    """Build httpx.Client kwargs for ElevenLabs (proxy, verify). Used so all requests go through VPN/proxy."""
    settings = get_settings()
    kwargs: dict = {"verify": settings.elevenlabs_verify_ssl}
    if settings.elevenlabs_http_proxy:
        kwargs["proxy"] = settings.elevenlabs_http_proxy
    return kwargs


def _need_custom_httpx() -> bool:
    s = get_settings()
    return not s.elevenlabs_verify_ssl or bool(s.elevenlabs_http_proxy)


def _get_shared_httpx_client() -> httpx.Client:
    """Возвращает один переиспользуемый httpx.Client (прокси/verify). Потокобезопасно."""
    global _shared_httpx_client
    with _shared_httpx_client_lock:
        if _shared_httpx_client is None:
            _shared_httpx_client = httpx.Client(**_httpx_client_kwargs())
        return _shared_httpx_client


def _client():
    """Lazy ElevenLabs client to avoid import at module load when key is missing."""
    from elevenlabs.client import ElevenLabs
    settings = get_settings()
    if not settings.elevenlabs_api_key:
        return None
    kwargs = {"api_key": settings.elevenlabs_api_key}
    if _need_custom_httpx():
        kwargs["httpx_client"] = _get_shared_httpx_client()
    return ElevenLabs(**kwargs)


def is_available() -> bool:
    return bool(get_settings().elevenlabs_api_key)


def _stt_sync(audio_bytes: bytes, filename: str, model_id: str) -> Optional[str]:
    """Sync STT (run in thread). Prefer filename with .webm for browser recordings."""
    from elevenlabs.client import ElevenLabs
    settings = get_settings()
    client_kwargs = {"api_key": settings.elevenlabs_api_key}
    if _need_custom_httpx():
        client_kwargs["httpx_client"] = _get_shared_httpx_client()
    client = ElevenLabs(**client_kwargs)
    if not audio_bytes or len(audio_bytes) < 100:
        logger.warning("STT: audio too short or empty (%s bytes)", len(audio_bytes) if audio_bytes else 0)
        return None
    file_obj = io.BytesIO(audio_bytes)
    file_obj.name = filename or "audio.webm"
    # Один общий клиент — вызов под lock, чтобы не использовать его из двух потоков одновременно
    if _need_custom_httpx():
        with _elevenlabs_call_lock:
            result = client.speech_to_text.convert(file=file_obj, model_id=model_id)
    else:
        result = client.speech_to_text.convert(file=file_obj, model_id=model_id)
    if hasattr(result, "text"):
        return result.text
    if isinstance(result, str):
        return result
    if hasattr(result, "transcript"):
        return result.transcript
    # API can return object with .words (list of {text, start, end, ...})
    if hasattr(result, "words") and result.words:
        parts = []
        for w in result.words:
            t = getattr(w, "text", None) if not isinstance(w, dict) else w.get("text")
            if t:
                parts.append(t)
        return " ".join(parts) if parts else None
    return str(result) if result else None


def _tts_sync(text: str, voice_id: str, model_id: str) -> Optional[bytes]:
    """Sync TTS (run in thread)."""
    from elevenlabs.client import ElevenLabs
    settings = get_settings()
    client_kwargs = {"api_key": settings.elevenlabs_api_key}
    if _need_custom_httpx():
        client_kwargs["httpx_client"] = _get_shared_httpx_client()
    client = ElevenLabs(**client_kwargs)
    if _need_custom_httpx():
        with _elevenlabs_call_lock:
            audio = client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=model_id,
                output_format="mp3_44100_128",
            )
    else:
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            output_format="mp3_44100_128",
        )
    if hasattr(audio, "read"):
        return audio.read()
    if isinstance(audio, bytes):
        return audio
    if hasattr(audio, "__iter__") and not isinstance(audio, (str, bytes)):
        return b"".join(audio)
    return None


def _log_elevenlabs_error(method: str, e: Exception) -> None:
    """Log ElevenLabs error; avoid traceback for known API restrictions (302/geo)."""
    try:
        from elevenlabs.core.api_error import ApiError
        if isinstance(e, ApiError) and e.status_code == 302:
            logger.warning(
                "ElevenLabs %s: API returned 302 redirect. Access may be restricted in this region/country. See https://help.elevenlabs.io/hc/en-us/articles/22497891312401",
                method,
            )
            return
    except ImportError:
        pass
    logger.warning("ElevenLabs %s failed: %s", method, e, exc_info=True)


async def speech_to_text(audio_bytes: bytes, filename: str = "audio.webm") -> Optional[str]:
    """Transcribe audio to text. Returns None if not configured or on error."""
    if not _client():
        return None
    settings = get_settings()
    try:
        return await asyncio.to_thread(
            _stt_sync,
            audio_bytes,
            filename,
            settings.elevenlabs_stt_model,
        )
    except Exception as e:
        _log_elevenlabs_error("STT", e)
        return None


async def text_to_speech(text: str) -> Optional[bytes]:
    """Synthesize text to MP3. Returns None if not configured or on error."""
    if not text.strip() or not _client():
        return None
    settings = get_settings()
    try:
        return await asyncio.to_thread(
            _tts_sync,
            text,
            settings.elevenlabs_voice_id,
            settings.elevenlabs_tts_model,
        )
    except Exception as e:
        _log_elevenlabs_error("TTS", e)
        return None


async def text_to_speech_base64(text: str) -> Optional[str]:
    """TTS and return base64-encoded MP3 for JSON response."""
    raw = await text_to_speech(text)
    return base64.b64encode(raw).decode("ascii") if raw else None
