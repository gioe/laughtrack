#!/usr/bin/env python3
"""Collapse duplicate podcast rows and strong-identity podcast episode rows.

This is intentionally conservative:

* Podcast rows merge only when normalized title + author match, unless an
  operator supplies an explicit canonical/non-canonical podcast pair.
* Episode rows merge only on strong identity keys: same GUID or same audio URL
  within a podcast.
* Weak normalized-title/date collisions are excluded because bad source dates
  can make many distinct numbered episodes look identical.
"""

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
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass(frozen=True)
class EpisodeDupeGroup:
    podcast_id: int
    reason: str
    identity_value: str
    canonical_id: int
    non_canonical_ids: tuple[int, ...]


@dataclass(frozen=True)
class PodcastDupeGroup:
    canonical_id: int
    non_canonical_ids: tuple[int, ...]


@dataclass
class CleanupSummary:
    podcast_groups_scanned: int = 0
    podcasts_deleted: int = 0
    podcast_episodes_repointed: int = 0
    comedian_podcasts_repointed: int = 0
    comedian_podcasts_absorbed: int = 0
    candidate_reviews_repointed: int = 0
    deny_list_repointed: int = 0
    deny_list_absorbed: int = 0
    favorite_podcasts_repointed: int = 0
    favorite_podcasts_absorbed: int = 0

    episode_groups_scanned: int = 0
    episodes_deleted: int = 0
    appearances_repointed: int = 0
    appearances_absorbed: int = 0
    reviews_repointed: int = 0

    groups_failed: int = 0
    errors: list[str] = field(default_factory=list)


_FIND_PODCAST_GROUPS_SQL = """
    WITH scored AS (
        SELECT
            p.id,
            LOWER(BTRIM(p.title)) AS title_norm,
            LOWER(BTRIM(COALESCE(p.author_name, ''))) AS author_norm,
            COUNT(DISTINCT pe.id) AS episode_count,
            COUNT(DISTINCT cp.id) FILTER (WHERE cp.review_status = 'accepted') AS accepted_owner_count,
            COUNT(DISTINCT fp.profile_id) AS favorite_count
        FROM podcasts p
        LEFT JOIN podcast_episodes pe ON pe.podcast_id = p.id
        LEFT JOIN comedian_podcasts cp ON cp.podcast_id = p.id
        LEFT JOIN favorite_podcasts fp ON fp.podcast_id = p.id
        GROUP BY p.id, title_norm, author_norm
    ),
    duplicate_groups AS (
        SELECT title_norm, author_norm
        FROM scored
        GROUP BY title_norm, author_norm
        HAVING COUNT(*) > 1
    ),
    ranked AS (
        SELECT
            scored.*,
            FIRST_VALUE(id) OVER (
                PARTITION BY title_norm, author_norm
                ORDER BY accepted_owner_count DESC, favorite_count DESC, episode_count DESC, id
            ) AS canonical_id
        FROM scored
        JOIN duplicate_groups USING (title_norm, author_norm)
    )
    SELECT
        canonical_id,
        array_agg(id ORDER BY id) FILTER (WHERE id <> canonical_id) AS non_canonical_ids
    FROM ranked
    GROUP BY canonical_id
    ORDER BY canonical_id
"""

_FIND_EPISODE_GUID_GROUPS_SQL = """
    SELECT
        podcast_id,
        'guid' AS reason,
        guid AS identity_value,
        array_agg(id ORDER BY id) AS ids
    FROM podcast_episodes
    WHERE guid IS NOT NULL
      AND BTRIM(guid) <> ''
      AND (%s::int[] IS NULL OR podcast_id = ANY(%s::int[]))
    GROUP BY podcast_id, guid
    HAVING COUNT(*) > 1
    ORDER BY podcast_id, MIN(id)
"""

_FIND_EPISODE_AUDIO_GROUPS_SQL = """
    SELECT
        podcast_id,
        'audio_url' AS reason,
        audio_url AS identity_value,
        array_agg(id ORDER BY id) AS ids
    FROM podcast_episodes
    WHERE audio_url IS NOT NULL
      AND BTRIM(audio_url) <> ''
      AND (%s::int[] IS NULL OR podcast_id = ANY(%s::int[]))
    GROUP BY podcast_id, audio_url
    HAVING COUNT(*) > 1
    ORDER BY podcast_id, MIN(id)
"""

