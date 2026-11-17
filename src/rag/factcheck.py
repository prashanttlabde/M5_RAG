"""Implements architecture §7 fact-check (PRD FR17; INV-3): a second LLM call per bullet.

The checker sees ONE bullet and its ONE cited chunk. Unsupported or rule-failing bullets get one
rewrite; if they still fail they are dropped.
"""

from __future__ import annotations

import logging

from rank_bm25 import BM25Okapi

from src.errors import LLMError
from src.llm import ask_json
from src.rag import validate
from src.rag.index import tokenize

log = logging.getLogger("review_pulse.factcheck")


def best_chunk(bullet: str, chunks: list[dict]) -> dict | None:
    """The chunk of the cited source that best matches the bullet, picked by code.

    Scores come from BM25 over the whole corpus (small per-source pools give degenerate scores);
    the best-scoring chunk of the cited source wins, even at score 0. None if the source is unknown.
    """
    text, source_id = validate.split_citation(bullet)
    bm25 = BM25Okapi([tokenize(c["text"]) for c in chunks])
    scores = bm25.get_scores(tokenize(text))
    candidates = [(scores[i], -i, c) for i, c in enumerate(chunks) if c["source_id"] == source_id]
    return max(candidates, key=lambda t: (t[0], t[1]))[2] if candidates else None


def fact_check(bullet_text: str, chunk_text: str) -> tuple[bool, str]:
    prompt = (
        "You are a strict fact-checker. Decide whether the CLAIM is fully supported by the SOURCE TEXT alone.\n"
        "Anything not stated in the source text counts as unsupported.\n"
        'Return JSON: {"supported": true or false, "reason": "short reason"}\n'
        f"CLAIM: {bullet_text}\nSOURCE TEXT: {chunk_text}"
    )
    data = ask_json(prompt, {"supported": "boolean", "reason": "string"}, cache_key="factcheck-v1")
    return bool(data["supported"]), str(data["reason"])


def rewrite(bullet_text: str, chunk: dict, reason: str) -> str:
    prompt = (
        "Rewrite the claim so it is fully supported by the source text, using only facts stated there. "
        "Neutral tone, one sentence, no advice, no opinions, no numbers unless they appear in the text.\n"
        f"Problem with the previous claim: {reason}\n"
        'Return JSON: {"bullet": "the rewritten claim"}\n'
        f"CLAIM: {bullet_text}\nSOURCE TEXT: {chunk['text']}"
    )
    data = ask_json(prompt, {"bullet": "string"}, cache_key="rewrite-v1")
    return validate.normalize(f"{data['bullet'].strip()} [{chunk['source_id']}]")


def check_and_repair(bullet: str, known_sources: set[str], chunks: list[dict], fallback_chunk: dict) -> dict:
    """Validate + fact-check one bullet; one rewrite allowed. Returns a record with `final` or None."""
    record = {"original": bullet, "final": None, "chunk_id": None, "rewritten": False, "reason": ""}
    current = validate.normalize(bullet)
    for attempt in range(2):
        chunk = best_chunk(current, chunks)
        problems = validate.validate_bullet(current, known_sources, chunk["text"] if chunk else None)
        reason = "; ".join(problems)
        if not problems:
            text, _ = validate.split_citation(current)
            supported, why = fact_check(text, chunk["text"])
            if supported:
                record.update(final=current, chunk_id=chunk["chunk_id"], reason="")
                return record
            reason = f"fact-check: {why}"
        record["reason"] = reason
        if attempt == 1:
            break
        try:
            current = rewrite(validate.split_citation(current)[0], chunk or fallback_chunk, reason)
            record["rewritten"] = True
        except LLMError:
            break
    return record
