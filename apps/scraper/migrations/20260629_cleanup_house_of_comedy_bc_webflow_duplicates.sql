-- Remove stale homepage-card rows after switching House of Comedy BC to Pixl Calendar.
DELETE FROM shows old
WHERE old.club_id = 2357
  AND old.last_scraped_by = 'tixr_webflow_day_card'
  AND old.date >= NOW()
  AND EXISTS (
      SELECT 1
      FROM shows newer
      WHERE newer.club_id = old.club_id
        AND newer.last_scraped_by = 'tixr'
        AND newer.name = old.name
        AND newer.date = old.date
        AND newer.show_page_url = old.show_page_url
  );
