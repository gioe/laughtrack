"""SQL queries for tag operations."""


class TagQueries:
    """SQL queries for tag operations."""
    
    GET_TAGS_FOR_SHOWS = """
        SELECT 
            st.show_id, t.slug
        FROM tagged_shows st
        JOIN tags t ON st.tag_id = t.id
        WHERE st.show_id = ANY(%s)
        AND t.visibility = 'ADMIN'
        ORDER BY st.show_id;
    """
    
    BATCH_GET_TAGS_FROM_SHOW_NAME = '''
        WITH show_names AS (
            SELECT unnest(%s::text[]) as show_name
        )
        SELECT t.id, sn.show_name 
        FROM tags t
        CROSS JOIN show_names sn
        WHERE t.type = 'show'
        AND (
            -- Exact match
            sn.show_name ILIKE t.slug
            -- Word boundary match
            OR sn.show_name ~* ('\\y' || t.slug || '\\y')
        );
    '''
    
    BATCH_ADD_TAGS = '''
        INSERT INTO tags (type, slug) 
        VALUES %s 
        ON CONFLICT (type, slug)       
        DO UPDATE SET 
            type = EXCLUDED.type,
            slug = EXCLUDED.slug
        RETURNING id, slug
    '''
    
    ADD_TAGS_TO_SHOW = '''
        INSERT INTO tagged_shows (show_id, tag_id) 
        VALUES %s 
        ON CONFLICT DO NOTHING
    '''
