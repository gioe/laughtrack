# Missing-lineup source audit — TASK-4055

Snapshot: 2026-09-26, beginning 22:41 UTC. Investigation only: no production
memberships, suppression rules, scraper code, or discovery code changed.

## Findings

Of 363 empty lineups at the four venue records examined, 44 have verified
event-specific performer announcements that the current extraction misses.
293 have no announced cast on the checked source surfaces; 26 remain unresolved.
An empty lineup alone does not establish a scraper defect, especially for ensemble
programming. Never manufacture a comedian from a show title to improve coverage.

| Venue (club ID) | Upcoming | Empty raw/public | Recoverable | No cast on checked sources | Unresolved |
| --- | ---: | ---: | ---: | ---: | ---: |
| Grisly Pear Greenwich (6) | 99 | 99 | 16 | 83 | 0 |
| Grisly Pear Midtown (7) | 33 | 33 | 19 | 12 | 2 |
| Gotham (18) | 117 | 115 | 9 | 106 | 0 |
| UP Comedy Club (187) | 116 | 116 | 0 | 92 | 24 |
| Total | 365 | 363 | 44 | 293 | 26 |

These are a fixed cohort, not the older task-description counts. The global
snapshot contains 42,535 upcoming shows, 19,308 without raw memberships and
19,811 without visible memberships. Global absence is not classified as a defect
by this targeted investigation. See queries.json, global-counts.json, cohort.json,
cohort-summary.json, sources.json, and recent-runs.json for reproducible SQL,
timestamped rows, source configuration, and recent-run context.

All four venues are visible. All 363 public-empty cohort rows also pass the
captured sold-out availability checks. Their raw and public empty counts agree:
there is no demonstrated current hidden-membership explanation for these gaps.
This does not reconstruct historical deletions or prove suppression never affected
older data.

## Grisly Pear: extraction and calendar identity defects

The real HttpClient stack fetched 131 of 132 stored detail URLs. Event-specific
JSON-LD performer arrays and Featuring blocks establish 35 date-matched lineups
(145 show-performer memberships, 69 unique names). Special Guest is excluded by
the existing shared performer validator. Another 95 fetched pages announce no
explicit performers. Absence is scoped to the current pages, not future schedules.

Two rows are unresolved, excluded from recovery:

- 6331162: the October 8 URL redirects to metadata for October 1. Candidate
  names in analysis.json belong to the target page, not the stored performance.
- 6395741: redirect loop reproduced with HttpClient and actual Playwright.

The listing extractor only recognizes terminal YYYY-MM-DDHHMMSS slugs and misses
the newer MM-DD-YY-HH-MM-am/pm format. All 35 recoverable canonical detail URLs
occur in the current calendar, but only one recoverable stored URL (6079203)
appears in the current pipeline output. Merely adding a lineup field would leave
most recoverable events unreachable. The readonly real get_data/Show conversion
emits 87 Greenwich and 12 Midtown events, all with empty lineups.

GrislyPearEvent.to_show in scrapers/implementations/venues/grisly_pear/data.py
explicitly sets lineup=[]; the scraper never fetches these detail pages. Repair
must follow current links, validate authoritative date and venue, reconcile
existing performance identity, and extract only explicit names. A redirected
page must not overwrite a different date or justify stale deletion.

Evidence: grisly/analysis.json, summary.json, pipeline.json, names.json, four
captured detail excerpts (positive, unnamed, and mismatched-date cases), and
calendar-current-url-excerpt.html. Full-page hashes in the manifest identify the
original captures; excerpts are intentionally smaller than the original pages.

## Gotham: explicit description text and dated poster text

Five feed pages yielded 434 records; all 117 stored cohort shows matched.
All matching descriptions and all 19 unique poster assets were inspected, plus
12 event detail pages. Two already populated lineups are excluded from recovery.

Three empty shows have explicit billing in text (six memberships): Laugh for
Sight 4400553 names Mark Normand, Aaron Berg, Cory Kahaney, and host Shaun Eli;
Mixtape 6370626 and 5645376 name host Royale Watkins. Historical has-featured
lists, alumni, biography credits, and music credits are not current comic billing.

Six additional empty shows announce 29 memberships only in dated posters:
5509344, 3985663, 5509343, 3985662, 5009565, and 7275695. Match printed date,
time, and room before using printed names. This is text extraction, not face
identification. MORE TBA and venue branding are not performers.

The Laugh for Sight poster conflicts with newer text/time and includes an extra
Brian Fischler candidate. Do not automatically add that candidate. This is a
performer-level uncertainty within an already text-recoverable show, not an
additional unresolved show in the table.

