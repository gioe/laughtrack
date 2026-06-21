-- TASK-3026: West River's json_ld Playwright path is blocked by hard
-- Cloudflare Turnstile from GHA datacenter egress. Use the dedicated
-- Ticket Tailor listing scraper instead: curl_cffi impersonation plus the
-- venue website Referer gets server-rendered event cards without Playwright.

UPDATE scraping_sources
   SET scraper_key = 'ticket_tailor',
       source_url = 'https://www.tickettailor.com/events/westrivercomedyclub/',
       metadata = '{
           "account_slug": "westrivercomedyclub",
           "single_venue": true,
           "cloudflare_bypass": {
               "strategy": "ticket_tailor_curl_cffi_referer",
               "referer": "https://www.westrivercomedy.com",
               "reason": "Ticket Tailor listing HTML clears Cloudflare via curl_cffi chrome impersonation plus the venue website Referer; avoids the hard Turnstile encountered by Playwright json_ld detail fetches from GHA datacenter egress.",
               "verified_at": "2026-06-20",
               "local_event_count": 48
           }
       }'::jsonb,
       updated_at = NOW()
 WHERE club_id = 1059
   AND scraper_key = 'json_ld'
   AND source_url = 'https://www.tickettailor.com/events/westrivercomedyclub';
