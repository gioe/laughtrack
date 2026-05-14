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

    # Review mode: source images to a folder for human review (no CDN write)
    python -m scripts.core.source_comedian_images --names-file curated.txt --review-dir /tmp/headshots

    # Publish reviewed images: each file's stem becomes the comedian name
    python -m scripts.core.source_comedian_images --upload-from-dir /tmp/headshots
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

from laughtrack.core.services.image_sourcing import (
    fetch_comedian_image_png,
    source_comedian_image,
    upload_comedian_image_png,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.database.connection import get_connection, get_transaction

_SUPPORTED_REVIEW_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

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
    parser.add_argument(
        "--review-dir",
        type=Path,
        default=None,
        help="Save sourced images to this directory as <name>.png instead of uploading to the CDN. has_image is NOT flipped — review images, then re-run with --upload-from-dir to publish.",
    )
    parser.add_argument(
        "--upload-from-dir",
        type=Path,
        default=None,
        help="Upload pre-reviewed images from this directory. Each file's stem is treated as the comedian name. Mutually exclusive with --name/--names-file/--limit/--review-dir.",
    )
    args = parser.parse_args()

    if args.upload_from_dir and (args.name or args.names_file or args.limit is not None or args.review_dir):
        print("Error: --upload-from-dir cannot be combined with --name/--names-file/--limit/--review-dir", file=sys.stderr)
        sys.exit(2)

    # Validate CDN credentials before starting (skip for dry-run and review-only)
    needs_cdn = not args.dry_run and not args.review_dir
    if needs_cdn:
        if not os.environ.get("BUNNYCDN_STORAGE_PASSWORD") and not dotenv_values(".env").get("BUNNYCDN_STORAGE_PASSWORD"):
            print("Error: BUNNYCDN_STORAGE_PASSWORD not set in environment or .env", file=sys.stderr)
            sys.exit(1)
        if not os.environ.get("BUNNYCDN_STORAGE_ZONE") and not dotenv_values(".env").get("BUNNYCDN_STORAGE_ZONE"):
            print("Error: BUNNYCDN_STORAGE_ZONE not set in environment or .env", file=sys.stderr)
            sys.exit(1)

    if args.upload_from_dir:
        _run_upload_from_dir(args.upload_from_dir, dry_run=args.dry_run)
        return

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

    if args.review_dir:
        args.review_dir.mkdir(parents=True, exist_ok=True)
        print(f"Review mode: saving images to {args.review_dir} (CDN upload skipped, has_image not flipped)")

    sourced = []
    failed = []
    for i, name in enumerate(names):
        progress = f"[{i + 1}/{len(names)}]"
        try:
            if args.review_dir:
                ok = _source_to_review_dir(name, args.review_dir)
            else:
                ok = source_comedian_image(name)
            if ok:
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

        # Batch-update has_image every 50 successful uploads (CDN mode only)
        if not args.review_dir and len(sourced) > 0 and len(sourced) % 50 == 0:
            _update_has_image(sourced[-50:])

    # Final batch update for remaining (CDN mode only)
    if not args.review_dir:
        remainder = len(sourced) % 50
        if remainder > 0:
            _update_has_image(sourced[-remainder:])

    print(f"\n=== Image Sourcing Complete ===")
    print(f"Processed: {len(names)}")
    print(f"Sourced:   {len(sourced)} ({100 * len(sourced) / len(names):.1f}%)")
    print(f"Failed:    {len(failed)} ({100 * len(failed) / len(names):.1f}%)")
    if args.review_dir:
        print(f"\nReview the images in {args.review_dir}, delete any wrong-person matches,")
        print(f"then publish with:")
        print(f"  python -m scripts.core.source_comedian_images --upload-from-dir {args.review_dir}")


def _source_to_review_dir(name: str, review_dir: Path) -> bool:
    """Source an image and save to review_dir/<name>.png. Returns True on success."""
    png = fetch_comedian_image_png(name)
    if png is None:
        return False
    out_path = review_dir / f"{name}.png"
    out_path.write_bytes(png)
    return True


def _run_upload_from_dir(upload_dir: Path, dry_run: bool):
    """Upload pre-reviewed images from a directory and flip has_image=true."""
    if not upload_dir.exists() or not upload_dir.is_dir():
        print(f"Error: --upload-from-dir not a directory: {upload_dir}", file=sys.stderr)
        sys.exit(1)

    all_files = sorted(
        p for p in upload_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _SUPPORTED_REVIEW_EXTS
    )
    # Dedup by stem so a sibling 'Patton Oswalt.jpg' doesn't double-upload after
    # 'Patton Oswalt.png'. First match (sorted alpha by full name) wins.
    by_stem: dict[str, Path] = {}
    skipped: list[Path] = []
    for p in all_files:
        if p.stem in by_stem:
            skipped.append(p)
            continue
        by_stem[p.stem] = p
    candidates = list(by_stem.values())

    if not candidates:
        print(f"No images found in {upload_dir} (looking for {sorted(_SUPPORTED_REVIEW_EXTS)})")
        return

    for p in candidates:
        _reject_unsafe_name(p.stem, f"--upload-from-dir file {p.name}")

    if skipped:
        print(f"Skipping {len(skipped)} sibling file(s) sharing a stem with an earlier file:")
        for p in skipped:
            print(f"  - {p.name} (stem already covered by another file)")

    print(f"Found {len(candidates)} reviewed image(s) in {upload_dir}")
    if dry_run:
        for p in candidates:
            print(f"  {p.stem}  ({p.name})")
        return

    sourced = []
    failed = []
    for i, path in enumerate(candidates):
        name = path.stem
        progress = f"[{i + 1}/{len(candidates)}]"
        try:
            if upload_comedian_image_png(name, path.read_bytes()):
                sourced.append(name)
                print(f"  {progress} ✓ {name}  ({path.name})")
            else:
                failed.append(name)
                print(f"  {progress} ✗ {name}  ({path.name})")
        except Exception as e:
            failed.append(name)
            Logger.warn(f"image_sourcing: unexpected upload error for '{name}': {e}")
            print(f"  {progress} ✗ {name} — {e}")

    if sourced:
        _update_has_image(sourced)

    print(f"\n=== Upload-from-dir Complete ===")
    print(f"Uploaded:  {len(sourced)} ({100 * len(sourced) / len(candidates):.1f}%)")
    print(f"Failed:    {len(failed)} ({100 * len(failed) / len(candidates):.1f}%)")


def _reject_unsafe_name(name: str, source: str) -> None:
    """Refuse names that could escape the review_dir or push to unintended CDN paths.

    Comedian names flow into ``review_dir / f"{name}.png"`` and into the CDN
    upload path. Reject path separators, parent traversal, NUL, and leading
    dots so a curated --names-file cannot smuggle e.g. '../etc/passwd'.
    """
    if "/" in name or "\\" in name or ".." in name or "\x00" in name or name.startswith("."):
        print(f"Error: unsafe comedian name from {source}: {name!r}", file=sys.stderr)
        sys.exit(2)


def _collect_explicit_names(name_args, names_file):
    """Merge --name and --names-file inputs into a deduped, ordered list.

    Preserves first-seen order. File lines are stripped; blanks and lines
    starting with '#' are skipped. Names containing path separators, '..',
    NUL, or a leading dot are rejected to keep --review-dir writes inside
    the chosen directory and CDN paths under comedians/.
    """
    seen = set()
    ordered = []

    def _add(n, source):
        n = n.strip()
        if not n or n in seen:
            return
        _reject_unsafe_name(n, source)
        seen.add(n)
        ordered.append(n)

    for n in name_args or []:
        _add(n, "--name")
    if names_file:
        if not names_file.exists():
            print(f"Error: --names-file not found: {names_file}", file=sys.stderr)
            sys.exit(1)
        for line in names_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            _add(stripped, f"--names-file {names_file}")
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
