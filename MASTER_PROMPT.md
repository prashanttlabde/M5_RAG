# Master Prompt for Cursor: Review Pulse for ChatGPT

*Paste it into Cursor (Agent mode, a Claude model) once. It stops at every milestone and waits for you.*

## How to use this

1. Make an empty folder, for example `Desktop/review-pulse-chatgpt`. In Cursor choose File, Open Folder, and pick it.
2. Inside it create a folder `docs` and put `PRD.md` and `architecture.md` in it. Optionally also add a folder `reference` with the three sample documents you were given (Mutual Fund `implementation.md`, GCC Atlas guide, Kizuki build guide) so Cursor can copy their format.
3. Open the chat panel, switch to **Agent mode**, pick a Claude model. (Claude Code works too: open Cursor's terminal, type `claude`, paste the same prompt.)
4. Copy everything between **START OF PROMPT** and **END OF PROMPT**. Paste and press enter.
5. It will stop at every milestone. That is by design. Reply `next` when you are ready.
6. Free accounts you need: GitHub, Groq, Google, Streamlit Community Cloud, n8n (start the n8n trial only when the prompt tells you to, because it lasts 14 days).

**Copying caution:** if quote marks turn curly after pasting from Word or a browser, commands will fail. Paste into a plain text editor first.

**If the paste is too long or Cursor stops following it:** paste only the sections from "Who you are talking to" to "What the code does vs what the AI does", say "Read this and do nothing yet", then paste each milestone as you reach it.

**If Cursor loses track, paste this:**

```
Stop. Do not change any files.
Re-read CLAUDE.md and docs/implementation.md in the project folder.
Then tell me, in plain English: which phase we are on, what is finished, and what is next.
Wait for me to say "next".
```

**Never paste a key, token or URL with a token into the chat.** The prompt tells you to put them in `.env` yourself.

---

## START OF PROMPT: COPY FROM HERE DOWN

### Who you are talking to

I am a product manager. I can read code a little but I do not write it. You are not just building this for me. You are teaching me while you build it, and you are building a portfolio piece I will be asked questions about in interviews.

### What we are building

"Review Pulse" is an AI workflow for ChatGPT (the Android app, India market, product package com.openai.chatgpt). It does this:

1. Collects 8 to 12 weeks of public Play Store reviews into a CSV.
2. Groups the reviews into at most 5 themes, finds the top 3, extracts 3 real user quotes, and finds 1 recurring confusion about a fee or charge. The fee issue must come from the data, not from my assumption.
3. Writes a weekly internal product pulse (250 words maximum).
4. Writes a standardised, facts-only fee explainer (6 bullets maximum, 2 official source links, a "Last checked" date) using retrieval over official pages that I supply.
5. After a human approval step, uses MCP tools (served by n8n) to append the output to a Google Doc and create a Gmail draft. It never sends email.
6. Has a Streamlit app, deployed, as the working prototype.

Two documents in the docs folder are the source of truth: docs/PRD.md and docs/architecture.md. Read both completely before doing anything. If this prompt and those documents disagree, tell me, and this prompt wins.

My context: this is an assignment called "RAGs and Context Engineering". The grader checks insight extraction from unstructured data, theme clustering, connecting insights to communication, controlled summarisation, structured explanation generation, workflow orchestration, and MCP tool calling with approval gating.

### Golden rules: follow these for the entire session

- **Explain before you do.** Before creating or editing any file, tell me in two or three plain sentences what the file is for and why it must exist. Define any jargon the first time you use it.
- **Stop at every milestone and every phase.** After each, print what you did, tell me exactly what to run or check, and wait for me to say "next". Do not run ahead.
- **Stop when I must leave the editor.** Creating accounts, putting secrets in files, building the n8n workflow, clicking Deploy: you cannot do these. Print numbered steps and wait. Never ask me to paste a secret into this chat. Tell me to put it in .env myself.
- **Build only what is specified.** No extra features, pages or libraries. If something seems missing, say so and let me decide.
- **The AI sorts, code counts.** Every count, rank, percentage, trend and word count is computed in Python. An LLM is never asked to count, add or rank, and never types a number that goes into the pulse.
- **Quotes are copied, never generated.** An LLM may return a review_id (and an optional excerpt). Code copies the text from the CSV and verifies any excerpt is a verbatim substring of the real review.
- **Never invent URLs or fee facts.** Official sources come only from config/sources.yaml, which I fill in. Fee facts must come only from retrieved chunk text.
- **Humans approve exact payloads.** Hash the payload (SHA-256), require me to type APPROVE in capitals, and re-check the hash before every write. Call MCP tools directly in a fixed order. Never let an LLM agent choose tools.
- **No send capability exists.** Never create, suggest or call a send-email tool. No tool name may contain "send".
- **No personal data.** Drop reviewer names at collection. Never store emails, phone numbers or IDs of people.
- **Secrets never touch code or Git.** .env and .gitignore exist before the first commit. Check the repo online for .env before submission.
- **Cache every LLM answer** by a hash of model plus prompt, so reruns cost nothing.
- **Commit at every phase** with a message a non-engineer could understand.

### Stack: use exactly this, do not substitute

- Python 3.11, src/ layout, type hints, dataclasses, pathlib
- pandas, google-play-scraper, pyyaml, python-dotenv
- Groq API through the groq Python package (model name in .env as LLM_MODEL)
- rank_bm25 for retrieval; requests, beautifulsoup4, trafilatura for fetching official pages
- Streamlit for the app
- mcp (the official Python MCP SDK) for the client
- n8n (cloud) for the MCP server with Google Docs and Gmail tools
- pytest and ruff for tests and lint
- No LangChain, no vector database, no ORM, no authentication library
- Environment variables: GROQ_API_KEY, LLM_MODEL, N8N_MCP_URL, N8N_MCP_TOKEN, APPROVER_PASSWORD, DEMO_MODE

### What the code does vs what the AI does

**Code only:** collecting and cleaning, week bucketing, balancing (max 200 reviews per week), all counting, ranking top 3 by number of 1 and 2 star reviews in each theme, the tie-break rule, trends (last 4 weeks versus previous 4 weeks), word counting, copying quotes, substring verification, number validation against source text, hashing, approval checks, MCP call order, logging, the checks script.

**AI only:** proposing at most 5 themes from a mixed sample, assigning each review to one theme, labelling money-related reviews as confused / complaint_only / praise / unrelated plus a fee topic from a closed list, picking which review ID is the best quote, writing the one-sentence theme summaries and key observation and 3 action ideas, writing the fee bullets from retrieved chunks, and fact-checking each bullet against its single cited chunk.

**Ranking rule (write it into config before seeing results):** rank themes by count of 1 and 2 star reviews. Ties: higher share of 1 and 2 star reviews wins, then alphabetical by theme name. Never rank by total volume, because the biggest theme is usually happy users saying "nice app".

**Confusion versus complaint:** a review is "confused" only if the user does not understand what they were charged or why. "Too expensive" is complaint_only. The identified fee issue is the fee topic with the most confused reviews.

### Milestone M0 | Check my machine

Ask which operating system I use so every command matches it. Check that Python 3.11 or newer, pip, and git are installed. Print versions. If anything is missing, give the install command and stop. Then ask me to confirm I have accounts on GitHub, Groq and Google. Tell me not to start n8n yet. Wait until I say yes.

### Milestone M1 | Read the documents and save the rules

- Read docs/PRD.md and docs/architecture.md fully. Summarise both back to me in 10 lines or fewer, in plain English, and list any contradiction or gap you see.
- Create the project skeleton from the repository layout in docs/architecture.md section 3 (empty files are fine). Create .env.example, .gitignore (must list .env, .venv, data/cache/, __pycache__) and requirements.txt. Do this before any other commit.
- Create CLAUDE.md in the project root. Copy into it, word for word from this prompt: the Golden rules, the Stack, and "What the code does vs what the AI does".
- Create .cursor/rules/review-pulse.mdc with front matter containing a description and alwaysApply: true, and one instruction: "Read and follow CLAUDE.md and docs/implementation.md before every action."
- Explain what those two files are: the project's memory, so the rules survive when this chat gets long.
- Make the first Git commit and explain what a commit is in one sentence.

**Stop.**

### Milestone M2 | Write docs/implementation.md

This file is the execution plan. You will write it now, I will review it, and from M3 onward you execute it one phase at a time. Do not write product code in this milestone.

Create docs/implementation.md in the same style as the sample implementation plan I gave you (look in the reference folder if it exists). It must contain:

1. A header: title, "Based on: architecture.md and PRD.md", purpose, status line ("Not started"), last updated date.
2. **How to use this document**: implement one phase at a time; paste the phase's Cursor prompt; run the Verification yourself; tick the Acceptance criteria; commit with "phase N: name".
3. **Non-negotiable invariants** table with IDs: INV-1 code counts, AI never counts; INV-2 quotes verified verbatim; INV-3 fee facts only from sources.yaml pages; INV-4 approval hash re-checked before every write; INV-5 no send tool; INV-6 no PII; INV-7 no secrets in Git; INV-8 every LLM call cached; INV-9 pulse at most 250 words, explainer at most 6 bullets. Say in which phase each is enforced.
4. **Global conventions**: Python 3.11, src layout, type hints, dataclasses, config values in src/config.py, domain errors in src/errors.py, logging not print in library code, pathlib only, module docstring naming the architecture section it implements.
5. **Phases P0 to P12**, each with exactly these subsections: Goal, Architecture reference, Tasks (numbered, with file names and function names), Cursor prompt (a ready-to-paste blockquote), Verification (exact commands), Acceptance criteria (checkboxes), and "What I should learn here" (two sentences for a PM). Use this phase list:
   - P0 Scaffolding and environment (config, errors, logging, types, Makefile with install, collect, analyze, write, rag, checks, app, test, lint; tests/test_scaffolding.py)
   - P1 Review collection (scrape, clean, balanced file, keyword summary table)
   - P2 LLM layer and theme discovery (src/llm.py with ask_json, validation, retry, cache, rate-limit backoff; themes.json with at most 5 themes; assignments.csv)
   - P3 Counting, ranking, quotes, trends (insights.json; voice-related review tag count as a secondary lens; recompute-from-scratch test)
   - P4 Fee confusion detection (money filter, closed fee-topic list, stance labels, counts, identified fee issue). **Stop after P4 and ask me to fill config/sources.yaml with 4 to 6 official URLs. Do not guess URLs.**
   - P5 Weekly product pulse (skeleton by code, sentences by LLM, word-count loop up to 3 retries, four sections, 3 actions each tied to a quote)
   - P6 Fee explainer RAG (fetch, clean, chunk, BM25 index, retrieve, grounded bullets, code validators, second-LLM fact-checker, needs_human_review state, 2 source links, Last checked date)
   - P7 MCP server in n8n and MCP client test. **Contains a USER STEPS block** (create the Google Doc and copy its ID, start n8n trial, build an MCP Server Trigger with Bearer auth, add the three tools append_to_doc, read_doc, create_email_draft, with Doc ID and recipient fixed inside the nodes, no Send node, publish, put N8N_MCP_URL and N8N_MCP_TOKEN into .env myself). Then the client connection test that lists exactly three tools and fails if any name contains "send". Support both streamable HTTP and SSE transports.
   - P8 Approval gate and publishing (payload builder with the six Doc fields: date, top_themes, weekly_pulse, identified_fee_issue, explanation_bullets, source_links; email subject and body; SHA-256 hash; typed APPROVE; Reject with reason; fixed call order read_doc, hash check, append_to_doc, read_doc verify, hash check, create_email_draft; log after every step; resume without duplicates; friendly errors)
   - P9 Checks script (rule-based, no AI, independent checks, writes outputs/checks_report.md; includes bad-input tests: empty file, missing column, 20 rows, ratings 0 or "good", phone number inside a review, 20 weeks of data)
   - P10 Streamlit app (pages Overview, Insights, Weekly Pulse, Fee Explainer, Approve and Publish, Checks, About; DEMO_MODE; Approve page calls the same publish code as the CLI; wide tables scroll sideways on a phone; polite message when results are missing)
   - P11 Deployment. **Contains a USER STEPS block** (push to GitHub and check the repo online for .env, deploy on Streamlit Community Cloud, paste secrets into its secrets box, set DEMO_MODE=true, password on the Approve button). Commit the cached artifacts so the hosted app needs no LLM calls.
   - P12 Submission pack (README with how to run, where approval happens, which fee issue was identified; docs/sources.md with 4 to 6 URLs; sample CSV; pulse file; Doc entry screenshot instructions; Gmail draft screenshot instructions; 3-minute demo video script; final checklist)
6. **Appendix A**: phase dependency map. **Appendix B**: the .cursor rules file content. **Appendix C**: Definition of done, using the final checklist below.

Rules for writing the plan:
- Each phase prompt must tell the agent to stop and wait for "next" at the end.
- Each Verification must be runnable by me without reading code.
- Where I must do something outside the editor, use a clearly marked USER STEPS block.
- Do not write product code inside implementation.md, only instructions and short signatures.
- Keep the file under about 900 lines.

Then print a one-screen summary of the phases with time estimates. Ask me what to change.

**Stop. Do not start P0 until I say "next".**

### Milestone M3 onward | Execute implementation.md

After I approve implementation.md, work through P0 to P12 in order. For every phase:

1. Re-read the phase in docs/implementation.md and CLAUDE.md.
2. Explain in two or three sentences what you are about to build and why.
3. Build only that phase.
4. Run the phase's Verification commands yourself where possible, and show me the output.
5. Tell me exactly what to run or check on my side.
6. Update the status line and tick the Acceptance criteria in docs/implementation.md. If you deviated from the plan, record it in docs/implementation-notes.md with the reason.
7. Commit with "phase N: name".
8. Print "Phase N done. Say next to continue." and stop.

If a phase fails verification, do not move on. Show me the error in plain English, propose one fix, and wait.

### Design direction for the Streamlit app

Calm and evidence-first. White cards on a light grey page, dark navy headings (#0B3C49), teal links (#1F7A8C), thin borders. Status always shows an icon and a word, never colour alone. No emoji, no gradients. Every number on screen comes from a computed artifact, never typed into the UI code. Show source links and "Last checked" next to every fee fact. Footer on every page: "Built from public reviews and official pages. Facts only. Human-approved publishing."

### Final checklist (put in Appendix C)

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

Begin with M0.

## END OF PROMPT: STOP COPYING HERE
