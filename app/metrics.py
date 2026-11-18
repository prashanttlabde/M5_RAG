"""Implements architecture §10 data access for the UI: cached, read-only views of the computed files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `src` importable on hosts that do not set PYTHONPATH

import pandas as pd
import streamlit as st

from src import config


@st.cache_data(show_spinner=False)
def _csv(path: str, mtime: float) -> pd.DataFrame:
    return pd.read_csv(path)


def read_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    return _csv(str(path), path.stat().st_mtime)


def reviews() -> pd.DataFrame | None:
    """Balanced reviews joined with their theme assignment (None if either file is missing)."""
    r, a = read_csv(config.REVIEWS_BALANCED_CSV), read_csv(config.ASSIGNMENTS_CSV)
    if r is None or a is None:
        return None
    return r.merge(a, on="review_id", how="inner")


def collected_count() -> int | None:
    full = read_csv(config.REVIEWS_FULL_CSV)
    return None if full is None else len(full)


def weekly_counts() -> pd.Series | None:
    r = read_csv(config.REVIEWS_BALANCED_CSV)
    return None if r is None else r.groupby("week_start").size().sort_index()


def weeks_gap_count(weeks: list[str]) -> int:
    """Number of missing weeks between the first and last week (0 = continuous)."""
    if len(weeks) < 2:
        return 0
    days = pd.to_datetime(pd.Series(sorted(weeks)))
    expected = (days.iloc[-1] - days.iloc[0]).days // 7 + 1
    return int(expected - len(days))


def checks_summary() -> tuple[int, int] | None:
    """(passed, total) parsed from outputs/checks_report.md."""
    if not config.CHECKS_REPORT_MD.exists():
        return None
    m = re.search(r"(\d+) of (\d+) checks passed", config.CHECKS_REPORT_MD.read_text(encoding="utf-8"))
    return (int(m.group(1)), int(m.group(2))) if m else None
