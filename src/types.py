"""Implements architecture §4 data model as dataclasses (fields only, no logic)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Review:
    review_id: str
    date: str
    week_start: str
    rating: int
    text: str


@dataclass
class Theme:
    theme_id: str
    name: str
    description: str


@dataclass
class Quote:
    theme_id: str
    review_id: str
    excerpt: str
    rating: int
    date: str


@dataclass
class FeeLabel:
    review_id: str
    stance: str  # confused | complaint_only | praise | unrelated
    fee_topic: str


@dataclass
class ThemeStats:
    theme_id: str
    name: str
    total: int
    low_star: int
    low_star_share: float


@dataclass
class WindowStats:
    start: str
    end: str
    weeks: int
    review_count: int


@dataclass
class TrendPoint:
    theme_id: str
    prev4: int
    last4: int


@dataclass
class VoiceTag:
    count: int
    low_star: int


@dataclass
class FeeInsight:
    topic: str
    confused: int
    complaint_only: int
    praise: int
    unrelated: int
    money_reviews: int


@dataclass
class Insights:
    window: WindowStats
    themes: list[ThemeStats]
    top3: list[str]
    ranking_rule: str
    quotes: list[Quote]
    trend: list[TrendPoint]
    voice_tag: VoiceTag
    fee: FeeInsight


@dataclass
class DocEntry:
    date: str
    top_themes: list[str]
    weekly_pulse: str
    identified_fee_issue: str
    explanation_bullets: list[str]
    source_links: list[str] = field(default_factory=list)
