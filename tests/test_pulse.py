"""Tests for architecture pulse path: word limit, no LLM digits, verbatim quotes (INV-1, INV-2, INV-9)."""

from __future__ import annotations

import pytest

from src.errors import LLMError
from src.writer import pulse
from src.writer.wordcount import count_words

QUOTE = "this app keeps getting worse with every update and the answers are wrong most of the time now"
CTX = {
    "window": {"start": "2026-08-24", "end": "2026-11-15", "weeks": 12, "review_count": 2377},
    "themes": [
        {"name": n, "low_star": 10, "total": 20, "low_star_share": 0.5, "prev4": 5, "last4": 4,
         "excerpt": QUOTE, "rating": 1, "quote": QUOTE, "description": "d", "direction": "falling"}
        for n in ("A", "B", "C")
    ],
    "fee_topic": "billing issues", "fee_confused": 21, "fee_money": 172,
}
PROSE = {
    "summaries": ["Users are unhappy."] * 3,
    "observation": "Billing and quality both hurt trust.",
    "actions": ["Fix billing emails."] * 3,
}


def test_count_words_matches_split():
    assert count_words("a  b\nc") == 3


def test_render_has_four_sections_and_code_numbers():
    text = pulse.render(CTX, PROSE)
    for h in ("## Summary of top themes", "## Supporting user quotes", "## Key observation", "## 3 action ideas"):
        assert h in text
    assert "2377 reviews" in text and "21 of 172" in text and "10 of 20" in text
    assert count_words(text) <= 250


def test_llm_digits_are_rejected():
    bad = {**PROSE, "observation": "Complaints rose 40 percent."}
    with pytest.raises(LLMError):
        pulse.validate_prose(bad)


def test_action_n_is_tied_to_quote_n_by_code():
    text = pulse.render(CTX, PROSE)
    assert "1. Fix billing emails. (Quote 1)" in text and "3. Fix billing emails. (Quote 3)" in text


def test_trimmed_quote_is_prefix_of_original():
    short = pulse.trim_quote(QUOTE, 8)
    assert short.endswith("…") and QUOTE.startswith(short[:-1])


def test_direction_is_computed_in_code():
    assert pulse.direction(5, 4) == "falling" and pulse.direction(4, 5) == "rising" and pulse.direction(4, 4) == "flat"
