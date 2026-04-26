"""Pure date and time utilities with no domain dependencies."""

import re
from datetime import datetime, timedelta
from typing import Any, List, Optional

import pytz

try:
    from dateutil.relativedelta import relativedelta

    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


class DateTimeUtils:
    """Pure utility class for date and time operations."""

    @staticmethod
    def validate_datetime(value: Any, field_name: str) -> Optional[str]:
        """
        Validate that a value is a datetime object.

        Args:
            value: Value to validate
            field_name: Name of field for error messages

        Returns:
            Error message if invalid, None if valid
        """
        if not value:
            return f"{field_name} is required"

        if not isinstance(value, datetime):
            return f"{field_name} must be a datetime object"

        return None

    @staticmethod
    def build_complete_date(date: str, separator: str) -> str:
        """
        Build a complete date string with year inference.

        Args:
            date: Date string in format like "12/25" or "Dec/25"
            separator: Separator used in the date string

        Returns:
            str: Complete date string in YYYY-MM-DD format
        """
        parts = date.split(separator)
        month = parts[0]
        day = parts[1]

        current_month = datetime.now().month
        year = datetime.now().year

        # Checks if we're dealing with a month name or number as a string.
        if month.isalpha():
            month_num = DateTimeUtils.get_month_number_from_name(month)
            if month_num is None:
                raise ValueError(f"Invalid month name: {month}")
            month = month_num

        if int(month) < current_month:
            year = year + 1

        return f"{year}-{month}-{day}"

    @staticmethod
    def get_month_number_from_name(month_name: str) -> Optional[int]:
        """
        Convert month name to month number.

        Args:
            month_name: Full or abbreviated month name

        Returns:
            Optional[int]: Month number (1-12) or None if invalid
        """
        try:
            month_number = datetime.strptime(month_name, "%B").month
            return month_number
        except ValueError:
            try:
                # Try abbreviated month name
                month_number = datetime.strptime(month_name, "%b").month
                return month_number
            except ValueError:
                return None

    @staticmethod
    def build_complete_time(time: str, meridiem: str) -> str:
        """
        Build a complete time string from time and AM/PM.

        Args:
            time: Time string like "7:30"
            meridiem: AM/PM indicator

        Returns:
            str: Complete time string in 24-hour format
        """
        time_parts = time.split(":")
        hour = int(time_parts[0])
        minute = time_parts[1] if len(time_parts) > 1 else "00"

        # Convert to 24-hour format
        if meridiem.upper() == "PM" and hour != 12:
            hour += 12
        elif meridiem.upper() == "AM" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute}"

    @staticmethod
    def parse_datetime_with_timezone(date_str: str, timezone: Optional[str] = "America/New_York") -> datetime:
        """
        Parse a datetime string and apply timezone.

        Args:
            date_str: ISO format datetime string
            timezone: Timezone name (default: America/New_York)

        Returns:
            datetime: Timezone-aware datetime object
        """
        if not HAS_DATEUTIL:
            raise ImportError("pytz and dateutil are required for timezone operations")

        # Parse the datetime
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        # If it's not timezone aware, assume it's in the specified timezone
        if dt.tzinfo is None and timezone:
            tz = pytz.timezone(timezone)
            dt = tz.localize(dt)

        return dt

    @staticmethod
    def format_utc_iso_date(dt: datetime) -> str:
        """
        Format datetime as UTC ISO string.

        Args:
            dt: Datetime object to format

        Returns:
            str: ISO formatted string in UTC
        """
        if not HAS_DATEUTIL:
            # Fallback without timezone conversion
            return dt.isoformat()

        if dt.tzinfo is None:
            # Assume local timezone if none specified
            dt = pytz.timezone("America/New_York").localize(dt)

        # Convert to UTC
        utc_dt = dt.astimezone(pytz.UTC)

        # Format as ISO string
        return utc_dt.isoformat().replace("+00:00", "Z")

    @staticmethod
    def get_current_year() -> int:
        """Get the current year."""
        return datetime.now().year

    @staticmethod
    def get_current_month() -> int:
        """Get the current month."""
        return datetime.now().month

    @staticmethod
    def get_current_day() -> int:
        """Get the current day."""
        return datetime.now().day

    @staticmethod
    def is_past_date(date: datetime) -> bool:
        """
        Check if a date is in the past.

        Args:
            date: Date to check

        Returns:
            bool: True if date is in the past
        """
        return date < datetime.now()

    @staticmethod
    def is_future_date(date: datetime, buffer_days: int = 1) -> bool:
        """
        Check if a date is in the future (with buffer for timezone issues).

        Args:
            date: DateTime to check
            buffer_days: Number of days in the past to allow

        Returns:
            True if date is considered "future"
        """
        cutoff = datetime.now(date.tzinfo) - timedelta(days=buffer_days)
        return date >= cutoff

    @staticmethod
    def add_months(date: datetime, months: int) -> datetime:
        """
        Add months to a datetime.

        Args:
            date: Starting date
            months: Number of months to add

        Returns:
            datetime: New datetime with months added
        """
        if HAS_DATEUTIL:
            return date + relativedelta(months=months)
        else:
            # Fallback: approximate by adding days (less accurate)
            return date + timedelta(days=months * 30)

    @staticmethod
    def add_days(date: datetime, days: int) -> datetime:
        """
        Add days to a datetime.

        Args:
            date: Starting date
            days: Number of days to add

        Returns:
            datetime: New datetime with days added
        """
        return date + timedelta(days=days)

    @staticmethod
    def add_hours(date: datetime, hours: int) -> datetime:
        """
        Add hours to a datetime.

        Args:
            date: Starting date
            hours: Number of hours to add

        Returns:
            datetime: New datetime with hours added
        """
        return date + timedelta(hours=hours)

    @staticmethod
    def parse_flexible_date(date_str: str) -> Optional[datetime]:
        """
        Parse various date formats flexibly.

        Args:
            date_str: Date string in various formats

        Returns:
            Optional[datetime]: Parsed datetime or None if parsing fails
        """
        # Common date formats to try
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        return None

    @staticmethod
    def get_date_offset_from_now(offset_months: int) -> str:
        """
        Get a date string that is 'offset_months' months from now.

        Args:
            offset_months: Number of months to offset from current date

        Returns:
            str: Date string in YYYY-MM format
        """
        now = datetime.now()
        future_date = DateTimeUtils.add_months(now, offset_months)
        return future_date.strftime("%Y-%m")

    @staticmethod
    def format_iso8601_date(date_str: str) -> str:
        """
        Format an ISO 8601 date string to remove timezone information.

        Args:
            date_str: ISO 8601 formatted date string (e.g., "2025-04-01T19:30:00-04:00")

        Returns:
            str: Formatted date string (e.g., "2025-04-01 19:30:00")
        """
        if not date_str:
            return ""

        try:
            # Split by T to separate date and time
            parts = date_str.split("T")
            if len(parts) != 2:
                return date_str

            date_part = parts[0]
            time_part = parts[1]

            # Remove timezone information from time part
            # Handle formats like: 19:30:00-04:00, 19:30:00Z, 19:30:00.123Z
            time_clean = re.sub(r"[+-]\d{2}:\d{2}|Z|\.?\d*Z?$", "", time_part)

            return f"{date_part} {time_clean}"
        except:
            return date_str

    @staticmethod
    def is_future_date_str(date_str: str, date_format: str = "%Y-%m-%d") -> bool:
        """Check if a date string represents a future date."""
        try:
            date_obj = datetime.strptime(date_str, date_format)
            return date_obj > datetime.now()
        except (ValueError, TypeError):
            return False

    @staticmethod
    def format_display_date(iso_date: str, format_string: str = "%B %d, %Y at %I:%M %p") -> str:
        """
        Format ISO date for display purposes.

        Args:
            iso_date: ISO formatted date string
            format_string: Format string for output

        Returns:
            Formatted date string
        """
        try:
            date_obj = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
            return date_obj.strftime(format_string)
        except (ValueError, TypeError):
            return iso_date

    @staticmethod
    def get_days_between(start_date: datetime, end_date: datetime) -> int:
        """
        Get number of days between two dates.

        Args:
            start_date: Starting date
            end_date: Ending date

        Returns:
            Number of days between dates
        """
        return (end_date - start_date).days

    @staticmethod
    def get_week_boundaries(date: datetime) -> tuple[datetime, datetime]:
        """
        Get start and end of week for given date (Monday to Sunday).

        Args:
            date: Date to get week boundaries for

        Returns:
            Tuple of (week_start, week_end)
        """
        days_since_monday = date.weekday()
        week_start = date - timedelta(days=days_since_monday)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        return week_start, week_end

    @staticmethod
    def get_month_boundaries(date: datetime) -> tuple[datetime, datetime]:
        """
        Get start and end of month for given date.

        Args:
            date: Date to get month boundaries for

        Returns:
            Tuple of (month_start, month_end)
        """
        month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if HAS_DATEUTIL:
            month_end = month_start + relativedelta(months=1) - timedelta(microseconds=1)
        else:
            # Fallback: go to next month, then subtract a day
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1)
            month_end = next_month - timedelta(microseconds=1)

        return month_start, month_end
