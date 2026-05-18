#!/usr/bin/env python3
"""
Tour-date onboarding queue — source of truth for clubs parked under tour_dates.

Queries clubs with enabled tour_dates scraping_sources rows (created by
TourDatesScraper but never upgraded to a dedicated scraper), fetches each club's
website to detect a scrapeable calendar platform, and classifies each candidate
into one of five states:

    ready        — specific platform marker matched; auto-create onboarding task
    review       — generic match (JSON-LD only); operator picks SCRAPERS.md path
    no-website   — no website on the club row; nothing to audit
    fetch-error  — HTTP / network failure when loading the website
    unknown      — fetched OK but no known platform marker matched

With --create-tasks, the script invokes `tusk dupes check` before each insert
and only creates tasks for the `ready` bucket. Resolves to the project-local
./.claude/bin/tusk so inserts target the same project DB the audit ran against.

Usage:
    python -m scripts.core.audit_tour_date_clubs
    python -m scripts.core.audit_tour_date_clubs --create-tasks
    python -m scripts.core.audit_tour_date_clubs --output audit.csv
    python -m scripts.core.audit_tour_date_clubs --dry-run
"""

import argparse
import asyncio
import csv
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
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
    # Etix / Rockhouse Partners
    ("etix.com", "etix"),
    ("rhp-event__", "etix"),
    ("ROCKHOUSE PARTNERS", "etix"),
    # SellingTicket
    ("sellingticket.com", "sellingticket"),
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
    "etix.com": "etix",
    "sellingticket.com": "sellingticket",
}

# Platforms that should be classified as "review" (operator must verify) rather
# than "ready" (auto-create an onboarding task). The generic JSON-LD marker only
# tells us the page emits schema.org events — it doesn't identify the calendar
# platform, so a human needs to pick the right SCRAPERS.md path.
_REVIEW_PLATFORMS: frozenset[str] = frozenset({"json_ld"})

# Status constants — also the section labels in the report
STATUS_READY = "ready"
STATUS_REVIEW = "review"
STATUS_NO_WEBSITE = "no-website"
STATUS_FETCH_ERROR = "fetch-error"
STATUS_UNKNOWN = "unknown"


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
    matched_marker: Optional[str] = None
    error: Optional[str] = None
    http_status: Optional[int] = None

    @property
    def status(self) -> str:
        if self.error == "no_website":
            return STATUS_NO_WEBSITE
        if self.error:
            return STATUS_FETCH_ERROR
        if self.platform in _REVIEW_PLATFORMS:
            return STATUS_REVIEW
        if self.platform:
            return STATUS_READY
        return STATUS_UNKNOWN

    @property
    def evidence(self) -> str:
        """Human-readable evidence string for operator triage."""
        parts: list[str] = []
        if self.matched_marker:
            parts.append(f"marker={self.matched_marker!r}")
        if self.http_status is not None:
            parts.append(f"http={self.http_status}")
        if self.error and self.error != "no_website":
            parts.append(f"err={self.error}")
        return " ".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

_GET_TOUR_DATE_CLUBS = """
    SELECT DISTINCT c.id, c.name, c.city, c.state, c.website
    FROM clubs c
    JOIN scraping_sources ss ON ss.club_id = c.id
    WHERE ss.platform = 'tour_dates'
      AND ss.enabled = TRUE
    ORDER BY c.name
"""


