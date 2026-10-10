-- Reuse the hotel-backed identity and preserve both aggregate-source rows.
DO $$
DECLARE alias_label text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM clubs WHERE id=4744 AND city='Princeton' AND state='NJ') THEN
        RAISE EXCEPTION 'TASK-4149 canonical Princeton identity changed';
    END IF;
    UPDATE clubs SET name='Catch a Rising Star at Hyatt Regency Princeton',
        website='https://www.catcharisingstar.com/' WHERE id=4744;
    FOREACH alias_label IN ARRAY ARRAY['Hyatt Regency Princeton', 'Catch a Rising Star Princeton'] LOOP
        INSERT INTO club_aliases (club_id, alias_name, city, state, source, verified, updated_at)
        VALUES (4744, alias_label, 'Princeton', 'NJ', 'TASK-4149', true, now())
        ON CONFLICT (normalized_alias_name, normalized_city, normalized_state) DO NOTHING;
        IF NOT EXISTS (SELECT 1 FROM club_aliases WHERE club_id=4744
            AND normalized_alias_name=lt_normalize_alias_key(alias_label)
            AND normalized_city='princeton' AND normalized_state='nj' AND verified) THEN
            RAISE EXCEPTION 'TASK-4149 alias collision: %', alias_label;
        END IF;
    END LOOP;
END $$;

INSERT INTO scraping_sources (club_id,platform,scraper_key,source_url,priority,enabled,metadata)
VALUES (4744,'custom'::"ScrapingPlatform",'json_ld',
    'https://www.ticketweb.com/venue/hyatt-regency-princeton-princeton-nj/44754',0,true,
    '{"force_js_rendering":true,"location_name_filter":"Hyatt Regency Princeton","localize_naive_dates":true,"infer_lineup_from_title":false,"performer_prefixes":["NJ 101.5''s ","Special Event Headlining Comedian "],"performer_aliases":{"Jackie \"The Joke Man\" Martling":"Jackie Martling"}}'::jsonb)
ON CONFLICT (club_id,platform,priority) DO UPDATE SET
    scraper_key=EXCLUDED.scraper_key,source_url=EXCLUDED.source_url,
    enabled=EXCLUDED.enabled,metadata=EXCLUDED.metadata,updated_at=now();
