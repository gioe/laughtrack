"""Data models for the generic Tugoz ticketing-platform scraper."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from html.parser import HTMLParser
from typing import Any, List, Optional
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.ports.scraping import EventListContainer
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self._parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _html_to_text(html: Optional[str]) -> Optional[str]:
    if not html:
        return None
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text() or None


def _parse_local_datetime(value: str, timezone_name: str) -> datetime:
    naive = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return naive.replace(tzinfo=ZoneInfo(timezone_name))


@dataclass
class TugozEvent(ShowConvertible):
    """A single Tugoz event from static.tugoz.com event JSON."""

    event_id: int
    title: str
    date: datetime
    show_page_url: str
    description: Optional[str] = None
    venue_name: Optional[str] = None
    status: Optional[str] = None
    live: Optional[int] = None
    ticket_label: Optional[str] = None

    @classmethod
    def from_api_response(cls, payload: dict[str, Any]) -> Optional["TugozEvent"]:
        einfo = payload.get("einfo")
        if not isinstance(einfo, dict):
            return None

        raw_event_id = einfo.get("eventid") or payload.get("eventid")
        raw_date = einfo.get("date")
        title = str(einfo.get("name") or "").strip()
        if not raw_event_id or not raw_date or not title:
            return None

        timezone_name = str(einfo.get("tziso") or "America/Los_Angeles").strip()
        try:
            event_id = int(raw_event_id)
            date = _parse_local_datetime(str(raw_date), timezone_name)
        except (TypeError, ValueError):
            return None

        event_url = str(einfo.get("eventurl") or "").strip()
        if not event_url:
            event_url = f"https://www.tugoz.com/e/{event_id}"
        show_page_url = urljoin("https://www.tugoz.com/", event_url)

        return cls(
            event_id=event_id,
            title=title,
            date=date,
            show_page_url=show_page_url,
            description=_html_to_text(einfo.get("about")),
            venue_name=str(einfo.get("venue") or "").strip() or None,
            status=str(einfo.get("status") or "").strip() or None,
            live=int(einfo.get("live") or 0),
            ticket_label=str(einfo.get("etp") or einfo.get("etl") or "General Admission"),
        )

    def is_stale(self, now: Optional[datetime] = None) -> bool:
        current = now or datetime.now(tz=self.date.tzinfo)
        if current.tzinfo is None:
            current = current.replace(tzinfo=self.date.tzinfo)
        return self.date < current.astimezone(self.date.tzinfo) - timedelta(hours=6)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        purchase_url = url or self.show_page_url
        if not purchase_url:
            return None

        tickets = [
            ShowFactoryUtils.create_fallback_ticket(
                purchase_url,
                ticket_type=self.ticket_label or "General Admission",
            )
        ]
        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=self.date,
            show_page_url=self.show_page_url or purchase_url,
            lineup=[],
            tickets=tickets,
            description=self.description,
            room=self.venue_name or "",
            supplied_tags=["event"],
            enhanced=enhanced,
        )


@dataclass
class TugozPageData(EventListContainer[TugozEvent]):
    """Extracted Tugoz events."""

    event_list: List[TugozEvent]

