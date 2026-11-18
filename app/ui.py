"""Implements architecture §10 shared UI: design system, components, artifact loaders, empty states.

Look: clean B2B SaaS analytics (Inter + Plus Jakarta Sans, indigo accent, hairline borders, light and
dark themes). The UI is a window onto computed artifacts: every number shown is loaded from data/ or
outputs/. Status is always an icon plus a word (never colour alone).
"""

from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from src import config

FOOTER = "Built from public reviews and official pages. Facts only. Human-approved publishing."
REPO_URL = "https://github.com/prashanttlabde/M5_RAG"

TOKENS = {
    "light": {
        "bg": "#F8FAFC", "surface": "#FFFFFF", "text": "#0F172A", "muted": "#64748B", "border": "#E2E8F0",
        "subtle": "rgba(248,250,252,0.7)", "accent": "#4F46E5", "accent_soft": "#EEF2FF", "accent_text": "#4338CA",
        "accent_ring": "rgba(79,70,229,0.15)", "ok": "#10B981", "ok_text": "#047857", "ok_soft": "#ECFDF5",
        "warn": "#F59E0B", "warn_text": "#B45309", "warn_soft": "#FFFBEB", "bad": "#F43F5E", "bad_text": "#BE123C",
        "bad_soft": "#FFF1F2", "shadow": "0 1px 3px rgba(15,23,42,0.04)", "blur_bg": "rgba(248,250,252,0.85)",
    },
    "dark": {
        "bg": "#020617", "surface": "#0F172A", "text": "#FFFFFF", "muted": "#94A3B8", "border": "#1E293B",
        "subtle": "rgba(30,41,59,0.45)", "accent": "#6366F1", "accent_soft": "rgba(99,102,241,0.16)",
        "accent_text": "#A5B4FC", "accent_ring": "rgba(129,140,248,0.25)", "ok": "#34D399", "ok_text": "#6EE7B7",
        "ok_soft": "rgba(16,185,129,0.14)", "warn": "#FBBF24", "warn_text": "#FCD34D", "warn_soft": "rgba(245,158,11,0.12)",
        "bad": "#FB7185", "bad_text": "#FDA4AF", "bad_soft": "rgba(244,63,94,0.14)", "shadow": "0 1px 3px rgba(0,0,0,0.35)",
        "blur_bg": "rgba(2,6,23,0.85)",
    },
}

FONTS = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700&display=swap"

# 16px outline icons (stroke = currentColor); used inside HTML only.
_ICONS = {
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "chat": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "lock": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "layout": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    "tag": '<path d="M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8z"/><circle cx="7" cy="7" r="1.5"/>',
    "alert": '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
    "arrow": '<path d="M5 12h14M12 5l7 7-7 7"/>',
    "chevron": '<path d="m6 9 6 6 6-6"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "pulse": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "play": '<polygon points="6 3 20 12 6 21 6 3"/>',
}


def icon(name: str, size: int = 16) -> str:
    return (
        f'<svg class="ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_ICONS[name]}</svg>'
    )


def is_dark() -> bool:
    return bool(st.session_state.get("dark", False))


