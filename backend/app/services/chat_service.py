"""Chat service: send message to LLM, persist, return response."""
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import ChatMessage
from app.llm.registry import get_llm_registry
from app.mcp.zapier_client import call_zapier_tool, get_zapier_tools, is_zapier_mcp_configured
from app.storage.repositories import (
    account_get_by_channel,
    account_get_or_create,
    agent_get,
    chat_get_with_messages,
    chat_set_model,
    chat_set_agent,
    chat_update_title,
    message_add,
)


async def get_system_prompt(session: AsyncSession, agent_id: str | None) -> str | None:
    if not agent_id:
        return None
    agent = await agent_get(session, agent_id)
    if not agent or not agent.system_prompt:
        return None
    return agent.system_prompt


async def resolve_model_for_chat(session: AsyncSession, chat_id: str, requested_model_id: str | None) -> str:
    """Resolve which model to use: request override, else chat's model_id, else default."""
    chat = await chat_get_with_messages(session, chat_id)
    if not chat:
        return requested_model_id or "openrouter/auto"
    if requested_model_id:
        return requested_model_id
    return chat.model_id or "openrouter/auto"


MAX_TOOL_ROUNDS = 5


async def generate_reply(
    session: AsyncSession,
    chat_id: str,
    user_message: str,
    model_id: str | None = None,
) -> str:
    """Load chat history, call LLM (with optional MCP tools), return assistant content."""
    chat = await chat_get_with_messages(session, chat_id)
    if not chat:
        raise ValueError("Chat not found")
    effective_model = model_id or chat.model_id or "openrouter/auto"
    registry = get_llm_registry()
    resolved = registry.get_provider_for_model(effective_model)
    if not resolved:
        return "No LLM provider configured for this model. Please set OPENROUTER_API_KEY or add another provider."
    _provider_id, provider = resolved
    system_prompt = await get_system_prompt(session, chat.agent_id)
    messages: list[ChatMessage] = [
        ChatMessage(role=m.role, content=m.content)
        for m in chat.messages
    ]
    messages.append(ChatMessage(role="user", content=user_message))

    # Zapier MCP: per-account (channel+external_id). Web chats without channel use env.
    mcp_url = None
    mcp_secret = None
    if chat.channel and chat.external_id:
        acc = await account_get_or_create(session, chat.channel, chat.external_id)
        mcp_url = acc.zapier_mcp_server_url
        mcp_secret = acc.zapier_mcp_secret
    tools: list[dict] = []
    if is_zapier_mcp_configured(mcp_url, mcp_secret):
        tools = await get_zapier_tools(mcp_url, mcp_secret)

    for _ in range(MAX_TOOL_ROUNDS):
        response = await provider.chat(
            messages=messages,
            model_id=effective_model,
            system_prompt=system_prompt,
            tools=tools if tools else None,
        )
        if not response.tool_calls:
            return response.content or ""

        # Append assistant message with tool_calls, then run tools and append tool results
        messages.append(
            ChatMessage(
                role="assistant",
                content=response.content or None,
                tool_calls=response.tool_calls,
            )
        )
        for tc in response.tool_calls:
            fn = (tc or {}).get("function") or {}
            name = fn.get("name") or ""
            args_str = fn.get("arguments") or "{}"
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}
            result = await call_zapier_tool(name, args, mcp_url, mcp_secret)
            call_id = (tc or {}).get("id") or ""
            messages.append(
                ChatMessage(role="tool", content=result, tool_call_id=call_id)
            )
        # Next iteration: LLM will see tool results and may return text or more tool_calls
    return response.content or "(Достигнут лимит вызовов инструментов.)"
