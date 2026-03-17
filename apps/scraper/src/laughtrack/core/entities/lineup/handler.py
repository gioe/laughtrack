"""Lineup database handler for lineup-specific operations."""

from typing import Dict, List

from laughtrack.core.data.base_handler import BaseDatabaseHandler
from sql.lineup_queries import LineupQueries

from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.database.template import BatchTemplateGenerator
from laughtrack.foundation.infrastructure.logger.logger import Logger

from .model import LineupItem


class LineupHandler(BaseDatabaseHandler[LineupItem]):
    """Handler for lineup database operations."""

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "lineup_item"

    def get_entity_class(self) -> type[LineupItem]:
        """Return the LineupItem class for instantiation."""
        return LineupItem

    def batch_update_lineups(self, shows: List[Show], current_lineups: Dict[int, List[Comedian]]) -> None:
        """
        Update lineups for multiple shows in batch.

        Args:
            shows: List of shows to update
            current_lineups: Dictionary mapping show IDs to their current lineups
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

        # First insert any new comedians into the database
        all_comedians = list({comedian for show in shows for comedian in show.lineup})
        if all_comedians:
            comedian_handler = ComedianHandler()
            comedian_handler.insert_comedians(all_comedians)

        # Then perform batch lineup updates
        if to_remove:
            self.batch_delete_lineup_items(to_remove)
        if to_add:
            self.batch_add_lineup_items(to_add)

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
            results = self.execute_batch_operation(
                LineupQueries.BATCH_GET_COMEDIANS_FROM_SHOW_NAME,
                show_names,
                template=BatchTemplateGenerator.get_single_field_template(),
                return_results=True,
            )

            if not results:
                return {}

            show_comedians_map = {}
            for row in results:
                comedian = Comedian.from_db_row(row)
                show_name = row["show_name"]
                if show_name not in show_comedians_map:
                    show_comedians_map[show_name] = []
                show_comedians_map[show_name].append(comedian)
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
