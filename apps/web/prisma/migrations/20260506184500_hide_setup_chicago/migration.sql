-- Hide The Setup Chicago (club 660).
--
-- Verification on 2026-05-06:
--   * The configured Stagetime CSV source 138 returns only the header row.
--   * The club has never produced DB show rows.
--   * The official /chicago page returns HTTP 404, while /vancouver still returns 200.
--   * The homepage title now lists SF, LA, and NYC, omitting Chicago.
--
-- Keep the club status active rather than closed/hiatus because there is no explicit
-- public closure notice; hide it and disable the source until The Setup restores a
-- Chicago listing or publishes future Chicago dates.
UPDATE clubs
SET visible = false
WHERE id = 660
  AND name = 'The Setup Chicago';

UPDATE scraping_sources
SET enabled = false,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_1973_disposition',
        jsonb_build_object(
            'kind', 'program_winding_down',
            'verified_at', '2026-05-06',
            'reason', 'Official Chicago page is gone and the Stagetime feed is header-only; hide until a live Chicago source returns.',
            'evidence', jsonb_build_array(
                'https://setupcomedy.com/chicago returned HTTP 404',
                'https://setupcomedy.com/vancouver returned HTTP 200',
                'source CSV for scraping_sources.id=138 returned only date/day/time/title/venue/city/ticket_url/urgency_tag/sold_out header',
                'club 660 has zero historical shows in the database'
            )
        )
    ),
    updated_at = NOW()
WHERE id = 138
  AND club_id = 660
  AND platform = 'stagetime'::"ScrapingPlatform"
  AND scraper_key = 'setup';
