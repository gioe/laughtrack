#!/usr/bin/env python3
"""Source comedian images from Wikidata and TMDb for all missing-image comedians.

Queries the database for comedians with has_image=false, attempts to source an
image for each (Wikidata first, TMDb fallback), uploads to Bunny CDN, and sets
has_image=true for successful uploads.

Re-running is safe — only comedians with has_image=false are processed.

Usage:
    python -m scripts.core.source_comedian_images
    python -m scripts.core.source_comedian_images --dry-run
    python -m scripts.core.source_comedian_images --limit 50
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Locate scraper root (apps/scraper/) by walking up to pyproject.toml, then
# put src/ + scraper root on sys.path so laughtrack imports resolve.
_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import psycopg2
from dotenv import dotenv_values

from laughtrack.core.services.image_sourcing import source_comedian_image
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.database.connection import get_transaction

# Delay between per-comedian requests (Wikidata + TMDb rate limits)
_IMAGE_SOURCE_DELAY_S = float(os.environ.get("IMAGE_SOURCE_DELAY_S", "1.0"))


def get_connection():
    v = {**dotenv_values(".env"), **os.environ}
    return psycopg2.connect(
        dbname=v["DATABASE_NAME"],
        user=v["DATABASE_USER"],
        password=v["DATABASE_PASSWORD"],
        host=v["DATABASE_HOST"],
        port=v.get("DATABASE_PORT", "5432"),
        sslmode="require",
    )


def get_missing_image_comedians(conn, limit=None):
    """Fetch comedian names where has_image=false (non-alias only)."""
    query = """
        SELECT name FROM comedians
        WHERE has_image = false
          AND parent_comedian_id IS NULL
        ORDER BY total_shows DESC NULLS LAST, name
    """
    if limit:
        query += f" LIMIT {int(limit)}"

    cur = conn.cursor()
    cur.execute(query)
    return [row[0] for row in cur.fetchall()]


def main():
    parser = argparse.ArgumentParser(
        description="Source comedian images from Wikidata and TMDb",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which comedians would be processed without sourcing images",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of comedians to process (default: all)",
    )
    args = parser.parse_args()

    # Validate CDN credentials before starting
    if not args.dry_run:
        if not os.environ.get("BUNNYCDN_STORAGE_PASSWORD") and not dotenv_values(".env").get("BUNNYCDN_STORAGE_PASSWORD"):
            print("Error: BUNNYCDN_STORAGE_PASSWORD not set in environment or .env", file=sys.stderr)
            sys.exit(1)
        if not os.environ.get("BUNNYCDN_STORAGE_ZONE") and not dotenv_values(".env").get("BUNNYCDN_STORAGE_ZONE"):
            print("Error: BUNNYCDN_STORAGE_ZONE not set in environment or .env", file=sys.stderr)
            sys.exit(1)

    conn = get_connection()
    names = get_missing_image_comedians(conn, limit=args.limit)
    print(f"Found {len(names)} comedians with has_image=false")

    if not names:
        print("Nothing to do.")
        conn.close()
        return

    if args.dry_run:
        for name in names:
            print(f"  {name}")
        conn.close()
        return

    sourced = []
    failed = []
    for i, name in enumerate(names):
        progress = f"[{i + 1}/{len(names)}]"
        try:
            if source_comedian_image(name):
                sourced.append(name)
                print(f"  {progress} ✓ {name}")
            else:
                failed.append(name)
                print(f"  {progress} ✗ {name}")
        except Exception as e:
            failed.append(name)
            Logger.warn(f"image_sourcing: unexpected error for '{name}': {e}")
            print(f"  {progress} ✗ {name} — {e}")

        # Rate-limit between requests
        if i < len(names) - 1:
            time.sleep(_IMAGE_SOURCE_DELAY_S)

        # Batch-update has_image every 50 successful uploads
        if len(sourced) > 0 and len(sourced) % 50 == 0:
            _update_has_image(sourced[-50:])

    # Final batch update for remaining
    remainder = len(sourced) % 50
    if remainder > 0:
        _update_has_image(sourced[-remainder:])

    print(f"\n=== Image Sourcing Complete ===")
    print(f"Processed: {len(names)}")
    print(f"Sourced:   {len(sourced)} ({100 * len(sourced) / len(names):.1f}%)")
    print(f"Failed:    {len(failed)} ({100 * len(failed) / len(names):.1f}%)")

    conn.close()


def _update_has_image(names):
    """Set has_image=true for a batch of comedian names."""
    if not names:
        return
    placeholders = ", ".join(["%s"] * len(names))
    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE comedians SET has_image = true WHERE name IN ({placeholders})",
                tuple(names),
            )
            rowcount = cur.rowcount
    Logger.info(f"source_comedian_images: set has_image=true for {rowcount} comedians")


if __name__ == "__main__":
    main()
