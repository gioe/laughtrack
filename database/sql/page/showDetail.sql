WITH final_query AS (
	SELECT
		s.id AS show_id,
		s.name AS show_name,
		s.date,
		jsonb_build_object('price', s.price, 'link', s.ticket_link) AS ticket,
		s.last_scrape_date AS scrapedate,
		COALESCE(jsonb_agg(DISTINCT jsonb_build_object('id', c.id, 'name', c.name, 'social_data', jsonb_build_object('instagram_account', instagram_account, 'instagram_followers', instagram_followers, 'tiktok_account', tiktok_account, 'tiktok_followers', tiktok_followers, 'youtube_account', youtube_account, 'youtube_followers', youtube_followers, 'website', website, 'popularity', c.popularity))) FILTER (WHERE c.id IS NOT NULL), '[]') AS lineup
	FROM
		shows s
		LEFT JOIN lineup_items l ON s.id = l.show_id
		LEFT JOIN comedians c ON c.id = l.comedian_id
	WHERE s.id = ${slug}
	GROUP BY
		s.id
),
total_count AS (
	SELECT
		count(DISTINCT l.comedian_id) AS total
	FROM
		shows s
		INNER JOIN lineup_items l ON s.id = l.show_id
		INNER JOIN comedians c ON c.id = l.comedian_id
	WHERE
		l.show_id = ${slug}
)
SELECT
	jsonb_build_object('data', jsonb_build_object('id', fq.show_id, 'date', date, 'name', fq.show_name, 'ticket', fq.ticket, 'scrapedate', fq.scrapedate, 'lineup', fq.lineup), 'total', (
			SELECT
				total
			FROM total_count)) AS response
FROM
	final_query fq
