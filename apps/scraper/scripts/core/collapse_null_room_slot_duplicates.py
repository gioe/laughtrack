#!/usr/bin/env python3
"""
Collapse legacy NULL-room shows that share one (club_id, date) slot — duplicate
captures of a single showtime that the (club_id, date, room) unique index could
not dedupe because NULL is distinct.

Background
----------
TASK-3490 (follow-up of TASK-3489). The shows unique index is
(club_id, date, room) and room is nullable, so Postgres treats NULL rooms as
DISTINCT — multiple NULL-room rows at the same (club_id, date) coexist. The
TASK-3489 collapse keyed its non-SeatEngine pass on (club_id, date, room, name),
so rows for the SAME showtime captured under DIFFERENT names never collapsed.

Investigation of the surviving conflicts (the TASK-3489 audit's
remaining_same_slot_conflicts) found 1,127 such groups across ~17 clubs, ALL in
the past, and they are NOT genuinely distinct concurrent shows — they are
scrape-artifact duplicates of one showtime: a generic placeholder name (e.g.
"New York Comedy Club Presents") plus lineup-variant names of the same show
(performers added/removed between scrapes). No genuinely-distinct same-slot case
exists in the data, so NO schema discriminator / unique-key migration is
warranted (decision recorded on the task). Forward convergence is already
guaranteed by the TASK-3489 handler fix (ShowHandler now writes room='' instead
of NULL, so future scrapes upsert onto a single row).

What this script does
---------------------
1. Groups NULL-room shows by (club_id, date). Any group with >1 row is a
   same-slot duplicate set.
2. Picks the canonical survivor: the row with the most lineup_items (the most
   complete real capture, beating generic placeholders), then the most recent
   last_scraped_date, then the highest id.
3. Repoints child rows (lineup_items, tagged_shows, tickets, sent_notifications,
   ticket_purchase_click_events) onto the survivor honoring each child's unique
   key, deletes the duplicate show rows, then normalizes the survivor's room
   NULL -> '' (only where no other row already occupies (club_id, date, '')) so
   future scrapes converge.

Idempotent: a second run finds no groups. Defaults to a dry run (rolls back);
pass --apply to commit.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/collapse_null_room_slot_duplicates.py            # dry run
    make run-script SCRIPT=scripts/core/collapse_null_room_slot_duplicates.py ARGS='--apply'
    make run-script SCRIPT=scripts/core/collapse_null_room_slot_duplicates.py ARGS='--club 2'
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

TASK_ID = 3490
RECOVERY_LOG_PATH = _root / "docs" / "audits" / "task-3490-collapse-null-room-slot-duplicates.json"


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _club_filter(club_id: Optional[int]) -> tuple[str, tuple]:
    if club_id is None:
        return "TRUE", ()
    return "s.club_id = %s", (club_id,)


def _create_temp_show_map(cur: RealDictCursor, club_id: Optional[int]) -> None:
    where, params = _club_filter(club_id)
    cur.execute(
        f"""
        CREATE TEMP TABLE task_3490_show_map ON COMMIT DROP AS
        WITH grp AS (
            SELECT
                s.id,
                s.club_id,
                s.date,
                s.last_scraped_date,
                (SELECT COUNT(*) FROM lineup_items li WHERE li.show_id = s.id) AS lineup_n
            FROM shows s
            WHERE s.room IS NULL
              AND {where}
        ),
        ranked AS (
            SELECT
                id,
                COUNT(*) OVER (PARTITION BY club_id, date) AS grp_size,
                FIRST_VALUE(id) OVER (
                    PARTITION BY club_id, date
                    ORDER BY lineup_n DESC, last_scraped_date DESC NULLS LAST, id DESC
                ) AS canonical_id
            FROM grp
        )
        SELECT id AS old_show_id, canonical_id AS new_show_id
        FROM ranked
        WHERE grp_size > 1 AND id <> canonical_id
        """,
        params,
    )
    cur.execute("CREATE INDEX ON task_3490_show_map (old_show_id)")
    cur.execute("CREATE INDEX ON task_3490_show_map (new_show_id)")


def _summary(cur: RealDictCursor) -> dict[str, Any]:
    cur.execute(
        """
        SELECT COUNT(*) AS duplicate_rows,
               COUNT(DISTINCT new_show_id) AS groups_collapsed
        FROM task_3490_show_map
        """
    )
    return dict(cur.fetchone())


def _top_offenders(cur: RealDictCursor, limit: int = 20) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT s.club_id, c.name AS club_name, COUNT(*) AS duplicate_rows
        FROM task_3490_show_map m
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
        JOIN task_3490_show_map m ON m.old_show_id = li.show_id
        ON CONFLICT (show_id, comedian_id) DO NOTHING
        """
    )
    counts["lineup_items_repointed"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tagged_shows (show_id, tag_id)
        SELECT m.new_show_id, ts.tag_id
        FROM tagged_shows ts
        JOIN task_3490_show_map m ON m.old_show_id = ts.show_id
        ON CONFLICT (show_id, tag_id) DO NOTHING
        """
    )
    counts["tagged_shows_repointed"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tickets (purchase_url, price, sold_out, show_id, type)
        SELECT t.purchase_url, t.price, t.sold_out, m.new_show_id, t.type
        FROM tickets t
        JOIN task_3490_show_map m ON m.old_show_id = t.show_id
        ON CONFLICT (show_id, type) DO NOTHING
        """
    )
    counts["tickets_repointed"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM sent_notifications sn
        USING task_3490_show_map m, sent_notifications existing
        WHERE sn.show_id = m.old_show_id
          AND existing.user_id = sn.user_id
          AND existing.comedian_id = sn.comedian_id
          AND existing.show_id = m.new_show_id
          AND existing.notification_type = sn.notification_type
        """
    )
    counts["conflicting_sent_notifications_deleted"] = cur.rowcount
    cur.execute(
        """
        UPDATE sent_notifications sn
        SET show_id = m.new_show_id
        FROM task_3490_show_map m
        WHERE sn.show_id = m.old_show_id
        """
    )
    counts["sent_notifications_repointed"] = cur.rowcount

    cur.execute(
        """
        UPDATE ticket_purchase_click_events tpce
        SET show_id = m.new_show_id
        FROM task_3490_show_map m
        WHERE tpce.show_id = m.old_show_id
        """
    )
    counts["click_events_repointed"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM shows s
        USING task_3490_show_map m
        WHERE s.id = m.old_show_id
        """
    )
    counts["duplicate_shows_deleted"] = cur.rowcount
    return counts


