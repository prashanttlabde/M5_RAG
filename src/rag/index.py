"""Implements architecture §7 retrieval: BM25 over data/chunks.jsonl via rank_bm25.

One interface, `search(query, k)`, so another backend could replace BM25 without touching callers.
"""

from __future__ import annotations

import json
import re

from rank_bm25 import BM25Okapi

from src import config
from src.errors import DataError

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def load_chunks() -> list[dict]:
    if not config.CHUNKS_JSONL.exists() or config.CHUNKS_JSONL.stat().st_size == 0:
        raise DataError("data/chunks.jsonl missing. Run `make rag` first.")
    return [json.loads(line) for line in config.CHUNKS_JSONL.read_text(encoding="utf-8").splitlines() if line.strip()]


def search(query: str, k: int = 5, chunks: list[dict] | None = None) -> list[dict]:
    """Top-k chunks for the query (score > 0 only), best first."""
    chunks = chunks if chunks is not None else load_chunks()
    bm25 = BM25Okapi([tokenize(c["text"]) for c in chunks])
    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(zip(scores, range(len(chunks))), key=lambda p: (-p[0], p[1]))
    return [{**chunks[i], "score": float(sc)} for sc, i in ranked[:k] if sc > 0]
