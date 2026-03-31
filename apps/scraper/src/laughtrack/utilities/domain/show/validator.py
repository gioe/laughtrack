"""
Show Validator

Utility for validating Show objects before database operations.
Provides comprehensive validation of show data integrity.
"""

from typing import Any, List, Optional, Tuple
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.utilities.number.utils import NumberUtils
from gioe_libs.string_utils import StringUtils
from laughtrack.utilities.domain.show.utils import ShowUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.foundation.utilities.url.utils import URLUtils


class ShowValidator:
    """Utility for validating Show objects before database operations."""

    @staticmethod
    def validate_shows(shows: List[Show]) -> Tuple[List[Show], List[str]]:
        """
        Validate a list of shows and return valid shows with error messages.

        Args:
            shows: List of Show objects to validate

        Returns:
            Tuple of (valid_shows, error_messages)
        """
        valid_shows = []
        error_messages = []

        for i, show in enumerate(shows):
            validation_errors = ShowValidator._validate_single_show(show)

            if validation_errors:
                error_msg = f"Show {i+1} validation failed: {'; '.join(validation_errors)}"
                error_messages.append(error_msg)
                Logger.warn(f"Invalid show: {show.name} - {'; '.join(validation_errors)}")
            else:
                valid_shows.append(show)

        # Log validation summary
        total_shows = len(shows)
        valid_count = len(valid_shows)
        ShowValidator.log_validation_summary(total_shows, valid_count, "shows")

        return valid_shows, error_messages

    @staticmethod
    def validate_cross_record(shows: List[Show]) -> List[str]:
        """Validate only cross-record allowances that require batch context.

        - Detect duplicate unique keys within the batch.
        - Optional: detect conflicting data for the same key (e.g., different names/rooms)

        Returns a list of error messages; an empty list means OK.
        """
        errors: List[str] = []

        if not shows:
            return errors

        # Generic duplicate detection for any DatabaseEntity
        from laughtrack.foundation.utilities.entity.validation import detect_duplicate_keys

        dups = detect_duplicate_keys(shows)
        if dups:
            sample = list(dups.items())[:5]
            sample_str = ", ".join([f"(club_id={k[0]}, date={k[1]}, room='{k[2]}') x{c}" for k, c in sample])
            more = "" if len(dups) <= 5 else f" (+{len(dups)-5} more)"
            Logger.warning(f"Duplicate show keys detected in batch: {sample_str}{more}")

        return errors

    @staticmethod
    def _validate_single_show(show: Show) -> List[str]:
        """
        Validate a single show object.

        Args:
            show: Show object to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate required fields using common utilities
        name_error = ShowValidator.validate_required_string(show.name, "Show name")
        if name_error:
            errors.append(name_error)
            ShowValidator._log_invalid_field("name", show.name, show, name_error)

        club_id_error = NumberUtils.validate_positive_number(show.club_id, "Club ID", allow_zero=False)
        if club_id_error:
            errors.append(club_id_error)
            ShowValidator._log_invalid_field("club_id", show.club_id, show, club_id_error)

        date_error = DateTimeUtils.validate_datetime(show.date, "Show date")
        if date_error:
            errors.append(date_error)
            ShowValidator._log_invalid_field("date", show.date, show, date_error)

        url_error = ShowValidator.validate_required_string(show.show_page_url, "Show page URL")
        if url_error:
            errors.append(url_error)
            ShowValidator._log_invalid_field("show_page_url", show.show_page_url, show, url_error)
        else:
            if not URLUtils.is_valid_url(show.show_page_url):
                ShowValidator._log_invalid_field("show_page_url", show.show_page_url, show, "Show page URL must be a valid URL format")
                errors.append("Show page URL must be a valid URL format")

        # Validate lineup
        if show.lineup:
            lineup_errors = ShowValidator._validate_lineup(show.lineup)
            if lineup_errors:
                ShowValidator._log_invalid_field("lineup", show.lineup, show, "; ".join(lineup_errors))
                errors.extend(lineup_errors)

        # Validate tickets
        if show.tickets:
            ticket_errors = ShowValidator._validate_tickets(show.tickets)
            if ticket_errors:
                ShowValidator._log_invalid_field("tickets", show.tickets, show, "; ".join(ticket_errors))
                errors.extend(ticket_errors)

        # Validate popularity score using common utilities
        popularity_error = NumberUtils.validate_positive_number(show.popularity, "Popularity score")
        if popularity_error:
            errors.append(popularity_error)
            ShowValidator._log_invalid_field("popularity", show.popularity, show, popularity_error)

        # Validate supplied tags
        if show.supplied_tags:
            if not isinstance(show.supplied_tags, list):
                errors.append("Supplied tags must be a list")
                ShowValidator._log_invalid_field("supplied_tags", show.supplied_tags, show, "Supplied tags must be a list")
            else:
                for tag in show.supplied_tags:
                    if not isinstance(tag, str) or not tag.strip():
                        errors.append("All supplied tags must be non-empty strings")
                        ShowValidator._log_invalid_field("supplied_tags", show.supplied_tags, show, "All supplied tags must be non-empty strings")
                        break

        return errors

    @staticmethod
    def _log_invalid_field(field: str, value: Any, show: Show, reason: str) -> None:
        """Log a standardized validation failure with offending value and show context."""
        try:
            value_str = str(value)
        except Exception:
            value_str = repr(value)

        if isinstance(value_str, str) and len(value_str) > 512:
            value_str = value_str[:512] + "...(truncated)"

        Logger.warn(
            f"Validation failed for {field}: {reason}",
            context={
                "field": field,
                "offending_value": value_str,
                "club_id": getattr(show, "club_id", "-"),
                "show_name": getattr(show, "name", "-"),
                "date": show.date.isoformat() if hasattr(show, "date") and hasattr(show.date, "isoformat") else str(getattr(show, "date", "-")),
                "room": getattr(show, "room", "-"),
            },
        )

    @staticmethod
    def _validate_lineup(lineup: List[Any]) -> List[str]:
        """
        Validate show lineup.

        Args:
            lineup: List of comedian objects

        Returns:
            List of validation error messages
        """
        errors = []

        if not isinstance(lineup, list):
            errors.append("Lineup must be a list")
            return errors

        for i, comedian in enumerate(lineup):
            # Basic comedian validation
            if not hasattr(comedian, "name"):
                errors.append(f"Comedian {i+1} must have a name attribute")
            elif not comedian.name or not comedian.name.strip():
                errors.append(f"Comedian {i+1} name cannot be empty")

        return errors
    
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
        # Normalize and check non-empty
        if value is None:
            return f"{field_name} is required and cannot be empty"

        cleaned = StringUtils.normalize_whitespace(str(value)).strip()
        if not cleaned:
            return f"{field_name} is required and cannot be empty"
        return None

    @staticmethod
    def _validate_tickets(tickets: List[Any]) -> List[str]:
        """
        Validate show tickets.

        Args:
            tickets: List of ticket objects

        Returns:
            List of validation error messages
        """
        errors = []

        if not isinstance(tickets, list):
            errors.append("Tickets must be a list")
            return errors

        for i, ticket in enumerate(tickets):
            # Basic ticket validation
            if not hasattr(ticket, "price"):
                errors.append(f"Ticket {i+1} must have a price attribute")
            elif not isinstance(ticket.price, (int, float)) or ticket.price < 0:
                errors.append(f"Ticket {i+1} price must be a non-negative number")

            if not hasattr(ticket, "purchase_url"):
                errors.append(f"Ticket {i+1} must have a purchase_url attribute")
            else:
                url_value = getattr(ticket, "purchase_url", "")
                url_str = (url_value or "").strip()
                if not url_str:
                    errors.append(f"Ticket {i+1} purchase URL cannot be empty")
                elif not URLUtils.is_valid_url(url_str):
                    errors.append(f"Ticket {i+1} purchase URL must be a valid URL format")

        return errors
    
        # Logging Utilities
    @staticmethod
    def log_validation_summary(total_count: int, valid_count: int, entity_type: str = "items") -> None:
        """
        Log standardized validation summary.

        Args:
            total_count: Total number of items processed
            valid_count: Number of valid items
            entity_type: Type of entity being validated
        """
        invalid_count = total_count - valid_count

        if invalid_count > 0:
            Logger.warning(
                f"{entity_type.title()} validation: {valid_count}/{total_count} valid " f"({invalid_count} failed)"
            )
        else:
            Logger.info(f"{entity_type.title()} validation: All {total_count} {entity_type} are valid")