#!/usr/bin/env python3
"""
Discover new clubs from comedian Bandsintown public pages.

Fetches the Bandsintown public artist page for each comedian with a
bandsintown_id, extracts venue names from the JSON-LD MusicEvent data,
and cross-references against the existing clubs table. Reports unmatched
venues sorted by how many comedians reference them.

Usage:
    python -m scripts.core.discover_clubs_from_tour_dates
    python -m scripts.core.discover_clubs_from_tour_dates --min-refs 2
    python -m scripts.core.discover_clubs_from_tour_dates --output clubs.csv
"""

import argparse
import asyncio
import csv
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import quote

_repo_root = Path(__file__).resolve().parents[2]
_src_path = _repo_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DiscoveredVenue:
    name: str
    city: str = ""
    state: str = ""
    ticket_urls: set[str] = field(default_factory=set)
    comedians: set[str] = field(default_factory=set)

    @property
    def location(self) -> str:
        if self.city and self.state:
            return f"{self.city}, {self.state}"
        return self.city or self.state or ""


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

_GET_COMEDIANS_WITH_BANDSINTOWN = """
    SELECT name, bandsintown_id
    FROM comedians
    WHERE bandsintown_id IS NOT NULL
      AND bandsintown_id <> ''
    ORDER BY popularity DESC NULLS LAST
"""

_GET_ALL_CLUB_NAMES = """
    SELECT LOWER(TRIM(name)) AS name
    FROM clubs
    WHERE name IS NOT NULL AND name <> ''
"""


def _load_known_clubs() -> set[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_GET_ALL_CLUB_NAMES)
            return {row[0] for row in cur.fetchall()}


def _load_comedians() -> list[tuple[str, str]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_GET_COMEDIANS_WITH_BANDSINTOWN)
            return cur.fetchall()


# ---------------------------------------------------------------------------
# Bandsintown page scraping
# ---------------------------------------------------------------------------

def _artist_id_to_slug(artist_id: str, comedian_name: str) -> str:
    """Convert a bandsintown_id to a URL slug for the public page.

    Numeric IDs (id_12345) can't be used in public URLs — fall back to
    the comedian's name as a slug. Slug-based IDs are used directly.
    """
    if artist_id.startswith("id_"):
        # Use comedian name as slug — lowercase, hyphenated
        slug = re.sub(r'[^a-z0-9]+', '-', comedian_name.lower()).strip('-')
        return slug
    # Already a slug or name
    return artist_id


async def _fetch_artist_events(slug: str) -> list[dict]:
    """Fetch events from a Bandsintown public artist page via JSON-LD."""
    from curl_cffi.requests import AsyncSession

    url = f"https://www.bandsintown.com/{quote(slug)}"
    try:
        async with AsyncSession() as session:
            resp = await session.get(url, timeout=20, impersonate="chrome")
            if resp.status_code != 200:
                return []

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            ld_scripts = soup.find_all("script", type="application/ld+json")

            events = []
            for script in ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        events.extend(
                            e for e in data
                            if isinstance(e, dict) and e.get("@type") in ("MusicEvent", "Event", "ComedyEvent")
                        )
                    elif isinstance(data, dict) and data.get("@type") in ("MusicEvent", "Event", "ComedyEvent"):
                        events.append(data)
                except (json.JSONDecodeError, TypeError):
                    continue
            return events
    except Exception as e:
        Logger.warn(f"Failed to fetch Bandsintown page for {slug}: {e}")
        return []


def _extract_venues(events: list[dict]) -> list[dict]:
    """Extract venue info from JSON-LD events."""
    venues = []
    for event in events:
        location = event.get("location") or {}
        venue_name = (location.get("name") or "").strip()
        if not venue_name:
            continue

        address = location.get("address") or {}
        city = (address.get("addressLocality") or "").strip()
        state = (address.get("addressRegion") or "").strip()
        ticket_url = (event.get("url") or "").strip()

        venues.append({
            "name": venue_name,
            "city": city,
            "state": state,
            "ticket_url": ticket_url,
        })
    return venues


# ---------------------------------------------------------------------------
# Discovery pipeline
# ---------------------------------------------------------------------------

