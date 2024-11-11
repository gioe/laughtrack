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
            c.website
        ) as social_data,
            COALESCE(jsonb_agg(
                DISTINCT jsonb_build_object(
            'id',
            fld.id,
            'date_time',
            fld.date_time,
            'name',
            fld.name,
            'social_data',
            fld.social_data,
            'price',
            fld.price,
            'ticket_link', 
            fld.ticket_link,
            'lineup',
            fld.lineup
        )) FILTER (WHERE fld.id IS NOT NULL), '[]') as dates
from
    clubs c
LEFT JOIN full_lineup_data fld ON c.id = fld.club_id
WHERE
    c.name  = ${name}
GROUP BY
    c.id, c.name
