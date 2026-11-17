"""Implements architecture §8 MCP client: official `mcp` SDK, Bearer auth, streamable HTTP or SSE.

Tools are called directly by name from fixed code (never chosen by an LLM). The token is read from
.env and is never logged or printed.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

from src import config
from src.errors import ConfigError, PublishError

log = logging.getLogger("review_pulse.mcp")

EXPECTED_TOOLS = frozenset({"append_to_doc", "read_doc", "create_email_draft"})


def _walk(exc: BaseException):
    """Yield exc and every nested exception (anyio wraps errors in exception groups)."""
    yield exc
    for sub in getattr(exc, "exceptions", ()) or ():
        yield from _walk(sub)
    if exc.__cause__ is not None:
        yield from _walk(exc.__cause__)


def explain_error(exc: BaseException) -> str:
    """Friendly message saying which setting is likely wrong (token vs URL vs network)."""
    for e in _walk(exc):
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status in (401, 403):
            return f"The server rejected the token (HTTP {status}). Check N8N_MCP_TOKEN matches the Bearer credential in n8n."
        if status == 404:
            return "The URL was not found (HTTP 404). Check N8N_MCP_URL is the Production URL and the workflow is Active."
        if status is not None:
            return f"The server answered HTTP {status}. Check the workflow is Active and N8N_MCP_URL is correct."
        name = type(e).__name__
        if "Connect" in name or "Timeout" in name or "gaierror" in name:
            return "Could not reach the server. Check N8N_MCP_URL (host name) and your internet connection."
    return f"MCP connection failed ({type(exc).__name__})."


def check_tool_names(names: list[str]) -> None:
    """Fail fast if any tool name contains 'send' (INV-5) or the set is not exactly the 3 safe tools."""
    sendish = sorted(n for n in names if "send" in n.lower())
    if sendish:
        raise PublishError(f"Unsafe tool(s) exposed by the server: {sendish}. No tool may contain 'send'.")
    if set(names) != EXPECTED_TOOLS or len(names) != len(EXPECTED_TOOLS):
        raise PublishError(
            f"Expected exactly {sorted(EXPECTED_TOOLS)} but the server lists {sorted(names)}."
        )


def _settings() -> tuple[str, dict[str, str]]:
    url, token = config.get_n8n_mcp_url(), config.get_n8n_mcp_token()
    if not url or not token:
        raise ConfigError("N8N_MCP_URL and N8N_MCP_TOKEN must be set in .env (fill them in yourself).")
    return url, {"Authorization": f"Bearer {token}"}


@asynccontextmanager
async def _streamable(url: str, headers: dict[str, str]) -> AsyncIterator[ClientSession]:
    async with (
        create_mcp_http_client(headers=headers) as http,
        streamable_http_client(url, http_client=http) as streams,
        ClientSession(streams[0], streams[1]) as session,
    ):
        await session.initialize()
        yield session


@asynccontextmanager
async def _sse(url: str, headers: dict[str, str]) -> AsyncIterator[ClientSession]:
    async with (
        sse_client(url, headers=headers) as streams,
        ClientSession(streams[0], streams[1]) as session,
    ):
        await session.initialize()
        yield session


@asynccontextmanager
async def open_session(transport: str = "auto") -> AsyncIterator[ClientSession]:
    """Open an initialised MCP session. transport: 'auto' (streamable HTTP, then SSE), 'http' or 'sse'."""
    url, headers = _settings()
    if transport == "sse":
        order = [_sse]
    elif transport == "http":
        order = [_streamable]
    else:
        order = [_streamable, _sse]
    last: BaseException | None = None
    for opener in order:
        try:
            async with opener(url, headers) as session:
                yield session
            return
        except Exception as exc:  # noqa: BLE001 - report and try the next transport
            last = exc
            log.warning("MCP transport %s failed: %s", opener.__name__.strip("_"), type(exc).__name__)
    raise PublishError(explain_error(last) if last else "MCP connection failed.") from last


async def list_tool_names(session: ClientSession) -> list[str]:
    result = await session.list_tools()
    return [t.name for t in result.tools]


async def call_tool(session: ClientSession, name: str, arguments: dict | None = None) -> str:
    """Call one tool by name (fixed code path) and return its text output."""
    if name not in EXPECTED_TOOLS:
        raise PublishError(f"Refusing to call unexpected tool '{name}'.")
    result = await session.call_tool(name, arguments or {})
    if getattr(result, "isError", False):
        raise PublishError(f"Tool '{name}' reported an error.")
    return "\n".join(getattr(c, "text", "") for c in result.content)
