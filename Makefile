# Review Pulse — common commands (P0 scaffolding)

.PHONY: install collect analyze write rag checks app test lint

PYTHON ?= python3
PIP ?= pip
PYTEST ?= pytest
RUFF ?= ruff

install:
	$(PYTHON) -m pip install -r requirements.txt

collect:
	@echo "not implemented (phase P1)"

analyze:
	@echo "not implemented (phase P2/P3/P4)"

write:
	@echo "not implemented (phase P5)"

rag:
	@echo "not implemented (phase P6)"

checks:
	@echo "not implemented (phase P9)"

app:
	@echo "not implemented (phase P10)"

test:
	PYTHONPATH=. $(PYTEST) tests/ -q

lint:
	$(RUFF) check src tests
