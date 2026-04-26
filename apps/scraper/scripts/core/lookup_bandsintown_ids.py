#!/usr/bin/env python3
"""
Look up Bandsintown artist IDs by comedian name via API.

Queries GET /artists/{name}?app_id=...&api_version=2 for each comedian
that doesn't yet have a bandsintown_id. If the API returns a valid profile
with an `id` field, persists it to the comedians table.

Usage:
    python -m scripts.core.lookup_bandsintown_ids
    python -m scripts.core.lookup_bandsintown_ids --limit 100
    python -m scripts.core.lookup_bandsintown_ids --dry-run --limit 20
"""

import argparse
import asyncio
import os
import ssl
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import quote

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BANDSINTOWN_BASE_URL = "https://rest.bandsintown.com/artists"
_APP_ID = "js_laughtrack"
_API_VERSION = "2"
_DEFAULT_CONCURRENCY = 10
_REQUEST_TIMEOUT = 15

_GET_COMEDIANS_WITHOUT_BANDSINTOWN_ID = """
    SELECT uuid, name
    FROM comedians
    WHERE bandsintown_id IS NULL
    ORDER BY popularity DESC NULLS LAST
"""

_UPDATE_BANDSINTOWN_ID = """
    UPDATE comedians
    SET bandsintown_id = %s
    WHERE uuid = %s
      AND bandsintown_id IS NULL
"""


# ---------------------------------------------------------------------------
# API lookup
# ---------------------------------------------------------------------------

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


async def _lookup_artist(name: str, session) -> Optional[str]:
    """Query Bandsintown for an artist by name. Returns artist ID or None."""
    encoded_name = quote(name, safe="")
    url = f"{_BANDSINTOWN_BASE_URL}/{encoded_name}?app_id={_APP_ID}&api_version={_API_VERSION}"
    try:
        resp = await session.get(url, timeout=_REQUEST_TIMEOUT, impersonate="chrome")
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            return None
        text = resp.text.strip()
        if not text or text == '""':
            return None
        import json
        data = json.loads(text)
        if isinstance(data, dict) and data.get("id"):
            return str(data["id"])
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------

async def _lookup_bandsintown_ids(
    limit: Optional[int] = None,
    dry_run: bool = False,
    concurrency: int = _DEFAULT_CONCURRENCY,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            query = _GET_COMEDIANS_WITHOUT_BANDSINTOWN_ID
            if limit:
                query += f" LIMIT {limit}"
            cur.execute(query)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    total = len(rows)
    Logger.info(f"Found {total} comedians without bandsintown_id to look up")

    if not rows:
        return

    found = 0
    not_found = 0
    errors = 0
    updates: list[tuple[str, str]] = []  # (bandsintown_id, uuid)
    semaphore = asyncio.Semaphore(concurrency)

    from curl_cffi.requests import AsyncSession

    async with AsyncSession() as session:

        async def process(row: dict):
            nonlocal found, not_found, errors
            name = row["name"]
            uuid = row["uuid"]

            async with semaphore:
                try:
                    artist_id = await _lookup_artist(name, session)
                except Exception:
                    errors += 1
                    return

                if artist_id:
                    found += 1
                    updates.append((artist_id, uuid))
                    Logger.info(f"  {name}: bandsintown_id={artist_id}")
                else:
                    not_found += 1

        await asyncio.gather(*[process(row) for row in rows])

    Logger.info(
        f"Lookup complete: {found} found, {not_found} not found, {errors} errors "
        f"(out of {total} comedians)"
    )

    if dry_run:
        print(f"\nDRY RUN — {found} bandsintown_ids would be written")
        for bit_id, uuid in updates[:20]:
            print(f"  {uuid} -> {bit_id}")
        if len(updates) > 20:
            print(f"  ... and {len(updates) - 20} more")
        return

    if not updates:
        print(f"\nNo new bandsintown_ids found")
        return

    # Persist in batches
    batch_size = 100
    with get_connection() as conn:
        with conn.cursor() as cur:
            for i in range(0, len(updates), batch_size):
                batch = updates[i : i + batch_size]
                for bit_id, uuid in batch:
                    cur.execute(_UPDATE_BANDSINTOWN_ID, (bit_id, uuid))

    print(f"\nWritten {len(updates)} bandsintown_ids to the comedians table")


def main():
    parser = argparse.ArgumentParser(
        description="Look up Bandsintown artist IDs by comedian name",
    )
    parser.add_argument("--limit", type=int, help="Max comedians to look up")
    parser.add_argument("--dry-run", action="store_true", help="Show results without writing to DB")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=_DEFAULT_CONCURRENCY,
        help=f"Max concurrent API requests (default: {_DEFAULT_CONCURRENCY})",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        current = os.environ.get("LAUGHTRACK_LOG_CONSOLE_LEVEL", "").upper()
        if current not in ("DEBUG", "INFO"):
            os.environ["LAUGHTRACK_LOG_CONSOLE_LEVEL"] = "INFO"

    try:
        asyncio.run(
            _lookup_bandsintown_ids(
                limit=args.limit,
                dry_run=args.dry_run,
                concurrency=args.concurrency,
            )
        )
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        Logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
