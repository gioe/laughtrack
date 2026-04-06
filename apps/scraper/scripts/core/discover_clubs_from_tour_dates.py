#!/usr/bin/env python3
"""
Discover new clubs from comedian Bandsintown public pages.

Fetches the Bandsintown public artist page for each comedian with a
bandsintown_id, extracts venue names from the JSON-LD MusicEvent data,
and cross-references against the existing clubs table. Auto-triages
venues into high-confidence comedy clubs (auto-creates onboarding tasks)
and a review list for ambiguous ones.

Usage:
    python -m scripts.core.discover_clubs_from_tour_dates
    python -m scripts.core.discover_clubs_from_tour_dates --min-refs 2
    python -m scripts.core.discover_clubs_from_tour_dates --output clubs.csv
    python -m scripts.core.discover_clubs_from_tour_dates --create-tasks
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

    @property
    def is_likely_comedy_club(self) -> bool:
        """Heuristic: does the name suggest a dedicated comedy venue?"""
        return _is_comedy_venue_name(self.name)

    @property
    def triage(self) -> str:
        """Auto-triage: 'auto' for high confidence, 'review' for ambiguous, 'skip' for non-US."""
        # Non-US venues
        if self.state and self.state not in _US_STATES:
            return "skip"
        # No state and no city — likely international
        if not self.state and not self.city:
            return "skip"

        # High confidence: comedy keyword + 2+ comedians
        if self.is_likely_comedy_club and len(self.comedians) >= 2:
            return "auto"

        # Medium confidence: comedy keyword OR 2+ comedians
        if self.is_likely_comedy_club or len(self.comedians) >= 2:
            return "review"

        # Single reference, no comedy keyword — likely a one-off theater
        return "skip"


# Comedy venue name keywords — if the venue name contains any of these,
# it's likely a dedicated comedy venue worth onboarding.
_COMEDY_NAME_KEYWORDS = [
    "comedy", "improv", "funny bone", "funnybone", "laugh", "comic",
    "joke", "stand-up", "standup", "humor", "hilari",
]

# Non-comedy venue patterns — theaters, casinos, arenas that occasionally
# host comedy but aren't dedicated clubs. Used to downgrade confidence.
_NON_COMEDY_PATTERNS = [
    "casino", "resort", "arena", "stadium", "amphitheater", "amphitheatre",
    "convention center", "fairground", "festival",
]

_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


def _is_comedy_venue_name(name: str) -> bool:
    """Check if a venue name suggests a dedicated comedy venue."""
    lower = name.lower()
    if any(kw in lower for kw in _COMEDY_NAME_KEYWORDS):
        # Downgrade if it also matches a non-comedy pattern
        if any(p in lower for p in _NON_COMEDY_PATTERNS):
            return False
        return True
    return False


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


_STRIP_SUFFIXES = [
    " comedy club", " comedy theatre", " comedy theater", " comedy night club",
    " comedy nightclub", " comedy cafe", " comedy lounge",
    " joke house", " joke shop",
    " improv", " improvisation",
    " theatre", " theater",
    " - downtown", " downtown",
]


def _normalize_club_name(name: str) -> str:
    """Strip common suffixes and noise for fuzzy comparison."""
    n = name.strip().lower()
    n = n.removeprefix("the ")
    for suffix in _STRIP_SUFFIXES:
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
            break
    # Remove possessive apostrophes: magooby's → magoobys
    n = n.replace("'", "").replace("\u2019", "")
    return n


def _is_known_club(name: str, known_clubs: set[str]) -> bool:
    """Check if a venue name matches a known club — exact or fuzzy."""
    lower = name.strip().lower()

    # Exact match
    if lower in known_clubs:
        return True

    # Normalize both sides and compare core names
    norm = _normalize_club_name(lower)
    if len(norm) < 5:
        return False

    for known in known_clubs:
        known_norm = _normalize_club_name(known)
        if len(known_norm) < 5:
            continue

        # Normalized exact match (e.g. "Magooby's Joke House" vs "Magoobys Joke House")
        if norm == known_norm:
            return True

        # Substring: one normalized name appears inside the other
        if len(norm) != len(known_norm):
            shorter = norm if len(norm) < len(known_norm) else known_norm
            longer = known_norm if len(norm) < len(known_norm) else norm
            if len(shorter) >= 8 and shorter in longer:
                return True

    return False


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
                if _is_known_club(v["name"], known_clubs):
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

    auto = [v for v in venues if v.triage == "auto"]
    review = [v for v in venues if v.triage == "review"]
    skipped = [v for v in venues if v.triage == "skip"]

    print(f"\n{'='*80}")
    print(f"CLUB DISCOVERY REPORT — {len(venues)} unmatched venues from Bandsintown")
    print(f"{'='*80}")
    print(f"  Auto-onboard:  {len(auto):4d}  (comedy keyword + 2+ comedians)")
    print(f"  Review:        {len(review):4d}  (comedy keyword OR 2+ comedians)")
    print(f"  Skipped:       {len(skipped):4d}  (one-off / non-US / ambiguous)")

    if auto:
        print(f"\n{'─'*80}")
        print(f"AUTO-ONBOARD ({len(auto)} venues)")
        print(f"{'─'*80}")
        print(f"{'Venue':<35s} {'City, State':<25s} {'Comedians':>9s}")
        print(f"{'─'*80}")
        for v in auto:
            print(f"{v.name[:34]:<35s} {v.location[:24]:<25s} {len(v.comedians):>9d}")

    if review:
        print(f"\n{'─'*80}")
        print(f"NEEDS REVIEW ({len(review)} venues)")
        print(f"{'─'*80}")
        print(f"{'Venue':<35s} {'City, State':<25s} {'Comedians':>9s} {'Signal'}")
        print(f"{'─'*80}")
        for v in review:
            signal = "comedy name" if v.is_likely_comedy_club else f"{len(v.comedians)} refs"
            print(f"{v.name[:34]:<35s} {v.location[:24]:<25s} {len(v.comedians):>9d} {signal}")


def _create_onboarding_tasks(venues: list[DiscoveredVenue]) -> int:
    """Create tusk onboarding tasks for auto-triaged venues. Returns count created."""
    import subprocess

    created = 0
    for v in venues:
        location = v.location
        comedians_str = ", ".join(sorted(v.comedians))
        sample_url = next(iter(v.ticket_urls)) if v.ticket_urls else ""

        summary = f"Onboard {v.name}"
        if location:
            summary += f" ({location})"

        description = (
            f"Discovered via Bandsintown tour dates. "
            f"Referenced by {len(v.comedians)} comedian(s): {comedians_str}."
        )
        if sample_url:
            description += f" Sample ticket URL: {sample_url}"

        cmd = [
            "tusk", "task-insert",
            summary, description,
            "--priority", "Medium",
            "--domain", "scraper",
            "--task-type", "feature",
            "--complexity", "S",
            "--criteria", f"Add {v.name} to the clubs table with correct scraper type",
            "--criteria", f"Verify scraper produces show records for {v.name}",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                created += 1
                Logger.info(f"  Created task: {summary}")
            elif result.returncode == 1:
                Logger.info(f"  Skipped (duplicate): {summary}")
            else:
                Logger.warn(f"  Failed to create task for {v.name}: {result.stderr.strip()}")
        except Exception as e:
            Logger.warn(f"  Error creating task for {v.name}: {e}")

    return created


def main():
    parser = argparse.ArgumentParser(
        description="Discover new clubs from comedian Bandsintown pages",
    )
    parser.add_argument("--min-refs", type=int, default=1,
                        help="Minimum comedian references to include (default: 1)")
    parser.add_argument("--output", type=str, help="Write CSV to this path")
    parser.add_argument("--create-tasks", action="store_true",
                        help="Auto-create onboarding tasks for high-confidence venues")
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
                w.writerow(["venue", "city", "state", "comedian_count", "comedians", "triage", "sample_url"])
                for v in results:
                    w.writerow([
                        v.name, v.city, v.state,
                        len(v.comedians),
                        "; ".join(sorted(v.comedians)),
                        v.triage,
                        next(iter(v.ticket_urls)) if v.ticket_urls else "",
                    ])
            print(f"\nCSV written to {args.output}")

        # Auto-create tasks for high-confidence venues
        auto_venues = [v for v in results if v.triage == "auto"]
        if args.create_tasks and auto_venues:
            print(f"\nCreating onboarding tasks for {len(auto_venues)} auto-triaged venues...")
            created = _create_onboarding_tasks(auto_venues)
            print(f"Created {created} tasks ({len(auto_venues) - created} skipped as duplicates)")
        elif auto_venues and not args.create_tasks:
            print(f"\n{len(auto_venues)} venues ready for auto-onboard — pass --create-tasks to create tusk tasks")

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
