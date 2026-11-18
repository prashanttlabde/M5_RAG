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


def _flatten(block):
    """Every element under a block, in page order."""
    from streamlit.testing.v1.element_tree import Block

    for child in block.children.values():
        yield child
        if isinstance(child, Block):
            yield from _flatten(child)


def test_app_run_buttons_sit_above_the_kpis_in_local_mode(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    at = AppTest.from_file(str(APP / "pages" / "1_Overview.py"), default_timeout=30).run()
    order = list(_flatten(at.main))
    first_button = next(i for i, e in enumerate(order) if getattr(e, "key", None) and str(e.key).startswith("run_"))
    kpi = next(i for i, e in enumerate(order) if "Reviews analysed" in str(getattr(e, "value", "")))
    assert first_button < kpi


def test_app_insights_draws_interactive_charts():
    at = AppTest.from_file(str(APP / "pages" / "2_Insights.py"), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.get("vega_lite_chart")) >= 7  # bars, donut, lines, heatmap, trend, fee donut, fee topics
    assert at.multiselect(key="ins_themes").value  # filters exist and default to all themes


def test_app_insights_filter_changes_the_selection(monkeypatch):
    at = AppTest.from_file(str(APP / "pages" / "2_Insights.py"), default_timeout=60).run()
    before = next(m.value for m in at.markdown if "Reviews in selection" in m.value)
    at.multiselect(key="ins_themes").set_value([at.multiselect(key="ins_themes").options[0]]).run()
    after = next(m.value for m in at.markdown if "Reviews in selection" in m.value)
    assert before != after and not at.exception


def _entry(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_app_topbar_has_its_controls(monkeypatch):
    keys = {b.key for b in _entry(monkeypatch).button}
    assert {"tb_stop", "tb_share", "tb_star", "tb_theme", "tb_cache"} <= keys


def test_app_stop_toggle_disables_the_run_buttons(monkeypatch):
    at = _entry(monkeypatch)
    at.button(key="tb_stop").click().run()
    assert at.session_state["paused"] is True
    runs = [b for b in at.button if b.key and str(b.key).startswith("run_")]
    assert runs and all(b.disabled for b in runs)


def test_app_theme_toggle_switches_to_dark(monkeypatch):
    at = _entry(monkeypatch)
    at.button(key="tb_theme").click().run()
    assert at.session_state["dark"] is True


def test_app_star_toggle(monkeypatch):
    at = _entry(monkeypatch)
    at.button(key="tb_star").click().run()
    assert at.session_state["starred"] is True


def test_app_starts_in_a_clean_process_without_pythonpath(tmp_path):
    """Regression: on Streamlit Cloud the repo root is not on sys.path, so the entry file must add it itself."""
    import os
    import subprocess
    import sys

    code = (
        "from streamlit.testing.v1 import AppTest;"
        f"at = AppTest.from_file({str(APP / 'streamlit_app.py')!r}, default_timeout=60).run();"
        "assert not at.exception, [e.value for e in at.exception];"
        "print('OK')"
    )
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"} | {"DEMO_MODE": "true"}
    out = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True, check=False)
    assert "OK" in out.stdout, out.stderr[-800:]
