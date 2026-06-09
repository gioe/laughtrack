#!/usr/bin/env python3
"""Backfill stale Your Mom's House historical episode release dates.

PodcastIndex and the current RSS feed both expose only the republished 2016 date
for the affected old YMH rows. Archived FeedBurner snapshots still include the
original Libsyn pubDates, so this script uses those snapshots as the source of
truth for the narrow podcast_id=5407/date cluster.
"""

from __future__ import annotations

import argparse
import calendar
import json
import ssl
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import urllib.request
from urllib.parse import urlencode

import feedparser

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.core.rss_episode_reader import _episode_number_prefix, _normalize_title

_PODCAST_ID = 5407
_BAD_RELEASE_DATE = "2016-10-17"
_NORMALIZED_TITLE = "your mom's house with christina pazsitzky and tom segura"
_FEED_URL = "http://feeds.feedburner.com/YourMomsHouseWithChristinaPazsitzkyAndTomSegura"
_CDX_URL = "https://web.archive.org/cdx"
_WAYBACK_FETCH_TIMEOUT = 45
_SSL_CONTEXT = ssl.create_default_context()
_SSL_CONTEXT.check_hostname = False
_SSL_CONTEXT.verify_mode = ssl.CERT_NONE

_LOAD_AFFECTED_ROWS_SQL = """
    SELECT id, title, release_date, guid, audio_url
    FROM podcast_episodes
    WHERE podcast_id = %s
      AND release_date::date = %s::date
      AND LOWER(REGEXP_REPLACE(BTRIM(title), '^\\s*(?:(?:ep(?:isode)?|#)\\s*[0-9]+(?:\\s*[:.\\-\\)\\]]|\\s+)\\s*|[0-9]+\\s*[:.\\-\\)\\]]\\s*)', '', 'i')) = %s
    ORDER BY id
"""

_UPDATE_RELEASE_DATE_SQL = """
    UPDATE podcast_episodes
    SET release_date = %s::timestamptz,
        evidence = COALESCE(evidence, '{}'::jsonb) || %s::jsonb,
        updated_at = NOW()
    WHERE id = %s
"""


@dataclass(frozen=True)
class AffectedEpisode:
    row_id: int
    title: str
    episode_number: int
    release_date: str
    guid: Optional[str]
    audio_url: Optional[str]


@dataclass(frozen=True)
class ArchivedEpisodeDate:
    episode_number: int
    title: str
    release_date: str
    snapshot_timestamp: str


@dataclass(frozen=True)
class BackfillPlan:
    affected: list[AffectedEpisode]
    matches: dict[int, ArchivedEpisodeDate]

    @property
    def matched_rows(self) -> list[AffectedEpisode]:
        return [episode for episode in self.affected if episode.episode_number in self.matches]

    @property
    def missing_rows(self) -> list[AffectedEpisode]:
        return [episode for episode in self.affected if episode.episode_number not in self.matches]


def _iso_from_struct_time(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(
            calendar.timegm(value),
            tz=timezone.utc,
        ).isoformat()
    except Exception:
        return None


def _load_affected_rows(conn: Any) -> list[AffectedEpisode]:
    with conn.cursor() as cur:
        cur.execute(_LOAD_AFFECTED_ROWS_SQL, (_PODCAST_ID, _BAD_RELEASE_DATE, _NORMALIZED_TITLE))
        rows = cur.fetchall()

    affected: list[AffectedEpisode] = []
    for row in rows:
        episode_number = _episode_number_prefix(row[1])
        if episode_number is None:
            continue
        affected.append(
            AffectedEpisode(
                row_id=int(row[0]),
                title=str(row[1]),
                episode_number=episode_number,
                release_date=row[2].isoformat() if hasattr(row[2], "isoformat") else str(row[2]),
                guid=row[3],
                audio_url=row[4],
            )
        )
    return affected


def _fetch_cdx_snapshots() -> list[str]:
    query = urlencode(
        {
            "url": _FEED_URL.replace("http://", ""),
            "output": "json",
            "fl": "timestamp,statuscode,mimetype,digest",
            "filter": "statuscode:200",
            "collapse": "digest",
        },
        safe="/:,",
    )
    with urllib.request.urlopen(f"{_CDX_URL}?{query}", timeout=_WAYBACK_FETCH_TIMEOUT, context=_SSL_CONTEXT) as response:
        rows = json.loads(response.read())
    if not isinstance(rows, list) or len(rows) <= 1:
        return []
    return [str(row[0]) for row in rows[1:] if isinstance(row, list) and row]


def _fetch_archived_feed(timestamp: str) -> bytes:
    url = f"https://web.archive.org/web/{timestamp}if_/{_FEED_URL}"
    with urllib.request.urlopen(url, timeout=_WAYBACK_FETCH_TIMEOUT, context=_SSL_CONTEXT) as response:
        return response.read()


def _archive_dates_from_feed(content: bytes, timestamp: str, wanted_numbers: set[int]) -> dict[int, ArchivedEpisodeDate]:
    parsed = feedparser.parse(content)
    dates: dict[int, ArchivedEpisodeDate] = {}
    for entry in parsed.get("entries") or []:
        title = str(entry.get("title") or "")
        episode_number = _episode_number_prefix(title)
        if episode_number not in wanted_numbers or episode_number in dates:
            continue
        if _normalize_title(title) != _NORMALIZED_TITLE:
            continue
        release_date = _iso_from_struct_time(entry.get("published_parsed") or entry.get("updated_parsed"))
        if not release_date:
            continue
        dates[episode_number] = ArchivedEpisodeDate(
            episode_number=episode_number,
            title=title,
            release_date=release_date,
            snapshot_timestamp=timestamp,
        )
    return dates


def build_plan(conn: Any) -> BackfillPlan:
    affected = _load_affected_rows(conn)
    wanted_numbers = {episode.episode_number for episode in affected}
    matches: dict[int, ArchivedEpisodeDate] = {}
    for timestamp in _fetch_cdx_snapshots():
        remaining = wanted_numbers - set(matches)
        if not remaining:
            break
        matches.update(_archive_dates_from_feed(_fetch_archived_feed(timestamp), timestamp, remaining))
    return BackfillPlan(affected=affected, matches=matches)


def apply_plan(conn: Any, plan: BackfillPlan) -> int:
    updated = 0
    with conn.cursor() as cur:
        for episode in plan.matched_rows:
            match = plan.matches[episode.episode_number]
            evidence = {
                "ymh_wayback_release_date_backfill": {
                    "snapshot_timestamp": match.snapshot_timestamp,
                    "archived_title": match.title,
                }
            }
            cur.execute(_UPDATE_RELEASE_DATE_SQL, (match.release_date, json.dumps(evidence, sort_keys=True), episode.row_id))
            updated += cur.rowcount
    return updated


def _print_plan(plan: BackfillPlan, *, updated: Optional[int] = None) -> None:
    print(
        f"YMH Wayback plan: {len(plan.affected)} affected rows, "
        f"{len(plan.matched_rows)} matched archived dates, {len(plan.missing_rows)} missing"
    )
    if updated is not None:
        print(f"Updated rows: {updated}")
    for episode in plan.missing_rows:
        print(f"  missing: id={episode.row_id} episode={episode.episode_number} title={episode.title}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill YMH old episode release dates from Wayback RSS snapshots")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)

    with get_connection(autocommit=False) as conn:
        plan = build_plan(conn)
        if args.dry_run:
            conn.rollback()
            _print_plan(plan)
            return 0
        updated = apply_plan(conn, plan)
        conn.commit()
        _print_plan(plan, updated=updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
