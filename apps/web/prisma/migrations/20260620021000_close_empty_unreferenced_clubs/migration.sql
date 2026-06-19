-- TASK-3016: close visible active clubs that currently have zero shows and no
-- enabled scraping source, and remove only clearly malformed hidden artifacts.
--
-- Live DB candidate regeneration before writing this migration found:
--
-- close/hide visible active zero-show/no-enabled-source rows:
--   379  Palm Beach Improv
--   2355 Rick Bronson's House of Comedy Phoenix
--   2585 The Parker
--   2586 Lyric Theatre
--   2625 Borgata Music Box
--   2816 The Cove at River Spirit Casino Resort
--   2823 The Venetian Theatre
--   2841 Thomas Wolfe Auditorium
--   2843 Center for the Arts - University at Buffalo
--   2850 The Berglund Center
--   2852 F.M. Kirby Center for the Performing Arts
--   2854 Peabody Auditorium
--   2855 Johnny Mercer Theatre
--   2862 Dominion Energy Center
--   2871 Hult Center for the Performing Arts
--   2873 Redding Civic Auditorium
--   2874 Durham Performing Arts Center
--   2876 Silver Legacy Grande Exposition Hall
--   2877 Stranahan Theater
--   2949 Youtube Theater
--   2957 Neal S. Blaisdell Concert Hall
--   2963 Pechanga Theater
--   3000 Capitol Theatre
--   3002 Tulsa Comedy Club
--   3007 MGM National Harbor
--   3008 The Venetian Resort
--   3009 Harrah's Resort
--   3016 LOL Comedy Club
--   3018 Trillith Live
--   3019 Mable House
--   3021 Martin Marietta Center
--   3022 Boardwalk Hall
--   3024 Foxwoods Casino
--   3032 Wheeler Opera House
--   3045 US Main Room, Hollywood Improv
--
-- delete hidden malformed tour-date artifact rows:
--   2951 713 Music Hall May 17 '26 Dallas, TX Majestic Theatre
--   3011 August 2, 2026 Stress Factory
--   3044 US Main Room, Hollywood Improv Interested
--   3046 US Hollywood Casino Joliet Interested
--
-- keep hidden real/staging/audit rows untouched:
--   Hidden rows with enabled sources are staging/onboarding rows.
--   Hidden rows without sources but with real websites may be future onboarding
--   candidates and should remain hidden rather than be deleted.
--   TASK-3015 closed duplicate rows (4962, 5400, 6755, 6875) are retained as
--   recent audit records.
--   Ticketmaster National (4036) is a platform trigger, not a public club row.
--   Explicit keep set from the live hidden-unreferenced query:
--     2879, 3003, 3047, 4036, 4741, 4962, 5400, 6755, 6875,
--     8691, 8694, 8697, 8700, 8706, 8708, 8723, 8733,
--     8819, 8820, 8821, 8826, 8827, 8828, 8832, 8835, 8838,
--     8840, 8841, 8842, 8843, 8848, 8849, 8850, 8851, 8852,
--     8853, 8854, 8858, 8859, 8860, 8863, 8865, 8866, 8869,
--     8870, 8871, 8873, 8874, 8875, 8877, 8880, 8881, 8882,
--     8885, 8886, 8887, 8889, 8891, 8892, 8893, 8894, 8895,
--     8896, 8898, 9063, 9066.

CREATE TEMP TABLE empty_club_cleanup_classification (
    club_id integer PRIMARY KEY,
    action text NOT NULL,
    rationale text NOT NULL
) ON COMMIT DROP;

