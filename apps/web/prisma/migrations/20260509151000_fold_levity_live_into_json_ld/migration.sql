-- Fold Levity Live venues into the shared json_ld scraper.
-- The detail_fetch metadata makes json_ld harvest sameAs URLs from the
-- calendar JSON-LD, fetch each comic detail page, and use the detail page URL
-- as show_page_url while keeping TicketWeb URLs on tickets.
UPDATE scraping_sources
SET
    scraper_key = 'json_ld',
    metadata = jsonb_set(
        COALESCE(metadata, '{}'::jsonb),
        '{detail_fetch}',
        '{"url_field":"sameAs","set_same_as_to_detail_url":true}'::jsonb,
        true
    ),
    updated_at = NOW()
WHERE club_id IN (26, 27, 28)
  AND scraper_key = 'levity_live'
  AND enabled = TRUE;
