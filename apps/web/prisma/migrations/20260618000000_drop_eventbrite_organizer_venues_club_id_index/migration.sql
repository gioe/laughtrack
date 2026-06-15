-- Drop the now-unused eventbrite_organizer_venues club_id index (TASK-2862).
-- TASK-2859 added eventbrite_organizer_venues_club_id_idx specifically for the
-- COVERED_BY_OTHER_ORGANIZER cross-organizer coverage probe ("is this club_id
-- claimed by any OTHER organizer?"). TASK-2861 replaced the conservative-skip
-- approach with per-show organizer attribution and removed that probe, so no
-- query filters this table by club_id alone anymore (GET_VENUE_CLUB_IDS keys on
-- production_company_id; DELETE_VENUE and the record_venues upsert use the
-- composite PK). The only remaining club_id-alone access is the FK cascade on a
-- rare club delete, which seq-scans this small table cheaply — not worth the
-- write amplification of a dedicated index.

-- DropIndex
DROP INDEX "eventbrite_organizer_venues_club_id_idx";
