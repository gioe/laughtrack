-- Formalize the clubs.club_type taxonomy.
--
-- Accepted values:
--   club            comedy-first fixed venue
--   venue           mixed-purpose physical host with comedy programming
--   festival        seasonal comedy festival; scraper scheduling special-cases this
--   producer        organizer identity, not a public physical venue
--   secret_location intentionally undisclosed venue placeholder
--   non_comedy      hidden discovery placeholder for reviewed non-comedy venues

UPDATE clubs
   SET club_type = 'non_comedy'
  FROM venue_deny_list
 WHERE clubs.google_place_id = venue_deny_list.google_place_id
   AND clubs.visible = FALSE
   AND clubs.status = 'active';

UPDATE clubs
   SET club_type = 'venue'
 WHERE club_type = 'theater';

ALTER TABLE clubs
    DROP CONSTRAINT IF EXISTS clubs_club_type_check;

ALTER TABLE clubs
    ADD CONSTRAINT clubs_club_type_check
    CHECK (club_type IN (
        'club',
        'venue',
        'festival',
        'producer',
        'secret_location',
        'non_comedy'
    ));
