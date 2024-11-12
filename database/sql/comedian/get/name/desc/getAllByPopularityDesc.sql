with filtered_data as (
    SELECT
        s.id as id,
        jsonb_build_object(
            'price',
            s.price,
            'link',
            s.ticket_link
        ) as ticket,
        s.name,
        c.*,
        array_agg(c.name) as lineup_names,
        s.last_scrape_date as scrapedate,
        cl.name as club_name,
		s.date,
        jsonb_agg(
            DISTINCT jsonb_build_object(
                'id',
                c.id,
                'name',
                c.name
            )
        ) as lineup
    FROM
        shows s
        INNER JOIN lineup_items l ON s.id = l.show_id
        INNER JOIN comedians c ON c.id = l.comedian_id
        INNER JOIN clubs cl ON cl.id = s.club_id
        INNER JOIN cities ci on cl.city_id = ci.id 
    WHERE
        ${name} = ANY(lineup_names) 
        AND s.date < ${end_date}
        AND s.date > ${start_date}
    GROUP BY
        s.id,
        club_name
    ORDER BY popularity_score DESC
    LIMIT ${rows} 
    OFFSET ${offset}
),
total_count as (
    SELECT
        COUNT(s.id) AS total
    FROM
        shows s
        INNER JOIN clubs cl ON cl.id = s.club_id
        INNER JOIN cities ci on cl.city_id = ci.id
    WHERE
        ${name} = ANY(lineup_names) 
        AND s.date < ${end_date}
        AND s.date > ${start_date}
)
SELECT
    JSONB_BUILD_OBJECT(
        'data',
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                'id',
                id,
                'ticket',
                ticket,
                'name',
                name,
                'club_name',
                club_name,
                'date',
                date,
                'lineup',
                lineup
            )
        ),
        'total',
        (
            SELECT
                total
            FROM
                total_count
        )
    ) as response
FROM
    filtered_data
