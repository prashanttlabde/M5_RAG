"""Implements architecture §9 publishing (PRD FR21, FR24; INV-4, INV-5).

Fixed order, direct tool calls (no LLM agent):
read_doc (duplicate check) -> hash re-check -> append_to_doc -> read_doc (verify) -> hash re-check
-> create_email_draft. Every step is logged to outputs/publish_log.jsonl; a failed run resumes
without writing the Doc entry twice. There is no send tool.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging

from src import config
from src.approval.payload import (
    compute_hash,
    core_of,
    doc_text,
    load_saved_payload,
    week_label,
)
from src.errors import DataError, PublishError
from src.mcp_client.client import (
    call_tool,
    check_tools,
    explain_error,
    list_tools,
    open_session,
    resolve_args,
)

log = logging.getLogger("review_pulse.publish")

STATES = ("APPROVED", "DOC_CHECKED", "DOC_WRITTEN", "DOC_VERIFIED", "EMAIL_DRAFTED", "DONE")


# --- logging -----------------------------------------------------------------------------------
def log_step(state: str, payload_hash: str, ok: bool, tool: str | None = None, detail: str = "") -> None:
    """Append one JSON line per step."""
    config.PUBLISH_LOG_JSONL.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": dt.datetime.now().isoformat(timespec="seconds"),
        "state": state,
        "hash": payload_hash,
        "tool": tool,
        "ok": ok,
        "detail": detail,
    }
    with config.PUBLISH_LOG_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def completed_states(payload_hash: str) -> set[str]:
    """States already finished OK for this exact payload hash (used to resume)."""
    path = config.PUBLISH_LOG_JSONL
    if not path.exists():
        return set()
    done: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("hash") == payload_hash and row.get("ok"):
            done.add(row["state"])
    return done


# --- safety checks -----------------------------------------------------------------------------
def recheck_hash(payload: dict, approved_hash: str, before: str) -> None:
    """INV-4: the payload about to be written, and the saved approval file, must match the approved hash."""
    current = compute_hash(core_of(payload))
    try:
        saved = compute_hash(core_of(load_saved_payload()))
    except DataError:
        saved = ""
    if current != approved_hash or saved != approved_hash:
        log_step("STOPPED_HASH_MISMATCH", approved_hash, ok=False, detail=f"before {before}")
        raise PublishError("The payload changed after approval. Nothing was written. Rebuild and approve again.")


def ensure_publishable(payload: dict) -> None:
    if payload.get("explainer_status") != "ok":
        raise PublishError("The fee explainer needs human review (fewer than 4 verified bullets). Publishing is blocked.")


def _marker(payload: dict) -> str:
    return f"=== Weekly Pulse | {week_label(payload)} |"


# --- the publish sequence ----------------------------------------------------------------------
async def publish(payload: dict, approved_hash: str, session=None) -> str:
    """Run the fixed publish sequence. Returns 'done' or 'already_done'. Raises PublishError on any stop."""
    ensure_publishable(payload)
    recheck_hash(payload, approved_hash, "start")
    if session is None:
        async with open_session() as live:
            return await publish(payload, approved_hash, live)

    done = completed_states(approved_hash)
    if "DONE" in done:
        return "already_done"
    # Safety before any call: no send-like tool, and each write tool accepts the inputs we will send.
    listed = await list_tools(session)
    check_tools(listed)
    tools = {t.name: t for t in listed}
    append_args = resolve_args(tools["append_to_doc"], {"text": doc_text(payload)})
    draft_args = resolve_args(
        tools["create_email_draft"], {"subject": payload["email_subject"], "message": payload["email_body"]}
    )
    log_step("APPROVED", approved_hash, ok=True)

    async def step(state: str, tool: str, args: dict | None = None) -> str:
        try:
            text = await call_tool(session, tool, args)
        except PublishError:
            raise
        except Exception as exc:
            msg = explain_error(exc)
            log_step("FAILED", approved_hash, ok=False, tool=tool, detail=msg)
            raise PublishError(f"{tool} failed: {msg} You can run publish again; finished steps are skipped.") from exc
        log_step(state, approved_hash, ok=True, tool=tool)
        return text

    # 1. duplicate check
    content = await step("DOC_CHECKED", "read_doc")
    already_written = False  # the Doc itself is the source of truth, not the log
    if _marker(payload) in content:
        if approved_hash in content:
            already_written = True  # this exact payload is already in the Doc: resume, never append twice
        else:
            log_step("STOPPED_DUPLICATE", approved_hash, ok=False, detail=week_label(payload))
            raise PublishError(f"The Doc already has an entry for {week_label(payload)}. Stopped to avoid a duplicate.")

    # 2. write the Doc entry
    if not already_written:
        recheck_hash(payload, approved_hash, "append_to_doc")
        await step("DOC_WRITTEN", "append_to_doc", append_args)
    else:
        log_step("DOC_WRITTEN", approved_hash, ok=True, detail="already present; skipped append")

    # 3. verify
    verify = await step("DOC_VERIFIED_READ", "read_doc")
    if _marker(payload) not in verify or approved_hash not in verify:
        log_step("FAILED", approved_hash, ok=False, tool="read_doc", detail="entry not found after write")
        raise PublishError("The Doc entry was not found after writing. Check the Doc, then run publish again.")
    log_step("DOC_VERIFIED", approved_hash, ok=True)

    # 4. Gmail draft (never sent)
    if "EMAIL_DRAFTED" not in done:
        recheck_hash(payload, approved_hash, "create_email_draft")
        await step("EMAIL_DRAFTED", "create_email_draft", draft_args)
    log_step("DONE", approved_hash, ok=True)
    return "done"


def publish_sync(payload: dict, approved_hash: str) -> str:
    """Blocking wrapper for the CLI and Streamlit."""
    return asyncio.run(publish(payload, approved_hash))
