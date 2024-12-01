SELECT
	c.name,
	c.id,
	jsonb_build_object('instagram_account', instagram_account, 'instagram_followers', instagram_followers, 'tiktok_account', tiktok_account, 'tiktok_followers', tiktok_followers, 'youtube_account', youtube_account, 'youtube_followers', youtube_followers, 'website', website, 'popularity', popularity) AS social_data,
	COALESCE(jsonb_agg(tc.id) FILTER (WHERE tc.id IS NOT NULL), '[]') AS tags
FROM
	comedians c
	LEFT JOIN tagged_comedians tc ON c.id = tc.comedian_id
WHERE
	name = ${name}
GROUP BY
	c.name,
	c.id
