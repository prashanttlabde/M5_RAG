"""Implements architecture §7 generation (PRD FR13-FR18; INV-3, INV-9).

Query = identified fee topic + frequent terms from confused reviews of that topic (computed, not LLM).
The LLM writes at most 6 neutral bullets from the retrieved chunks only; code validates and the
fact-checker verifies each. Fewer than 4 surviving bullets => status needs_human_review.
"""

from __future__ import annotations

import json
import re
from collections import Counter

import pandas as pd

from src import config
from src.errors import DataError
from src.llm import ask_json
from src.rag import validate
from src.rag.factcheck import check_and_repair
from src.rag.fetch import META_JSON, load_sources
from src.rag.index import load_chunks, search

TOP_K = 5
MIN_BULLETS = 4
QUERY_TERMS = 8
_STOP = {
    "that", "this", "with", "have", "from", "they", "them", "what", "when", "your", "were", "been", "will", "would", "just", "like", "very", "more", "than", "then", "also", "only", "into", "about", "there", "their", "which", "because", "after", "before", "even", "still", "being", "does", "dont", "cant", "chatgpt", "chat", "openai", "app", "please",
}


def build_query(topic: str) -> str:
    """Topic words + most common terms in confused reviews of that topic (pure code)."""
    labels = pd.read_csv(config.FEE_LABELS_CSV)
    reviews = pd.read_csv(config.REVIEWS_BALANCED_CSV).set_index("review_id")
    ids = labels[(labels["stance"] == "confused") & (labels["fee_topic"] == topic)]["review_id"]
    counts: Counter[str] = Counter()
    for rid in ids:
        counts.update(w for w in re.findall(r"[a-z]{4,}", str(reviews.loc[rid, "text"]).lower()) if w not in _STOP)
    return " ".join([topic.replace("_", " "), *(w for w, _ in counts.most_common(QUERY_TERMS))])


def build_prompt(topic: str, retrieved: list[dict]) -> str:
    blocks = "\n\n".join(f"[{c['source_id']}] ({c['section']})\n{c['text']}" for c in retrieved)
    return (
        "Write a neutral customer explainer about this fee topic using ONLY the official text below.\n"
        f"Fee topic users are confused about: {topic.replace('_', ' ')}\n"
        f"Rules: at most {validate.MAX_BULLETS} bullets; each bullet is ONE factual sentence that ends with "
        "the source id in square brackets, e.g. [openai_9039756]; use only facts stated in the text; "
        "include a number only if it appears in the text; no advice, no opinions, no marketing words.\n"
        'Return JSON: {"bullets": ["sentence. [source_id]"]}\n\n'
        f"Official text:\n{blocks}"
    )


def pick_links(cited: list[str], retrieved: list[dict], sources: list[dict]) -> list[dict]:
    """Exactly 2 official sources: most cited first, then retrieval order, then config order."""
    order = [s for s, _ in Counter(cited).most_common()]
    order += [c["source_id"] for c in retrieved] + [s["source_id"] for s in sources]
    by_id = {s["source_id"]: s for s in sources}
    picked: list[str] = []
    for sid in order:
        if sid in by_id and sid not in picked:
            picked.append(sid)
    return [by_id[s] for s in picked[:2]]


def run_explainer() -> dict:
    """Generate, validate and fact-check the explainer; write outputs/fee_explainer.{md,json}."""
    insights = json.loads(config.INSIGHTS_JSON.read_text(encoding="utf-8"))
    topic = insights["fee"].get("topic")
    if not topic:
        raise DataError("No fee issue in insights.json; run `make analyze` first.")
    sources = load_sources()
    known = {s["source_id"] for s in sources}
    chunks = load_chunks()
    retrieved = search(build_query(topic), k=TOP_K, chunks=chunks)
    if not retrieved:
        raise DataError("Retrieval found no relevant official text for this fee topic.")

    data = ask_json(build_prompt(topic, retrieved), {"bullets": "array"}, cache_key="explain-v1")
    raw = [b.strip() for b in data["bullets"] if isinstance(b, str) and b.strip()]
    raw = raw[: validate.MAX_BULLETS]

    records, finals, seen = [], [], set()
    for bullet in raw:
        rec = check_and_repair(bullet, known, chunks, retrieved[0])
        records.append(rec)
        if rec["final"] and rec["final"] not in seen:
            seen.add(rec["final"])
            finals.append(rec)
    status = "ok" if len(finals) >= MIN_BULLETS else "needs_human_review"

    cited = [validate.split_citation(r["final"])[1] for r in finals]
    links = pick_links(cited, retrieved, sources)
    meta = json.loads(META_JSON.read_text(encoding="utf-8"))
    last_checked = min(meta[s["source_id"]] for s in links)

    lines = [f"# Fee explainer: {topic.replace('_', ' ')}", ""]
    lines += [f"- {r['final']}" for r in finals]
    lines += ["", "Official sources: " + " | ".join(f"[{s['title']}]({s['url']})" for s in links)]
    lines += [f"Last checked: {last_checked}"]
    if status != "ok":
        lines += ["", f"STATUS: needs_human_review ({len(finals)} verified bullets, need {MIN_BULLETS}). Do not publish."]
    config.FEE_EXPLAINER_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    config.FEE_EXPLAINER_JSON.write_text(
        json.dumps(
            {
                "status": status,
                "topic": topic,
                "query": build_query(topic),
                "bullets": [{"text": r["final"], "chunk_id": r["chunk_id"]} for r in finals],
                "links": [{"title": s["title"], "url": s["url"]} for s in links],
                "last_checked": last_checked,
                "rejected": [r for r in records if not r["final"]],
                "rewritten_count": sum(r["rewritten"] for r in records),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return {"status": status, "bullets": len(finals), "generated": len(raw)}
