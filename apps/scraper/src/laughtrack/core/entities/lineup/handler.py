"""Lineup database handler for lineup-specific operations."""

import re
from typing import Dict, List, Tuple

from laughtrack.core.data.base_handler import BaseDatabaseHandler
from sql.lineup_queries import LineupQueries

from laughtrack.core.entities.comedian.false_positive_detector import detect_false_positive
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.database.template import BatchTemplateGenerator
from laughtrack.foundation.infrastructure.logger.logger import Logger

from .model import LineupItem


_NAME_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_SINGLE_TOKEN_NAME_PUNCTUATION_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*[-'’][A-Za-z'’-]*")
_INTERSTITIAL_NICKNAME_PATTERN = r'(?:\s+(?:"[^"]+"|“[^”]+”|\'[^\']+\'|‘[^’]+’|\([^)]*\)))*\s+'
_SINGLE_TOKEN_MIN_TOTAL_SHOWS = 5


def _is_high_confidence_single_token_comedian(row: dict) -> bool:
    if not row.get("visible"):
        return False
    if int(row.get("total_shows") or 0) >= _SINGLE_TOKEN_MIN_TOTAL_SHOWS:
        return True
    return any(
        row.get(field)
        for field in ("instagram_followers", "tiktok_followers", "youtube_followers")
    )


def _is_credible_show_name_comedian_match(show_name: str, row: dict) -> bool:
    """Return whether a show-title substring match is credible enough for enrichment."""
    if row.get("visible") is False:
        return False

    comedian_name = row.get("match_name") or row.get("name")
    cleaned_name = (comedian_name or "").strip()
    cleaned_show_name = (show_name or "").strip()
    if not cleaned_name or not cleaned_show_name:
        return False

    if detect_false_positive(cleaned_name):
        return False

    name_words = _NAME_WORD_RE.findall(cleaned_name)
    if (
        len(name_words) < 2
        and not _SINGLE_TOKEN_NAME_PUNCTUATION_RE.fullmatch(cleaned_name)
        and not _is_high_confidence_single_token_comedian(row)
    ):
        return False

    escaped_name = re.escape(cleaned_name)
    exact_match_pattern = rf"(?<![A-Za-z0-9]){escaped_name}(?![A-Za-z0-9])"
    if re.search(exact_match_pattern, cleaned_show_name, re.IGNORECASE):
        return True

    if len(name_words) < 2:
        return False

    nickname_match_pattern = (
        r"(?<![A-Za-z0-9])"
        + _INTERSTITIAL_NICKNAME_PATTERN.join(re.escape(word) for word in name_words)
        + r"(?![A-Za-z0-9])"
    )
    return re.search(nickname_match_pattern, cleaned_show_name, re.IGNORECASE) is not None