def _load_tour_date_clubs() -> list[dict]:
    """Load all clubs with an enabled tour_dates scraping source."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_GET_TOUR_DATE_CLUBS)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Website fetching and platform detection
# ---------------------------------------------------------------------------

def _detect_platform_from_url(url: str) -> tuple[Optional[str], Optional[str]]:
    """Detect platform from the website URL domain. Returns (platform, marker)."""
    if not url:
        return None, None
    try:
        from urllib.parse import urlparse
        hostname = (urlparse(url).hostname or "").lower()
        for domain, platform in _WEBSITE_DOMAIN_PLATFORMS.items():
            if hostname.endswith(domain):
                return platform, f"url:{domain}"
    except Exception:
        pass
    return None, None


def _detect_platform_from_html(html: str) -> tuple[Optional[str], Optional[str]]:
    """Detect platform by scanning HTML markers. Returns (platform, marker)."""
    if not html:
        return None, None
    for marker, platform in _HTML_PLATFORM_MARKERS:
        if marker in html:
            return platform, marker
    return None, None


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
    url_platform, url_marker = _detect_platform_from_url(result.website)
    if url_platform:
        result.platform = url_platform
        result.matched_marker = url_marker
        return result

    # Step 2: Fetch website and check HTML
    html, status, error = await _fetch_website(result.website)
    result.http_status = status

    if error:
        result.error = error
        return result

    # Step 3: Detect platform from HTML content
    html_platform, html_marker = _detect_platform_from_html(html)
    result.platform = html_platform
    result.matched_marker = html_marker

    return result


# ---------------------------------------------------------------------------
# Main audit pipeline
# ---------------------------------------------------------------------------

async def _run_audit(concurrency: int = 5) -> list[AuditResult]:
    """Audit all tour_dates clubs for scrapeable platforms."""
    clubs = _load_tour_date_clubs()
    Logger.info(f"Loaded {len(clubs)} clubs with enabled tour_dates scraping_sources")

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


def _bucket_by_status(results: list[AuditResult]) -> dict[str, list[AuditResult]]:
    """Group results by status. Always returns all five buckets (possibly empty)."""
    buckets: dict[str, list[AuditResult]] = {
        STATUS_READY: [],
        STATUS_REVIEW: [],
        STATUS_NO_WEBSITE: [],
        STATUS_FETCH_ERROR: [],
        STATUS_UNKNOWN: [],
    }
    for r in results:
        buckets[r.status].append(r)
    return buckets


def _print_report(results: list[AuditResult]) -> None:
    """Print audit report to stdout."""
    if not results:
        print("\nNo clubs with enabled tour_dates scraping_sources found.")
        return

    buckets = _bucket_by_status(results)
    ready = buckets[STATUS_READY]
    review = buckets[STATUS_REVIEW]
    no_website = buckets[STATUS_NO_WEBSITE]
    errors = buckets[STATUS_FETCH_ERROR]
    unknown = buckets[STATUS_UNKNOWN]

    # Platform breakdown across ready + review
    platform_counts: dict[str, int] = defaultdict(int)
    for r in ready + review:
        if r.platform:
            platform_counts[r.platform] += 1

    print(f"\n{'='*80}")
    print(f"TOUR-DATE ONBOARDING QUEUE — {len(results)} clubs with enabled tour_dates scraping_sources")
    print(f"{'='*80}")
    print(f"  Ready:        {len(ready):4d}    (auto-create onboarding tasks)")
    print(f"  Review:       {len(review):4d}    (generic match — operator picks SCRAPERS.md path)")
    print(f"  No website:   {len(no_website):4d}")
    print(f"  Fetch error:  {len(errors):4d}")
    print(f"  Unknown:      {len(unknown):4d}    (fetched OK but no platform marker matched)")

    if platform_counts:
        print(f"\nPlatform breakdown:")
        for platform, count in sorted(platform_counts.items(), key=lambda x: -x[1]):
            print(f"  {platform:20s} {count}")

    def _section(title: str, rows: list[AuditResult], *, show_url: bool = True) -> None:
        if not rows:
            return
        print(f"\n{'─'*80}")
        print(f"{title} ({len(rows)} clubs)")
        print(f"{'─'*80}")
        for r in sorted(rows, key=lambda r: (r.platform or "", r.name)):
            location = f"{r.city}, {r.state}" if r.city else r.state or ""
            evidence = r.evidence
            line = f"  [{r.club_id:>5d}] {r.name[:38]:<40s} {location[:20]:<22s}"
            if r.platform:
                line += f" platform={r.platform}"
            if show_url and r.website:
                line += f" url={r.website}"
            print(line)
            if evidence:
                print(f"          evidence: {evidence}")

    _section("READY FOR ONBOARDING — specific platform marker matched", ready)
    _section("REVIEW NEEDED — generic match, operator picks SCRAPERS.md path", review)
    _section("NO WEBSITE — needs a website on the club row before audit", no_website, show_url=False)
    _section("FETCH ERROR — could not load the website", errors)
    _section("UNKNOWN — fetched OK but no platform marker matched", unknown)


def _resolve_tusk_binary() -> str:
    """Resolve the tusk binary path.

    Prefers the project-local ./.claude/bin/tusk in this checkout so task
    inserts target the same project DB the audit ran against. Falls back to
    'tusk' on PATH only when no project-local binary is found.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".claude" / "bin" / "tusk"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    fallback = shutil.which("tusk")
    return fallback or "tusk"


