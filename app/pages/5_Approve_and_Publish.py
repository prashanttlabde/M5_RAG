"""Implements architecture §10 Approve and Publish (PRD FR20-FR24; INV-4, INV-5).

Password-gated. Uses the same gate and publish code as the command line: the human approves the exact
payload and its hash by typing APPROVE; Reject needs a reason and writes nothing; publishing re-checks
the hash before every write and can only create a Doc entry and an email draft.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hmac
import json

import streamlit as st
import ui

from src import config
from src.approval import gate, publish
from src.approval.payload import build_payload, doc_text, load_saved_payload
from src.errors import ReviewPulseError

MAX_PASSWORD_TRIES = 5

ui.page_header("Approve and Publish", "A person approves the exact text before anything is written")

# ---- password gate ---------------------------------------------------------------------------
expected = config.get_approver_password()
if not expected:
    st.markdown(ui.badge("warn", "Approver password not configured"), unsafe_allow_html=True)
    st.write("Set APPROVER_PASSWORD (in .env locally or in the host's secrets) to enable approval.")
    st.stop()
st.session_state.setdefault("approver_ok", False)
st.session_state.setdefault("password_tries", 0)
if not st.session_state["approver_ok"]:
    if st.session_state["password_tries"] >= MAX_PASSWORD_TRIES:
        st.markdown(ui.badge("fail", "Locked"), unsafe_allow_html=True)
        st.write("Too many attempts in this session. Reload the page to try again.")
        st.stop()
    typed_password = st.text_input("Approver password", type="password", key="approver_password")
    if st.button("Unlock", key="unlock"):
        if hmac.compare_digest(typed_password.encode(), expected.encode()):
            st.session_state["approver_ok"] = True
            st.rerun()
        st.session_state["password_tries"] += 1
        st.markdown(ui.badge("fail", "Wrong password"), unsafe_allow_html=True)
    st.stop()

# ---- payload ---------------------------------------------------------------------------------
if st.button("Build payload from the current results", key="build_payload"):
    try:
        build_payload()
        st.markdown(ui.badge("ok", "Payload rebuilt"), unsafe_allow_html=True)
    except ReviewPulseError as exc:
        st.markdown(ui.badge("fail", "Could not build"), unsafe_allow_html=True)
        st.write(str(exc))

try:
    payload = load_saved_payload()
except ReviewPulseError:
    ui.empty_state("The approval payload", "Press the build button above once the pulse and explainer exist.")
    st.stop()

st.subheader("What will be written")
st.markdown("**Payload fingerprint (SHA-256)**")
st.code(payload["hash"], language=None)
explainer_ok = payload.get("explainer_status") == "ok"
st.markdown(
    "Fee explainer: " + (ui.badge("ok", "Verified") if explainer_ok else ui.badge("fail", "Needs human review. Publishing is blocked")),
    unsafe_allow_html=True,
)
with st.expander("Google Doc entry (full)", expanded=True):
    st.code(doc_text(payload), language="json")
with st.expander("Gmail draft (full). It is saved as a draft and never sent", expanded=True):
    st.markdown(f"**Subject:** {payload['email_subject']}")
    st.code(payload["email_body"], language=None)

# ---- approve / reject ------------------------------------------------------------------------
st.subheader("Decision")
typed = st.text_input(f"Type {gate.APPROVE_WORD} in capitals to approve this exact payload", key="approve_text")
approved = gate.is_approval(typed)
if st.button("Approve and publish", key="approve_button", disabled=not (approved and explainer_ok)):
    try:
        with st.spinner("Publishing in a fixed order: check, write, verify, draft..."):
            result = publish.publish_sync(payload, payload["hash"])
        st.markdown(ui.badge("ok", "Already published earlier" if result == "already_done" else "Published"), unsafe_allow_html=True)
        st.write("The Doc entry was written and verified, and a Gmail draft was created. Nothing was sent.")
    except ReviewPulseError as exc:
        st.markdown(ui.badge("fail", "Stopped. Nothing further was written"), unsafe_allow_html=True)
        st.write(str(exc))

with st.expander("Reject instead"):
    reason = st.text_input("Reason for rejecting", key="reject_reason")
    if st.button("Reject", key="reject_button"):
        try:
            gate.reject(payload, reason)
            st.markdown(ui.badge("ok", "Rejected"), unsafe_allow_html=True)
            st.write("Nothing was written to the Doc or Gmail.")
        except ReviewPulseError as exc:
            st.write(str(exc))

# ---- step log --------------------------------------------------------------------------------
st.subheader("Publish log")
raw_log = ui.load_text(config.PUBLISH_LOG_JSONL)
if not raw_log:
    st.caption("No publish steps recorded yet.")
else:
    rows = [json.loads(l) for l in raw_log.splitlines() if l.strip()][-12:]
    ui.table(
        ["Time", "Step", "Tool", "Result", "Note"],
        [[r["ts"], r["state"], r["tool"] or "", ui.raw(ui.badge("ok", "OK") if r["ok"] else ui.badge("fail", "Stopped")), r["detail"]] for r in rows],
    )
