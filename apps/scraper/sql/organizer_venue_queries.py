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

    # NB: the upsert of this run's venue set is a multi-row execute_values insert
    # built inline in OrganizerVenueHandler.record_venues (it needs the VALUES %s
    # placeholder + per-row template), so there is intentionally no single-row
    # UPSERT constant here.

    # Drop a venue this organizer no longer produces (after the dropped-venue
    # reconcile, or when a sibling source owns it). Idempotent.
    DELETE_VENUE = """
        DELETE FROM eventbrite_organizer_venues
        WHERE production_company_id = %s
          AND club_id = %s
    """

    # Note: the TASK-2859 cross-organizer coverage probes (COVERED_BY_OTHER_ORGANIZER,
    # HAS_DIRECT_EVENTBRITE_SOURCE) were removed in TASK-2861. The reconcile no longer
    # skips shared venues; it scopes the DELETE to shows.scraped_by_organizer_id, so a
    # sibling source's shows are never matched. The history table here is now used only
    # to detect venues that dropped ENTIRELY from a feed.
