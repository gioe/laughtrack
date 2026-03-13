#!/usr/bin/env python3
"""
Enrich timezone for clubs where timezone IS NULL.

Queries clubs matching the given scraper type with a null timezone,
infers the timezone from the stored address, and updates only rows
that are still NULL — safe to re-run at any time.

Usage:
    python scripts/utils/enrich_club_timezones.py
    python scripts/utils/enrich_club_timezones.py --scraper seatengine
"""

import argparse
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
    parser = argparse.ArgumentParser(
        description="Enrich club timezones inferred from stored address data"
    )
    parser.add_argument(
        "--scraper",
        default="eventbrite",
        help="Scraper type to filter clubs by (default: eventbrite)",
    )
    args = parser.parse_args()

    handler = ClubHandler()
    updated = handler.enrich_timezones(scraper=args.scraper)
    Logger.info(f"Done. Updated {updated} club(s).")


if __name__ == "__main__":
    main()
