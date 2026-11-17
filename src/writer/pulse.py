"""Implements architecture pulse path (PRD FR9-FR12): code owns the skeleton and every number.

The LLM writes only prose (theme sentences, key observation, 3 actions) and may not output digits.
Total length is capped at 250 words (INV-9); if over, the LLM is asked to shorten (max 3 rewrites),
then displayed quotes are trimmed in code.
"""

from __future__ import annotations

import json
import logging
import re

import pandas as pd

from src import config
from src.errors import DataError, LLMError, ValidationError
from src.llm import ask_json
from src.writer.wordcount import count_words

log = logging.getLogger("review_pulse.pulse")

MAX_WORDS = 250
MAX_REWRITES = 3
MIN_QUOTE_WORDS = 8
_DIGIT = re.compile(r"\d")


def direction(prev4: int, last4: int) -> str:
    """Trend direction in words, decided by code."""
    if last4 > prev4:
        return "rising"
    if last4 < prev4:
        return "falling"
    return "flat"


def trim_quote(excerpt: str, max_words: int) -> str:
    """Shorten a verbatim excerpt to its first `max_words` words (still a prefix of the real text)."""
    words = excerpt.split()
    return excerpt if len(words) <= max_words else " ".join(words[:max_words]) + "…"


def fee_confused_count(topic: str) -> int:
    """Confused reviews for the identified fee topic, counted in code from fee_labels.csv."""
    labels = pd.read_csv(config.FEE_LABELS_CSV)
    return int(((labels["stance"] == "confused") & (labels["fee_topic"] == topic)).sum())


def build_prompt(ctx: dict, prose_budget: int, attempt: int) -> str:
    themes = "\n".join(
        f'{i + 1}. {t["name"]} ({t["description"]}); trend is {t["direction"]}; example review: {t["quote"]!r}'
        for i, t in enumerate(ctx["themes"])
    )
    shorter = "Your previous draft was too long. Be much shorter.\n" if attempt else ""
    return (
        "You write a one-minute weekly product pulse for a PM about the ChatGPT Play Store app.\n"
        f"{shorter}"
        f"STRICT: all text you write must total at most {prose_budget} words and contain NO digits "
        "and no numbers (spell nothing out as a figure; counts are added by code).\n"
        f"Top themes (already ranked):\n{themes}\n"
        f"Most common fee confusion: {ctx['fee_topic']}\n"
        "Return JSON: {\"summaries\": [3 strings, one short sentence per theme in order], "
        '"observation": "one sentence connecting the themes and the fee confusion", '
        '"actions": [3 short imperative ideas as strings]} '
        "Action N must address theme N and the problem shown in its example review (action 3 may also "
        "touch the fee confusion if it fits theme 3). Do not count, rank or quote numbers."
    )


def validate_prose(data: dict) -> dict:
    """Hand validation: 3 summaries, observation, 3 actions (action N tied to quote N by code), no digits anywhere."""
    summaries, actions = data["summaries"], data["actions"]
    if len(summaries) != 3 or not all(isinstance(s, str) and s.strip() for s in summaries):
        raise LLMError("Need exactly 3 summary sentences")
    if not isinstance(data["observation"], str) or not data["observation"].strip():
        raise LLMError("Need a key observation")
    if len(actions) != 3:
        raise LLMError("Need exactly 3 actions")
    clean_actions = []
    for a in actions:
        if not (isinstance(a, str) and a.strip()):
            raise LLMError("Each action must be a non-empty string")
        clean_actions.append(a.strip())
    joined = " ".join([*summaries, data["observation"], *clean_actions])
    if _DIGIT.search(joined):
        raise LLMError("LLM prose contained digits; numbers must come from code (INV-1)")
    return {
        "summaries": [s.strip() for s in summaries],
        "observation": data["observation"].strip(),
        "actions": clean_actions,
    }


