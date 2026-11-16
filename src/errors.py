"""Implements architecture failure modes as domain errors (see architecture §14)."""

from __future__ import annotations


class ReviewPulseError(Exception):
    """Base error for Review Pulse."""


class ConfigError(ReviewPulseError):
    """Missing or invalid configuration / environment."""


class DataError(ReviewPulseError):
    """Review or artifact data is missing, incomplete, or invalid."""


class LLMError(ReviewPulseError):
    """LLM call failed, returned invalid JSON, or exhausted retries."""


class ValidationError(ReviewPulseError):
    """A computed artifact failed a rule-based check."""


class PublishError(ReviewPulseError):
    """Approval or MCP publishing step failed or was blocked."""
