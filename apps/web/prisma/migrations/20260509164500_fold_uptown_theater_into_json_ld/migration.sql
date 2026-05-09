-- Fold Uptown Theater into the shared json_ld scraper.
-- The detail_fetch metadata makes json_ld harvest event page URLs from the
-- listing page's CollectionPage JSON-LD, then fetch each detail page where the
-- ComedyEvent JSON-LD contains the full show and AggregateOffer ticket data.
UPDATE scraping_sources
SET
    scraper_key = 'json_ld',
    metadata = jsonb_set(
        COALESCE(metadata, '{}'::jsonb),
        '{detail_fetch}',
        '{"listing_type":"CollectionPage","url_path":"mainEntity.itemListElement[].url"}'::jsonb,
        true
    ),
    updated_at = NOW()
WHERE club_id = 80
  AND scraper_key = 'uptown_theater'
  AND enabled = TRUE;
