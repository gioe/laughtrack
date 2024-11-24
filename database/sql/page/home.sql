WITH all_cities AS (
	SELECT
		*
	FROM
		cities
),
trending_comedians AS (
	SELECT
		id,
		name,
		jsonb_build_object('instagram_account', instagram_account, 'instagram_followers', instagram_followers, 'tiktok_account', tiktok_account, 'tiktok_followers', tiktok_followers, 'youtube_account', youtube_account, 'youtube_followers', youtube_followers, 'website', website, 'popularity', popularity) AS social_data
FROM
	comedians
ORDER BY
	random()
LIMIT 10
)
SELECT
	jsonb_build_object('comedians', jsonb_agg(jsonb_build_object('id', tc.id, 'name', tc.name, 'social_data', social_data)), 'cities', (
			SELECT
				jsonb_agg(json_build_object('id', id, 'name', name))
			FROM all_cities)) AS response
FROM
	trending_comedians tc
