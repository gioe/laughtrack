WITH all_cities AS (
	SELECT
		*
	FROM
		cities
),
comedian_dict as (
SELECT
	c.id,
	c.uuid,
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
	SELECT id, uuid, name, show_count, social_data from comedian_dict where show_count > 3 ORDER BY
	random()
LIMIT 10
),
trending_clubs AS (
	SELECT c.name, count (distinct comedian_id) from lineup_items ls JOIN shows s ON ls.show_id = s.id JOIN clubs c on s.club_id = c.id where s.date BETWEEN CURRENT_DATE AND (CURRENT_DATE + INTERVAL '30' DAY) GROUP BY c.name ORDER BY 2 DESC LIMIT 6
)
SELECT
	jsonb_build_object('comedians', jsonb_agg(jsonb_build_object('id', tc.id, 'uuid', tc.uuid, 'name', tc.name, 'social_data', tc.social_data, 'show_count', tc.show_count)), 'cities', (
			SELECT
				jsonb_agg(json_build_object('id', id, 'name', name))
			FROM all_cities), 'clubs', (SELECT jsonb_agg(jsonb_build_object('name', tc.name, 'count', tc.count)) FROM trending_clubs tc)) AS response
FROM
	trending_comedians tc
