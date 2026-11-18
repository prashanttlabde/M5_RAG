"""Implements architecture §10 Weekly Pulse: the pulse and its word count."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import ui

from src import config

ui.page_header("Weekly Pulse", "One-minute read for the product team")
text = ui.load_text(config.WEEKLY_PULSE_MD)
if text is None:
    ui.empty_state("The weekly pulse", "Run make write after the analysis.")
    st.stop()
words = len(text.split())
st.markdown(
    f'{ui.badge("ok" if words <= 250 else "fail", "Within the 250 word limit" if words <= 250 else "Over the 250 word limit")} <span class="sub">&nbsp;{words} words</span>',
    unsafe_allow_html=True,
)
with st.container(border=True):
    st.markdown(text)
st.caption("Every number is inserted by code; the language model only wrote the short sentences.")
