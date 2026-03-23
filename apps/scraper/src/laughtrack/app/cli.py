"""Unified CLI entry point for laughtrack scraper commands.

Usage:
    python -m laughtrack.app.cli <command> [args...]

Commands:
    audit-show    Dry-run lineup comparison for a specific show.
    manage-subscriptions  Manage email subscription tracking for clubs.

Run any command with --help for full usage details.
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="laughtrack.app.cli",
        description="LaughTrack scraper CLI.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    # --- audit-show ---
    audit_parser = subparsers.add_parser(
        "audit-show",
        help="Dry-run lineup comparison for a specific show.",
    )
    audit_parser.add_argument(
        "--show-id",
        type=int,
        required=True,
        metavar="N",
        help="Database ID of the show to audit.",
    )

    # --- manage-subscriptions (passthrough) ---
    subparsers.add_parser(
        "manage-subscriptions",
        help="Manage email subscription tracking for clubs.",
        add_help=False,  # delegate help to the sub-command's own parser
    )

    # Parse only the top-level command; leave the rest for sub-command parsers.
    args, remaining = parser.parse_known_args()

    if args.command == "audit-show":
        from laughtrack.app.commands.audit_show import main as _audit_main
        _audit_main(["--show-id", str(args.show_id)] + remaining)

    elif args.command == "manage-subscriptions":
        from laughtrack.app.commands.manage_subscriptions import main as _subs_main
        _subs_main(remaining)


if __name__ == "__main__":
    main()
