"""Timezone lookup utilities for US venue addresses."""

import re
from typing import Optional

# US state abbreviation → IANA timezone.
# For states spanning multiple time zones, the most-populated zone is used.
_STATE_TO_TIMEZONE: dict[str, str] = {
    "AL": "America/Chicago",
    "AK": "America/Anchorage",
    "AZ": "America/Phoenix",
    "AR": "America/Chicago",
    "CA": "America/Los_Angeles",
    "CO": "America/Denver",
    "CT": "America/New_York",
    "DC": "America/New_York",
    "DE": "America/New_York",
    "FL": "America/New_York",
    "GA": "America/New_York",
    "HI": "Pacific/Honolulu",
    "ID": "America/Boise",
    "IL": "America/Chicago",
    "IN": "America/Indiana/Indianapolis",
    "IA": "America/Chicago",
    "KS": "America/Chicago",
    "KY": "America/New_York",
    "LA": "America/Chicago",
    "ME": "America/New_York",
    "MD": "America/New_York",
    "MA": "America/New_York",
    "MI": "America/Detroit",
    "MN": "America/Chicago",
    "MS": "America/Chicago",
    "MO": "America/Chicago",
    "MT": "America/Denver",
    "NE": "America/Chicago",
    "NV": "America/Los_Angeles",
    "NH": "America/New_York",
    "NJ": "America/New_York",
    "NM": "America/Denver",
    "NY": "America/New_York",
    "NC": "America/New_York",
    "ND": "America/Chicago",
    "OH": "America/New_York",
    "OK": "America/Chicago",
    "OR": "America/Los_Angeles",
    "PA": "America/New_York",
    "RI": "America/New_York",
    "SC": "America/New_York",
    "SD": "America/Chicago",
    "TN": "America/Chicago",
    "TX": "America/Chicago",
    "UT": "America/Denver",
    "VT": "America/New_York",
    "VA": "America/New_York",
    "WA": "America/Los_Angeles",
    "WV": "America/New_York",
    "WI": "America/Chicago",
    "WY": "America/Denver",
    # Territories
    "PR": "America/Puerto_Rico",
    "VI": "America/St_Thomas",
    "GU": "Pacific/Guam",
}


def timezone_from_state(state_code: str) -> Optional[str]:
    """Return IANA timezone for a US state abbreviation, or None if unknown."""
    if not state_code:
        return None
    return _STATE_TO_TIMEZONE.get(state_code.strip().upper())


def parse_city_state_from_address(address: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Parse city and state from a comma-separated US address string.

    Expects format: "Street, City, State" or "Street, City, State ZIP"
    Returns (city, state) tuple; either may be None if unparseable.
    """
    if not address:
        return None, None
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if len(parts) < 2:
        return None, None
    # Last segment: state abbreviation (optionally followed by ZIP)
    candidate = parts[-1].strip()
    m = re.match(r"^([A-Za-z]{2})(?:\s+\d{5}(?:-\d{4})?)?$", candidate)
    if m:
        code = m.group(1).upper()
        state = code if code in _STATE_TO_TIMEZONE else None
    else:
        state = None
    # Second-to-last: city
    city = parts[-2].strip() or None
    return city, state


def timezone_from_address(address: Optional[str]) -> Optional[str]:
    """
    Infer IANA timezone from a venue address string.

    Expects the address to end with a US state abbreviation as the last
    comma-separated segment, e.g. "123 Main St, New York, NY".

    Returns:
        IANA timezone string, or None if the state cannot be determined.
    """
    if not address:
        return None
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if not parts:
        return None
    # Last segment is the state, optionally followed by a ZIP: "NY" or "NY 10001"
    candidate = parts[-1].strip()
    m = re.match(r"^([A-Za-z]{2})(?:\s+\d{5}(?:-\d{4})?)?$", candidate)
    if m:
        return timezone_from_state(m.group(1))
    return None
