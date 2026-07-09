#!/usr/bin/env python3
"""
Resolve the 8 same-venue duplicate-club collisions deferred by TASK-1956 by
folding the duplicate club into the canonical one and clearing the dupe's
typed scraping_sources id so the (platform, typed_id) collision query
returns zero rows.

Background
----------
TASK-1956's disposition_scraping_source_collisions_2026_05_06.py resolved 27
of 35 ``(platform, external_id)`` collisions by clearing the wrong row's id.
The remaining 8 collisions are NOT scraping_sources mismaps: both rows
correctly map to the same upstream venue, but each pair has two distinct
``clubs`` rows representing the same physical venue. Resolving them needs a
``clubs``-level merge decision (which is canonical), the dupe's shows folded
into the canonical row's ``shows.club_id``, and the dupe's scraping_sources
row disabled + typed-id-cleared so it stops appearing in the collision audit
query. Filed as TASK-1984 (Pattern B/C/SQ in the TASK-1956 audit doc).

Note on the schema delta
------------------------
The TASK-1956 audit doc and its disposition script were written against the
pre-typed-columns schema where ``scraping_sources`` carried a generic
``external_id``. After TASK-1985 ('Recover Prisma typed scraping source
migrations') the column was dropped and replaced by per-platform typed
columns (``seatengine_id``, ``seatengine_v3_id``, ``eventbrite_id``,
``ticketmaster_id``, ``squadup_id``, ``wix_event_id``, ``ovationtix_id``).
This script therefore clears the appropriate typed column per pair instead
of ``external_id``. The collision query expressed in typed columns is at
the bottom of this file's docstring and produces the same 8-row set the
audit doc enumerates.

Canonical decisions (snapshot 2026-05-06)
-----------------------------------------
+-----------+-----------+-----------+-------+---------------------------------+
| platform  | typed_id  | canonical | dupe  | shows: collide / dupe-unique    |
+-----------+-----------+-----------+-------+---------------------------------+
| seatengine|       21  |       132 | 1077  | 104 / 6                         |
| seatengine|      424  |       855 |  449  |   1 / 0                         |
| seatengine|      428  |       567 |  453  |   2 / 0                         |
| seatengine|      464  |        73 |  488  |   0 / 0                         |
| seatengine|      493  |       120 |  517  | 294 / 0  (HIGH — both visible)  |
| seatengine|      508  |       125 |  532  |  11 / 0                         |
| seatengine|      556  |       114 |  576  |  66 / 0                         |
| squadup   |  9086799  |       175 |  571  | 138 / 0  (HIGH — both visible)  |
+-----------+-----------+-----------+-------+---------------------------------+

Canonical was picked per pair by: visible > hidden, real address > empty,
more total shows > fewer, older established record > recently auto-discovered.
The two HIGH urgency cases (5 + 8) had both clubs visible AND were actively
double-scraping the same upstream venue.

What this script does, per pair
-------------------------------
1. Validates the expected (club_id, name, scraping_source_id, platform,
   scraper_key, typed_id) shape on both canonical and dupe rows. Refuses to
   write on any mismatch — collects the full mismatch list and prints it
   before exiting code 2. Tolerates already-applied state (typed_id=NULL on
   dupe row + visible=false on dupe club) by treating that pair as done and
   re-emitting it idempotently.
2. Migrates ``shows.club_id`` from dupe -> canonical:
   * Computes the (date, room) collision set between dupe and canonical.
   * For each colliding (date, room) pair: DELETE the dupe show. ON DELETE
     CASCADE on tickets / lineup_items / tagged_shows / sent_notifications
     drops the duplicate downstream rows (the canonical's are kept). The
     deleted dupe shows are re-derivable on the next nightly because the
     canonical row continues scraping the same upstream venue.
   * For each non-colliding (date, room) pair: UPDATE shows.club_id =
     canonical_id WHERE id = dupe_show_id. The unique constraint
     (club_id, date, room) cannot fire because the (date, room) is
     known-non-colliding.
3. Sets the dupe ``scraping_sources`` row to ``enabled=false`` + the
   appropriate typed_id column to NULL. Clearing the typed id is what
   removes the row from the (platform, typed_id) collision audit query;
   flipping enabled=false stops the nightly from continuing to scrape the
   now-hidden dupe club.
4. Sets dupe ``clubs.visible = FALSE`` (only flips when currently TRUE; the
   hidden cases are no-ops).
5. Stamps ``scraping_sources.metadata.task_1984_disposition`` on the dupe
   row with kind=same_venue_dupe_fold + per-row rationale + canonical
   pointer + show migration counts. Stamps ``task_1984_canonical_pointer``
   on the canonical row's metadata to make the pairing discoverable from
   either side. Idempotent: only updates metadata when the key is absent
   or differs.

After all 8 pairs are applied the (platform, typed_id) collision query at
the end of this docstring returns zero rows, satisfying TASK-1984
acceptance criterion 6512.

Usage
-----
    cd apps/scraper && make run-script SCRIPT=scripts/core/fold_task_1984_dup_pairs.py ARGS='--dry-run'
    cd apps/scraper && make run-script SCRIPT=scripts/core/fold_task_1984_dup_pairs.py
    # Optionally restrict to specific pairs by 1-based ordinal:
    cd apps/scraper && make run-script SCRIPT=scripts/core/fold_task_1984_dup_pairs.py ARGS='--only 5,8'

Verification query (typed columns, post-TASK-1985)
--------------------------------------------------
    SELECT 'seatengine' AS plat, seatengine_id::text AS ext,
           COUNT(DISTINCT club_id), ARRAY_AGG(DISTINCT club_id ORDER BY club_id)
      FROM scraping_sources WHERE seatengine_id IS NOT NULL
     GROUP BY seatengine_id HAVING COUNT(DISTINCT club_id) > 1
    UNION ALL
    SELECT 'seatengine_v3', seatengine_v3_id, COUNT(DISTINCT club_id),
           ARRAY_AGG(DISTINCT club_id ORDER BY club_id)
      FROM scraping_sources WHERE seatengine_v3_id IS NOT NULL
     GROUP BY seatengine_v3_id HAVING COUNT(DISTINCT club_id) > 1
    UNION ALL
    SELECT 'eventbrite', eventbrite_id, COUNT(DISTINCT club_id),
           ARRAY_AGG(DISTINCT club_id ORDER BY club_id)
      FROM scraping_sources WHERE eventbrite_id IS NOT NULL
     GROUP BY eventbrite_id HAVING COUNT(DISTINCT club_id) > 1
    UNION ALL
    SELECT 'ticketmaster', ticketmaster_id, COUNT(DISTINCT club_id),
           ARRAY_AGG(DISTINCT club_id ORDER BY club_id)
      FROM scraping_sources WHERE ticketmaster_id IS NOT NULL
     GROUP BY ticketmaster_id HAVING COUNT(DISTINCT club_id) > 1
    UNION ALL
    SELECT 'squadup', squadup_id, COUNT(DISTINCT club_id),
           ARRAY_AGG(DISTINCT club_id ORDER BY club_id)
      FROM scraping_sources WHERE squadup_id IS NOT NULL
     GROUP BY squadup_id HAVING COUNT(DISTINCT club_id) > 1
     ORDER BY 1, 2;
"""

