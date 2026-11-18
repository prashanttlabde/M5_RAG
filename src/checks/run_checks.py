"""Implements architecture §12 checks (PRD FR27; all INV-*): rule-based, NO AI.

Each check is independent, returns PASS or FAIL with a short detail, and the run continues after
failures. Numbers are recomputed from the CSVs here, not read back from the pipeline's own helpers.
Writes outputs/checks_report.md.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import yaml

from src import config
from src.checks.bad_inputs import find_pii, run_bad_input_cases, validate_reviews_csv

Result = tuple[bool, str]  # (passed, detail)
CHECKS: list[tuple[str, str, Callable[[], Result]]] = []

BANNED = ("best", "worst", "terrible", "awful", "great", "amazing", "unfair", "scam", "rip-off", "ripoff",
          "overpriced", "expensive", "cheap", "outrageous", "unfortunately", "fortunately", "obviously",
          "clearly", "recommend", "should", "must")
ID_TAG = re.compile(r"\s*\[([A-Za-z0-9_\-]+)\]\s*[.!?]?\s*$")


def check(group: str, name: str):
    def deco(fn: Callable[[], Result]):
        CHECKS.append((group, name, fn))
        return fn
    return deco


# ---------------------------------------------------------------- shared loaders
def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _joined() -> pd.DataFrame:
    reviews = pd.read_csv(config.REVIEWS_BALANCED_CSV)
    return reviews.merge(pd.read_csv(config.ASSIGNMENTS_CSV), on="review_id", how="left")


def _source_ids() -> dict[str, dict]:
    data = yaml.safe_load(config.SOURCES_YAML.read_text(encoding="utf-8")) or {}
    return {s["source_id"]: s for s in data.get("sources", [])}


def _numbers(text: str) -> set[str]:
    return {n.rstrip(".,").replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


# ---------------------------------------------------------------- DATA
@check("Data", "Review files have the required columns, valid ratings and no PII (both CSVs)")
def _data_files() -> Result:
    problems = []
    for path in (config.REVIEWS_FULL_CSV, config.REVIEWS_BALANCED_CSV):
        issues = validate_reviews_csv(path)
        problems += [f"{path.name}: {i}" for i in issues]
    return (not problems, "; ".join(problems) or "both files pass the validator")


@check("Data", "8 to 12 distinct weeks; exact review counts stated")
def _data_weeks() -> Result:
    full, bal = pd.read_csv(config.REVIEWS_FULL_CSV), pd.read_csv(config.REVIEWS_BALANCED_CSV)
    weeks = full["week_start"].nunique()
    return 8 <= weeks <= 12, f"{weeks} weeks; full={len(full)}, balanced={len(bal)}"


@check("Data", "Balanced file has at most 200 reviews per week")
def _data_balance() -> Result:
    biggest = int(pd.read_csv(config.REVIEWS_BALANCED_CSV).groupby("week_start").size().max())
    return biggest <= 200, f"largest week has {biggest}"


@check("Data", "No reviewer name column in either CSV (INV-6)")
def _data_names() -> Result:
    cols = set(pd.read_csv(config.REVIEWS_FULL_CSV, nrows=1).columns) | set(pd.read_csv(config.REVIEWS_BALANCED_CSV, nrows=1).columns)
    extra = sorted(cols - {"review_id", "date", "week_start", "rating", "text"})
    return not extra, f"unexpected columns: {extra}" if extra else "columns are review_id, date, week_start, rating, text"


@check("Data", "Balanced reviews are a subset of the full reviews")
def _data_subset() -> Result:
    full = set(pd.read_csv(config.REVIEWS_FULL_CSV)["review_id"])
    bal = set(pd.read_csv(config.REVIEWS_BALANCED_CSV)["review_id"])
    return bal <= full, f"{len(bal - full)} balanced reviews missing from full"


# ---------------------------------------------------------------- THEMES
@check("Themes", "At most 5 themes with unique ids")
def _themes_count() -> Result:
    themes = _json(config.THEMES_JSON)
    ids = [t["theme_id"] for t in themes]
    return 1 <= len(themes) <= 5 and len(set(ids)) == len(ids), f"{len(themes)} themes"


@check("Themes", "Every balanced review is assigned to exactly one valid theme")
def _themes_assignment() -> Result:
    themes = {t["theme_id"] for t in _json(config.THEMES_JSON)}
    a = pd.read_csv(config.ASSIGNMENTS_CSV)
    bal = set(pd.read_csv(config.REVIEWS_BALANCED_CSV)["review_id"])
    ok = set(a["review_id"]) == bal and a["review_id"].is_unique and set(a["theme_id"]) <= themes
    return ok, f"{len(a)} assignments for {len(bal)} reviews"


@check("Themes", "Per-theme totals and 1-2 star counts in insights.json match a fresh recount")
def _themes_counts() -> Result:
    ins, j = _json(config.INSIGHTS_JSON), _joined()
    bad = []
    for t in ins["themes"]:
        sub = j[j["theme_id"] == t["theme_id"]]
        total, low = len(sub), int((sub["rating"] <= 2).sum())
        if (total, low) != (t["total"], t["low_star"]):
            bad.append(f"{t['name']}: file {t['total']}/{t['low_star']} vs recount {total}/{low}")
    return not bad, "; ".join(bad) or "all counts match"


@check("Themes", "Top 3 follows the written rule (1-2 star count, then share, then name), never volume")
def _themes_rank() -> Result:
    ins, j = _json(config.INSIGHTS_JSON), _joined()
    names = {t["theme_id"]: t["name"] for t in _json(config.THEMES_JSON)}
    rows = []
    for tid, name in names.items():
        sub = j[j["theme_id"] == tid]
        low = int((sub["rating"] <= 2).sum())
        rows.append((-low, -(low / len(sub) if len(sub) else 0), name.lower(), tid))
    expected = [r[3] for r in sorted(rows)[:3]]
    return ins["top3"] == expected, f"file {ins['top3']} vs recomputed {expected}"


@check("Themes", "Ranking rule text exists in config and matches insights.json")
def _themes_rule() -> Result:
    rule = yaml.safe_load(config.PRODUCT_YAML.read_text(encoding="utf-8")).get("ranking_rule", "")
    return bool(rule) and rule == _json(config.INSIGHTS_JSON)["ranking_rule"], rule or "no ranking_rule in config"


# ---------------------------------------------------------------- QUOTES
@check("Quotes", "3 quotes, one per top theme, each from a real review of that theme")
def _quotes_real() -> Result:
    ins, j = _json(config.INSIGHTS_JSON), _joined().set_index("review_id")
    quotes, bad = ins["quotes"], []
    if sorted(q["theme_id"] for q in quotes) != sorted(ins["top3"]):
        bad.append("quotes do not cover the top 3 themes")
    for q in quotes:
        if q["review_id"] not in j.index:
            bad.append(f"{q['review_id']} not in CSV")
        elif j.loc[q["review_id"], "theme_id"] != q["theme_id"]:
            bad.append(f"{q['review_id']} belongs to another theme")
    return not bad, "; ".join(bad) or f"{len(quotes)} quotes verified"


@check("Quotes", "Every quote excerpt is a verbatim substring of the real review (INV-2), 25 words or fewer")
def _quotes_verbatim() -> Result:
    full = pd.read_csv(config.REVIEWS_FULL_CSV).set_index("review_id")
    bad = []
    for q in _json(config.INSIGHTS_JSON)["quotes"]:
        text = str(full.loc[q["review_id"], "text"]) if q["review_id"] in full.index else ""
        if q["excerpt"] not in text or len(q["excerpt"].split()) > 25:
            bad.append(q["review_id"])
    return not bad, f"not verbatim or too long: {bad}" if bad else "all excerpts are exact substrings"


# ---------------------------------------------------------------- PULSE
def _pulse_text() -> str:
    return config.WEEKLY_PULSE_MD.read_text(encoding="utf-8")


@check("Pulse", "Pulse is at most 250 words (INV-9)")
def _pulse_words() -> Result:
    n = len(_pulse_text().split())
    return n <= 250, f"{n} words"


@check("Pulse", "Pulse has all four sections and exactly 3 action ideas, each tied to a quote")
def _pulse_sections() -> Result:
    t = _pulse_text()
    needed = ["## Summary of top themes", "## Supporting user quotes", "## Key observation", "## 3 action ideas"]
    missing = [h for h in needed if h not in t]
    actions = t.split("## 3 action ideas")[-1].strip().splitlines()
    actions = [a for a in actions if re.match(r"\d\.", a)]
    ok = not missing and len(actions) == 3 and all(re.search(r"\(Quote [123]\)", a) for a in actions)
    return ok, f"missing: {missing}; actions: {len(actions)}" if not ok else "4 sections, 3 actions with quote links"


@check("Pulse", "Every number in the pulse comes from computed data (INV-1)")
def _pulse_numbers() -> Result:
    ins = _json(config.INSIGHTS_JSON)
    labels = pd.read_csv(config.FEE_LABELS_CSV)
    allowed = {str(ins["window"]["review_count"]), str(ins["window"]["weeks"]), "1", "2", "3", "4"}
    for key in ("start", "end"):
        allowed |= _numbers(ins["window"][key])
    stats = {t["theme_id"]: t for t in ins["themes"]}
    for tid in ins["top3"]:
        s = stats[tid]
        allowed |= {str(s["total"]), str(s["low_star"]), str(round(100 * s["low_star_share"]))}
    for tr in ins["trend"]:
        allowed |= {str(tr["prev4"]), str(tr["last4"])}
    topic = ins["fee"]["topic"]
    allowed |= {str(ins["fee"]["money_reviews"]),
                str(int(((labels["stance"] == "confused") & (labels["fee_topic"] == topic)).sum()))}
    lines, skip = [], False
    for line in _pulse_text().splitlines():
        if line.startswith("## "):
            skip = line.startswith("## Supporting user quotes")  # quotes are verbatim review text, checked elsewhere
        if not skip:
            lines.append(line)
    stray = sorted(n for n in _numbers("\n".join(lines)) if n not in allowed)
    return not stray, f"numbers not traceable to computed data: {stray}" if stray else "all numbers traced to computed data"


@check("Pulse", "Quotes shown in the pulse are real review text")
def _pulse_quotes() -> Result:
    corpus = "\n".join(pd.read_csv(config.REVIEWS_FULL_CSV)["text"].astype(str))
    section = _pulse_text().split("## Supporting user quotes")[1].split("## ")[0]
    quotes = re.findall(r'^\d\. "(.+)" \(', section, re.MULTILINE)
    bad = [q for q in quotes if q.rstrip("…") not in corpus]
    return len(quotes) == 3 and not bad, f"{len(quotes)} quotes, {len(bad)} not found in reviews"


# ---------------------------------------------------------------- EXPLAINER
def _explainer() -> tuple[dict, list[str], str]:
    meta = _json(config.FEE_EXPLAINER_JSON)
    md = config.FEE_EXPLAINER_MD.read_text(encoding="utf-8")
    bullets = [line[2:].strip() for line in md.splitlines() if line.startswith("- ")]
    return meta, bullets, md


@check("Explainer", "At most 6 bullets; status ok; zero fact-check rejections")
def _expl_count() -> Result:
    meta, bullets, _ = _explainer()
    ok = len(bullets) <= 6 and meta["status"] == "ok" and not meta["rejected"]
    return ok, f"{len(bullets)} bullets, status {meta['status']}, {len(meta['rejected'])} rejected"


@check("Explainer", "Exactly 2 official links, both from sources.yaml, plus a Last checked date")
def _expl_links() -> Result:
    _, _, md = _explainer()
    urls = re.findall(r"\]\((https?://[^)]+)\)", md)
    official = {s["url"] for s in _source_ids().values()}
    date = re.search(r"Last checked: (\d{4}-\d{2}-\d{2})", md)
    ok = len(urls) == 2 and set(urls) <= official and date is not None
    return ok, f"{len(urls)} links, all official: {set(urls) <= official}, Last checked: {date.group(1) if date else 'MISSING'}"


@check("Explainer", "Each bullet cites a known source_id and uses no opinion or advice words")
def _expl_cites() -> Result:
    _, bullets, _ = _explainer()
    known, bad = set(_source_ids()), []
    for b in bullets:
        m = ID_TAG.search(b)
        words = set(re.findall(r"[a-z][a-z\-]*", ID_TAG.sub("", b).lower()))
        if not m or m.group(1) not in known or words & set(BANNED):
            bad.append(b[:60])
    return not bad, f"problem bullets: {bad}" if bad else f"{len(bullets)} bullets cite known sources"


@check("Explainer", "Every number in each bullet appears in its cited chunk (INV-3)")
def _expl_numbers() -> Result:
    meta, _, _ = _explainer()
    chunks = {}
    for line in config.CHUNKS_JSONL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            c = json.loads(line)
            chunks[c["chunk_id"]] = c
    bad = []
    for b in meta["bullets"]:
        chunk = chunks.get(b["chunk_id"])
        text = ID_TAG.sub("", b["text"])
        cited = (ID_TAG.search(b["text"]) or [None, None])[1]
        if chunk is None:
            bad.append(f"{b['chunk_id']} no longer exists in chunks.jsonl")
        elif chunk["source_id"] != cited or not _numbers(text) <= _numbers(chunk["text"]):
            bad.append(f"{b['chunk_id']}: citation or numbers not supported by the chunk")
    return not bad, "; ".join(bad) or "numbers and citations match their chunks"


@check("Explainer", "Explainer is not older than the chunk set it was built from")
def _expl_fresh() -> Result:
    newest_input = max(config.CHUNKS_JSONL.stat().st_mtime, config.SOURCES_YAML.stat().st_mtime)
    stale = config.FEE_EXPLAINER_JSON.stat().st_mtime < newest_input
    return not stale, "explainer was generated before the latest sources/chunks; re-run `make rag`" if stale else "up to date"


# ---------------------------------------------------------------- SAFETY
def _git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], cwd=config.ROOT, capture_output=True, text=True, check=False)
    return [line for line in out.stdout.splitlines() if line]


def _tracked_text_files() -> list[Path]:
    files = []
    for rel in _git("ls-files"):
        p = config.ROOT / rel
        if p.is_file() and p.stat().st_size < 2_000_000 and p.suffix not in {".png", ".jpg", ".pdf"}:
            files.append(p)
    return files


@check("Safety", ".env is gitignored and not tracked (INV-7)")
def _safe_env() -> Result:
    tracked = [f for f in _git("ls-files") if f == ".env" or f.endswith("/.env")]
    ignored = bool(_git("check-ignore", ".env"))
    return not tracked and ignored, f"tracked: {tracked}; ignored: {ignored}"


@check("Safety", "No API keys or tokens in any tracked file (INV-7)")
def _safe_secrets() -> Result:
    secrets = []
    env = config.ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            k, _, v = line.partition("=")
            if k in {"GROQ_API_KEY", "N8N_MCP_TOKEN", "APPROVER_PASSWORD"} and len(v.strip()) >= 8:
                secrets.append(v.strip())
    pattern = re.compile(r"gsk_[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._\-]{24,}")
    hits = []
    for p in _tracked_text_files():
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if pattern.search(text) or any(s in text for s in secrets):
            hits.append(str(p.relative_to(config.ROOT)))
    return not hits, f"possible secrets in: {hits}" if hits else f"{len(_tracked_text_files())} tracked files scanned"


@check("Safety", "No personal data (email or phone) in the pulse, explainer, payload or email draft (INV-6)")
def _safe_pii() -> Result:
    bad = [p.name for p in (config.WEEKLY_PULSE_MD, config.FEE_EXPLAINER_MD, config.APPROVAL_PAYLOAD_JSON, config.EMAIL_DRAFT_TXT)
           if p.exists() and find_pii(p.read_text(encoding="utf-8"))]
    return not bad, f"personal data found in: {bad}" if bad else "none found"


@check("Safety", "No send tool anywhere: workflow export, code and publish log (INV-5)")
def _safe_nosend() -> Result:
    problems = []
    export = config.ROOT / "n8n" / "workflow.export.json"
    if export.exists() and export.stat().st_size:
        data = _json(export)
        wf = data[0] if isinstance(data, list) else data
        for n in wf.get("nodes", []):
            p = n.get("parameters", {})
            label = f"{n['name']} {n['type']} {p.get('operation', '')} {p.get('resource', '')}".lower()
            if "send" in label.replace("sendto", ""):
                problems.append(f"node '{n['name']}' looks like a send action")
            if n["type"].endswith("gmailTool") and p.get("resource") != "draft":
                problems.append(f"Gmail node '{n['name']}' is not Draft")
    code_hits = []
    for p in (config.ROOT / "src").rglob("*.py"):
        if "checks" in p.parts:
            continue
        if re.search(r"""["']\w*send\w*["']\s*[,)]|\bdef \w*send\w*\(|\bsend_\w+\(""", p.read_text(encoding="utf-8"), re.IGNORECASE):
            code_hits.append(p.name)
    problems += [f"send-like code in {c}" for c in code_hits]
    if config.PUBLISH_LOG_JSONL.exists():
        for line in config.PUBLISH_LOG_JSONL.read_text().splitlines():
            if line.strip() and "send" in str(json.loads(line).get("tool") or "").lower():
                problems.append("publish log shows a send-like tool call")
                break
    return not problems, "; ".join(problems) or "no send tool in the workflow, code or log"


@check("Safety", "Approval payload: exactly six Doc fields and the hash recomputes (INV-4)")
def _safe_payload() -> Result:
    p = _json(config.APPROVAL_PAYLOAD_JSON)
    fields = ["date", "top_themes", "weekly_pulse", "identified_fee_issue", "explanation_bullets", "source_links"]
    core = {k: p[k] for k in ("doc_entry", "email_subject", "email_body")}
    digest = hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    ok = list(p["doc_entry"]) == fields and digest == p["hash"] and p["email_subject"].startswith("Weekly Product Pulse + Customer Clarification - ")
    return ok, f"fields ok: {list(p['doc_entry']) == fields}; hash matches: {digest == p['hash']}"


@check("Safety", "Publish log is valid JSON lines and every finished run was verified before the email draft")
def _safe_log() -> Result:
    if not config.PUBLISH_LOG_JSONL.exists() or not config.PUBLISH_LOG_JSONL.read_text().strip():
        return True, "no publish yet (nothing to check)"
    rows = [json.loads(line) for line in config.PUBLISH_LOG_JSONL.read_text().splitlines() if line.strip()]
    order, bad = {}, []
    for r in rows:
        if r["ok"]:
            order.setdefault(r["hash"], []).append(r["state"])
    for h, states in order.items():
        if "EMAIL_DRAFTED" in states and not ("DOC_VERIFIED" in states and states.index("DOC_VERIFIED") < states.index("EMAIL_DRAFTED")):
            bad.append(h[:8])
    return not bad, f"draft created before doc verification for: {bad}" if bad else f"{len(rows)} log lines consistent"


@check("Safety", "Stack rule: no LangChain, vector DB, ORM or auth library in requirements.txt")
def _safe_stack() -> Result:
    reqs = (config.ROOT / "requirements.txt").read_text().lower()
    banned = [b for b in ("langchain", "chromadb", "faiss", "pinecone", "sqlalchemy", "django", "authlib", "flask-login") if b in reqs]
    return not banned, f"banned packages: {banned}" if banned else "requirements match the fixed stack"


@check("Safety", "This checks script makes no LLM call (imports no llm or groq module)")
def _safe_no_llm() -> Result:
    bad = []
    for p in (config.ROOT / "src" / "checks").glob("*.py"):
        if re.search(r"^\s*(from|import)\s+(src\.llm|groq)\b|from src import .*\bllm\b", p.read_text(encoding="utf-8"), re.MULTILINE):
            bad.append(p.name)
    return not bad, f"LLM imports in: {bad}" if bad else "no LLM imports"


@check("Safety", "Bad-input cases are all handled (empty, missing column, 20 rows, bad ratings, phone number, 20 weeks)")
def _safe_bad_inputs() -> Result:
    results = run_bad_input_cases()
    bad = [r["case"] for r in results if not r["ok"]]
    return not bad, f"not handled: {bad}" if bad else f"{len(results)} cases handled"


# ---------------------------------------------------------------- runner and report
def run_all() -> list[dict]:
    results = []
    for group, name, fn in CHECKS:
        try:
            passed, detail = fn()
        except Exception as exc:  # noqa: BLE001 - one broken check must not stop the others
            passed, detail = False, f"check could not run ({type(exc).__name__}: {exc})"
        results.append({"group": group, "name": name, "passed": bool(passed), "detail": detail})
    return results


def write_report(results: list[dict]) -> str:
    passed = sum(r["passed"] for r in results)
    lines = [
        "# Checks report",
        "",
        f"Generated {dt.datetime.now().isoformat(timespec='seconds')}. Rule-based checks only; no AI was used.",
        "",
        f"**{passed} of {len(results)} checks passed.**" + ("" if passed == len(results) else f" {len(results) - passed} FAILED."),
    ]
    for group in dict.fromkeys(r["group"] for r in results):
        lines += ["", f"## {group}", ""]
        for r in (x for x in results if x["group"] == group):
            lines.append(f"- {'PASS' if r['passed'] else 'FAIL'}: {r['name']}. {r['detail']}")
    text = "\n".join(lines) + "\n"
    config.CHECKS_REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    config.CHECKS_REPORT_MD.write_text(text, encoding="utf-8")
    return text


def main() -> int:
    results = run_all()
    write_report(results)
    for r in results:
        print(f"{'PASS' if r['passed'] else 'FAIL'}  [{r['group']}] {r['name']}")
        if not r["passed"]:
            print(f"      {r['detail']}")
    failed = sum(not r["passed"] for r in results)
    print(f"\n{len(results) - failed}/{len(results)} passed. Report: outputs/checks_report.md")
    return 1 if failed else 0