async def _discover_clubs(min_refs: int = 1) -> list[DiscoveredVenue]:
    Logger.info("Loading known clubs...")
    known_clubs = _load_known_clubs()
    Logger.info(f"Loaded {len(known_clubs)} known clubs")

    comedians = _load_comedians()
    Logger.info(f"Loaded {len(comedians)} comedians with Bandsintown IDs")

    if not comedians:
        return []

    # Deduplicate slugs (e.g. "Todd Barry" and "Tood Barry" both map to same BIT ID)
    slug_to_comedians: dict[str, list[str]] = defaultdict(list)
    for name, bit_id in comedians:
        slug = _artist_id_to_slug(bit_id, name)
        slug_to_comedians[slug].append(name)

    Logger.info(f"Unique artist slugs to fetch: {len(slug_to_comedians)}")

    venues: dict[str, DiscoveredVenue] = {}
    processed = 0
    total_events = 0
    semaphore = asyncio.Semaphore(3)  # Conservative — Bandsintown may rate-limit

    async def process(slug: str, comedian_names: list[str]):
        nonlocal processed, total_events

        async with semaphore:
            await asyncio.sleep(0.5)  # Rate limiting
            events = await _fetch_artist_events(slug)
            if not events:
                Logger.info(f"  {comedian_names[0]} ({slug}): no events")
                return

            extracted = _extract_venues(events)
            total_events += len(extracted)
            processed += 1

            Logger.info(f"  {comedian_names[0]} ({slug}): {len(extracted)} events, {len(events)} total")

            for v in extracted:
                key = v["name"].strip().lower()
                if key in known_clubs:
                    continue

                if key in venues:
                    existing = venues[key]
                    existing.comedians.update(comedian_names)
                    if v["ticket_url"]:
                        existing.ticket_urls.add(v["ticket_url"])
                    # Backfill city/state if missing
                    if not existing.city and v["city"]:
                        existing.city = v["city"]
                    if not existing.state and v["state"]:
                        existing.state = v["state"]
                else:
                    venues[key] = DiscoveredVenue(
                        name=v["name"],
                        city=v["city"],
                        state=v["state"],
                        ticket_urls={v["ticket_url"]} if v["ticket_url"] else set(),
                        comedians=set(comedian_names),
                    )

    tasks = [process(slug, names) for slug, names in slug_to_comedians.items()]
    await asyncio.gather(*tasks)

    Logger.info(f"Processed {processed} artists, {total_events} events total")

    results = [v for v in venues.values() if len(v.comedians) >= min_refs]
    results.sort(key=lambda v: (-len(v.comedians), v.name))
    return results


def _print_report(venues: list[DiscoveredVenue]) -> None:
    if not venues:
        print("\nNo unmatched venues found.")
        return

    print(f"\n{'='*80}")
    print(f"CLUB DISCOVERY REPORT — {len(venues)} unmatched venues from Bandsintown")
    print(f"{'='*80}")

    # By state
    state_counts: dict[str, int] = defaultdict(int)
    for v in venues:
        state_counts[v.state or "(unknown)"] += 1

    if any(s != "(unknown)" for s in state_counts):
        print("\nBy state:")
        for state, count in sorted(state_counts.items(), key=lambda x: -x[1])[:15]:
            print(f"  {state:5s} {count}")

    print(f"\n{'─'*80}")
    print(f"{'Venue':<35s} {'City, State':<25s} {'Comedians':>9s}")
    print(f"{'─'*80}")

    for v in venues:
        print(f"{v.name[:34]:<35s} {v.location[:24]:<25s} {len(v.comedians):>9d}")

    # Detail for high-ref venues
    high_ref = [v for v in venues if len(v.comedians) >= 2]
    if high_ref:
        print(f"\n{'='*80}")
        print(f"MULTI-COMEDIAN VENUES (2+ comedians)")
        print(f"{'='*80}")
        for v in high_ref:
            print(f"\n  {v.name} ({v.location})")
            print(f"  Referenced by: {', '.join(sorted(v.comedians))}")
            if v.ticket_urls:
                print(f"  Sample URL: {next(iter(v.ticket_urls))}")


def main():
    parser = argparse.ArgumentParser(
        description="Discover new clubs from comedian Bandsintown pages",
    )
    parser.add_argument("--min-refs", type=int, default=1,
                        help="Minimum comedian references to include (default: 1)")
    parser.add_argument("--output", type=str, help="Write CSV to this path")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        current = os.environ.get("LAUGHTRACK_LOG_CONSOLE_LEVEL", "").upper()
        if current not in ("DEBUG", "INFO"):
            os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "INFO"

    try:
        results = asyncio.run(_discover_clubs(min_refs=args.min_refs))
        _print_report(results)

        if args.output and results:
            with open(args.output, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["venue", "city", "state", "comedian_count", "comedians", "sample_url"])
                for v in results:
                    w.writerow([
                        v.name, v.city, v.state,
                        len(v.comedians),
                        "; ".join(sorted(v.comedians)),
                        next(iter(v.ticket_urls)) if v.ticket_urls else "",
                    ])
            print(f"\nCSV written to {args.output}")

        print(f"\nTotal: {len(results)} unmatched venues")

    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        Logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
