"""Implements architecture §6 assignment: LLM assigns each review to one theme (INV-1: no counting)."""

from __future__ import annotations

import json
import logging

import pandas as pd

from src import config
from src.errors import DataError, LLMError
from src.llm import ask_json

log = logging.getLogger("review_pulse.classify")

BATCH_SIZE = 25
TRIM_CHARS = 300
MAX_ATTEMPTS = 4


def build_prompt(batch: pd.DataFrame, themes: list[dict], indices: list[int] | None = None) -> str:
    """Prompt for the reviews at `indices` (default: all). Indices stay the batch-local ids."""
    theme_lines = "\n".join(f'- {t["theme_id"]}: {t["name"]} — {t["description"]}' for t in themes)
    wanted = range(len(batch)) if indices is None else indices
    review_lines = "\n".join(f"{i}: {str(batch.loc[i, 'text'])[:TRIM_CHARS]!r}" for i in wanted)
    return (
        "Assign each review to exactly ONE theme. Do not count anything.\n"
        f"Themes:\n{theme_lines}\n\n"
        'Return JSON: {"assignments": [{"i": 0, "theme_id": "t1"}]} with one entry per review index listed.\n'
        f"Reviews:\n{review_lines}"
    )


def classify_batch(batch: pd.DataFrame, themes: list[dict]) -> dict[int, str]:
    """Classify a batch; if the LLM skips reviews, re-ask only for the missing ones."""
    valid_ids = {t["theme_id"] for t in themes}
    result: dict[int, str] = {}
    for attempt in range(MAX_ATTEMPTS):
        missing = [i for i in range(len(batch)) if i not in result]
        if not missing:
            return result
        data = ask_json(
            build_prompt(batch, themes, missing),
            {"assignments": "array"},
            cache_key=f"classify-v2-{attempt}",
        )
        for item in data["assignments"]:
            if (
                isinstance(item, dict)
                and isinstance(item.get("i"), int)
                and item["i"] in missing
                and item.get("theme_id") in valid_ids
            ):
                result[item["i"]] = item["theme_id"]
        log.info("Batch attempt %d: %d/%d assigned", attempt + 1, len(result), len(batch))
    if len(result) < len(batch):
        raise LLMError(f"LLM left {len(batch) - len(result)} reviews unassigned after {MAX_ATTEMPTS} attempts")
    return result


def classify_all(themes: list[dict] | None = None) -> pd.DataFrame:
    """Assign every balanced review to one theme and write data/assignments.csv."""
    if themes is None:
        if not config.THEMES_JSON.exists():
            raise DataError("data/themes.json missing. Run theme discovery first.")
        themes = json.loads(config.THEMES_JSON.read_text(encoding="utf-8"))
    df = pd.read_csv(config.REVIEWS_BALANCED_CSV)
    rows: list[dict[str, str]] = []
    for start in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[start : start + BATCH_SIZE].reset_index(drop=True)
        mapping = classify_batch(batch, themes)
        rows.extend({"review_id": batch.loc[i, "review_id"], "theme_id": mapping[i]} for i in range(len(batch)))
        log.info("Classified %d/%d", min(start + BATCH_SIZE, len(df)), len(df))
    out = pd.DataFrame(rows, columns=["review_id", "theme_id"])
    out.to_csv(config.ASSIGNMENTS_CSV, index=False)
    return out
