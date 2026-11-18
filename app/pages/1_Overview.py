"""Implements architecture §10 Overview: window, review count, weeks, pipeline status."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import subprocess

import streamlit as st
import ui

from src import config

ins = ui.load_json(config.INSIGHTS_JSON)
ui.page_header("Overview", "Weekly product pulse for ChatGPT on Google Play (India, English)")

if ins is None:
    ui.empty_state("The insights file", "Run the analysis steps first (make analyze).")
else:
    w = ins["window"]
    cols = st.columns(3)
    cols[0].markdown(ui.metric("Reviews analysed", f"{w['review_count']:,}", f"{w['start']} to {w['end']}"), unsafe_allow_html=True)
    cols[1].markdown(ui.metric("Weeks covered", w["weeks"]), unsafe_allow_html=True)
    names = ui.theme_names()
    cols[2].markdown(ui.metric("Identified fee issue", (ins["fee"]["topic"] or "none").replace("_", " "), f"{ins['fee']['confused']} confused reviews"), unsafe_allow_html=True)
    stats = {t["theme_id"]: t for t in ins["themes"]}
    st.subheader("Top 3 themes")
    ui.table(
        ["Rank", "Theme", "1-2 star reviews", "All reviews"],
        [[i + 1, names.get(tid, tid), stats[tid]["low_star"], stats[tid]["total"]] for i, tid in enumerate(ins["top3"])],
    )

st.subheader("Pipeline status")
artifacts = [
    ("Reviews (balanced)", config.REVIEWS_BALANCED_CSV), ("Themes", config.THEMES_JSON),
    ("Theme assignments", config.ASSIGNMENTS_CSV), ("Insights", config.INSIGHTS_JSON),
    ("Weekly pulse", config.WEEKLY_PULSE_MD), ("Fee explainer", config.FEE_EXPLAINER_MD),
    ("Approval payload", config.APPROVAL_PAYLOAD_JSON), ("Checks report", config.CHECKS_REPORT_MD),
]
ui.table(
    ["Step output", "Status"],
    [[name, ui.raw(ui.badge("ok", "Ready") if p.exists() and p.stat().st_size else ui.badge("warn", "Missing"))] for name, p in artifacts],
)

log = ui.load_text(config.PUBLISH_LOG_JSONL)
done = bool(log) and '"state": "DONE"' in log
st.markdown(
    "Publishing: " + (ui.badge("ok", "Published to the Doc and Gmail draft") if done else ui.badge("warn", "Not published yet")),
    unsafe_allow_html=True,
)

if ui.is_demo():
    st.caption("Demo mode is on: results are loaded from saved files and run buttons are hidden.")
else:
    st.subheader("Run pipeline steps")
    st.caption("These run on this machine. Steps marked (AI) call the language model.")
    steps = [("Collect reviews", "src.collect.clean"), ("Analyse (AI)", "src.analyze"), ("Write pulse (AI)", "src.writer"),
             ("Build fee explainer (AI)", "src.rag"), ("Run checks", "src.checks")]
    for label, module in steps:
        if st.button(label, key=f"run_{module}"):
            with st.spinner(f"Running {label}..."):
                out = subprocess.run([sys.executable, "-m", module], cwd=config.ROOT, capture_output=True, text=True,
                                     env={**__import__("os").environ, "PYTHONPATH": str(config.ROOT)}, check=False)
            st.code("\n".join((out.stdout + out.stderr).strip().splitlines()[-12:]) or "(no output)", language=None)
            st.markdown(ui.badge("ok", "Finished") if out.returncode == 0 else ui.badge("fail", "Stopped with an error"), unsafe_allow_html=True)
