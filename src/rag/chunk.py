"""Implements architecture §7 chunking: sentence-aware chunks with ~15% overlap.

Chunk size was tuned with the user from the plan's ~300-500 tokens to ~55 chunks for this corpus
(about 130 words each). Tokens are estimated as words x 1.33. Output: data/chunks.jsonl with
{chunk_id, source_id, source_url, section, fetched_at, text}.
"""

from __future__ import annotations

import json
import re

from src import config
from src.errors import DataError
from src.rag.fetch import META_JSON, load_sources

TARGET_WORDS = 130  # ~175 tokens; tuned with the user to ~55 chunks for this ~6,000-word corpus
MAX_WORDS = 190  # ~250 tokens
OVERLAP_SHARE = 0.15
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])")


def _is_heading(line: str) -> bool:
    return len(line.split()) <= 10 and not line.endswith((".", ":", "!", "?")) and not line.startswith(("-", "*"))


def sentences_with_sections(text: str) -> list[tuple[str, str]]:
    """Split text into (sentence, section_heading) pairs, keeping headings as sentences."""
    out: list[tuple[str, str]] = []
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if _is_heading(line):
            section = line
            out.append((line, section))
            continue
        for sent in _SENTENCE_SPLIT.split(line):
            if sent.strip():
                out.append((sent.strip(), section))
    return out


def chunk_text(text: str) -> list[tuple[str, str]]:
    """Return [(chunk_text, section)] with sentence boundaries and ~15% sentence overlap."""
    sents = sentences_with_sections(text)
    chunks: list[tuple[str, str]] = []
    start = 0
    while start < len(sents):
        end, words = start, 0
        while end < len(sents):
            n = len(sents[end][0].split())
            if words >= TARGET_WORDS or (words and words + n > MAX_WORDS):
                break
            words += n
            end += 1
        chunks.append((" ".join(s for s, _ in sents[start:end]), sents[start][1]))
        if end >= len(sents):
            break
        # step back so ~15% of this chunk's words are repeated at the start of the next chunk
        back, carried = end, 0
        while back - 1 > start and carried < OVERLAP_SHARE * words:
            back -= 1
            carried += len(sents[back][0].split())
        start = back if back > start else end
    return chunks


def build_chunks() -> int:
    """Chunk every fetched source into data/chunks.jsonl; return chunk count."""
    if not META_JSON.exists():
        raise DataError("No fetched sources. Run fetch first.")
    meta = json.loads(META_JSON.read_text(encoding="utf-8"))
    rows = []
    for source in load_sources():
        sid = source["source_id"]
        path = config.SOURCES_TEXT_DIR / f"{sid}.txt"
        if sid not in meta or not path.exists():
            continue
        for n, (text, section) in enumerate(chunk_text(path.read_text(encoding="utf-8")), start=1):
            rows.append(
                {
                    "chunk_id": f"{sid}-{n}",
                    "source_id": sid,
                    "source_url": source["url"],
                    "section": section,
                    "fetched_at": meta[sid],
                    "text": text,
                }
            )
    config.CHUNKS_JSONL.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return len(rows)
