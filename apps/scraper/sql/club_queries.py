"""SQL queries for club operations."""


class ClubQueries:
    """SQL queries for club operations."""

    _SCRAPING_SOURCE_JSON = """
        json_build_object(
            'id', ss.id,
            'club_id', ss.club_id,
            'source_target_id', ss.source_target_id,
            'source_target_name', st.name,
            'source_target_slug', st.slug,
            'source_target_type', st.target_type,
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
            LEFT JOIN source_targets st ON st.id = ss.source_target_id
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

    _CLUB_SELECT_WITH_OPTIONAL_SOURCES = f"""
        SELECT c.*, source_list.scraping_sources
        FROM clubs c
        { _SCRAPING_SOURCES_LATERAL }
    """

    GET_ALL_CLUBS = f"""
        { _BASE_CLUB_SELECT }
        WHERE c.visible = TRUE
          AND c.status = 'active'
        ORDER BY c.id
    """

    GET_ALL_SOURCE_TARGETS = """
        SELECT
            st.id,
            st.name,
            ''::text AS address,
            COALESCE(st.source_url, '') AS website,
            0 AS popularity,
            ''::text AS zip_code,
            ''::text AS phone_number,
            st.visible,
            'America/New_York'::text AS timezone,
            NULL::text AS city,
            NULL::text AS state,
            st.status,
            'source_target'::text AS club_type,
            NULL::integer AS chain_id,
            source_list.scraping_sources
        FROM source_targets st
        JOIN LATERAL (
            SELECT COALESCE(
                json_agg(
                    json_build_object(
                        'id', ss.id,
                        'club_id', ss.club_id,
                        'source_target_id', ss.source_target_id,
                        'source_target_name', st.name,
                        'source_target_slug', st.slug,
                        'source_target_type', st.target_type,
                        'platform', ss.platform,
                        'scraper_key', ss.scraper_key,
                        'seatengine_id', ss.seatengine_id,
                        'eventbrite_id', ss.eventbrite_id,
                        'ticketmaster_id', ss.ticketmaster_id,
                        'wix_event_id', ss.wix_event_id,
                        'ovationtix_id', ss.ovationtix_id,
                        'squadup_id', ss.squadup_id,
                        'seatengine_v3_id', ss.seatengine_v3_id,
                        'source_url', COALESCE(ss.source_url, st.source_url),
                        'priority', ss.priority,
                        'enabled', ss.enabled,
                        'metadata', COALESCE(st.metadata, '{}'::jsonb) || COALESCE(ss.metadata, '{}'::jsonb),
                        'chain_scraping_default_id', NULL,
                        'chain_id', NULL
                    )
                    ORDER BY ss.priority, ss.id
                ) FILTER (WHERE ss.id IS NOT NULL),
                '[]'::json
            ) AS scraping_sources
            FROM scraping_sources ss
            WHERE ss.source_target_id = st.id
              AND ss.club_id IS NULL
              AND ss.enabled = TRUE
        ) source_list ON TRUE
        WHERE st.status = 'active'
          AND st.enabled = TRUE
        ORDER BY st.id
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

    GET_CLUB_BY_EVENTBRITE_VENUE_ID = f"""
        { _BASE_CLUB_SELECT }
        JOIN scraping_sources matched_source
          ON matched_source.club_id = c.id
         AND matched_source.platform = 'eventbrite'
         AND matched_source.enabled = TRUE
         AND matched_source.eventbrite_id = %s
        WHERE c.visible = TRUE
          AND c.status = 'active'
        ORDER BY c.id
        LIMIT 1
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
    # Params (positional): (candidate_name, candidate_city, candidate_state,
    # location_city, location_state). The alias_matches_candidate flag resolves
    # the alias dedup key entirely in SQL via lt_normalize_alias_key — the same
    # function the club_aliases_set_normalized trigger uses to populate the
    # stored columns — so the scraper never re-implements normalization in
    # Python and the writer/reader contract cannot drift (TASK-3462). The
    # candidate (name, city, state) equal the (location_city, location_state)
    # filter values for the same venue, so callers pass city/state twice.
    GET_CLUBS_BY_LOCATION = """
        SELECT
            c.*,
            '[]'::json AS scraping_sources,
            COALESCE(alias_list.aliases, '[]'::json) AS aliases,
            EXISTS (
                SELECT 1
                FROM club_aliases ca_match
                WHERE ca_match.club_id = c.id
                  AND ca_match.verified = TRUE
                  AND ca_match.normalized_alias_name = lt_normalize_alias_key(%s)
                  AND ca_match.normalized_city = lt_normalize_alias_key(%s)
                  AND ca_match.normalized_state = lower(%s)
            ) AS alias_matches_candidate
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
            WHERE (
                clubs.city IS NULL OR EXCLUDED.city IS NULL
                OR LOWER(TRIM(clubs.city)) = LOWER(TRIM(EXCLUDED.city))
            )
            AND (
                clubs.state IS NULL OR EXCLUDED.state IS NULL
                OR LOWER(TRIM(clubs.state)) = LOWER(TRIM(EXCLUDED.state))
            )
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
                        WHERE k LIKE 'task_%%_disposition'
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
                        WHERE k LIKE 'task_%%_disposition'
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
                        WHERE k LIKE 'task_%%_disposition'
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

    GET_ALL_VISIBLE_CLUBS_WITH_NULL_TIMEZONE = f"""
        { _BASE_CLUB_SELECT }
        WHERE c.visible = TRUE
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
        WITH input_venue AS (
            SELECT
                %s::text AS ticketmaster_id,
                %s::text AS name,
                %s::text AS address,
                %s::text AS zip_code,
                %s::text AS city,
                %s::text AS state,
                %s::text AS timezone
        ),
        existing_ticketmaster_club AS (
            SELECT c.*
            FROM clubs c
            JOIN scraping_sources s ON s.club_id = c.id
            JOIN input_venue iv ON s.ticketmaster_id = iv.ticketmaster_id
            WHERE s.platform = 'ticketmaster'
            ORDER BY s.enabled DESC, s.priority ASC, s.id ASC
            LIMIT 1
        ),
        updated_ticketmaster_club AS (
            UPDATE clubs c
            SET
                address  = COALESCE(NULLIF(c.address, ''), iv.address),
                zip_code = COALESCE(NULLIF(c.zip_code, ''), iv.zip_code),
                timezone = COALESCE(c.timezone, iv.timezone),
                city     = COALESCE(c.city,     iv.city),
                state    = COALESCE(c.state,    iv.state)
            FROM input_venue iv
            WHERE c.id IN (SELECT id FROM existing_ticketmaster_club)
            RETURNING c.*
        ),
        inserted_or_name_matched_club AS (
            INSERT INTO clubs (
                name, address, website, visible,
                zip_code, city, state, phone_number, popularity, timezone
            )
            SELECT
                iv.name, iv.address, '', TRUE,
                iv.zip_code, iv.city, iv.state, '', 0, iv.timezone
            FROM input_venue iv
            WHERE NOT EXISTS (SELECT 1 FROM updated_ticketmaster_club)
            ON CONFLICT (name) DO UPDATE SET
                timezone = COALESCE(clubs.timezone, EXCLUDED.timezone),
                city     = COALESCE(clubs.city,     EXCLUDED.city),
                state    = COALESCE(clubs.state,    EXCLUDED.state)
            RETURNING *
        ),
        resolved_club AS (
            SELECT * FROM updated_ticketmaster_club
            UNION ALL
            SELECT * FROM inserted_or_name_matched_club
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
                iv.ticketmaster_id,
                'https://www.ticketmaster.com',
                0,
                TRUE,
                '{}'::jsonb
            FROM resolved_club
            CROSS JOIN input_venue iv
            -- Skip the source insert when an *enabled* source already occupies
            -- one of scraping_sources' other partial unique indexes. Without
            -- this, an already-configured venue (overlap with a venue-specific
            -- TM scraper by ticketmaster_id, or a name-collision with an
            -- existing managed club that already has an enabled priority-0
            -- source) violates a constraint NOT covered by the ON CONFLICT
            -- target below, aborting the whole statement so the club is never
            -- returned and the venue + its shows are dropped. The
            -- disabled-source re-enable path still flows through the
            -- ON CONFLICT (club_id, platform, priority) carve-out.
            WHERE NOT EXISTS (   -- scraping_sources_ticketmaster_id_unique (WHERE enabled)
                SELECT 1 FROM scraping_sources s2
                WHERE s2.platform = 'ticketmaster'
                  AND s2.enabled
                  AND s2.ticketmaster_id = iv.ticketmaster_id
            )
            AND NOT EXISTS (     -- scraping_sources_club_priority_enabled_unique (WHERE enabled)
                SELECT 1 FROM scraping_sources s3
                WHERE s3.club_id = resolved_club.id
                  AND s3.priority = 0
                  AND s3.enabled
            )
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
                        WHERE k LIKE 'task_%%_disposition'
                    )
                    THEN scraping_sources.enabled
                    ELSE TRUE
                END
            RETURNING club_id
        )
        -- Return the club unconditionally. Even when the source insert is
        -- skipped above (venue already configured / enabled elsewhere), the
        -- club row exists and must be returned so the caller can attach shows.
        -- upserted_source is a data-modifying CTE, so it still executes even
        -- though the final query no longer references it.
        SELECT rc.*, '[]'::json AS scraping_sources
        FROM resolved_club rc
    """

    GET_CLUBS_BY_NORMALIZED_STREET_ADDRESS = f"""
        {_CLUB_SELECT_WITH_OPTIONAL_SOURCES}
        WHERE c.visible = TRUE
          AND NULLIF(regexp_replace(lower(split_part(COALESCE(c.address, ''), ',', 1)), '[^a-z0-9]', '', 'g'), '') =
              NULLIF(regexp_replace(lower(%s), '[^a-z0-9]', '', 'g'), '')
          AND (%s::text IS NULL OR lower(trim(COALESCE(c.city, ''))) = lower(trim(%s::text)))
          AND (%s::text IS NULL OR lower(trim(COALESCE(c.state, ''))) = lower(trim(%s::text)))
        ORDER BY c.id
    """

    UPSERT_TICKETMASTER_SOURCE_FOR_CLUB = f"""
        WITH input_source AS (
            SELECT
                %s::int AS club_id,
                %s::text AS ticketmaster_id
        ),
        upserted_source AS (
            INSERT INTO scraping_sources (
                club_id, platform, scraper_key, ticketmaster_id, source_url,
                priority, enabled, metadata
            )
            SELECT
                club_id,
                'ticketmaster',
                'live_nation',
                ticketmaster_id,
                'https://www.ticketmaster.com',
                1,
                TRUE,
                '{{}}'::jsonb
            FROM input_source
            WHERE NOT EXISTS (
                SELECT 1
                FROM scraping_sources s
                WHERE s.platform = 'ticketmaster'
                  AND s.enabled
                  AND s.ticketmaster_id = input_source.ticketmaster_id
            )
            ON CONFLICT (club_id, platform, priority) DO UPDATE SET
                scraper_key = COALESCE(scraping_sources.scraper_key, EXCLUDED.scraper_key),
                ticketmaster_id = COALESCE(scraping_sources.ticketmaster_id, EXCLUDED.ticketmaster_id),
                source_url = COALESCE(NULLIF(scraping_sources.source_url, ''), EXCLUDED.source_url),
                enabled = CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM jsonb_object_keys(COALESCE(scraping_sources.metadata, '{{}}'::jsonb)) k
                        WHERE k LIKE 'task_%%_disposition'
                    )
                    THEN scraping_sources.enabled
                    ELSE TRUE
                END
            RETURNING club_id
        )
        {_CLUB_SELECT_WITH_OPTIONAL_SOURCES}
        JOIN input_source i ON i.club_id = c.id
    """

    # Discovery-only venue upsert: inserts/updates the clubs row but does
    # NOT register a scraping_sources entry. Used by callers (comedian
    # websites, tour-page discovery scripts) that surface venues as a
    # side effect without committing to scrape from any specific platform.
    # Returning shape mirrors the *_VENUE upserts (clubs.* plus an empty
    # scraping_sources array) so ``Club.from_db_row`` can consume it.
    UPSERT_DISCOVERED_VENUE = """
        INSERT INTO clubs (
            name, address, website, visible,
            zip_code, city, state, phone_number, popularity, timezone, club_type
        )
        VALUES (%s, %s, %s, TRUE, %s, %s, %s, '', 0, %s, %s)
        ON CONFLICT (name) DO UPDATE SET
            website  = COALESCE(NULLIF(clubs.website, ''), EXCLUDED.website),
            timezone = COALESCE(clubs.timezone, EXCLUDED.timezone),
            city     = COALESCE(clubs.city,     EXCLUDED.city),
            state    = COALESCE(clubs.state,    EXCLUDED.state),
            club_type = CASE
                WHEN clubs.club_type = 'club' AND EXCLUDED.club_type <> 'club'
                THEN EXCLUDED.club_type
                ELSE clubs.club_type
            END
        RETURNING *, '[]'::json AS scraping_sources
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

    # Recent ticket-purchase click counts per club. All clicks count, including
    # clicks without confirmed purchases: this is an intent signal until the app
    # has conversion tracking. The 30-day window keeps the demand signal fresh
    # relative to the +/-90-day supply/quality window below.
    BATCH_GET_CLUB_CLICK_DEMAND = """
        SELECT
            club_id,
            COUNT(*) AS click_count,
            LEAST(COUNT(*)::float / 20.0, 1.0) AS click_demand_rate
        FROM ticket_purchase_click_events
        WHERE club_id = ANY(%s::int[])
          AND created_at >= NOW() - INTERVAL '30 days'
        GROUP BY club_id
    """

    # Computes popularity per club from three signals:
    #   - Activity: count of shows in the past 90 days + next 90 days,
    #     saturated at 60 shows (approx one show every three days on average).
    #   - Quality: booking-weighted average comedian popularity - the LEFT JOIN
    #     fans out one row per (show, comedian) pair, so a comedian booked
    #     multiple times at this club in the window contributes proportionally
    #     more. This intentionally rewards clubs that book popular comedians
    #     repeatedly, not just once. Values are already normalized to 0-1
    #     by update_comedian_popularity.
    #   - Click demand: all ticket-purchase clicks in the last 30 days,
    #     saturated at 20 clicks per club. These are intent clicks; they do not
    #     require confirmed purchases until conversion tracking exists.
    # Activity gets 50% weight, quality 35%, and click demand 15%.
    #
    # Dormant-club decay (TASK-2702): clubs with no shows at all in the last
    # 180 days are emitted with popularity = clubs.popularity * 0.5 so a venue
    # that has gone quiet for >6 months stops freezing at its last-active value
    # in search results. Each nightly run halves again, so a permanently
    # dormant club converges to 0 within a couple of weeks. A club whose most
    # recent show is between 90 and 180 days old is still treated as
    # absent (keeps its prior popularity untouched) — the decay only fires once
    # the club has been quiet for longer than the canonical ±90d activity
    # window, which avoids penalizing slow seasons.
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
        ),
        active_popularity AS (
            SELECT
                club_metrics.club_id,
                LEAST(
                    LEAST((upcoming_shows + recent_shows)::float / 60.0, 1.0) * 0.5 +
                    COALESCE(avg_comedian_popularity, 0) * 0.35 +
                    COALESCE(clicks.click_demand_rate, 0) * 0.15,
                    1.0
                ) AS popularity
            FROM club_metrics
            LEFT JOIN LATERAL (
                SELECT LEAST(COUNT(*)::float / 20.0, 1.0) AS click_demand_rate
                FROM ticket_purchase_click_events tpce
                WHERE tpce.club_id = club_metrics.club_id
                  AND tpce.created_at >= NOW() - INTERVAL '30 days'
            ) clicks ON true
            WHERE upcoming_shows + recent_shows > 0
        ),
        dormant_popularity AS (
            SELECT
                clubs.id AS club_id,
                clubs.popularity * 0.5 AS popularity
            FROM clubs
            WHERE clubs.id = ANY(%s::int[])
              AND clubs.popularity > 0
              AND clubs.id NOT IN (SELECT club_id FROM active_popularity)
              AND NOT EXISTS (
                  SELECT 1 FROM shows
                  WHERE shows.club_id = clubs.id
                    AND shows.date >= CURRENT_DATE - INTERVAL '180 days'
              )
        )
        SELECT club_id, popularity FROM active_popularity
        UNION ALL
        SELECT club_id, popularity FROM dormant_popularity
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
