"""Tests for architecture §9 approval + publishing (INV-4, INV-5) using a fake MCP session (no network)."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from src import config
from src.approval import gate, publish
from src.approval.payload import DOC_FIELDS, compute_hash, core_of, doc_text
from src.errors import PublishError


def make_payload(status: str = "ok") -> dict:
    core = {
        "doc_entry": {
            "date": "2026-11-18",
            "top_themes": ["A", "B", "C"],
            "weekly_pulse": "# Pulse",
            "identified_fee_issue": "billing issues",
            "explanation_bullets": ["x. [s]"],
            "source_links": ["https://example.com"],
        },
        "email_subject": "Weekly Product Pulse + Customer Clarification - billing issues - week ending 2026-11-15",
        "email_body": "body",
    }
    return {**core, "hash": compute_hash(core), "week_end": "2026-11-15", "explainer_status": status}


def tool(name, desc, props=None, required=None):
    schema = {"type": "object", "properties": {k: {"type": "string"} for k in (props or [])}, "required": required or []}
    return SimpleNamespace(name=name, description=desc, input_schema=schema)


GOOD_TOOLS = [
    tool("read_doc", "Get a document in Google Docs"),
    tool("append_to_doc", "Update a document in Google Docs", ["text"], ["text"]),
    tool("create_email_draft", "Create a draft in Gmail", ["Subject", "Message"], ["Subject", "Message"]),
]


class FakeSession:
    """Stands in for the n8n MCP session: a fake Doc and a list of recorded calls."""

    def __init__(self, doc: str = "", fail_on: str | None = None, on_first_read=None, tools=None):
        self.doc, self.calls, self.fail_on, self.on_first_read, self.reads = doc, [], fail_on, on_first_read, 0
        self.tools = GOOD_TOOLS if tools is None else tools

    async def list_tools(self):
        return SimpleNamespace(tools=self.tools)

    async def call_tool(self, name, arguments=None):
        self.calls.append(name)
        if name == self.fail_on:
            self.fail_on = None
            raise RuntimeError("boom")
        if name == "read_doc":
            self.reads += 1
            if self.reads == 1 and self.on_first_read:
                self.on_first_read()
            text = self.doc
        elif name == "append_to_doc":
            self.doc += arguments["text"]
            text = "ok"
        else:
            text = "draft created"
        return SimpleNamespace(is_error=False, content=[SimpleNamespace(text=text)])


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PUBLISH_LOG_JSONL", tmp_path / "publish_log.jsonl")
    monkeypatch.setattr(config, "APPROVAL_PAYLOAD_JSON", tmp_path / "approval_payload.json")
    payload = make_payload()
    config.APPROVAL_PAYLOAD_JSON.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def run(payload, session):
    return asyncio.run(publish.publish(payload, payload["hash"], session))


def log_states():
    return [json.loads(line)["state"] for line in config.PUBLISH_LOG_JSONL.read_text().splitlines()]


def test_doc_entry_has_exactly_the_six_fields():
    assert tuple(make_payload()["doc_entry"]) == DOC_FIELDS


def test_fixed_call_order_and_no_send_tool(env):
    s = FakeSession()
    assert run(env, s) == "done"
    assert s.calls == ["read_doc", "append_to_doc", "read_doc", "create_email_draft"]
    assert not any("send" in c for c in s.calls)
    assert log_states()[-1] == "DONE"


def test_hash_mismatch_before_any_call_writes_nothing(env):
    env["email_body"] = "tampered"
    s = FakeSession()
    with pytest.raises(PublishError, match="changed after approval"):
        run(env, s)
    assert s.calls == []


def test_saved_file_changed_after_approval_stops(env):
    tampered = {**env, "email_body": "other"}
    config.APPROVAL_PAYLOAD_JSON.write_text(json.dumps(tampered), encoding="utf-8")
    s = FakeSession()
    with pytest.raises(PublishError):
        run(env, s)
    assert s.calls == []


def test_change_during_run_stops_before_the_write(env):
    s = FakeSession(on_first_read=lambda: env.__setitem__("email_body", "changed mid-run"))
    with pytest.raises(PublishError):
        run(env, s)
    assert s.calls == ["read_doc"]  # never reached append_to_doc


def test_duplicate_week_entry_stops(env):
    s = FakeSession(doc="=== Weekly Pulse | week ending 2026-11-15 | payload sha256 deadbeef ===")
    with pytest.raises(PublishError, match="already has an entry"):
        run(env, s)
    assert "append_to_doc" not in s.calls


def test_resume_after_failure_does_not_duplicate_doc_entry(env):
    s = FakeSession(fail_on="create_email_draft")
    with pytest.raises(PublishError, match="run publish again"):
        run(env, s)
    assert run(env, s) == "done"
    assert s.calls.count("append_to_doc") == 1
    assert s.doc.count(env["hash"]) == 1
    assert s.calls.count("create_email_draft") == 2  # failed once, succeeded once; draft created once


def test_already_done_makes_no_calls(env):
    run(env, FakeSession())
    s = FakeSession()
    assert run(env, s) == "already_done"
    assert s.calls == []


def test_blocked_when_explainer_needs_human_review(env):
    payload = make_payload("needs_human_review")
    s = FakeSession()
    with pytest.raises(PublishError, match="human review"):
        run(payload, s)
    assert s.calls == []


def test_only_exact_APPROVE_counts():
    assert gate.is_approval("APPROVE")
    for bad in ("approve", "Approve", "APPROVE ", " APPROVE", "yes", ""):
        assert not gate.is_approval(bad)


def test_reject_logs_reason_and_writes_nothing(env):
    gate.reject(env, "numbers look wrong")
    assert log_states() == ["REJECTED"]
    with pytest.raises(PublishError):
        gate.reject(env, "   ")


def test_doc_text_contains_hash_and_week_marker():
    p = make_payload()
    assert p["hash"] in doc_text(p) and "week ending 2026-11-15" in doc_text(p)
    assert compute_hash(core_of(p)) == p["hash"]


def test_tool_described_as_send_blocks_everything(env):
    bad = [*GOOD_TOOLS[:2], tool("create_email_draft", "Send a message in Gmail", ["Subject", "Message"], ["Subject", "Message"])]
    s = FakeSession(tools=bad)
    with pytest.raises(PublishError, match="Send"):
        run(env, s)
    assert s.calls == []


def test_n8n_auto_named_insert_text_input_is_accepted():
    from src.mcp_client.client import resolve_args

    t = tool("append_to_doc", "Update a document in Google Docs", ["actionFields0_Old_Text"], ["actionFields0_Old_Text"])
    assert resolve_args(t, {"text": "hello"}) == {"actionFields0_Old_Text": "hello"}


def test_misconfigured_append_node_stops_before_any_call(env):
    bad = [GOOD_TOOLS[0], tool("append_to_doc", "Update a document in Google Docs", ["something_else"], ["something_else"]), GOOD_TOOLS[2]]
    s = FakeSession(tools=bad)
    with pytest.raises(PublishError, match="no 'text' input"):
        run(env, s)
    assert s.calls == []


def test_write_that_silently_does_nothing_is_caught_and_not_marked_done(env):
    s = FakeSession()
    s.call_tool_original = s.call_tool

    async def ignore_append(name, arguments=None):
        if name == "append_to_doc":
            s.calls.append(name)
            return SimpleNamespace(is_error=False, content=[SimpleNamespace(text="ok")])
        return await s.call_tool_original(name, arguments)

    s.call_tool = ignore_append
    with pytest.raises(PublishError, match="not found after writing"):
        run(env, s)
    assert "create_email_draft" not in s.calls
    assert "DONE" not in log_states()


def test_log_saying_doc_written_does_not_skip_append_if_doc_is_empty(env):
    publish.log_step("DOC_WRITTEN", env["hash"], ok=True)  # stale log line from a write that did nothing
    s = FakeSession()
    assert run(env, s) == "done"
    assert s.calls.count("append_to_doc") == 1


def test_tool_error_flag_is_detected():
    from src.mcp_client import client

    class Boom:
        async def call_tool(self, name, arguments=None):
            return SimpleNamespace(is_error=True, content=[])

    with pytest.raises(PublishError, match="reported an error"):
        asyncio.run(client.call_tool(Boom(), "read_doc"))


def test_resolve_args_is_case_insensitive():
    from src.mcp_client.client import resolve_args

    assert resolve_args(GOOD_TOOLS[2], {"subject": "s", "message": "m"}) == {"Subject": "s", "Message": "m"}