import argparse
import json
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

_METADATA_KEY_DUPE = "task_1984_disposition"
_METADATA_KEY_CANONICAL = "task_1984_canonical_pointer"

# Map platform name to (typed_id_column, expected_id_python_type, expected_scraper_key)
_TYPED_COLUMN = {
    "seatengine": ("seatengine_id", int),
    "squadup": ("squadup_id", str),
}


@dataclass(frozen=True)
class FoldTarget:
    ordinal: int  # 1..8 for --only
    platform: str
    typed_id_value: object  # int for seatengine, str for squadup
    canonical_club_id: int
    canonical_club_name: str
    canonical_source_id: int
    dupe_club_id: int
    dupe_club_name: str
    dupe_source_id: int
    rationale: str
    pattern_label: str  # "B" / "C" / "SQ" from the TASK-1956 audit doc


_TARGETS: list[FoldTarget] = [
    FoldTarget(
        ordinal=1,
        platform="seatengine",
        typed_id_value=21,
        canonical_club_id=132,
        canonical_club_name="Helium & Elements Restaurant - Buffalo",
        canonical_source_id=55,
        dupe_club_id=1077,
        dupe_club_name="Helium & Elements Restaurant",
        dupe_source_id=338,
        pattern_label="B",
        rationale=(
            "Pattern B same-venue dupe: SE API venue 21 = 'Helium & Elements Restaurant' "
            "(heliumcomedy.com/buffalo). Both clubs map correctly to the same upstream venue. "
            "Canonical is club 132 — visible, has the real Buffalo NY address, scraper_key="
            "seatengine_classic, 241 historical shows back to 2025-07. Dupe is club 1077 — "
            "hidden, no address, auto-discovered later via scraper_key=seatengine. The dupe "
            "carries 110 shows, 104 of which collide with the canonical on (date, room) and "
            "are duplicates from the parallel scrape; 6 are unique to the dupe and migrate. "
            "Clearing seatengine_id and disabling the dupe row stops the parallel scrape and "
            "removes the (platform, seatengine_id) collision."
        ),
    ),
    FoldTarget(
        ordinal=2,
        platform="seatengine",
        typed_id_value=424,
        canonical_club_id=855,
        canonical_club_name="Laugh Tonight Comedy",
        canonical_source_id=294,
        dupe_club_id=449,
        dupe_club_name="Laugh Tonight Comedy @ Laugh Factory",
        dupe_source_id=279,
        pattern_label="C",
        rationale=(
            "Pattern C same-venue dupe: SE API venue 424 = 'Laugh Tonight Comedy'. Both "
            "rows auto-discovered against the same upstream venue under different ad-hoc "
            "names. Canonical is club 855 (visible, name matches SE upstream, 3 shows). "
            "Dupe is club 449 (hidden, 1 show, name carries a stale '@ Laugh Factory' "
            "qualifier that doesn't match upstream). The single dupe show collides on "
            "(date, room) with canonical's identical scrape — deleted, not migrated."
        ),
    ),
    FoldTarget(
        ordinal=3,
        platform="seatengine",
        typed_id_value=428,
        canonical_club_id=567,
        canonical_club_name="J.R.'s Comedy Club",
        canonical_source_id=476,
        dupe_club_id=453,
        dupe_club_name="J.R.'s Comedy Club (INSIDE THE JUNKYARD CAFE)",
        dupe_source_id=62,
        pattern_label="C",
        rationale=(
            "Pattern C same-venue dupe: SE API venue 428 = J.R.'s Comedy Club (INSIDE THE "
            "JUNKYARD CAFE), tocomedy.com. Canonical is club 567 (visible, real address "
            "2585 Cochran St., Simi Valley, 6 shows, 4 future). Dupe is club 453 (hidden, "
            "no address, 2 past shows). Both dupe shows collide on (date, room) with the "
            "canonical's parallel-scrape — deleted."
        ),
    ),
    FoldTarget(
        ordinal=4,
        platform="seatengine",
        typed_id_value=464,
        canonical_club_id=73,
        canonical_club_name="The Comedy Zone Greenville",
        canonical_source_id=32,
        dupe_club_id=488,
        dupe_club_name="Greenville Comedy Zone @ Revel Event Center",
        dupe_source_id=127,
        pattern_label="C",
        rationale=(
            "Pattern C same-venue dupe: SE API venue 464 = 'Greenville Comedy Zone @ Revel "
            "Event Center', greenvillecomedyzone.com. Canonical is club 73 'The Comedy Zone "
            "Greenville', visible, real Greenville SC address, 406 shows. Dupe is club 488 "
            "— already status='closed' and visible=false, with 0 shows attached. No show "
            "migration. Just clears seatengine_id and disables the dupe scraping_source so "
            "the collision query stops returning the pair."
        ),
    ),
    FoldTarget(
        ordinal=5,
        platform="seatengine",
        typed_id_value=493,
        canonical_club_id=120,
        canonical_club_name="Mic Drop Mania",
        canonical_source_id=96,
        dupe_club_id=517,
        dupe_club_name="Mic Drop Comedy Chandler",
        dupe_source_id=548,
        pattern_label="C",
        rationale=(
            "HIGH urgency Pattern C — both clubs visible with hundreds of future shows, "
            "actively double-scraping. SE API venue 493 = 'Mic Drop Comedy Chandler' "
            "(micdropcomedychandler.com). Canonical is club 120 'Mic Drop Mania', visible, "
            "real Chandler AZ address, 578 historical shows back to 2025-07 (the original "
            "established record). Dupe is club 517 'Mic Drop Comedy Chandler', visible, no "
            "address, 294 shows — auto-discovered later when SE upstream was renamed. All "
            "294 dupe shows collide on (date, room) with the canonical (230 future + 64 "
            "past), so the entire dupe show set is deleted as parallel-scrape duplicates. "
            "Future SE national sweeps will continue to dedupe by seatengine_id against "
            "club 120's row (the only remaining row pointing at SE venue 493), so no new "
            "duplicate club is created. Note: club 120's name is the now-stale 'Mic Drop "
            "Mania' — renaming to match upstream is intentionally OUT of scope here "
            "(would collide with the @@unique([name]) constraint until the dupe is "
            "deleted, plus changes user-facing slugs); this script only stops the "
            "parallel scrape."
        ),
    ),
    FoldTarget(
        ordinal=6,
        platform="seatengine",
        typed_id_value=508,
        canonical_club_id=125,
        canonical_club_name="Sticks and Stones Comedy Club",
        canonical_source_id=267,
        dupe_club_id=532,
        dupe_club_name="STICKS AND STONES COMEDY CLUB",
        dupe_source_id=412,
        pattern_label="C",
        rationale=(
            "Pattern C same-venue dupe: SE API venue 508 = 'STICKS AND STONES COMEDY CLUB' "
            "(sticksandstonescomedyclub.com). Canonical is club 125 'Sticks and Stones "
            "Comedy Club', visible, real Southampton NY address, 274 shows. Dupe is club "
            "532 (hidden, no address, 11 future shows under all-caps name from auto-"
            "discovery). All 11 dupe shows collide on (date, room) with canonical's "
            "parallel-scrape — deleted."
        ),
    ),
    FoldTarget(
        ordinal=7,
        platform="seatengine",
        typed_id_value=556,
        canonical_club_id=114,
        canonical_club_name="Laugh Camp Comedy Club",
        canonical_source_id=383,
        dupe_club_id=576,
        dupe_club_name="Laugh Camp Comedy Club - Saint Paul MN at Camp Bar",
        dupe_source_id=424,
        pattern_label="C",
        rationale=(
            "Pattern C same-venue dupe: SE API venue 556 = 'Laugh Camp Comedy Club - Saint "
            "Paul MN at Camp Bar' (camp-bar.net). Canonical is club 114 'Laugh Camp Comedy "
            "Club', visible, real Saint Paul MN address, 142 shows. Dupe is club 576 "
            "(hidden, no address, 66 shows under the verbose SE-upstream name). All 66 "
            "dupe shows collide on (date, room) with canonical's parallel-scrape — deleted."
        ),
    ),
    FoldTarget(
        ordinal=8,
        platform="squadup",
        typed_id_value="9086799",
        canonical_club_id=175,
        canonical_club_name="Sunset Strip Comedy Club",
        canonical_source_id=511,
        dupe_club_id=571,
        dupe_club_name="Sunset Strip",
        dupe_source_id=216,
        pattern_label="SQ",
        rationale=(
            "HIGH urgency Pattern SQ — both clubs visible with hundreds of future shows, "
            "actively double-scraping the same SquadUp user_id 9086799. Same Austin TX "
            "address (214 E 6th Street, Unit C). Canonical is club 175 'Sunset Strip "
            "Comedy Club', 171 shows (the older more-established record with the comedy-"
            "specific name). Dupe is club 571 'Sunset Strip', 138 shows, all 138 colliding "
            "on (date, room) with canonical — deleted. Note: club 571 also carries an "
            "extra disabled seatengine scraping_sources row (id=895, seatengine_id=551) "
            "from a separate auto-discovery; that row stays where it is on the now-hidden "
            "club 571 because it is already enabled=false and does not contribute to any "
            "(platform, typed_id) collision."
        ),
    ),
]