def _is_duplicate(tusk_bin: str, summary: str) -> tuple[bool, str]:
    """Check whether `summary` already exists as an open or recently-closed task.

    Returns (is_dupe, reason). Conservative on errors: treats a failed check
    as "not a duplicate" so we don't silently skip every candidate when the
    dupes-check binary is unavailable — the task-insert call still has its
    own dedup guard as a second line of defense.
    """
    try:
        proc = subprocess.run(
            [tusk_bin, "dupes", "check", "--json", "--domain", "scraper", summary],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            Logger.warn(f"  dupes check exited {proc.returncode}: {proc.stderr.strip()[:200]}")
            return False, ""
        payload = json.loads(proc.stdout or "{}")
        dupes = payload.get("duplicates") or []
        recent = payload.get("recently_closed") or []
        if dupes:
            ids = ", ".join(str(d.get("id")) for d in dupes if d.get("id") is not None)
            return True, f"duplicates: {ids}" if ids else "duplicates: yes"
        if recent:
            ids = ", ".join(str(d.get("id")) for d in recent if d.get("id") is not None)
            return True, f"recently closed: {ids}" if ids else "recently closed: yes"
        return False, ""
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        Logger.warn(f"  dupes check failed ({type(e).__name__}): {e}")
        return False, ""


def _create_onboarding_tasks(results: list[AuditResult]) -> int:
    """Create tusk onboarding tasks for READY entries. Returns count created."""
    tusk_bin = _resolve_tusk_binary()
    Logger.info(f"Using tusk binary: {tusk_bin}")

    created = 0
    for r in results:
        if r.status != STATUS_READY:
            continue

        location = f"{r.city}, {r.state}" if r.city else r.state or ""
        summary = f"Onboard {r.name}"
        if location:
            summary += f" ({location})"

        is_dupe, dupe_reason = _is_duplicate(tusk_bin, summary)
        if is_dupe:
            Logger.info(f"  Skipped (dupe — {dupe_reason}): {summary}")
            continue

        description_parts = [
            f"Club already in DB (id={r.club_id}) with an enabled tour_dates scraping_sources row.",
            f"Website: {r.website} — detected platform: {r.platform}.",
            f"Upgrade from tour_dates discovery to dedicated {r.platform} scraper.",
        ]
        if r.evidence:
            description_parts.append(f"Detection evidence: {r.evidence}")
        description = " ".join(description_parts)

        cmd = [
            tusk_bin, "task-insert",
            summary, description,
            "--priority", "Medium",
            "--domain", "scraper",
            "--task-type", "feature",
            "--complexity", "S",
            "--criteria", f"Upgrade club id={r.club_id} from tour_dates to '{r.platform}' with correct platform config",
            "--criteria", f"Verify scraper produces show records for {r.name}",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                created += 1
                Logger.info(f"  Created task: {summary}")
            elif result.returncode == 1:
                Logger.info(f"  Skipped (duplicate caught by task-insert): {summary}")
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
                w.writerow([
                    "club_id", "name", "city", "state", "website",
                    "status", "platform", "matched_marker", "http_status", "error",
                ])
                for r in results:
                    w.writerow([
                        r.club_id, r.name, r.city, r.state, r.website,
                        r.status, r.platform or "", r.matched_marker or "",
                        r.http_status if r.http_status is not None else "",
                        r.error or "",
                    ])
            print(f"\nCSV written to {args.output}")

        ready = [r for r in results if r.status == STATUS_READY]
        if args.create_tasks and not args.dry_run and ready:
            print(f"\nCreating onboarding tasks for {len(ready)} READY clubs...")
            created = _create_onboarding_tasks(results)
            print(f"Created {created} tasks ({len(ready) - created} skipped as duplicates)")
        elif ready and not args.create_tasks:
            print(f"\n{len(ready)} READY clubs — pass --create-tasks to create tusk tasks")

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
