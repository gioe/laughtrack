#!/usr/bin/env python3
"""
Collapse duplicate show rows that accreted because show identity was keyed on
the unstable show_page_url and on a NULL-distinct (club_id, date, room) unique
index.

Background
----------
TASK-3489. Two defects let the same logical showtime spawn many physical show
rows:

1. NULL-room accretion. shows.room is nullable and the unique index
   shows_club_id_date_room_key is a plain (club_id, date, room) btree, so
   Postgres treats every NULL room as DISTINCT — two NULL-room rows at the same
   (club_id, date) never conflict. Legacy rows were written with room=NULL, and
   ShowHandler._canonical_cross_batch_room used to rewrite an incoming room=""
   onto an existing NULL room, so the upsert's ON CONFLICT (club_id, date, room)
   missed and INSERTED a fresh NULL row on every scrape. Bricktown Comedy
   (club 90, Steve Hofstetter /shows/319290) reached 75 NULL-room rows for one
   showtime. The handler fix (this task) now always writes room="" so future
   scrapes converge; this script collapses the legacy rows.

2. Domain rebrand / start-time drift. A SeatEngine "/shows/<id>" performance is
   stable, but the host in show_page_url drifts (e.g. Fort Lauderdale Improv,
   club 53: daniaimprov.com -> www.improvftl.com) and the parsed UTC start time
   has drifted across runs (Rick Glassman /shows/313789 stored at both
   2025-08-17T01:30Z and 2025-08-17T05:30Z). Same club + same /shows/<id> = one
   performance regardless of host or the drifted date, so those rows collapse to
   one too.

What this script does
---------------------
1. Builds a stable-identity duplicate map (temp table task_3489_show_map):
   - SeatEngine-style rows (show_page_url contains /shows/<digits>) group by
     (club_id, <id>) — host-agnostic, date-agnostic. Catches both defects for
     SeatEngine venues.
   - All other rows group by (club_id, date, COALESCE(room,''), COALESCE(name,''))
     — exact same-slot duplicates (the NULL-room accretion for non-SeatEngine
     venues). Name is included so two genuinely different shows at one (club,
     date) are never merged.
   The canonical survivor per group is the most recently scraped row
   (last_scraped_by NOT NULL first, then newest last_scraped_date, then highest
   id) so the survivor keeps the current parser's date and attribution.
2. Repoints child rows (lineup_items, tagged_shows, tickets, sent_notifications,
   ticket_purchase_click_events) from the duplicates onto the survivor, honoring
   each child's unique key (ON CONFLICT DO NOTHING / delete-then-repoint), then
   deletes the duplicate show rows.
3. Normalizes surviving room=NULL -> '' ONLY where it is safe: when no other
   row shares that (club_id, date). Where two NULL-room rows at one (club_id,
   date) carry DIFFERENT names (genuine distinct shows the schema cannot
   represent without a room), they are LEFT as NULL and reported for manual
   room assignment — collapsing them would lose a real show.

Idempotent: re-running finds no duplicate groups and no unsafe NULLs to change.
Safe to re-run. Defaults to a dry run (rolls back); pass --apply to commit.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/collapse_duplicate_shows_stable_identity.py            # dry run
    make run-script SCRIPT=scripts/core/collapse_duplicate_shows_stable_identity.py ARGS='--apply'
    make run-script SCRIPT=scripts/core/collapse_duplicate_shows_stable_identity.py ARGS='--club 53'
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction

TASK_ID = 3489
RECOVERY_LOG_PATH = _root / "docs" / "audits" / "task-3489-collapse-duplicate-shows.json"

# Stable-identity grouping. The sid branch is host- and date-agnostic (same
# club + same /shows/<id> = one performance); the fallback branch is the exact
# (club, date, room, name) same-slot key with NULL room folded to ''.
#
# The sid branch is scoped to last_scraped_by='seatengine_classic' OR NULL and
# uses the delimiter-anchored /shows/([0-9]+)(?:[/?#]|$) regex, mirroring the
# handler reconciler (GET_SEATENGINE_CLASSIC_SHOWS_BY_CLUB /
# _extract_seatengine_classic_show_id). Without that scope a non-SeatEngine
# venue whose URL merely contains /shows/<digits> (where the id is not a
# per-performance id) would have distinct showtimes grouped by (club, id) and
# wrongly collapsed (TASK-3491). Such rows fall through to the (date, room,
# name) same-slot key instead.
_SEATENGINE_SHOW_ID_RE = "/shows/([0-9]+)(?:[/?#]|$)"
_GROUP_KEY_SQL = f"""
    CASE
        WHEN (last_scraped_by = 'seatengine_classic' OR last_scraped_by IS NULL)
             AND substring(show_page_url from '{_SEATENGINE_SHOW_ID_RE}') IS NOT NULL
            THEN 'sid:' || club_id || ':' || substring(show_page_url from '{_SEATENGINE_SHOW_ID_RE}')
        ELSE 'dt:' || club_id || ':'
             || to_char(date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS') || ':'
             || COALESCE(lower(trim(room)), '') || ':'
             || COALESCE(lower(trim(name)), '')
    END
"""

# Ordering that picks the canonical survivor: a row this scraper is known to
# have produced (last_scraped_by NOT NULL) wins over legacy NULL rows, then the
# freshest scrape, then the highest id.
_CANONICAL_ORDER_SQL = "(last_scraped_by IS NOT NULL) DESC, last_scraped_date DESC NULLS LAST, id DESC"


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _club_filter(club_id: Optional[int], alias: Optional[str] = None) -> tuple[str, tuple]:
    """Return a SQL predicate fragment + params scoping to one club (or all).

    ``alias`` qualifies the column for queries that join ``shows`` under an alias
    (e.g. ``alias='s'`` -> ``s.club_id = %s``). Passing it explicitly avoids
    brittle string rewriting of the returned fragment at the call site.
    """
    if club_id is None:
        return "TRUE", ()
    column = f"{alias}.club_id" if alias else "club_id"
    return f"{column} = %s", (club_id,)


def _create_temp_show_map(cur: RealDictCursor, club_id: Optional[int]) -> None:
    where, params = _club_filter(club_id)
    cur.execute(
        f"""
        CREATE TEMP TABLE task_3489_show_map ON COMMIT DROP AS
        WITH grouped AS (
            SELECT id, last_scraped_by, last_scraped_date,
                   {_GROUP_KEY_SQL} AS gkey
            FROM shows
            WHERE {where}
        ),
        ranked AS (
            SELECT id, gkey,
                   COUNT(*)      OVER (PARTITION BY gkey) AS grp_size,
                   FIRST_VALUE(id) OVER (
                       PARTITION BY gkey ORDER BY {_CANONICAL_ORDER_SQL}
                   ) AS canonical_id
            FROM grouped
        )
        SELECT id AS old_show_id, canonical_id AS new_show_id
        FROM ranked
        WHERE grp_size > 1 AND id <> canonical_id
        """,
        params,
    )
    cur.execute("CREATE INDEX ON task_3489_show_map (old_show_id)")
    cur.execute("CREATE INDEX ON task_3489_show_map (new_show_id)")


def _map_summary(cur: RealDictCursor) -> dict[str, Any]:
    cur.execute(
        """
        SELECT COUNT(*) AS duplicate_rows,
               COUNT(DISTINCT new_show_id) AS groups_collapsed
        FROM task_3489_show_map
        """
    )
    return dict(cur.fetchone())


def _sample_axis_b(cur: RealDictCursor, limit: int = 10) -> list[dict[str, Any]]:
    """Sample SeatEngine groups whose duplicates span more than one date.

    These are the domain-rebrand / start-time-drift collapses (the Fort
    Lauderdale Improv case); surfaced so a reviewer can eyeball them.
    """
    cur.execute(
        """
        SELECT s.club_id,
               substring(s.show_page_url from '/shows/([0-9]+)') AS seatengine_show_id,
               COUNT(*) AS rows_collapsed,
               COUNT(DISTINCT s.date) AS distinct_dates,
               array_agg(DISTINCT s.show_page_url) AS urls
        FROM task_3489_show_map m
        JOIN shows s ON s.id = m.old_show_id
        WHERE substring(s.show_page_url from '/shows/([0-9]+)') IS NOT NULL
        GROUP BY 1, 2
        HAVING COUNT(DISTINCT s.date) > 1
        ORDER BY rows_collapsed DESC
        LIMIT %s
        """,
        (limit,),
    )
    return [dict(r) for r in cur.fetchall()]


def _top_offenders(cur: RealDictCursor, limit: int = 15) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT s.club_id, c.name AS club_name, COUNT(*) AS duplicate_rows
        FROM task_3489_show_map m
        JOIN shows s ON s.id = m.old_show_id
        JOIN clubs c ON c.id = s.club_id
        GROUP BY s.club_id, c.name
        ORDER BY duplicate_rows DESC
        LIMIT %s
        """,
        (limit,),
    )
    return [dict(r) for r in cur.fetchall()]


