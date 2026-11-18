"""Implements architecture §10 app shell: custom sidebar navigation and the sticky top bar."""

from __future__ import annotations

import metrics
import pandas as pd
import streamlit as st
import ui

from src import config

PAGES = [
    ("Overview", "pages/1_Overview.py", None, ":material/space_dashboard:"),
    ("Insights", "pages/2_Insights.py", "insights", ":material/monitoring:"),
    ("Weekly Pulse", "pages/3_Weekly_Pulse.py", "weekly-pulse", ":material/summarize:"),
    ("Fee Explainer", "pages/4_Fee_Explainer.py", "fee-explainer", ":material/receipt_long:"),
    ("Approve and Publish", "pages/5_Approve_and_Publish.py", "approve", ":material/verified:"),
    ("Checks", "pages/6_Checks.py", "checks", ":material/fact_check:"),
    ("About", "pages/7_About.py", "about", ":material/info:"),
]
EDIT_URL = f"{ui.REPO_URL}/edit/main/config/sources.yaml"
DOCS_URL = f"{ui.REPO_URL}#readme"


def build_pages() -> list:
    """Overview is the default page (served at '/'); the rest get readable URLs."""
    out = []
    for title, path, url_path, _ in PAGES:
        if url_path is None:
            out.append(st.Page(path, title=title, default=True))
        else:
            out.append(st.Page(path, title=title, url_path=url_path))
    return out


# ------------------------------------------------------------------ callbacks (toasts are non-blocking)
def _toggle_stop() -> None:
    st.session_state["paused"] = not st.session_state.get("paused", False)
    ui.toast("Pipeline stopped. Run buttons are paused." if st.session_state["paused"] else "Pipeline resumed.")


def _toggle_star() -> None:
    st.session_state["starred"] = not st.session_state.get("starred", False)
    ui.toast("Starred for this session." if st.session_state["starred"] else "Removed from starred.")


def _toggle_theme() -> None:
    st.session_state["dark"] = not st.session_state.get("dark", False)
    ui.toast("Dark theme on." if st.session_state["dark"] else "Light theme on.")


def _open_share() -> None:
    st.session_state["show_share"] = True
    ui.toast("Share link ready to copy.")


def _clear_cache() -> None:
    st.cache_data.clear()
    ui.toast("Local cache cleared. Data reloaded from files.")


@st.dialog("Share this dashboard")
def _share_dialog() -> None:
    try:
        url = st.context.url
    except Exception:  # noqa: BLE001 - not available in every runtime
        url = ui.REPO_URL
    st.write("Copy the link with the copy icon:")
    st.code(url, language=None)
    st.caption("Anyone with the link sees the saved results. Approving and publishing still needs the approver password.")


# ------------------------------------------------------------------ sidebar
def render_sidebar() -> None:
    ins = ui.load_json(config.INSIGHTS_JSON) or {}
    summary = metrics.checks_summary()
    artifacts = [config.REVIEWS_BALANCED_CSV, config.THEMES_JSON, config.ASSIGNMENTS_CSV, config.INSIGHTS_JSON,
                 config.WEEKLY_PULSE_MD, config.FEE_EXPLAINER_MD]
    healthy = all(p.exists() and p.stat().st_size for p in artifacts) and (summary is None or summary[0] == summary[1])
    mode = "Demo mode" if ui.is_demo() else "Local mode"
    with st.sidebar:
        st.markdown(
            f'<div class="brand"><div class="logo">{ui.icon("pulse", 18)}</div><div><div class="title">Review Pulse</div>'
            f'<div class="mode"><span class="dot"></span>{ui.esc(mode)}</div></div></div><div class="nav-label">Workspace</div>',
            unsafe_allow_html=True,
        )
        for title, path, _, icon in PAGES:
            st.page_link(path, label=title, icon=icon)
        w = ins.get("window", {})
        meta = f"{w.get('weeks', 0)} weekly cohorts, {w.get('review_count', 0):,} reviews" if w else "No data yet"
        word = ui.pill("ok", "Healthy") if healthy else ui.pill("warn", "Needs attention")
        st.markdown(
            f'<div class="health"><div class="row"><span>Pipeline engine</span>{word}</div><div class="meta">{ui.esc(meta)}</div></div>',
            unsafe_allow_html=True,
        )
        st.link_button("Manage app", "https://share.streamlit.io/", icon=":material/settings:", width="stretch", key="manage_app")
        confused = (ins.get("fee") or {}).get("confused")
        if confused is not None:  # numeric badge on the Fee Explainer link, loaded from insights.json
            st.markdown(
                '<style>[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][href$="fee-explainer"]::after'
                f'{{content:"{int(confused)}";margin-left:auto;font-size:.7rem;font-weight:600;padding:0 8px;border-radius:999px;'
                'background:var(--accent-soft);color:var(--accent-text);font-variant-numeric:tabular-nums}</style>',
                unsafe_allow_html=True,
            )


