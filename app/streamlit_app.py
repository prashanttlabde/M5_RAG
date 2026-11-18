"""Implements architecture §10 entry point: navigation over seven pages, shared footer.

Run: streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
import ui

st.set_page_config(page_title="Review Pulse", layout="wide", initial_sidebar_state="auto")
ui.inject_css()

pages = [
    st.Page("pages/1_Overview.py", title="Overview", url_path="overview", default=True),
    st.Page("pages/2_Insights.py", title="Insights", url_path="insights"),
    st.Page("pages/3_Weekly_Pulse.py", title="Weekly Pulse", url_path="weekly-pulse"),
    st.Page("pages/4_Fee_Explainer.py", title="Fee Explainer", url_path="fee-explainer"),
    st.Page("pages/5_Approve_and_Publish.py", title="Approve and Publish", url_path="approve"),
    st.Page("pages/6_Checks.py", title="Checks", url_path="checks"),
    st.Page("pages/7_About.py", title="About", url_path="about"),
]
with st.sidebar:
    st.markdown("### Review Pulse")
    st.caption("Demo mode: saved results only" if ui.is_demo() else "Local mode")
pg = st.navigation(pages)
pg.run()
ui.footer()
