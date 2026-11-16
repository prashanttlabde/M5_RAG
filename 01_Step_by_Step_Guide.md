# Review Pulse for ChatGPT: Step-by-Step Guide (Beginning to End)

**What you are building:** an AI workflow that turns ChatGPT (India, Play Store) reviews into a weekly product pulse and a fact-checked fee explainer, then publishes both to a Google Doc and a Gmail draft, only after a human approves.

**Your path:** Python + Streamlit app, built with Cursor/Claude Code, plus an n8n MCP server for the publishing tools.
**Total effort:** about 12-15 focused hours. **Order matters:** do not start a phase before the previous checkpoint passes.

---

## The 3 rules that decide your score

1. **The AI sorts, your code counts.** The LLM labels reviews; Python does all counting and ranking.
2. **The AI never writes quotes or numbers.** It returns a review ID; code copies the exact text and inserts every number.
3. **Nothing is published without approval.** Show the exact payload, hash it, require typing `APPROVE`, and build no send-email tool at all.

---

## Phase A: Prepare (1 hour)

| # | Action | Where |
|---|---|---|
| A1 | Install Python 3.11+, Git, Cursor | your laptop |
| A2 | Create accounts: GitHub, Groq (free API key), Google account, Streamlit Community Cloud | web |
| A3 | Create an empty Google Doc named "Weekly Log"; copy its ID (between `/d/` and `/edit`) | Google Docs |
| A4 | Create an empty folder `review-pulse-chatgpt`, open it in Cursor | Cursor |
| A5 | **Do NOT start the n8n trial yet.** It lasts 14 days; start it in Phase G | -- |

**Checkpoint A:** you have a Groq key and a Google Doc ID saved somewhere private (not in chat, not in code).

## Phase B: Hand the documents to Cursor (30 min)

1. In the empty folder create `docs/` and drop in `PRD.md` and `architecture.md` (from this pack).
2. Open Cursor chat, switch to **Agent mode**, pick a Claude model.
3. Paste the whole of `MASTER_PROMPT.md` (between the START and END lines).
4. Cursor will: check your machine, scaffold the project, save rules to `CLAUDE.md`, then **write `docs/implementation.md`** and stop for your review.

**Checkpoint B:** you read `docs/implementation.md`, and it has phases P0 to P12, each with Tasks, a Cursor prompt, Verification and Acceptance criteria. Reply "next" only after you skim it.

## Phase C: Collect reviews (about 1 hour) = implementation P1

- Scrape 12 weeks of ChatGPT Play Store reviews (India, English) into a CSV.
- Clean: no names, no blanks, no reviews under 5 words, no duplicates.
- Make a **balanced** file: max 200 reviews per week.

**Checkpoint C:** 8-12 weeks, at least a few hundred reviews, and a printed keyword table (charge, GST, tax, renew, refund, subscription, plan, billing, price).

**Bring back to me:** the printed summary. We decide next steps together.

## Phase D: Themes, counts, quotes (about 2-3 hours) = implementation P2 and P3

1. LLM proposes at most 5 themes from a mixed sample.
2. LLM assigns every review to one theme, in small batches, cached.
3. **Code** counts reviews per theme and 1-2 star reviews per theme.
4. **Code** ranks the top 3 by 1-2 star count. Tie-break (written before you look): higher share of 1-2 star wins.
5. LLM returns only review IDs for the 3 best quotes. Code copies exact text.
6. Code computes the last-4-weeks vs previous-4-weeks trend, and a voice-feature tag count (your Milestone 1 lens).

**Checkpoint D:** `data/insights.json` exists; you can recompute the counts by hand in a spreadsheet for one theme and they match.

## Phase E: Find the fee confusion from data (about 2 hours) = implementation P4

1. Code filters reviews that mention money words.
2. LLM discovers at most 6 fee topics from a sample (for example GST on plan price, auto-renewal, refund, price difference between store and web).
3. LLM labels each money review: `confused`, `complaint_only`, `praise`, `unrelated`, plus one fee topic.
4. **Code** counts. The **identified fee issue** is the topic with the most `confused` reviews.

**Checkpoint E:** you can say in one sentence: "N of M fee-related reviews were confused about X." Read 20 of those reviews yourself and confirm they are really confusion, not just "too expensive".

## Phase F: Pulse, official sources, RAG explainer (about 4 hours) = implementation P5 and P6

