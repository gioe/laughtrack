"""
Club registry with basic club information.

This module contains the registry of comedy clubs with their IDs and timezone information.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ClubInfo:
    """Basic club information."""

    club_id: int
    timezone: Optional[str] = None


# Registry of comedy clubs
CLUB_REGISTRY: Dict[str, ClubInfo] = {
    "New York Comedy Club": ClubInfo(club_id=2),
    "New York Comedy Club on 4th Street": ClubInfo(club_id=3),
    "New York Comedy Club Upper West Side": ClubInfo(club_id=4),
    "Grisly Pear": ClubInfo(club_id=6),
    "The Grisly Pear Midtown": ClubInfo(club_id=7),
    "West Nyack Levity Live": ClubInfo(club_id=26, timezone="America/New_York"),
    "Oxnard Levity Live": ClubInfo(club_id=27, timezone="America/Los_Angeles"),
    "Huntsville Levity Live": ClubInfo(club_id=28, timezone="America/Chicago"),
    "Addison Improv": ClubInfo(club_id=29),
    "Brea Improv": ClubInfo(club_id=30, timezone="America/Los_Angeles"),
    "Chicago Improv": ClubInfo(club_id=31, timezone="America/Chicago"),
    "Hollywood Improv": ClubInfo(club_id=32, timezone="America/Los_Angeles"),
    "Irvine Improv": ClubInfo(club_id=33, timezone="America/Los_Angeles"),
    "Milwaukee Improv": ClubInfo(club_id=34, timezone="America/Chicago"),
    "Ontario Improv": ClubInfo(club_id=35, timezone="America/Los_Angeles"),
    "Pittsburgh Improv": ClubInfo(club_id=36, timezone="America/New_York"),
    "Raleigh Improv": ClubInfo(club_id=37, timezone="America/New_York"),
    "San Jose Improv": ClubInfo(club_id=38, timezone="America/Los_Angeles"),
    "Arlington Improv": ClubInfo(club_id=39),
    "Houston Improv": ClubInfo(club_id=40),
    "LOL San Antonio": ClubInfo(club_id=41),
    "Tribeca Comedy Club": ClubInfo(club_id=48),
    "Dark Horse Comedy Club": ClubInfo(club_id=49),
    "Midtown Comedy Club": ClubInfo(club_id=50),
    "Denver Improv": ClubInfo(club_id=56, timezone="America/Denver"),
}


def get_club_info(location: str) -> ClubInfo:
    """
    Get club information by location name.

    Args:
        location: The name/location of the club

    Returns:
        ClubInfo object containing club data

    Raises:
        ValueError: If location is not found in registry
    """
    if location not in CLUB_REGISTRY:
        available_locations = list(CLUB_REGISTRY.keys())
        raise ValueError(f"Unknown location: '{location}'. Available locations: {available_locations}")

    return CLUB_REGISTRY[location]


def get_club_id(location: str) -> int:
    """
    Get club ID by location name.

    Args:
        location: The name/location of the club

    Returns:
        Club ID

    Raises:
        ValueError: If location is not found in registry
    """
    return get_club_info(location).club_id


def get_club_timezone(location: str) -> Optional[str]:
    """
    Get club timezone by location name.

    Args:
        location: The name/location of the club

    Returns:
        Timezone string if configured, None otherwise

    Raises:
        ValueError: If location is not found in registry
    """
    return get_club_info(location).timezone


def get_all_club_locations() -> list[str]:
    """
    Get all available club location names.

    Returns:
        List of club location names
    """
    return list(CLUB_REGISTRY.keys())


def get_clubs_by_timezone(timezone: str) -> list[str]:
    """
    Get all clubs in a specific timezone.

    Args:
        timezone: The timezone string (e.g., "America/New_York")

    Returns:
        List of club location names in the specified timezone
    """
    return [location for location, info in CLUB_REGISTRY.items() if info.timezone == timezone]


def get_all_club_info() -> list[ClubInfo]:
    """
    Get all club information.

    Returns:
        List of all ClubInfo objects
    """
    return list(CLUB_REGISTRY.values())
