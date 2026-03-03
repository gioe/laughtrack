"""
Club configuration mappings.

This module contains configuration data for comedy clubs including
club IDs and timezone information.
"""

from typing import Any, Dict

from laughtrack.foundation.models.types import JSONDict

CLUB_CONFIGS: Dict[str, JSONDict] = {
    "New York Comedy Club": {
        "club_id": 2,
    },
    "New York Comedy Club on 4th Street": {
        "club_id": 3,
    },
    "New York Comedy Club Upper West Side": {
        "club_id": 4,
    },
    "Grisly Pear": {
        "club_id": 6,
    },
    "The Grisly Pear Midtown": {
        "club_id": 7,
    },
    "West Nyack Levity Live": {
        "club_id": 26,
        "timezone": "America/New_York",
    },
    "Oxnard Levity Live": {
        "club_id": 27,
        "timezone": "America/Los_Angeles",
    },
    "Huntsville Levity Live": {
        "club_id": 28,
        "timezone": "America/Chicago",
    },
    "Addison Improv": {
        "club_id": 29,
    },
    "Brea Improv": {
        "club_id": 30,
        "timezone": "America/Los_Angeles",
    },
    "Chicago Improv": {
        "club_id": 31,
        "timezone": "America/Chicago",
    },
    "Hollywood Improv": {
        "club_id": 32,
        "timezone": "America/Los_Angeles",
    },
    "Irvine Improv": {
        "club_id": 33,
        "timezone": "America/Los_Angeles",
    },
    "Milwaukee Improv": {
        "club_id": 34,
        "timezone": "America/Chicago",
    },
    "Ontario Improv": {
        "club_id": 35,
        "timezone": "America/Los_Angeles",
    },
    "Pittsburgh Improv": {
        "club_id": 36,
        "timezone": "America/New_York",
    },
    "Raleigh Improv": {
        "club_id": 37,
        "timezone": "America/New_York",
    },
    "San Jose Improv": {
        "club_id": 38,
        "timezone": "America/Los_Angeles",
    },
    "Arlington Improv": {
        "club_id": 39,
    },
    "Houston Improv": {
        "club_id": 40,
    },
    "LOL San Antonio": {
        "club_id": 41,
    },
    "Tribeca Comedy Club": {
        "club_id": 48,
    },
    "Dark Horse Comedy Club": {
        "club_id": 49,
    },
    "Midtown Comedy Club": {
        "club_id": 50,
    },
    "Denver Improv": {
        "club_id": 56,
        "timezone": "America/Denver",
    },
}


def get_club_config(location: str) -> JSONDict:
    """
    Get club configuration by location name.

    Args:
        location: The name/location of the club

    Returns:
        Dictionary containing club configuration data

    Raises:
        ValueError: If location is not found in configurations
    """
    if location not in CLUB_CONFIGS:
        raise ValueError(f"Unexpected location: {location}")
    return CLUB_CONFIGS[location]


def get_all_club_configs() -> Dict[str, JSONDict]:
    """
    Get all club configurations.

    Returns:
        Dictionary mapping location names to club configurations
    """
    return CLUB_CONFIGS.copy()


def get_club_locations() -> list[str]:
    """
    Get all available club location names.

    Returns:
        List of club location names
    """
    return list(CLUB_CONFIGS.keys())
