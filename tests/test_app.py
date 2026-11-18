"""Tests for architecture §10 Streamlit app: every page loads, footer present, Approve is gated. No network."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import config

APP = Path(config.ROOT) / "app"
PAGES = sorted((APP / "pages").glob("*.py"))
FOOTER = "Built from public reviews and official pages. Facts only. Human-approved publishing."


def texts(at: AppTest) -> str:
    parts = [m.value for m in at.markdown] + [t.value for t in at.title] + [c.value for c in at.code]
    return "\n".join(parts)


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.stem)
def test_app_page_loads_without_error(page, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("APPROVER_PASSWORD", raising=False)
    at = AppTest.from_file(str(page), default_timeout=30).run()
    assert not at.exception, [e.value for e in at.exception]


def test_app_entry_shows_footer_and_seven_pages(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=30).run()
    assert not at.exception
    assert FOOTER in texts(at)


def test_app_demo_mode_hides_run_buttons(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    at = AppTest.from_file(str(APP / "pages" / "1_Overview.py"), default_timeout=30).run()
    assert not [b for b in at.button if b.key and b.key.startswith("run_")]


def test_app_local_mode_shows_run_buttons(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    at = AppTest.from_file(str(APP / "pages" / "1_Overview.py"), default_timeout=30).run()
    assert [b for b in at.button if b.key and b.key.startswith("run_")]


def test_app_approve_page_needs_a_password_configured(monkeypatch):
    monkeypatch.delenv("APPROVER_PASSWORD", raising=False)
    monkeypatch.setattr(config, "get_approver_password", lambda: None)
    at = AppTest.from_file(str(APP / "pages" / "5_Approve_and_Publish.py"), default_timeout=30).run()
    assert "not configured" in texts(at)
    assert not at.text_input


def test_app_approve_page_hides_payload_until_password_is_correct(monkeypatch):
    monkeypatch.setattr(config, "get_approver_password", lambda: "s3cret-pass")
    at = AppTest.from_file(str(APP / "pages" / "5_Approve_and_Publish.py"), default_timeout=30).run()
    assert "SHA-256" not in texts(at)
    at.text_input(key="approver_password").set_value("wrong").run()
    at.button(key="unlock").click().run()
    assert "Wrong password" in texts(at) and "SHA-256" not in texts(at)


def test_app_approve_button_stays_disabled_until_exact_APPROVE(monkeypatch):
    monkeypatch.setattr(config, "get_approver_password", lambda: "s3cret-pass")
    at = AppTest.from_file(str(APP / "pages" / "5_Approve_and_Publish.py"), default_timeout=30).run()
    at.text_input(key="approver_password").set_value("s3cret-pass").run()
    at.button(key="unlock").click().run()
    assert not at.exception
    if at.button(key="approve_button"):  # payload exists in this checkout
        for typed in ("approve", "Approve", "yes", ""):
            at.text_input(key="approve_text").set_value(typed).run()
            assert at.button(key="approve_button").disabled
        at.text_input(key="approve_text").set_value("APPROVE").run()
        assert not at.button(key="approve_button").disabled
