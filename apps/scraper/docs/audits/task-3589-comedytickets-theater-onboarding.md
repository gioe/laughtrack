# TASK-3589 ComedyTickets theater and venue onboarding

ComedyTickets was used only as a discovery signal. No ComedyTickets URL is used
as a route target or scraper source.

## Result

- Candidates reviewed: 33
- Newly onboarded: 1
- Already covered by existing production clubs/sources: 12
- Left without enabled sources: 20

## Newly onboarded

| Candidate | Source | Smoke result |
| --- | --- | --- |
| Fallout Theater | `platform=eventbrite`, `scraper_key=eventbrite`, `eventbrite_id=16738257328`, `source_url=https://www.eventbrite.com`, metadata `{"exclude_classes": true}` | `EventbriteScraper` single-venue mode returned 172 future shows. The venue endpoint 404s and falls back to the organizer endpoint, which is the existing single-venue pattern and does not create per-venue proxy clubs. |

## Already covered

These candidates already have production coverage and should not receive new
duplicate rows:

| Candidate | Existing club | Current source evidence |
| --- | --- | --- |
| Agora Theater & Ballroom | #4599 Agora Theatre | `ticketmaster_comedy`, 1 future show |
| Eccles Theater | #5433 Eccles Theater - Salt Lake City | `ticketmaster_comedy`, 9 future shows |
| Funnybone Des Moines | #1030 Des Moines Funny Bone | `etix`, 85 future shows |
| Levity Live Oxnard | #27 Oxnard Levity Live | `json_ld`, 52 future shows |
| Lillian S. Wells Hall at The Parker | #4850 Wells Hall at The Parker | `ticketmaster_comedy`, 15 future shows |
| Old National Centre | #2510 Murat Egyptian Room at Old National Centre | `live_nation`, 7 future shows |
| Playhouse Square | #5058 Connor Palace at Playhouse Square | `playhouse_square` / `ticketmaster_comedy`, 20 future shows |
| Rialto Theatre | #4884 Rialto Theatre-Tucson | `ticketmaster_comedy`, 15 future shows |
| Rio Suite Hotel & Casino | #4548 Comedy Cellar at Rio Las Vegas | `ticketmaster_comedy`, 359 future shows |
| River: A Waterfront Restaurant and Bar | #1350 Brew HaHa Comedy at River | `json_ld`, 6 future shows |
| Robert Kirk Walker Theatre | #4671 The Walker Theatre | `ticketmaster_comedy`, 13 future shows |
| Silver Legacy Resort Casino | #4571 Silver Legacy Casino Reno | `ticketmaster_comedy`, 2 future shows |

## Skipped

The remaining venues were left without enabled sources. The durable disposition
is in `task-3589-comedytickets-theater-onboarding.csv`.

Key skip reasons:

- Mixed venue with no verified first-party comedy-only source.
- Supported API probe returned a valid empty result, so adding the row would only
  create a dry scraper.
- The available source is unsupported or lacks a safe comedy filter. SoulJoel's
  is the clearest case: its WooCommerce products are categorized as `Tickets`,
  not `Comedy Events`, and include non-comedy events such as football podcasts
  and line dancing.
- Room/alias records that should not become independent scrape targets without a
  canonical merge.

## Verification notes

- Production duplicate/source check used normalized name and same-city/state
  candidate review, plus exact follow-up checks for likely aliases.
- Ticketmaster probes used the official Discovery API with
  `classificationName=Comedy`.
- Eventbrite probes used the private-token API. Fallout organizer
  `16738257328` returned 172 live events across Eventbrite venue records named
  `Fallout Theater`; single-venue mode keeps them attached to the one LaughTrack
  club.
- Lounge Boise's Squarespace collection
  `678f06e33a43e509beaaf7f7` returned 0 events for July, August, and September
  2026, so it was not enabled.
