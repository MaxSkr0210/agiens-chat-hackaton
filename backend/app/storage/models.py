"""SQLAlchemy models for accounts, chats, messages, agents, tickets."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage.db import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class AccountModel(Base):
    """User account by channel (e.g. telegram) + external_id. Zapier MCP stored here for all user's chats."""
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    channel: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    zapier_mcp_server_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    zapier_mcp_secret: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("channel", "external_id", name="uq_accounts_channel_external"),)


class AgentModel(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(64), default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    model_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Comma-separated categories this agent handles (e.g. "technical,billing") for ticket routing
    supported_categories: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatModel(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    title: Mapped[str] = mapped_column(String(512), default="New chat")
    model_id: Mapped[str] = mapped_column(String(255), default="openrouter/auto")
    agent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    # Multi-channel: telegram, whatsapp, etc.
    channel: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages: Mapped[list["MessageModel"]] = relationship("MessageModel", back_populates="chat", order_by="MessageModel.created_at")


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    chat_id: Mapped[str] = mapped_column(String(36), ForeignKey("chats.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    chat: Mapped["ChatModel"] = relationship("ChatModel", back_populates="messages")


class TicketModel(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    chat_id: Mapped[str] = mapped_column(String(36), ForeignKey("chats.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="open")  # open, assigned, resolved, escalated
    category: Mapped[str] = mapped_column(String(128), default="general")
    assigned_agent_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
