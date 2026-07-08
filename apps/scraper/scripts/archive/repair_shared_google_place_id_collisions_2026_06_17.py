#!/usr/bin/env python3
"""
Repair clubs that share a google_place_id with another club.

Background
----------
Before TASK-2934 gated the ``backfill_club_timezones`` name_geocode step, the
script opportunistically wrote a name-search-resolved place_id +
formatted_address + lat/lng onto ``clubs``. A generic / SEO-junk club name could
match an unrelated venue, so two clubs ended up claiming the same physical place.
The documented incident was club 620 "Comedy Shows Near Me" grabbing Comedy
Cellar's place_id (ChIJmzPYgJFZwokRg4zUwTlZwtI) and 117 MacDougal St (club 620
has since been cleaned up out of band; this script re-asserts that and is a no-op
for it). The same shape also shows up where duplicate-import rows and distinct
venues resolved to one Google place.

A ``google_place_id`` uniquely identifies one physical place, so at most one club
may hold it. This script enforces that invariant.

What this script does
---------------------
For every ``google_place_id`` shared by more than one club it keeps the id on a
single declared "primary" club and nulls the misattributed geocode identity
(``google_place_id`` -> NULL, ``address`` -> '' [NOT NULL column], ``latitude`` /
``longitude`` -> NULL) on the others. ``state`` and ``timezone`` are left intact:
those are the only fields the fixed name_geocode path is now allowed to write and
are correct at the state granularity.

The resolutions are declared explicitly (one ``GroupResolution`` per colliding
place_id) rather than auto-picked by a heuristic, because choosing the legitimate
owner of a physical place is a judgement call on production rows (some with
hundreds of shows). A group with ``keep_club_id=None`` nulls every member -- used
when the colliding clubs are genuinely *distinct* venues that all resolved to a
third, wrong place (e.g. Wicked Funny Danvers vs Salisbury, both mis-geocoded to a
North Andover address).

Safety
------
- Dry-run by default. Pass ``--apply`` to write.
- Idempotent: members already nulled are skipped; re-running writes nothing.
- Refuses if the live set of clubs sharing any place_id is not covered by the
  declared resolutions (a new, undeclared collision appeared since the audit) so
  the repair never silently misses data.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/repair_shared_google_place_id_collisions_2026_06_17.py
    make run-script SCRIPT=scripts/core/repair_shared_google_place_id_collisions_2026_06_17.py ARGS='--apply'
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction


@dataclass(frozen=True)
class GroupResolution:
    """Declared resolution for one colliding google_place_id.

    keep_club_id: the single club that legitimately owns the place_id, or None
        to null the place_id on *every* member (distinct venues all mis-geocoded
        to a third place).
    member_club_ids: every club id observed holding this place_id at audit time.
    """

    place_id: str
    keep_club_id: int | None
    member_club_ids: frozenset[int]
    rationale: str

    def __post_init__(self) -> None:
        if self.keep_club_id is not None and self.keep_club_id not in self.member_club_ids:
            raise ValueError(
                f"keep_club_id={self.keep_club_id} not in members {sorted(self.member_club_ids)}"
            )


# Audited 2026-06-17 against production. Selection rule for keep_club_id:
# most shows -> visible -> lowest id, overridden when the high-show row is the
# clear canonical venue and the others are duplicate-import / junk rows.
GROUPS: list[GroupResolution] = [
    GroupResolution(
        place_id="ChIJ09FBbwy_QIYRy7QNN2j26_8",
        keep_club_id=2952,  # "713 Music Hall" (2 shows); 2951 is a hidden junk-name dup
        member_club_ids=frozenset({2951, 2952}),
        rationale="713 Music Hall duplicate; keep canonical 2952, null junk row 2951.",
    ),
    GroupResolution(
        place_id="ChIJ0TNasENiDogRy06isgSWSY0",
        keep_club_id=2926,  # "Hollywood Casino Joliet" (7 shows); 3046/3047 are 0-show imports
        member_club_ids=frozenset({2926, 3046, 3047}),
        rationale="Hollywood Casino Joliet duplicates; keep 2926, null import rows 3046/3047.",
    ),
    GroupResolution(
        place_id="ChIJ34GzxAG1QYgR1Phf4I5EFLY",
        keep_club_id=2290,  # "Bombs Away! Comedy at the Comet" (16 shows) vs 2291 (6 shows)
        member_club_ids=frozenset({2290, 2291}),
        rationale="Bombs Away Comedy duplicate; keep higher-show 2290, null 2291.",
    ),
    GroupResolution(
        place_id="ChIJ4furWdMH44kRyGkqh2wqtvM",
        keep_club_id=None,  # distinct venues, both mis-geocoded to a North Andover address
        member_club_ids=frozenset({636, 637}),
        rationale=(
            "Wicked Funny Danvers (636) and Salisbury (637) are distinct venues both "
            "wrongly geocoded to 946 Osgood St, North Andover; null both."
        ),
    ),
    GroupResolution(
        place_id="ChIJ7YQxfL2p2YgR4E2OSYPIGXo",
        keep_club_id=3045,  # both 0-show; keep cleaner-named 3045, null "...Interested" 3044
        member_club_ids=frozenset({3044, 3045}),
        rationale="Hollywood Improv duplicate import; keep 3045, null junk-suffix 3044.",
    ),
    GroupResolution(
        place_id="ChIJFdEl9GoiiYgRz4jWRUh-o9c",
        keep_club_id=633,  # "Stardome Comedy Club" (243 shows, full address) vs 3003 (0 shows)
        member_club_ids=frozenset({633, 3003}),
        rationale="Stardome duplicate; keep canonical 633, null bare dup 3003.",
    ),
]


_NULL_GEOCODE_SQL = """
    UPDATE clubs
    SET google_place_id = NULL,
        address = '',
        latitude = NULL,
        longitude = NULL
    WHERE id = %s
      AND google_place_id = %s
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enforce google_place_id uniqueness across clubs (dry-run by default)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the repair. Without this flag the script previews and rolls back.",
    )
    args = parser.parse_args()
    dry_run = not args.apply

    declared_by_place = {g.place_id: g for g in GROUPS}
    if len(declared_by_place) != len(GROUPS):
        print("Duplicate place_id in GROUPS declaration; aborting.")
        return 2

    problems: list[str] = []
    with get_transaction() as conn:
        with conn.cursor() as cur:
            # Audit (criterion 1): every place_id held by >1 club, live.
            cur.execute(
                """
                SELECT google_place_id, array_agg(id ORDER BY id) AS club_ids
                FROM clubs
                WHERE google_place_id IS NOT NULL
                GROUP BY google_place_id
                HAVING COUNT(*) > 1
                ORDER BY google_place_id
                """
            )
            live_collisions = {row[0]: list(row[1]) for row in cur.fetchall()}

            print("AUDIT: google_place_id values shared by >1 club")
            if not live_collisions:
                print("  (none)")
            for place_id, club_ids in live_collisions.items():
                declared = declared_by_place.get(place_id)
                tag = "declared" if declared else "UNDECLARED"
                print(f"  {place_id}  clubs={club_ids}  [{tag}]")
                if declared is None:
                    problems.append(
                        f"undeclared collision place_id={place_id} clubs={club_ids}; "
                        "audit the GROUPS table before repairing"
                    )
                    continue
                extra = set(club_ids) - declared.member_club_ids
                if extra:
                    problems.append(
                        f"place_id={place_id} has unexpected member club(s) {sorted(extra)} "
                        f"not in declared members {sorted(declared.member_club_ids)}"
                    )

            if problems:
                print("\nRefusing to repair:")
                for problem in problems:
                    print(f"  - {problem}")
                conn.rollback()
                return 2

            # Plan: per group, the members to null are the live holders minus the keeper.
            planned: list[tuple[str, int]] = []  # (place_id, club_id)
            print("\nPLAN")
            for group in GROUPS:
                holders = set(live_collisions.get(group.place_id, []))
                if not holders:
                    print(f"  {group.place_id}: already resolved (no active collision)")
                    continue
                to_null = sorted(holders - ({group.keep_club_id} if group.keep_club_id else set()))
                keep = group.keep_club_id if group.keep_club_id is not None else "NONE"
                print(f"  {group.place_id}: keep={keep} null={to_null}")
                print(f"     {group.rationale}")
                for club_id in to_null:
                    planned.append((group.place_id, club_id))

            print(f"\nrows_to_null={len(planned)}")
            if dry_run:
                print("DRY RUN: no changes written (pass --apply to write)")
                conn.rollback()
                return 0

            nulled = 0
            for place_id, club_id in planned:
                cur.execute(_NULL_GEOCODE_SQL, (club_id, place_id))
                if cur.rowcount != 1:
                    print(
                        f"Expected to null 1 row for club_id={club_id} place_id={place_id}; "
                        f"affected {cur.rowcount}"
                    )
                    conn.rollback()
                    return 3
                nulled += 1

            print(f"\nNulled misattributed geocode identity on {nulled} club row(s).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
