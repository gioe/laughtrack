"""
ComedianWebsiteScraper: fetches upcoming shows from comedian personal websites
that contain JSON-LD structured data (schema.org Event markup).

For each event found on a comedian's website:
- Upserts a clubs row for the venue (via ClubHandler.upsert_for_tour_date_venue).
- Upserts a shows row for the event.
- Links the comedian as a LineupItem.
- Updates the comedian's website_last_scraped and website_scrape_strategy metadata.

Triggered by a single clubs row with scraper='comedian_websites'.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import List, Optional

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.lineup.handler import LineupHandler
from laughtrack.core.entities.show.handler import ShowHandler
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.comedian_websites.tour_link_detector import detect_tour_links
from laughtrack.scrapers.implementations.api.comedian_websites.widget_detector import detect_widgets
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.utilities.domain.club.timezone_lookup import timezone_from_address
from laughtrack.utilities.domain.comedian.website_confidence import score_website
from sql.comedian_queries import ComedianQueries


# US state abbreviations used to filter events to US only
_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


class ComedianWebsiteScraper(BaseScraper):
    """
    Scrapes comedian personal websites for JSON-LD Event markup, converts
    discovered events into Show records, and links the comedian as a LineupItem.

    Triggered by a single clubs row with scraper='comedian_websites'.
    """

    key = "comedian_websites"

    _DEFAULT_MAX_CONCURRENT = 5
    _REQUEST_TIMEOUT = 30

    def __init__(self, club: Club, comedian_name: Optional[str] = None, limit: Optional[int] = None, **kwargs):
        super().__init__(club, **kwargs)
        self._club_handler = ClubHandler()
        self._comedian_handler = ComedianHandler()
        self._show_handler = ShowHandler()
        self._lineup_handler = LineupHandler()
        self._comedian_name_filter = comedian_name
        self._limit = limit

    # ------------------------------------------------------------------ #
    # BaseScraper pipeline                                                 #
    # ------------------------------------------------------------------ #

    async def collect_scraping_targets(self) -> List[str]:
        """Single logical target representing the comedian website aggregation job."""
        return ["comedian_websites"]

    async def get_data(self, target: str) -> None:
        """Not used: scrape_async is fully overridden."""
        return None  # pragma: no cover

    @property
    def _max_concurrent(self) -> int:
        try:
            val = int(os.environ.get("MAX_CONCURRENT_COMEDIANS", self._DEFAULT_MAX_CONCURRENT))
            return val if val > 0 else self._DEFAULT_MAX_CONCURRENT
        except (ValueError, TypeError):
            return self._DEFAULT_MAX_CONCURRENT

    async def scrape_async(self) -> List[Show]:
        """Override: fetch comedian websites concurrently, extract JSON-LD events, persist shows + lineups."""
        try:
            comedian_rows = self._get_comedians_for_scraping(
                limit=self._limit, comedian_name=self._comedian_name_filter,
            )
            if not comedian_rows:
                Logger.info(f"{self._log_prefix}: no comedians with websites needing scrape found", self.logger_context)
                return []

            Logger.info(
                f"{self._log_prefix}: scraping websites for {len(comedian_rows)} comedians",
                self.logger_context,
            )

            semaphore = asyncio.Semaphore(self._max_concurrent)
            results = await asyncio.gather(
                *[self._scrape_comedian_website(row, semaphore) for row in comedian_rows]
            )

            all_shows: List[Show] = [show for shows in results for show in shows]

            Logger.info(
                f"{self._log_prefix}: discovered {len(all_shows)} total shows from comedian websites",
                self.logger_context,
            )

            if all_shows:
                self._persist_shows_and_lineups(all_shows)

            return all_shows

        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed: {e}", self.logger_context)
            raise
        finally:
            await self._cleanup_resources()

    # ------------------------------------------------------------------ #
    # Per-comedian scraping                                                #
    # ------------------------------------------------------------------ #

    _MAX_SUBPAGES = 3

    async def _scrape_comedian_website(self, row: dict, semaphore: asyncio.Semaphore) -> List[Show]:
        """Fetch a comedian's website and any tour subpages, extract JSON-LD events, and convert to Shows."""
        comedian = Comedian(name=row["name"], uuid=row["uuid"])
        website = row.get("website", "").strip()
        scraping_url = (row.get("website_scraping_url") or "").strip()
        strategy = "none"

        async with semaphore:
            try:
                if not website:
                    return []

                # If we already know the scraping URL, fetch it directly
                if scraping_url:
                    html = await self.fetch_html(scraping_url, timeout=self._REQUEST_TIMEOUT)
                    if not html:
                        self._update_scrape_metadata(row["uuid"], strategy)
                        return []

                    self._detect_and_persist_widgets(row["uuid"], comedian.name, html)
                    events = EventExtractor.extract_events(html)

                    if not events:
                        strategy = "json_ld_empty"
                        self._update_scrape_metadata(row["uuid"], strategy)
                        return []

                    strategy = "json_ld_subpage"
                    shows = self._events_to_shows(events, comedian)
                    self._update_scrape_metadata(row["uuid"], strategy)
                    self._update_confidence(row["uuid"], comedian.name, website, has_events=True)

                    if shows:
                        Logger.info(
                            f"{self._log_prefix}: {comedian.name} — {len(shows)} shows extracted from {scraping_url}",
                            self.logger_context,
                        )
                    return shows

                # No scraping URL yet — fetch homepage and discover tour subpages
                html = await self.fetch_html(website, timeout=self._REQUEST_TIMEOUT)
                if not html:
                    self._update_scrape_metadata(row["uuid"], strategy)
                    return []

                # Detect Bandsintown/Songkick widgets on homepage
                self._detect_and_persist_widgets(row["uuid"], comedian.name, html)

                # Collect HTML pages to extract events from (homepage + subpages)
                pages_html: List[str] = [html]
                discovered_scraping_url: Optional[str] = None

                # Detect and fetch tour/shows/events subpages
                tour_links = detect_tour_links(html, website)
                if tour_links:
                    Logger.info(
                        f"{self._log_prefix}: {comedian.name} — found {len(tour_links)} tour subpage link(s): {tour_links}",
                        self.logger_context,
                    )
                    for link in tour_links[:self._MAX_SUBPAGES]:
                        subpage_html = await self._fetch_subpage(link, comedian.name)
                        if subpage_html:
                            pages_html.append(subpage_html)
                            self._detect_and_persist_widgets(row["uuid"], comedian.name, subpage_html)
                            # Remember the first subpage that has events as the scraping URL
                            if discovered_scraping_url is None and EventExtractor.extract_events(subpage_html):
                                discovered_scraping_url = link

                # Extract events from all pages and deduplicate
                all_events = []
                for page_html in pages_html:
                    all_events.extend(EventExtractor.extract_events(page_html))

                events = self._deduplicate_events(all_events)

                if not events:
                    strategy = "json_ld_empty"
                    self._update_scrape_metadata(row["uuid"], strategy)
                    self._update_confidence(row["uuid"], comedian.name, website, has_events=False)
                    return []

                strategy = "json_ld_subpage" if len(pages_html) > 1 else "json_ld"
                shows = self._events_to_shows(events, comedian)
                self._update_scrape_metadata(row["uuid"], strategy)
                self._update_confidence(row["uuid"], comedian.name, website, has_events=True)

                # Persist the discovered scraping URL for next time
                if discovered_scraping_url:
                    self._update_scraping_url(row["uuid"], discovered_scraping_url)

                if shows:
                    Logger.info(
                        f"{self._log_prefix}: {comedian.name} — {len(shows)} shows extracted from {website}"
                        + (f" (+{len(pages_html) - 1} subpage(s))" if len(pages_html) > 1 else ""),
                        self.logger_context,
                    )

                return shows

            except Exception as e:
                Logger.error(
                    f"{self._log_prefix}: skipping comedian '{comedian.name}' ({website}) due to error: {e}",
                    self.logger_context,
                )
                self._update_scrape_metadata(row["uuid"], "error")
                return []

    def _events_to_shows(self, events: list, comedian: Comedian) -> List[Show]:
        """Convert a list of JSON-LD events to Shows."""
        shows: List[Show] = []
        for event in events:
            show = self._json_ld_event_to_show(event, comedian)
            if show:
                shows.append(show)
        return shows

    async def _fetch_subpage(self, url: str, comedian_name: str) -> Optional[str]:
        """Fetch a tour subpage, returning HTML or None on failure."""
        try:
            return await self.fetch_html(url, timeout=self._REQUEST_TIMEOUT)
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: {comedian_name} — failed to fetch subpage {url}: {e}",
            )
            return None

    @staticmethod
    def _deduplicate_events(events: list) -> list:
        """Remove duplicate JSON-LD events by (name, start_date, location.name)."""
        seen: set[tuple] = set()
        unique: list = []
        for event in events:
            location_name = ""
            if event.location:
                location_name = (event.location.name or "").strip().lower()
            key = (
                (event.name or "").strip().lower(),
                event.start_date.isoformat() if event.start_date else "",
                location_name,
            )
            if key not in seen:
                seen.add(key)
                unique.append(event)
        return unique

    # ------------------------------------------------------------------ #
    # Event conversion                                                     #
    # ------------------------------------------------------------------ #

    def _json_ld_event_to_show(self, event, comedian: Comedian) -> Optional[Show]:
        """Convert a JsonLdEvent to a Show, filtering to US-only future events."""
        try:
            # Parse date
            event_dt = event.start_date
            if event_dt is None:
                return None

            # Ensure timezone-aware
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=timezone.utc)

            # Only include future events
            if event_dt < datetime.now(tz=timezone.utc):
                return None

            # Extract venue information from the event location
            location = event.location
            if location is None:
                return None

            venue_name = (location.name or "").strip()
            if not venue_name:
                return None

            # Build address and filter to US
            address_obj = location.address
            city = ""
            state = ""
            zip_code = ""
            address = ""

            if address_obj:
                city = (address_obj.address_locality or "").strip()
                state = (address_obj.address_region or "").strip()
                zip_code = (address_obj.postal_code or "").strip()
                country = (address_obj.address_country or "").strip().upper()

                # Filter to US only
                if country and country not in ("US", "USA", "UNITED STATES"):
                    return None

                # If no country specified, check state is a known US state
                if not country and state and state.upper() not in _US_STATES:
                    return None

                address = f"{city}, {state}" if state else city

            tz = timezone_from_address(address) if address else None

            venue_dict = {
                "name": venue_name,
                "address": address,
                "zip_code": zip_code,
                "timezone": tz,
            }

            club = self._club_handler.upsert_for_tour_date_venue(venue_dict)
            if not club:
                return None

            # Use event URL or the offer URL as the show page URL
            show_url = event.url or ""
            if not show_url and event.offers:
                show_url = event.offers[0].url or ""

            return Show(
                name=event.name or f"{comedian.name} at {venue_name}",
                club_id=club.id,
                date=event_dt,
                show_page_url=show_url,
                description=event.description,
                timezone=club.timezone,
                lineup=[comedian],
            )

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error converting JSON-LD event to show: {e}",
                self.logger_context,
            )
            return None

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _persist_shows_and_lineups(self, shows: List[Show]) -> None:
        """Upsert shows and link comedians as LineupItems.

        Comedian insertion invariant: same as TourDatesScraper — comedians
        in show.lineup already exist in the DB (queried from the comedians
        table). batch_update_lineups will silently skip any missing UUIDs.
        """
        try:
            self._show_handler.insert_shows(shows)

            shows_with_ids = [s for s in shows if s.id is not None]
            if not shows_with_ids:
                return

            self._lineup_handler.batch_update_lineups(shows_with_ids, {})

            Logger.info(
                f"{self._log_prefix}: persisted {len(shows_with_ids)} shows with lineup links",
                self.logger_context,
            )
        except Exception as e:
            Logger.error(f"{self._log_prefix}: error persisting shows/lineups: {e}", self.logger_context)
            raise

    # ------------------------------------------------------------------ #
    # Metadata updates                                                     #
    # ------------------------------------------------------------------ #

    def _detect_and_persist_widgets(self, comedian_uuid: str, comedian_name: str, html: str) -> None:
        """Detect Bandsintown/Songkick widgets in HTML and write IDs to the comedian row."""
        try:
            result = detect_widgets(html)
            if not result.has_any:
                return

            parts = []
            if result.bandsintown_id:
                parts.append(f"bandsintown_id={result.bandsintown_id}")
            if result.songkick_id:
                parts.append(f"songkick_id={result.songkick_id}")

            Logger.info(
                f"{self._log_prefix}: {comedian_name} — widget detected: {', '.join(parts)}",
                self.logger_context,
            )

            self._comedian_handler.execute_batch_operation(
                ComedianQueries.UPDATE_COMEDIAN_TOUR_IDS,
                [(comedian_uuid, result.bandsintown_id, result.songkick_id)],
                log_summary=False,
            )
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error persisting widget IDs for {comedian_name}: {e}",
                self.logger_context,
            )

    def _update_scrape_metadata(self, comedian_uuid: str, strategy: str) -> None:
        """Update website_last_scraped and website_scrape_strategy for a comedian."""
        now = datetime.now(tz=timezone.utc).isoformat()
        try:
            self._comedian_handler.execute_batch_operation(
                ComedianQueries.UPDATE_COMEDIAN_WEBSITE_SCRAPE_METADATA,
                [(comedian_uuid, None, now, strategy)],
                log_summary=False,
            )
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error updating scrape metadata for {comedian_uuid}: {e}",
                self.logger_context,
            )

    def _update_confidence(self, comedian_uuid: str, comedian_name: str, website: str, has_events: bool) -> None:
        """Compute and persist website confidence score."""
        try:
            result = score_website(comedian_name, website, has_events=has_events)
            self._comedian_handler.execute_batch_operation(
                ComedianQueries.UPDATE_COMEDIAN_WEBSITE_CONFIDENCE,
                [(comedian_uuid, result.confidence)],
                log_summary=False,
            )
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error updating confidence for {comedian_uuid}: {e}",
                self.logger_context,
            )

    def _update_scraping_url(self, comedian_uuid: str, scraping_url: str) -> None:
        """Persist the discovered tour subpage URL for future scrape runs."""
        try:
            self._comedian_handler.execute_batch_operation(
                ComedianQueries.UPDATE_COMEDIAN_WEBSITE_SCRAPING_URL,
                [(comedian_uuid, scraping_url)],
                log_summary=False,
            )
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error updating scraping URL for {comedian_uuid}: {e}",
                self.logger_context,
            )

    # ------------------------------------------------------------------ #
    # DB helpers                                                           #
    # ------------------------------------------------------------------ #

    def _get_comedians_for_scraping(self, limit: Optional[int] = None, comedian_name: Optional[str] = None) -> List[dict]:
        """Query comedians with websites that need scraping."""
        if comedian_name:
            results = self._comedian_handler.execute_with_cursor(
                ComedianQueries.GET_COMEDIANS_WITH_WEBSITES + " AND LOWER(name) LIKE LOWER(%s)",
                (f"%{comedian_name}%",),
                return_results=True,
            )
        else:
            results = self._comedian_handler.execute_with_cursor(
                ComedianQueries.GET_COMEDIANS_FOR_WEBSITE_SCRAPING,
                return_results=True,
            )

        rows = [dict(row) for row in results] if results else []

        if limit and len(rows) > limit:
            rows = rows[:limit]

        return rows
