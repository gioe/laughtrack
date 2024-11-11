with filtered_data as (
    SELECT
        *
    from
        comedians
    ORDER BY
        popularity_score ASC
    LIMIT
        ${rows} OFFSET ${offset}
),
total_count as (
    SELECT
        COUNT(c.id) AS total
    FROM
        comedians c
)
SELECT
	jsonb_build_object('data', jsonb_agg(jsonb_build_object('id', id, 'name', name, 'social_data', jsonb_build_object('instagram_account', instagram_account, 'instagram_followers', instagram_followers, 'tiktok_account', tiktok_account, 'tiktok_followers', tiktok_followers, 'youtube_account', youtube_account, 'youtube_followers', youtube_followers, 'website', website, 'popularity_score', popularity_score))), 'total', (
	SELECT
		total
	FROM total_count)) AS response
FROM
    filtered_data
