"""SQL queries for show operations."""


class ShowQueries:
    """SQL queries for show operations."""
    
    GET_ALL_SHOW_IDS = """
        SELECT id FROM shows ORDER BY id;
    """
    
    VALIDATE_SHOW_IDS = """
        SELECT id FROM shows WHERE id = ANY(%s) ORDER BY id;
    """
    
    GET_SHOW_DETAILS = """
        SELECT 
            id, name, show_page_url, description, date, club_id, room, popularity, show_type
        FROM shows
        WHERE id = ANY(%s)
        ORDER BY id;
    """
    
    BATCH_INSERT_SHOWS = '''
        INSERT INTO shows (
            name, show_page_url, description, date, club_id, last_scraped_date, room,
            production_company_id, last_scraped_by, scraped_by_organizer_id, show_type
        )
        VALUES %s
        ON CONFLICT (club_id, date, room)
        DO UPDATE SET
            name = EXCLUDED.name,
            show_page_url = EXCLUDED.show_page_url,
            description = EXCLUDED.description,
            date = EXCLUDED.date,
            club_id = EXCLUDED.club_id,
            last_scraped_date = EXCLUDED.last_scraped_date,
            room = EXCLUDED.room,
            production_company_id = COALESCE(EXCLUDED.production_company_id, shows.production_company_id),
            last_scraped_by = COALESCE(EXCLUDED.last_scraped_by, shows.last_scraped_by),
            -- Overwrite (NOT coalesce): the last producer's attribution always
            -- wins. An organizer stamps its id; a non-organizer re-scrape sets it
            -- NULL, correctly clearing the claim so that organizer's reconcile no
            -- longer matches the row (TASK-2861).
            scraped_by_organizer_id = EXCLUDED.scraped_by_organizer_id,
            show_type = EXCLUDED.show_type
        RETURNING
            id, club_id, room, date,
            CASE
                WHEN xmax::text::int > 0 THEN 'updated'
                ELSE 'inserted'
            END AS operation_type
    '''

    # TASK-2847: stale-future-show reconciliation. After a CLEAN scrape of a
    # club (see ScrapingResultProcessor._is_clean_for_reconciliation), delete
    # future shows that THIS scraper key produced but did not re-emit this run —
    # their source event was cancelled/delisted. Scoped to last_scraped_by so a
    # multi-source club's other scrapers' shows are never touched; gated on
    # last_scraped_date < the cutoff captured before this run's upsert, so shows
    # re-seen this run (stamped now() by Show.to_tuple) are excluded. Tickets and
    # ticket-click events cascade (onDelete: Cascade). A NULL last_scraped_date is
    # left alone — only rows this scraper is known to have last seen before now
    # are removed.
    DELETE_STALE_FUTURE_SHOWS = '''
        DELETE FROM shows
        WHERE club_id = %s
          AND last_scraped_by = %s
          AND date > NOW()
          AND last_scraped_date < %s
        RETURNING id, name, date, room
    '''

    # Companion count for the same predicate as DELETE_STALE_FUTURE_SHOWS. The
    # reconciler counts first and refuses to delete when the count exceeds a
    # safety cap: a single clean scrape that drops a venue's ENTIRE future
    # calendar at once is the signature of a silent parser break (e.g. an
    # upstream JSON shape change yielding zero events on an HTTP 200), not a
    # handful of genuine per-event cancellations. Over the cap, the reconciler
    # logs loudly for human review instead of wiping inventory (TASK-2847).
    COUNT_STALE_FUTURE_SHOWS = '''
        SELECT COUNT(*) AS stale_count
        FROM shows
        WHERE club_id = %s
          AND last_scraped_by = %s
          AND date > NOW()
          AND last_scraped_date < %s
    '''

    # TASK-2861: organizer-attributed variant of the stale-future-show reconcile.
    # Eventbrite organizer-mode scrapes scope by scraped_by_organizer_id (the
    # production company whose /o/ feed produced the show) instead of
    # last_scraped_by, because every Eventbrite show shares
    # last_scraped_by='eventbrite'. This deletes ONLY future shows THIS organizer
    # produced but did not re-emit this run, so a sibling organizer/source's shows
    # at a shared venue are never touched, while cancelled shows at a
    # multi-organizer venue ARE reconciled. Same cutoff semantics as the
    # scraper-key variant (last_scraped_date < the pre-upsert cutoff).
    DELETE_STALE_FUTURE_SHOWS_BY_ORGANIZER = '''
        DELETE FROM shows
        WHERE club_id = %s
          AND scraped_by_organizer_id = %s
          AND date > NOW()
          AND last_scraped_date < %s
        RETURNING id, name, date, room
    '''

    COUNT_STALE_FUTURE_SHOWS_BY_ORGANIZER = '''
        SELECT COUNT(*) AS stale_count
        FROM shows
        WHERE club_id = %s
          AND scraped_by_organizer_id = %s
          AND date > NOW()
          AND last_scraped_date < %s
    '''

    GET_SHOWS_BY_CLUB_DATE_NAME = '''
        SELECT id, club_id, date, room, COALESCE(name, '') AS name
        FROM shows
        WHERE club_id = ANY(%s)
          AND date = ANY(%s)
          AND COALESCE(name, '') = ANY(%s)
        ORDER BY id
    '''

    # Club names for the room-equals-club-name suppression in
    # _suppress_room_matching_club_name: scrapers (ticketmaster/live_nation,
    # tixr PIXL) copy the venue name into room, which carries no information and
    # duplicates the club name on every show row.
    GET_CLUB_NAMES_BY_IDS = '''
        SELECT id, name
        FROM clubs
        WHERE id = ANY(%s)
    '''

    # PatronTicket-family shows (generic patron_ticket + bespoke up_comedy_club)
    # carry a stable Salesforce instance id in the #/instances/<id> fragment of
    # show_page_url. Fetch existing instance-bearing rows for the affected clubs so
    # the handler can match an incoming show to its existing row by instance id and
    # move it to a rescheduled date in place (see _reconcile_patronticket_instances).
    GET_PATRONTICKET_SHOWS_BY_CLUB = '''
        SELECT id, club_id, date, room, show_page_url
        FROM shows
        WHERE club_id = ANY(%s)
          AND show_page_url LIKE '%%/instances/%%'
        ORDER BY id
    '''

    # SeatEngine Classic performance pages have stable /shows/<id> URLs. Fetch
    # existing rows for affected clubs so the handler can move a rescheduled or
    # corrected row in place before the (club_id, date, room) upsert. Includes
    # legacy NULL-attributed rows so a current scrape can overwrite old multi-tier
    # ticket rows through the normal stale-ticket sweep.
    GET_SEATENGINE_CLASSIC_SHOWS_BY_CLUB = '''
        SELECT id, club_id, date, room, show_page_url, last_scraped_by
        FROM shows
        WHERE club_id = ANY(%s)
          AND show_page_url LIKE '%%/shows/%%'
          AND (last_scraped_by = 'seatengine_classic' OR last_scraped_by IS NULL)
        ORDER BY id
    '''

    # Move an existing show to a new (rescheduled) date in place, keyed by id, so the
    # downstream ON CONFLICT (club_id, date, room) upsert updates the same row instead
    # of inserting a near-duplicate. The NOT EXISTS guard prevents a unique-constraint
    # violation if some other row already occupies (club_id, new_date, room); in that
    # case the move is skipped and the upsert reconciles against that row instead.
    # Params: (new_date, show_id, new_date).
    UPDATE_SHOW_DATE_BY_ID = '''
        UPDATE shows AS s
        SET date = %s
        WHERE s.id = %s
          AND NOT EXISTS (
              SELECT 1 FROM shows o
              WHERE o.club_id = s.club_id
                AND o.date = %s
                AND o.room = s.room
                AND o.id <> s.id
          )
    '''
    
    # Recent ticket-purchase click counts per show. All clicks count, including
    # clicks without confirmed purchases: this is an intent signal until the app
    # has conversion tracking. The 30-day window matches the freshest first-party
    # demand signal used by BATCH_GET_LINEUP_POPULARITY.
    BATCH_GET_SHOW_CLICK_DEMAND = '''
        SELECT
            show_id,
            COUNT(*) AS click_count,
            LEAST(COUNT(*)::float / 5.0, 1.0) AS click_demand_rate
        FROM ticket_purchase_click_events
        WHERE show_id = ANY(%s::int[])
          AND created_at >= NOW() - INTERVAL '30 days'
        GROUP BY show_id
    '''

    # Show popularity ∈ [0, 1], blended from lineup, venue, ticket-sales, and
    # recent ticket-purchase click demand signals and multiplied by a piecewise
    # time-decay on s.date so upcoming shows score highest and past shows fade.
    # Component weights mirror PopularityScorer.calculate_show_popularity (the
    # docstring contract this SQL must honor):
    #   - lineup (0.45): headliner-concentrated weighted average of comedian
    #     popularity over the show's lineup: 0.7 * top headliner + 0.3 * rest
    #     average. For one-comedian shows, rest average falls back to the top
    #     headliner, so a solo touring headliner keeps the full lineup signal.
    #     Comedian popularity is already in [0, 1] from update_comedian_popularity.
    #   - venue  (0.20): clubs.popularity, already in [0, 1] from
    #     BATCH_UPDATE_CLUB_POPULARITY's outer LEAST clamp.
    #   - sales  (0.25): 1.0 if any ticket for the show is sold_out, else 0.0.
    #   - click demand (0.10): all ticket-purchase clicks in the last 30 days,
    #     saturated at 5 clicks per show. These are intent clicks; they do not
    #     require confirmed purchases until conversion tracking exists.
    # Each component ∈ [0, 1] and weights sum to 1.0, so the blend is bounded.
    # Time-decay ∈ [0.1, 1.0]; the product is therefore already in [0, 1].
    # Outer LEAST(..., 1.0) is a belt-and-suspenders clamp that pins the
    # docstring contract regardless of upstream drift — the previous SQL had
    # no clamp and produced values up to 3.76 in production (TASK-2697).
    #
    # The LATERAL aggregation for tickets mirrors BATCH_UPDATE_COMEDIAN_SHOW_COUNTS:
    # BOOL_OR per show via the tickets(show_id, type) unique index, so work
    # scales with len(shows in batch) instead of len(tickets) and the query
    # stays inside Neon's statement_timeout under live load.
    #
    # Coverage note: this CTE returns one row per input show_id (LEFT JOIN from
    # shows, not from lineup_items), so shows with empty lineups are no longer
    # silently skipped — they get popularity computed from venue + sales +
    # time-decay alone (lineup component → 0 via COALESCE). Previously such
    # shows kept whatever popularity was last written (often stale), which
    # was harmless when the formula was lineup-only and 0 was the right floor,
    # but is wrong now that other signals matter. The downside is one extra
    # BATCH_UPDATE_SHOW_POPULARITY row per empty-lineup show per nightly run.
    BATCH_GET_LINEUP_POPULARITY = '''
        WITH lineup_ranked AS (
            SELECT
                s.id AS show_id,
                s.club_id,
                s.date,
                c.popularity,
                ROW_NUMBER() OVER (
                    PARTITION BY s.id
                    ORDER BY c.popularity DESC NULLS LAST
                ) AS lineup_rank
            FROM shows s
            LEFT JOIN lineup_items li ON li.show_id = s.id
            LEFT JOIN comedians c ON c.uuid = li.comedian_id
            WHERE s.id = ANY(%s)
        ),
        show_lineup AS (
            SELECT
                show_id,
                club_id,
                date,
                MAX(popularity) FILTER (WHERE lineup_rank = 1) AS top_headliner_popularity,
                AVG(popularity) FILTER (WHERE lineup_rank > 1) AS rest_lineup_popularity
            FROM lineup_ranked
            GROUP BY show_id, club_id, date
        )
        SELECT
            sl.show_id,
            LEAST(
                (
                    (
                        COALESCE(sl.top_headliner_popularity, 0) * 0.7
                        + COALESCE(sl.rest_lineup_popularity, sl.top_headliner_popularity, 0) * 0.3
                    ) * 0.45
                    + COALESCE(cl.popularity, 0) * 0.2
                    + CASE WHEN sales.any_sold_out THEN 1.0 ELSE 0.0 END * 0.25
                    + COALESCE(clicks.click_demand_rate, 0) * 0.1
                ) * (
                    CASE
                        WHEN sl.date >= CURRENT_DATE THEN 1.0
                        WHEN sl.date >= CURRENT_DATE - INTERVAL '30 days' THEN 0.75
                        WHEN sl.date >= CURRENT_DATE - INTERVAL '90 days' THEN 0.5
                        WHEN sl.date >= CURRENT_DATE - INTERVAL '180 days' THEN 0.25
                        ELSE 0.1
                    END
                ),
                1.0
            ) AS modified_popularity
        FROM show_lineup sl
        LEFT JOIN clubs cl ON cl.id = sl.club_id
        LEFT JOIN LATERAL (
            SELECT BOOL_OR(t.sold_out) AS any_sold_out
            FROM tickets t
            WHERE t.show_id = sl.show_id
        ) sales ON true
        LEFT JOIN LATERAL (
            SELECT LEAST(COUNT(*)::float / 5.0, 1.0) AS click_demand_rate
            FROM ticket_purchase_click_events tpce
            WHERE tpce.show_id = sl.show_id
              AND tpce.created_at >= NOW() - INTERVAL '30 days'
        ) clicks ON true
    '''
    
    BATCH_UPDATE_SHOW_POPULARITY = '''
        UPDATE shows
        SET popularity = v.modified_popularity
        FROM (
            SELECT show_id, modified_popularity
            FROM UNNEST(%s::int[], %s::numeric[]) AS v(show_id, modified_popularity)
        ) v
        WHERE id = v.show_id
    '''
    
    DELETE_ORPHANED_SHOWS = '''
        DELETE FROM shows 
        WHERE id NOT IN (
            SELECT DISTINCT show_id 
            FROM lineup_items 
            WHERE show_id IS NOT NULL
        )
        AND date < CURRENT_DATE - INTERVAL '30 days'
    '''
