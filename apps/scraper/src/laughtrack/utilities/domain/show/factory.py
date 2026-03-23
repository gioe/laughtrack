"""
Show Factory Utilities

Common utilities for creating Show objects from various event types.
Standardizes initialization logic across different venue-specific initializers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
import pytz

from laughtrack.foundation.utilities.number.utils import NumberUtils
from laughtrack.utilities.domain.show.enhancement import ShowEnhancement
from laughtrack.utilities.domain.show.utils import ShowUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.datetime import DateTimeUtils

# Names that are placeholder/generic strings and should not be treated as real comedians
_LINEUP_NAME_BLOCKLIST = frozenset({
    # TBA / TBD variants
    "tba",
    "to be announced",
    "to be determined",
    "tbd",
    "headliner tbd",
    "lineup tba",
    "more tba",
    "comedian tba",
    "comedian tbd",
    "comics tba",
    "comics tbd",
    "opener tbd",
    # Guest / surprise variants
    "special guest",
    "special guests",
    "and special guests",
    "surprise guest",
    "surprise guests",
    "surprise",
    "surprise act",
    "mystery guest",
    "guest",
    "guest comedian",
    # Generic show/artist labels
    "various",
    "various artists",
    "comedy show",
    "open mic",
    # Role labels
    "comedian",
    "comedians",
    "featured comedian",
    "local comedian",
    "comic",
    "comics",
    "host",
    "hosts",
    "co-host",
    "emcee",
    "mc",
    "headliner",
    "featured",
    "opener",
    "openers",
    "opening act",
    # Filler / "and more" variants
    "plus more",
    "and more",
    # Music genre labels (false-positive comedians from scraper output)
    "rap",
    "r&b",
    "jazz",
    "hip-hop",
    "hip hop",
    "blues",
    "soul",
    "country",
    "rock",
    "pop",
    "funk",
    "reggae",
    "classical",
    "electronic",
    "edm",
    "metal",
    "punk",
    "folk",
    "gospel",
})

_LINEUP_NAME_MIN_LENGTH = 2


def _is_valid_lineup_name(name: Optional[str]) -> bool:
    """Return True if name is a real comedian name, False if it is a placeholder or None."""
    if not name:
        return False
    stripped = name.strip()
    if len(stripped) < _LINEUP_NAME_MIN_LENGTH:
        return False
    if stripped.lower() in _LINEUP_NAME_BLOCKLIST:
        return False
    if not any(c.isalpha() for c in stripped):
        return False
    return True


class ShowFactoryUtils:
    """Utilities for standardizing Show creation from various event types."""

    @staticmethod
    def apply_enhanced_processing(show: Show, enhanced: bool = True) -> "Show":
        """
        Apply standardized enhanced processing to a Show object.

        Args:
            show: The Show object to enhance
            enhanced: Whether to apply enhanced processing

        Returns:
            Enhanced Show object with applied processing and logged warnings
        """
        if not enhanced:
            return show

        # URL enhancement from source_url removed by design

        # Validate and fix any data issues
        show, warnings = ShowEnhancement.validate_and_fix_show_data(show)

        # Log any warnings from validation
        for warning in warnings:
            Logger.warning(f"Show data fix applied: {warning}")

        return show

    @staticmethod
    def parse_datetime_with_timezone_fallback(
        date_str: str, timezone_str: Optional[str] = None, fallback_timezone: str = "America/New_York"
    ) -> datetime:
        """
        Parse datetime string with timezone fallback handling.

        Args:
            date_str: Date string to parse
            timezone_str: Timezone string (can be None)
            fallback_timezone: Fallback timezone if none provided

        Returns:
            Parsed datetime object with timezone

        Raises:
            ValueError: If datetime parsing fails
        """
        try:
            effective_timezone = timezone_str or fallback_timezone
            return DateTimeUtils.parse_datetime_with_timezone(date_str, effective_timezone)
        except Exception as e:
            Logger.error(f"Failed to parse datetime {date_str} with timezone {timezone_str}: {e}")
            raise ValueError(f"Could not parse datetime: {date_str}")

    @staticmethod
    def create_fallback_ticket(
        purchase_url: str, price: float = 0.0, ticket_type: str = "General Admission", sold_out: bool = False
    ) -> Ticket:
        """
        Create a standardized fallback ticket with common defaults.

        Args:
            purchase_url: URL for purchasing the ticket
            price: Ticket price (defaults to 0.0)
            ticket_type: Type of ticket (defaults to "General Admission")
            sold_out: Whether the ticket is sold out (defaults to False)

        Returns:
            Standardized Ticket object
        """
        return Ticket(
            price=price,
            purchase_url=purchase_url,
            sold_out=sold_out,
            type=ticket_type,
        )

    @staticmethod
    def create_lineup_from_performers(performers: List[Any]) -> List[Comedian]:
        """
        Create standardized lineup from various performer data formats.

        Args:
            performers: List of performer objects/strings

        Returns:
            List of Comedian objects
        """
        if not performers:
            return []

        lineup = []
        for performer in performers:
            try:
                # Handle different performer formats
                if hasattr(performer, "name"):
                    name = performer.name
                elif isinstance(performer, str):
                    name = performer
                elif isinstance(performer, dict) and "name" in performer:
                    name = performer["name"]
                else:
                    Logger.warning(f"Unknown performer format: {performer}")
                    continue

                if name and _is_valid_lineup_name(name):
                    lineup.append(Comedian(name=name.strip()))
            except Exception as e:
                Logger.warning(f"Error processing performer {performer}: {e}")
                continue

        return lineup

    @staticmethod
    def build_description_from_parts(parts: List[str]) -> str:
        """
        Build standardized description from multiple parts.

        Args:
            parts: List of description parts to combine

        Returns:
            Combined description string
        """
        # Filter out None and empty strings, strip whitespace
        clean_parts = [part.strip() for part in parts if part and part.strip()]

        # Join with ". " and ensure proper ending
        if clean_parts:
            description = ". ".join(clean_parts)
            if not description.endswith("."):
                description += "."
            return description

        return ""

    @staticmethod
    def extract_room_from_name(name: str, room_patterns: Dict[str, str]) -> str:
        """
        Extract room information from show name using pattern matching.

        Args:
            name: Show name to analyze
            room_patterns: Dict mapping patterns to room names

        Returns:
            Room name or empty string if no match
        """
        if not name:
            return ""

        name_lower = name.lower()
        for pattern, room_name in room_patterns.items():
            if pattern.lower() in name_lower:
                return room_name

        return ""

    @staticmethod
    def validate_required_fields(name: str, date: datetime, club_id: int, context: str = "show creation") -> None:
        """
        Validate required fields for Show creation using common utilities.

        Args:
            name: Show name
            date: Show date
            club_id: Club ID
            context: Context for error messages

        Raises:
            ValueError: If any required field is invalid
        """
        name_error = ShowUtils.validate_required_string(name, f"Show name for {context}")
        if name_error:
            raise ValueError(name_error)

        date_error = DateTimeUtils.validate_datetime(date, f"Show date for {context}")
        if date_error:
            raise ValueError(date_error)

        club_id_error = NumberUtils.validate_positive_number(club_id, f"Club ID for {context}", allow_zero=False)
        if club_id_error:
            raise ValueError(club_id_error)

    @staticmethod
    def create_enhanced_show_base(
        name: str,
        club: Club,
        date: datetime,
        show_page_url: str,
        lineup: Optional[List[Comedian]] = None,
        tickets: Optional[List[Ticket]] = None,
        description: Optional[str] = None,
        room: str = "",
        supplied_tags: Optional[List[str]] = None,
        enhanced: bool = True,
    ) -> "Show":
        """
        Create a standardized Show object with common processing applied.

        Args:
            name: Show name
            club: Club object
            date: Show date
            show_page_url: URL for the show page
            lineup: List of comedians (defaults to empty list)
            tickets: List of tickets (defaults to empty list)
            description: Show description
            room: Room name (defaults to empty string)
            supplied_tags: List of tags (defaults to ["event"])
            enhanced: Whether to apply enhanced processing

        Returns:
            Standardized Show object with enhanced processing applied
        """
        # Validate required fields
        ShowFactoryUtils.validate_required_fields(name, date, club.id)

        # Apply defaults
        lineup = lineup or []
        tickets = tickets or []
        supplied_tags = supplied_tags or ["event"]
        room = room or ""

    # Create the basic show instance
        show = Show(
                name=name,
                club_id=club.id,
                date=date,
                show_page_url=show_page_url,
                lineup=lineup,
                tickets=tickets,
                description=description,
                room=room,
                supplied_tags=supplied_tags,
            )

        # Apply enhanced processing if enabled
        return ShowFactoryUtils.apply_enhanced_processing(show, enhanced)

    @staticmethod
    def safe_parse_datetime_string(
        datetime_str: str, format_string: str, timezone_name: str = "America/New_York"
    ) -> Optional[datetime]:
        """
        Safely parse datetime string with timezone handling.

        Args:
            datetime_str: Datetime string to parse
            format_string: Format string for parsing
            timezone_name: Timezone name to apply

        Returns:
            Parsed datetime object or None if parsing fails
        """
        try:
            # Parse the datetime
            parsed_dt = datetime.strptime(datetime_str, format_string)

            # Make it timezone-aware
            tz = pytz.timezone(timezone_name)
            return tz.localize(parsed_dt)

        except Exception as e:
            Logger.error(f"Failed to parse datetime '{datetime_str}' with format '{format_string}': {e}")
            return None

    @staticmethod
    def safe_float_conversion(value: Any, default: float = 0.0) -> float:
        """
        Safely convert a value to float with default fallback.

        DEPRECATED: Use NumberUtils.safe_float_conversion instead.
        This method is kept for backward compatibility.

        Args:
            value: Value to convert
            default: Default value if conversion fails

        Returns:
            Float value or default
        """
        return NumberUtils.safe_float_conversion(value, default)

    @staticmethod
    def parse_wix_iso_date(date_str: str, timezone_name: str = "America/New_York") -> Optional[datetime]:
        """
        Parse Wix-style ISO date string with timezone conversion.

        Args:
            date_str: ISO date string from Wix API
            timezone_name: Target timezone name

        Returns:
            Parsed datetime object or None if parsing fails
        """
        try:
            if "T" in date_str:
                parsed_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                target_tz = pytz.timezone(timezone_name)
                return parsed_date.astimezone(target_tz)
        except Exception as e:
            Logger.error(f"Failed to parse Wix date '{date_str}': {e}")

        return None
