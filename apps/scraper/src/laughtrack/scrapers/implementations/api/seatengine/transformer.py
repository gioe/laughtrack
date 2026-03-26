"""
SeatEngine data utilities: transformer and helper extractor.
"""

from typing import List, Optional

from laughtrack.foundation.models.types import JSONDict
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.core.entities.show.model import Show
from laughtrack.core.clients.seatengine.client import SeatEngineClient


class SeatEngineExtractor:
	@staticmethod
	def to_page_data(events: List[JSONDict]):
		from .page_data import SeatEnginePageData

		return SeatEnginePageData(event_list=events)


class SeatEngineEventTransformer(DataTransformer[JSONDict]):
	def __init__(self, club, client: Optional["SeatEngineClient"] = None):
		super().__init__(club)
		# Reuse a pre-built client (e.g., from the scraper) so that venue_website
		# cached during fetch_events is available when create_show is called.
		self._client = client

	def can_transform(self, raw_data: JSONDict) -> bool:  # type: ignore[override]
		# Basic shape: SeatEngine events usually have id and event object
		return isinstance(raw_data, dict) and ("id" in raw_data or "event" in raw_data)

	def transform_to_show(
		self,
		raw_data: JSONDict,
		source_url: Optional[str] = None,
	) -> Optional[Show]:  # type: ignore[override]
		try:
			client = self._client or SeatEngineClient(self.club)
			return client.create_show(raw_data)
		except Exception as e:
			Logger.error(f"SeatEngine transformer failed: {e}")
			return None
