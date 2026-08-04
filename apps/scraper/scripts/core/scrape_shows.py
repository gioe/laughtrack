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
    ./scrape_shows.py --club "Comedy Cellar"         # Scrape by name (partial match supported)
    ./scrape_shows.py --scraper-type json_ld         # Scrape all clubs using json_ld
    ./scrape_shows.py --scraper-type-interactive     # Interactive selection of scraper type(s)
    ./scrape_shows.py --list-scrapers                # List available scraper types
    ./scrape_shows.py --list-clubs                   # List all clubs with IDs and names
    ./scrape_shows.py                                # Interactive club selection
"""

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

# Locate scraper root (apps/scraper/) by walking up to pyproject.toml, then
# put src/ + scraper root on sys.path so laughtrack and 'scripts' package imports resolve.
_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.core.clients.eventbrite.health import validate_eventbrite_token
from laughtrack.core.entities.club.service import ClubService
from laughtrack.core.entities.scraper.service import ScraperService
from laughtrack.core.services.scraping import ScrapingService
from laughtrack.app.commands.scrape_all import run as run_scrape_all
from laughtrack.foundation.infrastructure.http import scraper_proxy_registry
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.core.services.metrics import MetricsService
from laughtrack.core.models.metrics import ScrapingMetricsSnapshot
from laughtrack.core.models.metrics_snapshot import ClubsBlock, ErrorsBlock, SessionBlock, ShowsBlock
from laughtrack.utilities.domain.club.coordinates import geocode_missing_clubs


def _club_uses_eventbrite(club) -> bool:
    active_source = getattr(club, "active_scraping_source", None)
    platform = getattr(active_source, "platform", None) or getattr(club, "scraper", None)
    scraper_key = getattr(active_source, "scraper_key", None)
    return (
        str(platform or "").startswith("eventbrite")
        or str(scraper_key or "").startswith("eventbrite")
    )


def _merge_partition_snapshots(
    metrics_root: Path, expected_partitions: int
) -> ScrapingMetricsSnapshot:
    """Combine one metrics snapshot per completed partition into a full run."""
    metric_files = sorted(metrics_root.glob("**/metrics_*.json"))
    snapshots = [ScrapingMetricsSnapshot.from_file(path) for path in metric_files]
    snapshots = [snapshot for snapshot in snapshots if snapshot is not None]
    if len(snapshots) != expected_partitions:
        raise ValueError(
            f"Expected {expected_partitions} partition metrics snapshots, "
            f"found {len(snapshots)} under {metrics_root}"
        )
    if any(snapshot.run_type != "scraper_partition" for snapshot in snapshots):
        raise ValueError("Every partition snapshot must use run_type=scraper_partition")

    now = dt.datetime.now(dt.timezone.utc)
    shows_scraped = sum(snapshot.shows.scraped for snapshot in snapshots)
    shows_saved = sum(snapshot.shows.saved for snapshot in snapshots)
    return ScrapingMetricsSnapshot(
        timestamp=now.isoformat(),
        datetime=now,
        session=SessionBlock(
            duration_seconds=sum(snapshot.session.duration_seconds for snapshot in snapshots),
            exported_at=now.isoformat(),
        ),
        shows=ShowsBlock(
            scraped=shows_scraped,
            saved=shows_saved,
            inserted=sum(snapshot.shows.inserted for snapshot in snapshots),
            updated=sum(snapshot.shows.updated for snapshot in snapshots),
            failed_save=sum(snapshot.shows.failed_save for snapshot in snapshots),
            skipped_dedup=sum(snapshot.shows.skipped_dedup for snapshot in snapshots),
            validation_failed=sum(snapshot.shows.validation_failed for snapshot in snapshots),
            db_errors=sum(snapshot.shows.db_errors for snapshot in snapshots),
        ),
        clubs=ClubsBlock(
            processed=sum(snapshot.clubs.processed for snapshot in snapshots),
            successful=sum(snapshot.clubs.successful for snapshot in snapshots),
            failed=sum(snapshot.clubs.failed for snapshot in snapshots),
        ),
        errors=ErrorsBlock(total=sum(snapshot.errors.total for snapshot in snapshots)),
        success_rate=(shows_saved / shows_scraped * 100.0) if shows_scraped else 0.0,
        execution_times=[value for snapshot in snapshots for value in snapshot.execution_times],
        per_club_stats=[stat for snapshot in snapshots for stat in snapshot.per_club_stats],
        error_details=[error for snapshot in snapshots for error in snapshot.error_details],
        duplicate_show_details=[
            duplicate
            for snapshot in snapshots
            for duplicate in snapshot.duplicate_show_details
        ],
        run_type="scraper",
    )


def _finalize_partition_metrics(
    metrics_root: Path,
    expected_partitions: int,
    metrics_service: MetricsService,
    club_service: ClubService,
) -> None:
    """Publish the canonical full snapshot after every partition completed."""
    snapshot = _merge_partition_snapshots(metrics_root, expected_partitions)
    metrics_service._render_and_save_dashboard(snapshot)
    metrics_service._persist_snapshot_json(snapshot)
    if not metrics_service._persist_snapshot_postgres(snapshot):
        raise RuntimeError("Failed to persist merged scraper metrics snapshot")
    club_service.club_handler.refresh_club_total_shows()
    try:
        result = geocode_missing_clubs()
        Logger.info(
            "Club geocoding post-partitions: "
            f"attempted={result.attempted}, resolved={result.resolved}, "
            f"unresolved={result.unresolved}"
        )
    except Exception as exc:
        Logger.warn(
            f"Club geocoding post-partitions failed; finalization will continue: {exc}"
        )


def main():
    """Main entry point for the scraping script."""
    parser = argparse.ArgumentParser(
        description="Laughtrack Scraper - Main entry point for scraping comedy shows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                          # Scrape all configured clubs
  %(prog)s --club-id 5                    # Scrape a specific club by ID
  %(prog)s --club "Comedy Cellar"         # Scrape by name (partial match supported)
  %(prog)s --scraper-type json_ld         # Scrape all clubs using json_ld
  %(prog)s --scraper-type-interactive     # Interactive selection of scraper type(s)
  %(prog)s --list-scrapers                # List available scraper types
  %(prog)s --list-clubs                   # List all clubs with IDs and names
  %(prog)s                                # Interactive club selection
        """,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Scrape all configured clubs")
    group.add_argument(
        "--merge-partition-metrics",
        type=Path,
        help="Merge completed partition metrics under this directory into one full run",
    )
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
    group.add_argument("--list-clubs-json", action="store_true", help="Output all clubs as JSON (name, city, state, website)")

    parser.add_argument("--partition-index", type=int, help="Zero-based partition to scrape")
    parser.add_argument("--partition-count", type=int, help="Total deterministic scrape partitions")
    parser.add_argument(
        "--expected-partitions",
        type=int,
        help="Expected snapshot count for --merge-partition-metrics",
    )

    # Verbosity controls for console logging
    parser.add_argument("-v", "--verbose", action="store_true", help="Show INFO-level logs in the terminal")
    parser.add_argument("--debug", action="store_true", help="Show DEBUG-level logs in the terminal")
    parser.add_argument(
        "--open-dashboard",
        action="store_true",
        help="After scraping completes, generate and open the HTML dashboard with analysis",
    )

    args = parser.parse_args()

    partition_args_present = args.partition_index is not None or args.partition_count is not None
    if partition_args_present:
        if not args.all or args.partition_index is None or args.partition_count is None:
            parser.error("--partition-index and --partition-count must be used together with --all")
        if args.partition_count < 1 or not 0 <= args.partition_index < args.partition_count:
            parser.error("partition index must be in the range [0, partition count)")
    if args.merge_partition_metrics is not None:
        if args.expected_partitions is None or args.expected_partitions < 1:
            parser.error("--merge-partition-metrics requires --expected-partitions >= 1")
    elif args.expected_partitions is not None:
        parser.error("--expected-partitions requires --merge-partition-metrics")

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

    # Fail fast on bad/missing EVENTBRITE_PRIVATE_TOKEN before any per-venue
    # work, so a stale GHA secret produces one loud ERROR instead of ~27
    # silent 401 WARNs scattered across every Eventbrite-backed venue.
    # Skip pure listing/dashboard commands — they don't hit the API.
    listing_only = args.list_scrapers or args.list_clubs or args.list_clubs_json
    maintenance_only = args.merge_partition_metrics is not None
    will_scrape = (
        args.all
        or args.club_id
        or args.club
        or args.scraper_type
        or args.scraper_type_interactive
        or not (listing_only or args.open_dashboard or maintenance_only)
    )
    selected_club = None
    if args.club_id:
        selected_club = club_service.club_handler.get_club_by_id(args.club_id)
        if selected_club is None:
            sys.exit(1)
    elif args.club:
        selected_club = club_service.find_club_by_name(args.club)
        if selected_club is None:
            sys.exit(1)

    needs_eventbrite_token = False
    if will_scrape:
        if selected_club is not None:
            needs_eventbrite_token = _club_uses_eventbrite(selected_club)
        elif args.scraper_type:
            needs_eventbrite_token = args.scraper_type.startswith("eventbrite")
        else:
            needs_eventbrite_token = True

    if needs_eventbrite_token:
        validate_eventbrite_token()

    if will_scrape:
        scraper_proxy_registry.log_proxy_status()

    try:
        # Perform the primary action (scrape/list). "--open-dashboard" is an optional post-action flag
        # and should not short‑circuit other actions when combined.
        performed_primary = False
        scrape_results = None  # populated by the scraping code paths so we can check for config_error below
        if args.merge_partition_metrics is not None:
            _finalize_partition_metrics(
                args.merge_partition_metrics,
                args.expected_partitions,
                metrics_service,
                club_service,
            )
            performed_primary = True
        elif args.all:
            if args.partition_index is None:
                scrape_results = scraping_service.scrape_all_clubs()
            else:
                scrape_results = scraping_service.scrape_all_clubs(
                    partition_index=args.partition_index,
                    partition_count=args.partition_count,
                )
            performed_primary = True
        elif args.club_id:
            scrape_results = scraping_service.scrape_single_club(club_id=args.club_id); performed_primary = True
        elif args.club:
            if selected_club is None:
                Logger.error(f"Club not found: {args.club}")
                sys.exit(1)
            scrape_results = scraping_service.scrape_single_club(club_id=selected_club.id); performed_primary = True
        elif args.scraper_type:
            scrape_results = scraping_service.scrape_by_scraper_type(args.scraper_type); performed_primary = True
        elif args.scraper_type_interactive:
            scrape_results = scraping_service.scrape_by_scraper_type(); performed_primary = True
        elif args.list_scrapers:
            scraper_service.list_available_scraper_types(); performed_primary = True
        elif args.list_clubs:
            club_service.list_available_clubs(); performed_primary = True
        elif args.list_clubs_json:
            club_service.list_clubs_json(); performed_primary = True
        elif args.open_dashboard:
            # Allow opening the dashboard without scraping anything.
            metrics_service.open_dashboard(open_in_browser=True); performed_primary = True
        if not performed_primary:
            Logger.info("Starting interactive club selection...")
            scrape_results = scraping_service.scrape_single_club()

        # If user requested dashboard opening (and it wasn't the sole primary action) do it after scraping.
        if args.open_dashboard and not (args.list_scrapers or args.list_clubs):
            # For list operations we already opened if requested above.
            if not (args.open_dashboard and not performed_primary):
                metrics_service.open_dashboard(open_in_browser=True)

    except KeyboardInterrupt:
        Logger.warn("Scrape partition interrupted before completion")
        sys.exit(130)
    except Exception as e:
        Logger.error(f"An error occurred while scraping: {e}")
        sys.exit(1)

    # Propagate scraper-key configuration errors as a non-zero exit so CI /
    # make scrape-club fails loudly instead of treating an unregistered key
    # as a legitimate zero-shows scrape (TASK-2172). Unaffected clubs in the
    # same run have already been persisted by this point.
    if scrape_results is not None:
        config_errored = [r for r in scrape_results if getattr(r, "config_error", False)]
        if config_errored:
            for r in config_errored:
                Logger.error(f"Config error for '{r.club_name}': {r.error}")
            Logger.error(
                f"{len(config_errored)} club(s) failed with unregistered scraper_key — exiting non-zero"
            )
            sys.exit(1)


# For backward compatibility - standalone script functionality
if __name__ == "__main__":
    main()
