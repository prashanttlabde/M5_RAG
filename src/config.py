"""Implements architecture §3 layout paths and §11 configuration / secrets."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root: parent of src/
ROOT: Path = Path(__file__).resolve().parent.parent

CONFIG_DIR: Path = ROOT / "config"
DATA_DIR: Path = ROOT / "data"
CACHE_DIR: Path = DATA_DIR / "cache"
SOURCES_TEXT_DIR: Path = DATA_DIR / "sources"
OUTPUTS_DIR: Path = ROOT / "outputs"

PRODUCT_YAML: Path = CONFIG_DIR / "product.yaml"
SOURCES_YAML: Path = CONFIG_DIR / "sources.yaml"

REVIEWS_FULL_CSV: Path = DATA_DIR / "reviews_full.csv"
REVIEWS_BALANCED_CSV: Path = DATA_DIR / "reviews_balanced.csv"
THEMES_JSON: Path = DATA_DIR / "themes.json"
ASSIGNMENTS_CSV: Path = DATA_DIR / "assignments.csv"
FEE_LABELS_CSV: Path = DATA_DIR / "fee_labels.csv"
INSIGHTS_JSON: Path = DATA_DIR / "insights.json"
CHUNKS_JSONL: Path = DATA_DIR / "chunks.jsonl"

WEEKLY_PULSE_MD: Path = OUTPUTS_DIR / "weekly_pulse.md"
FEE_EXPLAINER_MD: Path = OUTPUTS_DIR / "fee_explainer.md"
FEE_EXPLAINER_JSON: Path = OUTPUTS_DIR / "fee_explainer.json"
APPROVAL_PAYLOAD_JSON: Path = OUTPUTS_DIR / "approval_payload.json"
EMAIL_DRAFT_TXT: Path = OUTPUTS_DIR / "email_draft.txt"
PUBLISH_LOG_JSONL: Path = OUTPUTS_DIR / "publish_log.jsonl"
CHECKS_REPORT_MD: Path = OUTPUTS_DIR / "checks_report.md"

_ENV_LOADED = False


def load_env() -> None:
    """Load `.env` from the project root once. Never prints secret values."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    load_dotenv(ROOT / ".env")
    _ENV_LOADED = True


def _get_env(name: str, default: str | None = None) -> str | None:
    load_env()
    value = os.getenv(name, default)
    if value is None or value == "":
        return default
    return value


def get_groq_api_key() -> str | None:
    return _get_env("GROQ_API_KEY")


def get_llm_model() -> str | None:
    return _get_env("LLM_MODEL")


def get_n8n_mcp_url() -> str | None:
    return _get_env("N8N_MCP_URL")


def get_n8n_mcp_token() -> str | None:
    return _get_env("N8N_MCP_TOKEN")


def get_approver_password() -> str | None:
    return _get_env("APPROVER_PASSWORD")


def get_demo_mode() -> bool:
    raw = (_get_env("DEMO_MODE", "false") or "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def get_product_config() -> dict:
    """Load config/product.yaml (ranking rule, keyword lists, etc.)."""
    import yaml

    with PRODUCT_YAML.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}
