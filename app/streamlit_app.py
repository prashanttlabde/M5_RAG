"""Implements architecture §10 entry point: custom shell (sidebar + top bar) over seven pages.

Run: streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit Cloud runs from the repo but does not put the repo root on sys.path: add it (for `src`) and app/ (for `ui`).
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import shell
import streamlit as st
import ui

st.set_page_config(page_title="Review Pulse", layout="wide", initial_sidebar_state="auto")
ui.inject_css()
pg = st.navigation(shell.build_pages(), position="hidden")
shell.render_sidebar()
shell.render_topbar()
pg.run()
ui.footer()
