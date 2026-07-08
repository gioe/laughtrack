#!/usr/bin/env python3
"""
Canonicalize seatengine_classic source_urls that 3xx-redirect cross-host (TASK-2561).

Background
----------
TASK-2559 found that canonicalizing OTH (club_id=122) from
``offthehookcomedy.com/events`` to ``www.offthehookcomedy.com/events`` cut its
GHA seatengine_classic scrape from 237.68s to 44.70s (5.3x). The redirect tax
was ~0.21s per fetch, paid on 1 listing + 1 calendar + 315 price-detail fetches.

This script extends that fix to the rest of the seatengine_classic platform.
A 2026-06-01 probe (``curl -sI -A 'Mozilla/5.0'``) of all 54 enabled
seatengine_classic ``scraping_sources`` rows found 28 cross-host 302
redirects: 25 add a ``www.`` host prefix, 3 redirect to a different host
entirely (magoobys → magoobysjokehouse, planetofthetapes.seatengine →
planetofthetapes.biz, elpasocomicstrip → laff2nite). All three substantive
target hosts were verified to serve SeatEngine content (grep'd the response
body for ``seatengine``).

What this script does
---------------------
1. Loads each ``scraping_sources`` row by ``ssid`` and verifies the current
   ``source_url`` matches the recorded pre-update value (so a re-run after an
   admin edit refuses to clobber).
2. Validates platform=``seatengine``, scraper_key=``seatengine_classic``,
   enabled=true.
3. Updates ``source_url`` to the canonical target, stamps
   ``metadata.task_2561_canonicalize_source_url`` with the before-value, the
   probed Location header, and the probe timestamp, and bumps ``updated_at``.
4. Idempotent: rows that already have the target ``source_url`` are skipped.

Usage
-----
    cd apps/scraper && make run-script SCRIPT=scripts/core/canonicalize_seatengine_classic_source_urls_2026_06_01.py ARGS='--dry-run'
    cd apps/scraper && make run-script SCRIPT=scripts/core/canonicalize_seatengine_classic_source_urls_2026_06_01.py
"""

import argparse
import json
import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction

_METADATA_KEY = "task_2561_canonicalize_source_url"
_PROBE_TIMESTAMP = "2026-06-01"
_PROBE_USER_AGENT = "Mozilla/5.0"


# (ssid, expected_club_id, expected_source_url_before, canonical_source_url_after, probed_location)
_TARGETS: list[tuple[int, int, str, str, str]] = [
    (77, 88, "barrelroompdx.com/events",
     "https://www.barrelroompdx.com/events",
     "https://www.barrelroompdx.com/events"),
    (584, 90, "bricktowncomedyclub.com/events",
     "https://www.bricktowncomedy.com/events",
     "https://www.bricktowncomedy.com/events"),
    (537, 92, "brickyscomedy.com/events",
     "https://www.brickyscomedy.com/events",
     "https://www.brickyscomedy.com/events"),
    (86, 95, "coastalcomedynight.com/events",
     "https://www.coastalcomedynight.com/events",
     "https://www.coastalcomedynight.com/events"),
    (569, 97, "cabinlaughs.com/events",
     "https://www.cabinlaughs.com/events",
     "https://www.cabinlaughs.com/events"),
    (76, 47, "comedyinharlem.com/events",
     "https://www.comedyinharlem.com/events",
     "https://www.comedyinharlem.com/events"),
    (11, 59, "comedyzone.com/events",
     "https://www.comedyzone.com/events",
     "https://www.comedyzone.com/events"),
    (610, 104, "desertridgeimprov.com/events",
     "https://www.desertridgeimprov.com/events",
     "https://www.desertridgeimprov.com/events"),
    (14, 106, "emeraldcitycomedy.com/events",
     "https://www.emeraldcitycomedy.com/events",
     "https://www.emeraldcitycomedy.com/events"),
    (44, 53, "improvftl.com/events",
     "https://www.improvftl.com/events",
     "https://www.improvftl.com/events"),
    (633, 116, "looneescc.com/events",
     "https://www.looneescc.com/events",
     "https://www.looneescc.com/events"),
    (415, 118, "magoobys.com/events",
     "https://www.magoobysjokehouse.com/events",
     "https://www.magoobysjokehouse.com/events"),
    (326, 123, "planetofthetapes.seatengine.com/events",
     "https://www.planetofthetapes.biz/events",
     "https://www.planetofthetapes.biz/events"),
    (133, 126, "snapperscomedyclub.com/events",
     "https://www.snapperscomedyclub.com/events",
     "https://www.snapperscomedyclub.com/events"),
    (431, 127, "snappersgrill.com/events",
     "https://www.snappersgrill.com/events",
     "https://www.snappersgrill.com/events"),
    (79, 128, "spokanecomedyclub.com/events",
     "https://www.spokanecomedyclub.com/events",
     "https://www.spokanecomedyclub.com/events"),
    (325, 66, "comedyattic.com/events",
     "https://www.comedyattic.com/events",
     "https://www.comedyattic.com/events"),
    (114, 67, "thecomedycatch.com/events",
     "https://www.thecomedycatch.com/events",
     "https://www.thecomedycatch.com/events"),
    (38, 69, "thecomedyclubkc.com/events",
     "https://www.thecomedyclubkc.com/events",
     "https://www.thecomedyclubkc.com/events"),
    (619, 70, "comedyfortcollins.com/events",
     "https://www.comedyfortcollins.com/events",
     "https://www.comedyfortcollins.com/events"),
    (327, 72, "comedyvaultbatavia.com/events",
     "https://www.comedyvaultbatavia.com/events",
     "https://www.comedyvaultbatavia.com/events"),
    (139, 58, "cltcomedyzone.com/events",
     "https://www.cltcomedyzone.com/events",
     "https://www.cltcomedyzone.com/events"),
    (314, 60, "cherokeecomedyzone.com/events",
     "https://www.cherokeecomedyzone.com/events",
     "https://www.cherokeecomedyzone.com/events"),
    (51, 74, "elpasocomicstrip.com/events",
     "https://www.laff2nite.com/events",
     "https://www.laff2nite.com/events"),
    (147, 75, "tiffscomedy.com/events",
     "https://www.tiffscomedy.com/events",
     "https://www.tiffscomedy.com/events"),
    (182, 77, "thewellcomedyclub.com/events",
     "https://www.thewellcomedyclub.com/events",
     "https://www.thewellcomedyclub.com/events"),
    (333, 79, "undergroundcomedydc.com/events",
     "https://www.undergroundcomedydc.com/events",
     "https://www.undergroundcomedydc.com/events"),
    (299, 83, "witsendcharleston.com/events",
     "https://www.witsendcharleston.com/events",
     "https://www.witsendcharleston.com/events"),
]


