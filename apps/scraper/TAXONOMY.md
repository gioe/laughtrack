# Scraper Taxonomy & Onboarding Checklist

This document formalizes the two-axis classification framework for all venue scrapers and provides a decision-tree checklist for onboarding new venues. It complements [SCRAPERS.md](SCRAPERS.md) (platform-specific implementation guides) and serves as the entry point for `/find-clubs` -> onboarding.

---

## Two-Axis Framework

Every scraper is classified along two independent axes:

### Axis 1: Data Source Type

How the scraper obtains raw event data from the venue or platform.

| Type | Definition | Example |
|---|---|---|
| **external_api** | Calls a structured REST/GraphQL API provided by a ticketing platform or the venue itself. Authentication may be required (OAuth tokens, API keys). | Eventbrite `/organizers/{id}/events/`, Tixr JSON-LD pages, Wix paginated-events API, OvationTix `Production({id})/performance`, Comedy Cellar API, Tessera API |
| **html** | Parses server-rendered HTML using CSS selectors, regex, or BeautifulSoup. The page is fetched via HTTP (curl_cffi or Playwright for JS-rendered pages). | Comedy Store daily calendar, Flappers PHP calendar, rhp-events WordPress plugin, TicketSource event listings, VBO Tickets session-based HTML |
| **json_feed** | Fetches a JSON endpoint that is not part of a formal API — S3 buckets, Netlify functions, Tockify calendar feeds, Pixl Calendar, or inline JSON embedded in HTML. | Gotham S3 bucket, Creek and Cave S3, Tockify API, East Austin Netlify functions, Laugh Boston Pixl Calendar |
| **json_ld** | Extracts `<script type="application/ld+json">` structured data blocks from HTML pages. Uses the generic `json_ld` scraper or venue-specific multi-step variants. | Prekindle events pages, Humanitix host pages, Improv multi-step (listing -> detail pages), Uptown Theater, Grove 34 detail pages |
| **rsc** | Parses React Server Component (RSC) wire format payloads from `self.__next_f.push()` streaming script tags. Data is embedded in the server-rendered HTML but encoded as RSC flight format, not standard JSON or JSON-LD. | StageTime (`{slug}.stageti.me`), West Side (Punchup/Next.js), Comedy Key West (Punchup/Tixologi) |
| **next_data** | Extracts event data from `<script id="__NEXT_DATA__">` JSON blocks in Next.js pages. Similar to json_ld but uses Next.js's built-in SSR data serialization. | Vivenu seller pages (`tickets.{venue}.com`), Comedy Mothership (SquadUP via Next.js pagination) |
| **graphql** | Queries a GraphQL endpoint directly (not via a REST wrapper). | StandUp NY (ShowTix4U), UP Comedy Club (Second City platform) |
| **google_sheets** | Fetches event data from a published Google Sheets CSV export. | The Setup SF (and other Setup cities) |
| **email** | Parses show listings from venue emails via MIME/HTML extraction. | Comedy Cellar (email-based), Gotham (email-based) — these are secondary sources alongside their primary scrapers |

### Axis 2: Process Type

How many HTTP round-trips are needed to collect all event data.

| Type | Definition | Example |
|---|---|---|
| **single** | All event data is available from a single URL or a predictable set of URLs (e.g., one per month) that can be generated without inspecting prior responses. No detail-page fetching required. | Comedy Store (one URL per day), Gotham (single S3 endpoint), json_ld (single page), Eventbrite (paginated but auto-handled by client) |
| **multi_step** | Requires at least two phases: (1) discover event URLs/IDs from a listing page, then (2) fetch detail pages to get full event data. The second phase depends on data extracted in the first phase. | Improv (listing -> JSON-LD detail pages), Flappers (listing -> detail pages), StageTime (listing -> RSC event pages), OvationTix (discover production IDs -> fetch performances), Comedy Cellar (multi-date API calls) |

**Note on pagination:** A scraper that paginates through a single API endpoint (e.g., Eventbrite page 1, 2, 3...) is still **single** process type. Multi-step means the scraper must discover URLs from one response to feed into subsequent requests for *different* data.

---

## Reference Table: All Venues

50 venue scrapers + 15 API-level scrapers classified by (data source, process type).

### Venue Scrapers (50)