_UPDATE_EPISODE_PODCASTS_SQL = """
    UPDATE podcast_episodes SET podcast_id = %s WHERE podcast_id = ANY(%s)
"""

_REPOINT_COMEDIAN_PODCASTS_SQL = """
    UPDATE comedian_podcasts
    SET podcast_id = %s
    WHERE id IN (
        SELECT DISTINCT ON (comedian_id, association_type, source) id
        FROM comedian_podcasts cp
        WHERE cp.podcast_id = ANY(%s)
          AND NOT EXISTS (
              SELECT 1 FROM comedian_podcasts cp2
              WHERE cp2.podcast_id = %s
                AND cp2.comedian_id = cp.comedian_id
                AND cp2.association_type = cp.association_type
                AND cp2.source = cp.source
          )
        ORDER BY comedian_id, association_type, source, id
    )
"""

_DELETE_LEFTOVER_COMEDIAN_PODCASTS_SQL = """
    DELETE FROM comedian_podcasts WHERE podcast_id = ANY(%s)
"""

_UPDATE_CANDIDATE_REVIEWS_SQL = """
    UPDATE podcast_candidate_reviews SET podcast_id = %s WHERE podcast_id = ANY(%s)
"""

_REPOINT_DENY_LIST_SQL = """
    UPDATE podcast_deny_list
    SET podcast_id = %s
    WHERE id IN (
        SELECT id
        FROM podcast_deny_list dl
        WHERE dl.podcast_id = ANY(%s)
          AND NOT EXISTS (
              SELECT 1 FROM podcast_deny_list dl2
              WHERE dl2.podcast_id = %s
          )
        ORDER BY id
        LIMIT 1
    )
"""

_DELETE_LEFTOVER_DENY_LIST_SQL = """
    DELETE FROM podcast_deny_list WHERE podcast_id = ANY(%s)
"""

_REPOINT_FAVORITES_SQL = """
    UPDATE favorite_podcasts
    SET podcast_id = %s
    WHERE id IN (
        SELECT DISTINCT ON (profile_id) id
        FROM favorite_podcasts fp
        WHERE fp.podcast_id = ANY(%s)
          AND NOT EXISTS (
              SELECT 1 FROM favorite_podcasts fp2
              WHERE fp2.podcast_id = %s
                AND fp2.profile_id = fp.profile_id
          )
        ORDER BY profile_id, id
    )
"""

_DELETE_LEFTOVER_FAVORITES_SQL = """
    DELETE FROM favorite_podcasts WHERE podcast_id = ANY(%s)
"""

_DELETE_PODCASTS_SQL = """
    DELETE FROM podcasts WHERE id = ANY(%s)
"""

_REPOINT_APPEARANCES_SQL = """
    UPDATE episode_appearances
    SET episode_id = %s
    WHERE id IN (
        SELECT DISTINCT ON (comedian_id, source) id
        FROM episode_appearances ea
        WHERE ea.episode_id = ANY(%s)
          AND NOT EXISTS (
              SELECT 1 FROM episode_appearances ea2
              WHERE ea2.episode_id = %s
                AND ea2.comedian_id = ea.comedian_id
                AND ea2.source = ea.source
          )
        ORDER BY comedian_id, source, id
    )
"""

_DELETE_LEFTOVER_APPEARANCES_SQL = """
    DELETE FROM episode_appearances WHERE episode_id = ANY(%s)
"""

_REPOINT_REVIEWS_SQL = """
    UPDATE episode_appearance_reviews SET episode_id = %s WHERE episode_id = ANY(%s)
"""

_DELETE_EPISODES_SQL = """
    DELETE FROM podcast_episodes WHERE id = ANY(%s)
"""

_PREVIEW_REPOINTABLE_APPEARANCES_SQL = """
    SELECT COUNT(*) FROM (
        SELECT DISTINCT ON (comedian_id, source) id
        FROM episode_appearances ea
        WHERE ea.episode_id = ANY(%s)
          AND NOT EXISTS (
              SELECT 1 FROM episode_appearances ea2
              WHERE ea2.episode_id = %s
                AND ea2.comedian_id = ea.comedian_id
                AND ea2.source = ea.source
          )
        ORDER BY comedian_id, source, id
    ) AS preview
"""

