"""Implements architecture §10 interactive charts (Altair, bundled with Streamlit).

Every chart is drawn from DataFrames that code computed from the saved review and label files.
Tooltips, legend click-to-filter and pan/zoom are native Altair interactions.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import ui

PALETTE = ["#4F46E5", "#10B981", "#F59E0B", "#F43F5E", "#0EA5E9", "#8B5CF6"]
STANCE_COLORS = {"confused": "#F59E0B", "complaint_only": "#F43F5E", "praise": "#10B981", "unrelated": "#94A3B8"}
STANCE_LABELS = {"confused": "Confused", "complaint_only": "Complaint only", "praise": "Praise", "unrelated": "Unrelated"}
LOW, HIGH = "1-2 star", "3-5 star"


def _tok() -> dict:
    return ui.TOKENS["dark" if ui.is_dark() else "light"]


def _style(chart: alt.Chart | alt.LayerChart, height: int = 300) -> alt.Chart:
    t = _tok()
    return (
        chart.properties(height=height, background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(labelColor=t["muted"], titleColor=t["muted"], gridColor=t["border"], domainColor=t["border"], tickColor=t["border"],
                        labelFont="Inter", titleFont="Inter", labelFontSize=12, titleFontSize=12)
        .configure_legend(labelColor=t["text"], titleColor=t["muted"], labelFont="Inter", orient="bottom", symbolType="circle")
        .configure_title(color=t["text"], font="Inter")
    )


def show(chart: alt.Chart | alt.LayerChart, height: int = 300) -> None:
    import streamlit as st

    st.altair_chart(_style(chart, height), width="stretch", theme=None)


def theme_colors(names: list[str]) -> alt.Scale:
    return alt.Scale(domain=names, range=[PALETTE[i % len(PALETTE)] for i in range(len(names))])


def theme_breakdown(df: pd.DataFrame, order: list[str]) -> alt.Chart:
    """Stacked horizontal bars: 1-2 star vs 3-5 star reviews per theme (df: theme, group, reviews)."""
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, height=22)
        .encode(
            y=alt.Y("theme:N", sort=order, title=None),
            x=alt.X("reviews:Q", title="Reviews", stack="zero"),
            color=alt.Color("group:N", scale=alt.Scale(domain=[LOW, HIGH], range=["#F43F5E", "#CBD5E1" if not ui.is_dark() else "#475569"]), title=None),
            order=alt.Order("group:N", sort="ascending"),
            tooltip=[alt.Tooltip("theme:N", title="Theme"), alt.Tooltip("group:N", title="Rating group"), alt.Tooltip("reviews:Q", title="Reviews", format=",")],
        )
    )


def donut(df: pd.DataFrame, category: str, value: str, domain: list[str], colors: list[str], title: str) -> alt.Chart:
    """Donut chart with a hover tooltip and click-to-isolate legend."""
    sel = alt.selection_point(fields=[category], bind="legend")
    return (
        alt.Chart(df)
        .mark_arc(innerRadius=62, outerRadius=105, stroke=_tok()["surface"], strokeWidth=2)
        .encode(
            theta=alt.Theta(f"{value}:Q", stack=True),
            color=alt.Color(f"{category}:N", scale=alt.Scale(domain=domain, range=colors), title=None, legend=alt.Legend(columns=3, orient="bottom")),
            opacity=alt.condition(sel, alt.value(1), alt.value(0.25)),
            tooltip=[alt.Tooltip(f"{category}:N", title=title), alt.Tooltip(f"{value}:Q", title="Reviews", format=",")],
        )
        .add_params(sel)
    )


def weekly_lines(df: pd.DataFrame, names: list[str], metric_title: str) -> alt.Chart:
    """Weekly line per theme (df: week, theme, reviews). Click the legend to isolate a theme; drag to pan, scroll to zoom."""
    sel = alt.selection_point(fields=["theme"], bind="legend")
    return (
        alt.Chart(df)
        .mark_line(point=alt.OverlayMarkDef(filled=True, size=55), strokeWidth=2.5, interpolate="monotone")
        .encode(
            x=alt.X("week:T", title=None, axis=alt.Axis(format="%b %d")),
            y=alt.Y("reviews:Q", title=metric_title),
            color=alt.Color("theme:N", scale=theme_colors(names), title=None),
            opacity=alt.condition(sel, alt.value(1), alt.value(0.15)),
            tooltip=[alt.Tooltip("week:T", title="Week of", format="%Y-%m-%d"), alt.Tooltip("theme:N", title="Theme"), alt.Tooltip("reviews:Q", title="Reviews", format=",")],
        )
        .add_params(sel)
        .interactive(bind_y=False)
    )


def rating_heat(df: pd.DataFrame, order: list[str]) -> alt.LayerChart:
    """Theme x star-rating heatmap with counts in the cells (df: theme, rating, reviews)."""
    t = _tok()
    top = max(float(df["reviews"].max()), 1.0)
    base = alt.Chart(df).encode(
        x=alt.X("rating:O", title="Star rating", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("theme:N", sort=order, title=None),
    )
    rect = base.mark_rect(cornerRadius=4, stroke=t["surface"], strokeWidth=2).encode(
        color=alt.Color("reviews:Q", scale=alt.Scale(range=[t["accent_soft"] if not ui.is_dark() else "#1E1B4B", "#4F46E5"]), legend=None),
        tooltip=[alt.Tooltip("theme:N", title="Theme"), alt.Tooltip("rating:O", title="Stars"), alt.Tooltip("reviews:Q", title="Reviews", format=",")],
    )
    text = base.mark_text(font="Inter", fontSize=12, fontWeight=600).encode(
        text=alt.Text("reviews:Q", format=","),
        color=alt.condition(alt.datum.reviews > top * 0.5, alt.value("#FFFFFF"), alt.value(t["text"])),
    )
    return alt.layer(rect, text)


def trend_bars(df: pd.DataFrame, order: list[str]) -> alt.Chart:
    """Grouped bars: previous 4 weeks vs last 4 weeks per top theme (df: theme, period, reviews)."""
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("theme:N", sort=order, title=None, axis=alt.Axis(labelAngle=0, labelLimit=120)),
            xOffset=alt.XOffset("period:N", sort=["Previous 4 weeks", "Last 4 weeks"]),
            y=alt.Y("reviews:Q", title="Reviews"),
            color=alt.Color("period:N", scale=alt.Scale(domain=["Previous 4 weeks", "Last 4 weeks"], range=["#A5B4FC", "#4F46E5"]), title=None),
            tooltip=[alt.Tooltip("theme:N", title="Theme"), alt.Tooltip("period:N", title="Period"), alt.Tooltip("reviews:Q", title="Reviews", format=",")],
        )
    )


def fee_topic_stack(df: pd.DataFrame, order: list[str]) -> alt.Chart:
    """Stacked horizontal bars: stance per fee topic (df: topic, stance, reviews)."""
    stances = list(STANCE_COLORS)
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, height=20)
        .encode(
            y=alt.Y("topic:N", sort=order, title=None),
            x=alt.X("reviews:Q", title="Money-related reviews", stack="zero"),
            color=alt.Color("stance:N", scale=alt.Scale(domain=[STANCE_LABELS[s] for s in stances], range=[STANCE_COLORS[s] for s in stances]), title=None),
            tooltip=[alt.Tooltip("topic:N", title="Fee topic"), alt.Tooltip("stance:N", title="Stance"), alt.Tooltip("reviews:Q", title="Reviews", format=",")],
        )
    )
