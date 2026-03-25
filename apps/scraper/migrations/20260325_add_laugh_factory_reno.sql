-- TASK-683: Add Laugh Factory Reno as a new venue
-- Website: https://www.laughfactory.com/reno
-- Laugh Factory Reno is located at 407 N Virginia St, Reno, NV 89501.
-- Shows are listed on the Laugh Factory CMS page and ticketed via Tixologi
-- (partner ID 690, https://tixologi.com).  The Tixologi public API does not
-- expose an events endpoint; shows are parsed from server-rendered HTML.
-- Ticket links follow https://www.laughfactory.club/checkout/show/{punchup_id}.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Laugh Factory Reno',
    '407 N Virginia St',
    'Reno',
    'NV',
    '89501',
    'America/Los_Angeles',
    'laugh_factory_reno',
    TRUE,
    'https://www.laughfactory.com/reno',
    'https://www.laughfactory.com/reno'
);
