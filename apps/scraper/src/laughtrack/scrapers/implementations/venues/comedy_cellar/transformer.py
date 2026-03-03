"""
Custom data transformer for Comedy Cellar scraper.

Handles multi-step API data from Comedy Cellar:
- Combines lineup HTML data with show API data
- Creates ComedyCellarEvent objects for Show factory method conversion
"""

from laughtrack.core.entities.event.comedy_cellar import ComedyCellarEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ComedyCellarEventTransformer(DataTransformer[ComedyCellarEvent]):
    """Transform Comedy Cellar combined API responses into Show objects using the Show factory method."""

    pass
