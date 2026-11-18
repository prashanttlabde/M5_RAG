"""Implements architecture §10 Overview: run controls, KPIs, top 3 themes, pipeline status."""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import metrics
import streamlit as st
import ui

from src import config

ins = ui.load_json(config.INSIGHTS_JSON)
names = ui.theme_names()
product = config.get_product_config()

# ------------------------------------------------------------------ header
synced = all(p.exists() and p.stat().st_size for p in (config.REVIEWS_BALANCED_CSV, config.INSIGHTS_JSON, config.WEEKLY_PULSE_MD, config.FEE_EXPLAINER_MD))
right = ""
if ins:
    w = ins["window"]
    right = ui.pill("", f"{w['start']} to {w['end']}", "calendar")
ui.page_header(
    "Overview",
    "Weekly product pulse for ChatGPT on Google Play (India, English)",
    pill_html=ui.pill("ok", "Synced", "check") if synced else ui.pill("warn", "Incomplete"),
    right_html=right,
)

# ------------------------------------------------------------------ run pipeline (top of the page)
STEPS = [
    ("Collect reviews", "src.collect.clean", ":material/download:", config.REVIEWS_BALANCED_CSV, False),
    ("Analyse (AI)", "src.analyze", ":material/psychology:", config.INSIGHTS_JSON, True),
    ("Write pulse (AI)", "src.writer", ":material/edit_note:", config.WEEKLY_PULSE_MD, True),
    ("Build fee explainer (AI)", "src.rag", ":material/menu_book:", config.FEE_EXPLAINER_MD, True),
    ("Run checks", "src.checks", ":material/fact_check:", config.CHECKS_REPORT_MD, False),
]
paused = st.session_state.get("paused", False)
with ui.card_container("run"):
    status = ui.pill("bad", "Paused") if paused else (ui.pill("accent", "Demo mode") if ui.is_demo() else ui.pill("ok", "Ready to run"))
    st.markdown(
        f'<div class="card-head"><h3>Run pipeline</h3>{status}</div>'
        '<p class="sub" style="margin:-4px 0 6px">Collect reviews, analyse them, write the pulse and the fee explainer, then check everything. Steps marked (AI) call the language model.</p>',
        unsafe_allow_html=True,
    )
    if ui.is_demo():
        chips = "".join(
            ui.pill("ok" if path.exists() and path.stat().st_size else "warn", f"{label}: " + ("ready" if path.exists() and path.stat().st_size else "missing"))
            for label, _, _, path, _ in STEPS
        )
        st.markdown(f'<div class="chips">{chips}</div>', unsafe_allow_html=True)
        st.caption("Demo mode: results are loaded from saved files and run buttons are hidden. Set DEMO_MODE=false locally to run the steps.")
    else:
        cols = st.columns(len(STEPS))
        clicked = None
        for col, (label, module, icn, _, _) in zip(cols, STEPS, strict=True):
            if col.button(label, key=f"run_{module}", icon=icn, width="stretch", disabled=paused):
                clicked = (label, module)
        if paused:
            st.caption("The pipeline is stopped. Press Resume in the top bar to run steps again.")
        if clicked:
            label, module = clicked
            with st.spinner(f"Running {label}..."):
                out = subprocess.run([sys.executable, "-m", module], cwd=config.ROOT, capture_output=True, text=True,
                                     env={**os.environ, "PYTHONPATH": str(config.ROOT)}, check=False)
            st.markdown(ui.badge("ok", f"{label} finished") if out.returncode == 0 else ui.badge("fail", f"{label} stopped with an error"), unsafe_allow_html=True)
            st.code("\n".join((out.stdout + out.stderr).strip().splitlines()[-12:]) or "(no output)", language=None)
            if out.returncode == 0:
                st.cache_data.clear()
                ui.toast(f"{label} finished.")

if ins is None:
    ui.empty_state("The insights file", "Run the analysis steps first (make analyze).")
    st.stop()

# ------------------------------------------------------------------ KPI row
w = ins["window"]
stats = {t["theme_id"]: t for t in ins["themes"]}
collected = metrics.collected_count()
weekly = metrics.weekly_counts()
fee = ins["fee"]
labels = metrics.read_csv(config.FEE_LABELS_CSV)
topic_confused = int(((labels["stance"] == "confused") & (labels["fee_topic"] == fee["topic"])).sum()) if labels is not None and fee["topic"] else 0

