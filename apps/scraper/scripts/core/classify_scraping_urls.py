#!/usr/bin/env python3
"""
Classify unclassified comedian scraping URLs using Playwright.

Renders each page in a headless browser to detect:
- JSON-LD events (injected by JS frameworks)
- Bandsintown/Songkick widgets (JS-rendered)
- Ticketing platform links (Eventbrite, Ticketmaster, AXS, etc.)

Updates bandsintown_id/songkick_id when widgets are found, and
reports the classification breakdown.

Usage:
    python -m scripts.core.classify_scraping_urls
    python -m scripts.core.classify_scraping_urls --limit 50
    python -m scripts.core.classify_scraping_urls --dry-run --limit 20
"""

import argparse
import asyncio
import csv
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.implementations.api.comedian_websites.widget_detector import detect_widgets
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PageClassification:
    comedian: str
    url: str
    has_json_ld: bool = False
    json_ld_event_count: int = 0
    bandsintown_id: Optional[str] = None
    songkick_id: Optional[str] = None
    platforms: list[str] = field(default_factory=list)
    has_ticket_links: bool = False
    has_event_content: bool = False  # dates, venue names, event-like HTML
    outbound_ticket_urls: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def classification(self) -> str:
        if self.error:
            return "error"
        if self.has_json_ld and self.json_ld_event_count > 0:
            return "json_ld"
        if self.bandsintown_id:
            return "bandsintown"
        if self.songkick_id:
            return "songkick"
        if self.platforms:
            return "ticketing_platform"
        if self.has_event_content:
            return "html_events"
        if self.has_ticket_links:
            return "ticket_links"
        return "no_events"

    @property
    def summary(self) -> str:
        parts = []
        if self.has_json_ld:
            parts.append(f"JSON-LD ({self.json_ld_event_count} events)")
        if self.bandsintown_id:
            parts.append(f"BIT={self.bandsintown_id}")
        if self.songkick_id:
            parts.append(f"SK={self.songkick_id}")
        if self.platforms:
            parts.append(f"platforms: {', '.join(self.platforms)}")
        if self.has_event_content and not self.has_json_ld:
            parts.append("HTML event content")
        if self.outbound_ticket_urls:
            parts.append(f"{len(self.outbound_ticket_urls)} ticket URLs")
        if self.has_ticket_links and not parts:
            parts.append("ticket links only")
        if self.error:
            parts.append(f"error: {self.error}")
        return " | ".join(parts) if parts else "no events detected"


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_GET_UNCLASSIFIED = """
    SELECT uuid, name, website_scraping_url
    FROM comedians
    WHERE website_scraping_url IS NOT NULL
      AND website_scraping_url <> ''
      AND bandsintown_id IS NULL
      AND songkick_id IS NULL
      AND (website_scrape_strategy IS NULL
           OR website_scrape_strategy NOT IN ('json_ld', 'json_ld_subpage'))
    ORDER BY popularity DESC NULLS LAST
"""

_UPDATE_WIDGET_IDS = """
    UPDATE comedians
    SET bandsintown_id = COALESCE(%s, bandsintown_id),
        songkick_id = COALESCE(%s, songkick_id)
    WHERE uuid = %s
"""

_UPDATE_SCRAPE_STRATEGY = """
    UPDATE comedians
    SET website_scrape_strategy = %s
    WHERE uuid = %s
"""


# ---------------------------------------------------------------------------
# Ticketing platform detection
# ---------------------------------------------------------------------------

