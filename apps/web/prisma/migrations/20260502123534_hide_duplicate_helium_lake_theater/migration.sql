-- Hide duplicate/bad Helium row (club 1428).
--
-- Club 1428 is a corrupt hybrid row:
--   * its name, "Helium", is already represented by the real Philadelphia Helium
--     record, club 110
--   * its website/source point at laketheatercafe.com, which is already represented
--     by the real Lake Theater & Cafe record, club 1136
--   * it has no location metadata and has never produced shows
--
-- Local verification on 2026-05-02:
--   * club 1428 SeatEngine source 115 scraped 0 shows
--   * club 110 SeatEngine source 1 is the canonical Philadelphia Helium row
--   * club 1136 Eventbrite source 87504744283 is the canonical Lake Theater row

UPDATE clubs
SET visible = false
WHERE id = 1428
  AND name = 'Helium'
  AND website = 'https://laketheatercafe.com';

UPDATE scraping_sources
SET enabled = false,
    metadata = metadata || jsonb_build_object(
        'disabled_reason', 'duplicate_bad_import',
        'canonical_name_club_id', 110,
        'canonical_source_club_id', 1136
    )
WHERE club_id = 1428
  AND platform = 'seatengine'
  AND external_id = '115';