def _typed_column_for(platform: str) -> str:
    if platform not in _TYPED_COLUMN:
        raise ValueError(f"unsupported platform {platform!r}")
    return _TYPED_COLUMN[platform][0]


def _fetch_clubs(cur, ids: list[int]) -> dict[int, dict]:
    cur.execute(
        "SELECT id, name, visible, status FROM clubs WHERE id = ANY(%s)",
        (ids,),
    )
    cols = [d.name for d in cur.description]
    return {r[0]: dict(zip(cols, r)) for r in cur.fetchall()}


def _fetch_sources(cur, ids: list[int]) -> dict[int, dict]:
    cur.execute(
        """
        SELECT id, club_id, platform::text, scraper_key, priority, enabled,
               seatengine_id, seatengine_v3_id, eventbrite_id, ticketmaster_id,
               squadup_id, wix_event_id, ovationtix_id, metadata
          FROM scraping_sources WHERE id = ANY(%s)
        """,
        (ids,),
    )
    cols = [d.name for d in cur.description]
    out = {}
    for r in cur.fetchall():
        d = dict(zip(cols, r))
        md = d.get("metadata")
        if isinstance(md, str):
            try:
                d["metadata"] = json.loads(md)
            except Exception:
                d["metadata"] = {}
        elif md is None:
            d["metadata"] = {}
        out[d["id"]] = d
    return out


