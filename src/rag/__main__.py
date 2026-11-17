"""Implements architecture §7 entry point for `make rag`: fetch (if needed), chunk, explain."""

from __future__ import annotations

from src.logging_config import setup_logging
from src.rag.chunk import build_chunks
from src.rag.explain import run_explainer
from src.rag.fetch import META_JSON, fetch_all, load_sources


def main() -> None:
    setup_logging()
    wanted = {s["source_id"] for s in load_sources()}
    have = set(__import__("json").loads(META_JSON.read_text())) if META_JSON.exists() else set()
    if wanted - have:
        fetch_all()
    else:
        print("reusing fetched pages in data/sources (delete meta.json to refetch)")
    print(f"{build_chunks()} chunks written")
    result = run_explainer()
    print(f"explainer: {result['bullets']} verified bullets of {result['generated']} generated; status {result['status']}")


if __name__ == "__main__":
    main()
