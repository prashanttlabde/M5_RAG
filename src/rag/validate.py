"""Implements architecture §7 validation (PRD FR16; INV-3, INV-9): rule-based, no AI.

A bullet must: end with [source_id] of a known source, cite a real chunk, contain only numbers that
appear in that chunk, and avoid opinion/advice words. The bullet total is capped at 6.
"""

from __future__ import annotations

import re

MAX_BULLETS = 6
BANNED_WORDS = (
    "best", "worst", "terrible", "awful", "great", "amazing", "unfair", "scam", "rip-off", "ripoff",
    "overpriced", "expensive", "cheap", "outrageous", "unfortunately", "fortunately", "obviously",
    "clearly", "recommend", "should", "must",
)
_CITE = re.compile(r"\s*\[([A-Za-z0-9_\-]+)\]\s*[.!?]?\s*$")
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def split_citation(bullet: str) -> tuple[str, str | None]:
    """Return (text_without_citation, source_id or None)."""
    m = _CITE.search(bullet)
    if not m:
        return bullet.strip(), None
    return bullet[: m.start()].strip(), m.group(1)


def normalize(bullet: str) -> str:
    """Canonical form `Sentence. [source_id]` (accepts `[id].` too); unchanged if no citation."""
    text, source_id = split_citation(bullet)
    if source_id is None or not text:
        return bullet.strip()
    if not text.endswith((".", "!", "?")):
        text += "."
    return f"{text} [{source_id}]"


def numbers_in(text: str) -> set[str]:
    return {n.rstrip(".,").replace(",", "") for n in _NUMBER.findall(text)}


def validate_bullet(bullet: str, known_sources: set[str], chunk_text: str | None) -> list[str]:
    """Return a list of problems (empty = valid). `chunk_text` is the cited chunk, if found."""
    problems: list[str] = []
    text, source_id = split_citation(bullet)
    if not text:
        problems.append("empty bullet")
    if source_id is None:
        problems.append("must end with [source_id]")
    elif source_id not in known_sources:
        problems.append(f"unknown source_id {source_id}")
    elif chunk_text is None:
        problems.append("no chunk found for cited source")
    else:
        missing = numbers_in(text) - numbers_in(chunk_text)
        if missing:
            problems.append(f"numbers not in cited chunk: {sorted(missing)}")
    words = set(re.findall(r"[a-z][a-z\-]*", text.lower()))
    banned = sorted(w for w in BANNED_WORDS if w in words)
    if banned:
        problems.append(f"banned opinion words: {banned}")
    return problems


def validate_count(bullets: list[str]) -> list[str]:
    return [f"too many bullets ({len(bullets)} > {MAX_BULLETS})"] if len(bullets) > MAX_BULLETS else []
