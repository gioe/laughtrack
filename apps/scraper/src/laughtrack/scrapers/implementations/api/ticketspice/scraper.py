"""Generic TicketSpice (Webconnex) ticketing-form scraper.

TicketSpice forms (``<account>.ticketspice.com/<slug>``) are single-event
ticketing pages: one form == one show on one date. The form HTML embeds its full
config in a ``window.__BOOTSTRAP__`` JS object — ``appSettings`` (formName,
eventStart, timeZone, status) and ``formData`` (ticket levels / price). The page
is plain server-rendered HTML (no auth, no API call needed), so a single
``fetch_html`` of the form URL is the scrapable seam.

Per-venue configuration is the form URL, read from the active scraping source's
``source_url`` (falling back to the club's ``scraping_url``). Because TicketSpice
forms carry no wall-clock show time, the Show uses
``scraping_sources.metadata.default_show_time`` (``HH:MM``, default 19:00)
localized to the club timezone — same pattern as the AXS homepage scraper.

Pipeline:
    1. collect_scraping_targets(): return the TicketSpice form URL.
    2. get_data(url): fetch the form HTML, parse the bootstrap into one event.
    3. transformation_pipeline: TicketSpiceEvent.to_show() -> Show (or None when
       the show date is already past, so a stale un-updated form drops off).
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import TicketSpicePageData
from .extractor import extract_event
from .transformer import TicketSpiceTransformer


class TicketSpiceScraper(BaseScraper):
    """Single-form scraper for venues ticketing through TicketSpice."""

    key = "ticketspice"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TicketSpiceTransformer(club))

    def _form_url(self) -> Optional[str]:
        # source_url (the active scraping_sources row) is the canonical form URL;
        # fall back to the club's scraping_url for legacy single-source configs.
        return (self.club.source_metadata or {}).get("form_url") or self.club.scraping_url

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        form_url = self._form_url()
        if not form_url:
            Logger.warn(
                f"{self._log_prefix}: no TicketSpice form URL configured (source_url/scraping_url)",
                self.logger_context,
            )
            return []
        return [URLUtils.normalize_url(form_url)]

    async def get_data(self, target: ScrapingTarget) -> Optional[TicketSpicePageData]:
        try:
            html = await self.fetch_html(target)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: failed to fetch TicketSpice form {target}: {e}",
                self.logger_context,
            )
            return None

        if not html:
            self._warn_empty_extraction(target, html=html)
            return None

        event = extract_event(html, form_url=target)
        if event is None:
            self._warn_empty_extraction(
                target,
                html=html,
                note="no published event parsed from TicketSpice bootstrap",
            )
            return None

        Logger.info(
            f"{self._log_prefix}: parsed TicketSpice event '{event.title}' on {event.event_date}",
            self.logger_context,
        )
        return TicketSpicePageData(event_list=[event])
