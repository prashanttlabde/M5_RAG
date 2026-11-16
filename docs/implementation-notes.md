# Implementation notes (deviations from the plan)

## P0 — Scaffolding and environment

- Added `src/__init__.py` so `import src.config` works as a package.
- Added `pytest.ini` with `pythonpath = .` so tests resolve `src` without manual `PYTHONPATH` outside Make.
- Makefile `lint` runs full `ruff check src tests` (critical-select fallback removed after imports were clean).
