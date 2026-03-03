"""Tag database handler for tag-specific operations."""

from typing import Any, Dict, List, Tuple

from sql.tag_queries import TagQueries

from laughtrack.foundation.models.types import JSONDict
from laughtrack.core.data.base_handler import BaseDatabaseHandler
from laughtrack.core.entities.show.model import Show
from laughtrack.utilities.domain.tag.utils import TagUtils
from laughtrack.foundation.infrastructure.database.template import BatchTemplateGenerator
from laughtrack.foundation.infrastructure.logger.logger import Logger

from .model import Tag


class TagHandler(BaseDatabaseHandler[Tag]):
    """Handler for tag database operations."""

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "tag"

    def get_entity_class(self) -> type[Tag]:
        """Return the Tag class for instantiation."""
        return Tag

    def standardize_tag_string(self, tag: str) -> str:
        """
        Standardize a tag string for storage.

        Delegates to FormattingUtils for consistent tag formatting across the application.
        """
        return TagUtils.standardize_tag_string(tag)

    def transform_tag_string(self, tag_str: str) -> tuple:
        """Transform tag string to database tuple format."""
        # Use the standardized formatting utility for consistent tag processing
        standardized_tag = TagUtils.standardize_tag_string(tag_str)

        # Handle multiple underscores with regex (additional processing beyond basic standardization)
        import re

        standardized_tag = re.sub(r"_+", "_", standardized_tag)

        return ("show", False, tag_str, False, standardized_tag, "ADMIN")

    def get_tags_for_shows(self, show_ids: List[int]) -> Dict[int, List[JSONDict]]:
        """
        Get tags for a list of shows.

        Args:
            show_ids: List of show IDs to get tags for

        Returns:
            Dictionary mapping show IDs to their tags
        """
        try:
            results = self.execute_with_cursor(TagQueries.GET_TAGS_FOR_SHOWS, (show_ids,), return_results=True) or []

            # Group tags by show ID
            tags_by_show = {}
            for row in results:
                show_id = row["show_id"]
                if show_id not in tags_by_show:
                    tags_by_show[show_id] = []

                tags_by_show[show_id].append(row["slug"])

            return tags_by_show

        except Exception as e:
            Logger.error(f"Error getting tags for shows: {str(e)}")
            raise

    def process_show_tags(self, shows: List[Show]) -> None:
        """
        Process all tags for a list of shows.

        Args:
            conn: Database connection
            shows: List of Show objects
        """
        Logger.info("Processing show tags")

        # Insert new tags and get show-tag mappings
        show_tag_tuples = self.insert_tags(shows)

        # Get existing tags from show names
        show_name_tag_tuples = self.get_tags_from_show_names(shows)

        all_tag_pairs = (
            show_tag_tuples
            + show_name_tag_tuples
            + [
                (show.id, price_tag)
                for show in shows
                for ticket in show.tickets
                if (price_tag := ticket.price_tag) is not None and show.id is not None
            ]
        )
        # Add all tags to shows
        self.add_tags_to_shows(all_tag_pairs)

    def transform_tag(self, tag: str) -> tuple:
        """
        Transform tag string to database tuple.

        Args:
            tag: Tag string to transform

        Returns:
            Tuple of tag data in database format
        """
        return ("show", self.standardize_tag_string(tag))

    def insert_tags(self, shows: List[Show]) -> List[tuple[int, int]]:
        """
        Insert tags for shows into the database.

        Args:
            conn: Database connection
            shows: List of Show

        Returns:
            List of (show_id, tag_id) tuples
        """
        # Collect unique tags and show mappings
        new_tags = {
            self.transform_tag(tag)
            for show in shows
            for tag in show.supplied_tags
            if (normalized_tag := self.standardize_tag_string(tag))
        }

        # Build show tag mapping
        show_tag_map = {}
        for show in shows:
            for tag in show.supplied_tags:
                if normalized_tag := self.standardize_tag_string(tag):
                    show_tag_map.setdefault(normalized_tag, []).append((show.id, show.name))

        if not new_tags:
            Logger.info("No tags to insert")
            return []

        # Insert tags and map results
        try:
            items = list(new_tags)
            template = BatchTemplateGenerator.generate_dynamic_template(items)
            results = self.execute_batch_operation(
                TagQueries.BATCH_ADD_TAGS, items, template=template, return_results=True
            )

            if not results:
                raise ValueError("No tags were inserted")

            # Map results back to shows
            result_pairs = []
            for tag_id, slug in results:
                if slug in show_tag_map:
                    for show_id, _ in show_tag_map[slug]:
                        if show_id is not None:  # Filter out None show IDs
                            result_pairs.append((show_id, tag_id))
            return result_pairs

        except Exception as e:
            Logger.error(f"Error inserting tags: {str(e)}")
            raise

    def get_tags_from_show_names(self, shows: List[Show]) -> List[tuple[int, int]]:
        """
        Get tags associated with show names.

        Args:
            shows: List of Show objects

        Returns:
            List of (show_id, tag_id) tuples
        """
        show_names = [show.name for show in shows]
        show_name_to_id = {show.name: show.id for show in shows}

        try:
            results = (
                self.execute_with_cursor(TagQueries.BATCH_GET_TAGS_FROM_SHOW_NAME, (show_names,), return_results=True)
                or []
            )

            result_pairs = []
            for tag_id, show_name in results:
                show_id = show_name_to_id[show_name]
                if show_id is not None:  # Filter out None show IDs
                    result_pairs.append((show_id, tag_id))
            return result_pairs
        except Exception as e:
            raise

    def add_tags_to_shows(self, tag_pairs: List[Tuple[int, int]]) -> None:
        """
        Add tags to shows in the database.

        Args:
            conn: Database connection
            show_tag_pairs: List of (show_id, tag_id) tuples for show tags
            price_tags: List of (show_id, tag_id) tuples for price tags
        """
        if not tag_pairs:
            Logger.info("No tags to add to shows")
            return

        try:
            self.execute_batch_operation(
                TagQueries.ADD_TAGS_TO_SHOW, tag_pairs, template=BatchTemplateGenerator.get_two_field_template()
            )
        except Exception as e:
            Logger.error(f"Error adding tags to shows: {str(e)}")
            raise
