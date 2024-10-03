WITH lineups as (
    SELECT
        s.id,
        s.date_time,
        s.ticket_link,
        club_id,
        array_agg(c.name) as lineup_names,
        jsonb_agg(
            DISTINCT jsonb_build_object(
                'id',
                c.id,
                'name',
                c.name,
                'popularity_score',
                c.popularity_score
            )
        ) as lineup_details
    FROM
        shows s
        INNER JOIN lineups l ON s.id = sc.show_id
        INNER JOIN comedians c ON c.id = sc.comedian_id
    GROUP BY
        s.id
),
full_data as (
    SELECT
        cl.id as club_id,
        cl.name as club_name,
        l.id as show_id,
        lineup_details as lineup_details,
        date_time,
        ticket_link,
        city,
        longitude,
        latitude
    FROM
        lineups l
        INNER JOIN lineups l ON l.id = sc.show_id
        INNER JOIN comedians c ON c.id = sc.comedian_id
        INNER JOIN clubs cl ON cl.id = l.club_id
)
SELECT
    f.club_id as id,
    f.club_name as name,
    f.city,
    f.longitude,
    f.latitude,
    jsonb_agg(
        DISTINCT jsonb_build_object(
            'show_id',
            f.show_id,
            'lineup',
            f.lineup_details,
            'city',
            f.city,
            'club_name',
            f.club_name,
            'date_time',
            f.date_time,
            'ticket_link',
            f.ticket_link
        )
    ) as dates 
from
    full_data f
WHERE
    club_name = ${name} and f.date_time > NOW()
GROUP BY
    f.club_id,
    f.club_name,
    f.city,
    f.longitude,
    f.latitude