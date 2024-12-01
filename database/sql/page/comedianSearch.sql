with filtered_data as (
    SELECT
        c.id, 
		name, 
		jsonb_build_object(
            'linktree', linktree,
            'instagram_account',
            instagram_account,
            'instagram_followers',
            instagram_followers,
            'tiktok_account',
            tiktok_account,
            'tiktok_followers',
            tiktok_followers,
            'youtube_account',
            youtube_account,
            'youtube_followers',
            youtube_followers,
            'website',
            website,
            'popularity',
            popularity
        ) AS social_data
	FROM
		comedians c
		LEFT JOIN tagged_comedians tc ON c.id = tc.comedian_id
		LEFT JOIN tags t ON tc.tag_id = t.id
    Where name ILIKE ${query}
    AND (${tagsEmpty} = TRUE) OR (t.value IN (${tags:csv}))
    ORDER BY ${sort_by:name} ${direction:value}
    LIMIT ${size} 
    OFFSET ${offset}
),
total_count as (
    SELECT
        COUNT(c.id) AS total
	FROM
		comedians c
		LEFT JOIN tagged_comedians tc ON c.id = tc.comedian_id
		LEFT JOIN tags t ON tc.tag_id = t.id
    Where name ILIKE ${query}
    AND (${tagsEmpty} = TRUE) OR (t.value IN (${tags:csv}))
)
SELECT
    JSONB_BUILD_OBJECT(
        'data',
        COALESCE(jsonb_agg(JSONB_BUILD_OBJECT(
                'id',
                id, 
                'name', name,
                'social_data', social_data
            )) FILTER (where id IS NOT NULL), '[]'),
        'total',
        (
            SELECT
                total
            FROM
                total_count
        )
    ) as response
FROM
    filtered_data
