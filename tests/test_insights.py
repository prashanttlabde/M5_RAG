"""Tests for architecture §4 insights: ranking rule, verbatim quotes, recompute-from-scratch (INV-1, INV-2)."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src import config
from src.analyze import quotes, rank, trend

needs_artifacts = pytest.mark.skipif(
    not config.INSIGHTS_JSON.exists() or config.INSIGHTS_JSON.stat().st_size == 0,
    reason="run `make analyze` first",
)


def test_rank_tie_break_order():
    stats = [
        {"theme_id": "a", "name": "Zeta", "total": 10, "low_star": 5, "low_star_share": 0.5},
        {"theme_id": "b", "name": "Beta", "total": 5, "low_star": 5, "low_star_share": 1.0},
        {"theme_id": "c", "name": "Alpha", "total": 10, "low_star": 5, "low_star_share": 0.5},
        {"theme_id": "d", "name": "Huge", "total": 1000, "low_star": 4, "low_star_share": 0.004},
    ]
    # most low-star wins; tie -> higher share (Beta); tie -> alphabetical (Alpha before Zeta); volume ignored
    assert rank.rank_top3(stats) == ["b", "c", "a"]


def test_excerpt_must_be_verbatim_substring():
    text = "the app keeps charging me every month even after I cancelled my plan last week"
    assert quotes.verified_excerpt("charging me every month even after I cancelled", text) == (
        "charging me every month even after I cancelled"
    )
    fallback = quotes.verified_excerpt("charges me monthly despite cancelling", text)
    assert fallback == quotes.first_words(text)
    assert fallback in text


def test_candidates_exclude_pii():
    df = pd.DataFrame(
        {
            "review_id": ["1", "2"],
            "theme_id": ["t1", "t1"],
            "rating": [1, 1],
            "text": ["call me on 9876543210 because this app charged me twice already this month ok", "this app charged me twice already this month and nobody replied to me ok"],
        }
    )
    assert list(quotes.candidates_for(df, "t1")["review_id"]) == ["2"]


@needs_artifacts
def test_recompute_matches_insights_json():
    saved = json.loads(config.INSIGHTS_JSON.read_text(encoding="utf-8"))
    joined, themes = rank.load_joined()
    stats = rank.compute_theme_stats(joined, themes)
    top3 = rank.rank_top3(stats)
    assert saved["themes"] == stats
    assert saved["top3"] == top3 and len(top3) == 3
    assert saved["window"] == trend.compute_window(joined)
    assert saved["trend"] == trend.compute_trend(joined, top3)
    assert saved["voice_tag"] == trend.compute_voice_tag(joined)
    assert saved["ranking_rule"] == rank.ranking_rule()


@needs_artifacts
def test_saved_quotes_are_real_review_text():
    saved = json.loads(config.INSIGHTS_JSON.read_text(encoding="utf-8"))
    full = pd.read_csv(config.REVIEWS_FULL_CSV).set_index("review_id")
    assert len(saved["quotes"]) == 3
    for q in saved["quotes"]:
        assert q["excerpt"] in full.loc[q["review_id"], "text"]
        assert len(q["excerpt"].split()) <= 25


def test_fee_issue_is_topic_with_most_confused():
    from src.analyze.fee import count_fee

    labels = pd.DataFrame(
        {
            "review_id": list("abcdef"),
            "stance": ["confused", "confused", "confused", "complaint_only", "complaint_only", "praise"],
            "fee_topic": ["gst", "unexpected_charge", "unexpected_charge", "too_pricey", "too_pricey", "gst"],
        }
    )
    fee = count_fee(labels)
    assert fee["topic"] == "unexpected_charge"  # most confused, not most complaints
    assert fee["confused"] == 3 and fee["complaint_only"] == 2 and fee["money_reviews"] == 6


def test_fee_zero_confused_gives_empty_topic():
    from src.analyze.fee import count_fee

    labels = pd.DataFrame({"review_id": ["a"], "stance": ["complaint_only"], "fee_topic": ["other"]})
    assert count_fee(labels)["topic"] == ""
