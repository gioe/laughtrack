WITH future_shows as (
    SELECT
        id,
        date_time,
        ticket_link,
        popularity_score,
        club_id
    FROM
        shows
    where
        date_time > NOW()
)
SELECT
    c.id,
    c.name,
    c.base_url, 
    c.timezone,
    c.city,
    c.address,
    c.popularity_score,
    c.zip_code,
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
            c.id
        )
    ) FILTER (WHERE fs.id IS NOT NULL), '[]') AS shows
from
    clubs c
    left join future_shows fs on fs.club_id = c.id
WHERE
    c.name = ${name}
GROUP BY
    c.id,
    c.name,
    fs.date_time
ORDER BY
    fs.date_time ASC