"""SQL queries for per-organizer Eventbrite venue history (TASK-2859).

Records the distinct venue club_ids each Eventbrite organizer (production
company) feed produced shows for, so a later clean scrape can detect a venue
that dropped entirely from the feed and reconcile its now-stale future shows.
"""


class OrganizerVenueQueries:
    """SQL for the eventbrite_organizer_venues history table."""

    # The organizer's persisted venue set (its prior run's venues).
    GET_VENUE_CLUB_IDS = """
        SELECT club_id
        FROM eventbrite_organizer_venues
        WHERE production_company_id = %s
    """

    # Stamp this run's venues. last_seen_at is refreshed so the row reflects the
    # most recent run that produced a show for the venue.
    UPSERT_VENUE = """
        INSERT INTO eventbrite_organizer_venues (production_company_id, club_id, last_seen_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (production_company_id, club_id)
        DO UPDATE SET last_seen_at = NOW()
    """

    # Drop a venue this organizer no longer produces (after the dropped-venue
    # reconcile, or when a sibling source owns it). Idempotent.
    DELETE_VENUE = """
        DELETE FROM eventbrite_organizer_venues
        WHERE production_company_id = %s
          AND club_id = %s
    """

    # Cross-organizer safety (criterion 9184): is this venue claimed by ANY other
    # organizer's history? If so, that organizer still maintains the venue's shows
    # and this organizer must not reconcile (delete) them.
    COVERED_BY_OTHER_ORGANIZER = """
        SELECT 1
        FROM eventbrite_organizer_venues
        WHERE club_id = %s
          AND production_company_id <> %s
        LIMIT 1
    """

    # Cross-organizer safety (criterion 9184): does the venue have its OWN enabled
    # direct Eventbrite scraping source? If so, it is independently scraped and an
    # organizer drop must not delete its inventory.
    HAS_DIRECT_EVENTBRITE_SOURCE = """
        SELECT 1
        FROM scraping_sources
        WHERE club_id = %s
          AND platform = 'eventbrite'
          AND enabled = TRUE
        LIMIT 1
    """
