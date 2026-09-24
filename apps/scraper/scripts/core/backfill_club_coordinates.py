"""Preview or run the shared bounded venue-coordinate enrichment.

The default dry-run lists eligible candidates without provider requests or writes.
Pass --apply to resolve and persist the next batch through the nightly enrichment
path; --limit controls the maximum batch size (default 30).
"""

import argparse
import sys
from pathlib import Path

# Ensure local 'src' takes precedence over any installed laughtrack package.
_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from laughtrack.utilities.domain.club import coordinates  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Preview or apply bounded venue-coordinate enrichment.")
    parser.add_argument("--apply", action="store_true", help="Resolve candidates and persist enrichment results")
    parser.add_argument("--limit", type=int, default=30, help="Process at most N clubs (default: 30)")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be a positive integer")

    if not args.apply:
        rows = coordinates.preview_missing_clubs(limit=args.limit)
        for club in rows:
            print(f"  [candidate] club {club.id} {club.name!r} address={club.address!r} zip={club.zip_code!r}")
        print(f"Dry-run: {len(rows)} eligible candidates; no provider requests or DB writes. Use --apply to resolve.")
        return 0

    result = coordinates.geocode_missing_clubs(limit=args.limit)
    print(
        f"Summary: attempted={result.attempted} resolved={result.resolved} unresolved={result.unresolved} "
        f"failed={result.failed} retried={result.retried} skipped={result.skipped}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
