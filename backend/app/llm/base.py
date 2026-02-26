"""Base interface for any LLM provider — implement this to add a new model/provider."""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system" | "tool"
    content: str | None = ""
    tool_calls: list[dict[str, Any]] | None = None  # [{id, type, function: {name, arguments}}]
    tool_call_id: str | None = None  # for role="tool"


class LLMResponse(BaseModel):
    content: str
    model_used: str
    finish_reason: str | None = None
    tool_calls: list[dict[str, Any]] | None = Field(default=None, description="When model requests tool use")


class LLMProvider(ABC):
    """Abstract LLM provider. Register implementations in app.llm.registry."""

    provider_id: str  # e.g. "openrouter", "openai", "anthropic"
    display_name: str = ""

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model_id: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Send chat completion request. model_id is provider-specific. tools = OpenRouter-style tool definitions."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[ChatMessage],
        model_id: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream chat completion (optional; can raise NotImplementedError)."""
        ...

    def is_available(self) -> bool:
        """Whether this provider is configured (e.g. API key set)."""
        return True
