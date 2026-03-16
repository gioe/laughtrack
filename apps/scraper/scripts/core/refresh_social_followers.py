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

Environment variables:
    YOUTUBE_API_KEY  YouTube Data API v3 key (required for YouTube refresh)
"""

import argparse
import os
import sys

from laughtrack.domain.entities.comedian import ComedianService
from laughtrack.foundation.infrastructure.logger.logger import Logger


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Laughtrack Social Follower Refresh — update comedian follower counts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Refresh all configured platforms
  %(prog)s --platform youtube  # Refresh YouTube only
        """,
    )
    parser.add_argument(
        "--platform",
        choices=["youtube", "all"],
        default="all",
        help="Platform to refresh (default: all)",
    )
    args = parser.parse_args()

    youtube_api_key = os.environ.get("YOUTUBE_API_KEY")

    try:
        service = ComedianService()

        if args.platform in ("youtube", "all"):
            if not youtube_api_key:
                Logger.warn("YOUTUBE_API_KEY not set — skipping YouTube follower refresh")
            else:
                updated = service.refresh_youtube_followers(youtube_api_key)
                Logger.info(f"YouTube follower refresh complete: {updated} comedians updated")

    except KeyboardInterrupt:
        Logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        Logger.error(f"Social follower refresh failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
