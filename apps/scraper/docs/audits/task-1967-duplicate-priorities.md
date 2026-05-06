# TASK-1967 — Enabled `scraping_sources` Duplicate-Priority Audit (2026-05-06)

TASK-1953 audited the SeatEngine slice of the duplicate `(club_id, priority)`
problem. TASK-1967 generalises the check across every platform, ships a
repeatable script
(`apps/scraper/scripts/core/check_duplicate_scraping_priorities.py`,
runnable as `make check-scraping-priorities`), and records this snapshot of
the live state plus a recommendation on whether to harden the schema with a
partial unique index.

The convention that primary source is `priority=0` and fallbacks are `1+`
(see `tusk conventions search scraping_sources`) implies that two enabled
rows at the same priority are ambiguous: the scraper has no deterministic
ordering between them, so both run, both produce show inserts, and any
`no events found` warnings get amplified.

## Live snapshot

Run on 2026-05-06 against the production scraper DB:

```
$ make check-scraping-priorities
❌ 21 duplicate (club_id, priority) group(s) found with multiple enabled scraping_sources rows
```

All 21 groups are at `priority=0`. Every group contains exactly two enabled
rows, and exactly one of those two rows has `platform = seatengine`. The
other row is the venue's manually-configured primary on a different platform.
Distribution of the non-SeatEngine sibling platform:

| sibling platform | groups |
|------------------|-------:|
| `custom`         | 7 |
| `eventbrite`     | 3 |
| `ticketmaster`   | 3 |
| `crowdwork`      | 2 |
| `wix_events`     | 1 |
| `squadup`        | 1 |
| `simpletix`      | 1 |
| `jetbook`        | 1 |
| `showpass`       | 1 |
| `showslinger`    | 1 |

Per-club detail (taken from the script's stdout):

| club_id | club | visible | sibling rows |
|--------:|------|---------|--------------|
|  80 | Uptown Theater | true  | ss=101 `custom` (uptown_theater); ss=931 `seatengine` ext=617 |
| 140 | Laugh Boston | true  | ss=444 `custom` (laugh_boston); ss=672 `seatengine` ext=34 |
| 143 | Nick's Comedy Stop | true  | ss=510 `wix_events` ext=comp-m4t1prev; ss=735 `seatengine` ext=136 |
| 158 | The Comedy Store | true  | ss=167 `custom` (comedy_store); ss=848 `seatengine` ext=488 |
| 223 | Post Office Cafe | true  | ss=209 `custom` (post_office_cafe); ss=660 `seatengine` ext=20 |
| 308 | Funny Bone Columbus | true  | ss=191 `ticketmaster` (live_nation) ext=Z7r9jZadLM; ss=711 `seatengine` ext=105 |
| 317 | Dayton Funny Bone | true  | ss=210 `ticketmaster` (live_nation) ext=Z7r9jZa7KA; ss=719 `seatengine` ext=114 |
| 323 | Albany Funny Bone | true  | ss=193 `ticketmaster` (live_nation) ext=Z7r9jZa7eK; ss=722 `seatengine` ext=120 |
| 327 | the Comedy Shoppe | true  | ss=617 `showslinger` (show_slinger); ss=726 `seatengine` ext=124 |
| 506 | Rails Comedy | true  | ss=578 `crowdwork` (rails_comedy); ss=843 `seatengine` ext=482 |
| 510 | Comedy Blvd | false | ss=423 `eventbrite` ext=43929578463; ss=846 `seatengine` ext=486 |
| 552 | The Bit Theater | true  | ss=235 `custom` (the_bit_theater); ss=880 `seatengine` ext=532 |
| 571 | Sunset Strip | true  | ss=216 `squadup` ext=9086799; ss=895 `seatengine` ext=551 |
| 575 | The Attic Comedy Club | true  | ss=401 `eventbrite` ext=113948356841; ss=899 `seatengine` ext=555 |
| 593 | National Lampoon The Yellow Door | true  | ss=152 `eventbrite` ext=87966212103; ss=915 `seatengine` ext=577 |
| 786 | ImprovCity | true  | ss=350 `simpletix`; ss=767 `seatengine` ext=203 |
| 794 | The Improv Collective | true  | ss=37  `jetbook`; ss=772 `seatengine` ext=214 |
| 796 | The Backline | true  | ss=452 `crowdwork` (the_backline); ss=774 `seatengine` ext=217 |
| 817 | Laughing Skull | true  | ss=111 `custom` (json_ld); ss=791 `seatengine` ext=250 |
| 818 | The Comedy Cave | true  | ss=57  `showpass`; ss=792 `seatengine` ext=251 |
| 826 | The Comedy Club On State | false | ss=553 `custom` (json_ld); ss=798 `seatengine` ext=265 |

## Root cause

Every flagged group fits the same pattern: a manually-configured primary
source plus an auto-discovered `seatengine` row inserted by the
`seatengine_national` discovery scan.

`UPSERT_CLUB_BY_SEATENGINE_VENUE` in `apps/scraper/sql/club_queries.py:226`
unconditionally inserts at `(platform='seatengine', priority=0,
enabled=TRUE)`. Its `ON CONFLICT (club_id, platform, priority)` clause only
deduplicates against an existing `seatengine` row at priority 0; it does
not consider whether the club already has a primary on a different
platform. The existing TASK-1966 disposition note records that this is
also why prior `enabled=false` migrations get reverted: `seatengine_national`
runs nightly, the SE venue ID still resolves to a real name, and the upsert
flips the row back to `enabled=TRUE`. This is a venue-scoped bug, but it
manifests at the `(club_id, priority)` shape the schema currently does not
guard.

## Intentional multi-source exceptions

**None today.** Every duplicate group in the snapshot above is unintentional
drift from the discovery upsert; none of them is a deliberately-parallel
configuration whose answer is "leave both running."

The check script's `_INTENTIONAL_EXCEPTIONS` dict is therefore empty as of
this commit. New entries must carry a rationale string referencing the task
that approved the exception, so additions are auditable. Adding an entry
suppresses the duplicate from the script's failure output (and from the
exit-2 signal) while keeping it visible in the `excepted_groups` JSON
section, so the audit trail is preserved.

