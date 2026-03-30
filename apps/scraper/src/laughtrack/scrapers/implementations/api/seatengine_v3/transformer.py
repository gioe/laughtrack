"""
SeatEngine v3 event transformer.

Converts a flat (event, show) dict (produced by SeatEngineV3Extractor)
into a Show domain object.
"""

from typing import List, Optional

from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class SeatEngineV3EventTransformer(DataTransformer[JSONDict]):
    """Transforms a SeatEngine v3 (event, show) dict into a Show."""

    def can_transform(self, raw_data: JSONDict) -> bool:
        return (
            isinstance(raw_data, dict)
            and "event_name" in raw_data
            and "start_datetime" in raw_data
        )

    def transform_to_show(
        self,
        raw_data: JSONDict,
        source_url: Optional[str] = None,
    ) -> Optional[Show]:
        try:
            name = raw_data.get("event_name") or ""
            start_dt = raw_data.get("start_datetime") or ""
            show_page_url = raw_data.get("show_page_url") or source_url or ""
            talents = raw_data.get("talents", [])
            inventories = raw_data.get("inventories", [])
            sold_out = raw_data.get("sold_out", False)

            lineup = [Comedian(name=t) for t in talents if t]
            tickets = self._build_tickets(inventories, show_page_url, sold_out)

            return Show.create(
                name=name,
                date=start_dt,
                show_page_url=show_page_url,
                lineup=lineup,
                tickets=tickets,
                club_id=self.club.id,
                timezone=self.club.timezone,
            )
        except Exception as exc:
            Logger.error(f"{self._log_prefix}: failed: {exc}")
            return None

    def _build_tickets(
        self,
        inventories: List[JSONDict],
        show_page_url: str,
        show_sold_out: bool,
    ) -> List[Ticket]:
        tickets: List[Ticket] = []
        for inv in inventories:
            if not inv.get("active"):
                continue
            raw_price = inv.get("price")
            # SeatEngine v3 API returns prices in integer cents (e.g. 2000 = $20.00)
            price = float(raw_price) / 100.0 if raw_price is not None else 0.0
            title = inv.get("title") or inv.get("name") or "General Admission"
            tickets.append(
                Ticket(
                    price=price,
                    purchase_url=show_page_url,
                    sold_out=show_sold_out,
                    type=title,
                )
            )
        return tickets
