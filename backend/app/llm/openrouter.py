"""OpenRouter LLM provider — compatible with OpenRouter API (multiple models)."""
import json
import logging
import os
from typing import Any, AsyncIterator

import httpx

from app.llm.base import ChatMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


def _message_to_api(m: ChatMessage) -> dict[str, Any]:
    """Convert ChatMessage to OpenRouter API message format (supports tool_calls and tool role)."""
    out: dict[str, Any] = {"role": m.role}
    if m.role == "tool":
        out["content"] = m.content or ""
        if m.tool_call_id:
            out["tool_call_id"] = m.tool_call_id
        return out
    if m.tool_calls:
        out["content"] = m.content if m.content else None
        out["tool_calls"] = m.tool_calls
        return out
    out["content"] = m.content or ""
    return out


class OpenRouterProvider(LLMProvider):
    provider_id = "openrouter"
    display_name = "OpenRouter"

    def __init__(self, api_key: str | None = None, base_url: str = "https://openrouter.ai/api/v1"):
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self._base_url = base_url.rstrip("/")

    def is_available(self) -> bool:
        return bool(self._api_key)

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
        if not self._api_key:
            return LLMResponse(
                content="OpenRouter API key is not configured. Set OPENROUTER_API_KEY.",
                model_used=model_id,
                finish_reason="error",
            )
        openrouter_model = model_id if model_id.startswith("openrouter/") or "/" in model_id else f"openrouter/{model_id}"
        body: dict = {
            "model": openrouter_model,
            "messages": [_message_to_api(m) for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            body["messages"] = [{"role": "system", "content": system_prompt}] + body["messages"]
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self._base_url,
                },
                json=body,
            )
            if r.status_code >= 400:
                try:
                    err_body = r.text
                    if len(err_body) > 500:
                        err_body = err_body[:500] + "..."
                    logger.warning("OpenRouter API error %s: %s", r.status_code, err_body)
                except Exception:
                    pass
                if r.status_code == 500:
                    return LLMResponse(
                        content="Сервис LLM временно недоступен (ошибка 500). Попробуйте через минуту или выберите другую модель.",
                        model_used=model_id,
                        finish_reason="error",
                    )
                if r.status_code == 401:
                    return LLMResponse(
                        content="Неверный API-ключ OpenRouter. Проверьте OPENROUTER_API_KEY.",
                        model_used=model_id,
                        finish_reason="error",
                    )
                if r.status_code == 429:
                    return LLMResponse(
                        content="Превышен лимит запросов к OpenRouter. Подождите и попробуйте снова.",
                        model_used=model_id,
                        finish_reason="error",
                    )
                r.raise_for_status()
            data = r.json()
        choices = data.get("choices") or []
        if not choices:
            return LLMResponse(content="", model_used=openrouter_model, finish_reason="unknown")
        c = choices[0]
        msg = c.get("message") or {}
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls")
        return LLMResponse(
            content=content if content else "",
            model_used=data.get("model") or openrouter_model,
            finish_reason=c.get("finish_reason"),
            tool_calls=tool_calls,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        model_id: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        if not self._api_key:
            yield "OpenRouter API key is not configured."
            return
        openrouter_model = model_id if "/" in model_id else f"openrouter/{model_id}"
        body: dict = {
            "model": openrouter_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if system_prompt:
            body["messages"] = [{"role": "system", "content": system_prompt}] + body["messages"]

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self._base_url,
                },
                json=body,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        if line == "data: [DONE]":
                            break
                        import json
                        try:
                            data = json.loads(line[6:])
                            for chunk in (data.get("choices") or []):
                                delta = (chunk.get("delta") or {})
                                content = delta.get("content")
                                if content:
                                    yield content
                        except Exception:
                            pass
