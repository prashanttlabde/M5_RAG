"""Implements architecture §2/§4 fee confusion detection (PRD FR7; INV-1, INV-3).

AI only labels (stance + fee topic from a closed list). Code filters money reviews, counts, and
picks the identified fee issue = the topic with the most `confused` reviews.
"""

from __future__ import annotations

import json
import logging
import re

import pandas as pd

from src import config
from src.errors import DataError, LLMError
from src.llm import ask_json

log = logging.getLogger("review_pulse.fee")

STANCES = ("confused", "complaint_only", "praise", "unrelated")
MAX_PROPOSED_TOPICS = 5  # code appends "other", so the closed list has at most 6
OTHER = "other"
TOPIC_SAMPLE = 60
BATCH_SIZE = 25
TRIM_CHARS = 300
MAX_ATTEMPTS = 4

_DEFINITIONS = (
    "Stance definitions (be strict):\n"
    "- confused: the user explicitly does NOT understand, or was surprised by, a charge, price, refund, "
    "tax/GST, renewal, or what a plan includes. Typical signs: 'why was I charged', 'unexpected charge', "
    "'charged after cancelling', 'I paid but it still says free', 'what does this plan include', "
    "'hit a limit I did not expect on my paid plan'.\n"
    "- complaint_only: the user understands the pricing but dislikes it (too expensive, paywall, "
    "usage limits, forced upgrade prompts, no refund policy, payment method not supported).\n"
    "- praise: positive about price or value.\n"
    "- unrelated: the review is really about something else (crashes, bugs, lost chats, ads, censorship, "
    "wrong answers), even if the user mentions being a paying customer.\n"
    'Examples: "too expensive" -> complaint_only. "app keeps crashing, I pay a subscription" -> unrelated. '
    '"I was charged twice and don\'t know why" -> confused.\n'
    "When unsure between confused and anything else, choose the other label.\n"
)


def money_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """Reviews containing a money keyword from config (whole word, case-insensitive)."""
    words = config.get_product_config()["money_keywords"]
    pattern = re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.IGNORECASE)
    hit = df["text"].astype(str).apply(lambda t: bool(pattern.search(t)))
    return df[hit].reset_index(drop=True)


def _lines(df: pd.DataFrame, indices) -> str:
    return "\n".join(f"{i}: {str(df.loc[i, 'text'])[:TRIM_CHARS]!r}" for i in indices)


def propose_topics(money: pd.DataFrame) -> list[str]:
    """LLM proposes a short closed list of fee topics; code adds 'other' and normalises."""
    sample = money.sample(n=min(TOPIC_SAMPLE, len(money)), random_state=42).reset_index(drop=True)
    prompt = (
        "These Play Store reviews of the ChatGPT app mention money. "
        f"Propose AT MOST {MAX_PROPOSED_TOPICS} short fee topics (snake_case, e.g. unexpected_charge) "
        "that cover what users talk about regarding fees, charges, plans or billing. Do not count anything.\n"
        'Return JSON: {"topics": ["topic_one", "topic_two"]}\n'
        f"Reviews:\n{_lines(sample, range(len(sample)))}"
    )
    data = ask_json(prompt, {"topics": "array"}, cache_key="fee-topics-v1")
    topics: list[str] = []
    for t in data["topics"]:
        name = re.sub(r"[^a-z0-9]+", "_", str(t).lower()).strip("_")
        if name and name != OTHER and name not in topics:
            topics.append(name)
    if not topics:
        raise LLMError("LLM proposed no usable fee topics")
    return topics[:MAX_PROPOSED_TOPICS] + [OTHER]


def label_batch(batch: pd.DataFrame, topics: list[str]) -> dict[int, tuple[str, str]]:
    """Label a batch; re-ask only for reviews the LLM skipped or labelled invalidly."""
    result: dict[int, tuple[str, str]] = {}
    for attempt in range(MAX_ATTEMPTS):
        missing = [i for i in range(len(batch)) if i not in result]
        if not missing:
            return result
        prompt = (
            "Label each review about money in the ChatGPT app.\n"
            f"{_DEFINITIONS}"
            f"Allowed fee_topic values: {topics}. Use 'other' if none fits.\n"
            'Return JSON: {"labels": [{"i": 0, "stance": "confused", "fee_topic": "unexpected_charge"}]} '
            "with one entry per review index listed. Do not count anything.\n"
            f"Reviews:\n{_lines(batch, missing)}"
        )
        data = ask_json(prompt, {"labels": "array"}, cache_key=f"fee-labels-v2-{attempt}")
        for item in data["labels"]:
            if (
                isinstance(item, dict)
                and item.get("i") in missing
                and item.get("stance") in STANCES
                and item.get("fee_topic") in topics
            ):
                result[item["i"]] = (item["stance"], item["fee_topic"])
    if len(result) < len(batch):
        raise LLMError(f"LLM left {len(batch) - len(result)} money reviews unlabelled")
    return result


def count_fee(labels: pd.DataFrame) -> dict:
    """All counts and the identified issue, in code. Ties: alphabetical topic."""
    stance_counts = {s: int((labels["stance"] == s).sum()) for s in STANCES}
    confused = labels[labels["stance"] == "confused"]["fee_topic"].value_counts()
    topic = ""
    if len(confused):
        best = confused.max()
        topic = min(t for t, n in confused.items() if n == best)
    return {"topic": topic, **stance_counts, "money_reviews": len(labels)}


def run_fee() -> dict:
    """Label money reviews, write data/fee_labels.csv, update the fee block of insights.json."""
    if not config.REVIEWS_BALANCED_CSV.exists():
        raise DataError("data/reviews_balanced.csv missing. Run `make collect` first.")
    if not config.INSIGHTS_JSON.exists() or config.INSIGHTS_JSON.stat().st_size == 0:
        raise DataError("data/insights.json missing. Run the P3 steps first.")
    money = money_reviews(pd.read_csv(config.REVIEWS_BALANCED_CSV))
    if money.empty:
        raise DataError("No money-related reviews found.")
    topics = propose_topics(money)
    rows: list[dict[str, str]] = []
    for start in range(0, len(money), BATCH_SIZE):
        batch = money.iloc[start : start + BATCH_SIZE].reset_index(drop=True)
        labelled = label_batch(batch, topics)
        for i in range(len(batch)):
            stance, topic = labelled[i]
            rows.append({"review_id": batch.loc[i, "review_id"], "stance": stance, "fee_topic": topic})
    labels = pd.DataFrame(rows, columns=["review_id", "stance", "fee_topic"])
    labels.to_csv(config.FEE_LABELS_CSV, index=False)

    fee = count_fee(labels)
    insights = json.loads(config.INSIGHTS_JSON.read_text(encoding="utf-8"))
    insights["fee"] = fee
    config.INSIGHTS_JSON.write_text(json.dumps(insights, indent=2, ensure_ascii=False), encoding="utf-8")

    if fee["topic"]:
        n = int(((labels["stance"] == "confused") & (labels["fee_topic"] == fee["topic"])).sum())
        print(f"{n} of {fee['money_reviews']} fee-related reviews were confused about {fee['topic']}.")
    else:
        print(f"0 of {fee['money_reviews']} fee-related reviews were confused; no fee issue identified.")
    return fee