def _repoint_children_and_delete(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}

    cur.execute(
        """
        INSERT INTO lineup_items (show_id, comedian_id, role)
        SELECT m.new_show_id, li.comedian_id, li.role
        FROM lineup_items li
        JOIN task_3489_show_map m ON m.old_show_id = li.show_id
        ON CONFLICT (show_id, comedian_id) DO NOTHING
        """
    )
    counts["lineup_items_repointed"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tagged_shows (show_id, tag_id)
        SELECT m.new_show_id, ts.tag_id
        FROM tagged_shows ts
        JOIN task_3489_show_map m ON m.old_show_id = ts.show_id
        ON CONFLICT (show_id, tag_id) DO NOTHING
        """
    )
    counts["tagged_shows_repointed"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tickets (purchase_url, price, sold_out, show_id, type)
        SELECT t.purchase_url, t.price, t.sold_out, m.new_show_id, t.type
        FROM tickets t
        JOIN task_3489_show_map m ON m.old_show_id = t.show_id
        ON CONFLICT (show_id, type) DO NOTHING
        """
    )
    counts["tickets_repointed"] = cur.rowcount

    # sent_notifications has a per-channel unique key
    # (user_id, comedian_id, show_id, notification_type). Two deletes make the
    # subsequent repoint UPDATE collision-proof:
    #   1. Drop old-row notifications that collide with one ALREADY on the
    #      survivor.
    cur.execute(
        """
        DELETE FROM sent_notifications sn
        USING task_3489_show_map m, sent_notifications existing
        WHERE sn.show_id = m.old_show_id
          AND existing.user_id = sn.user_id
          AND existing.comedian_id = sn.comedian_id
          AND existing.show_id = m.new_show_id
          AND existing.notification_type = sn.notification_type
        """
    )
    counts["conflicting_sent_notifications_deleted"] = cur.rowcount
    #   2. Dedupe AMONG the multiple old rows mapping to the same survivor: keep
    #      one per (new_show_id, user, comedian, notification_type). Without this
    #      two old rows carrying the same channel both UPDATE to new_show_id and
    #      violate the unique key (TASK-3491).
    cur.execute(
        """
        DELETE FROM sent_notifications sn
        USING (
            SELECT s2.id,
                   ROW_NUMBER() OVER (
                       PARTITION BY m.new_show_id, s2.user_id, s2.comedian_id, s2.notification_type
                       ORDER BY s2.id
                   ) AS rn
            FROM sent_notifications s2
            JOIN task_3489_show_map m ON m.old_show_id = s2.show_id
        ) dups
        WHERE sn.id = dups.id AND dups.rn > 1
        """
    )
    counts["intra_group_sent_notifications_deleted"] = cur.rowcount
    cur.execute(
        """
        UPDATE sent_notifications sn
        SET show_id = m.new_show_id
        FROM task_3489_show_map m
        WHERE sn.show_id = m.old_show_id
        """
    )
    counts["sent_notifications_repointed"] = cur.rowcount

    cur.execute(
        """
        UPDATE ticket_purchase_click_events tpce
        SET show_id = m.new_show_id
        FROM task_3489_show_map m
        WHERE tpce.show_id = m.old_show_id
        """
    )
    counts["click_events_repointed"] = cur.rowcount

    # tickets / tagged_shows / lineup_items left on the duplicate rows cascade
    # away with the show delete (FK onDelete: Cascade); only the conflict-skipped
    # children remain on the old rows and are removed here.
    cur.execute(
        """
        DELETE FROM shows s
        USING task_3489_show_map m
        WHERE s.id = m.old_show_id
        """
    )
    counts["duplicate_shows_deleted"] = cur.rowcount
    return counts