_PLATFORM_PATTERNS = [
    ("bandsintown", re.compile(r"bandsintown", re.I)),
    ("songkick", re.compile(r"songkick", re.I)),
    ("eventbrite", re.compile(r"eventbrite\.com", re.I)),
    ("ticketmaster", re.compile(r"ticketmaster\.com", re.I)),
    ("axs", re.compile(r"axs\.com", re.I)),
    ("dice", re.compile(r"dice\.fm", re.I)),
    ("seated", re.compile(r"seated\.com", re.I)),
    ("seetickets", re.compile(r"seetickets\.(us|com)", re.I)),
    ("tixr", re.compile(r"tixr\.com", re.I)),
    ("etix", re.compile(r"etix\.com", re.I)),
    ("showclix", re.compile(r"showclix\.com", re.I)),
    ("seatengine", re.compile(r"seatengine\.com", re.I)),
    ("prekindle", re.compile(r"prekindle\.com", re.I)),
    ("simpletix", re.compile(r"simpletix\.com", re.I)),
    ("universe", re.compile(r"universe\.com", re.I)),
    ("veeps", re.compile(r"veeps\.com", re.I)),
    ("momenthouse", re.compile(r"momenthouse\.com", re.I)),
    ("nugs", re.compile(r"nugs\.net", re.I)),
]

_TICKET_RE = re.compile(r"(buy.tickets|get.tickets|book.now|on.sale|purchase.tickets)", re.I)

# Patterns that suggest event listings in plain HTML (dates, venue references)
_DATE_PATTERNS = [
    re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2}", re.I),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
]

# Extract outbound ticket URLs from <a> tags
_TICKET_URL_RE = re.compile(
    r'href=["\']?(https?://[^"\'>\s]*(?:'
    r'eventbrite\.com|ticketmaster\.com|axs\.com|dice\.fm|seated\.com|'
    r'seetickets\.|tixr\.com|etix\.com|showclix\.com|seatengine\.com|'
    r'prekindle\.com|simpletix\.com|universe\.com|veeps\.com|'
    r'ticketweb\.com|freshtix\.com|crowdwork\.com|humanitix\.com|'
    r'ticketsource\.|ovationtix\.com|opendate\.io|venuepilot\.co'
    r')[^"\'>\s]*)',
    re.I,
)


def _classify_html(html: str, name: str) -> PageClassification:
    """Classify a rendered page's content."""
    result = PageClassification(comedian=name, url="")

    # JSON-LD
    events = EventExtractor.extract_events(html)
    if events:
        result.has_json_ld = True
        result.json_ld_event_count = len(events)

    # Widget detection
    widget_result = detect_widgets(html)
    result.bandsintown_id = widget_result.bandsintown_id
    result.songkick_id = widget_result.songkick_id

    # Platform detection
    for platform_name, pattern in _PLATFORM_PATTERNS:
        if platform_name == "bandsintown" and result.bandsintown_id:
            continue
        if platform_name == "songkick" and result.songkick_id:
            continue
        if pattern.search(html):
            result.platforms.append(platform_name)

    # Extract outbound ticket URLs
    ticket_urls = list(set(_TICKET_URL_RE.findall(html)))
    result.outbound_ticket_urls = ticket_urls[:20]  # cap to avoid noise

    # Generic ticket links
    result.has_ticket_links = bool(_TICKET_RE.search(html))

    # HTML event content detection — dates + ticket-like context
    if not result.has_json_ld and not result.bandsintown_id and not result.songkick_id:
        date_matches = sum(len(p.findall(html)) for p in _DATE_PATTERNS)
        if date_matches >= 3 and result.has_ticket_links:
            result.has_event_content = True

    return result


# ---------------------------------------------------------------------------
# Playwright rendering
# ---------------------------------------------------------------------------

