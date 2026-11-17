"""Tests for architecture §7 RAG: chunking, retrieval, validation, chunk lookup (INV-3, INV-9)."""

from __future__ import annotations

from src.rag import chunk, explain, factcheck, index, validate

CHUNKS = [
    {"chunk_id": "a-1", "source_id": "a", "source_url": "u", "section": "", "fetched_at": "d",
     "text": "Subscriptions renew every month. The price is 20 dollars per month in the US."},
    {"chunk_id": "b-1", "source_id": "b", "source_url": "u", "section": "", "fetched_at": "d",
     "text": "Refund requests must be sent within 14 days of the charge."},
    {"chunk_id": "b-2", "source_id": "b", "source_url": "u", "section": "", "fetched_at": "d",
     "text": "Taxes may apply depending on your country."},
]


def test_chunks_are_sentence_aware_with_overlap():
    text = "\n".join(f"Heading {i}\n" + " ".join(f"Sentence {i} number {j} has several words in it." for j in range(30)) for i in range(3))
    out = chunk.chunk_text(text)
    assert len(out) > 1
    for body, _ in out:
        assert len(body.split()) <= chunk.MAX_WORDS
    first_end = out[0][0].split(". ")[-1].rstrip(".")
    assert first_end in out[1][0]  # overlap: last sentence of chunk 1 reappears in chunk 2


def test_search_returns_relevant_chunk_first():
    hits = index.search("refund within days", k=2, chunks=CHUNKS)
    assert hits[0]["chunk_id"] == "b-1"


def test_validate_accepts_supported_bullet():
    bullet = "Refund requests must be made within 14 days. [b]"
    assert validate.validate_bullet(bullet.replace("must be made", "are accepted"), {"a", "b"}, CHUNKS[1]["text"]) == []


def test_validate_rejects_number_not_in_chunk():
    problems = validate.validate_bullet("Refunds take 30 days. [b]", {"a", "b"}, CHUNKS[1]["text"])
    assert any("numbers not in cited chunk" in p for p in problems)


def test_source_id_digits_are_not_treated_as_numbers():
    assert validate.validate_bullet("Billing is managed in settings. [openai_9039756]", {"openai_9039756"}, "Billing is managed in settings.") == []


def test_validate_rejects_unknown_source_missing_citation_and_opinions():
    assert validate.validate_bullet("Plans renew monthly. [zzz]", {"a"}, "x")
    assert "must end with [source_id]" in validate.validate_bullet("Plans renew monthly.", {"a"}, "x")
    assert any("banned" in p for p in validate.validate_bullet("This is a terrible fee. [a]", {"a"}, "terrible fee"))


def test_bullet_cap_is_six():
    assert validate.validate_count(["x"] * 6) == [] and validate.validate_count(["x"] * 7)


def test_best_chunk_picks_best_of_cited_source_only():
    c = factcheck.best_chunk("Refund requests are accepted within 14 days. [b]", CHUNKS)
    assert c["chunk_id"] == "b-1"
    assert factcheck.best_chunk("Anything. [unknown]", CHUNKS) is None


def test_pick_links_returns_exactly_two_known_sources():
    sources = [{"source_id": s, "title": s, "url": f"https://x/{s}"} for s in ("a", "b", "c")]
    links = explain.pick_links(["b", "b", "a"], [{"source_id": "c"}], sources)
    assert [s["source_id"] for s in links] == ["b", "a"]
    assert len(explain.pick_links([], [], sources)) == 2


def test_citation_before_final_period_is_accepted_and_normalised():
    bullet = "Refund requests are accepted within 14 days [b]."
    assert validate.split_citation(bullet) == ("Refund requests are accepted within 14 days", "b")
    assert validate.normalize(bullet) == "Refund requests are accepted within 14 days. [b]"
    assert validate.validate_bullet(validate.normalize(bullet), {"a", "b"}, CHUNKS[1]["text"]) == []