INSERT INTO empty_club_cleanup_classification (club_id, action, rationale)
VALUES
    (379, 'close_hide', 'Visible active club has zero shows and no enabled source; disabled source metadata says upstream empty.'),
    (2355, 'close_hide', 'Visible active club has zero shows and no enabled source; disabled source metadata says upstream empty.'),
    (2585, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2586, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2625, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2816, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2823, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2841, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2843, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2850, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2852, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2854, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2855, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2862, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2871, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2873, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2874, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2876, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2877, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2949, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion; malformed city cleanup is tracked separately.'),
    (2957, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion; malformed city cleanup is tracked separately.'),
    (2963, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion; malformed city cleanup is tracked separately.'),
    (3000, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (3002, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (3007, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (3008, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (3009, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (3016, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (3018, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (3019, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (3021, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (3022, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (3024, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (3032, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (3045, 'close_hide', 'Visible active tour_dates remnant has zero shows and no enabled source after TASK-2581 removed tour_dates ingestion.'),
    (2951, 'delete', 'Hidden unreferenced malformed tour_dates parse artifact, not a real venue row.'),
    (3011, 'delete', 'Hidden unreferenced malformed tour_dates parse artifact, not a real venue row.'),
    (3044, 'delete', 'Hidden unreferenced malformed tour_dates parse artifact, not a real venue row.'),
    (3046, 'delete', 'Hidden unreferenced malformed tour_dates parse artifact, not a real venue row.');

DO $$
DECLARE
    close_count integer;
    delete_count integer;
    unsafe_count integer;
BEGIN
    SELECT count(*) INTO close_count
    FROM empty_club_cleanup_classification
    WHERE action = 'close_hide';

    SELECT count(*) INTO delete_count
    FROM empty_club_cleanup_classification
    WHERE action = 'delete';

    IF close_count <> 35 THEN
        RAISE EXCEPTION 'TASK-3016 expected 35 close/hide candidates, found %', close_count;
    END IF;

    IF delete_count <> 4 THEN
        RAISE EXCEPTION 'TASK-3016 expected 4 delete candidates, found %', delete_count;
    END IF;

    SELECT count(*) INTO unsafe_count
    FROM empty_club_cleanup_classification ecc
    JOIN clubs c ON c.id = ecc.club_id
    WHERE EXISTS (SELECT 1 FROM shows s WHERE s.club_id = c.id)
       OR EXISTS (SELECT 1 FROM scraping_sources ss WHERE ss.club_id = c.id AND ss.enabled = true)
       OR EXISTS (SELECT 1 FROM club_aliases ca WHERE ca.club_id = c.id)
       OR EXISTS (SELECT 1 FROM favorite_clubs fc WHERE fc.club_id = c.id)
       OR EXISTS (SELECT 1 FROM email_subscriptions es WHERE es.club_id = c.id)
       OR EXISTS (SELECT 1 FROM ticket_purchase_click_events tpce WHERE tpce.club_id = c.id)
       OR EXISTS (SELECT 1 FROM tagged_clubs tc WHERE tc.club_id = c.id)
       OR EXISTS (SELECT 1 FROM club_image_assets cia WHERE cia.club_id = c.id)
       OR EXISTS (SELECT 1 FROM processed_emails pe WHERE pe.club_id = c.id)
       OR EXISTS (SELECT 1 FROM production_company_venues pcv WHERE pcv.club_id = c.id)
       OR EXISTS (SELECT 1 FROM eventbrite_organizer_venues eov WHERE eov.club_id = c.id);

    IF unsafe_count <> 0 THEN
        RAISE EXCEPTION 'TASK-3016 cleanup candidates gained meaningful references; refusing to continue';
    END IF;
END $$;

UPDATE clubs c
SET
    visible = FALSE,
    status = 'closed',
    closed_at = NOW(),
    total_shows = 0,
    description = concat_ws(
        E'\n\n',
        NULLIF(c.description, ''),
        'Closed by TASK-3016: visible active club had zero shows and no enabled scraping source. ' || ecc.rationale
    )
FROM empty_club_cleanup_classification ecc
WHERE ecc.action = 'close_hide'
  AND c.id = ecc.club_id
  AND c.visible = TRUE
  AND c.status = 'active'
  AND NOT EXISTS (SELECT 1 FROM shows s WHERE s.club_id = c.id)
  AND NOT EXISTS (
      SELECT 1
      FROM scraping_sources ss
      WHERE ss.club_id = c.id
        AND ss.enabled = TRUE
  );

DELETE FROM scraping_sources ss
USING empty_club_cleanup_classification ecc
WHERE ss.club_id = ecc.club_id
  AND ecc.action IN ('close_hide', 'delete')
  AND ss.enabled = FALSE;

DELETE FROM clubs c
USING empty_club_cleanup_classification ecc
WHERE ecc.action = 'delete'
  AND c.id = ecc.club_id
  AND c.visible = FALSE
  AND NOT EXISTS (SELECT 1 FROM shows s WHERE s.club_id = c.id)
  AND NOT EXISTS (SELECT 1 FROM scraping_sources ss WHERE ss.club_id = c.id)
  AND NOT EXISTS (SELECT 1 FROM club_aliases ca WHERE ca.club_id = c.id)
  AND NOT EXISTS (SELECT 1 FROM favorite_clubs fc WHERE fc.club_id = c.id)
  AND NOT EXISTS (SELECT 1 FROM email_subscriptions es WHERE es.club_id = c.id)
  AND NOT EXISTS (SELECT 1 FROM ticket_purchase_click_events tpce WHERE tpce.club_id = c.id)
  AND NOT EXISTS (SELECT 1 FROM tagged_clubs tc WHERE tc.club_id = c.id)
  AND NOT EXISTS (SELECT 1 FROM club_image_assets cia WHERE cia.club_id = c.id)
  AND NOT EXISTS (SELECT 1 FROM processed_emails pe WHERE pe.club_id = c.id)
  AND NOT EXISTS (SELECT 1 FROM production_company_venues pcv WHERE pcv.club_id = c.id)
  AND NOT EXISTS (SELECT 1 FROM eventbrite_organizer_venues eov WHERE eov.club_id = c.id);

DO $$
DECLARE
    remaining_visible_empty integer;
BEGIN
    SELECT count(*)
    INTO remaining_visible_empty
    FROM clubs c
    WHERE c.visible = TRUE
      AND c.status = 'active'
      AND NOT EXISTS (SELECT 1 FROM shows s WHERE s.club_id = c.id)
      AND NOT EXISTS (
          SELECT 1
          FROM scraping_sources ss
          WHERE ss.club_id = c.id
            AND ss.enabled = TRUE
      );

    IF remaining_visible_empty <> 0 THEN
        RAISE EXCEPTION 'TASK-3016 left % visible active clubs with zero shows and no enabled source', remaining_visible_empty;
    END IF;
END $$;
