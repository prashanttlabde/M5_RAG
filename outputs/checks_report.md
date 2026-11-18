# Checks report

Generated 2026-11-18T09:22:29. Rule-based checks only; no AI was used.

**30 of 30 checks passed.**

## Data

- PASS: Review files have the required columns, valid ratings and no PII (both CSVs). both files pass the validator
- PASS: 8 to 12 distinct weeks; exact review counts stated. 12 weeks; full=3107, balanced=2377
- PASS: Balanced file has at most 200 reviews per week. largest week has 200
- PASS: No reviewer name column in either CSV (INV-6). columns are review_id, date, week_start, rating, text
- PASS: Balanced reviews are a subset of the full reviews. 0 balanced reviews missing from full

## Themes

- PASS: At most 5 themes with unique ids. 5 themes
- PASS: Every balanced review is assigned to exactly one valid theme. 2377 assignments for 2377 reviews
- PASS: Per-theme totals and 1-2 star counts in insights.json match a fresh recount. all counts match
- PASS: Top 3 follows the written rule (1-2 star count, then share, then name), never volume. file ['t3', 't2', 't1'] vs recomputed ['t3', 't2', 't1']
- PASS: Ranking rule text exists in config and matches insights.json. low_star desc, then low_star_share desc, then name

## Quotes

- PASS: 3 quotes, one per top theme, each from a real review of that theme. 3 quotes verified
- PASS: Every quote excerpt is a verbatim substring of the real review (INV-2), 25 words or fewer. all excerpts are exact substrings

## Pulse

- PASS: Pulse is at most 250 words (INV-9). 245 words
- PASS: Pulse has all four sections and exactly 3 action ideas, each tied to a quote. 4 sections, 3 actions with quote links
- PASS: Every number in the pulse comes from computed data (INV-1). all numbers traced to computed data
- PASS: Quotes shown in the pulse are real review text. 3 quotes, 0 not found in reviews

## Explainer

- PASS: At most 6 bullets; status ok; zero fact-check rejections. 6 bullets, status ok, 0 rejected
- PASS: Exactly 2 official links, both from sources.yaml, plus a Last checked date. 2 links, all official: True, Last checked: 2026-11-18
- PASS: Each bullet cites a known source_id and uses no opinion or advice words. 6 bullets cite known sources
- PASS: Every number in each bullet appears in its cited chunk (INV-3). numbers and citations match their chunks
- PASS: Explainer is not older than the chunk set it was built from. up to date

## Safety

- PASS: .env is gitignored and not tracked (INV-7). tracked: []; ignored: True
- PASS: No API keys or tokens in any tracked file (INV-7). 102 tracked files scanned
- PASS: No personal data (email or phone) in the pulse, explainer, payload or email draft (INV-6). none found
- PASS: No send tool anywhere: workflow export, code and publish log (INV-5). no send tool in the workflow, code or log
- PASS: Approval payload: exactly six Doc fields and the hash recomputes (INV-4). fields ok: True; hash matches: True
- PASS: Publish log is valid JSON lines and every finished run was verified before the email draft. 12 log lines consistent
- PASS: Stack rule: no LangChain, vector DB, ORM or auth library in requirements.txt. requirements match the fixed stack
- PASS: This checks script makes no LLM call (imports no llm or groq module). no LLM imports
- PASS: Bad-input cases are all handled (empty, missing column, 20 rows, bad ratings, phone number, 20 weeks). 7 cases handled
