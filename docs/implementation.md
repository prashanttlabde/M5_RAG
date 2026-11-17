# Implementation Plan: Review Pulse for ChatGPT

**Based on:** architecture.md and PRD.md  
**Purpose:** Step-by-step execution plan so each phase is built, verified, and committed before the next starts.  
**Status:** P6 complete — ready for P7 (user must build the n8n MCP server first)
**Last updated:** 2026-11-16

---

## How to use this document

1. Implement **one phase at a time** (P0 → P12). Do not start the next phase until Acceptance criteria are ticked.
2. Paste the phase’s **Cursor prompt** into Agent mode (or Claude Code).
3. Run the **Verification** commands yourself; compare to expected outcomes.
4. Tick the **Acceptance criteria** checkboxes when they pass.
5. Commit with message format: `phase N: name` (example: `phase 0: scaffolding and environment`).
6. Say **next** only when you are ready for the following phase.
7. If the agent must leave the editor (accounts, secrets, n8n UI, Deploy), follow the **USER STEPS** block; never paste secrets into chat.

---

## Non-negotiable invariants

| ID | Invariant | Enforced in |
|---|---|---|
| INV-1 | Code counts; AI never counts, ranks, or types numbers that go into the pulse | P2, P3, P5, P9 |
| INV-2 | Quotes verified verbatim (LLM returns review_id; code copies; excerpt is substring) | P3, P9 |
| INV-3 | Fee facts only from pages listed in `config/sources.yaml` | P4 stop → user fills URLs; P6, P9 |
| INV-4 | Approval hash (SHA-256) re-checked before every write | P8, P9 |
| INV-5 | No send tool; no tool name may contain "send" | P7, P8, P9 |
| INV-6 | No PII (drop names at collection; checks scan for emails/phones) | P1, P9 |
| INV-7 | No secrets in Git (`.env` gitignored; verify online before submit) | P0, P11, P12 |
| INV-8 | Every LLM call cached by hash of model + prompt | P2 onward |
| INV-9 | Pulse ≤ 250 words; explainer ≤ 6 bullets | P5, P6, P9 |

---

## Global conventions

- Python 3.11+ (project targets 3.11; 3.13 OK if installed), `src/` layout, type hints, dataclasses.
- Config values live in `src/config.py` (loads `config/*.yaml` and `.env`).
- Domain errors live in `src/errors.py`.
- Logging via `src/logging_config.py`; library code uses logging, not `print`.
- Paths via `pathlib.Path` only.
- Every module starts with a docstring naming the architecture section it implements (e.g. `"""Implements architecture §5 LLM layer."""`).
- Stack is fixed in `CLAUDE.md`; do not add LangChain, vector DBs, ORMs, or auth libraries.

---

## Phase P0 — Scaffolding and environment

### Goal
Make the empty skeleton runnable: config, errors, logging, shared types, Makefile targets, and a scaffolding test.

### Architecture reference
architecture.md §3 (layout), §11 (secrets), CLAUDE.md Stack

### Tasks
1. Fill `src/config.py`: load `.env` via python-dotenv; expose paths and env getters for `GROQ_API_KEY`, `LLM_MODEL`, `N8N_MCP_URL`, `N8N_MCP_TOKEN`, `APPROVER_PASSWORD`, `DEMO_MODE`.
2. Fill `src/errors.py`: domain exceptions (`ConfigError`, `DataError`, `LLMError`, `ValidationError`, `PublishError`).
3. Fill `src/logging_config.py`: `setup_logging()` → console logger.
4. Fill `src/types.py`: dataclasses for Review, Theme, Quote, FeeLabel, Insights, DocEntry (fields only; no logic).
5. Write `Makefile` targets: `install`, `collect`, `analyze`, `write`, `rag`, `checks`, `app`, `test`, `lint` (stubs that echo “not implemented” except `install`, `test`, `lint` which work).
6. Write `tests/test_scaffolding.py`: imports `src.config`, `src.errors`, `src.types`; asserts `.gitignore` lists `.env` and `data/cache/`.
7. Ensure `requirements.txt` matches Stack; document `python -m venv .venv` in README one-liner only if needed for install.

