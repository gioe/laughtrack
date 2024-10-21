SELECT id, name, jsonb_build_object(
            'instagram_account',
            instagram_account,
            'instagram_followers',
            instagram_followers,
            'tiktok_account',
            tiktok_account,
            'tiktok_followers',
            tiktok_followers,
            'youtube_account',
            youtube_account,
            'youtube_followers',
            youtube_followers,
            'website',
            website,
            'popularity_score',
            popularity_score
        ) AS social_data
FROM comedians 
ORDER BY popularity_score DESC LIMIT 5;