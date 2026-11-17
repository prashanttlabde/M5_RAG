"""Implements architecture §5 LLM layer: cached, validated, JSON-only Groq calls (INV-8)."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src import config
from src.errors import ConfigError, LLMError

log = logging.getLogger("review_pulse.llm")

MAX_JSON_RETRIES = 2
MAX_RATE_LIMIT_RETRIES = 5

_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


def cache_path(model: str, prompt: str, cache_dir: Path | None = None) -> Path:
    """Cache file path = sha256(model + prompt)."""
    digest = hashlib.sha256((model + "\n" + prompt).encode("utf-8")).hexdigest()
    return (cache_dir or config.CACHE_DIR) / f"{digest}.json"


def validate_keys(data: Any, schema: dict[str, str]) -> None:
    """Hand-rolled validation: data must be a dict with each key present and typed.

    `schema` maps key -> one of string|integer|number|boolean|array|object.
    """
    if not isinstance(data, dict):
        raise LLMError(f"Expected a JSON object, got {type(data).__name__}")
    for key, type_name in schema.items():
        if key not in data:
            raise LLMError(f"Missing key '{key}' in LLM JSON")
        expected = _TYPE_MAP[type_name]
        value = data[key]
        if isinstance(value, bool) and type_name in {"integer", "number"}:
            raise LLMError(f"Key '{key}' should be {type_name}, got boolean")
        if not isinstance(value, expected):
            raise LLMError(f"Key '{key}' should be {type_name}, got {type(value).__name__}")


def _parse_json(raw: str) -> Any:
    text = raw.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    return json.loads(text)


def _limit_detail(exc: Exception) -> str:
    """The usage/limit/wait figures from Groq's message (contains no secrets)."""
    m = re.search(r"Limit \d+, Used \d+, Requested \d+\. Please try again in [\w.]+", str(exc))
    return m.group(0) if m else ""


def _groq_complete(model: str, prompt: str) -> str:
    """One raw Groq call in JSON mode. Retries with backoff on 429."""
    api_key = config.get_groq_api_key()
    if not api_key:
        raise ConfigError("GROQ_API_KEY is not set. Add it to .env yourself.")
    from groq import (
        APIConnectionError,
        APITimeoutError,
        BadRequestError,
        Groq,
        RateLimitError,
    )

    client = Groq(api_key=api_key, timeout=60.0)
    # gpt-oss models are reasoning models; low effort keeps output budget for the JSON answer.
    extra = {"reasoning_effort": "low"} if "gpt-oss" in model else {}
    delay = 2.0
    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Reply with a single valid JSON object only."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,
                **extra,
            )
            return resp.choices[0].message.content or ""
        except BadRequestError as exc:
            if "json_validate_failed" in str(exc):
                log.warning("Groq could not produce valid JSON; treating as a bad answer")
                return ""
            raise LLMError(f"Groq rejected the request: {exc}") from exc
        except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
            if isinstance(exc, RateLimitError) and "per day" in str(exc):
                raise LLMError(
                    "Groq daily token limit reached for this model. Wait, or change LLM_MODEL in .env. "
                    + _limit_detail(exc)
                ) from exc
            if attempt == MAX_RATE_LIMIT_RETRIES:
                raise LLMError("Groq rate limit/timeout persisted after retries.") from exc
            log.warning("Groq 429/timeout (%s); sleeping %.0fs", type(exc).__name__, delay)
            time.sleep(delay)
            delay *= 2
    raise LLMError("unreachable")  # pragma: no cover


def ask_json(
    prompt: str,
    schema: dict[str, str],
    cache_key: str | None = None,
    *,
    complete: Callable[[str, str], str] | None = None,
    cache_dir: Path | None = None,
) -> dict:
    """Ask the LLM for JSON; validate keys; retry up to 2x on bad JSON; cache by hash.

    `cache_key` is an optional human label mixed into the hash (e.g. "themes-v1").
    `complete` lets tests inject a fake model call.
    """
    model = config.get_llm_model()
    if not model:
        raise ConfigError("LLM_MODEL is not set. Add it to .env yourself.")
    hashed_prompt = f"{cache_key}\n{prompt}" if cache_key else prompt
    path = cache_path(model, hashed_prompt, cache_dir)

    if path.exists():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            validate_keys(cached, schema)
            return cached
        except (json.JSONDecodeError, LLMError):
            log.warning("Ignoring invalid cache file %s", path.name)

    call = complete or _groq_complete
    last_error: Exception | None = None
    for attempt in range(MAX_JSON_RETRIES + 1):
        raw = call(model, prompt)
        try:
            data = _parse_json(raw)
            validate_keys(data, schema)
        except (json.JSONDecodeError, LLMError) as exc:
            last_error = exc
            log.warning("Invalid LLM JSON (attempt %d): %s", attempt + 1, exc)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data
    raise LLMError(f"LLM returned invalid JSON after retries: {last_error}")
