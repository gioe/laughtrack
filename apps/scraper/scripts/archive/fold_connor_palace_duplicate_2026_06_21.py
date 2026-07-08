#!/usr/bin/env python3
"""
Fold club 9612 "Connor Palace - Cleveland" into canonical club 5058.

The Ticketmaster national scraper created a duplicate Connor Palace row after
the Playhouse Square venue-specific onboarding had already established club 5058
as canonical. This script:

  1. Adds a verified club_alias so future "Connor Palace - Cleveland" upserts
     resolve to club 5058.
  2. Copies child rows from colliding duplicate shows to the canonical show.
  3. Moves non-colliding shows to club 5058.
  4. Preserves sent-notification/click history by repointing references before
     deleting colliding duplicate show rows.
  5. Disables duplicate club sources and hides/closes club 9612.

Usage:
    cd apps/scraper
    make run-script SCRIPT=scripts/core/fold_connor_palace_duplicate_2026_06_21.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/fold_connor_palace_duplicate_2026_06_21.py
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


CANONICAL_CLUB_ID = 5058
DUPLICATE_CLUB_ID = 9612
CANONICAL_NAME = "Connor Palace at Playhouse Square"
DUPLICATE_NAME = "Connor Palace - Cleveland"
DUPLICATE_CLOSED_NAME = f"{DUPLICATE_NAME} (duplicate of club {CANONICAL_CLUB_ID}; folded from club {DUPLICATE_CLUB_ID})"
ALIAS_SOURCE = "TASK-3043"
RECOVERY_LOG_PATH = _root / "docs" / "audits" / "task-3043-connor-palace-duplicate-fold.json"


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


def _validate(cur: RealDictCursor) -> tuple[dict[str, Any], dict[str, Any]]:
    canonical = _fetch_one(
        cur,
        """
        SELECT id, name, city, state, visible, status, total_shows
        FROM clubs
        WHERE id = %s
        FOR UPDATE
        """,
        (CANONICAL_CLUB_ID,),
    )
    duplicate = _fetch_one(
        cur,
        """
        SELECT id, name, city, state, visible, status, total_shows
        FROM clubs
        WHERE id = %s
        FOR UPDATE
        """,
        (DUPLICATE_CLUB_ID,),
    )
    problems = []
    if canonical is None:
        problems.append(f"canonical club {CANONICAL_CLUB_ID} not found")
    elif canonical["name"] != CANONICAL_NAME:
        problems.append(f"club {CANONICAL_CLUB_ID} name is {canonical['name']!r}, expected {CANONICAL_NAME!r}")
    if duplicate is None:
        problems.append(f"duplicate club {DUPLICATE_CLUB_ID} not found")
    elif duplicate["name"] not in {
        DUPLICATE_NAME,
        DUPLICATE_CLOSED_NAME,
    }:
        problems.append(f"club {DUPLICATE_CLUB_ID} name is {duplicate['name']!r}, expected {DUPLICATE_NAME!r}")
    if problems:
        raise RuntimeError("; ".join(problems))
    return canonical, duplicate


def _already_folded(duplicate: dict[str, Any]) -> bool:
    return (not duplicate["visible"]) and duplicate.get("status") == "closed"


def _snapshot(cur: RealDictCursor) -> dict[str, Any]:
    return {
        "clubs": _fetch_all(
            cur,
            """
            SELECT id, name, city, state, visible, status, total_shows
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
            WHERE club_id IN (%s, %s)
            ORDER BY club_id, priority, id
            """,
            (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
        ),
        "duplicate_shows": _fetch_all(
            cur,
            """
            SELECT s_dup.id AS duplicate_show_id,
                   s_dup.name AS duplicate_name,
                   s_dup.date,
                   s_dup.room,
                   s_can.id AS canonical_show_id
            FROM shows s_dup
            LEFT JOIN shows s_can
              ON s_can.club_id = %s
             AND s_can.date = s_dup.date
             AND s_can.room IS NOT DISTINCT FROM s_dup.room
            WHERE s_dup.club_id = %s
            ORDER BY s_dup.date, s_dup.id
            """,
            (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
        ),
        "alias": _fetch_all(
            cur,
            """
            SELECT id, club_id, alias_name, normalized_alias_name, city, state,
                   normalized_city, normalized_state, source, verified
            FROM club_aliases
            WHERE normalized_alias_name = 'connor palace cleveland'
              AND normalized_city = 'cleveland'
              AND normalized_state = 'oh'
            ORDER BY id
            """,
        ),
    }


def _apply(cur: RealDictCursor) -> dict[str, int]:
    counts: dict[str, int] = {}

    counts.update(_ensure_future_routing(cur))

    cur.execute(
        """
        CREATE TEMP TABLE task_3043_duplicate_show_map AS
        SELECT
            s_dup.id AS old_show_id,
            s_can.id AS new_show_id
        FROM shows s_dup
        LEFT JOIN shows s_can
          ON s_can.club_id = %s
         AND s_can.date = s_dup.date
         AND s_can.room IS NOT DISTINCT FROM s_dup.room
        WHERE s_dup.club_id = %s
        """,
        (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID),
    )

    cur.execute(
        """
        INSERT INTO lineup_items (show_id, comedian_id, role)
        SELECT m.new_show_id, li.comedian_id, li.role
        FROM lineup_items li
        JOIN task_3043_duplicate_show_map m ON m.old_show_id = li.show_id
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
        JOIN task_3043_duplicate_show_map m ON m.old_show_id = ts.show_id
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
        JOIN task_3043_duplicate_show_map m ON m.old_show_id = t.show_id
        WHERE m.new_show_id IS NOT NULL
        ON CONFLICT (show_id, type) DO NOTHING
        """
    )
    counts["tickets_copied"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM sent_notifications sn
        USING task_3043_duplicate_show_map m,
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
        FROM task_3043_duplicate_show_map m
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
        FROM task_3043_duplicate_show_map m
        WHERE m.new_show_id IS NOT NULL
          AND tpce.show_id = m.old_show_id
        """,
        (CANONICAL_CLUB_ID,),
    )
    counts["click_events_repointed_to_existing_show"] = cur.rowcount

    cur.execute(
        """
        DELETE FROM shows s
        USING task_3043_duplicate_show_map m
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

    cur.execute(
        """
        UPDATE favorite_clubs f
        SET club_id = %s
        WHERE f.club_id = %s
          AND NOT EXISTS (
              SELECT 1 FROM favorite_clubs f2
              WHERE f2.club_id = %s AND f2.profile_id = f.profile_id
          )
        """,
        (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID, CANONICAL_CLUB_ID),
    )
    counts["favorites_moved"] = cur.rowcount

    cur.execute("DELETE FROM favorite_clubs WHERE club_id = %s", (DUPLICATE_CLUB_ID,))
    counts["duplicate_favorites_deleted"] = cur.rowcount

    cur.execute(
        """
        UPDATE clubs
        SET name = %s,
            visible = false,
            status = 'closed',
            closed_at = COALESCE(closed_at, NOW())
        WHERE id = %s
        """,
        (DUPLICATE_CLOSED_NAME, DUPLICATE_CLUB_ID),
    )
    counts["duplicate_club_closed"] = cur.rowcount

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


def _ensure_future_routing(cur: RealDictCursor) -> dict[str, int]:
    """Ensure future Ticketmaster national discoveries resolve to club 5058."""
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
            'connor palace cleveland',
            'Cleveland',
            'OH',
            'cleveland',
            'oh',
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
        (CANONICAL_CLUB_ID, DUPLICATE_NAME, ALIAS_SOURCE),
    )
    counts["aliases_upserted"] = cur.rowcount

    cur.execute(
        """
        UPDATE scraping_sources ss
        SET club_id = %s,
            enabled = false,
            metadata = COALESCE(metadata, '{}'::jsonb)
                || jsonb_build_object(
                    'task_3043_disposition',
                    'moved disabled duplicate Connor Palace source from club 9612 to club 5058'
                ),
            updated_at = NOW()
        WHERE ss.club_id = %s
          AND NOT EXISTS (
              SELECT 1
              FROM scraping_sources existing
              WHERE existing.club_id = %s
                AND existing.platform = ss.platform
                AND existing.priority = ss.priority
                AND existing.id <> ss.id
          )
        """,
        (CANONICAL_CLUB_ID, DUPLICATE_CLUB_ID, CANONICAL_CLUB_ID),
    )
    counts["duplicate_sources_moved_to_canonical"] = cur.rowcount

    cur.execute(
        """
        UPDATE scraping_sources
        SET enabled = false,
            metadata = COALESCE(metadata, '{}'::jsonb)
                || jsonb_build_object(
                    'task_3043_disposition',
                    'disabled duplicate Connor Palace source after folding club 9612 into club 5058'
                ),
            updated_at = NOW()
        WHERE club_id = %s
        """,
        (DUPLICATE_CLUB_ID,),
    )
    counts["remaining_duplicate_sources_disabled"] = cur.rowcount

    cur.execute(
        """
        UPDATE scraping_sources
        SET metadata = COALESCE(metadata, '{}'::jsonb)
                || jsonb_build_object(
                    'task_3043_note',
                    'Connor Palace duplicate club 9612 folded into 5058; alternate Ticketmaster ids route here'
                ),
            updated_at = NOW()
        WHERE club_id = %s
          AND platform = 'ticketmaster'
        """,
        (CANONICAL_CLUB_ID,),
    )
    counts["canonical_ticketmaster_sources_annotated"] = cur.rowcount
    return counts


def run(dry_run: bool) -> dict[str, Any]:
    log: dict[str, Any] = {
        "task_id": 3043,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
    }
    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            canonical, duplicate = _validate(cur)
            log["canonical_before"] = canonical
            log["duplicate_before"] = duplicate
            log["before"] = _snapshot(cur)
            if _already_folded(duplicate):
                log["counts"] = _ensure_future_routing(cur)
                log["skipped_show_fold"] = "duplicate already hidden + closed"
                log["after"] = _snapshot(cur)
            else:
                log["counts"] = _apply(cur)
                log["after"] = _snapshot(cur)

            if dry_run:
                conn.rollback()
            else:
                RECOVERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                RECOVERY_LOG_PATH.write_text(
                    json.dumps(log, indent=2, sort_keys=True, default=_json_default) + "\n",
                    encoding="utf-8",
                )
    return log


def main() -> int:
    parser = argparse.ArgumentParser(description="Fold Connor Palace duplicate club 9612 into canonical club 5058.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log = run(dry_run=args.dry_run)
    print(json.dumps(log, indent=2, sort_keys=True, default=_json_default))
    if args.dry_run:
        print("DRY RUN: no database rows were changed and no recovery log was written.")
    else:
        print(f"Wrote recovery log: {RECOVERY_LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
