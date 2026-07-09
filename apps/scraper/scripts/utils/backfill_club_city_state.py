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

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# Wire the concrete DB adapter into the base_handler seam. Needed here (not
# just scripts/__init__.py) because this script supports direct-file
# invocation (make run-script / python path/to/script.py), which never
# executes the scripts package init (TASK-3701).
import laughtrack.adapters.db  # noqa: F401  # isort: skip

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger


def main() -> None:
    handler = ClubHandler()
    updated = handler.backfill_city_state()
    Logger.info(f"Done. Updated {updated} club(s).")


if __name__ == "__main__":
    main()
