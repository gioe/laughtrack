-- Switch Laugh Factory Reno (club 173) from laugh_factory_reno scraper to live_nation (Ticketmaster)
-- The venue's own website (laughfactory.com/reno) has a "coming soon" placeholder with no shows listed.
-- Ticketmaster has 66 upcoming events for this venue (venue ID: KovZ917AP-J).
UPDATE clubs
SET scraper = 'live_nation',
    scraping_url = 'ticketmaster/KovZ917AP-J',
    ticketmaster_id = 'KovZ917AP-J'
WHERE id = 173;
