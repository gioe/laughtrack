"""
Batch Template Generator

Utility for generating SQL parameter templates for batch database operations.
Generates parameterized templates like (%s,%s,%s) for use with psycopg2 batch operations.
"""

from typing import Any, List, Tuple


class BatchTemplateGenerator:
    """Generates SQL parameter templates for batch database operations."""

    @staticmethod
    def generate_dynamic_template(items: List[Tuple[Any, ...]]) -> str:
        """
        Generate a template dynamically based on the structure of the items.

        Args:
            items: List of tuples representing the data structure

        Returns:
            SQL parameter template string like "(%s,%s,%s)"

        Raises:
            ValueError: If items list is empty
        """
        if not items:
            raise ValueError("Cannot generate template from empty items list")

        # Use the first item to determine the number of fields
        field_count = len(items[0])
        return BatchTemplateGenerator.generate_fixed_template(field_count)

    @staticmethod
    def generate_fixed_template(field_count: int) -> str:
        """
        Generate a template for a fixed number of fields.

        Args:
            field_count: Number of fields in the template

        Returns:
            SQL parameter template string like "(%s,%s,%s)"

        Raises:
            ValueError: If field_count is not positive
        """
        if field_count <= 0:
            raise ValueError("Field count must be positive")

        placeholders = ",".join(["%s"] * field_count)
        return f"({placeholders})"

    @staticmethod
    def get_two_field_template() -> str:
        """
        Get the commonly used two-field template.

        Returns:
            Two-field template string "(%s,%s)"
        """
        return "(%s,%s)"

    @staticmethod
    def get_single_field_template() -> str:
        """
        Get the commonly used single-field template.

        Returns:
            Single-field template string "(%s)"
        """
        return "(%s)"

    @staticmethod
    def get_template_from_sample(sample_tuple: Tuple[Any, ...]) -> str:
        """
        Generate a template from a sample tuple.

        Args:
            sample_tuple: Sample tuple to determine structure

        Returns:
            SQL parameter template string
        """
        field_count = len(sample_tuple)
        return BatchTemplateGenerator.generate_fixed_template(field_count)

    @staticmethod
    def get_three_field_template() -> str:
        """
        Get the commonly used three-field template.

        Returns:
            Three-field template string "(%s,%s,%s)"
        """
        return "(%s,%s,%s)"

    @staticmethod
    def get_four_field_template() -> str:
        """
        Get the commonly used four-field template.

        Returns:
            Four-field template string "(%s,%s,%s,%s)"
        """
        return "(%s,%s,%s,%s)"

    @staticmethod
    def get_five_field_template() -> str:
        """
        Get the commonly used five-field template.

        Returns:
            Five-field template string "(%s,%s,%s,%s,%s)"
        """
        return "(%s,%s,%s,%s,%s)"
