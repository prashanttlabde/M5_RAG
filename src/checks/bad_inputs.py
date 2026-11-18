"""Implements architecture §12 bad-input handling: a review-file validator and six broken inputs it must catch.

No LLM, no network. `validate_reviews_csv` never raises; it returns a list of human-readable problems
(empty list = file is acceptable).
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ("review_id", "date", "week_start", "rating", "text")
NAME_COLUMNS = {"author", "username", "user_name", "name", "reviewer", "reviewername"}
MIN_ROWS = 100
MIN_WEEKS, MAX_WEEKS = 8, 12
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"(?<!\d)\+?\d(?:[\s().-]?\d){9,}(?!\d)")


def find_pii(text: str) -> bool:
    """True if the text contains an email address or a phone-number-like digit run (10+ digits)."""
    return bool(EMAIL.search(text) or PHONE.search(text))


def validate_reviews_csv(path: Path) -> list[str]:
    """Return the problems found in a reviews CSV (never raises)."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return ["file is empty or missing"]
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001 - any unreadable file is just a problem to report
        return [f"file could not be read ({type(exc).__name__})"]
    problems: list[str] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        problems.append(f"missing columns: {missing}")
    present_names = sorted(c for c in df.columns if c.lower() in NAME_COLUMNS)
    if present_names:
        problems.append(f"reviewer name column present: {present_names}")
    if len(df) < MIN_ROWS:
        problems.append(f"too few reviews ({len(df)} < {MIN_ROWS})")
    if "rating" in df.columns:
        ratings = pd.to_numeric(df["rating"], errors="coerce")
        if ratings.isna().any():
            problems.append(f"{int(ratings.isna().sum())} non-numeric ratings")
        bad = ratings.dropna()
        out_of_range = int(((bad < 1) | (bad > 5) | (bad != bad.round())).sum())
        if out_of_range:
            problems.append(f"{out_of_range} ratings outside 1-5")
    if "text" in df.columns:
        texts = df["text"].astype(str)
        blank = int((df["text"].isna() | (texts.str.strip() == "")).sum())
        if blank:
            problems.append(f"{blank} blank review texts")
        pii = int(texts.apply(find_pii).sum())
        if pii:
            problems.append(f"possible personal data (email/phone) in {pii} reviews")
    if "week_start" in df.columns:
        weeks = df["week_start"].nunique()
        if not MIN_WEEKS <= weeks <= MAX_WEEKS:
            problems.append(f"{weeks} weeks of data (need {MIN_WEEKS}-{MAX_WEEKS})")
    return problems


def _clean_frame(weeks: int = 10, per_week: int = 20) -> pd.DataFrame:
    rows = []
    for w in range(weeks):
        start = (pd.Timestamp("2026-01-05") + pd.Timedelta(weeks=w)).date().isoformat()
        for i in range(per_week):
            rows.append(
                {"review_id": f"r{w}-{i}", "date": start, "week_start": start, "rating": 1 + (i % 5),
                 "text": f"this is review number {i} of week {w} and it has enough words"}
            )
    return pd.DataFrame(rows)


def _cases() -> dict[str, tuple[callable, str]]:
    """name -> (builder(path), substring expected in the problems). 'clean' must produce no problems."""
    def clean(p: Path):
        _clean_frame().to_csv(p, index=False)

    def empty(p: Path):
        p.write_text("")

    def missing_column(p: Path):
        _clean_frame().drop(columns=["rating"]).to_csv(p, index=False)

    def twenty_rows(p: Path):
        _clean_frame(weeks=10, per_week=2).to_csv(p, index=False)

    def bad_ratings(p: Path):
        df = _clean_frame().astype({"rating": object})
        df.loc[0, "rating"], df.loc[1, "rating"] = 0, "good"
        df.to_csv(p, index=False)

    def phone_number(p: Path):
        df = _clean_frame()
        df.loc[3, "text"] = "call me on +91 98765 43210 about my refund please"
        df.to_csv(p, index=False)

    def twenty_weeks(p: Path):
        _clean_frame(weeks=20, per_week=10).to_csv(p, index=False)

    return {
        "clean file (control)": (clean, ""),
        "empty file": (empty, "empty"),
        "missing column": (missing_column, "missing columns"),
        "only 20 rows": (twenty_rows, "too few reviews"),
        "ratings 0 and 'good'": (bad_ratings, "ratings"),
        "phone number inside a review": (phone_number, "personal data"),
        "20 weeks of data": (twenty_weeks, "weeks of data"),
    }


def run_bad_input_cases() -> list[dict]:
    """Build each broken file in a temp dir and confirm the validator catches it. Safe and offline."""
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, (build, expected) in _cases().items():
            path = Path(tmp) / "reviews.csv"
            build(path)
            problems = validate_reviews_csv(path)
            ok = (not problems) if not expected else any(expected in p for p in problems)
            results.append({"case": name, "ok": ok, "problems": problems})
    return results
