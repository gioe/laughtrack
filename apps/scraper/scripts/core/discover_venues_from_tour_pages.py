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
    python -m scripts.core.discover_venues_from_tour_pages --create-clubs --create-tasks
"""

import argparse
import asyncio
import html
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Locate scraper root (apps/scraper/) by walking up to pyproject.toml, then
# put src/ + scraper root on sys.path so laughtrack imports resolve.
_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.implementations.api.comedian_websites.platform_detector import detect_platform
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

_COMEDY_NAME_KEYWORDS = [
    "comedy", "improv", "funny bone", "funnybone", "laugh", "comic",
    "joke", "stand-up", "standup", "humor", "hilari",
]

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
    lower = name.lower()
    if any(kw in lower for kw in _COMEDY_NAME_KEYWORDS):
        if any(p in lower for p in _NON_COMEDY_PATTERNS):
            return False
        return True
    return False


_STRIP_SUFFIXES = [
    " comedy club", " comedy theatre", " comedy theater", " comedy night club",
    " comedy nightclub", " comedy cafe", " comedy lounge",
    " joke house", " joke shop",
    " improv", " improvisation",
    " theatre", " theater",
    " - downtown", " downtown",
]


def _normalize_club_name(name: str) -> str:
    # Decode HTML entities first (&#8217; -> ', &amp; -> &, etc.)
    n = html.unescape(name).strip().lower()
    n = n.removeprefix("the ")
    for suffix in _STRIP_SUFFIXES:
        if n.endswith(suffix):
            candidate = n[: -len(suffix)].strip()
            # Only strip if meaningful words remain (avoid "raleigh improv" -> "raleigh")
            if len(candidate) >= 5:
                n = candidate
            break
    # Strip city qualifiers: " - CityName", " - CityName, ST"
    n = re.sub(r"\s*[-–—]\s*[a-z ]+(?:,\s*[a-z]{2})?\s*$", "", n)
    # Remove apostrophes / smart quotes
    n = n.replace("'", "").replace("\u2019", "")
    # Remove commas
    n = n.replace(",", "")
    # Remove extra qualifiers like "at <place>" for substring matching
    n = re.sub(r"\s+at\s+.*$", "", n)
    return n.strip()


def _clean_name(name: str) -> str:
    """Minimal cleaning: decode HTML, lowercase, strip punctuation. No suffix removal."""
    n = html.unescape(name).strip().lower()
    n = n.removeprefix("the ")
    n = n.replace("'", "").replace("\u2019", "")
    n = n.replace(",", "")
    # Strip city qualifiers after dash: " - CityName" / " – CityName, ST"
    n = re.sub(r"\s*[-–—]\s*[a-z ]+(?:,\s*[a-z]{2})?\s*$", "", n)
    return n.strip()


def _sorted_words(name: str) -> str:
    """Return space-joined sorted words — catches word-order swaps like 'Raleigh Improv' vs 'Improv Raleigh'."""
    return " ".join(sorted(name.split()))


def _is_known_club(name: str, known_clubs: set[str]) -> bool:
    """Check if a venue name matches a known club — exact or fuzzy."""
    # Decode HTML entities before any comparison
    lower = html.unescape(name).strip().lower()
    if lower in known_clubs:
        return True

    norm = _normalize_club_name(lower)
    clean = _clean_name(lower)
    if len(norm) < 5 and len(clean) < 5:
        return False

    norm_words = _sorted_words(norm)
    clean_words = _sorted_words(clean)

    for known in known_clubs:
        known_norm = _normalize_club_name(known)
        known_clean = _clean_name(known)
        if len(known_norm) < 5 and len(known_clean) < 5:
            continue

        # Exact match on either normalization level
        if norm == known_norm or clean == known_clean:
            return True

        # Word-order-independent match (e.g. "Improv Raleigh" vs "Raleigh Improv")
        if norm_words == _sorted_words(known_norm) or clean_words == _sorted_words(known_clean):
            return True

        # Substring containment (either direction, min 8 chars) on both levels
        for a, b in [(norm, known_norm), (clean, known_clean)]:
            if len(a) >= 8 and len(b) >= 8 and len(a) != len(b):
                shorter, longer = (a, b) if len(a) < len(b) else (b, a)
                if shorter in longer:
                    return True

    return False


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

    @property
    def location(self) -> str:
        if self.city and self.state:
            return f"{self.city}, {self.state}"
        return self.city or self.state or ""

    @property
    def is_likely_comedy_club(self) -> bool:
        return _is_comedy_venue_name(self.venue_name)

    @property
    def triage(self) -> str:
        """Auto-triage: 'auto' for high confidence, 'review' for ambiguous, 'skip' for non-US."""
        if self.state and self.state not in _US_STATES:
            return "skip"
        if not self.state and not self.city:
            return "skip"
        if self.is_likely_comedy_club and len(self.comedians) >= 2:
            return "auto"
        if self.is_likely_comedy_club or len(self.comedians) >= 2:
            return "review"
        return "skip"


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
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_GET_ALL_CLUB_NAMES)
            return {row[0] for row in cur.fetchall()}


def _load_comedians(limit: Optional[int] = None, comedian_name: Optional[str] = None) -> list[dict]:
    """Load comedians whose websites have yielded JSON-LD data."""
    with get_connection() as conn:
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

        venue_name = html.unescape((location.name or "")).strip()
        if not venue_name:
            continue

        # Skip if already a known club (fuzzy match)
        if _is_known_club(venue_name, known_clubs):
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

    auto = [v for v in venues if v.triage == "auto"]
    review = [v for v in venues if v.triage == "review"]
    skipped = [v for v in venues if v.triage == "skip"]

    # Summary by platform
    platform_counts: dict[str, int] = defaultdict(int)
    for v in venues:
        for p in v.platforms:
            platform_counts[p] += 1
    unknown_count = sum(1 for v in venues if not v.platforms)

    print(f"\n{'='*80}")
    print(f"VENUE DISCOVERY REPORT — {len(venues)} unmatched venues found")
    print(f"{'='*80}")
    print(f"  Auto-onboard:  {len(auto):4d}  (comedy keyword + 2+ comedians)")
    print(f"  Review:        {len(review):4d}  (comedy keyword OR 2+ comedians)")
    print(f"  Skipped:       {len(skipped):4d}  (one-off / non-US / ambiguous)")

    if platform_counts:
        print("\nBy ticketing platform:")
        for platform, count in sorted(platform_counts.items(), key=lambda x: -x[1]):
            print(f"  {platform:20s} {count}")
        if unknown_count:
            print(f"  {'(unknown)':20s} {unknown_count}")

    if auto:
        print(f"\n{'─'*80}")
        print(f"AUTO-ONBOARD ({len(auto)} venues)")
        print(f"{'─'*80}")
        print(f"{'Venue':<35s} {'City, State':<25s} {'Platform(s)':<20s} {'Refs':>4s}")
        print(f"{'─'*80}")
        for v in auto:
            platforms_str = ", ".join(sorted(v.platforms)) if v.platforms else "(unknown)"
            print(f"{v.venue_name[:34]:<35s} {v.location[:24]:<25s} {platforms_str[:19]:<20s} {len(v.comedians):>4d}")

    if review:
        print(f"\n{'─'*80}")
        print(f"NEEDS REVIEW ({len(review)} venues)")
        print(f"{'─'*80}")
        print(f"{'Venue':<35s} {'City, State':<25s} {'Platform(s)':<20s} {'Refs':>4s} {'Signal'}")
        print(f"{'─'*80}")
        for v in review:
            platforms_str = ", ".join(sorted(v.platforms)) if v.platforms else "(unknown)"
            signal = "comedy name" if v.is_likely_comedy_club else f"{len(v.comedians)} refs"
            print(f"{v.venue_name[:34]:<35s} {v.location[:24]:<25s} {platforms_str[:19]:<20s} {len(v.comedians):>4d} {signal}")

    # Detail section for high-reference venues
    high_ref = [v for v in venues if len(v.comedians) >= 2]
    if high_ref:
        print(f"\n{'='*80}")
        print("HIGH-REFERENCE VENUES (2+ comedians)")
        print(f"{'='*80}")
        for v in high_ref:
            print(f"\n  {v.venue_name} ({v.location})")
            print(f"  Triage: {v.triage}")
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


# ---------------------------------------------------------------------------
# Persist clubs and create tasks
# ---------------------------------------------------------------------------

def _create_clubs(venues: list[DiscoveredVenue]) -> int:
    """Insert discovered venues into the clubs table. Returns count created."""
    from laughtrack.core.entities.club.handler import ClubHandler

    handler = ClubHandler()
    created = 0
    for v in venues:
        address = v.location  # "City, State" or partial
        venue_dict = {
            "name": v.venue_name,
            "address": address,
            "zip_code": "",
            "timezone": None,
        }
        try:
            club = handler.upsert_for_tour_date_venue(venue_dict)
            if club:
                created += 1
                Logger.info(f"  Upserted club: {v.venue_name} (id={club.id})")
            else:
                Logger.info(f"  Skipped (junk filter): {v.venue_name}")
        except Exception as e:
            Logger.warn(f"  Error upserting {v.venue_name}: {e}")
    return created


def _send_discord_report(venues: list[DiscoveredVenue]) -> None:
    """Send Discord notifications summarizing discovered venues.

    Sends up to two separate messages:
    1. Auto-onboarded + needs-review venues (actionable)
    2. Skipped venues (for visibility)
    """
    auto = [v for v in venues if v.triage == "auto"]
    review = [v for v in venues if v.triage == "review"]
    skipped = [v for v in venues if v.triage == "skip"]

    if not auto and not review and not skipped:
        return

    try:
        from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig
        from gioe_libs.alerting import DiscordAlertChannel, Alert, AlertSeverity
    except ImportError as e:
        Logger.error(f"Monitoring package not available; skipping Discord report: {e}")
        return

    try:
        config = MonitoringConfig.default()
        if not config.is_discord_configured() or not config.discord_webhook_url:
            Logger.warn("Discord webhook not configured; skipping venue discovery report")
            return

        channel = DiscordAlertChannel(webhook_url=config.discord_webhook_url)

        # --- Alert 1: Auto-onboarded + review ---
        if auto or review:
            lines: list[str] = []
            if auto:
                lines.append(f"**Auto-onboarded ({len(auto)}):**")
                for v in auto:
                    line = f"• {v.venue_name}"
                    if v.location:
                        line += f" — {v.location}"
                    parts = []
                    if v.platforms:
                        parts.append(", ".join(sorted(v.platforms)))
                    parts.append(f"{len(v.comedians)} comedian refs")
                    line += f" ({', '.join(parts)})"
                    lines.append(line)
            if review:
                lines.append(f"\n**Needs review ({len(review)}):**")
                for v in review:
                    line = f"• {v.venue_name}"
                    if v.location:
                        line += f" — {v.location}"
                    parts = []
                    if v.platforms:
                        parts.append(", ".join(sorted(v.platforms)))
                    if v.is_likely_comedy_club:
                        parts.append("comedy venue name")
                    else:
                        parts.append(f"{len(v.comedians)} comedian refs")
                    line += f" ({', '.join(parts)})"
                    lines.append(line)

            alert = Alert(
                title=f"Venue Discovery: {len(auto)} auto-onboarded, {len(review)} need review",
                message="\n".join(lines),
                severity=AlertSeverity.LOW,
                metadata={
                    "auto_count": len(auto),
                    "review_count": len(review),
                    "total_unmatched": len(venues),
                },
            )
            if channel.send(alert):
                Logger.info("Discord venue discovery report sent (auto + review)")
            else:
                Logger.error("Discord venue discovery report delivery failed (auto + review)")

        # --- Alert 2: Skipped venues ---
        if skipped:
            skip_lines: list[str] = []
            for v in skipped:
                line = f"• {v.venue_name}"
                if v.location:
                    line += f" — {v.location}"
                parts = []
                if v.platforms:
                    parts.append(", ".join(sorted(v.platforms)))
                parts.append(f"{len(v.comedians)} comedian refs")
                line += f" ({', '.join(parts)})"
                skip_lines.append(line)

            # Discord embeds have a 4096-char description limit; truncate if needed
            body = "\n".join(skip_lines)
            if len(body) > 3800:
                truncated = []
                total_len = 0
                for line in skip_lines:
                    if total_len + len(line) + 1 > 3700:
                        break
                    truncated.append(line)
                    total_len += len(line) + 1
                remaining = len(skip_lines) - len(truncated)
                truncated.append(f"\n… and {remaining} more")
                body = "\n".join(truncated)

            skip_alert = Alert(
                title=f"Venue Discovery — Skipped: {len(skipped)} venues",
                message=body,
                severity=AlertSeverity.LOW,
                metadata={
                    "skipped_count": len(skipped),
                    "total_unmatched": len(venues),
                },
            )
            if channel.send(skip_alert):
                Logger.info("Discord venue discovery report sent (skipped)")
            else:
                Logger.error("Discord venue discovery report delivery failed (skipped)")

    except Exception as e:
        Logger.error(f"Failed to send Discord venue discovery report: {e}")


def _create_onboarding_tasks(venues: list[DiscoveredVenue]) -> int:
    """Create tusk onboarding tasks for auto-triaged venues. Returns count created."""
    import subprocess

    created = 0
    for v in venues:
        location = v.location
        comedians_str = ", ".join(sorted(v.comedians))
        platforms_str = ", ".join(sorted(v.platforms)) if v.platforms else "unknown"
        sample_url = next(iter(v.ticket_urls)) if v.ticket_urls else ""

        summary = f"Onboard {v.venue_name}"
        if location:
            summary += f" ({location})"

        description = (
            f"Discovered via comedian tour pages (JSON-LD). "
            f"Referenced by {len(v.comedians)} comedian(s): {comedians_str}. "
            f"Detected platform(s): {platforms_str}."
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
            "--criteria", f"Add {v.venue_name} to the clubs table with correct scraper type",
            "--criteria", f"Verify scraper produces show records for {v.venue_name}",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                created += 1
                Logger.info(f"  Created task: {summary}")
            elif result.returncode == 1:
                Logger.info(f"  Skipped (duplicate): {summary}")
            else:
                Logger.warn(f"  Failed to create task for {v.venue_name}: {result.stderr.strip()}")
        except Exception as e:
            Logger.warn(f"  Error creating task for {v.venue_name}: {e}")

    return created


def main():
    parser = argparse.ArgumentParser(
        description="Discover new venues from comedian tour pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--limit", type=int, help="Max comedians to process")
    parser.add_argument("--comedian-name", type=str, help="Process specific comedian (partial match)")
    parser.add_argument("--min-refs", type=int, default=1, help="Minimum comedian references to include (default: 1)")
    parser.add_argument("--create-clubs", action="store_true",
                        help="Insert discovered venues into clubs table (auto-triaged only)")
    parser.add_argument("--create-tasks", action="store_true",
                        help="Auto-create onboarding tasks for high-confidence venues")
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
        _send_discord_report(results)

        auto_venues = [v for v in results if v.triage == "auto"]

        # Persist clubs
        if args.create_clubs and auto_venues:
            print(f"\nInserting {len(auto_venues)} auto-triaged venues into clubs table...")
            created = _create_clubs(auto_venues)
            print(f"Upserted {created} clubs ({len(auto_venues) - created} skipped/filtered)")
        elif auto_venues and not args.create_clubs:
            print(f"\n{len(auto_venues)} venues ready for auto-onboard — pass --create-clubs to persist")

        # Create tasks
        if args.create_tasks and auto_venues:
            print(f"\nCreating onboarding tasks for {len(auto_venues)} auto-triaged venues...")
            created = _create_onboarding_tasks(auto_venues)
            print(f"Created {created} tasks ({len(auto_venues) - created} skipped as duplicates)")
        elif auto_venues and not args.create_tasks:
            print(f"\n{len(auto_venues)} venues ready for task creation — pass --create-tasks to create tusk tasks")

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
