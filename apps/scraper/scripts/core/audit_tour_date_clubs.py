#!/usr/bin/env python3
"""
Audit clubs discovered via tour-date scraping and identify onboarding candidates.

Queries clubs with scraper='tour_dates' (created by TourDatesScraper but never
upgraded to a dedicated scraper), fetches each club's website to detect a
scrapeable calendar platform, and reports findings. Optionally creates tusk
onboarding tasks for clubs with detected platforms.

Usage:
    python -m scripts.core.audit_tour_date_clubs
    python -m scripts.core.audit_tour_date_clubs --create-tasks
    python -m scripts.core.audit_tour_date_clubs --output audit.csv
    python -m scripts.core.audit_tour_date_clubs --dry-run
"""

import argparse
import asyncio
import csv
import os
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger


# ---------------------------------------------------------------------------
# Platform detection patterns (HTML source inspection)
# ---------------------------------------------------------------------------

# Maps (marker_in_html, platform_name). Checked in order; first match wins.
_HTML_PLATFORM_MARKERS: list[tuple[str, str]] = [
    # Squarespace
    ("Static.SQUARESPACE_CONTEXT", "squarespace"),
    # Wix Events
    ("wix-events-widget", "wix"),
    ("wixstatic.com", "wix"),
    # SeatEngine
    ("seatengine.com", "seatengine"),
    ("seatengine.net", "seatengine"),
    # Eventbrite embedded
    ("eventbrite.com/e/", "eventbrite"),
    ("eventbrite.com/o/", "eventbrite"),
    ("eventbriteapi.com", "eventbrite"),
    # Ticketmaster / LiveNation
    ("ticketmaster.com", "ticketmaster"),
    ("livenation.com", "ticketmaster"),
    # Crowdwork
    ("crowdwork.com", "crowdwork"),
    # Tockify
    ("tockify.com", "tockify"),
    # VBO Tickets
    ("vbotickets.com", "vbo_tickets"),
    # ThunderTix
    ("thundertix.com", "thundertix"),
    # Tixr
    ("tixr.com", "tixr"),
    # OvationTix
    ("ovationtix.com", "ovationtix"),
    # SquadUP
    ("squadup", "squadup"),
    # Tribe Events (WordPress)
    ("tribe-events", "tribe_events"),
    ("/wp-json/tribe/events", "tribe_events"),
    # Humanitix
    ("humanitix.com", "humanitix"),
    # Prekindle
    ("prekindle.com", "prekindle"),
    # Ninkashi
    ("ninkashi.com", "ninkashi"),
    # StageTime
    ("stageti.me", "stagetime"),
    # OpenDate
    ("opendate.io", "opendate"),
    # TicketSource
    ("ticketsource.us", "ticketsource"),
    ("ticketsource.co.uk", "ticketsource"),
    # SimpleTix
    ("simpletix.com", "simpletix"),
    # JSON-LD events (generic)
    ('"@type":"Event"', "json_ld"),
    ('"@type": "Event"', "json_ld"),
    ('"@type":"ComedyEvent"', "json_ld"),
    ('"@type": "ComedyEvent"', "json_ld"),
]

