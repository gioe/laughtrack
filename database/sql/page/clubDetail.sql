WITH filtered_shows AS (
    SELECT DISTINCT
        s.id,
        s.name,
        s.last_scraped_date AS scrape_date,
        s.date,
        s.popularity,
        cl.id AS club_id,
        cl.name AS club_name,
        cl.website AS club_website,
        jsonb_build_object(
            'price', s.ticket_price,
            'link', s.ticket_purchase_url
        ) AS ticket
    FROM shows s
    INNER JOIN clubs cl ON cl.id = s.club_id
    LEFT JOIN tagged_shows ts ON s.id = ts.show_id
    LEFT JOIN tags t ON ts.tag_id = t.id
    WHERE cl.name = 'Comedy Cellar New York'
        AND s.date > NOW()
        AND (${tagsEmpty} = TRUE OR t.value IN (${tags:csv}))
    ORDER BY date ASC 
    LIMIT 10 OFFSET 0
),
show_lineups AS (
    SELECT 
        fs.id AS show_id,
        jsonb_agg(DISTINCT jsonb_build_object(
            'id', c.id,
            'name', c.name,
            'is_favorite', CASE 
                WHEN ${userId} IS NULL THEN false
                ELSE EXISTS (
                    SELECT 1 
                    FROM favorite_comedians fc 
                    WHERE fc.comedian_id = c.uuid 
                    AND fc.user_id = ${userId}
                )
            END,
            'is_alias', EXISTS (
                SELECT 1
                FROM tagged_comedians tc
                JOIN tags t ON t.id = tc.tag_id
                WHERE tc.comedian_id = c.uuid
                AND t.value = 'alias'
            )
        )) AS lineup
    FROM filtered_shows fs
    INNER JOIN lineup_items l ON fs.id = l.show_id
    INNER JOIN comedians c ON c.uuid = l.comedian_id
    GROUP BY fs.id
),
total_count AS (
    SELECT COUNT(DISTINCT s.id) AS total
    FROM shows s
    INNER JOIN clubs cl ON cl.id = s.club_id
    LEFT JOIN tagged_shows ts ON s.id = ts.show_id
    LEFT JOIN tags t ON ts.tag_id = t.id
    WHERE cl.name = 'Comedy Cellar New York'
        AND s.date > NOW()
        AND (${tagsEmpty} = TRUE OR t.value IN (${tags:csv}))
),
club_shows AS (
    SELECT
        c.id AS club_id,
        c.name AS club_name,
        c.website AS club_website,
        COALESCE(
            jsonb_agg(
                jsonb_build_object(
                    'id', fs.id,
                    'date', fs.date,
                    'name', fs.name,
                    'ticket', fs.ticket,
                    'club_name', fs.club_name,
                    'scrapedate', fs.scrape_date,
                    'lineup', sl.lineup
                )
                ORDER BY fs.date ASC
            ) FILTER (WHERE fs.id IS NOT NULL),
            '[]'
        ) AS shows
    FROM clubs c
    LEFT JOIN filtered_shows fs ON fs.club_id = c.id
    LEFT JOIN show_lineups sl ON fs.id = sl.show_id
    WHERE c.name = 'Comedy Cellar New York'
    GROUP BY c.id, c.name, c.website
)
SELECT jsonb_build_object(
    'data', jsonb_build_object(
        'name', cs.club_name,
        'id', cs.club_id,
        'website', cs.club_website,
        'dates', cs.shows
    ),
    'total', (SELECT total FROM total_count)
) AS response
FROM club_shows cs;
