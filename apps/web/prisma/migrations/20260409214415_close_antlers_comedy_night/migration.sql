-- Close Antlers Comedy Night (club 820) — antlerscomedy.com ECONNREFUSED,
-- SeatEngine API 404, no venue-hosted events page. Comedy nights run by
-- third-party promoter (Billy Reno) via individual Humanitix event pages
-- with no scrapable listing URL.
UPDATE "clubs"
SET visible = false,
    scraper = NULL,
    scraping_url = '',
    seatengine_id = NULL
WHERE id = 820;
