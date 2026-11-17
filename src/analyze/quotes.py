"""Implements architecture §4 quotes: LLM picks a review, code copies the text (INV-2).

The LLM sees short ids (r1, r2...) and returns one id plus an optional excerpt. Code maps the id
back to the real review_id, copies text from the CSV, and keeps the excerpt only if it is a
verbatim substring of 10-25 words; otherwise falls back to the first 25 words of the real review.
"""

from __future__ import annotations

import re

import pandas as pd

from src.errors import LLMError
from src.llm import ask_json

MAX_CANDIDATES = 25
MIN_WORDS = 10
MAX_WORDS = 80
EXCERPT_MAX_WORDS = 25
_PII = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\+?\d[\d\s().-]{8,}\d")


def candidates_for(joined: pd.DataFrame, theme_id: str) -> pd.DataFrame:
    """Deterministic pool: low-star reviews of the theme, 10-80 words, no emails/phones."""
    sub = joined[(joined["theme_id"] == theme_id) & (joined["rating"] <= 2)]
    words = sub["text"].astype(str).str.split().str.len()
    sub = sub[(words >= MIN_WORDS) & (words <= MAX_WORDS)]
    sub = sub[~sub["text"].astype(str).str.contains(_PII)]
    return sub.sort_values("review_id").head(MAX_CANDIDATES).reset_index(drop=True)


def first_words(text: str, n: int = EXCERPT_MAX_WORDS) -> str:
    return " ".join(str(text).split()[:n])


def verified_excerpt(excerpt: str, text: str) -> str:
    """Return the excerpt only if it is a verbatim substring with 1-25 words; else a safe fallback."""
    excerpt = (excerpt or "").strip()
    n = len(excerpt.split())
    if excerpt and 0 < n <= EXCERPT_MAX_WORDS and excerpt in str(text):
        return excerpt
    return first_words(text)


def build_prompt(theme: dict, pool: pd.DataFrame) -> str:
    lines = "\n".join(f"r{i + 1}: {str(t)!r}" for i, t in enumerate(pool["text"]))
    return (
        f'Theme: {theme["name"]} — {theme["description"]}\n'
        "Pick the ONE review below that best illustrates this theme with a clear, specific complaint.\n"
        'Return JSON: {"review_id": "r3", "excerpt": "an exact 10-25 word phrase copied from that review"}.\n'
        "Copy the excerpt exactly; do not paraphrase. Do not count anything.\n"
        f"Reviews:\n{lines}"
    )


def pick_quote(joined: pd.DataFrame, theme: dict) -> dict:
    pool = candidates_for(joined, theme["theme_id"])
    if pool.empty:
        raise LLMError(f"No quote candidates for theme {theme['name']}")
    data = ask_json(
        build_prompt(theme, pool),
        {"review_id": "string", "excerpt": "string"},
        cache_key="quote-v1",
    )
    match = re.fullmatch(r"r(\d+)", data["review_id"].strip())
    idx = int(match.group(1)) - 1 if match else -1
    row = pool.iloc[idx] if 0 <= idx < len(pool) else pool.iloc[0]  # invalid id -> first candidate
    return {
        "theme_id": theme["theme_id"],
        "review_id": str(row["review_id"]),
        "excerpt": verified_excerpt(data["excerpt"], row["text"]),
        "rating": int(row["rating"]),
        "date": str(row["date"]),
    }
