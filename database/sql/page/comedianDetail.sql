with 
all_relevant_shows as (
    SELECT s.id as show_id, s.name as name FROM
		shows s
		INNER JOIN lineup_items l ON s.id = l.show_id
		INNER JOIN comedians c ON c.uuid = l.comedian_id
	WHERE
    s.date > now()
	AND c.name = $(slug)
    ORDER BY ${sort:name} ${direction:value}
    LIMIT ${size} 
    OFFSET ${offset}
), 
relevant_show_ids AS (
	SELECT
		show_id
	FROM
		all_relevant_shows
),
show_data AS (
	SELECT
		s.id AS show_id,
		s.name AS show_name,
		s.date AS show_date,
		s.last_scraped_date AS scrapedate,
		jsonb_build_object('price', s.price, 'link', s.ticket_link) AS ticket,
	    jsonb_agg(DISTINCT jsonb_build_object('id', c.id, 'name', c.name)) AS lineup,
	    cl.name AS club_name
FROM
	relevant_show_ids rsi
	JOIN shows s ON rsi.show_id = s.id
	INNER JOIN lineup_items l ON s.id = l.show_id
	INNER JOIN comedians c ON c.uuid = l.comedian_id
	INNER JOIN clubs cl ON s.club_id = cl.id
GROUP BY
	s.id,
	cl.name
ORDER BY ${sort:name} ${direction:value}
),
formatted_query AS (
	SELECT
		COALESCE(jsonb_agg(jsonb_build_object('id', sd.show_id, 'date', sd.show_date, 'name', sd.show_name, 'ticket', sd.ticket, 'club_name', club_name, 'scrapedate', scrapedate, 'lineup', sd.lineup)) FILTER (WHERE sd.show_id IS NOT NULL), '[]') AS shows
FROM
	show_data sd
),
total_count AS (
SELECT
		count(DISTINCT show_id) AS total
	FROM all_relevant_shows
),
comedian_data AS (
	SELECT
		*
	FROM
		comedians
	WHERE
		name = $(slug))
SELECT
	jsonb_build_object(
        'data', jsonb_build_object('name', (SELECT name FROM comedian_data),
        'social_data', (
			SELECT
				jsonb_build_object(
                'instagram_account', instagram_account, 'instagram_followers', 
                instagram_followers, 'tiktok_account', tiktok_account, 
                'tiktok_followers', tiktok_followers, 'youtube_account', 
                youtube_account, 'youtube_followers', youtube_followers,
                'website', website, 'popularity', popularity)
			FROM comedian_data), 
    'dates', fq.shows), 
    'total', (
		SELECT
			total
		FROM total_count)) AS response
FROM
	formatted_query fq
GROUP BY
	fq.shows
