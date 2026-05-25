"""Comedian database handler for comedian-specific operations."""

import itertools
import os
import re
import threading
import time
from typing import Callable, List, Optional, Tuple

import requests
from psycopg2.extras import DictRow
from laughtrack.core.data.base_handler import BaseDatabaseHandler
from sql.comedian_queries import ComedianQueries

from laughtrack.foundation.infrastructure.database.template import BatchTemplateGenerator
from laughtrack.foundation.infrastructure.logger.logger import Logger

from .false_positive_detector import detect_false_positive
from .model import Comedian

_YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/channels"
_CHANNEL_ID_RE = re.compile(r"UC[\w-]{22}")
_INSTAGRAM_API_URL = "https://i.instagram.com/api/v1/users/web_profile_info/"
_TIKTOK_API_URL = "https://www.tiktok.com/api/user/detail/"
# Realistic browser UA required by both Instagram and TikTok endpoint fingerprinting
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
# Delay between per-comedian requests to avoid rate-limiting on unofficial endpoints
_SOCIAL_REQUEST_DELAY_S = float(os.environ.get("SOCIAL_REQUEST_DELAY_S", "1.0"))
# Abort a platform refresh after this many consecutive failures (e.g. datacenter IP blocked)
_CIRCUIT_BREAKER_THRESHOLD = int(os.environ.get("SOCIAL_CIRCUIT_BREAKER", "10"))


def _itunes_on_insert_enabled() -> bool:
    return os.environ.get("LAUGHTRACK_ITUNES_ON_INSERT_ENABLED", "1") != "0"


def _itunes_on_insert_min_confidence() -> float:
    return float(os.environ.get("LAUGHTRACK_ITUNES_ON_INSERT_MIN_CONFIDENCE", "0.8"))


def _itunes_on_insert_max_results() -> int:
    return int(os.environ.get("LAUGHTRACK_ITUNES_ON_INSERT_MAX_RESULTS", "10"))


def _itunes_on_insert_country() -> str:
    return os.environ.get("LAUGHTRACK_ITUNES_ON_INSERT_COUNTRY", "US")


_itunes_thread_counter = itertools.count(1)


def _itunes_on_insert_background() -> bool:
    """Run discovery in a daemon thread so it never blocks lineup ingestion.

    Default ``"1"`` (background). Set to ``"0"`` to run inline — useful for
    deterministic tests and one-shot scripts that want to observe candidate
    counts before exit.
    """
    return os.environ.get("LAUGHTRACK_ITUNES_ON_INSERT_BACKGROUND", "1") != "0"


def _itunes_on_insert_deny_list_ttl() -> float:
    """Seconds to cache the active podcast deny list across discovery batches.

    ``load_active_deny_list`` scans the full ``podcast_deny_list`` table on every
    call. During a heavy scraper run, ``insert_comedians`` fires iTunes discovery
    per insert batch, each re-querying the deny list through a fresh transaction.
    The deny list rarely changes mid-scrape, so we memoize it briefly. ``0``
    disables caching (every batch re-queries).
    """
    return float(os.environ.get("LAUGHTRACK_ITUNES_ON_INSERT_DENY_LIST_TTL", "60"))


_DenyList = Tuple[set, set]


