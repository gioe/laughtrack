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
        from .data import SeatEnginePageData

        return SeatEnginePageData(event_list=events)


# This filter changes only Whiplash conversion; other source transforms remain
# unchanged. Reviewed hidden identities are separately blocked at persistence
# by the shared ComedianHandler, including associations from other sources.
_WHIPLASH_EVENT_LABELS = frozenset({"grand opening", "summer 2026", "heavy hitters"})


class SeatEngineEventTransformer(DataTransformer[JSONDict]):
    def __init__(self, club, client: Optional["SeatEngineClient"] = None):
        super().__init__(club)
        # Reuse a pre-built client (e.g., from the scraper) so that venue_website
        # cached during fetch_events is available when create_show is called.
        self._client = client

    def can_transform(self, raw_data: JSONDict) -> bool:
        # Basic shape: SeatEngine events usually have id and event object
        return isinstance(raw_data, dict) and ("id" in raw_data or "event" in raw_data)

    def transform_to_show(
        self,
        raw_data: JSONDict,
        source_url: Optional[str] = None,
    ) -> Optional[Show]:
        try:
            client = self._client or SeatEngineClient(self.club)
            return client.create_show(self._filter_whiplash_talents(raw_data, client))
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed: {e}")
            return None

    def _filter_whiplash_talents(self, raw_data: JSONDict, client: SeatEngineClient) -> JSONDict:
        """Remove exact reviewed labels only from the verified Whiplash source."""
        source = self.club.scraping_source
        if (
            self.club.id != 1347
            or source is None
            or source.id != 591
            or source.club_id != 1347
            or str(self.club.seatengine_id) != "650"
        ):
            return raw_data
        event = raw_data.get("event") or {}
        for scope in (raw_data, event):
            identities = [scope.get("venue_id")]
            if isinstance(scope.get("venue"), dict):
                identities.append(scope["venue"].get("id"))
            for ident in identities:
                if ident is not None and str(ident) != "650":
                    client.record_routing_hold("Whiplash performer source venue identity mismatch")
                    raise ValueError("Whiplash performer source venue identity mismatch")
        talents = event.get("talents", [])
        kept = [
            talent
            for talent in talents
            if not (
                isinstance(talent, dict)
                and isinstance(talent.get("name"), str)
                and " ".join(talent["name"].casefold().split()) in _WHIPLASH_EVENT_LABELS
            )
        ]
        return {**raw_data, "event": {**event, "talents": kept}}
