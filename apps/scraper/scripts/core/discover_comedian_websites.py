#!/usr/bin/env python3
"""
Discover comedian websites via Google Custom Search.

Finds official websites for comedians who don't have one yet, prioritized
by popularity (highest first). Respects the Google Custom Search free tier
(100 queries/day).

Usage:
    python -m scripts.core.discover_comedian_websites --limit 10
    python -m scripts.core.discover_comedian_websites --limit 50 --dry-run
    python -m scripts.core.discover_comedian_websites --comedian-name "John Mulaney"
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

from laughtrack.foundation.infrastructure.logger.logger import Logger


def main():
    parser = argparse.ArgumentParser(
        description="Discover comedian websites via Google Custom Search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--limit", type=int, help="Maximum number of comedians to process (default: remaining daily quota)")
    parser.add_argument("--dry-run", action="store_true", help="Search but don't write to the database")
    parser.add_argument("--comedian-name", type=str, help="Process a specific comedian by name (partial match)")
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

    try:
        from laughtrack.core.services.enrichment.website_discovery import discover_websites

        results = discover_websites(
            limit=args.limit,
            dry_run=args.dry_run,
            comedian_name=args.comedian_name,
        )

        found = [r for r in results if r.website]
        skipped = [r for r in results if r.skipped]

        if args.dry_run and found:
            print(f"\n{'='*60}")
            print(f"DRY RUN — {len(found)} websites would be written:")
            print(f"{'='*60}")
            for r in found:
                print(f"  {r.name} → {r.website}")

        if skipped and args.debug:
            print(f"\nSkipped ({len(skipped)}):")
            for r in skipped:
                print(f"  {r.name}: {r.reason}")

    except KeyboardInterrupt:
        Logger.info("Operation cancelled")
        sys.exit(0)
    except Exception as e:
        Logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
