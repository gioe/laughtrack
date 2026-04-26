#!/usr/bin/env python3
"""
Discover website_scraping_url for comedians who have a website but no scraping URL.

Fetches each comedian's homepage, detects tour/shows/events subpage links,
verifies they contain JSON-LD events, and writes the best one to
website_scraping_url with a confidence score.

Usage:
    python -m scripts.core.discover_scraping_urls
    python -m scripts.core.discover_scraping_urls --limit 50
    python -m scripts.core.discover_scraping_urls --comedian-name "John Mulaney"
    python -m scripts.core.discover_scraping_urls --dry-run --limit 10
    python -m scripts.core.discover_scraping_urls --include-homepage
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.implementations.api.comedian_websites.tour_link_detector import detect_tour_links
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.utilities.domain.comedian.website_confidence import score_website


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_GET_COMEDIANS_NEEDING_SCRAPING_URL = """
    SELECT uuid, name, website
    FROM comedians
    WHERE website IS NOT NULL
      AND website <> ''
      AND (website_scraping_url IS NULL OR website_scraping_url = '')
      AND (website_confidence IS NULL OR website_confidence != 'low')
    ORDER BY popularity DESC NULLS LAST
"""

_UPDATE_SCRAPING_URL_AND_CONFIDENCE = """
    UPDATE comedians
    SET website_scraping_url = %s,
        website_scraping_url_confidence = %s
    WHERE uuid = %s
"""


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


# ---------------------------------------------------------------------------
# Discovery logic
# ---------------------------------------------------------------------------

async def _discover_for_comedian(
    uuid: str,
    name: str,
    website: str,
    include_homepage: bool = False,
) -> Optional[tuple[str, str]]:
    """Discover the best scraping URL for a comedian.

    Returns (scraping_url, confidence) or None if nothing found.
    """
    html = await _fetch_html(website)
    if not html:
        return None

    # Check for tour subpage links
    tour_links = detect_tour_links(html, website)

    # Try each tour link — pick the first one with JSON-LD events
    for link in tour_links[:3]:
        subpage_html = await _fetch_html(link)
        if not subpage_html:
            continue
        events = EventExtractor.extract_events(subpage_html)
        if events:
            confidence = score_website(name, link, has_events=True).confidence
            Logger.info(f"  {name}: {link} — {len(events)} events ({confidence})")
            return link, confidence

    # If no tour subpage had events, try tour links without event verification
    if tour_links:
        best_link = tour_links[0]
        confidence = score_website(name, best_link, has_events=False).confidence
        Logger.info(f"  {name}: {best_link} — no events but tour link found ({confidence})")
        return best_link, confidence

    # Fallback: use homepage itself if it has JSON-LD events
    if include_homepage:
        events = EventExtractor.extract_events(html)
        if events:
            confidence = score_website(name, website, has_events=True).confidence
            Logger.info(f"  {name}: {website} — {len(events)} homepage events ({confidence})")
            return website, confidence

    return None


async def _run_discovery(
    limit: Optional[int] = None,
    comedian_name: Optional[str] = None,
    dry_run: bool = False,
    include_homepage: bool = False,
):
    """Run the scraping URL discovery pipeline."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            query = _GET_COMEDIANS_NEEDING_SCRAPING_URL
            params: tuple = ()
            if comedian_name:
                query += " AND LOWER(name) LIKE LOWER(%s)"
                params = (f"%{comedian_name}%",)
            if limit:
                query += " LIMIT %s"
                params = params + (limit,)
            cur.execute(query, params)
            rows = cur.fetchall()

    total = len(rows)
    Logger.info(f"Found {total} comedians needing scraping URL discovery")

    if not rows:
        return

    semaphore = asyncio.Semaphore(5)
    found = 0
    errors = 0
    results: list[tuple[str, str, str]] = []  # (uuid, url, confidence)

    async def process(uuid: str, name: str, website: str):
        nonlocal found, errors
        async with semaphore:
            try:
                result = await _discover_for_comedian(uuid, name, website, include_homepage)
                if result:
                    scraping_url, confidence = result
                    results.append((uuid, scraping_url, confidence))
                    found += 1
            except Exception as e:
                Logger.warn(f"  {name}: error — {e}")
                errors += 1

    await asyncio.gather(*[process(uuid, name, website) for uuid, name, website in rows])

    Logger.info(f"Discovery complete: {found}/{total} found, {errors} errors")

    if dry_run:
        print(f"\n{'='*70}")
        print(f"DRY RUN — {found} scraping URLs would be written:")
        print(f"{'='*70}")
        for uuid, url, confidence in sorted(results, key=lambda r: r[2]):
            # Find the comedian name
            name = next(n for u, n, _ in rows if u == uuid)
            print(f"  [{confidence:6s}] {name}: {url}")
        return

    if not results:
        return

    # Write to DB
    with get_connection() as conn:
        with conn.cursor() as cur:
            for uuid, scraping_url, confidence in results:
                cur.execute(_UPDATE_SCRAPING_URL_AND_CONFIDENCE, (scraping_url, confidence, uuid))
    Logger.info(f"Wrote {len(results)} scraping URLs to database")

    # Summary
    from collections import Counter
    counts = Counter(c for _, _, c in results)
    print(f"\nResults: {len(results)} scraping URLs discovered")
    for level in ("high", "medium", "low"):
        if counts.get(level):
            print(f"  {level:8s} {counts[level]}")


def main():
    parser = argparse.ArgumentParser(
        description="Discover website_scraping_url for comedians with websites",
    )
    parser.add_argument("--limit", type=int, help="Max comedians to process")
    parser.add_argument("--comedian-name", type=str, help="Process specific comedian (partial match)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be written without updating DB")
    parser.add_argument("--include-homepage", action="store_true",
                        help="Fall back to homepage URL if it has JSON-LD events and no tour subpage found")
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
        asyncio.run(_run_discovery(
            limit=args.limit,
            comedian_name=args.comedian_name,
            dry_run=args.dry_run,
            include_homepage=args.include_homepage,
        ))
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