c1, c2, c3 = st.columns(3)
share_tag = ui.pill("ok", f"{round(100 * w['review_count'] / collected)}% of {collected:,} collected") if collected else ""
c1.markdown(
    f'<div class="kpi"><div class="top"><span class="label">Reviews analysed</span><span class="badge-ic">{ui.icon("chat")}</span></div>'
    f'<div class="value num">{w["review_count"]:,}{share_tag}</div>'
    f'<div class="foot"><span class="num">{ui.esc(w["start"])} to {ui.esc(w["end"])}</span><span class="num">~{round(w["review_count"] / w["weeks"])} / wk</span></div></div>',
    unsafe_allow_html=True,
)
bars = ""
gaps = 0
if weekly is not None and len(weekly):
    top = max(weekly.max(), 1)
    bars = "".join(f'<span title="{ui.esc(d)}: {int(n)} reviews" style="height:{max(8, round(100 * n / top))}%"></span>' for d, n in weekly.items())
    gaps = metrics.weeks_gap_count(list(weekly.index))
cont = ui.esc("Continuous" if gaps == 0 else f"{gaps} missing week{'s' if gaps != 1 else ''}")
c2.markdown(
    f'<div class="kpi"><div class="top"><span class="label">Weeks covered</span><span class="badge-ic">{ui.icon("calendar")}</span></div>'
    f'<div class="value num">{w["weeks"]}<div class="spark">{bars}</div></div>'
    f'<div class="foot"><span>Weekly cohorts tracked</span><span>{cont}</span></div></div>',
    unsafe_allow_html=True,
)
with c3:
    with ui.card_container("fee"):
        topic = (fee["topic"] or "none").replace("_", " ")
        st.markdown(
            f'<div class="card-head" style="margin-bottom:0"><span class="label" style="font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;font-weight:600;color:var(--muted)">Identified fee issue</span>'
            f'<span class="badge-ic" style="width:28px;height:28px;border-radius:8px;background:var(--warn-soft);color:var(--warn-text);display:flex;align-items:center;justify-content:center">{ui.icon("alert")}</span></div>'
            f'<div class="fee-title">{ui.esc(topic)}</div>'
            f'<div class="chips">{ui.pill("warn", f"{topic_confused} confused about this topic")}{ui.pill("", f"{fee["confused"]} confused in all fee topics")}</div>',
            unsafe_allow_html=True,
        )
        ui.page_link("pages/4_Fee_Explainer.py", "Fee Explainer", ":material/arrow_forward:")

# ------------------------------------------------------------------ top 3 themes
ICON_BY_KEYWORD = [("accur", "target"), ("limit", "lock"), ("paywall", "lock"), ("perform", "zap"), ("ui", "layout"), ("educ", "book")]


def theme_icon(name: str) -> str:
    low = name.lower()
    return next((ic for key, ic in ICON_BY_KEYWORD if key in low), "tag")


trend = {t["theme_id"]: t for t in ins["trend"]}
quotes = {q["theme_id"]: q for q in ins["quotes"]}
rows = ""
for i, tid in enumerate(ins["top3"]):
    s, name = stats[tid], names.get(tid, tid)
    share = 100 * s["low_star_share"]
    t = trend.get(tid)
    if t:
        change = (100 * (t["last4"] - t["prev4"]) / t["prev4"]) if t["prev4"] else 0.0
        delta = (f'<div class="big num">{change:+.0f}%</div>Last 4 weeks vs the 4 before<br><span class="num">{t["last4"]} vs {t["prev4"]} reviews</span>')
    else:
        delta = "No trend data."
    q = quotes.get(tid)
    quote_html = (f'<div class="quote">"{ui.esc(q["excerpt"])}"<div class="meta">{ui.esc(q["rating"])} star, {ui.esc(q["date"])}</div></div>' if q else "")
    rows += (
        f'<details class="trow"><summary class="tgrid"><span><span class="rank">{i + 1}</span></span>'
        f'<span class="tname"><span class="cat">{ui.icon(theme_icon(name))}</span><span>{ui.esc(name)}<small class="num">{share:.0f}% rated 1-2 star</small></span></span>'
        f'<span class="sev"><span class="bar"><i style="width:{share:.1f}%"></i></span><b class="num">{s["low_star"]}</b></span>'
        f'<span class="num">{s["total"]} {ui.pill("", f"{100 * s["total"] / w["review_count"]:.1f}%")}</span>'
        f'<span class="chev">{ui.icon("chevron")}</span></summary>'
        f'<div class="drawer"><div>{quote_html}</div><div class="delta-card">{delta}</div></div></details>'
    )
