"""Temporary voice URL for external channels (e.g. WhatsApp needs a public URL for media)."""
import base64
import time
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

# In-memory: id -> (bytes, timestamp). Expire after 120s.
_voice_temp: dict[str, tuple[bytes, float]] = {}
_TTL = 120


class TempVoiceIn(BaseModel):
    audioBase64: str


router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/temp")
def create_temp_voice(body: TempVoiceIn) -> dict:
    """Store base64 audio, return { id }. Use GET /api/voice/temp/{id} to retrieve (URL for Twilio etc.)."""
    b64 = body.audioBase64
    if not b64:
        raise HTTPException(status_code=400, detail="audioBase64 required")
    try:
        raw = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64")
    id = str(uuid.uuid4())
    _voice_temp[id] = (raw, time.time())
    # Prune old
    for k in list(_voice_temp):
        if time.time() - _voice_temp[k][1] > _TTL:
            del _voice_temp[k]
    return {"id": id}


@router.get("/temp/{id}")
def get_temp_voice(id: str) -> Response:
    """Return audio bytes (MP3). One-time: removed after first read."""
    if id not in _voice_temp:
        raise HTTPException(status_code=404, detail="Not found or expired")
    raw, _ = _voice_temp.pop(id)
    return Response(content=raw, media_type="audio/mpeg")
