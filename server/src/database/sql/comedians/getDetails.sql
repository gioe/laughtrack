SELECT
    c.id,
    c.name,
        jsonb_build_object(
            'instagram_account',
            c.instagram_account,
            'instagram_followers',
            c.instagram_followers,
            'tiktok_account',
            c.tiktok_account,
            'tiktok_followers',
            c.tiktok_followers,
            'website', 
            c.website,
            'popularity_score',
            c.popularity_score
        ) AS social_data,
        jsonb_agg(
        DISTINCT jsonb_build_object(
            'show_id',
            s.id,
            'date_time',
            s.date_time,
            'ticket_link',
            s.ticket_link,
            'city',
            cl.city,
            'club_name',
            c.name
        )
    ) AS shows
from shows s
inner join show_comedians sc on s.id = sc.show_id
inner join comedians c on c.id = sc.comedian_id
inner join clubs cl on cl.id = s.club_id
WHERE c.name = ${name}
GROUP BY
    c.id