### Cursor prompt
> Re-read CLAUDE.md and docs/implementation.md phase P0. Explain in 2–3 sentences what you will build, then implement only P0 Tasks. Do not implement later phases. Run Verification. Update this phase’s Acceptance criteria checkboxes in docs/implementation.md. Commit with `phase 0: scaffolding and environment`. Print “Phase 0 done. Say next to continue.” and stop.

### Verification
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make install
make test
make lint
```
Expect: venv works; `tests/test_scaffolding.py` passes; ruff runs without crash (empty modules OK).

### Acceptance criteria
- [x] `src/config.py`, `src/errors.py`, `src/logging_config.py`, `src/types.py` are non-empty and importable
- [x] Makefile has all listed targets
- [x] `tests/test_scaffolding.py` passes
- [x] Commit message is `phase 0: scaffolding and environment`

### What I should learn here
Scaffolding is the shared foundation every later phase imports. Getting config and errors right early prevents secrets and vague failures from spreading through the app.

---

## Phase P1 — Review collection

### Goal
Scrape, clean, and balance Play Store reviews for `com.openai.chatgpt` (India, English) into CSVs plus a keyword summary table.

### Architecture reference
architecture.md §4 (reviews CSVs); PRD FR1, FR2, P6

### Tasks
1. Fill `config/product.yaml`: `app_id`, `country`, `lang`, `weeks` (12), money/voice keyword lists, ranking tie-break rule text (write rule before any results).
2. Implement `src/collect/scrape.py`: `scrape_reviews() -> Path` using google-play-scraper; newest first; keep `review_id, date, rating, text`; drop reviewer names.
3. Implement `src/collect/clean.py`: drop blanks, under-5-word texts, duplicates; add `week_start`; write `data/reviews_full.csv`; write `data/reviews_balanced.csv` (max 200 per week).
4. Print/write a keyword hit summary table for: charge, GST, tax, renew, refund, subscription, plan, billing, price.
5. Wire `make collect` to run scrape + clean.
6. If fewer than 8 weeks of data: raise clear `DataError` and stop.

### Cursor prompt
> Re-read CLAUDE.md and docs/implementation.md phase P1. Explain in 2–3 sentences what you will build, then implement only P1. Enforce INV-6 (no names). Run Verification. Tick Acceptance criteria. Commit `phase 1: review collection`. Print “Phase 1 done. Say next to continue.” and stop.

### Verification
```bash
source .venv/bin/activate
make collect
python -c "import pandas as pd; f=pd.read_csv('data/reviews_full.csv'); b=pd.read_csv('data/reviews_balanced.csv'); print(f.columns.tolist()); print('full', len(f), 'balanced', len(b)); print('weeks', f['week_start'].nunique()); print(b.groupby('week_start').size().max())"
```
Expect: columns `review_id, date, week_start, rating, text`; 8–12 weeks; max per week ≤ 200; keyword table printed.

### Acceptance criteria
- [x] `data/reviews_full.csv` and `data/reviews_balanced.csv` exist with required columns
- [x] 8–12 distinct weeks; exact review counts known
- [x] No reviewer name column; keyword summary produced
- [x] Commit `phase 1: review collection`

### What I should learn here
Collection quality decides everything downstream. Balancing weeks stops one viral week from drowning the rest of the signal.

---

## Phase P2 — LLM layer and theme discovery

### Goal
Add a cached Groq JSON LLM helper; discover ≤5 themes; assign every review to one theme.

### Architecture reference
architecture.md §5, §6; PRD FR3, FR4; INV-1, INV-8

### Tasks
1. Implement `src/llm.py`: `ask_json(prompt: str, schema: dict, cache_key: str | None = None) -> dict` — Groq call, JSON-only, validate keys by hand, retry up to 2 on invalid JSON, cache under `data/cache/<sha256(model+prompt)>.json`, exponential backoff on 429.
2. Implement `src/analyze/themes.py`: sample mixed ~150 reviews (angry/neutral/happy); LLM proposes ≤5 themes; reject and retry if >5; write `data/themes.json`.
3. Implement `src/analyze/classify.py`: batch ~25, trim text ~300 chars; assign each review to one `theme_id`; write `data/assignments.csv`.
4. Wire `make analyze` for theme discovery + assignment (ranking comes in P3).
5. Tests: cache hit makes no network call (mock or offline cache file).

### Cursor prompt
> Re-read CLAUDE.md and docs/implementation.md phase P2. Explain in 2–3 sentences, then implement only P2. AI may propose/assign themes; code must never count or rank. Cache every LLM call (INV-8). Stop and wait for “next” after Verification, Acceptance ticks, and commit `phase 2: llm layer and theme discovery`.

### Verification
```bash
source .venv/bin/activate
# Put GROQ_API_KEY and LLM_MODEL in .env yourself before this step. Never paste them in chat.
make analyze
python -c "import json; t=json.load(open('data/themes.json')); print(len(t), [x.get('name') for x in t]); import pandas as pd; a=pd.read_csv('data/assignments.csv'); print(a.columns.tolist(), len(a))"
ls data/cache | head
```
Expect: ≤5 themes; assignments cover reviews; cache files appear.

### Acceptance criteria
- [x] `ask_json` validates, retries, caches
- [x] `data/themes.json` has at most 5 themes
- [x] `data/assignments.csv` has `review_id, theme_id`
- [x] Commit `phase 2: llm layer and theme discovery`

### What I should learn here
“Ask for JSON and validate it” is how you make an LLM safe to automate. Caching makes demos cheap and reproducible.

---

## Phase P3 — Counting, ranking, quotes, trends

### Goal
Compute `insights.json` entirely in code: counts, top 3, quotes (copied), trends, voice tag.

### Architecture reference
architecture.md §4 insights.json; PRD FR5–FR8; INV-1, INV-2

### Tasks
1. Implement `src/analyze/rank.py`: count total and low-star (1–2) per theme; rank top 3 by low-star count; tie-break: higher `low_star_share`, then alphabetical name; read rule from `config/product.yaml`.
2. Implement `src/analyze/quotes.py`: LLM returns best `review_id` (+ optional excerpt) per top theme; code copies text from CSV; verify excerpt is verbatim substring; else fall back to first 25 words of real review.
3. Implement `src/analyze/trend.py`: last-4-weeks vs previous-4-weeks counts per top theme; voice-related review counts via keyword list in config.
4. Write `data/insights.json` matching architecture schema (all numbers from code).
5. Test: recompute-from-scratch — delete derived ranks in memory and rebuild from CSVs; must match `insights.json`.

### Cursor prompt
> Re-read CLAUDE.md and docs/implementation.md phase P3. Explain in 2–3 sentences, then implement only P3. Enforce INV-1 and INV-2. Run Verification including recompute test. Commit `phase 3: counting ranking quotes trends`. Print “Phase 3 done. Say next to continue.” and stop.

### Verification
```bash
source .venv/bin/activate
make analyze
python -c "import json; i=json.load(open('data/insights.json')); print(i['ranking_rule']); print(i['top3']); print(len(i['quotes'])); print(i.get('voice_tag')); print(i['window'])"
pytest tests/ -k recompute -q
```
Expect: ranking rule string present; exactly 3 top themes; 3 quotes with review_ids; voice_tag counts present.

### Acceptance criteria
- [x] `data/insights.json` matches schema; all counts recomputable
- [x] Top 3 ranked by low-star rule written before results
- [x] 3 quotes substring-verified against CSV
- [x] Commit `phase 3: counting ranking quotes trends`

### What I should learn here
Ranking by unhappy reviews surfaces pain, not praise volume. Verbatim quotes are evidence; paraphrases are not.

---

## Phase P4 — Fee confusion detection

### Goal
From money-related reviews, label stance + fee topic; identify the fee issue as the topic with most `confused` labels. Then stop for human URLs.

### Architecture reference
architecture.md §2, §4 fee_labels; PRD FR7; INV-3

### Tasks
1. Implement `src/analyze/fee.py`: filter money keywords from config; LLM proposes closed fee-topic list (≤6) from a sample; LLM labels each money review `confused | complaint_only | praise | unrelated` + one topic; code counts; set identified issue = topic with most confused.
2. Write `data/fee_labels.csv` and update `data/insights.json` fee block.
3. Print one-sentence summary: “N of M fee-related reviews were confused about X.”
4. **STOP for user:** ask them to fill `config/sources.yaml` with 4–6 official URLs. Do not guess URLs.

### Cursor prompt
> Re-read CLAUDE.md and docs/implementation.md phase P4. Explain in 2–3 sentences, then implement only P4. Confusion ≠ complaint. Do not invent URLs. After Verification, print USER STEPS for filling sources.yaml, commit `phase 4: fee confusion detection`, then stop and wait.

### Verification
```bash
source .venv/bin/activate
make analyze
python -c "import pandas as pd, json; f=pd.read_csv('data/fee_labels.csv'); print(f['stance'].value_counts().to_dict()); i=json.load(open('data/insights.json')); print(i['fee'])"
```
Expect: stance counts; fee.topic set; confused count > 0 or honest zero with clear message.

### Acceptance criteria
- [x] `data/fee_labels.csv` exists with `review_id, stance, fee_topic`
- [x] Identified fee issue comes from confused counts, not assumption
- [x] Agent asked user to fill `config/sources.yaml` and did not guess URLs
- [x] Commit `phase 4: fee confusion detection`

### USER STEPS (after P4 code works)
1. Read ~20 reviews labelled `confused` yourself.
2. Choose 4–6 **official** pages that could explain that fee (OpenAI help/pricing, Google Play subscriptions/billing/tax — only pages that actually apply).
3. Edit `config/sources.yaml` yourself with `source_id`, `title`, `url` for each. Do not paste URLs into chat if you prefer privacy; editing the file is enough.
4. Say **next** only after the file has 4–6 real URLs.

### What I should learn here
“Too expensive” is a complaint; “I don’t know why I was charged” is confusion. Product and support fix those differently.

---

## Phase P5 — Weekly product pulse

### Goal
Produce `outputs/weekly_pulse.md` ≤250 words with four sections; numbers from code; sentences from LLM.

### Architecture reference
architecture.md pulse path; PRD FR9–FR12; INV-1, INV-9

### Tasks
1. Implement `src/writer/wordcount.py`: `count_words(text: str) -> int`.
2. Implement `src/writer/pulse.py`: code builds skeleton (title, theme names, counts, trends, quote blocks); LLM writes one-sentence theme summaries, key observation, 3 action ideas each tied to a quote; LLM must not output digits for counts (code inserts); if word count >250, rewrite up to 3 times.
3. Sections required: Summary of top themes; Supporting user quotes; Key observation; 3 action ideas.
4. Wire `make write`.

### Cursor prompt
> Re-read CLAUDE.md and docs/implementation.md phase P5. Explain in 2–3 sentences, then implement only P5. Enforce INV-1 and INV-9. Commit `phase 5: weekly product pulse`. Stop after Verification.

### Verification
```bash
source .venv/bin/activate
make write
python -c "from pathlib import Path; t=Path('outputs/weekly_pulse.md').read_text(); print(len(t.split())); print(t[:500])"
```
Expect: ≤250 words; four sections visible; three actions.

### Acceptance criteria
- [x] `outputs/weekly_pulse.md` ≤250 words with all four sections
- [x] All numbers inserted by code; 3 actions reference quotes
- [x] Commit `phase 5: weekly product pulse`

### What I should learn here
Controlled summarisation means the model writes prose inside a skeleton you own. Word limits force clarity for a one-minute PM read.

---

## Phase P6 — Fee explainer RAG

### Goal
Fetch official pages, chunk, BM25 retrieve, write grounded bullets, validate, fact-check; write `outputs/fee_explainer.md`.

### Architecture reference
architecture.md §7; PRD FR13–FR18; INV-3, INV-9

### Tasks
1. Implement `src/rag/fetch.py`: read `config/sources.yaml`; download with trafilatura (BeautifulSoup fallback); save `data/sources/<source_id>.txt`; record fetch date; manual-paste fallback path if download fails.
2. Implement `src/rag/chunk.py`: ~300–500 token sentence-aware chunks, ~15% overlap; write `data/chunks.jsonl` with metadata.
3. Implement `src/rag/index.py`: BM25 via rank_bm25; `search(query, k=5)`.
4. Implement `src/rag/explain.py`: build query from fee topic + confused phrasing (computed text); LLM writes ≤6 neutral bullets each ending with `[source_id]`.
5. Implement `src/rag/validate.py`: bullet count, citation exists, every number in cited chunk, banned opinion words absent.
6. Implement `src/rag/factcheck.py`: second LLM call per bullet vs one chunk; one rewrite; drop failures; if <4 bullets → `needs_human_review` and block publish later.
7. Append exactly 2 official source links + `Last checked: YYYY-MM-DD`.
8. Wire `make rag`.

### Cursor prompt
> Re-read CLAUDE.md and docs/implementation.md phase P6. Explain in 2–3 sentences, then implement only P6. Never invent URLs or fee facts (INV-3). Commit `phase 6: fee explainer rag`. Stop after Verification.

### Verification
```bash
source .venv/bin/activate
make rag
python -c "from pathlib import Path; t=Path('outputs/fee_explainer.md').read_text(); print(t); print('bullets', t.count('\n-')+t.count('\n*'))"
wc -l data/chunks.jsonl
```
Expect: ≤6 bullets; 2 links; Last checked date; chunks file non-empty.

### Acceptance criteria
- [x] Sources fetched only from `sources.yaml`
- [x] Explainer ≤6 bullets, 2 links, Last checked present
- [x] Validators + fact-check run; status recorded if needs_human_review
- [x] Commit `phase 6: fee explainer rag`

### What I should learn here
RAG here means “retrieve official text, then write only from that.” Fact-checking each bullet against one chunk is context engineering for trust.

---

## Phase P7 — MCP server in n8n and MCP client test

### Goal
Human builds n8n MCP tools; Python client lists exactly three safe tools.

### Architecture reference
architecture.md §8; PRD FR19; INV-5

### Tasks
1. Print **USER STEPS** below and wait until `.env` has `N8N_MCP_URL` and `N8N_MCP_TOKEN` (user fills; never paste into chat).
2. Implement `src/mcp_client/client.py`: connect via official `mcp` SDK; support streamable HTTP and SSE; Bearer auth.
3. Implement `src/mcp_client/test_connection.py`: list tools; assert exactly `append_to_doc`, `read_doc`, `create_email_draft`; fail if any name contains `"send"` (case-insensitive).
4. Add `n8n/README.md` notes (no credentials); leave `n8n/workflow.export.json` for user export later.

### USER STEPS
1. Create an empty Google Doc named “Weekly Log”; copy its document ID (between `/d/` and `/edit`). Keep it private.
2. Start the n8n cloud trial **now** (14 days).
3. New workflow → **MCP Server Trigger** with Bearer auth (long random token you invent).
4. Add exactly three tools wired to Google Docs / Gmail nodes:
   - `append_to_doc` — Doc ID fixed inside the node
   - `read_doc` — same Doc ID
   - `create_email_draft` — recipient fixed to your email; **Create Draft only**
5. **Do not add any Send node** (not even disabled).
6. Publish; copy the **Production URL**.
7. Put `N8N_MCP_URL` and `N8N_MCP_TOKEN` into `.env` yourself.
8. Tell the agent you are ready (say **next** or “ready”) without pasting the token.

### Cursor prompt
> Re-read CLAUDE.md and docs/implementation.md phase P7. Explain in 2–3 sentences. First ensure USER STEPS are printed if secrets are missing; do not ask for secrets in chat. Implement client + test_connection only. Run Verification. Commit `phase 7: mcp client and connection test`. Stop.

### Verification
```bash
source .venv/bin/activate
python -m src.mcp_client.test_connection
```
Expect: lists exactly three tools; no name contains “send”.

### Acceptance criteria
- [ ] USER STEPS completed by human; `.env` has URL and token (not in Git)
- [ ] Connection test passes with exactly three tools
- [ ] Fail-fast if any tool name contains “send”
- [ ] Commit `phase 7: mcp client and connection test`

### What I should learn here
MCP is a standard way for apps to call tools. Safety comes from which tools exist — if Send is never built, it cannot be called.

---

## Phase P8 — Approval gate and publishing

### Goal
Build payload + hash + APPROVE gate; publish in fixed MCP order with logging and resume.

### Architecture reference
architecture.md §9; PRD FR20–FR24; INV-4, INV-5

### Tasks
1. Implement `src/approval/payload.py`: build canonical JSON with Doc fields `date, top_themes, weekly_pulse, identified_fee_issue, explanation_bullets, source_links`; email subject `Weekly Product Pulse + Customer Clarification - <fee issue> - <week>`; body = pulse + explainer snippet; SHA-256 of sorted-key payload; write `outputs/approval_payload.json` and `outputs/email_draft.txt`.
2. Implement `src/approval/gate.py`: show payload + hash; require typed `APPROVE`; Reject collects reason and writes nothing.
3. Implement `src/approval/publish.py`: fixed order — `read_doc` (duplicate check) → hash re-check → `append_to_doc` → `read_doc` verify → hash re-check → `create_email_draft`; log each step to `outputs/publish_log.jsonl`; resume without duplicates; friendly errors; block if explainer `needs_human_review`.
4. CLI entry for approve/publish; same functions used later by Streamlit.

### Cursor prompt
> Re-read CLAUDE.md and docs/implementation.md phase P8. Explain in 2–3 sentences, then implement only P8. Enforce INV-4 and INV-5. Never create a send tool. Commit `phase 8: approval gate and publishing`. Stop after Verification.

### Verification
```bash
source .venv/bin/activate
python -c "from src.approval.payload import build_payload; p=build_payload(); print(p['hash'][:16], list(p['doc_entry'].keys()))"
# Manual: run approve CLI, type Reject → confirm Doc unchanged
# Manual: type APPROVE → confirm Doc entry + Gmail draft only
```
Expect: six Doc fields; hash shown; reject writes nothing; approve creates draft not send.

### Acceptance criteria
- [ ] Payload has six Doc fields + email subject/body + hash
- [ ] APPROVE required; hash re-checked before writes
- [ ] Fixed MCP call order; publish_log.jsonl updated per step
- [ ] Commit `phase 8: approval gate and publishing`

### What I should learn here
Approval gating means the human signs the exact bytes that will be written. Hashing detects silent changes between “I approved” and “write now”.

---

## Phase P9 — Checks script

### Goal
Rule-based, no-AI verification writing `outputs/checks_report.md`, including bad-input tests.

### Architecture reference
architecture.md §12; PRD FR27; all INV-*

### Tasks
1. Implement `src/checks/run_checks.py`: independent checks (data, themes, quotes, pulse, explainer, safety); each PASS/FAIL; continue after failures; write report.
2. Implement `src/checks/bad_inputs.py`: empty file, missing column, 20 rows, ratings 0 or `"good"`, phone number inside a review, 20 weeks of data.
3. Wire `make checks`.
4. No LLM calls in this phase’s runtime path.

### Cursor prompt
> Re-read CLAUDE.md and docs/implementation.md phase P9. Explain in 2–3 sentences, then implement only P9. No AI in checks. Commit `phase 9: checks script`. Stop after Verification.

### Verification
```bash
source .venv/bin/activate
make checks
cat outputs/checks_report.md
pytest tests/ -k bad_input -q
```
Expect: report with PASS/FAIL lines; bad-input tests exercise failures safely.

### Acceptance criteria
- [ ] `outputs/checks_report.md` generated without LLM
- [ ] Bad-input cases covered
- [ ] Commit `phase 9: checks script`

### What I should learn here
Independent checks are how you prove the pipeline to a grader without trusting the model that wrote the prose.

---

## Phase P10 — Streamlit app

### Goal
Working multipage app; DEMO_MODE; Approve page calls same publish code as CLI.

### Architecture reference
architecture.md §10; PRD FR25–FR26; Design direction in master prompt

### Tasks
1. Implement `app/streamlit_app.py` entry + pages: Overview, Insights, Weekly Pulse, Fee Explainer, Approve and Publish, Checks, About.
2. Visual direction: white cards on light grey; headings `#0B3C49`; links `#1F7A8C`; thin borders; status = icon + word (not colour alone); no emoji; no gradients; footer on every page: “Built from public reviews and official pages. Facts only. Human-approved publishing.”
3. Every number loaded from computed artifacts, never hard-coded in UI.
4. Fee facts show source links + Last checked.
5. `DEMO_MODE=true` loads cached artifacts; hides scrape/LLM run buttons.
6. Approve page: password via `APPROVER_PASSWORD`; calls `src/approval/publish.py`.
7. Wide tables scroll horizontally on small screens; polite empty states when artifacts missing.