def build_css(dark: bool) -> str:
    t = TOKENS["dark" if dark else "light"]
    var = ";".join(f"--{k.replace('_', '-')}:{v}" for k, v in t.items())
    return f"""
<style>
@import url('{FONTS}');
:root {{ {var}; }}
html, body, .stApp, [data-testid="stAppViewContainer"], .stApp p, .stApp label, .stApp li, .stApp input, .stApp textarea, .stApp button {{ font-family: 'Inter', system-ui, sans-serif; }}
[data-testid="stIconMaterial"], .material-symbols-rounded {{ font-family: 'Material Symbols Rounded' !important; font-variant-numeric: normal; }}
.stApp {{ background: var(--bg); color: var(--text); }}
.stApp, .stApp p, .stApp li, .stApp label {{ color: var(--text); }}
h1, h2, h3, h4, .display {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important; color: var(--text) !important; font-weight: 700 !important; letter-spacing: -0.015em; }}
a {{ color: var(--accent-text) !important; text-decoration: none; }}
.num, .stApp [data-testid="stMetricValue"], table.t td, .kpi .value, .pill, .badge {{ font-variant-numeric: tabular-nums; }}
[data-testid="stHeader"], [data-testid="stToolbar"] {{ background: transparent; pointer-events: none; }}
[data-testid="stHeader"] button, [data-testid="stHeader"] a {{ pointer-events: auto; }}
[data-testid="stToolbarActions"], [data-testid="stAppDeployButton"], [data-testid="stMainMenu"], #MainMenu, footer {{ display: none !important; }}
[data-testid="stMainBlockContainer"] {{ max-width: 1180px; padding: 0.75rem 2rem 3rem; }}
[data-testid="stSidebar"] {{ background: var(--surface); border-right: 1px solid var(--border); }}
[data-testid="stSidebar"][aria-expanded="true"] {{ width: 256px !important; min-width: 256px !important; }}
[data-testid="stSidebarContent"] {{ padding: 0; }}
[data-testid="stSidebarUserContent"] {{ padding: 16px 14px 12px; }}
/* ---- sidebar brand and nav */
.brand {{ display: flex; align-items: center; gap: 10px; padding: 4px 6px 14px; }}
.brand .logo {{ width: 34px; height: 34px; border-radius: 10px; background: var(--accent); color: #fff; display: flex; align-items: center; justify-content: center; box-shadow: 0 1px 2px rgba(79,70,229,0.35); }}
.brand .title {{ font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; font-size: 1.02rem; color: var(--text); line-height: 1.15; }}
.brand .mode {{ font-size: 0.74rem; color: var(--muted); display: flex; align-items: center; gap: 6px; margin-top: 2px; }}
.dot {{ width: 7px; height: 7px; border-radius: 50%; background: var(--ok); position: relative; display: inline-block; }}
.dot::after {{ content: ""; position: absolute; inset: -3px; border-radius: 50%; background: var(--ok); opacity: .35; animation: pulse 2s ease-out infinite; }}
@keyframes pulse {{ 0% {{ transform: scale(.6); opacity: .5; }} 100% {{ transform: scale(1.7); opacity: 0; }} }}
.nav-label {{ font-size: 0.68rem; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); padding: 6px 8px 6px; font-weight: 600; }}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {{ border-radius: 8px; padding: 7px 10px; margin: 1px 0; color: var(--muted) !important; border: 1px solid transparent; }}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"], [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] * {{ color: var(--muted) !important; }}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p {{ font-size: 0.9rem; font-weight: 500; }}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"], [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] * {{ color: var(--accent-text) !important; }}
[data-testid="stMain"] [data-testid="stPageLink-NavLink"], [data-testid="stMain"] [data-testid="stPageLink-NavLink"] * {{ color: var(--text) !important; }}
[data-testid="stCode"] pre, [data-testid="stCode"] code {{ background: var(--surface) !important; color: var(--text) !important; }}
[data-testid="stPopoverBody"], div[role="dialog"] {{ background: var(--surface) !important; color: var(--text); border: 1px solid var(--border); }}
[data-testid="stExpander"] summary, [data-testid="stExpander"] p {{ color: var(--text); }}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {{ background: var(--accent-soft); }}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] {{ background: var(--accent-soft); color: var(--accent-text) !important; border-color: var(--accent-ring); }}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] p {{ font-weight: 600; }}
.health {{ border: 1px solid var(--border); background: var(--subtle); border-radius: 12px; padding: 10px 12px; margin: 14px 0 10px; }}
.health .row {{ display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; font-weight: 600; color: var(--text); }}
.health .meta {{ font-size: 0.74rem; color: var(--muted); margin-top: 4px; }}
.st-key-manage_app a {{ width: 100%; justify-content: space-between !important; }}
.st-key-manage_app a::after {{ content: "\\2318K"; font-size: 0.68rem; border: 1px solid var(--border); border-radius: 5px; padding: 0 5px; color: var(--muted); margin-left: auto; }}
/* ---- top bar */
.st-key-topbar {{ position: sticky; top: 0; z-index: 90; background: var(--blur-bg); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); margin: 0 -2rem 18px; padding: 8px 2rem; }}
.st-key-topbar [data-testid="stHorizontalBlock"] {{ align-items: center; gap: 0.4rem; flex-wrap: wrap; }}
.ctx {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
.ctx .app {{ font-weight: 600; font-size: 0.92rem; color: var(--text); }}
/* ---- buttons */
.stApp [data-testid="stBaseButton-secondary"], .stApp [data-testid="stBaseButton-secondaryFormSubmit"], .stApp .stDownloadButton button, .stApp [data-testid="stPopoverButton"], .stApp a[data-testid="stBaseLinkButton-secondary"] {{ background: var(--surface); color: var(--text); border: 1px solid var(--border); border-radius: 8px; font-size: 0.84rem; font-weight: 500; min-height: 34px; padding: 0.2rem 0.7rem; box-shadow: var(--shadow); }}
.stApp [data-testid="stBaseButton-secondary"]:hover, .stApp [data-testid="stPopoverButton"]:hover, .stApp a[data-testid="stBaseLinkButton-secondary"]:hover {{ border-color: var(--accent); color: var(--accent-text); }}
.stApp [data-testid="stBaseButton-primary"], .stApp a[data-testid="stBaseLinkButton-primary"] {{ background: var(--accent); color: #fff !important; border: 1px solid var(--accent); border-radius: 8px; font-size: 0.84rem; font-weight: 600; min-height: 34px; padding: 0.2rem 0.8rem; }}
.stApp [data-testid="stBaseButton-primary"]:hover {{ filter: brightness(1.08); }}
.st-key-tb_stop button {{ background: var(--bad-soft) !important; color: var(--bad-text) !important; border-color: transparent !important; }}
.stApp [data-testid="stBaseButton-secondary"]:disabled {{ opacity: .55; }}
/* ---- cards and layout */
.card, [class*="st-key-card"] {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; margin-bottom: 14px; box-shadow: var(--shadow); }}
[class*="st-key-card"] > [data-testid="stVerticalBlock"] {{ gap: 0.6rem; }}
.card-head {{ display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }}
.card-head h3 {{ margin: 0; font-size: 1.02rem; }}
.page-head {{ display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; margin: 4px 0 18px; }}
.page-head .titlerow {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
.page-head h1 {{ margin: 0 !important; padding: 0 !important; font-size: 1.75rem !important; }}
.page-head .sub {{ color: var(--muted); margin: 4px 0 0; font-size: 0.93rem; }}
.sub, .stApp p.sub {{ color: var(--muted); font-size: 0.9rem; }}
.stApp .card-head + p.sub, .stApp .page-head p.sub {{ font-size: 0.9rem; }}
.st-key-card_run button {{ min-height: 46px; }}
.st-key-card_run button p {{ white-space: normal; line-height: 1.15; font-size: 0.82rem; }}
.st-key-card_fee [data-testid="stElementContainer"]:has([data-testid="stPageLink"]) {{ display: flex; justify-content: flex-end; }}
.st-key-card_fee [data-testid="stPageLink-NavLink"] {{ flex-direction: row-reverse; width: fit-content; margin-left: auto; }}
.kpis {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-bottom: 14px; }}
@media (max-width: 900px) {{ .kpis {{ grid-template-columns: 1fr; }} }}
.kpi {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; box-shadow: var(--shadow); }}
.kpi .top {{ display: flex; justify-content: space-between; align-items: center; }}
.kpi .label {{ font-size: 0.72rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); font-weight: 600; }}
.kpi .badge-ic {{ width: 28px; height: 28px; border-radius: 8px; background: var(--accent-soft); color: var(--accent-text); display: flex; align-items: center; justify-content: center; }}
.kpi .value {{ font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; font-size: 2.1rem; color: var(--text); line-height: 1.2; margin: 8px 0 2px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
.kpi .foot {{ border-top: 1px solid var(--border); margin-top: 12px; padding-top: 9px; display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--muted); gap: 8px; flex-wrap: wrap; }}
.spark {{ display: flex; align-items: flex-end; gap: 3px; height: 34px; margin-left: auto; }}
.spark span {{ width: 6px; background: var(--accent); opacity: .85; border-radius: 2px; display: block; }}
.st-key-card_fee {{ background: linear-gradient(135deg, var(--surface), var(--warn-soft)); border-color: var(--warn); }}
.fee-title {{ font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; font-size: 1.5rem; color: var(--text); margin: 6px 0 8px; text-transform: capitalize; }}
.st-key-card_fee [data-testid="stPageLink-NavLink"] {{ justify-content: flex-end; }}
/* ---- pills and badges */
.pill, .badge {{ display: inline-flex; align-items: center; gap: 6px; font-size: 0.76rem; font-weight: 600; padding: 2px 10px; border-radius: 999px; border: 1px solid var(--border); background: var(--subtle); color: var(--muted); white-space: nowrap; }}
.pill.ok, .badge.ok {{ color: var(--ok-text); background: var(--ok-soft); border-color: transparent; }}
.pill.warn, .badge.warn {{ color: var(--warn-text); background: var(--warn-soft); border-color: transparent; }}
.pill.bad, .badge.fail {{ color: var(--bad-text); background: var(--bad-soft); border-color: transparent; }}
.pill.accent {{ color: var(--accent-text); background: var(--accent-soft); border-color: transparent; }}
.badge .ic-dot {{ width: 15px; height: 15px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: .65rem; color: #fff; }}
.badge .ic-dot b {{ color: #fff; font-weight: 700; }}
.badge.ok .ic-dot {{ background: var(--ok-text); }} .badge.warn .ic-dot {{ background: var(--warn-text); }} .badge.fail .ic-dot {{ background: var(--bad-text); }}
/* ---- tables */
.scroll {{ overflow-x: auto; }}
table.t {{ border-collapse: collapse; width: 100%; min-width: 520px; }}
table.t th {{ background: var(--subtle); color: var(--muted); font-size: 0.72rem; letter-spacing: .05em; text-transform: uppercase; font-weight: 600; text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--border); }}
table.t td {{ border-bottom: 1px solid var(--border); padding: 10px 12px; font-size: 0.9rem; vertical-align: top; color: var(--text); }}
table.t tr:last-child td {{ border-bottom: 0; }}
/* ---- theme rows */
.trows {{ min-width: 640px; }}
.tgrid {{ display: grid; grid-template-columns: 52px minmax(160px, 1.5fr) minmax(200px, 1.7fr) minmax(130px, 1fr) 24px; gap: 12px; align-items: center; padding: 11px 12px; }}
.thead {{ background: var(--subtle); border-radius: 8px; font-size: 0.72rem; letter-spacing: .05em; text-transform: uppercase; color: var(--muted); font-weight: 600; padding-top: 8px; padding-bottom: 8px; }}
details.trow {{ border-bottom: 1px solid var(--border); }}
details.trow:last-child {{ border-bottom: 0; }}
details.trow > summary {{ list-style: none; cursor: pointer; border-radius: 8px; }}
details.trow > summary::-webkit-details-marker {{ display: none; }}
details.trow > summary:hover {{ background: var(--subtle); }}
details.trow[open] .chev {{ transform: rotate(180deg); }}
.chev {{ color: var(--muted); transition: transform .15s; display: flex; }}
.rank {{ width: 26px; height: 26px; border-radius: 8px; background: var(--accent-soft); color: var(--accent-text); display: inline-flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.8rem; }}
.tname {{ display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: 0.92rem; color: var(--text); }}
.tname .cat {{ width: 28px; height: 28px; border-radius: 8px; background: var(--subtle); border: 1px solid var(--border); color: var(--muted); display: flex; align-items: center; justify-content: center; flex: none; }}
.tname small {{ display: block; font-weight: 500; color: var(--muted); font-size: 0.74rem; }}
.sev {{ display: flex; align-items: center; gap: 10px; }}
.sev .bar {{ flex: 1; height: 8px; border-radius: 999px; background: var(--bad-soft); overflow: hidden; min-width: 60px; }}
.sev .bar i {{ display: block; height: 100%; background: var(--bad); border-radius: 999px; }}
.sev b {{ min-width: 34px; text-align: right; font-weight: 600; }}
.drawer {{ padding: 4px 14px 14px 76px; display: grid; grid-template-columns: 1.6fr 1fr; gap: 16px; }}
@media (max-width: 700px) {{ .drawer {{ grid-template-columns: 1fr; padding-left: 14px; }} }}
.quote {{ border-left: 3px solid var(--accent); padding: 4px 12px; margin: 4px 0; color: var(--text); background: transparent; }}
.quote .meta {{ color: var(--muted); font-size: 0.8rem; margin-top: 4px; }}
.delta-card {{ border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; background: var(--subtle); font-size: 0.82rem; color: var(--muted); }}
.delta-card .big {{ font-size: 1.15rem; font-weight: 700; color: var(--text); }}
/* ---- pipeline */
.stage-list {{ display: flex; flex-direction: column; }}
.stage {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 2px; border-bottom: 1px solid var(--border); }}
.stage:last-child {{ border-bottom: 0; }}
.stage .nm {{ font-weight: 600; font-size: 0.9rem; color: var(--text); }}
.stage .meta {{ color: var(--muted); font-size: 0.78rem; }}
.stage .right {{ display: flex; align-items: center; gap: 12px; text-align: right; }}
.stage .when {{ color: var(--muted); font-size: 0.76rem; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.chips .pill {{ font-size: 0.8rem; padding: 4px 12px; }}
.st-key-card_pulse h1 {{ font-size: 1.3rem !important; margin: 0 0 6px !important; }}
.st-key-card_pulse h2 {{ font-size: 1.02rem !important; margin: 18px 0 4px !important; }}
.st-key-card_pulse p, .st-key-card_pulse li {{ font-size: 0.93rem; }}
.footer {{ text-align: center; color: var(--muted); font-size: 0.82rem; padding: 26px 0 6px; border-top: 1px solid var(--border); margin-top: 30px; }}
.crumb {{ margin-bottom: 4px; }}
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="base-input"] {{ background: var(--surface) !important; border-color: var(--border) !important; color: var(--text) !important; }}
[data-baseweb="select"] input, [data-baseweb="select"] span {{ color: var(--text) !important; }}
[data-baseweb="popover"] ul, [data-baseweb="menu"] {{ background: var(--surface) !important; color: var(--text) !important; }}
[data-testid="stExpander"] {{ border: 1px solid var(--border); border-radius: 10px; background: var(--surface); }}
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {{ background: var(--surface); color: var(--text); border-radius: 8px; }}
[data-testid="stCode"], pre {{ border-radius: 10px; }}
@media (max-width: 640px) {{
[data-testid="stMainBlockContainer"] {{ padding: 0.5rem 1rem 2rem; }}
.st-key-topbar {{ margin: 0 -1rem 14px; padding: 6px 1rem 6px 3.4rem; }}
.st-key-topbar [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap; gap: 0.25rem; }}
.st-key-topbar [data-testid="stColumn"] {{ min-width: 0 !important; width: auto !important; flex: 0 0 auto !important; }}
.st-key-topbar [data-testid="stColumn"]:first-child {{ flex: 1 1 auto !important; }}
.st-key-topbar [data-testid="stColumn"]:nth-child(5), .st-key-topbar [data-testid="stColumn"]:nth-child(6) {{ display: none !important; }}
.st-key-topbar button p, .st-key-topbar a p {{ display: none; }}
.ctx {{ display: none; }}
.kpi .value {{ font-size: 1.7rem; }}
}}
.kpi {{ margin-bottom: 12px; }}
</style>
"""