class _DenyListCache:
    """Process-wide TTL cache for the active podcast deny list.

    Shared across all ``ComedianHandler`` instances because the deny list is
    global, and guarded by a lock because discovery runs in background daemon
    threads. On a cache miss the loader runs *outside* the lock: a slow DB call
    must not pin every discovery thread, and a redundant query at the TTL
    boundary is cheaper than serializing all threads through the database.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._value: Optional[_DenyList] = None
        self._expires_at: float = 0.0

    def get(self, loader: Callable[[], _DenyList], ttl: float) -> _DenyList:
        now = time.monotonic()
        with self._lock:
            if self._value is not None and now < self._expires_at:
                return self._value
        value = loader()
        with self._lock:
            self._value = value
            self._expires_at = time.monotonic() + ttl
        return value

    def clear(self) -> None:
        with self._lock:
            self._value = None
            self._expires_at = 0.0


# Module-level so the deny-list query is deduplicated across every
# ComedianHandler instance (show handler, comedian service, scrapers) for the
# duration of the TTL — not just within a single handler.
_deny_list_cache = _DenyListCache()


def _normalize_deny_list_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace("\xa0", " ")).strip().lower()


class ComedianHandler(BaseDatabaseHandler[Comedian]):
    """Handler for comedian database operations."""

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "comedian"

    def get_entity_class(self) -> type[Comedian]:
        """Return the Comedian class for instantiation."""
        return Comedian

    def insert_comedians(self, comedians: List[Comedian], *, pre_filtered: bool = False) -> List[DictRow]:
        """
        Insert comedians into the database.

        Uses ON CONFLICT DO NOTHING so that name-only stubs created during lineup
        extraction (e.g. from StandupNY) never overwrite existing comedian data
        (follower counts, social accounts, show stats).  Callers should not rely on
        the return value to detect pre-existing comedians; an empty list means all
        provided comedians were already present.

        Names present in comedian_deny_list are skipped before insertion and logged
        at warn level (unless pre_filtered=True).

        Args:
            comedians: List of comedians to insert
            pre_filtered: If True, skip deny-list and false-positive filtering.
                Use when the caller has already applied both filters (e.g.
                update_show_lineups) to avoid redundant DB queries and
                potential divergence between outer and inner filtering.

        Returns:
            List of newly inserted comedian rows (empty when all already existed)
        """
        if not comedians:
            raise ValueError("No comedians to insert")

        try:
            if not pre_filtered:
                comedians = self._filter_false_positive_comedians(comedians)
                if not comedians:
                    Logger.info("insert_comedians: all candidates were false positives; nothing inserted")
                    return []

                comedians = self._filter_denied_comedians(comedians)
                if not comedians:
                    Logger.info("insert_comedians: all candidates were on the deny list; nothing inserted")
                    return []

            items = [comedian.to_insert_tuple() for comedian in comedians]
            template = BatchTemplateGenerator.generate_dynamic_template(items)
            results = self.execute_batch_operation(
                ComedianQueries.BATCH_ADD_COMEDIANS, items, template=template, return_results=True
            )

            inserted_count = len(results) if results else 0
            skipped_count = len(comedians) - inserted_count
            Logger.info(
                f"insert_comedians: {inserted_count} inserted, {skipped_count} already existed (skipped)"
            )

            # Dispatch iTunes podcast discovery for newly inserted comedians off the
            # lineup ingestion hot path. By default the work runs in a daemon thread
            # so insert_comedians returns immediately; failures inside the worker
            # are logged and never raised. Set
            # LAUGHTRACK_ITUNES_ON_INSERT_BACKGROUND=0 to run inline.
            #
            # Scope note: this covers all Python insertion paths (lineup ingestion is
            # the only current call site; future scraper-side inserts inherit the
            # trigger). The web admin POST flow (apps/web/app/api/admin/comedians)
            # writes via Prisma in TypeScript and does NOT invoke this hook —
            # cross-language invocation isn't justified for the low admin-create
            # volume; the periodic backfill CLI (scripts/core/search_itunes_podcasts.py)
            # covers any admin-created comedians on its next run.
            self._trigger_itunes_discovery_for_inserted(results or [])

            return results or []
        except Exception as e:
            Logger.error(f"Error inserting comedians: {str(e)}")
            raise

    def _trigger_itunes_discovery_for_inserted(
        self, inserted_rows: List[DictRow]
    ) -> Optional[threading.Thread]:
        """Schedule iTunes podcast discovery for newly inserted comedians.

        Background mode (default): spawns a daemon thread and returns it without
        waiting, so the lineup ingestion hot path is unblocked. Process exit
        terminates any still-running threads; the periodic backfill CLI
        (scripts/core/search_itunes_podcasts.py) covers any losses.

        Sync mode (``LAUGHTRACK_ITUNES_ON_INSERT_BACKGROUND=0``): runs the worker
        inline and returns ``None``. Useful for deterministic tests and scripts.
        """
        if not inserted_rows or not _itunes_on_insert_enabled():
            return None

        if not _itunes_on_insert_background():
            self._run_itunes_discovery_for_inserted(inserted_rows)
            return None

        # Counter suffix keeps thread names unique across calls so logs/stack
        # traces stay greppable when multiple workers are alive at once.
        thread_seq = next(_itunes_thread_counter)
        thread = threading.Thread(
            target=self._run_itunes_discovery_for_inserted,
            args=(inserted_rows,),
            name=f"itunes-discovery-{thread_seq}-n{len(inserted_rows)}",
            daemon=True,
        )
        thread.start()
        return thread

    def _run_itunes_discovery_for_inserted(self, inserted_rows: List[DictRow]) -> int:
        """Worker that runs iTunes discovery + persistence for the given rows.

        Any failure (network, DB, missing dependency, malformed env var) is
        logged but never raised, so comedian insertion succeeds even when
        iTunes is unreachable. Returns the number of PodcastCandidateReview
        rows upserted (0 on early return or failure).
        """
        # Defense-in-depth: the dispatcher already filters empty inputs, but
        # this worker is also called inline from tests, so we re-check here.
        if not inserted_rows:
            return 0

        # Resolve all configuration up front, inside the swallow-all guard, so
        # malformed env vars (e.g. LAUGHTRACK_ITUNES_ON_INSERT_MIN_CONFIDENCE="not-a-float")
        # cannot escape into insert_comedians' outer raise.
        try:
            from laughtrack.core.itunes_podcast_discovery import (
                PodcastDiscoveryComedian,
                candidate_is_denied,
                discover_candidates_for_comedians,
                load_active_deny_list,
                upsert_candidate_with_conn,
            )
            min_confidence = _itunes_on_insert_min_confidence()
            max_results = _itunes_on_insert_max_results()
            country = _itunes_on_insert_country()
            deny_list_ttl = _itunes_on_insert_deny_list_ttl()
        except Exception as e:
            Logger.warn(f"itunes_on_insert: setup failed (import or config parse), skipping: {e}")
            return 0

        discovery_comedians: List = []
        for row in inserted_rows:
            try:
                comedian_id = row["id"]
                name = row["name"]
            except (KeyError, IndexError, TypeError):
                continue
            if comedian_id is None or not name:
                continue
            discovery_comedians.append(
                PodcastDiscoveryComedian(comedian_id=int(comedian_id), name=str(name), aliases=[])
            )

        if not discovery_comedians:
            return 0

        try:
            candidates, failed = discover_candidates_for_comedians(
                discovery_comedians,
                max_results=max_results,
                country=country,
            )
        except Exception as e:
            Logger.warn(f"itunes_on_insert: discovery failed for {len(discovery_comedians)} new comedians: {e}")
            return 0

        eligible = [c for c in candidates if c.confidence >= min_confidence]
        if not eligible:
            Logger.info(
                f"itunes_on_insert: {len(discovery_comedians)} new comedians searched, "
                f"{len(candidates)} candidates, 0 at or above confidence {min_confidence:.2f}"
            )
            return 0

        written = 0
        try:
            with self.transaction() as conn:
                # Memoize the deny list across insert batches with a short TTL —
                # it rarely changes mid-scrape, so re-scanning the full
                # podcast_deny_list table on every batch is wasteful. On a hit
                # this skips the SELECT entirely; the transaction stays open for
                # the candidate upserts below regardless.
                def _load_deny_list() -> Tuple[set, set]:
                    with conn.cursor() as cur:
                        return load_active_deny_list(cur)

                deny_keys, deny_urls = _deny_list_cache.get(_load_deny_list, deny_list_ttl)
                for candidate in eligible:
                    if candidate_is_denied(candidate, deny_keys, deny_urls):
                        continue
                    upsert_candidate_with_conn(conn, candidate)
                    written += 1
        except Exception as e:
            Logger.warn(f"itunes_on_insert: persistence failed after discovery: {e}")
            return 0

        Logger.info(
            f"itunes_on_insert: {len(discovery_comedians)} new comedians searched, "
            f"{written} candidate review rows upserted, {failed} search failures"
        )
        return written

    def _filter_false_positive_comedians(self, comedians: List[Comedian]) -> List[Comedian]:
        """Return comedians whose names are NOT false positives (placeholder, structural, etc.).

        Detected names are logged at warn level with the detection reason and excluded
        from the returned list so they are never inserted into the database.
        """
        allowed = []
        for c in comedians:
            reason = detect_false_positive(c.name)
            if reason:
                Logger.warn(f"lineup_filter: skipping false-positive '{c.name}' — {reason}")
            else:
                allowed.append(c)
        return allowed

    def _filter_denied_comedians(self, comedians: List[Comedian]) -> List[Comedian]:
        """Return comedians whose names are NOT on the deny list.

        Names that are denied are logged at warn level and excluded from the result.
        """
        names = [_normalize_deny_list_name(c.name) for c in comedians]
        try:
            rows = self.execute_with_cursor(
                ComedianQueries.GET_DENIED_NAMES, (names,), return_results=True
            ) or []
        except Exception as e:
            # If the deny-list table is unavailable (e.g. migration not yet applied),
            # log and proceed rather than blocking all ingestion.
            Logger.warn(f"_filter_denied_comedians: deny-list query failed, skipping filter: {e}")
            return comedians

        denied = {_normalize_deny_list_name(row["name"]) for row in rows}
        if not denied:
            return comedians

        allowed = [
            c for c in comedians if _normalize_deny_list_name(c.name) not in denied
        ]
        for name in denied:
            Logger.warn(f"lineup_filter: skipping deny-listed name '{name}'")
        return allowed

    def source_images_for_new_comedians(self, comedian_names: List[str]) -> int:
        """Attempt to source and upload images for newly inserted comedians.

        Queries Wikidata and TMDb for each comedian, downloads/resizes images,
        uploads to Bunny CDN, and sets has_image=true in the database.

        This method is non-blocking — failures are logged but never raised.

        Args:
            comedian_names: Names of newly inserted comedians.

        Returns:
            Number of comedians for which images were found and uploaded.
        """
        if not comedian_names:
            return 0

        try:
            from laughtrack.core.services.image_sourcing import source_images_for_comedians

            sourced_names = source_images_for_comedians(comedian_names)
            if sourced_names:
                self.execute_with_cursor(
                    ComedianQueries.BATCH_SET_HAS_IMAGE_TRUE, (sourced_names,)
                )
                Logger.info(f"source_images: set has_image=true for {len(sourced_names)} comedians")
            return len(sourced_names)
        except Exception as e:
            Logger.warn(f"source_images: non-fatal error during image sourcing: {e}")
            return 0

    def update_comedian_popularity(self, comedian_ids: Optional[List[str]] = None) -> None:
        """
        Update popularity for comedians in the database.

        Fetches recency scores (date-decayed recent/upcoming show activity) and merges
        them with social follower data before recomputing each comedian's popularity score.

        Args:
            comedian_ids: Optional list of specific comedian IDs to update. If None, updates all comedians.
        """
        try:
            # Get target comedian UUIDs - either provided ones or all comedians
            target_uuids = self._get_comedian_uuids(comedian_ids)
            if not target_uuids:
                raise ValueError("No comedians found to update")

            # Refresh sold_out_shows and total_shows before reading comedian details
            self._refresh_comedian_show_counts(target_uuids)

            # Get current comedian details
            comedians = self._fetch_comedian_details(target_uuids)
            if not comedians:
                raise ValueError("No comedian details found")

            # Fetch recency scores and apply them to the comedian objects
            recency_map = self._fetch_recency_scores(target_uuids)
            for comedian in comedians:
                comedian.recency_score = recency_map.get(comedian.uuid, 0.0)

            # Update comedians with new popularity values
            items = [comedian.to_popularity_tuple() for comedian in comedians]
            self.execute_batch_operation(
                ComedianQueries.BATCH_UPDATE_COMEDIAN_POPULARITY, items
            )

            Logger.info(f"update_comedian_popularity: processed {len(items)} comedians")

        except Exception as e:
            Logger.error(f"Error updating comedian popularity: {str(e)}")
            raise

    def _fetch_recency_scores(self, comedian_uuids: List[str]) -> dict:
        """Fetch date-decayed recency scores for a list of comedian UUIDs.

        Returns a dict mapping comedian UUID to recency_score (0.0–1.0).
        Comedians with no shows in the last 180 days are absent from the dict
        and should be treated as 0.0.
        """
        try:
            results = (
                self.execute_with_cursor(
                    ComedianQueries.GET_COMEDIAN_RECENCY_SCORES, (comedian_uuids,), return_results=True
                )
                or []
            )
            return {row["comedian_id"]: float(row["recency_score"]) for row in results}
        except Exception as e:
            Logger.error(f"Error fetching comedian recency scores: {str(e)}")
            raise

    def _refresh_comedian_show_counts(self, comedian_uuids: List[str]) -> None:
        """Update sold_out_shows and total_shows for the given comedians across all shows.

        Aggregates show counts from the full historical lineup_items / tickets data
        (no show_id filter) so that the popularity scorer always uses accurate stats.
        """
        try:
            self.execute_with_cursor(
                ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS,
                (comedian_uuids,),
            )
        except Exception as e:
            Logger.error(f"Error refreshing comedian show counts: {str(e)}")
            raise

    def get_all_comedian_uuids(self) -> List[str]:
        """
        Get all comedian UUIDs from the database.

        Returns:
            List of all comedian UUIDs in the database
        """
        results = self.execute_with_cursor(ComedianQueries.GET_ALL_COMEDIAN_UUIDS, return_results=True)

        if not results:
            raise ValueError("No comedians found in database")

        Logger.info(f"Retrieved {len(results)} comedian UUIDs from database")
        return [row["uuid"] for row in results]

    # ------------------------------------------------------------------
    # Social follower refresh
    # ------------------------------------------------------------------

    def refresh_youtube_followers(self, api_key: str, batch_size: int = 50) -> int:
        """Fetch current YouTube subscriber counts and persist them to the DB.

        Queries the YouTube Data API v3 for comedians that have a youtube_account
        set, then updates only the youtube_followers column (all other fields are
        left unchanged).

        Args:
            api_key: YouTube Data API v3 key.
            batch_size: Max channel IDs per API request (YouTube limit: 50).

        Returns:
            Number of comedian rows updated.
        """
        rows = self._get_comedians_with_youtube_accounts()
        if not rows:
            Logger.info("refresh_youtube_followers: no comedians with YouTube accounts")
            return 0

        updates: List[tuple] = []
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            updates.extend(self._fetch_youtube_subscriber_counts(api_key, batch))

        if updates:
            self.execute_batch_operation(
                ComedianQueries.UPDATE_COMEDIAN_YOUTUBE_FOLLOWERS, updates
            )

        Logger.info(f"refresh_youtube_followers: updated {len(updates)} comedians")
        return len(updates)

    def _get_comedians_with_youtube_accounts(self) -> List[dict]:
        """Return rows with (uuid, youtube_account) for all comedians that have one."""
        rows = (
            self.execute_with_cursor(
                ComedianQueries.GET_COMEDIANS_WITH_YOUTUBE_ACCOUNT, return_results=True
            )
            or []
        )
        return [{"uuid": r["uuid"], "youtube_account": r["youtube_account"]} for r in rows]

    def _fetch_youtube_subscriber_counts(
        self, api_key: str, rows: List[dict]
    ) -> List[tuple]:
        """Call the YouTube Data API for a batch of comedians.

        Separates rows into channel-ID vs handle lookups; channel IDs are batched
        in a single request (up to 50), handles are requested individually because
        the ``forHandle`` parameter only accepts one value at a time.

        Returns list of ``(uuid, subscriber_count)`` tuples.
        """
        channel_id_rows: List[tuple] = []   # (uuid, channel_id)
        handle_rows: List[tuple] = []        # (uuid, handle)

        for row in rows:
            uuid = row["uuid"]
            account = row["youtube_account"].strip()
            channel_id = _CHANNEL_ID_RE.search(account)
            if channel_id:
                channel_id_rows.append((uuid, channel_id.group()))
            else:
                # Strip URL prefix or leading @
                m = re.search(r"youtube\.com/@([\w.-]+)", account)
                handle = m.group(1) if m else account.lstrip("@")
                handle_rows.append((uuid, handle))

        results: List[tuple] = []

        # Batch request for channel IDs
        if channel_id_rows:
            ids = [cid for _, cid in channel_id_rows]
            id_to_uuid = {cid: uuid for uuid, cid in channel_id_rows}
            try:
                data = self._youtube_request(api_key, ids=ids)
                for item in data.get("items", []):
                    cid = item["id"]
                    count = item["statistics"].get("subscriberCount")
                    if count is not None and cid in id_to_uuid:
                        results.append((id_to_uuid[cid], int(count)))
            except Exception as e:
                Logger.error(f"YouTube channel-ID batch request failed: {e}")

        # Individual requests for handles
        for uuid, handle in handle_rows:
            try:
                data = self._youtube_request(api_key, handle=handle)
                items = data.get("items", [])
                if items:
                    count = items[0]["statistics"].get("subscriberCount")
                    if count is not None:
                        results.append((uuid, int(count)))
            except Exception as e:
                Logger.warn(f"YouTube request failed for handle @{handle}: {e}")

        return results

    @staticmethod
    def _youtube_request(
        api_key: str,
        ids: Optional[List[str]] = None,
        handle: Optional[str] = None,
    ) -> dict:
        """Make a single YouTube Data API v3 channels request."""
        params: dict = {"part": "statistics", "key": api_key}
        if ids:
            params["id"] = ",".join(ids)
        elif handle:
            params["forHandle"] = handle if handle.startswith("@") else f"@{handle}"
        resp = requests.get(_YOUTUBE_API_URL, params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Instagram follower refresh
    # ------------------------------------------------------------------

    def refresh_instagram_followers(self) -> int:
        """Fetch current Instagram follower counts and persist them to the DB.

        Queries the Instagram web profile API for comedians that have an
        instagram_account set, then updates only the instagram_followers column.

        Returns:
            Number of comedian rows updated.
        """
        rows = self._get_comedians_with_instagram_accounts()
        if not rows:
            Logger.info("refresh_instagram_followers: no comedians with Instagram accounts")
            return 0

        updates: List[tuple] = []
        consecutive_failures = 0
        for row in rows:
            result = self._fetch_instagram_follower_count(row)
            if result is not None:
                updates.append(result)
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= _CIRCUIT_BREAKER_THRESHOLD:
                    Logger.warn(
                        f"refresh_instagram_followers: {_CIRCUIT_BREAKER_THRESHOLD} consecutive "
                        f"failures — aborting (likely blocked). {len(updates)}/{len(rows)} updated."
                    )
                    break
            time.sleep(_SOCIAL_REQUEST_DELAY_S)

        if not updates:
            Logger.warn(
                f"refresh_instagram_followers: {len(rows)} accounts found but 0 updated — "
                "API may be rate-limiting or unavailable"
            )
            return 0

        self.execute_batch_operation(
            ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS, updates
        )

        Logger.info(f"refresh_instagram_followers: updated {len(updates)} comedians")
        return len(updates)

    def _get_comedians_with_instagram_accounts(self) -> List[dict]:
        """Return rows with (uuid, instagram_account) for all comedians that have one."""
        rows = (
            self.execute_with_cursor(
                ComedianQueries.GET_COMEDIANS_WITH_INSTAGRAM_ACCOUNT, return_results=True
            )
            or []
        )
        return [{"uuid": r["uuid"], "instagram_account": r["instagram_account"]} for r in rows]

    def _fetch_instagram_follower_count(self, row: dict) -> Optional[tuple]:
        """Fetch the current Instagram follower count for a single comedian.

        Returns a ``(uuid, follower_count)`` tuple on success, or ``None`` if
        the account is unreachable or the response cannot be parsed.
        """
        uuid = row["uuid"]
        account = row["instagram_account"].strip().lstrip("@")
        try:
            data = self._instagram_request(account)
            count = data["data"]["user"]["edge_followed_by"]["count"]
            return (uuid, int(count))
        except Exception as e:
            Logger.warn(f"Instagram request failed for @{account}: {e}")
            return None

    @staticmethod
    def _instagram_request(account: str) -> dict:
        """Fetch Instagram public profile info for a username."""
        app_id = os.environ.get("INSTAGRAM_APP_ID", "936619743392459")
        headers = {
            "X-IG-App-ID": app_id,
            "User-Agent": _BROWSER_UA,
        }
        resp = requests.get(
            _INSTAGRAM_API_URL,
            params={"username": account},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # TikTok follower refresh
    # ------------------------------------------------------------------

    def refresh_tiktok_followers(self) -> int:
        """Fetch current TikTok follower counts and persist them to the DB.

        Queries the TikTok public user detail API for comedians that have a
        tiktok_account set, then updates only the tiktok_followers column.

        Returns:
            Number of comedian rows updated.
        """
        rows = self._get_comedians_with_tiktok_accounts()
        if not rows:
            Logger.info("refresh_tiktok_followers: no comedians with TikTok accounts")
            return 0

        updates: List[tuple] = []
        consecutive_failures = 0
        for row in rows:
            result = self._fetch_tiktok_follower_count(row)
            if result is not None:
                updates.append(result)
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= _CIRCUIT_BREAKER_THRESHOLD:
                    Logger.warn(
                        f"refresh_tiktok_followers: {_CIRCUIT_BREAKER_THRESHOLD} consecutive "
                        f"failures — aborting (likely blocked). {len(updates)}/{len(rows)} updated."
                    )
                    break
            time.sleep(_SOCIAL_REQUEST_DELAY_S)

        if not updates:
            Logger.warn(
                f"refresh_tiktok_followers: {len(rows)} accounts found but 0 updated — "
                "API may be rate-limiting or unavailable"
            )
            return 0

        self.execute_batch_operation(
            ComedianQueries.UPDATE_COMEDIAN_TIKTOK_FOLLOWERS, updates
        )

        Logger.info(f"refresh_tiktok_followers: updated {len(updates)} comedians")
        return len(updates)

    def _get_comedians_with_tiktok_accounts(self) -> List[dict]:
        """Return rows with (uuid, tiktok_account) for all comedians that have one."""
        rows = (
            self.execute_with_cursor(
                ComedianQueries.GET_COMEDIANS_WITH_TIKTOK_ACCOUNT, return_results=True
            )
            or []
        )
        return [{"uuid": r["uuid"], "tiktok_account": r["tiktok_account"]} for r in rows]

    def _fetch_tiktok_follower_count(self, row: dict) -> Optional[tuple]:
        """Fetch the current TikTok follower count for a single comedian.

        Returns a ``(uuid, follower_count)`` tuple on success, or ``None`` if
        the account is unreachable or the response cannot be parsed.
        """
        uuid = row["uuid"]
        account = row["tiktok_account"].strip().lstrip("@")
        try:
            data = self._tiktok_request(account)
            count = data["userInfo"]["stats"]["followerCount"]
            return (uuid, int(count))
        except Exception as e:
            Logger.warn(f"TikTok request failed for @{account}: {e}")
            return None

    @staticmethod
    def _tiktok_request(account: str) -> dict:
        """Fetch TikTok public user detail for a username."""
        params = {"uniqueId": account}
        headers = {
            "User-Agent": _BROWSER_UA,
            "Referer": "https://www.tiktok.com/",
        }
        resp = requests.get(_TIKTOK_API_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _get_comedian_uuids(self, comedian_ids: Optional[List[str]] = None) -> List[str]:
        """Get the list of comedian UUIDs to process."""
        if comedian_ids:
            # Deduplicate while preserving order so the count comparison below is accurate.
            # collect_comedian_uuids() returns a flat list with duplicates (same comedian
            # appearing in multiple shows); without deduplication every duplicate triggers
            # a spurious "UUID not found" warning.
            unique_ids = list(dict.fromkeys(comedian_ids))

            # Verify the provided UUIDs exist
            results = self.execute_with_cursor(
                ComedianQueries.GET_TARGET_COMEDIAN_IDS, (unique_ids,), return_results=True
            )

            if not results:
                raise ValueError("No matching comedians found in database")

            found_uuids = [row.get("uuid") for row in results]

            if len(found_uuids) != len(unique_ids):
                missing_uuids = set(unique_ids) - set(found_uuids)
                Logger.warn(
                    f"Warning: {len(missing_uuids)} comedian UUIDs not found in database "
                    f"(popularity update only — lineup data was already saved): {missing_uuids}"
                )
            return found_uuids
        else:
            # Use the extracted reusable function
            all_uuids = self.get_all_comedian_uuids()
            Logger.info(f"Processing all {len(all_uuids)} comedians for popularity update")
            return all_uuids

    def _fetch_comedian_details(self, comedian_uuids: List[str]) -> List[Comedian]:
        """Fetch comedian details from database."""
        try:
            results = (
                self.execute_with_cursor(
                    ComedianQueries.BATCH_GET_COMEDIAN_DETAILS, (comedian_uuids,), return_results=True
                )
                or []
            )

            if not results:
                raise ValueError("No comedian details found")

            # Use the entity class to create instances
            Logger.info(f"Retrieved details for {len(results)} comedians")
            return [Comedian.from_db_row(row) for row in results]
        except Exception as e:
            Logger.error(f"Error fetching comedian details: {str(e)}")
            raise
