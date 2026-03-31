"""Pure JSON manipulation utilities with no domain dependencies."""

import json
import logging
import re
from typing import Any, List, Optional, Union

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict, JSONValue, T
from gioe_libs.string_utils import StringUtils


class JSONUtils:
    """Pure JSON manipulation and parsing utilities."""

    @staticmethod
    def safe_loads(json_str: str, default: Any = None) -> Any:
        """
        Safely parse JSON string with fallback.

        Args:
            json_str: JSON string to parse
            default: Default value if parsing fails

        Returns:
            Parsed JSON object or default value
        """
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            logging.getLogger(__name__).warning(f"JSON parsing failed: {e}")
            return default

    @staticmethod
    def safe_dumps(obj: Any, default: Any = None, **kwargs) -> str:
        """
        Safely serialize object to JSON string.

        Args:
            obj: Object to serialize
            default: Default value if serialization fails
            **kwargs: Additional arguments for json.dumps

        Returns:
            JSON string or empty string if failed
        """
        try:
            return json.dumps(obj, **kwargs)
        except (TypeError, ValueError) as e:
            logging.getLogger(__name__).warning(f"JSON serialization failed: {e}")
            return default or ""

    @staticmethod
    def clean_javascript_json(json_str: str) -> str:
        """
        Clean a JSON string extracted from JavaScript code to make it parseable.

        This method handles common issues when extracting JSON objects from
        JavaScript code embedded in HTML pages.

        Args:
            json_str: Raw JSON string from JavaScript

        Returns:
            Cleaned JSON string that can be parsed by json.loads()
        """
        try:
            # Fix common escape sequence issues that break JSON parsing
            cleaned = json_str

            # First, temporarily replace already properly escaped sequences
            temp_replacements = {
                '\\"': "___ESCAPED_QUOTE___",
                "\\\\": "___ESCAPED_BACKSLASH___",
                "\\n": "___ESCAPED_NEWLINE___",
                "\\t": "___ESCAPED_TAB___",
                "\\r": "___ESCAPED_RETURN___",
                "\\/": "___ESCAPED_SLASH___",
            }

            for original, temp in temp_replacements.items():
                cleaned = cleaned.replace(original, temp)

            # Now escape any remaining unescaped backslashes
            cleaned = cleaned.replace("\\", "\\\\")

            # Restore the properly escaped sequences
            for original, temp in temp_replacements.items():
                cleaned = cleaned.replace(temp, original)

            return cleaned

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Error cleaning JSON string: {str(e)}")
            return json_str  # Return original if cleaning fails

    @staticmethod
    def clean_quotes(json_str: str) -> str:
        """
        Convert single quotes to double quotes in JSON string.

        Args:
            json_str: JSON string that may contain single quotes

        Returns:
            JSON string with properly escaped double quotes
        """
        try:
            # Fix single-quoted keys: 'key' -> "key"
            cleaned = re.sub(r"'([^']*)'(\s*:\s*)", r'"\1"\2', json_str)

            # Fix single-quoted string values: : 'value' -> : "value"
            cleaned = re.sub(r"(\s*:\s*)\'([^\']*)\'", r'\1"\2"', cleaned)

            return cleaned

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Error cleaning quotes in JSON string: {str(e)}")
            return json_str

    @staticmethod
    def remove_trailing_commas(json_str: str) -> str:
        """
        Remove trailing commas from JSON objects and arrays.

        Args:
            json_str: JSON string that may contain trailing commas

        Returns:
            JSON string with trailing commas removed
        """
        try:
            # Remove trailing commas before closing braces/brackets
            cleaned = re.sub(r",(\s*[}\]])", r"\1", json_str)
            return cleaned

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Error removing trailing commas: {str(e)}")
            return json_str

    @staticmethod
    def comprehensive_clean(json_str: str) -> str:
        """
        Apply all cleaning operations to a JSON string.

        Args:
            json_str: Raw JSON string from JavaScript

        Returns:
            Cleaned JSON string ready for parsing
        """
        cleaned = json_str

        # Apply all cleaning operations in order
        cleaned = JSONUtils.clean_javascript_json(cleaned)
        cleaned = JSONUtils.clean_quotes(cleaned)
        cleaned = JSONUtils.remove_trailing_commas(cleaned)

        return cleaned

    @staticmethod
    def extract_json_variable(html_content: str, variable_name: str) -> Optional[Any]:
        """
        Extract a JSON object assigned to a JavaScript variable in HTML.

        Looks for patterns like:
            var EVENT = {"event_id": "123", ...};

        Uses json.JSONDecoder.raw_decode() so semicolons and closing braces
        inside string values (e.g. HTML entities, formatted text) never
        terminate the extraction early.

        Args:
            html_content: HTML content containing JavaScript
            variable_name: JavaScript variable name (e.g. "EVENT")

        Returns:
            Parsed Python object (dict, list, etc.) or None if not found /
            not parseable.
        """
        import json as _json

        marker = f"var {variable_name} = {{"
        idx = html_content.find(marker)
        if idx == -1:
            return None

        start = idx + len(marker) - 1  # position of the opening '{'
        try:
            obj, _ = _json.JSONDecoder().raw_decode(html_content, start)
            return obj
        except (_json.JSONDecodeError, ValueError):
            return None

    @staticmethod
    def extract_variable_assignments(html_content: str, variable_name: str) -> List[str]:
        """
        Extract variable assignments from JavaScript code.

        .. deprecated::
            Use :meth:`extract_json_variable` instead.
            This method uses a semicolon-terminated non-greedy regex
            (``(.+?);``) that truncates the match at the first ``;`` inside
            the value — breaking on HTML entities (``&amp;``) and any other
            embedded semicolons.  ``extract_json_variable`` uses
            ``json.JSONDecoder.raw_decode()`` and handles all JSON-legal
            content correctly.

        Args:
            html_content: HTML content containing JavaScript
            variable_name: Name of the JavaScript variable to extract

        Returns:
            List of extracted variable values
        """
        pattern = rf"{re.escape(variable_name)}\s*=\s*(.+?);"
        matches = re.findall(pattern, html_content, re.DOTALL)
        return matches

    @staticmethod
    def extract_function_calls(html_content: str, function_name: str) -> List[str]:
        """
        Extract function calls from JavaScript code.

        Args:
            html_content: HTML content containing JavaScript
            function_name: Name of the JavaScript function

        Returns:
            List of extracted function arguments
        """
        pattern = rf"{re.escape(function_name)}\((.+?)\);"
        matches = re.findall(pattern, html_content, re.DOTALL)
        return matches

    @staticmethod
    def deep_get(data: JSONDict, key_path: str, default: Any = None, separator: str = ".") -> Any:
        """
        Get nested value from dictionary using dot notation.

        Args:
            data: Dictionary to search
            key_path: Dot-separated path to value (e.g., "user.profile.name")
            default: Default value if key not found
            separator: Separator character for key path

        Returns:
            Value at key path or default
        """
        keys = key_path.split(separator)
        current = data

        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return current
        except (KeyError, TypeError):
            return default

    @staticmethod
    def flatten_dict(data: JSONDict, separator: str = ".", parent_key: str = "") -> JSONDict:
        """
        Flatten nested dictionary using separator.

        Args:
            data: Dictionary to flatten
            separator: Separator for flattened keys
            parent_key: Current parent key (used for recursion)

        Returns:
            Flattened dictionary
        """
        items = []

        for key, value in data.items():
            new_key = f"{parent_key}{separator}{key}" if parent_key else key

            if isinstance(value, dict):
                items.extend(JSONUtils.flatten_dict(value, separator, new_key).items())
            else:
                items.append((new_key, value))

        return dict(items)

    @staticmethod
    def parse_json_list(
        json_strings: List[str], logger_context: JSONDict, max_error_details: int = 3
    ) -> List[JSONValue]:
        parsed_objects = []
        parse_failures = []

        for i, json_string in enumerate(json_strings):
            try:
                parsed_obj = json.loads(json_string)
                parsed_objects.append(parsed_obj)
            except (json.JSONDecodeError, ValueError) as e:
                # Capture failure details for debugging
                snippet = json_string[:200] if len(json_string) > 200 else json_string
                parse_failures.append({"index": i, "error": str(e), "snippet": snippet})

        # Log results with failure details
        if parse_failures:
            Logger.warning(f"Failed to parse {len(parse_failures)}/{len(json_strings)} JSON strings", logger_context)
            # Log first few failures for debugging
            for failure in parse_failures[:max_error_details]:
                Logger.debug(
                    f"Parse failure at index {failure['index']}: {failure['error']} - snippet: {failure['snippet'][:100]}...",
                    logger_context,
                )

        Logger.info(f"Successfully parsed {len(parsed_objects)} JSON objects", logger_context)

        return parsed_objects

    @staticmethod
    def parse_single_json(
        json_string: str, logger_context: JSONDict, fallback_value: Optional[T] = None
    ) -> Union[Any, T]:
        """
        Parse a single JSON string with error logging.

        Args:
            json_string: JSON string to parse
            logger_context: Logger context for error reporting
            fallback_value: Value to return on parse failure

        Returns:
            Parsed JSON object or fallback_value on failure
        """
        try:
            return json.loads(json_string)
        except (json.JSONDecodeError, ValueError) as e:
            snippet = json_string[:200] if len(json_string) > 200 else json_string
            Logger.warning(f"Failed to parse JSON - {str(e)} - snippet: {snippet[:100]}...", logger_context)
            return fallback_value

    @staticmethod
    def safe_json_loads(
        json_string: str,
        default: Optional[T] = None,
        logger_context: Optional[JSONDict] = None,
    ) -> Union[Any, T]:
        """
        Safe JSON parsing with optional logging.

        Lightweight wrapper for cases where detailed error tracking isn't needed.

        Args:
            json_string: JSON string to parse
            default: Default value on parse failure
            logger_context: Optional logger context

        Returns:
            Parsed JSON object or default value on failure
        """
        try:
            return json.loads(json_string)
        except (json.JSONDecodeError, ValueError) as e:
            if logger_context:
                Logger.debug(f"JSON parse error - {str(e)}", logger_context)
            return default

    @staticmethod
    def parse_json_ld_contents(script_contents: List[str]) -> List[JSONDict]:
        """
        Parse JSON-LD script contents into structured data.

        Args:
            script_contents: List of raw JSON-LD script contents to parse

        Returns:
            List[JSONDict]: List of parsed JSON-LD objects
        """
        json_ld_objects = []

        for content in script_contents:
            try:
                # Clean the content using StringUtils
                cleaned_content = StringUtils.clean_html_content(content)
                if not cleaned_content:
                    continue

                data = json.loads(cleaned_content)

                # Handle both single objects and arrays
                if isinstance(data, list):
                    json_ld_objects.extend(data)
                else:
                    json_ld_objects.append(data)

            except (json.JSONDecodeError, TypeError):
                continue
            except Exception:
                # Silently continue on other parsing errors
                continue

        return json_ld_objects
