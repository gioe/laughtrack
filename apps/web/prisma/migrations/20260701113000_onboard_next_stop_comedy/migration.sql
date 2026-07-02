-- Onboard Next Stop Comedy as a roving production-company scraper.
--
-- Next Stop Comedy is a promoter, not a venue. Its public calendar lists shows
-- across many physical venues; the next_stop_comedy scraper discovers each
-- venue from event JSON-LD and attaches the show to that venue while the
-- production-company proxy stamps production_company_id.

INSERT INTO production_companies (
    name,
    slug,
    website,
    scraping_url,
    visible,
    show_name_keywords
)
VALUES (
    'Next Stop Comedy',
    'next-stop-comedy',
    'https://www.nextstopcomedy.com',
    'https://www.nextstopcomedy.com/events',
    TRUE,
    ARRAY[]::TEXT[]
)
ON CONFLICT (slug) DO UPDATE
SET name = EXCLUDED.name,
    website = EXCLUDED.website,
    scraping_url = EXCLUDED.scraping_url,
    visible = EXCLUDED.visible,
    show_name_keywords = EXCLUDED.show_name_keywords;