| # | Venue | Scraper Key | Data Source | Process Type | Platform / Notes |
|---|---|---|---|---|---|
| 1 | Annoyance Theatre | `annoyance` | json_feed | single | ThunderTix calendar JSON API (12 weekly URLs) |
| 2 | Broadway Comedy Club | `broadway_comedy_club` | external_api | multi_step | Tessera API + HTML enrichment |
| 3 | Bushwick Comedy Club | `bushwick` | external_api | single | Wix Events paginated API |
| 4 | Comedy @ The Carlson | `comedy_at_the_carlson` | external_api | multi_step | OvationTix calendar -> production API |
| 5 | Comedy Cellar | `comedy_cellar` | external_api | multi_step | Custom Comedy Cellar API (multi-date) |
| 6 | Comedy Clubhouse | `comedy_clubhouse` | html | single | TicketSource server-rendered HTML |
| 7 | Comedy Corner Underground | `comedy_corner_underground` | rsc | multi_step | StageTime Next.js RSC (listing -> event pages) |
| 8 | Comedy Key West | `comedy_key_west` | rsc | single | Punchup/Next.js RSC hydration + Tixologi tickets |
| 9 | Comedy & Magic Club | `comedy_magic_club` | html | multi_step | rhp-events WordPress + eTix detail pages |
| 10 | Comedy Mothership | `comedy_mothership` | next_data | single | Next.js SSR + SquadUP (paginated listing) |
| 11 | Comedy Store | `comedy_store` | html | single | Custom PHP calendar (one URL per day) |
| 12 | Creek and The Cave | `creek_and_cave` | json_feed | single | S3 bucket monthly JSON files |
| 13 | CSz Philadelphia | `csz_philadelphia` | html | single | VBO Tickets server-rendered HTML |
| 14 | Dynasty Typewriter | `dynasty_typewriter` | external_api | single | SquadUP JSON API (Cloudflare-protected) |
| 15 | East Austin Comedy | `east_austin_comedy` | json_feed | single | Netlify serverless functions (7 weekday endpoints) |
| 16 | Esther's Follies | `esthers_follies` | html | single | VBO Tickets session-based HTML |
| 17 | Flappers | `flappers` | html | multi_step | PHP calendar listing -> detail pages |
| 18 | Four Day Weekend | `four_day_weekend` | external_api | multi_step | OvationTix direct productions -> performances API |
| 19 | Funny Bone | `funny_bone` | html | single | rhp-events WordPress (single page, no detail fetch) |
| 20 | Goofs | `goofs` | rsc | single | Next.js RSC flight payload (single page) |
| 21 | Gotham | `gotham` | json_feed | single | S3 bucket JSON endpoint |
| 22 | Grove 34 | `grove_34` | json_ld | multi_step | Webflow listing -> JSON-LD detail pages |
| 23 | HAHA Comedy Club | `haha_comedy_club` | json_ld | single | Webflow calendar with inline JSON-LD + Tixr links |
| 24 | Ice House | `ice_house` | json_feed | single | Tockify calendar API + ShowClix tickets |
| 25 | Improv | `improv` | json_ld | multi_step | Calendar listing -> JSON-LD event detail pages |
| 26 | Improv Asylum | `improv_asylum` | external_api | multi_step | Tixr group page -> per-event JSON-LD fetch |
| 27 | iO Theater | `io_theater` | json_feed | single | Crowdwork/Fourthwall API |
| 28 | Laugh Boston | `laugh_boston` | json_feed | single | Pixl Calendar API (builds TixrEvents directly) |
| 29 | Laugh Factory Covina | `laugh_factory_covina` | external_api | multi_step | Tixr group page -> per-event JSON-LD fetch |
| 30 | Laugh Factory Reno | `laugh_factory_reno` | html | single | Tixologi CMS HTML scraping (.show-sec.jokes divs) |
| 31 | Logan Square Improv | `logan_square_improv` | json_feed | single | Crowdwork/Fourthwall API |
| 32 | McCurdy's Comedy Theatre | `mccurdys_comedy_theatre` | html | multi_step | ColdFusion listing -> detail pages |
| 33 | Nick's Comedy Stop | `nicks_comedy_stop` | external_api | single | Wix Events paginated API |
| 34 | Philly Improv Theater | `philly_improv_theater` | json_feed | single | Crowdwork/Fourthwall API |
| 35 | Red Room | `red_room` | external_api | single | Wix Events paginated API |
| 36 | Rodney's | `rodneys` | html | multi_step | Custom HTML listing -> Eventbrite/22Rams detail pages |
| 37 | The Setup | `setup` | google_sheets | single | Published Google Sheets CSV export (multi-city via gid) |
| 38 | Sports Drink | `sports_drink` | html | single | OpenDate server-rendered HTML |
| 39 | St. Marks | `st_marks` | external_api | multi_step | Tixr group page -> per-event JSON-LD fetch |
| 40 | StandUp NY | `standup_ny` | graphql | multi_step | ShowTix4U GraphQL + VenuePilot enrichment |
| 41 | Stevie Ray's | `stevie_rays` | html | single | AudienceView HTML (Playwright JS execution required) |
| 42 | Sunset Strip | `sunset_strip` | external_api | single | SquadUP JSON API (paginated) |
| 43 | The Rockwell | `the_rockwell` | json_feed | single | Tribe Events WordPress REST API |
| 44 | The Stand | `the_stand` | external_api | multi_step | Tixr group page -> per-event JSON-LD fetch |
| 45 | Third Coast Comedy | `third_coast_comedy` | next_data | single | Vivenu `__NEXT_DATA__` JSON |
| 46 | Uncle Vinnie's | `uncle_vinnies` | external_api | multi_step | OvationTix calendar -> production API |
| 47 | UP Comedy Club | `up_comedy_club` | graphql | multi_step | Second City platform GraphQL (show list -> detail) |
| 48 | Uptown Theater | `uptown_theater` | json_ld | multi_step | Next.js JSON-LD listing -> detail pages |
| 49 | West Side | `west_side` | rsc | single | Punchup/Next.js RSC hydration state |
| 50 | Zanies | `zanies` | html | multi_step | rhp-events WordPress listing -> series/event detail pages |

