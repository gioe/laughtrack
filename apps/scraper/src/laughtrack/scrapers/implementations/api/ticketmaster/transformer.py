"""
Transformer for Ticketmaster API event data to Show objects.

This integrates Ticketmaster with the shared transformation pipeline.
"""

from typing import Optional

from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.clients.ticketmaster.client import TicketmasterClient


class TicketmasterEventTransformer(DataTransformer[JSONDict]):
    @property
    def _log_prefix(self) -> str:
        return f"{self.__class__.__name__} [{self.club.name}]"

    def can_transform(self, raw_data: JSONDict) -> bool:  # type: ignore[override]
        # Basic shape check for Ticketmaster API events
        return isinstance(raw_data, dict) and ("id" in raw_data or "dates" in raw_data)

    def transform_to_show(self, raw_data: JSONDict, source_url: Optional[str] = None) -> Optional[Show]:  # type: ignore[override]
        try:
            client = TicketmasterClient(self.club)
            return client.create_show(raw_data)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed: {e}")
            return None
