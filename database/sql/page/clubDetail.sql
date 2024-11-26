WITH filtered_data AS (
	SELECT
		s.id AS id,
		s.name AS name,
		s.last_scraped_date AS scrapedate,
		s.date AS date,
		s.popularity,
		cl.id as club_id,
		cl.name AS club_name,
		cl.website as club_website,
		jsonb_build_object('price', s.price, 'link', s.ticket_link) AS ticket
	FROM
		shows s
		LEFT JOIN tagged_shows ts ON s.id = ts.show_id
		LEFT JOIN tags t ON ts.tag_id = t.id
		INNER JOIN clubs cl ON cl.id = s.club_id
	WHERE
		cl.name = ${name}
		AND s.date > now()
		AND t.name IN (${tags:csv})
    ORDER BY ${sort_by:name} ${direction:value}
    LIMIT ${size} 
    OFFSET ${offset}
),
lineups AS (
	SELECT
		fd.id as show_id,
		jsonb_agg(DISTINCT jsonb_build_object('id', c.id, 'name', c.name)) AS lineup
	FROM 
		filtered_data fd
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
	WHERE
		cl.name = ${name}
		AND s.date > now()
		AND t.id IN (${tags:csv})
    WHERE cl.name = ${name}
    AND s.date > NOW()
), 
all_values AS (
	SELECT
		c.id as club_id,
		c.name as club_name,
		c.website as club_website,
		COALESCE(jsonb_agg(jsonb_build_object('id', fd.id, 'date', date, 'name', fd.name, 'ticket', ticket, 'club_name', club_name, 'scrapedate', scrapedate, 'lineup', l.lineup)) FILTER (where fd.id IS NOT NULL), '[]') AS shows
	FROM
	    clubs c
	    LEFT JOIN filtered_data fd ON fd.club_id = c.id
		LEFT JOIN lineups l ON fd.id = l.show_id
    WHERE c.name = ${name}
	GROUP BY
		c.name,
		c.website,
		c.id
)
SELECT
	jsonb_build_object('data', jsonb_build_object('name', av.club_name, 'id', av.club_id, 'website', av.club_website, 'dates', av.shows), 'total', (
			SELECT
				total
			FROM total_count)) AS response
FROM
	all_values av
GROUP BY
	av.club_name,
	av.club_website,
	av.shows,
	av.club_id

