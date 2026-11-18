"""Implements architecture §9 payload: canonical JSON + SHA-256 hash of exactly what will be written.

Payload core = {doc_entry, email_subject, email_body}, serialised with sorted keys. The hash is shown
to the human, stored in the log and in the Doc entry, and re-checked before every write (INV-4).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json

from src import config
from src.errors import DataError

DOC_FIELDS = ("date", "top_themes", "weekly_pulse", "identified_fee_issue", "explanation_bullets", "source_links")


def canonical_json(core: dict) -> str:
    """Deterministic JSON: sorted keys, no extra whitespace."""
    return json.dumps(core, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_hash(core: dict) -> str:
    return hashlib.sha256(canonical_json(core).encode("utf-8")).hexdigest()


def core_of(payload: dict) -> dict:
    """The part of a payload that is hashed."""
    return {k: payload[k] for k in ("doc_entry", "email_subject", "email_body")}


def week_label(payload_or_end: dict | str) -> str:
    end = payload_or_end if isinstance(payload_or_end, str) else payload_or_end["week_end"]
    return f"week ending {end}"


def _load_json(path):
    if not path.exists() or path.stat().st_size == 0:
        raise DataError(f"{path.name} missing. Run the earlier phases first.")
    return json.loads(path.read_text(encoding="utf-8"))


def build_email_body(pulse: str, explainer: dict) -> str:
    bullets = "\n".join(f"- {b['text']}" for b in explainer["bullets"])
    links = "\n".join(f"- {s['title']}: {s['url']}" for s in explainer["links"])
    return (
        f"{pulse.strip()}\n\n---\nCustomer support snippet: {explainer['topic'].replace('_', ' ')}\n\n"
        f"{bullets}\n\nOfficial sources:\n{links}\nLast checked: {explainer['last_checked']}\n"
    )


def build_payload(today: str | None = None) -> dict:
    """Build the payload from computed artifacts, write it to outputs/, and return it (with hash)."""
    insights = _load_json(config.INSIGHTS_JSON)
    explainer = _load_json(config.FEE_EXPLAINER_JSON)
    if not config.WEEKLY_PULSE_MD.exists():
        raise DataError("outputs/weekly_pulse.md missing. Run `make write` first.")
    pulse = config.WEEKLY_PULSE_MD.read_text(encoding="utf-8")
    names = {t["theme_id"]: t["name"] for t in insights["themes"]}
    end = insights["window"]["end"]
    fee_issue = explainer["topic"].replace("_", " ")
    doc_entry = {
        "date": today or dt.date.today().isoformat(),
        "top_themes": [names[tid] for tid in insights["top3"]],
        "weekly_pulse": pulse,
        "identified_fee_issue": fee_issue,
        "explanation_bullets": [b["text"] for b in explainer["bullets"]],
        "source_links": [s["url"] for s in explainer["links"]],
    }
    core = {
        "doc_entry": doc_entry,
        "email_subject": f"Weekly Product Pulse + Customer Clarification - {fee_issue} - {week_label(end)}",
        "email_body": build_email_body(pulse, explainer),
    }
    payload = {**core, "hash": compute_hash(core), "week_end": end, "explainer_status": explainer["status"]}
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config.APPROVAL_PAYLOAD_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    config.EMAIL_DRAFT_TXT.write_text(f"Subject: {core['email_subject']}\n\n{core['email_body']}", encoding="utf-8")
    return payload


def load_saved_payload() -> dict:
    """Re-read outputs/approval_payload.json (what the human approved)."""
    return _load_json(config.APPROVAL_PAYLOAD_JSON)


def doc_text(payload: dict) -> str:
    """The exact text appended to the Doc: a marker header (week + hash) then the Doc entry JSON."""
    header = f"=== Weekly Pulse | {week_label(payload)} | payload sha256 {payload['hash']} ==="
    return f"{header}\n{json.dumps(payload['doc_entry'], indent=2, ensure_ascii=False)}\n"
