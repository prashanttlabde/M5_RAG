# CLAUDE.md — Review Pulse project memory

Follow these rules for the entire session. If this file and a chat message disagree, this file wins unless the human says otherwise.

## Golden rules

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

## Stack: use exactly this, do not substitute

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

## What the code does vs what the AI does

**Code only:** collecting and cleaning, week bucketing, balancing (max 200 reviews per week), all counting, ranking top 3 by number of 1 and 2 star reviews in each theme, the tie-break rule, trends (last 4 weeks versus previous 4 weeks), word counting, copying quotes, substring verification, number validation against source text, hashing, approval checks, MCP call order, logging, the checks script.

**AI only:** proposing at most 5 themes from a mixed sample, assigning each review to one theme, labelling money-related reviews as confused / complaint_only / praise / unrelated plus a fee topic from a closed list, picking which review ID is the best quote, writing the one-sentence theme summaries and key observation and 3 action ideas, writing the fee bullets from retrieved chunks, and fact-checking each bullet against its single cited chunk.

**Ranking rule (write it into config before seeing results):** rank themes by count of 1 and 2 star reviews. Ties: higher share of 1 and 2 star reviews wins, then alphabetical by theme name. Never rank by total volume, because the biggest theme is usually happy users saying "nice app".

**Confusion versus complaint:** a review is "confused" only if the user does not understand what they were charged or why. "Too expensive" is complaint_only. The identified fee issue is the fee topic with the most confused reviews.
