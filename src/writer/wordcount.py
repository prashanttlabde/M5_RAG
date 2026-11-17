"""Implements architecture pulse path: word counting in code, never by the LLM (INV-1, INV-9)."""

from __future__ import annotations


def count_words(text: str) -> int:
    """Whitespace-separated token count (same rule as `len(text.split())`)."""
    return len(text.split())
