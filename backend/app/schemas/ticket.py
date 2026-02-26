"""Request/response schemas for tickets."""
from typing import Optional

from pydantic import BaseModel


class TicketCreateIn(BaseModel):
    chatId: str


class TicketOut(BaseModel):
    id: str
    chatId: str
    status: str
    category: str
    assignedAgentId: Optional[str] = None
    priority: int
    createdAt: str
    updatedAt: str


class TicketUpdateIn(BaseModel):
    status: Optional[str] = None
    category: Optional[str] = None
    assignedAgentId: Optional[str] = None
    priority: Optional[int] = None