GothamFeedEvent.from_feed_item retains raw source data but to_show in
core/clients/gotham/models/models.py emits a generic description and lineup=[].
Readonly conversion of the nine real feed records reproduces the omission.
Ticket enrichment does not restore the cast. The remaining 106 empty shows have
no explicit cast in the inspected feed descriptions/posters; only a sample of
detail pages was inspected. Email, social announcements, and later updates are
outside this evidence claim.

Evidence: gotham/matched-feed-items.json (117 records), selected-fixtures.json
(nine recovery cases and all asset inspection metadata), transform-preview.json,
three detail pages, and three retained posters covering positive, logo-only, and
stale/conflicting cases. Non-retained images are explicitly marked in the manifest;
their source URLs and hashes remain available, not falsely promised as fixtures.

## UP: ensemble absence and unresolved roster/venue identity

The actual UPComedyClubScraper.fetch_json stack fetched five resolvers and decoded
ticket instances. Every resolver has castAndProduction.castMember=null. Of 116
stored empty shows, 92 match source instances without a current announced cast.
Best of mentions Tina Fey, Stephen Colbert, and Steve Carell as alumni, not the
current lineup.

Four Grad Revue shows (7061192–7061195) have ambiguous descriptions: class rosters
of 11 and eight names are labelled Tuesday/Saturday, while performances occur on
three Mondays and one Tuesday. Neither assigning all 19 nor inferring cast from
weekday is justified. Another 20 stored purchase URLs do not match current future
source tickets. They are unresolved, not automatically canceled.

Source ticket addresses also point to e.t.c. Theater for Grad Revue and Chicago
Mainstage for Best of despite show-level UP associations. Eight duplicate purchase
URL groups cover 16 stored rows with different times. These need per-performance
venue/date investigation before deduplication or reassignment; the evidence was
attached to existing TASK-4065. No speculative UP lineup repair is proposed.

Evidence: up/summary.json, targets.json, and five full resolver/decoded-ticket
pairs. The source has 92 future instances; 88 distinct purchase URLs match 96 DB
rows. Two source instances have blank purchase URLs and two other current URLs
are absent from the cohort. These source and DB denominators are distinct.

## Discovery impact and identity safeguards

The 44 source-named shows contain 180 announced memberships and 95 unique names:
35 Grisly shows/145 memberships, three Gotham text shows/six memberships, and six
Gotham poster shows/29 memberships. Thus 38 shows have text/structured evidence;
six require poster extraction. All 44 have at least one existing exact-name
public comedian match. They are potentially recoverable for comedian-first
discovery without depending on a new identity being created.

performer-identity-query.sql, performer-identities.json, and
recovery-identity-summary.json preserve the case-insensitive exact-name check.
Four source names have no exact match: Julianna Dudley, Monte Marshall, Shaun Eli,
and Teressa DeGaetano. This is not proof of no alias; resolve identity before
creating anyone. No exact source name matches the denylist. Dj Collins matches
an existing visible identity with a non-public tag: preserve its suppression.

apps/web/lib/data/home/findShowsForHome.ts requires a visible, non-public-tag-free
lineup member when requireLineup is enabled. Tonight, trending-week, near-ZIP,
favorite, rising, touring-scarcity, and affinity queries use that gate. The cohort
currently cannot satisfy it. Restoring verified memberships can remove that
specific exclusion, enable favorite-performer joins, and supply headliner-image
inputs. It does not guarantee a show appears: geography, date, availability,
ranking, canonical identity, and each query's additional constraints still apply.
Trending-comedian eligibility has separate thresholds as well.

Checked related code: showSelect.ts (public lineup filtering),
getFavoriteComedianShows.ts (membership join), getTrendingComedians.ts (additional
eligibility), and showHeroImage.ts (empty lineup has no inferred headliner).
No public-visibility relaxation is recommended for the 293 source-unnamed or 26
unresolved shows. Ensemble programming should remain factually unannounced.

## Validation and limits

Source probes used the scraper's actual HTTP/browser or venue JSON stack, not a
plain HTTP fetchability proxy. Replays stopped at source/model conversion and did
not call persistence. Real captured inputs supply positive and negative fixtures.
The SQL cohort is fixed while upstream sources can change during/after capture;
future repair tasks must revalidate current dates and announcements before writes.
Exact-name candidates are evidence for coverage, not a replacement for canonical
identity resolution. Follow-up task IDs and executable regression contracts are
recorded separately in FOLLOWUPS.md.
