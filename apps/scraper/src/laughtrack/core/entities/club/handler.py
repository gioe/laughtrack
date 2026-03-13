"""Club database handler for club-specific operations."""

from typing import List, Optional

from sql.club_queries import ClubQueries

from laughtrack.core.data.base_handler import BaseDatabaseHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger

from .model import Club


class ClubHandler(BaseDatabaseHandler[Club]):
    """Handler for club database operations."""

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "club"

    def get_entity_class(self) -> type[Club]:
        """Return the Club class for instantiation."""
        return Club

    def get_all_clubs(self) -> List[Club]:
        """
        Fetch all clubs with non-null scrapers from database.

        Returns:
            List[Club]: List of all active clubs
        """
        try:
            results = self.execute_with_cursor(ClubQueries.GET_ALL_CLUBS, return_results=True)
            if not results:
                raise ValueError("No clubs found in database")

            Logger.info(f"Retrieved {len(results)} clubs from database")
            return [Club.from_db_row(row) for row in results]

        except Exception as e:
            Logger.error(f"Error fetching clubs: {str(e)}")
            raise

    def get_clubs_by_ids(self, club_ids: List[int]) -> List[Club]:
        """
        Fetch clubs by their IDs.

        Args:
            club_ids: List of club IDs to retrieve, or a single ID in a list

        Returns:
            List[Club]: List of clubs matching the provided IDs
        """
        if not club_ids:
            Logger.info("No club IDs provided")
            return []

        try:
            results = self.execute_with_cursor(ClubQueries.GET_CLUB_BY_IDS, (club_ids,), return_results=True)
            if not results:
                raise ValueError(f"No clubs found for IDs: {club_ids}")

            Logger.info(f"Retrieved {len(results)} clubs for {len(club_ids)} requested IDs")
            return [Club.from_db_row(row) for row in results]

        except Exception as e:
            Logger.error(f"Error fetching clubs {club_ids}: {str(e)}")
            raise

    def get_club_by_id(self, club_id: int) -> Optional[Club]:
        """
        Fetch a single club by its ID.

        Args:
            club_id: The club ID to retrieve

        Returns:
            Club | None: The club if found, None otherwise
        """
        if not club_id:
            raise ValueError("No club ID provided")

        clubs = self.get_clubs_by_ids([club_id])
        return clubs[0] if clubs else None

    def get_specific_clubs(self, club_ids: List[int]) -> List[Club]:
        """
        Fetch specific clubs by their IDs.

        Deprecated: Use get_clubs_by_ids instead.

        Args:
            club_ids: List of club IDs to retrieve

        Returns:
            List[Club]: List of clubs matching the provided IDs
        """
        return self.get_clubs_by_ids(club_ids)

    def upsert_for_eventbrite_venue(self, venue) -> Optional[Club]:
        """
        Upsert a clubs row for an Eventbrite venue discovered via the national
        search API.  On conflict (name), preserves any existing eventbrite_id
        and scraper values rather than overwriting them.

        Args:
            venue: EventbriteVenue from the API response

        Returns:
            Club: the upserted (or existing) club, or None on invalid input
        """
        if not venue or not getattr(venue, "id", None) or not getattr(venue, "name", None):
            return None

        address = ""
        zip_code = ""
        if venue.address:
            parts = [
                p for p in [venue.address.address_1, venue.address.city, venue.address.region]
                if p
            ]
            address = ", ".join(parts)
            zip_code = venue.address.postal_code or ""

        try:
            results = self.execute_with_cursor(
                ClubQueries.UPSERT_CLUB_BY_EVENTBRITE_VENUE,
                (venue.name, address, venue.id, zip_code),
                return_results=True,
            )
            if not results:
                return None
            return Club.from_db_row(results[0])
        except Exception as e:
            Logger.error(f"Error upserting club for Eventbrite venue {venue.id}: {e}")
            raise

    def upsert_for_seatengine_venue(self, venue: dict) -> Optional[Club]:
        """
        Upsert a clubs row for a SeatEngine venue discovered via the national
        enumeration job.  On conflict (name), preserves any existing seatengine_id
        and scraper values rather than overwriting them.

        Args:
            venue: dict with at minimum 'id' and 'name' keys from SeatEngine API

        Returns:
            Club: the upserted (or existing) club, or None on invalid input
        """
        venue_id = str(venue.get("id", "")).strip()
        name = (venue.get("name") or "").strip()
        if not venue_id or not name:
            return None

        address = (venue.get("address") or "").strip()
        website = (venue.get("website") or "").strip()
        zip_code = (venue.get("zip") or venue.get("postal_code") or "").strip()

        try:
            results = self.execute_with_cursor(
                ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE,
                (name, address, website, venue_id, zip_code),
                return_results=True,
            )
            if not results:
                return None
            return Club.from_db_row(results[0])
        except Exception as e:
            Logger.error(f"Error upserting club for SeatEngine venue {venue_id}: {e}")
            raise

    def upsert_for_ticketmaster_venue(self, venue: dict) -> Optional[Club]:
        """
        Upsert a clubs row for a Ticketmaster venue discovered via the national
        comedy genre scraper.  On conflict (name), preserves any existing
        ticketmaster_id, scraper, and timezone values.

        Args:
            venue: dict from TM Discovery API _embedded.venues[0]

        Returns:
            Club: the upserted (or existing) club, or None on invalid input
        """
        venue_id = (venue.get("id") or "").strip()
        name = (venue.get("name") or "").strip()
        if not venue_id or not name:
            return None

        address_obj = venue.get("address") or {}
        street = address_obj.get("line1", "")
        city = (venue.get("city") or {}).get("name", "")
        state = (venue.get("state") or {}).get("stateCode", "")
        address_parts = [p for p in [street, city, state] if p]
        address = ", ".join(address_parts)
        zip_code = (venue.get("postalCode") or "").strip()
        timezone = (venue.get("timezone") or "").strip() or None

        try:
            results = self.execute_with_cursor(
                ClubQueries.UPSERT_CLUB_BY_TICKETMASTER_VENUE,
                (name, address, venue_id, zip_code, timezone),
                return_results=True,
            )
            if not results:
                return None
            return Club.from_db_row(results[0])
        except Exception as e:
            Logger.error(f"Error upserting club for Ticketmaster venue {venue_id}: {e}")
            raise

    def enrich_timezones(self, scraper: str = "eventbrite") -> int:
        """
        Enrich timezone for clubs that were upserted without one.

        Queries clubs WHERE scraper = <scraper> AND timezone IS NULL, infers
        the timezone from the stored address (US state abbreviation), and
        updates only rows still NULL — so re-running is always safe.

        Args:
            scraper: The scraper type to filter clubs by (default: 'eventbrite').

        Returns:
            Number of clubs whose timezone was successfully updated.
        """
        from laughtrack.utilities.domain.club.timezone_lookup import timezone_from_address  # noqa: PLC0415

        rows = self.execute_with_cursor(
            ClubQueries.GET_CLUBS_WITH_NULL_TIMEZONE,
            (scraper,),
            return_results=True,
        )
        if not rows:
            Logger.info(f"No clubs with scraper='{scraper}' and timezone=NULL found.")
            return 0

        updates: List[tuple] = []
        for row in rows:
            club = Club.from_db_row(row)
            tz = timezone_from_address(club.address)
            if tz:
                updates.append((club.id, tz))
            else:
                Logger.warning(
                    f"Could not resolve timezone for club {club.id} '{club.name}' "
                    f"(address: {club.address!r})"
                )

        if not updates:
            Logger.info("Timezone enrichment: no resolvable timezones found.")
            return 0

        results = self.execute_batch_operation(
            ClubQueries.BATCH_UPDATE_CLUB_TIMEZONES,
            updates,
            return_results=True,
        )
        updated = len(results) if results else 0
        Logger.info(f"Timezone enrichment complete: {updated}/{len(rows)} clubs updated.")
        return updated

    def get_clubs_for_scraper(self, scraper_type: str) -> List[Club]:
        """
        Fetch all clubs that use a specific scraper type.

        Args:
            scraper_type: The scraper type to filter clubs by

        Returns:
            List[Club]: List of clubs using the specified scraper type
        """
        if not scraper_type:
            raise ValueError("No scraper type provided")

        try:
            results = self.execute_with_cursor(ClubQueries.GET_CLUBS_BY_SCRAPER, (scraper_type,), return_results=True)
            if not results:
                raise ValueError(f"No clubs found for scraper type: {scraper_type}")

            Logger.info(f"Retrieved {len(results)} clubs for scraper type '{scraper_type}'")
            return [Club.from_db_row(row) for row in results]

        except Exception as e:
            Logger.error(f"Error fetching clubs for scraper '{scraper_type}': {str(e)}")
            raise
