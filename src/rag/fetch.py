"""Implements architecture §7 ingestion: fetch ONLY the pages listed in config/sources.yaml (INV-3).

Saves data/sources/<source_id>.txt and data/sources/meta.json (fetch dates). If a download fails or
returns too little text, a manual-paste file data/sources/<source_id>.manual.txt is used when present
(its modification date becomes the 'fetched' date).
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

from src import config
from src.errors import ConfigError, DataError

log = logging.getLogger("review_pulse.fetch")

MAX_SOURCES = 12
MIN_CHARS = 400
META_JSON = config.SOURCES_TEXT_DIR / "meta.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; review-pulse-student-project)"}


def load_sources() -> list[dict]:
    """Read sources.yaml; every entry needs source_id, title, url."""
    if not config.SOURCES_YAML.exists():
        raise ConfigError("config/sources.yaml missing. Fill it in yourself.")
    data = yaml.safe_load(config.SOURCES_YAML.read_text(encoding="utf-8")) or {}
    sources = data.get("sources") or []
    if not 1 <= len(sources) <= MAX_SOURCES:
        raise ConfigError(f"config/sources.yaml should list 1-{MAX_SOURCES} official sources.")
    for s in sources:
        if not all(isinstance(s.get(k), str) and s[k] for k in ("source_id", "title", "url")):
            raise ConfigError(f"Each source needs source_id, title, url: {s}")
    return sources


def _extract(html: str) -> str:
    import trafilatura

    text = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
    if len(text) >= MIN_CHARS:
        return text
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())


def fetch_one(source: dict) -> tuple[str, str]:
    """Return (text, fetched_date). Falls back to the manual-paste file on failure."""
    sid = source["source_id"]
    manual = config.SOURCES_TEXT_DIR / f"{sid}.manual.txt"
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=30)
        resp.raise_for_status()
        text = _extract(resp.text)
        if len(text) >= MIN_CHARS:
            return text, dt.date.today().isoformat()
        log.warning("%s: only %d chars extracted", sid, len(text))
    except requests.RequestException as exc:
        log.warning("%s: download failed (%s)", sid, type(exc).__name__)
    if manual.exists() and manual.stat().st_size > 0:
        date = dt.date.fromtimestamp(manual.stat().st_mtime).isoformat()
        return manual.read_text(encoding="utf-8"), date
    raise DataError(
        f"Could not fetch {sid}. Paste the page text into {manual.relative_to(config.ROOT)} and re-run."
    )


def fetch_all() -> dict[str, str]:
    """Fetch every source; return {source_id: fetched_date}. Failures are reported, not hidden."""
    config.SOURCES_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    meta: dict[str, str] = {}
    failures: list[str] = []
    for source in load_sources():
        try:
            text, date = fetch_one(source)
        except DataError as exc:
            failures.append(str(exc))
            continue
        Path(config.SOURCES_TEXT_DIR / f"{source['source_id']}.txt").write_text(text, encoding="utf-8")
        meta[source["source_id"]] = date
        print(f"{source['source_id']}: {len(text)} chars, fetched {date}")
    META_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    for message in failures:
        print("FAILED:", message)
    if not meta:
        raise DataError("No sources could be fetched.")
    return meta
