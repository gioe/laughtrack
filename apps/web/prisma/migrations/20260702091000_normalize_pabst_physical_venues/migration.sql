-- Normalize existing physical venues that can be routed by the Pabst Theater
-- Group operator scraper. These are mixed-purpose host venues, not comedy clubs.

UPDATE clubs
SET club_type = 'venue',
    website = CASE
        WHEN name = 'Miller High Life Theatre' AND COALESCE(website, '') = ''
        THEN 'https://www.pabsttheatergroup.com/venues/detail/miller-high-life-theatre'
        WHEN name = 'Fiserv Forum' AND COALESCE(website, '') = ''
        THEN 'https://www.fiservforum.com'
        ELSE website
    END
WHERE name IN ('Miller High Life Theatre', 'Fiserv Forum')
  AND club_type IS DISTINCT FROM 'venue';
