"""Tests for architecture §8 MCP client safety guards (INV-5) and error messages. No network."""

from __future__ import annotations

import pytest

from src.errors import PublishError
from src.mcp_client import client

GOOD = ["append_to_doc", "read_doc", "create_email_draft"]


def test_exact_three_tools_pass():
    client.check_tool_names(GOOD)


@pytest.mark.parametrize("extra", ["send_email", "Gmail_SEND", "resend_draft"])
def test_any_send_tool_fails_fast(extra):
    with pytest.raises(PublishError, match="send"):
        client.check_tool_names([*GOOD, extra])


def test_missing_or_extra_tool_fails():
    with pytest.raises(PublishError):
        client.check_tool_names(GOOD[:2])
    with pytest.raises(PublishError):
        client.check_tool_names([*GOOD, "delete_doc"])


def test_call_tool_refuses_unknown_names():
    import asyncio

    with pytest.raises(PublishError):
        asyncio.run(client.call_tool(None, "send_email"))  # type: ignore[arg-type]


class _Resp:
    def __init__(self, code):
        self.status_code = code


class _HttpErr(Exception):
    def __init__(self, code):
        self.response = _Resp(code)


def test_error_messages_name_the_wrong_setting():
    assert "token" in client.explain_error(_HttpErr(401)).lower()
    assert "url" in client.explain_error(_HttpErr(404)).lower()
    group = ExceptionGroup("g", [_HttpErr(401)])
    assert "token" in client.explain_error(group).lower()
