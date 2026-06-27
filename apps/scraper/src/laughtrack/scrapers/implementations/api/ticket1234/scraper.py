"""Generic scraper for venues ticketed through the 1234ticket platform.

1234ticket (api.1234ticket.com/api_040/landing-data) exposes a single public,
unauthenticated endpoint returning every event across the platform's venues
(currently Flamingo Theater Bar + La Scala de Miami — both Miami Latin-events
venues that mix stand-up comedy with music/dance concerts).

Because one feed serves all venues and carries no event category, each
`scraping_sources` row:
  - filters to its venue via ``metadata.venue_id`` (the venue UUID) or
    ``metadata.venue_name``; and
  - applies an opt-in ``include_title_patterns`` comedy allowlist (matched
    case-insensitively against the title + description + de-hyphenated link
    slug) so a comedy-platform onboard does not ingest the venue's music acts.
    ``exclude_title_patterns`` is also supported. With no filters every event
    for the venue is kept.

Newer ``live.1234ticket.com`` Next.js storefront uses a token-gated ``api-live``
v2 API (403 anonymously); this scraper deliberately uses the older public
``api_040`` feed instead.
"""

from datetime import datetime, timezone
from typing import List, Optional, Type
from urllib.parse import urlencode

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import Ticket1234Event, Ticket1234PageData
from .extractor import (
    display_name,
    normalize_for_match,
    parse_events,
    show_datetime,
)
from .transformer import Ticket1234Transformer

_DEFAULT_TIMEZONE = "America/New_York"
_PAGE_SIZE = 50
_MAX_PAGES = 20


class Ticket1234Scraper(BaseScraper):
    """Configurable scraper for 1234ticket landing-data venues."""

    key = "1234ticket"
    page_data_cls: Type[EventListContainer[Ticket1234Event]] = Ticket1234PageData
    transformer_cls: Type[DataTransformer[Ticket1234Event]] = Ticket1234Transformer

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(self.transformer_cls(club))
        self._configure_from_source_metadata()

    def _configure_from_source_metadata(self) -> None:
        metadata = self.club.source_metadata or {}
        self._venue_id = metadata.get("venue_id")
        self._venue_name = metadata.get("venue_name")
        self._timezone = metadata.get("default_timezone") or self.club.timezone or _DEFAULT_TIMEZONE
        self._include_title_patterns = self._normalize_patterns(metadata.get("include_title_patterns"))
        self._exclude_title_patterns = self._normalize_patterns(metadata.get("exclude_title_patterns"))

    @staticmethod
    def _normalize_patterns(raw: object) -> List[str]:
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list):
            return [str(p).strip().lower() for p in raw if str(p).strip()]
        return []

    def _belongs_to_venue(self, event: dict) -> bool:
        venue = event.get("venue") or {}
        if self._venue_id:
            return str(venue.get("id")) == str(self._venue_id) or str(event.get("venue_id")) == str(self._venue_id)
        if self._venue_name:
            return str(venue.get("name", "")).strip().lower() == str(self._venue_name).strip().lower()
        # No venue filter configured: keep everything (single-venue platform use).
        return True

    def _title_allowed(self, event: dict) -> bool:
        """Apply the optional comedy include/exclude filters.

        Matched against the title + description + de-hyphenated link slug, since
        the bare ``title`` is often an abbreviated single word.
        """
        haystack = normalize_for_match(
            event.get("title"), event.get("description"), event.get("link")
        )
        if self._exclude_title_patterns and any(p in haystack for p in self._exclude_title_patterns):
            return False
        if self._include_title_patterns and not any(p in haystack for p in self._include_title_patterns):
            return False
        return True

    async def collect_scraping_targets(self) -> List[str]:
        base = self.club.scraping_url
        if not base:
            Logger.error(f"{self._log_prefix}: No scraping_url configured", self.logger_context)
            return []
        return [base]

    async def get_data(self, target: str) -> Optional[Ticket1234PageData]:
        now = datetime.now(timezone.utc)
        events: List[Ticket1234Event] = []
        seen_raw = 0

        for page in range(1, _MAX_PAGES + 1):
            query = urlencode({
                "search": "null", "page": page, "limit": _PAGE_SIZE,
                "sortBy": "date", "sortOrder": "asc",
            })
            payload = await self.fetch_json(f"{target}?{query}")
            raw_events = parse_events(payload)
            if not raw_events:
                break
            seen_raw += len(raw_events)
            for ev in raw_events:
                if not self._belongs_to_venue(ev):
                    continue
                if not self._title_allowed(ev):
                    continue
                start = show_datetime(ev.get("date"), ev.get("time"), self._timezone)
                if not start or start < now:  # skip unparseable / past
                    continue
                events.append(Ticket1234Event(
                    name=display_name(ev.get("title"), ev.get("link") or ""),
                    start_date=start,
                    show_page_url=ev.get("link") or target,
                    ticket_url=ev.get("link") or target,
                    price=None,
                    performers=[],
                ))
            if len(raw_events) < _PAGE_SIZE:
                break

        if not events:
            Logger.info(
                f"{self._log_prefix}: no upcoming matching events from 1234ticket "
                f"(scanned {seen_raw} platform event(s))",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} upcoming show(s) "
            f"from {seen_raw} platform event(s)",
            self.logger_context,
        )
        return self.page_data_cls(event_list=events)
