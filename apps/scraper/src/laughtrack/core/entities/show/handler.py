"""Show database handler for show-specific operations."""

from typing import Dict, List, Optional, Tuple

from laughtrack.core.data.base_handler import BaseDatabaseHandler
from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.comedian.name_splitter import split_combined_name
from laughtrack.core.entities.lineup.handler import LineupHandler
from laughtrack.core.entities.tag.handler import TagHandler
from laughtrack.core.entities.ticket.handler import TicketHandler
import psycopg2
from psycopg2.extras import DictRow
from sql.show_queries import ShowQueries

from laughtrack.foundation.models.operation_result import DatabaseOperationResult
from laughtrack.utilities.domain.show.utils import ShowUtils
from laughtrack.foundation.infrastructure.database.operation import DatabaseOperationLogger
from laughtrack.foundation.infrastructure.database.template import BatchTemplateGenerator
from laughtrack.foundation.infrastructure.logger.logger import Logger

from .model import Show


class ShowHandler(BaseDatabaseHandler[Show]):
    """Handler for show database operations."""

    # Constants for configuration
    DEFAULT_BATCH_SIZE = 100
    OPERATION_TYPE_INSERTED = "inserted"
    OPERATION_TYPE_UPDATED = "updated"
    OPERATION_TYPE_UNKNOWN = "unknown"

    def __init__(self):
        super().__init__()
        self.ticket_handler = TicketHandler()
        self.tag_handler = TagHandler()
        self.lineup_handler = LineupHandler()
        self.comedian_handler = ComedianHandler()

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "show"

    def get_entity_class(self) -> type[Show]:
        """Return the Show class for instantiation."""
        return Show

    def insert_shows(self,
                     shows: List[Show],
                     batch_size: int = DEFAULT_BATCH_SIZE,
                     club_name: Optional[str] = None) -> DatabaseOperationResult:
        """Save shows to database with full processing including tickets and tags.
        Processes shows in batches for optimal performance.

        Args:
            shows: List of shows to save
            batch_size: Size of each batch for processing
            club_name: Optional club name for error reporting in metrics

        Returns:
            DatabaseOperationResult with operation counts
        """
        total_items = len(shows)
        total_result = DatabaseOperationResult()
        successful_batches = 0
        failed_batches = 0

        Logger.info(f"Processing {total_items} shows in batches of {batch_size}")

        for i in range(0, total_items, batch_size):
            batch = shows[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_items + batch_size - 1) // batch_size

            try:
                Logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} shows)")

                batch_result = self._process_single_batch(batch)
                successful_batches += 1
                total_result += batch_result

            except psycopg2.DatabaseError as e:
                failed_batches += 1
                Logger.error(f"Database error processing batch {batch_num}/{total_batches}: {e}")
                total_result.db_errors += 1
                if club_name:
                    total_result.error_entries.append(
                        (club_name, f"DB error batch {batch_num}/{total_batches}: {e}")
                    )
                continue
            except ValueError as e:
                failed_batches += 1
                Logger.error(f"Validation error in batch {batch_num}/{total_batches}: {e}")
                total_result.validation_errors += 1
                if club_name:
                    total_result.error_entries.append(
                        (club_name, f"Validation error batch {batch_num}/{total_batches}: {e}")
                    )
                continue
            except Exception as e:
                failed_batches += 1
                Logger.error(f"Unexpected error processing batch {batch_num}/{total_batches}: {e}")
                total_result.errors += 1
                if club_name:
                    total_result.error_entries.append(
                        (club_name, f"Unexpected error batch {batch_num}/{total_batches}: {e}")
                    )
                continue

        return total_result

    def _create_show_results(self, updated_shows: List[Show]) -> List[Dict]:
        """Create show result dictionaries for logging and counting.

        Args:
            updated_shows: List of shows with database IDs populated

        Returns:
            List of show result dictionaries
        """
        show_results = []
        for show in updated_shows:
            if show.id is not None:
                show_result = {
                    "id": show.id,
                    "club_id": show.club_id,
                    "date": show.date.isoformat(),
                    "operation_type": show.operation_type or self.OPERATION_TYPE_UNKNOWN,
                }
                show_results.append(show_result)
        return show_results

    def _count_operation_types(self, show_results: List[Dict]) -> Tuple[int, int]:
        """Count insert and update operations from show results.

        Args:
            show_results: List of show result dictionaries

        Returns:
            Tuple of (inserts_count, updates_count)
        """
        inserts = sum(1 for result in show_results if result.get("operation_type", "") == self.OPERATION_TYPE_INSERTED)
        updates = sum(1 for result in show_results if result.get("operation_type", "") == self.OPERATION_TYPE_UPDATED)
        return inserts, updates

    def _build_items_and_template(self, batch: List[Show]) -> Tuple[List[tuple], str]:
        """Build batch items and the dynamic template for batch insertion."""
        items = [show.to_tuple() for show in batch]
        template = BatchTemplateGenerator.generate_dynamic_template(items)
        return items, template

    def _update_shows_and_related(
        self, batch: List[Show], results: List[DictRow]
    ) -> Tuple[List[Show], int, int]:
        """Update shows with DB results and process tickets, tags, and lineups.

        Returns:
            Tuple of (updated_shows, comedians_inserted, lineup_items_added).
        """
        # Update shows with database results
        updated_shows = ShowUtils.update_shows_with_results(batch, results)

        # Process tickets, tags, and lineups through their handlers
        self.ticket_handler.insert_tickets(updated_shows)
        self.tag_handler.process_show_tags(updated_shows)
        comedians_inserted, lineup_items_added = self.update_show_lineups(updated_shows)

        return updated_shows, comedians_inserted, lineup_items_added

    def _summarize_and_log(self, updated_shows: List[Show], batch_len: int) -> Tuple[int, int, List[Dict]]:
        """Create results payload, count operations, and log metrics."""
        show_results = self._create_show_results(updated_shows)
        inserts, updates = self._count_operation_types(show_results)

        # Log detailed metrics
        DatabaseOperationLogger.log_show_save_results(show_results, batch_len)

        return inserts, updates, show_results

    def _process_single_batch(self, batch: List[Show]) -> DatabaseOperationResult:
        """Process a single batch of shows.

        Args:
            batch: List of shows to process

        Returns:
            DatabaseOperationResult with operation counts

        Raises:
            ValueError: If no shows were inserted or updated
            psycopg2.DatabaseError: If database operation fails
        """
        if not batch:
            Logger.info("No shows to process in batch")
            return DatabaseOperationResult()

        # Validate and deduplicate
        batch, duplicate_details = ShowUtils.deduplicate_shows_with_details(batch)

        # Insert shows and get results
        Logger.info(f"Processing batch of {len(batch)} shows")
        items, template = self._build_items_and_template(batch)
        results = self.execute_batch_operation(ShowQueries.BATCH_INSERT_SHOWS, items, template, return_results=True)

        if not results:
            raise ValueError("No shows were inserted or updated")

        # Update shows and related entities, then summarize
        updated_shows, comedians_inserted, lineup_items_added = self._update_shows_and_related(batch, results)
        inserts, updates, show_results = self._summarize_and_log(updated_shows, len(batch))

        return DatabaseOperationResult(
            inserts=inserts,
            updates=updates,
            total=len(show_results),
            duplicate_details=duplicate_details,
            comedians_inserted=comedians_inserted,
            lineup_items_added=lineup_items_added,
        )

    def get_show_details(self, show_ids: List[int]) -> List[DictRow]:
        """Get detailed information for shows.

        Args:
            show_ids: List of show IDs to get details for

        Returns:
            List of dictionaries containing show details

        Raises:
            Exception: If database query fails
        """
        if not show_ids:
            Logger.warn("No show IDs provided for getting show details")
            return []

        try:
            return self.execute_with_cursor(ShowQueries.GET_SHOW_DETAILS, (show_ids,), return_results=True) or []
        except Exception as e:
            Logger.error(f"Error getting show details: {str(e)}")
            raise

    def get_all_show_ids(self) -> List[int]:
        """Get all show IDs from the database.

        Returns:
            List of all show IDs in the database

        Raises:
            Exception: If database query fails
        """
        try:
            results = self.execute_with_cursor(ShowQueries.GET_ALL_SHOW_IDS, return_results=True) or []
            return [row["id"] for row in results]
        except Exception as e:
            Logger.error(f"Error getting all show IDs: {str(e)}")
            raise

    def validate_show_ids(self, show_ids: List[int]) -> List[int]:
        """Validate that show IDs exist in the database.

        Args:
            show_ids: List of show IDs to validate

        Returns:
            List of validated show IDs that exist in the database

        Raises:
            Exception: If database query fails
        """
        if not show_ids:
            return []

        show_ids = list(dict.fromkeys(show_ids))

        try:
            results = self.execute_with_cursor(ShowQueries.VALIDATE_SHOW_IDS, (show_ids,), return_results=True) or []
            found_ids = [row["id"] for row in results]

            if not found_ids:
                Logger.warn("No matching shows found in database.")
                return []

            if len(found_ids) != len(show_ids):
                missing_ids = set(show_ids) - set(found_ids)
                Logger.warn(f"Warning: {len(missing_ids)} show IDs not found: {sorted(missing_ids)}")

            Logger.info(f"Validated {len(found_ids)} show IDs")
            return found_ids
        except Exception as e:
            Logger.error(f"Error validating show IDs: {str(e)}")
            raise

    def calculate_and_update_popularity(self, show_ids: List[int]) -> None:
        """Calculate and update popularity for a list of shows.

        Args:
            show_ids: List of show IDs to update

        Raises:
            Exception: If database operations fail
        """
        if not show_ids:
            Logger.info("No show IDs provided for popularity update")
            return

        try:
            Logger.info(f"Calculating popularity for {len(show_ids)} shows")

            # Get the popularity values
            results = self.execute_with_cursor(
                ShowQueries.BATCH_GET_LINEUP_POPULARITY, (show_ids,), return_results=True
            )

            if not results:
                Logger.info("No popularity results to update (no lineup data found)")
                return

            # Transform results for batch update
            result_show_ids = [int(row["show_id"]) for row in results]
            popularity_values = [float(row["modified_popularity"]) for row in results]

            # Update shows with new popularity values
            self.execute_with_cursor(ShowQueries.BATCH_UPDATE_SHOW_POPULARITY, (result_show_ids, popularity_values))

            Logger.info(f"Successfully updated popularity for {len(results)} shows")

        except Exception as e:
            Logger.error(f"Error calculating and updating show popularity: {str(e)}")
            raise

    def _extract_valid_show_ids(self, shows: List[Show]) -> List[int]:
        """Extract valid show IDs from a list of shows.

        Args:
            shows: List of shows to extract IDs from

        Returns:
            List of valid show IDs (non-None values)
        """
        return [show.id for show in shows if show.id is not None]

    def _process_comedian_additions(self, shows: List[Show], show_name_comedians_map: Dict) -> None:
        """Process comedian additions to show lineups based on show names.

        Args:
            shows: List of shows to update
            show_name_comedians_map: Mapping of show names to comedians
        """
        for show in shows:
            if show_name_comedians := show_name_comedians_map.get(show.name, []):
                existing_comedian_uuids = {comedian.uuid for comedian in show.lineup}
                novel_comedians = [
                    comedian for comedian in show_name_comedians if comedian.uuid not in existing_comedian_uuids
                ]
                if novel_comedians:
                    show.lineup.extend(novel_comedians)

    def _expand_multi_comedian_lineups(self, shows: List[Show]) -> None:
        """Expand lineup entries that contain multiple comedian names.

        For each show, splits combined names (e.g. "X & Y", "X with Y") into
        individual Comedian objects so each person gets their own lineup item.
        The original combined entry is replaced by the split parts.
        """
        from laughtrack.core.entities.comedian.model import Comedian

        for show in shows:
            expanded: List = []
            for comedian in show.lineup:
                parts = split_combined_name(comedian.name)
                if len(parts) > 1:
                    Logger.info(
                        f"lineup_split: '{comedian.name}' → {parts}"
                    )
                    for part in parts:
                        expanded.append(Comedian(name=part))
                else:
                    expanded.append(comedian)
            if len(expanded) != len(show.lineup):
                # Deduplicate by UUID in case a split name already exists in the lineup
                seen_uuids = set()
                deduped = []
                for c in expanded:
                    if c.uuid not in seen_uuids:
                        seen_uuids.add(c.uuid)
                        deduped.append(c)
                show.lineup = deduped

    def update_show_lineups(self, shows: List[Show]) -> Tuple[int, int]:
        """Update lineups for shows with full processing including comedian popularity updates.

        Args:
            shows: List of shows to update

        Returns:
            Tuple of (comedians_inserted, lineup_items_added).

        Raises:
            Exception: If database operations fail
        """
        if not shows:
            Logger.info("No shows provided for lineup update")
            return 0, 0

        try:
            # Extract valid show IDs
            show_ids = self._extract_valid_show_ids(shows)

            # Get current lineups from database
            db_lineups = self.lineup_handler.get_lineup(show_ids)

            # Get all comedians from show names in one batch
            show_names = [(show.name,) for show in shows]
            show_name_comedians_map = self.lineup_handler.get_comedians_from_show_names(show_names)

            # Process comedian additions in memory
            self._process_comedian_additions(shows, show_name_comedians_map)

            # Split multi-comedian lineup entries (e.g. "X & Y") into individual items
            self._expand_multi_comedian_lineups(shows)

            # Insert any new comedians before updating lineup links.
            # Determine denied and false-positive names first so we can strip them
            # from show.lineup too — these comedians are never inserted, so their
            # UUIDs would cause FK violations in batch_update_lineups if left in
            # the lineup lists.
            all_comedians = list({comedian for show in shows for comedian in show.lineup})
            comedians_inserted = 0
            if all_comedians:
                allowed_comedians = self.comedian_handler._filter_denied_comedians(all_comedians)
                denied_names = {c.name for c in all_comedians} - {c.name for c in allowed_comedians}
                if denied_names:
                    for show in shows:
                        show.lineup = [c for c in show.lineup if c.name not in denied_names]

                # False-positive comedians are also filtered here so their UUIDs
                # don't reach batch_update_lineups. Pass pre_filtered=True since
                # we've already applied both deny-list and FP filters.
                fp_allowed = self.comedian_handler._filter_false_positive_comedians(allowed_comedians)
                fp_names = {c.name for c in allowed_comedians} - {c.name for c in fp_allowed}
                if fp_names:
                    for show in shows:
                        show.lineup = [c for c in show.lineup if c.name not in fp_names]

                inserted_rows = self.comedian_handler.insert_comedians(fp_allowed, pre_filtered=True)
                comedians_inserted = len(inserted_rows)

                # Source images for newly inserted comedians (non-blocking —
                # source_images_for_new_comedians catches all exceptions internally)
                if inserted_rows:
                    inserted_uuids = {row["uuid"] for row in inserted_rows}
                    new_names = [c.name for c in fp_allowed if c.uuid in inserted_uuids]
                    self.comedian_handler.source_images_for_new_comedians(new_names)

            # Batch update all lineups at once
            lineup_items_added, _ = self.lineup_handler.batch_update_lineups(shows, db_lineups)

            # Collect all comedian UUIDs and update popularity
            comedian_uuids = ShowUtils.collect_comedian_uuids(shows)
            if comedian_uuids:
                self.comedian_handler.update_comedian_popularity(comedian_uuids)

            # Calculate and update popularity for all shows in batch
            self.calculate_and_update_popularity(show_ids)

            Logger.info(f"Successfully updated lineups for {len(shows)} shows")
            return comedians_inserted, lineup_items_added

        except Exception as e:
            Logger.error(f"Error updating show lineups (non-fatal): {str(e)}")
            return 0, 0
