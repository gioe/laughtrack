"""
TourDatesScraper: fetches upcoming US tour dates for comedians that have
a songkick_id or bandsintown_id recorded in the comedians table.

For each event returned:
- Upserts a clubs row for the venue (scraper='tour_dates').
- Upserts a shows row for the event.
- Links the comedian as a LineupItem.

Triggered by a single clubs row with scraper='tour_dates'.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from urllib.parse import urlencode

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.lineup.handler import LineupHandler
from laughtrack.core.entities.show.handler import ShowHandler
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.config.config_manager import ConfigManager
from laughtrack.scrapers.base.base_scraper import BaseScraper
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


class TourDatesScraper(BaseScraper):
    """
    Artist-level tour-date scraper that queries Songkick and BandsInTown
    for upcoming US shows by comedians who have a songkick_id or
    bandsintown_id recorded in the comedians table.

    Triggered by a single clubs row with scraper='tour_dates'.
    For each tour date found, upserts a venue club, upserts the show,
    and links the comedian as a LineupItem.
    """

    key = "tour_dates"

    _SONGKICK_BASE_URL = "https://api.songkick.com/api/3.0"
    _BANDSINTOWN_BASE_URL = "https://rest.bandsintown.com/v3"
    _REQUEST_TIMEOUT = 30
    _MAX_PAGES = 20

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._club_handler = ClubHandler()
        self._comedian_handler = ComedianHandler()
        self._show_handler = ShowHandler()
        self._lineup_handler = LineupHandler()
        self._songkick_api_key: Optional[str] = ConfigManager.get_config("api", "songkick_api_key")
        self._bandsintown_app_id: Optional[str] = ConfigManager.get_config("api", "bandsintown_app_id")

    # ------------------------------------------------------------------ #
    # BaseScraper pipeline                                                 #
    # ------------------------------------------------------------------ #

    async def collect_scraping_targets(self) -> List[str]:
        """Single logical target representing the tour-date aggregation job."""
        return ["tour_dates"]

    async def get_data(self, target: str) -> None:
        """Not used: scrape_async is fully overridden."""
        return None  # pragma: no cover

    async def scrape_async(self) -> List[Show]:
        """Override: fetch tour dates per comedian, upsert venues, persist shows + lineups."""
        try:
            comedian_rows = self._get_comedians_with_tour_ids()
            if not comedian_rows:
                Logger.info("TourDates: no comedians with Songkick/BandsInTown IDs found", self.logger_context)
                return []

            Logger.info(
                f"TourDates: fetching tour dates for {len(comedian_rows)} comedians",
                self.logger_context,
            )

            all_shows: List[Show] = []

            for row in comedian_rows:
                comedian = Comedian(name=row["name"], uuid=row["uuid"])
                try:
                    shows: List[Show] = []

                    if row.get("songkick_id") and self._songkick_api_key:
                        shows.extend(
                            await self._fetch_songkick_shows(comedian, row["songkick_id"])
                        )
                    if row.get("bandsintown_id") and self._bandsintown_app_id:
                        shows.extend(
                            await self._fetch_bandsintown_shows(comedian, row["bandsintown_id"])
                        )

                    all_shows.extend(shows)
                except Exception as e:
                    Logger.error(
                        f"TourDates: skipping comedian '{comedian.name}' due to error: {e}",
                        self.logger_context,
                    )
                    continue

            Logger.info(
                f"TourDates: discovered {len(all_shows)} total tour-date shows",
                self.logger_context,
            )

            # Persist shows and link lineups within the scraper because the
            # standard ShowService pipeline does not process show.lineup.
            if all_shows:
                self._persist_shows_and_lineups(all_shows)

            return all_shows

        except Exception as e:
            Logger.error(f"TourDatesScraper failed: {e}", self.logger_context)
            raise
        finally:
            await self._cleanup_resources()

    # ------------------------------------------------------------------ #
    # Songkick                                                             #
    # ------------------------------------------------------------------ #

    async def _fetch_songkick_shows(self, comedian: Comedian, artist_id: str) -> List[Show]:
        """Fetch upcoming US tour dates from the Songkick artist calendar API."""
        shows: List[Show] = []
        page = 1

        while page <= self._MAX_PAGES:
            params = {
                "apikey": self._songkick_api_key,
                "per_page": 50,
                "page": page,
            }
            url = f"{self._SONGKICK_BASE_URL}/artists/{artist_id}/calendar.json?{urlencode(params)}"

            try:
                data = await self.fetch_json(url, timeout=self._REQUEST_TIMEOUT)
            except Exception as e:
                Logger.error(
                    f"TourDates/Songkick: error fetching page {page} for artist {artist_id}: {e}",
                    self.logger_context,
                )
                break

            if not data:
                break

            results_page = data.get("resultsPage", {})
            if results_page.get("status") == "error":
                Logger.warn(
                    f"TourDates/Songkick: API error for artist {artist_id}: {results_page.get('error')}",
                    self.logger_context,
                )
                break

            entries = results_page.get("results", {}).get("calendarEntry", []) or []
            if not entries:
                break

            for entry in entries:
                event = entry.get("event", {})
                show = self._songkick_event_to_show(event, comedian)
                if show:
                    shows.append(show)

            total_entries = results_page.get("totalEntries", 0)
            per_page = results_page.get("perPage", 50)
            if page * per_page >= total_entries:
                break
            page += 1

        return shows

    def _songkick_event_to_show(self, event: dict, comedian: Comedian) -> Optional[Show]:
        """Convert a Songkick calendar event to a Show, or None if not a US event."""
        try:
            # Only include US events
            location = event.get("location", {})
            city_str = location.get("city", "")  # e.g. "New York, NY, US"
            if not city_str.endswith(", US"):
                return None

            venue_data = event.get("venue", {}) or {}
            venue_name = (venue_data.get("displayName") or "").strip()
            if not venue_name:
                return None

            # Parse date
            start = event.get("start", {})
            date_str = start.get("datetime") or start.get("date")
            if not date_str:
                return None

            event_dt = self._parse_datetime(date_str)
            if not event_dt:
                return None

            # Only include future events
            if event_dt < datetime.now(tz=timezone.utc):
                return None

            # Build address from city string components ("New York, NY, US" → "New York, NY")
            city_core = city_str.removesuffix(", US")
            parts = [p.strip() for p in city_core.split(",")]
            state = parts[-1].strip() if len(parts) >= 2 else ""
            city = parts[0].strip() if parts else ""
            address = f"{city}, {state}" if state else city

            venue = {
                "name": venue_name,
                "address": address,
                "zip_code": "",
                "timezone": timezone_from_address(address),
            }

            club = self._club_handler.upsert_for_tour_date_venue(venue)
            if not club:
                return None

            show_url = event.get("uri") or f"https://www.songkick.com/concerts/{event.get('id', '')}"

            return Show(
                name=f"{comedian.name} at {venue_name}",
                club_id=club.id,
                date=event_dt,
                show_page_url=show_url,
                description=event.get("displayName"),
                timezone=club.timezone,
                lineup=[comedian],
            )

        except Exception as e:
            Logger.error(
                f"TourDates/Songkick: error converting event to show: {e}",
                self.logger_context,
            )
            return None

    # ------------------------------------------------------------------ #
    # BandsInTown                                                          #
    # ------------------------------------------------------------------ #

    async def _fetch_bandsintown_shows(self, comedian: Comedian, artist_id: str) -> List[Show]:
        """Fetch upcoming US tour dates from the BandsInTown artist events API."""
        now = datetime.now(tz=timezone.utc)
        date_from = now.strftime("%Y-%m-%d")
        date_to = (now + timedelta(days=365)).strftime("%Y-%m-%d")

        params = {
            "app_id": self._bandsintown_app_id,
            "date": f"{date_from},{date_to}",
        }
        url = f"{self._BANDSINTOWN_BASE_URL}/artists/{artist_id}/events?{urlencode(params)}"

        try:
            data = await self.fetch_json(url, timeout=self._REQUEST_TIMEOUT)
        except Exception as e:
            Logger.error(
                f"TourDates/BandsInTown: error fetching events for artist {artist_id}: {e}",
                self.logger_context,
            )
            return []

        if not data or not isinstance(data, list):
            return []

        shows: List[Show] = []
        for event in data:
            show = self._bandsintown_event_to_show(event, comedian)
            if show:
                shows.append(show)

        return shows

    def _bandsintown_event_to_show(self, event: dict, comedian: Comedian) -> Optional[Show]:
        """Convert a BandsInTown event to a Show, or None if not a US event."""
        try:
            venue = event.get("venue", {}) or {}
            country = (venue.get("country") or "").strip()
            # Filter to US only
            if country not in ("United States", "US"):
                return None

            venue_name = (venue.get("name") or "").strip()
            if not venue_name:
                return None

            date_str = event.get("datetime") or event.get("starts_at")
            if not date_str:
                return None

            event_dt = self._parse_datetime(date_str)
            if not event_dt:
                return None

            # Only include future events
            if event_dt < datetime.now(tz=timezone.utc):
                return None

            city = (venue.get("city") or "").strip()
            region = (venue.get("region") or "").strip()
            # Filter: region should be a known US state abbreviation
            if region and region not in _US_STATES:
                return None

            address = f"{city}, {region}" if region else city
            zip_code = (venue.get("postal_code") or "").strip()

            venue_dict = {
                "name": venue_name,
                "address": address,
                "zip_code": zip_code,
                "timezone": timezone_from_address(address),
            }

            club = self._club_handler.upsert_for_tour_date_venue(venue_dict)
            if not club:
                return None

            show_url = event.get("url") or f"https://www.bandsintown.com/e/{event.get('id', '')}"

            return Show(
                name=f"{comedian.name} at {venue_name}",
                club_id=club.id,
                date=event_dt,
                show_page_url=show_url,
                description=event.get("description") or event.get("title"),
                timezone=club.timezone,
                lineup=[comedian],
            )

        except Exception as e:
            Logger.error(
                f"TourDates/BandsInTown: error converting event to show: {e}",
                self.logger_context,
            )
            return None

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _persist_shows_and_lineups(self, shows: List[Show]) -> None:
        """Upsert shows and link comedians as LineupItems."""
        try:
            # insert_shows() upserts shows and populates their .id fields
            self._show_handler.insert_shows(shows)

            # Gather shows that now have DB IDs
            shows_with_ids = [s for s in shows if s.id is not None]
            if not shows_with_ids:
                return

            # batch_update_lineups needs the current DB state as the baseline;
            # pass empty dict so it only adds (never removes).
            self._lineup_handler.batch_update_lineups(shows_with_ids, {})

            Logger.info(
                f"TourDates: persisted {len(shows_with_ids)} shows with lineup links",
                self.logger_context,
            )
        except Exception as e:
            Logger.error(f"TourDates: error persisting shows/lineups: {e}", self.logger_context)
            raise

    # ------------------------------------------------------------------ #
    # DB helpers                                                           #
    # ------------------------------------------------------------------ #

    def _get_comedians_with_tour_ids(self) -> List[dict]:
        """Query all comedians that have a songkick_id or bandsintown_id."""
        results = self._comedian_handler.execute_with_cursor(
            ComedianQueries.GET_COMEDIANS_WITH_TOUR_IDS,
            return_results=True,
        )
        return [dict(row) for row in results] if results else []

    # ------------------------------------------------------------------ #
    # Utility                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_datetime(date_str: str) -> Optional[datetime]:
        """Parse an ISO-8601 date/datetime string into a UTC-aware datetime."""
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S+0000",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue
        return None
