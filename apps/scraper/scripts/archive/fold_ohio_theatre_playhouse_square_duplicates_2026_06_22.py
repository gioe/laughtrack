#!/usr/bin/env python3
"""
Fold Ohio Theatre Playhouse Square duplicate clubs into Mimi Ohio Theatre.

TASK-3054 found active duplicate clubs 9906 and 9955 are the same Cleveland,
OH Playhouse Square venue as canonical club 5394. Both duplicate rows contain
the same two shows as club 5394; one show title is shortened by Ticketmaster,
so the fold maps duplicate shows by date and room and preserves child rows
before deleting the colliding duplicate show rows.

Usage:
    cd apps/scraper
    make run-script SCRIPT=scripts/core/fold_ohio_theatre_playhouse_square_duplicates_2026_06_22.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/fold_ohio_theatre_playhouse_square_duplicates_2026_06_22.py
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction


TASK_ID = 3165
SOURCE_AUDIT_TASK = "TASK-3054"
CANONICAL_CLUB_ID = 5394
CANONICAL_NAME = "Mimi Ohio Theatre"
CITY = "Cleveland"
STATE = "OH"
ALIAS_SOURCE = "TASK-3165"
RECOVERY_LOG_PATH = _root / "docs" / "audits" / "task-3054-ohio-theatre-playhouse-square-fold.json"


@dataclass(frozen=True)
class DuplicateClub:
    club_id: int
    name: str

    @property
    def closed_name(self) -> str:
        return f"{self.name} (duplicate of club {CANONICAL_CLUB_ID}; folded from club {self.club_id})"


DUPLICATES: tuple[DuplicateClub, ...] = (
    DuplicateClub(9906, "Ohio Theatre at PlayhouseSquare"),
    DuplicateClub(9955, "Ohio Theatre - Playhouse Square"),
)


def _duplicate_ids() -> list[int]:
    return [duplicate.club_id for duplicate in DUPLICATES]


def _all_club_ids() -> list[int]:
    return [CANONICAL_CLUB_ID, *_duplicate_ids()]


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _fetch_one(cur: RealDictCursor, sql: str, params: tuple = ()) -> dict[str, Any] | None:
    cur.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def _fetch_all(cur: RealDictCursor, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]


def _validate(cur: RealDictCursor) -> dict[str, Any]:
    clubs = _fetch_all(
        cur,
        """
        SELECT id, name, address, website, city, state, timezone, visible, status,
               total_shows, google_place_id
        FROM clubs
        WHERE id = ANY(%s)
        FOR UPDATE
        """,
        (_all_club_ids(),),
    )
    by_id = {row["id"]: row for row in clubs}
    problems: list[str] = []

    canonical = by_id.get(CANONICAL_CLUB_ID)
    if canonical is None:
        problems.append(f"canonical club {CANONICAL_CLUB_ID} not found")
    elif canonical["name"] != CANONICAL_NAME:
        problems.append(
            f"club {CANONICAL_CLUB_ID} name is {canonical['name']!r}, expected {CANONICAL_NAME!r}"
        )

    for duplicate in DUPLICATES:
        row = by_id.get(duplicate.club_id)
        if row is None:
            problems.append(f"duplicate club {duplicate.club_id} not found")
        elif row["name"] not in {duplicate.name, duplicate.closed_name}:
            problems.append(
                f"club {duplicate.club_id} name is {row['name']!r}, expected {duplicate.name!r}"
            )

    if problems:
        raise RuntimeError("; ".join(problems))
    return {"clubs": clubs}


def _remaining_duplicate_references(cur: RealDictCursor) -> dict[str, Any] | None:
    duplicate_ids = _duplicate_ids()
    return _fetch_one(
        cur,
        """
        SELECT
            (SELECT COUNT(*) FROM shows WHERE club_id = ANY(%s)) AS shows,
            (SELECT COUNT(*) FROM ticket_purchase_click_events WHERE club_id = ANY(%s)) AS click_events,
            (SELECT COUNT(*) FROM favorite_clubs WHERE club_id = ANY(%s)) AS favorite_clubs,
            (SELECT COUNT(*) FROM email_subscriptions WHERE club_id = ANY(%s)) AS email_subscriptions,
            (SELECT COUNT(*) FROM tagged_clubs WHERE club_id = ANY(%s)) AS tagged_clubs,
            (SELECT COUNT(*) FROM production_company_venues WHERE club_id = ANY(%s)) AS production_company_venues,
            (SELECT COUNT(*) FROM processed_emails WHERE club_id = ANY(%s)) AS processed_emails,
            (SELECT COUNT(*) FROM eventbrite_organizer_venues WHERE club_id = ANY(%s)) AS eventbrite_organizer_venues,
            (SELECT COUNT(*) FROM club_image_assets WHERE club_id = ANY(%s)) AS club_image_assets,
            (SELECT COUNT(*) FROM scraper_run_clubs WHERE club_id = ANY(%s)) AS scraper_run_clubs,
            (SELECT COUNT(*) FROM scraping_sources WHERE club_id = ANY(%s)) AS sources,
            (SELECT COUNT(*) FROM scraping_sources WHERE club_id = ANY(%s) AND enabled) AS enabled_sources
        """,
        (
            duplicate_ids,
            duplicate_ids,
            duplicate_ids,
            duplicate_ids,
            duplicate_ids,
            duplicate_ids,
            duplicate_ids,
            duplicate_ids,
            duplicate_ids,
            duplicate_ids,
            duplicate_ids,
            duplicate_ids,
        ),
    )


def _snapshot(cur: RealDictCursor) -> dict[str, Any]:
    all_ids = _all_club_ids()
    duplicate_ids = _duplicate_ids()
    return {
        "clubs": _fetch_all(
            cur,
            """
            SELECT id, name, address, website, city, state, timezone, visible,
                   status, closed_at, total_shows, google_place_id
            FROM clubs
            WHERE id = ANY(%s)
            ORDER BY id
            """,
            (all_ids,),
        ),
        "sources": _fetch_all(
            cur,
            """
            SELECT id, club_id, platform, scraper_key, ticketmaster_id,
                   source_url, priority, enabled, metadata
            FROM scraping_sources
            WHERE club_id = ANY(%s)
               OR id IN (6675, 6719)
            ORDER BY club_id, platform, priority, id
            """,
            (all_ids,),
        ),
        "aliases": _fetch_all(
            cur,
            """
            SELECT id, club_id, alias_name, normalized_alias_name, city, state,
                   normalized_city, normalized_state, source, verified
            FROM club_aliases
            WHERE club_id = ANY(%s)
               OR source = %s
            ORDER BY club_id, id
            """,
            (all_ids, ALIAS_SOURCE),
        ),
        "show_summary": _fetch_all(
            cur,
            """
            SELECT club_id, COUNT(*) AS show_count, MIN(date) AS first_show, MAX(date) AS last_show
            FROM shows
            WHERE club_id = ANY(%s)
            GROUP BY club_id
            ORDER BY club_id
            """,
            (all_ids,),
        ),
        "duplicate_show_map_summary": _fetch_all(
            cur,
            """
            WITH duplicate_shows AS (
                SELECT *
                FROM shows
                WHERE club_id = ANY(%s)
            ),
            mapped AS (
                SELECT old_show.club_id AS duplicate_club_id,
                       old_show.id AS old_show_id,
                       new_show.id AS new_show_id,
                       old_show.name AS old_name,
                       new_show.name AS new_name
                FROM duplicate_shows old_show
                LEFT JOIN shows new_show
                  ON new_show.club_id = %s
                 AND new_show.date = old_show.date
                 AND new_show.room IS NOT DISTINCT FROM old_show.room
            )
            SELECT
                duplicate_club_id,
                COUNT(*) AS duplicate_shows,
                COUNT(new_show_id) AS date_room_mapped_shows,
                COUNT(*) - COUNT(new_show_id) AS noncolliding_shows,
                COALESCE(SUM((old_name = new_name)::int), 0) AS same_name_mapped,
                COALESCE(SUM((old_name <> new_name)::int), 0) AS name_mismatch_mapped
            FROM mapped
            GROUP BY duplicate_club_id
            ORDER BY duplicate_club_id
            """,
            (duplicate_ids, CANONICAL_CLUB_ID),
        ),
        "mapped_name_mismatches": _fetch_all(
            cur,
            """
            SELECT old_show.club_id AS duplicate_club_id,
                   old_show.id AS duplicate_show_id,
                   old_show.name AS duplicate_name,
                   old_show.date,
                   old_show.room,
                   new_show.id AS canonical_show_id,
                   new_show.name AS canonical_name,
                   old_show.show_page_url AS duplicate_show_page_url,
                   new_show.show_page_url AS canonical_show_page_url
            FROM shows old_show
            JOIN shows new_show
              ON new_show.club_id = %s
             AND new_show.date = old_show.date
             AND new_show.room IS NOT DISTINCT FROM old_show.room
            WHERE old_show.club_id = ANY(%s)
              AND old_show.name <> new_show.name
            ORDER BY old_show.club_id, old_show.date, old_show.id
            """,
            (CANONICAL_CLUB_ID, duplicate_ids),
        ),
        "child_row_summary": _fetch_all(
            cur,
            """
            WITH mapped AS (
                SELECT old_show.club_id AS duplicate_club_id,
                       old_show.id AS old_show_id,
                       new_show.id AS new_show_id
                FROM shows old_show
                JOIN shows new_show
                  ON new_show.club_id = %s
                 AND new_show.date = old_show.date
                 AND new_show.room IS NOT DISTINCT FROM old_show.room
                WHERE old_show.club_id = ANY(%s)
            )
            SELECT m.duplicate_club_id,
                   m.old_show_id,
                   m.new_show_id,
                   (SELECT COUNT(*) FROM tickets t WHERE t.show_id = m.old_show_id) AS old_tickets,
                   (SELECT COUNT(*) FROM tickets t WHERE t.show_id = m.new_show_id) AS new_tickets,
                   (SELECT COUNT(*) FROM lineup_items li WHERE li.show_id = m.old_show_id) AS old_lineup_items,
                   (SELECT COUNT(*) FROM lineup_items li WHERE li.show_id = m.new_show_id) AS new_lineup_items,
                   (SELECT COUNT(*) FROM tagged_shows ts WHERE ts.show_id = m.old_show_id) AS old_tagged_shows,
                   (SELECT COUNT(*) FROM tagged_shows ts WHERE ts.show_id = m.new_show_id) AS new_tagged_shows,
                   (SELECT COUNT(*) FROM ticket_purchase_click_events c WHERE c.show_id = m.old_show_id) AS old_click_events
            FROM mapped m
            ORDER BY m.duplicate_club_id, m.old_show_id
            """,
            (CANONICAL_CLUB_ID, duplicate_ids),
        ),
        "remaining_duplicate_references": _remaining_duplicate_references(cur),
    }


def _create_temp_show_map(cur: RealDictCursor) -> None:
    cur.execute(
        """
        CREATE TEMP TABLE task_3165_show_map AS
        SELECT
            old_show.club_id AS duplicate_club_id,
            old_show.id AS old_show_id,
            new_show.id AS new_show_id,
            old_show.name AS old_name,
            new_show.name AS new_name,
            old_show.date,
            old_show.room
        FROM shows old_show
        LEFT JOIN shows new_show
          ON new_show.club_id = %s
         AND new_show.date = old_show.date
         AND new_show.room IS NOT DISTINCT FROM old_show.room
        WHERE old_show.club_id = ANY(%s)
        """,
        (CANONICAL_CLUB_ID, _duplicate_ids()),
    )
    unmatched = _fetch_one(
        cur,
        "SELECT COUNT(*) AS count FROM task_3165_show_map WHERE new_show_id IS NULL",
    )
    if unmatched and unmatched["count"]:
        samples = _fetch_all(
            cur,
            """
            SELECT duplicate_club_id, old_show_id, old_name, date, room
            FROM task_3165_show_map
            WHERE new_show_id IS NULL
            ORDER BY duplicate_club_id, date
            LIMIT 10
            """,
        )
        raise RuntimeError(f"{unmatched['count']} duplicate shows lack date-room matches: {samples}")


def _upsert_alias(cur: RealDictCursor, alias_name: str) -> int:
    cur.execute(
        """
        INSERT INTO club_aliases (
            club_id,
            alias_name,
            normalized_alias_name,
            city,
            state,
            normalized_city,
            normalized_state,
            source,
            verified,
            created_at,
            updated_at
        )
        VALUES (
            %s,
            %s,
            btrim(regexp_replace(replace(lower(%s), '&', ' and '), '[^a-z0-9]+', ' ', 'g')),
            %s,
            %s,
            btrim(regexp_replace(lower(%s), '[^a-z0-9]+', ' ', 'g')),
            lower(%s),
            %s,
            TRUE,
            NOW(),
            NOW()
        )
        ON CONFLICT (normalized_alias_name, normalized_city, normalized_state)
        DO UPDATE SET
            club_id = EXCLUDED.club_id,
            alias_name = EXCLUDED.alias_name,
            city = EXCLUDED.city,
            state = EXCLUDED.state,
            source = EXCLUDED.source,
            verified = TRUE,
            updated_at = NOW()
        """,
        (CANONICAL_CLUB_ID, alias_name, alias_name, CITY, STATE, CITY, STATE, ALIAS_SOURCE),
    )
    return cur.rowcount


def _apply_future_routing(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}
    for duplicate in DUPLICATES:
        counts[f"alias_{duplicate.club_id}_upserted"] = _upsert_alias(cur, duplicate.name)

    cur.execute(
        """
        WITH duplicate_sources AS (
            SELECT
                ss.id,
                COALESCE((
                    SELECT MAX(existing.priority)
                    FROM scraping_sources existing
                    WHERE existing.club_id = %s
                      AND existing.platform = ss.platform
                      AND existing.id <> ss.id
                ), -1) + ROW_NUMBER() OVER (PARTITION BY ss.platform ORDER BY ss.priority, ss.id) AS new_priority
            FROM scraping_sources ss
            WHERE ss.club_id = ANY(%s)
        )
        UPDATE scraping_sources ss
        SET club_id = %s,
            priority = d.new_priority,
            enabled = false,
            metadata = COALESCE(ss.metadata, '{}'::jsonb)
                || jsonb_build_object(
                    'task_3165_disposition',
                    'moved disabled duplicate Ticketmaster source from Ohio Theatre duplicate club to Mimi Ohio Theatre',
                    'task_3165_source_audit',
                    %s
                ),
            updated_at = NOW()
        FROM duplicate_sources d
        WHERE ss.id = d.id
        """,
        (CANONICAL_CLUB_ID, _duplicate_ids(), CANONICAL_CLUB_ID, SOURCE_AUDIT_TASK),
    )
    counts["duplicate_sources_moved_to_canonical"] = cur.rowcount
    return counts


def _apply_show_updates(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}

    cur.execute(
        """
        INSERT INTO lineup_items (show_id, comedian_id, role)
        SELECT m.new_show_id, li.comedian_id, li.role
        FROM lineup_items li
        JOIN task_3165_show_map m ON m.old_show_id = li.show_id
        ON CONFLICT (show_id, comedian_id) DO NOTHING
        """
    )
    counts["lineup_items_copied"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tagged_shows (show_id, tag_id)
        SELECT m.new_show_id, ts.tag_id
        FROM tagged_shows ts
        JOIN task_3165_show_map m ON m.old_show_id = ts.show_id
        ON CONFLICT (show_id, tag_id) DO NOTHING
        """
    )
    counts["tagged_shows_copied"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tickets (purchase_url, price, sold_out, show_id, type)
        SELECT t.purchase_url, t.price, t.sold_out, m.new_show_id, t.type
        FROM tickets t
        JOIN task_3165_show_map m ON m.old_show_id = t.show_id
        ON CONFLICT (show_id, type) DO NOTHING
        """
    )
    counts["tickets_copied"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM sent_notifications sn
        USING task_3165_show_map m,
              sent_notifications existing
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
        FROM task_3165_show_map m
        WHERE sn.show_id = m.old_show_id
        """
    )
    counts["sent_notifications_repointed"] = cur.rowcount

    cur.execute(
        """
        UPDATE ticket_purchase_click_events tpce
        SET show_id = m.new_show_id,
            club_id = %s
        FROM task_3165_show_map m
        WHERE tpce.show_id = m.old_show_id
        """,
        (CANONICAL_CLUB_ID,),
    )
    counts["click_events_repointed_to_existing_show"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM shows s
        USING task_3165_show_map m
        WHERE s.id = m.old_show_id
        """
    )
    counts["colliding_duplicate_shows_deleted"] = cur.rowcount

    cur.execute(
        """
        UPDATE ticket_purchase_click_events
        SET club_id = %s
        WHERE club_id = ANY(%s)
        """,
        (CANONICAL_CLUB_ID, _duplicate_ids()),
    )
    counts["click_events_club_repointed"] = cur.rowcount
    return counts


def _apply_club_reference_updates(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}
    duplicate_ids = _duplicate_ids()

    cur.execute(
        """
        INSERT INTO favorite_clubs (profile_id, club_id)
        SELECT fc.profile_id, %s
        FROM favorite_clubs fc
        WHERE fc.club_id = ANY(%s)
          AND NOT EXISTS (
              SELECT 1
              FROM favorite_clubs existing
              WHERE existing.profile_id = fc.profile_id
                AND existing.club_id = %s
          )
        """,
        (CANONICAL_CLUB_ID, duplicate_ids, CANONICAL_CLUB_ID),
    )
    counts["favorite_clubs_inserted"] = cur.rowcount

    cur.execute("DELETE FROM favorite_clubs WHERE club_id = ANY(%s)", (duplicate_ids,))
    counts["duplicate_favorite_clubs_deleted"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO production_company_venues (production_company_id, club_id)
        SELECT pcv.production_company_id, %s
        FROM production_company_venues pcv
        WHERE pcv.club_id = ANY(%s)
          AND NOT EXISTS (
              SELECT 1
              FROM production_company_venues existing
              WHERE existing.production_company_id = pcv.production_company_id
                AND existing.club_id = %s
          )
        """,
        (CANONICAL_CLUB_ID, duplicate_ids, CANONICAL_CLUB_ID),
    )
    counts["production_company_venues_inserted"] = cur.rowcount

    cur.execute("DELETE FROM production_company_venues WHERE club_id = ANY(%s)", (duplicate_ids,))
    counts["duplicate_production_company_venues_deleted"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tagged_clubs (club_id, tag_id)
        SELECT %s, tc.tag_id
        FROM tagged_clubs tc
        WHERE tc.club_id = ANY(%s)
          AND NOT EXISTS (
              SELECT 1
              FROM tagged_clubs existing
              WHERE existing.club_id = %s
                AND existing.tag_id = tc.tag_id
          )
        """,
        (CANONICAL_CLUB_ID, duplicate_ids, CANONICAL_CLUB_ID),
    )
    counts["tagged_clubs_inserted"] = cur.rowcount

    cur.execute("DELETE FROM tagged_clubs WHERE club_id = ANY(%s)", (duplicate_ids,))
    counts["duplicate_tagged_clubs_deleted"] = cur.rowcount

    cur.execute(
        "UPDATE email_subscriptions SET club_id = %s WHERE club_id = ANY(%s)",
        (CANONICAL_CLUB_ID, duplicate_ids),
    )
    counts["email_subscriptions_moved"] = cur.rowcount

    cur.execute(
        "UPDATE processed_emails SET club_id = %s WHERE club_id = ANY(%s)",
        (CANONICAL_CLUB_ID, duplicate_ids),
    )
    counts["processed_emails_moved"] = cur.rowcount

    cur.execute(
        "UPDATE eventbrite_organizer_venues SET club_id = %s WHERE club_id = ANY(%s)",
        (CANONICAL_CLUB_ID, duplicate_ids),
    )
    counts["eventbrite_organizer_venues_moved"] = cur.rowcount

    cur.execute(
        "UPDATE club_image_assets SET club_id = %s WHERE club_id = ANY(%s)",
        (CANONICAL_CLUB_ID, duplicate_ids),
    )
    counts["club_image_assets_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE scraper_run_clubs
        SET club_id = %s,
            club_name = %s
        WHERE club_id = ANY(%s)
        """,
        (CANONICAL_CLUB_ID, CANONICAL_NAME, duplicate_ids),
    )
    counts["scraper_run_clubs_moved"] = cur.rowcount
    return counts


