-- Hide Helen Borgers Theatre: active theatre venue, not a comedy club.

UPDATE scraping_sources
SET enabled = FALSE,
    updated_at = NOW()
WHERE club_id = 424;

UPDATE clubs
SET visible = FALSE,
    status = 'active',
    closed_at = NULL
WHERE id = 424;
