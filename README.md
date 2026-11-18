# Review Pulse for ChatGPT

Turns public Google Play reviews of the ChatGPT app (India, English) into a weekly product pulse, a plain-language
fee explainer grounded in official pages, and a human-approved Google Doc entry plus Gmail **draft**.
Code counts, the AI only sorts and writes; nothing is ever sent. (Full write-up comes in the submission pack.)

## Run it locally

```bash
python3 -m venv .venv && source .venv/bin/activate && make install
cp .env.example .env        # then fill in the values yourself; never commit .env
make collect                # reviews -> data/*.csv
make analyze                # themes, ranking, quotes, fee labels -> data/insights.json
make write                  # outputs/weekly_pulse.md
make rag                    # outputs/fee_explainer.md (official pages in config/sources.yaml only)
make checks                 # rule-based checks -> outputs/checks_report.md
make app                    # Streamlit app on a local URL
python -m src.approval      # approve (type APPROVE) and publish from the command line
```

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub and confirm `.env` is **not** in the file list.
2. On https://share.streamlit.io choose **New app**, pick the repo, and set the main file to `app/streamlit_app.py`.
3. In **Advanced settings** pick Python 3.12 or 3.13 and paste your secrets (never commit them):
   `LLM_MODEL`, `N8N_MCP_URL`, `N8N_MCP_TOKEN`, `APPROVER_PASSWORD`, `DEMO_MODE = "true"`
   (`GROQ_API_KEY` is only needed if you turn demo mode off).
4. With `DEMO_MODE=true` the app reads the saved results in `data/` and `outputs/` and makes no AI calls.
   The host's file system is not persistent, so publish logs written there last only for the session.

## What is committed for the demo

Cleaned public reviews (no reviewer names, phone/email-like text redacted), theme assignments, `insights.json`,
the pulse, the fee explainer and its source chunks, the checks report, the approval payload and the publish log.
Not committed: `.env`, the LLM cache, and the raw downloaded help pages (`make rag` re-downloads them).
