#!/usr/bin/env python3
"""
Popularity update utilities for the Laughtrack scraper.

This script serves as the primary interface for updating popularity scores for
comedians, shows, and clubs.  It provides both a command-line interface and
functions that can be imported by other modules.

Usage:
    ./update_popularity.py [options]

Examples:
    ./update_popularity.py                           # Update popularity for all comedians, shows, and clubs
    ./update_popularity.py --comedians               # Update all comedians only
    ./update_popularity.py --shows                   # Update all shows only
    ./update_popularity.py --clubs                   # Update all clubs only
    ./update_popularity.py --comedians uuid1 uuid2   # Update specific comedians
    ./update_popularity.py --shows 123 456           # Update specific shows
    ./update_popularity.py --clubs 12 34             # Update specific clubs
"""

import argparse
import sys

from laughtrack.domain.entities.club import ClubService
from laughtrack.domain.entities.comedian import ComedianService
from laughtrack.domain.entities.show import ShowService
from laughtrack.foundation.infrastructure.logger.logger import Logger

def main():
    """Main entry point for the popularity update script."""
    parser = argparse.ArgumentParser(
        description="Laughtrack Popularity Update - Update popularity scores for comedians, shows, and clubs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Update popularity for all comedians, shows, and clubs
  %(prog)s --comedians               # Update all comedians only
  %(prog)s --shows                   # Update all shows only
  %(prog)s --clubs                   # Update all clubs only
  %(prog)s --comedians 1 2           # Update specific comedians
  %(prog)s --shows 123 456           # Update specific shows
  %(prog)s --clubs 12 34             # Update specific clubs
        """,
    )

    parser.add_argument(
        "--comedians", nargs="*", help="Update comedian popularity. If no values provided, updates all comedians."
    )
    parser.add_argument(
        "--shows", nargs="*", type=int, help="Update show popularity. If no values provided, updates all shows."
    )
    parser.add_argument(
        "--clubs", nargs="*", type=int, help="Update club popularity. If no values provided, updates all clubs."
    )

    args = parser.parse_args()

    # Convert empty lists to None to indicate "update all"
    comedian_ids = args.comedians if args.comedians is not None and args.comedians else None
    show_ids = args.shows if args.shows is not None and args.shows else None
    club_ids = args.clubs if args.clubs is not None and args.clubs else None

    # Track which flags were explicitly passed (distinct from empty-list → None)
    comedians_requested = args.comedians is not None
    shows_requested = args.shows is not None
    clubs_requested = args.clubs is not None

    try:
        comedian_service = ComedianService()
        show_service = ShowService()
        club_service = ClubService()

        # Club popularity depends on comedian popularity (via lineup aggregation)
        # and show popularity depends on comedian popularity (via lineup), so
        # always run comedians → shows → clubs when any combination is requested.

        if comedians_requested:
            comedian_service.update_comedian_popularity(comedian_ids)

        if shows_requested:
            show_service.update_show_popularity(show_ids)

        if clubs_requested:
            club_service.update_club_popularity(club_ids)

        # If no flag was provided, update everything
        if not (comedians_requested or shows_requested or clubs_requested):
            comedian_service.update_comedian_popularity()
            show_service.update_show_popularity()
            club_service.update_club_popularity()

    except KeyboardInterrupt:
        Logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        Logger.error(f"An error occurred while updating popularity: {e}")
        sys.exit(1)


# For backward compatibility - standalone script functionality
if __name__ == "__main__":
    main()
