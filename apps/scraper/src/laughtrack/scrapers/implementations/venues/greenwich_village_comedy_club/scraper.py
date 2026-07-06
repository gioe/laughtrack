"""Greenwich Village Comedy Club scraper using WordPress shows plus Tessera tickets."""

import re
from html import unescape
from typing import Any, List, Optional

from laughtrack.core.clients.tessera.instances.greenwich_village import (
    GreenwichVillageTesseraClient,
)
from laughtrack.core.entities.event.broadway import BroadwayEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.implementations.venues.broadway_comedy_club.data import (
    BroadwayEventData,
)
from laughtrack.scrapers.implementations.venues.broadway_comedy_club.scraper import (
    BroadwayComedyClubScraper,
)


class GreenwichVillageComedyClubScraper(BroadwayComedyClubScraper):
    """Scraper for Greenwich Village Comedy Club's Tessera-backed listings."""

    key = "greenwich_village_comedy_club"
    tessera_client_cls = GreenwichVillageTesseraClient
    _API_ROOT = "https://www.greenwichvillagecomedyclub.com/wp-json/wp/v2/shows"
    _PER_PAGE = 100
    _MAX_PAGES = 10

    async def get_data(self, url: str) -> Optional[BroadwayEventData]:
        """Fetch Greenwich's WordPress show API and map rows into BroadwayEvent."""
        try:
            events: List[BroadwayEvent] = []
            for page in range(1, self._MAX_PAGES + 1):
                api_url = self._api_url(page)
                payload = await self.fetch_json(api_url)
                if not isinstance(payload, list):
                    break

                events.extend(self._events_from_payload(payload))
                if len(payload) < self._PER_PAGE:
                    break

            if not events:
                Logger.warning(f"{self._log_prefix}: no events extracted from WordPress shows API", self.logger_context)
                return None

            if not await self.tessera_client.refresh_session_id():
                Logger.warning(
                    f"{self._log_prefix}: Tessera session refresh failed — enrichment will"
                    " proceed with existing session key (may produce empty responses)",
                    self.logger_context,
                )

            events = await self._enrich_events_with_tickets(events)
            return BroadwayEventData(events) if events else None

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error extracting data from {url}: {str(e)}", self.logger_context)
            return None

    def _api_url(self, page: int) -> str:
        return f"{self._API_ROOT}?per_page={self._PER_PAGE}&page={page}"

    def _events_from_payload(self, payload: List[dict]) -> List[BroadwayEvent]:
        events: List[BroadwayEvent] = []
        for row in payload:
            event = self._event_from_row(row)
            if event is not None:
                events.append(event)
        return events

    def _event_from_row(self, row: dict) -> Optional[BroadwayEvent]:
        acf = row.get("acf") if isinstance(row.get("acf"), dict) else {}
        if acf.get("hide_show") is True:
            return None

        event_date = self._clean_text(acf.get("date_and_time_of_show"))
        if not event_date:
            return None

        event_id = self._clean_text(row.get("id"))
        link = self._clean_text(row.get("link"))
        title = self._title_from_row(row, acf)

        return BroadwayEvent.from_dict(
            {
                "id": event_id,
                "eventDate": event_date,
                "additionalInformation": self._html_to_text(acf.get("show_description")),
                "mainArtist": self._artist_names(acf.get("headliner")),
                "additionalArtists": self._artist_names(acf.get("additional_artists")),
                "venue": self._nested_title(acf.get("venue")),
                "image": self._image_url(acf.get("show_image")),
                "isTesseraProduct": not bool(acf.get("external_ticket_button_url")),
                "externalLink": link,
                "externalLinkButtonText": self._clean_text(acf.get("external_ticket_button_text")),
                "doors": self._clean_text(acf.get("door_time")),
                "buyNowButtonText": self._clean_text(acf.get("custom_buy_now_button")) or "Buy Tickets",
                "tags": self._string_list(acf.get("private_tags")),
                "ages": "",
                "title": title,
                "room": self._clean_text(acf.get("room")),
                "show_page_url": link,
            }
        )

    def _title_from_row(self, row: dict, acf: dict) -> str:
        template = acf.get("show_template")
        if isinstance(template, dict):
            title = self._clean_text(template.get("post_title"))
            if title:
                return title

        title = self._clean_text(acf.get("show_title"))
        if title:
            return title

        rendered = row.get("title", {}).get("rendered") if isinstance(row.get("title"), dict) else ""
        return self._strip_date_prefix(self._clean_text(rendered))

    def _artist_names(self, value: Any) -> List[str]:
        if isinstance(value, list):
            names = []
            for item in value:
                if isinstance(item, dict):
                    name = self._clean_text(item.get("post_title") or item.get("name"))
                else:
                    name = self._clean_text(item)
                if name:
                    names.append(name)
            return names
        if isinstance(value, str):
            text = self._clean_text(value)
            return [text] if text else []
        return []

    def _string_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [text for item in value if (text := self._clean_text(item))]
        text = self._clean_text(value)
        return [text] if text else []

    def _nested_title(self, value: Any) -> str:
        if isinstance(value, dict):
            return self._clean_text(value.get("post_title") or value.get("name"))
        return self._clean_text(value)

    def _image_url(self, value: Any) -> str:
        if isinstance(value, dict):
            return self._clean_text(value.get("url"))
        return ""

    @staticmethod
    def _clean_text(value: Any) -> str:
        if value is None or value is False:
            return ""
        return unescape(str(value)).strip()

    @classmethod
    def _html_to_text(cls, value: Any) -> str:
        text = cls._clean_text(value)
        if not text:
            return ""
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()

    @classmethod
    def _strip_date_prefix(cls, title: str) -> str:
        return re.sub(r"^\d{4}-\d{2}-\d{2}\s+", "", title).strip()
