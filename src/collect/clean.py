"""Implements architecture review cleaning and balancing (PRD FR1, FR2)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from src.collect.scrape import RAW_REVIEWS_CSV
from src.config import (
    DATA_DIR,
    PRODUCT_YAML,
    REVIEWS_BALANCED_CSV,
    REVIEWS_FULL_CSV,
)
from src.errors import ConfigError, DataError
from src.logging_config import setup_logging

logger = setup_logging()

KEYWORD_SUMMARY_CSV: Path = DATA_DIR / "keyword_summary.csv"


def _load_product() -> dict:
    if not PRODUCT_YAML.exists():
        raise ConfigError(f"Missing product config: {PRODUCT_YAML}")
    with PRODUCT_YAML.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _word_count(text: str) -> int:
    return len([w for w in str(text).split() if w])


def _week_start(series: pd.Series) -> pd.Series:
    """Monday week start as ISO date string."""
    dates = pd.to_datetime(series, utc=True)
    mondays = dates.dt.normalize() - pd.to_timedelta(dates.dt.day_of_week, unit="D")
    return mondays.dt.date.astype(str)


def clean_and_balance(raw_path: Path | None = None) -> tuple[Path, Path]:
    """
    Clean raw reviews, add week_start, write full + balanced CSVs.

    Drops blanks, under-min-word reviews, and duplicates. Caps each week at
    max_reviews_per_week (newest first). Raises DataError if fewer than 8 weeks.
    """
    product = _load_product()
    min_words = int(product.get("min_review_words", 5))
    max_per_week = int(product.get("max_reviews_per_week", 200))
    weeks_target = int(product.get("weeks", 12))
    summary_terms = list(product.get("keyword_summary_terms") or [])

    path = raw_path or RAW_REVIEWS_CSV
    if not path.exists():
        raise DataError(f"Raw reviews file not found: {path}. Run scrape first.")

    df = pd.read_csv(path)
    required = ["review_id", "date", "rating", "text"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataError(f"Raw reviews missing columns: {missing}")

    # INV-6: never keep a name column even if present upstream.
    drop_pii = [c for c in df.columns if c.lower() in {"username", "user_name", "name", "userid", "user_id"}]
    if drop_pii:
        df = df.drop(columns=drop_pii)

    df["text"] = df["text"].fillna("").astype(str).str.strip()
    df = df[df["text"] != ""]
    df = df[df["text"].map(_word_count) >= min_words]
    df = df.drop_duplicates(subset=["review_id"], keep="first")
    df = df.drop_duplicates(subset=["text"], keep="first")

    df["week_start"] = _week_start(df["date"])
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.dropna(subset=["rating"])
    df["rating"] = df["rating"].astype(int)

    df = df.sort_values(["date", "review_id"], ascending=[False, True])
    full = df[["review_id", "date", "week_start", "rating", "text"]].reset_index(drop=True)

    week_count = int(full["week_start"].nunique())
    if week_count < 8:
        raise DataError(
            f"Only {week_count} distinct weeks after cleaning; need at least 8 "
            f"(configured window {weeks_target} weeks). Collect more reviews or widen the window."
        )
    if week_count > 12:
        # Keep the newest 12 week_start values only.
        newest_weeks = sorted(full["week_start"].unique(), reverse=True)[:12]
        full = full[full["week_start"].isin(newest_weeks)].reset_index(drop=True)
        week_count = int(full["week_start"].nunique())

    balanced = (
        full.groupby("week_start", group_keys=False)
        .head(max_per_week)
        .reset_index(drop=True)
    )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    full.to_csv(REVIEWS_FULL_CSV, index=False)
    balanced.to_csv(REVIEWS_BALANCED_CSV, index=False)

    _write_keyword_summary(full, summary_terms)

    logger.info(
        "Cleaned full=%s balanced=%s weeks=%s max_per_week=%s",
        len(full),
        len(balanced),
        week_count,
        int(balanced.groupby("week_start").size().max()) if len(balanced) else 0,
    )
    return REVIEWS_FULL_CSV, REVIEWS_BALANCED_CSV


def _write_keyword_summary(df: pd.DataFrame, terms: list[str]) -> None:
    rows = []
    texts = df["text"].fillna("").astype(str)
    for term in terms:
        needle = term.lower()
        hits = int(texts.str.lower().str.contains(rf"\b{needle}\b", regex=True, na=False).sum())
        rows.append({"keyword": term, "review_hits": hits})
    summary = pd.DataFrame(rows)
    summary.to_csv(KEYWORD_SUMMARY_CSV, index=False)
    # Also print a simple table for the human verification step.
    print("\nKeyword summary (reviews containing each term):")
    print(summary.to_string(index=False))
    print(f"\nWrote {KEYWORD_SUMMARY_CSV}")


def run_collect() -> None:
    """Scrape then clean (used by `make collect`)."""
    from src.collect.scrape import scrape_reviews

    raw = scrape_reviews()
    clean_and_balance(raw)


if __name__ == "__main__":
    run_collect()
