#!/usr/bin/env python3
"""
Discover Bandsintown/Songkick widget IDs from comedian websites.

Fetches both the homepage (website) and scraping URL for comedians who
don't yet have widget IDs. Runs widget detection on each page and
persists any discovered IDs.

Usage:
    python -m scripts.core.discover_widget_ids
    python -m scripts.core.discover_widget_ids --limit 100
    python -m scripts.core.discover_widget_ids --dry-run --limit 20
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
from laughtrack.scrapers.implementations.api.comedian_websites.widget_detector import detect_widgets


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_GET_COMEDIANS_NEEDING_WIDGETS = """
    SELECT uuid, name, website, website_scraping_url
    FROM comedians
    WHERE website IS NOT NULL
      AND website <> ''
      AND bandsintown_id IS NULL
      AND songkick_id IS NULL
      AND (website_confidence IS NULL OR website_confidence != 'low')
    ORDER BY popularity DESC NULLS LAST
"""

_UPDATE_WIDGET_IDS = """
    UPDATE comedians
    SET bandsintown_id = COALESCE(%s, bandsintown_id),
        songkick_id = COALESCE(%s, songkick_id)
    WHERE uuid = %s
"""


# ---------------------------------------------------------------------------
# HTML fetching
# ---------------------------------------------------------------------------

async def _fetch_html(url: str, timeout: int = 20) -> Optional[str]:
    try:
        from curl_cffi.requests import AsyncSession
        async with AsyncSession() as session:
            resp = await session.get(url, timeout=timeout, impersonate="chrome")
            if resp.status_code == 200:
                return resp.text
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

async def _discover_widgets(
    limit: Optional[int] = None,
    dry_run: bool = False,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            query = _GET_COMEDIANS_NEEDING_WIDGETS
            if limit:
                query += f" LIMIT {limit}"
            cur.execute(query)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    total = len(rows)
    Logger.info(f"Found {total} comedians without widget IDs to scan")

    if not rows:
        return

    found_bit = 0
    found_sk = 0
    updates: list[tuple[Optional[str], Optional[str], str]] = []
    semaphore = asyncio.Semaphore(10)

    async def process(row: dict):
        nonlocal found_bit, found_sk
        name = row["name"]
        website = (row.get("website") or "").strip()
        scraping_url = (row.get("website_scraping_url") or "").strip()

        async with semaphore:
            bit_id = None
            sk_id = None

            # Check homepage first (most widgets are on the homepage)
            if website:
                html = await _fetch_html(website)
                if html:
                    result = detect_widgets(html)
                    bit_id = result.bandsintown_id
                    sk_id = result.songkick_id

            # If nothing found on homepage, try scraping URL
            if not bit_id and not sk_id and scraping_url and scraping_url != website:
                html = await _fetch_html(scraping_url)
                if html:
                    result = detect_widgets(html)
                    bit_id = result.bandsintown_id
                    sk_id = result.songkick_id

            if bit_id or sk_id:
                parts = []
                if bit_id:
                    parts.append(f"BIT={bit_id}")
                    found_bit += 1
                if sk_id:
                    parts.append(f"SK={sk_id}")
                    found_sk += 1
                Logger.info(f"  {name}: {', '.join(parts)}")
                updates.append((bit_id, sk_id, row["uuid"]))

    await asyncio.gather(*[process(row) for row in rows])

    Logger.info(f"Scan complete: {len(updates)}/{total} found ({found_bit} BIT, {found_sk} SK)")

    if dry_run:
        print(f"\nDRY RUN — {len(updates)} widget IDs would be written")
        return

    if not updates:
        print(f"\nNo new widget IDs found")
        return

    # Persist
    with get_connection() as conn:
        with conn.cursor() as cur:
            for bit_id, sk_id, uuid in updates:
                cur.execute(_UPDATE_WIDGET_IDS, (bit_id, sk_id, uuid))

    print(f"\nWritten {len(updates)} widget IDs ({found_bit} Bandsintown, {found_sk} Songkick)")


def main():
    parser = argparse.ArgumentParser(
        description="Discover Bandsintown/Songkick widget IDs from comedian websites",
    )
    parser.add_argument("--limit", type=int, help="Max comedians to scan")
    parser.add_argument("--dry-run", action="store_true", help="Show results without writing to DB")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        current = os.environ.get("LAUGHTRACK_LOG_CONSOLE_LEVEL", "").upper()
        if current not in ("DEBUG", "INFO"):
            os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "INFO"

    try:
        asyncio.run(_discover_widgets(limit=args.limit, dry_run=args.dry_run))
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        Logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
