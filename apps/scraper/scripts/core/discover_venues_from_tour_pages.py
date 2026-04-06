#!/usr/bin/env python3
"""
Discover new venues from comedian tour pages.

Fetches comedian websites with JSON-LD Event markup, extracts venue names
and ticket URLs, identifies ticketing platforms, and cross-references against
the existing clubs table. Outputs unmatched venues as onboarding candidates.

Usage:
    python -m scripts.core.discover_venues_from_tour_pages
    python -m scripts.core.discover_venues_from_tour_pages --limit 50
    python -m scripts.core.discover_venues_from_tour_pages --comedian-name "Anthony Rodia"
    python -m scripts.core.discover_venues_from_tour_pages --min-refs 2
"""

import argparse
import asyncio
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Ensure local 'src' package path takes precedence over any installed package
_repo_root = Path(__file__).resolve().parents[2]
_src_path = _repo_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from laughtrack.core.data.db import db
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.implementations.api.comedian_websites.platform_detector import detect_platform
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DiscoveredVenue:
    """A venue found on a comedian's tour page that is not in our clubs table."""
    venue_name: str
    city: str = ""
    state: str = ""
    ticket_urls: set[str] = field(default_factory=set)
    platforms: set[str] = field(default_factory=set)
    comedians: set[str] = field(default_factory=set)

    @property
    def key(self) -> str:
        """Normalized key for deduplication."""
        return self.venue_name.strip().lower()


# ---------------------------------------------------------------------------
# Database queries
# ---------------------------------------------------------------------------

_GET_COMEDIANS_WITH_SCRAPED_WEBSITES = """
    SELECT uuid, name, website, website_scrape_strategy
    FROM comedians
    WHERE website IS NOT NULL
      AND website <> ''
      AND website_scrape_strategy IN ('json_ld', 'json_ld_subpage')
"""

_GET_ALL_CLUB_NAMES = """
    SELECT LOWER(TRIM(name)) AS name
    FROM clubs
    WHERE name IS NOT NULL AND name <> ''
"""


def _load_known_club_names() -> set[str]:
    """Load all club names from the DB, lowercased for matching."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_GET_ALL_CLUB_NAMES)
            return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


def _load_comedians(limit: Optional[int] = None, comedian_name: Optional[str] = None) -> list[dict]:
    """Load comedians whose websites have yielded JSON-LD data."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            query = _GET_COMEDIANS_WITH_SCRAPED_WEBSITES
            params: tuple = ()
            if comedian_name:
                query += " AND LOWER(name) LIKE LOWER(%s)"
                params = (f"%{comedian_name}%",)
            query += " ORDER BY name"
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    finally:
        conn.close()

    if limit and len(rows) > limit:
        rows = rows[:limit]
    return rows


# ---------------------------------------------------------------------------
# HTML fetching
# ---------------------------------------------------------------------------

async def _fetch_html(url: str, timeout: int = 30) -> Optional[str]:
    """Fetch HTML from a URL using curl_cffi."""
    try:
        from curl_cffi.requests import AsyncSession
        async with AsyncSession() as session:
            resp = await session.get(url, timeout=timeout, impersonate="chrome")
            if resp.status_code == 200:
                return resp.text
    except Exception as e:
        Logger.warn(f"Failed to fetch {url}: {e}")
    return None


async def _fetch_tour_pages(website: str) -> list[str]:
    """Fetch the homepage and any tour subpages, return list of HTML strings."""
    from laughtrack.scrapers.implementations.api.comedian_websites.tour_link_detector import detect_tour_links

    pages: list[str] = []
    html = await _fetch_html(website)
    if not html:
        return pages
    pages.append(html)

    tour_links = detect_tour_links(html, website)
    for link in tour_links[:3]:
        subpage_html = await _fetch_html(link)
        if subpage_html:
            pages.append(subpage_html)

    return pages


# ---------------------------------------------------------------------------
# Event extraction and venue discovery
# ---------------------------------------------------------------------------

def _extract_venues_from_events(
    events: list,
    comedian_name: str,
    known_clubs: set[str],
    venues: dict[str, DiscoveredVenue],
) -> None:
    """Extract venue info from JSON-LD events. Merge into venues dict by normalized name."""
    for event in events:
        location = event.location
        if not location:
            continue

        venue_name = (location.name or "").strip()
        if not venue_name:
            continue

        # Skip if already a known club
        if venue_name.lower() in known_clubs:
            continue

        city = ""
        state = ""
        if location.address:
            city = (location.address.address_locality or "").strip()
            state = (location.address.address_region or "").strip()

        # Collect ticket URLs
        ticket_urls: set[str] = set()
        if event.url:
            ticket_urls.add(event.url)
        for offer in (event.offers or []):
            if offer.url:
                ticket_urls.add(offer.url)

        # Detect platforms from ticket URLs
        platforms: set[str] = set()
        for url in ticket_urls:
            platform = detect_platform(url)
            if platform:
                platforms.add(platform)

        # Merge into venues dict
        key = venue_name.strip().lower()
        if key in venues:
            existing = venues[key]
            existing.ticket_urls.update(ticket_urls)
            existing.platforms.update(platforms)
            existing.comedians.add(comedian_name)
        else:
            venues[key] = DiscoveredVenue(
                venue_name=venue_name,
                city=city,
                state=state,
                ticket_urls=ticket_urls,
                platforms=platforms,
                comedians={comedian_name},
            )


