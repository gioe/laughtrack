"""Show-specific utility functions for the Laughtrack domain."""

from typing import Any, Dict, List, Optional, Set, Tuple, cast
from datetime import datetime, timezone

from psycopg2.extras import DictRow

from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.foundation.utilities.string import StringUtils
from laughtrack.foundation.models.types import DuplicateKeyDetails, DuplicateShowRef
from laughtrack.foundation.utilities.entity.validation import deduplicate_entities_with_details


class ShowUtils:
    """Domain-specific utilities for Show entities."""

    # Validation Helper Functions

    @staticmethod
    def validate_required_string(value: str, field_name: str) -> Optional[str]:
        """
        Validate that a string field is present and non-empty using primitive utilities.

        Args:
            value: String value to validate
            field_name: Name of field for error messages

        Returns:
            Error message if invalid, None if valid
        """
        if value is None:
            return f"{field_name} is required and cannot be empty"

        cleaned = StringUtils.normalize_whitespace(str(value)).strip()
        if not cleaned:
            return f"{field_name} is required and cannot be empty"
        return None

    @staticmethod
    def collect_comedian_uuids(shows: List[Show]) -> List[str]:
        """
        Collect all comedian UUIDs from show lineups.

        Args:
            shows: List of shows to collect UUIDs from

        Returns:
            List of valid comedian UUIDs (non-None values)
        """
        return [comedian.uuid for show in shows for comedian in show.lineup if comedian.uuid is not None]

    @staticmethod
    def get_unique_comedian_uuids(shows: List[Show]) -> Set[str]:
        """
        Get unique comedian UUIDs from show lineups.

        Args:
            shows: List of shows to collect UUIDs from

        Returns:
            Set of unique comedian UUIDs
        """
        return set(ShowUtils.collect_comedian_uuids(shows))

    @staticmethod
    def group_shows_by_date(shows: List[Show]) -> Dict[str, List[Show]]:
        """
        Group shows by date.

        Args:
            shows: List of shows to group

        Returns:
            Dictionary mapping date strings to lists of shows
        """
        grouped = {}
        for show in shows:
            date_str = show.date.strftime("%Y-%m-%d") if show.date else "No Date"
            if date_str not in grouped:
                grouped[date_str] = []
            grouped[date_str].append(show)
        return grouped

    @staticmethod
    def filter_future_shows(shows: List[Show]) -> List[Show]:
        """
        Filter shows to only include future shows using common utilities.

        Args:
            shows: List of shows to filter

        Returns:
            List of future shows
        """
        return [show for show in shows if show.date and DateTimeUtils.is_future_date(show.date)]

    @staticmethod
    def get_show_lineup_size(show: Show) -> int:
        """
        Get the number of comedians in a show's lineup.

        Args:
            show: Show to analyze

        Returns:
            Number of comedians in lineup
        """
        return len(show.lineup) if show.lineup else 0

    @staticmethod
    def get_shows_with_comedian(shows: List[Show], comedian_name: str) -> List[Show]:
        """
        Find shows featuring a specific comedian.

        Args:
            shows: List of shows to search
            comedian_name: Name of comedian to find

        Returns:
            List of shows featuring the comedian
        """
        matching_shows = []
        for show in shows:
            if show.lineup:
                for comedian in show.lineup:
                    if comedian.name and comedian_name.lower() in comedian.name.lower():
                        matching_shows.append(show)
                        break
        return matching_shows

    @staticmethod
    def get_headliner(show: Show) -> Optional[str]:
        """
        Get the headliner (first comedian) from a show's lineup.

        Args:
            show: Show to analyze

        Returns:
            Name of headliner or None if no lineup
        """
        if show.lineup and len(show.lineup) > 0:
            return show.lineup[0].name
        return None

    @staticmethod
    def calculate_average_lineup_size(shows: List[Show]) -> float:
        """
        Calculate average lineup size across shows.

        Args:
            shows: List of shows to analyze

        Returns:
            Average number of comedians per show
        """
        if not shows:
            return 0.0

        total_comedians = sum(ShowUtils.get_show_lineup_size(show) for show in shows)
        return total_comedians / len(shows)

    @staticmethod
    def clean_show_name(name: str, remove_prefixes: Optional[List[str]] = None) -> str:
        """
        Clean and standardize names using primitive utilities.

        Args:
            name: Raw name to clean
            remove_prefixes: List of prefixes to remove (e.g., ["the ", "a "])

        Returns:
            Cleaned name
        """
        if not name:
            return ""

        # Use primitive utility for whitespace normalization
        name = StringUtils.normalize_whitespace(name)

        # Remove specified prefixes using primitive utility
        if remove_prefixes:
            for prefix in remove_prefixes:
                name = StringUtils.remove_prefix(name, prefix, case_sensitive=False)

        return name.strip()

    @staticmethod
    def _normalize_date_for_key(dt: Optional[datetime]) -> Optional[datetime]:
        """Return a UTC-naive datetime for use as a dict key.

        psycopg2 returns TIMESTAMPTZ columns as timezone-aware UTC datetimes,
        but show.date may be naive (no tzinfo) or aware with a non-UTC offset.
        Stripping tzinfo after converting to UTC makes the comparison consistent
        regardless of how the date was originally parsed.
        """
        if dt is None:
            return None
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    @staticmethod
    def update_shows_with_results(shows: List[Show], db_results: List[DictRow]) -> List[Show]:
        """
        Update show objects with database results (IDs and operation types).

        Args:
            shows: List of show objects
            db_results: List of database results from insert/update operations

        Returns:
            List of updated show objects
        """
        if not shows or not db_results:
            Logger.warn("No shows or database results to process")
            return shows

        # Create a mapping of shows by their standardized key.
        # Normalize date to UTC-naive so that naive show dates and the
        # UTC-aware dates returned by psycopg2 from TIMESTAMPTZ columns compare equal.
        show_map = {}
        for i, show in enumerate(shows):
            norm_date = ShowUtils._normalize_date_for_key(show.date)
            key = (show.club_id, norm_date, show.room)
            show_map[key] = i

        # Update shows with database results
        updated_shows = shows.copy()

        for result in db_results:
            # Try to match database result to show using the same unique key tuple
            # as Show.to_unique_key(): (club_id, date, room)
            result_key = (
                result.get("club_id"),
                ShowUtils._normalize_date_for_key(result.get("date")),
                result.get("room", "") or "",
            )

            if result_key in show_map:
                show_index = show_map[result_key]
                show = updated_shows[show_index]

                # Update show with database information
                if "id" in result and result["id"]:
                    show.id = result["id"]

                if "operation_type" in result:
                    show.operation_type = result["operation_type"]

                Logger.debug(f"Updated show '{show.name}' with id={show.id}, operation_type={show.operation_type}")
            else:
                Logger.warn(f"Could not match database result to show: {result_key}")

        return updated_shows

    # Deduplication helpers
    @staticmethod
    def deduplicate_shows(shows: List[Show]) -> List[Show]:
        """Deduplicate shows by their unique key (club_id, date, room).

        Keeps the first occurrence for each unique key and logs a concise summary
        if duplicates were found and removed.

        Args:
            shows: List of Show objects

        Returns:
            List of deduplicated Show objects (order preserved for first occurrences)
        """
        if not shows:
            return shows

        unique: dict[tuple, Show] = {}
        order: list[tuple] = []
        for show in shows:
            key = show.to_unique_key()
            if key not in unique:
                unique[key] = show
                order.append(key)
        deduped = [unique[k] for k in order]

        removed = len(shows) - len(deduped)
        if removed > 0:
            Logger.warning(f"Deduplicated {removed} duplicate shows (kept {len(deduped)})")
        return deduped

    @staticmethod
    def deduplicate_shows_with_details(shows: List[Show]) -> tuple[List[Show], List[DuplicateKeyDetails]]:
        """Deduplicate shows and return details about duplicates that were dropped.

        Keeps the first occurrence for each unique key and returns:
          - the deduplicated list (order preserved for first occurrences)
          - a list of duplicate detail dicts with club_id, date, room, kept, and dropped metadata

        Args:
            shows: List of Show objects

        Returns:
            Tuple of (deduplicated_shows, duplicate_details)
        """
        if not shows:
            return shows, []

        def map_detail(s: Show) -> dict:
            # Map to a simple dict; we'll convert to dataclasses below
            return {"name": s.name, "show_page_url": s.show_page_url}

        deduped, generic_details = deduplicate_entities_with_details(shows, map_detail)

        # Shape generic details into DuplicateKeyDetails (ISO date, explicit club_id/date/room, and key tuple)
        duplicate_details: List[DuplicateKeyDetails] = []
        for raw_key, info in generic_details.items():
            club_id, date_obj, room = cast(Tuple[int, datetime, str], raw_key)
            iso_date = date_obj.isoformat()
            kept_dict = cast(Dict[str, Any], info.get("kept", {}))
            dropped_list = cast(List[Dict[str, Any]], info.get("dropped", []))

            kept = DuplicateShowRef(
                name=str(kept_dict.get("name", "") or ""),
                show_page_url=kept_dict.get("show_page_url"),
            )
            dropped = [
                DuplicateShowRef(
                    name=str(d.get("name", "") or ""),
                    show_page_url=d.get("show_page_url"),
                )
                for d in dropped_list
                if isinstance(d, dict)
            ]

            duplicate_details.append(
                DuplicateKeyDetails(
                    key=(club_id, iso_date, room or ""),
                    club_id=club_id,
                    date=iso_date,
                    room=(room or ""),
                    kept=kept,
                    dropped=dropped,
                )
            )

        return deduped, duplicate_details

    @staticmethod
    def find_duplicate_keys(shows: List[Show]) -> dict[tuple, int]:
        """Find duplicate unique keys among shows.

        Args:
            shows: List of Show objects

        Returns:
            Mapping of unique key -> count for keys that appear more than once
        """
        counts: dict[tuple, int] = {}
        for show in shows:
            key = show.to_unique_key()
            counts[key] = counts.get(key, 0) + 1
        return {k: c for k, c in counts.items() if c > 1}
