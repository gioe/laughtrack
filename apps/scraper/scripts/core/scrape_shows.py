#!/usr/bin/env python3
"""
Main entry point for the Laughtrack Scraper.

This script serves as the primary interface for scraping comedy shows from various venues.
It provides both a command-line interface and functions that can be imported by other modules.

Usage:
    ./scrape_shows.py [options]

Examples:
    ./scrape_shows.py --all                          # Scrape all configured clubs
    ./scrape_shows.py --club-id 5                    # Scrape a specific club by ID
    ./scrape_shows.py --scraper-type json_ld         # Scrape all clubs using json_ld
    ./scrape_shows.py --scraper-type-interactive     # Interactive selection of scraper type(s)
    ./scrape_shows.py --list-scrapers                # List available scraper types
    ./scrape_shows.py --list-clubs                   # List all clubs with IDs and names
    ./scrape_shows.py                                # Interactive club selection
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure local 'src' package path takes precedence over any installed package
_repo_root = Path(__file__).resolve().parents[2]
_src_path = _repo_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))
# Also add the repository root so we can import from the local 'scripts' package
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from laughtrack.core.entities.club.service import ClubService
from laughtrack.core.entities.scraper.service import ScraperService
from laughtrack.core.services.scraping import ScrapingService
from laughtrack.app.commands.scrape_all import run as run_scrape_all
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.core.services.metrics import MetricsService


def main():
    """Main entry point for the scraping script."""
    parser = argparse.ArgumentParser(
        description="Laughtrack Scraper - Main entry point for scraping comedy shows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                          # Scrape all configured clubs
  %(prog)s --club-id 5                    # Scrape a specific club by ID
  %(prog)s --scraper-type json_ld         # Scrape all clubs using json_ld
  %(prog)s --scraper-type-interactive     # Interactive selection of scraper type(s)
  %(prog)s --list-scrapers                # List available scraper types
  %(prog)s --list-clubs                   # List all clubs with IDs and names
  %(prog)s                                # Interactive club selection
        """,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Scrape all configured clubs")
    group.add_argument("--club-id", type=int, help="ID of specific club to scrape")
    group.add_argument("--club", type=str, help="Name of specific club to scrape (case-insensitive, partial match supported)")
    group.add_argument(
        "--scraper-type", type=str, help="Scrape all clubs using a specific scraper type (e.g., json_ld)"
    )
    group.add_argument(
        "--scraper-type-interactive",
        action="store_true",
        help="Interactive selection of scraper type(s) to scrape all clubs of that type",
    )
    group.add_argument(
        "--list-scrapers", action="store_true", help="List available scraper types and their club counts"
    )
    group.add_argument("--list-clubs", action="store_true", help="List all available clubs with their IDs and names")

    # Verbosity controls for console logging
    parser.add_argument("-v", "--verbose", action="store_true", help="Show INFO-level logs in the terminal")
    parser.add_argument("--debug", action="store_true", help="Show DEBUG-level logs in the terminal")
    parser.add_argument(
        "--open-dashboard",
        action="store_true",
        help="After scraping completes, generate and open the HTML dashboard with analysis",
    )

    args = parser.parse_args()

    # Ensure console logging is configured before any logger is created/used
    # Defaults are WARNING to keep noise low; enable INFO/DEBUG when requested.
    # IMPORTANT: If the environment already requested DEBUG (e.g., via `make ... --debug`),
    # don't downgrade it just because --verbose is present in Makefile targets.
    current_console_level = os.environ.get("LAUGHTRACK_LOG_CONSOLE_LEVEL", "").upper()
    if args.debug:
        os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "DEBUG"
    elif args.verbose:
        # Only raise to INFO if no stronger setting (DEBUG) is already in effect
        if current_console_level not in ("DEBUG", "INFO"):
            os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "INFO"

    scraping_service = ScrapingService()
    club_service = ClubService()
    scraper_service = ScraperService()
    metrics_service = MetricsService()

    try:
        # Perform the primary action (scrape/list). "--open-dashboard" is an optional post-action flag
        # and should not short‑circuit other actions when combined.
        performed_primary = False
        if args.all:
            scraping_service.scrape_all_clubs(); performed_primary = True
        elif args.club_id:
            scraping_service.scrape_single_club(club_id=args.club_id); performed_primary = True
        elif args.club:
            club = club_service.find_club_by_name(args.club)
            if club is None:
                sys.exit(1)
            scraping_service.scrape_single_club(club_id=club.id); performed_primary = True
        elif args.scraper_type:
            scraping_service.scrape_by_scraper_type(args.scraper_type); performed_primary = True
        elif args.scraper_type_interactive:
            scraping_service.scrape_by_scraper_type(); performed_primary = True
        elif args.list_scrapers:
            scraper_service.list_available_scraper_types(); performed_primary = True
        elif args.list_clubs:
            club_service.list_available_clubs(); performed_primary = True
        elif args.open_dashboard:
            # Allow opening the dashboard without scraping anything.
            metrics_service.open_dashboard(open_in_browser=True); performed_primary = True
        if not performed_primary:
            Logger.info("Starting interactive club selection...")
            scraping_service.scrape_single_club()

        # If user requested dashboard opening (and it wasn't the sole primary action) do it after scraping.
        if args.open_dashboard and not (args.list_scrapers or args.list_clubs):
            # For list operations we already opened if requested above.
            if not (args.open_dashboard and not performed_primary):
                metrics_service.open_dashboard(open_in_browser=True)

    except KeyboardInterrupt:
        Logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        Logger.error(f"An error occurred while scraping: {e}")
        sys.exit(1)


# For backward compatibility - standalone script functionality
if __name__ == "__main__":
    main()
