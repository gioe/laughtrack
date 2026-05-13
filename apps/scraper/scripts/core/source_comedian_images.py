#!/usr/bin/env python3
"""Source comedian images from Wikidata and TMDb for missing-image comedians.

Default mode queries the database for comedians with has_image=false, attempts
to source an image for each (Wikidata first, TMDb fallback), uploads to Bunny
CDN, and sets has_image=true for successful uploads.

Re-running is safe — only comedians with has_image=false are processed.

Usage:
    # DB-driven (top-N by total_shows where has_image=false)
    python -m scripts.core.source_comedian_images
    python -m scripts.core.source_comedian_images --dry-run
    python -m scripts.core.source_comedian_images --limit 50

    # Targeted: explicit names bypass the DB candidate query
    python -m scripts.core.source_comedian_images --name "Patton Oswalt"
    python -m scripts.core.source_comedian_images --name "Patton Oswalt" --name "Luenell"
    python -m scripts.core.source_comedian_images --names-file curated.txt
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

from dotenv import dotenv_values

from laughtrack.core.services.image_sourcing import source_comedian_image
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.database.connection import get_connection, get_transaction

# Delay between per-comedian requests (Wikidata + TMDb rate limits)
_IMAGE_SOURCE_DELAY_S = float(os.environ.get("IMAGE_SOURCE_DELAY_S", "1.0"))


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
        help="Max number of comedians to process (default: all). Ignored when --name/--names-file is used.",
    )
    parser.add_argument(
        "--name",
        action="append",
        default=[],
        help="Explicit comedian name to source (repeatable). Bypasses the DB candidate query.",
    )
    parser.add_argument(
        "--names-file",
        type=Path,
        default=None,
        help="Path to a file with one comedian name per line (blank lines and # comments ignored).",
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

    explicit_names = _collect_explicit_names(args.name, args.names_file)
    if explicit_names:
        if args.limit is not None:
            print("Note: --limit ignored when explicit --name/--names-file is provided", file=sys.stderr)
        names = explicit_names
        print(f"Targeting {len(names)} explicit comedian(s) — bypassing DB candidate query")
    else:
        with get_connection() as conn:
            names = get_missing_image_comedians(conn, limit=args.limit)
        print(f"Found {len(names)} comedians with has_image=false")

    if not names:
        print("Nothing to do.")
        return

    if args.dry_run:
        for name in names:
            print(f"  {name}")
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


def _collect_explicit_names(name_args, names_file):
    """Merge --name and --names-file inputs into a deduped, ordered list.

    Preserves first-seen order. File lines are stripped; blanks and lines
    starting with '#' are skipped.
    """
    seen = set()
    ordered = []

    def _add(n):
        n = n.strip()
        if not n or n in seen:
            return
        seen.add(n)
        ordered.append(n)

    for n in name_args or []:
        _add(n)
    if names_file:
        if not names_file.exists():
            print(f"Error: --names-file not found: {names_file}", file=sys.stderr)
            sys.exit(1)
        for line in names_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            _add(stripped)
    return ordered


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
