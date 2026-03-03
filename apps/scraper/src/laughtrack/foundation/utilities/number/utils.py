"""
Number utilities for validation and conversion operations.

Pure utilities with no domain dependencies. These can be used anywhere
in the application without causing circular imports.
"""

import re
from typing import Any, List, Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger


class NumberUtils:
    """Pure utility class for number validation and manipulation operations."""

    @staticmethod
    def validate_positive_number(value: Any, field_name: str, allow_zero: bool = True) -> Optional[str]:
        """
        Validate that a value is a positive number.

        Args:
            value: Value to validate
            field_name: Name of field for error messages
            allow_zero: Whether zero is allowed

        Returns:
            Error message if invalid, None if valid
        """
        if not isinstance(value, (int, float)):
            return f"{field_name} must be a number"

        min_value = 0 if allow_zero else 0.01
        if value < min_value:
            comparison = "non-negative" if allow_zero else "positive"
            return f"{field_name} must be a {comparison} number"

        return None

    @staticmethod
    def safe_float_conversion(value: Any, default: float = 0.0) -> float:
        """
        Safely convert a value to float with default fallback.

        Args:
            value: Value to convert
            default: Default value if conversion fails

        Returns:
            Float value or default
        """
        if value is None:
            return default

        try:
            return float(value)
        except (ValueError, TypeError):
            Logger.warning(f"Could not convert '{value}' to float, using default {default}")
            return default

    @staticmethod
    def safe_int_conversion(value: Any, default: int = 0) -> int:
        """
        Safely convert a value to int with default fallback.

        Args:
            value: Value to convert
            default: Default value if conversion fails

        Returns:
            Integer value or default
        """
        if value is None:
            return default

        try:
            return int(value)
        except (ValueError, TypeError):
            Logger.warning(f"Could not convert '{value}' to int, using default {default}")
            return default

    @staticmethod
    def extract_numbers(text: str) -> List[str]:
        """Extract all numbers from text."""
        return re.findall(r"\d+", text)

    @staticmethod
    def extract_decimal_numbers(text: str) -> List[str]:
        """Extract all decimal numbers from text."""
        return re.findall(r"\d+\.\d+", text)

    @staticmethod
    def is_valid_integer(value: str) -> bool:
        """
        Check if a string represents a valid integer.

        Args:
            value: String to check

        Returns:
            True if string represents a valid integer
        """
        if not value:
            return False

        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_valid_float(value: str) -> bool:
        """
        Check if a string represents a valid float.

        Args:
            value: String to check

        Returns:
            True if string represents a valid float
        """
        if not value:
            return False

        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def clamp(value: float, min_value: float, max_value: float) -> float:
        """
        Clamp a value between min and max bounds.

        Args:
            value: Value to clamp
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            Clamped value
        """
        return max(min_value, min(value, max_value))

    @staticmethod
    def round_to_decimal_places(value: float, decimal_places: int = 2) -> float:
        """
        Round a float to specified decimal places.

        Args:
            value: Value to round
            decimal_places: Number of decimal places

        Returns:
            Rounded value
        """
        return round(value, decimal_places)