class LineupHandler(BaseDatabaseHandler[LineupItem]):
    """Handler for lineup database operations."""

    def _get_show_name_comedian_rows_cache(self) -> Dict[str, List[dict]]:
        """Return the per-handler cache for title-derived comedian match rows."""
        cache = getattr(self, "_show_name_comedian_rows_cache", None)
        if cache is None:
            cache = {}
            self._show_name_comedian_rows_cache = cache
        return cache

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "lineup_item"

    def get_entity_class(self) -> type[LineupItem]:
        """Return the LineupItem class for instantiation."""
        return LineupItem

    def batch_update_lineups(
        self,
        shows: List[Show],
        current_lineups: Dict[int, List[Comedian]],
    ) -> Tuple[int, int]:
        """
        Update lineups for multiple shows in batch.

        Callers are responsible for inserting any new comedians into the database
        before calling this method.

        Args:
            shows: List of shows to update
            current_lineups: Dictionary mapping show IDs to their current lineups

        Returns:
            Tuple of (items_added, items_removed) counts.
        """
        # Collect all lineup changes
        to_add = []
        to_remove = []

        for show in shows:
            # Skip shows without IDs (they haven't been saved to the database yet)
            if show.id is None:
                continue

            # At this point show.id is guaranteed to be not None
            show_id = show.id
            current_lineup = current_lineups.get(show_id, [])
            current_comedian_uuids = {item.uuid for item in current_lineup}
            new_comedian_uuids = {comedian.uuid for comedian in show.lineup}

            # Find comedians to add and remove
            add_uuids = new_comedian_uuids - current_comedian_uuids
            remove_uuids = current_comedian_uuids - new_comedian_uuids

            # Collect additions (filter out None uuids)
            to_add.extend([LineupItem.create_lineup_item(show_id, uuid) for uuid in add_uuids if uuid is not None])

            # Collect removals (filter out None uuids)
            to_remove.extend(
                [LineupItem.create_lineup_item(show_id, uuid) for uuid in remove_uuids if uuid is not None]
            )

        # Perform batch lineup updates
        if to_remove:
            self.batch_delete_lineup_items(to_remove)
        if to_add:
            self.batch_add_lineup_items(to_add)

        return len(to_add), len(to_remove)

    def get_lineup(self, show_ids: List[int]) -> Dict[int, List[Comedian]]:
        """
        Get lineup for shows.

        Args:
            show_ids: List of show IDs

        Returns:
            Dictionary mapping show IDs to their lineups (lists of Comedian objects)
        """
        try:
            results = self.execute_with_cursor(LineupQueries.BATCH_GET_LINEUP, (show_ids,), return_results=True)
            if not results:
                return {}

            return {row["show_id"]: [Comedian.from_db_row(row) for row in row["lineup"]] for row in results}
        except Exception as e:
            Logger.error(f"Error getting lineup: {str(e)}")
            raise

    def get_comedians_from_show_names(self, show_names: list[tuple[str]]) -> Dict[str, List[Comedian]]:
        """
        Get comedians found in show names.

        Args:
            show_names: List of show names

        Returns:
            Dictionary mapping show names to lists of Comedian objects found in those show names
        """
        try:
            unique_show_names = []
            seen_show_names = set()
            for show_name_row in show_names:
                if not show_name_row:
                    continue
                show_name = show_name_row[0]
                if show_name in seen_show_names:
                    continue
                seen_show_names.add(show_name)
                unique_show_names.append(show_name)

            if not unique_show_names:
                return {}

            cached_rows_by_show_name = self._get_show_name_comedian_rows_cache()
            missing_show_names = [
                show_name for show_name in unique_show_names if show_name not in cached_rows_by_show_name
            ]

            if missing_show_names:
                results = self.execute_batch_operation(
                    LineupQueries.BATCH_GET_COMEDIANS_FROM_SHOW_NAME,
                    [(show_name,) for show_name in missing_show_names],
                    template=BatchTemplateGenerator.get_single_field_template(),
                    return_results=True,
                )

                rows_by_show_name = {show_name: [] for show_name in missing_show_names}
                seen_comedian_keys_by_show_name = {}
                for row in results or []:
                    show_name = row["show_name"]
                    if show_name not in rows_by_show_name:
                        continue
                    if not _is_credible_show_name_comedian_match(show_name, row):
                        continue

                    comedian_key = row.get("uuid") or row.get("name")
                    seen_comedian_keys = seen_comedian_keys_by_show_name.setdefault(show_name, set())
                    if comedian_key in seen_comedian_keys:
                        continue
                    seen_comedian_keys.add(comedian_key)
                    rows_by_show_name[show_name].append(dict(row))

                cached_rows_by_show_name.update(rows_by_show_name)

            show_comedians_map = {}
            for show_name in unique_show_names:
                cached_rows = cached_rows_by_show_name.get(show_name, [])
                if cached_rows:
                    show_comedians_map[show_name] = [Comedian.from_db_row(row) for row in cached_rows]
            return show_comedians_map
        except Exception as e:
            Logger.error(f"Error getting comedians from show names: {str(e)}")
            raise

    def batch_delete_lineup_items(self, items: List[tuple[int, str]]) -> None:
        """
        Delete multiple lineup items in batch.

        Args:
            items: List of tuples containing (show_id, comedian_uuid)
        """
        if not items:
            Logger.info("No lineup items to delete")
            return

        try:
            self.execute_batch_operation(
                LineupQueries.BATCH_DELETE_LINEUP_ITEMS, items, template=BatchTemplateGenerator.get_two_field_template()
            )
        except Exception as e:
            Logger.error(f"Error batch deleting lineup items: {str(e)}")
            raise

    def batch_add_lineup_items(self, items: List[tuple[int, str]]) -> None:
        """
        Add multiple lineup items in batch.

        Args:
            items: List of tuples containing (show_id, comedian_uuid)
        """
        if not items:
            raise ValueError("No lineup items to add")

        try:
            self.execute_batch_operation(
                LineupQueries.BATCH_ADD_LINEUP_ITEMS, items, template=BatchTemplateGenerator.get_two_field_template()
            )
        except Exception as e:
            Logger.error(f"Error batch adding lineup items: {str(e)}")
            raise
