SELECT
	c.name,
	c.id,
	jsonb_build_object('website', c.website) as social_data,
	count (distinct s) as show_count
FROM
	clubs c
	LEFT JOIN tagged_clubs tc ON c.id = tc.club_id
	LEFT JOIN shows s on c.id = s.club_id
WHERE
	c.name = ${name}
GROUP BY
	c.name,
	c.id