_PREVIEW_ALL_APPEARANCES_ON_NON_CANONICAL_SQL = """
    SELECT COUNT(*) FROM episode_appearances WHERE episode_id = ANY(%s)
"""

_PREVIEW_REVIEWS_SQL = """
    SELECT COUNT(*) FROM episode_appearance_reviews WHERE episode_id = ANY(%s)
"""

_PREVIEW_REPOINTABLE_COMEDIAN_PODCASTS_SQL = """
    SELECT COUNT(*) FROM (
        SELECT DISTINCT ON (comedian_id, association_type, source) id
        FROM comedian_podcasts cp
        WHERE cp.podcast_id = ANY(%s)
          AND NOT EXISTS (
              SELECT 1 FROM comedian_podcasts cp2
              WHERE cp2.podcast_id = %s
                AND cp2.comedian_id = cp.comedian_id
                AND cp2.association_type = cp.association_type
                AND cp2.source = cp.source
          )
        ORDER BY comedian_id, association_type, source, id
    ) AS preview
"""

_PREVIEW_ALL_COMEDIAN_PODCASTS_ON_NON_CANONICAL_SQL = """
    SELECT COUNT(*) FROM comedian_podcasts WHERE podcast_id = ANY(%s)
"""

_PREVIEW_REPOINTABLE_FAVORITES_SQL = """
    SELECT COUNT(*) FROM (
        SELECT DISTINCT ON (profile_id) id
        FROM favorite_podcasts fp
        WHERE fp.podcast_id = ANY(%s)
          AND NOT EXISTS (
              SELECT 1 FROM favorite_podcasts fp2
              WHERE fp2.podcast_id = %s
                AND fp2.profile_id = fp.profile_id
          )
        ORDER BY profile_id, id
    ) AS preview
"""

_PREVIEW_ALL_FAVORITES_ON_NON_CANONICAL_SQL = """
    SELECT COUNT(*) FROM favorite_podcasts WHERE podcast_id = ANY(%s)
"""

_PREVIEW_EPISODES_ON_NON_CANONICAL_PODCASTS_SQL = """
    SELECT COUNT(*) FROM podcast_episodes WHERE podcast_id = ANY(%s)
"""

_PREVIEW_CANDIDATE_REVIEWS_SQL = """
    SELECT COUNT(*) FROM podcast_candidate_reviews WHERE podcast_id = ANY(%s)
"""

_PREVIEW_DENY_LIST_SQL = """
    SELECT COUNT(*) FROM podcast_deny_list WHERE podcast_id = ANY(%s)
"""

_PREVIEW_REPOINTABLE_DENY_LIST_SQL = """
    SELECT COUNT(*) FROM (
        SELECT id
        FROM podcast_deny_list dl
        WHERE dl.podcast_id = ANY(%s)
          AND NOT EXISTS (
              SELECT 1 FROM podcast_deny_list dl2
              WHERE dl2.podcast_id = %s
          )
        ORDER BY id
        LIMIT 1
    ) AS preview
"""


def _rows_to_episode_groups(rows: list[tuple[Any, ...]], seen_ids: set[int]) -> list[EpisodeDupeGroup]:
    groups: list[EpisodeDupeGroup] = []
    for row in rows:
        podcast_id, reason, identity_value, ids = row
        available_ids = [int(i) for i in ids if int(i) not in seen_ids]
        if len(available_ids) < 2:
            continue
        canonical_id = available_ids[0]
        non_canonical_ids = tuple(available_ids[1:])
        seen_ids.update(available_ids)
        groups.append(
            EpisodeDupeGroup(
                podcast_id=int(podcast_id),
                reason=str(reason),
                identity_value=str(identity_value),
                canonical_id=canonical_id,
                non_canonical_ids=non_canonical_ids,
            )
        )
    return groups


def load_episode_dupe_groups(
    conn: Any,
    *,
    limit: Optional[int] = None,
    podcast_ids: Optional[list[int]] = None,
) -> list[EpisodeDupeGroup]:
    seen_ids: set[int] = set()
    groups: list[EpisodeDupeGroup] = []
    with conn.cursor() as cur:
        cur.execute(_FIND_EPISODE_GUID_GROUPS_SQL, (podcast_ids, podcast_ids))
        groups.extend(_rows_to_episode_groups(cur.fetchall() or [], seen_ids))
        cur.execute(_FIND_EPISODE_AUDIO_GROUPS_SQL, (podcast_ids, podcast_ids))
        groups.extend(_rows_to_episode_groups(cur.fetchall() or [], seen_ids))
    return groups[:limit] if limit is not None else groups


