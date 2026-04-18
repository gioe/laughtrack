"""SQL queries for club operations."""


class ClubQueries:
    """SQL queries for club operations."""
    
    GET_ALL_CLUBS = '''
        SELECT * FROM clubs WHERE scraper IS NOT NULL AND visible = True AND status = 'active' ORDER BY id
    '''

    GET_ALL_CLUBS_JSON = '''
        SELECT name, city, state, website FROM clubs ORDER BY name
    '''
    
    GET_CLUB_BY_ID = '''
        SELECT *
        FROM clubs
        WHERE id = %s AND scraper IS NOT NULL AND status = 'active'
    '''

    GET_CLUB_BY_IDS = '''
        SELECT *
        FROM clubs
        WHERE id = ANY(%s::int[]) AND scraper IS NOT NULL AND status = 'active'
        ORDER BY id
    '''
    
    # Backward compatibility alias
    GET_SPECIFIC_CLUBS = GET_CLUB_BY_IDS
    
    GET_CLUBS_BY_SCRAPER = '''
        SELECT *
        FROM clubs
        WHERE scraper = %s AND scraper IS NOT NULL AND status = 'active'
        ORDER BY id
    '''

    GET_ACTIVE_FESTIVAL_IDS = '''
        SELECT DISTINCT c.id
        FROM clubs c
        JOIN shows s ON s.club_id = c.id
        WHERE c.club_type = 'festival'
          AND s.date >= NOW()
          AND s.date <= NOW() + INTERVAL '90 days'
    '''
    
    GET_DISTINCT_SCRAPER_TYPES = '''
        SELECT scraper, COUNT(*) as club_count
        FROM clubs
        WHERE scraper IS NOT NULL AND status = 'active'
        GROUP BY scraper
        ORDER BY scraper
    '''

    UPSERT_CLUB_BY_EVENTBRITE_VENUE = '''
        INSERT INTO clubs (
            name, address, website, scraping_url,
            eventbrite_id, scraper, visible,
            zip_code, city, state, phone_number, popularity, timezone
        )
        VALUES (%s, %s, '', 'www.eventbrite.com', %s, 'eventbrite', true, %s, %s, %s, '', 0, NULL)
        ON CONFLICT (name) DO UPDATE SET
            eventbrite_id = COALESCE(clubs.eventbrite_id, EXCLUDED.eventbrite_id),
            scraper       = COALESCE(clubs.scraper,       EXCLUDED.scraper),
            city          = COALESCE(clubs.city,          EXCLUDED.city),
            state         = COALESCE(clubs.state,         EXCLUDED.state)
        RETURNING *
    '''

    UPSERT_CLUB_BY_SEATENGINE_VENUE = '''
        INSERT INTO clubs (
            name, address, website, scraping_url,
            seatengine_id, scraper, visible,
            zip_code, city, state, phone_number, popularity, timezone
        )
        VALUES (%s, %s, %s, %s, %s, 'seatengine', true, %s, %s, %s, '', 0, NULL)
        ON CONFLICT (name) DO UPDATE SET
            seatengine_id = COALESCE(clubs.seatengine_id, EXCLUDED.seatengine_id),
            scraper       = COALESCE(clubs.scraper,       EXCLUDED.scraper),
            -- Migrate the exact legacy placeholder inserted before this fix;
            -- 'www.seatengine.com' is the only variant ever written by this query.
            scraping_url  = COALESCE(NULLIF(clubs.scraping_url, 'www.seatengine.com'), EXCLUDED.scraping_url),
            city          = COALESCE(clubs.city,          EXCLUDED.city),
            state         = COALESCE(clubs.state,         EXCLUDED.state)
        RETURNING *
    '''

    UPSERT_CLUB_BY_SEATENGINE_V3_VENUE = '''
        INSERT INTO clubs (
            name, address, website, scraping_url,
            seatengine_id, scraper, visible,
            zip_code, city, state, phone_number, popularity, timezone
        )
        VALUES (%s, %s, %s, %s, %s, 'seatengine_v3', true, %s, %s, %s, '', 0, NULL)
        ON CONFLICT (name) DO UPDATE SET
            seatengine_id = COALESCE(clubs.seatengine_id, EXCLUDED.seatengine_id),
            scraper       = COALESCE(clubs.scraper,       EXCLUDED.scraper),
            scraping_url  = COALESCE(NULLIF(clubs.scraping_url, ''), EXCLUDED.scraping_url),
            city          = COALESCE(clubs.city,          EXCLUDED.city),
            state         = COALESCE(clubs.state,         EXCLUDED.state)
        RETURNING *
    '''

    GET_CLUBS_WITH_NULL_TIMEZONE = '''
        SELECT * FROM clubs
        WHERE scraper = %s AND timezone IS NULL
        ORDER BY id
    '''

    BATCH_UPDATE_CLUB_TIMEZONES = '''
        UPDATE clubs AS c
        SET timezone = v.timezone
        FROM (VALUES %s) AS v(id, timezone)
        WHERE c.id = v.id AND c.timezone IS NULL
        RETURNING c.id
    '''

    UPSERT_CLUB_BY_TICKETMASTER_VENUE = '''
        INSERT INTO clubs (
            name, address, website, scraping_url,
            ticketmaster_id, scraper, visible,
            zip_code, city, state, phone_number, popularity, timezone
        )
        VALUES (%s, %s, '', 'www.ticketmaster.com', %s, 'live_nation', true, %s, %s, %s, '', 0, %s)
        ON CONFLICT (name) DO UPDATE SET
            ticketmaster_id = COALESCE(clubs.ticketmaster_id, EXCLUDED.ticketmaster_id),
            scraper         = COALESCE(clubs.scraper,         EXCLUDED.scraper),
            timezone        = COALESCE(clubs.timezone,        EXCLUDED.timezone),
            city            = COALESCE(clubs.city,            EXCLUDED.city),
            state           = COALESCE(clubs.state,           EXCLUDED.state)
        RETURNING *
    '''

    UPSERT_CLUB_BY_TOUR_DATE_VENUE = '''
        INSERT INTO clubs (
            name, address, website, scraping_url,
            scraper, visible,
            zip_code, city, state, phone_number, popularity, timezone
        )
        VALUES (%s, %s, '', 'tour_dates', 'tour_dates', true, %s, %s, %s, '', 0, %s)
        ON CONFLICT (name) DO UPDATE SET
            scraper   = COALESCE(clubs.scraper,   EXCLUDED.scraper),
            timezone  = COALESCE(clubs.timezone,  EXCLUDED.timezone),
            city      = COALESCE(clubs.city,      EXCLUDED.city),
            state     = COALESCE(clubs.state,     EXCLUDED.state)
        RETURNING *
    '''

    # Recomputes total_shows for every club by counting all Show rows per club_id.
    # Clubs with no shows are set to 0 (correlated subquery covers all clubs).
    UPDATE_CLUB_TOTAL_SHOWS = '''
        UPDATE clubs
        SET total_shows = (SELECT COUNT(*) FROM shows WHERE shows.club_id = clubs.id)
    '''

    GET_ALL_CLUB_IDS = '''
        SELECT id FROM clubs WHERE visible = True AND status = 'active' ORDER BY id
    '''

    # Computes popularity per club from two signals over the ±90-day window:
    #   - Activity: count of shows in the past 90 days + next 90 days,
    #     saturated at 60 shows (≈ one show every three days on average).
    #   - Quality: average popularity of comedians in the lineups of those
    #     same shows (already normalized to 0–1 by update_comedian_popularity).
    # Activity gets 60% weight, quality 40%, mirroring the comedian scorer's
    # performance-over-social split.  Clubs with no shows in the window are
    # absent from the result set and keep their existing popularity untouched.
    BATCH_GET_CLUB_POPULARITY = '''
        WITH club_metrics AS (
            SELECT
                s.club_id,
                COUNT(DISTINCT CASE
                    WHEN s.date >= CURRENT_DATE
                     AND s.date <= CURRENT_DATE + INTERVAL '90 days'
                    THEN s.id END) AS upcoming_shows,
                COUNT(DISTINCT CASE
                    WHEN s.date >= CURRENT_DATE - INTERVAL '90 days'
                     AND s.date <  CURRENT_DATE
                    THEN s.id END) AS recent_shows,
                AVG(c.popularity) FILTER (
                    WHERE s.date >= CURRENT_DATE - INTERVAL '90 days'
                      AND s.date <= CURRENT_DATE + INTERVAL '90 days'
                ) AS avg_comedian_popularity
            FROM shows s
            LEFT JOIN lineup_items li ON li.show_id = s.id
            LEFT JOIN comedians c ON c.uuid = li.comedian_id
            WHERE s.club_id = ANY(%s::int[])
              AND s.date >= CURRENT_DATE - INTERVAL '90 days'
              AND s.date <= CURRENT_DATE + INTERVAL '90 days'
            GROUP BY s.club_id
        )
        SELECT
            club_id,
            LEAST(
                LEAST((upcoming_shows + recent_shows)::float / 60.0, 1.0) * 0.6 +
                COALESCE(avg_comedian_popularity, 0) * 0.4,
                1.0
            ) AS popularity
        FROM club_metrics
        WHERE upcoming_shows + recent_shows > 0
    '''

    BATCH_UPDATE_CLUB_POPULARITY = '''
        UPDATE clubs
        SET popularity = v.popularity
        FROM (
            SELECT club_id, popularity
            FROM UNNEST(%s::int[], %s::numeric[]) AS v(club_id, popularity)
        ) v
        WHERE id = v.club_id
    '''

    GET_CLUBS_WITH_NULL_CITY_STATE = '''
        SELECT * FROM clubs
        WHERE (city IS NULL OR state IS NULL) AND address IS NOT NULL AND address != ''
        ORDER BY id
    '''

    BATCH_UPDATE_CLUB_CITY_STATE = '''
        UPDATE clubs AS c
        SET city  = COALESCE(c.city,  v.city),
            state = COALESCE(c.state, v.state)
        FROM (VALUES %s) AS v(id, city, state)
        WHERE c.id = v.id AND (c.city IS NULL OR c.state IS NULL)
        RETURNING c.id
    '''
