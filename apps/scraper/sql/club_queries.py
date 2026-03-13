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

    UPSERT_CLUB_BY_SEATENGINE_VENUE = '''
        INSERT INTO clubs (
            name, address, website, scraping_url,
            seatengine_id, scraper, visible,
            zip_code, phone_number, popularity, timezone
        )
        VALUES (%s, %s, %s, 'www.seatengine.com', %s, 'seatengine', true, %s, '', 0, NULL)
        ON CONFLICT (name) DO UPDATE SET
            seatengine_id = COALESCE(clubs.seatengine_id, EXCLUDED.seatengine_id),
            scraper       = COALESCE(clubs.scraper,       EXCLUDED.scraper)
        RETURNING *
    '''

    GET_CLUBS_WITH_NULL_TIMEZONE = '''
        SELECT * FROM clubs
        WHERE scraper = %s AND timezone IS NULL
        ORDER BY id
    '''

    UPDATE_CLUB_TIMEZONE = '''
        UPDATE clubs
        SET timezone = %s
        WHERE id = %s AND timezone IS NULL
        RETURNING id
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
            zip_code, phone_number, popularity, timezone
        )
        VALUES (%s, %s, '', 'www.ticketmaster.com', %s, 'live_nation', true, %s, '', 0, %s)
        ON CONFLICT (name) DO UPDATE SET
            ticketmaster_id = COALESCE(clubs.ticketmaster_id, EXCLUDED.ticketmaster_id),
            scraper         = COALESCE(clubs.scraper,         EXCLUDED.scraper),
            timezone        = COALESCE(clubs.timezone,        EXCLUDED.timezone)
        RETURNING *
    '''
