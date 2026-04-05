#!/usr/bin/env python3
"""
Entry point for scraping comedian personal websites for tour dates.

Fetches comedian websites with JSON-LD Event markup, extracts show data,
upserts venues, and persists Show + LineupItem records.

Usage:
    python -m scripts.core.scrape_comedian_websites --all
    python -m scripts.core.scrape_comedian_websites --comedian-name "John Mulaney"
    python -m scripts.core.scrape_comedian_websites --limit 10
    python -m scripts.core.scrape_comedian_websites --dry-run --all
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
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger


def main():
    """Main entry point for comedian website scraping."""
    parser = argparse.ArgumentParser(
        description="Scrape comedian personal websites for tour dates via JSON-LD",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--all", action="store_true", help="Scrape all comedians with websites needing refresh")
    parser.add_argument("--comedian-name", type=str, help="Scrape a specific comedian by name (partial match)")
    parser.add_argument("--limit", type=int, help="Limit the number of comedians to process")
    parser.add_argument("--dry-run", action="store_true", help="List comedians that would be scraped without fetching")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show INFO-level logs")
    parser.add_argument("--debug", action="store_true", help="Show DEBUG-level logs")

    args = parser.parse_args()

    # Configure logging
    if args.debug:
        os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "DEBUG"
    elif args.verbose:
        current = os.environ.get("LAUGHTRACK_LOG_CONSOLE_LEVEL", "").upper()
        if current not in ("DEBUG", "INFO"):
            os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "INFO"

    if not args.all and not args.comedian_name:
        parser.error("Either --all or --comedian-name is required")

    try:
        # Find the synthetic club row that triggers this scraper
        club_handler = ClubHandler()
        clubs = club_handler.get_clubs_for_scraper("comedian_websites")
        if not clubs:
            Logger.error("No club row with scraper='comedian_websites' found. Insert one first.")
            sys.exit(1)
        club = clubs[0]

        # Import scraper after path setup
        from laughtrack.scrapers.implementations.api.comedian_websites.scraper import ComedianWebsiteScraper

        scraper = ComedianWebsiteScraper(club, comedian_name=args.comedian_name, limit=args.limit)

        # Get the list of comedians that would be scraped
        comedians = scraper._get_comedians_for_scraping(
            limit=args.limit,
            comedian_name=args.comedian_name,
        )

        if not comedians:
            Logger.info("No comedians found matching criteria.")
            return

        if args.dry_run:
            print(f"\n{'='*60}")
            print(f"DRY RUN: {len(comedians)} comedian(s) would be scraped")
            print(f"{'='*60}")
            for c in comedians:
                last = c.get("website_last_scraped") or "never"
                strategy = c.get("website_scrape_strategy") or "unknown"
                print(f"  {c['name']:40s}  {c['website']:50s}  last={last}  strategy={strategy}")
            print(f"{'='*60}\n")
            return

        # Run the scrape
        Logger.info(f"Scraping websites for {len(comedians)} comedians...")
        shows = scraper.scrape()
        Logger.info(f"Done — {len(shows)} shows discovered from comedian websites.")

    except KeyboardInterrupt:
        Logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        Logger.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
