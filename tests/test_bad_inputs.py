"""Tests for architecture §12: each broken input must be caught safely (no crash, no LLM, no network)."""

from __future__ import annotations

import pytest

from src.checks import bad_inputs


@pytest.mark.parametrize("result", bad_inputs.run_bad_input_cases(), ids=lambda r: r["case"])
def test_bad_input_case_is_handled(result):
    assert result["ok"], f"{result['case']}: validator said {result['problems']}"


def test_bad_input_clean_control_has_no_problems():
    control = next(r for r in bad_inputs.run_bad_input_cases() if "control" in r["case"])
    assert control["problems"] == []


def test_bad_input_missing_file_does_not_crash(tmp_path):
    assert bad_inputs.validate_reviews_csv(tmp_path / "nope.csv") == ["file is empty or missing"]


def test_bad_input_garbage_file_does_not_crash(tmp_path):
    p = tmp_path / "x.csv"
    p.write_bytes(b"\x00\x01\x02 not,a\ncsv")
    assert isinstance(bad_inputs.validate_reviews_csv(p), list)


@pytest.mark.parametrize("text,expected", [
    ("mail me at a.b@example.com", True), ("call +91 98765 43210", True), ("9876543210", True),
    ("I paid Rs 399 for 3 months in 2026", False), ("it took 15 minutes 3 times", False),
])
def test_bad_input_pii_detector(text, expected):
    assert bad_inputs.find_pii(text) is expected