def inject_css() -> None:
    st.markdown(build_css(is_dark()), unsafe_allow_html=True)


def esc(value: object) -> str:
    """HTML-escape anything that comes from data (reviews are untrusted text)."""
    return html.escape(str(value))


class _Raw(str):
    """Marks trusted HTML (such as a badge) inside a table cell."""


def raw(html_text: str) -> _Raw:
    return _Raw(html_text)


def toast(message: str) -> None:
    """Non-blocking bottom-right notification."""
    st.toast(message)


def footer() -> None:
    st.markdown(f'<div class="footer">{esc(FOOTER)}</div>', unsafe_allow_html=True)


def pill(kind: str, text: str, with_icon: str | None = None) -> str:
    ic = icon(with_icon, 13) if with_icon else ""
    return f'<span class="pill {kind}">{ic}{esc(text)}</span>'


def badge(kind: str, word: str) -> str:
    """Status = icon + word. kind: ok | fail | warn."""
    mark = {"ok": "&#10003;", "fail": "&#10007;", "warn": "!"}[kind]
    return f'<span class="badge {kind}"><span class="ic-dot"><b>{mark}</b></span>{esc(word)}</span>'


def metric(label: str, value: object, note: str = "") -> str:
    extra = f'<div class="sub" style="font-size:.85rem">{esc(note)}</div>' if note else ""
    return f'<div class="kpi"><div class="label">{esc(label)}</div><div class="value">{esc(value)}</div>{extra}</div>'


