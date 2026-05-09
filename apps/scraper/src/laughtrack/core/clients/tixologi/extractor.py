"""Shared extraction helpers for Tixologi-backed venue pages."""

import json
import re
from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.tixologi import TixologiEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

_LAUGH_FACTORY_TICKET_URL_RE = re.compile(
    r"https://www\.laughfactory\.club/checkout/show/([^/?#]+)"
)
_EVENT_TIXOLOGI_TICKET_URL_RE = re.compile(
    r"https://event\.tixologi\.com/event/([^/?#]+)/tickets"
)


@dataclass(frozen=True)
class TixologiPartner:
    """Partner metadata returned by Tixologi's public partner endpoint."""

    partner_id: int
    name: str
    punchup_id: Optional[str] = None


@dataclass(frozen=True)
class TixologiTicketReference:
    """Normalized Tixologi ticket URL fields embedded by upstream venue systems."""

    ticket_url: str
    event_id: Optional[str] = None


@dataclass
class TixologiCmsEvent:
    """A raw event shape parsed from a Tixologi-backed CMS show block."""

    title: str
    date_str: str
    time_str: str
    ticket_url: str = ""
    comedians: List[str] = field(default_factory=list)
    punchup_id: Optional[str] = None

    def to_event(self, club_id: int, timezone: str) -> TixologiEvent:
        """Convert the parsed CMS event shape to the scraper event entity."""
        return TixologiEvent(
            club_id=club_id,
            title=self.title,
            date_str=self.date_str,
            time_str=self.time_str,
            ticket_url=self.ticket_url,
            timezone=timezone,
            comedians=self.comedians,
            punchup_id=self.punchup_id,
        )


class TixologiExtractor:
    """Extracts Tixologi CMS events and normalizes Tixologi API/ticket payloads."""

    PARTNER_API_BASE_URL = "https://api-v2.tixologi.com/public/users/partners"

    @staticmethod
    def partner_api_endpoint(partner_id: int) -> str:
        """Return the public partner metadata endpoint for a Tixologi partner ID."""
        return f"{TixologiExtractor.PARTNER_API_BASE_URL}/{partner_id}"

    @staticmethod
    def parse_partner_response(payload: str | Mapping[str, Any]) -> Optional[TixologiPartner]:
        """Parse Tixologi partner metadata from a JSON string or mapping."""
        try:
            data: Any
            if isinstance(payload, str):
                data = json.loads(payload)
            else:
                data = payload

            if not isinstance(data, Mapping):
                return None

            raw_partner_id = data.get("id") or data.get("partner_id")
            name = (data.get("name") or "").strip()
            if raw_partner_id is None or not name:
                return None

            return TixologiPartner(
                partner_id=int(raw_partner_id),
                name=name,
                punchup_id=data.get("punchup_id") or None,
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def normalize_ticket_reference(
        ticket_url: str | None,
        explicit_event_id: str | None = None,
    ) -> TixologiTicketReference:
        """Normalize Tixologi ticket URL and event identifier fields."""
        normalized_url = (ticket_url or "").strip()
        event_id = (explicit_event_id or "").strip() or None

        if not event_id and normalized_url:
            for pattern in (_EVENT_TIXOLOGI_TICKET_URL_RE, _LAUGH_FACTORY_TICKET_URL_RE):
                match = pattern.match(normalized_url)
                if match:
                    event_id = match.group(1)
                    break

        return TixologiTicketReference(ticket_url=normalized_url, event_id=event_id)

    @staticmethod
    def extract_shows(html_content: str, club_id: int, timezone: str) -> List[TixologiEvent]:
        """Parse `.show-sec.jokes` divs from a Tixologi-backed CMS page."""
        try:
            cms_events = TixologiExtractor.extract_cms_events(html_content)
            return [event.to_event(club_id=club_id, timezone=timezone) for event in cms_events]
        except Exception as e:
            Logger.error(f"TixologiExtractor: failed to parse HTML: {e}")
            return []

    @staticmethod
    def extract_cms_events(html_content: str) -> List[TixologiCmsEvent]:
        """Parse raw Tixologi CMS event shapes from HTML."""
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        events: List[TixologiCmsEvent] = []
        for div in soup.select("div.show-sec.jokes"):
            event = TixologiExtractor._parse_show_div(div)
            if event is not None:
                events.append(event)
        return events

    @staticmethod
    def _parse_show_div(div) -> Optional[TixologiCmsEvent]:
        """Parse a single `.show-sec.jokes` div into a raw Tixologi CMS event."""
        try:
            date_span = div.select_one(".shedule span.date")
            if not date_span:
                return None

            date_str = TixologiExtractor._strip_weekday_prefix(date_span.get_text())

            time_span = div.select_one(".shedule span.timing")
            time_str = time_span.get_text().strip() if time_span else "8:00 PM"

            ticket_anchor = div.select_one(".tickets a.ticket-toggle-btn")
            ticket_url = ticket_anchor.get("href", "").strip() if ticket_anchor else ""
            ticket_reference = TixologiExtractor.normalize_ticket_reference(ticket_url)

            title_tag = div.select_one(".show-top-content-sec h4")
            title = title_tag.get_text(strip=True) if title_tag else "Comedy Show"

            figcaptions = div.select(".show-thumbnails-sec figure figcaption")
            comedians = [
                figcaption.get_text(strip=True)
                for figcaption in figcaptions
                if figcaption.get_text(strip=True)
            ]

            return TixologiCmsEvent(
                title=title,
                date_str=date_str,
                time_str=time_str,
                ticket_url=ticket_reference.ticket_url,
                comedians=comedians,
                punchup_id=ticket_reference.event_id,
            )
        except Exception as e:
            Logger.error(f"TixologiExtractor: failed to parse show div: {e}")
            return None

    @staticmethod
    def _strip_weekday_prefix(raw_date: str) -> str:
        """Strip weekday prefixes such as `Wed\xa0Mar 25` or `Wed Mar 25`."""
        if "\xa0" in raw_date:
            return raw_date.split("\xa0", 1)[1].strip()

        parts = raw_date.strip().split(None, 1)
        return parts[1] if len(parts) > 1 else raw_date.strip()
