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
    
    BATCH_UPDATE_COMEDIAN_SHOW_COUNTS = '''
        WITH show_ticket_status AS (
            SELECT 
                li.comedian_id, s.id as show_id,
                COUNT(*) as total_tickets,
                COUNT(*) FILTER (WHERE t.sold_out) as sold_out_tickets
            FROM lineup_items li
            JOIN shows s ON s.id = li.show_id
            JOIN tickets t ON t.show_id = s.id
            WHERE s.id = ANY(%s)
            GROUP BY li.comedian_id, s.id
            HAVING COUNT(*) > 0
        ),
        comedian_stats AS (
            SELECT 
                comedian_id,
                COUNT(DISTINCT show_id) as total_shows,
                COUNT(DISTINCT CASE WHEN total_tickets = sold_out_tickets THEN show_id END) as sold_out_shows
            FROM show_ticket_status
            GROUP BY comedian_id
        )
        UPDATE comedians AS c
        SET 
            total_shows = COALESCE(cs.total_shows, 0),
            sold_out_shows = COALESCE(cs.sold_out_shows, 0)
        FROM comedian_stats cs
        WHERE c.uuid = cs.comedian_id
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