**Pulse (P5):** code builds the skeleton and numbers; the LLM fills one sentence per theme, one key observation and 3 action ideas (each tied to a quote). Code counts words and rejects anything over 250.

**Explainer (P6), your RAG step:**
1. You choose 4-6 official URLs for the identified fee (OpenAI pricing/help pages, Google Play billing/subscription help, tax page). Put them in `config/sources.yaml`. **Never let the AI guess URLs.**
2. Cursor downloads each page as plain text and chunks it.
3. BM25 search retrieves the chunks most relevant to the fee issue.
4. LLM writes at most 6 neutral bullets, each citing a source ID.
5. Code checks numbers appear in the source, no opinion words, at most 6 bullets.
6. A second LLM fact-checks each bullet against only its cited chunk. Rejected bullets are rewritten; if too many fail, save as "needs human review".
7. Add 2 official links and "Last checked: <date>".

**Checkpoint F:** pulse is under 250 words with all four sections; explainer has at most 6 bullets, 2 links and a date, and zero fact-checker rejections.

## Phase G: n8n MCP server (about 1 hour) = implementation P7

Start the n8n trial now.

1. New workflow, add **MCP Server Trigger**, set Bearer auth with a long random token.
2. Attach 3 tools: `append_to_doc` (your Doc ID fixed in the node), `read_doc`, `create_email_draft` (recipient fixed to your own email, **Create Draft only**).
3. **Do not add any Send node.** Not disabled, never built.
4. Publish, copy the **Production URL**.
5. Put URL and token in `.env` yourself. Never paste them in chat.
6. Run Cursor's connection test: it must list exactly 3 tools.

**Checkpoint G:** the test lists `append_to_doc`, `read_doc`, `create_email_draft`, and no tool name contains "send".

## Phase H: Approval gate and publish (about 2 hours) = implementation P8

Order of operations after you type `APPROVE`:
1. `read_doc`: if this week is already there, stop (no duplicates).
2. Re-check the SHA-256 hash of the approved payload.
3. `append_to_doc`.
4. `read_doc` again: confirm the entry exists.
5. Re-check hash, then `create_email_draft`.
6. Write a log line after every step.

**Checkpoint H:** open the Google Doc and Gmail Drafts. Your entry and draft are there. Nothing was sent. Try Reject: nothing is written.

## Phase I: Prove it works (about 1 hour) = implementation P9

A plain-Python checks script (no AI) prints PASS/FAIL for: 8-12 weeks, no PII columns, at most 5 themes, exactly 3 top themes, recomputed counts match, quotes exist verbatim, pulse at most 250 words, at most 6 bullets, 2 links, hash matches, no tool named "send", plus bad inputs (empty file, missing column, 20 rows).

**Checkpoint I:** `outputs/checks_report.md` is green. Keep it for your README.

## Phase J: Streamlit UI and deploy (about 3 hours) = implementation P10 and P11

Pages: Overview, Insights, Weekly Pulse, Fee Explainer, Approve and Publish, Checks, About. Deployed app uses **cached results** (demo mode) so nothing takes 20 minutes on camera. Approve page needs a password because the link is public.

**Checkpoint J:** the live Streamlit URL loads on your phone, shows the pulse, and the approve page asks for the password.

## Phase K: Submission pack (about 1 hour) = implementation P12

- GitHub repo (no secrets; check the repo online for `.env`)
- Live prototype link (and a 3-minute demo video as backup)
- `outputs/weekly_pulse.md`
- Screenshot of the Doc entry and of the Gmail draft
- `data/reviews_balanced.csv` sample
- `docs/sources.md` with 4-6 URLs
- README: how to run, where approval happens, which fee issue was found

### Final checklist

- [ ] 8-12 weeks of reviews, exact count stated
- [ ] At most 5 themes, top 3 named, tie-break rule written
- [ ] 3 quotes verified verbatim in the CSV
- [ ] One fee confusion found from data, with counts
- [ ] Pulse at most 250 words, four sections, 3 actions
- [ ] Explainer at most 6 bullets, neutral, 2 official links, Last checked date
- [ ] Approval step visible and working
- [ ] Doc entry has all six fields: date, top_themes, weekly_pulse, identified_fee_issue, explanation_bullets, source_links
- [ ] Gmail draft exists, never sent
- [ ] No keys in the repo

---

## Where to ask me for help

After each checkpoint, send me the output (not secrets). Good things to bring: the keyword table (C), the top 3 themes and ranking (D), 20 fee reviews (E), the draft pulse (F), any error text from the MCP test (G).