def _normalize_safe_null_rooms(cur: RealDictCursor, club_id: Optional[int]) -> int:
    """Set room='' for NULL-room shows that are the sole row at their (club, date).

    Leaves NULL rows that share a (club_id, date) with another row, because
    forcing both to '' would collide on shows_club_id_date_room_key. Those are
    reported separately as needing manual room assignment.
    """
    where, params = _club_filter(club_id, alias="s")
    cur.execute(
        f"""
        UPDATE shows s
        SET room = ''
        WHERE s.room IS NULL
          AND {where}
          AND NOT EXISTS (
              SELECT 1 FROM shows o
              WHERE o.club_id = s.club_id
                AND o.date = s.date
                AND o.id <> s.id
          )
        """,
        params,
    )
    return cur.rowcount


def _remaining_null_room_conflicts(cur: RealDictCursor, club_id: Optional[int]) -> list[dict[str, Any]]:
    """(club_id, date) slots still holding >1 row after collapse + normalize.

    A genuine multi-show-same-slot case the (club_id, date, room) schema cannot
    represent without distinct rooms — left untouched for human review.
    """
    where, params = _club_filter(club_id)
    cur.execute(
        f"""
        SELECT club_id,
               date,
               COUNT(*) AS rows,
               array_agg(DISTINCT COALESCE(name, '')) AS names,
               bool_or(room IS NULL) AS has_null_room
        FROM shows
        WHERE {where}
        GROUP BY club_id, date
        HAVING COUNT(*) > 1
        ORDER BY rows DESC
        LIMIT 50
        """,
        params,
    )
    return [dict(r) for r in cur.fetchall()]


