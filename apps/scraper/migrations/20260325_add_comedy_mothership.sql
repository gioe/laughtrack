-- TASK-687: Add Comedy Mothership as a new venue
-- Website: https://comedymothership.com/
-- Comedy Mothership is located at 320 E 6th St, Austin, TX 78701.
-- Joe Rogan's Austin comedy club with regular drop-ins and national touring acts.
-- Shows are listed on the venue's Next.js website; tickets sold via SquadUP.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Comedy Mothership',
    '320 E 6th St',
    'Austin',
    'TX',
    '78701',
    'America/Chicago',
    'comedy_mothership',
    TRUE,
    'https://comedymothership.com',
    'https://comedymothership.com/shows'
);
