-- Tighten the Pabst Theater Group operator calendar so mixed-programming
-- concerts/dance events do not leak through via broad known-name matching.

UPDATE source_targets
SET metadata = COALESCE(metadata, '{}'::jsonb)
    || jsonb_build_object(
        'disable_known_comedian_match', true,
        'comedy_title_allowlist', jsonb_build_array(
            'anthony jeselnik',
            'ben schwartz',
            'danny gonzalez',
            'derrick stroup',
            'daniel sloss',
            'hasan',
            'josh johnson',
            'jonathan van ness',
            'kevin smith',
            'matt mathews',
            'mojo brookzz',
            'natalie cuomo',
            'ron funches',
            'ronny chieng',
            'small town murder',
            'steve hofstetter',
            'tony dabas',
            'wait wait',
            'zarna garg'
        )
    )
WHERE name = 'Pabst Theater Group';

DELETE FROM tickets
WHERE show_id IN (
    SELECT id
    FROM shows
    WHERE last_scraped_by = 'pabst_theater_group'
      AND (
          show_page_url ILIKE '%/derek-hough-%'
          OR show_page_url ILIKE '%/tori-amos-%'
          OR show_page_url ILIKE '%/raq-baby-%'
      )
);

DELETE FROM shows
WHERE last_scraped_by = 'pabst_theater_group'
  AND (
      show_page_url ILIKE '%/derek-hough-%'
      OR show_page_url ILIKE '%/tori-amos-%'
      OR show_page_url ILIKE '%/raq-baby-%'
  );

UPDATE clubs
SET total_shows = counts.total
FROM (
    SELECT c.id, COUNT(s.id)::int AS total
    FROM clubs c
    LEFT JOIN shows s ON s.club_id = c.id
    GROUP BY c.id
) counts
WHERE clubs.id = counts.id;
