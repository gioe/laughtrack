-- TASK-4124: separate the verified New York venue from the unrelated LA club.
-- Evidence: https://www.theclubhouseny.com/ and Next Stop's October 24 event.
-- Show reassignment is performed separately by the guarded repair script.
DO $$
DECLARE target clubs%ROWTYPE;
BEGIN
    PERFORM 1 FROM clubs WHERE id = 8828 AND name = 'The Clubhouse'
      AND address = '1607 N Vermont Ave, Los Angeles, CA 90027, USA'
      AND city = 'Los Angeles' AND state = 'CA' AND zip_code = '90027';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'TASK-4124: Los Angeles identity changed';
    END IF;

    IF EXISTS (SELECT 1 FROM clubs WHERE address ILIKE '%377%Denton%'
               AND name <> 'The Clubhouse (New Hyde Park)') THEN
        RAISE EXCEPTION 'TASK-4124: unreviewed Denton Avenue venue exists';
    END IF;

    INSERT INTO clubs (name, address, website, city, state, zip_code, country,
                       timezone, club_type, visible, status)
    VALUES ('The Clubhouse (New Hyde Park)', '377 Denton Avenue',
            'https://www.theclubhouseny.com/', 'New Hyde Park', 'NY', '11040',
            'US', 'America/New_York', 'venue', true, 'active')
    ON CONFLICT (name) DO NOTHING;

    SELECT * INTO STRICT target FROM clubs
      WHERE name = 'The Clubhouse (New Hyde Park)' FOR UPDATE;
    IF ROW(target.address, target.website, target.city, target.state,
           target.zip_code, target.country, target.timezone, target.club_type,
           target.visible, target.status) IS DISTINCT FROM
       ROW('377 Denton Avenue'::text, 'https://www.theclubhouseny.com/'::text,
           'New Hyde Park'::text, 'NY'::text, '11040'::varchar, 'US'::text,
           'America/New_York'::text, 'venue'::text, true, 'active'::text) THEN
        RAISE EXCEPTION 'TASK-4124: New Hyde Park target identity changed';
    END IF;

    -- Trigger supplies normalized keys. Never overwrite an existing alias owner.
    INSERT INTO club_aliases (club_id, alias_name, city, state, source, verified, updated_at)
    VALUES (target.id, 'The Clubhouse', 'New Hyde Park', 'NY', 'TASK-4124', true, now())
    ON CONFLICT (normalized_alias_name, normalized_city, normalized_state) DO NOTHING;
    PERFORM 1 FROM club_aliases WHERE club_id = target.id
      AND normalized_alias_name = lt_normalize_alias_key('The Clubhouse')
      AND normalized_city = lt_normalize_alias_key('New Hyde Park')
      AND normalized_state = 'ny' AND verified;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'TASK-4124: alias is unverified or belongs to another venue';
    END IF;
END $$;
