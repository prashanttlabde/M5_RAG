"""Implements architecture §10 shared UI: look and feel, artifact loaders, empty states.

The UI is a window onto computed artifacts: every number shown is loaded from data/ or outputs/.
Status is always an icon plus a word (never colour alone). No emoji, no gradients.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from src import config

FOOTER = "Built from public reviews and official pages. Facts only. Human-approved publishing."

CSS = """
<style>
.stApp { background: #F3F5F7; }
h1, h2, h3, h4 { color: #0B3C49 !important; font-weight: 600 !important; }
a { color: #1F7A8C !important; }
.card { background: #FFFFFF; border: 1px solid #D8DEE4; border-radius: 8px; padding: 16px 18px; margin-bottom: 12px; }
[data-testid="stVerticalBlockBorderWrapper"] { background: #FFFFFF; border-color: #D8DEE4 !important; border-radius: 8px; }
.metric .label { font-size: .78rem; color: #52616B; text-transform: uppercase; letter-spacing: .04em; }
.metric .value { font-size: 1.9rem; font-weight: 600; color: #0B3C49; line-height: 1.2; }
.metric .note { font-size: .85rem; color: #52616B; }
.scroll { overflow-x: auto; }
table.t { border-collapse: collapse; width: 100%; min-width: 520px; }
table.t th, table.t td { border-bottom: 1px solid #E3E8ED; padding: 8px 10px; text-align: left; font-size: .92rem; vertical-align: top; }
table.t th { color: #0B3C49; font-weight: 600; }
.badge { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; font-size: .85rem; padding: 2px 10px; border: 1px solid; border-radius: 999px; }
.badge .ic { width: 16px; height: 16px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: .7rem; color: #FFFFFF; }
.badge.ok { color: #1B6E3C; border-color: #1B6E3C; } .badge.ok .ic { background: #1B6E3C; }
.badge.fail { color: #A4262C; border-color: #A4262C; } .badge.fail .ic { background: #A4262C; }
.badge.warn { color: #8A5A00; border-color: #8A5A00; } .badge.warn .ic { background: #8A5A00; }
.quote { border-left: 3px solid #1F7A8C; padding: 4px 12px; margin: 8px 0; color: #26343D; }
.quote .meta { color: #52616B; font-size: .82rem; }
.footer { text-align: center; color: #52616B; font-size: .85rem; padding: 24px 0 8px; border-top: 1px solid #D8DEE4; margin-top: 32px; }
.sub { color: #52616B; margin-top: -8px; }
@media (max-width: 640px) { .metric .value { font-size: 1.5rem; } }
</style>
"""


def esc(value: object) -> str:
    """HTML-escape anything that comes from data (reviews are untrusted text)."""
    return html.escape(str(value))


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def footer() -> None:
    st.markdown(f'<div class="footer">{esc(FOOTER)}</div>', unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    st.title(title)
    if subtitle:
        st.markdown(f'<p class="sub">{esc(subtitle)}</p>', unsafe_allow_html=True)


def is_demo() -> bool:
    return config.get_demo_mode()


def badge(kind: str, word: str) -> str:
    """Status = icon + word. kind: ok | fail | warn."""
    icon = {"ok": "✓", "fail": "✗", "warn": "!"}[kind]
    return f'<span class="badge {kind}"><span class="ic">{icon}</span>{esc(word)}</span>'


def metric(label: str, value: object, note: str = "") -> str:
    extra = f'<div class="note">{esc(note)}</div>' if note else ""
    return f'<div class="card metric"><div class="label">{esc(label)}</div><div class="value">{esc(value)}</div>{extra}</div>'


def table(headers: list[str], rows: list[list[object]]) -> None:
    """Horizontally scrollable table (safe on small screens). Cell text is escaped."""
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c if isinstance(c, _Raw) else esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    st.markdown(f'<div class="card scroll"><table class="t"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>', unsafe_allow_html=True)


class _Raw(str):
    """Marks trusted HTML (such as a badge) inside a table cell."""


def raw(html_text: str) -> _Raw:
    return _Raw(html_text)


def load_json(path: Path) -> dict | list | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_text(path: Path) -> str | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    return path.read_text(encoding="utf-8")


def empty_state(what: str, how: str) -> None:
    """Polite message when an artifact has not been produced yet."""
    st.markdown(
        f'<div class="card">{badge("warn", "Not available yet")} <p style="margin:8px 0 0">{esc(what)} has not been produced. {esc(how)}</p></div>',
        unsafe_allow_html=True,
    )


def theme_names() -> dict[str, str]:
    themes = load_json(config.THEMES_JSON) or []
    return {t["theme_id"]: t["name"] for t in themes}
