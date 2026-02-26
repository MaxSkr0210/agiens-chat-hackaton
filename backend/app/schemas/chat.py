"""Request/response schemas for chats and messages."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    createdAt: str  # ISO datetime

    class Config:
        from_attributes = True


class ChatSummaryOut(BaseModel):
    id: str
    title: str
    model: str
    lastMessagePreview: str
    lastMessageAt: str  # ISO datetime


class ChatWithMessagesOut(BaseModel):
    id: str
    title: str
    modelId: str
    agentId: Optional[str] = None
    messages: list[MessageOut]


class SendMessageIn(BaseModel):
    message: str
    modelId: Optional[str] = None
    withVoice: bool = False  # Level 2 Voice: TTS response for text messages


class SendMessageOut(BaseModel):
    content: str
    audioBase64: Optional[str] = None  # Present when withVoice=True (ElevenLabs TTS)


class SetModelIn(BaseModel):
    modelId: str


class SetAgentIn(BaseModel):
    agentId: str


class CreateChatIn(BaseModel):
    modelId: Optional[str] = None
    channel: Optional[str] = None  # telegram, whatsapp
    externalId: Optional[str] = None  # telegram chat_id, whatsapp number
