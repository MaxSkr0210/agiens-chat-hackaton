"""Zapier MCP client: list tools and call tools (Google Drive, Sheets, etc.) via zapier.com/mcp."""
import json
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

try:
    from mcp import ClientSession, types
    from mcp.client.streamable_http import streamable_http_client
    _MCP_AVAILABLE = True
except ImportError:
    ClientSession = None  # type: ignore[misc, assignment]
    types = None  # type: ignore[assignment]
    streamable_http_client = None  # type: ignore[misc, assignment]
    _MCP_AVAILABLE = False


def is_zapier_mcp_configured(
    server_url: str | None = None,
    secret: str | None = None,
) -> bool:
    """Return True if Zapier MCP is available: either (server_url, secret) or global env."""
    if server_url and secret:
        return True
    s = get_settings()
    return bool(s.zapier_mcp_server_url and s.zapier_mcp_secret)


async def get_zapier_tools(
    server_url: str | None = None,
    secret: str | None = None,
) -> list[dict[str, Any]]:
    """
    Connect to Zapier MCP, list tools. Use server_url/secret if provided, else global env.
    Returns [] if MCP is not configured or on error.
    """
    if not _MCP_AVAILABLE:
        logger.debug("MCP package not installed; install with: pip install mcp")
        return []
    url = (server_url or "").strip() or None
    sec = (secret or "").strip() or None
    if not url or not sec:
        s = get_settings()
        url = s.zapier_mcp_server_url
        sec = s.zapier_mcp_secret
    if not url or not sec:
        return []

    headers = {"Authorization": f"Bearer {sec}"}
    try:
        async with httpx.AsyncClient(
            headers=headers,
            timeout=30.0,
        ) as http_client:
            async with streamable_http_client(
                url,
                http_client=http_client,
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    tools = _mcp_tools_to_openrouter(result.tools)
                    logger.info("Zapier MCP: loaded %s tools", len(tools))
                    return tools
    except Exception as e:
        logger.warning("Zapier MCP list_tools failed: %s", e, exc_info=True)
        return []


def _mcp_tools_to_openrouter(mcp_tools: list[Any]) -> list[dict[str, Any]]:
    """Convert MCP Tool list to OpenRouter tools format (type: function, function: { name, description, parameters })."""
    out = []
    for t in mcp_tools:
        # MCP uses inputSchema (JSON Schema); OpenRouter uses "parameters" (same structure)
        params = getattr(t, "inputSchema", None) or {"type": "object", "properties": {}}
        if isinstance(params, dict) and "required" not in params:
            params = {**params, "required": []}
        out.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or f"Tool: {t.name}",
                "parameters": params,
            },
        })
    return out


async def call_zapier_tool(
    name: str,
    arguments: dict[str, Any] | None,
    server_url: str | None = None,
    secret: str | None = None,
) -> str:
    """
    Execute one Zapier MCP tool. Use server_url/secret if provided, else global env.
    """
    if not _MCP_AVAILABLE:
        return "MCP не установлен. Установите: pip install mcp"
    url = (server_url or "").strip() or None
    sec = (secret or "").strip() or None
    if not url or not sec:
        s = get_settings()
        url = s.zapier_mcp_server_url
        sec = s.zapier_mcp_secret
    if not url or not sec:
        return "Zapier MCP не настроен. Укажите ссылку и секрет в блоке Zapier MCP для этого чата (или в .env)."

    headers = {"Authorization": f"Bearer {sec}"}
    try:
        async with httpx.AsyncClient(
            headers=headers,
            timeout=60.0,
        ) as http_client:
            async with streamable_http_client(
                url,
                http_client=http_client,
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments or {})
                    return _call_tool_result_to_text(result)
    except Exception as e:
        logger.warning("Zapier MCP call_tool %s failed: %s", name, e, exc_info=True)
        return f"Ошибка вызова инструмента {name}: {e!s}"


def _call_tool_result_to_text(result: Any) -> str:
    """Extract plain text from MCP CallToolResult (content list of TextContent, etc.)."""
    if getattr(result, "isError", False) and getattr(result, "content", None):
        for c in result.content:
            if types and isinstance(c, types.TextContent):
                return c.text
        return "Tool returned an error (no message)."

    parts = []
    for c in getattr(result, "content", []) or []:
        if types and isinstance(c, types.TextContent):
            parts.append(c.text)
        elif hasattr(c, "text"):
            parts.append(str(c.text))
    if parts:
        return "\n".join(parts)

    if getattr(result, "structuredContent", None) is not None:
        return json.dumps(result.structuredContent, ensure_ascii=False, indent=0)

    return "OK"
