#!/usr/bin/env python3
"""Sync podcast episodes directly from Podcast.feed_url RSS feeds."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.core import rss_episode_reader as reader
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class DriverSummary:
    podcasts_scanned: int = 0
    podcasts_failed: int = 0
    episodes_seen: int = 0
    episodes_inserted: int = 0
    episodes_updated: int = 0
    episodes_unchanged: int = 0
    episodes_skipped: int = 0
    not_modified: int = 0
    per_podcast_errors: list[str] = field(default_factory=list)


_LOAD_PODCASTS_SQL = """
    SELECT id, source, source_podcast_id, feed_url, title, source_payload
    FROM podcasts
    WHERE feed_url IS NOT NULL
      AND (%s::text IS NULL OR source = %s)
      AND (%s::int[] IS NULL OR id = ANY(%s::int[]))
    ORDER BY last_synced_at ASC NULLS FIRST, id ASC
    {limit_clause}
"""

_COUNT_EPISODES_SQL = "SELECT COUNT(*) FROM podcast_episodes"
_BUMP_LAST_SYNCED_SQL = "UPDATE podcasts SET last_synced_at = NOW(), updated_at = NOW() WHERE id = %s"


def load_podcasts(
    conn: Any, *, source: Optional[str], podcast_ids: Optional[list[int]], limit: Optional[int]
) -> list[reader.PodcastRssFeed]:
    limit_clause = "LIMIT %s" if limit else ""
    query = _LOAD_PODCASTS_SQL.format(limit_clause=limit_clause)
    params: list[Any] = [source, source, podcast_ids, podcast_ids]
    if limit:
        params.append(int(limit))
    with conn.cursor() as cur:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
    return [
        reader.PodcastRssFeed(
            podcast_id=int(row[0]),
            source=str(row[1]),
            source_podcast_id=str(row[2]),
            feed_url=row[3],
            title=str(row[4]),
            source_payload=row[5] if isinstance(row[5], dict) else {},
        )
        for row in rows
    ]


def _episode_count(conn: Any) -> int:
    with conn.cursor() as cur:
        cur.execute(_COUNT_EPISODES_SQL)
        row = cur.fetchone()
    return int(row[0] if row else 0)


def _bump_last_synced(conn: Any, podcast_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(_BUMP_LAST_SYNCED_SQL, (podcast_id,))


def sync_podcasts_from_rss(
    *,
    dry_run: bool,
    limit: Optional[int],
    source: Optional[str],
    podcast_ids: Optional[list[int]] = None,
) -> DriverSummary:
    summary = DriverSummary()
    with get_connection(autocommit=False) as conn:
        try:
            before_count = _episode_count(conn)
            print("=== BEFORE ===")
            print(f"PodcastEpisode rows: {before_count}")

            podcasts = load_podcasts(conn, source=source, podcast_ids=podcast_ids, limit=limit)
            print(f"Podcasts selected: {len(podcasts)}")

            for podcast in podcasts:
                summary.podcasts_scanned += 1
                try:
                    podcast_summary = reader.sync_podcast_episodes_from_rss(conn, podcast, dry_run=dry_run)
                except Exception as exc:
                    summary.podcasts_failed += 1
                    message = f"podcast {podcast.podcast_id} ({podcast.title}): {exc}"
                    summary.per_podcast_errors.append(message)
                    Logger.warn(f"[rss-episode-reader] sync failed for {message}")
                    continue

                summary.episodes_seen += podcast_summary.episodes_seen
                summary.episodes_inserted += podcast_summary.episodes_inserted
                summary.episodes_updated += podcast_summary.episodes_updated
                summary.episodes_unchanged += podcast_summary.episodes_unchanged
                summary.episodes_skipped += podcast_summary.episodes_skipped
                if podcast_summary.not_modified:
                    summary.not_modified += 1
                if not dry_run:
                    _bump_last_synced(conn, podcast.podcast_id)

            print("=== AFTER ===")
            if dry_run:
                print("DRY RUN: no database writes applied")
                print(f"PodcastEpisode rows: {before_count}")
                conn.rollback()
            else:
                conn.commit()
                print(f"PodcastEpisode rows: {_episode_count(conn)}")
        except Exception:
            conn.rollback()
            raise

    return summary


def _print_report(summary: DriverSummary, *, dry_run: bool) -> None:
    prefix = "DRY RUN - " if dry_run else ""
    print(
        f"{prefix}Summary: {summary.podcasts_scanned} podcasts scanned, "
        f"{summary.episodes_seen} episodes seen, "
        f"{summary.episodes_inserted} inserted, "
        f"{summary.episodes_updated} updated, "
        f"{summary.episodes_unchanged} unchanged, "
        f"{summary.episodes_skipped} skipped, "
        f"{summary.not_modified} not modified, "
        f"{summary.podcasts_failed} failures"
    )
    for error in summary.per_podcast_errors:
        print(f"  error: {error}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync podcast episodes directly from source-agnostic RSS feed URLs",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Fetch and report without writing")
    mode.add_argument("--confirm", action="store_true", help="Write podcast_episodes rows")
    parser.add_argument("--limit", type=int, default=None, help="Max podcasts to scan")
    parser.add_argument("--source", default=None, help="Optional parent podcast source filter")
    parser.add_argument("--podcast-id", dest="podcast_ids", type=int, action="append", default=None)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.dry_run == args.confirm:
        parser.error("choose exactly one of --dry-run or --confirm")

    summary = sync_podcasts_from_rss(
        dry_run=args.dry_run,
        limit=args.limit,
        source=args.source,
        podcast_ids=args.podcast_ids,
    )
    _print_report(summary, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
