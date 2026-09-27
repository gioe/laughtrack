# TASK-4057: untrusted podcast duration repair

Snapshot: 2026-09-27 13:04 UTC. The database contained 612,624 episodes,
including 1,002 durations above 86,400 seconds. All 1,002 retained RSS
itunes_duration fields; their source labels were 1,001 podcast_index and one
itunes. Source labels do not identify the latest ingestion path.

| Podcast | Rows | Stored seconds |
|---|---:|---:|
| Fight Laugh Feast USA | 996 | 86,921–35,024,207 |
| Hyperfixation Investigations | 2 | 158,665–159,360 |
| Brandon Women's Bible Study | 1 | 172,740 |
| Who Invited Her? | 1 | 1,631,523,781 |
| The Wretched | 1 | 110,004 |
| B.O.P I Decided | 1 | 108,720 |

None of these episodes had appearances or an accepted association with a
visible comedian at snapshot time. This does not mean they cannot appear on
other surfaces. The cohort is retained in cohort.json with explicit fields;
no feed configuration or credentials are exported.

## Policy

The shared parser accepts positive whole seconds from 1 through 86,400,
including M:SS and H:MM:SS. In M:SS, minutes can exceed 59; in H:MM:SS,
minutes and seconds must be below 60. ASCII digits and surrounding whitespace
are accepted; signed values, decimals, booleans, malformed components, zero,
and values above one day become unknown (NULL). Leading zeros are allowed.

Twenty-four hours is a conservative metadata-confidence limit, not proof
that longer recordings cannot exist. Six-, twelve-, and twenty-four-hour
recordings remain supported. Longer recordings remain playable but their
unverified duration is withheld. No millisecond conversion or alternative
interpretation of 44:16:00 is guessed. Raw source_payload remains available
for future evidence-based correction. This is not an audio-length probe.

Both RSS sync and PodcastIndex backfill use the shared parser. Same-source
upserts assign NULL directly, rather than retaining an old invalid duration.

## Repair and verification

Migration 20260927131500_clear_untrusted_podcast_durations archives original
identity, duration and timestamps in podcast_duration_repairs_4057, then
clears only over-day rows with RSS duration provenance. It does not delete
episodes or alter source payloads, associations, or appearances. Existing
zero values (1,301 at snapshot) are outside this audited repair; future
ingestion treats zero as unknown. The 282 stored values between six and
24 hours were preserved, not individually certified as accurate.

Before production application, the exact SQL was rehearsed against
session-local PostgreSQL tables copied from all 1,002 outliers plus those
282 long-form controls. Assertions verified repair count, unchanged control
rows, whole-row equality on repeat execution, whole-row equality after
rollback, and preservation of a later corrected value during rollback.
The real same-source upsert SQL was then run twice on the retained
Who Invited Her RSS payload in the shadow table; duration stayed NULL.
All 1,002 raw outlier values also reparse to unknown. verification.json
records results. Temporary tables used their own sequence, never public IDs.

The migration contains guarded rollback SQL. It restores a value only while
identity and repaired timestamp still match and duration is still NULL, so
later corrections or resyncs are not overwritten. Keep the archive after
rollback. Re-running the migration does not overwrite an existing archive
or repeat a previously archived repair after a later sync.

Production application results are recorded separately in production.json.
