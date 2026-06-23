"""
Elfsight Event Calendar scraper.

Some venues embed an Elfsight Event Calendar widget (a third-party app, common
on Squarespace/Wix sites) instead of a native events collection. The widget
renders client-side from two anonymous JSON endpoints:

  1. Boot:   GET https://core.service.elfsight.com/p/boot/?w={widget_pid}
             -> data.widgets.{widget_pid}.data.public_widget_token   (a short-lived JWT)
             -> data.widgets.{widget_pid}.data.settings.integrationGoogleCalendar.source
  2. Events: GET https://widget-data.service.elfsight.com/api/events
             ?source={source}&from={iso}&timeZone={tz}&limit={n}&widget-token={token}
             -> { "code": 200, "payload": [ {name, start, description, ...}, ... ] }

The token expires (a few hours), so it is fetched fresh on every scrape from
the boot endpoint; only the widget PID is persisted.

DB config (scraping_sources):
  source_url           = the venue's own calendar PAGE (used as show_page_url)
  metadata.widget_pid  = the Elfsight widget id (the boot `w` parameter)
  metadata.comedy_filter (optional) = true for mixed-use venues to drop
                         non-comedy programming via the comedy keyword allowlist

Currently used by: Eclectic Box SF (San Francisco, CA).
A second Elfsight venue can be onboarded with only a DB row — no Python changes.
"""

from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlencode

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.elfsight import ElfsightEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import ElfsightPageData
from .extractor import ElfsightExtractor
from .transformer import ElfsightEventTransformer

_BOOT_URL = "https://core.service.elfsight.com/p/boot/"
_EVENTS_URL = "https://widget-data.service.elfsight.com/api/events"
# Upcoming-event cap. Google-Calendar-backed widgets rarely list more than a few
# dozen future events; 200 is comfortably above any realistic venue calendar.
_EVENTS_LIMIT = 200


class ElfsightScraper(BaseScraper):
    """Generic Elfsight Event Calendar scraper.

    Reads ``club.scraping_url`` as the venue calendar page (show_page_url) and
    ``club.source_metadata['widget_pid']`` as the Elfsight widget id. Fetches a
    fresh token from the boot endpoint, then upcoming events from the widget
    events API.
    """

    key = "elfsight"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ElfsightEventTransformer(club))
        metadata = club.source_metadata or {}
        self.widget_pid = (metadata.get("widget_pid") or "").strip()
        self.comedy_filter = bool(metadata.get("comedy_filter"))
        self.page_url = (club.scraping_url or "").strip()

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Single target — the widget PID drives both Elfsight requests."""
        if not self.widget_pid:
            Logger.error(
                f"{self._log_prefix}: missing metadata.widget_pid; cannot scrape Elfsight widget",
                self.logger_context,
            )
            return []
        return [self.widget_pid]

    async def get_data(self, target: ScrapingTarget) -> Optional[ElfsightPageData]:
        """Boot the widget for a fresh token, then fetch upcoming events."""
        widget_pid = target
        try:
            await self.rate_limiter.await_if_needed(_BOOT_URL)
            boot = await self.fetch_json(f"{_BOOT_URL}?{urlencode({'w': widget_pid})}")
            token, source = self._parse_boot(boot, widget_pid)
            if not token or not source:
                self._warn_empty_extraction(_BOOT_URL, subject="boot token/source", payload=boot)
                return None

            params = {
                "source": source,
                "from": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "timeZone": self.club.timezone or "America/Los_Angeles",
                "limit": str(_EVENTS_LIMIT),
                "widget-token": token,
            }
            events_url = f"{_EVENTS_URL}?{urlencode(params)}"
            await self.rate_limiter.await_if_needed(events_url)
            response = await self.fetch_json(events_url)

            payload = response.get("payload") if isinstance(response, dict) else None
            events = ElfsightExtractor.extract_events(
                payload, page_url=self.page_url, comedy_filter=self.comedy_filter
            )
            if not events:
                self._warn_empty_extraction(events_url, payload=response)
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} event(s) from Elfsight widget {widget_pid}",
                self.logger_context,
            )
            return ElfsightPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching Elfsight events for widget {widget_pid}: {e}",
                self.logger_context,
            )
            return None

    @staticmethod
    def _parse_boot(boot: Optional[dict], widget_pid: str) -> tuple[str, str]:
        """Pull the public widget token and events source id out of the boot payload."""
        if not isinstance(boot, dict):
            return "", ""
        widget = (((boot.get("data") or {}).get("widgets") or {}).get(widget_pid) or {}).get("data") or {}
        token = (widget.get("public_widget_token") or "").strip()
        settings = widget.get("settings") or {}
        source = ((settings.get("integrationGoogleCalendar") or {}).get("source") or "").strip()
        return token, source
