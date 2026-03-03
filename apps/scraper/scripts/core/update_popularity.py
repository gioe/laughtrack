#!/usr/bin/env python3
"""
Popularity update utilities for the Laughtrack scraper.

This script serves as the primary interface for updating popularity scores for comedians and shows.
It provides both a command-line interface and functions that can be imported by other modules.

Usage:
    ./update_popularity.py [options]

Examples:
    ./update_popularity.py                           # Update popularity for all comedians and shows
    ./update_popularity.py --comedians               # Update all comedians only
    ./update_popularity.py --shows                   # Update all shows only
    ./update_popularity.py --comedians uuid1 uuid2  # Update specific comedians
    ./update_popularity.py --shows 123 456          # Update specific shows
"""

import argparse
import sys

from laughtrack.domain.entities.comedian import ComedianService
from laughtrack.domain.entities.show import ShowService
from laughtrack.foundation.infrastructure.logger.logger import Logger

def main():
    """Main entry point for the popularity update script."""
    parser = argparse.ArgumentParser(
        description="Laughtrack Popularity Update - Update popularity scores for comedians and shows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Update popularity for all comedians and shows
  %(prog)s --comedians               # Update all comedians only
  %(prog)s --shows                   # Update all shows only
  %(prog)s --comedians 1 2           # Update specific comedians
  %(prog)s --shows 123 456           # Update specific shows
        """,
    )

    parser.add_argument(
        "--comedians", nargs="*", help="Update comedian popularity. If no values provided, updates all comedians."
    )
    parser.add_argument(
        "--shows", nargs="*", type=int, help="Update show popularity. If no values provided, updates all shows."
    )

    args = parser.parse_args()

    # Convert empty lists to None to indicate "update all"
    comedian_ids = args.comedians if args.comedians is not None and args.comedians else None
    show_ids = args.shows if args.shows is not None and args.shows else None

    try:
        comedian_service = ComedianService()
        show_service = ShowService()

        if comedian_ids is not None:
            comedian_service.update_comedian_popularity(comedian_ids)

        # Update show popularity if show_ids is provided
        if show_ids is not None:
            show_service.update_show_popularity(show_ids)

        # If neither argument was provided, update both
        if comedian_ids is None and show_ids is None:
            comedian_service.update_comedian_popularity()
            show_service.update_show_popularity()

    except KeyboardInterrupt:
        Logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        Logger.error(f"An error occurred while updating popularity: {e}")
        sys.exit(1)


# For backward compatibility - standalone script functionality
if __name__ == "__main__":
    main()