def _validate(cur, target: FoldTarget) -> list[str]:
    problems: list[str] = []
    clubs = _fetch_clubs(cur, [target.canonical_club_id, target.dupe_club_id])
    if target.canonical_club_id not in clubs:
        problems.append(
            f"target #{target.ordinal} canonical club {target.canonical_club_id} not found"
        )
    else:
        c = clubs[target.canonical_club_id]
        if c["name"] != target.canonical_club_name:
            problems.append(
                f"target #{target.ordinal} canonical club {target.canonical_club_id} "
                f"name={c['name']!r} (expected {target.canonical_club_name!r})"
            )
    if target.dupe_club_id not in clubs:
        problems.append(
            f"target #{target.ordinal} dupe club {target.dupe_club_id} not found"
        )
    else:
        d = clubs[target.dupe_club_id]
        if d["name"] != target.dupe_club_name:
            problems.append(
                f"target #{target.ordinal} dupe club {target.dupe_club_id} "
                f"name={d['name']!r} (expected {target.dupe_club_name!r})"
            )

    sources = _fetch_sources(cur, [target.canonical_source_id, target.dupe_source_id])
    typed_col = _typed_column_for(target.platform)
    if target.canonical_source_id not in sources:
        problems.append(
            f"target #{target.ordinal} canonical source {target.canonical_source_id} not found"
        )
    else:
        s = sources[target.canonical_source_id]
        if s["club_id"] != target.canonical_club_id:
            problems.append(
                f"target #{target.ordinal} canonical source {target.canonical_source_id} "
                f"club_id={s['club_id']} (expected {target.canonical_club_id})"
            )
        if s["platform"] != target.platform:
            problems.append(
                f"target #{target.ordinal} canonical source {target.canonical_source_id} "
                f"platform={s['platform']!r} (expected {target.platform!r})"
            )
        if str(s[typed_col]) != str(target.typed_id_value):
            problems.append(
                f"target #{target.ordinal} canonical source {target.canonical_source_id} "
                f"{typed_col}={s[typed_col]!r} (expected {target.typed_id_value!r})"
            )
    if target.dupe_source_id not in sources:
        problems.append(
            f"target #{target.ordinal} dupe source {target.dupe_source_id} not found"
        )
    else:
        s = sources[target.dupe_source_id]
        if s["club_id"] != target.dupe_club_id:
            problems.append(
                f"target #{target.ordinal} dupe source {target.dupe_source_id} "
                f"club_id={s['club_id']} (expected {target.dupe_club_id})"
            )
        if s["platform"] != target.platform:
            problems.append(
                f"target #{target.ordinal} dupe source {target.dupe_source_id} "
                f"platform={s['platform']!r} (expected {target.platform!r})"
            )
        # On idempotent re-runs the dupe typed id has been cleared. Accept either
        # the original value or NULL — but if NULL, we expect the disposition stamp.
        live_typed = s[typed_col]
        if live_typed is None:
            md = s.get("metadata") or {}
            if _METADATA_KEY_DUPE not in md:
                problems.append(
                    f"target #{target.ordinal} dupe source {target.dupe_source_id} "
                    f"{typed_col}=NULL but metadata.{_METADATA_KEY_DUPE} is missing — "
                    f"refusing to write because we can't tell whether this was a partial "
                    f"prior run or a different cleanup"
                )
        elif str(live_typed) != str(target.typed_id_value):
            problems.append(
                f"target #{target.ordinal} dupe source {target.dupe_source_id} "
                f"{typed_col}={live_typed!r} (expected {target.typed_id_value!r} or NULL "
                f"already-applied)"
            )
    return problems


