WITH filtered_data AS (
	SELECT
		s.id AS id,
		s.name AS name,
		s.last_scrape_date AS scrapedate,
		s.date AS date,
		s.popularity,
		cl.name AS club_name,
		cl.website as club_website,
		jsonb_build_object('price', s.price, 'link', s.ticket_link) AS ticket
	FROM shows s
	INNER JOIN clubs cl ON cl.id = s.club_id
    WHERE cl.name = ${slug}
    AND s.date > NOW()
    ORDER BY ${sort:name} ASC
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
	INNER JOIN comedians c ON c.id = l.comedian_id
	GROUP BY fd.id
),
total_count AS (
	SELECT
		count(DISTINCT s.id) AS total
	FROM 
		shows s
	INNER JOIN clubs cl ON cl.id = s.club_id
    WHERE cl.name = ${slug}
    AND s.date > NOW()
), 
all_values as (
	SELECT club_name,
		club_website,
		jsonb_agg(jsonb_build_object('id', fd.id, 'date', date, 'name', fd.name, 'ticket', ticket, 'club_name', club_name, 'scrapedate', scrapedate, 'lineup', l.lineup)) as shows
	FROM
		filtered_data fd 
	LEFT JOIN lineups l on fd.id = l.show_id GROUP BY club_name, club_website
)
SELECT
	jsonb_build_object('data', jsonb_build_object('name', av.club_name, 'website', av.club_website, 'dates', av.shows), 'total', (
			SELECT
				total
			FROM total_count)
			) AS response
FROM
	all_values av GROUP BY av.club_name, av.club_website, av.shows


