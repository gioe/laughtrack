-- Fix Helium Comedy Club Philadelphia scraping_url: add missing https:// prefix.
-- Without the scheme, URLUtils.get_formatted_domain returns an empty string,
-- causing BaseHeaders to omit origin/referer headers in SeatEngine API requests.
UPDATE clubs
SET scraping_url = 'https://heliumcomedy.com/philadelphia/events'
WHERE id = 110
  AND scraping_url = 'heliumcomedy.com/philadelphia/events';
