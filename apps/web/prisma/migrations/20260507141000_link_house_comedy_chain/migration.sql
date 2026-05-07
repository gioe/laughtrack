-- Link House of Comedy venues to a shared chain record.
--
-- TASK-1999 onboarded Rick Bronson's House of Comedy Phoenix as a standalone
-- club. The chain table already supports venue grouping via clubs.chain_id, so
-- keep this migration idempotent and attach Phoenix plus any pre-existing
-- Bloomington venue row to the same House of Comedy chain.

WITH chain_row AS (
    INSERT INTO chains (
        name,
        slug,
        website
    )
    VALUES (
        'House of Comedy',
        'house-of-comedy',
        'https://houseofcomedy.net/'
    )
    ON CONFLICT (slug) DO UPDATE
    SET name = EXCLUDED.name,
        website = EXCLUDED.website
    RETURNING id
)
UPDATE clubs
SET chain_id = (SELECT id FROM chain_row)
WHERE name IN (
    'Rick Bronson''s House of Comedy Phoenix',
    'House of Comedy Bloomington'
)
OR website IN (
    'https://az.houseofcomedy.net/',
    'https://moa.houseofcomedy.net/',
    'https://moa.houseofcomedy.net'
);
