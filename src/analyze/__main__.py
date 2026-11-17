"""Implements architecture §6 entry point for `make analyze` (P2: themes + assignments only)."""

from __future__ import annotations

import json

from src import config
from src.analyze.classify import classify_all
from src.analyze.themes import discover_themes
from src.logging_config import setup_logging


def main() -> None:
    setup_logging()
    if config.THEMES_JSON.exists() and config.THEMES_JSON.stat().st_size > 0:
        themes = json.loads(config.THEMES_JSON.read_text(encoding="utf-8"))
        print("reusing existing data/themes.json (delete it to rediscover)")
    else:
        themes = discover_themes()
    print(f"{len(themes)} themes: {[t['name'] for t in themes]}")
    out = classify_all(themes)
    print(f"assigned {len(out)} reviews")


if __name__ == "__main__":
    main()
