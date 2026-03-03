"""
SeatEngine venue configuration mappings.

This module contains mappings between club IDs and SeatEngine venue IDs
for clubs that use the SeatEngine ticketing platform.
"""

from typing import Dict, Optional

# Mapping of club_id to SeatEngine venue_id
SEAT_ENGINE_VENUE_IDS: Dict[int, int] = {
    42: 458,  # McGuire's Comedy Club
    43: 457,  # Brokerage Comedy Club
    44: 456,  # Governors' Comedy Club
    45: 325,  # Stress Factory New Brunswick
    46: 326,  # Stress Factory Bridgeport
    47: 481,  # Harlem
    53: 435,  # Dania
}


def get_venue_id(club_id: int) -> Optional[int]:
    """
    Get SeatEngine venue ID by club ID.

    Args:
        club_id: The internal club ID

    Returns:
        SeatEngine venue ID if found, None otherwise
    """
    return SEAT_ENGINE_VENUE_IDS.get(club_id)


def get_all_seatengine_mappings() -> Dict[int, int]:
    """
    Get all SeatEngine venue mappings.

    Returns:
        Dictionary mapping club IDs to SeatEngine venue IDs
    """
    return SEAT_ENGINE_VENUE_IDS.copy()


def is_seatengine_club(club_id: int) -> bool:
    """
    Check if a club uses SeatEngine for ticketing.

    Args:
        club_id: The internal club ID

    Returns:
        True if club uses SeatEngine, False otherwise
    """
    return club_id in SEAT_ENGINE_VENUE_IDS


def get_seatengine_club_ids() -> list[int]:
    """
    Get all club IDs that use SeatEngine.

    Returns:
        List of club IDs that use SeatEngine
    """
    return list(SEAT_ENGINE_VENUE_IDS.keys())
