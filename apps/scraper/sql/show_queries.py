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
            production_company_id, last_scraped_by
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
            production_company_id = COALESCE(EXCLUDED.production_company_id, shows.production_company_id),
            last_scraped_by = COALESCE(EXCLUDED.last_scraped_by, shows.last_scraped_by)
        RETURNING
            id, club_id, room, date,
            CASE
                WHEN xmax::text::int > 0 THEN 'updated'
                ELSE 'inserted'
            END AS operation_type
    '''

    GET_SHOWS_BY_CLUB_DATE_NAME = '''
        SELECT id, club_id, date, room, COALESCE(name, '') AS name
        FROM shows
        WHERE club_id = ANY(%s)
          AND date = ANY(%s)
          AND COALESCE(name, '') = ANY(%s)
        ORDER BY id
    '''

    # PatronTicket-family shows (generic patron_ticket + bespoke up_comedy_club)
    # carry a stable Salesforce instance id in the #/instances/<id> fragment of
    # show_page_url. Fetch existing instance-bearing rows for the affected clubs so
    # the handler can match an incoming show to its existing row by instance id and
    # move it to a rescheduled date in place (see _reconcile_patronticket_instances).
    GET_PATRONTICKET_SHOWS_BY_CLUB = '''
        SELECT id, club_id, date, room, show_page_url
        FROM shows
        WHERE club_id = ANY(%s)
          AND show_page_url LIKE '%%/instances/%%'
        ORDER BY id
    '''

    # Move an existing show to a new (rescheduled) date in place, keyed by id, so the
    # downstream ON CONFLICT (club_id, date, room) upsert updates the same row instead
    # of inserting a near-duplicate. The NOT EXISTS guard prevents a unique-constraint
    # violation if some other row already occupies (club_id, new_date, room); in that
    # case the move is skipped and the upsert reconciles against that row instead.
    # Params: (new_date, show_id, new_date).
    UPDATE_SHOW_DATE_BY_ID = '''
        UPDATE shows AS s
        SET date = %s
        WHERE s.id = %s
          AND NOT EXISTS (
              SELECT 1 FROM shows o
              WHERE o.club_id = s.club_id
                AND o.date = %s
                AND o.room = s.room
                AND o.id <> s.id
          )
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
