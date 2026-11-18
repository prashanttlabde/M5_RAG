"""Implements architecture §10 Insights: interactive charts (filters, tooltips, legend click) plus the data tables."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import charts
import metrics
import pandas as pd
import streamlit as st
import ui

from src import config

ins = ui.load_json(config.INSIGHTS_JSON)
ui.page_header("Insights", "Interactive view of every count, computed by code from the review files",
               pill_html=ui.pill("accent", "Interactive", "zap"))
if ins is None:
    ui.empty_state("The insights file", "Run the analysis steps first (make analyze).")
    st.stop()

names = ui.theme_names()
stats = {t["theme_id"]: t for t in ins["themes"]}
rank = {tid: i + 1 for i, tid in enumerate(ins["top3"])}
joined = metrics.reviews()
fee = ins["fee"]
st.markdown(f'<p class="sub">Ranking rule: {ui.esc(ins["ranking_rule"])}. Themes are ranked by unhappy (1-2 star) reviews, never by total volume.</p>', unsafe_allow_html=True)

if joined is None:
    ui.empty_state("The review and assignment files", "Run make collect and make analyze to draw the charts.")
else:
    joined = joined.assign(theme=joined["theme_id"].map(names))
    order = [names[t["theme_id"]] for t in sorted(stats.values(), key=lambda t: (rank.get(t["theme_id"], 99), -t["low_star"]))]
    weeks = sorted(joined["week_start"].unique())

    # ---------------------------------------------------------------- filters
    with ui.card_container("filters"):
        f1, f2, f3 = st.columns([2.2, 2.4, 1.4])
        picked = f1.multiselect("Themes", order, default=order, key="ins_themes")
        lo, hi = f2.select_slider("Week range", options=weeks, value=(weeks[0], weeks[-1]), key="ins_weeks")
        metric_choice = f3.radio("Weekly lines show", ["All reviews", "1-2 star only"], horizontal=False, key="ins_metric")
    sel = joined[joined["theme"].isin(picked) & (joined["week_start"] >= lo) & (joined["week_start"] <= hi)]
    if sel.empty:
        ui.empty_state("A chart for this selection", "Pick at least one theme and a week range that contains reviews.")
        st.stop()
    low_n = int((sel["rating"] <= 2).sum())
    k1, k2, k3 = st.columns(3)
    k1.markdown(ui.metric("Reviews in selection", f"{len(sel):,}", f"{lo} to {hi}"), unsafe_allow_html=True)
    k2.markdown(ui.metric("1-2 star reviews", f"{low_n:,}", f"{100 * low_n / len(sel):.1f}% of the selection"), unsafe_allow_html=True)
    k3.markdown(ui.metric("Themes shown", len(picked), "Use the filters above"), unsafe_allow_html=True)

    # ---------------------------------------------------------------- row 1: stacked bars + donut
    by_theme = sel.assign(group=sel["rating"].map(lambda r: charts.LOW if r <= 2 else charts.HIGH)).groupby(["theme", "group"]).size().reset_index(name="reviews")
    share = sel.groupby("theme").size().reset_index(name="reviews")
    c1, c2 = st.columns([3, 2])
    with c1:
        with ui.card_container("c_breakdown"):
            st.markdown('<div class="card-head"><h3>Reviews by theme</h3></div>', unsafe_allow_html=True)
            charts.show(charts.theme_breakdown(by_theme, [o for o in order if o in picked]), 280)
            st.caption("Rose = 1-2 star (unhappy), grey = 3-5 star. Hover for counts.")
    with c2:
        with ui.card_container("c_share"):
            st.markdown('<div class="card-head"><h3>Share of reviews</h3></div>', unsafe_allow_html=True)
            doms = [o for o in order if o in picked]
            charts.show(charts.donut(share, "theme", "reviews", doms, [charts.PALETTE[order.index(d) % len(charts.PALETTE)] for d in doms], "Theme"), 280)
            st.caption("Click a legend entry to isolate a theme.")

    # ---------------------------------------------------------------- row 2: weekly lines
    only_low = metric_choice == "1-2 star only"
    base = sel[sel["rating"] <= 2] if only_low else sel
    weekly = base.groupby(["week_start", "theme"]).size().reset_index(name="reviews").rename(columns={"week_start": "week"})
    full_grid = pd.MultiIndex.from_product([sorted(sel["week_start"].unique()), picked], names=["week", "theme"]).to_frame(index=False)
    weekly = full_grid.merge(weekly, on=["week", "theme"], how="left").fillna({"reviews": 0})
    with ui.card_container("c_weekly"):
        st.markdown(f'<div class="card-head"><h3>Weekly trend by theme</h3>{ui.pill("", metric_choice)}</div>', unsafe_allow_html=True)
        charts.show(charts.weekly_lines(weekly, order, "Reviews per week"), 320)
        st.caption("Click a legend entry to isolate a theme. Drag to pan and scroll to zoom. Weekly counts come from the analysed sample, which is capped per week.")

    # ---------------------------------------------------------------- row 3: heatmap + trend bars
    heat = sel.groupby(["theme", "rating"]).size().reset_index(name="reviews")
    heat = pd.MultiIndex.from_product([picked, [1, 2, 3, 4, 5]], names=["theme", "rating"]).to_frame(index=False).merge(heat, on=["theme", "rating"], how="left").fillna({"reviews": 0})
    trend_rows = []
    for t in ins["trend"]:
        trend_rows += [{"theme": names.get(t["theme_id"], t["theme_id"]), "period": "Previous 4 weeks", "reviews": t["prev4"]},
                       {"theme": names.get(t["theme_id"], t["theme_id"]), "period": "Last 4 weeks", "reviews": t["last4"]}]
    c3, c4 = st.columns(2)
    with c3:
        with ui.card_container("c_heat"):
            st.markdown('<div class="card-head"><h3>Star ratings by theme</h3></div>', unsafe_allow_html=True)
            charts.show(charts.rating_heat(heat, [o for o in order if o in picked]), 280)
    with c4:
        with ui.card_container("c_trend"):
            st.markdown('<div class="card-head"><h3>Top 3: last 4 weeks vs the 4 before</h3></div>', unsafe_allow_html=True)
            charts.show(charts.trend_bars(pd.DataFrame(trend_rows), [names.get(tid, tid) for tid in ins["top3"]]), 280)
            st.caption("Always uses the full window, as in the ranking.")

# ---------------------------------------------------------------- fee charts
labels = metrics.read_csv(config.FEE_LABELS_CSV)
c5, c6 = st.columns([2, 3])
with c5:
    with ui.card_container("c_fee_donut"):
        st.markdown('<div class="card-head"><h3>Fee-related reviews by stance</h3></div>', unsafe_allow_html=True)
        stance_df = pd.DataFrame([{"stance": charts.STANCE_LABELS[k], "reviews": fee[k]} for k in charts.STANCE_COLORS])
        charts.show(charts.donut(stance_df, "stance", "reviews", list(stance_df["stance"]), [charts.STANCE_COLORS[k] for k in charts.STANCE_COLORS], "Stance"), 280)
        st.caption(f"{fee['money_reviews']} money-related reviews in total.")
with c6:
    with ui.card_container("c_fee_topics"):
        st.markdown('<div class="card-head"><h3>Fee topics and stance</h3></div>', unsafe_allow_html=True)
        if labels is None:
            ui.empty_state("The fee labels", "Run make analyze.")
        else:
            ft = labels.assign(topic=labels["fee_topic"].str.replace("_", " "), stance=labels["stance"].map(charts.STANCE_LABELS)).groupby(["topic", "stance"]).size().reset_index(name="reviews")
            topic_order = list(ft.groupby("topic")["reviews"].sum().sort_values(ascending=False).index)
            charts.show(charts.fee_topic_stack(ft, topic_order), 280)
            st.caption("Confused means the user does not understand a charge. Too expensive is a complaint, not confusion.")

# ---------------------------------------------------------------- quotes and voice
st.subheader("Supporting quotes")
st.caption("Copied word for word from real reviews and checked against the review file.")
for q in ins["quotes"]:
    st.markdown(
        f'<div class="card"><div class="quote">"{ui.esc(q["excerpt"])}"<div class="meta">{ui.esc(names.get(q["theme_id"], q["theme_id"]))}, {ui.esc(q["rating"])} star, {ui.esc(q["date"])}</div></div></div>',
        unsafe_allow_html=True,
    )
v = ins["voice_tag"]
st.markdown(ui.metric("Voice-related reviews", v["count"], f"{v['low_star']} of them are 1-2 star"), unsafe_allow_html=True)

# ---------------------------------------------------------------- tables (the exact numbers behind the charts)
with st.expander("Data tables: themes, trend and fee stance"):
    ordered = sorted(stats.values(), key=lambda t: (rank.get(t["theme_id"], 99), -t["low_star"]))
    ui.table(["Rank", "Theme", "All reviews", "1-2 star", "1-2 star share"],
             [[rank.get(t["theme_id"], "-"), t["name"], t["total"], t["low_star"], f"{100 * t['low_star_share']:.1f}%"] for t in ordered])

    def _dir(p: int, last: int) -> str:
        return "Rising" if last > p else "Falling" if last < p else "Flat"

    ui.table(["Theme", "Previous 4 weeks", "Last 4 weeks", "Direction"],
             [[names.get(t["theme_id"], t["theme_id"]), t["prev4"], t["last4"], _dir(t["prev4"], t["last4"])] for t in ins["trend"]])
    ui.table(["Stance", "Reviews"],
             [["Confused (does not understand a charge)", fee["confused"]], ["Complaint only", fee["complaint_only"]], ["Praise", fee["praise"]],
              ["Unrelated", fee["unrelated"]], ["All money-related reviews", fee["money_reviews"]]])
