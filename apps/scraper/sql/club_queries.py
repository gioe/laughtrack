"""SQL queries for club operations."""


class ClubQueries:
    """SQL queries for club operations."""

    _SCRAPING_SOURCE_JSON = """
        json_build_object(
            'id', ss.id,
            'club_id', ss.club_id,
            'platform', ss.platform,
            'scraper_key', COALESCE(NULLIF(ss.scraper_key, ''), csd.scraper_key, ss.scraper_key),
            'seatengine_id', ss.seatengine_id,
            'eventbrite_id', ss.eventbrite_id,
            'ticketmaster_id', ss.ticketmaster_id,
            'wix_event_id', ss.wix_event_id,
            'ovationtix_id', ss.ovationtix_id,
            'squadup_id', ss.squadup_id,
            'seatengine_v3_id', ss.seatengine_v3_id,
            'source_url', ss.source_url,
            'priority', ss.priority,
            'enabled', ss.enabled,
            'metadata', COALESCE(csd.metadata, '{}'::jsonb) || COALESCE(ss.metadata, '{}'::jsonb),
            'chain_scraping_default_id', csd.id,
            'chain_id', csd.chain_id
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
            LEFT JOIN chain_scraping_defaults csd
              ON csd.chain_id = c.chain_id
             AND csd.platform = ss.platform
             AND csd.priority = ss.priority
             AND NULLIF(ss.scraper_key, '') IS NULL
             AND csd.enabled = TRUE
            WHERE ss.club_id = c.id
              AND ss.enabled = TRUE
        ) source_list ON TRUE
    """

    _PRIMARY_SOURCE_LATERAL = """
        JOIN LATERAL (
            SELECT
                ss.id,
                ss.platform,
                COALESCE(NULLIF(ss.scraper_key, ''), csd.scraper_key, ss.scraper_key) AS scraper_key,
                ss.seatengine_id,
                ss.eventbrite_id,
                ss.ticketmaster_id,
                ss.wix_event_id,
                ss.ovationtix_id,
                ss.squadup_id,
                ss.seatengine_v3_id,
                ss.source_url,
                ss.priority,
                ss.enabled,
                COALESCE(csd.metadata, '{}'::jsonb) || COALESCE(ss.metadata, '{}'::jsonb) AS metadata,
                csd.id AS chain_scraping_default_id,
                csd.chain_id
            FROM scraping_sources ss
            LEFT JOIN chain_scraping_defaults csd
              ON csd.chain_id = c.chain_id
             AND csd.platform = ss.platform
             AND csd.priority = ss.priority
             AND NULLIF(ss.scraper_key, '') IS NULL
             AND csd.enabled = TRUE
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
                COALESCE(NULLIF(ss.scraper_key, ''), csd.scraper_key, ss.scraper_key) AS scraper_key
            FROM scraping_sources ss
            JOIN clubs c ON c.id = ss.club_id
            LEFT JOIN chain_scraping_defaults csd
              ON csd.chain_id = c.chain_id
             AND csd.platform = ss.platform
             AND csd.priority = ss.priority
             AND NULLIF(ss.scraper_key, '') IS NULL
             AND csd.enabled = TRUE
            WHERE ss.enabled = TRUE
            ORDER BY ss.club_id, ss.priority, ss.id
        ) ps
        JOIN clubs c ON c.id = ps.club_id
        WHERE c.status = 'active'
        GROUP BY ps.scraper_key
        ORDER BY ps.scraper_key
    """

    # Pre-upsert lookup for EventbriteScraper organizer-mode fuzzy-name
    # reconciliation (TASK-1926). Returns every clubs row that shares the
    # given (city, state) so ClubHandler can fold near-identical name
    # spellings (e.g. 'Big Couch' / 'Big Couch New Orleans') into one row
    # before UPSERT_CLUB_BY_EVENTBRITE_VENUE's ON CONFLICT (name) splits
    # them. scraping_sources is projected as '[]' because the caller only
    # needs id/name/city/state/timezone for routing; full source lists go
    # through GET_CLUB_BY_ID.
    #
    # The visible/status filter mirrors the dominant pattern in every other
    # club-fetch query in this file. Without it the fuzzy-match path could
    # route fresh organizer events to a hidden vestigial row (e.g. one of the
    # 8 clubs hidden in TASK-1918), which would silently ingest events that
    # never surface to users. ORDER BY c.id makes the candidate selection
    # deterministic when two same-(city, state) rows happen to normalize to
    # the same core form — non-deterministic ordering across nightly runs
    # would let the same fuzzy hit flip-flop between IDs.
    GET_CLUBS_BY_LOCATION = """
        SELECT
            c.*,
            '[]'::json AS scraping_sources,
            COALESCE(alias_list.aliases, '[]'::json) AS aliases
        FROM clubs c
        LEFT JOIN LATERAL (
            SELECT json_agg(
                json_build_object(
                    'alias_name', ca.alias_name,
                    'normalized_alias_name', ca.normalized_alias_name,
                    'normalized_city', ca.normalized_city,
                    'normalized_state', ca.normalized_state
                )
                ORDER BY ca.id
            ) AS aliases
            FROM club_aliases ca
            WHERE ca.club_id = c.id
              AND ca.verified = TRUE
        ) alias_list ON TRUE
        WHERE LOWER(TRIM(c.city)) = LOWER(TRIM(%s))
          AND LOWER(TRIM(c.state)) = LOWER(TRIM(%s))
          AND c.visible = TRUE
          AND c.status = 'active'
        ORDER BY c.id
    """

    # NOTE: the final SELECT projects from the upserted_club CTE rather than
    # JOINing back to the clubs table. Data-modifying CTEs share a single
    # snapshot with the rest of the statement, so a JOIN against `clubs`
    # cannot see a freshly INSERTed row — for first-time per-venue upserts
    # in EventbriteScraper organizer-mode, the JOIN returned 0 rows and
    # ClubHandler.upsert_for_eventbrite_venue treated that as a failure
    # (TASK-1927: 90 'Big Couch' shows silently dropped on 2026-05-05).
    # scraping_sources is left as '[]' because organizer-mode callers only
    # read .id and .timezone from the returned Club; existing-row reads of
    # the full source list go through GET_CLUB_BY_ID, not this upsert.
    UPSERT_CLUB_BY_EVENTBRITE_VENUE = """
        WITH upserted_club AS (
            INSERT INTO clubs (
                name, address, website, visible,
                zip_code, city, state, phone_number, popularity, timezone
            )
            VALUES (%s, %s, '', TRUE, %s, %s, %s, '', 0, NULL)
            ON CONFLICT (name) DO UPDATE SET
                city  = COALESCE(clubs.city,  EXCLUDED.city),
                state = COALESCE(clubs.state, EXCLUDED.state)
            RETURNING *
        ),
        upserted_source AS (
            INSERT INTO scraping_sources (
                club_id, platform, scraper_key, eventbrite_id, source_url,
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
                '{}'::jsonb
            FROM upserted_club
            ON CONFLICT (club_id, platform, priority) DO UPDATE SET
                scraper_key = EXCLUDED.scraper_key,
                eventbrite_id = COALESCE(scraping_sources.eventbrite_id, EXCLUDED.eventbrite_id),
                source_url  = COALESCE(NULLIF(scraping_sources.source_url, ''), EXCLUDED.source_url),
                -- Preserve the existing enabled flag when the row carries any
                -- task_<id>_disposition stamp; otherwise re-enable. Eventbrite
                -- organizer-mode re-emits every distinct per-venue
                -- (name, city, state) on every nightly run, so without this
                -- carve-out any dispositional disable on a venue that still
                -- appears in any organizer's feed reverts within 24h
                -- (TASK-1968 / TASK-1978).
                enabled     = CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM jsonb_object_keys(COALESCE(scraping_sources.metadata, '{}'::jsonb)) k
                        WHERE k LIKE 'task_%_disposition'
                    )
                    THEN scraping_sources.enabled
                    ELSE TRUE
                END
            RETURNING club_id
        )
        SELECT uc.*, '[]'::json AS scraping_sources
        FROM upserted_club uc
        WHERE EXISTS (SELECT 1 FROM upserted_source)
    """

    # See UPSERT_CLUB_BY_EVENTBRITE_VENUE comment above for why the final
    # SELECT projects from the CTE rather than JOINing the clubs table.
    UPSERT_CLUB_BY_SEATENGINE_VENUE = """
        WITH upserted_club AS (
            INSERT INTO clubs (
                name, address, website, visible,
                zip_code, city, state, phone_number, popularity, timezone
            )
            VALUES (%s, %s, %s, TRUE, %s, %s, %s, '', 0, NULL)
            ON CONFLICT (name) DO UPDATE SET
                city  = COALESCE(clubs.city,  EXCLUDED.city),
                state = COALESCE(clubs.state, EXCLUDED.state)
            RETURNING *
        ),
        upserted_source AS (
            INSERT INTO scraping_sources (
                club_id, platform, scraper_key, seatengine_id, source_url,
                priority, enabled, metadata
            )
            SELECT
                id,
                'seatengine',
                'seatengine',
                %s::integer,
                %s,
                0,
                TRUE,
                '{}'::jsonb
            FROM upserted_club
            ON CONFLICT (club_id, platform, priority) DO UPDATE SET
                scraper_key = COALESCE(scraping_sources.scraper_key, EXCLUDED.scraper_key),
                seatengine_id = COALESCE(scraping_sources.seatengine_id, EXCLUDED.seatengine_id),
                source_url  = COALESCE(
                    NULLIF(scraping_sources.source_url, 'https://www.seatengine.com'),
                    EXCLUDED.source_url
                ),
                -- Preserve the existing enabled flag when the row carries any
                -- task_<id>_disposition stamp; otherwise re-enable. seatengine_national
                -- sweeps v1 venue ids 1..N each nightly and would otherwise revert
                -- every dispositional disable on a still-listed venue (TASK-1968).
                enabled     = CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM jsonb_object_keys(COALESCE(scraping_sources.metadata, '{}'::jsonb)) k
                        WHERE k LIKE 'task_%_disposition'
                    )
                    THEN scraping_sources.enabled
                    ELSE TRUE
                END
            RETURNING club_id
        )
        SELECT uc.*, '[]'::json AS scraping_sources
        FROM upserted_club uc
        WHERE EXISTS (SELECT 1 FROM upserted_source)
    """

    # See UPSERT_CLUB_BY_EVENTBRITE_VENUE comment above for why the final
    # SELECT projects from the CTE rather than JOINing the clubs table.
    UPSERT_CLUB_BY_SEATENGINE_V3_VENUE = """
        WITH upserted_club AS (
            INSERT INTO clubs (
                name, address, website, visible,
                zip_code, city, state, phone_number, popularity, timezone
            )
            VALUES (%s, %s, %s, TRUE, %s, %s, %s, '', 0, NULL)
            ON CONFLICT (name) DO UPDATE SET
                city  = COALESCE(clubs.city,  EXCLUDED.city),
                state = COALESCE(clubs.state, EXCLUDED.state)
            RETURNING *
        ),
        upserted_source AS (
            INSERT INTO scraping_sources (
                club_id, platform, scraper_key, seatengine_v3_id, source_url,
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
                '{}'::jsonb
            FROM upserted_club
            ON CONFLICT (club_id, platform, priority) DO UPDATE SET
                scraper_key = COALESCE(scraping_sources.scraper_key, EXCLUDED.scraper_key),
                seatengine_v3_id = COALESCE(scraping_sources.seatengine_v3_id, EXCLUDED.seatengine_v3_id),
                source_url  = COALESCE(NULLIF(scraping_sources.source_url, ''), EXCLUDED.source_url),
                -- See UPSERT_CLUB_BY_SEATENGINE_VENUE for the disposition carve-out
                -- rationale (TASK-1968); same pattern, same risk on the v3 directory sweep.
                enabled     = CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM jsonb_object_keys(COALESCE(scraping_sources.metadata, '{}'::jsonb)) k
                        WHERE k LIKE 'task_%_disposition'
                    )
                    THEN scraping_sources.enabled
                    ELSE TRUE
                END
            RETURNING club_id
        )
        SELECT uc.*, '[]'::json AS scraping_sources
        FROM upserted_club uc
        WHERE EXISTS (SELECT 1 FROM upserted_source)
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

    # See UPSERT_CLUB_BY_EVENTBRITE_VENUE comment above for why the final
    # SELECT projects from the CTE rather than JOINing the clubs table.
    UPSERT_CLUB_BY_TICKETMASTER_VENUE = """
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
            RETURNING *
        ),
        upserted_source AS (
            INSERT INTO scraping_sources (
                club_id, platform, scraper_key, ticketmaster_id, source_url,
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
                '{}'::jsonb
            FROM upserted_club
            ON CONFLICT (club_id, platform, priority) DO UPDATE SET
                scraper_key = COALESCE(scraping_sources.scraper_key, EXCLUDED.scraper_key),
                ticketmaster_id = COALESCE(scraping_sources.ticketmaster_id, EXCLUDED.ticketmaster_id),
                source_url  = COALESCE(NULLIF(scraping_sources.source_url, ''), EXCLUDED.source_url),
                -- Preserve the existing enabled flag when the row carries any
                -- task_<id>_disposition stamp; otherwise re-enable.
                -- ticketmaster_national paginates the TM Discovery API for US
                -- Comedy events each nightly and upserts every venue surfaced,
                -- so without this carve-out any dispositional disable on a
                -- still-listed TM venue reverts within 24h
                -- (TASK-1968 / TASK-1978).
                enabled     = CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM jsonb_object_keys(COALESCE(scraping_sources.metadata, '{}'::jsonb)) k
                        WHERE k LIKE 'task_%_disposition'
                    )
                    THEN scraping_sources.enabled
                    ELSE TRUE
                END
            RETURNING club_id
        )
        SELECT uc.*, '[]'::json AS scraping_sources
        FROM upserted_club uc
        WHERE EXISTS (SELECT 1 FROM upserted_source)
    """

    # See UPSERT_CLUB_BY_EVENTBRITE_VENUE comment above for why the final
    # SELECT projects from the CTE rather than JOINing the clubs table.
    UPSERT_CLUB_BY_TOUR_DATE_VENUE = """
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
            RETURNING *
        ),
        upserted_source AS (
            INSERT INTO scraping_sources (
                club_id, platform, scraper_key, source_url,
                priority, enabled, metadata
            )
            SELECT
                id,
                'tour_dates',
                'tour_dates',
                'tour_dates',
                0,
                TRUE,
                %s::jsonb
            FROM upserted_club
            ON CONFLICT (club_id, platform, priority) DO UPDATE SET
                scraper_key = EXCLUDED.scraper_key,
                source_url  = COALESCE(NULLIF(scraping_sources.source_url, ''), EXCLUDED.source_url),
                metadata    = COALESCE(scraping_sources.metadata, '{}'::jsonb)
                    || EXCLUDED.metadata
                    || jsonb_build_object(
                        'first_seen_at',
                        COALESCE(
                            scraping_sources.metadata ->> 'first_seen_at',
                            EXCLUDED.metadata ->> 'first_seen_at'
                        ),
                        'last_seen_at',
                        EXCLUDED.metadata ->> 'last_seen_at',
                        'reference_count',
                        (
                            COALESCE((scraping_sources.metadata ->> 'reference_count')::integer, 0)
                            + COALESCE((EXCLUDED.metadata ->> 'reference_count')::integer, 1)
                        )
                    ),
                -- Preserve the existing enabled flag when the row carries any
                -- task_<id>_disposition stamp; otherwise re-enable. tour_dates
                -- and comedian_websites iterate the full comedian universe
                -- nightly and re-discover venues per artist, so without this
                -- carve-out any dispositional disable on a venue any tracked
                -- comedian still books reverts within 24h
                -- (TASK-1968 / TASK-1978).
                enabled     = CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM jsonb_object_keys(COALESCE(scraping_sources.metadata, '{}'::jsonb)) k
                        WHERE k LIKE 'task_%_disposition'
                    )
                    THEN scraping_sources.enabled
                    ELSE TRUE
                END
            RETURNING club_id
        )
        SELECT uc.*, '[]'::json AS scraping_sources
        FROM upserted_club uc
        WHERE EXISTS (SELECT 1 FROM upserted_source)
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