### Cursor prompt
> Re-read CLAUDE.md and docs/implementation.md phase P10. Explain in 2–3 sentences, then implement only P10. Follow design direction. Commit `phase 10: streamlit app`. Stop after Verification.

### Verification
```bash
source .venv/bin/activate
make app
# Open local URL; click each page; confirm empty-state messages if needed
```
Expect: all seven pages load; Approve uses shared publish path.

### Acceptance criteria
- [ ] All listed pages exist and load artifacts
- [ ] DEMO_MODE respected; Approve password-gated
- [ ] Design direction followed; footer present
- [ ] Commit `phase 10: streamlit app`

### What I should learn here
The UI is a window onto artifacts, not a place where numbers are typed. Same publish code in CLI and UI prevents “demo-only” safety gaps.

---

## Phase P11 — Deployment

### Goal
GitHub + Streamlit Community Cloud demo with secrets and DEMO_MODE; cached artifacts committed for zero LLM on host.

### Architecture reference
architecture.md §13; INV-7

### Tasks
1. Print **USER STEPS** and wait.
2. Commit cached artifacts needed for demo (`insights.json`, pulse, explainer, chunks, themes, assignments sample as needed) — not `.env`, not live secrets.
3. Ensure README has run + deploy pointers (full README polish in P12).
4. Export n8n workflow JSON without credentials into `n8n/workflow.export.json` if not already.

