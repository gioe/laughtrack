"""House of Comedy Bloomington scraper.

The venue calendar embeds enough event data to avoid fetching individual Tixr
event pages, which are currently blocked by Tixr's DataDome WAF.
"""

import re
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, Tag

from laughtrack.core.clients.tixr import TixrVenueEventTransformer
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.tixr.data import TixrPageData
from laughtrack.scrapers.implementations.api.tixr.extractor import TixrExtractor

_SHOW_START_RE = re.compile(
    r"Show\s+Starts:\s*([A-Za-z]+ \d{1,2}, \d{4} \d{1,2}:\d{2}\s*[AP]M)",
    re.IGNORECASE,
)
_COMPACT_DATE_RE = re.compile(
    r"\b([A-Za-z]+ \d{1,2}, \d{4} \d{1,2}:\d{2}\s*[AP]M)\b",
    re.IGNORECASE,
)
_WEEKDAY_RE = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
    re.IGNORECASE,
)
_DATE_FORMAT = "%B %d, %Y %I:%M %p"


class HouseOfComedyBloomingtonScraper(BaseScraper):
    """Extract events directly from House of Comedy Bloomington's calendar HTML."""

    key = "house_of_comedy_bloomington"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TixrVenueEventTransformer(club))

    async def collect_scraping_targets(self) -> list[str]:
        url = self.club.scraping_url
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return [url]

    async def get_data(self, url: str) -> Optional[TixrPageData]:
        html = await self.fetch_html(url)
        if not html:
            return None

        events = self._parse_events(html)
        if not events:
            Logger.info(f"{self._log_prefix}: no direct calendar events found on {url}", self.logger_context)
            return None

        Logger.info(f"{self._log_prefix}: parsed {len(events)} direct calendar events", self.logger_context)
        return TixrPageData(event_list=events)

    def _parse_events(self, html: str) -> list[TixrEvent]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[TixrEvent] = []
        seen_ids: set[str] = set()

        for url in TixrExtractor.extract_tixr_urls(html):
            if "houseofcomedymn" not in url:
                continue

            link = soup.find("a", href=lambda href: isinstance(href, str) and href == url)
            if link is None:
                link = soup.find("a", href=lambda href: isinstance(href, str) and url in href)
            if not isinstance(link, Tag):
                continue

            container = self._event_container(link)
            if container is None:
                continue

            event = self._event_from_container(url, container)
            if event is None or event.event_id in seen_ids:
                continue

            seen_ids.add(event.event_id)
            events.append(event)

        return events

    def _event_container(self, link: Tag) -> Optional[Tag]:
        node: Optional[Tag] = link
        for _ in range(8):
            if node is None:
                return None
            text = node.get_text(" ", strip=True)
            if "Show Starts:" in text or _COMPACT_DATE_RE.search(text):
                return node
            parent = node.parent
            node = parent if isinstance(parent, Tag) else None
        return None

    def _event_from_container(self, url: str, container: Tag) -> Optional[TixrEvent]:
        text = " ".join(container.get_text(" ", strip=True).split())
        match = _SHOW_START_RE.search(text)
        compact_match = None if match is not None else _COMPACT_DATE_RE.search(text)
        raw_date = match.group(1) if match is not None else (compact_match.group(1) if compact_match else None)
        if raw_date is None:
            return None

        date = self._parse_date(raw_date)
        if date is None:
            return None

        title = self._extract_title(container, text)
        if not title:
            return None

        if match is None:
            title = self._extract_compact_title(text)
            if not title:
                return None

        event_id = TixrExtractor.get_event_id(url)
        if not event_id:
            return None

        show = Show(
            name=title,
            club_id=self.club.id,
            date=date,
            show_page_url=url,
            lineup=[],
            tickets=[Ticket(price=0, purchase_url=url, sold_out=False, type="General Admission")],
            supplied_tags=["event"],
            description=None,
            timezone=self.club.timezone,
            room="",
        )
        return TixrEvent.from_tixr_show(show=show, source_url=url, event_id=event_id)

    def _parse_date(self, raw: str) -> Optional[datetime]:
        try:
            return datetime.strptime(raw, _DATE_FORMAT).replace(tzinfo=ZoneInfo(self.club.timezone))
        except (ValueError, TypeError):
            Logger.warn(f"{self._log_prefix}: could not parse show start {raw!r}", self.logger_context)
            return None

    @staticmethod
    def _extract_title(container: Tag, text: str) -> str:
        heading = container.find(["h1", "h2", "h3", "h4", "h5"])
        if heading is not None:
            return heading.get_text(" ", strip=True)

        title = text.split("Show Starts:", 1)[0].strip()
        return re.sub(r"\s+", " ", title)

    @staticmethod
    def _extract_compact_title(text: str) -> str:
        before_weekday = _WEEKDAY_RE.split(text, maxsplit=1)[0].strip()
        return re.sub(r"\s+", " ", before_weekday)
