-- Backfill location data for Comedy Club at The Park (club 520)
UPDATE "clubs"
SET
    website = 'https://www.thepark.com/comedy-club/',
    address = '1407 Cummings Drive',
    city = 'Richmond',
    state = 'VA',
    zip_code = '23220',
    timezone = 'America/New_York'
WHERE id = 520;