# ---------------------------------------------------------------------------
# Main discovery flow
# ---------------------------------------------------------------------------

async def _discover_venues(
    limit: Optional[int] = None,
    comedian_name: Optional[str] = None,
    min_refs: int = 1,
) -> list[DiscoveredVenue]:
    """Run the venue discovery pipeline."""
    Logger.info("Loading known clubs from database...")
    known_clubs = _load_known_club_names()
    Logger.info(f"Loaded {len(known_clubs)} known club names")

    comedians = _load_comedians(limit=limit, comedian_name=comedian_name)
    Logger.info(f"Loaded {len(comedians)} comedians with JSON-LD websites")

    if not comedians:
        Logger.info("No comedians found — nothing to discover")
        return []

    venues: dict[str, DiscoveredVenue] = {}
    processed = 0
    errors = 0

    semaphore = asyncio.Semaphore(5)

    async def process_comedian(row: dict) -> None:
        nonlocal processed, errors
        name = row["name"]
        website = row.get("website", "").strip()
        if not website:
            return

        async with semaphore:
            try:
                pages = await _fetch_tour_pages(website)
                if not pages:
                    return

                all_events = []
                for page_html in pages:
                    all_events.extend(EventExtractor.extract_events(page_html))

                processed += 1
                if all_events:
                    _extract_venues_from_events(all_events, name, known_clubs, venues)
            except Exception as e:
                Logger.warn(f"Error processing {name} ({website}): {e}")
                errors += 1

    await asyncio.gather(*[process_comedian(row) for row in comedians])

    Logger.info(f"Processed {processed} comedian websites ({errors} errors)")

    # Filter by minimum comedian references
    results = [v for v in venues.values() if len(v.comedians) >= min_refs]
    results.sort(key=lambda v: (-len(v.comedians), v.venue_name))

    return results


def _print_report(venues: list[DiscoveredVenue]) -> None:
    """Print the venue discovery report to stdout."""
    if not venues:
        print("\nNo unmatched venues found.")
        return

    # Summary by platform
    platform_counts: dict[str, int] = defaultdict(int)
    for v in venues:
        for p in v.platforms:
            platform_counts[p] += 1
    unknown_count = sum(1 for v in venues if not v.platforms)

    print(f"\n{'='*80}")
    print(f"VENUE DISCOVERY REPORT — {len(venues)} unmatched venues found")
    print(f"{'='*80}")

    if platform_counts:
        print("\nBy ticketing platform:")
        for platform, count in sorted(platform_counts.items(), key=lambda x: -x[1]):
            print(f"  {platform:20s} {count}")
        if unknown_count:
            print(f"  {'(unknown)':20s} {unknown_count}")

    print(f"\n{'─'*80}")
    print(f"{'Venue':<35s} {'City, State':<25s} {'Platform(s)':<20s} {'Refs':>4s}")
    print(f"{'─'*80}")

    for v in venues:
        location = f"{v.city}, {v.state}" if v.city else v.state or ""
        platforms_str = ", ".join(sorted(v.platforms)) if v.platforms else "(unknown)"
        print(f"{v.venue_name[:34]:<35s} {location[:24]:<25s} {platforms_str[:19]:<20s} {len(v.comedians):>4d}")

    # Detail section for high-reference venues
    high_ref = [v for v in venues if len(v.comedians) >= 2]
    if high_ref:
        print(f"\n{'='*80}")
        print("HIGH-REFERENCE VENUES (2+ comedians)")
        print(f"{'='*80}")
        for v in high_ref:
            location = f"{v.city}, {v.state}" if v.city else v.state or ""
            print(f"\n  {v.venue_name} ({location})")
            print(f"  Platforms: {', '.join(sorted(v.platforms)) if v.platforms else '(unknown)'}")
            print(f"  Comedians: {', '.join(sorted(v.comedians))}")
            # Show first unique ticket URL per platform
            seen_platforms: set[str] = set()
            for url in v.ticket_urls:
                platform = detect_platform(url)
                label = platform or "(unknown)"
                if label not in seen_platforms:
                    seen_platforms.add(label)
                    print(f"  Sample URL ({label}): {url}")


def main():
    parser = argparse.ArgumentParser(
        description="Discover new venues from comedian tour pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--limit", type=int, help="Max comedians to process")
    parser.add_argument("--comedian-name", type=str, help="Process specific comedian (partial match)")
    parser.add_argument("--min-refs", type=int, default=1, help="Minimum comedian references to include (default: 1)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show INFO-level logs")
    parser.add_argument("--debug", action="store_true", help="Show DEBUG-level logs")

    args = parser.parse_args()

    if args.debug:
        os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "DEBUG"
    elif args.verbose:
        current = os.environ.get("LAUGHTRACK_LOG_CONSOLE_LEVEL", "").upper()
        if current not in ("DEBUG", "INFO"):
            os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "INFO"

    try:
        results = asyncio.run(_discover_venues(
            limit=args.limit,
            comedian_name=args.comedian_name,
            min_refs=args.min_refs,
        ))
        _print_report(results)

        print(f"\nTotal: {len(results)} unmatched venues")
    except KeyboardInterrupt:
        Logger.info("Cancelled")
        sys.exit(0)
    except Exception as e:
        Logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
