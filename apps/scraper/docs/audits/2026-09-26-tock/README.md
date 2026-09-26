# Tock coverage audit — 2026-09-26

TASK-4054 covers My Buddy's (club 9119/source 6002), BATSU! Chicago
(11073/6842), and BATSU! NYC (16048/7643).

## Baseline

The three most recent production runs for each venue returned zero shows with
Playwright Cloudflare signatures, but success=true and no error. My Buddy's had
5 historical shows and zero upcoming, last refreshed August 5. Chicago had 150
stored shows (74 upcoming), last refreshed July 29; NYC had 236 (124 upcoming),
last refreshed August 28. The 198 retained future BATSU shows are not evidence of
fresh coverage. Full row IDs/dates and run diagnostics are retained beside this
report so any later reconciliation can be compared to the baseline.

## Verified failures and source evidence

The actual configured HttpClient.fetch_html recovered all three public Tock pages
through its existing fallback after initial HTTP 403 responses. The old scraper
used browser-only fetching. Accessible pages now contain navigation.onClose as
function noop(..._) {}; the old parser accepted only noop() and silently returned
an empty state. Blocking, transport errors, malformed states and incomplete GA
records were likewise swallowed as successful empty fetches.

Tock's offerings.openDate and openTime arrays are global choices spanning all
experiences. They contain no date/time pairing. For example, My Buddy's combines
bingo, trivia, drag and comedy times. PRIX_FIXE reservation details have empty
schedule and slots arrays. Generating every date/time combination is unsupported.
Chicago's official weekly schedule lists Thursday/Friday 19:00 and Saturday
19:00/22:00; NYC lists Tuesday–Thursday 19:00 and Friday/Saturday 19:00/22:00.
The DB instead has both times on every listed weekday: 24 future Chicago rows
and 37 NYC rows conflict with those ordinary weekly patterns. These are suspicious,
not conclusively canceled: dated exceptions and the year of holiday notices
could not be verified. No blanket deletion is authorized by this evidence.

Date-specific reservation searches either returned aggregate state without pairs
or a challenge. No reliable PRIX_FIXE availability feed was recovered. Sanitized
current Redux fixtures retain only public business names, experience listings and
calendar choices. See source-summary.json for official URLs and probe limits.

Verified individually dated GA performances: My Buddy's September 27 19:00 and
September 30 21:00; NYC Laughter Party September 28, October 19 and November 23
at 19:00. Their own eventDetails.schedule dates and slots support these pairs.
The old parser emitted only one date from a repeated GA experience.

## Implemented safeguards and verification

The scraper now decodes the observed noop syntax, uses the existing shared
HTTP/fallback stack, propagates mandatory-source failures, and keeps missing price
unknown. It expands explicit GA schedules, retaining event-specific ticket URLs,
without multiplying business-wide date/time arrays. Unverifiable recurring
coverage blocks stale reconciliation while allowing verified GA recovery.

Source priceCents are base ticket prices: My Buddy's 1000 and Laughter Party 1500.
Public cards show 11 and 17 dollars respectively, apparently including charges;
this task does not claim fee-inclusive checkout pricing.

Nineteen focused tests and the full scraper commit gate passed. Tests cover
mandatory-source failures, loaded-state uncertainty, mixed partial calendars,
explicit dated GA schedules, the November DST transition, and current public
fixtures. A real local read-only preview recovered 2/0/3 shows for My Buddy's,
Chicago and NYC respectively; live-preview.json retains the diagnostics.

## Scheduled runner verification and production recovery

All runs used code commit 151a1b13f1d0dff0ea3f355d1c0adc8184e863a2 and the
Ubuntu 24.04 scraper-verify workflow with the same proxy/solver secrets as nightly.
The first round still received Cloudflare HTTP 403s. It correctly recorded failed
club runs, unlike the earlier false successes. Logs showed Tock was absent from
the residential proxy registry, so the solver had neither proxy egress nor a
Turnstile sitekey. No claim of missing credentials was made.

Migration 20260926195800_enable_tock_proxy.sql enables the existing proxy path
for Tock. Its production-shaped rolled-back test changed one row on first apply,
zero on repeat; the exact migration was then applied with its migration ledger
entry. A second scheduled-runner round returned HTTP 200 for every venue:

| Venue | Before proxy: workflow / DB run | After proxy: workflow / DB run | Result |
|---|---|---|---|
| My Buddy's | [36267614905](https://github.com/gioe/laughtrack/actions/runs/36267614905) / 1475 | [36269658871](https://github.com/gioe/laughtrack/actions/runs/36269658871) / 1485 | 2 verified shows persisted; success |
| BATSU Chicago | [36267621989](https://github.com/gioe/laughtrack/actions/runs/36267621989) / 1477 | [36269666743](https://github.com/gioe/laughtrack/actions/runs/36269666743) / 1481 | 0; correctly failed for unverified PRIX_FIXE pairs |
| BATSU NYC | [36267627668](https://github.com/gioe/laughtrack/actions/runs/36267627668) / 1479 | [36269672866](https://github.com/gioe/laughtrack/actions/runs/36269672866) / 1482 | 3 verified GA dates persisted; recurring coverage partial |

Production inventory increased from 391 to 396 rows, adding IDs 7510583–7510587
with five matching tickets (two at $10 base and three at $15 base). All 391
baseline IDs, names, dates and last-scraped timestamps remain unchanged. Thus the
198 previously retained future BATSU rows were preserved, not refreshed or
validated. recovery-diff.json and inventory-after.json record the exact comparison.

Workflow green does not mean complete venue coverage. NYC's current run-history
success flag is true because safe GA shows were recovered, but its diagnostics
and warning identify unsupported recurring inventory and prevent reconciliation.
TASK-4059 tracks this broader partial-run health reporting limitation.

TASK-4085 tracks date-specific BATSU reservation availability and evidence-based
reconciliation of the 61 suspicious future times. Access is now recovered; the
remaining limitation is absence of verified performance pairs for PRIX_FIXE.
No stale BATSU listing was deleted based only on ordinary weekly schedules.