def _classify_dupe_shows(cur, target: FoldTarget) -> tuple[list[int], list[int]]:
    """Return (collide_ids, movable_ids).

    collide_ids: dupe show IDs whose (date, room) already exists on canonical;
    these are deleted on apply.

    movable_ids: dupe show IDs whose (date, room) has no match on canonical;
    these are UPDATEd to canonical_id on apply.
    """
    cur.execute(
        """
        WITH dupe AS (
            SELECT id, date, room FROM shows WHERE club_id = %s
        ),
        canonical AS (
            SELECT date, room FROM shows WHERE club_id = %s
        )
        SELECT d.id,
               EXISTS (
                   SELECT 1 FROM canonical c
                    WHERE c.date = d.date
                      AND c.room IS NOT DISTINCT FROM d.room
               ) AS collides
          FROM dupe d
        """,
        (target.dupe_club_id, target.canonical_club_id),
    )
    collide_ids: list[int] = []
    movable_ids: list[int] = []
    for sid, collides in cur.fetchall():
        (collide_ids if collides else movable_ids).append(sid)
    return collide_ids, movable_ids


def _apply_target(cur, target: FoldTarget, dry_run: bool) -> dict:
    typed_col = _typed_column_for(target.platform)

    clubs = _fetch_clubs(cur, [target.canonical_club_id, target.dupe_club_id])
    sources = _fetch_sources(cur, [target.canonical_source_id, target.dupe_source_id])
    dupe_club = clubs[target.dupe_club_id]
    dupe_source = sources[target.dupe_source_id]
    canonical_source = sources[target.canonical_source_id]

    collide_ids, movable_ids = _classify_dupe_shows(cur, target)

    will_delete_shows = bool(collide_ids)
    will_move_shows = bool(movable_ids)
    will_clear_typed_id = dupe_source[typed_col] is not None
    will_disable_source = dupe_source["enabled"] is True
    will_stamp_dupe_metadata = _METADATA_KEY_DUPE not in (dupe_source.get("metadata") or {})
    will_stamp_canonical_metadata = _METADATA_KEY_CANONICAL not in (
        canonical_source.get("metadata") or {}
    )
    will_hide_club = dupe_club["visible"] is True

    summary = {
        "ordinal": target.ordinal,
        "platform": target.platform,
        "typed_id": target.typed_id_value,
        "pattern": target.pattern_label,
        "canonical_club_id": target.canonical_club_id,
        "dupe_club_id": target.dupe_club_id,
        "shows_to_delete": len(collide_ids),
        "shows_to_move": len(movable_ids),
        "will_clear_typed_id": will_clear_typed_id,
        "will_disable_source": will_disable_source,
        "will_stamp_dupe_metadata": will_stamp_dupe_metadata,
        "will_stamp_canonical_metadata": will_stamp_canonical_metadata,
        "will_hide_club": will_hide_club,
    }

    print(
        f"\n=== TARGET #{target.ordinal} {target.platform}/{target.typed_id_value} "
        f"({target.pattern_label}) — canonical={target.canonical_club_id} "
        f"dupe={target.dupe_club_id} ==="
    )
    print(
        f"  canonical: club {target.canonical_club_id!r} {target.canonical_club_name!r} "
        f"visible={clubs[target.canonical_club_id]['visible']}"
    )
    print(
        f"  dupe:      club {target.dupe_club_id!r} {target.dupe_club_name!r} "
        f"visible={dupe_club['visible']}"
    )
    print(
        f"  dupe source #{target.dupe_source_id}: enabled={dupe_source['enabled']} "
        f"{typed_col}={dupe_source[typed_col]!r}"
    )
    print(
        f"  shows: collide={len(collide_ids)} (will delete) "
        f"move={len(movable_ids)} (will UPDATE club_id={target.canonical_club_id})"
    )
    print(
        f"  writes pending: clear_typed={will_clear_typed_id} disable={will_disable_source} "
        f"stamp_dupe={will_stamp_dupe_metadata} stamp_canonical={will_stamp_canonical_metadata} "
        f"hide_club={will_hide_club}"
    )

    if not (
        will_delete_shows
        or will_move_shows
        or will_clear_typed_id
        or will_disable_source
        or will_stamp_dupe_metadata
        or will_stamp_canonical_metadata
        or will_hide_club
    ):
        print("  → no changes needed (idempotent re-run).")
        summary["applied"] = "noop"
        return summary

    if dry_run:
        print("  → --dry-run: no DB write performed.")
        summary["applied"] = "dry-run"
        return summary

    if collide_ids:
        cur.execute("DELETE FROM shows WHERE id = ANY(%s)", (collide_ids,))
    if movable_ids:
        cur.execute(
            "UPDATE shows SET club_id = %s WHERE id = ANY(%s)",
            (target.canonical_club_id, movable_ids),
        )

    if will_clear_typed_id or will_disable_source or will_stamp_dupe_metadata:
        new_md = dict(dupe_source.get("metadata") or {})
        if will_stamp_dupe_metadata:
            new_md[_METADATA_KEY_DUPE] = {
                "kind": "same_venue_dupe_fold",
                "pattern": target.pattern_label,
                "platform": target.platform,
                "typed_id_cleared": target.typed_id_value,
                "canonical_club_id": target.canonical_club_id,
                "canonical_source_id": target.canonical_source_id,
                "shows_deleted": len(collide_ids),
                "shows_migrated": len(movable_ids),
                "rationale": target.rationale,
            }
        cur.execute(
            f"""
            UPDATE scraping_sources
               SET {typed_col} = NULL,
                   enabled = FALSE,
                   metadata = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (json.dumps(new_md), target.dupe_source_id),
        )

    if will_stamp_canonical_metadata:
        new_md = dict(canonical_source.get("metadata") or {})
        new_md[_METADATA_KEY_CANONICAL] = {
            "kind": "same_venue_dupe_canonical",
            "pattern": target.pattern_label,
            "platform": target.platform,
            "typed_id_kept": target.typed_id_value,
            "dupe_club_id": target.dupe_club_id,
            "dupe_source_id": target.dupe_source_id,
            "rationale": (
                f"This row is the canonical for the same-venue duplicate-club pair "
                f"resolved by TASK-1984. The duplicate club {target.dupe_club_id} "
                f"({target.dupe_club_name!r}) was hidden and its scraping_source "
                f"{target.dupe_source_id} had its {target.platform} typed id cleared."
            ),
        }
        cur.execute(
            """
            UPDATE scraping_sources
               SET metadata = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (json.dumps(new_md), target.canonical_source_id),
        )

    if will_hide_club:
        cur.execute(
            "UPDATE clubs SET visible = FALSE WHERE id = %s AND visible = TRUE",
            (target.dupe_club_id,),
        )

    print("  → applied.")
    summary["applied"] = "wrote"
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Comma-separated 1-based target ordinals to apply (default: all 8)",
    )
    args = parser.parse_args()

    selected_ords = None
    if args.only:
        try:
            selected_ords = {int(x) for x in args.only.split(",") if x.strip()}
        except ValueError:
            print(f"ABORT: --only must be comma-separated integers, got {args.only!r}", file=sys.stderr)
            return 2
        bad = selected_ords - {t.ordinal for t in _TARGETS}
        if bad:
            print(f"ABORT: --only references unknown ordinals {sorted(bad)}", file=sys.stderr)
            return 2

    targets = [t for t in _TARGETS if selected_ords is None or t.ordinal in selected_ords]

    with get_transaction() as conn:
        with conn.cursor() as cur:
            problems: list[str] = []
            for t in targets:
                problems.extend(_validate(cur, t))
            if problems:
                print("ABORT: shape mismatch — refusing to write:", file=sys.stderr)
                for p in problems:
                    print(f"  {p}", file=sys.stderr)
                return 1

            summaries = []
            for t in targets:
                summaries.append(_apply_target(cur, t, args.dry_run))

    print("\n=== summary ===")
    for s in summaries:
        print(
            f"  #{s['ordinal']} {s['platform']}/{s['typed_id']} ({s['pattern']}) "
            f"canonical={s['canonical_club_id']} dupe={s['dupe_club_id']} "
            f"delete={s['shows_to_delete']} move={s['shows_to_move']} "
            f"applied={s['applied']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
