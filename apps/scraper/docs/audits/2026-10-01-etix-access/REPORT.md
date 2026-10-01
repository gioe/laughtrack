# TASK-4083: Etix access and verified partial recovery

## Reproduction

On October 1, 2026, each affected venue still had zero stored shows. Three independent single-club workflow runs on main commit 72501def7c10511fa7be6b358cb781c5eb73c59e reproduced HTTP 403, DataDome browser blocking and CapSolver rejection: `ERROR_INVALID_TASK_DATA — invalid task data: blocked captcha url is not supported`.

| Venue | Club / source | Scheduled-environment reproduction |
| --- | --- | --- |
| The Laughing Tap | 9070 / 5941 | [36854217008](https://github.com/gioe/laughtrack/actions/runs/36854217008) |
| Ann Arbor Comedy Showcase | 16122 / 7682 | [36854219802](https://github.com/gioe/laughtrack/actions/runs/36854219802) |
| The Vixen | 9074 / 5945 | [36854222836](https://github.com/gioe/laughtrack/actions/runs/36854222836) |

These workflows use the same residential proxy and CapSolver secret configuration as the scheduled scraper. Each venue reports success=false, bot_block_detected=true, fetches_failed=1 and zero emitted shows, despite the workflow itself completing successfully. Each process made its own initial browser solve; retries in that process subsequently hit the host circuit breaker. The audit does not count those skipped retries as independent solves. Metrics are in baseline-runs.json; before-inventory.json records source configuration and stored counts.

## Authoritative alternative evidence

The scraper's actual HttpClient with curl-cffi and its browser fallback fetched the official sites. source-fetches.json records retrieval times, URLs and content hashes. No generic weekly schedule, ticket slug, doors time or source publication timestamp was promoted into a performance start.

### The Laughing Tap

The official [homepage](https://laughingtap.com/) links directly to seven Milwaukee Comedy Ticket Tailor events. Five provide matching explicit 2026 dates, local showtimes, venue name/ZIP, ticket identity and visible/structured evidence:

| Ticket Tailor event | Local start (America/Chicago) | Title |
| --- | --- | --- |
| [2388761](https://www.tickettailor.com/events/milwaukeecomedy/2388761) | 2026-10-08 19:00 | Laugh A Lot Thursday at MKE Comedy Fest! |
| [2388785](https://www.tickettailor.com/events/milwaukeecomedy/2388785) | 2026-10-09 19:00 | Primetime Laughs at MKE Comedy Fest! |
| [2351156](https://www.tickettailor.com/events/milwaukeecomedy/2351156) | 2026-10-09 22:00 | Late Night Laughs at MKE Comedy Fest! |
| [2351158](https://www.tickettailor.com/events/milwaukeecomedy/2351158) | 2026-10-10 19:30 | Saturday Night Laughs at MKE Comedy Fest! |
| [2351161](https://www.tickettailor.com/events/milwaukeecomedy/2351161) | 2026-10-10 22:00 | Night Owl Comedy at MKE Comedy Fest! |

Two pages are internally inconsistent and must remain excluded: [Matinee Mayhem, 2388786](https://www.tickettailor.com/events/milwaukeecomedy/2388786) advertises October 10 at 16:00 but its description says show starts at 22:00; [Sunday Fun Day, 2388794](https://www.tickettailor.com/events/milwaukeecomedy/2388794) has the same 16:00 versus 22:00 disagreement on October 11. No precedence rule can establish which is correct. Venue/organizer correction is required.

### The Vixen

The official homepage links these dated individual comedy events. Their main descriptions explicitly state doors at 19:30 and **show starts at 20:00**; the full event dates are independently printed on the pages:

- [Zach Albers](https://vixenmchenry.com/event/comedy-zach-albers/): 2026-10-07 20:00 America/Chicago.
- [Andy Beningo](https://vixenmchenry.com/event/comedy-night-andy-beningo/): 2026-10-14 20:00 America/Chicago.
- [Wyatt Feegrado](https://vixenmchenry.com/event/free-stand-up-comedy-night-featuring-wyatt-feegrado/): 2026-10-21 20:00 America/Chicago.

All three explicitly advertise free admission with no cover. The structured/calendar 19:30 timestamp is the doors time; accepting that field as the performance start would be wrong. [Pat Tomasulo on December 19](https://vixenmchenry.com/event/pat-tomasulo/) supplies only doors at 18:00 and remains excluded until an explicit showtime is published or Etix access recovers. Music, DJ and other non-comedy events are excluded.

### Ann Arbor Comedy Showcase

The [official homepage](https://www.aacomedy.com/) now gives Tommy Ryman specific October 1 and 2 starts at 19:15 and October 3 starts at 19:15 and 21:45. However, the performance section supplies no event-specific year. Footer copyright, page-publication dates and the ticket slug ryman26 are not authoritative performance years. Other cards are series dates or general recurring hours; the Comedy Nerdz happy-hour card mixes doors and open-mic times. No machine-verifiable complete dated performance feed was established. The source remains blocked, with no records invented.

## External blocker and resolution conditions

Etix/DataDome rejects the configured runner access and CapSolver rejects the resulting challenge. Vendor-owned resolution requires a supported access path or authoritative venue feed with explicit dated show starts. Current [CapSolver documentation](https://docs.capsolver.com/en/guide/captcha/datadome/) distinguishes solvable t=fe from banned-IP t=bv challenges; Chrome 145 remains listed as supported. The scheduled logs capture the rejection but do not expose the challenge query, so they do not independently prove its exact mode. Changing the user agent or rewriting the challenge URL is not an evidenced fix. No challenge scans, proxy-rotation campaign or weakened bot-block handling was introduced.

To reproduce, dispatch scraper-verify.yml on the merged main branch with club_id 9070, 16122 or 9074, then inspect per_club_stats and the solve rejection in the artifact, rather than relying on GitHub's job conclusion. If the vendor resolves access, rerun these checks and require real persisted performances, explicit showtimes, and clean diagnostics before treating the calendar as complete. TASK-2858 separately owns automated periodic reprobes.

## Implementation and verification

The implementation retains primary source configuration and marks the inaccessible calendar incomplete even when verified alternatives produce shows. This prevents deletion of unseen performances. It handles blocked, empty and nonempty unparseable primary responses; the latter reproduced a missing fallback in the first live check and now has a regression test. Requests are bounded to 12 official-home-linked details with two concurrent fetches and per-fetch timeouts. The focused Etix/Ticket Tailor suite passes 164 tests. The actual read-only scraper returned five Laughing Tap and three Vixen shows with failed-fetch diagnostics retained for each; see readonly-preview.json. The full scraper gate passed after one transient ThunderTix timing-test failure; the unchanged isolated test and full-suite retry passed. TASK-4129 tracks deterministic coverage for that 50 ms budget.

The first branch runner pass exposed a second access boundary: [Laughing Tap run 36875864960](https://github.com/gioe/laughtrack/actions/runs/36875864960) discovered all seven Ticket Tailor links, but direct bare requests received HTTP 403 for every detail. The local eight-show preview was therefore insufficient proof of runner recovery. The detail fetch path now uses the configured proxy/browser HTTP stack, while keeping independent official-home requests unchanged. [Ann Arbor run 36875874464](https://github.com/gioe/laughtrack/actions/runs/36875874464) reproduced the same safely blocked zero-show result. These initial branch metrics are retained in initial-branch-runs.json.

## Final scheduled-environment and production results

| Venue | Runner | Saved shows | Remaining boundary |
| --- | --- | ---: | --- |
| Vixen | [36875869680](https://github.com/gioe/laughtrack/actions/runs/36875869680) | 3 | Etix remains DataDome-blocked; official highlights are partial |
| Laughing Tap | [36884179521](https://github.com/gioe/laughtrack/actions/runs/36884179521) | 0 | Etix remains blocked; proxy CONNECT to Ticket Tailor is rejected with HTTP 403 |
| Ann Arbor | [36875874464](https://github.com/gioe/laughtrack/actions/runs/36875874464) | 0 | Etix remains blocked; alternative lacks an explicit performance year |

The corrected Laughing Tap runner attempted all seven official Ticket Tailor links through the existing allowlisted residential-proxy stack. Each failed with curl error 56, CONNECT tunnel failed, response 403. This is a proxy access rejection before an origin HTTP response, distinct from the bare-request origin 403 on the first runner pass. Browser fallback was not reached for these transport failures. Supported proxy access or another authoritative feed is still required; local source availability is not scheduled-run recovery. No manual insertion from cached pages was performed.

final-runner-verification.json preserves all three results. Every venue retained bot_block_detected=true and fetches_failed>0, so none qualifies for stale reconciliation. Vixen reports success=true because it emitted shows, but the failure diagnostics still correctly block destructive cleanup. The production query in production-inventory.json confirms exactly three Vixen records, their separate 20:00 local starts, original official detail URLs, free tickets and empty room fields. Laughing Tap and Ann Arbor still have zero records. source-config-verification.json confirms all three source rows and venue timezones are unchanged.

The five locally verified Laughing Tap performances above remain **unrecovered in production**. This task delivers Vixen partial recovery and reproducible external blockers for the other venues under its explicit alternative completion criterion. Vendor access recovery remains unproven. TASK-2858 retains scheduled-reprobe ownership; TASK-4128 separately tracks skipping unsupported banned-IP DataDome modes without implying that the current logged rejection proves a specific mode.
