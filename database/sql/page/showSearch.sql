WITH filtered_data AS (
	SELECT
		s.id AS id,
		s.name AS name,
		s.last_scraped_date AS scrapedate,
		s.date AS date,
		s.popularity,
		cl.name AS club_name,
		jsonb_build_object('price', s.price, 'link', s.ticket_link) AS ticket
	FROM
		shows s
		LEFT JOIN tagged_shows ts ON s.id = ts.show_id
		LEFT JOIN tags t ON ts.tag_id = t.id
		INNER JOIN clubs cl ON cl.id = s.club_id
		INNER JOIN cities ci ON cl.city_id = ci.id
    WHERE ci.name = ${city}
    AND s.date < ${to_date}
    AND s.date > ${from_date}
	AND (${tagsEmpty} = TRUE) OR (t.value IN (${tags:csv}))
    ORDER BY ${sort_by:name} ${direction:value}
    LIMIT ${size} 
    OFFSET ${offset}
),
lineups AS (
	SELECT
		fd.id as show_id,
		jsonb_agg(DISTINCT jsonb_build_object('id', c.id, 'name', c.name)) AS lineup
		FROM filtered_data fd
		INNER JOIN lineup_items l ON fd.id = l.show_id
		INNER JOIN comedians c ON c.uuid = l.comedian_id
		GROUP BY fd.id
),
total_count AS (
	SELECT
		count(DISTINCT s.id) AS total
	FROM
		shows s
		LEFT JOIN tagged_shows ts ON s.id = ts.show_id
		LEFT JOIN tags t ON ts.tag_id = t.id
		INNER JOIN clubs cl ON cl.id = s.club_id
		INNER JOIN cities ci ON cl.city_id = ci.id
    WHERE ci.name = ${city}
        AND s.date < ${to_date}
        AND s.date > ${from_date}
	AND (${tagsEmpty} = TRUE) OR (t.value IN (${tags:csv}))
)
SELECT
	jsonb_build_object('data', COALESCE(jsonb_agg(jsonb_build_object('id', fd.id, 'date', date, 'name', fd.name, 'ticket', ticket, 'club_name', club_name, 'scrapedate', scrapedate, 'lineup', l.lineup)) FILTER (WHERE fd.id IS NOT NULL), '[]'), 'total', (
			SELECT
				total
			FROM total_count)) AS response
FROM
	filtered_data fd
	LEFT JOIN lineups l ON fd.id = l.show_id
