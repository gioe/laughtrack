# TASK-3563 19103 High-Confidence Comedy Club Triage

Discovery source: Google Places API, centered on `19103`, radius 100 miles,
deduped against the current DB. This audit covers `primary_type=comedy_club`
candidates from the high-confidence bucket.

## Onboarded In Migration

`apps/web/prisma/migrations/20260702195000_onboard_19103_high_confidence_validated/migration.sql`
adds these validated venues:

| Candidate | Google place id | Scraper | Source | Live validation |
| --- | --- | --- | --- | --- |
| The N Crowd | `ChIJs84JlYfIxokRSi0i_-Vg82Y` | `json_ld` | `https://events.humanitix.com/host/the-n-crowd` | 11 future shows |
| Laughing Stock Comedy Club | `ChIJaUIa3syxyIkRCUbHTrRQrQw` | `json_ld` | `https://www.laughingstockcc.com/` | 3 future shows |
| Brooklyn Comedy Collective | `ChIJVVWIvFlZwokRCb91vYtPZjA` | `squarespace` | `https://www.brooklyncomedy.com/api/open/GetItemsByMonth?collectionId=5a94518324a69489a755b5d9` | 101 future shows |
| Meadowlands Comedy Club | `ChIJXdCbldpXwokRfoD0jom327Q` | `json_ld` detail fetch | `https://meadowlandscomedyclub.com/` with `url_path_prefix=/event/` | 2 future shows |
| High Line Comedy Club | `ChIJXfsikHhZwokRxr1XAbft_X8` | `eventbrite` | `https://www.eventbrite.com`, eventbrite id `91898788783` | 23 future shows |
| BATSU! | `ChIJ4QKVd5xZwokRKNIH6nKJPAE` | `tock` | `https://www.exploretock.com/batsunyc` | 240 future shows |
| Give A Hoot Comedy Club NJ | `ChIJXd-xbnItwYkRuNSn__rA_2o` | `seatengine_web` | `https://www.giveahootcomedyclubnj.com/` | 6 future shows |
| Colonial Comedy | `ChIJn8bwdkSnw4kRzYbWgB3rhO8` | `wix_events` | `https://www.colonialcomedy.com/` | 2 future shows |
| Captain Kirk's Comedy Lounge | `ChIJvQQs6nlbwokR8Y4g0f5pXZA` | `eventbrite` | `https://www.eventbrite.com`, eventbrite id `58553141833` | 4 future shows |
| Sheba's Speakeasy Comedy Club | `ChIJFzCDZx1ZwokR0Xbe8D5v1jQ` | `eventbrite` | `https://www.eventbrite.com`, eventbrite id `77390385933` | 38 future shows |
| East Village Stand Up Comedy | `ChIJfWiS_xVZwokRwizGl3R3AME` | `eventbrite` | `https://www.eventbrite.com`, eventbrite id `10025720196` | 25 future shows |

Validation was done on 2026-07-02 by instantiating the same generic scraper
classes that `make scrape-club` will use after the migration rows exist. The
runner itself requires DB rows, so the post-deploy verification commands are:

```bash
cd apps/scraper && make scrape-club CLUB='The N Crowd'
cd apps/scraper && make scrape-club CLUB='Laughing Stock Comedy Club'
cd apps/scraper && make scrape-club CLUB='Brooklyn Comedy Collective'
cd apps/scraper && make scrape-club CLUB='Meadowlands Comedy Club'
cd apps/scraper && make scrape-club CLUB='High Line Comedy Club'
cd apps/scraper && make scrape-club CLUB='BATSU!'
cd apps/scraper && make scrape-club CLUB='Give A Hoot Comedy Club NJ'
cd apps/scraper && make scrape-club CLUB='Colonial Comedy'
cd apps/scraper && make scrape-club CLUB="Captain Kirk's Comedy Lounge"
cd apps/scraper && make scrape-club CLUB="Sheba's Speakeasy Comedy Club"
cd apps/scraper && make scrape-club CLUB='East Village Stand Up Comedy'
```

## Already Covered / Duplicate-Like

