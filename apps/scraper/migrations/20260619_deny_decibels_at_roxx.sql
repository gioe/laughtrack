-- TASK-2973: Deny Decibels at Roxx as a discovered comedy venue.
--
-- Google classifies the place as a live_music_venue, not a comedy club. Its
-- Squarespace account currently serves the platform "Website Expired" system
-- page on the root and likely event paths, and the sister On The Roxx domain is
-- frozen. With no venue-owned comedy calendar or comedy signal to scrape, keep
-- the venue hidden, add no scraping_sources row, and deny-list the Google Place
-- so discover-nearby does not re-file it as a comedy onboarding candidate.

INSERT INTO clubs (
    name,
    address,
    website,
    zip_code,
    timezone,
    visible,
    city,
    state,
    status,
    club_type,
    latitude,
    longitude,
    google_place_id
)
SELECT
    'Decibels at Roxx',
    '2522 Portage Mall',
    'https://www.decibelsportage.com/',
    '46368',
    'America/Chicago',
    FALSE,
    'Portage',
    'IN',
    'active',
    'club',
    41.5789209,
    -87.1775927,
    'ChIJ9cLpO-K_EYgR3FY53QVUszI'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJ9cLpO-K_EYgR3FY53QVUszI'
        OR lower(name) = lower('Decibels at Roxx')
);

UPDATE clubs
   SET address = '2522 Portage Mall',
       website = 'https://www.decibelsportage.com/',
       zip_code = '46368',
       timezone = 'America/Chicago',
       visible = FALSE,
       city = 'Portage',
       state = 'IN',
       status = 'active',
       club_type = 'club',
       latitude = COALESCE(latitude, 41.5789209),
       longitude = COALESCE(longitude, -87.1775927),
       google_place_id = COALESCE(google_place_id, 'ChIJ9cLpO-K_EYgR3FY53QVUszI')
 WHERE google_place_id = 'ChIJ9cLpO-K_EYgR3FY53QVUszI'
    OR lower(name) = lower('Decibels at Roxx');

INSERT INTO venue_deny_list (
    google_place_id,
    name,
    reason,
    added_by
)
SELECT
    'ChIJ9cLpO-K_EYgR3FY53QVUszI',
    'Decibels at Roxx',
    'Discovered as a comedy venue candidate, but current evidence shows a live-music venue with expired/frozen sites and no public comedy calendar.',
    'TASK-2973'
WHERE NOT EXISTS (
    SELECT 1
      FROM venue_deny_list
     WHERE google_place_id = 'ChIJ9cLpO-K_EYgR3FY53QVUszI'
);
