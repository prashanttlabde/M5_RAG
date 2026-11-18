"""Implements architecture §9 approval gate (PRD FR20; INV-4): the human signs the exact payload.

Only the exact text APPROVE (capitals) approves. Reject needs a reason, is logged, and writes nothing
to the Doc or Gmail. The same functions are used by the CLI and, later, the Streamlit page.
"""

from __future__ import annotations

import json

from src.approval import publish
from src.approval.payload import doc_text, week_label
from src.errors import PublishError

APPROVE_WORD = "APPROVE"


def render_for_review(payload: dict) -> str:
    """Everything the human must see: full Doc entry, full email draft, and the hash."""
    return (
        f"PAYLOAD HASH (sha256): {payload['hash']}\n\n"
        f"--- DOC ENTRY ({week_label(payload)}) ---\n{doc_text(payload)}\n"
        f"--- EMAIL DRAFT (will be saved as a Gmail draft, never sent) ---\n"
        f"Subject: {payload['email_subject']}\n\n{payload['email_body']}\n"
        f"Explainer status: {payload['explainer_status']}\n"
    )


def is_approval(typed: str) -> bool:
    """Exactly APPROVE, in capitals, nothing else."""
    return typed == APPROVE_WORD


def reject(payload: dict, reason: str) -> None:
    """Record a rejection (reason required). Writes nothing to the Doc or Gmail."""
    if not reason.strip():
        raise PublishError("Please give a reason for rejecting.")
    publish.log_step("REJECTED", payload["hash"], ok=True, detail=reason.strip())


def run_cli(payload: dict) -> str:
    """Interactive gate. Returns 'approved', 'rejected' or 'no_action'."""
    print(render_for_review(payload))
    typed = input(f"Type {APPROVE_WORD} (capitals) to publish, or Reject: ").strip("\n")
    if is_approval(typed):
        return "approved"
    if typed.strip().lower() == "reject":
        reject(payload, input("Reason for rejecting: "))
        print("Rejected. Nothing was written to the Doc or Gmail.")
        return "rejected"
    print("Not approved. Nothing was written.")
    return "no_action"


def summary_json(payload: dict) -> str:
    return json.dumps({"hash": payload["hash"], "subject": payload["email_subject"]}, indent=2)
