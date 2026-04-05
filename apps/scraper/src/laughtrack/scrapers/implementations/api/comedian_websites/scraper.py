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
from typing import Dict, List, Optional

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.lineup.handler import LineupHandler
from laughtrack.core.entities.show.handler import ShowHandler
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.utilities.domain.club.timezone_lookup import timezone_from_address
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

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._club_handler = ClubHandler()
        self._comedian_handler = ComedianHandler()
        self._show_handler = ShowHandler()
        self._lineup_handler = LineupHandler()

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
            comedian_rows = self._get_comedians_for_scraping()
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

    async def _scrape_comedian_website(self, row: dict, semaphore: asyncio.Semaphore) -> List[Show]:
        """Fetch a comedian's website, extract JSON-LD events, and convert to Shows."""
        comedian = Comedian(name=row["name"], uuid=row["uuid"])
        website = row.get("website", "").strip()
        strategy = "none"

        async with semaphore:
            try:
                if not website:
                    return []

                html = await self.fetch_html(website, timeout=self._REQUEST_TIMEOUT)
                if not html:
                    self._update_scrape_metadata(row["uuid"], strategy)
                    return []

                events = EventExtractor.extract_events(html)
                if not events:
                    strategy = "json_ld_empty"
                    self._update_scrape_metadata(row["uuid"], strategy)
                    return []

                strategy = "json_ld"
                shows: List[Show] = []
                for event in events:
                    show = self._json_ld_event_to_show(event, comedian)
                    if show:
                        shows.append(show)

                self._update_scrape_metadata(row["uuid"], strategy)

                if shows:
                    Logger.info(
                        f"{self._log_prefix}: {comedian.name} — {len(shows)} shows extracted from {website}",
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
