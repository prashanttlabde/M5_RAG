"""Implements architecture §10 Insights: themes table, top 3, trend, quotes, fee stance counts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import ui

from src import config

ins = ui.load_json(config.INSIGHTS_JSON)
ui.page_header("Insights", "Everything here is counted by code from the review files")
if ins is None:
    ui.empty_state("The insights file", "Run the analysis steps first (make analyze).")
    st.stop()

names = ui.theme_names()
stats = {t["theme_id"]: t for t in ins["themes"]}
rank = {tid: i + 1 for i, tid in enumerate(ins["top3"])}

st.subheader("Themes")
st.markdown(f'<p class="sub">Ranking rule: {ui.esc(ins["ranking_rule"])}. Ranked by unhappy (1-2 star) reviews, never by total volume.</p>', unsafe_allow_html=True)
ordered = sorted(stats.values(), key=lambda t: (rank.get(t["theme_id"], 99), -t["low_star"]))
ui.table(
    ["Rank", "Theme", "All reviews", "1-2 star", "1-2 star share"],
    [[rank.get(t["theme_id"], "-"), t["name"], t["total"], t["low_star"], f"{100 * t['low_star_share']:.1f}%"] for t in ordered],
)

st.subheader("Trend: last 4 weeks vs the 4 weeks before")
def _dir(p: int, l: int) -> str:
    return "Rising" if l > p else "Falling" if l < p else "Flat"

ui.table(
    ["Theme", "Previous 4 weeks", "Last 4 weeks", "Direction"],
    [[names.get(t["theme_id"], t["theme_id"]), t["prev4"], t["last4"], _dir(t["prev4"], t["last4"])] for t in ins["trend"]],
)

st.subheader("Supporting quotes")
st.caption("Copied word for word from real reviews and checked against the review file.")
for q in ins["quotes"]:
    st.markdown(
        f'<div class="card"><div class="quote">"{ui.esc(q["excerpt"])}"<div class="meta">{ui.esc(names.get(q["theme_id"], q["theme_id"]))}, {ui.esc(q["rating"])} star, {ui.esc(q["date"])}</div></div></div>',
        unsafe_allow_html=True,
    )

st.subheader("Voice-related reviews")
v = ins["voice_tag"]
st.markdown(ui.metric("Reviews mentioning voice", v["count"], f"{v['low_star']} of them are 1-2 star"), unsafe_allow_html=True)

st.subheader("Fee-related reviews by stance")
f = ins["fee"]
ui.table(
    ["Stance", "Reviews"],
    [["Confused (does not understand a charge)", f["confused"]], ["Complaint only", f["complaint_only"]],
     ["Praise", f["praise"]], ["Unrelated", f["unrelated"]], ["All money-related reviews", f["money_reviews"]]],
)
