"""Implements architecture §8 / PRD FR19: connect to the n8n MCP server and verify the three safe tools.

Run: python -m src.mcp_client.test_connection
"""

from __future__ import annotations

import asyncio
import sys

from src.errors import ConfigError, PublishError
from src.logging_config import setup_logging
from src.mcp_client.client import check_tools, list_tools, open_session


async def _run() -> list:
    async with open_session() as session:
        return await list_tools(session)


def main() -> int:
    setup_logging()
    try:
        tools = asyncio.run(_run())
        for t in sorted(tools, key=lambda t: t.name):
            print(f"tool: {t.name} | {t.description}")
        check_tools(tools)
    except (ConfigError, PublishError) as exc:
        print("FAIL:", exc)
        return 1
    print("OK: exactly 3 tools, no name or description mentions 'send'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
