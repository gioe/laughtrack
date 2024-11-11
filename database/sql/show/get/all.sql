with complete_shows as (
    SELECT
        s.id as id,
        jsonb_build_object(
                'price',
                s.price,
                'link',
                s.ticket_link
            ) as ticket,
        s.name,
        cl.name as club_name,
        s.date_time as date_time,
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
    ci.id = ${city_id} AND  s.date_time < ${end_date}
        AND s.date_time > ${start_date}
    GROUP BY
        s.id,
        club_name
    ORDER BY
        s.date_time ASC
)
SELECT
*
from
    complete_shows cs
LIMIT ${rows}
OFFSET ${offset}