### USER STEPS
1. Create a GitHub repo (private or public as you prefer for the assignment).
2. Push the project. In the GitHub website file browser, **confirm `.env` is not present**.
3. Go to Streamlit Community Cloud → New app → point at `app/streamlit_app.py`.
4. Paste secrets into Streamlit’s secrets box yourself: `GROQ_API_KEY` (optional if DEMO_MODE only), `LLM_MODEL`, `N8N_MCP_URL`, `N8N_MCP_TOKEN`, `APPROVER_PASSWORD`, `DEMO_MODE=true`.
5. Deploy. Open the URL on your phone.
6. Tell the agent the app URL is live (you may share the public app URL; never share tokens).

### Cursor prompt
> Re-read CLAUDE.md and docs/implementation.md phase P11. Explain in 2–3 sentences. Guide USER STEPS; commit demo artifacts with `phase 11: deployment`. Do not ask for secrets. Stop after human confirms deploy.

### Verification
- Human: GitHub shows no `.env`
- Human: Streamlit URL loads on phone in DEMO_MODE
- Human: Approve page asks for password

### Acceptance criteria
- [ ] Repo online without secrets
- [ ] Streamlit app live with DEMO_MODE=true
- [ ] Cached artifacts committed for demo
- [ ] Commit `phase 11: deployment`

