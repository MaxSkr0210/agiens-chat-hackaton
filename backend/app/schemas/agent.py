"""Request/response schemas for agents."""
from typing import Optional

from pydantic import BaseModel


class AgentOut(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    systemPrompt: str
    modelId: Optional[str] = None
    supportedCategories: Optional[str] = None  # Comma-separated, for ticket routing


class AgentCreateIn(BaseModel):
    name: str
    description: str = ""
    systemPrompt: str = ""
    icon: Optional[str] = None
    supportedCategories: Optional[str] = None


class AgentUpdateIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    systemPrompt: Optional[str] = None
    modelId: Optional[str] = None
    supportedCategories: Optional[str] = None