def load_podcast_dupe_groups(conn: Any, *, limit: Optional[int] = None) -> list[PodcastDupeGroup]:
    with conn.cursor() as cur:
        cur.execute(_FIND_PODCAST_GROUPS_SQL)
        rows = cur.fetchall() or []
    groups: list[PodcastDupeGroup] = []
    for canonical_id, non_canonical_ids in rows:
        ids = tuple(int(i) for i in (non_canonical_ids or []) if int(i) != int(canonical_id))
        if not ids:
            continue
        groups.append(PodcastDupeGroup(canonical_id=int(canonical_id), non_canonical_ids=ids))
        if limit is not None and len(groups) >= limit:
            break
    return groups


def _preview_episode_group(conn: Any, group: EpisodeDupeGroup) -> tuple[int, int, int]:
    non_canonical = list(group.non_canonical_ids)
    with conn.cursor() as cur:
        cur.execute(_PREVIEW_REPOINTABLE_APPEARANCES_SQL, (non_canonical, group.canonical_id))
        repointable = int((cur.fetchone() or (0,))[0] or 0)
        cur.execute(_PREVIEW_ALL_APPEARANCES_ON_NON_CANONICAL_SQL, (non_canonical,))
        total_appearances = int((cur.fetchone() or (0,))[0] or 0)
        cur.execute(_PREVIEW_REVIEWS_SQL, (non_canonical,))
        reviews = int((cur.fetchone() or (0,))[0] or 0)
    return repointable, total_appearances - repointable, reviews


def _reconcile_episode_group(conn: Any, group: EpisodeDupeGroup) -> tuple[int, int, int]:
    non_canonical = list(group.non_canonical_ids)
    with conn.cursor() as cur:
        cur.execute(_REPOINT_APPEARANCES_SQL, (group.canonical_id, non_canonical, group.canonical_id))
        appearances_repointed = cur.rowcount or 0
        cur.execute(_DELETE_LEFTOVER_APPEARANCES_SQL, (non_canonical,))
        appearances_absorbed = cur.rowcount or 0
        cur.execute(_REPOINT_REVIEWS_SQL, (group.canonical_id, non_canonical))
        reviews_repointed = cur.rowcount or 0
        cur.execute(_DELETE_EPISODES_SQL, (non_canonical,))
    return appearances_repointed, appearances_absorbed, reviews_repointed


def _preview_podcast_group(conn: Any, group: PodcastDupeGroup) -> tuple[int, int, int, int, int, int, int, int]:
    non_canonical = list(group.non_canonical_ids)
    with conn.cursor() as cur:
        cur.execute(_PREVIEW_EPISODES_ON_NON_CANONICAL_PODCASTS_SQL, (non_canonical,))
        episodes = int((cur.fetchone() or (0,))[0] or 0)
        cur.execute(_PREVIEW_REPOINTABLE_COMEDIAN_PODCASTS_SQL, (non_canonical, group.canonical_id))
        comedian_repointable = int((cur.fetchone() or (0,))[0] or 0)
        cur.execute(_PREVIEW_ALL_COMEDIAN_PODCASTS_ON_NON_CANONICAL_SQL, (non_canonical,))
        total_comedian = int((cur.fetchone() or (0,))[0] or 0)
        cur.execute(_PREVIEW_CANDIDATE_REVIEWS_SQL, (non_canonical,))
        candidate_reviews = int((cur.fetchone() or (0,))[0] or 0)
        cur.execute(_PREVIEW_REPOINTABLE_DENY_LIST_SQL, (non_canonical, group.canonical_id))
        deny_list_repointable = int((cur.fetchone() or (0,))[0] or 0)
        cur.execute(_PREVIEW_DENY_LIST_SQL, (non_canonical,))
        total_deny_list = int((cur.fetchone() or (0,))[0] or 0)
        cur.execute(_PREVIEW_REPOINTABLE_FAVORITES_SQL, (non_canonical, group.canonical_id))
        favorite_repointable = int((cur.fetchone() or (0,))[0] or 0)
        cur.execute(_PREVIEW_ALL_FAVORITES_ON_NON_CANONICAL_SQL, (non_canonical,))
        total_favorites = int((cur.fetchone() or (0,))[0] or 0)
    return (
        episodes,
        comedian_repointable,
        total_comedian - comedian_repointable,
        candidate_reviews,
        deny_list_repointable,
        total_deny_list - deny_list_repointable,
        favorite_repointable,
        total_favorites - favorite_repointable,
    )


