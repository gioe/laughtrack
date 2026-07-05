# TASK-3587 ComedyTickets source triage

Generated from `/private/tmp/comedytickets-onboarding-classification.csv`, filtered to the ComedyTickets candidates that remained after duplicate screening and collapsed to the same 141 logical rows used by the candidate-club onboarding migration.

ComedyTickets is treated only as a discovery signal. It is not a first-party route target and no `scraping_sources` rows were enabled by this task.

## Output

- CSV: `apps/scraper/docs/audits/task-3587-comedytickets-source-triage.csv`
- Total logical candidates: 141

## Status counts

- `already-covered`: 20
- `scraper-ready`: 0
- `needs-manual-research`: 106
- `needs-deny`: 15

## Category counts

- `class_or_open_mic`: 2
- `dedicated_comedy_candidate`: 72
- `festival_or_event`: 3
- `general_venue_candidate`: 34
- `theater_or_mixed_venue`: 30

## Follow-up routing

- `3588`: 47
- `3589`: 33
- `3590`: 26
- `3591`: 15
- `none`: 20

## Already covered highlights

| Candidate | Existing club | Existing sources |
| --- | --- | --- |
| Bricktown Comedy Club - Oklahoma City | #90 Bricktown Comedy Club | live_nation,seatengine_classic |
| City Winery - New York | #2420 City Winery - New York City | city_winery |
| Comedy Cellar | #4548 Comedy Cellar at Rio Las Vegas | ticketmaster_comedy |
| Comedy Mothership - Fat Man | #174 Comedy Mothership | comedy_mothership |
| Count Basie Center for the Arts | #4638 The Vogel at Count Basie Center for the Arts | ticketmaster_comedy |
| Denver Improv Comedy Theater and Restaurant | #56 Denver Improv | improv |
| Dr. Grins Comedy Club at The B.O.B. | #207 Dr. Grins Comedy Club | dr_grins |
| Ha Ha Cafe Comedy Club | #163 HAHA Comedy Club | haha_comedy_club |
| House of Comedy Bloomington MN | #655 House of Comedy Bloomington | house_of_comedy_bloomington |
| Laugh Factory at Horseshoe Las Vegas | #172 Laugh Factory Las Vegas | live_nation |
| Laughs Unlimited Comedy Club and Lounge | #115 Laughs Unlimited | seatengine |
| Mayo Civic Center | #5144 Mayo Civic Center Arena | ticketmaster_comedy |
| New Jersey Performing Arts Center | #2489 New Jersey Performing Arts Center - Prudential Hall | live_nation |
| North Charleston Coliseum & Performing Arts Center | #2498 North Charleston Performing Arts Center | live_nation |
| Rose City Comedy - 9PM | #1023 Rose City Comedy | tixr |
| Skyline Comedy Cafe | #1057 Skyline Comedy Club | seatengine_classic |
| SPORTS DRINK: Cafe & Comedy Club | #653 Sports Drink | sports_drink |
| Stand Up Live | #129 StandUpLive Phoenix | seatengine_classic |
| Stress Factory - Valley Forge Casino | #130 Stress Factory - Valley Forge | seatengine_classic |
| Tacoma Comedy Club - Downtown - 7PM | #1031 Tacoma Comedy Club - Downtown | seatengine_classic |

## Triage interpretation

- `already-covered` rows should be merged or ignored during scraper onboarding; they point at an existing LaughTrack club and include current enabled scraper keys when present.
- `needs-manual-research` rows need first-party website discovery and platform detection before any source can be enabled.
- `needs-deny` rows are placeholders, event-specific listings, classes, festivals, cruises, or room/time-slot records. They should be merged to a canonical venue, denied, or kept hidden before downstream onboarding.
- `scraper-ready` is intentionally empty in this first pass because no row was promoted without either an existing LaughTrack source or first-party verification.

## Safety checks

- No database writes were performed.
- No `scraping_sources` rows were enabled.
- The CSV carries ComedyTickets source ids and event counts so downstream tasks can trace each decision back to the audit input.
