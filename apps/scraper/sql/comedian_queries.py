"""SQL queries for comedian operations."""


class ComedianQueries:
    """SQL queries for comedian operations."""
    
    BATCH_GET_COMEDIAN_DETAILS = '''
        SELECT 
            uuid, name, instagram_followers, tiktok_followers, youtube_followers,
            sold_out_shows, total_shows
        FROM comedians
        WHERE uuid = ANY(%s)
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
        RETURNING uuid
    '''

    # Recomputes sold_out_shows and total_shows for each comedian across ALL shows
    # (no show_id filter).  A show is sold out when every ticket for that show has
    # sold_out = TRUE and at least one ticket exists; shows with no tickets are not
    # counted as sold out.
    BATCH_UPDATE_COMEDIAN_SHOW_COUNTS = '''
        UPDATE comedians AS c
        SET
            total_shows    = v.total_shows,
            sold_out_shows = v.sold_out_shows
        FROM (
            SELECT
                li.comedian_id,
                COUNT(DISTINCT li.show_id) AS total_shows,
                COUNT(DISTINCT CASE
                    WHEN ta.all_sold_out THEN li.show_id
                END) AS sold_out_shows
            FROM lineup_items li
            LEFT JOIN (
                SELECT
                    show_id,
                    BOOL_AND(sold_out) AS all_sold_out
                FROM tickets
                GROUP BY show_id
            ) ta ON ta.show_id = li.show_id
            WHERE li.comedian_id = ANY(%s)
            GROUP BY li.comedian_id
        ) v
        WHERE c.uuid = v.comedian_id
    '''

    GET_COMEDIAN_RECENCY_SCORES = '''
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
            ) AS recency_score
        FROM lineup_items li
        JOIN shows s ON s.id = li.show_id
        WHERE li.comedian_id = ANY(%s)
          AND s.date >= CURRENT_DATE - INTERVAL '180 days'
        GROUP BY li.comedian_id
    '''

    GET_COMEDIANS_WITH_TOUR_IDS = '''
        SELECT uuid, name, bandsintown_id
        FROM comedians
        WHERE bandsintown_id IS NOT NULL
        ORDER BY name
    '''

    GET_COMEDIANS_WITH_YOUTUBE_ACCOUNT = '''
        SELECT uuid, youtube_account
        FROM comedians
        WHERE youtube_account IS NOT NULL
          AND youtube_account <> ''
        ORDER BY name
    '''

    UPDATE_COMEDIAN_YOUTUBE_FOLLOWERS = '''
        UPDATE comedians AS c
        SET youtube_followers = v.followers::int
        FROM (VALUES %s) AS v(uuid, followers)
        WHERE c.uuid = v.uuid::text
    '''

    GET_COMEDIANS_WITH_INSTAGRAM_ACCOUNT = '''
        SELECT uuid, instagram_account
        FROM comedians
        WHERE instagram_account IS NOT NULL
          AND instagram_account <> ''
        ORDER BY name
    '''

    UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS = '''
        UPDATE comedians AS c
        SET instagram_followers = v.followers::int
        FROM (VALUES %s) AS v(uuid, followers)
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
        SELECT name FROM comedian_deny_list WHERE name = ANY(%s)
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
        SET bandsintown_id = COALESCE(v.bandsintown_id, c.bandsintown_id),
            songkick_id = COALESCE(v.songkick_id, c.songkick_id)
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