def table(headers: list[str], rows: list[list[object]]) -> None:
    """Horizontally scrollable table (safe on small screens). Cell text is escaped."""
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c if isinstance(c, _Raw) else esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    st.markdown(f'<div class="card scroll"><table class="t"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>', unsafe_allow_html=True)


def card_container(key: str):
    """A white card that can hold Streamlit widgets. Keys must be unique per page."""
    return st.container(key=f"card_{key}")


def page_link(path: str, label: str, icon: str | None = None) -> None:
    """Link to another page; silently skipped if the page is not registered (for example in isolated tests)."""
    try:
        st.page_link(path, label=label, icon=icon)
    except Exception:  # noqa: BLE001 - navigation context missing
        return


def page_header(title: str, subtitle: str = "", pill_html: str = "", right_html: str = "", back: bool = True) -> None:
    """Title row. Every page except Overview gets a 'Back to Overview' link."""
    if back and title != "Overview":
        page_link("pages/1_Overview.py", "Back to Overview", ":material/arrow_back:")
    sub = f'<p class="sub">{esc(subtitle)}</p>' if subtitle else ""
    st.markdown(
        f'<div class="page-head"><div><div class="titlerow"><h1>{esc(title)}</h1>{pill_html}</div>{sub}</div><div>{right_html}</div></div>',
        unsafe_allow_html=True,
    )


def is_demo() -> bool:
    return config.get_demo_mode()


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


def relative_time(path: Path) -> str:
    """'3 hours ago' style text from a file's modification time."""
    if not path.exists():
        return "not produced"
    secs = max(0, (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).total_seconds())
    for limit, unit, div in ((60, "second", 1), (3600, "minute", 60), (86400, "hour", 3600), (86400 * 30, "day", 86400)):
        if secs < limit:
            n = max(1, int(secs // div))
            return f"{n} {unit}{'s' if n != 1 else ''} ago"
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