### API-Level / National Scrapers (15)

| Scraper Key | Data Source | Process Type | Scope |
|---|---|---|---|
| `eventbrite` | external_api | single | Per-venue (organizer/venue ID) |
| `eventbrite_national` | external_api | single | **RETIRED** (search API deprecated) |
| `seatengine` | external_api | single | Per-venue (numeric ID) |
| `seatengine_classic` | html | single | Per-venue (scraping_url) |
| `seatengine_v3` | external_api | single | Per-venue (UUID) |
| `seatengine_national` | external_api | single | National discovery |
| `seatengine_v3_national` | external_api | single | National discovery |
| `squarespace` | json_feed | single | Per-venue (collectionId) |
| `ticketmaster` | external_api | single | Per-venue (Discovery API ID) |
| `ticketmaster_national` | external_api | single | National discovery |
| `tixr` | external_api | multi_step | Generic Tixr link extraction + detail fetch |
| `tour_dates` | external_api | single | Comedian tour dates (Songkick/Bandsintown) |
| `ninkashi` | external_api | single | Per-venue (tickets subdomain) |
| `comedian_websites` | json_ld | single | Comedian personal website JSON-LD |
| `crowdwork` | — | — | Utility module (used by iO, LSI, PHIT venue scrapers) |

### Other Scrapers

| Scraper Key | Data Source | Process Type | Location |
|---|---|---|---|
| `json_ld` | json_ld | single | Generic JSON-LD extractor (`implementations/json_ld/`) |
| Comedy Cellar (email) | email | single | `implementations/email/comedy_cellar/` |
| Gotham (email) | email | single | `implementations/email/gotham/` |

---

## Data Source Distribution

| Data Source | Count | % |
|---|---|---|
| external_api | 17 | 34% |
| html | 14 | 28% |
| json_feed | 9 | 18% |
| json_ld | 4 | 8% |
| rsc | 4 | 8% |
| next_data | 2 | 4% |
| graphql | 2 | 4% |
| google_sheets | 1 | 2% |

(Percentages based on 50 venue scrapers; some venues appear in multiple categories when they have secondary data sources.)

---

## Onboarding Decision-Tree Checklist

When onboarding a new venue, work through this checklist to determine the data source type, process type, and which existing infrastructure to use.

### Step 1: Identify the Data Source Type

Open the venue's show listing page in a browser and inspect using these methods in order:

