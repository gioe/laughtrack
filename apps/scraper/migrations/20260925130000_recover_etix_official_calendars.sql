-- TASK-4052: verified official calendars bypass Etix's blocked venue endpoint.
-- Guard the old URL so replay cannot overwrite a later operator repair.
-- Evidence: docs/audits/2026-09-25-etix/. Preserve source IDs and metadata.
UPDATE scraping_sources AS source
SET source_url = repair.new_url,
    metadata = source.metadata || repair.extra_metadata,
    updated_at = now()
FROM (VALUES
    (6960, 4756, 'https://www.etix.com/ticket/v/3536/mark-ridleys-comedy-castle',
     'https://www.comedycastle.com/events/', '{}'::jsonb),
    (5865, 8715, 'https://www.etix.com/ticket/v/6228/robins-theatre',
     'https://robinstheatre.com/events/',
     '{"comedy_filter":true,"excluded_event_titles":["O Christmas Tea: A British Comedy"]}'::jsonb),
    (5878, 8730, 'https://www.etix.com/ticket/v/31604/the-original-pittsburgh-winery',
     'https://pittsburghwinery.com/events/', '{"comedy_filter":true}'::jsonb),
    (5943, 9072, 'https://www.etix.com/ticket/v/20795/des-plaines-theatre',
     'https://desplainestheatre.com/events/category/comedy/',
     '{"comedy_filter":true,"comedy_title_allowlist":["terry fator"]}'::jsonb),
    (5944, 9073, 'https://www.etix.com/ticket/v/16722/raue-center-for-the-arts',
     'https://events.rauecenter.org',
     '{"comedy_filter":true,"excluded_event_titles":["Sitting Down to Stand Up Comedy Class"]}'::jsonb)
) AS repair(id, club_id, old_url, new_url, extra_metadata)
WHERE source.id = repair.id AND source.club_id = repair.club_id
  AND source.scraper_key = 'etix' AND source.enabled
  AND source.source_url = repair.old_url;
