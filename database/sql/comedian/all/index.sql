with filtered_data as (
    SELECT
        id, 
		name, 
		jsonb_build_object(
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
    from
        comedians
    Where name ILIKE ${query}
    ORDER BY ${sort:name} ${direction:value}
    LIMIT ${size} 
    OFFSET ${offset}
),
total_count as (
    SELECT
        COUNT(c.id) AS total
    FROM
        comedians c
)
SELECT
    JSONB_BUILD_OBJECT(
        'data',
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                'id',
                id, 
                'name', name,
                'social_data', social_data
            )
        ),
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
