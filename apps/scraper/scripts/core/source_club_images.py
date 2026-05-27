#!/usr/bin/env python3
"""Source club venue images from website og:image and Google Places.

Default mode queries the database for clubs with has_image=false (top-N by
popularity then total_shows), attempts to source a venue image for each (the
club website's og:image first, a Google Places venue photo as fallback),
uploads to Bunny CDN as ``clubs/{name}.png``, and sets has_image=true for
successful uploads.

Re-running is safe — only clubs with has_image=false are processed.

Usage:
    # DB-driven (top-N imageless clubs by popularity / total_shows)
    python -m scripts.core.source_club_images
    python -m scripts.core.source_club_images --dry-run
    python -m scripts.core.source_club_images --limit 50

    # Review mode: source images to a folder for human review (no CDN write,
    # has_image is NOT flipped)
    python -m scripts.core.source_club_images --review-dir /tmp/club-images

    # Publish reviewed images: each file's stem becomes the club name
    python -m scripts.core.source_club_images --upload-from-dir /tmp/club-images
"""

import argparse
import json
import os
import re
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
    fetch_club_image_png,
    find_club_image_source,
    upload_club_image_png,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.database.connection import get_connection, get_transaction

_SUPPORTED_REVIEW_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

# Delay between per-club source attempts. Lower than the comedian default
# because clubs hit many distinct hosts (not one rate-limited API), and the
# Places client paces its own requests internally.
_CLUB_IMAGE_SOURCE_DELAY_S = float(os.environ.get("CLUB_IMAGE_SOURCE_DELAY_S", "1.0"))

# BunnyCDN storage zone slug rule: lowercase alphanumeric + hyphen.
_BUNNYCDN_ZONE_RE = re.compile(r"^[a-z0-9-]+$")
# BunnyCDN storage regions (https://docs.bunny.net/reference/edge-storage-api-regions).
_BUNNYCDN_REGIONS = {"la", "ny", "sg", "syd", "uk", "se", "br", "jh", "de"}


def _validate_bunny_credentials() -> None:
    """Validate BunnyCDN env vars are present and well-shaped. Exits on failure.

    Assumes ``.env`` defaults have already been merged into ``os.environ`` by
    :func:`_load_env_defaults`.
    """
    if not os.environ.get("BUNNYCDN_STORAGE_PASSWORD"):
        print("Error: BUNNYCDN_STORAGE_PASSWORD not set in environment or .env", file=sys.stderr)
        sys.exit(1)

    zone = os.environ.get("BUNNYCDN_STORAGE_ZONE", "")
    if not zone:
        print("Error: BUNNYCDN_STORAGE_ZONE not set in environment or .env", file=sys.stderr)
        sys.exit(1)
    if not _BUNNYCDN_ZONE_RE.match(zone):
        if "/" in zone or zone.lower().startswith("http"):
            print(
                f"Error: BUNNYCDN_STORAGE_ZONE='{zone}' looks like the full URL — "
                "pass just the zone slug (e.g. 'laughtrack')",
                file=sys.stderr,
            )
        else:
            print(
                f"Error: BUNNYCDN_STORAGE_ZONE='{zone}' must match {_BUNNYCDN_ZONE_RE.pattern} "
                "(lowercase alphanumeric and hyphens only)",
                file=sys.stderr,
            )
        sys.exit(1)

    region = os.environ.get("BUNNYCDN_STORAGE_REGION", "")
    if region and region not in _BUNNYCDN_REGIONS:
        print(
            f"Error: BUNNYCDN_STORAGE_REGION='{region}' is not a known BunnyCDN region. "
            f"Expected one of: {sorted(_BUNNYCDN_REGIONS)}",
            file=sys.stderr,
        )
        sys.exit(1)


def _is_review_safe_name(name: str) -> bool:
    """Return True when a club name is safe as a flat ``<name>.png`` filename.

    Names flow into ``review_dir / f"{name}.png"`` and the round-trip publish
    reads each file's stem back as the club name, so the stem must equal the
    name exactly. Reject path separators, parent traversal, NUL, and leading
    dots so a stray DB value can't escape the review dir or break the stem
    invariant. Unsafe names are skipped (with a warning) rather than crashing
    a batch — they come from the DB, not user CLI input.
    """
    return not (
        "/" in name
        or "\\" in name
        or ".." in name
        or "\x00" in name
        or name.startswith(".")
    )


