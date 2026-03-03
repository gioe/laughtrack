"""
SQL query classes for database operations.

This package contains organized SQL query classes separated by functional area.
Each class contains static SQL query strings for their respective domain.
"""

from .club_queries import ClubQueries
from .comedian_queries import ComedianQueries
from .email_queries import EmailQueries
from .lineup_queries import LineupQueries
from .show_queries import ShowQueries
from .tag_queries import TagQueries
from .ticket_queries import TicketQueries

__all__ = [
    'ClubQueries',
    'ComedianQueries', 
    'EmailQueries',
    'LineupQueries',
    'ShowQueries',
    'TagQueries',
    'TicketQueries',
]
