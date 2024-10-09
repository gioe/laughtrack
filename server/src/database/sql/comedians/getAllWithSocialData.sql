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
            'youtube_account',
            c.youtube_account,
            'youtube_followers',
            c.youtube_followers,
            'website',
            c.website,
            'popularity_score',
            c.popularity_score
        ) AS social_data
from comedians c ORDER BY c.popularity_score ASC