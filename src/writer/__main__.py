"""Implements architecture pulse path entry point for `make write` (P5)."""

from __future__ import annotations

from src.logging_config import setup_logging
from src.writer.pulse import generate_pulse
from src.writer.wordcount import count_words


def main() -> None:
    setup_logging()
    text = generate_pulse()
    print(f"wrote outputs/weekly_pulse.md ({count_words(text)} words)")


if __name__ == "__main__":
    main()