## Recommendation: defer the partial unique index

A natural hardening would be a partial unique index of the shape

```sql
CREATE UNIQUE INDEX scraping_sources_club_priority_enabled_unique
    ON scraping_sources (club_id, priority)
    WHERE enabled = true;
```

This would prevent any future cross-platform priority collision at the DB
layer. **Do not apply it yet.** Two reasons:

1. **It would crash `seatengine_national` against 20 of the 21 currently
   affected venues.** The discovery upsert's `ON CONFLICT (club_id,
   platform, priority)` clause does not match a different-platform sibling,
   so the second-platform `INSERT` would hit the new partial unique
   constraint instead of being deduplicated. The upsert presently runs
   inside a transaction per venue; adding the index without first fixing
   the upsert would convert today's silent drift into a nightly hard error
   on every affected venue.
2. **The right shape of the upsert fix is not obvious without dispositioning
   the existing inventory first.** Some of the 21 cases (e.g. clubs 308 /
   317 / 323 — Funny Bone venues with both Ticketmaster and SeatEngine) are
   probably legitimate fallback configurations that have been mis-set to
   `priority=0` rather than `priority=1`. Others (the `custom` siblings
   that share a `scraper_key` with the venue's own scraper module) are
   probably "auto-discovered SeatEngine should be disabled". Until each
   case has a recorded disposition, we don't know whether the upstream fix
   should demote auto-discovered rows to `priority=1`, skip the insert
   when a primary exists on another platform, or honour a
   `metadata.task_*_disposition` stamp the way TASK-1950 / TASK-1924 /
   TASK-1966 did one venue at a time.

The recommended sequencing is therefore:

1. **(this task)** Land the repeatable check + this audit so future drift
   is detectable.
2. **(follow-up)** Disposition the 21 cases — for each club, decide whether
   the auto-discovered SeatEngine row should be disabled, demoted to
   `priority=1`, or kept (because SeatEngine is genuinely the canonical
   source and the other row is the stale one). The check script's `--json`
   output is designed to be the input format for a batch disposition
   script.
3. **(follow-up)** Once the live count is zero, change
   `UPSERT_CLUB_BY_SEATENGINE_VENUE` (and its v3 sibling) to either insert
   at the lowest unused priority for the club or skip the insert when a
   non-SeatEngine enabled row already exists at `priority=0`. The behaviour
   change is structural and warrants its own task.
4. **(follow-up)** Add the partial unique index as the trailing safety net
   once the upsert and the inventory both invariably maintain the property.

The check shipped here is the durable signal that gates each step: it stays
in CI / cron and exits non-zero whenever the count climbs back above zero,
so regressions can't silently re-accumulate.

## Re-running

```bash
cd apps/scraper
make check-scraping-priorities                              # human report, exits 0/2
make check-scraping-priorities ARGS='--json' > out.json      # machine-readable
```

Exit codes:

- `0` — clean (no unexcepted duplicate groups)
- `1` — DB / configuration error (printed to stderr)
- `2` — at least one unexcepted duplicate group remains
