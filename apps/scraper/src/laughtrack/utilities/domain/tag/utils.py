"""Pure formatting utilities with no domain dependencies."""


class TagUtils:
    """Pure utility class for text and string formatting operations."""

    @staticmethod
    def standardize_tag_string(tag: str) -> str:
        """
        Standardize a tag string for consistent formatting.

        Performs comprehensive tag normalization:
        - Removes whitespace
        - Removes hashtags
        - Converts to lowercase
        - Replaces spaces with underscores
        - Removes duplicate underscores

        Args:
            tag: Tag string to standardize

        Returns:
            Standardized tag string
        """
        # Remove bad whitespace
        tag = tag.strip()
        # Remove hashtag
        tag = tag.replace("#", "")
        # Convert to lowercase
        tag = tag.lower()
        # Replace spaces with underscores
        tag = tag.replace(" ", "_")
        # Remove any double underscores
        tag = tag.replace("__", "_")
        return tag
