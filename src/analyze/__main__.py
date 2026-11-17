"""Implements architecture §6/§4 entry point for `make analyze`: themes, assignments, insights.json."""

from __future__ import annotations

import json

import pandas as pd

from src import config
from src.analyze.classify import classify_all
from src.analyze.fee import run_fee
from src.analyze.quotes import pick_quote
from src.analyze.rank import compute_theme_stats, load_joined, rank_top3, ranking_rule
from src.analyze.themes import discover_themes
from src.analyze.trend import compute_trend, compute_voice_tag, compute_window
from src.logging_config import setup_logging

EMPTY_FEE = {"topic": "", "confused": 0, "complaint_only": 0, "praise": 0, "unrelated": 0, "money_reviews": 0}


def _themes() -> list[dict]:
    if config.THEMES_JSON.exists() and config.THEMES_JSON.stat().st_size > 0:
        print("reusing existing data/themes.json (delete it to rediscover)")
        return json.loads(config.THEMES_JSON.read_text(encoding="utf-8"))
    return discover_themes()


def _assignments_complete() -> bool:
    if not config.ASSIGNMENTS_CSV.exists() or config.ASSIGNMENTS_CSV.stat().st_size == 0:
        return False
    done = set(pd.read_csv(config.ASSIGNMENTS_CSV)["review_id"])
    return done == set(pd.read_csv(config.REVIEWS_BALANCED_CSV)["review_id"])


def main() -> None:
    setup_logging()
    themes = _themes()
    print(f"{len(themes)} themes: {[t['name'] for t in themes]}")
    if _assignments_complete():
        print("reusing complete data/assignments.csv")
    else:
        print(f"assigned {len(classify_all(themes))} reviews")

    joined, themes = load_joined()
    stats = compute_theme_stats(joined, themes)
    top3 = rank_top3(stats)
    by_id = {t["theme_id"]: t for t in themes}
    previous_fee = EMPTY_FEE
    if config.INSIGHTS_JSON.exists() and config.INSIGHTS_JSON.stat().st_size > 0:
        previous_fee = json.loads(config.INSIGHTS_JSON.read_text(encoding="utf-8")).get("fee", EMPTY_FEE)
    insights = {
        "window": compute_window(joined),
        "themes": stats,
        "top3": top3,
        "ranking_rule": ranking_rule(),
        "quotes": [pick_quote(joined, by_id[tid]) for tid in top3],
        "trend": compute_trend(joined, top3),
        "voice_tag": compute_voice_tag(joined),
        "fee": previous_fee,  # filled in by phase P4
    }
    config.INSIGHTS_JSON.write_text(json.dumps(insights, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {config.INSIGHTS_JSON.name}: top3 = {[by_id[t]['name'] for t in top3]}")
    run_fee()


if __name__ == "__main__":
    main()
