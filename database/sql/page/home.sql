WITH all_cities AS (
	SELECT
		*
	FROM
		cities
),
comedian_dict as (
SELECT
	c.id,
	c.name, 
	jsonb_build_object('instagram_account', c.instagram_account, 'instagram_followers', c.instagram_followers, 'tiktok_account', c.tiktok_account, 'tiktok_followers',
	c.tiktok_followers, 'youtube_account', c.youtube_account, 'youtube_followers', c.youtube_followers, 
	'website', c.website, 'popularity', c.popularity, 'linktree', c.linktree) AS social_data,
	count (distinct li.id) as show_count 
	FROM comedians c
	JOIN lineup_items li ON li.comedian_id = c.uuid
	JOIN shows s ON li.show_id = s.id
	WHERE s.date > NOW()
	GROUP BY c.id
),
trending_comedians AS (
	SELECT id, name, show_count, social_data from comedian_dict where show_count > 3 ORDER BY
	random()
LIMIT 10
)
SELECT
	jsonb_build_object('comedians', jsonb_agg(jsonb_build_object('id', tc.id, 'name', tc.name, 'social_data', tc.social_data, 'show_count', tc.show_count)), 'cities', (
			SELECT
				jsonb_agg(json_build_object('id', id, 'name', name))
			FROM all_cities)) AS response
FROM
	trending_comedians tc
