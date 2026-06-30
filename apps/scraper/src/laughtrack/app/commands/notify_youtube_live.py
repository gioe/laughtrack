"""CLI command: notify-youtube-live

Sends push notifications to followers when verified YouTube WebSub events are live.
"""

from __future__ import annotations

import argparse
import sys

from laughtrack.core.services.notification.service import YouTubeLiveNotificationService
from laughtrack.foundation.infrastructure.logger.logger import Logger


def main(argv: list | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="notify-youtube-live",
        description="Send push notifications for verified-live YouTube WebSub events.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        metavar="N",
        help="Maximum verified-live WebSub events to process (default: 50).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count matching pushes and validate provider config without sending or recording.",
    )
    args = parser.parse_args(argv)

    Logger.info(f"notify-youtube-live: starting with limit={args.limit}, dry_run={args.dry_run}")

    service = YouTubeLiveNotificationService()
    summary = service.run(limit=args.limit, dry_run=args.dry_run)

    print(
        f"Done — global_gated: {summary['global_gated']}, "
        f"candidates: {summary['candidates']}, "
        f"push_would_send: {summary['push_would_send']}, "
        f"push_sent: {summary['push_sent']}, "
        f"push_errors: {summary['push_errors']}, "
        f"duplicates: {summary['duplicates']}, "
        f"errors: {summary['errors']}"
    )

    if summary["errors"] > 0:
        Logger.warn(f"notify-youtube-live: completed with {summary['errors']} error(s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
