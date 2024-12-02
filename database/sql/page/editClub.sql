SELECT
	c.name,
	c.id,
	jsonb_build_object('website', c.website) as social_data
FROM
	clubs c
	LEFT JOIN tagged_clubs tc ON c.id = tc.club_id
WHERE
	name = ${name}
GROUP BY
	c.name,
	c.id
