WITH filtered_shows AS (
    SELECT DISTINCT
        s.id,
        s.name,
        s.date,
        s.last_scraped_date AS scrape_date,
        s.popularity,
        cl.name AS club_name,
        jsonb_build_object(
            'price', s.ticket_price,
            'link', s.ticket_purchase_url
        ) AS ticket
    FROM shows s
    INNER JOIN clubs cl ON cl.id = s.club_id
    INNER JOIN cities ci ON cl.city_id = ci.id
    LEFT JOIN tagged_shows ts ON s.id = ts.show_id
    LEFT JOIN tags t ON ts.tag_id = t.id
    WHERE ci.name = ${city}
        AND s.date BETWEEN ${from_date} AND ${to_date}
        AND (${tagsEmpty} = TRUE OR t.value IN (${tags:csv}))
    ORDER BY ${sort_by:name} ${direction:value}
    LIMIT ${size} 
    OFFSET ${offset}
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
total_results AS (
    SELECT COUNT(DISTINCT s.id) AS total
    FROM shows s
    INNER JOIN clubs cl ON cl.id = s.club_id
    INNER JOIN cities ci ON cl.city_id = ci.id
    LEFT JOIN tagged_shows ts ON s.id = ts.show_id
    LEFT JOIN tags t ON ts.tag_id = t.id
    WHERE ci.name = ${city}
        AND s.date BETWEEN ${from_date} AND ${to_date}
        AND (${tagsEmpty} = TRUE OR t.value IN (${tags:csv}))
)
SELECT jsonb_build_object(
    'data', COALESCE(
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
        ) FILTER (WHERE fs.id IS NOT NULL),
        '[]'
    ),
    'total', (SELECT total FROM total_results)
) AS response
FROM filtered_shows fs
LEFT JOIN show_lineups sl ON fs.id = sl.show_id;
