"""SQL queries for comedian operations."""


class ComedianQueries:
    """SQL queries for comedian operations."""
    
    # has_image and has_podcast_appearance feed PopularityScorer's confidence
    # gate so a 1-of-1 sold-out attribution on a lineup-extraction-noise row
    # cannot saturate performance_score onto the 0.6 popularity cliff. The
    # podcast EXISTS clauses use review_status='accepted' (the human-verified
    # state used by review_podcast_*_candidates / backfill_podcast_appearances)
    # so an "accepted" appearance counts via either comedian_podcasts or
    # episode_appearances — matching the discovery → review → publish pipeline.
    # favorite_count is a lightly weighted first-party signal in PopularityScorer.
    BATCH_GET_COMEDIAN_DETAILS = '''
        SELECT
            c.uuid, c.name, c.instagram_followers, c.tiktok_followers, c.youtube_followers,
            c.sold_out_shows, c.total_shows,
            c.has_image,
            (
                EXISTS (
                    SELECT 1 FROM comedian_podcasts cp
                    WHERE cp.comedian_id = c.id
                      AND cp.review_status = 'accepted'
                )
                OR EXISTS (
                    SELECT 1 FROM episode_appearances ea
                    WHERE ea.comedian_id = c.id
                      AND ea.review_status = 'accepted'
                )
            ) AS has_podcast_appearance,
            (
                SELECT COUNT(*)
                FROM favorite_comedians fc
                WHERE fc.comedian_id = c.uuid
            ) AS favorite_count
        FROM comedians c
        WHERE c.uuid = ANY(%s)
    '''
    
    BATCH_UPDATE_COMEDIAN_POPULARITY = '''
        UPDATE comedians AS c
        SET popularity = v.popularity
        FROM (VALUES %s) AS v(uuid, popularity)
        WHERE c.uuid = v.uuid::text
    '''
    
    GET_TARGET_COMEDIAN_IDS = '''
        SELECT uuid FROM comedians WHERE uuid = ANY(%s);
    '''

    GET_ALL_COMEDIAN_UUIDS = '''
        SELECT uuid FROM comedians;
    '''
    
    # Insert-only upsert: name-only stubs (e.g. from lineup extraction) must never
    # overwrite existing comedian data. DO NOTHING on conflict ensures that follower
    # counts, social accounts, and show stats for established comedians are preserved.
    BATCH_ADD_COMEDIANS = '''
        INSERT INTO comedians (uuid, name, sold_out_shows, total_shows)
        VALUES %s
        ON CONFLICT (uuid) DO NOTHING
        RETURNING id, uuid, name
    '''

    # Recomputes sold_out_shows and total_shows for each comedian across ALL shows
    # (no show_id filter).  A show is sold out when every ticket for that show has
    # sold_out = TRUE and at least one ticket exists; shows with no tickets are not
    # counted as sold out. total_shows is the sold-out-rate denominator: it includes
    # confirmed sellouts from any source plus non-sold-out shows only when the
    # scraper reports sold_out reliably.
    #
    # The LATERAL subquery is load-bearing: a previous version used a top-level
    # `(SELECT show_id, BOOL_AND(sold_out) FROM tickets GROUP BY show_id)` LEFT
    # JOIN, which Postgres materialized over the entire tickets table on every
    # call because the outer `comedian_id = ANY(%s)` filter cannot push into an
    # aggregated subquery. As tickets scaled this single statement crossed
    # Neon's 30s statement_timeout mid-nightly (TASK-2544). The LATERAL form
    # computes BOOL_AND per-show using the tickets(show_id, type) unique index,
    # so the work scales with len(lineup_items for target comedians) instead of
    # len(tickets).
    BATCH_UPDATE_COMEDIAN_SHOW_COUNTS = '''
        WITH source_sold_out_capabilities AS (
            SELECT
                resolved.scraper_key,
                CASE
                    WHEN resolved.metadata ? 'reports_sold_out' THEN
                        lower(resolved.metadata->>'reports_sold_out') IN ('1', 'true', 'yes')
                    ELSE
                        resolved.platform IN ('eventbrite', 'seatengine', 'seatengine_v3', 'tixr')
                        OR resolved.scraper_key IN (
                            'eventbrite',
                            'seatengine',
                            'seatengine_classic',
                            'seatengine_v3',
                            'tixr'
                        )
                END AS reports_sold_out
            FROM scraping_sources ss
            JOIN clubs cl ON cl.id = ss.club_id
            LEFT JOIN chain_scraping_defaults csd
              ON csd.chain_id = cl.chain_id
             AND csd.platform = ss.platform
             AND csd.priority = ss.priority
             AND NULLIF(ss.scraper_key, '') IS NULL
             AND csd.enabled = TRUE
            CROSS JOIN LATERAL (
                SELECT
                    COALESCE(NULLIF(ss.scraper_key, ''), csd.scraper_key, ss.scraper_key) AS scraper_key,
                    -- ss.platform is the ScrapingPlatform enum; NULLIF(enum, '') fails
                    -- on Postgres because '' cannot be cast to the enum domain. The text
                    -- NULLIF pattern works on scraper_key (text column) but NOT here.
                    COALESCE(ss.platform, csd.platform) AS platform,
                    COALESCE(csd.metadata, '{}'::jsonb) || COALESCE(ss.metadata, '{}'::jsonb) AS metadata
            ) resolved
            WHERE ss.enabled = TRUE
              AND NULLIF(resolved.scraper_key, '') IS NOT NULL
        ),
        reliable_sold_out_scrapers AS (
            SELECT scraper_key, BOOL_OR(reports_sold_out) AS reports_sold_out
            FROM source_sold_out_capabilities
            GROUP BY scraper_key
        )
        UPDATE comedians AS c
        SET
            total_shows    = v.total_shows,
            sold_out_shows = v.sold_out_shows
        FROM (
            SELECT
                li.comedian_id,
                COUNT(DISTINCT li.show_id) FILTER (
                    WHERE ta.all_sold_out OR COALESCE(ros.reports_sold_out, FALSE)
                ) AS total_shows,
                COUNT(DISTINCT li.show_id) FILTER (WHERE ta.all_sold_out)
                    AS sold_out_shows
            FROM lineup_items li
            JOIN shows s ON s.id = li.show_id
            LEFT JOIN reliable_sold_out_scrapers ros
              ON ros.scraper_key = s.last_scraped_by
            LEFT JOIN LATERAL (
                SELECT BOOL_AND(t.sold_out) AS all_sold_out
                FROM tickets t
                WHERE t.show_id = li.show_id
            ) ta ON true
            WHERE li.comedian_id = ANY(%s)
            GROUP BY li.comedian_id
        ) v
        WHERE c.uuid = v.comedian_id
    '''

    # Home location uses recently scraped, distinct engagements rather than raw
    # lineup rows. A venue run can create one row per showtime/listing, so
    # show_page_url (or date when no URL exists) is the durable engagement key.
    # Recency weights keep current touring from losing to stale all-time runs.
    BATCH_UPDATE_COMEDIAN_HOME_LOCATION = '''
        WITH target_comedians AS (
            SELECT uuid
            FROM comedians
            WHERE uuid = ANY(%s)
        ),
        engagement_rows AS (
            SELECT
                li.comedian_id,
                cl.id AS club_id,
                NULLIF(BTRIM(cl.city), '') AS city,
                NULLIF(BTRIM(cl.state), '') AS state,
                NULLIF(BTRIM(cl.country), '') AS country,
                COALESCE(
                    NULLIF(BTRIM(s.show_page_url), ''),
                    s.date::date::text
                ) AS engagement_key,
                CASE
                    WHEN s.date >= CURRENT_DATE THEN 4.0
                    WHEN s.date >= CURRENT_DATE - INTERVAL '90 days' THEN 2.0
                    WHEN s.date >= CURRENT_DATE - INTERVAL '365 days' THEN 1.0
                    ELSE 0.25
                END AS engagement_weight,
                s.date AS seen_at
            FROM lineup_items li
            JOIN target_comedians tc ON tc.uuid = li.comedian_id
            JOIN shows s ON s.id = li.show_id
            JOIN clubs cl ON cl.id = s.club_id
            WHERE s.last_scraped_date IS NOT NULL
              AND s.last_scraped_date >= NOW() - (%s * INTERVAL '1 day')
        ),
        distinct_engagements AS (
            SELECT
                comedian_id,
                club_id,
                city,
                state,
                country,
                engagement_key,
                MAX(engagement_weight) AS engagement_weight,
                MAX(seen_at) AS last_seen_at
            FROM engagement_rows
            GROUP BY
                comedian_id,
                club_id,
                city,
                state,
                country,
                engagement_key
        ),
        club_counts AS (
            SELECT
                comedian_id,
                club_id,
                COUNT(DISTINCT engagement_key) AS engagement_count,
                SUM(engagement_weight) AS engagement_score,
                MAX(last_seen_at) AS last_seen_at
            FROM distinct_engagements
            GROUP BY comedian_id, club_id
        ),
        ranked_clubs AS (
            SELECT
                comedian_id,
                club_id,
                ROW_NUMBER() OVER (
                    PARTITION BY comedian_id
                    ORDER BY
                        engagement_score DESC,
                        engagement_count DESC,
                        last_seen_at DESC,
                        club_id ASC
                ) AS club_rank,
                -- Touring detection: RANK (not ROW_NUMBER) so every club sharing
                -- the top (engagement_score, engagement_count) gets club_tie_rank=1.
                -- The deterministic last_seen_at/club_id tiebreakers are
                -- DELIBERATELY excluded here so a genuine score+count tie is
                -- detectable rather than silently broken.
                RANK() OVER (
                    PARTITION BY comedian_id
                    ORDER BY
                        engagement_score DESC,
                        engagement_count DESC
                ) AS club_tie_rank
            FROM club_counts
        ),
        -- A comedian has a home club only if exactly ONE club sits at the top
        -- score+count tie. 2+ tied clubs means no clear anchor -> touring.
        club_top_ties AS (
            SELECT comedian_id, COUNT(*) AS top_count
            FROM ranked_clubs
            WHERE club_tie_rank = 1
            GROUP BY comedian_id
        ),
        city_counts AS (
            SELECT
                comedian_id,
                city,
                state,
                country,
                COUNT(DISTINCT engagement_key) AS engagement_count,
                SUM(engagement_weight) AS engagement_score,
                MAX(last_seen_at) AS last_seen_at
            FROM distinct_engagements
            WHERE city IS NOT NULL
            GROUP BY
                comedian_id,
                city,
                state,
                country
        ),
        ranked_cities AS (
            SELECT
                comedian_id,
                city,
                state,
                country,
                ROW_NUMBER() OVER (
                    PARTITION BY comedian_id
                    ORDER BY
                        engagement_score DESC,
                        engagement_count DESC,
                        last_seen_at DESC,
                        city ASC,
                        state ASC,
                        country ASC
                ) AS city_rank,
                -- City touring detection, independent of the club tie: a comedian
                -- touring many clubs in ONE city still has a clear home city, so
                -- this ties on the city-level score+count, not the club's.
                RANK() OVER (
                    PARTITION BY comedian_id
                    ORDER BY
                        engagement_score DESC,
                        engagement_count DESC
                ) AS city_tie_rank
            FROM city_counts
        ),
        city_top_ties AS (
            SELECT comedian_id, COUNT(*) AS top_count
            FROM ranked_cities
            WHERE city_tie_rank = 1
            GROUP BY comedian_id
        )
        UPDATE comedians AS c
        SET
            -- NULL home (touring) when 2+ cities/clubs tie for the top
            -- score+count. Club and city are gated independently so a
            -- single-city tourer keeps its home city while losing its home club.
            home_city = CASE WHEN cct.top_count = 1 THEN rc.city END,
            home_state = CASE WHEN cct.top_count = 1 THEN rc.state END,
            home_country = CASE WHEN cct.top_count = 1 THEN rc.country END,
            home_club_id = CASE WHEN clt.top_count = 1 THEN rcl.club_id END,
            home_location_updated_at = NOW()
        FROM target_comedians tc
        LEFT JOIN ranked_cities rc
          ON rc.comedian_id = tc.uuid
         AND rc.city_rank = 1
        LEFT JOIN city_top_ties cct
          ON cct.comedian_id = tc.uuid
        LEFT JOIN ranked_clubs rcl
          ON rcl.comedian_id = tc.uuid
         AND rcl.club_rank = 1
        LEFT JOIN club_top_ties clt
          ON clt.comedian_id = tc.uuid
        WHERE c.uuid = tc.uuid
    '''

    # Comedian recency blends date-decayed show activity with first-party click
    # demand inherited through lineup_items. All ticket-purchase clicks count,
    # including clicks without confirmed purchases: this is an intent signal
    # until conversion tracking exists.
    GET_COMEDIAN_RECENCY_SCORES = '''
        WITH comedian_metrics AS (
            SELECT
                li.comedian_id,
                LEAST(
                    SUM(
                        CASE
                            WHEN s.date >= CURRENT_DATE               THEN 4.0
                            WHEN s.date >= CURRENT_DATE - INTERVAL '30 days'  THEN 3.0
                            WHEN s.date >= CURRENT_DATE - INTERVAL '90 days'  THEN 2.0
                            WHEN s.date >= CURRENT_DATE - INTERVAL '180 days' THEN 1.0
                            ELSE 0.0
                        END
                    ) / 20.0,
                    1.0
                ) AS activity_recency_score,
                LEAST(SUM(show_clicks.click_count)::float / 20.0, 1.0) AS click_demand_rate
            FROM lineup_items li
            JOIN shows s ON s.id = li.show_id
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS click_count
                FROM ticket_purchase_click_events tpce
                WHERE tpce.show_id = s.id
                  AND tpce.created_at >= NOW() - INTERVAL '30 days'
            ) show_clicks ON true
            WHERE li.comedian_id = ANY(%s)
              AND s.date >= CURRENT_DATE - INTERVAL '180 days'
            GROUP BY li.comedian_id
        )
        SELECT
            comedian_id,
            LEAST(
                activity_recency_score * 0.85
                + click_demand_rate * 0.15,
                1.0
            ) AS recency_score
        FROM comedian_metrics
    '''

    GET_COMEDIANS_WITH_TOUR_IDS = '''
        SELECT uuid, name, bandsintown_id
        FROM comedians
        WHERE bandsintown_id IS NOT NULL
        ORDER BY name
    '''

    # Only return comedians whose subscriber count is stale (never refreshed, or
    # refreshed longer than the bound stale-days ago). Oldest-first so partial or
    # --limit runs always make progress on the most out-of-date rows. Mirrors the
    # Instagram staleness gate so both platforms refresh as a weekly cohort.
    # Positional %s (not %(name)s) so the sql-parse-time guard can rewrite it to
    # $1 for PREPARE — see tests/sql/test_sql_parse_time.py.
    GET_STALE_COMEDIANS_WITH_YOUTUBE_ACCOUNT = '''
        SELECT uuid, youtube_account
        FROM comedians
        WHERE youtube_account IS NOT NULL
          AND youtube_account <> ''
          AND (
            youtube_followers_refreshed_at IS NULL
            OR youtube_followers_refreshed_at < NOW() - make_interval(days => %s)
          )
        ORDER BY youtube_followers_refreshed_at ASC NULLS FIRST, name
    '''

    UPDATE_COMEDIAN_YOUTUBE_FOLLOWERS = '''
        UPDATE comedians AS c
        SET youtube_followers = v.followers::int,
            youtube_followers_refreshed_at = NOW()
        FROM (VALUES %s) AS v(uuid, followers)
        WHERE c.uuid = v.uuid::text
    '''

    # Only return comedians whose follower count is stale (never refreshed, or
    # refreshed longer than the bound stale-days ago). Oldest-first so partial
    # or --limit runs always make progress on the most out-of-date rows.
    # Positional %s (not %(name)s) so the sql-parse-time guard can rewrite it to
    # $1 for PREPARE — see tests/sql/test_sql_parse_time.py.
    GET_STALE_COMEDIANS_WITH_INSTAGRAM_ACCOUNT = '''
        SELECT uuid, instagram_account
        FROM comedians
        WHERE instagram_account IS NOT NULL
          AND instagram_account <> ''
          AND (
            instagram_followers_refreshed_at IS NULL
            OR instagram_followers_refreshed_at < NOW() - make_interval(days => %s)
          )
        ORDER BY instagram_followers_refreshed_at ASC NULLS FIRST, name
    '''

    UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS = '''
        UPDATE comedians AS c
        SET instagram_followers = v.followers::int,
            instagram_followers_refreshed_at = NOW()
        FROM (VALUES %s) AS v(uuid, followers)
        WHERE c.uuid = v.uuid::text
    '''

    # Clear a dead Instagram handle (404 — account gone/renamed). Nulls the
    # handle and its follower count together to preserve the "no follower count
    # without a handle" invariant, plus the refresh timestamp so the row reads
    # as fully un-enriched.
    CLEAR_COMEDIAN_INSTAGRAM_ACCOUNT = '''
        UPDATE comedians AS c
        SET instagram_account = NULL,
            instagram_followers = NULL,
            instagram_followers_refreshed_at = NULL
        FROM (VALUES %s) AS v(uuid)
        WHERE c.uuid = v.uuid::text
    '''

    GET_COMEDIANS_WITH_TIKTOK_ACCOUNT = '''
        SELECT uuid, tiktok_account
        FROM comedians
        WHERE tiktok_account IS NOT NULL
          AND tiktok_account <> ''
        ORDER BY name
    '''

    UPDATE_COMEDIAN_TIKTOK_FOLLOWERS = '''
        UPDATE comedians AS c
        SET tiktok_followers = v.followers::int
        FROM (VALUES %s) AS v(uuid, followers)
        WHERE c.uuid = v.uuid::text
    '''

    # Deny-list: insert names of deleted false-positive comedians so ingestion can skip them.
    # ON CONFLICT DO NOTHING prevents duplicate entries when the same name is deleted again.
    UPSERT_DENY_LIST_NAMES = '''
        INSERT INTO comedian_deny_list (name, reason, added_by)
        VALUES %s
        ON CONFLICT (name) DO NOTHING
    '''

    # Check which names in a given list are on the deny list.
    GET_DENIED_NAMES = '''
        SELECT name
        FROM comedian_deny_list
        WHERE lower(btrim(regexp_replace(replace(name, chr(160), ' '), '[[:space:]]+', ' ', 'g'))) = ANY(%s)
    '''

    # Check which names in a given list match existing comedians.visible=false rows.
    # Companion to GET_DENIED_NAMES — together they form the two-stage suppression
    # check per docs/comedian-visible-consolidation.md Decision 1: hidden comedians
    # (already ingested, suppressed via visible=false) + orphan deny-list names
    # (never ingested, pre-emptively blocked by name).
    GET_HIDDEN_COMEDIAN_NAMES = '''
        SELECT name
        FROM comedians
        WHERE visible = false
          AND lower(btrim(regexp_replace(replace(name, chr(160), ' '), '[[:space:]]+', ' ', 'g'))) = ANY(%s)
    '''

    BATCH_SET_HAS_IMAGE_TRUE = '''
        UPDATE comedians
        SET has_image = true
        WHERE name = ANY(%s)
    '''

    # Website scraping metadata queries

    GET_COMEDIANS_WITH_WEBSITES_BASE = '''
        SELECT uuid, name, website, website_scraping_url,
               website_discovery_source,
               website_last_scraped, website_scrape_strategy
        FROM comedians
        WHERE website IS NOT NULL
          AND website <> ''
    '''

    GET_COMEDIANS_WITH_WEBSITES = GET_COMEDIANS_WITH_WEBSITES_BASE + '''
        ORDER BY name
    '''

    GET_COMEDIANS_FOR_WEBSITE_SCRAPING = '''
        SELECT uuid, name, website, website_scraping_url,
               website_discovery_source,
               website_last_scraped, website_scrape_strategy
        FROM comedians
        WHERE website_scraping_url IS NOT NULL
          AND website_scraping_url <> ''
          AND (website_scraping_url_confidence IS NULL
               OR website_scraping_url_confidence != 'low')
          AND (website_last_scraped IS NULL
               OR website_last_scraped < NOW() - INTERVAL '7 days')
        ORDER BY website_last_scraped ASC NULLS FIRST
    '''

    UPDATE_COMEDIAN_TOUR_IDS = '''
        UPDATE comedians AS c
        SET bandsintown_id = CASE
                WHEN v.bandsintown_id IS NOT NULL
                 AND NULLIF(BTRIM(COALESCE(c.bandsintown_id, '')), '') IS NULL
                THEN v.bandsintown_id
                ELSE c.bandsintown_id
            END,
            songkick_id = CASE
                WHEN v.songkick_id IS NOT NULL
                 AND NULLIF(BTRIM(COALESCE(c.songkick_id, '')), '') IS NULL
                THEN v.songkick_id
                ELSE c.songkick_id
            END
        FROM (VALUES %s) AS v(uuid, bandsintown_id, songkick_id)
        WHERE c.uuid = v.uuid::text
    '''

    UPDATE_COMEDIAN_WEBSITE_SCRAPE_METADATA = '''
        UPDATE comedians AS c
        SET website_discovery_source = v.discovery_source,
            website_last_scraped = v.last_scraped::timestamptz,
            website_scrape_strategy = v.scrape_strategy
        FROM (VALUES %s) AS v(uuid, discovery_source, last_scraped, scrape_strategy)
        WHERE c.uuid = v.uuid::text
    '''

    UPDATE_COMEDIAN_WEBSITE_SCRAPING_URL = '''
        UPDATE comedians AS c
        SET website_scraping_url = v.scraping_url
        FROM (VALUES %s) AS v(uuid, scraping_url)
        WHERE c.uuid = v.uuid::text
          AND c.website_scraping_url IS DISTINCT FROM v.scraping_url
    '''

    UPDATE_COMEDIAN_WEBSITE_CONFIDENCE = '''
        UPDATE comedians AS c
        SET website_confidence = v.confidence
        FROM (VALUES %s) AS v(uuid, confidence)
        WHERE c.uuid = v.uuid::text
          AND c.website_confidence IS DISTINCT FROM v.confidence
    '''

    UPDATE_COMEDIAN_WEBSITE_SCRAPING_URL_CONFIDENCE = '''
        UPDATE comedians AS c
        SET website_scraping_url_confidence = v.confidence
        FROM (VALUES %s) AS v(uuid, confidence)
        WHERE c.uuid = v.uuid::text
          AND c.website_scraping_url_confidence IS DISTINCT FROM v.confidence
    '''

    # Stored popularity by exact comedian name. Used by genre-less venue scrapers
    # (e.g. playhouse_square) to gate a name-match comedy filter on the comedian's
    # popularity floor, dropping junk/miscategorised comedian rows whose names
    # collide with non-comedy show titles (e.g. a "The Nutcracker" ballet row).
    GET_STORED_POPULARITY_BY_NAMES = '''
        SELECT name, popularity
        FROM comedians
        WHERE name = ANY(%s)
    '''
