"""P0 scaffolding tests: imports and secret-safety gitignore entries."""

from __future__ import annotations

from pathlib import Path

import src.config
import src.errors
import src.types

ROOT = Path(__file__).resolve().parent.parent


def test_config_module_exposes_paths_and_env_helpers() -> None:
    assert src.config.ROOT == ROOT
    assert callable(src.config.get_groq_api_key)
    assert callable(src.config.get_llm_model)
    assert callable(src.config.get_n8n_mcp_url)
    assert callable(src.config.get_n8n_mcp_token)
    assert callable(src.config.get_approver_password)
    assert callable(src.config.get_demo_mode)
    assert isinstance(src.config.get_demo_mode(), bool)


def test_errors_module_exposes_domain_exceptions() -> None:
    assert issubclass(src.errors.ConfigError, src.errors.ReviewPulseError)
    assert issubclass(src.errors.DataError, src.errors.ReviewPulseError)
    assert issubclass(src.errors.LLMError, src.errors.ReviewPulseError)
    assert issubclass(src.errors.ValidationError, src.errors.ReviewPulseError)
    assert issubclass(src.errors.PublishError, src.errors.ReviewPulseError)


def test_types_module_exposes_core_dataclasses() -> None:
    assert src.types.Review
    assert src.types.Theme
    assert src.types.Quote
    assert src.types.FeeLabel
    assert src.types.Insights
    assert src.types.DocEntry


def test_gitignore_lists_env_and_cache() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in text
    assert "data/cache/" in text or "data/cache" in text


def test_redact_pii_removes_emails_and_phone_like_numbers():
    from src.collect.clean import redact_pii

    assert redact_pii("write to a.b@example.com now") == "write to [email] now"
    assert redact_pii("rate -99999999999 stars") == "rate -[number] stars"
    assert redact_pii("I paid Rs 399 for 3 months") == "I paid Rs 399 for 3 months"
