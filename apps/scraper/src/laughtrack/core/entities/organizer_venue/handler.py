"""Handler for the per-organizer Eventbrite venue history (TASK-2859).

Records which venue club_ids each Eventbrite organizer (production company) feed
produced shows for, and answers the cross-organizer safety questions the
dropped-venue reconciler needs before deleting any inventory.
"""

from typing import List

from psycopg2.extras import execute_values
from sql.organizer_venue_queries import OrganizerVenueQueries

from laughtrack.core.data.base_handler import BaseDatabaseHandler


class OrganizerVenueHandler(BaseDatabaseHandler[int]):
    """Reads and writes the eventbrite_organizer_venues history table."""

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "organizer_venue"

    def get_entity_class(self) -> type[int]:
        """The history table has no rich domain model; rows are (pc_id, club_id).

        Required by BaseDatabaseHandler's abstract contract but never used on this
        handler's code paths (all access is via raw queries below).
        """
        return int

    def get_venue_club_ids(self, production_company_id: int) -> List[int]:
        """Return the organizer's persisted venue set (its prior run's venues)."""
        rows = self.execute_with_cursor(
            OrganizerVenueQueries.GET_VENUE_CLUB_IDS,
            (production_company_id,),
            return_results=True,
        )
        return [row["club_id"] for row in rows] if rows else []

    def record_venues(self, production_company_id: int, club_ids: List[int]) -> None:
        """Upsert this run's venue set, refreshing last_seen_at for each venue."""
        if not club_ids:
            return
        with self.transaction() as conn:
            with conn.cursor() as cursor:
                execute_values(
                    cursor,
                    """
                    INSERT INTO eventbrite_organizer_venues
                        (production_company_id, club_id, last_seen_at)
                    VALUES %s
                    ON CONFLICT (production_company_id, club_id)
                    DO UPDATE SET last_seen_at = NOW()
                    """,
                    [(production_company_id, club_id) for club_id in club_ids],
                    template="(%s, %s, NOW())",
                )

    def forget_venue(self, production_company_id: int, club_id: int) -> None:
        """Drop a venue this organizer no longer produces. Idempotent."""
        self.execute_with_cursor(
            OrganizerVenueQueries.DELETE_VENUE,
            (production_company_id, club_id),
        )

    def is_venue_covered_elsewhere(
        self, production_company_id: int, club_id: int
    ) -> bool:
        """Does a sibling Eventbrite source still maintain this venue's shows?

        True when another organizer's history claims the venue, or when the venue
        has its own enabled direct Eventbrite scraping source. The dropped-venue
        (and present-venue) reconcile must skip such venues so it never deletes a
        sibling source's live inventory (criterion 9184).
        """
        other = self.execute_with_cursor(
            OrganizerVenueQueries.COVERED_BY_OTHER_ORGANIZER,
            (club_id, production_company_id),
            return_results=True,
        )
        if other:
            return True
        direct = self.execute_with_cursor(
            OrganizerVenueQueries.HAS_DIRECT_EVENTBRITE_SOURCE,
            (club_id,),
            return_results=True,
        )
        return bool(direct)
