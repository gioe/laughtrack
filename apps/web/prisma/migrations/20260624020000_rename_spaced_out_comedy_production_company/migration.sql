-- Rename production_company "Have a Laugh" -> "Spaced Out Comedy" (correct brand name).
--
-- CONTEXT: TASK-3226 ("Have A Laugh Comedy Shows", San Jose) discovered that the
-- Google pin "Have A Laugh" at 1788 N First St is actually a restaurant (The
-- Province) and that the real comedy entity is the recurring indie stand-up
-- series "Spaced Out Comedy" (spacedoutcomedy.com), ticketed through Eventbrite
-- organizer 80647104493. 3226 onboarded that organizer as the production_company
-- but mislabeled it "Have a Laugh". Sibling TASK-3228 ("Spaced Out Comedy")
-- resolved to the SAME organizer and was deduped into this row (its duplicate
-- single-venue club was removed in 20260624010000).
--
-- This corrects the display name + slug to the real brand. It stays modeled as a
-- production_company in Eventbrite organizer mode (NOT a club) because Spaced Out
-- Comedy is a roving pop-up series, not a fixed venue — organizer mode routes
-- each show to the actual per-venue club (e.g. the "Mysterieux Brand" barbershop)
-- where it is held.
--
-- Idempotent: guarded on the organizer scraping_url + the old name, so re-runs
-- (and a fresh-DB replay after the onboarding migration) are no-ops.

UPDATE production_companies
SET name = 'Spaced Out Comedy',
    slug = 'spaced-out-comedy-eventbrite-organizer'
WHERE scraping_url = 'https://www.eventbrite.com/o/spaced-out-comedy-80647104493'
  AND name = 'Have a Laugh'
  AND NOT EXISTS (
      SELECT 1 FROM production_companies p2
      WHERE p2.slug = 'spaced-out-comedy-eventbrite-organizer'
  );