### What I should learn here
Hosted demos must not call paid/rate-limited APIs live. Secrets belong in the host’s secret store, never in Git.

---

## Phase P12 — Submission pack

### Goal
README, sources list, samples, screenshot instructions, 3-minute demo script, final checklist.

### Architecture reference
PRD §8 Deliverables; Appendix C below

### Tasks
1. Write full `README.md`: how to run locally, where approval happens, which fee issue was identified, link to live app, how checks work.
2. Fill `docs/sources.md` with the 4–6 URLs from `sources.yaml` (titles + links).
3. Ensure sample `data/reviews_balanced.csv` (or a clearly named sample) is present for graders.
4. Ensure `outputs/weekly_pulse.md` and explainer are present.
5. Add `docs/demo_script.md`: 3-minute demo video script.
6. Add screenshot instructions for Google Doc entry and Gmail draft (what to capture).
7. Tick Appendix C checklist with the human; fix any gaps before declaring done.

### Cursor prompt
> Re-read CLAUDE.md and docs/implementation.md phase P12. Explain in 2–3 sentences, then implement only P12 submission docs. Commit `phase 12: submission pack`. Stop after Verification and final checklist review with the human.

### Verification
```bash
test -f README.md && test -f docs/sources.md && test -f outputs/weekly_pulse.md && test -f docs/demo_script.md && echo OK
# Human: walk Appendix C checklist aloud
```

