# TASK-1956 — `scraping_sources` (platform, external_id) Collision Audit (2026-05-06)

After TASK-1951 fixed the `(seatengine, 487)` collision between The Well
Comedy Club (club 77) and Wicked Funny Comedy Club North Andover (club 82),
a survey of `scraping_sources` surfaced ~30 more `(platform, external_id)`
pairs where two distinct `club_id`s share the same upstream venue ID. Each
is a latent silent-mismap bug — any audit/disposition/dedup tool that joins
on `(platform, external_id)` attributes one club's data to the other
(this is exactly what masked The Well's scraping in TASK-1951).

This audit re-ran the collision query on 2026-05-06, probed the upstream
SeatEngine API for the canonical `(platform, external_id) → name` mapping,
classified every pair, and recorded a per-case resolution decision.

## Reproduction query

```sql
SELECT platform,
       external_id,
       COUNT(DISTINCT club_id),
       ARRAY_AGG(club_id ORDER BY club_id)
  FROM scraping_sources
 WHERE external_id IS NOT NULL AND external_id != ''
 GROUP BY platform, external_id
HAVING COUNT(DISTINCT club_id) > 1
 ORDER BY platform, external_id;
```

## 2026-05-06 snapshot

**Total collisions: 35** (5 eventbrite, 29 seatengine, 1 squadup).

Pattern breakdown:

| Pattern | Count | Resolution |
|---|---|---|
| `A_MANUAL_HAS_STALE_ID` | 21 | Clear `external_id` on the manually-configured `seatengine_classic` row (the API canonical name does not match this club; the classic scraper does not consume `external_id` so clearing is functionally a no-op) |
| `D_BOTH_WRONG_DEAD_VENUE` | 1 | Clear `external_id` on both rows (SE API returns an empty venue — upstream record deleted) |
| `EB_DUPE_DISABLED_GHOST` | 5 | Clear `external_id` on the already-disabled+hidden ghost row of each Eventbrite duplicate-club pair |
| `B_BOTH_MATCH_SAME_VENUE_DUPE` | 1 | Defer — same venue represented by two clubs; needs merge/disable decision |
| `C_BOTH_AUTO_DISCOVERED` | 6 | Defer — both rows auto-discovered against the same SE venue but pointing at different clubs; needs merge/disable decision |
| `SQ_BOTH_VISIBLE_DUPE` | 1 | Defer — Sunset Strip duplicate club; needs merge/disable decision |

**Resolved by this task: 27 collisions.**
**Deferred (follow-up tasks filed): 8 collisions.**

## Why "clear `external_id`" rather than "fix `external_id`"

For Pattern A and Pattern D, the manually-configured row has scraper key
`seatengine_classic`, which scrapes the venue's own SeatEngine HTML page
from `source_url` directly (`buffalo.heliumcomedy.com/events`,
`thecomedycatch.com/events`, etc.) — it does **not** consume
`scraping_sources.external_id`. The id was populated long ago and is
either stale or simply wrong. Setting it to a "correct" SeatEngine venue
ID would require enumerating SE's full venue space and matching by
website per case (~30 venues), a much larger investigation with no
runtime benefit. Clearing the wrong id removes the collision and removes
the latent mismap risk without adding new state.

For Pattern EB, the ghost row is already `enabled=false` and the club
is already `visible=false`. The collision is metadata residue from the
duplicate-club artifact; clearing the disabled row's `external_id` is a
zero-impact metadata cleanup.

## Per-case results

The full per-case breakdown — including SE API responses, name/site
match comparisons, and recommended action — is captured in
`apps/scraper/docs/audits/task-1956-collision-data.json` next to this
file. The disposition script
`apps/scraper/scripts/core/disposition_scraping_source_collisions_2026_05_06.py`
applies the resolutions, stamps `metadata.task_1956_disposition` on every
modified row with the SE API canonical name + per-row rationale, and
follows the TASK-1962 / TASK-1966 / TASK-1979 dataclass pattern (per
convention #79 — Python disposition script under `scripts/core/`, not
a raw SQL migration).

### Pattern A (21 cases): manually-configured row has stale `external_id`

Each entry: `(platform, external_id) → SE_API_name | wrong_club_id [name] / canonical_club_id [name]`. The `wrong_club_id`'s `external_id` is cleared.

| ext | SE API name | Wrong row (cleared) | Auto row (kept) |
|----:|---|---|---|
|  21 | Helium & Elements Restaurant | — | (Pattern B; see deferred) |
| 132 | Levé's 2015 Charity Ball | club 108 (Helium & Elements -St. Louis) | club 334 |
| 157 | Royal Comedy Theatre | club 1031 (Tacoma Comedy Club - Downtown) | club 359 |
| 338 | Nauti Parrot Dock Bar | club 69 (The Comedy Club of Kansas City) | club 368 |
| 359 | HOUSE OF COMEDY | club 90 (Bricktown Comedy Club) | club 388 |
| 368 | Campus JAX Charities | club 79 (Underground Comedy) | club 394 |
| 389 | House of Laffs | club 72 (The Comedy Vault) | club 414 |
| 392 | Bridgestone Comedy | club 75 (The Dojo of Comedy) | club 417 |
| 402 | Sandman Comedy Club | club 58 (The Comedy Zone - Charlotte) | club 427 |
| 419 | Boulder Comedy Show | club 123 (Planet Of The Tapes) | club 444 |
| 425 | Kes Test 2 | club 67 (The Comedy Catch) | club 450 |
| 442 | Rahmein Presents... | club 43 (Brokerage Comedy Club) | club 467 |
| 443 | The Caravan Fundraisers | club 42 (McGuire's Comedy Club) | club 468 |
| 448 | Matt Stanley | club 57 (The Comedy Zone Greensboro) | club 473 |
| 453 | Secret Island | club 59 (Comedy Zone Jacksonville) | club 478 |
| 460 | Copa Comedy Club | club 116 (Loonees Comedy Corner) | club 484 |
| 466 | The Cave | club 47 (Comedy In Harlem) | club 490 |
| 483 | The All New First Fridays | club 124 (Rooster T. Feathers Comedy Club) | club 507 |
| 504 | Test Site | club 60 (The Comedy Zone - Cherokee) | club 528 |
| 530 | Silly Beaver Comedy Club | club 134 (Helium Comedy Club - Atlanta) | club 550 |
| 561 | Lotus Store | club 92 (Bricky's Comedy Club) | club 581 |
| 564 | Cafe Corretto | club 95 (Coastal Creative) | club 584 |

### Pattern D (1 case): SE API returns empty venue

| ext | SE API | Action |
|----:|---|---|
| 588 | name=`""` (deleted upstream) | Clear `external_id` on **both** rows: club 94 (Capitol Hill Comedy Bar, closed) and club 106 (Emerald City Comedy Club). Both are `seatengine_classic` URL-based scrapers; ids were stale before SE deleted the venue. |

### Pattern EB (5 cases): disabled ghost row of dupe-club pair

| ext | Real club (kept) | Ghost row (cleared) |
|----:|---|---|
| 28808914 | club 160 Laugh Factory Hollywood | club 2273 "Laugh Factory - Hollywood" |
| 35896069 | club 184 The Comedy Bar Chicago | club 2279 "The Comedy Bar - Chicago Main Stage" |
| 41248441 | club 169 Laugh Factory Long Beach | club 2276 "Long Beach Laugh Factory" |
| 60930661 | club 170 Laugh Factory San Diego | club 2277 "Laugh Factory" |
| 90437249 | club 1038 Counter Weight Brewing | club 2288 "Counter Weight Brewing Company" |

## Deferred — same-venue duplicate clubs (8 cases)

These cases are NOT resolvable by clearing one row's `external_id`
because both rows correctly map to the same upstream venue — the bug
is at the **club** level (two `clubs` rows for one physical venue),
not the `scraping_sources` level. Resolving them requires deciding
which club is canonical, merging shows, and hiding/disabling the
duplicate club. Each is filed as a separate follow-up task.

### Pattern B (1 case): one manual + one auto, both correctly mapped

| ext | SE API canonical | Members |
|----:|---|---|
| 21 | Helium & Elements Restaurant (heliumcomedy.com/buffalo) | club 132 (visible, scraper_key=`seatengine_classic`, 89 future shows) AND club 1077 (hidden, scraper_key=`seatengine`, 88 future shows). Same venue. |

### Pattern C (6 cases): both rows auto-discovered, both name-match SE

| ext | SE API canonical | Members |
|----:|---|---|
| 424 | Laugh Tonight Comedy | club 449 (hidden, 1 fut) + club 855 (visible, 3 fut) |
| 428 | J.R.'s Comedy Club (INSIDE THE JUNKYARD CAFE) | club 453 (hidden, 0 fut) + club 567 (visible, 4 fut) |
| 464 | Greenville Comedy Zone @ Revel Event Center | club 73 (visible, 207 fut) + club 488 (hidden, 0 fut) |
| 493 | Mic Drop Comedy Chandler | club 120 Mic Drop Mania (visible, 275 fut) + club 517 Mic Drop Comedy Chandler (visible, 230 fut) — both actively scraping! |
| 508 | STICKS AND STONES COMEDY CLUB | club 125 (visible, 191 fut) + club 532 (hidden, 11 fut) |
| 556 | Laugh Camp Comedy Club - Saint Paul MN at Camp Bar | club 114 (visible, 50 fut) + club 576 (hidden, 31 fut) |

### Pattern SQ (1 case): SquadUp duplicate

| ext | Members |
|----:|---|
| 9086799 | club 175 Sunset Strip Comedy Club (visible, 107 fut) + club 571 Sunset Strip (visible, 102 fut) — same Austin venue, both `squadup` scraper |

## Verification (2026-05-06 — applied)

`disposition_scraping_source_collisions_2026_05_06.py` ran clean against
prod on 2026-05-06: 28 shape validations passed, 28 rows updated, 0
skipped. Re-running the reproduction query at the top of this document
returns exactly **8 rows** — the deferred same-venue duplicate-club
cases enumerated above:

```
seatengine | ext=21       | clubs=[132, 1077]
seatengine | ext=424      | clubs=[449, 855]
seatengine | ext=428      | clubs=[453, 567]
seatengine | ext=464      | clubs=[73, 488]
seatengine | ext=493      | clubs=[120, 517]
seatengine | ext=508      | clubs=[125, 532]
seatengine | ext=556      | clubs=[114, 576]
squadup    | ext=9086799  | clubs=[175, 571]
```

These 8 are tracked under follow-up **TASK-1984** ("Resolve 8 same-venue
duplicate-club collisions (TASK-1956 deferred)"), which uses the
`fold_clubs` / merge-shows pattern (precedent: TASK-1925's
`scripts/core/fold_big_couch_dup_clubs_row.py`) to fold the duplicate
club into the canonical one. The two highest-urgency cases are ext=493
(Mic Drop Chandler — both clubs visible with 275 + 230 future shows,
actively double-scraping) and ext=9086799 (Sunset Strip Austin — both
visible with 107 + 102 future shows). Each remaining row has an inline
metadata stamp explaining the deferral via the **B / C / SQ** pattern
labels documented in this file's "Deferred" section above; the
disposition script intentionally does not touch them because their
resolution requires a `clubs`-level merge decision, not a
`scraping_sources` mismap fix.

## Schema delta — typed columns (post-TASK-1985)

The reproduction query at the top of this doc references
`scraping_sources.external_id`, which was the generic id column at the
time TASK-1956 ran. **TASK-1985 ('Recover Prisma typed scraping source
migrations') replaced `external_id` with per-platform typed columns**:
`seatengine_id`, `seatengine_v3_id`, `eventbrite_id`,
`ticketmaster_id`, `squadup_id`, `wix_event_id`, `ovationtix_id`. The
original query no longer runs as written. The equivalent typed-column
query (used by TASK-1984 verification and `tusk conventions search
scraping_sources` for the column reference) is:

```sql
SELECT 'seatengine' AS plat, seatengine_id::text AS ext,
       COUNT(DISTINCT club_id), ARRAY_AGG(DISTINCT club_id ORDER BY club_id)
  FROM scraping_sources WHERE seatengine_id IS NOT NULL
 GROUP BY seatengine_id HAVING COUNT(DISTINCT club_id) > 1
UNION ALL
SELECT 'seatengine_v3', seatengine_v3_id, COUNT(DISTINCT club_id),
       ARRAY_AGG(DISTINCT club_id ORDER BY club_id)
  FROM scraping_sources WHERE seatengine_v3_id IS NOT NULL
 GROUP BY seatengine_v3_id HAVING COUNT(DISTINCT club_id) > 1
UNION ALL
SELECT 'eventbrite', eventbrite_id, COUNT(DISTINCT club_id),
       ARRAY_AGG(DISTINCT club_id ORDER BY club_id)
  FROM scraping_sources WHERE eventbrite_id IS NOT NULL
 GROUP BY eventbrite_id HAVING COUNT(DISTINCT club_id) > 1
UNION ALL
SELECT 'ticketmaster', ticketmaster_id, COUNT(DISTINCT club_id),
       ARRAY_AGG(DISTINCT club_id ORDER BY club_id)
  FROM scraping_sources WHERE ticketmaster_id IS NOT NULL
 GROUP BY ticketmaster_id HAVING COUNT(DISTINCT club_id) > 1
UNION ALL
SELECT 'squadup', squadup_id, COUNT(DISTINCT club_id),
       ARRAY_AGG(DISTINCT club_id ORDER BY club_id)
  FROM scraping_sources WHERE squadup_id IS NOT NULL
 GROUP BY squadup_id HAVING COUNT(DISTINCT club_id) > 1
 ORDER BY 1, 2;
```

## Verification (2026-05-06 — TASK-1984 fold applied)

`apps/scraper/scripts/core/fold_task_1984_dup_pairs.py` ran clean
against prod on 2026-05-06: shape validation passed all 16 club refs
and 16 source refs, all 8 targets applied, 622 dupe shows folded into
canonicals (616 colliding deleted via ON DELETE CASCADE, 6 unique
shows on Helium Buffalo's dupe migrated). Per-target deltas captured in
the disposition script's per-pair `task_1984_disposition` metadata
stamp on each dupe `scraping_sources` row, plus a
`task_1984_canonical_pointer` stamp on the canonical row for
discoverability from either side. Re-running the typed-column collision
query above against prod returns **zero rows**, satisfying TASK-1984
acceptance criterion 6512:

```
Collisions remaining: 0
```

The two HIGH urgency cases (ext=493 Mic Drop Chandler, ext=9086799
Sunset Strip Austin) had their dupe club's `visible` flag flipped to
false; the other 6 dupe clubs were already hidden. All 8 dupe
`scraping_sources` rows are now `enabled=false` with the appropriate
typed id (`seatengine_id` or `squadup_id`) cleared to NULL, so future
SE national / SquadUp nightlies will not produce parallel shows on
the dupe clubs.
