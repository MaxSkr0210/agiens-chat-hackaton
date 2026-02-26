"""ElevenLabs STT and TTS. Uses official SDK (sync calls run in thread pool)."""
import asyncio
import base64
import io
import logging
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def _client():
    """Lazy ElevenLabs client to avoid import at module load when key is missing."""
    from elevenlabs.client import ElevenLabs
    settings = get_settings()
    if not settings.elevenlabs_api_key:
        return None
    kwargs = {"api_key": settings.elevenlabs_api_key}
    if not settings.elevenlabs_verify_ssl:
        kwargs["httpx_client"] = httpx.Client(verify=False)
    return ElevenLabs(**kwargs)


def is_available() -> bool:
    return bool(get_settings().elevenlabs_api_key)


def _stt_sync(audio_bytes: bytes, filename: str, model_id: str) -> Optional[str]:
    """Sync STT (run in thread). Prefer filename with .webm for browser recordings."""
    from elevenlabs.client import ElevenLabs
    settings = get_settings()
    kwargs = {"api_key": settings.elevenlabs_api_key}
    if not settings.elevenlabs_verify_ssl:
        kwargs["httpx_client"] = httpx.Client(verify=False)
    client = ElevenLabs(**kwargs)
    if not audio_bytes or len(audio_bytes) < 100:
        logger.warning("STT: audio too short or empty (%s bytes)", len(audio_bytes) if audio_bytes else 0)
        return None
    file_obj = io.BytesIO(audio_bytes)
    file_obj.name = filename or "audio.webm"
    # Omit language_code for auto-detect; API rejects "auto"
    result = client.speech_to_text.convert(
        file=file_obj,
        model_id=model_id,
    )
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
    kwargs = {"api_key": settings.elevenlabs_api_key}
    if not settings.elevenlabs_verify_ssl:
        kwargs["httpx_client"] = httpx.Client(verify=False)
    client = ElevenLabs(**kwargs)
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
