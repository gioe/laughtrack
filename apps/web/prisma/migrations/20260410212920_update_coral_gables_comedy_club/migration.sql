-- Update Coral Gables Comedy Club (club 311)
-- Venue moved from SeatEngine to Square Online (saugatuckcomedy.com).
-- SeatEngine venue 108 returns 302 redirect (dead).
-- Correct location: 220 Water St, Saugatuck, MI 49453 (not Florida).
UPDATE "clubs"
SET
    website = 'https://www.saugatuckcomedy.com',
    scraping_url = 'https://cdn5.editmysite.com/app/store/api/v28/editor/users/136260138/sites/258418661117809030/products?product_type=event&visibilities[]=visible&per_page=50&include=images,media_files&excluded_fulfillment=dine_in',
    scraper = 'coral_gables_comedy_club',
    address = '220 Water St',
    city = 'Saugatuck',
    state = 'MI',
    zip_code = '49453',
    timezone = 'America/New_York',
    seatengine_id = NULL,
    visible = true
WHERE id = 311;
