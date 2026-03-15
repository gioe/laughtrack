#!/usr/bin/env python3
"""
Backfill city and state for clubs where either column IS NULL.

Parses the stored address field (format: "Street, City, State ZIP") and
updates only rows that are still missing city or state — safe to re-run.

Usage:
    python scripts/utils/backfill_club_city_state.py
"""

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
_src_path = _repo_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger


def main() -> None:
    handler = ClubHandler()
    updated = handler.backfill_city_state()
    Logger.info(f"Done. Updated {updated} club(s).")


if __name__ == "__main__":
    main()
