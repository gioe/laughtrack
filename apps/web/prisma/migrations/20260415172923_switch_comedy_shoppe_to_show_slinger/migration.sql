-- Switch The Comedy Shoppe (club 327) from SeatEngine to ShowSlinger.
-- SeatEngine venue 124 returns 404; the venue now uses a ShowSlinger
-- widget embedded on jjcomedy.com/calendar/.

UPDATE clubs
SET scraper     = 'show_slinger',
    scraping_url = 'https://app.showslinger.com/promo_widget_v3/combo_widget?id=238&secure_code=ec8183215e'
WHERE id = 327;
