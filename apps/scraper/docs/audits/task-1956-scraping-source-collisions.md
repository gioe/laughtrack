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

## Verification

After applying `apps/scraper/migrations/20260506_resolve_scraping_source_collisions.sql`,
the reproduction query at the top of this document should return **8
rows** (the deferred cases). Each remaining row has an inline
justification in the migration file referencing the follow-up task.