### Acceptance criteria
- [ ] README covers run, approval, fee issue, live link
- [ ] docs/sources.md has 4–6 URLs
- [ ] Demo script + screenshot instructions present
- [ ] Appendix C checklist reviewed with human
- [ ] Commit `phase 12: submission pack`

### What I should learn here
Submission is product storytelling: show evidence, safety, and a path for a stranger to reproduce the demo in minutes.

---

## Appendix A — Phase dependency map

```
P0 scaffold
 └─► P1 collect
      └─► P2 LLM + themes/assignments
           └─► P3 counts/quotes/trends ──┐
                └─► P4 fee confusion ────┼─► P5 pulse
                         │               └─► P6 RAG explainer
                         │ USER fills sources.yaml
                         ▼
                    P7 n8n MCP + client test
                         └─► P8 approval + publish
                              └─► P9 checks
                                   └─► P10 Streamlit
                                        └─► P11 deploy
                                             └─► P12 submission
```

---

## Appendix B — `.cursor/rules/review-pulse.mdc` content

```markdown
---
description: Review Pulse project rules — always read project memory before acting
alwaysApply: true
---

Read and follow CLAUDE.md and docs/implementation.md before every action.
```

---

## Appendix C — Definition of done (final checklist)

- [ ] 8 to 12 weeks of reviews, exact count stated
- [ ] At most 5 themes, top 3 named, ranking rule written
- [ ] 3 quotes verified verbatim in the CSV
- [ ] One fee confusion identified from data with counts
- [ ] Pulse at most 250 words with all four sections and 3 action ideas
- [ ] Explainer at most 6 bullets, neutral, 2 official links, Last checked date, zero fact-check rejections
- [ ] Approval step visible and working; reject writes nothing
- [ ] Doc entry contains all six required fields
- [ ] Gmail draft created, never sent; no send tool exists
- [ ] Live prototype link works on a phone
- [ ] No keys or tokens anywhere in the repository
