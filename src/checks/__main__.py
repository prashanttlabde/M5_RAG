"""Implements architecture §12 entry point for `make checks`."""

from __future__ import annotations

import sys

from src.checks.run_checks import main

if __name__ == "__main__":
    sys.exit(main())
