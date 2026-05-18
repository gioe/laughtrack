#!/usr/bin/env python3
"""Observe accepted podcast RSS feeds for incremental episode ingestion."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger
from scripts.core import backfill_podcast_episodes as episode_mod
from scripts.core import detect_podcast_episode_appearances as detect_mod


@dataclass
class ObserveSummary:
    feeds_scanned: int = 0
    episodes_seen: int = 0
    episodes_inserted: int = 0
    episodes_updated: int = 0
    episodes_unchanged: int = 0
    episodes_skipped: int = 0
    api_failures: int = 0
    detector_episode_ids: list[int] = field(default_factory=list)
    detection_candidates: int = 0
    detection_auto_accepted: int = 0
    detection_pending: int = 0
    detection_ignored: int = 0
    detection_written: int = 0
    per_feed_errors: list[str] = field(default_factory=list)

    @property
    def episodes_changed(self) -> int:
        return self.episodes_inserted + self.episodes_updated


def _load_latest_release_date(conn: Any, podcast_id: int) -> Optional[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT MAX(release_date)
            FROM podcast_episodes
            WHERE podcast_id = %s
              AND source = %s
            """,
            (podcast_id, episode_mod._SOURCE),
        )
        row = cur.fetchone()
    if not row or row[0] is None:
        return None
    value = row[0]
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return str(value)


def _detect_new_episode_appearances(
    conn: Any,
    episode_ids: list[int],
    include_aliases: bool,
) -> detect_mod.DetectSummary:
    if not episode_ids:
        return detect_mod.DetectSummary()
    comedians = detect_mod.load_match_comedians_from_conn(
        conn,
        comedian_ids=None,
        comedian_names=None,
        limit=None,
    )
    episodes = detect_mod.load_episode_inputs_from_conn(conn, episode_ids=episode_ids, limit=None)
    candidates = detect_mod.detect_episode_candidates(
        comedians,
        episodes,
        include_aliases=include_aliases,
        auto_accept=True,
    )
    return detect_mod.persist_candidates_with_conn(conn, candidates, dry_run=False)


def _finish_transaction(conn: Any, *, dry_run: bool) -> None:
    if dry_run and hasattr(conn, "rollback"):
        conn.rollback()
    elif hasattr(conn, "commit"):
        conn.commit()


def observe_podcast_rss_feeds(
    *,
    dry_run: bool,
    feed_ids: Optional[list[str]],
    comedian_ids: Optional[list[int]],
    comedian_names: Optional[list[str]],
    limit: Optional[int],
    max_episodes_per_feed: int,
    include_aliases: bool,
) -> ObserveSummary:
    credentials = episode_mod._load_podcast_index_credentials()
    feeds = episode_mod.load_accepted_feeds(
        feed_ids=feed_ids,
        comedian_ids=comedian_ids,
        comedian_names=comedian_names,
        limit=limit,
    )
    summary = ObserveSummary()

    with get_connection(autocommit=False) as conn:
        try:
            changed_episode_ids: list[int] = []
            seen_changed_episode_ids: set[int] = set()
            for feed in feeds:
                summary.feeds_scanned += 1
                since = _load_latest_release_date(conn, feed.podcast_id)
                params = episode_mod._build_fetch_params(
                    feed,
                    max_episodes_per_feed=max_episodes_per_feed,
                    since=since,
                )
                try:
                    raw_episodes = episode_mod.fetch_feed_episodes(feed, credentials, params)
                except Exception as exc:
                    summary.api_failures += 1
                    message = f"feed {feed.source_podcast_id} ({feed.title}): {exc}"
                    summary.per_feed_errors.append(message)
                    Logger.warn(f"[podcast-rss-observer] fetch failed for {message}")
                    continue

                for raw_episode in raw_episodes:
                    summary.episodes_seen += 1
                    episode = episode_mod.episode_from_payload(
                        podcast_id=feed.podcast_id,
                        source_podcast_id=feed.source_podcast_id,
                        episode=raw_episode,
                    )
                    if episode is None:
                        summary.episodes_skipped += 1
                        continue
                    if dry_run:
                        continue

                    result = episode_mod.upsert_episode_with_result(conn, episode)
                    if result.inserted:
                        summary.episodes_inserted += 1
                    elif result.changed:
                        summary.episodes_updated += 1
                    else:
                        summary.episodes_unchanged += 1

                    if result.changed and result.episode_id is not None:
                        if result.episode_id not in seen_changed_episode_ids:
                            seen_changed_episode_ids.add(result.episode_id)
                            changed_episode_ids.append(result.episode_id)

            summary.detector_episode_ids = changed_episode_ids
            if changed_episode_ids:
                detect_summary = _detect_new_episode_appearances(
                    conn,
                    changed_episode_ids,
                    include_aliases,
                )
                summary.detection_candidates = detect_summary.candidates
                summary.detection_auto_accepted = detect_summary.auto_accepted
                summary.detection_pending = detect_summary.pending
                summary.detection_ignored = detect_summary.ignored
                summary.detection_written = detect_summary.written

            _finish_transaction(conn, dry_run=dry_run)
        except Exception:
            if hasattr(conn, "rollback"):
                conn.rollback()
            raise

    return summary


def _print_report(summary: ObserveSummary, *, dry_run: bool) -> None:
    prefix = "DRY RUN - " if dry_run else ""
    print(
        f"{prefix}Summary: {summary.feeds_scanned} feeds scanned, "
        f"{summary.episodes_seen} episodes seen, "
        f"{summary.episodes_inserted} inserted, "
        f"{summary.episodes_updated} updated, "
        f"{summary.episodes_unchanged} unchanged, "
        f"{summary.episodes_skipped} skipped, "
        f"{summary.api_failures} API failures"
    )
    print(
        "Detection: "
        f"{len(summary.detector_episode_ids)} episode IDs scoped, "
        f"{summary.detection_candidates} candidates, "
        f"{summary.detection_auto_accepted} auto-accepted, "
        f"{summary.detection_pending} pending, "
        f"{summary.detection_ignored} ignored, "
        f"{summary.detection_written} written"
    )
    for error in summary.per_feed_errors:
        print(f"  error: {error}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Observe accepted podcast RSS feeds and detect appearances in new episodes",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Fetch and report without writing")
    mode.add_argument("--confirm", action="store_true", help="Write changed episodes and detections")
    parser.add_argument("--feed-id", dest="feed_ids", action="append", default=None)
    parser.add_argument(
        "--comedian-id",
        dest="comedian_ids",
        type=int,
        action="append",
        default=None,
    )
    parser.add_argument("--comedian-name", dest="comedian_names", action="append", default=None)
    parser.add_argument("--limit", type=int, default=None, help="Max accepted feeds to poll")
    parser.add_argument(
        "--max-episodes-per-feed",
        type=int,
        default=episode_mod._DEFAULT_MAX_EPISODES_PER_FEED,
        help="Max episodes requested from PodcastIndex per feed",
    )
    parser.add_argument("--no-aliases", action="store_true")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.dry_run == args.confirm:
        parser.error("choose exactly one of --dry-run or --confirm")
    summary = observe_podcast_rss_feeds(
        dry_run=args.dry_run,
        feed_ids=args.feed_ids,
        comedian_ids=args.comedian_ids,
        comedian_names=args.comedian_names,
        limit=args.limit,
        max_episodes_per_feed=args.max_episodes_per_feed,
        include_aliases=not args.no_aliases,
    )
    _print_report(summary, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
