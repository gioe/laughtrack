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
        SELECT v.show_id, v.comedian_id
        FROM (VALUES %s) AS v(show_id, comedian_id)
        WHERE EXISTS (SELECT 1 FROM comedians c WHERE c.uuid = v.comedian_id)
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
        ), candidate_comedians AS (
            SELECT
                c.uuid, c.name, c.sold_out_shows, c.total_shows,
                trim(regexp_replace(lower(c.name), '[^[:alnum:]]+', ' ', 'g')) as normalized_name
            FROM comedians c
            WHERE c.name IS NOT NULL
              AND array_length(regexp_split_to_array(trim(c.name), '[[:space:]]+'), 1) >= 2
              AND lower(trim(c.name)) NOT IN (
                  'tba',
                  'tbd',
                  'to be announced',
                  'to be determined',
                  'special guest',
                  'special guests',
                  'surprise guest',
                  'surprise act',
                  'mystery guest',
                  'comedy show',
                  'various artists',
                  'headliner',
                  'featured comedian',
                  'local comedian',
                  'guest comedian',
                  'guest',
                  'open mic',
                  'host',
                  'mc',
                  'emcee',
                  'opener',
                  'opener tbd',
                  'headliner tbd',
                  'lineup tba',
                  'more tba',
                  'plus more',
                  'and more',
                  'and special guests',
                  'comedian tba',
                  'comedian tbd',
                  'comics tba',
                  'comics tbd',
                  'private event',
                  'free show',
                  'talent',
                  'test talent',
                  'test event talent',
                  'unknown artist',
                  'se test',
                  'fourth of july',
                  'all new',
                  'half',
                  'couples',
                  'lovers',
                  'culture',
                  'best of',
                  'alex',
                  'blue',
                  'columbus',
                  'comedysportz',
                  'down',
                  'drag',
                  'jessica',
                  'laughs',
                  'love',
                  'paranormal',
                  'sketch',
                  'live',
                  'more',
                  'music',
                  'show',
                  'the'
              )
        )
        SELECT 
            c.uuid, c.name, c.sold_out_shows, c.total_shows, s.name as show_name
        FROM candidate_comedians c
        CROSS JOIN show_names s
        WHERE (' ' || regexp_replace(lower(s.name), '[^[:alnum:]]+', ' ', 'g') || ' ')
            LIKE '%% ' || c.normalized_name || ' %%'
        ORDER BY s.name, c.name;
    """