def render(ctx: dict, prose: dict, quote_words: int = 25) -> str:
    """Assemble the pulse. Every number below comes from ctx (computed by code)."""
    w = ctx["window"]
    lines = [
        f"# Weekly Product Pulse: ChatGPT Play Store (India), week ending {w['end']}",
        f"Based on {w['review_count']} reviews over {w['weeks']} weeks.",
        "",
        "## Summary of top themes",
    ]
    for i, t in enumerate(ctx["themes"]):
        share = round(100 * t["low_star_share"])
        lines.append(
            f"{i + 1}. **{t['name']}**: {t['low_star']} of {t['total']} reviews were 1-2 star ({share}%); "
            f"last 4 weeks {t['last4']} vs {t['prev4']} before. {prose['summaries'][i]}"
        )
    lines += ["", "## Supporting user quotes"]
    for i, t in enumerate(ctx["themes"]):
        lines.append(f'{i + 1}. "{trim_quote(t["excerpt"], quote_words)}" ({t["rating"]} star, {t["name"]})')
    lines += ["", "## Key observation", prose["observation"]]
    lines.append(
        f"Fee confusion: {ctx['fee_confused']} of {ctx['fee_money']} money-related reviews, mostly about {ctx['fee_topic']}."
    )
    lines += ["", "## 3 action ideas"]
    for i, a in enumerate(prose["actions"]):
        lines.append(f"{i + 1}. {a} (Quote {i + 1})")  # action N <-> theme N <-> quote N, fixed by code
    return "\n".join(lines) + "\n"


def build_context() -> dict:
    """Load computed artifacts only; nothing is typed by hand."""
    for path in (config.INSIGHTS_JSON, config.THEMES_JSON, config.FEE_LABELS_CSV):
        if not path.exists() or path.stat().st_size == 0:
            raise DataError(f"{path.name} missing. Run `make analyze` first.")
    ins = json.loads(config.INSIGHTS_JSON.read_text(encoding="utf-8"))
    themes = {t["theme_id"]: t for t in json.loads(config.THEMES_JSON.read_text(encoding="utf-8"))}
    stats = {t["theme_id"]: t for t in ins["themes"]}
    trend = {t["theme_id"]: t for t in ins["trend"]}
    quotes = {q["theme_id"]: q for q in ins["quotes"]}
    fee = ins["fee"]
    if not fee.get("topic"):
        raise DataError("No fee issue identified in insights.json; run `make analyze`.")
    rows = []
    for tid in ins["top3"]:
        s, tr, q = stats[tid], trend[tid], quotes[tid]
        rows.append(
            {
                **s,
                "description": themes[tid]["description"],
                "prev4": tr["prev4"],
                "last4": tr["last4"],
                "direction": direction(tr["prev4"], tr["last4"]),
                "excerpt": q["excerpt"],
                "rating": q["rating"],
            }
        )
    return {
        "window": ins["window"],
        "themes": [{**r, "quote": r["excerpt"]} for r in rows],
        "fee_topic": fee["topic"].replace("_", " "),
        "fee_confused": fee_confused_count(fee["topic"]),
        "fee_money": fee["money_reviews"],
    }


def generate_pulse() -> str:
    """Write outputs/weekly_pulse.md (<=250 words) and return its text."""
    ctx = build_context()
    placeholder = {
        "summaries": ["" for _ in range(3)],
        "observation": "",
        "actions": ["" for _ in range(3)],
    }
    skeleton_words = count_words(render(ctx, placeholder))
    budget = max(40, MAX_WORDS - skeleton_words)
    text = ""
    for attempt in range(MAX_REWRITES + 1):
        data = ask_json(
            build_prompt(ctx, budget, attempt),
            {"summaries": "array", "observation": "string", "actions": "array"},
            cache_key=f"pulse-v2-{attempt}",
        )
        try:
            prose = validate_prose(data)
        except LLMError as exc:
            log.warning("Pulse prose rejected (attempt %d): %s", attempt + 1, exc)
            continue
        text = render(ctx, prose)
        if count_words(text) <= MAX_WORDS:
            break
        log.warning("Pulse has %d words; asking for a shorter draft", count_words(text))
        budget = max(30, budget - 15)
    else:
        text = ""
    if not text:
        raise LLMError("Could not get a valid pulse draft from the LLM")
    # Last resort, in code: trim displayed quotes (still verbatim prefixes) until within limit.
    quote_words = 25
    while count_words(text) > MAX_WORDS and quote_words > MIN_QUOTE_WORDS:
        quote_words -= 2
        text = render(ctx, prose, quote_words)
    if count_words(text) > MAX_WORDS:
        raise ValidationError(f"Pulse is {count_words(text)} words (limit {MAX_WORDS})")
    config.WEEKLY_PULSE_MD.parent.mkdir(parents=True, exist_ok=True)
    config.WEEKLY_PULSE_MD.write_text(text, encoding="utf-8")
    return text