def get_missing_image_clubs(conn, limit=None):
    """Fetch clubs where has_image=false, highest-value first.

    Returns a list of ``{"name", "website", "place_query"}`` dicts ordered by
    popularity then total_shows so a capped run images the most-trafficked
    venues first. ``place_query`` disambiguates the Google Places fallback
    using city/state when available.
    """
    query = """
        SELECT name, website, city, state FROM clubs
        WHERE has_image = false
          AND (visible IS NULL OR visible = true)
        ORDER BY popularity DESC NULLS LAST, total_shows DESC NULLS LAST, name
    """
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    if limit:
        rows = rows[: int(limit)]

    clubs = []
    for name, website, city, state in rows:
        place_parts = [name] + [p for p in (city, state) if p]
        clubs.append(
            {
                "name": name,
                "website": website,
                "place_query": ", ".join(place_parts),
            }
        )
    return clubs


def _load_env_defaults(path: Path = Path(".env")):
    """Load .env values needed by downstream sourcing helpers."""
    for key, value in dotenv_values(path).items():
        if value:
            os.environ.setdefault(key, value)


def main():
    parser = argparse.ArgumentParser(
        description="Source club venue images from website og:image and Google Places",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List imageless clubs and the chosen candidate source without writing anything",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of clubs to process (default: all). Ignored when --upload-from-dir is used.",
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
        help="Upload pre-reviewed images from this directory. Each file's stem is treated as the club name. Mutually exclusive with --limit/--review-dir.",
    )
    args = parser.parse_args()

    _load_env_defaults()

    if args.upload_from_dir and (args.limit is not None or args.review_dir):
        print("Error: --upload-from-dir cannot be combined with --limit/--review-dir", file=sys.stderr)
        sys.exit(2)

    # Validate CDN credentials before starting (skip for dry-run and review-only)
    needs_cdn = not args.dry_run and not args.review_dir
    if needs_cdn:
        _validate_bunny_credentials()

    if args.upload_from_dir:
        _run_upload_from_dir(args.upload_from_dir, dry_run=args.dry_run)
        return

    with get_connection() as conn:
        clubs = get_missing_image_clubs(conn, limit=args.limit)
    print(f"Found {len(clubs)} clubs with has_image=false")

    if not clubs:
        print("Nothing to do.")
        return

    if args.dry_run:
        _print_dry_run(clubs)
        return

    if args.review_dir:
        args.review_dir.mkdir(parents=True, exist_ok=True)
        print(f"Review mode: saving images to {args.review_dir} (CDN upload skipped, has_image not flipped)")

    sourced = []
    failed = []
    for i, club in enumerate(clubs):
        name = club["name"]
        progress = f"[{i + 1}/{len(clubs)}]"
        try:
            if args.review_dir:
                ok, label = _source_to_review_dir(club, args.review_dir)
            else:
                ok, label = _source_to_cdn(club)
            if ok:
                sourced.append(name)
                print(f"  {progress} ✓ {name} ({label})")
            else:
                failed.append(name)
                print(f"  {progress} ✗ {name}")
        except Exception as e:
            failed.append(name)
            Logger.warn(f"image_sourcing: unexpected error for club '{name}': {e}")
            print(f"  {progress} ✗ {name} — {e}")

        # Rate-limit between clubs
        if i < len(clubs) - 1:
            time.sleep(_CLUB_IMAGE_SOURCE_DELAY_S)

        # Batch-update has_image every 50 successful uploads (CDN mode only)
        if not args.review_dir and len(sourced) > 0 and len(sourced) % 50 == 0:
            _update_has_image(sourced[-50:])

    # Final batch update for remaining (CDN mode only)
    if not args.review_dir:
        remainder = len(sourced) % 50
        if remainder > 0:
            _update_has_image(sourced[-remainder:])

    print(f"\n=== Club Image Sourcing Complete ===")
    print(f"Processed: {len(clubs)}")
    print(f"Sourced:   {len(sourced)} ({100 * len(sourced) / len(clubs):.1f}%)")
    print(f"Failed:    {len(failed)} ({100 * len(failed) / len(clubs):.1f}%)")
    if args.review_dir:
        print(f"\nReview the images in {args.review_dir}, delete any wrong matches,")
        print(f"then publish with:")
        print(f"  python -m scripts.core.source_club_images --upload-from-dir {args.review_dir}")


def _print_dry_run(clubs):
    """Print each imageless club and the source that would be attempted.

    Probes the (free) website og:image only; clubs without one are labelled
    as the Google Places fallback rather than spending paid Places quota on a
    listing pass.
    """
    for club in clubs:
        candidate = find_club_image_source(
            club["name"], club["website"], place_query=club["place_query"], use_places=False
        )
        if candidate is not None:
            label = candidate.source_label
        else:
            label = "google places (fallback — not probed in dry-run)"
        print(f"  {club['name']} — {label}")


