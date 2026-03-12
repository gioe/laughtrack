"""SQL queries for club operations."""


class ClubQueries:
    """SQL queries for club operations."""
    
    GET_ALL_CLUBS = '''
        SELECT * FROM clubs WHERE scraper IS NOT NULL and visible = True ORDER BY id
    '''
    
    GET_CLUB_BY_ID = '''
        SELECT * 
        FROM clubs 
        WHERE id = %s AND scraper IS NOT NULL
    '''
    
    GET_CLUB_BY_IDS = '''
        SELECT * 
        FROM clubs 
        WHERE id = ANY(%s::int[]) AND scraper IS NOT NULL
        ORDER BY id
    '''
    
    # Backward compatibility alias
    GET_SPECIFIC_CLUBS = GET_CLUB_BY_IDS
    
    GET_CLUBS_BY_SCRAPER = '''
        SELECT * 
        FROM clubs 
        WHERE scraper = %s AND scraper IS NOT NULL
        ORDER BY id
    '''
    
    GET_DISTINCT_SCRAPER_TYPES = '''
        SELECT scraper, COUNT(*) as club_count
        FROM clubs
        WHERE scraper IS NOT NULL
        GROUP BY scraper
        ORDER BY scraper
    '''

    UPSERT_CLUB_BY_EVENTBRITE_VENUE = '''
        INSERT INTO clubs (
            name, address, website, scraping_url,
            eventbrite_id, scraper, visible,
            zip_code, phone_number, popularity, timezone
        )
        VALUES (%s, %s, '', 'www.eventbrite.com', %s, 'eventbrite', true, %s, '', 0, NULL)
        ON CONFLICT (name) DO UPDATE SET
            eventbrite_id = COALESCE(clubs.eventbrite_id, EXCLUDED.eventbrite_id),
            scraper       = COALESCE(clubs.scraper,       EXCLUDED.scraper)
        RETURNING *
    '''
