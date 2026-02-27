"""Playwright MCP client: list and call tools via local npx @playwright/mcp (stdio)."""
import json
import logging
import sys
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

# Tool names exposed to LLM are prefixed to avoid clashes with Zapier and route calls
PLAYWRIGHT_TOOL_PREFIX = "playwright_"

_MCP_AVAILABLE = False
_STDIO_AVAILABLE = False
ClientSession = None  # type: ignore[misc, assignment]
types = None  # type: ignore[assignment]
stdio_client = None  # type: ignore[misc, assignment]
StdioServerParameters = None  # type: ignore[misc, assignment]

try:
    from mcp import ClientSession, types
    _MCP_AVAILABLE = True
except ImportError:
    pass

try:
    from mcp.client.stdio import stdio_client, StdioServerParameters
    _STDIO_AVAILABLE = True
except ImportError:
    pass


def is_playwright_mcp_available() -> bool:
    """True if MCP and stdio client are available and Playwright MCP is enabled in config."""
    if not _MCP_AVAILABLE or not _STDIO_AVAILABLE:
        return False
    return get_settings().playwright_mcp_enabled


def _server_params() -> Any:
    """StdioServerParameters for npx -y @playwright/mcp."""
    if StdioServerParameters is None:
        raise RuntimeError("MCP stdio not available")
    return StdioServerParameters(
        command="npx",
        args=["-y", "@playwright/mcp"],
        env=None,
        cwd=None,
        encoding="utf-8",
    )


def _mcp_tools_to_openrouter(mcp_tools: list[Any], prefix: str) -> list[dict[str, Any]]:
    """Convert MCP tools to OpenRouter format; add prefix to tool names."""
    out = []
    for t in mcp_tools:
        params = getattr(t, "inputSchema", None) or {"type": "object", "properties": {}}
        if isinstance(params, dict) and "required" not in params:
            params = {**params, "required": []}
        name = getattr(t, "name", "") or ""
        out.append({
            "type": "function",
            "function": {
                "name": prefix + name,
                "description": (getattr(t, "description", None) or f"Playwright: {name}"),
                "parameters": params,
            },
        })
    return out


def _call_tool_result_to_text(result: Any) -> str:
    """Extract text from MCP CallToolResult."""
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


async def get_playwright_tools() -> list[dict[str, Any]]:
    """
    Spawn Playwright MCP via stdio, list tools. Returns [] if disabled or on error.
    Tool names are prefixed with playwright_ for routing.
    """
    if not is_playwright_mcp_available():
        return []
    if ClientSession is None or stdio_client is None:
        logger.debug("MCP or stdio client not available")
        return []

    try:
        async with stdio_client(_server_params(), errlog=sys.stderr) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                tools = _mcp_tools_to_openrouter(result.tools, PLAYWRIGHT_TOOL_PREFIX)
                logger.info("Playwright MCP: loaded %s tools", len(tools))
                return tools
    except FileNotFoundError as e:
        logger.warning("Playwright MCP: npx or Node not found: %s", e)
        return []
    except Exception as e:
        logger.warning("Playwright MCP list_tools failed: %s", e, exc_info=True)
        return []


async def call_playwright_tool(name: str, arguments: dict[str, Any] | None) -> str:
    """
    Execute one Playwright MCP tool. name must be the full name (with playwright_ prefix).
    """
    if not _MCP_AVAILABLE or not _STDIO_AVAILABLE:
        return "Playwright MCP не доступен: установите mcp и убедитесь, что есть mcp.client.stdio."
    if not get_settings().playwright_mcp_enabled:
        return "Playwright MCP отключён. Включите PLAYWRIGHT_MCP_ENABLED=1 и установите Node.js и npx."

    raw_name = name
    if name.startswith(PLAYWRIGHT_TOOL_PREFIX):
        raw_name = name[len(PLAYWRIGHT_TOOL_PREFIX):]

    try:
        async with stdio_client(_server_params(), errlog=sys.stderr) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(raw_name, arguments or {})
                return _call_tool_result_to_text(result)
    except FileNotFoundError as e:
        logger.warning("Playwright MCP call_tool: npx not found: %s", e)
        return f"Ошибка: не найден npx/Node.js. Установите Node.js и повторите. ({e})"
    except Exception as e:
        logger.warning("Playwright MCP call_tool %s failed: %s", name, e, exc_info=True)
        return f"Ошибка вызова инструмента {name}: {e!s}"
