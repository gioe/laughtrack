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
        SELECT uuid, name, songkick_id, bandsintown_id
        FROM comedians
        WHERE songkick_id IS NOT NULL OR bandsintown_id IS NOT NULL
        ORDER BY name
    '''
