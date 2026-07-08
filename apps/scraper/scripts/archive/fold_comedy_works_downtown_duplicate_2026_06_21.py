#!/usr/bin/env python3
"""
Fold duplicate Downtown Denver Comedy Works club 5297 into canonical club 1036.

This applies the safe fold plan recorded by TASK-3050:

  * 5297 Comedy Works -> 1036 Comedy Works Downtown
  * preserve click history on the surviving canonical shows
  * move and disable Ticketmaster source 4387 so future source lookup resolves
    to the canonical club without re-enabling the weaker duplicate feed
  * add a Denver-scoped Comedy Works alias to avoid colliding with Comedy Works
    South in Greenwood Village

Usage:
    cd apps/scraper
    make run-script SCRIPT=scripts/core/fold_comedy_works_downtown_duplicate_2026_06_21.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/fold_comedy_works_downtown_duplicate_2026_06_21.py
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


TASK_ID = 3153
SOURCE_TASK_REF = "TASK-3050"
ALIAS_SOURCE = "TASK-3153"
CANONICAL_ID = 1036
DUPLICATE_ID = 5297
CANONICAL_NAME = "Comedy Works Downtown"
DUPLICATE_NAME = "Comedy Works"
ALIAS_NAME = "Comedy Works"
CITY = "Denver"
STATE = "CO"
RECOVERY_LOG_PATH = _root / "docs" / "audits" / "task-3153-comedy-works-downtown-fold.json"


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


def _closed_name() -> str:
    return f"{DUPLICATE_NAME} (duplicate of club {CANONICAL_ID}; folded from club {DUPLICATE_ID})"


def _validate(cur: RealDictCursor) -> dict[str, Any]:
    rows = _fetch_all(
        cur,
        """
        SELECT id, name, city, state, visible, status, total_shows, google_place_id
        FROM clubs
        WHERE id IN (%s, %s)
        FOR UPDATE
        """,
        (CANONICAL_ID, DUPLICATE_ID),
    )
    clubs_by_id = {row["id"]: row for row in rows}
    problems: list[str] = []

    canonical = clubs_by_id.get(CANONICAL_ID)
    duplicate = clubs_by_id.get(DUPLICATE_ID)
    if canonical is None:
        problems.append(f"canonical club {CANONICAL_ID} not found")
    elif canonical["name"] != CANONICAL_NAME:
        problems.append(f"club {CANONICAL_ID} name is {canonical['name']!r}, expected {CANONICAL_NAME!r}")

    if duplicate is None:
        problems.append(f"duplicate club {DUPLICATE_ID} not found")
    elif duplicate["name"] not in {DUPLICATE_NAME, _closed_name()}:
        problems.append(f"club {DUPLICATE_ID} name is {duplicate['name']!r}, expected {DUPLICATE_NAME!r}")

    if canonical and duplicate and canonical["google_place_id"] != duplicate["google_place_id"]:
        problems.append(
            f"google_place_id mismatch: {CANONICAL_ID}={canonical['google_place_id']!r}, "
            f"{DUPLICATE_ID}={duplicate['google_place_id']!r}"
        )

    if problems:
        raise RuntimeError("; ".join(problems))
    return {"clubs": rows}


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
            (CANONICAL_ID, DUPLICATE_ID),
        ),
        "sources": _fetch_all(
            cur,
            """
            SELECT id, club_id, platform, scraper_key, ticketmaster_id,
                   source_url, priority, enabled, metadata
            FROM scraping_sources
            WHERE club_id IN (%s, %s) OR id = 4387
            ORDER BY club_id, priority, id
            """,
            (CANONICAL_ID, DUPLICATE_ID),
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
            (CANONICAL_ID, DUPLICATE_ID, ALIAS_SOURCE),
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
            (CANONICAL_ID, DUPLICATE_ID),
        ),
        "remaining_duplicate_references": _fetch_one(
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
                (SELECT COUNT(*) FROM scraper_run_clubs WHERE club_id = %s) AS scraper_run_clubs
            """,
            (
                DUPLICATE_ID,
                DUPLICATE_ID,
                DUPLICATE_ID,
                DUPLICATE_ID,
                DUPLICATE_ID,
                DUPLICATE_ID,
                DUPLICATE_ID,
                DUPLICATE_ID,
                DUPLICATE_ID,
                DUPLICATE_ID,
            ),
        ),
    }


