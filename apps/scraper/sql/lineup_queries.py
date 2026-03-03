"""SQL queries for lineup operations."""


class LineupQueries:
    """SQL queries for lineup operations."""
    
    BATCH_DELETE_LINEUP_ITEMS = """
        DELETE FROM lineup_items
        WHERE (show_id, comedian_id) IN (
            SELECT * FROM (VALUES %s) as v(show_id, comedian_id)
        );
    """
    
    BATCH_ADD_LINEUP_ITEMS = """
        INSERT INTO lineup_items (show_id, comedian_id)
        VALUES %s
        ON CONFLICT (show_id, comedian_id) DO NOTHING;
    """
    
    BATCH_GET_LINEUP = '''
        SELECT 
            s.id as show_id,
            array_agg(json_build_object('name', c.name, 'uuid', c.uuid)) as lineup
        FROM lineup_items li 
        JOIN shows s ON s.id = li.show_id 
        JOIN comedians c ON c.uuid = li.comedian_id 
        WHERE s.id = ANY(%s)
        GROUP BY s.id
    '''
    
    BATCH_GET_COMEDIANS_FROM_SHOW_NAME = """
        WITH show_names AS (
            SELECT unnest(array_agg(name)) as name
            FROM (VALUES %s) AS t(name)
        )
        SELECT 
            c.uuid, c.name, c.sold_out_shows, c.total_shows, s.name as show_name
        FROM comedians c
        CROSS JOIN show_names s
        WHERE lower(s.name) LIKE '%%' || lower(c.name) || '%%'
        ORDER BY s.name, c.name;
    """