# ------------------------------------------------------------------ top bar
def _snapshot_csv() -> str | None:
    ins = ui.load_json(config.INSIGHTS_JSON)
    if not ins:
        return None
    names = ui.theme_names()
    rows = [{"theme": names.get(t["theme_id"], t["theme_id"]), "all_reviews": t["total"], "low_star_reviews": t["low_star"],
             "low_star_share": t["low_star_share"], "in_top3": t["theme_id"] in ins["top3"]} for t in ins["themes"]]
    return pd.DataFrame(rows).to_csv(index=False)


def render_topbar() -> None:
    product = config.get_product_config()
    country = {"in": "India"}.get(str(product.get("country", "")).lower(), str(product.get("country", "")).upper())
    lang = {"en": "English"}.get(str(product.get("lang", "")).lower(), str(product.get("lang", "")).upper())
    paused, starred, dark = (st.session_state.get(k, False) for k in ("paused", "starred", "dark"))
    with st.container(key="topbar"):
        cols = st.columns([4.4, 1.15, 1.2, 0.55, 0.55, 1.3, 0.55, 0.55], vertical_alignment="center")
        cols[0].markdown(
            f'<div class="ctx"><span class="app">ChatGPT</span>{ui.pill("", f"Google Play | {country}, {lang}")}</div>',
            unsafe_allow_html=True,
        )
        cols[1].button("Resume" if paused else "Stop", key="tb_stop", icon=":material/play_arrow:" if paused else ":material/stop_circle:",
                       on_click=_toggle_stop, width="stretch")
        cols[2].button("Share", key="tb_share", type="primary", icon=":material/ios_share:", on_click=_open_share, width="stretch")
        cols[3].button(" ", key="tb_star", icon=":material/star:" if starred else ":material/star_border:", help="Star", on_click=_toggle_star)
        cols[4].link_button(" ", EDIT_URL, icon=":material/edit:", help="Edit the source list on GitHub")
        cols[5].link_button("GitHub", ui.REPO_URL, icon=":material/code:", help="Open the repository", width="stretch")
        cols[6].button(" ", key="tb_theme", icon=":material/light_mode:" if dark else ":material/dark_mode:",
                       help="Switch to light theme" if dark else "Switch to dark theme", on_click=_toggle_theme)
        with cols[7].popover(" ", icon=":material/more_vert:", help="More"):
            csv = _snapshot_csv()
            st.download_button("Export CSV snapshot", csv or "", file_name="review_pulse_snapshot.csv", mime="text/csv",
                               disabled=csv is None, key="tb_export", on_click=lambda: ui.toast("CSV snapshot exported."),
                               width="stretch", icon=":material/download:")
            st.button("Re-run local cache", key="tb_cache", on_click=_clear_cache, width="stretch", icon=":material/refresh:")
            st.link_button("Pipeline documentation", DOCS_URL, width="stretch", icon=":material/menu_book:")
    if st.session_state.pop("show_share", False):
        _share_dialog()


__all__ = ["build_pages", "render_sidebar", "render_topbar"]