async def _render_and_classify(
    rows: list[dict],
    limit: Optional[int],
    dry_run: bool,
) -> list[PageClassification]:
    from playwright.async_api import async_playwright

    if limit:
        rows = rows[:limit]

    results: list[PageClassification] = []
    total = len(rows)
    processed = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        semaphore = asyncio.Semaphore(3)  # 3 concurrent pages

        async def process(row: dict):
            nonlocal processed
            uuid = row["uuid"]
            name = row["name"]
            url = row["website_scraping_url"]

            async with semaphore:
                try:
                    page = await context.new_page()
                    await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)  # Let JS render
                    html = await page.content()
                    await page.close()

                    classification = _classify_html(html, name)
                    classification.url = url

                    processed += 1
                    if processed % 25 == 0:
                        Logger.info(f"  Progress: {processed}/{total}")

                    if classification.classification != "no_events":
                        Logger.info(f"  {name}: {classification.summary}")

                    # Persist widget IDs
                    if not dry_run and (classification.bandsintown_id or classification.songkick_id):
                        with get_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute(_UPDATE_WIDGET_IDS, (
                                    classification.bandsintown_id,
                                    classification.songkick_id,
                                    uuid,
                                ))

                    # Update scrape strategy if JSON-LD found
                    if not dry_run and classification.has_json_ld and classification.json_ld_event_count > 0:
                        with get_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute(_UPDATE_SCRAPE_STRATEGY, ("json_ld", uuid))

                    results.append(classification)

                except Exception as e:
                    err_msg = str(e)[:80]
                    Logger.warn(f"  {name}: error — {err_msg}")
                    c = PageClassification(comedian=name, url=url, error=err_msg)
                    results.append(c)
                    processed += 1

        await asyncio.gather(*[process(row) for row in rows])
        await browser.close()

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _print_report(results: list[PageClassification]) -> None:
    counts = Counter(r.classification for r in results)
    total = len(results)

    print(f"\n{'='*70}")
    print(f"CLASSIFICATION REPORT — {total} pages rendered")
    print(f"{'='*70}")
    for cls in ["json_ld", "bandsintown", "songkick", "ticketing_platform", "html_events", "ticket_links", "no_events", "error"]:
        c = counts.get(cls, 0)
        if c > 0:
            pct = c * 100 // total
            print(f"  {cls:25s} {c:5d}  ({pct}%)")

    # Platform breakdown
    all_platforms: list[str] = []
    for r in results:
        all_platforms.extend(r.platforms)
    if all_platforms:
        platform_counts = Counter(all_platforms)
        print(f"\nTicketing platforms detected:")
        for platform, count in platform_counts.most_common():
            print(f"  {platform:20s} {count}")

    # Show actionable results
    actionable = [r for r in results if r.classification not in ("no_events", "error")]
    if actionable:
        print(f"\n{'─'*70}")
        print(f"ACTIONABLE ({len(actionable)} pages with extractable events)")
        print(f"{'─'*70}")
        for r in sorted(actionable, key=lambda r: r.classification):
            print(f"  [{r.classification:20s}] {r.comedian:25s} {r.summary}")


def main():
    parser = argparse.ArgumentParser(
        description="Classify unclassified scraping URLs using Playwright",
    )
    parser.add_argument("--limit", type=int, help="Max pages to render")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    parser.add_argument("--output", type=str, help="Write CSV to this path")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        current = os.environ.get("LAUGHTRACK_LOG_CONSOLE_LEVEL", "").upper()
        if current not in ("DEBUG", "INFO"):
            os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "INFO"

    # Load unclassified comedians
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_GET_UNCLASSIFIED)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    Logger.info(f"Found {len(rows)} unclassified scraping URLs")

    if not rows:
        print("No unclassified scraping URLs found.")
        return

    try:
        results = asyncio.run(_render_and_classify(rows, limit=args.limit, dry_run=args.dry_run))
        _print_report(results)

        if args.output and results:
            with open(args.output, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["comedian", "url", "classification", "json_ld_events", "bandsintown_id", "songkick_id", "platforms", "ticket_urls", "summary"])
                for r in results:
                    w.writerow([
                        r.comedian, r.url, r.classification,
                        r.json_ld_event_count,
                        r.bandsintown_id or "", r.songkick_id or "",
                        "; ".join(r.platforms),
                        "; ".join(r.outbound_ticket_urls[:5]),
                        r.summary,
                    ])
            print(f"\nCSV written to {args.output}")

    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        Logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
