# TASK-1953 - SeatEngine Priority-0 Parallel Source Audit (2026-05-06)

TASK-1950 found clubs where a classic `seatengine` source and a
`seatengine_v3` source were both configured at `priority=0`, causing parallel
nightly attempts for the same club. This audit re-ran the duplicate-source
query against the live scraper database on 2026-05-06 and recorded a
per-club disposition.

The live database still has the pre-typed `scraping_sources.external_id`
column shape, so the query below intentionally uses `external_id` rather than
the newer Prisma-side typed id columns.

## Query

```sql
WITH parallel_clubs AS (
    SELECT club_id
    FROM scraping_sources
    WHERE priority = 0
      AND platform IN (
          'seatengine'::"ScrapingPlatform",
          'seatengine_v3'::"ScrapingPlatform"
      )
    GROUP BY club_id
    HAVING COUNT(*) > 1
       AND COUNT(DISTINCT platform) > 1
),
club_show_stats AS (
    SELECT
        club_id,
        COUNT(*) AS total_shows,
        COUNT(*) FILTER (WHERE date >= CURRENT_DATE) AS future_shows,
        MAX(last_scraped_date) AS latest_scraped
    FROM shows
    GROUP BY club_id
)
SELECT
    c.id AS club_id,
    c.name,
    c.status,
    c.visible,
    c.website,
    COALESCE(st.total_shows, 0) AS total_shows,
    COALESCE(st.future_shows, 0) AS future_shows,
    st.latest_scraped,
    ss.id AS source_id,
    ss.platform,
    ss.scraper_key,
    ss.external_id,
    ss.source_url,
    ss.priority,
    ss.enabled,
    ss.metadata
FROM parallel_clubs pc
JOIN clubs c ON c.id = pc.club_id
JOIN scraping_sources ss
  ON ss.club_id = c.id
 AND ss.priority = 0
 AND ss.platform IN (
     'seatengine'::"ScrapingPlatform",
     'seatengine_v3'::"ScrapingPlatform"
 )
LEFT JOIN club_show_stats st ON st.club_id = c.id
ORDER BY c.id, ss.platform::text, ss.id;
```

## Summary

The query returned 6 clubs / 12 `scraping_sources` rows.

| club_id | club | visible | shows | latest_scraped | source rows | disposition |
|--------:|------|---------|------:|----------------|-------------|-------------|
| 144 | The Comedy Studio | true | 221 total / 153 future | 2026-05-06 07:01 UTC | ss=943 `seatengine` id 631; ss=485 `seatengine_v3` id cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3 | Repoint priority: keep v3 at priority 0 and move or disable classic v1. Both endpoints currently return 151 records, so the duplicate is live, not dormant. Running both at priority 0 is redundant and risks duplicate upsert churn. |
| 147 | Cafe CODA | false | 0 | never | ss=907 `seatengine` id 565; ss=330 `seatengine_v3` id e7ea1e53-8a31-48b6-bfe4-fd9672791615 | Disable duplicate rows or leave hidden/no-op until cleanup. Both endpoints returned 0 records and the club is hidden. |
| 568 | The Brick Room | true | 0 | never | ss=892 `seatengine` id 548; ss=359 `seatengine_v3` id c5595eca-1589-485a-9488-e01d4d455d76 | Already handled by TASK-1950. Both rows are disabled with `metadata.task_1950_disposition.kind = stub_dormant`. |
| 583 | Cultural Center for the Arts with Krackpots Comedy Club | false | 0 | never | ss=905 `seatengine` id 563; ss=158 `seatengine_v3` id 58a56237-0902-40c0-8e4b-e592e782aec0 | Disable duplicate rows or leave hidden/no-op until cleanup. Prior migration says v1 id 563 is dead and v3 is canonical, but the club is hidden and both endpoints returned 0 records. |
| 589 | Midtown Comedy Lounge | true | 0 | never | ss=911 `seatengine` id 569; ss=426 `seatengine_v3` id 364f13ff-86b9-479f-9720-bd191e285ac3 | Already handled by TASK-1950. Both rows are disabled with `metadata.task_1950_disposition.kind = stub_dormant`. |
| 602 | Laugh And Enjoy | false | 0 | never | ss=924 `seatengine` id 586; ss=460 `seatengine_v3` id c91f790c-4cb1-41cd-84fc-bee3b91a0b61 | Disable classic v1 duplicate. Prior migration `20260502195959_hide_laugh_and_enjoy_pending_opening` intended this exact state, but live DB still has ss=924 enabled. Keep verified v3 row for reopening. |

## Source Probe

For the four still-enabled duplicate clubs, each source was fetched through the
scraper's own SeatEngine clients without writing to the DB:

| club_id | source | records returned |
|--------:|--------|-----------------:|
| 144 | `seatengine` 631 | 151 |
| 144 | `seatengine_v3` cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3 | 151 |
| 147 | `seatengine` 565 | 0 |
| 147 | `seatengine_v3` e7ea1e53-8a31-48b6-bfe4-fd9672791615 | 0 |
| 583 | `seatengine` 563 | 0 |
| 583 | `seatengine_v3` 58a56237-0902-40c0-8e4b-e592e782aec0 | 0 |
| 602 | `seatengine` 586 | 0 |
| 602 | `seatengine_v3` c91f790c-4cb1-41cd-84fc-bee3b91a0b61 | 0 |

## Recommended Follow-Up

1. File or run a disposition migration for the remaining enabled duplicates:
   - club 144: keep `seatengine_v3` as the canonical active priority-0 source;
     disable or demote classic `seatengine` ss=943.
   - club 602: disable classic `seatengine` ss=924; this matches the intended
     prior migration comment.
   - clubs 147 and 583: because both clubs are hidden and have no show history,
     either disable both rows as cleanup or fold them into the broader hidden
     club cleanup backlog.
2. Re-run the query above after disposition. The expected remaining rows should
   be only already-disabled historical pairs, or no rows if the query is changed
   to filter `enabled = true`.