def _load_metadata(raw) -> dict:
    if isinstance(raw, str):
        return json.loads(raw)
    if raw is None:
        return {}
    return dict(raw)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Canonicalize seatengine_classic source_urls that 3xx-redirect cross-host (TASK-2561)."
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    print(f"Targets: {len(_TARGETS)} seatengine_classic scraping_sources rows")
    print()

    updated = 0
    skipped_idempotent = 0
    problems: list[str] = []

    with get_transaction() as conn:
        with conn.cursor() as cur:
            for ssid, expected_cid, before_url, after_url, probed_location in _TARGETS:
                cur.execute(
                    """
                    SELECT id, club_id, platform::text, scraper_key, source_url, enabled, metadata
                    FROM scraping_sources
                    WHERE id = %s
                    """,
                    (ssid,),
                )
                row = cur.fetchone()
                if row is None:
                    problems.append(f"ssid={ssid}: row not found")
                    continue

                _id, cid, platform, scraper_key, source_url, enabled, raw_meta = row
                if cid != expected_cid:
                    problems.append(f"ssid={ssid}: club_id={cid}, expected {expected_cid}")
                    continue
                if platform != "seatengine":
                    problems.append(f"ssid={ssid}: platform={platform!r}, expected 'seatengine'")
                    continue
                if scraper_key != "seatengine_classic":
                    problems.append(f"ssid={ssid}: scraper_key={scraper_key!r}, expected 'seatengine_classic'")
                    continue
                if not enabled:
                    problems.append(f"ssid={ssid}: enabled=false (expected true)")
                    continue
                if source_url == after_url:
                    skipped_idempotent += 1
                    print(f"  ssid={ssid:>4} cid={cid:>4} SKIP (already canonical): {source_url}")
                    continue
                if source_url != before_url:
                    problems.append(
                        f"ssid={ssid}: source_url={source_url!r}, expected before-value {before_url!r} "
                        f"(was something else changed since the 2026-06-01 probe?)"
                    )
                    continue

            if problems:
                print("\nABORT: shape mismatch / unexpected state:", file=sys.stderr)
                for p in problems:
                    print(f"  {p}", file=sys.stderr)
                return 1

            if skipped_idempotent == len(_TARGETS):
                print("\nAll rows already canonicalized — nothing to do.")
                return 0

            print("\n=== BEFORE ===")
            for ssid, expected_cid, before_url, after_url, probed_location in _TARGETS:
                cur.execute("SELECT source_url FROM scraping_sources WHERE id = %s", (ssid,))
                cur_url = cur.fetchone()[0]
                if cur_url == after_url:
                    continue
                print(f"  ssid={ssid:>4} cid={expected_cid:>4} {cur_url!r}")

            if args.dry_run:
                print("\n--dry-run: no DB write performed.")
                return 0

            for ssid, expected_cid, before_url, after_url, probed_location in _TARGETS:
                cur.execute("SELECT source_url, metadata FROM scraping_sources WHERE id = %s", (ssid,))
                cur_url, raw_meta = cur.fetchone()
                if cur_url == after_url:
                    continue

                metadata = _load_metadata(raw_meta)
                metadata[_METADATA_KEY] = {
                    "previous_source_url": before_url,
                    "probed_location_header": probed_location,
                    "probed_at": _PROBE_TIMESTAMP,
                    "probed_user_agent": _PROBE_USER_AGENT,
                }

                cur.execute(
                    """
                    UPDATE scraping_sources
                    SET source_url = %s,
                        metadata = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (after_url, json.dumps(metadata, sort_keys=True), ssid),
                )
                updated += 1

            print("\n=== AFTER ===")
            for ssid, expected_cid, before_url, after_url, _loc in _TARGETS:
                cur.execute("SELECT source_url FROM scraping_sources WHERE id = %s", (ssid,))
                cur_url = cur.fetchone()[0]
                print(f"  ssid={ssid:>4} cid={expected_cid:>4} {cur_url!r}")

            print(f"\nUpdated {updated} rows; {skipped_idempotent} already canonical.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