def _close_duplicates(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}
    for duplicate in DUPLICATES:
        cur.execute(
            """
            UPDATE clubs
            SET name = %s,
                visible = false,
                status = 'closed',
                closed_at = COALESCE(closed_at, NOW()),
                total_shows = 0
            WHERE id = %s
            """,
            (duplicate.closed_name, duplicate.club_id),
        )
        counts[f"duplicate_{duplicate.club_id}_closed"] = cur.rowcount

    cur.execute(
        """
        UPDATE clubs
        SET total_shows = (SELECT COUNT(*) FROM shows WHERE shows.club_id = clubs.id)
        WHERE id = ANY(%s)
        """,
        (_all_club_ids(),),
    )
    counts["club_totals_recomputed"] = cur.rowcount
    return counts


def _assert_postconditions(cur: RealDictCursor) -> None:
    remaining = _remaining_duplicate_references(cur)
    if not remaining:
        raise RuntimeError("could not compute duplicate reference postconditions")
    nonzero = {key: value for key, value in remaining.items() if value}
    if nonzero:
        raise RuntimeError(f"duplicate clubs still have references after fold: {nonzero}")


def _write_recovery_log(payload: dict[str, Any]) -> None:
    RECOVERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECOVERY_LOG_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8",
    )


def run(*, dry_run: bool) -> dict[str, Any]:
    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            validation = _validate(cur)
            before = _snapshot(cur)
            _create_temp_show_map(cur)

            counts: dict[str, int] = {}
            for section in (
                _apply_future_routing(cur),
                _apply_show_updates(cur),
                _apply_club_reference_updates(cur),
                _close_duplicates(cur),
            ):
                counts.update(section)

            _assert_postconditions(cur)
            after = _snapshot(cur)
            payload = {
                "task": f"TASK-{TASK_ID}",
                "source_audit_task": SOURCE_AUDIT_TASK,
                "dry_run": dry_run,
                "generated_at": datetime.now(timezone.utc),
                "fold": {
                    "canonical_id": CANONICAL_CLUB_ID,
                    "canonical_name": CANONICAL_NAME,
                    "duplicate_ids": _duplicate_ids(),
                    "duplicates": [
                        {"club_id": duplicate.club_id, "name": duplicate.name}
                        for duplicate in DUPLICATES
                    ],
                    "aliases": [
                        {"alias_name": duplicate.name, "city": CITY, "state": STATE}
                        for duplicate in DUPLICATES
                    ],
                    "match_key": ["date", "room"],
                    "name_mismatch_policy": (
                        "Rows with the same date and room must merge because "
                        "shows_club_id_date_room_key prevents preserving both "
                        "under the canonical club."
                    ),
                },
                "validation": validation,
                "before": before,
                "counts": counts,
                "after": after,
            }

            if dry_run:
                conn.rollback()
            else:
                _write_recovery_log(payload)
            return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fold Ohio Theatre Playhouse Square duplicate clubs into Mimi Ohio Theatre."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    payload = run(dry_run=args.dry_run)
    print(json.dumps(payload, indent=2, sort_keys=True, default=_json_default))
    if args.dry_run:
        print("DRY RUN: no database rows were changed and no recovery log was written.")
    else:
        print(f"Wrote recovery log: {RECOVERY_LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
