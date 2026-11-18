"""Implements architecture §10 About: method, limits, disclaimer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import ui

from src import config

ui.page_header("About", "How this pulse is made, and what it cannot tell you")
ins = ui.load_json(config.INSIGHTS_JSON) or {}
product = config.get_product_config()
cap = product.get("max_reviews_per_week")

st.subheader("Method")
st.markdown(
    "1. Public Google Play reviews are collected and cleaned; reviewer names are never kept.\n"
    "2. A language model proposes at most five themes and assigns each review to one theme.\n"
    "3. **Code counts everything**: themes are ranked by the number of 1-2 star reviews, so the loudest "
    "pain surfaces, not the most praise.\n"
    "4. Quotes are copied from real reviews and checked word for word.\n"
    "5. Fee explanations are retrieved from official pages only, then each sentence is fact-checked.\n"
    "6. A person approves the exact text and its fingerprint before anything is written. Only a Doc entry and an email **draft** can be created; nothing is ever sent."
)
st.subheader("Ranking rule")
st.write(ins.get("ranking_rule", product.get("ranking_rule", "Not available yet.")))

st.subheader("Limits")
st.markdown(
    f"- The review file keeps up to {cap} reviews per week and samples happy reviews more lightly than unhappy ones, so counts describe this sample, not every Play Store review.\n"
    "- A language model labels themes and fee confusion, so a few labels will be wrong.\n"
    "- Fee explanations cover only the official pages listed on the Fee Explainer page."
)
st.subheader("Disclaimer")
st.write("This is a student project built from public reviews and official help pages. It is not affiliated with or endorsed by OpenAI or Google.")
