WITH filtered_data AS (
	SELECT
		s.id AS id,
		s.name AS name,
		s.last_scrape_date AS scrapedate,
		s.date AS date,
		s.popularity,
		cl.name AS club_name,
		jsonb_build_object('price', s.price, 'link', s.ticket_link) AS ticket
	FROM
		shows s
		INNER JOIN clubs cl ON cl.id = s.club_id
		INNER JOIN cities ci ON cl.city_id = ci.id
    WHERE ci.id = ${city_id}
    AND s.date < ${end_date}
    AND s.date > ${start_date}
    ORDER BY ${sort:name} ASC
    LIMIT ${size} 
    OFFSET ${offset}
),
lineups AS (
	SELECT
		fd.id as show_id,
		jsonb_agg(DISTINCT jsonb_build_object('id', c.id, 'name', c.name)) AS lineup
		FROM filtered_data fd
		INNER JOIN lineup_items l ON fd.id = l.show_id
		INNER JOIN comedians c ON c.id = l.comedian_id
		GROUP BY fd.id
),
total_count AS (
	SELECT
		count(DISTINCT s.id) AS total
	FROM
		shows s
		INNER JOIN clubs cl ON cl.id = s.club_id
		INNER JOIN cities ci ON cl.city_id = ci.id
    WHERE ci.id = ${city_id}
        AND s.date < ${end_date}
        AND s.date > ${start_date}
)
SELECT
	jsonb_build_object('data', jsonb_agg(jsonb_build_object('id', fd.id, 'date', date, 'name', fd.name, 'ticket', ticket, 
	'club_name', club_name, 'scrapedate', scrapedate, 'lineup', l.lineup)), 
	'total', (
			SELECT
				total
			FROM total_count)) AS response
FROM
	filtered_data fd LEFT JOIN lineups l on fd.id = l.show_id
