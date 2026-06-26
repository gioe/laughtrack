"""Generic iCalendar (ICS) / Google Calendar scraper.

Many small venues expose their schedule as a public ICS feed — most commonly a
Google Calendar embed whose feed lives at
``https://calendar.google.com/calendar/ical/<id>/public/basic.ics``. Store that
feed URL in ``scraping_sources.source_url`` and this scraper fetches it, parses
every VEVENT, and emits Shows.

Because these calendars are usually mixed-use (a bar's ICS carries music, club
nights, private meetings, *and* comedy), filter to comedy via the shared
title-pattern metadata on ``scraping_sources.metadata``:

    {"include_title_patterns": ["comedy", "open mic", "stand-?up"]}
    {"exclude_title_patterns": ["watch party", "club night"]}

With no patterns configured the scraper keeps every event (generic behavior).
``event_page_url`` metadata sets the per-show fallback link when a VEVENT has no
URL of its own (e.g. the venue's own /events page).
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ical_event import IcalEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.ical.data import IcalPageData
from laughtrack.scrapers.implementations.api.ical.extractor import IcalExtractor
from laughtrack.scrapers.implementations.api.ical.transformer import IcalEventTransformer


class IcalScraper(BaseScraper):
    """Scraper for public iCalendar (ICS) feeds, e.g. Google Calendar."""

    key = "ical"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.default_timezone = club.timezone or "America/Chicago"
        self.transformation_pipeline.register_transformer(IcalEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """Scrape the ICS feed URL stored in the source_url."""
        return [self.club.scraping_url]

    async def get_data(self, url: str) -> Optional[EventListContainer[IcalEvent]]:
        """Fetch the ICS feed and return the (optionally title-filtered) events."""
        try:
            ics_text = await self.fetch_html(url)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None

        if not ics_text or "BEGIN:VCALENDAR" not in ics_text:
            Logger.warn(
                f"{self._log_prefix}: response from {url} is not an ICS feed",
                self.logger_context,
            )
            return None

        page_url_fallback = self.club.metadata_value("event_page_url") or url
        # ICS feeds carry recent past events; drop them by default (1-day grace)
        # unless the source opts in via metadata include_past_events.
        drop_before = None
        if not (self.club.source_metadata or {}).get("include_past_events"):
            drop_before = datetime.now(timezone.utc) - timedelta(days=1)
        events = IcalExtractor.extract_events(
            ics_text, self.default_timezone, page_url_fallback, drop_before=drop_before
        )
        if not events:
            Logger.info(
                f"{self._log_prefix}: no VEVENTs parsed from ICS feed ({url})",
                self.logger_context,
            )
            return None

        kept = self._apply_title_filter(events)
        if not kept:
            Logger.info(
                f"{self._log_prefix}: no events matched title filter "
                f"({len(events)} parsed)",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(kept)}/{len(events)} ICS event(s)",
            self.logger_context,
        )
        return IcalPageData(event_list=kept)

    def _apply_title_filter(self, events: List[IcalEvent]) -> List[IcalEvent]:
        """Keep events whose SUMMARY matches the opt-in include/exclude regexes."""
        include = self.compile_title_patterns("include_title_patterns")
        exclude = self.compile_title_patterns("exclude_title_patterns")
        if not include and not exclude:
            return events

        kept: List[IcalEvent] = []
        for event in events:
            title = event.summary or ""
            if include and not any(p.search(title) for p in include):
                continue
            if exclude and any(p.search(title) for p in exclude):
                continue
            kept.append(event)
        return kept
