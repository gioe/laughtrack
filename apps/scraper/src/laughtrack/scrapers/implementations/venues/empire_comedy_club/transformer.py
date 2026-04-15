"""Empire Comedy Club data transformer for converting EmpireEvent objects to Show objects."""

from typing import List, Optional

from laughtrack.core.entities.event.empire import EmpireEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.foundation.utilities.datetime import DateTimeUtils


class EmpireEventTransformer(DataTransformer[EmpireEvent]):
    """Transformer for converting EmpireEvent objects to Show objects."""

    def can_transform(self, raw_data: EmpireEvent) -> bool:
        return isinstance(raw_data, EmpireEvent) and bool(raw_data.name) and raw_data.date_time is not None

    def transform_to_show(self, raw_data: EmpireEvent, source_url: str = "") -> Optional[Show]:
        try:
            date_str = raw_data.date_time.isoformat()
            show_date = DateTimeUtils.parse_datetime_with_timezone(date_str, self.club.timezone)
            if not show_date:
                Logger.error(f"Empire Comedy Club: failed to parse date for '{raw_data.name}'")
                return None

            tickets: List[Ticket] = []
            if raw_data.show_page_url:
                sold_out = (raw_data.status or "").lower() == "sold out"
                tickets.append(
                    Ticket(
                        price=0.0,
                        type="General Admission",
                        purchase_url=raw_data.show_page_url,
                        sold_out=sold_out,
                    )
                )

            return Show(
                name=raw_data.name,
                date=show_date,
                show_page_url=raw_data.show_page_url,
                lineup=[],
                tickets=tickets,
                timezone=self.club.timezone,
                club_id=self.club.id,
            )

        except Exception as e:
            Logger.error(f"Empire Comedy Club: failed to transform event '{raw_data.name}': {e}")
            return None
