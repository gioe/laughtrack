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

Validation was done on 2026-07-02 by instantiating the same generic scraper
classes that `make scrape-club` will use after the migration rows exist. The
runner itself requires DB rows, so the post-deploy verification commands are:

```bash
cd apps/scraper && make scrape-club CLUB='The N Crowd'
cd apps/scraper && make scrape-club CLUB='Laughing Stock Comedy Club'
cd apps/scraper && make scrape-club CLUB='Brooklyn Comedy Collective'
```

## Already Covered / Duplicate-Like

| Candidate | Evidence |
| --- | --- |
| Comedy Clubs / AC Jokes | Existing DB has `AC Jokes` in Atlantic City, id 412, website `https://www.acjokes.com`, google place id `ChIJpVu0ZzPvwIkRlPwG8dwYVkQ`. The discovered Google record has a different place id and generic label, so it should not be inserted as a new club without a duplicate audit. |

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
| Meadowlands Comedy Club | `json_ld`, homepage | 0 JSON-LD events. |
| Living Room Laughs | `json_ld`, `/shows/` | 0 JSON-LD events. |
| Rhino Comedy | `json_ld` and `squarespace` event collection | 0 shows. |
| Laughing Buddha Comedy | `squarespace` products mode, `/tickets` | 0 shows. |
| offnights comedy | `wix_events`, site root without compId | 0 events. |
| Upper East Side Comedy Club | `wix_events`, site root without compId | 0 events. |
| Church of Satire Comedy Club | `wix_events`, site root without compId | Wix access-token app lookup failed. |
| ComedySportz NYC | `wix_events`, site root without compId | Wix Events API returned 400 / 0 events. |

## Needs Follow-Up Triage

The remaining high-confidence candidates still need classification as onboarded,
already covered, or deny-listed. Prioritize fixed venues with supported-source
signals, then deny-list obvious non-venue/person/podcast records:

- Fixed/promising but needs source extraction: The Comedy Works, Give A Hoot
  Comedy Club NJ, The Backroom LIVE, High Line Comedy Club, Captain Kirk's
  Comedy Lounge, BATSU!, Top Secret Comedy Club, The PIT, Second City New York,
  Best Comedy Tickets, Village Underground, Fat Black Pussycat, UCB Theatre,
  and the Looney Bin records.
- Likely producer/event-series rather than fixed venue: Comic Cure / South
  Jersey Comedy Club variants, Main Line Laughs, Case Comedy, Kings Highway
  Comedy, Comedy Explosion, Die Laughing, Cool J's AfterDARK, TravLee Comedy,
  Poconos Underground Comedy, Airplane Mode, Punching Bag Comedy, Popped Collar
  Comedy, Expired Milk Comedy variants, Laughing Lassi Comedy, Living Room
  Laughs, Two in the Bush, Poe's Comedy Cabaret Baltimore, and Rhino Comedy.
- Likely deny-list/non-venue/person records: Raise your dongers, Tony's
  Crescenzo's strange humor, Comedian Ala Bama, DangItJared, Chip Ambrogio
  Comedy, FUNY Stand Up Classes / NY Comedy School, and Funny By The Pound
  Comedy Cafe if the discovered website remains a 404.
