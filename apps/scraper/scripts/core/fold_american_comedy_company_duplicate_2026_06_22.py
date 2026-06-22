#!/usr/bin/env python3
"""
Fold duplicate club 4725 "The American Comedy Co." into canonical club 1035.

TASK-3051 found the Ticketmaster national scraper-created row is the same San
Diego venue as American Comedy Company. Shows that collide on the database
uniqueness key are merged into their canonical rows, while non-colliding
Ticketmaster shows are preserved by moving them to club 1035.

Usage:
    cd apps/scraper
    make run-script SCRIPT=scripts/core/fold_american_comedy_company_duplicate_2026_06_22.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/fold_american_comedy_company_duplicate_2026_06_22.py
"""

from __future__ import annotations

import argparse
import json
import sys
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


TASK_ID = 3157
SOURCE_AUDIT_TASK = "TASK-3051"
CANONICAL_CLUB_ID = 1035
DUPLICATE_CLUB_ID = 4725
CANONICAL_NAME = "American Comedy Company"
DUPLICATE_NAME = "The American Comedy Co."
DUPLICATE_CLOSED_NAME = (
    f"{DUPLICATE_NAME} (duplicate of club {CANONICAL_CLUB_ID}; "
    f"folded from club {DUPLICATE_CLUB_ID})"
)
CITY = "San Diego"
STATE = "CA"
ALIAS_SOURCE = "TASK-3157"
RECOVERY_LOG_PATH = _root / "docs" / "audits" / "task-3051-american-comedy-company-fold.json"


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
        SELECT id, name, city, state, visible, status, total_shows, google_place_id
        FROM clubs
        WHERE id IN (%s, %s)
        FOR UPDATE
        """,
        (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
    )
    by_id = {row["id"]: row for row in clubs}
    problems: list[str] = []

    canonical = by_id.get(CANONICAL_CLUB_ID)
    duplicate = by_id.get(DUPLICATE_CLUB_ID)
    if canonical is None:
        problems.append(f"canonical club {CANONICAL_CLUB_ID} not found")
    elif canonical["name"] != CANONICAL_NAME:
        problems.append(
            f"club {CANONICAL_CLUB_ID} name is {canonical['name']!r}, expected {CANONICAL_NAME!r}"
        )

    if duplicate is None:
        problems.append(f"duplicate club {DUPLICATE_CLUB_ID} not found")
    elif duplicate["name"] not in {DUPLICATE_NAME, DUPLICATE_CLOSED_NAME}:
        problems.append(
            f"club {DUPLICATE_CLUB_ID} name is {duplicate['name']!r}, expected {DUPLICATE_NAME!r}"
        )

    if canonical and duplicate and canonical["google_place_id"] != duplicate["google_place_id"]:
        problems.append(
            f"google_place_id mismatch: {CANONICAL_CLUB_ID}={canonical['google_place_id']!r}, "
            f"{DUPLICATE_CLUB_ID}={duplicate['google_place_id']!r}"
        )

    if problems:
        raise RuntimeError("; ".join(problems))
    return {"clubs": clubs}


def _snapshot(cur: RealDictCursor) -> dict[str, Any]:
    return {
        "clubs": _fetch_all(
            cur,
            """
            SELECT id, name, city, state, visible, status, closed_at, total_shows
            FROM clubs
            WHERE id IN (%s, %s)
            ORDER BY id
            """,
            (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
        ),
        "sources": _fetch_all(
            cur,
            """
            SELECT id, club_id, platform, scraper_key, ticketmaster_id,
                   source_url, priority, enabled, metadata
            FROM scraping_sources
            WHERE club_id IN (%s, %s) OR id = 3815
            ORDER BY club_id, priority, id
            """,
            (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
        ),
        "aliases": _fetch_all(
            cur,
            """
            SELECT id, club_id, alias_name, normalized_alias_name, city, state,
                   normalized_city, normalized_state, source, verified
            FROM club_aliases
            WHERE club_id IN (%s, %s)
               OR source = %s
            ORDER BY club_id, id
            """,
            (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID, ALIAS_SOURCE),
        ),
        "show_summary": _fetch_all(
            cur,
            """
            SELECT club_id, COUNT(*) AS show_count, MIN(date) AS first_show, MAX(date) AS last_show
            FROM shows
            WHERE club_id IN (%s, %s)
            GROUP BY club_id
            ORDER BY club_id
            """,
            (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
        ),
        "duplicate_show_map_summary": _fetch_one(
            cur,
            """
            WITH duplicate_shows AS (
                SELECT *
                FROM shows
                WHERE club_id = %s
            ),
            mapped AS (
                SELECT old_show.id AS old_show_id, new_show.id AS new_show_id
                FROM duplicate_shows old_show
                LEFT JOIN shows new_show
                  ON new_show.club_id = %s
                 AND new_show.date = old_show.date
                 AND new_show.room IS NOT DISTINCT FROM old_show.room
            )
            SELECT
                COUNT(*) AS duplicate_shows,
                COUNT(new_show_id) AS date_room_mapped_shows,
                COUNT(*) - COUNT(new_show_id) AS noncolliding_shows
            FROM mapped
            """,
            (DUPLICATE_CLUB_ID, CANONICAL_CLUB_ID),
        ),
        "noncolliding_duplicate_shows": _fetch_all(
            cur,
            """
            SELECT old_show.id, old_show.name, old_show.date, old_show.room,
                   old_show.show_page_url,
                   (SELECT COUNT(*) FROM tickets t WHERE t.show_id = old_show.id) AS tickets,
                   (SELECT COUNT(*) FROM lineup_items li WHERE li.show_id = old_show.id) AS lineup_items,
                   (SELECT COUNT(*) FROM tagged_shows ts WHERE ts.show_id = old_show.id) AS tagged_shows,
                   (SELECT COUNT(*) FROM ticket_purchase_click_events c WHERE c.show_id = old_show.id) AS click_events
            FROM shows old_show
            LEFT JOIN shows new_show
              ON new_show.club_id = %s
             AND new_show.date = old_show.date
             AND new_show.room IS NOT DISTINCT FROM old_show.room
            WHERE old_show.club_id = %s
              AND new_show.id IS NULL
            ORDER BY old_show.date, old_show.id
            """,
            (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
        ),
        "mapped_name_mismatches": _fetch_all(
            cur,
            """
            SELECT old_show.id AS duplicate_show_id,
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
            WHERE old_show.club_id = %s
              AND old_show.name <> new_show.name
            ORDER BY old_show.date, old_show.id
            """,
            (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
        ),
        "remaining_duplicate_references": _remaining_duplicate_references(cur),
    }


def _remaining_duplicate_references(cur: RealDictCursor) -> dict[str, Any] | None:
    return _fetch_one(
        cur,
        """
        SELECT
            (SELECT COUNT(*) FROM shows WHERE club_id = %s) AS shows,
            (SELECT COUNT(*) FROM ticket_purchase_click_events WHERE club_id = %s) AS click_events,
            (SELECT COUNT(*) FROM favorite_clubs WHERE club_id = %s) AS favorite_clubs,
            (SELECT COUNT(*) FROM email_subscriptions WHERE club_id = %s) AS email_subscriptions,
            (SELECT COUNT(*) FROM tagged_clubs WHERE club_id = %s) AS tagged_clubs,
            (SELECT COUNT(*) FROM production_company_venues WHERE club_id = %s) AS production_company_venues,
            (SELECT COUNT(*) FROM processed_emails WHERE club_id = %s) AS processed_emails,
            (SELECT COUNT(*) FROM eventbrite_organizer_venues WHERE club_id = %s) AS eventbrite_organizer_venues,
            (SELECT COUNT(*) FROM club_image_assets WHERE club_id = %s) AS club_image_assets,
            (SELECT COUNT(*) FROM scraper_run_clubs WHERE club_id = %s) AS scraper_run_clubs,
            (SELECT COUNT(*) FROM scraping_sources WHERE club_id = %s AND enabled) AS enabled_sources
        """,
        (
            DUPLICATE_CLUB_ID,
            DUPLICATE_CLUB_ID,
            DUPLICATE_CLUB_ID,
            DUPLICATE_CLUB_ID,
            DUPLICATE_CLUB_ID,
            DUPLICATE_CLUB_ID,
            DUPLICATE_CLUB_ID,
            DUPLICATE_CLUB_ID,
            DUPLICATE_CLUB_ID,
            DUPLICATE_CLUB_ID,
            DUPLICATE_CLUB_ID,
        ),
    )


def _create_temp_show_map(cur: RealDictCursor) -> None:
    cur.execute(
        """
        CREATE TEMP TABLE task_3157_show_map AS
        SELECT
            old_show.id AS old_show_id,
            new_show.id AS new_show_id,
            old_show.name,
            old_show.date,
            old_show.room
        FROM shows old_show
        LEFT JOIN shows new_show
          ON new_show.club_id = %s
         AND new_show.date = old_show.date
         AND new_show.room IS NOT DISTINCT FROM old_show.room
        WHERE old_show.club_id = %s
        """,
        (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
    )


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
    counts["aliases_upserted"] = _upsert_alias(cur, DUPLICATE_NAME)
    counts["punctuation_aliases_upserted"] = _upsert_alias(cur, "American Comedy Co.")

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
            WHERE ss.club_id = %s
        )
        UPDATE scraping_sources ss
        SET club_id = %s,
            priority = d.new_priority,
            enabled = false,
            metadata = COALESCE(ss.metadata, '{}'::jsonb)
                || jsonb_build_object(
                    'task_3157_disposition',
                    'moved disabled duplicate Ticketmaster source from club 4725 to club 1035',
                    'task_3157_source_audit',
                    %s
                ),
            updated_at = NOW()
        FROM duplicate_sources d
        WHERE ss.id = d.id
        """,
        (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID, CANONICAL_CLUB_ID, SOURCE_AUDIT_TASK),
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
        JOIN task_3157_show_map m ON m.old_show_id = li.show_id
        WHERE m.new_show_id IS NOT NULL
        ON CONFLICT (show_id, comedian_id) DO NOTHING
        """
    )
    counts["lineup_items_copied"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tagged_shows (show_id, tag_id)
        SELECT m.new_show_id, ts.tag_id
        FROM tagged_shows ts
        JOIN task_3157_show_map m ON m.old_show_id = ts.show_id
        WHERE m.new_show_id IS NOT NULL
        ON CONFLICT (show_id, tag_id) DO NOTHING
        """
    )
    counts["tagged_shows_copied"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tickets (purchase_url, price, sold_out, show_id, type)
        SELECT t.purchase_url, t.price, t.sold_out, m.new_show_id, t.type
        FROM tickets t
        JOIN task_3157_show_map m ON m.old_show_id = t.show_id
        WHERE m.new_show_id IS NOT NULL
        ON CONFLICT (show_id, type) DO NOTHING
        """
    )
    counts["tickets_copied"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM sent_notifications sn
        USING task_3157_show_map m,
              sent_notifications existing
        WHERE m.new_show_id IS NOT NULL
          AND sn.show_id = m.old_show_id
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
        FROM task_3157_show_map m
        WHERE m.new_show_id IS NOT NULL
          AND sn.show_id = m.old_show_id
        """
    )
    counts["sent_notifications_repointed"] = cur.rowcount

    cur.execute(
        """
        UPDATE ticket_purchase_click_events tpce
        SET show_id = m.new_show_id,
            club_id = %s
        FROM task_3157_show_map m
        WHERE m.new_show_id IS NOT NULL
          AND tpce.show_id = m.old_show_id
        """,
        (CANONICAL_CLUB_ID,),
    )
    counts["click_events_repointed_to_existing_show"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM shows s
        USING task_3157_show_map m
        WHERE s.id = m.old_show_id
          AND m.new_show_id IS NOT NULL
        """
    )
    counts["colliding_duplicate_shows_deleted"] = cur.rowcount

    cur.execute(
        """
        UPDATE shows
        SET club_id = %s
        WHERE club_id = %s
        """,
        (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
    )
    counts["noncolliding_shows_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE ticket_purchase_click_events
        SET club_id = %s
        WHERE club_id = %s
        """,
        (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
    )
    counts["click_events_club_repointed"] = cur.rowcount
    return counts


def _apply_club_reference_updates(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}

    cur.execute(
        """
        INSERT INTO favorite_clubs (profile_id, club_id)
        SELECT fc.profile_id, %s
        FROM favorite_clubs fc
        WHERE fc.club_id = %s
          AND NOT EXISTS (
              SELECT 1
              FROM favorite_clubs existing
              WHERE existing.profile_id = fc.profile_id
                AND existing.club_id = %s
          )
        """,
        (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID, CANONICAL_CLUB_ID),
    )
    counts["favorite_clubs_inserted"] = cur.rowcount

    cur.execute("DELETE FROM favorite_clubs WHERE club_id = %s", (DUPLICATE_CLUB_ID,))
    counts["duplicate_favorite_clubs_deleted"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO production_company_venues (production_company_id, club_id)
        SELECT pcv.production_company_id, %s
        FROM production_company_venues pcv
        WHERE pcv.club_id = %s
          AND NOT EXISTS (
              SELECT 1
              FROM production_company_venues existing
              WHERE existing.production_company_id = pcv.production_company_id
                AND existing.club_id = %s
          )
        """,
        (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID, CANONICAL_CLUB_ID),
    )
    counts["production_company_venues_inserted"] = cur.rowcount

    cur.execute("DELETE FROM production_company_venues WHERE club_id = %s", (DUPLICATE_CLUB_ID,))
    counts["duplicate_production_company_venues_deleted"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tagged_clubs (club_id, tag_id)
        SELECT %s, tc.tag_id
        FROM tagged_clubs tc
        WHERE tc.club_id = %s
          AND NOT EXISTS (
              SELECT 1
              FROM tagged_clubs existing
              WHERE existing.club_id = %s
                AND existing.tag_id = tc.tag_id
          )
        """,
        (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID, CANONICAL_CLUB_ID),
    )
    counts["tagged_clubs_inserted"] = cur.rowcount

    cur.execute("DELETE FROM tagged_clubs WHERE club_id = %s", (DUPLICATE_CLUB_ID,))
    counts["duplicate_tagged_clubs_deleted"] = cur.rowcount

    cur.execute("UPDATE email_subscriptions SET club_id = %s WHERE club_id = %s", (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID))
    counts["email_subscriptions_moved"] = cur.rowcount

    cur.execute("UPDATE processed_emails SET club_id = %s WHERE club_id = %s", (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID))
    counts["processed_emails_moved"] = cur.rowcount

    cur.execute(
        "UPDATE eventbrite_organizer_venues SET club_id = %s WHERE club_id = %s",
        (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
    )
    counts["eventbrite_organizer_venues_moved"] = cur.rowcount

    cur.execute("UPDATE club_image_assets SET club_id = %s WHERE club_id = %s", (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID))
    counts["club_image_assets_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE scraper_run_clubs
        SET club_id = %s,
            club_name = %s
        WHERE club_id = %s
        """,
        (CANONICAL_CLUB_ID, CANONICAL_NAME, DUPLICATE_CLUB_ID),
    )
    counts["scraper_run_clubs_moved"] = cur.rowcount
    return counts


def _close_duplicate(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}
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
        (DUPLICATE_CLOSED_NAME, DUPLICATE_CLUB_ID),
    )
    counts["duplicate_clubs_closed"] = cur.rowcount

    cur.execute(
        """
        UPDATE clubs
        SET total_shows = (SELECT COUNT(*) FROM shows WHERE shows.club_id = clubs.id)
        WHERE id IN (%s, %s)
        """,
        (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
    )
    counts["club_totals_recomputed"] = cur.rowcount
    return counts


def _assert_postconditions(cur: RealDictCursor) -> None:
    remaining = _remaining_duplicate_references(cur)
    if not remaining:
        raise RuntimeError("could not compute duplicate reference postconditions")
    nonzero = {key: value for key, value in remaining.items() if value}
    if nonzero:
        raise RuntimeError(f"club {DUPLICATE_CLUB_ID} still has references after fold: {nonzero}")


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
                _close_duplicate(cur),
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
                    "duplicate_id": DUPLICATE_CLUB_ID,
                    "canonical_name": CANONICAL_NAME,
                    "duplicate_name": DUPLICATE_NAME,
                    "aliases": [
                        {"alias_name": DUPLICATE_NAME, "city": CITY, "state": STATE},
                        {"alias_name": "American Comedy Co.", "city": CITY, "state": STATE},
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
    parser = argparse.ArgumentParser(description="Fold American Comedy Company duplicate club 4725 into 1035.")
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
