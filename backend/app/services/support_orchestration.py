"""Support orchestration: classify ticket with LLM, route to agent by category."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import ChatMessage
from app.llm.registry import get_llm_registry
from app.storage.repositories import (
    agents_supporting_category,
    agent_list,
    chat_set_agent,
    ticket_get,
    ticket_update,
)

# Categories used for classification and routing
SUPPORT_CATEGORIES = "technical, billing, general, other"


async def classify_support_message(text: str) -> str:
    """
    Use LLM to classify support message into one of the configured categories.
    Returns category string (e.g. technical, billing, general, other).
    """
    registry = get_llm_registry()
    resolved = registry.get_provider_for_model("openrouter/auto")
    if not resolved:
        return "general"
    _pid, provider = resolved
    prompt = (
        f"Classify this support request into exactly one category. "
        f"Categories: {SUPPORT_CATEGORIES}. Reply with only the single category word, nothing else.\n\n"
        f"Request: {text[:500]}"
    )
    response = await provider.chat(
        messages=[ChatMessage(role="user", content=prompt)],
        model_id="openrouter/auto",
        max_tokens=20,
    )
    raw = (response.content or "").strip().lower()
    for cat in SUPPORT_CATEGORIES.split(","):
        if cat.strip() in raw or raw == cat.strip():
            return cat.strip()
    return "general"


async def route_ticket_to_agent(session: AsyncSession, ticket_id: str, category: str) -> bool:
    """
    Assign ticket to an agent that supports this category.
    If found, updates ticket (assigned_agent_id, status=assigned) and chat's agent_id.
    Returns True if assigned.
    """
    ticket = await ticket_get(session, ticket_id)
    if not ticket:
        return False
    agents = await agents_supporting_category(session, category)
    if not agents:
        agents = await agent_list(session)
    if not agents:
        return False
    agent = agents[0]
    await ticket_update(
        session,
        ticket_id,
        assigned_agent_id=agent.id,
        status="assigned",
    )
    await chat_set_agent(session, ticket.chat_id, agent.id)
    return True
