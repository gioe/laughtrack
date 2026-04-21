"""SQL queries for club operations."""


class ClubQueries:
    """SQL queries for club operations."""

    _SCRAPING_SOURCE_JSON = """
        json_build_object(
            'id', ss.id,
            'club_id', ss.club_id,
            'platform', ss.platform,
            'scraper_key', ss.scraper_key,
            'external_id', ss.external_id,
            'source_url', ss.source_url,
            'priority', ss.priority,
            'enabled', ss.enabled,
            'metadata', COALESCE(ss.metadata, '{}'::jsonb)
        )
    """

    _SCRAPING_SOURCES_LATERAL = f"""
        LEFT JOIN LATERAL (
            SELECT COALESCE(
                json_agg(
                    { _SCRAPING_SOURCE_JSON }
                    ORDER BY ss.priority, ss.id
                ) FILTER (WHERE ss.id IS NOT NULL),
                '[]'::json
            ) AS scraping_sources
            FROM scraping_sources ss
            WHERE ss.club_id = c.id
              AND ss.enabled = TRUE
        ) source_list ON TRUE
    """

    _PRIMARY_SOURCE_LATERAL = """
        JOIN LATERAL (
            SELECT
                ss.id,
                ss.platform,
                ss.scraper_key,
                ss.external_id,
                ss.source_url,
                ss.priority,
                ss.enabled,
                COALESCE(ss.metadata, '{}'::jsonb) AS metadata
            FROM scraping_sources ss
            WHERE ss.club_id = c.id
              AND ss.enabled = TRUE
            ORDER BY ss.priority, ss.id
            LIMIT 1
        ) primary_source ON TRUE
    """

    _BASE_CLUB_SELECT = f"""
        SELECT c.*, source_list.scraping_sources
        FROM clubs c
        { _SCRAPING_SOURCES_LATERAL }
        { _PRIMARY_SOURCE_LATERAL }
    """

    GET_ALL_CLUBS = f"""
        { _BASE_CLUB_SELECT }
        WHERE c.visible = TRUE
          AND c.status = 'active'
        ORDER BY c.id
    """

    GET_ALL_CLUBS_JSON = """
        SELECT name, city, state, website FROM clubs ORDER BY name
    """

    GET_CLUB_BY_ID = f"""
        { _BASE_CLUB_SELECT }
        WHERE c.id = %s
          AND c.status = 'active'
    """

    GET_CLUB_BY_IDS = f"""
        { _BASE_CLUB_SELECT }
        WHERE c.id = ANY(%s::int[])
          AND c.status = 'active'
        ORDER BY c.id
    """

    # Backward compatibility alias
    GET_SPECIFIC_CLUBS = GET_CLUB_BY_IDS

    GET_CLUBS_BY_SCRAPER = f"""
        { _BASE_CLUB_SELECT }
        WHERE primary_source.scraper_key = %s
          AND c.status = 'active'
        ORDER BY c.id
    """

    GET_ACTIVE_FESTIVAL_IDS = """
        SELECT DISTINCT c.id
        FROM clubs c
        JOIN shows s ON s.club_id = c.id
        WHERE c.club_type = 'festival'
          AND s.date >= NOW()
          AND s.date <= NOW() + INTERVAL '90 days'
    """

    GET_DISTINCT_SCRAPER_TYPES = """
        SELECT ps.scraper_key AS scraper, COUNT(*) AS club_count
        FROM (
            SELECT DISTINCT ON (ss.club_id)
                ss.club_id,
                ss.scraper_key
            FROM scraping_sources ss
            WHERE ss.enabled = TRUE
            ORDER BY ss.club_id, ss.priority, ss.id
        ) ps
        JOIN clubs c ON c.id = ps.club_id
        WHERE c.status = 'active'
        GROUP BY ps.scraper_key
        ORDER BY ps.scraper_key
    """

    UPSERT_CLUB_BY_EVENTBRITE_VENUE = f"""
        WITH upserted_club AS (
            INSERT INTO clubs (
                name, address, website, visible,
                zip_code, city, state, phone_number, popularity, timezone
            )
            VALUES (%s, %s, '', TRUE, %s, %s, %s, '', 0, NULL)
            ON CONFLICT (name) DO UPDATE SET
                city  = COALESCE(clubs.city,  EXCLUDED.city),
                state = COALESCE(clubs.state, EXCLUDED.state)
            RETURNING id
        ),
        upserted_source AS (
            INSERT INTO scraping_sources (
                club_id, platform, scraper_key, external_id, source_url,
                priority, enabled, metadata
            )
            SELECT
                id,
                'eventbrite',
                'eventbrite',
                %s,
                'https://www.eventbrite.com',
                0,
                TRUE,
                '{{}}'::jsonb
            FROM upserted_club
            ON CONFLICT (club_id, platform, priority) DO UPDATE SET
                scraper_key = EXCLUDED.scraper_key,
                external_id = COALESCE(scraping_sources.external_id, EXCLUDED.external_id),
                source_url  = COALESCE(NULLIF(scraping_sources.source_url, ''), EXCLUDED.source_url),
                enabled     = TRUE
            RETURNING club_id
        )
        SELECT c.*, source_list.scraping_sources
        FROM clubs c
        JOIN upserted_club uc ON uc.id = c.id
        { _SCRAPING_SOURCES_LATERAL }
    """

    UPSERT_CLUB_BY_SEATENGINE_VENUE = f"""
        WITH upserted_club AS (
            INSERT INTO clubs (
                name, address, website, visible,
                zip_code, city, state, phone_number, popularity, timezone
            )
            VALUES (%s, %s, %s, TRUE, %s, %s, %s, '', 0, NULL)
            ON CONFLICT (name) DO UPDATE SET
                city  = COALESCE(clubs.city,  EXCLUDED.city),
                state = COALESCE(clubs.state, EXCLUDED.state)
            RETURNING id
        ),
        upserted_source AS (
            INSERT INTO scraping_sources (
                club_id, platform, scraper_key, external_id, source_url,
                priority, enabled, metadata
            )
            SELECT
                id,
                'seatengine',
                'seatengine',
                %s,
                %s,
                0,
                TRUE,
                '{{}}'::jsonb
            FROM upserted_club
            ON CONFLICT (club_id, platform, priority) DO UPDATE SET
                scraper_key = COALESCE(scraping_sources.scraper_key, EXCLUDED.scraper_key),
                external_id = COALESCE(scraping_sources.external_id, EXCLUDED.external_id),
                source_url  = COALESCE(
                    NULLIF(scraping_sources.source_url, 'https://www.seatengine.com'),
                    EXCLUDED.source_url
                ),
                enabled     = TRUE
            RETURNING club_id
        )
        SELECT c.*, source_list.scraping_sources
        FROM clubs c
        JOIN upserted_club uc ON uc.id = c.id
        { _SCRAPING_SOURCES_LATERAL }
    """

    UPSERT_CLUB_BY_SEATENGINE_V3_VENUE = f"""
        WITH upserted_club AS (
            INSERT INTO clubs (
                name, address, website, visible,
                zip_code, city, state, phone_number, popularity, timezone
            )
            VALUES (%s, %s, %s, TRUE, %s, %s, %s, '', 0, NULL)
            ON CONFLICT (name) DO UPDATE SET
                city  = COALESCE(clubs.city,  EXCLUDED.city),
                state = COALESCE(clubs.state, EXCLUDED.state)
            RETURNING id
        ),
        upserted_source AS (
            INSERT INTO scraping_sources (
                club_id, platform, scraper_key, external_id, source_url,
                priority, enabled, metadata
            )
            SELECT
                id,
                'seatengine_v3',
                'seatengine_v3',
                %s,
                %s,
                0,
                TRUE,
                '{{}}'::jsonb
            FROM upserted_club
            ON CONFLICT (club_id, platform, priority) DO UPDATE SET
                scraper_key = COALESCE(scraping_sources.scraper_key, EXCLUDED.scraper_key),
                external_id = COALESCE(scraping_sources.external_id, EXCLUDED.external_id),
                source_url  = COALESCE(NULLIF(scraping_sources.source_url, ''), EXCLUDED.source_url),
                enabled     = TRUE
            RETURNING club_id
        )
        SELECT c.*, source_list.scraping_sources
        FROM clubs c
        JOIN upserted_club uc ON uc.id = c.id
        { _SCRAPING_SOURCES_LATERAL }
    """

    GET_CLUBS_WITH_NULL_TIMEZONE = f"""
        { _BASE_CLUB_SELECT }
        WHERE primary_source.scraper_key = %s
          AND c.timezone IS NULL
        ORDER BY c.id
    """

    BATCH_UPDATE_CLUB_TIMEZONES = """
        UPDATE clubs AS c
        SET timezone = v.timezone
        FROM (VALUES %s) AS v(id, timezone)
        WHERE c.id = v.id AND c.timezone IS NULL
        RETURNING c.id
    """

    UPSERT_CLUB_BY_TICKETMASTER_VENUE = f"""
        WITH upserted_club AS (
            INSERT INTO clubs (
                name, address, website, visible,
                zip_code, city, state, phone_number, popularity, timezone
            )
            VALUES (%s, %s, '', TRUE, %s, %s, %s, '', 0, %s)
            ON CONFLICT (name) DO UPDATE SET
                timezone = COALESCE(clubs.timezone, EXCLUDED.timezone),
                city     = COALESCE(clubs.city,     EXCLUDED.city),
                state    = COALESCE(clubs.state,    EXCLUDED.state)
            RETURNING id
        ),
        upserted_source AS (
            INSERT INTO scraping_sources (
                club_id, platform, scraper_key, external_id, source_url,
                priority, enabled, metadata
            )
            SELECT
                id,
                'ticketmaster',
                'live_nation',
                %s,
                'https://www.ticketmaster.com',
                0,
                TRUE,
                '{{}}'::jsonb
            FROM upserted_club
            ON CONFLICT (club_id, platform, priority) DO UPDATE SET
                scraper_key = COALESCE(scraping_sources.scraper_key, EXCLUDED.scraper_key),
                external_id = COALESCE(scraping_sources.external_id, EXCLUDED.external_id),
                source_url  = COALESCE(NULLIF(scraping_sources.source_url, ''), EXCLUDED.source_url),
                enabled     = TRUE
            RETURNING club_id
        )
        SELECT c.*, source_list.scraping_sources
        FROM clubs c
        JOIN upserted_club uc ON uc.id = c.id
        { _SCRAPING_SOURCES_LATERAL }
    """

    UPSERT_CLUB_BY_TOUR_DATE_VENUE = f"""
        WITH upserted_club AS (
            INSERT INTO clubs (
                name, address, website, visible,
                zip_code, city, state, phone_number, popularity, timezone
            )
            VALUES (%s, %s, '', TRUE, %s, %s, %s, '', 0, %s)
            ON CONFLICT (name) DO UPDATE SET
                timezone = COALESCE(clubs.timezone, EXCLUDED.timezone),
                city     = COALESCE(clubs.city,     EXCLUDED.city),
                state    = COALESCE(clubs.state,    EXCLUDED.state)
            RETURNING id
        ),
        upserted_source AS (
            INSERT INTO scraping_sources (
                club_id, platform, scraper_key, external_id, source_url,
                priority, enabled, metadata
            )
            SELECT
                id,
                'tour_dates',
                'tour_dates',
                NULL,
                'tour_dates',
                0,
                TRUE,
                '{{}}'::jsonb
            FROM upserted_club
            ON CONFLICT (club_id, platform, priority) DO UPDATE SET
                scraper_key = EXCLUDED.scraper_key,
                source_url  = COALESCE(NULLIF(scraping_sources.source_url, ''), EXCLUDED.source_url),
                enabled     = TRUE
            RETURNING club_id
        )
        SELECT c.*, source_list.scraping_sources
        FROM clubs c
        JOIN upserted_club uc ON uc.id = c.id
        { _SCRAPING_SOURCES_LATERAL }
    """

    # Recomputes total_shows for every club by counting all Show rows per club_id.
    # Clubs with no shows are set to 0 (correlated subquery covers all clubs).
    UPDATE_CLUB_TOTAL_SHOWS = """
        UPDATE clubs
        SET total_shows = (SELECT COUNT(*) FROM shows WHERE shows.club_id = clubs.id)
    """

    GET_ALL_CLUB_IDS = """
        SELECT id FROM clubs WHERE visible = TRUE AND status = 'active' ORDER BY id
    """

    # Computes popularity per club from two signals over the +/-90-day window:
    #   - Activity: count of shows in the past 90 days + next 90 days,
    #     saturated at 60 shows (approx one show every three days on average).
    #   - Quality: booking-weighted average comedian popularity - the LEFT JOIN
    #     fans out one row per (show, comedian) pair, so a comedian booked
    #     multiple times at this club in the window contributes proportionally
    #     more. This intentionally rewards clubs that book popular comedians
    #     repeatedly, not just once. Values are already normalized to 0-1
    #     by update_comedian_popularity.
    # Activity gets 60% weight, quality 40%, mirroring the comedian scorer's
    # performance-over-social split. Clubs with no shows in the window are
    # absent from the result set and keep their existing popularity untouched.
    BATCH_GET_CLUB_POPULARITY = """
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
    """

    BATCH_UPDATE_CLUB_POPULARITY = """
        UPDATE clubs
        SET popularity = v.popularity
        FROM (
            SELECT club_id, popularity
            FROM UNNEST(%s::int[], %s::numeric[]) AS v(club_id, popularity)
        ) v
        WHERE id = v.club_id
    """

    GET_CLUBS_WITH_NULL_CITY_STATE = """
        SELECT * FROM clubs
        WHERE (city IS NULL OR state IS NULL) AND address IS NOT NULL AND address != ''
        ORDER BY id
    """

    BATCH_UPDATE_CLUB_CITY_STATE = """
        UPDATE clubs AS c
        SET city  = COALESCE(c.city,  v.city),
            state = COALESCE(c.state, v.state)
        FROM (VALUES %s) AS v(id, city, state)
        WHERE c.id = v.id AND (c.city IS NULL OR c.state IS NULL)
        RETURNING c.id
    """
