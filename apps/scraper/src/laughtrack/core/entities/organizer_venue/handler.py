"""Handler for the per-organizer Eventbrite venue history (TASK-2859).

Records which venue club_ids each Eventbrite organizer (production company) feed
produced shows for, so a later clean scrape can diff its current venue set
against the prior one and detect venues that dropped ENTIRELY from the feed.
(The TASK-2859 cross-organizer coverage probes were removed in TASK-2861, which
scopes the reconcile DELETE to shows.scraped_by_organizer_id instead.)
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
