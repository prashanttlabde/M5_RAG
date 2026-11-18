"""Implements architecture §10 Checks: latest checks_report.md."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import ui

from src import config

ui.page_header("Checks", "Rule-based checks, no AI involved")
report = ui.load_text(config.CHECKS_REPORT_MD)
if report is None:
    ui.empty_state("The checks report", "Run make checks.")
    st.stop()

rows, group = [], ""
for line in report.splitlines():
    if line.startswith("## "):
        group = line[3:]
    elif line.startswith(("- PASS: ", "- FAIL: ")):
        passed = line.startswith("- PASS")
        rows.append([group, ui.raw(ui.badge("ok" if passed else "fail", "Pass" if passed else "Fail")), line[8:]])
summary = next((l for l in report.splitlines() if "checks passed" in l), "")
st.markdown(f'<p class="sub">{ui.esc(summary.replace("**", ""))}</p>', unsafe_allow_html=True)
ui.table(["Area", "Result", "Check"], rows)
with st.expander("Full report"):
    st.markdown(report)
