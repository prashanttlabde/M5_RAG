"""Implements architecture §4 trend + voice tag + window — code only, INV-1."""

from __future__ import annotations

import re

import pandas as pd

from src import config

TREND_WEEKS = 4


def compute_window(joined: pd.DataFrame) -> dict:
    return {
        "start": str(joined["week_start"].min()),
        "end": str(joined["date"].max()),
        "weeks": int(joined["week_start"].nunique()),
        "review_count": len(joined),
    }


def compute_trend(joined: pd.DataFrame, theme_ids: list[str]) -> list[dict]:
    """Review counts in the last 4 weeks vs the 4 weeks before, per theme."""
    weeks = sorted(joined["week_start"].unique())
    last = set(weeks[-TREND_WEEKS:])
    prev = set(weeks[-2 * TREND_WEEKS : -TREND_WEEKS])
    out = []
    for tid in theme_ids:
        sub = joined[joined["theme_id"] == tid]
        out.append(
            {
                "theme_id": tid,
                "prev4": int(sub["week_start"].isin(prev).sum()),
                "last4": int(sub["week_start"].isin(last).sum()),
            }
        )
    return out


def compute_voice_tag(joined: pd.DataFrame) -> dict:
    """Reviews mentioning a voice keyword (whole-word, case-insensitive) and how many are 1-2 star."""
    words = config.get_product_config()["voice_keywords"]
    pattern = re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.IGNORECASE)
    hit = joined["text"].astype(str).apply(lambda t: bool(pattern.search(t)))
    return {"count": int(hit.sum()), "low_star": int((hit & (joined["rating"] <= 2)).sum())}