#### 1a. Check buy links for known ticketing platforms

| What to look for | Platform | Data Source | Infrastructure |
|---|---|---|---|
| `ticketmaster.com` buy links | Ticketmaster | external_api | `ticketmaster` scraper (generic) |
| `eventbrite.com` buy links or widget | Eventbrite | external_api | `eventbrite` scraper (generic) |
| `v-{uuid}.seatengine.net` subdomain | SeatEngine v3 | external_api | `seatengine_v3` scraper (generic) |
| `{venue}.seatengine.net` (no `v-` prefix) | SeatEngine v1 | external_api | `seatengine` scraper (generic) |
| `cdn.seatengine.com/assets/application` in scripts | SeatEngine Classic | html | `seatengine_classic` scraper (generic) |
| `tixr.com/groups/` or `tixr.com/e/` buy links | Tixr | external_api | `tixr` scraper (generic) or venue-specific |
| `{slug}.thundertix.com` links | ThunderTix | json_feed | Venue-specific (ref: `annoyance`) |
| `ticketsource.com/{slug}` links | TicketSource | html | Venue-specific (ref: `comedy_clubhouse`) |
| `events.humanitix.com/host/{slug}` | Humanitix | json_ld | `json_ld` scraper (generic) |
| `tickets.{venue}.com` + `api.ninkashi.com` | Ninkashi | external_api | `ninkashi` scraper (generic) |
| `event.tixologi.com/event/{id}/tickets` | Tixologi | html | Venue-specific (ref: `laugh_factory_reno`) |
| `ci.ovationtix.com/{clientId}/production/{id}` | OvationTix | external_api | Venue-specific (ref: `uncle_vinnies` or `four_day_weekend`) |
| `app.opendate.io/v/{slug}` | OpenDate | html | Venue-specific (ref: `sports_drink`) |
| `prekindle.com/events/{slug}` | Prekindle | json_ld | `json_ld` scraper (generic) |
| `squadup.com/events/{slug}` ticket links | SquadUP | external_api | Venue-specific (ref: `sunset_strip`) |

#### 1b. Check browser network requests (DevTools or Playwright)

Navigate to the venue page and inspect XHR/fetch requests:

| Network request pattern | Platform | Data Source | Infrastructure |
|---|---|---|---|
| `tockify.com/api/ngevent?calname=...` | Tockify | json_feed | Venue-specific (ref: `ice_house`) |
| `/api/open/GetItemsByMonth?collectionId=...` | Squarespace | json_feed | `squarespace` scraper (generic) |
| `crowdwork.com/api/v2/{theatre}/shows` | Crowdwork | json_feed | Venue-specific (ref: `io_theater`) |
| `plugin.vbotickets.com` | VBO Tickets | html | Venue-specific (ref: `esthers_follies`) |
| `/.netlify/functions/availability` | Netlify Functions | json_feed | Venue-specific (ref: `east_austin_comedy`) |
| `/wp-json/tribe/events/v1/events` | Tribe Events (WP) | json_feed | `the_rockwell` scraper (generic) |
| `wix-one-events-server/web/paginated-events` | Wix Events | external_api | Venue-specific (ref: `bushwick`) |
| `inffuse.eventscalendar.co` + Eventbrite backend | Wix + Eventbrite | external_api | `eventbrite` scraper (generic) |

#### 1c. Check page source

| Source pattern | Platform | Data Source | Infrastructure |
|---|---|---|---|
| `<script type="application/ld+json">` with `@type: Event` | JSON-LD | json_ld | `json_ld` scraper (generic) or venue-specific multi-step |
| `self.__next_f.push([1,"..."])` RSC segments | Next.js RSC | rsc | Venue-specific (ref: `comedy_corner_underground` for StageTime, `west_side` for Punchup) |
| `<script id="__NEXT_DATA__">` JSON block | Next.js SSR | next_data | Venue-specific (ref: `third_coast_comedy` for Vivenu) |
| CSS classes: `rhpSingleEvent`, `rhp-event__title--list` | rhp-events (WP) | html | `comedy_magic_club` scraper (generic) |
| CSS classes: `eventRow`, `dateTime`, `event-btn` | TicketSource | html | Venue-specific (ref: `comedy_clubhouse`) |
| `squadup = { userId: [...] }` in inline JS | SquadUP | external_api | Venue-specific (ref: `sunset_strip`) |
| `{slug}.stageti.me` subdomain | StageTime | rsc | Venue-specific (ref: `comedy_corner_underground`) |
| `confirm-card` divs at `app.opendate.io` | OpenDate | html | Venue-specific (ref: `sports_drink`) |

