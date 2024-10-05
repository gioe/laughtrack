WITH future_shows_with_lineup as (
SELECT
    s.id,
    s.club_id as club_id,
    s.date_time,
    s.ticket_link,
    s.popularity_score,
    jsonb_agg(
        jsonb_build_object(
            'id',
            c.id,
            'name',
            c.name,
            'popularity_score',
            c.popularity_score
        )
    ) AS lineup
from shows s
inner join lineups l on s.id = l.show_id
inner join comedians c on c.id = l.comedian_id
WHERE date_time > NOW()
GROUP BY
    s.id,
    s.date_time 
ORDER BY s.date_time ASC
)
SELECT
    c.id,
    c.name,
     COALESCE(
    jsonb_agg(
        jsonb_build_object(
            'id',
            fs.id,
            'date_time',
            fs.date_time,
            'ticket_link',
            fs.ticket_link,
            'popularity_score',
            fs.popularity_score,
            'club_id',
            c.id, 
            'lineup',
            fs.lineup
        )
    ) FILTER (WHERE fs.id IS NOT NULL), '[]') AS shows
from
    clubs c
    left join future_shows_with_lineup fs on fs.club_id = c.id
WHERE
    c.name = ${name}
GROUP BY
    c.id,
    c.name