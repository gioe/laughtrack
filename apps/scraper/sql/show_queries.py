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
            id, name, show_page_url, description, date, club_id, room, popularity
        FROM shows
        WHERE id = ANY(%s)
        ORDER BY id;
    """
    
    BATCH_INSERT_SHOWS = '''
        INSERT INTO shows (
            name, show_page_url, description, date, club_id, last_scraped_date, room,
            production_company_id
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
            production_company_id = COALESCE(EXCLUDED.production_company_id, shows.production_company_id)
        RETURNING
            id, club_id, room, date,
            CASE
                WHEN xmax::text::int > 0 THEN 'updated'
                ELSE 'inserted'
            END AS operation_type
    '''
    
    BATCH_GET_LINEUP_POPULARITY = '''
        WITH lineup_details AS (
            SELECT 
                li.show_id, li.comedian_id, c.popularity
            FROM lineup_items li
            JOIN comedians c ON c.uuid = li.comedian_id
            WHERE li.show_id = ANY(%s)
        )
        SELECT 
            show_id,
            (
                SUM(popularity) * (1 + LEAST(ln(COUNT(comedian_id)), ln(5))) / 5.0
            ) as modified_popularity
        FROM lineup_details
        GROUP BY show_id
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
