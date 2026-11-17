"""Implements architecture review intelligence: Play Store scrape (PRD FR1)."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml
from google_play_scraper import Sort, reviews

from src.config import DATA_DIR, PRODUCT_YAML
from src.errors import ConfigError, DataError
from src.logging_config import setup_logging

logger = setup_logging()

RAW_REVIEWS_CSV: Path = DATA_DIR / "reviews_raw.csv"


def _load_product() -> dict:
    if not PRODUCT_YAML.exists():
        raise ConfigError(f"Missing product config: {PRODUCT_YAML}")
    with PRODUCT_YAML.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    required = ["app_id", "country", "lang", "weeks"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ConfigError(f"product.yaml missing keys: {missing}")
    return data


def _as_utc(at: object) -> datetime:
    if isinstance(at, datetime):
        return at if at.tzinfo else at.replace(tzinfo=UTC)
    return pd.to_datetime(at, utc=True).to_pydatetime()


def _week_start_date(at_dt: datetime) -> str:
    local = at_dt.astimezone(UTC).date()
    monday = local - timedelta(days=local.weekday())
    return monday.isoformat()


def _scrape_score(
    *,
    app_id: str,
    country: str,
    lang: str,
    score: int,
    cutoff: datetime,
    batch_size: int,
    sleep_s: float,
    max_reviews: int,
    reach_cutoff: bool,
    max_keep_per_week: int,
) -> list[dict]:
    """
    Scrape newest-first for one star rating.

    When reach_cutoff is true, keep paginating until reviews fall before cutoff,
    but only retain max_keep_per_week rows per week (still advances the token).
    """
    rows: list[dict] = []
    kept_per_week: dict[str, int] = defaultdict(int)
    pages = 0
    continuation_token = None
    stop = False
    # Hard safety on API pages when walking high-volume weeks toward cutoff.
    max_pages = 400 if reach_cutoff else 80

    while not stop and pages < max_pages:
        try:
            batch, continuation_token = reviews(
                app_id,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=batch_size,
                filter_score_with=score,
                continuation_token=continuation_token,
            )
        except Exception as exc:
            raise DataError(f"Play Store scrape failed (score={score}): {exc}") from exc

        pages += 1
        if not batch:
            break

        for item in batch:
            # Never keep userName or other personal fields (INV-6).
            review_id = str(item.get("reviewId") or "").strip()
            text = (item.get("content") or "").strip()
            item_score = item.get("score")
            at = item.get("at")
            if not review_id or item_score is None or at is None:
                continue

            at_dt = _as_utc(at)
            if at_dt < cutoff:
                stop = True
                break

            week = _week_start_date(at_dt)
            if kept_per_week[week] >= max_keep_per_week:
                # Skip store, but continue paging so we can reach older weeks.
                continue
            if len(rows) >= max_reviews:
                if reach_cutoff:
                    # Still need to walk older pages; do not append more rows.
                    continue
                stop = True
                break

            kept_per_week[week] += 1
            rows.append(
                {
                    "review_id": review_id,
                    "date": at_dt.date().isoformat(),
                    "rating": int(item_score),
                    "text": text,
                }
            )

        oldest_kept = min((r["date"] for r in rows), default=None)
        logger.info(
            "score=%s pages=%s kept=%s weeks=%s oldest_kept=%s",
            score,
            pages,
            len(rows),
            len(kept_per_week),
            oldest_kept,
        )

        if not reach_cutoff and len(rows) >= max_reviews:
            break
        if continuation_token is None or getattr(continuation_token, "token", None) is None:
            break
        if sleep_s > 0:
            time.sleep(sleep_s)

    return rows


def scrape_reviews() -> Path:
    """
    Scrape newest-first Play Store reviews for the configured app.

    Drops reviewer names at collection (INV-6). Writes review_id, date, rating, text
    to data/reviews_raw.csv and returns that path.
    """
    product = _load_product()
    app_id = str(product["app_id"])
    country = str(product["country"])
    lang = str(product["lang"])
    weeks = int(product["weeks"])
    batch_size = int(product.get("scrape_batch_size", 200))
    sleep_s = float(product.get("scrape_sleep_seconds", 0.5))
    score_cfg = product.get("scrape_scores") or {}

    cutoff = datetime.now(UTC) - timedelta(weeks=weeks)
    logger.info(
        "Scraping %s country=%s lang=%s weeks=%s cutoff=%s",
        app_id,
        country,
        lang,
        weeks,
        cutoff.date().isoformat(),
    )

    all_rows: list[dict] = []
    for score in (1, 2, 3, 4, 5):
        cfg = score_cfg.get(score) or score_cfg.get(str(score)) or {}
        all_rows.extend(
            _scrape_score(
                app_id=app_id,
                country=country,
                lang=lang,
                score=score,
                cutoff=cutoff,
                batch_size=batch_size,
                sleep_s=sleep_s,
                max_reviews=int(cfg.get("max_reviews", 3000)),
                reach_cutoff=bool(cfg.get("reach_cutoff", False)),
                max_keep_per_week=int(cfg.get("max_keep_per_week", 200)),
            )
        )

    if not all_rows:
        raise DataError("Scrape returned zero reviews inside the configured window.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(all_rows, columns=["review_id", "date", "rating", "text"])
    df = df.drop_duplicates(subset=["review_id"], keep="first")
    df = df.sort_values(["date", "review_id"], ascending=[False, True]).reset_index(drop=True)
    df.to_csv(RAW_REVIEWS_CSV, index=False)
    logger.info(
        "Wrote %s (%s rows, dates %s .. %s, weeks~%s)",
        RAW_REVIEWS_CSV,
        len(df),
        df["date"].min(),
        df["date"].max(),
        pd.to_datetime(df["date"]).dt.to_period("W-SUN").nunique(),
    )
    return RAW_REVIEWS_CSV


if __name__ == "__main__":
    path = scrape_reviews()
    print(f"Wrote raw reviews to {path}")
