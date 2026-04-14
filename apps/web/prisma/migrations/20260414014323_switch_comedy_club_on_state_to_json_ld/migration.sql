-- Hide The Comedy Club On State (club 826) — duplicate of Comedy on State (club 435)
-- Club 826 used SeatEngine venue 265 which returns 404; venue rebranded as
-- "Comedy on State" and is already onboarded as club 435 (json_ld scraper,
-- scraping madisoncomedy.com, 10 total shows). Hiding the duplicate.

UPDATE "clubs"
SET visible = false
WHERE id = 826;