def _normalize_survivor_rooms(cur: RealDictCursor, club_id: Optional[int]) -> int:
    """Set survivor room NULL -> '' where it is now the sole row at (club, date).

    After the duplicates are deleted each collapsed slot holds one NULL-room
    survivor; normalizing it to '' lets future scrapes (which write '') upsert
    onto it. Guarded against the rare case where a non-NULL '' row already
    occupies the slot.
    """
    where, params = _club_filter(club_id)
    cur.execute(
        f"""
        UPDATE shows s
        SET room = ''
        WHERE s.room IS NULL
          AND {where}
          AND EXISTS (SELECT 1 FROM task_3490_show_map m WHERE m.new_show_id = s.id)
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


def _remaining_conflicts(cur: RealDictCursor, club_id: Optional[int]) -> int:
    where, params = _club_filter(club_id)
    cur.execute(
        f"""
        SELECT COUNT(*) AS groups
        FROM (
            SELECT s.club_id, s.date
            FROM shows s
            WHERE s.room IS NULL AND {where}
            GROUP BY s.club_id, s.date
            HAVING COUNT(*) > 1
        ) g
        """,
        params,
    )
    return int(cur.fetchone()["groups"])


def run(*, apply: bool, club_id: Optional[int]) -> dict[str, Any]:
    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _create_temp_show_map(cur, club_id)
            before = {"map": _summary(cur), "top_offenders": _top_offenders(cur)}

            counts = _repoint_children_and_delete(cur)
            counts["survivor_rooms_normalized"] = _normalize_survivor_rooms(cur, club_id)

            after = {"remaining_null_room_slot_conflicts": _remaining_conflicts(cur, club_id)}

            payload = {
                "task": f"TASK-{TASK_ID}",
                "applied": apply,
                "club_scope": club_id,
                "generated_at": datetime.now(timezone.utc),
                "before": before,
                "counts": counts,
                "after": after,
            }

            if apply:
                _write_recovery_log(payload)
            else:
                conn.rollback()
            return payload


def _write_recovery_log(payload: dict[str, Any]) -> None:
    RECOVERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECOVERY_LOG_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default)
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collapse NULL-room same-slot duplicate shows (TASK-3490)."
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