def _create_temp_show_map(cur: RealDictCursor) -> None:
    cur.execute(
        """
        CREATE TEMP TABLE task_3153_show_map AS
        SELECT
            old_show.id AS old_show_id,
            new_show.id AS new_show_id,
            old_show.name,
            old_show.date
        FROM shows old_show
        LEFT JOIN shows new_show
          ON new_show.club_id = %s
         AND new_show.name = old_show.name
         AND new_show.date = old_show.date
        WHERE old_show.club_id = %s
        """,
        (CANONICAL_ID, DUPLICATE_ID),
    )
    unmatched = _fetch_one(
        cur,
        "SELECT COUNT(*) AS count FROM task_3153_show_map WHERE new_show_id IS NULL",
    )
    if unmatched and unmatched["count"]:
        samples = _fetch_all(
            cur,
            """
            SELECT old_show_id, name, date
            FROM task_3153_show_map
            WHERE new_show_id IS NULL
            ORDER BY date
            LIMIT 5
            """,
        )
        raise RuntimeError(f"{unmatched['count']} duplicate shows lack canonical matches: {samples}")


def _apply_future_routing(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}
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
        (CANONICAL_ID, ALIAS_NAME, ALIAS_NAME, CITY, STATE, CITY, STATE, ALIAS_SOURCE),
    )
    counts["aliases_upserted"] = cur.rowcount

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
                    'task_3153_disposition',
                    'moved disabled duplicate source from club 5297 to club 1036',
                    'task_3153_source_task',
                    %s
                ),
            updated_at = NOW()
        FROM duplicate_sources d
        WHERE ss.id = d.id
        """,
        (CANONICAL_ID, DUPLICATE_ID, CANONICAL_ID, SOURCE_TASK_REF),
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
        JOIN task_3153_show_map m ON m.old_show_id = li.show_id
        ON CONFLICT (show_id, comedian_id) DO NOTHING
        """
    )
    counts["lineup_items_copied"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tagged_shows (show_id, tag_id)
        SELECT m.new_show_id, ts.tag_id
        FROM tagged_shows ts
        JOIN task_3153_show_map m ON m.old_show_id = ts.show_id
        ON CONFLICT (show_id, tag_id) DO NOTHING
        """
    )
    counts["tagged_shows_copied"] = cur.rowcount

    cur.execute(
        """
        INSERT INTO tickets (purchase_url, price, sold_out, show_id, type)
        SELECT t.purchase_url, t.price, t.sold_out, m.new_show_id, t.type
        FROM tickets t
        JOIN task_3153_show_map m ON m.old_show_id = t.show_id
        ON CONFLICT (show_id, type) DO NOTHING
        """
    )
    counts["tickets_copied"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM sent_notifications sn
        USING task_3153_show_map m,
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
        FROM task_3153_show_map m
        WHERE sn.show_id = m.old_show_id
        """
    )
    counts["sent_notifications_repointed"] = cur.rowcount

    cur.execute(
        """
        UPDATE ticket_purchase_click_events tpce
        SET show_id = m.new_show_id,
            club_id = %s
        FROM task_3153_show_map m
        WHERE tpce.show_id = m.old_show_id
        """,
        (CANONICAL_ID,),
    )
    counts["click_events_repointed_to_existing_show"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM shows s
        USING task_3153_show_map m
        WHERE s.id = m.old_show_id
        """
    )
    counts["colliding_duplicate_shows_deleted"] = cur.rowcount

    cur.execute(
        """
        UPDATE ticket_purchase_click_events
        SET club_id = %s
        WHERE club_id = %s
        """,
        (CANONICAL_ID, DUPLICATE_ID),
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
        (CANONICAL_ID, DUPLICATE_ID, CANONICAL_ID),
    )
    counts["favorite_clubs_inserted"] = cur.rowcount

    cur.execute("DELETE FROM favorite_clubs WHERE club_id = %s", (DUPLICATE_ID,))
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
        (CANONICAL_ID, DUPLICATE_ID, CANONICAL_ID),
    )
    counts["production_company_venues_inserted"] = cur.rowcount

    cur.execute("DELETE FROM production_company_venues WHERE club_id = %s", (DUPLICATE_ID,))
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
        (CANONICAL_ID, DUPLICATE_ID, CANONICAL_ID),
    )
    counts["tagged_clubs_inserted"] = cur.rowcount

    cur.execute("DELETE FROM tagged_clubs WHERE club_id = %s", (DUPLICATE_ID,))
    counts["duplicate_tagged_clubs_deleted"] = cur.rowcount

    cur.execute(
        """
        UPDATE email_subscriptions
        SET club_id = %s
        WHERE club_id = %s
        """,
        (CANONICAL_ID, DUPLICATE_ID),
    )
    counts["email_subscriptions_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE processed_emails
        SET club_id = %s
        WHERE club_id = %s
        """,
        (CANONICAL_ID, DUPLICATE_ID),
    )
    counts["processed_emails_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE eventbrite_organizer_venues
        SET club_id = %s
        WHERE club_id = %s
        """,
        (CANONICAL_ID, DUPLICATE_ID),
    )
    counts["eventbrite_organizer_venues_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE club_image_assets
        SET club_id = %s
        WHERE club_id = %s
        """,
        (CANONICAL_ID, DUPLICATE_ID),
    )
    counts["club_image_assets_moved"] = cur.rowcount

    cur.execute(
        """
        UPDATE scraper_run_clubs
        SET club_id = %s,
            club_name = %s
        WHERE club_id = %s
        """,
        (CANONICAL_ID, CANONICAL_NAME, DUPLICATE_ID),
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
        (_closed_name(), DUPLICATE_ID),
    )
    counts["duplicate_clubs_closed"] = cur.rowcount

    cur.execute(
        """
        UPDATE clubs c
        SET total_shows = counts.show_count
        FROM (
            SELECT club_id, COUNT(*) AS show_count
            FROM shows
            WHERE club_id IN (%s, %s)
            GROUP BY club_id
        ) counts
        WHERE c.id = counts.club_id
        """,
        (CANONICAL_ID, DUPLICATE_ID),
    )
    counts["club_totals_recomputed"] = cur.rowcount
    return counts


def _write_recovery_log(payload: dict[str, Any]) -> None:
    RECOVERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECOVERY_LOG_PATH.write_text(
        json.dumps(payload, indent=2, default=_json_default) + "\n",
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

            after = _snapshot(cur)
            payload = {
                "task": f"TASK-{TASK_ID}",
                "source_audit_task": SOURCE_TASK_REF,
                "dry_run": dry_run,
                "applied_at": datetime.now(timezone.utc),
                "fold": {
                    "canonical_id": CANONICAL_ID,
                    "duplicate_id": DUPLICATE_ID,
                    "canonical_name": CANONICAL_NAME,
                    "duplicate_name": DUPLICATE_NAME,
                    "alias": {"alias_name": ALIAS_NAME, "city": CITY, "state": STATE},
                },
                "validation": validation,
                "before": before,
                "counts": counts,
                "after": after,
            }

            if dry_run:
                conn.rollback()
                print(json.dumps(payload, indent=2, default=_json_default))
            else:
                _write_recovery_log(payload)
                print(json.dumps({"wrote": str(RECOVERY_LOG_PATH), "counts": counts}, indent=2))
            return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