#### 1d. None of the above

If no known platform is detected, the venue uses a custom website. Inspect the HTML structure and build a venue-specific **html** scraper.

### Step 2: Determine the Process Type

| Question | Answer | Process Type |
|---|---|---|
| Does the listing page contain all event data (dates, times, lineup, ticket URLs)? | Yes | **single** |
| Does the listing page only contain event links/IDs, requiring detail page fetches? | Yes | **multi_step** |
| Does the API paginate but each page has complete event data? | Yes | **single** |
| Does the API return event IDs that require a second API call for full details? | Yes | **multi_step** |

### Step 3: Map to Existing Infrastructure

Use the decision matrix below to determine whether you need new code:

#### Generic scrapers (DB config only, no code needed)

| Platform | Scraper Key | Required DB Fields |
|---|---|---|
| Ticketmaster | `live_nation` | `ticketmaster_id` |
| Eventbrite | `eventbrite` | `eventbrite_id` |
| SeatEngine v1 | `seatengine` | `seatengine_id` (numeric) |
| SeatEngine Classic | `seatengine_classic` | `scraping_url` |
| SeatEngine v3 | `seatengine_v3` | `seatengine_id` (UUID) |
| Tribe Events (WP) | `the_rockwell` | `scraping_url` |
| rhp-events (WP) | `comedy_magic_club` | `scraping_url` |
| JSON-LD | `json_ld` | `scraping_url` |
| Prekindle | `json_ld` | `scraping_url` |
| Humanitix | `json_ld` | `scraping_url` |
| Ninkashi | `ninkashi` | `scraping_url` |
| Vivenu | `vivenu` | `scraping_url` |
| Squarespace | `squarespace` | `scraping_url` (with collectionId) |
| Tixr (when calendar HTML has links) | `tixr` | `scraping_url` |

#### Venue-specific scrapers (new code required)

Copy the reference implementation and modify:

| Platform | Reference Scraper | What to Change |
|---|---|---|
| Tixr (DataDome-blocked) | `haha_comedy_club` or `laugh_boston` | Calendar parsing logic |
| Tockify | `ice_house` | `calname` parameter |
| Wix Events | `bushwick` or `red_room` | `compId` parameter |
| Crowdwork | `io_theater` or `logan_square_improv` | Theatre slug |
| VBO Tickets | `esthers_follies` | `SITE_ID` and `EID` constants |
| SquadUP | `sunset_strip` or `dynasty_typewriter` | `user_ids` parameter |
| ThunderTix | `annoyance` | Base URL and filter prefixes |
| TicketSource | `comedy_clubhouse` | Venue slug |
| OvationTix (calendar) | `uncle_vinnies` | Production discovery URL |
| OvationTix (direct) | `four_day_weekend` | Buy-tickets page URL |
| StageTime | `comedy_corner_underground` | Subdomain slug |
| Punchup/Next.js RSC | `west_side` or `comedy_key_west` | Calendar page URL |
| OpenDate | `sports_drink` | Venue slug |
| Netlify Functions | `east_austin_comedy` | API endpoint URLs |
| Custom HTML | — | Build from scratch using `BaseScraper` |

---

## Platform Signature Quick Reference

When inspecting a new venue's website, use these markers to quickly identify the ticketing platform:

