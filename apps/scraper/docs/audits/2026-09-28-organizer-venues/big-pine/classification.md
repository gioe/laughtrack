# Big Pine classification reconciliation

Big Pine remains a visible festival intentionally. Its continued presence in `clubs` is not evidence that TASK-3027 was unapplied or that a deleted venue was recreated.

The June 20 TASK-3027 commit `27fe8cb149b5ac552557d51257b03d9359535a45` shipped `apps/scraper/migrations/20260620_backfill_club_location_records_google_places.sql`. Although criterion 9788 broadly described moving festivals out of clubs, the actual migration explicitly exempted Big Pine: the schema represented festivals as `clubs.club_type='festival'`. It classified row 573 as a festival and described its address as multiple venues in Arizona; it did not move or delete it.

TASK-3028's `apps/web/prisma/migrations/20260620040000_add_source_targets/migration.sql` formalized non-venue scraper targets. Its comments expressly retained festivals in `clubs`. It moved Ticketmaster National from club 4036 to source target 1 and transferred source 3126, with dependent-row checks before removing the old club.

TASK-3031's subsequent disposition script, introduced in `d397313d8e17976dbb3b502a602d0b72215b182b`, made the Big Pine decision explicit: `target_visible=True`, `target_club_type='festival'`, address `Festival based in Chandler, AZ`, source 360 left enabled. The script now lives at `apps/scraper/scripts/archive/disposition_non_venue_club_rows_2026_06_20.py` after TASK-3645 archived it. Those target fields match the September 28 production snapshot.

The current schema and queries still support festivals as a club type; `ClubQueries.GET_ACTIVE_FESTIVAL_IDS` selects them using upcoming shows. The collection therefore should not be blanket hidden, converted to a physical venue, or assigned the generic JSON-LD street address simply to satisfy a missing-ZIP audit.

## Current event-level defect

All 19 upcoming Big Pine records have matching event-specific source dates, but none is an ordinary audience performance:

| Source-backed category | Rows |
| --- | ---: |
| Digital downloads | 6 |
| Digital EPK/social-media review services | 5 |
| Individually scheduled coaching consultations | 3 |
| Fall educational camp sessions | 2 |
| Winter workshop/panel passes | 2 |
| Multi-city networking game | 1 |

`shows.json` records all IDs, source URLs, retrieval times, page digests, brief supporting excerpts and a location assessment. The fall camp names Mic Drop Mania in Chandler; the winter pass does not establish a specific physical event venue. The networking game spans San Diego, Phoenix/Chandler and Plano. The generic JSON-LD on every page names Big Pine at 51 E. Boston St.; it is not reliable evidence that a download or virtual consultation is a performance at that address. Geoff Grooms's consultation is clearly individually scheduled, but the captured page does not establish its delivery modality; the audit does not label it virtual without evidence.

Source 360 has empty metadata. `SeatEngineScraper.get_data` applies opt-in title patterns and comedy filtering only when configured; otherwise the full inventory proceeds. `SeatEngineClient.create_show` assigns the configured club ID. Existing source-specific title exclusion support should be evaluated before adding a general classifier. A generic comedy-keyword filter alone would be unsafe because these non-performance products use comedy vocabulary.

The focused repair must filter verified non-performance inventory, inspect dependent rows before bounded cleanup, and preserve the festival and enabled source. If all 19 rows are excluded, an empty feed is not permission to bypass reconciliation safeguards. Revalidate current source inventory and explicitly verify the cleanup result.

## Preserve intentional system targets

`platform-targets.json` records the current non-venue targets: Ticketmaster National (target 1, source 3126) and Pabst Theater Group (target 2, source 7146). Both are enabled and hidden, with source ownership on `source_target_id` and no club owner. These are intentional system records and must not be geocoded, deleted, or conflated with Big Pine's visible festival identity.

No classification, address, visibility, source configuration or production show was changed in TASK-4065. The apparent conflict with TASK-3027 is resolved by its explicit migration exception and the later disposition, while the current non-performance ingestion defect is tracked separately.
