with filtered_data as (
    SELECT
        cl.name as club_name,
        cl.id as club_id,
        s.id as show_id,
        s.popularity_score,
        s.date as show_date,
        jsonb_build_object(
            'price',
            s.price,
            'link',
            s.ticket_link
        ) as ticket,
        s.name as show_name,
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
        WHERE cl.name = ${name}
        AND date > now()
    GROUP BY
        s.id,
        club_name, cl.id
    ORDER BY popularity_score ASC
   LIMIT ${rows} 
   OFFSET ${offset}
),
total_count as (
    SELECT
        COUNT(s.id) AS total
    FROM
        shows s
        JOIN clubs c on s.club_id = c.id
        WHERE c.name = ${name}
        AND date > now()
)
SELECT
    JSONB_BUILD_OBJECT(
        'data',
            JSONB_BUILD_OBJECT(
                'id', 
                club_id,
                'name',
                club_name,
                'dates',
                JSONB_AGG(
            JSONB_BUILD_OBJECT(
                'id',
                show_id,
                'ticket',
                ticket,
                'name',
                show_name,
                'date',
                show_date,
                'lineup',
                lineup
            )
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
    filtered_data GROUP BY club_name, club_id
