"""Implements architecture §8 / PRD FR19: connect to the n8n MCP server and verify the three safe tools.

Run: python -m src.mcp_client.test_connection
"""

from __future__ import annotations

import asyncio
import sys

from src.errors import ConfigError, PublishError
from src.logging_config import setup_logging
from src.mcp_client.client import check_tool_names, list_tool_names, open_session


async def _run() -> list[str]:
    async with open_session() as session:
        return await list_tool_names(session)


def main() -> int:
    setup_logging()
    try:
        names = asyncio.run(_run())
        print("tools:", sorted(names))
        check_tool_names(names)
    except (ConfigError, PublishError) as exc:
        print("FAIL:", exc)
        return 1
    print("OK: exactly 3 tools, none contains 'send'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
