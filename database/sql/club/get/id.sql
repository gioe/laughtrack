with shows_with_lineups as (
    SELECT
        s.id,
        club_id,
        s.name,
        jsonb_build_object(
            'price', 
            s.price,
            'link',
            s.ticket_link
        ) as ticket,
        s.date_time,
        COALESCE(jsonb_agg(
            DISTINCT jsonb_build_object(
                'id',
                c.id,
                'name',
                c.name
            ))FILTER (WHERE c.id IS NOT NULL), '[]') as lineup
    FROM
        shows s
        LEFT JOIN lineup_items l ON s.id = l.show_id
        LEFT JOIN comedians c ON c.id = l.comedian_id
        LEFT JOIN clubs cl ON cl.id = s.club_id
    WHERE date_time > NOW()
    GROUP BY
        s.id
    ORDER BY
        ${order_clause}
    LIMIT ${size}
)
SELECT
     c.id,
     c.name,
        jsonb_build_object( 
                        'id',
            c.id,
            'website',
            c.base_url
        ) as social_data,
            COALESCE(jsonb_agg(
                DISTINCT jsonb_build_object(
            'id',
            swl.id,
            'date_time',
            swl.date_time,
            'name',
            swl.name,
            'ticket',
            swl.ticket,
            'lineup',
            swl.lineup
        )) FILTER (WHERE swl.id IS NOT NULL), '[]') as dates
from
    clubs c
LEFT JOIN shows_with_lineups swl ON c.id = swl.club_id
WHERE
    c.id  = ${id}
GROUP BY
    c.id, c.name