def _source_to_review_dir(club, review_dir: Path):
    """Source a club image and save to review_dir/<name>.png.

    Returns ``(ok, label)`` where ``label`` names the candidate source.
    """
    name = club["name"]
    if not _is_review_safe_name(name):
        Logger.warn(f"image_sourcing: skipping club with unsafe name for review file: {name!r}")
        return (False, "")
    result = fetch_club_image_png(name, club["website"], place_query=club["place_query"])
    if result is None:
        return (False, "")
    png, candidate = result
    (review_dir / f"{name}.png").write_bytes(png)
    _persist_places_provenance(name, candidate)
    return (True, candidate.source_label)


def _source_to_cdn(club):
    """Source a club image and upload it to the CDN. Returns ``(ok, label)``."""
    name = club["name"]
    result = fetch_club_image_png(name, club["website"], place_query=club["place_query"])
    if result is None:
        return (False, "")
    png, candidate = result
    ok = upload_club_image_png(name, png)
    if ok:
        _persist_places_provenance(name, candidate)
    return (ok, candidate.source_label)


def _run_upload_from_dir(upload_dir: Path, dry_run: bool):
    """Upload pre-reviewed images from a directory and flip has_image=true."""
    if not upload_dir.exists() or not upload_dir.is_dir():
        print(f"Error: --upload-from-dir not a directory: {upload_dir}", file=sys.stderr)
        sys.exit(1)

    all_files = sorted(
        p for p in upload_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _SUPPORTED_REVIEW_EXTS
    )
    # Dedup by stem so a sibling '<club>.jpg' doesn't double-upload after
    # '<club>.png'. First match (sorted alpha by full name) wins.
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
            if upload_club_image_png(name, path.read_bytes()):
                sourced.append(name)
                print(f"  {progress} ✓ {name}  ({path.name})")
            else:
                failed.append(name)
                print(f"  {progress} ✗ {name}  ({path.name})")
        except Exception as e:
            failed.append(name)
            Logger.warn(f"image_sourcing: unexpected upload error for club '{name}': {e}")
            print(f"  {progress} ✗ {name} — {e}")

    if sourced:
        _update_has_image(sourced)

    print(f"\n=== Upload-from-dir Complete ===")
    print(f"Uploaded:  {len(sourced)} ({100 * len(sourced) / len(candidates):.1f}%)")
    print(f"Failed:    {len(failed)} ({100 * len(failed) / len(candidates):.1f}%)")


def _reject_unsafe_name(name: str, source: str) -> None:
    """Refuse names that could escape the review_dir or push to unintended CDN paths.

    Club names flow into ``clubs/{name}.png`` on the CDN. Reject path
    separators, parent traversal, NUL, and leading dots so a stray reviewed
    filename cannot smuggle e.g. '../etc/passwd'.
    """
    if "/" in name or "\\" in name or ".." in name or "\x00" in name or name.startswith("."):
        print(f"Error: unsafe club name from {source}: {name!r}", file=sys.stderr)
        sys.exit(2)


def _persist_places_provenance(name, candidate):
    """Persist a Google Places candidate's place_id + attribution onto a club.

    No-op for website og:image candidates (no place_id, no attribution). Stores
    the required author attributions as JSONB so they travel with the venue for
    downstream display. Matches the club by unique name, mirroring
    ``_update_has_image``.

    Provenance is intentionally coupled to the *source attempt*, not to CDN
    publication: it is written whenever a Places photo is sourced — both the
    direct ``_source_to_cdn`` path and the ``--review-dir`` staging path. The
    place_id is venue identity and stays correct regardless of whether a staged
    image is later published or discarded, and the ``--upload-from-dir`` publish
    step only has file bytes (no candidate) so it cannot re-derive provenance.
    The chosen storage is a JSON column on ``clubs`` (not a per-image sidecar),
    so persisting at source time is the only point where the candidate exists.
    """
    if candidate.place_id is None and not candidate.attributions:
        return
    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE clubs SET google_place_id = %s, "
                "google_place_attribution = %s::jsonb WHERE name = %s",
                (candidate.place_id, json.dumps(candidate.attributions), name),
            )
            rowcount = cur.rowcount
    if rowcount == 0:
        # Name drift (rename or casing mismatch between fetch and persist) means
        # the provenance was silently dropped — surface it for debugging.
        Logger.warn(
            f"source_club_images: no club matched name {name!r} — Google Places "
            f"provenance not stored (place_id={candidate.place_id!r})"
        )
    else:
        Logger.info(
            f"source_club_images: stored Google Places provenance for {rowcount} club(s) "
            f"(place_id={candidate.place_id!r})"
        )


def _update_has_image(names):
    """Set has_image=true for a batch of club names."""
    if not names:
        return
    placeholders = ", ".join(["%s"] * len(names))
    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE clubs SET has_image = true WHERE name IN ({placeholders})",
                tuple(names),
            )
            rowcount = cur.rowcount
    Logger.info(f"source_club_images: set has_image=true for {rowcount} clubs")


if __name__ == "__main__":
    main()
