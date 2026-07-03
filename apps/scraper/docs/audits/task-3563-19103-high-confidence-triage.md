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
| The Comedy Works | `ChIJ2WY0G-pNwYkRSA9-Mu25f24` | `ticketspice` | `https://comedyworksbristol.ticketspice.com/comedyweekendlaughsjuly10-11` | 1 future show |
| Comedy Explosion | `ChIJoTL1eJ_7xokRxKP67A-9Aw0` | `wix_events` | `https://thecomedyexplosion.com/` | 1 future show |
| The Lab | `ChIJgRv5Eqe7xokRNgxFBVzkqRY` | `eventbrite` filtered | `https://www.eventbrite.com`, eventbrite id `26956500819`, `exclude_classes=true`, show-title include patterns | 4 future shows |
| Upright Citizens Brigade Theatre New York | `ChIJYwz0-YJZwokR1XOunnE1Pe4` | `ucb` | `https://ucbcomedy.com/shows/`, location slugs `nyc-mainstage` and `nyc-upstairs` | 62 Mainstage shows; 10 Upstairs shows |

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
cd apps/scraper && make scrape-club CLUB='The Comedy Works'
cd apps/scraper && make scrape-club CLUB='Comedy Explosion'
cd apps/scraper && make scrape-club CLUB='The Lab'
cd apps/scraper && make scrape-club CLUB='Upright Citizens Brigade Theatre New York'
```

## Already Covered / Duplicate-Like

| Candidate | Evidence |
| --- | --- |
| Comedy Clubs / AC Jokes | Existing DB has `AC Jokes` in Atlantic City, id 412, website `https://www.acjokes.com`, google place id `ChIJpVu0ZzPvwIkRlPwG8dwYVkQ`. The discovered Google record has a different place id and generic label, so it should not be inserted as a new club without a duplicate audit. |
| Village Underground | Existing DB has `Comedy Cellar New York`, id 1. Live validation of the existing `comedy_cellar` scraper returned 111 shows with rooms including `Village Underground`, so this Places record is already represented as a room under the Comedy Cellar club rather than a separate club row. |
| Fat Black Pussycat | Existing DB has `Comedy Cellar New York`, id 1. Live validation of the existing `comedy_cellar` scraper returned rooms including `Fat Black Pussycat` and `Room 5`; the venue website also points users to the Comedy Cellar lineup. |
| Dark Horse Comedy Club | Existing DB has `Dark Horse Comedy Club`, id 49, same website `https://www.darkhorsecomedyclub.com/` but an older address and no `google_place_id`. Do not insert a duplicate club from this Places record; it needs a separate location/current-address audit if we want to update the existing row. |
| Poe's Comedy Cabaret: Baltimore Comedy Club | Existing DB has `Poe's Magic Theatre`, id 565, at the Lord Baltimore Hotel. The existing Poe onboarding notes already identify `poesmagic.com` and `poescabaret.com` as the same Poe's Magic LLC operation, so this alternate Places record is already represented by the existing club rather than a new row. |

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
| The Laff House Atlantic City | `ChIJYU68C-fvwIkRnnT3nK6nICg` | Stale/no-calendar record; discovered domain no longer resolves. |
| Funny By The Pound Comedy Cafe | `ChIJk1zXo8Rjx4kRP55ii9K1hFc` | Stale/non-venue false positive; discovered Wix site returns 404 and exposes no public venue calendar. |
| The Looney Bin Comedy Club - Richmond Ave | `ChIJYf3-4MNNwokR29uqyb4wyL4` | Stale/no-calendar record; website returns a provider error page. |
| The Looney Bin Comedy Club - Hylan Blvd | `ChIJdUNZhZ9MwokRWNxtCHCYniI` | Alternate stale Looney Bin record; website returns 404/error and exposes no calendar. |
| Chip Ambrogio Comedy | `ChIJHxc11BPvwokRJnO9QrOJfHE` | Individual comedian website/listing, not a venue. |
| Best Comedy Tickets | `ChIJQXZTgZFZwokRAFmiulJft4w` | Ticket reseller/listing site for multiple NYC comedy venues, not a fixed venue calendar. |
| FUNY Stand Up Comedy Classes - The New York Comedy School | `ChIJD3c4lKVZwokRjdZJoUEQHj8` | Comedy class/school program, not a fixed club calendar. |
| KIDS 'N COMEDY | `ChIJC6VawohYwokRSM714XYSVBo` | Youth comedy program/show listing; event signal points to Gotham Comedy Club rather than a distinct venue. |
| The Industry Room | `ChIJYUSi3gpZwokRkMg8LalEFHY` | Comedy class/training-room listing; public ticket signal found was a stand-up class, not a fixed public club calendar. |
| Popped Collar Comedy - Free Show in Bushwick, Brooklyn | `ChIJ2QNRX-ddwokRj-YibDeFnoM` | Named recurring showcase at another venue, not a distinct club. |
| Two in the Bush: A Standup Comedy Showcase | `ChIJFcAVWzz3wokRw7A5-4bKHNs` | Named showcase, not a distinct club. |
| 124 world | `ChIJQ-32JULHxokRL-5ZQOzBfMA` | No website and no public venue-owned calendar evidence; address appears to be a non-public/private listing. |
| Case Comedy | `ChIJqzj_JPvHxokRSRW9qTzyolw` | Instagram-only comedy show/producer listing, not a fixed venue-owned club calendar. |
| South Jersey Comedy Club at Perkins Center - Collingswood | `ChIJX5NzI7fJxokRn2tAWlZNIto` | Comic Cure/South Jersey Comedy producer listing at a host venue, not a distinct fixed comedy club. |
| Main Line Laughs at the Palombaro Club | `ChIJETKduEfBxokRPXydhqcDg8w` | Comic Cure/Main Line Laughs producer listing at a host venue, not a distinct fixed comedy club. |
| South Jersey Comedy Club at Plays & Players | `ChIJHYCHtJjNxokRyigUhxrVthE` | Comic Cure/South Jersey Comedy producer listing at a host venue, not a distinct fixed comedy club. |
| South Jersey Comedy Club at Perkins Center - Moorestown | `ChIJ_wlA6Uw1wYkRLK4iN9LITzE` | Comic Cure/South Jersey Comedy producer listing at a host venue, not a distinct fixed comedy club. |
| South Jersey Comedy by Comic Cure | `ChIJpUejQUnXxokRX4eEvKyDLnc` | Comic Cure/South Jersey Comedy producer listing, not a distinct fixed comedy club. |
| New Sight Comedy | `ChIJj9cYtgoHx4kRcIpOJCt_0fA` | No website and no public venue-owned calendar evidence; address appears to be a non-public/private listing. |
| Cool J's AfterDARK | `ChIJh8PlzpMHx4kRGEDnSClDgw0` | Comedy producer/event-series listing rather than a fixed venue-owned comedy-club calendar. |
| TravLee Comedy | `ChIJMwywGmJxx4kREn69PkTwdaA` | Individual/producer comedy-brand listing, not a fixed comedy venue. |
| Poconos Underground Comedy | `ChIJuR4CPQCJxIkRveYIhfPiwt0` | Named comedy producer/showcase listing with no venue-owned public calendar, not a distinct fixed comedy club. |
| Comedy Show 3rd Fridays of the month at Fort Hamilton Distillery | `ChIJTTQXeERbwokRTbAzD7n2iGQ` | Named monthly showcase at Fort Hamilton Distillery, not a distinct fixed comedy club. |
| Punching Bag Comedy | `ChIJfZe5TAtbwokRbgS-m87GIfw` | Named comedy show/producer listing without a venue-owned public calendar, not a distinct fixed comedy club. |
| Expired Milk Comedy (at Planet Showbiz) | `ChIJAQJ5YOJfwokRRcnMweQ58HI` | Named show/producer listing at another venue, not a distinct fixed comedy club. |
| Living Room Laughs | `ChIJZblXaL5ZwokR-0Uctqy7N0o` | Private-show producer listing at an office address; site offers private comedy show packages rather than a fixed public venue calendar. |
| Comedy Cabaret Comedy Club Northeast | `ChIJy5ZWovyyxokRK7e8UIt1DAs` | Closed location; the venue page says Comedy Cabaret Comedy Club Northeast is closed due to building issues. |
| Eight Is Never Enough Improv | `ChIJucyRblNYwokRBjdPNwuHUZs` | Improv/class/showcase brand at a shared class/performance address, not a distinct venue-owned comedy-club calendar. |
| Laughing Lassi Comedy | `ChIJu0zwlrtZwokRjqYLUIr_Imk` | Named comedy show/producer listing at a shared class/performance address, not a distinct fixed comedy club. |

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
| Upright Citizens Brigade Theatre | `ucb`, `https://ucbcomedy.com/shows/` with likely NYC location slugs | Initial guesses returned 0 events, but later source extraction found the rendered card class slugs `nyc-mainstage` and `nyc-upstairs`; the venue is onboarded in the migration. |
| Laughing Buddha Comedy | `ticket_tailor`, `https://www.tickettailor.com/events/laughingbuddhacomedy/` | 38 parsed events, but the account mixes classes and offsite shows including New York Comedy Club; not a clean single-venue source without additional filtering. |
| The Backroom LIVE | `eventbrite`, organizer id `120674296136` discovered from collection page | 0 shows through the existing single-venue Eventbrite venue/fallback path; collection page is mixed and organizer mode would route as a multi-venue producer, not a fixed club. |
| Stones Comedy Club | `modern_events_calendar`, `https://stonestreetcomedyclub.com/wp-json/wp/v2/mec-events` | REST endpoint returned 404 / 0 shows. |
| Stones Comedy Club | `json_ld` detail fetch over `/events/` links | 0 JSON-LD events. |
| The Fear City Comedy Club | `squarespace`, `https://www.thefearcitycomedyclub.com/api/open/GetItemsByMonth?collectionId=66d33a4d09d98a61587e40bf` | 0 shows through the existing Squarespace scraper; the collection is present but did not return current/next-two-month events. |
| Comedy Cabaret Comedy Club | `the_events_calendar`, `https://comedycabaret.com/wp-json/tribe/events/v1/events` | REST endpoint returned 404 / 0 shows. |
| Comedy Cabaret Comedy Club | `modern_events_calendar`, `https://comedycabaret.com/wp-json/wp/v2/mec-events` | REST endpoint returned 404 / 0 shows. |
| The Lab | `wix_events`, `https://www.thelabambler.com/` root mode | Wix Events API returned HTTP 400 / 0 events. |
| The Lab | `eventbrite`, organizer id `26956500819` without filters | 10 events, but the feed mixes classes/workshops with shows. A filtered Eventbrite source is onboarded in the migration. |
| Upper East Side Comedy Club at Bedford Falls NYC | `wix_events`, `https://www.uppereastsidecomedyclub.com/` root mode | 0 events through the existing generic Wix Events scraper. |
| Stones Comedy Club | `ical`, `https://stonestreetcomedyclub.com/events/?ical=1` | HTTP 200 with an empty/non-ICS body, so the generic iCalendar scraper returned 0 shows. |