# URL-based platform detection — check the club website domain itself
_WEBSITE_DOMAIN_PLATFORMS: dict[str, str] = {
    "eventbrite.com": "eventbrite",
    "seatengine.com": "seatengine",
    "squarespace.com": "squarespace",
    "wixsite.com": "wix",
    "tockify.com": "tockify",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AuditResult:
    club_id: int
    name: str
    city: str
    state: str
    website: str
    platform: Optional[str] = None
    error: Optional[str] = None
    http_status: Optional[int] = None

    @property
    def status(self) -> str:
        if self.error:
            return "error"
        if self.platform:
            return "detected"
        return "unknown"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

_GET_TOUR_DATE_CLUBS = """
    SELECT id, name, city, state, website
    FROM clubs
    WHERE scraper = 'tour_dates'
    ORDER BY name
"""


def _load_tour_date_clubs() -> list[dict]:
    """Load all clubs with scraper='tour_dates'."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_GET_TOUR_DATE_CLUBS)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Website fetching and platform detection
# ---------------------------------------------------------------------------

def _detect_platform_from_url(url: str) -> Optional[str]:
    """Detect platform from the website URL domain alone."""
    if not url:
        return None
    try:
        from urllib.parse import urlparse
        hostname = (urlparse(url).hostname or "").lower()
        for domain, platform in _WEBSITE_DOMAIN_PLATFORMS.items():
            if hostname.endswith(domain):
                return platform
    except Exception:
        pass
    return None


def _detect_platform_from_html(html: str) -> Optional[str]:
    """Detect platform by scanning HTML for known markers."""
    if not html:
        return None
    for marker, platform in _HTML_PLATFORM_MARKERS:
        if marker in html:
            return platform
    return None


async def _fetch_website(url: str, timeout: int = 20) -> tuple[Optional[str], Optional[int], Optional[str]]:
    """Fetch website HTML. Returns (html, status_code, error)."""
    if not url:
        return None, None, "no_url"

    # Ensure URL has a scheme
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        from curl_cffi.requests import AsyncSession
        async with AsyncSession() as session:
            resp = await session.get(
                url,
                timeout=timeout,
                impersonate="chrome",
                allow_redirects=True,
            )
            if resp.status_code == 200:
                return resp.text, resp.status_code, None
            return None, resp.status_code, f"http_{resp.status_code}"
    except Exception as e:
        error_type = type(e).__name__
        return None, None, f"{error_type}: {str(e)[:100]}"


async def _audit_club(club: dict) -> AuditResult:
    """Audit a single club: fetch website and detect platform."""
    result = AuditResult(
        club_id=club["id"],
        name=club["name"],
        city=club.get("city") or "",
        state=club.get("state") or "",
        website=club.get("website") or "",
    )

    if not result.website:
        result.error = "no_website"
        return result

    # Step 1: Check URL-based platform detection
    url_platform = _detect_platform_from_url(result.website)
    if url_platform:
        result.platform = url_platform
        return result

    # Step 2: Fetch website and check HTML
    html, status, error = await _fetch_website(result.website)
    result.http_status = status

    if error:
        result.error = error
        return result

    # Step 3: Detect platform from HTML content
    result.platform = _detect_platform_from_html(html)

    return result


# ---------------------------------------------------------------------------
# Main audit pipeline
# ---------------------------------------------------------------------------

async def _run_audit(concurrency: int = 5) -> list[AuditResult]:
    """Audit all tour_dates clubs for scrapeable platforms."""
    clubs = _load_tour_date_clubs()
    Logger.info(f"Loaded {len(clubs)} clubs with scraper='tour_dates'")

    if not clubs:
        return []

    results: list[AuditResult] = []
    semaphore = asyncio.Semaphore(concurrency)
    processed = 0

    async def process(club: dict) -> AuditResult:
        nonlocal processed
        async with semaphore:
            result = await _audit_club(club)
            processed += 1
            status = result.platform or result.error or "unknown"
            Logger.info(f"  [{processed}/{len(clubs)}] {club['name']}: {status}")
            return result

    results = await asyncio.gather(*[process(c) for c in clubs])
    return list(results)


def _print_report(results: list[AuditResult]) -> None:
    """Print audit report to stdout."""
    if not results:
        print("\nNo clubs with scraper='tour_dates' found.")
        return

    detected = [r for r in results if r.platform]
    no_website = [r for r in results if r.error == "no_website"]
    errors = [r for r in results if r.error and r.error != "no_website"]
    unknown = [r for r in results if not r.platform and not r.error]

    # Platform breakdown
    platform_counts: dict[str, int] = defaultdict(int)
    for r in detected:
        platform_counts[r.platform] += 1

    print(f"\n{'='*80}")
    print(f"TOUR-DATE CLUB AUDIT — {len(results)} clubs with scraper='tour_dates'")
    print(f"{'='*80}")
    print(f"  Platform detected: {len(detected):4d}")
    print(f"  No website:        {len(no_website):4d}")
    print(f"  Fetch errors:      {len(errors):4d}")
    print(f"  Unknown platform:  {len(unknown):4d}")

    if platform_counts:
        print(f"\nPlatform breakdown:")
        for platform, count in sorted(platform_counts.items(), key=lambda x: -x[1]):
            print(f"  {platform:20s} {count}")

    if detected:
        print(f"\n{'─'*80}")
        print(f"ONBOARDING CANDIDATES ({len(detected)} clubs with detected platforms)")
        print(f"{'─'*80}")
        print(f"{'ID':>5s}  {'Club':<35s} {'City, State':<25s} {'Platform'}")
        print(f"{'─'*80}")
        for r in sorted(detected, key=lambda r: (r.platform, r.name)):
            location = f"{r.city}, {r.state}" if r.city else r.state or ""
            print(f"{r.club_id:>5d}  {r.name[:34]:<35s} {location[:24]:<25s} {r.platform}")

    if no_website:
        print(f"\n{'─'*80}")
        print(f"NO WEBSITE ({len(no_website)} clubs)")
        print(f"{'─'*80}")
        for r in sorted(no_website, key=lambda r: r.name):
            location = f"{r.city}, {r.state}" if r.city else r.state or ""
            print(f"  {r.name[:40]:<42s} {location}")

    if errors:
        print(f"\n{'─'*80}")
        print(f"FETCH ERRORS ({len(errors)} clubs)")
        print(f"{'─'*80}")
        for r in sorted(errors, key=lambda r: r.name):
            print(f"  {r.name[:40]:<42s} {r.website[:30]:<32s} {r.error}")

    if unknown:
        print(f"\n{'─'*80}")
        print(f"UNKNOWN PLATFORM ({len(unknown)} clubs — manual review needed)")
        print(f"{'─'*80}")
        for r in sorted(unknown, key=lambda r: r.name):
            location = f"{r.city}, {r.state}" if r.city else r.state or ""
            print(f"  {r.name[:40]:<42s} {location:<25s} {r.website}")


def _create_onboarding_tasks(results: list[AuditResult]) -> int:
    """Create tusk onboarding tasks for clubs with detected platforms. Returns count created."""
    created = 0
    for r in results:
        if not r.platform:
            continue

        location = f"{r.city}, {r.state}" if r.city else r.state or ""
        summary = f"Onboard {r.name}"
        if location:
            summary += f" ({location})"

        description = (
            f"Club already in DB (id={r.club_id}) with scraper='tour_dates'. "
            f"Website: {r.website} — detected platform: {r.platform}. "
            f"Upgrade from tour_dates discovery to dedicated {r.platform} scraper."
        )

        cmd = [
            "tusk", "task-insert",
            summary, description,
            "--priority", "Medium",
            "--domain", "scraper",
            "--task-type", "feature",
            "--complexity", "S",
            "--criteria", f"Update club id={r.club_id} scraper to '{r.platform}' with correct platform config",
            "--criteria", f"Verify scraper produces show records for {r.name}",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                created += 1
                Logger.info(f"  Created task: {summary}")
            elif result.returncode == 1:
                Logger.info(f"  Skipped (duplicate): {summary}")
            else:
                Logger.warn(f"  Failed to create task for {r.name}: {result.stderr.strip()}")
        except Exception as e:
            Logger.warn(f"  Error creating task for {r.name}: {e}")

    return created


def main():
    parser = argparse.ArgumentParser(
        description="Audit tour-date-discovered clubs for scrapeable calendar platforms",
    )
    parser.add_argument("--output", type=str, help="Write CSV results to this path")
    parser.add_argument("--create-tasks", action="store_true",
                        help="Create onboarding tasks for clubs with detected platforms")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run audit without creating tasks (report only)")
    parser.add_argument("--concurrency", type=int, default=5,
                        help="Max concurrent website fetches (default: 5)")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        current = os.environ.get("LAUGHTRACK_LOG_CONSOLE_LEVEL", "").upper()
        if current not in ("DEBUG", "INFO"):
            os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "INFO"

    try:
        results = asyncio.run(_run_audit(concurrency=args.concurrency))
        _print_report(results)

        if args.output and results:
            with open(args.output, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["club_id", "name", "city", "state", "website", "platform", "status", "error"])
                for r in results:
                    w.writerow([
                        r.club_id, r.name, r.city, r.state,
                        r.website, r.platform or "", r.status, r.error or "",
                    ])
            print(f"\nCSV written to {args.output}")

        detected = [r for r in results if r.platform]
        if args.create_tasks and not args.dry_run and detected:
            print(f"\nCreating onboarding tasks for {len(detected)} clubs with detected platforms...")
            created = _create_onboarding_tasks(results)
            print(f"Created {created} tasks ({len(detected) - created} skipped as duplicates)")
        elif detected and not args.create_tasks:
            print(f"\n{len(detected)} clubs ready for onboarding — pass --create-tasks to create tusk tasks")

        print(f"\nTotal: {len(results)} tour-date clubs audited")

    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        Logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
