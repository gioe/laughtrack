"""CLI command: notify-comedian-arrivals

Sends email and push notifications to users when a comedian they follow has an upcoming
show within a configurable distance of their zip code.

Usage:
    python -m laughtrack.app.cli notify-comedian-arrivals [--radius MILES] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys

from laughtrack.core.services.notification.service import ComedianArrivalNotificationService
from laughtrack.foundation.infrastructure.logger.logger import Logger


def main(argv: list | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="notify-comedian-arrivals",
        description=(
            "Send email and push notifications when followed comedians have nearby upcoming shows."
        ),
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=50.0,
        metavar="MILES",
        help="Maximum distance in miles between user zip and club zip (default: 50.0).",
    )
    parser.add_argument(
        "--days-ahead",
        type=int,
        default=30,
        metavar="DAYS",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count matching notifications without sending emails, pushes, or sent-notification records.",
    )
    parser.add_argument(
        "--discovered-within-days",
        type=int,
        default=7,
        metavar="DAYS",
        help=(
            "Notify for unsent matching shows first discovered within this many days "
            "(default: 7)."
        ),
    )
    args = parser.parse_args(argv)

    Logger.info(
        f"notify-comedian-arrivals: starting with radius={args.radius} miles, "
        f"discovered_within_days={args.discovered_within_days}, dry_run={args.dry_run}"
    )

    service = ComedianArrivalNotificationService()
    summary = service.run(
        radius_miles=args.radius,
        discovered_within_days=args.discovered_within_days,
        dry_run=args.dry_run,
    )

    print(
        f"Done — candidates: {summary['candidates']}, "
        f"distance_filtered: {summary['distance_filtered']}, "
        f"emails_would_send: {summary['emails_would_send']}, "
        f"emails_sent: {summary['emails_sent']}, "
        f"push_candidates: {summary['push_candidates']}, "
        f"push_filtered: {summary['push_filtered']}, "
        f"push_would_send: {summary['push_would_send']}, "
        f"push_sent: {summary['push_sent']}, "
        f"push_errors: {summary['push_errors']}, "
        f"errors: {summary['errors']}"
    )

    if summary["errors"] > 0:
        Logger.warn(f"notify-comedian-arrivals: completed with {summary['errors']} error(s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
