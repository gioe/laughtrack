"""Comedian database handler for comedian-specific operations."""

from typing import List, Optional

from psycopg2.extras import DictRow
from laughtrack.core.data.base_handler import BaseDatabaseHandler
from sql.comedian_queries import ComedianQueries

from laughtrack.foundation.infrastructure.database.template import BatchTemplateGenerator
from laughtrack.foundation.infrastructure.logger.logger import Logger

from .model import Comedian


class ComedianHandler(BaseDatabaseHandler[Comedian]):
    """Handler for comedian database operations."""

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "comedian"

    def get_entity_class(self) -> type[Comedian]:
        """Return the Comedian class for instantiation."""
        return Comedian

    def insert_comedians(self, comedians: List[Comedian]) -> List[DictRow]:
        """
        Insert comedians into the database.

        Uses ON CONFLICT DO NOTHING so that name-only stubs created during lineup
        extraction (e.g. from StandupNY) never overwrite existing comedian data
        (follower counts, social accounts, show stats).  Callers should not rely on
        the return value to detect pre-existing comedians; an empty list means all
        provided comedians were already present.

        Args:
            comedians: List of comedians to insert

        Returns:
            List of newly inserted comedian rows (empty when all already existed)
        """
        if not comedians:
            raise ValueError("No comedians to insert")

        try:
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

            return results or []
        except Exception as e:
            Logger.error(f"Error inserting comedians: {str(e)}")
            raise

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
            updated_count = self.execute_batch_operation(
                ComedianQueries.BATCH_UPDATE_COMEDIAN_POPULARITY, items, return_results=True
            )

            if not updated_count:
                raise ValueError("No comedians were updated")

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

    def _get_comedian_uuids(self, comedian_ids: Optional[List[str]] = None) -> List[str]:
        """Get the list of comedian UUIDs to process."""
        if comedian_ids:
            # Verify the provided UUIDs exist
            results = self.execute_with_cursor(
                ComedianQueries.GET_TARGET_COMEDIAN_IDS, (comedian_ids,), return_results=True
            )

            if not results:
                raise ValueError("No matching comedians found in database")

            found_uuids = [row.get("uuid") for row in results]

            if len(found_uuids) != len(comedian_ids):
                missing_count = len(comedian_ids) - len(found_uuids)
                Logger.warn(f"Warning: {missing_count} comedian UUIDs not found in database")
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