| Candidate | Evidence |
| --- | --- |
| Comedy Clubs / AC Jokes | Existing DB has `AC Jokes` in Atlantic City, id 412, website `https://www.acjokes.com`, google place id `ChIJpVu0ZzPvwIkRlPwG8dwYVkQ`. The discovered Google record has a different place id and generic label, so it should not be inserted as a new club without a duplicate audit. |
| Village Underground | Existing DB has `Comedy Cellar New York`, id 1. Live validation of the existing `comedy_cellar` scraper returned 111 shows with rooms including `Village Underground`, so this Places record is already represented as a room under the Comedy Cellar club rather than a separate club row. |
| Fat Black Pussycat | Existing DB has `Comedy Cellar New York`, id 1. Live validation of the existing `comedy_cellar` scraper returned rooms including `Fat Black Pussycat` and `Room 5`; the venue website also points users to the Comedy Cellar lineup. |

## Deny-Listed In Migration

These records are clear non-venue false positives from the Google Places bucket.
The migration inserts hidden `clubs` rows with `club_type=non_comedy` and no
`scraping_sources`, plus `venue_deny_list` rows so discovery does not re-file
them as comedy-club onboarding candidates.

| Candidate | Google place id | Classification |
| --- | --- | --- |
| Raise your dongers | `ChIJmTPfAx17x4kR5vWbRtXqdB8` | Non-venue false positive; no public website or fixed venue evidence. |
| Tony's Crescenzo's strange humor (podcast on Spotify) | `ChIJ1UPf_OCduIkRFoN2BVfsXzU` | Podcast/personality, not a venue. |
| Comedian Ala Bama | `ChIJ58EKNDIbyIkR7QZZSFUaYSM` | Individual comedian, not a venue. |
| DangItJared | `ChIJ_Ug6nRufxYkRQpLUGjWlUJc` | Individual performer/brand, not a venue. |
| Funny By The Pound Comedy Cafe | `ChIJk1zXo8Rjx4kRP55ii9K1hFc` | Stale/non-venue false positive; discovered Wix site returns 404 and exposes no public venue calendar. |
| Chip Ambrogio Comedy | `ChIJHxc11BPvwokRJnO9QrOJfHE` | Individual comedian website/listing, not a venue. |
| Best Comedy Tickets | `ChIJQXZTgZFZwokRAFmiulJft4w` | Ticket reseller/listing site for multiple NYC comedy venues, not a fixed venue calendar. |
| FUNY Stand Up Comedy Classes - The New York Comedy School | `ChIJD3c4lKVZwokRjdZJoUEQHj8` | Comedy class/school program, not a fixed club calendar. |
| KIDS 'N COMEDY | `ChIJC6VawohYwokRSM714XYSVBo` | Youth comedy program/show listing; event signal points to Gotham Comedy Club rather than a distinct venue. |
| The Industry Room | `ChIJYUSi3gpZwokRkMg8LalEFHY` | Comedy class/training-room listing; public ticket signal found was a stand-up class, not a fixed public club calendar. |
| Popped Collar Comedy - Free Show in Bushwick, Brooklyn | `ChIJ2QNRX-ddwokRj-YibDeFnoM` | Named recurring showcase at another venue, not a distinct club. |
| Two in the Bush: A Standup Comedy Showcase | `ChIJFcAVWzz3wokRw7A5-4bKHNs` | Named showcase, not a distinct club. |

## Existing Generic Scraper Did Not Validate

These candidates had promising platform signals but returned zero shows or did
not match the existing generic scraper contract during live validation:

| Candidate | Tested scraper/source | Result |
| --- | --- | --- |
| SoulJoel's at SunnyBrook | `woocommerce_store_api`, `https://www.souljoels.com` | 0 showtimes; products do not match the expected `Show Dates` / `Show Times` attribute contract. |
| Wise Crackers Comedy Club | `woocommerce_store_api`, `https://www.wisecrackers.biz` | 0 showtimes; products do not match the expected WooCommerce Store API contract. |
| Claude's Comedy Club & Bar | `woocommerce_store_api`, `https://claudescomedy.com` | Store API endpoint returned 404 / 0 showtimes. |
| Stitches Comedy Club | `woocommerce_store_api`, `https://first-laugh.com` | 0 showtimes; ticket links use a custom `buy-tickets/?action=seatsForEvent&eventid=...` flow. |
| The Mask and Wig Club | `arts_people`, `https://app.arts-people.com/index.php?show=309603` | 0 shows; existing `arts_people` scraper expects a `?ticketing=<shortName>` list page, not a one-off `?show=<id>` link. |
| Eleven Laughs Comedy Club | `json_ld`, homepage | 0 JSON-LD events. |
| Greenwich Village Comedy Club | `json_ld`, homepage | 0 JSON-LD events despite show links on the page. |
| Greenwich Village Comedy Club | `json_ld` detail fetch over `/shows/` links | 0 JSON-LD events after dozens of detail pages; stopped the validation run because the site produced many detail URLs with no JSON-LD events. |
| Meadowlands Comedy Club | `json_ld`, homepage | 0 JSON-LD events. |
| Living Room Laughs | `json_ld`, `/shows/` | 0 JSON-LD events. |
| Rhino Comedy | `json_ld` and `squarespace` event collection | 0 shows. |
| Laughing Buddha Comedy | `squarespace` products mode, `/tickets` | 0 shows. |
| offnights comedy | `wix_events`, site root without compId | 0 events. |
| Upper East Side Comedy Club | `wix_events`, site root without compId | 0 events. |
| Church of Satire Comedy Club | `wix_events`, site root without compId | Wix access-token app lookup failed. |
| ComedySportz NYC | `wix_events`, site root without compId | Wix Events API returned 400 / 0 events. |
| Top Secret Comedy Club | `json_ld` detail fetch over `/events-listings/` links | 0 JSON-LD events. |
| The PIT | `json_ld` detail fetch over `/events/` links | Timed out while fetching many detail pages; not safe to onboard via generic JSON-LD without a narrower source or scraper. |
| Upright Citizens Brigade Theatre | `ucb`, `https://ucbcomedy.com/shows/` with likely NYC location slugs | 0 events for `ny`, `nyc`, `new-york`, `east-village`, `ucb-new-york`, `ucb-nyc`, `ny-theatre`, `new-york-theatre`, and `ucb-theatre-ny`; needs source extraction before onboarding. |
| Laughing Buddha Comedy | `ticket_tailor`, `https://www.tickettailor.com/events/laughingbuddhacomedy/` | 38 parsed events, but the account mixes classes and offsite shows including New York Comedy Club; not a clean single-venue source without additional filtering. |
| The Backroom LIVE | `eventbrite`, organizer id `120674296136` discovered from collection page | 0 shows through the existing single-venue Eventbrite venue/fallback path; collection page is mixed and organizer mode would route as a multi-venue producer, not a fixed club. |
| Stones Comedy Club | `modern_events_calendar`, `https://stonestreetcomedyclub.com/wp-json/wp/v2/mec-events` | REST endpoint returned 404 / 0 shows. |
| Stones Comedy Club | `json_ld` detail fetch over `/events/` links | 0 JSON-LD events. |
| The Fear City Comedy Club | `squarespace`, `https://www.thefearcitycomedyclub.com/api/open/GetItemsByMonth?collectionId=66d33a4d09d98a61587e40bf` | 0 shows through the existing Squarespace scraper; the collection is present but did not return current/next-two-month events. |

## Needs Follow-Up Triage

The remaining high-confidence candidates still need classification as onboarded,
already covered, or deny-listed. Prioritize fixed venues with supported-source
signals, then deny-list obvious non-venue/person/podcast records:

- Fixed/promising but needs source extraction: The Comedy Works,
  The Backroom LIVE, The PIT, Second City New York,
  UCB Theatre, The Fear City Comedy Club, and the Looney Bin records.
- Likely producer/event-series rather than fixed venue: Comic Cure / South
  Jersey Comedy Club variants, Main Line Laughs, Case Comedy, Kings Highway
  Comedy, Comedy Explosion, Die Laughing, Cool J's AfterDARK, TravLee Comedy,
  Poconos Underground Comedy, Airplane Mode, Punching Bag Comedy, Expired Milk
  Comedy variants, Laughing Lassi Comedy, Living Room Laughs, Poe's Comedy
  Cabaret Baltimore, Rhino Comedy, Eight Is Never Enough Improv, Flop House
  Comedy Club, Sesh Comedy, and Stones Comedy Club.