def run(*, apply: bool, club_id: Optional[int]) -> dict[str, Any]:
    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _create_temp_show_map(cur, club_id)
            before = {
                "map": _map_summary(cur),
                "top_offenders": _top_offenders(cur),
                "axis_b_multi_date_groups_sample": _sample_axis_b(cur),
            }

            counts = _repoint_children_and_delete(cur)
            counts["rooms_normalized_null_to_empty"] = _normalize_safe_null_rooms(cur, club_id)

            after = {
                "remaining_same_slot_conflicts": _remaining_null_room_conflicts(cur, club_id),
            }

            payload = {
                "task": f"TASK-{TASK_ID}",
                "applied": apply,
                "club_scope": club_id,
                "generated_at": datetime.now(timezone.utc),
                "before": before,
                "counts": counts,
                "after": after,
            }

            if not apply:
                conn.rollback()

    # Write the recovery log only AFTER the transaction has committed cleanly on
    # context-manager exit — so an applied=true log is never written for a run
    # whose commit later failed (TASK-3491).
    if apply:
        _write_recovery_log(payload)
    return payload


def _write_recovery_log(payload: dict[str, Any]) -> None:
    RECOVERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECOVERY_LOG_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default)
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collapse duplicate show rows onto a stable identity (TASK-3489)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the changes. Without this flag the script runs as a dry run and rolls back.",
    )
    parser.add_argument(
        "--club",
        type=int,
        default=None,
        help="Limit to a single club_id (useful for verification).",
    )
    args = parser.parse_args()

    payload = run(apply=args.apply, club_id=args.club)
    print(json.dumps(payload, indent=2, sort_keys=True, default=_json_default))
    if not args.apply:
        print("DRY RUN: no rows changed and no recovery log written. Re-run with --apply to commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
