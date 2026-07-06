# TASK-3564 Google Places 19103 Lower-Confidence Triage

Source bucket: Google Places discovery around ZIP 19103, 100-mile radius, `NEW_ONLY=1`, after DB dedupe. These candidates matched comedy/improv/cabaret naming signals but did not have Google `primary_type=comedy_club`.

## Outcome

- 25 candidates classified.
- 2 candidates onboarded with verified first-party, venue-owned calendars and existing scraper coverage.
- 23 candidates deny-listed to prevent recurring lower-confidence discovery noise.
- No candidates were already covered by exact Google Place ID or exact candidate name at triage time.

## Onboarded

| Club | Google Place ID | Source | Smoke result |
| --- | --- | --- | --- |
| Lancaster Improv Players | `ChIJic7wlFglxokRl5sigzliBvA` | Eventbrite organizer `18160289357` via `eventbrite` | 10 shows |
| Shore Thing Theater | `ChIJSzKexYAnwokRxWhUQlv4JhA` | Crowdwork API `shorethingtheater1` via `crowdwork` | 5 shows |

Required `make scrape-club` validation was run after applying the idempotent onboarding SQL to the configured scraper database:

- `cd apps/scraper && make scrape-club CLUB='Lancaster Improv Players'`: success, scraped and persisted 10 shows.
- `cd apps/scraper && make scrape-club CLUB='Shore Thing Theater'`: success, scraped and persisted 5 shows.

## Deny-Listed Categories

- Services/producers/individuals: Comedy On The Waterfront, Vince Valentine's Comedy Collective, Gemini Comedy Entertainment, Comedian Joseph Anthony.
- Education/classes/training: Improv 4 Life, Manhattan Comedy School, Improv 4 Kids, Long Island Improv, Letter of Marque Theater Co. & Brooklyn Improv Training.
- Non-comedy or theater feeds: Al's Diamond Cabaret, Cabaret Theatre (Rutgers University), Amateur Comedy Club, IMPROV.
- Festivals/corporate offices: New York Comedy Festival, Baltimore Comedy Festival.
- No supported scrapeable calendar found: Improv Ambler, Good Human Improv Company, Improvolution, Drop Three Improv and Sketch Comedy, Greenpoint Comedy Club, The Red Room Cabaret, Harrisburg Improv Theatre.
- Unsupported ticketing: Poco's Restaurant, Bar & Comedy Cabaret links to Comedy Cabaret's PatronBase ticketing, which is not covered by the existing PatronTicket scraper.

Full row-level evidence is in `task-3564-google-places-19103-lower-confidence.csv`.