| Signal Type | What to Look For | Platform |
|---|---|---|
| **Buy link domain** | `ticketmaster.com` | Ticketmaster |
| **Buy link domain** | `eventbrite.com` | Eventbrite |
| **Buy link subdomain** | `v-{uuid}.seatengine.net` | SeatEngine v3 |
| **Buy link subdomain** | `{venue}.seatengine.net` (no v-) | SeatEngine v1 |
| **Buy link domain** | `tixr.com` | Tixr |
| **Buy link domain** | `{slug}.thundertix.com` | ThunderTix |
| **Buy link domain** | `ticketsource.com` / `ticketsource.us` | TicketSource |
| **Buy link domain** | `events.humanitix.com` | Humanitix |
| **Buy link domain** | `prekindle.com` | Prekindle |
| **Buy link domain** | `ci.ovationtix.com` | OvationTix |
| **Buy link domain** | `event.tixologi.com` | Tixologi |
| **Buy link domain** | `app.opendate.io` | OpenDate |
| **Buy link domain** | `squadup.com` | SquadUP |
| **Ticket subdomain** | `tickets.{venue}.com` + Ninkashi API | Ninkashi |
| **Network request** | `tockify.com/api/ngevent` | Tockify |
| **Network request** | `/api/open/GetItemsByMonth` | Squarespace |
| **Network request** | `crowdwork.com/api/v2/{theatre}/shows` | Crowdwork |
| **Network request** | `plugin.vbotickets.com` | VBO Tickets |
| **Network request** | `/.netlify/functions/availability` | Netlify Functions |
| **Network request** | `/wp-json/tribe/events/v1/events` | Tribe Events (WP) |
| **Page source** | `<script type="application/ld+json">` + `@type: Event` | JSON-LD |
| **Page source** | `self.__next_f.push()` RSC segments | Next.js RSC (StageTime, Punchup) |
| **Page source** | `<script id="__NEXT_DATA__">` | Next.js SSR (Vivenu) |
| **Page source** | `rhpSingleEvent` CSS class | rhp-events WordPress |
| **Page source** | `data-compId` + `wixstatic.com` | Wix Events |
| **Page source** | `squadup = { userId: [...] }` | SquadUP |
| **Page source** | `{slug}.stageti.me` links | StageTime |
| **Page footer** | "Powered by Seat Engine" | SeatEngine |
| **Page footer** | "Powered by Wix" | Wix |
| **Script src** | `cdn.seatengine.com/assets/application` | SeatEngine Classic |

---

## Architecture Components

Every venue scraper directory follows the **5-component pattern**:

```
scrapers/implementations/venues/{venue}/
  __init__.py       # Empty — marks as Python package
  scraper.py        # Main orchestration — extends BaseScraper
  data.py           # PageData model (MUST be named data.py, not page_data.py)
  extractor.py      # Raw data -> venue-specific event objects
  transformer.py    # Event objects -> Show objects
  models.py         # (optional) Venue-specific event dataclass
```

### Key Base Classes

| Class | Location | Purpose |
|---|---|---|
| `BaseScraper` | `scrapers/base/base_scraper.py` | Abstract base for all scrapers. Implements the 5-phase pipeline: `collect_scraping_targets()` -> `process_target()` -> `get_data()` (abstract) -> `transform_data()` -> `scrape_async()` |
| `EmailBaseScraper` | `scrapers/base/email_base_scraper.py` | Base for email-based scrapers (MIME parsing, HTML extraction) |
| `HttpConvenienceMixin` | `ports/http.py` | Provides `fetch_html()`, `fetch_json()`, `fetch_html_bare()` methods |

### Key Platform Clients

| Client | Location | Used By |
|---|---|---|
| `EventbriteClient` | `core/clients/eventbrite/` | Eventbrite scraper |
| `TixrClient` | `core/clients/tixr/` | All Tixr-based venue scrapers |
| `WixClient` | `core/clients/wix/` | Bushwick, Nick's, Red Room |
| `OvationTixClient` | `core/clients/ovationtix/` | Uncle Vinnies, Four Day Weekend, Comedy at the Carlson |
| `SeatEngineClient` | `core/clients/seatengine/` | SeatEngine v1/v3/classic/national scrapers |
| `TesseraClient` | `core/clients/tessera/` | Broadway Comedy Club |
| `ComedyCellarAPIClient` | `core/clients/comedy_cellar/` | Comedy Cellar |
| `TixologiClient` | `core/clients/tixologi/` | Laugh Factory Reno |
| `NinkashiClient` | `core/clients/ninkashi/` | Ninkashi scraper |
| `PunchupClient` | `core/clients/punchup/` | Punchup-based venues |
| `GothamClient` | `core/clients/gotham/` | Gotham |
| `LiveNationClient` | `core/clients/live_nation/` | Ticketmaster scraper |
| `VenuePilotClient` | `core/clients/venuepilot/` | StandUp NY enrichment |