def _reconcile_podcast_group(conn: Any, group: PodcastDupeGroup) -> tuple[int, int, int, int, int, int, int, int]:
    non_canonical = list(group.non_canonical_ids)
    with conn.cursor() as cur:
        cur.execute(_UPDATE_EPISODE_PODCASTS_SQL, (group.canonical_id, non_canonical))
        episodes = cur.rowcount or 0
        cur.execute(_REPOINT_COMEDIAN_PODCASTS_SQL, (group.canonical_id, non_canonical, group.canonical_id))
        comedian_repointed = cur.rowcount or 0
        cur.execute(_DELETE_LEFTOVER_COMEDIAN_PODCASTS_SQL, (non_canonical,))
        comedian_absorbed = cur.rowcount or 0
        cur.execute(_UPDATE_CANDIDATE_REVIEWS_SQL, (group.canonical_id, non_canonical))
        candidate_reviews = cur.rowcount or 0
        cur.execute(_REPOINT_DENY_LIST_SQL, (group.canonical_id, non_canonical, group.canonical_id))
        deny_list = cur.rowcount or 0
        cur.execute(_DELETE_LEFTOVER_DENY_LIST_SQL, (non_canonical,))
        deny_list_absorbed = cur.rowcount or 0
        cur.execute(_REPOINT_FAVORITES_SQL, (group.canonical_id, non_canonical, group.canonical_id))
        favorites_repointed = cur.rowcount or 0
        cur.execute(_DELETE_LEFTOVER_FAVORITES_SQL, (non_canonical,))
        favorites_absorbed = cur.rowcount or 0
        cur.execute(_DELETE_PODCASTS_SQL, (non_canonical,))
    return (
        episodes,
        comedian_repointed,
        comedian_absorbed,
        candidate_reviews,
        deny_list,
        deny_list_absorbed,
        favorites_repointed,
        favorites_absorbed,
    )


