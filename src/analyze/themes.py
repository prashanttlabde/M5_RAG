"""Implements architecture §6 theme discovery: LLM proposes at most 5 themes (INV-1: no counting)."""

from __future__ import annotations

import json
import logging

import pandas as pd

from src import config
from src.errors import DataError, LLMError
from src.llm import ask_json

log = logging.getLogger("review_pulse.themes")

MAX_THEMES = 5
SAMPLE_SIZE = 150
MAX_ATTEMPTS = 3
TRIM_CHARS = 300


def sample_reviews(df: pd.DataFrame, n: int = SAMPLE_SIZE, seed: int = 42) -> pd.DataFrame:
    """Mixed sample: roughly a third each of angry (1-2), neutral (3), happy (4-5)."""
    groups = [df[df["rating"] <= 2], df[df["rating"] == 3], df[df["rating"] >= 4]]
    per = n // 3
    parts = [g.sample(n=min(per, len(g)), random_state=seed) for g in groups if len(g)]
    return pd.concat(parts).sample(frac=1, random_state=seed)


def build_prompt(sample: pd.DataFrame, extra: str = "") -> str:
    lines = [f"- ({int(r.rating)}*) {str(r.text)[:TRIM_CHARS]}" for r in sample.itertuples()]
    return (
        "You are analysing Google Play reviews of the ChatGPT app (India).\n"
        f"Propose AT MOST {MAX_THEMES} distinct themes that cover what users talk about.\n"
        "Do not count anything. Return JSON: "
        '{"themes": [{"theme_id": "t1", "name": "...", "description": "one sentence"}]}\n'
        "Use theme_id values t1, t2, ... Names must be short and unique.\n"
        f"{extra}\nReviews:\n" + "\n".join(lines)
    )


def _valid_themes(data: dict) -> list[dict]:
    themes = data["themes"]
    if not themes or len(themes) > MAX_THEMES:
        raise LLMError(f"Got {len(themes)} themes; need 1-{MAX_THEMES}")
    for t in themes:
        if not isinstance(t, dict) or not all(isinstance(t.get(k), str) and t[k] for k in ("theme_id", "name", "description")):
            raise LLMError("Each theme needs theme_id, name, description")
    ids = [t["theme_id"] for t in themes]
    if len(set(ids)) != len(ids):
        raise LLMError("Duplicate theme_id")
    return [{k: t[k] for k in ("theme_id", "name", "description")} for t in themes]


def discover_themes() -> list[dict]:
    """Discover themes from balanced reviews and write data/themes.json."""
    if not config.REVIEWS_BALANCED_CSV.exists():
        raise DataError("data/reviews_balanced.csv missing. Run `make collect` first.")
    df = pd.read_csv(config.REVIEWS_BALANCED_CSV)
    sample = sample_reviews(df)
    extra = ""
    for attempt in range(MAX_ATTEMPTS):
        prompt = build_prompt(sample, extra)
        data = ask_json(prompt, {"themes": "array"}, cache_key=f"themes-v1-{attempt}")
        try:
            themes = _valid_themes(data)
        except LLMError as exc:
            log.warning("Rejected themes (attempt %d): %s", attempt + 1, exc)
            extra = f"IMPORTANT: your previous answer was rejected ({exc}). Return at most {MAX_THEMES} themes."
            continue
        config.THEMES_JSON.parent.mkdir(parents=True, exist_ok=True)
        config.THEMES_JSON.write_text(json.dumps(themes, indent=2, ensure_ascii=False), encoding="utf-8")
        return themes
    raise LLMError(f"Could not get a valid theme list after {MAX_ATTEMPTS} attempts")
