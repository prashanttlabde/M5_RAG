"""Implements architecture §9 CLI entry: build payload -> human gate -> publish.

Run: python -m src.approval
"""

from __future__ import annotations

import sys

from src.approval import gate, publish
from src.approval.payload import build_payload
from src.errors import ReviewPulseError
from src.logging_config import setup_logging


def main() -> int:
    setup_logging()
    try:
        payload = build_payload()
        publish.ensure_publishable(payload)
        if gate.run_cli(payload) != "approved":
            return 0
        result = publish.publish_sync(payload, payload["hash"])
    except ReviewPulseError as exc:
        print("STOPPED:", exc)
        return 1
    print("Already published earlier; nothing new written." if result == "already_done" else
          "Done: Doc entry written and verified; Gmail draft created (not sent).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
