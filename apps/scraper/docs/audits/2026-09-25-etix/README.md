# Etix recovery audit — TASK-4052

Audited 2026-09-25 using production source/run records and the scraper's own
HTTP/Playwright implementations. Captures contain public event information;
no credentials or customer records are included.

## Baseline

All eight venues reported zero shows, `success=true`, HTTP 403, and a detected
bot block in nightly run 1446. Seven had no upcoming inventory; Ridley retained
two stale Phil Hanley shows. This was not evidence of eight empty calendars.

Direct Etix probes used `_fetch_etix_html`, the configured residential proxy,
and browser fallback. DataDome blocked all eight. The first browser attempt
returned CapSolver `ERROR_INVALID_TASK_DATA: blocked captcha url is not supported`;
the host circuit breaker short-circuited later attempts. Thus these were eight
HTTP probes, not eight independent browser solves. Official pages were checked
with Playwright and the exact `fetch_html_bare` fallback used by this scraper.

## Source decisions

| Club / source | Verified evidence | Recovery / remaining blocker |
|---|---|---|
| Ridley 4756 / 6960 | Official `/events/` has 107 unique ticket IDs; `Show \|` times previously became 8pm. Five ticket IDs have conflicting titles. | Recover 102 unambiguous performances with explicit times. Omit conflicting identities and mark the result incomplete to prevent stale reconciliation. Venue must correct IDs 62115951, 84649375, 68862675, 82720075, 50537895 before complete coverage is possible. |
| Robins 8715 / 5865 | Official `/events/` has 15 events, predominantly music. The apparent comedy *O Christmas Tea* is explicitly a play. | Use official calendar with comedy filtering and an explicit title exclusion. Zero eligible comedy is distinct from a blocked source. |
| Winery 8730 / 5878 | Official `/events/` has an explicit unfiltered Rockhouse “There were no results found” notice. | Accept this verified empty calendar. Arbitrary empty extraction remains a failure. |
| Laughing Tap 9070 / 5941 | Official tickets page delegates to Etix; posters contain series links without individual times. | Retain blocked source. Recover Etix access or obtain a venue-owned per-performance feed; posters and weekly hours are insufficient. |
| Des Plaines 9072 / 5943 | Official comedy calendar has matching visible/JSON-LD time and individual ticket for Terry Fator, Dec 15 at 7:30pm CST. | Recover Terry Fator; exclude film screening and theatrical production despite their comedy categories. Fail on unknown pagination or conflicting identity/time. |
| Raue 9073 / 5944 | Official calendar has 56 performances; comedy filtering also admitted a class. Lucy's detail says tickets start at $29 although card says $0–$29. | Recover comedy performances, exclude the class, and leave zero-to-paid prices unknown rather than advertise free admission. |
| Vixen 9074 / 5945 | Blake Burkhart Sep 30 is confirmed; 7:30pm JSON-LD matches explicitly labeled doors, not a verified showtime. | Retain blocked source. Obtain actual showtime or accessible Etix performance data; never convert doors to showtime. |
| Ann Arbor 16122 / 7682 | Official home has series dates and generic weekly hours, not verified individual performance times. | Retain blocked source. Recover Etix access or a verified per-performance venue feed. |

## Safety and verification

Mandatory transport errors, challenge HTML, and unrecognized calendars now
record failed fetches and cannot authorize stale-show deletion. Known public
fallbacks remain supported. Verified empty calendars require a positive,
unfiltered calendar shape; missing event cards alone are insufficient.

The source migration preserves IDs, existing metadata, and later manual URL
changes. A production transaction dry run changed exactly five rows; replay
changed zero, and both runs were rolled back. No shows are deleted by the SQL.

TASK-4082 tracks authoritative resolution of Ridley's five conflicting IDs.
TASK-4083 tracks the remaining unsupported Etix access at Laughing Tap, Vixen,
and Ann Arbor. TASK-2858 owns general scheduled reprobe automation.

## Scheduled-environment outcome

The migration was applied and all five source URLs were verified afterward.
All eight single-club GitHub runs completed on commit `42bf6d8f5`, using the
nightly browser/proxy/solver setup. Full evidence and run links are in
[scheduled-verification.json](scheduled-verification.json).

| Venue | DB run | Upcoming shows | Result |
|---|---:|---:|---|
| Ridley | 1454 | 102 | Supported performances persisted; five ambiguous ticket IDs omitted |
| Robins | 1451 | 0 | Healthy calendar, no eligible comedy |
| Winery | 1450 | 0 | Verified empty calendar |
| Laughing Tap | 1458 | 0 | HTTP 403, bot block, `success=false` |
| Des Plaines | 1462 | 1 | Verified Terry Fator performance persisted |
| Raue | 1456 | 16 | Comedy performances persisted; class excluded |
| Vixen | 1464 | 0 | HTTP 403, bot block, `success=false` |
| Ann Arbor | 1460 | 0 | HTTP 403, bot block, `success=false` |

All 119 stored names and UTC times match the source preview. Every show has a
ticket, no ticket is falsely free, and the class/play/screening exclusions are
absent. Existing Phil Hanley IDs 2874906/2874907 were refreshed in place with
their original correct dates. No comedian identities were created during these
runs. Full scraper tests passed; the Etix suite contains 90 passing cases.

Observability limitation: Ridley's runtime failed-fetch signal prevents stale
reconciliation, but the existing metrics serializer omits that counter and
reports success when any shows exist. The runner log preserves the explicit
five-ID conflict warning. This evidence is attached to TASK-4059; its audit
must distinguish partial nonempty inventory from complete healthy coverage.

## Reproduction

Run the Etix suite with the worktree source on `PYTHONPATH`. For live verification,
use `.github/workflows/scraper-verify.yml` with each club ID; it supplies the same
proxy and solver secrets and browser setup as the nightly workflow. Inspect
per-club diagnostics and stored inventory, not only the workflow exit status.

For local production refresh, use `make scrape-club CLUB='<venue name>'` from
`apps/scraper`. Source probes and parser previews do not persist shows.
