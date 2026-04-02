"""Laugh Boston data extraction utilities."""

import html
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.foundation.utilities.url import URLUtils


class LaughBostonEventExtractor:
    """Utility class for extracting Laugh Boston event data."""

    @staticmethod
    def parse_events_from_pixl(data: Dict[str, Any], club: Any) -> List[TixrEvent]:
        """
        Parse TixrEvent objects directly from a Pixl Calendar API response.

        Uses the Pixl event data (title, start, timezone, sales, ticketUrl) to
        build Show/TixrEvent objects without fetching individual Tixr pages.
        This avoids Tixr's DataDome WAF which blocks GitHub Actions IP ranges.

        Args:
            data: Parsed JSON from https://pixlcalendar.com/api/events/{slug}
            club: Club instance for club_id

        Returns:
            List of TixrEvent objects, in response order
        """
        try:
            events = data.get("events", [])
            result = []
            for event in events:
                tixr_event = LaughBostonEventExtractor._build_tixr_event(event, club)
                if tixr_event:
                    result.append(tixr_event)
            return result
        except Exception as e:
            Logger.error(f"Error parsing events from Pixl Calendar response: {e}")
            return []

    @staticmethod
    def _build_tixr_event(event: Dict[str, Any], club: Any) -> Optional[TixrEvent]:
        """
        Build a TixrEvent from a single Pixl Calendar event dict.

        Args:
            event: Single event dict from Pixl Calendar API
            club: Club instance for club_id

        Returns:
            TixrEvent if successful, None otherwise
        """
        try:
            name = html.unescape(event.get("title", "").strip())
            if not name:
                return None

            start_str = event.get("start")
            timezone_str = event.get("timezone") or "America/New_York"
            if not start_str:
                Logger.warning(f"Pixl event '{name}' has no start date; skipping")
                return None

            try:
                date = DateTimeUtils.parse_datetime_with_timezone(start_str, timezone_str)
            except Exception as e:
                Logger.error(f"Could not parse start date {start_str!r} for '{name}': {e}")
                return None

            raw_desc = event.get("description")
            description = html.unescape(raw_desc) if raw_desc else None

            ticket_url = event.get("ticketUrl", "")

            # Build tickets from sales array
            sales = event.get("sales", [])
            tickets: List[Ticket] = []
            for sale in sales:
                if not isinstance(sale, dict):
                    continue
                price = float(sale.get("currentPrice", 0))
                sold_out = sale.get("state", "OPEN") != "OPEN"
                ticket_type = sale.get("name", "General Admission")
                tickets.append(Ticket(price=price, purchase_url=ticket_url, sold_out=sold_out, type=ticket_type))

            if not tickets:
                # Fallback: use top-level price and status fields
                price_val = float(event.get("price", 0) or 0)
                status = event.get("status", "available")
                sold_out = status.lower() not in ("available", "open")
                tickets.append(
                    Ticket(price=price_val, purchase_url=ticket_url, sold_out=sold_out, type="General Admission")
                )

            # Extract Tixr event ID from ticketUrl
            event_id = URLUtils.extract_id_from_url(ticket_url, ["/events/"]) or ""

            show = Show(
                name=name,
                club_id=club.id,
                date=date,
                show_page_url=ticket_url,
                lineup=[],
                tickets=tickets,
                supplied_tags=["event"],
                description=description,
                timezone=timezone_str,
                room="",
            )

            return TixrEvent.from_tixr_show(show=show, source_url=ticket_url, event_id=event_id)

        except Exception as e:
            Logger.error(f"Error building TixrEvent from Pixl event: {e}")
            return None
