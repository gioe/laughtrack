-- Switch American Comedy Company (club 1035) from dead tour_dates to Shopify scraper
-- Venue is active at americancomedyco.com, selling tickets via Shopify collections
UPDATE "clubs"
SET
    scraper = 'shopify',
    scraping_url = 'https://americancomedyco.com/collections/shows',
    website = 'https://americancomedyco.com'
WHERE id = 1035;
