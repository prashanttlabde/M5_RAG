"""Implements architecture §4 insights (counts and ranking) — code only, INV-1.

Rule (written in config/product.yaml before results): rank themes by count of 1-2 star reviews;
ties: higher low-star share, then alphabetical by theme name. Never rank by total volume.
"""

from __future__ import annotations

import json

import pandas as pd

from src import config
from src.errors import DataError

LOW_STAR_MAX = 2


def load_joined() -> tuple[pd.DataFrame, list[dict]]:
    """Balanced reviews joined with their theme assignment, plus the theme list."""
    for path in (config.REVIEWS_BALANCED_CSV, config.ASSIGNMENTS_CSV, config.THEMES_JSON):
        if not path.exists() or path.stat().st_size == 0:
            raise DataError(f"{path.name} missing or empty. Run `make analyze` steps first.")
    reviews = pd.read_csv(config.REVIEWS_BALANCED_CSV)
    assignments = pd.read_csv(config.ASSIGNMENTS_CSV)
    themes = json.loads(config.THEMES_JSON.read_text(encoding="utf-8"))
    joined = reviews.merge(assignments, on="review_id", how="inner")
    if len(joined) != len(reviews):
        raise DataError(f"{len(reviews) - len(joined)} reviews have no theme assignment.")
    return joined, themes


def compute_theme_stats(joined: pd.DataFrame, themes: list[dict]) -> list[dict]:
    """Per-theme total, low-star count and low-star share."""
    stats = []
    for theme in themes:
        sub = joined[joined["theme_id"] == theme["theme_id"]]
        total = len(sub)
        low = int((sub["rating"] <= LOW_STAR_MAX).sum())
        stats.append(
            {
                "theme_id": theme["theme_id"],
                "name": theme["name"],
                "total": total,
                "low_star": low,
                "low_star_share": round(low / total, 4) if total else 0.0,
            }
        )
    return stats


def rank_top3(stats: list[dict]) -> list[str]:
    """Top 3 theme_ids: low_star desc, low_star_share desc, name asc (case-insensitive)."""
    ordered = sorted(stats, key=lambda t: (-t["low_star"], -t["low_star_share"], t["name"].lower()))
    return [t["theme_id"] for t in ordered[:3]]


def ranking_rule() -> str:
    """The rule text, read from config (written before results were seen)."""
    return str(config.get_product_config()["ranking_rule"])
