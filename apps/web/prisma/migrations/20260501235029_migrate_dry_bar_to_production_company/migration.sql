-- Model Dry Bar Comedy as a production company, with club 497 as the Provo venue.

UPDATE clubs
SET name = 'Dry Bar Comedy Showroom'
WHERE id = 497
  AND name = 'Dry Bar Comedy';

INSERT INTO production_companies (
    name,
    slug,
    website,
    scraping_url,
    visible,
    show_name_keywords
)
VALUES (
    'Dry Bar Comedy',
    'dry-bar-comedy',
    'https://www.drybarcomedy.com',
    'https://store.drybarcomedy.com/collections/tickets',
    true,
    ARRAY[]::text[]
)
ON CONFLICT (slug) DO UPDATE
SET name = EXCLUDED.name,
    website = EXCLUDED.website,
    scraping_url = EXCLUDED.scraping_url,
    visible = true,
    show_name_keywords = EXCLUDED.show_name_keywords;

INSERT INTO production_company_venues (production_company_id, club_id)
SELECT pc.id, 497
FROM production_companies pc
WHERE pc.slug = 'dry-bar-comedy'
ON CONFLICT DO NOTHING;

UPDATE shows
SET production_company_id = pc.id
FROM production_companies pc
WHERE pc.slug = 'dry-bar-comedy'
  AND shows.club_id = 497
  AND shows.production_company_id IS DISTINCT FROM pc.id;
