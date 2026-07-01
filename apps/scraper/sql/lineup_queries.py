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
                COALESCE(parent.uuid, c.uuid) AS uuid,
                COALESCE(parent.name, c.name) AS name,
                COALESCE(parent.sold_out_shows, c.sold_out_shows) AS sold_out_shows,
                COALESCE(parent.total_shows, c.total_shows) AS total_shows,
                COALESCE(parent.visible, c.visible) AS visible,
                COALESCE(parent.instagram_followers, c.instagram_followers) AS instagram_followers,
                COALESCE(parent.tiktok_followers, c.tiktok_followers) AS tiktok_followers,
                COALESCE(parent.youtube_followers, c.youtube_followers) AS youtube_followers,
                COALESCE(parent.instagram_account, c.instagram_account) AS instagram_account,
                COALESCE(parent.tiktok_account, c.tiktok_account) AS tiktok_account,
                COALESCE(parent.youtube_account, c.youtube_account) AS youtube_account,
                COALESCE(parent.website, c.website) AS website,
                COALESCE(parent.linktree, c.linktree) AS linktree,
                CASE
                    WHEN parent.id IS NOT NULL THEN parent.parent_comedian_id
                    ELSE c.parent_comedian_id
                END AS parent_comedian_id,
                COALESCE(parent.website_discovery_source, c.website_discovery_source) AS website_discovery_source,
                COALESCE(parent.website_last_scraped, c.website_last_scraped) AS website_last_scraped,
                COALESCE(parent.website_scrape_strategy, c.website_scrape_strategy) AS website_scrape_strategy,
                COALESCE(parent.home_city, c.home_city) AS home_city,
                COALESCE(parent.home_state, c.home_state) AS home_state,
                COALESCE(parent.home_country, c.home_country) AS home_country,
                COALESCE(parent.home_club_id, c.home_club_id) AS home_club_id,
                COALESCE(parent.has_image, c.has_image) AS has_image,
                c.name AS match_name,
                trim(regexp_replace(lower(c.name), '[^[:alnum:]]+', ' ', 'g')) as normalized_name
            FROM comedians c
            LEFT JOIN comedians parent ON parent.id = c.parent_comedian_id
            WHERE c.name IS NOT NULL
              AND (
                  array_length(regexp_split_to_array(trim(c.name), '[[:space:]]+'), 1) >= 2
                  OR trim(c.name) ~ '[[:alpha:]][[:alpha:]''’]*[-''’][[:alpha:]''’]*'
                  OR (
                      COALESCE(parent.visible, c.visible) = TRUE
                      AND (
                          COALESCE(parent.total_shows, c.total_shows) >= 5
                          OR COALESCE(parent.instagram_followers, c.instagram_followers) IS NOT NULL
                          OR COALESCE(parent.tiktok_followers, c.tiktok_followers) IS NOT NULL
                          OR COALESCE(parent.youtube_followers, c.youtube_followers) IS NOT NULL
                      )
                  )
              )
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
            c.uuid, c.name, c.sold_out_shows, c.total_shows,
            c.visible, c.instagram_followers, c.tiktok_followers, c.youtube_followers,
            c.instagram_account, c.tiktok_account, c.youtube_account,
            c.website, c.linktree, c.parent_comedian_id,
            c.website_discovery_source, c.website_last_scraped, c.website_scrape_strategy,
            c.home_city, c.home_state, c.home_country, c.home_club_id, c.has_image,
            c.match_name,
            s.name as show_name
        FROM candidate_comedians c
        CROSS JOIN show_names s
        WHERE (' ' || regexp_replace(lower(s.name), '[^[:alnum:]]+', ' ', 'g') || ' ')
            LIKE '%% ' || c.normalized_name || ' %%'
        ORDER BY s.name, c.name;
    """
