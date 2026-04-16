-- Update The Improv Collective (club 794) metadata — venue is active but runs on JetBook (Bubble.io).
-- No existing scraper supports JetBook's Elasticsearch-backed API, so scraper build is deferred to a
-- follow-up task. Clears stale seatengine_id=214 (0 shows since import), sets correct address/tz/zip,
-- and points scraping_url at the JetBook iframe endpoint so the follow-up task inherits the URL.
-- Keeps visible=false and leaves scraper='seatengine' as a placeholder until the JetBook scraper lands.
UPDATE clubs
SET
    address = '1215 Baker Street',
    city = 'Costa Mesa',
    state = 'CA',
    zip_code = '92626',
    timezone = 'America/Los_Angeles',
    website = 'https://improvcollective.fun',
    scraping_url = 'https://jetbook.co/o_iframe/improv-collective-srzaf',
    seatengine_id = NULL
WHERE id = 794;
