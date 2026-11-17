"""Tests for architecture §5 LLM layer: validation, retry, caching (INV-8)."""

from __future__ import annotations

import pytest

from src import llm
from src.errors import LLMError


@pytest.fixture(autouse=True)
def _model(monkeypatch):
    monkeypatch.setattr(llm.config, "get_llm_model", lambda: "test-model")


def test_cache_hit_makes_no_second_call(tmp_path):
    calls = []

    def fake(model, prompt):
        calls.append(1)
        return '{"themes": []}'

    schema = {"themes": "array"}
    assert llm.ask_json("p", schema, complete=fake, cache_dir=tmp_path) == {"themes": []}
    assert llm.ask_json("p", schema, complete=fake, cache_dir=tmp_path) == {"themes": []}
    assert len(calls) == 1
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_retries_on_invalid_json_then_succeeds(tmp_path):
    answers = iter(["not json", '{"x": "wrong"}', '{"themes": [1]}'])
    out = llm.ask_json("p", {"themes": "array"}, complete=lambda m, p: next(answers), cache_dir=tmp_path)
    assert out == {"themes": [1]}


def test_gives_up_after_two_retries(tmp_path):
    calls = []

    def bad(model, prompt):
        calls.append(1)
        return "nope"

    with pytest.raises(LLMError):
        llm.ask_json("p", {"a": "string"}, complete=bad, cache_dir=tmp_path)
    assert len(calls) == 3


def test_validate_keys_rejects_wrong_type():
    with pytest.raises(LLMError):
        llm.validate_keys({"n": "5"}, {"n": "integer"})
