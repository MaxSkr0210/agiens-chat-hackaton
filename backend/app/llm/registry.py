"""Central registry for LLM providers. Add any provider by registering it here."""
from typing import Optional

from app.llm.base import LLMProvider


class LLMRegistry:
    """Registry of LLM providers. Supports multiple providers; each can expose multiple model IDs."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> Optional[LLMProvider]:
        return self._providers.get(provider_id)

    def get_provider_for_model(self, model_id: str) -> Optional[tuple[str, LLMProvider]]:
        """
        Resolve model_id to a provider. By default we use 'openrouter' for OpenRouter models.
        Custom logic: model_id can be 'openrouter/<path>' or '<provider_id>/<model>' for future providers.
        """
        if "/" in model_id:
            prefix, _ = model_id.split("/", 1)
            if prefix in self._providers:
                return prefix, self._providers[prefix]
        # Default to openrouter if no prefix (e.g. legacy model ids)
        if "openrouter" in self._providers:
            return "openrouter", self._providers["openrouter"]
        return None

    def list_available_providers(self) -> list[tuple[str, LLMProvider]]:
        return [(pid, p) for pid, p in self._providers.items() if p.is_available()]


# Global registry; populated in main.py
llm_registry = LLMRegistry()


def get_llm_registry() -> LLMRegistry:
    return llm_registry
