"""CLI command: notify-comedian-arrivals

Sends notification emails to users when a comedian they follow has an upcoming
show within a configurable distance of their zip code.

Usage:
    python -m laughtrack.app.cli notify-comedian-arrivals [--radius MILES] [--days-ahead DAYS]
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
            "Send notification emails when followed comedians have nearby upcoming shows."
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
        help="Number of days ahead to look for upcoming shows (default: 30).",
    )
    args = parser.parse_args(argv)

    Logger.info(
        f"notify-comedian-arrivals: starting with radius={args.radius} miles, "
        f"days_ahead={args.days_ahead}"
    )

    service = ComedianArrivalNotificationService()
    summary = service.run(radius_miles=args.radius, days_ahead=args.days_ahead)

    print(
        f"Done — candidates: {summary['candidates']}, "
        f"distance_filtered: {summary['distance_filtered']}, "
        f"emails_sent: {summary['emails_sent']}, "
        f"errors: {summary['errors']}"
    )

    if summary["errors"] > 0:
        Logger.warn(f"notify-comedian-arrivals: completed with {summary['errors']} error(s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