def cleanup_canonical_podcast_duplicates(
    *,
    dry_run: bool,
    confirm: bool,
    podcast_limit: Optional[int] = None,
    episode_limit: Optional[int] = None,
    canonical_podcast_id: Optional[int] = None,
    non_canonical_podcast_ids: Optional[list[int]] = None,
) -> CleanupSummary:
    if dry_run == confirm:
        raise ValueError("choose exactly one of dry_run or confirm")
    if (canonical_podcast_id is None) != (non_canonical_podcast_ids is None):
        raise ValueError("canonical_podcast_id and non_canonical_podcast_ids must be provided together")

    summary = CleanupSummary()

    def process(conn: Any) -> None:
        if canonical_podcast_id is not None and non_canonical_podcast_ids is not None:
            podcast_groups = [
                PodcastDupeGroup(
                    canonical_id=canonical_podcast_id,
                    non_canonical_ids=tuple(non_canonical_podcast_ids),
                )
            ]
            episode_podcast_ids = [canonical_podcast_id]
        else:
            podcast_groups = load_podcast_dupe_groups(conn, limit=podcast_limit)
            episode_podcast_ids = None
        summary.podcast_groups_scanned = len(podcast_groups)
        for group in podcast_groups:
            try:
                if dry_run:
                    result = _preview_podcast_group(conn, group)
                else:
                    result = _reconcile_podcast_group(conn, group)
            except Exception as exc:
                summary.groups_failed += 1
                message = f"podcast canonical_id={group.canonical_id}: {exc}"
                summary.errors.append(message)
                Logger.warn(f"[cleanup-podcast-canonical-duplicates] group failed: {message}")
                raise
            (
                episode_count,
                cp_repointed,
                cp_absorbed,
                candidate_reviews,
                deny_list,
                deny_list_absorbed,
                favorite_repointed,
                favorite_absorbed,
            ) = result
            summary.podcasts_deleted += len(group.non_canonical_ids)
            summary.podcast_episodes_repointed += episode_count
            summary.comedian_podcasts_repointed += cp_repointed
            summary.comedian_podcasts_absorbed += cp_absorbed
            summary.candidate_reviews_repointed += candidate_reviews
            summary.deny_list_repointed += deny_list
            summary.deny_list_absorbed += deny_list_absorbed
            summary.favorite_podcasts_repointed += favorite_repointed
            summary.favorite_podcasts_absorbed += favorite_absorbed

        episode_groups = load_episode_dupe_groups(
            conn,
            limit=episode_limit,
            podcast_ids=episode_podcast_ids,
        )
        summary.episode_groups_scanned = len(episode_groups)
        for group in episode_groups:
            try:
                if dry_run:
                    result = _preview_episode_group(conn, group)
                else:
                    result = _reconcile_episode_group(conn, group)
            except Exception as exc:
                summary.groups_failed += 1
                message = (
                    f"episode podcast_id={group.podcast_id} reason={group.reason} "
                    f"identity={group.identity_value!r}: {exc}"
                )
                summary.errors.append(message)
                Logger.warn(f"[cleanup-podcast-canonical-duplicates] group failed: {message}")
                raise
            appearances_repointed, appearances_absorbed, reviews_repointed = result
            summary.episodes_deleted += len(group.non_canonical_ids)
            summary.appearances_repointed += appearances_repointed
            summary.appearances_absorbed += appearances_absorbed
            summary.reviews_repointed += reviews_repointed

    if dry_run:
        with get_connection() as conn:
            process(conn)
        return summary

    with get_connection(autocommit=False) as conn:
        try:
            process(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return summary


def _print_report(summary: CleanupSummary, *, dry_run: bool) -> None:
    prefix = "DRY RUN - " if dry_run else ""
    print(
        f"{prefix}Podcast rows: {summary.podcast_groups_scanned} groups, "
        f"{summary.podcasts_deleted} podcasts deleted, "
        f"{summary.podcast_episodes_repointed} episodes re-pointed, "
        f"{summary.comedian_podcasts_repointed} comedian_podcasts re-pointed, "
        f"{summary.comedian_podcasts_absorbed} comedian_podcasts absorbed, "
        f"{summary.candidate_reviews_repointed} candidate reviews re-pointed, "
        f"{summary.deny_list_repointed} deny-list rows re-pointed, "
        f"{summary.deny_list_absorbed} deny-list rows absorbed, "
        f"{summary.favorite_podcasts_repointed} favorites re-pointed, "
        f"{summary.favorite_podcasts_absorbed} favorites absorbed"
    )
    print(
        f"{prefix}Episodes: {summary.episode_groups_scanned} groups, "
        f"{summary.episodes_deleted} episodes deleted, "
        f"{summary.appearances_repointed} appearances re-pointed, "
        f"{summary.appearances_absorbed} appearances absorbed, "
        f"{summary.reviews_repointed} reviews re-pointed"
    )
    if summary.groups_failed:
        print(f"{summary.groups_failed} groups failed")
    for error in summary.errors:
        print(f"  error: {error}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge duplicate podcast rows and strong-identity duplicate podcast episodes.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Report planned writes without mutating")
    mode.add_argument("--confirm", action="store_true", help="Apply cleanup in one transaction")
    parser.add_argument("--podcast-limit", type=int, default=None, help="Process at most N podcast groups")
    parser.add_argument("--episode-limit", type=int, default=None, help="Process at most N episode groups")
    parser.add_argument(
        "--canonical-podcast-id",
        type=int,
        default=None,
        help="Explicit canonical podcast row for a targeted manual fold",
    )
    parser.add_argument(
        "--non-canonical-podcast-id",
        dest="non_canonical_podcast_ids",
        type=int,
        action="append",
        default=None,
        help="Podcast row to fold into --canonical-podcast-id; repeat for multiple rows",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.dry_run == args.confirm:
        parser.error("choose exactly one of --dry-run or --confirm")
    summary = cleanup_canonical_podcast_duplicates(
        dry_run=args.dry_run,
        confirm=args.confirm,
        podcast_limit=args.podcast_limit,
        episode_limit=args.episode_limit,
        canonical_podcast_id=args.canonical_podcast_id,
        non_canonical_podcast_ids=args.non_canonical_podcast_ids,
    )
    _print_report(summary, dry_run=args.dry_run)
    return 0 if summary.groups_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
