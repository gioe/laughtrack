WITH venues AS (
    SELECT
        c.name AS club_name,
        COUNT(DISTINCT ls.comedian_id) AS comedian_count
    FROM clubs c
    JOIN shows s ON s.club_id = c.id
    JOIN lineup_items ls ON ls.show_id = s.id
    WHERE s.date BETWEEN CURRENT_DATE AND (CURRENT_DATE + INTERVAL '30' DAY)
    GROUP BY c.name
    ORDER BY comedian_count DESC
    LIMIT 6
),
active_comedians AS (
    SELECT
        c.id,
        c.uuid,
        c.name,
        COUNT(DISTINCT li.id) AS show_count,
        jsonb_build_object(
            'instagram_account', c.instagram_account,
            'instagram_followers', c.instagram_followers,
            'tiktok_account', c.tiktok_account,
            'tiktok_followers', c.tiktok_followers,
            'youtube_account', c.youtube_account,
            'youtube_followers', c.youtube_followers,
            'website', c.website,
            'popularity', c.popularity,
            'linktree', c.linktree
        ) AS social_data,
        CASE 
            WHEN ${userId} IS NULL THEN false
            ELSE EXISTS (
                SELECT 1 
                FROM favorite_comedians fc 
                WHERE fc.comedian_id = c.uuid 
                AND fc.user_id = ${userId}
            )
        END AS is_favorite,
		        CASE 
            WHEN ${userId} IS NULL THEN false
            ELSE EXISTS (
                SELECT 1 
                FROM favorite_comedians fc 
                WHERE fc.comedian_id = c.uuid 
                AND fc.user_id = ${userId}
            )
        END AS is_favorite
    FROM comedians c
    JOIN lineup_items li ON li.comedian_id = c.uuid
    JOIN shows s ON li.show_id = s.id
    WHERE s.date > NOW()
    GROUP BY c.id, c.uuid, c.name
    HAVING COUNT(DISTINCT li.id) > 3
    ORDER BY RANDOM()
    LIMIT 10
)
SELECT jsonb_build_object(
    'comedians', (
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', id,
                'uuid', uuid,
                'name', name,
                'social_data', social_data,
                'is_favorite', is_favorite,
                'show_count', show_count
            )
        )
        FROM active_comedians
    ),
    'cities', (
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', id,
                'name', name
            )
        )
        FROM cities
    ),
    'clubs', (
        SELECT jsonb_agg(
            jsonb_build_object(
                'name', club_name,
                'count', comedian_count
            )
        )
        FROM venues
    )
) AS response;