## Source Extraction Required

These are plausible fixed venues or recurring club brands, but the existing
generic scrapers did not produce a safe DB-only onboarding source in this task:

- `Comedy Cabaret Comedy Club` Doylestown (`ChIJgywfGpgCxIkRvQVpKm08aZg`)
  has a real fixed-venue page with PatronBase ticket links under
  `us.patronbase.com/_ComedyCabaret`, but the existing `patron_ticket` scraper
  is for Salesforce PatronTicket and does not cover PatronBase.
- `Kings Highway Comedy` (`ChIJYXEnsPJNwYkRjESWnP4dY_0`) has a GoDaddy site
  with form links and no validated generic event API in the scraper probe.
- `Die Laughing` (`ChIJFZh5yjCHxokRz_8cbQHXVRM`), `The Backroom LIVE`
  (`ChIJwSKD8ClTwokRirWjcbUWnlU`), `The PIT`
  (`ChIJG3e1NKdZwokR26WFFB6Lx7w`), `The Second City New York`
  (`ChIJv4cccglZwokRwENgJq6qkXs`), `Upper East Side Comedy Club at Bedford
  Falls NYC` (`ChIJi-qNZNtZwokRQBdBfR3dLM4`), `The Fear City Comedy Club`,
  `Sesh Comedy`, `Flop House Comedy Club`, `Rhino Comedy`, and `Stones Comedy
  Club` all need source extraction or scraper work before they are safe to
  onboard.

## Needs Follow-Up Triage

The remaining high-confidence candidates still need source extraction before
they can be onboarded safely. Prioritize fixed venues with supported-source
signals:

- Fixed/promising but needs source extraction: The Backroom LIVE,
  The PIT, Second City New York, The Fear City Comedy Club,
  Comedy Cabaret, Kings Highway Comedy, Die Laughing, Upper East Side Comedy
  Club, Sesh Comedy, Flop House Comedy Club, Rhino Comedy, and Stones Comedy
  Club.
