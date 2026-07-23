#!/usr/bin/env python3
"""
Refresh comedian social follower counts from external APIs.

Reads account handles stored on each Comedian row and fetches the current
follower / subscriber count from the corresponding platform API, then writes
the updated values back to the ``comedians`` table (partial update — only the
follower columns are touched).

Usage:
    python -m scripts.core.refresh_social_followers
    python -m scripts.core.refresh_social_followers --platform youtube
    python -m scripts.core.refresh_social_followers --platform instagram
    python -m scripts.core.refresh_social_followers --platform tiktok

Environment variables:
    YOUTUBE_API_KEY  YouTube Data API v3 key (required for YouTube refresh)
"""

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from laughtrack.core.entities.comedian.service import ComedianService
from laughtrack.foundation.infrastructure.logger.logger import Logger


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Laughtrack Social Follower Refresh — update comedian follower counts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Refresh all configured platforms
  %(prog)s --platform youtube   # Refresh YouTube only
  %(prog)s --platform instagram # Refresh Instagram only
  %(prog)s --platform instagram --ids-csv comedian_ids.csv
  %(prog)s --platform tiktok    # Refresh TikTok only
        """,
    )
    parser.add_argument(
        "--platform",
        choices=["youtube", "instagram", "tiktok", "all"],
        default="all",
        help="Platform to refresh (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N comedians (Instagram/YouTube; useful for smoke tests)",
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=None,
        help="Instagram/YouTube: skip comedians refreshed within this many days (default 7)",
    )
    parser.add_argument(
        "--ids-csv",
        type=Path,
        default=None,
        help="Instagram only: refresh exactly the numeric comedian IDs in a CSV with an id header",
    )
    return parser


def _read_comedian_ids_csv(path: Path) -> List[int]:
    """Read positive comedian IDs, preserving first-seen CSV order."""
    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None or "id" not in reader.fieldnames:
            raise ValueError("CSV must include an id header")

        comedian_ids: List[int] = []
        seen = set()
        for line_number, row in enumerate(reader, start=2):
            raw_id = (row.get("id") or "").strip()
            if not raw_id and not any(row.values()):
                continue
            if not raw_id.isascii() or not raw_id.isdecimal() or int(raw_id) <= 0:
                raise ValueError(f"CSV row {line_number} has an invalid comedian id: {raw_id!r}")
            comedian_id = int(raw_id)
            if comedian_id not in seen:
                seen.add(comedian_id)
                comedian_ids.append(comedian_id)

    if not comedian_ids:
        raise ValueError("CSV does not contain any comedian IDs")
    return comedian_ids


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    comedian_ids = None
    if args.ids_csv is not None:
        if args.platform != "instagram":
            parser.error("--ids-csv requires --platform instagram")
        if args.limit is not None or args.stale_days is not None:
            parser.error("--ids-csv cannot be combined with --limit or --stale-days")
        try:
            comedian_ids = _read_comedian_ids_csv(args.ids_csv)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))

    youtube_api_key = os.environ.get("YOUTUBE_API_KEY")

    try:
        service = ComedianService()

        if args.platform in ("youtube", "all"):
            if not youtube_api_key:
                Logger.warn("YOUTUBE_API_KEY not set — skipping YouTube follower refresh")
            else:
                updated = service.refresh_youtube_followers(
                    youtube_api_key, limit=args.limit, stale_days=args.stale_days
                )
                Logger.info(f"YouTube follower refresh complete: {updated} comedians updated")

        if args.platform in ("instagram", "all"):
            updated = service.refresh_instagram_followers(
                limit=args.limit,
                stale_days=args.stale_days,
                comedian_ids=comedian_ids,
            )
            Logger.info(f"Instagram follower refresh complete: {updated} comedians updated")

        if args.platform in ("tiktok", "all"):
            updated = service.refresh_tiktok_followers()
            Logger.info(f"TikTok follower refresh complete: {updated} comedians updated")

    except KeyboardInterrupt:
        Logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        Logger.error(f"Social follower refresh failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
