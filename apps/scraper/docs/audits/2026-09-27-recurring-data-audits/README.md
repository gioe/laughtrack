# TASK-4059 — recurring production anomaly audit

The daily scraper workflow now retains read-only anomaly evidence even when a
scraper partition or finalization fails. Findings request review; they never
merge identities, delete events, guess duration units, or change moderation.

## Commands and retained output

From `apps/scraper/`:

```sh
PYTHONPATH=src .venv/bin/python3 -m scripts.core.audit_scraping_data --json --output audit-results/data-audit.json
PYTHONPATH=src .venv/bin/python3 -m scripts.core.check_scraping_source_invariants --json
```

The main audit exits 0 for a completed report, including review findings, and 1
for execution errors. Source coverage exits 2 when active visible venues have
stale/absent evidence, 0 otherwise, and 1 for execution errors. The workflow
turns code 2 into an annotation and preserves genuine errors as failures.
No extra notifications are sent. The existing daily schedule is 21:00 UTC.

The independent `audit_data` job uses `always()` after the scraper phases and
uploads exactly `data-audit.json` and `source-invariants.json`, retained for
30 days under `scraper-data-audit-<run_id>`. Main report examples default to ten
IDs per metric; complete counts are not truncated. `--days` defaults to a
365-day future-show window and accepts 1–730; `--sample-limit` accepts 0–100.
Podcast duration checks cover stored episodes at all dates.

The default human output is the anomaly summary. `--legacy` additionally prints
the historical inventory/ticket tables, now import-safe and read-only. It is
not used in retained scheduled reports.

## Interpretation and thresholds

Each review metric has an explicit threshold of one affected entity/group;
informational metrics have no warning threshold. The JSON declares both status
and threshold. Potential show exposure means upcoming inventory at visible
venues, not a guarantee that every discovery surface otherwise accepts it.

- False-lineup candidates reuse the ingestion detector. These require review,
  since name patterns do not prove a person is fictional.
- Cross-venue and different-room candidates require a shared event identity and
  instant. Shared calendars without event IDs and different event IDs are not
  collapsed. Eventbrite title-slug variants normalize by numeric event ID.
  Stale room candidates additionally require both a fresh and a >7-day-old
  (or missing) refresh. No deduplication is performed.
- Missing ZIP counts distinguish US, other-country and unknown-country venues.
  Producer or multi-location records require human interpretation.
- Missing/invalid timezone means unknown local time; UTC midnight is never
  substituted. Known local-midnight events remain review candidates.
- Source coverage uses seven-day persisted show evidence, including historical
  shows. Known aggregate scraper keys or organizer attribution establish indirect
  coverage. Other fresh writes are informational. Missing direct source alone
  never establishes an outage. Main summary coverage uses upcoming-show evidence;
  the dedicated source report also sees historical writes.
- Shared handles normalize case, whitespace and leading @ across Instagram,
  TikTok and YouTube. Only separate visible roots are collisions; legitimate
  linked aliases are excluded. Visible children of hidden parents are separate
  review findings. Neither check authorizes an automatic merge or suppression.
- Durations follow `parse_duration_seconds`: 1–86400 whole seconds. Over-day and
  nonpositive values are reported separately; 6–24-hour content is valid and
  informational. Legacy zeros are a baseline, not proof of a new regression.
  Source labels and retained duration-field provenance are separate dimensions.
- Per-club `num_shows` is extraction, not persistence. Failed fetch/error signals
  with output mean partial; blocked empty output is distinct from recovery with
  complete fetches. Missing legacy counters mean unknown. New target/fetch
  counters survive aggregation, partition roundtrip, and `raw_stat` persistence.
  Global save/validation failures are retained per run, never attributed to a
  club. Partition and merged snapshots overlap and must not be summed.

## Safety and validation

Both query paths enforce database read-only transactions. The main collector
uses a repeatable snapshot with a 120-second per-query timeout; source coverage
uses a 60-second timeout. Queries select required columns and scalar evidence
only. Reports never copy arbitrary source metadata, podcast payloads, error
strings, or authenticated URLs. Synthetic nested API-key/password/token fixtures
verify this before artifact publication; main output is written atomically.

Production execution succeeded with these read-only paths. The source audit
returned 2 for retained review findings (not a query error). The timestamped main
report is adjacent; source coverage is retained here as counts and ten examples,
while scheduled artifacts retain the complete whitelisted source report.

Regression coverage includes all task criteria, counter persistence, workflow
structure, and execution of the workflow shell exit-code handling. Existing
timezone tests were updated because they required the UTC fallback now removed.
No production records were changed by validation.

## Production snapshot

Main audit timestamp: 2026-09-27T22:10:25.219307+00:00. Upcoming visible-venue inventory in its window: 41,227 shows.

| Metric | Count | Affected upcoming shows | Status |
| --- | ---: | ---: | --- |
| suspicious_lineup_identities | 0 | 0 | clear |
| cross_venue_event_candidates | 129 | 258 | review |
| room_duplicate_candidates | 0 | 0 | clear |
| stale_room_duplicate_candidates | 0 | 0 | clear |
| missing_zip_us | 8 | 186 | review |
| missing_zip_unknown_country | 2 | 79 | review |
| missing_zip_other_country | 2 | 106 | review |
| aggregate_covered_without_direct_source | 616 | 2319 | info |
| unverified_source_coverage | 30 | 184 | info |
| unknown_local_time | 20 | 20 | review |
| local_midnight_candidates | 83 | 83 | review |
| unlinked_social_handle_identities | 4 | 74 | review |
| visible_alias_hidden_parent | 0 | 0 | clear |
| podcast_duration_over_day | 0 | n/a | clear |
| podcast_duration_nonpositive | 1301 | n/a | review |
| podcast_duration_valid_long_form | 282 | n/a | info |
| run_health_healthy_productive | 0 | 0 | clear |
| run_health_healthy_empty | 0 | 0 | clear |
| run_health_recovered_productive | 0 | 0 | clear |
| run_health_partial_productive | 13 | 983 | review |
| run_health_blocked_empty | 21 | 1467 | review |
| run_health_failed | 27 | 662 | review |
| run_health_unknown | 1762 | 35611 | info |
| run_persistence_failures | 24 | 0 | review |

Source coverage snapshot: 2026-09-27T22:01:32.893614+00:00. 655 venues have recent aggregate evidence; 142 active visible venues require coverage review. These are not confirmed broken scrapers.
