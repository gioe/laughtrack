-- Fix The Comedy Zone - Cherokee (club 60) metadata
-- Timezone was America/Denver (Mountain) but Cherokee, NC is Eastern
-- Backfill missing city, state, country fields
UPDATE "clubs"
SET timezone = 'America/New_York',
    city = 'Cherokee',
    state = 'NC',
    country = 'US'
WHERE id = 60;
