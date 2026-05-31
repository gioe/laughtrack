#!/usr/bin/env python3
"""Sync podcast episodes directly from Podcast.feed_url RSS feeds."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import psycopg2

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
    podcasts_skipped_unreachable: int = 0
    per_podcast_errors: list[str] = field(default_factory=list)


_LOAD_PODCASTS_SQL = """
    SELECT id, source, source_podcast_id, feed_url, title, source_payload
    FROM podcasts
    WHERE feed_url IS NOT NULL
      AND (%s::text IS NULL OR source = %s)
      AND (%s::int[] IS NULL OR id = ANY(%s::int[]))
      AND {reachable}
    ORDER BY last_synced_at ASC NULLS FIRST, id ASC
    {limit_clause}
"""

# Counts feeds excluded by the reachability cooldown (benched), respecting the
# same source / podcast-id filters, so the run report can surface how many dead
# feeds were skipped.
_COUNT_UNREACHABLE_SQL = """
    SELECT COUNT(*)
    FROM podcasts
    WHERE feed_url IS NOT NULL
      AND (%s::text IS NULL OR source = %s)
      AND (%s::int[] IS NULL OR id = ANY(%s::int[]))
      AND NOT {reachable}
"""

_COUNT_EPISODES_SQL = "SELECT COUNT(*) FROM podcast_episodes"
_BUMP_LAST_SYNCED_SQL = "UPDATE podcasts SET last_synced_at = NOW(), updated_at = NOW() WHERE id = %s"


def load_podcasts(
    conn: Any, *, source: Optional[str], podcast_ids: Optional[list[int]], limit: Optional[int]
) -> list[reader.PodcastRssFeed]:
    limit_clause = "LIMIT %s" if limit else ""
    reachable_clause, reachable_params = reader.reachable_feed_clause()
    query = _LOAD_PODCASTS_SQL.format(reachable=reachable_clause, limit_clause=limit_clause)
    params: list[Any] = [source, source, podcast_ids, podcast_ids, *reachable_params]
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


def _count_unreachable(conn: Any, *, source: Optional[str], podcast_ids: Optional[list[int]]) -> int:
    reachable_clause, reachable_params = reader.reachable_feed_clause()
    query = _COUNT_UNREACHABLE_SQL.format(reachable=reachable_clause)
    params: list[Any] = [source, source, podcast_ids, podcast_ids, *reachable_params]
    with conn.cursor() as cur:
        cur.execute(query, tuple(params))
        row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _bump_last_synced(conn: Any, podcast_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(_BUMP_LAST_SYNCED_SQL, (podcast_id,))


def _rollback_safely(conn: Any) -> None:
    if getattr(conn, "closed", False):
        Logger.warn("[rss-episode-reader] skipping rollback because database connection is already closed")
        return
    try:
        conn.rollback()
    except (psycopg2.InterfaceError, psycopg2.OperationalError) as exc:
        Logger.warn(f"[rss-episode-reader] rollback failed after database connection error: {exc}")


def _load_sync_inputs(
    *, source: Optional[str], podcast_ids: Optional[list[int]], limit: Optional[int]
) -> tuple[int, list[reader.PodcastRssFeed], int]:
    with get_connection() as conn:
        before_count = _episode_count(conn)
        podcasts = load_podcasts(conn, source=source, podcast_ids=podcast_ids, limit=limit)
        skipped_unreachable = _count_unreachable(conn, source=source, podcast_ids=podcast_ids)
    return before_count, podcasts, skipped_unreachable


def _record_unreachable(podcast: reader.PodcastRssFeed) -> None:
    """Persist a feed's failed-fetch outcome on its own short transaction.

    The fetch in ``_sync_one_podcast`` raises before any DB connection is opened,
    so the failure is recorded here. Wrapped defensively: a bookkeeping write
    must never abort the sync run.
    """
    try:
        with get_connection(autocommit=False) as conn:
            try:
                reader.record_fetch_failure(conn, podcast)
                conn.commit()
            except Exception:
                _rollback_safely(conn)
                raise
    except Exception as exc:
        Logger.warn(
            f"[rss-episode-reader] could not record unreachable state for podcast {podcast.podcast_id}: {exc}"
        )


def _sync_one_podcast(podcast: reader.PodcastRssFeed, *, dry_run: bool) -> reader.RssSyncSummary:
    fetched = reader.fetch_rss_episodes(podcast)
    with get_connection(autocommit=False) as conn:
        try:
            podcast_summary = reader.persist_rss_fetch_result(conn, podcast, fetched, dry_run=dry_run)
            if not dry_run:
                _bump_last_synced(conn, podcast.podcast_id)

            if dry_run:
                conn.rollback()
            else:
                conn.commit()
        except Exception:
            _rollback_safely(conn)
            raise
    return podcast_summary


def sync_podcasts_from_rss(
    *,
    dry_run: bool,
    limit: Optional[int],
    source: Optional[str],
    podcast_ids: Optional[list[int]] = None,
) -> DriverSummary:
    summary = DriverSummary()
    before_count, podcasts, skipped_unreachable = _load_sync_inputs(
        source=source, podcast_ids=podcast_ids, limit=limit
    )
    summary.podcasts_skipped_unreachable = skipped_unreachable
    print("=== BEFORE ===")
    print(f"PodcastEpisode rows: {before_count}")
    print(f"Podcasts selected: {len(podcasts)}")
    print(f"Podcasts skipped (unreachable, in cooldown): {skipped_unreachable}")

    for podcast in podcasts:
        summary.podcasts_scanned += 1
        try:
            podcast_summary = _sync_one_podcast(podcast, dry_run=dry_run)
        except Exception as exc:
            summary.podcasts_failed += 1
            message = f"podcast {podcast.podcast_id} ({podcast.title}): {exc}"
            summary.per_podcast_errors.append(message)
            Logger.warn(f"[rss-episode-reader] sync failed for {message}")
            if not dry_run:
                _record_unreachable(podcast)
            continue

        summary.episodes_seen += podcast_summary.episodes_seen
        summary.episodes_inserted += podcast_summary.episodes_inserted
        summary.episodes_updated += podcast_summary.episodes_updated
        summary.episodes_unchanged += podcast_summary.episodes_unchanged
        summary.episodes_skipped += podcast_summary.episodes_skipped
        if podcast_summary.not_modified:
            summary.not_modified += 1

    print("=== AFTER ===")
    if dry_run:
        print("DRY RUN: no database writes applied")
        print(f"PodcastEpisode rows: {before_count}")
    else:
        with get_connection() as conn:
            print(f"PodcastEpisode rows: {_episode_count(conn)}")

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
        f"{summary.podcasts_failed} failures, "
        f"{summary.podcasts_skipped_unreachable} skipped unreachable"
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
