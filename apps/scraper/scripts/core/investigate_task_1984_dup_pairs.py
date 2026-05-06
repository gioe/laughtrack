#!/usr/bin/env python3
"""
Read-only investigation of the 8 same-venue duplicate-club pairs deferred from
TASK-1956. Produces per-pair facts needed to choose the canonical club:
clubs metadata, scraping_sources rows, show counts (total/future/SE/by-source),
(date, room) collision counts between the two clubs, and downstream-FK counts
(production_company_venues, tagged_clubs, email_subscriptions, processed_emails).

Usage
-----
    cd apps/scraper && make run-script SCRIPT=scripts/core/investigate_task_1984_dup_pairs.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction

# (platform, external_id, [club_id_a, club_id_b]) — order from task-1956 audit JSON
_PAIRS = [
    ("seatengine", "21", [132, 1077]),
    ("seatengine", "424", [449, 855]),
    ("seatengine", "428", [453, 567]),
    ("seatengine", "464", [73, 488]),
    ("seatengine", "493", [120, 517]),
    ("seatengine", "508", [125, 532]),
    ("seatengine", "556", [114, 576]),
    ("squadup", "9086799", [175, 571]),
]


def _club_facts(cur, club_id: int) -> dict:
    cur.execute(
        """
        SELECT id, name, address, website, city, state, country, visible, status,
               closed_at, total_shows, popularity
          FROM clubs WHERE id = %s
        """,
        (club_id,),
    )
    row = cur.fetchone()
    if row is None:
        return {"id": club_id, "missing": True}
    cols = [
        "id", "name", "address", "website", "city", "state", "country",
        "visible", "status", "closed_at", "total_shows", "popularity",
    ]
    out = dict(zip(cols, row))
    if isinstance(out.get("closed_at"), datetime):
        out["closed_at"] = out["closed_at"].isoformat()
    return out


def _scraping_sources(cur, club_id: int) -> list[dict]:
    cur.execute(
        """
        SELECT id, club_id, platform::text, scraper_key, priority, enabled, source_url,
               seatengine_id, seatengine_v3_id, eventbrite_id,
               ticketmaster_id, squadup_id, wix_event_id, ovationtix_id,
               metadata, created_at, updated_at
          FROM scraping_sources WHERE club_id = %s ORDER BY priority, id
        """,
        (club_id,),
    )
    rows = cur.fetchall()
    cols = [
        "id", "club_id", "platform", "scraper_key", "priority", "enabled",
        "source_url", "seatengine_id", "seatengine_v3_id",
        "eventbrite_id", "ticketmaster_id", "squadup_id", "wix_event_id",
        "ovationtix_id", "metadata", "created_at", "updated_at",
    ]
    out = []
    for r in rows:
        d = dict(zip(cols, r))
        for k in ("created_at", "updated_at"):
            if isinstance(d.get(k), datetime):
                d[k] = d[k].isoformat()
        if isinstance(d.get("metadata"), str):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except Exception:
                pass
        out.append(d)
    return out


def _show_counts(cur, club_id: int) -> dict:
    cur.execute("SELECT COUNT(*) FROM shows WHERE club_id = %s", (club_id,))
    total = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM shows WHERE club_id = %s AND date >= NOW()",
        (club_id,),
    )
    future = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM shows WHERE club_id = %s AND date < NOW()",
        (club_id,),
    )
    past = cur.fetchone()[0]
    cur.execute(
        """
        SELECT MIN(date), MAX(date)
          FROM shows WHERE club_id = %s
        """,
        (club_id,),
    )
    rng = cur.fetchone()
    cur.execute(
        """
        SELECT COUNT(DISTINCT room)
          FROM shows WHERE club_id = %s AND room IS NOT NULL
        """,
        (club_id,),
    )
    distinct_rooms = cur.fetchone()[0]
    cur.execute(
        """
        SELECT room, COUNT(*) c FROM shows WHERE club_id = %s
         GROUP BY room ORDER BY c DESC LIMIT 10
        """,
        (club_id,),
    )
    rooms = [{"room": r[0], "count": r[1]} for r in cur.fetchall()]
    return {
        "total": total,
        "future": future,
        "past": past,
        "min_date": rng[0].isoformat() if rng[0] else None,
        "max_date": rng[1].isoformat() if rng[1] else None,
        "distinct_rooms": distinct_rooms,
        "top_rooms": rooms,
    }


def _show_source_breakdown(cur, club_id: int) -> list[dict]:
    cur.execute(
        """
        SELECT t.type AS source_platform, COUNT(*) c
          FROM shows s
          LEFT JOIN tickets t ON t.show_id = s.id
         WHERE s.club_id = %s AND s.date >= NOW()
         GROUP BY t.type ORDER BY c DESC
        """,
        (club_id,),
    )
    return [{"platform": r[0], "future_shows": r[1]} for r in cur.fetchall()]


def _collision_count(cur, club_a: int, club_b: int) -> dict:
    cur.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT date, room FROM shows WHERE club_id = %s
            INTERSECT
            SELECT date, room FROM shows WHERE club_id = %s
        ) x
        """,
        (club_a, club_b),
    )
    intersect_total = cur.fetchone()[0]
    cur.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT date, room FROM shows WHERE club_id = %s AND date >= NOW()
            INTERSECT
            SELECT date, room FROM shows WHERE club_id = %s AND date >= NOW()
        ) x
        """,
        (club_a, club_b),
    )
    intersect_future = cur.fetchone()[0]
    return {
        "shared_date_room_total": intersect_total,
        "shared_date_room_future": intersect_future,
    }


def _fk_counts(cur, club_id: int) -> dict:
    out = {}
    for table in (
        "production_company_venues",
        "tagged_clubs",
        "email_subscriptions",
        "processed_emails",
    ):
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE club_id = %s", (club_id,))
        out[table] = cur.fetchone()[0]
    return out


def main() -> int:
    snapshot = {
        "snapshot_taken_at": datetime.now(timezone.utc).isoformat(),
        "pairs": [],
    }
    with get_transaction() as conn:
        with conn.cursor() as cur:
            for platform, ext, members in _PAIRS:
                pair = {
                    "platform": platform,
                    "external_id": ext,
                    "club_ids": members,
                    "members": [],
                }
                for cid in members:
                    pair["members"].append({
                        "club": _club_facts(cur, cid),
                        "scraping_sources": _scraping_sources(cur, cid),
                        "show_counts": _show_counts(cur, cid),
                        "show_source_breakdown": _show_source_breakdown(cur, cid),
                        "fk_counts": _fk_counts(cur, cid),
                    })
                pair["collisions"] = _collision_count(cur, members[0], members[1])
                snapshot["pairs"].append(pair)
    print(json.dumps(snapshot, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
