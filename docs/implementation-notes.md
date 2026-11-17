# Implementation notes (deviations from the plan)

## P0 — Scaffolding and environment

- Added `src/__init__.py` so `import src.config` works as a package.
- Added `pytest.ini` with `pythonpath = .` so tests resolve `src` without manual `PYTHONPATH` outside Make.
- Makefile `lint` runs full `ruff check src tests` (critical-select fallback removed after imports were clean).

## P1 — Review collection

- A flat newest-first scrape hit 8000 reviews in ~2 days (ChatGPT India volume). Switched to per-star-rating scrapes with week thinning.
- Scores 1–2 paginate until the 12-week cutoff (keeping ≤250/week/score while advancing the token). Scores 3–5 use capped recent samples so praise volume does not dominate runtime.
- Result after clean: **3107** full reviews, **2377** balanced, **12** weeks (2026-08-24 … 2026-11-09 week starts), max 200/week.
- Intermediate `data/reviews_raw.csv` is gitignored; cleaned CSVs are the source of truth.
- Keyword hits on full set: subscription 77, plan 22, price 11, refund 9, charge 5, renew 2, billing 1, GST 0, tax 0.