st.markdown(
    '<div class="card scroll" id="top-3-themes"><div class="card-head"><h3>Top 3 themes</h3>'
    f'<a href="#top-3-themes" title="Link to this section">{ui.icon("link")}</a></div><div class="trows">'
    '<div class="tgrid thead"><span>Rank</span><span>Theme</span><span>1-2 star reviews</span><span>All reviews</span><span></span></div>'
    f'{rows}</div></div>',
    unsafe_allow_html=True,
)
st.caption("Click a row to see a real quote and the 4-week trend.")

# ------------------------------------------------------------------ pipeline status
def count_rows(path: Path) -> int | None:
    df = metrics.read_csv(path)
    return None if df is None else len(df)


words = len(ui.load_text(config.WEEKLY_PULSE_MD).split()) if ui.load_text(config.WEEKLY_PULSE_MD) else 0
expl = ui.load_json(config.FEE_EXPLAINER_JSON) or {}
payload = ui.load_json(config.APPROVAL_PAYLOAD_JSON) or {}
summary = metrics.checks_summary()
themes_file = ui.load_json(config.THEMES_JSON) or []
stages = [
    ("Reviews (balanced)", config.REVIEWS_BALANCED_CSV, f"{count_rows(config.REVIEWS_BALANCED_CSV) or 0:,} reviews"),
    ("Themes", config.THEMES_JSON, f"{len(themes_file)} themes"),
    ("Theme assignments", config.ASSIGNMENTS_CSV, f"{count_rows(config.ASSIGNMENTS_CSV) or 0:,} assignments"),
    ("Insights", config.INSIGHTS_JSON, f"{len(ins['top3'])} themes ranked"),
    ("Weekly pulse", config.WEEKLY_PULSE_MD, f"{words} words"),
    ("Fee explainer", config.FEE_EXPLAINER_MD, f"{len(expl.get('bullets', []))} verified bullets"),
    ("Approval payload", config.APPROVAL_PAYLOAD_JSON, f"fingerprint {str(payload.get('hash', ''))[:8]}"),
    ("Checks report", config.CHECKS_REPORT_MD, f"{summary[0]} of {summary[1]} passed" if summary else "not run"),
]
ready = sum(1 for _, p, _ in stages if p.exists() and p.stat().st_size)
body = "".join(
    f'<div class="stage"><div><div class="nm">{ui.esc(name)}</div><div class="meta">{ui.esc(meta)}</div></div>'
    f'<div class="right"><span class="when">Updated {ui.esc(ui.relative_time(p))}</span>{ui.badge("ok", "Ready") if p.exists() and p.stat().st_size else ui.badge("warn", "Missing")}</div></div>'
    for name, p, meta in stages
)
head_status = ui.pill("ok", f"All {len(stages)} stages verified", "check") if ready == len(stages) else ui.pill("warn", f"{ready} of {len(stages)} stages ready")
log = ui.load_text(config.PUBLISH_LOG_JSONL)
done = bool(log) and '"state": "DONE"' in log
publish = ui.badge("ok", "Published to the Doc and Gmail draft") if done else ui.badge("warn", "Not published yet")
st.markdown(
    f'<div class="card"><div class="card-head"><h3>Pipeline status</h3>{head_status}</div><div class="stage-list">{body}</div>'
    f'<div class="stage"><div><div class="nm">Publishing</div><div class="meta">Doc entry and Gmail draft (never sent)</div></div><div class="right">{publish}</div></div></div>',
    unsafe_allow_html=True,
)
