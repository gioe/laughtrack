# SCRAPERS.md — Platform Decision Guide

A developer onboarding a new comedy club should be able to pick the right scraper in under 5 minutes using this guide. Start at the **Decision Flowchart**, confirm with the **Platform Sections**, then follow the DB setup instructions.

---

## Entry Format

When adding a newly discovered platform or scraper pattern, add one platform
section using this shape. Keep the table as the canonical summary; put API
quirks, pricing behavior, pagination, bot blocking, and historical notes in the
bullets below it. If endpoint URLs are documented, verify them against the
actual client source before writing them down.

````md
### Platform Name

| | |
|---|---|
| **Scraper key** | `scraper_key` or venue-specific (reference: `existing_venue`) |
| **Platform** | `ScrapingPlatform` enum value, or `custom` when no enum exists |
| **DB field** | `scraping_url`, `scraping_sources.source_url`, metadata keys, or platform-specific columns |
| **Value format** | Exact URL/ID shape to store |
| **Generic?** | ✅ DB-only / ✅ generic for specific source shape / ❌ venue-specific code required |

**Detection signals:**
- Hostnames, widgets, CSS classes, page-source markers, or network requests that identify the platform

**API/source pattern:**
- Endpoint or page pattern used by the scraper
- Required request parameters or metadata

**Key extraction notes:**
- Date/time parsing, timezone, title, ticket URL, price, sold-out, lineup, and pagination details

**DB setup:**
```sql
-- Minimal row/update needed to onboard a venue
```

**Failure modes / gotchas:**
- Bot-blocking behavior, stale IDs, missing prices, duplicate pages, rate limits, or unsupported variants

**Reference implementation:**
- `apps/scraper/src/laughtrack/...`
- Reference venue/task, if known
````

When updating the decision flow or summary tables, update the matching platform
section in the same change so the quick references do not drift from the
canonical section.

---

## Decision Flowchart

```
Is there a Ticketmaster widget or ticketmaster.com buy link?
  └── YES → platform: Ticketmaster → scraper: live_nation for comedy-first venues
                                      scraper: ticketmaster_comedy for multi-purpose venues
              DB: ticketmaster_id = Discovery API venue ID (e.g. KovZpZAJalFA)

Is there an Eventbrite widget or eventbrite.com buy link?
  └── YES → platform: Eventbrite → scraper: eventbrite
              DB: eventbrite_id = organizer ID (11 digits) or venue ID (8-9 digits)

Is there a DICE event-list widget or widgets.dice.fm script?
  └── YES → platform: DICE → scraper: dice (generic)
              DB: source_url = venue-owned calendar page; metadata must include
                  dice_api_key plus at least one dice_venue_id/dice_venue_name/
                  dice_promoter_id/dice_promoter_name filter
              (see DICE section for browser extraction details)

Is there an Etix venue page or a venue-owned Rockhouse Partners event listing
with etix.com/ticket/p/ buy links?
  └── YES → platform: Etix → scraper: etix
              DB: source_url = Etix venue URL if reachable, otherwise the
                  venue-owned Rockhouse public listing URL

Is there a SeatEngine buy link?
  └── Check the subdomain in the link:
      v-{uuid}.seatengine.net → scraper: seatengine_v3
                                 DB: seatengine_id = UUID from page JSON-LD "identifier"
      (no v- prefix)          → scraper: seatengine  (or seatengine_classic for legacy)
                                 DB: seatengine_id = numeric venue ID (1–700 range)

Is there a buy link to `{venue}.thundertix.com`?
  └── YES → platform: ThunderTix → generic scraper, configure via scraping_sources
              (see ThunderTix section — set platform=thundertix, scraper_key=thundertix)

Is there a buy link to `{venue}.showare.com` or an accesso ShoWare footer?
  └── YES → platform: custom → scraper: showare
              DB: source_url = ShoWare default.asp or venue root URL
              (see ShoWare section — use metadata title filters for multi-purpose theatres)

Is there a tixr.com buy link?
  └── YES → platform: Tixr → scraper: tixr for server-rendered event links
                                      tixr_public_card for supported venue-owned cards
                                      tixr_webflow_day_card for supported Webflow day cards
                                      venue-specific only for unsupported source shapes
              (see Tixr section — short/long URL format and DataDome behavior matter)

Is there an events.timely.fun embed or a WordPress All-in-One Event Calendar / time.ly widget?
  └── YES → platform: custom → scraper = 'timely' (generic)
              DB: source_url = https://events.timely.fun/{slug}/agenda,
                  metadata.timely_calendar_id = numeric calendar id
              (see Timely section — browser requests require a public x-api-key)

Is there a Tugoz widget (`www.tugoz.com/js/tugoz.js`) or SITE_CONFIG.LIVE_EVENTS mapping?
  └── YES → platform: custom → scraper = 'tugoz' (generic)
              DB: source_url = venue config.js that defines LIVE_EVENTS;
                  metadata.event_keys optional
              (see Tugoz section — stale disabled event keys are common)

Is there a Showpass widget or showpass.com buy link?
  └── YES → platform: Showpass → scraper = 'showpass' (generic)
              DB: scraping_url = Showpass calendar API base URL
              (see Showpass section for details)

Is there an events.ticketleap.com/events/{slug} link or a TicketLeap widget?
  └── YES → platform: TicketLeap → scraper = 'ticketleap' (generic)
              DB: scraping_url = https://events.ticketleap.com/events/{org_slug}
              (see TicketLeap section — listing page requires JS, detail pages emit
               standard schema.org Event JSON-LD)

Is there an exploretock.com/{business_slug} page or exploretock.com/{business_slug}/event/{id}/{slug} buy link?
  └── YES → platform: Tock → scraper = 'tock' (generic)
              DB: source_url = https://www.exploretock.com/{business_slug}
              (see Tock section — business page requires JS and exposes rendered
               Redux calendar state)

Is there a fareharbor.com/embeds/book/{shortname}/ widget or FareHarbor booking link?
  └── YES → platform: custom → scraper = 'fareharbor' (generic)
              DB: source_url = https://fareharbor.com/embeds/book/{shortname}/,
                  metadata.shortname = {shortname}
              (see FareHarbor section — public item list plus monthly calendar JSON)

Is there a brasstix.com/pmt/calendar.php?Show=... ticket calendar?
  └── YES → platform: BrassTix → scraper = 'brasstix' (generic)
              DB: source_url = full BrassTix calendar.php URL
              (see BrassTix section — calendar events are inline eventArray JS)

Is the box office a Tessitura TNEW page loading `production.tnew-assets.com`
assets and POSTing `/api/products/productionseasons`?
  └── YES → platform: custom → scraper = 'tessitura_tnew' (generic)
              DB: source_url = TNEW list page, usually /events?view=list

Is there a SimpleTix event page link?
  └── YES → platform: SimpleTix → scraper = 'simpletix' (generic)
              DB: scraping_url = full SimpleTix event page URL

Is there a Shopify collection page for shows?
  └── YES → platform: Shopify → scraper = 'shopify' (generic)
              DB: scraping_url = Shopify collection page URL

Is there a BookTix box office at `{org}.booktix.com`?
  └── YES → platform: BookTix → scraper = 'booktix' (generic)
              DB: source_url = https://{org}.booktix.com/dept/main

Check browser network requests (browser_navigate + browser_network_requests):
  └── tockify.com/api/tagoptions/<calname>   → platform: Tockify
                                                → new venue-specific scraper required
  └── /api/open/GetItemsByMonth              → platform: Squarespace
                                                → scraper: squarespace (generic; set scraping_url)
  └── crowdwork.com/api/v2/<theatre>/shows   → platform: Crowdwork
                                                → new venue-specific scraper required
  └── plugin.vbotickets.com                  → platform: VBO Tickets
                                                → scraper: vbo_tickets for multi-event listings
                                                  (single-recurring-show venues may still use venue-specific scrapers)
  └── /.netlify/functions/availability       → platform: Netlify Functions
                                                → new venue-specific scraper required
  └── showpass.com/api/public/venues/          → platform: Showpass
                                                → scraper: showpass (generic; set scraping_url)
  └── widgets.dice.fm/dice-event-list-widget.js
      + partners-endpoint.dice.fm/api/v2/events
                                             → platform: DICE
                                               → scraper: dice (generic; set source_url + metadata)
  └── editmysite.com/app/store/api/          → platform: Square Online (Weebly)
                                                → new venue-specific scraper required
                                                (see Square Online section — use coral_gables_comedy_club as reference)
  └── /wp-json/tribe/events/v1/events        → platform: Tribe Events Calendar (WordPress)
                                                → scraper: the_events_calendar (generic; set source_url)
  └── /wp-json/wp/v2/mec-events              → platform: Modern Events Calendar (WordPress)
                                                → scraper: modern_events_calendar (generic; set source_url)
  └── /wp-json/wp/v2/posts?categories=<id>   → WordPress category posts
                                                → venue-specific scraper when dates live only in post titles
  └── jetbook.co/elasticsearch/msearch        → platform: JetBook (Bubble.io)
                                                → scraper: jetbook (generic)
                                                  DB: scraping_url = https://jetbook.co/o_iframe/<venue-slug>

Check page source:
  └── squadup = { userId: [<id>] ... } in page JS
        → platform: SquadUP → new venue-specific scraper required
  └── <script type="application/ld+json"> with "@type": "Event"
        → platform: JSON-LD → scraper: json_ld (generic; set scraping_url)
  └── Odoo website_event pages at /event with itemtype="http://schema.org/Event"
      microdata cards/detail pages
        → platform: custom → scraper: odoo_events (generic; set source_url)
  └── CSS classes: rhpSingleEvent / eventWrapper / rhp-event__title--list
        → platform: rhp-events (WordPress) → scraper: comedy_magic_club (generic; set scraping_url)
  └── data-compId on Wix event widget / wixstatic.com assets
        → platform: Wix Events → new venue-specific scraper required
  └── CSS classes: eventRow / dateTime (with content attr) / event-btn
        → platform: TicketSource → new venue-specific scraper required
              (see TicketSource section — use comedy_clubhouse scraper as reference)
  └── events.humanitix.com/host/<slug> in buy links
        → platform: Humanitix → scraper: json_ld (generic; set scraping_url to host URL)
  └── tickets.{venue}.com subdomain + api.ninkashi.com network requests
        → platform: Ninkashi → scraper: ninkashi (generic; set scraping_url to subdomain)

Is there a ShowSlinger widget or app.showslinger.com buy link?
  └── YES → platform: ShowSlinger → scraper: show_slinger
              DB: scraping_url = full combo_widget URL with id, secure_code, and origin_url
              (see ShowSlinger section — origin_url is REQUIRED to bypass Cloudflare)

Is there a secure.sellingticket.com/design22/clients/list page?
  └── YES → platform: SellingTicket → scraper: sellingticket (generic)
              DB: scraping_url = full index_byUserListAll.aspx URL with OrganizationID
              (see SellingTicket section — configure include_title_patterns for multi-use venues)

None of the above → custom HTML scraper required
  (StageTime: self.__next_f.push RSC segments at {slug}.stageti.me — see StageTime section)
  (OpenDate: server-rendered confirm-card divs at app.opendate.io — see OpenDate section)
```

---

## Platform Sections

### Ticketmaster

| | |
|---|---|
| **Scraper key** | `live_nation` |
| **DB field** | `ticketmaster_id` |
| **Value format** | Alphanumeric Discovery API venue ID, e.g. `KovZpZAJalFA` — NOT a numeric ID |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Ticketmaster widget embedded on the venue page
- Buy links pointing to `ticketmaster.com`
- Discovery API returns JSON-LD `@type=Event` blocks

**Finding the venue ID:**
```bash
curl -s "https://app.ticketmaster.com/discovery/v2/venues.json?apikey=<KEY>&keyword=<venue name>&countryCode=US" \
  | python3 -c "import sys,json; [print(v['id'], v['name']) for v in json.load(sys.stdin).get('_embedded',{}).get('venues',[])]"
```

**Diagnosis — 0 events returned:**
When a Ticketmaster-backed scraper returns 0 events, first verify the stored `ticketmaster_id` is the correct **Discovery API venue ID** (alphanumeric, e.g. `KovZ917ARvk`) — NOT a numeric ID from another system. Query without any classification filter first to confirm events exist for the venue ID at all; only investigate `classificationName` filters *after* confirming the ID works.

**Multi-purpose venues:** Use `scraper_key='ticketmaster_comedy'` when the Ticketmaster venue hosts concerts, sports, talks, tours, VIP add-ons, or other non-comedy events. This focused scraper calls the same Discovery API with `classificationName=Comedy`, then keeps the existing comedy transformer guard. Keep `live_nation` for comedy-first venues where uncategorized Arts & Theatre events should remain eligible.

**Nightly TM path is batched (`ticketmaster_national`, TASK-3042).** Do NOT add new
TM comedy venues as per-venue `ticketmaster_comedy` nightly sources by default —
that pattern made one Discovery API call per venue against a shared 5 req/sec
limit and blew the nightly past the 120-min GHA timeout once ~800 TM venues
accumulated. The nightly now runs the single `ticketmaster_national` source target
(~18 windowed national `classificationName=Comedy` calls over a 180-day horizon),
which discovers every US comedy venue, upserts a club per venue, and persists in
chunks. Per-venue `ticketmaster_comedy` is reserved for the **edge cases national
cannot cover**: venues with comedy beyond the 180-day horizon or not classified
`Comedy` nationally (national returns nothing for them). Name differences alone
are not a keep-list reason: `ticketmaster_national` resolves discovered venues by
the stable `scraping_sources.ticketmaster_id` first, then falls back to name for
brand-new venues (TASK-3043). The cutover migrations
(`migrations/20260621_cutover_ticketmaster_comedy_to_national.sql` and
`migrations/20260621_rekey_ticketmaster_national_upsert.sql`) key the keep-list
on `ticketmaster_id`.

**DB setup:**
```sql
UPDATE clubs SET scraper = 'live_nation', ticketmaster_id = 'KovZpZAJalFA' WHERE name = 'My Club';
```

---

### DICE

| | |
|---|---|
| **Scraper key** | `dice` |
| **Platform** | `dice` |
| **DB field** | `scraping_sources.source_url` plus metadata keys |
| **Value format** | `source_url` = venue-owned calendar/widget page; metadata = `dice_api_key` plus one or more DICE venue/promoter filters; optional `dice_tags` CSV |
| **Generic?** | ✅ DB-only for DICE event-list widgets |

**Detection signals:**
- Page or rendered DOM loads `https://widgets.dice.fm/dice-event-list-widget.js`
- Inline rendered script calls `DiceEventListWidget.create({...})`
- Browser network calls `https://partners-endpoint.dice.fm/api/v2/events`

**API/source pattern:**
- Scraper source: `apps/scraper/src/laughtrack/scrapers/implementations/api/dice/scraper.py`
- Endpoint: `GET https://partners-endpoint.dice.fm/api/v2/events`
- Required header: `x-api-key: <metadata.dice_api_key>`
- Core params: `page[size]`, `types=linkout,event`, `filter[flags][]=going_ahead`, `filter[flags][]=rescheduled`
- Supported filters from metadata:
  - `dice_venue_id` → `filter[venue_ids][]`
  - `dice_venue_name` → `filter[venues][]`
  - `dice_promoter_id` → `filter[promoter_ids][]`
  - `dice_promoter_name` → `filter[promoters][]`
  - `dice_tags` → `filter[tags][]`
- Pagination comes from `links.next`, but DICE may return an `events-api.dice.fm`
  URL there. The scraper preserves the query string and replays it against
  `partners-endpoint.dice.fm/api/v2/events`, matching the widget's own next-page
  behavior and avoiding `events-api` 403s.

**Key extraction notes:**
- Use a browser/network capture when static HTML only shows a Squarespace shell. The Color Club `/comedy` rendered page had:
  `DiceEventListWidget.create({"partnerId":"d285d692","apiKey":"...","venues":["Color Club"],"tags":["type:comedy"], ...})`
- Prefer numeric `dice_venue_id` or `dice_promoter_id` once the first API response reveals them. Keep name filters in metadata as audit context/fallback.
- Ticket URL uses `url` for native DICE events and `external_url` for linkout events.
- Price is `ticket_types[0].price.total / 100` when present; linkout/free events may expose top-level `price`.
- The scraper filters cancelled/postponed flags and keeps DICE `linkout` rows so venue calendars that point to external ticketing still produce shows.

**DB setup:**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'dice'::"ScrapingPlatform", 'dice', 'https://www.example.com/calendar', 0, TRUE,
       jsonb_build_object(
         'dice_api_key', '<apiKey from DiceEventListWidget.create>',
         'dice_partner_id', '<partnerId from widget config>',
         'dice_venue_id', '<numeric venue id from first API response>',
         'dice_venue_name', '<widget venue name>',
         'dice_tags', '<optional comma-separated DICE tags, e.g. type:comedy>'
       ),
       now(), now()
FROM clubs c
WHERE c.name = 'My Club'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'dice');
```

**Failure modes / gotchas:**
- Static `curl` of Squarespace pages may not show the inline widget config; use a browser-rendered DOM/network capture.
- DICE partner API requires the widget API key in `x-api-key`; unauthenticated requests fail or return no usable payload.
- The public widget can filter by names, but names are less stable than numeric venue/promoter ids. Capture numeric ids from the first successful API response.
- Mixed-use venues expose music, markets, and workshops alongside comedy. Prefer the venue's comedy-specific widget/page when present and copy its `tags` value into `dice_tags`.

**Reference implementation:**
- `apps/scraper/src/laughtrack/scrapers/implementations/api/dice/scraper.py`
- `apps/scraper/src/laughtrack/core/entities/event/dice.py`
- Color Club (TASK-3013): `https://www.colorclub.events/comedy`, DICE venue id `14681`, promoter id `14931`, tag `type:comedy`

---

### Eventbrite

| | |
|---|---|
| **Scraper key** | `eventbrite` |
| **DB field** | `eventbrite_id` |
| **Value format** | Organizer ID (11 digits, from `/o/<slug>-<id>` URL) or venue ID (8-9 digits) |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Eventbrite widget embedded on the venue page
- Buy links pointing to `eventbrite.com`
- Organizer URL: `eventbrite.com/o/<slug>-<organizer_id>`

**Finding the ID:**
1. **Organizer ID**: extract from `eventbrite.com/o/<slug>-<organizer_id>` URL
2. **Venue ID**: grab any event ID from the embedded widget JS (`eventId: '<digits>'`), fetch `eventbrite.com/e/<event_id>`, find the organizer link

The scraper tries `/venues/{id}/events/` first; if that 404s, it auto-falls back to `/organizers/{id}/events/`.

**Organizer ID vs Venue ID:**
- Organizer ID: typically 11 digits, from `/o/<slug>-<id>` URL — auto-routed to `/organizers/{id}/events/`
- Venue ID: typically 8–9 digits, from an individual event's JSON `"venue_id"` field — auto-routed to `/venues/{id}/events/`
The scraper tries the venue endpoint first and auto-falls back to the organizer endpoint on 404.

**`scraping_url` format:** Always use the full organizer URL including the slug:
  `'https://www.eventbrite.com/o/<slug>-<organizer_id>'`
The slug is required for consistency with existing venues.

**Multi-location chains:** Don't guess the organizer URL using a sibling location's ID (always redirects to the primary organizer). Instead:
1. Fetch the venue's show listing page (e.g. `laughfactory.com/long-beach`)
2. Grab any Eventbrite event ID from the embedded widget JS (`eventId: '<digits>'` in page source)
3. Fetch `https://www.eventbrite.com/e/<event_id>` — the organizer URL appears in the page data

**Wix + Eventbrite backend:** Some Wix-hosted venues use the "Events Calendar" widget (inffuse.eventscalendar.co) backed by Eventbrite. Identify via Playwright network inspection:
- POST to `https://inffuse.eventscalendar.co/js/v0.1/calendar/data`
- GET to `https://broker.eventscalendar.co/api/eventbrite/events?calendar=<id>`
The `calendar=` parameter **is the Eventbrite organizer ID** — use `scraper='eventbrite'` with that ID. No Wix access token needed.

**DB setup:**
```sql
UPDATE clubs SET scraper = 'eventbrite', eventbrite_id = '30460267696' WHERE name = 'My Club';
```

**Mixed-use organizers (classes / music vs comedy):** a single Eventbrite
organizer feed often mixes non-comedy listings (improv classes at training
centers; band/DJ acts at Blues/Jazz/Comedy venues) with the comedy shows. Three
opt-in `scraping_sources.metadata` title filters isolate the comedy (all OFF by
default, so pure-comedy sources are unchanged):
- `include_title_patterns: ['<regex>', ...]` — keep ONLY events whose title
  matches at least one pattern (the comedy allowlist). Use this when the
  non-comedy titles are unpredictable, e.g. a Blues/Jazz/Comedy venue whose
  music events are named after the band/DJ (TASK-3205, Deja Blue) — an exclude
  list can't enumerate them, so allowlist the comedy words instead.
- `exclude_classes: true` — applies built-in class/course/workshop/drop-in/leveled-improv
  patterns.
- `exclude_title_patterns: ['<regex>', ...]` — drop events whose title matches any pattern.

`include` and `exclude` compose: an event must match an include pattern AND not
match an exclude pattern to survive. All are matched case-insensitively against
the event title only.

```sql
-- Comedy allowlist for a mixed Blues/Jazz/Comedy organizer feed:
UPDATE scraping_sources
SET metadata = jsonb_set(COALESCE(metadata,'{}'::jsonb), '{include_title_patterns}',
    '["comedy","stand[ -]?up","comedian"]'::jsonb)
WHERE club_id = <id> AND scraper_key = 'eventbrite';

-- Class exclusion for an improv training center:
UPDATE scraping_sources
SET metadata = jsonb_set(COALESCE(metadata,'{}'::jsonb), '{exclude_classes}', 'true')
WHERE club_id = <id> AND scraper_key = 'eventbrite';
```

---

### TicketWeb

| | |
|---|---|
| **Scraper key** | `ticketweb` |
| **DB field** | `scraping_sources.source_url` (the venue's own calendar page) plus optional metadata title filters |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Buy links pointing to `ticketweb.com/event/...?pl=<client>` on the venue's own site
- A WordPress `tw-plugin-upcoming-event-list` widget, or an inline `var all_events = [...]` JS array, on the venue's `/calendar` page

**Datasource:** the venue's OWN calendar page (not ticketweb.com). The scraper parses the inline `var all_events` JS array first, then falls back to the `tw-plugin-upcoming-event-list` HTML (with pagination), and reads the TicketWeb buy link + sold-out status off each event's detail page. `source_url` = the venue's calendar page.

**Mixed-use live-music venues (comedy vs concerts):** many TicketWeb rooms are live-music venues that host a recurring comedy series alongside mostly band/DJ shows. Two opt-in `scraping_sources.metadata` title filters keep only the comedy (OFF by default, so pure-comedy TicketWeb venues like The Stand Up Comedy Club are unchanged):
- `include_title_patterns: ['<regex>', ...]` — keep ONLY events whose title matches at least one pattern (the comedy-series allowlist).
- `exclude_title_patterns: ['<regex>', ...]` — drop events whose title matches any pattern.

```sql
-- Onboard a mixed-use live-music venue, keeping only its comedy series:
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
VALUES (
    <club_id>, 'custom'::"ScrapingPlatform", 'ticketweb',
    'https://<venue>/calendar/', 0, TRUE,
    jsonb_build_object('include_title_patterns',
        jsonb_build_array('Stand-Up Comedy', 'Clement St Comedy')),
    NOW(), NOW()
);
```

---

### Etix / Rockhouse Partners

| | |
|---|---|
| **Scraper key** | `etix` |
| **Platform** | `etix` |
| **DB field** | `source_url` |
| **Value format** | Prefer `https://www.etix.com/ticket/v/{venue_id}/{slug}`. If that endpoint is DataDome-blocked but the venue site exposes the Rockhouse event widget, use the venue-owned public listing URL. |
| **Generic?** | ✅ Generic for Etix venue pages and Rockhouse public listings with Etix ticket links |

**Detection signals:**
- Buy links point to `www.etix.com/ticket/p/...`
- Venue link points to `www.etix.com/ticket/v/{venue_id}/...`
- Footer says "Powered by ROCKHOUSE PARTNERS an ETIX company"
- Event list markup contains Rockhouse classes such as `rhp-event__single-event--list`, `rhp-event__title--list`, or `rhp-events-list-separator-month`

**DB setup:**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled)
VALUES (<club_id>, 'etix'::"ScrapingPlatform", 'etix', 'https://www.etix.com/ticket/v/<venue_id>/<slug>', 0, TRUE);
```

If the Etix venue API is DataDome-blocked and the venue-owned page has the Rockhouse widget, set `source_url` to the venue public listing instead:

```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled)
VALUES (<club_id>, 'etix'::"ScrapingPlatform", 'etix', 'https://venue.example.com/', 0, TRUE);
```

---

### SeatEngine — Identification Checklist

When onboarding a new SeatEngine venue, check the subdomain before assuming which platform variant it uses:

1. Check the page footer for "Powered by Seat Engine" + the banner/contact link
2. If the linked domain matches `v-{uuid}.seatengine.net` → **v3 platform** (UUID-based, GraphQL API). Scanning numeric IDs 1–700 will find nothing.
3. If page source contains `cdn.seatengine.com/assets/application` in `<script>` tags → **Classic platform** (HTML-rendered, no REST API). The numeric venue ID is embedded in the logo CDN URL: `https://files.seatengine.com/styles/logos/{id}/original/`.
4. If none of the above → **v1 platform** (numeric ID, REST API). Use `seatengine_national` to discover IDs via enumeration.

⚠️ **CDN file IDs ≠ API venue IDs.** The `files.seatengine.com/styles/logos/{ID}/` CDN path embeds a classic-platform file storage ID — this is NOT the same namespace as the new-platform API (`services.seatengine.com/api/v1/venues/{id}`).

---

### SeatEngine v1

| | |
|---|---|
| **Scraper key** | `seatengine` (or `seatengine_classic` for legacy endpoints) |
| **DB field** | `seatengine_id` |
| **Value format** | Numeric ID, typically in the 1–700 range |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Buy links pointing to a seatengine.net domain **without** the `v-{uuid}` prefix
- Footer: "Powered by Seat Engine" with a non-UUID link
- Page footer or contact link uses a plain subdomain (e.g., `myvenue.seatengine.net`)

**Finding the ID:** Use the `seatengine_national` discovery scraper, or enumerate via the SeatEngine REST API.

**DB setup:**
```sql
UPDATE clubs SET scraper = 'seatengine', seatengine_id = '123' WHERE name = 'My Club';
```

---

### SeatEngine Classic (Legacy)

| | |
|---|---|
| **Scraper key** | `seatengine_classic` |
| **DB field** | `scraping_url` (runtime) · `seatengine_id` (metadata only) |
| **Value format** | `scraping_url`: full venue calendar URL · `seatengine_id`: numeric (may be NULL) |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**⚠️ Important: `seatengine_id` is NOT used at runtime.**
`seatengine_classic` fetches events from `scraping_url` directly — `seatengine_id` is stored for
record-keeping only and never appears in any URL or API call. The field name is misleading; do NOT
enumerate or look up numeric IDs for `seatengine_classic` venues. If `seatengine_id` is NULL, the
scraper still works correctly as long as `scraping_url` is set.

**⚠️ CDN file IDs ≠ API venue IDs.**
`files.seatengine.com/styles/logos/{ID}/` CDN URLs embed a numeric ID, but this is the
classic-platform **file storage ID** — it is NOT the same namespace as the new-platform API
(`services.seatengine.com/api/v1/venues/{id}`). The new platform recycles numeric IDs as venues
migrate or deactivate, so the same number may point to a completely different venue in the API.
Do not use CDN URL extraction to recover or verify SeatEngine API venue IDs.

**Detection signals:**
- Same as SeatEngine v1, but the venue's calendar is served at a custom URL path rather than via
  the standard SeatEngine REST API
- `scraping_url` is set; `seatengine_id` may be NULL or present as a reference value

**DB setup:**
```sql
UPDATE clubs SET scraper = 'seatengine_classic', scraping_url = 'https://myvenue.seatengine.net/shows' WHERE name = 'My Club';
-- seatengine_id may be set for record-keeping but is ignored at runtime
```

---

### SeatEngine v3

| | |
|---|---|
| **Scraper key** | `seatengine_v3` |
| **DB field** | `seatengine_id` |
| **Value format** | UUID, e.g. `cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3` |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Buy links or contact link uses `v-{uuid}.seatengine.net` subdomain
- Footer: "Powered by Seat Engine" + banner/contact link with `v-` prefix
- Page JSON-LD `<script>` contains `"identifier": "<uuid>"`

**Finding the UUID:** Inspect the page's JSON-LD `<script>` for `"identifier"`.

**DB setup:**
```sql
UPDATE clubs SET scraper = 'seatengine_v3', seatengine_id = 'cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3' WHERE name = 'My Club';
```

---

### Tixr

| | |
|---|---|
| **Scraper key** | `tixr`, `tixr_public_card`, or venue-specific (e.g. `haha_comedy_club`) |
| **DB field** | `scraping_url` |
| **Generic?** | ✅ for detail-page enrichment and supported public-card pages |

**Detection signals:**
- Buy buttons linking to `tixr.com/groups/{group}/events/{slug}-{id}` (long form)
- Buy buttons linking to `tixr.com/e/{id}` (short form)

**URL format matters:**
| Format | Example | Support |
|---|---|---|
| Long form (`-{id}`) | `tixr.com/groups/foo/events/show-name-12345` | ✅ Full — JSON-LD extracted |
| Short form (`/e/{id}`) | `tixr.com/e/12345` | ✅ Full — redirect followed, JSON-LD extracted |
| Double-dash (`--{id}`) | `tixr.com/groups/foo/events/show-name--12345` | ❌ Silently skipped — no JSON-LD in SSR |

**Implementation pattern:** First decide which Tixr identity applies:
- `tixr`: the source page only provides Tixr event URLs, so the scraper must fetch each Tixr-hosted event page and parse JSON-LD detail data.
- `tixr_public_card`: the source page is venue-owned and each event card already exposes title, date, time, and a Tixr ticket URL. Tixr is only the checkout provider; event-detail pages are not fetched.
- Venue-specific key: the source shape is not covered by either generic path, such as a custom API feed or markup that needs bespoke extraction.

**Generic `tixr` scraper (server-rendered calendar pages with Tixr detail enrichment):**
When a venue's calendar page (own website or a Tixr group page like `tixr.com/groups/<slug>`) embeds Tixr event links in server-rendered HTML, use the generic `tixr` scraper — no custom Python code needed:
- `scraper_key = 'tixr'`
- `source_url = '<venue calendar page URL>'`

The `TixrScraper` fetches the page, extracts all Tixr URLs (both short-form and long-form) via `TixrExtractor`, then batch-resolves each to a `TixrEvent` via `TixrClient`.

**Generic `tixr_public_card` scraper (venue-owned public cards):**
When a venue-owned page already contains complete event cards plus Tixr ticket URLs, use `tixr_public_card` instead of `tixr`:
- `scraper_key = 'tixr_public_card'`
- `source_url = '<venue-owned calendar page URL>'`

`TixrPublicCardScraper` parses the venue page directly and does not call `TixrClient.get_event_detail_from_url()`. Use this for St. Marks Comedy Club and House of Comedy Bloomington style Webflow cards where DataDome blocks Tixr detail enrichment but the public card has enough data to build shows.

**Audit remaining DataDome-dependent Tixr sources:**
```sql
SELECT c.id, c.name, ss.source_url, ss.metadata
FROM scraping_sources ss
JOIN clubs c ON c.id = ss.club_id
WHERE ss.platform = 'tixr'::"ScrapingPlatform"
  AND ss.scraper_key = 'tixr'
  AND ss.enabled = true
ORDER BY c.name;
```

**When to use a custom scraper instead:** If the venue's Tixr group page triggers DataDome bot-detection (returns 403 or empty results when fetched via `fetch_html`), use a Covina-style venue scraper that calls `tixr_client._fetch_tixr_page(url)` instead — this uses a bare curl_cffi session with no application headers, bypassing DataDome.

**Group-events API fallback (DataDome-blocked group pages):**
When a Tixr group page is DataDome-blocked through every scraper fetch path, the
generic `tixr` scraper falls back to the JSON API the page itself consumes —
`GET https://www.tixr.com/api/groups/{numeric_group_id}/events?page=N` — via
`TixrClient.fetch_group_events`. Enable per source:
- `scraping_sources.metadata.tixr_group_events_api_fallback = true`
- `scraping_sources.metadata.tixr_group_id = '<numeric id>'` (string)
- `source_url` may be the Tixr group page or a venue-owned page that links Tixr
  events: the fallback fires when the calendar page yields no HTML, when no Tixr
  URLs are extracted, or when every extracted detail URL fails extraction
  (TASK-2763). Pointing source_url at the Tixr group page (Covina/Rose City
  pattern, TASK-2125) remains the most direct configuration.

The API accepts only **numeric** group ids — slugs return 400. To discover the
id: load `tixr.com/groups/<slug>` in a real headed browser (e.g. Playwright MCP)
and watch network requests for `/api/groups/{id}/events` (Covina=1613, Rose
City=2444). Bounded id scans don't work: every probe is DataDome-403'd from
scraper egress, so hits are indistinguishable from misses.

**When per-event Tixr fetches are blocked in CI:** Tixr's DataDome WAF can block GitHub Actions IP ranges even with curl_cffi impersonation. If a venue's calendar page already embeds all needed show data (name, date, time, performer, ticket URL), prefer `tixr_public_card` when the markup matches the shared public-card parser; otherwise build a custom scraper that extracts directly from the calendar HTML:
- `haha_comedy_club`: Webflow calendar with JSON-LD Event blocks (name, date, performer, ticket URL) + time in `<div class="month day time">` — see `scrapers/implementations/venues/haha_comedy_club/`
- `laugh_boston`: Pixl Calendar API response includes all show data (title, start, timezone, sales) — `LaughBostonEventExtractor.parse_events_from_pixl()` builds `TixrEvent` objects directly
- `tixr` with `scraping_sources.metadata.pixl_calendar_api_url`: venue-owned Pixl Calendar API response is parsed directly into `TixrEvent` objects using `sales.currentPrice` tiers and Tixr `ticketUrl` values. Use this when a venue's Webflow/Tixr page exposes only a partial card subset or no prices, but Pixl exposes the full inventory.

**Decision notes — should HAHA / Laugh Boston become `tixr_public_card`?**

`TixrScraper` is generic only when the upstream page can be treated as:
1. fetch calendar HTML
2. extract Tixr URLs
3. fetch each Tixr event page
4. parse JSON-LD from the Tixr event page

`TixrPublicCardScraper` is narrower: it expects venue-owned Webflow-style event cards with title, month, day, time, and a Tixr ticket link. Both `haha_comedy_club` and `laugh_boston` intentionally break the `tixr` detail-enrichment path, but neither is a drop-in `tixr_public_card` source today.

- `haha_comedy_club` should stay custom for now. The Webflow calendar page already contains one JSON-LD `Event` block per show plus the start time in nearby HTML, and the linked short-form `tixr.com/e/{id}` pages hit 100% HTTP 403 failure in the 2026-04-01 nightly run. Its markup is not the same card structure used by St. Marks / House of Comedy Bloomington.
- `laugh_boston` should stay custom for now. The Pixl Calendar API became the source because the homepage-based Tixr flow only surfaced a small subset of shows, and the Pixl endpoint returns the full catalogue plus the fields needed to build `Show`/`TixrEvent` objects directly. `tixr_public_card` does not operate on JSON feeds.

**Short URL format:** Tixr event links appear in two formats:
1. **Long form**: `https://www.tixr.com/groups/{group}/events/{slug}-{id}` — regex: `r"https?://[^\s\"]*tixr\.com/[^\s\"]*/events/[^\s\"]*"`
2. **Short form**: `https://tixr.com/e/{id}` — regex: `r"https?://(?:www\.)?tixr\.com/e/(\d+)"`

`TixrClient.get_event_detail_from_url()` handles both formats transparently — curl_cffi follows the redirect from short URLs to the full event page.

**Double-dash format (`--{id}`) — Won't-Fix:**
The `--{id}` URL format (`/events/{slug}--{id}`) only embeds `window.pageSetup = { eventId: {id} }` in SSR HTML — no JSON-LD, no date, no performers. Event data requires a DataDome CAPTCHA-solved JS session to fetch from the client-side API, which curl_cffi impersonation cannot provide. These events are silently skipped with a specific warning:
> "Tixr special-event page (--ID format) has no JSON-LD; data requires JS execution — skipping: {url}"

**Smoke test pattern:** `tixr` scraper tests instantiate `TixrScraper(club)`, mock `TixrScraper.fetch_html` (not `_fetch_tixr_page`), and assert `get_event_detail_from_url()` is awaited. `tixr_public_card` tests instantiate `TixrPublicCardScraper(club)`, mock `TixrPublicCardScraper.fetch_html`, and assert `get_event_detail_from_url()` is not called.

---

### Tixr Webflow Day Card

| | |
|---|---|
| **Scraper key** | `tixr_webflow_day_card` |
| **DB fields** | `scraping_sources.source_url` · `scraping_sources.metadata.tixr_group_fragment` |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:** Venue-owned Webflow homepage where each show is rendered as `<a class="day-card">` whose `href` points at a Tixr group URL (e.g. `tixr.com/groups/<slug>/events/...`). Selectors and date/time formats are identical across these venues; the only per-venue input is the Tixr group fragment used to filter foreign cards on shared homepages.

**Why this is separate from `tixr_public_card`:** `tixr_public_card` parses St. Marks / House of Comedy Bloomington style cards that don't share `a.day-card` markup. The day-card path is its own card shape (House of Comedy BC, ...). Comic Strip Edmonton previously used this path, but now routes through the `tixr` Pixl Calendar API path because Pixl exposes the full inventory and sale-tier prices.

**DB setup — fresh onboarding (no prior scraping_sources row):**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, enabled, priority, metadata)
VALUES (
    <id>,
    'custom',
    'tixr_webflow_day_card',
    'https://<venue-webflow-homepage>/',
    TRUE,
    0,
    jsonb_build_object('tixr_group_fragment', 'tixr.com/groups/<group-slug>/events/')
);
```

**DB setup — folding an existing per-venue wrapper onto the generic key:** match by the legacy `scraper_key` (not by `priority`, which would also pick up other platforms' rows). See `migrations/20260509161000_fold_webflow_day_card_venues_into_generic/migration.sql` for a worked example covering House of Comedy BC.

**When NOT to use it:** If the venue's calendar page exposes JSON-LD `Event` blocks with the start time in adjacent visible HTML (e.g. `<div class="month day time">`), keep a custom scraper — `haha_comedy_club` is the canonical example. The day-card extractor relies on `a.day-card` markup; venues that don't follow that exact card structure won't match.

**Smoke test pattern:** `tixr_webflow_day_card` tests instantiate `TixrWebflowDayCardScraper(club)` with a `Club` whose `active_scraping_source.metadata` contains `tixr_group_fragment`, mock `TixrWebflowDayCardScraper.fetch_html`, and assert that `WebflowDayCardPageData` is returned. Construction without `tixr_group_fragment` or without `source_url` raises `ValueError`.

---

### Tugoz

| | |
|---|---|
| **Scraper key** | `tugoz` |
| **Platform** | `custom` |
| **DB field** | `scraping_sources.source_url`; optional `scraping_sources.metadata.event_keys` / `event_ids` |
| **Value format** | Venue-owned config JS URL that defines `SITE_CONFIG.LIVE_EVENTS`, e.g. `https://masalacc.org/config.js?v=2` |
| **Generic?** | ✅ Generic for Tugoz widgets that expose live event IDs through config JS |

**Detection signals:**
- Venue page includes `www.tugoz.com/js/tugoz.js`.
- Venue page has a `tugoz-embed.js` helper or a `<div id="tugoz-embed" data-event-key="...">`.
- Site config includes `SITE_CONFIG.LIVE_EVENTS: { key: <event_id> }`.
- Browser network requests fetch `https://static.tugoz.com/api/json/www/v4/e-<event_id>`.

**API/source pattern:**
- The scraper fetches the configured `source_url` and parses integer event IDs from `LIVE_EVENTS`.
- Each event ID is fetched from `https://static.tugoz.com/api/json/www/v4/e-<event_id>`.
- `metadata.event_keys` can restrict the keys read from config JS. `metadata.event_ids` is a fallback when the config is unavailable or a venue exposes fixed IDs only.

**Key extraction notes:**
- Event details live under `einfo`: `name`, `date`, `tziso`, `eventurl`, `about`, and venue fields.
- Dates are naive local strings (`YYYY-MM-DD HH:MM:SS`) paired with `tziso`.
- The static JSON currently does not expose stable public price tiers; create a fallback ticket with unknown price pointing at `einfo.eventurl`.
- The scraper skips stale past events because some Tugoz sites keep old keys in `LIVE_EVENTS` after disabling the visible embed.

**DB setup:**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, enabled, priority, metadata)
VALUES (
    <id>,
    'custom',
    'tugoz',
    'https://<venue>/config.js?v=2',
    TRUE,
    0,
    jsonb_build_object('event_keys', jsonb_build_array('<key>'))
);
```

**Failure modes / gotchas:**
- A Tugoz event can have `status='Draft'` / `live=0` while the venue-owned page still renders the booking widget, so do not filter solely by those fields.
- Pages may include commented-out Tugoz embeds for upcoming shows; the config key can still point at a stale past event. Let the scraper's stale-date skip handle it or restrict `metadata.event_keys`.
- Tugoz's dynamic `www.tugoz.com/api?action=...` calls are widget-session oriented; the stable extraction source is the static event JSON.

**Reference implementation:**
- `apps/scraper/src/laughtrack/scrapers/implementations/api/tugoz/`
- Masala Comedy Club, TASK-3194.

---

### Tockify

| | |
|---|---|
| **Scraper key** | Venue-specific (e.g. `ice_house`) |
| **DB field** | `scraping_url` (optional override) |
| **Generic?** | ❌ Requires parameterization — the `calname` is hardcoded per venue |

**Detection signals (via Playwright network inspection):**
```
GET https://tockify.com/api/tagoptions/<calname>
```
The `<calname>` is the venue's Tockify calendar identifier (e.g., `theicehouse`).

**API endpoint:**
```
GET https://tockify.com/api/ngevent?calname=<calname>&max=200&startms=<now_ms>
```

**Key implementation details:**
- Timestamps are in **milliseconds** (not seconds)
- Ticket URLs: normalize `embed.showclix.com/event/{slug}` → `www.showclix.com/event/{slug}`
- Paginate via `metaData.hasNext` + `startms`: the scraper loops in `get_data()` while `metaData.hasNext` is true, re-fetching with `startms` set to `max(event.start_ms) + 1` from the previous page. A 20-page safety cap (4000 events) prevents a server that always returns `hasNext=true` from spinning forever; if the cap fires, `Logger.warn` flags possible truncation.
- `when.start.tzid` gives the timezone string
- **Pricing** (TASK-2837 pattern, TASK-2838): the ngevent payload has no price
  keys. The scraper fetches each distinct `customButtonLink` ticket page once
  per run (memoized; embed URLs normalized to www first) and parses the lowest
  positive per-tier price from the page's schema.org JSON-LD `Event.offers`
  via the shared `EventExtractor` pipeline. All-zero offers parse as
  proven-free 0.0; the ~10% seated-sales page variant has no JSON-LD and keeps
  price `None` (TASK-2841 may cover that residue via the ShowClix seated API).

**To onboard a new Tockify venue:**
1. Use Playwright to find the `calname` in network requests
2. Create a new scraper directory (copy `ice_house/`) and replace `theicehouse` with the new calname
3. Verify the `customButtonLink` ticket URL format. Events without
   `customButtonLink` (walk-in / recurring socials like Ice House's
   "Social Hour") fall back to the public Tockify detail URL
   `https://tockify.com/<calname>/detail/<uid>/<tid>`, derived by the
   extractor from the API URL. No per-venue work required.
4. Set `scraping_url` in the DB (optional — only needed if overriding the hardcoded URL)

---

### Timely

| | |
|---|---|
| **Scraper key** | `timely` |
| **Platform** | `custom` |
| **DB field** | `scraping_sources.source_url` + `metadata.timely_calendar_id` |
| **Value format** | `source_url='https://events.timely.fun/<slug>/agenda'`; metadata numeric `timely_calendar_id` |
| **Generic?** | ✅ Generic — a second Timely calendar needs only a DB row once the numeric calendar id is captured |

**Detection signals:**
- Venue page embeds or links to `events.timely.fun/<slug>/agenda`
- Page source includes `<timely-calendar ... data-info="...">`
- Browser network requests hit:
  ```
  GET https://events.timely.fun/api/calendars/<calendar_id>/events?group_by_date=1&timezone=<iana>&view=agenda&start_date_utc=<local-midnight-epoch>&per_page=30&page=1
  ```

**API/source pattern:**
- Timely's public browser API endpoint is:
  ```
  GET https://events.timely.fun/api/calendars/<calendar_id>/events
  ```
- Required query params used by the scraper: `group_by_date=1`, `timezone`, `view=agenda`, `start_date_utc`, `per_page`, and `page`.
- The request requires Timely's public browser `x-api-key` header. The scraper stores the currently shipped key as a default and allows `metadata.timely_api_key` to override it if Timely rotates the key.
- The slug (`fwq8raf8` for Jacques' Cabaret) is not accepted as the API calendar id. Capture the numeric id from browser requests or from the page's decoded `data-info.id`.

**Key extraction notes:**
- `data.items` is grouped by date when `group_by_date=1`; flatten every list under that object.
- Dates are local strings (`start_datetime`) plus an IANA `timezone`; parse with `ShowFactoryUtils.parse_datetime_with_timezone_fallback`.
- Public event URL shape is `<source_url>/event/<custom_url>/<instance>`.
- Positive `tickets_min_price` values are parsed as ticket prices. `ticket_type='no_ticket'`, `cost_display='0'`, or a missing price does **not** prove the event is free, so leave price unknown.
- `cost_external_url`, when present, is the ticket purchase URL; otherwise the Timely event URL is the fallback ticket URL.
- Pagination uses `data.has_next`; the scraper has a safety cap.

**DB setup:**
```sql
INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, priority, enabled, metadata
)
VALUES (
    <club_id>,
    'custom'::"ScrapingPlatform",
    'timely',
    'https://events.timely.fun/<slug>/agenda',
    0,
    TRUE,
    '{"timely_calendar_id": <numeric_id>, "calendar_slug": "<slug>"}'::jsonb
);
```

**Failure modes / gotchas:**
- The API returns `Calendar Not Found` if the `x-api-key` header is omitted.
- The visible slug and SSR route event ids are not valid substitutes for the numeric calendar id in `/api/calendars/<id>/events`.
- Some Timely calendars include mixed programming; use a separate task before adding a comedy-only filter, because the generic scraper currently keeps every event in the calendar.

**Reference implementation:**
- `apps/scraper/src/laughtrack/scrapers/implementations/api/timely/`
- `apps/scraper/src/laughtrack/core/entities/event/timely.py`
- Jacques' Cabaret (TASK-3155): slug `fwq8raf8`, calendar id `54755528`

---

### Squarespace

| | |
|---|---|
| **Scraper key** | `squarespace` |
| **DB field** | `scraping_url` (full GetItemsByMonth URL including `collectionId` query param) |
| **Generic?** | ✅ Generic — a second venue needs only a DB row |

**Detection signals:**
- `WebFetch` returns an HTML shell with no event data (JS-rendered)
- Playwright `browser_network_requests` shows:
  ```
  GET /api/open/GetItemsByMonth?month=MM-YYYY&collectionId=<id>
  ```

**Key implementation details:**
- Response is a **root-level JSON array** (not a dict) — handle accordingly
- `collectionId` is NOT in page source; find it via Playwright network inspection
- The `crumb` param seen in browser requests is NOT required for `/api/open/` — omit it
- Timestamps are in **milliseconds**
- API returns one month at a time — iterate current month + N months ahead
- No external ticket URL — use `fullUrl` (prepend base domain) as the show page / ticket fallback

**Two-collection trap:** Some Squarespace sites have a calendar-block collection (type 10, e.g. `/shows`) separate from the actual event-items collection (e.g. `/all-shows`). If `GetItemsByMonth` returns `[]` for the ID found on the listing page, fetch an individual event's page (`/all-shows/<slug>`) and read its `Static.SQUARESPACE_CONTEXT` — the `collection.id` there is the correct ID to use in the scraping URL.

**Products-collection mode (TASK-3012):** Some venues sell each show as a dated store product (collection `typeName='products'`, type 13, e.g. `/tickets/p/june-19-2026`) instead of an Events collection, so `GetItemsByMonth` returns `[]`. Onboard with `scraping_url` = the collection PAGE url (e.g. `https://<domain>/tickets`, no `collectionId` param) and `metadata.collection_type='products'`; the scraper then reads the page via `?format=json`, follows `pagination.nextPageUrl`, and parses each product's show date from its `fullUrl` slug (`/tickets/p/june-19-2026`) plus the time from the title (`@8pm`, default 19:00 if absent). Example: Westside Improv Studio (Wheaton, IL).

**To onboard a new Squarespace venue:**
1. Navigate in Playwright → capture `browser_network_requests` → find `GetItemsByMonth` call
2. Extract `collectionId` from the network request URL
3. Insert a DB row with `scraper='squarespace'` and `scraping_url='https://<domain>/api/open/GetItemsByMonth?collectionId=<id>'`
4. No Python changes needed

---

### Wix Events

| | |
|---|---|
| **Scraper key** | Venue-specific (e.g. `bushwick`) |
| **DB field** | `scraping_url` |
| **Generic?** | ❌ Requires parameterization — `compId` is hardcoded per venue |

**Detection signals:**
- `wixstatic.com` assets loaded
- Event widget has `data-compId` attributes
- Footer: "Powered by Wix"

**Finding the `compId`** (Playwright required):
```javascript
// Run this in browser_evaluate after navigating to the venue homepage
(() => {
  const btn = document.querySelector('[data-hook^="more-info-link-"]');
  let el = btn;
  const ids = [];
  while (el && el !== document.body) {
    const id = el.id || el.getAttribute('data-comp-id') || '';
    if (id.startsWith('comp-')) ids.push({ id, cls: el.className.substring(0, 60) });
    el = el.parentElement;
  }
  return ids;
})()
```
The innermost `comp-xxxx` result is the `compId`.

**Key implementation details:**
- `categoryId` is NOT required unless the venue uses Wix event categories
- API: `POST /_api/wix-one-events-server/web/paginated-events/viewer?compId=<compId>` — paginated event list
- Requires an OAuth access token fetched first from `/_api/v1/access-tokens`

**Schedule-page variant (no compId):**
Some Wix venues use the Wix Events "Schedule" full-page app instead of embedding a
widget on a regular page. These venues have a `/schedule` page but no `compId`.
Detection: navigate to the schedule page and look for `data-hook="EVENTS_ROOT_NODE"`
with a `TPAMultiSection_*` parent (not a `comp-*` widget).

For these venues:
- Set `scraper = 'wix_events'` and `scraping_url` to the site root
- Leave `wix_comp_id` NULL — the `paginated-events/viewer` API returns all events
  without a `compId` param when authenticated
- The scraper automatically omits `compId` from the request when it's not set

**Not-scrapable variant (Wix Stores, not Wix Events):**
A Wix site can have the Events app installed yet sell shows as **undated,
recurring Wix Stores products** (a "select ticket option" dropdown, e.g.
"Date Night Fridays" $30/$45/$80) rather than dated events. The
`paginated-events/viewer` API then returns **0 upcoming events** (often only
stale demo/template events with `status=2`). There are no per-show dates to
build `Show` rows → **not scrapable**; close `wont_do`. Always confirm the
API returns `> 0` upcoming events before onboarding a Wix venue. (TASK-2957)

---

### Crowdwork

| | |
|---|---|
| **Scraper key** | `crowdwork` (generic) |
| **DB field** | `source_url` = `https://crowdwork.com/api/v2/<theatre>/shows` |
| **Platform enum** | `crowdwork` |
| **Generic?** | ✅ — the theatre slug lives in `source_url`; no per-venue code |

**Detection signals (via Playwright network inspection, or curl the venue's events page):**
```
GET https://crowdwork.com/api/v2/<theatre>/shows
```
The `<theatre>` slug comes from the embedded CrowdWork links on the venue's site
(e.g. `crowdwork.com/v/<theatre>/shows`, `<theatre>.crowdwork.com/shows`) or the
`data-theatre` attribute on the embedded `crowdwork.com/embed.js` script tag.

**To onboard a new Crowdwork venue:** insert a `scraping_sources` row with
`platform='crowdwork'`, `scraper_key='crowdwork'`, and `source_url` set to the
`/api/v2/<theatre>/shows` endpoint. No new scraper directory is needed — the generic
`crowdwork` scraper reads the URL from `source_url` and its config from `metadata`:
- `default_timezone` (IANA) — fallback when a show has no `timezone` field.
- `rails_to_iana: true` — set this when the API returns **Rails-style** timezone
  names (`"Pacific Time (US & Canada)"`, etc.) so they normalise to IANA. Venues
  whose API already returns IANA names (e.g. Philly Improv → `America/New_York`)
  omit it. Example (Haus of Comedy, TASK-3200, slug `windhausimprov`):
  `metadata = {"rails_to_iana": true, "default_timezone": "America/Los_Angeles"}`.

---

### VBO Tickets

| | |
|---|---|
| **Scraper key** | `vbo_tickets` (generic, multi-event listing) — or venue-specific (`esthers_follies`, `csz_philadelphia`) for single-recurring-show / seat-tier venues |
| **DB field** | `source_url` = the loadplugin URL `https://plugin.vbotickets.com/plugin/loadplugin?siteid=<SITE_ID>&page=ListEvents` |
| **Platform enum** | `custom` |
| **Generic?** | ✅ for multi-event venues — use `vbo_tickets`; it reads the SiteID from `source_url`, no per-venue code |

**Which scraper:** Use the generic **`vbo_tickets`** scraper for venues whose VBO plugin renders a multi-event listing (the `/Plugin/events/showevents` grid — many distinct shows). It parses both VBO's structured per-occurrence rows (`Tue, 6/16/2026 @ 7:00 PM`) and free-form / recurring date text entered by hand (`Fri 9:30pm 6/5, 6/12, ...`), and accepts an optional `category_filter` in `scraping_sources.metadata` to keep only matching `data-event-category` values.

**Consolidation decision (TASK-2938):** The Nest Theatre — formerly the venue-specific `nest_theatre` scraper — was migrated onto `vbo_tickets`: it read the same `showevents` listing and differed only in its `Live Shows` category filter and free-form recurring dates, both now handled generically (set `metadata.category_filter='Live Shows'`). The remaining venue-specific VBO scrapers **stay separate on purpose**:
- **`esthers_follies`** — a single recurring show scraped via the per-event date slider (`load_eventdate_slider`), with per-show seat-tier price enrichment (extra seat-map SVG + getseats JSON fetches). The multi-event listing flow does not model seat tiers.
- **`csz_philadelphia`** — a two-stage flow (showevents → per-event date slider) with dynamic session self-healing and `data-event-subcategory='Comedy'` filtering; it expands each event's slider dates rather than reading the listing's dates.

Folding either into `vbo_tickets` would require the generic scraper to grow the date-slider mode + seat-tier enrichment — high complexity for two venues with divergent logic — so they remain venue-specific.

**`vbo_tickets` setup:** insert a `scraping_sources` row with `platform='custom'`, `scraper_key='vbo_tickets'`, and `source_url` = the loadplugin URL with the venue's SiteID. Optionally add `metadata = {"category_filter": "Live Shows"}` (string or list) to drop non-matching `data-event-category` entries (e.g. classes). The scraper acquires a session from that URL, then GETs `https://plugin.vbotickets.com/Plugin/events/showevents?ViewType=list&EventType=current&day=&s=<session>` and parses each `<div id="EDID…">` block (`data-event-name`, `data-event-category`, `.TextEventDate`, `.EventListPrice`, `event.asp?eid=`). **Find the SiteID** in the venue's `/tickets` page inline JS: `var SiteID = "<GUID>";` (also exposed on any VBO event page as `SiteID = "<GUID>"`).

**Mixed-use venues (title filter, OFF by default):** a performing-arts center that runs comedy alongside concerts / films / theatre / magic often can't be isolated by `category_filter` — its comedy shares a generic VBO category (e.g. "Performing Arts") with non-comedy events. Use the title-pattern filter instead: `metadata = {"include_title_patterns": ["Comedy Under the Stars"]}` keeps only event names matching the regex(es); `exclude_title_patterns` drops matches. Both are case-insensitive (string or list), compose (include then exclude), and are OFF by default so single-purpose VBO venues are unaffected. Example: Fair Oaks Performing Arts Center (club 11112) keeps only its "Comedy Under the Stars" series.

**Detection signals:**
- Network requests to `plugin.vbotickets.com` / `connect.vbotickets.com`
- Ticketing iframe loads `plugin.vbotickets.com/plugin/loadplugin?siteid=<UUID>`

**Session flow:** VBO uses a session-based iframe — there is no unauthenticated public JSON API.
The scraper must:
1. `GET plugin.vbotickets.com/plugin/loadplugin?siteid=<SITE_ID>&page=ListEvents`
   → Returns a small HTML page with the session UUID embedded in inline JS
2. Extract the UUID — VBO uses **unquoted JS object keys**, not JSON:
   ```python
   _SESSION_RE = re.compile(
       r'value["\s:]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
       re.IGNORECASE,
   )
   ```
   A quoted-key regex (`"value"\s*:\s*"uuid"`) will silently return no match.
3. `GET plugin.vbotickets.com/v5.0/controls/events.asp?a=load_eventdate_slider&eid=<EID>&s=<SESSION>`
   → Returns server-rendered HTML with upcoming show dates (~6 week window)

**Finding `SITE_ID` and `EID`:** `SITE_ID` is in the loadplugin URL. `EID` is in the seatmap inline JS (`LoadEvent('<EID>', ...)` onclick handlers).

**Ticket URLs:** Per-show VBO URLs are session-dependent and non-shareable. Use the venue's stable tickets page as the ticket URL fallback.

**Troubleshooting HTTP 401 errors:** When a VBO scraper returns 401, the session key stored in `scraping_url` has rotated. The static page JS (e.g. Squarespace `var s = "..."`) shows the **old** key. The real working key only appears in live Playwright network requests — skip static inspection and go straight to:
```bash
# Use Playwright MCP: navigate to the venue's /calendar page, then call browser_network_requests
# Look for: GET plugin.vbotickets.com/Plugin/events/showevents?...&s=<NEW_KEY>
# Update clubs SET scraping_url = '...?s=<NEW_KEY>' WHERE name = '<Venue>';
```

**Esther's Follies (Austin, TX) — venue-specific constants:**
- `SITE_ID`: `5D695E7C-1246-4F54-BF57-B1D92D1E6B83`
- `EID`: `39242`
- Stable ticket URL: `https://www.esthersfollies.com/tickets`
- Shows run **Thu–Sat nights** at 7 PM and 9 PM (~6 week window returned by date slider)

**DB setup:**
```sql
INSERT INTO clubs (..., scraper, scraping_url, ...) VALUES (..., 'esthers_follies', 'https://www.esthersfollies.com/tickets', ...);
```

---

### Tribe Events Calendar (WordPress)

| | |
|---|---|
| **Scraper key** | `the_events_calendar` |
| **Platform enum** | `tribe_events` |
| **DB field** | `scraping_sources.source_url` |
| **Generic?** | ✅ Generic — works for any Tribe Events Calendar venue |

> Note: The Rockwell (club 150) originally shipped as a venue-specific `the_rockwell`
> scraper; TASK-2921 migrated it onto this generic scraper and deleted the duplicate.
> Use `the_events_calendar` for all Tribe / The Events Calendar venues.

**Detection signals:**
- Network requests to `/wp-json/tribe/events/v1/events`
- WordPress site with The Events Calendar plugin

**DB setup:** Insert a `scraping_sources` row pointing `source_url` at the base REST API URL (config lives in `scraping_sources`, not flat `clubs` columns):
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'tribe_events'::"ScrapingPlatform", 'the_events_calendar', 'https://myvenue.com/wp-json/tribe/events/v1/events', 0, TRUE, '{}'::jsonb
FROM clubs c WHERE c.name = 'My Club'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'the_events_calendar');
```

---

### WordPress Category Posts

| | |
|---|---|
| **Scraper key** | venue-specific (reference: `kenosha_comedy_club`) |
| **Platform** | `custom` |
| **DB field** | `scraping_sources.source_url` |
| **Value format** | WordPress posts endpoint, e.g. `https://site.example/wp-json/wp/v2/posts?categories=<id>&per_page=20&_fields=id,date,modified,link,title,excerpt,categories` |
| **Generic?** | ❌ venue-specific code required unless the title/date format matches an existing scraper exactly |

**Detection signals:**
- WordPress category archive represents a venue or event series.
- `/wp-json/wp/v2/categories?search=<name>` returns a category whose `name` or `description` names the venue.
- `/wp-json/wp/v2/posts?categories=<id>` returns plain posts, not event custom post types.
- Standard event-plugin APIs (for example `/wp-json/tribe/events/v1/events`) are missing or empty for these shows.

**API/source pattern:**
- Fetch the category posts endpoint directly.
- Use `_fields=` to keep payloads small; include at least `id`, `link`, `title`, and `excerpt`.

**Key extraction notes:**
- These posts are hand-maintained content, so date/time may live only in the title.
- Do not invent a showtime when the post title has dates but no time; skip that post or add a venue-specific fallback only when the site exposes a reliable time elsewhere.
- Use the post URL as the show/ticket URL when no deeper ticketing link is exposed.

**DB setup:**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom'::"ScrapingPlatform", '<venue_scraper_key>',
       'https://site.example/wp-json/wp/v2/posts?categories=<id>&per_page=20&_fields=id,date,modified,link,title,excerpt,categories',
       0, TRUE, '{}'::jsonb
  FROM clubs c
 WHERE c.name = '<Venue Name>';
```

**Failure modes / gotchas:**
- WordPress publish dates are not show dates; parse event dates from the post content/title instead.
- Category slugs can be generic or misleading. Kenosha Comedy Club uses category slug `comedy`, but category id `506` and name `Kenosha Comedy Club`.
- Posts can be stale or reused across years; parse against the current year and roll past month/day values forward only when the parsed date is before today.

**Reference implementation:**
- `apps/scraper/src/laughtrack/scrapers/implementations/venues/kenosha_comedy_club/`
- TASK-2978, Kenosha Comedy Club

---

### Modern Events Calendar (WordPress)

| | |
|---|---|
| **Scraper key** | `modern_events_calendar` |
| **Platform** | `custom` |
| **DB field** | `scraping_sources.source_url` |
| **Value format** | WordPress MEC endpoint, e.g. `https://site.example/wp-json/wp/v2/mec-events?mec_category=<id>` |
| **Generic?** | ✅ Generic when MEC detail pages render schema.org Event JSON-LD |

**Detection signals:**
- `/wp-json/wp/v2/types` lists `mec-events` with `rest_base: "mec-events"`.
- `/wp-json/wp/v2/mec_category` lists a comedy/category id that can filter the venue's mixed calendar.
- Event detail pages render `<script type="application/ld+json">` with schema.org `Event` data including `startDate`, `offers`, and `location`.

**Source pattern:** Use the REST collection as the index and the event detail pages as the canonical date/price source. Some sites, including Moonlight Theatre, return empty HTML to plain curl but render correctly in Playwright; set `metadata.force_js_rendering=true` for those sources.

**DB setup:**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom'::"ScrapingPlatform", 'modern_events_calendar',
       'https://site.example/wp-json/wp/v2/mec-events?mec_category=<id>',
       0, TRUE,
       jsonb_build_object(
         'listing_url', 'https://site.example/event-category/comedy/',
         'force_js_rendering', TRUE,
         'per_page', 20,
         'max_pages', 3,
         'max_detail_pages', 60
       )
  FROM clubs c
 WHERE c.name = '<Venue Name>';
```

---

### rhp-events (WordPress Plugin)

| | |
|---|---|
| **Scraper key** | `comedy_magic_club` |
| **DB field** | `scraping_url` |
| **Generic?** | ✅ Already generic — works for any rhp-events venue |

**Detection signals (page source):**
```
rhpSingleEvent    eventWrapper    rhp-event__title--list
```

**Important:** Do NOT implement pagination — all `/events/page/N/` URLs return identical content. Fetch only the base `/events/` URL. Deduplication via upsert handles any double-fetches.

**Single-show page quirk:** The `class = "eventStDate"` attribute on single-show detail pages uses spaces around `=` (i.e. `class = "..."`, not `class="..."`). Regex patterns targeting class attributes on these pages must use `class\s*=\s*"` rather than `class="` to match correctly.

**Pricing** (TASK-2842): each card's `rhp-event__cost-text--list` (or `--grid`)
span carries the cost text (e.g. `$27`, `$27 - $37`). The extractor parses the
lowest positive dollar amount into the fallback ticket — ranges take the low
end; `$0` or dollar-less text stays `None` (price unknown). Same markup family
the Funny Bone Rockhouse parser reads (`_funny_bone_ticket_price` in
`api/etix/scraper.py`).

**DB setup:**
```sql
UPDATE clubs SET scraper = 'comedy_magic_club', scraping_url = 'https://myvenue.com/events/' WHERE name = 'My Club';
```

---

### EventPrime (WordPress Plugin)

| | |
|---|---|
| **Scraper key** | `eventprime` |
| **Platform** | `custom` |
| **DB field** | `scraping_sources.source_url` (the full `get_events` endpoint) |
| **Value format** | `https://<site>/wp-json/eventprime/v1/get_events` |
| **Generic?** | ✅ DB-only onboarding for any WordPress site running the EventPrime plugin |

**Detection signals:**
- WordPress site whose shows are managed by the EventPrime events plugin (event
  pages under `/event/<slug>/`; site source references `eventprime` / `em_` assets).
- Public, unauthenticated REST endpoint `…/wp-json/eventprime/v1/get_events`
  returns `{"status":"success","count":N,"events":[…]}` (HTTP 200, no auth).
- **Do NOT** wire `woocommerce_store_api` for these venues even if the site runs
  WooCommerce — the Store API typically returns only multi-show passes / virtual
  EventPrime placeholders (Season/Month/Week/10-Show Pass), not dated shows.

**API/source pattern:**
- `EventPrimeScraper` fetches the `get_events` endpoint via `fetch_json`
  (curl_cffi impersonation; Playwright fallback as backstop).
- Each event carries `id`, `title`, `slug`, `content` (HTML), `status`
  (`"publish"` when live), `permalink`, `image_url`, `start_date` / `end_date`
  (ISO-8601, usually with a UTC offset), `timezone`, `venue`, and
  `tickets` (`[{name, price, capacity}]`).

**Key extraction notes:**
- `title` → name, `permalink` → show page, `image_url` → image, `content` → HTML
  stripped to plain-text description, each `tickets[]` entry → a USD Offer
  (`price` 0 → free).
- `start_date` is parsed with `datetime.fromisoformat` (preserves the embedded
  offset); a naive timestamp is localized to the club timezone.
- The endpoint returns the venue's **entire** event history (past + future), so
  the extractor **drops past occurrences** — only upcoming shows are emitted.
- Optional `metadata.comedy_filter=true` for mixed-use venues (drops non-comedy
  titles via `is_comedy_event`).

**DB setup:**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom'::"ScrapingPlatform", 'eventprime',
       'https://<site>/wp-json/eventprime/v1/get_events',
       0, TRUE, '{}'::jsonb
  FROM clubs c
 WHERE c.name = '<Venue Name>';
```

**Reference implementation:**
- `apps/scraper/src/laughtrack/scrapers/implementations/eventprime/`
- `apps/scraper/tests/scrapers/implementations/eventprime/test_scraper.py`
- TASK-3169: Flip Flops Comedy Club (Old Orchard Beach, ME)

---

### JSON-LD (Generic Fallback)

| | |
|---|---|
| **Scraper key** | `json_ld` |
| **DB field** | `scraping_url` |
| **Generic?** | ✅ Already generic — works for any page with JSON-LD Event markup |

**Detection signals (page source):**
```html
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Event", ...}
</script>
```

**DB setup:**
```sql
UPDATE clubs SET scraper = 'json_ld', scraping_url = 'https://myvenue.com/events/' WHERE name = 'My Club';
```

**Optional `scraping_sources.metadata` flags:**
- `location_name_filter` (string) — keep only events whose JSON-LD `location.name`
  contains the substring; for multi-venue calendar pages.
- `detail_fetch` (object) — two-pass scrape when the listing page has only event
  *links* (not full Event blocks). Fetch the index, harvest detail URLs, then
  extract each detail page's Event JSON-LD. Anchor mode:
  `{"enabled": true, "url_path_prefix": "/shows/"}` collects every `<a href>` under
  that path prefix; `pagination` / typed-field (`object_type`/`url_path`) modes
  also exist.
- `comedy_filter` (bool) — for **mixed-use venues** (a music bar / arts space whose
  calendar is mostly non-comedy). When `true`, drops events whose title +
  description carry no comedy keyword (`is_comedy_event`), mirroring the
  `wix_events` flag. schema.org Event JSON-LD has no genre field, so the keyword
  match is the only signal. Leave unset for all-comedy venues so a show titled with
  only a comedian's name is never dropped.

**Mixed-use example — Cole's Bar (TASK-2964):** an Opendate music bar whose
`/shows/<slug>` detail pages embed `MusicEvent` JSON-LD. The homepage lists ~85%
live music plus a weekly "Comedy Open Mic". Onboarded with `scraper_key='json_ld'`,
`source_url='https://colesbarchicago.com/'`, and
`metadata={"detail_fetch": {"enabled": true, "url_path_prefix": "/shows/"}, "comedy_filter": true}`
→ scrapes only the comedy open mics.

---

### Odoo website_event

| | |
|---|---|
| **Scraper key** | `odoo_events` |
| **Platform** | `custom` |
| **DB field** | `scraping_sources.source_url` |
| **Value format** | Odoo event listing URL, usually `https://<host>/event` |
| **Generic?** | ✅ Generic for Odoo website_event pages whose detail pages expose schema.org Event microdata |

**Detection signals:**
- Listing page at `/event` with links shaped `/event/<slug>-<id>/register`
- Page source contains `itemscope itemtype="http://schema.org/Event"` and `itemprop` attributes (`startDate`, `name`, `offers`, `location`)
- Odoo asset/page markers such as `website_event` may appear, but the scraper keys off the public Event microdata and links

**API/source pattern:**
- Fetch `scraping_sources.source_url`
- Crawl same-host register links under `/event/`
- Follow Odoo pagination links such as `/event/page/2?date=upcoming`
- Fetch each detail page and parse schema.org Event microdata

**Key extraction notes:**
- Odoo stores event datetimes as UTC-like strings without a timezone suffix (for example `2026-06-27T01:00:00` for an evening Central Time show). The scraper treats naive datetimes as UTC and converts to the club timezone.
- Detail pages are the canonical source for price, location, and description. Listing cards are used only for discovery.
- The scraper drops past shows and defaults to excluding class/workshop/camp title matches. Configure `metadata.exclude_title_patterns` when a venue has additional non-comedy series (Comedy Plex uses `\bjazz\b`).

**DB setup:**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
VALUES (<club_id>, 'custom'::"ScrapingPlatform", 'odoo_events', 'https://www.example.com/event', 0, TRUE, '{}'::jsonb);
```

**Failure modes / gotchas:**
- If the venue customizes detail pages and removes Event microdata, this scraper will return no shows.
- Pagination is capped by metadata/defaults; increase `metadata.detail_fetch.pagination.max_pages` only when a venue has more than ten upcoming listing pages.
- Some Odoo venues use category tags for mixed calendars; this generic scraper does not currently filter Odoo categories.

**Reference implementation:**
- `src/laughtrack/scrapers/implementations/api/odoo_events/scraper.py`
- Onboarded example: Comedy Plex Comedy Club (TASK-3021)

---

### TicketsCandy

| | |
|---|---|
| **Scraper key** | `ticketscandy` |
| **DB field** | `scraping_url` (the venue's shows-listing page) |
| **Generic?** | ✅ Generic platform scraper |

TicketsCandy (`ticketscandy.com`) is a ticketing platform; venues link out to
per-show TicketsCandy event pages from their own sites. There is **no
TicketsCandy organizer/venue aggregation endpoint**, so the scraper discovers
event URLs by crawling the venue's own site and collecting every
`ticketscandy.com/e/<slug>` link. Each TicketsCandy page carries standard
schema.org Event JSON-LD, parsed via the shared `json_ld` extractor.

**Detection signals:** the venue's show pages link to `ticketscandy.com/e/...`;
those pages contain `<script type="application/ld+json">` with `"@type":"Event"`.

**`scraping_sources.metadata`:**
- `detail_link_prefix` (string, optional) — for **two-hop** venues (e.g. a
  WordPress `/shows/` index linking to `/shows/<slug>/` sub-pages that each carry
  the TicketsCandy links): same-host sub-pages under this prefix are crawled for
  TicketsCandy links. Omit for **one-hop** venues that link to TicketsCandy
  directly from the listing.

**Two TicketsCandy data quirks the scraper corrects automatically:**
1. `startDate` is mislabeled `+00:00` even though the time is venue-local
   wall-clock — the scraper strips the offset and re-localizes to the club tz.
2. The `startDate` **time** is sometimes wrong (e.g. `07:00` for a 7:30 PM show)
   while the title reliably reads `(... - 7:30PM)` — the title's clock time wins
   (the date is taken from `startDate`).

**Example — Funny Pharm Comedy Club (TASK-3024):** WordPress two-hop site →
`scraper_key='ticketscandy'`, `source_url='https://www.funnypharmcomedy.com/shows/'`,
`metadata={"detail_link_prefix": "/shows/"}` → 29 shows, all 7:30 PM ET, DST-correct.

---

### SquadUP

| | |
|---|---|
| **Scraper key** | venue-specific (e.g. `sunset_strip`) |
| **DB field** | `scraping_url` (display URL only; API URL is hard-coded in scraper) |
| **Generic?** | ❌ Venue-specific — `user_id` differs per venue |

**Detection signals:**
- Page JS contains `squadup = { userId: [<id>], ... }` (inline script on the events page)
- SquadUP embed CSS/JS loaded from `embed.squadup.com`
- Ticket links go to `squadup.com/events/<slug>`

**API endpoint:**
```
GET https://www.squadup.com/api/v3/events
    ?user_ids=<id>&page_size=100&include=custom_fields&page=<N>
```

**Key non-obvious details:**
1. The `userId` array in the page JS (e.g. `userId: [9086799]`) is the value to pass as `user_ids`.
2. The API is Cloudflare-protected. Use a **bare `AsyncSession.get(url)`** with `impersonate="chrome124"` and **no extra headers** — adding application headers triggers a 403.
3. Pagination: `meta.paging.total_pages` in the first response tells you how many pages to fetch.
4. `start_at` is ISO 8601 with UTC offset (e.g. `"2026-03-26T20:00:00-05:00"`). Parse directly with `datetime.fromisoformat()`.
5. Ticket URL: use the `url` field (e.g. `"https://squadup.com/events/comedy-gold-51"`).
6. Shows at SquadUP venues are often recurring showcases with rotating lineups — comedian names are typically not pre-announced in the API data. Use the show title heuristic (generic title regex → `[]` performers) rather than expecting a dedicated performers field.

**To onboard a new SquadUP venue:**
1. Fetch the venue events page and search the HTML for `userId:` to extract the numeric ID.
2. Create a new scraper dir under `scrapers/implementations/venues/<venue>/`.
3. Hard-code `_SQUADUP_USER_ID` in the scraper; set `scraper='<key>'` in the DB.
4. Use bare `AsyncSession(impersonate="chrome124")` with no extra headers in `_fetch_events_page()`.

---

### Tixologi (Laugh Factory CMS)

| | |
|---|---|
| **Scraper key** | `laugh_factory_reno` |
| **DB field** | `scraping_url` |
| **Generic?** | ❌ Venue-specific — the CMS page URL is hardcoded |

**Detection signals:**
- Ticket links follow the pattern `laughfactory.club/checkout/show/{punchup_id}`
- Shows are server-rendered as `.show-sec.jokes` divs on a Laugh Factory CMS page
- Note: `api-v2.tixologi.com/public/users/{partner_id}/events` returns 401 — HTML scraping required

The `TixologiClient` fetches the CMS HTML page; `LaughFactoryRenoEventExtractor` parses the `.show-sec.jokes` divs (date span, timing span, ticket anchor, title h4, figcaption comedian names).

**API limitations:**
- `GET https://api-v2.tixologi.com/public/users/partners/{partner_id}/events` → 401 Unauthorized
- `GET https://api-v2.tixologi.com/public/users/partners/{partner_id}` → partner metadata only (works without auth)
- HTML scraping of the Laugh Factory CMS page is required; there is no public events API

**Date format quirk:** The `.shedule span.date` contains a non-breaking space (`\xa0`) between the weekday abbreviation and the date string, e.g. `"Wed\xa0Apr 10"`. Strip the weekday prefix on `\xa0`, then infer year (current if future, else next).

**Reference implementation:** `apps/scraper/src/laughtrack/core/clients/tixologi/`

---

### Gotham Comedy Club (Webflow CMS worker feed)

| | |
|---|---|
| **Scraper key** | `gotham` |
| **Generic?** | ❌ Venue-specific — the worker feed URL is hardcoded in the scraper |

Gotham's site is a Webflow rebuild whose `/calendar` page fetches
`https://square-mountain-7159.alex-cdc.workers.dev/items?limit=N&offset=M` —
a Cloudflare Worker proxying the venue's Webflow CMS event collection
(`{"items": [...], "pagination": {"total": N}}`; the worker hard-caps
`limit` at 100). Each item is one showtime; `fieldData["event-id"]` is the
**Showclix** event id, so ticket price/sold-out enrichment is a direct
`ShowclixAPIClient.get_event_data(event_id)` call — no HTML scraping.
Plain curl gets a Cloudflare 403; the shared curl_cffi-impersonated session
is required.

**History:** until June 2026 the venue published monthly JSONs at
`gothamevents.s3.amazonaws.com/events/month/<YYYY-MM>.json` (venue-owned
bucket, also served their site assets). The bucket was deleted outright
(`NoSuchBucket`) when they rebuilt on Webflow — TASK-2822. Their
`/calendar-old` page's SquadUp API (`squadup.com/api/v3/events?user_ids=9987142`)
returns 0 events; dead end, do not readopt.

---

### Punchup venue sites (The Creek and The Cave, West Side, Comedy Key West)

The Creek and The Cave (Austin) rebuilt on the **Punchup** platform in June
2026 (previously a venue-owned S3 monthly-JSON feed at
`creekandcaveevents.s3.amazonaws.com`, deleted outright — TASK-2822). Its
`https://www.creekandcave.com/calendar` page (canonical;
`thecreekandthecave.com` 301s there) is Next.js SSR: the full ~200-row
upcoming list is embedded as a `"shows": [...]` RSC component prop inside
`self.__next_f.push` chunks — NOT in the React Query dehydrated cache,
which only holds the 20-row carousel. The shared `core/clients/rsc`
primitives decode the chunks and `PunchupShow`/`PunchupExtractor` handle the
row shape (`title`, naive-local `datetime`, Tixologi `ticket_link`,
`is_sold_out`, `vip_ticket_link`, structured `show_comedians`). Tickets are
Tixologi (`event.tixologi.com/event/<id>/tickets`).

**Pricing:** the Punchup RSC rows carry no price field. All three venues
enrich each show's `tixologi_event_id` against the public no-auth
`api-v2.tixologi.com` ticket-types endpoint so `PunchupShow._build_tickets`
emits per-tier priced tickets from `initial_price` — west_side (original),
creek_and_cave (TASK-2840), comedy_key_west (TASK-2851). The latter two guard
each show individually (a Tixologi outage degrades that show to the priceless
fallback, not a dropped calendar) and cap in-flight requests at 10;
consolidation of the duplicated machinery is tracked as TASK-2848.

---

### Netlify Functions (East Austin Comedy)

| | |
|---|---|
| **Scraper key** | `east_austin_comedy` |
| **DB field** | `scraping_url` (venue homepage, unused at runtime) |
| **Generic?** | ❌ Venue-specific — API endpoints are hardcoded |

**Detection signals:**
- Network requests to `eastaustincomedy.com/.netlify/functions/availability`
- Ticket purchase is handled via an embedded Square modal on the homepage (no per-show URL)

**API endpoints:** One endpoint per weekday name — 7 total calls per scrape run:
```
GET https://eastaustincomedy.com/.netlify/functions/availability?showDay={day}&offset=0
```
where `{day}` is one of: `monday tuesday wednesday thursday friday saturday sunday`.

Each response is a JSON array of upcoming dates for that day-of-week with show times and seat
availability. The scraper queries all 7 endpoints and deduplicates on `(date, time)`.

**Key non-obvious details:**
1. **No comedian lineups** — the website never publishes performer names. All shows are titled
   "Live Stand-Up Comedy"; the lineup is always an empty list.
2. **No per-show ticket URL** — tickets are sold via an embedded Square modal on the homepage.
   The ticket URL is always the homepage anchor: `https://eastaustincomedy.com/#shows`.
   *Re-verified 2026-05-26 (TASK-2466):* clicking a showtime opens the Square **Web Payments SDK**
   checkout modal in-page (card iframe hydrated via `pci-connect.squareup.com/payments/hydrate`,
   `locationId=L3KHDZCAXZKGT`) — the URL never leaves `#shows`, the availability function returns
   only `(date, time, seat-tier counts)`, and the booking flow carries no per-show product/event ID
   (FB `InitiateCheckout` reports `content_ids=[""]`). The `#shows` anchor remains the canonical and
   only purchase target; no remediation needed.
3. **Show volume:** weekday evenings typically have 1–2 shows; Fri/Sat/Sun have up to 3 shows
   (e.g. 6 PM / 8 PM / 10 PM).
4. The `scraping_url` DB field is unused at runtime — the scraper ignores it and always hits
   the Netlify function directly.

**DB setup:**
```sql
INSERT INTO clubs (..., scraper, scraping_url, ...) VALUES (..., 'east_austin_comedy', 'https://eastaustincomedy.com/#shows', ...);
```

---

### Vivenu

| | |
|---|---|
| **Scraper key** | `vivenu` |
| **DB field** | `scraping_url` (Vivenu seller page root URL) |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Venue sells tickets through a custom subdomain (e.g. `tickets.thirdcoastcomedy.club`)
- The seller page is a Next.js app — page source contains `<script id="__NEXT_DATA__" type="application/json">`
- `__NEXT_DATA__` has `props.pageProps.sellerPage.events[]`

**Key implementation details:**
- Event data path: `props.pageProps.sellerPage.events[]` in `__NEXT_DATA__` JSON
- Ticket URL pattern: `{base_url}/event/{event.url}` where `base_url` is derived from `scraping_url`
- Start times: ISO 8601 UTC strings (e.g. `"2026-04-15T00:00:00.000Z"`) — convert via the event's `timezone` field
- HTTP: uses `fetch_html_bare` (no application headers) to avoid Cloudflare bot-detection
- Only upcoming events are returned (start > now)

**DB setup:**
```sql
INSERT INTO clubs (..., scraper, scraping_url, ...)
VALUES (..., 'vivenu', 'https://tickets.thirdcoastcomedy.club/', ...);
```

**Example — Third Coast Comedy Club (Nashville, TN):**
```sql
UPDATE clubs SET scraper = 'vivenu', scraping_url = 'https://tickets.thirdcoastcomedy.club/'
WHERE name = 'Third Coast Comedy Club';
```

---

### Prekindle

| | |
|---|---|
| **Scraper key** | `json_ld` |
| **DB field** | `scraping_url` (full Prekindle events page URL) |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Venue's website links to `prekindle.com/events/{slug}`
- The Prekindle events page is server-rendered HTML with a `<script type="application/ld+json">` block
- JSON-LD `@type` is `ComedyEvent`

**Key implementation details:**
- Uses the existing `json_ld` scraper — no new code needed
- The `{venue-slug}` appears in the venue's Prekindle events page URL: `prekindle.com/events/{slug}`
- All upcoming events are embedded in a single JSON-LD block on the listing page
- **Rate-limiting:** rapid successive fetches (< ~60s) return HTML without the JSON-LD block,
  triggering "Page loaded but contained no JSON-LD events". Nightly single-run scrapes are unaffected.
- The Prekindle events page may include a `wicketpath` attribute on the JSON-LD `<script>` tag (Java Wicket framework). BeautifulSoup handles this correctly — no special handling needed.

**DB setup:**
```sql
INSERT INTO clubs (..., scraper, scraping_url, ...)
VALUES (..., 'json_ld', 'https://www.prekindle.com/events/{venue-slug}', ...);
```

**Example — Hyena's Comedy Nightclub:**
```sql
UPDATE clubs SET scraper = 'json_ld', scraping_url = 'https://www.prekindle.com/events/hyenas-comedy-nightclub'
WHERE name = 'Hyena''s Comedy Nightclub';
```

---

### SimpleTix

| | |
|---|---|
| **Scraper key** | `simpletix` |
| **Platform** | `simpletix` |
| **DB field** | `scraping_url` |
| **Value format** | Full SimpleTix event page URL, e.g. `https://www.simpletix.com/e/{event-slug}-tickets-{id}` |
| **Generic?** | Yes - single event-page scraper, configured by `scraping_url` |

**Detection signals:**
- Venue website links to `simpletix.com/e/...` ticket/event pages
- The SimpleTix event page embeds `var timeArray = [...]` JavaScript containing show time entries
- Page HTML may include JSON-LD offer data for ticket pricing

**Key implementation details:**
- Uses the generic `SimpleTixScraper` at `apps/scraper/src/laughtrack/scrapers/implementations/api/simpletix/`
- `collect_scraping_targets()` returns the club's `scraping_url` as the single target
- `SimpleTixExtractor` parses `var timeArray = [...]` entries with `Id` and `Time` fields, extracts the page `<h1>` as the event title, and reads the lowest JSON-LD offer price when present
- Each future `timeArray` entry becomes a show with the SimpleTix page as both show URL and ticket URL

**DB setup:**
```sql
UPDATE clubs
SET scraper = 'simpletix',
    scraping_url = 'https://www.simpletix.com/e/{event-slug}-tickets-{id}'
WHERE name = '<Club Name>';
```

**Reference implementation:** `apps/scraper/src/laughtrack/scrapers/implementations/api/simpletix/`

---

### TicketSpice (Webconnex)

| | |
|---|---|
| **Scraper key** | `ticketspice` (generic — `TicketSpiceScraper`) |
| **Platform** | `custom` |
| **DB field** | `scraping_sources.source_url` (+ optional `metadata.default_show_time`, `metadata.form_url`) |
| **Value format** | Full TicketSpice form URL, e.g. `https://{account}.ticketspice.com/{form-slug}` |
| **Generic?** | ✅ Single scraper, configured per-venue via `scraping_sources` |

**Detection signals:**
- Venue website links to `{account}.ticketspice.com/{slug}` ticket pages
- The form page footer/branding shows "Powered by TicketSpice"
- Page HTML contains a `window.__BOOTSTRAP__ = { ... }` JS object whose
  `appSettings` and `formData` members are escaped JSON strings

**Single-event model (IMPORTANT):** A TicketSpice form is a SINGLE-EVENT
ticketing page — one form == one show on one date. There is no multi-date
calendar; recurring shows post a NEW form per date (`schedules` and `items` in
`formData` are empty for single-date forms). The scraper therefore parses one
show per form URL. Once that date passes, `to_show` drops the show, so a stale
un-updated form stops emitting a past show (it just scrapes 0 until the venue
posts the next date's form).

**Where the data lives:** the form HTML embeds `window.__BOOTSTRAP__` near the
top of the page. Two members are themselves escaped JSON strings:
- `appSettings` → `formName` (show title), `eventStart` (ISO date at UTC
  midnight — **date only, no reliable wall-clock time**), `timeZone`, `status`
  (`1` == published; the scraper skips anything else)
- `formData` → `ticketBlock.levels[].price` (lowest level becomes the ticket
  price); `soldOut` flags the whole form sold out and is propagated to the
  ticket's `sold_out`

**Show time:** TicketSpice forms carry no show time, so each Show uses
`metadata.default_show_time` (`HH:MM`, default `19:00`) localized to the club
timezone — same pattern as the AXS homepage scraper.

**Key implementation details:**
- `collect_scraping_targets()` returns the form URL (`metadata.form_url` override,
  else the active source's `source_url` via `club.scraping_url`)
- `extractor.extract_event()` parses the bootstrap into one `TicketSpiceEvent`
- The page is plain server-rendered HTML — a single `fetch_html` suffices (no
  auth, no separate API call)

**DB setup:**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, enabled, priority, metadata)
VALUES (
  <club_id>, 'custom'::"ScrapingPlatform", 'ticketspice',
  'https://{account}.ticketspice.com/{form-slug}', TRUE, 0, '{}'::jsonb
);
```

**Reference implementation:** `apps/scraper/src/laughtrack/scrapers/implementations/api/ticketspice/`
(first venue: The Stage at Burke Junction — `thestage.ticketspice.com/barley-me-comedy`, TASK-3207)

---

### ThunderTix

| | |
|---|---|
| **Scraper key** | `thundertix` (generic — `GenericThunderTixScraper`) |
| **Platform** | `thundertix` |
| **DB field** | `scraping_sources.source_url` (+ optional `metadata.title_skip_prefixes`) |
| **Value format** | `https://{venue-slug}.thundertix.com` |
| **Generic?** | ✅ Single scraper, configured per-venue via `scraping_sources` |

**Detection signals:**
- Buy links or calendar pages at `{venue-slug}.thundertix.com`
- Network requests to `{venue-slug}.thundertix.com/reports/calendar`

**API pattern:**
```
GET https://{venue-slug}.thundertix.com/reports/calendar?week=0&start={ts}&end={ts+7d}
```
Returns a JSON array of performance objects, one per show. A single request covers a 7-day window.
The generic scraper generates 12 weekly URLs starting from the current Sunday.

**Key fields in each performance object:**
- `title` — show name
- `start` — datetime string with UTC offset (e.g. `"2026-03-24 20:00:00 -0500"`)
- `order_products_url` — relative ticket purchase path (prepend base URL)
- `truncated_url` — relative show page path (prepend base URL)
- `publicly_available` — skip when `False`
- `is_sold_out` — mark ticket as sold out when `True`

**Pricing:** the calendar API carries no price field. The scraper fetches each
distinct event detail page (`truncated_url`) once per run — performances share
a page and events recur across weekly windows — and parses the schema.org
JSON-LD `AggregateOffer.lowPrice` into the fallback ticket (TASK-2837).
Pages that fail to fetch are retried on a later window; missing/unparseable
prices stay `None` (price unknown).

**Filtering rules:**
- Skip events where `publicly_available` is `False` (always-on, engine-level)
- Skip events whose title starts with any of `metadata.title_skip_prefixes`
  (CSV; e.g. `"CLASS:,TRAINING CENTER:"` for The Annoyance Theatre's class listings).
  Omit the metadata key when the venue has no skip rules.

**Reference implementation:** `apps/scraper/src/laughtrack/scrapers/implementations/api/thundertix/`

**To onboard a new ThunderTix venue:**
1. Confirm the venue slug from the buy page URL: `{slug}.thundertix.com` (e.g. `theannoyance`).
2. Insert a `scraping_sources` row pointing at the venue:
   ```sql
   INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, metadata)
   VALUES (
     <club_id>,
     'thundertix'::"ScrapingPlatform",
     'thundertix',
     'https://{slug}.thundertix.com',
     -- optional: skip-prefix filter, comma-separated
     '{"title_skip_prefixes": "CLASS:,TRAINING CENTER:"}'::jsonb
   );
   ```
3. No code change required — the existing `GenericThunderTixScraper` resolves the new row automatically.

---

### TicketSource

| | |
|---|---|
| **Scraper key** | venue-specific (e.g. `comedy_clubhouse`) |
| **DB field** | `scraping_url` |
| **Value format** | `https://www.ticketsource.com/{venue-slug}` |
| **Generic?** | ❌ New venue-specific scraper required |

**Detection signals:**
- Buy links or redirects to `ticketsource.com/{slug}` or `ticketsource.us/{slug}`
- Page source contains CSS classes `eventRow`, `dateTime`, `event-btn`
- Server-rendered HTML — no JS required; `WebFetch` returns full event data

**HTML structure per event card:**
```
div.eventRow[data-id="..."]
  div.eventTitle > a[itemprop="url", href="/slug/event-title/e-XXXXX"]
    span[itemprop="name"]                      ← show title
  div.dateTime[content="2026-03-28T19:30"]     ← ISO local datetime (no timezone)
  div.event-btn > a[href="/booking/init/XXXX"] ← ticket purchase path
```

**Key implementation details:**
- Use `div.dateTime[content]` for datetime — parse with `strptime(dt_str, "%Y-%m-%dT%H:%M")`
  and localize with `pytz.timezone(club.timezone).localize(naive_dt)`
- Use `urllib.parse.urljoin(TICKETSOURCE_BASE, href)` for all URL construction — TicketSource
  hrefs are relative paths; `urljoin` handles both relative and absolute hrefs safely
- All upcoming events appear on a single page — no pagination needed
- **Rate-limiting:** TicketSource returns HTTP 429 on rapid successive WebFetch calls

**Reference implementation:** `apps/scraper/src/laughtrack/scrapers/implementations/venues/comedy_clubhouse/`

**To onboard a new TicketSource venue:**
1. Confirm the venue slug from the buy page URL: `ticketsource.com/{slug}`
2. Copy the `comedy_clubhouse/` scraper directory as the reference implementation
3. Update `SCRAPING_URL` constant, scraper `key`, and class names
4. Add a DB migration setting `scraper` and `scraping_url`

**DB setup:**
```sql
INSERT INTO clubs (name, scraper, scraping_url, ...)
VALUES ('My Venue', 'my_venue', 'https://www.ticketsource.com/my-venue', ...);
```

---

### Tempo Tickets

| | |
|---|---|
| **Scraper key** | `tempo_tickets` (generic — shared across all Tempo venues) |
| **Platform** | `custom` |
| **DB field** | `scraping_sources.source_url` + `metadata` keys `category_id` (required), `tags` (optional) |
| **Value format** | `source_url`: `https://www.tempotickets.com/tempotickets/site/pages/listing.php?c=<category_id>`; `metadata`: `{"category_id": "80", "tags": ["event", "improv"]}` |
| **Generic?** | ✅ generic — any tempotickets.com venue onboards via metadata, no new code |

**Detection signals:**
- Buy links / ticketing redirects to `tempotickets.com`
- Listing page is `…/tempotickets/site/pages/listing.php?c=<id>` (the `c=<id>` is the venue/category key)
- Server-rendered PHP HTML — browser UA, no JSON-LD / API / auth / anti-bot

**API/source pattern:**
- **Listing** `listing.php?c=<id>`: one `div.listing_table_row` per recurring event, each with `<a href='.../event/{code}'>{title}</a>`
- **Event** `/event/{code}`: upcoming individual dates live in `<select name='EventDateID'><option value='{dateId}'>Fri Jun 26 @ 7:30pm (...)</option>…</select>`

**Key extraction notes:**
- The scraper builds the listing URL from `metadata.category_id`, falling back to `source_url`
- Option `value='0'` is a placeholder (empty text) — skip it. Past dates render as `div.date_past` and are **not** inside the select, so no past-date filtering is needed
- **Year inference (GOTCHA):** option text carries no year ("Fri Jun 26 @ 7:30pm"). Since the select lists only upcoming dates, the year is inferred by rollover from the current date (a December scrape reads a "Jan 9" option as next year)
- Title is pulled from the event page `<h1>`/`<title>`; a leading 4-digit year ("2026 …") is stripped so rolled-over next-year dates don't carry a stale year
- `tags` come from source metadata (default `["event"]`), keeping the shared scraper generic — set `["event", "improv"]` for improv venues, etc.
- Buy URL = the `/event/{code}` page (the EventDateID is passable downstream)

**DB setup:**
```sql
-- See migrations/20260620_onboard_comedysportz_milwaukee_tempo.sql for the full
-- idempotent club + scraping_sources onboarding pattern.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom'::"ScrapingPlatform", 'tempo_tickets',
       'https://www.tempotickets.com/tempotickets/site/pages/listing.php?c=80',
       0, TRUE, '{"category_id": "80", "tags": ["event", "improv"]}'::jsonb
  FROM clubs c WHERE c.id = <club_id>;
```

**Failure modes / gotchas:**
- Recurring events fan out into many shows (one per upcoming option) — a single listing of 4 events produced 54 dated shows for ComedySportz MKE
- If a future Tempo listing changes the `div.listing_table_row` / `EventDateID` markup, the extractor returns zero — covered by the recorded-fixture smoke tests

**Reference implementation:**
- `apps/scraper/src/laughtrack/scrapers/implementations/tempo_tickets/`
- Event entity: `apps/scraper/src/laughtrack/core/entities/event/tempo_tickets.py`
- Reference venue/task: ComedySportz Milwaukee (`c=80`), TASK-3022

---

### Ticket Tailor

| | |
|---|---|
| **Scraper key** | `ticket_tailor` (generic — shared across all Ticket Tailor box offices) |
| **Platform** | `custom` |
| **Onboarded as** | Usually a `production_companies` row for roving producers; use a `scraping_sources` row with `metadata.single_venue=true` when the Ticket Tailor account is one physical club |
| **DB field** | Roving: `production_companies.scraping_url` = the box-office URL; `website` = the producer site. Single venue: `scraping_sources.source_url` = the box-office URL; `clubs.website` = the venue site. Both website fields are used as the Cloudflare-clearing Referer |
| **Value format** | `https://www.tickettailor.com/events/<account_slug>/` (== `/all-tickets/<account_slug>/`) |
| **Generic?** | ✅ generic — any tickettailor.com account onboards with config only |

**Detection signals:**
- Buy links / ticketing redirects to `tickettailor.com`
- Box-office listing at `tickettailor.com/events/<account>/` (the `<account>` slug is the box office)
- Server-rendered HTML (no reliable JSON-LD), behind Cloudflare

**Roving-producer model (per-show venues):**
- A Ticket Tailor account is modeled as a `production_companies` row with **no** `production_company_venues` mapping. `ScrapingService._scrape_production_companies` then builds a synthetic in-memory Club proxy via `_build_synthetic_proxy_for_company`, which recognizes Ticket Tailor box-office URLs (alongside Eventbrite organizers) and drives `TicketTailorScraper`.
- The scraper parses each event's own venue (name + zip) from the listing and upserts one `clubs` row per distinct venue via `ClubHandler.upsert_discovered_venue`; each Show is built on its per-venue club. The orchestrator stamps `production_company_id` on every resulting Show.
- Set `production_companies.visible = FALSE` for a hidden proxy producer — its shows surface under the auto-created per-venue clubs, not under a producer page.

**Single-venue club model:**
- If the Ticket Tailor account belongs to one venue, add a normal enabled `scraping_sources` row on that club with `scraper_key='ticket_tailor'`, `source_url='https://www.tickettailor.com/events/<account_slug>/'`, and metadata `{"account_slug": "<account_slug>", "single_venue": true}`.
- In `single_venue` mode, `TicketTailorScraper` attaches every listing event to the configured club and does **not** call `ClubHandler.upsert_discovered_venue`.
- West River Comedy Club (TASK-3026) uses this mode because the previous `json_ld` + `force_js_rendering` source hit hard Cloudflare Turnstile from GHA datacenter egress, while the Ticket Tailor listing HTML clears via curl-cffi impersonation plus the venue website Referer and avoids Playwright entirely.

**Mixed-use venues (comedy title filter, off by default):** Some Ticket Tailor box offices are general event halls that host an intermittent comedy series alongside raves / DJ nights / concerts / private parties (e.g. Continental Club Oakland, TASK-3216). Apply an opt-in title filter via `scraping_sources.metadata` so only comedy is ingested:
- `include_title_patterns` — keep only events whose title matches at least one regex (the comedy allowlist, e.g. `["comedy", "stand[- ]?up", "comedian", "open mic", "improv", "showcase"]`).
- `exclude_title_patterns` — drop events whose title matches any regex (a blocklist).
Both are off by default (pattern parsing via the shared `BaseScraper.compile_title_patterns`; include-then-exclude loop mirrors `ticketweb`/`sellingticket`/`showare`), so existing pure-comedy Ticket Tailor sources (West River, Milwaukee Comedy) are unchanged. When the live feed is currently all non-comedy, the filter yields **0 shows by design** — comedy auto-populates when the next stand-up night is listed (Clayton Club precedent, TASK-3192). A 0-show scrape on a comedy-filtered mixed-use source is expected, not a failure.

**Key extraction notes:**
- Each event card is `li.events-listing__item`: `h3.event__title` / `a.event__link` (detail link), `span.event-meta__date` ("Tue Jun 30, 2026 6:00 PM - 9:00 PM CDT"), `span.event-meta__location` ("Vendetta Coffee Bar, 53204" = name + zip)
- The date carries the year; the US timezone abbreviation (CDT/EST/…) is mapped to an IANA zone for localization
- Per-venue clubs get only name + zip (the listing has no street/city), so `city`/`state` are empty — see TASK-3023 context atom on the dedup limitation

**Anti-bot (Cloudflare):**
- tickettailor.com 403s a plain request. The scraper clears it with `curl_cffi` browser impersonation plus a `Referer` header set to the producer or venue website.
- Cloudflare can reject one browser fingerprint from datacenter egress while accepting another, so the scraper tries `chrome124`, then `chrome120`, then `safari17_0` before failing the source.
- Prefer this scraper over `json_ld` + `force_js_rendering` for Ticket Tailor-hosted calendars. Playwright may get a local residential managed challenge that auto-clears but a GHA datacenter hard Turnstile that does not; the listing scraper avoids that path.

**DB setup:**
```sql
-- See migrations/20260620_onboard_milwaukee_comedy_ticket_tailor.sql for the full
-- idempotent onboarding. No production_company_venues row (→ synthetic proxy).
INSERT INTO production_companies (name, slug, scraping_url, website, visible, show_name_keywords)
VALUES ('Milwaukee Comedy', 'milwaukee-comedy',
        'https://www.tickettailor.com/events/milwaukeecomedy/',
        'https://www.milwaukeecomedy.com/', FALSE, ARRAY[]::text[])
ON CONFLICT (name) DO UPDATE SET scraping_url = EXCLUDED.scraping_url, website = EXCLUDED.website;
```

**Failure modes / gotchas:**
- If the listing markup (`li.events-listing__item` / `event-meta__*`) changes, the extractor returns zero — covered by the recorded-fixture smoke test
- The simple per-venue upsert loop omits the Eventbrite organizer scraper's lock-cascade retry machinery; fine for small indie feeds, revisit if a high-volume Ticket Tailor producer is onboarded

**Reference implementation:**
- `apps/scraper/src/laughtrack/scrapers/implementations/ticket_tailor/`
- Event entity: `apps/scraper/src/laughtrack/core/entities/event/ticket_tailor.py`
- Synthetic-proxy dispatch: `_build_synthetic_proxy_for_company` in `core/services/scraping/__init__.py`
- Reference producer/task: Milwaukee Comedy (account `milwaukeecomedy`), TASK-3023

---

### Ludus

| | |
|---|---|
| **Scraper key** | `ludus` (generic — shared across all Ludus venues) |
| **Platform** | `custom` |
| **DB field** | `scraping_sources.source_url` + `metadata` keys `ludus_subdomain` (required), `comedy_category_id` (required), `comedy_filter` (optional) |
| **Value format** | `metadata`: `{"ludus_subdomain": "parktheatreholland", "comedy_category_id": "468", "comedy_filter": true}` |
| **Generic?** | ✅ generic — any ludus.com venue onboards via metadata, no new code |

**Detection signals:**
- Buy links / embedded widget from `*.ludus.com` (formerly Tixato); the venue's own site often only embeds the Ludus widget
- Box-office embed at `{subdomain}.ludus.com/embed/index.php?widget=1&sections=all&hideNav=false`

**API/source pattern (two-step embed → detail):**
- **Embed**: one `div.show_item[data-show-id][data-event-categories]` per show, title in `h2.show_item_title`. The `&category_id=` URL param does NOT server-side filter — comedy shows are filtered client-side on the `;`-separated `data-event-categories` containing the venue-specific `comedy_category_id`
- **Detail** `{subdomain}.ludus.com/index.php?show_id=<id>`: dates are NOT on the embed cards; each detail page lists `div.showtimes_item[data-past-date]` rows with a human-readable "Sunday, July 12, 2026 7:00 PM" date

**Key extraction notes:**
- The `comedy_category_id` is a coarse venue tag and can be mis-applied (e.g. a "Radiohead Performed by Android Paranoid" tribute band mis-tagged comedy). Layer the shared comedy filter (`comedy_filter: true` → `select_comedy_titles`, keyword OR known-comedian) on top to drop mis-tags. This keeps bare-comedian-name titles (e.g. "Cam Bertrand") via the comedian DB while dropping the tribute band
- The card title is trimmed at the " ★ <Venue>" separator the listing appends
- Skip `div.showtimes_item[data-past-date="1"]`; dedupe (the row repeats its date text). The human-readable date carries the year; localize with the club timezone (e.g. America/Detroit, EDT/EST)

**Anti-bot (Cloudflare):**
- Ludus sits behind a Cloudflare managed challenge that 403s a plain request; a `curl_cffi` `impersonate='chrome120'` session clears it (no Referer needed)

**DB setup:**
```sql
-- See migrations/20260620_onboard_park_theatre_holland_ludus.sql for the full
-- idempotent club + scraping_sources onboarding.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom'::"ScrapingPlatform", 'ludus', 'https://parktheatreholland.ludus.com/', 0, TRUE,
       '{"ludus_subdomain": "parktheatreholland", "comedy_category_id": "468", "comedy_filter": true}'::jsonb
  FROM clubs c WHERE c.id = <club_id>;
```

**Failure modes / gotchas:**
- The `comedy_category_id` is **venue-specific** — find it by inspecting `data-event-categories` on the embed's comedy cards
- The full embed page is large (~500 KB); recorded fixtures are trimmed to a few real cards
- If the embed markup (`show_item` / `showtimes_item`) changes, the extractor returns zero — covered by the recorded-fixture smoke test

**Reference implementation:**
- `apps/scraper/src/laughtrack/scrapers/implementations/ludus/`
- Event entity: `apps/scraper/src/laughtrack/core/entities/event/ludus.py`
- Reference venue/task: Park Theatre Holland (subdomain `parktheatreholland`, category `468`), TASK-3025

---

### Humanitix

| | |
|---|---|
| **Scraper key** | `json_ld` |
| **DB field** | `scraping_url` (full Humanitix host page URL) |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Venue's website links to `events.humanitix.com/host/<slug>`
- The host page embeds `<script type="application/ld+json">` blocks with `@type=Event`
- Some orgs instead publish a **collections page** at `collections.humanitix.com/<slug>` — its
  JSON-LD nests the events inside an `ItemList` (`itemListElement[].item` with `@type=Event`)
  rather than as top-level `Event` blocks. The `json_ld` scraper recurses the `ItemList`, so the
  collections URL works as `scraping_url` exactly like a host URL (TASK-3177, Safe Words Comedy Show).

**Key implementation details:**
- Uses the existing `json_ld` scraper — no new code needed
- The `<slug>` appears in the Humanitix host page URL
- The `JsonLdScraper` fetches the host page and extracts all events in a single request — no per-event page visits needed
- Ticket URLs follow the pattern `https://events.humanitix.com/{event-slug}/tickets`
- **No public REST API** — the host page HTML is the only data source
- No `humanitix_id` column exists; store the full host URL in `scraping_url`
- Collections-page JSON-LD leads with a urless `AggregateOffer` (a price-range summary); the
  ticket layer falls back to the event URL for `purchase_url` so the show isn't dropped by validation
- **No host/collections page (events linked individually):** when the venue's own CMS page
  (Squarespace/Wix/etc.) links each show as a separate `events.humanitix.com/<slug>` event and the
  org exposes no host or collections page, use the `json_ld` scraper in **detail-fetch mode**: set
  `scraping_url` to the venue's own shows/calendar page and configure `metadata.detail_fetch` to
  collect the Humanitix anchors, then fetch each event page's (multi-date) JSON-LD. Each event page
  embeds every date of that recurring event as its own `Event` block (TASK-3185, All Out Comedy
  Theater — 5 event pages → 17 shows).

**DB setup:**
```sql
-- Host page (all events in one fetch):
INSERT INTO clubs (..., scraper, scraping_url, ...)
VALUES (..., 'json_ld', 'https://events.humanitix.com/host/my-venue', ...);

-- Detail-fetch over a CMS page that links individual Humanitix events (no host page):
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, enabled, priority, metadata)
VALUES (
  <club_id>, 'custom', 'json_ld', 'https://myvenue.com/shows', TRUE, 0,
  jsonb_build_object('detail_fetch', jsonb_build_object(
    'url_path_prefix', '/',
    'allowed_hosts', jsonb_build_array('events.humanitix.com'),
    'set_same_as_to_detail_url', true
  ))
);
```

---

### Elfsight Event Calendar

| | |
|---|---|
| **Scraper key** | `elfsight` |
| **DB fields** | `source_url` = venue calendar page; `metadata.widget_pid` = Elfsight widget id; `metadata.comedy_filter` (optional) |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- The venue's events/calendar page makes no native data call (no JSON-LD events, no Squarespace `GetItemsByMonth`); instead it loads an Elfsight widget.
- Network tab shows `core.service.elfsight.com/p/boot/?w=<widget_pid>` and `widget-data.service.elfsight.com/api/events?source=...&widget-token=...`.
- The page HTML references `elfsightcdn.com` / `service.elfsight.com` assets.

**Key implementation details:**
- Two-step anonymous flow: boot the widget (`/p/boot/?w=<widget_pid>`) for a fresh `public_widget_token` + the events `source` id (under `settings.integrationGoogleCalendar.source`), then call the events API. The token is short-lived, so it is fetched on every scrape — only the widget PID is persisted.
- The calendar is usually backed by a Google Calendar, so events carry no per-event ticket field; the scraper lifts the first `href` from each event's description HTML as the ticket URL (falling back to `buttonLink`, then the venue calendar page).
- **Mixed-use venues**: set `metadata.comedy_filter=true` to drop non-comedy programming (film screenings, live music, drama) via the comedy keyword allowlist. Note the allowlist matches `improv`/`sketch`/`comedy`/`stand-up`/`open-mic`/`roast` but **not** `parody`, so parody-only shows are dropped under the filter.

**DB setup:**
```sql
-- source_url = venue calendar page; widget_pid drives both Elfsight requests
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, enabled, priority, metadata)
VALUES (
  <club_id>, 'custom', 'elfsight', 'https://venue.com/event-calendar', TRUE, 0,
  jsonb_build_object('widget_pid', '<widget-uuid>', 'comedy_filter', true)
);
```

Reference impl: Eclectic Box SF (San Francisco, CA) — TASK-3179.

---

### Ninkashi

| | |
|---|---|
| **Scraper key** | `ninkashi` |
| **DB field** | `scraping_url` (the `url_site` subdomain, e.g. `tickets.cttcomedy.com`) |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Venue has a `tickets.{venue}.com` subdomain
- Network requests to `api.ninkashi.com/public_access/events/find_by_url_site`

**API endpoint** (no auth required):
```
GET https://api.ninkashi.com/public_access/events/find_by_url_site?url_site=<url_site>&page=1&per_page=100
```

Response is a **root-level JSON array** of events. Key fields: `id`, `title`, `time_zone` (IANA string), `tickets_attributes`, `event_dates_attributes`.

**Pagination behavior:**
- The client requests `per_page=100` per page and increments `page` until a stop condition is met.
- **Stop condition:** a page whose length is less than the first page's actual response size (not the hardcoded `PER_PAGE=100`). This handles APIs that return fewer items on the first page and ensures the loop terminates correctly even if the first page is a partial page.
- **Duplicate-page early stop:** After fetching each page, the client checks whether all event IDs on that page were already seen on a previous page. If so, it stops immediately. This prevents the MAX_PAGES=50 warning for CTT (Cheaper Than Therapy): the Ninkashi API for that venue ignores the `page` parameter and returns the same 105 events on every page, so the deduplication check fires on page 2 and the client fetches only 1 unique page. Without this, the loop ran to MAX_PAGES=50 and processed 5250 duplicate records.
- **Date-horizon early stop:** `DATE_HORIZON_DAYS=730` (2 years) — if any event on a page starts more than 730 days from now, pagination stops immediately and those events are excluded. This is a secondary safeguard for venues (including CTT) that pre-book many years of inventory.
- **Hard cap:** `MAX_PAGES=50` — pagination stops regardless of page size once 50 pages have been fetched, with a warning logged. This is a last-resort safety net.
- **Past-event filtering:** The client filters events client-side using `_is_future_event()`. Each event's `event_dates_attributes[0].starts_at` is compared to `datetime.now(UTC)`. Events with a start time in the past are discarded before returning. Events with a missing or unparseable start time are included (fail-open to avoid silent drops).

**Important API quirks:**
- `starts_at` is **NOT** at the top level — it is nested under `event_dates_attributes[0].starts_at` (format: `"2026-04-01 19:45:00 -0700"`, space-separated with 4-digit offset, no colon). Parse with `strptime("%Y-%m-%d %H:%M:%S %z")`.
- Ticket tier name is in the `description` field (not `name`) of each `tickets_attributes` entry
- Ticket `price` is in **cents** (e.g. `2500` = $25.00) — divide by 100 to get dollars

Ticket URL is constructed as `https://{url_site}/events/{id}`.

**Reference implementation:** `apps/scraper/src/laughtrack/scrapers/implementations/api/ninkashi/`

**DB setup:**
```sql
INSERT INTO clubs (..., scraper, scraping_url, ...)
VALUES (..., 'ninkashi', 'tickets.myvenue.com', ...);
```

---

### StageTime

| | |
|---|---|
| **Scraper key** | Venue-specific (e.g. `comedy_corner_underground`) |
| **DB field** | `scraping_url` |
| **Value format** | `https://{slug}.stageti.me` |
| **Generic?** | ❌ Custom venue scraper required |

StageTime (stageti.me) is a Next.js ticketing platform. Venues have a subdomain: `{slug}.stageti.me`.

**Data extraction approach:**
1. Fetch the listing page `https://{slug}.stageti.me/` — extract event slugs from `href="/v/{slug}/e/{event-slug}"` anchor links (BeautifulSoup).
2. For each event slug, fetch `https://{slug}.stageti.me/e/{event-slug}`. Event pages embed data in `self.__next_f.push([1,"..."])` RSC wire format segments:
   - JSON-decode the quoted string content
   - Split by newlines — each line is one RSC chunk (`XX:[...]` format)
   - Chunk containing `"occurrences":[` has: event name, isOpenMic, admissionType, occurrences[].startTime (UTC ISO), venue.timezone
   - Chunk with `"id":"event-jsonld"` has: performer names and ticket URL (in `dangerouslySetInnerHTML.__html` as a doubly-escaped JSON-LD string)
3. One event per occurrence; skip `isOpenMic=true` and `admissionType='no_advance_sales'` events.

**Occurrence start times** are UTC ISO strings (`"2026-04-04T01:00:00.000Z"`). Convert to local time via pytz: parse with `%Y-%m-%dT%H:%M:%S.%fZ`, localize to UTC, then convert to `venue.timezone`.

**Test fixtures:** RSC status fields are double-escaped in push segments. To patch a published occurrence to cancelled in a test:
`html.replace('\\"status\\": \\"published\\"', '\\"status\\": \\"cancelled\\"', 1)`

**Reference implementation:** `apps/scraper/src/laughtrack/scrapers/implementations/venues/comedy_corner_underground/`

**DB setup:**
```sql
INSERT INTO clubs (..., scraper, scraping_url, ...)
VALUES (..., 'comedy_corner_underground', 'https://comedycornerunderground.stageti.me', ...);
```

---

### JetBook (Bubble.io)

| | |
|---|---|
| **Scraper key** | `jetbook` |
| **DB field** | `scraping_url` |
| **Value format** | `https://jetbook.co/o_iframe/<venue-slug>` |
| **Generic?** | ✅ One scraper handles all JetBook venues |

JetBook is a hosted comedy/improv ticketing platform built on Bubble.io. Venues are embedded as an iframe on their own site (e.g. Framer, Squarespace) pointing at `https://jetbook.co/o_iframe/<venue-slug>`.

**Detection signals:**
- `jetbook.co/o_iframe/...` iframe `src` on the venue's site
- Page issues POSTs to `/elasticsearch/msearch` and `/elasticsearch/mget`
- `/api/1.1/init/data?location=<iframe_url>` returns Bubble lookup IDs (format `<id>__LOOKUP__<id>`) in `data[0].data.list_events_list_custom_event1` — NOT full event objects

**Data extraction approach:**

The init endpoint only returns opaque lookup IDs; full event records are resolved via `POST /elasticsearch/msearch`. Bubble **encrypts the msearch request body** (opaque `{"z":"..."}` payload) but the **response body is plaintext JSON** and contains the full record:

```json
{"responses":[{"hits":{"hits":[{"_id":"<bubble id>","_source":{
  "name_text": "<title>",
  "parsedate_start_date": <unix ms>,
  "Slug": "<per-event slug>",
  "typevisible_option_typevisible": "visible",
  "visble_boolean": true,
  "ticket_page_visible_boolean": true,
  "description_text": "...",
  ...
}}, ...]}}, ...]}
```

Pipeline:
1. Launch a Playwright headless Chromium browser.
2. Attach a `response` listener that captures every `/elasticsearch/msearch` 200 body.
3. Navigate to the iframe URL with `wait_until='networkidle'`.
4. Scroll to the bottom of the page and click the "Show more" button repeatedly via `page.evaluate()` (standard Playwright `.click()` times out because Bubble's custom button is considered "not visible"). Each click triggers another msearch batch.
5. Parse every captured body; filter to records where `visble_boolean=true`, `ticket_page_visible_boolean=true`, `typevisible_option_typevisible='visible'`, and `parsedate_start_date >= now`; dedupe by `_id`.

**Ticket URL pattern:** `https://jetbook.co/e/<slug>` (returns HTTP 200 with the event's detail page).

**Gotchas:**
- `init/data` exposes an `eventbrite_org_id_text` field — this is NOT a real Eventbrite org (the Eventbrite API returns 404). Do not onboard JetBook venues via the Eventbrite scraper.
- The "Show more" button must be clicked via `evaluate()` — `ElementHandle.click()` times out.
- `parsedate_start_date` is a Unix **millisecond** timestamp (UTC).

**Reference implementation:** `apps/scraper/src/laughtrack/scrapers/implementations/jetbook/`

**DB setup:**
```sql
UPDATE clubs
SET scraper = 'jetbook',
    scraping_url = 'https://jetbook.co/o_iframe/<venue-slug>',
    visible = TRUE
WHERE id = <club_id>;
```

---

### OvationTix

| | |
|---|---|
| **Scraper key** | `uncle_vinnies` (calendar-based) or `four_day_weekend` (direct productions) |
| **DB field** | `scraping_url` |
| **Generic?** | ❌ Venue-specific — production IDs differ per venue |

**Detection signals:**
- Ticket buy links go to `ci.ovationtix.com/{clientId}/production/{id}`
- Network requests to `web.ovationtix.com/trs/api/rest/Production({id})/performance?`

**Two patterns based on how the venue organizes its productions:**

**Pattern 1 — Calendar-based (e.g. Uncle Vinnies)**
- Many production IDs, each representing a single recurring show series
- Discover IDs by scraping the venue's HTML calendar pages (look for `class="tickets-button"` anchors pointing to `ci.ovationtix.com/.../production/{id}`)
- For each production, fetch only `performanceSummary.nextPerformance` (one upcoming date)
- `scraper = 'uncle_vinnies'`

**Pattern 2 — Direct productions (e.g. Four Day Weekend Comedy)**
- Few production IDs on a static buy-tickets page, each with many upcoming performances
- Discover IDs by fetching the venue's buy-tickets page and extracting `ci.ovationtix.com/{clientId}/production/{id}` links
- For each production, use the full `performances[]` array (all upcoming dates)
- `scraper = 'four_day_weekend'` (reuse this key for new venues following this pattern)

**Both patterns** use `Production({id})/performance?` with `clientId` and `newCIRequest: true` headers. The client/org ID appears in the production URL on the venue's buy page.

**Pattern 3 — Generic OvationTix scraper (e.g. Comedy @ The Carlson, Side Splitters)**
- Uses scraper key `ovationtix` — reads `ovationtix_client_id` from the club record
- `scraping_url` **must** be `https://web.ovationtix.com/trs/cal/{clientId}` (server-rendered calendar page). Do NOT use `ci.ovationtix.com/{clientId}` — that is a JS SPA and the HTML contains no production IDs for the scraper to discover.
- Discovers all production IDs from the calendar HTML, fetches performances and pricing automatically

**Ticket pricing:** fetched via a separate `Performance({id})` call per upcoming show. Response `sections[].ticketTypeViews` provides per-tier pricing. Format the ticket `type` as `f"{ticketGroupName} - {name}"` (e.g. `"General - Adult"`) to match `OvationTixClient._extract_ticket_data()` and avoid dedup key mismatches.

---

### OpenDate

| | |
|---|---|
| **Scraper key** | venue-specific (ref: `sports_drink`) |
| **DB field** | `scraping_url` |
| **Value format** | `https://app.opendate.io/v/{venue-slug}?per_page=500` |
| **Generic?** | ❌ New venue-specific scraper required |

**Detection signals:**
- Venue sells tickets via `app.opendate.io`
- Playwright network inspection shows only analytics/Stripe requests — no JSON API calls
- WebFetch on the listing page returns full event HTML (server-rendered)

**Listing URL format:**
```
https://app.opendate.io/v/{venue-slug}?per_page=500
```
The `?per_page=500` parameter is **required** — the default returns only ~50 events per page with no auto-pagination.

**HTML structure per event card (`div.confirm-card`):**
```html
<div class="card confirm-card">
  <div class="card-body">
    <p class="mb-0 text-dark">
      <a class="text-dark stretched-link" href="https://app.opendate.io/e/{slug}"><strong>{Title}</strong></a>
    </p>
    <p class="mb-0" style="color: #1982c4; ...">April 03, 2026</p>   <!-- date -->
    <p class="mb-0" style="color: #1982c4; ...">Doors: 6:30 PM - Show: 7:00 PM</p>   <!-- time -->
    <p class="mb-0 text-truncate" ...>VENUE NAME • City, ST</p>
  </div>
</div>
```

**Key extraction notes:**
1. The stretched-link `<a>` gives both the event URL (tickets) and title (via `<strong>`)
2. Blue `p.mb-0` paragraphs identified by `color: #1982c4` inline style — first is date, second is time. Exclude `text-dark` and `text-truncate` paragraphs.
3. Extract show time via regex: `Show:\s*(\d{1,2}:\d{2}\s*[AP]M)`. Normalize compact format (`"8:30PM"`) to `"8:30 PM"` before strptime.
4. Date format: `"%B %d, %Y"` (e.g. `"March 29, 2026"`)
5. Event URL doubles as the ticket purchase URL
6. **Pricing** (TASK-2839): the listing renders no price strings; each detail
   page (`/e/{slug}`) embeds schema.org JSON-LD with `offers.price` (single
   Offer dict, string price). The scraper fetches each distinct detail URL
   once per run (memoized, failure-evicting) and parses it via the shared
   `EventExtractor.extract_min_offer_price`; at the default 1 req/s host
   limit this adds ~2.5 min for ~143 events — fine for a nightly job.

**To onboard a new OpenDate venue:**
1. Find the venue slug from their OpenDate page URL: `app.opendate.io/v/{slug}`
2. Copy the `sports_drink/` scraper directory as the reference implementation
3. Update the venue slug constant

---

### Fienta

| | |
|---|---|
| **Scraper key** | venue-specific (ref: `madrid_comedy_lab`) |
| **DB field** | `scraping_url` |
| **Value format** | `https://fienta.com/api/v1/public/events?organizer={organizer_id}` |
| **Generic?** | ❌ New venue-specific scraper required |

**Detection signals:**
- Venue website loads events via JavaScript calling `fienta.com/api/v1/public/events`
- Buy/ticket links point to `fienta.com/{event-slug}`
- Venue listed on `fienta.com/o/{organizer-slug}`

**API endpoint:**
```
https://fienta.com/api/v1/public/events?organizer={organizer_id}
```
Returns a JSON object with `events` array containing all upcoming events. No pagination needed — all events are returned in a single response.

**Response structure:**
```json
{
  "success": {"code": 200},
  "count": 25,
  "events": [
    {
      "id": 177670,
      "title": "Dark Humour Night",
      "starts_at": "2026-04-09 20:30:00",
      "ends_at": "2026-04-09 22:00:00",
      "url": "https://fienta.com/dark-humour-night-lab-177670",
      "sale_status": "onSale",
      "address": "...",
      "description": "<p>...</p>"
    }
  ]
}
```

**Key extraction notes:**
1. `starts_at` and `ends_at` are in the organizer's local timezone (no UTC offset)
2. `sale_status` can be `"onSale"` or `"soldOut"` — use for ticket availability
3. Some organizers mix non-show items (gift vouchers) — filter by title keywords
4. Find the `organizer_id` by inspecting the venue website's JS source for the API call

**To onboard a new Fienta venue:**
1. Find the organizer ID from the venue website's JavaScript (`fienta.com/api/v1/public/events?organizer=XXXXX`)
2. Copy the `madrid_comedy_lab/` scraper directory as the reference implementation
3. Update the organizer ID constant and title exclusion filters

---

### Showpass

| | |
|---|---|
| **Scraper key** | `showpass` |
| **DB field** | `scraping_url` |
| **Value format** | Showpass calendar API base URL: `https://www.showpass.com/api/public/venues/{slug}/calendar/` |
| **Generic?** | ✅ DB-only onboarding — no Python changes needed |

**Detection signals:**
- Venue website embeds a Showpass calendar widget (iframe to `showpass.com/widget/tickets/events/calendar/{venue_id}/`)
- Buy/ticket links point to `showpass.com/{event-slug}/`
- Network requests to `showpass.com/api/public/venues/{slug}/calendar/`
- Venue listed on `showpass.com/o/{organizer-slug}`

**API endpoint:**
```
GET https://www.showpass.com/api/public/venues/{slug}/calendar/
    ?only_parents=true
    &page_size=100
    &ends_on__gte={start}
    &starts_on__lt={end}
    &slug={slug}
    &version=1
```
Returns a JSON object with a `results` array. No auth required. Paginate by month.

**IMPORTANT:** Datetime parameters must use `.000Z` suffix (e.g. `2026-04-01T00:00:00.000Z`),
NOT `+00:00`. The API returns HTTP 400 for `+00:00` format.

**Response structure:**
```json
{
  "results": [
    {
      "id": 1500904,
      "name": "Performing April 13 : Tre Stewart",
      "slug": "performing-april-13-tre-stewart",
      "starts_on": "2026-04-14T01:30:00+00:00",
      "ends_on": "2026-04-14T03:00:00+00:00",
      "timezone": "America/Edmonton",
      "sold_out": false,
      "status": "sp_event_active",
      "description": "<p>...</p>",
      "image_banner": "images/events/comedy-cave/img-banner/..."
    }
  ]
}
```

**Key extraction notes:**
1. `starts_on`/`ends_on` are ISO 8601 with UTC offset — parse with `datetime.fromisoformat()`
2. `status` should be `"sp_event_active"` — skip other statuses
3. Comedian name is often in the event `name` field as "Performing <date> : <Name>"
4. Ticket URL: `https://www.showpass.com/{slug}/`
5. Find the venue slug by inspecting the embedded widget URL or network requests

**To onboard a new Showpass venue:**
1. Find the venue slug from the embedded widget URL or API network requests
2. Insert a DB row: `scraper = 'showpass'`, `scraping_url = 'https://www.showpass.com/api/public/venues/{slug}/calendar/'`
3. Set `website` to the venue's own website URL (used as the show page URL for traffic attribution)

---

### TicketLeap

| | |
|---|---|
| **Scraper key** | `ticketleap` |
| **DB field** | `scraping_url` |
| **Value format** | Org listing URL: `https://events.ticketleap.com/events/{org_slug}` |
| **Generic?** | ✅ DB-only onboarding — no Python changes needed |

**Detection signals:**
- Venue website embeds a TicketLeap widget or links to `events.ticketleap.com/events/{org_slug}`
- Buy/ticket links point to `events.ticketleap.com/tickets/{org_slug}/{event-slug}`
- Event detail URLs follow `events.ticketleap.com/event/{event_id}` (numeric ID)

**Two-step (listing → detail) flow:**

1. **Listing page** (`events.ticketleap.com/events/{org_slug}`) does **not** embed per-event
   JSON-LD. Event IDs are only available inside a `window.dataLayer.push({...})` call that
   runs client-side. Extract with Playwright + `json.JSONDecoder().raw_decode()`:

   ```html
   <script>
     window.dataLayer = window.dataLayer || [];
     window.dataLayer.push({"event":"orglisting_page_view",
                            "listing_slug":"funny",
                            "event_ids":[2053571, 2091519, 2080411, ...],
                            "event_names":[...],
                            "display_type":"grid"});
   </script>
   ```

   Listing page requires JS rendering — curl-cffi receives a ~17 KB shell without the
   dataLayer payload. The scraper uses `_fetch_html_with_js()` (Playwright) for this
   single request.

2. **Event detail page** (`events.ticketleap.com/event/{event_id}`) is server-rendered
   and carries a single standard schema.org `<script type="application/ld+json">` Event
   block. Fetch with plain `fetch_html()` (curl-cffi) and run the shared
   `EventExtractor.extract_events()` on the HTML. Maps cleanly to `JsonLdEvent`.

**Key extraction notes:**
1. `startDate` is the show's first performance (TicketLeap may emit `endDate` months
   later for recurring series — it denotes the last performance in the run, not the
   single show's end time).
2. Ticket `offers[]` may contain multiple tiers (e.g. "General Admission", "preferred
   seating") — the existing JSON-LD offer transformer captures them all.
3. `location.name` distinguishes different physical locations under the same org slug
   (see "Multi-location caveat" below).

**Multi-location caveat:**

A single TicketLeap org (`/events/{org_slug}`) can back multiple physical venues. The
only structured signal distinguishing them is `location.name` on each per-event JSON-LD
block. When onboarding, always enumerate the distinct `location.name` values in the
feed:
- One value → one club row.
- Multiple values → model each location as its own club row with its own `scraper=
  ticketleap` entry; add a per-event `location.name` filter in a venue-specific scraper
  (subclass `TicketleapScraper` or filter in the transformer) so each club only ingests
  its own shows.

Example: Mesquite St. Comedy Club's 'funny' org covers a downtown and a southside
venue. At onboarding time (2026-04-16) all shows were tagged downtown so a single club
row was sufficient; if southside events reappear a second club row + filter will be
needed to avoid mis-attributing them.

**To onboard a new TicketLeap venue:**
1. Visit `events.ticketleap.com/events/{org_slug}` in a browser to confirm events are listed.
2. Check the distinct `location.name` values on a few event detail pages to decide
   whether to model as one club or many.
3. Insert/update the DB row: `scraper = 'ticketleap'`, `scraping_url =
   'https://events.ticketleap.com/events/{org_slug}'`, and set `website` to the venue's
   own site for traffic attribution.

---

### Tock

| | |
|---|---|
| **Scraper key** | `tock` |
| **Platform** | `custom` |
| **DB field** | `scraping_sources.source_url`, optional `metadata.comedy_filter` |
| **Value format** | Business page URL: `https://www.exploretock.com/{business_slug}` |
| **Generic?** | ✅ DB-only onboarding for Tock business pages with rendered calendar state |

**Detection signals:**
- Venue website links to `exploretock.com/{business_slug}` or `exploretock.com/{business_slug}/event/{id}/{slug}` ticket pages
- Plain HTTP may return Cloudflare, but the scraper's Playwright browser can render the Tock page
- Rendered HTML contains `window.$REDUX_STATE` with `calendar.offerings.experience[]`

**API/source pattern:**
- `TockScraper` uses `_fetch_html_with_js()` on the configured business page.
- It parses the rendered `window.$REDUX_STATE` object, normalizing Tock's JavaScript-only
  values (`undefined`, `function noop`) before JSON decoding.
- Each `GA_EVENT` experience becomes one event using `eventDetails.date`,
  `eventDetails.startTime`, `eventDetails.location`, `priceCents`, `id`, and `slug`.
- Recurring `PRIX_FIXE` reservation pages (e.g. BATSU! Chicago) expose ticket
  tiers as experiences plus `calendar.openDate[]` and `calendar.openTime[]`.
  The scraper creates one show per date/time and attaches each tier as a ticket.

**Key extraction notes:**
- Dates/times are local to the club timezone from the club row.
- Ticket/show URL is reconstructed as `{source_url}/event/{id}/{slug}`.
- `priceCents` becomes a USD ticket price; missing or malformed prices stay unknown.
- For recurring `PRIX_FIXE` pages, the show URL is the business page and ticket
  URLs point to the tier detail pages.
- Mixed-use calendars should set `metadata.comedy_filter = true`; filtering uses
  title/description comedy keywords (`comedy`, `stand-up`, `improv`, `open mic`, etc.).

**DB setup:**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom'::"ScrapingPlatform", 'tock',
       'https://www.exploretock.com/{business_slug}',
       0, TRUE, '{"comedy_filter": true}'::jsonb
  FROM clubs c
 WHERE c.name = '<Venue Name>';
```

**Failure modes / gotchas:**
- Do not confuse Tock (`exploretock.com`) with Tockify (`tockify.com`); they use unrelated
  data shapes and scraper keys.
- Plain `curl` can hit Cloudflare and return a challenge page. Test fetchability with
  `PlaywrightBrowser`, not `requests`.
- Tock also has lower-level session/protobuf APIs, but this scraper intentionally uses
  the rendered business-page state so onboarding remains DB-configurable.

**Reference implementation:**
- `apps/scraper/src/laughtrack/scrapers/implementations/tock/`
- `apps/scraper/tests/scrapers/implementations/tock/test_scraper.py`
- TASK-2993: My Buddy's (Chicago)
- TASK-3014: BATSU! Chicago recurring PRIX_FIXE reservations

---

### FareHarbor

| | |
|---|---|
| **Scraper key** | `fareharbor` |
| **Platform** | `custom` (no `ScrapingPlatform` enum value) |
| **DB field** | `scraping_sources.source_url` + `metadata.shortname`, optional `metadata.exclude_item_pks`, `metadata.allow_item_pks`, `metadata.months_ahead` |
| **Value format** | `source_url=https://fareharbor.com/embeds/book/{shortname}/`; `metadata.shortname="{shortname}"` |
| **Generic?** | ✅ generic for FareHarbor public item/calendar JSON |

**Detection signals:**
- Booking links or embeds under `fareharbor.com/embeds/book/{shortname}/...`.
- Public company items API responds at `https://fareharbor.com/api/v1/companies/{shortname}/items/`.
- Embed pages load FareHarbor's Angular booking shell and item calendar JSON.

**API/source pattern:**
- Fetch the public items endpoint:
  `https://fareharbor.com/api/v1/companies/{shortname}/items/`
- For each kept item, scan monthly calendars:
  `https://fareharbor.com/api/v1/companies/{shortname}/items/{item_pk}/calendar/{yyyy}/{mm}/`
- The previously suspected `minimal/availabilities/date-range` endpoint can 404
  without the right app context; the monthly calendar endpoint is public for
  Firehouse Theater and carries the dated availability rows needed by the scraper.

**Key extraction notes:**
- Each calendar availability becomes one show. `start_at` is a naive local time
  localized with the club timezone; `utc_start_at` is a fallback.
- Adjacent monthly calendars can include spillover days from the previous/next
  month, so the scraper de-duplicates by FareHarbor booking URL.
- Ticket URL comes from `availability.book_url`, resolved against
  `https://fareharbor.com`.
- Price is parsed from item copy such as a Rates/Ticket line; if absent, the
  fallback ticket has unknown price.
- Operational products should be excluded. The scraper has conservative default
  keyword skips for gift cards, donations, classes, workshops, and practice
  items; use `metadata.exclude_item_pks` for venue-specific certainty.

**DB setup:**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
VALUES (
  <club_id>,
  'custom'::"ScrapingPlatform",
  'fareharbor',
  'https://fareharbor.com/embeds/book/<shortname>/',
  0,
  TRUE,
  jsonb_build_object(
    'shortname', '<shortname>',
    'exclude_item_pks', jsonb_build_array(<gift_card_pk>, <donation_pk>, <class_pk>),
    'months_ahead', 12
  )
);
```

**Failure modes / gotchas:**
- Some item/month combinations return HTTP 404 when no public calendar exists;
  treat these as empty and continue.
- Item pages may include non-event retail/service products in the same feed.
- The item list is public and useful for discovery, but dated shows require
  calendar endpoint fan-out per item/month.

**Reference implementation:**
- `apps/scraper/src/laughtrack/scrapers/implementations/api/fareharbor/`
- `apps/scraper/tests/scrapers/implementations/api/fareharbor/test_scraper.py`
- TASK-3167: Firehouse Theater Newport (`shortname=firehousetheater`)

---

### AnyRoad

| | |
|---|---|
| **Scraper key** | `anyroad` |
| **Platform** | `custom` (no `ScrapingPlatform` enum value) |
| **DB field** | `scraping_sources.metadata.plugin_id` (preferred); `source_url` as parse fallback |
| **Value format** | Plugin id, e.g. `rozziesquaretheater`; `source_url` = `https://app.anyroad.com/i/plugin/{plugin_id}` |
| **Generic?** | ✅ DB-only onboarding for any AnyRoad experiences widget |

**Detection signals:**
- Venue page embeds `window.anyroad = new AnyRoad({ plugin: { id: '{plugin_id}' } })`
  loaded from `app.anyroad.com/assets/integration-v1.1.js`.
- The booking widget renders from `https://integrations.anyroad.com/{plugin_id}`
  (a React SPA shell). The Squarespace/CMS host page is often just a wrapper — do
  **not** wire `squarespace` for these venues (its events collection is typically
  an empty placeholder).

**API/source pattern:**
- `AnyRoadScraper` resolves the plugin id (metadata → source_url) and walks
  `GET https://app.anyroad.com/plugins/api/v3/experiences?plugin_id={id}&page=N`,
  page 1.. until an empty `experiences.data[]` (no `links`/`meta` pagination).
- Cloudflare-gated to plain `curl`, but cleared by curl_cffi Chrome impersonation —
  the default `fetch_json` session works directly (Playwright fallback as backstop).
- The list's inline `schedule` carries only a **placeholder** slot time (Rozzie's
  feed reports a uniform `9:00 AM`). The scraper therefore also fetches each
  experience's **booking detail page** (`attributes.url`,
  `app.anyroad.com/i/plugin/{plugin_id}/tours/{slug}?lang=en-US`, also curl_cffi-
  fetchable via `fetch_html`) and parses the embedded
  `"tour_availability":{...,"dates":{"YYYY-MM-DD":{" 6:00pm":<count>}}}` JSON for
  the **real** per-occurrence times and the **full** availability calendar.
- One show is fanned per (date, time) from the detail availability; if a detail
  fetch/parse fails for an experience, it falls back to that experience's list
  `schedule` (placeholder time) rather than being dropped (TASK-3171).

**Key extraction notes:**
- `nameTranslation` → name, `descriptionTranslation` → description,
  `unformattedPrice`/`zeroPriced` → USD ticket price, `url` → show page, `picture`
  → image, availability count > 0 → InStock else SoldOut.
- Detail-page times are lower-case with a leading space (`" 6:00pm"`); the extractor
  upper-cases before parsing (`%I:%M%p` / `%I:%M %p` / `%H:%M`).
- `locationInfo` (sub-venue free text, e.g. `18b Corinth Street`) is mapped onto
  `Show.room`, so experiences at different sub-venues stay distinct under the
  `(club, date, room)` identity key (and the club-page Show Rooms grouping shows a
  real location). With real per-occurrence times now captured, same-date
  experiences no longer collapse (Rozzie: 45 placeholder-collapsed → 103 distinct).

**DB setup:**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom'::"ScrapingPlatform", 'anyroad',
       'https://app.anyroad.com/i/plugin/{plugin_id}',
       0, TRUE, '{"plugin_id": "{plugin_id}"}'::jsonb
  FROM clubs c
 WHERE c.name = '<Venue Name>';
```

**Failure modes / gotchas:**
- A venue's resident companies can share one AnyRoad feed: Rozzie Square Theater's
  feed is the whole building's calendar (CSz Boston + Riot Theater shows included),
  so onboarding the host venue alone covers the trio — do **not** triple-onboard.
- Optional `metadata.comedy_filter` (bool) drops non-comedy experiences via
  `is_comedy_event` for AnyRoad venues that mix in non-comedy bookings; leave unset
  for all-comedy venues.
- Many AnyRoad venues mix ticketed *shows* with multi-week *classes/workshops*; the
  scraper persists all dated experiences (the full ticketed calendar).

**Reference implementation:**
- `apps/scraper/src/laughtrack/scrapers/implementations/anyroad/`
- `apps/scraper/tests/scrapers/implementations/anyroad/test_scraper.py`
- `apps/scraper/scripts/core/onboard_rozzie_square_theater_anyroad_2026_06_22.py`
- TASK-3158: The Rozzie Square Theater (Roslindale, MA)

---

### BrassTix

| | |
|---|---|
| **Scraper key** | `brasstix` |
| **Platform** | `custom` |
| **DB field** | `scraping_sources.source_url` |
| **Value format** | Full calendar URL, e.g. `https://brasstix.com/pmt/calendar.php?Show=DrunkChicago` |
| **Generic?** | ✅ DB-only for BrassTix `calendar.php` pages with inline `eventArray` data |

**Detection signals:**
- Ticket links point to `brasstix.com/pmt/calendar.php?Show=...`
- Page source loads FullCalendar and embeds `eventArray = [...]` / `eventArray.push.apply(...)`
- Event objects include `eventid`, `start`, `url`, and `ShowName` fields

**API/source pattern:**
- The calendar page is server-rendered HTML with inline JavaScript, not JSON-LD.
- `BrassTixScraper` fetches the configured `source_url` and parses each inline event
  object into a `BrassTixEvent`.
- Empty `url` values are sold-out or placeholder events and are skipped.

**Key extraction notes:**
- `title` may contain leading status labels such as `SELLING OUT` or `SOLD OUT`;
  the scraper strips those from the show name and keeps purchasable status text in
  the description.
- `start` is a local naive timestamp (`YYYY-MM-DD HH:MM:SS`) and is interpreted in
  the club's configured timezone.
- BrassTix does not expose structured prices on the calendar entries; tickets are
  persisted with unknown price (`NULL`) and the per-event purchase URL.

**DB setup:**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom'::"ScrapingPlatform", 'brasstix',
       'https://brasstix.com/pmt/calendar.php?Show=DrunkChicago',
       0, TRUE, '{}'::jsonb
  FROM clubs c
 WHERE c.name = 'Drunk Shakespeare Chicago';
```

**Failure modes / gotchas:**
- Some calendars include future placeholder events far outside the normal booking
  window; those generally have empty purchase URLs and are skipped.
- One calendar can include related productions under different `ShowName` values
  at the same venue.

**Reference implementation:**
- `apps/scraper/src/laughtrack/scrapers/implementations/api/brasstix/`
- `apps/scraper/tests/scrapers/implementations/api/brasstix/test_scraper.py`
- TASK-2990: Drunk Shakespeare Chicago

---

### SellingTicket

| | |
|---|---|
| **Scraper key** | `sellingticket` |
| **DB field** | `scraping_url` / `scraping_sources.source_url` |
| **Value format** | Full list URL, e.g. `https://secure.sellingticket.com/design22/clients/list/index_byUserListAll.aspx?OrganizationID=64` |
| **Generic?** | ✅ DB-only onboarding — no Python changes needed |

**Detection signals:**
- Venue website links "Purchase Tickets" to `secure.sellingticket.com`
- The list URL contains `/design22/clients/list/index_byUserListAll.aspx?OrganizationID=<id>`
- The page is a server-rendered table with title, address, date/time, and buy links

**Multi-use venues:** SellingTicket feeds often include films, recitals, concerts, and comedy on one page.
Always configure `metadata.include_title_patterns` for theatres that are not comedy-only:

```sql
INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, priority, enabled, metadata
) VALUES (
    <club_id>,
    'custom'::"ScrapingPlatform",
    'sellingticket',
    'https://secure.sellingticket.com/design22/clients/list/index_byUserListAll.aspx?OrganizationID=<id>',
    0,
    TRUE,
    jsonb_build_object(
        'include_title_patterns',
        jsonb_build_array('comedy', 'comedian', 'comic', '<known comedian name>')
    )
);
```

Use only patterns that are broad enough to catch verified comedy rows but narrow
enough to avoid importing every event from a mixed theatre calendar.

---

### Square Online (Weebly)

| | |
|---|---|
| **Scraper key** | venue-specific (ref: `coral_gables_comedy_club`) |
| **DB field** | `scraping_url` (full products API URL) |
| **Value format** | `https://cdn5.editmysite.com/app/store/api/v28/editor/users/{user_id}/sites/{site_id}/products?product_type=event&visibilities[]=visible&per_page=50&include=images,media_files&excluded_fulfillment=dine_in` |
| **Generic?** | ❌ New venue-specific scraper required |

**Detection signals:**
- `window.__BOOTSTRAP_STATE__` in page source contains `squareMerchantId`
- Network requests to `cdn5.editmysite.com/app/store/api/` or `editmysite.com/app/store/api/`
- `square.online` or `web.squarecdn.com/v1/square.js` script references
- Site built on Weebly/Square Online (check footer or page source for `weebly` references)

**API details:**
- Public storefront API — no auth required
- Returns products with `product_type=event` containing full event details
- Event data is in `product_type_details`: `start_date`, `start_time`, `timezone`, `address`
- Performer names are in the product `name` field (often delimited by " & ")
- Prices are in `price.regular` (in cents)
- Sold-out status in `badges.out_of_stock`
- Ticket URLs are relative (`site_link` field) — prepend the venue domain

**Key non-obvious details:**
1. The `user_id` and `site_id` are visible in the network request URL when the page loads events.
   They can also be found in `__BOOTSTRAP_STATE__` as `properties.classicSiteID` (site_id) and
   in the store API URLs captured via Playwright network inspection.
2. Static HTML contains almost no event data — events are loaded client-side via JS.
   Always use Playwright `browser_network_requests` to discover the API URL.
3. Past events are returned alongside upcoming ones — filter by `start_date >= today`.

**To onboard a new Square Online venue:**
1. Navigate in Playwright → capture `browser_network_requests` → find `editmysite.com/app/store/api/.../products?product_type=event` call
2. Extract `user_id` and `site_id` from the URL path
3. Copy the `coral_gables_comedy_club/` scraper directory as the reference implementation
4. Update the event entity and scraper key for the new venue

---

### Shopify

| | |
|---|---|
| **Scraper key** | `shopify` |
| **DB field** | `scraping_url` |
| **Value format** | Shopify collection page URL (e.g. `https://americancomedyco.com/collections/shows`) |
| **Generic?** | ✅ Yes — new venues need only a DB row, no Python changes |

**Detection signals:**
- Venue sells tickets as Shopify "products" (Add to Cart → Shopify checkout)
- URL path contains `/collections/{handle}` (e.g. `/collections/shows`, `/collections/events`)
- Appending `/products.json` to the collection URL returns a JSON object with a `products` array
- Page source contains `cdn.shopify.com` or `Shopify.theme` references
- Checkout redirects to `{domain}/checkouts/` or `checkout.shopify.com`

**API endpoint:**
```
GET https://{domain}/collections/{handle}/products.json?limit=250
```
Public, no auth required. Returns up to 250 products in a single request — no pagination needed.

**Response structure:**
```json
{
  "products": [
    {
      "id": 123456,
      "title": "Michael Rapaport LIVE! [THU]",
      "handle": "michael-rapaport-live-thu",
      "body_html": "<p>...</p>",
      "images": [{ "src": "https://cdn.shopify.com/..." }],
      "tags": ["comedy", "headliner"],
      "variants": [
        {
          "id": 456789,
          "title": "Thursday April 9 2026 / 8:00pm General Admission",
          "price": "25.00",
          "available": true
        }
      ]
    }
  ]
}
```

**Three date/time parsing formats (tried in order):**

1. **Format A — date in variant title:** Each variant encodes a specific date/time
   (e.g. `"Thursday April 9 2026 / 8:00pm General Admission"`). Multiple variants per
   product → one show per unique (date, time) combo. Lowest price among matching variants.

2. **Format B — date in product title:** Product title contains the date/time
   (e.g. `"Sat Apr 11th @6:30pm - Des Mulrooney, Caleb Synan and Landry"`). Variants
   are ticket tiers only (General Admission, VIP). One show per product.

3. **Format C — date in handle / numeric title (TASK-2949):** No weekday/month-name
   date anywhere; the date lives in the product **handle** (`20260625-capybara-comedy-hour`
   → `YYYYMMDD`, or `6-27-saturday-night-improv-showcase` → `M-D`) and/or a numeric
   `M/D` product title (`"6/26 7pm - Capybara Comedy Hour"`). The **time** comes from the
   title (`"6/26 7pm"`) or from per-showtime variant titles (`"6pm - <act>"`, `"7pm - <act>"`
   → one show per variant time). Month/day prefer the title's `M/D` (the venue's advertised
   date); the year is trusted from a `YYYYMMDD` handle, else inferred from the current year —
   and an inferred date already in the past is **dropped as a stale listing**, not bumped to
   next year (avoids resurrecting past weekly shows as phantoms).

The extractor tries Format A first, then Format B, then Format C.
Products where none match are skipped.

**Non-show filtering:** products whose `tags` contain a word-boundary match for
`class` / `classes` / `merch` / `membership` are excluded (drops classes, workshops,
merch, memberships). Substrings like "classic comedy" / "masterclass" are **not** swept up.

**Onboarding a venue whose shows span multiple collections:** if no single
`/collections/{handle}` holds all the dated shows (e.g. separate `improv-shows` and
`stand-up-comedy-shows` collections), set `scraping_url`/`source_url` to the **base domain**
(`https://www.example.com`) so the scraper fetches `/products.json` (the whole catalog) and
relies on the tag filter + date parsing to keep only real shows. Improv School Redlands
(club 8878, source 5904) is onboarded this way.

**Comedian name extraction:**
- Format A: Cleaned from product title (strips "LIVE!", day markers like "[THU]", parenthetical notes)
- Format B: Text after the ` - ` separator in the product title

**Key implementation details:**
- Ticket URL constructed from `scraping_url` domain + product `handle`:
  `https://{domain}/products/{handle}`
- Price: lowest among applicable variants (in dollars, e.g. `"25.00"`)
- Availability: `true` if any matching variant is available
- Timezone: uses `club.timezone` from DB; defaults to `America/Los_Angeles`
- No pagination — `limit=250` covers all products in a single request

**DB setup:**
```sql
UPDATE clubs
SET scraper = 'shopify',
    scraping_url = 'https://example.com/collections/shows'
WHERE name = 'My Comedy Club';
```
The scraper appends `/products.json?limit=250` at runtime — store only the collection page URL.

**Reference implementation:** `american_comedy_co/`

**To onboard a new Shopify venue:**
1. Confirm the venue uses Shopify — check for `/collections/` URL and `products.json` API
2. Find the correct collection handle (usually `shows` or `events`)
3. Verify the API returns data: `curl 'https://{domain}/collections/{handle}/products.json?limit=1' | python3 -m json.tool`
4. Insert/update the DB row with `scraper='shopify'` and `scraping_url` pointing to the collection page
5. Run `make scrape-club CLUB='<name>'` from `apps/scraper/` to verify

**Troubleshooting:**
- **0 events but products exist:** Check that variant or product titles match one of the two date formats.
  Custom title formats require extending the regex patterns in `ShopifyExtractor`.
- **403 or empty response:** Some Shopify stores restrict the JSON API by region or bot detection.
  Test with the scraper's Playwright browser fallback if `fetch_json` fails.

### Stand-Up NY (standup_ny)

Events come from the VenuePilot GraphQL feed (accountIds `[2535]` via
`venuepilot.co/graphql`; `api.showtix4u.com` is a dead fallback). Ticket price
enhancement is dispatched by `ticketsUrl` host (TASK-2836):

- **tickets.venuepilot.com** — fetch the page and read the pinia state
  (`checkout.tickets[].breakdown.price`). As of May 2026 only free open mics
  use this path.
- **square.link** — the venue moved paid checkout to Square payment links
  (~May 2026). The link redirects to `checkout.square.site` whose embedded JSON
  carries per-tier `"price_money":{"amount":<cents>}`; the scraper takes the
  lowest positive tier. Fixture:
  `tests/scrapers/implementations/venues/standup_ny/fixtures/`.
- Other hosts (eventbrite, venue sites) get the priceless fallback ticket.

If prices vanish again, re-check the `ticketsUrl` host distribution first — the
venue has switched checkout platforms before.

---

### BookTix

`scraper_key = booktix`, `platform = custom` (BookTix has no dedicated
`ScrapingPlatform` enum value). Generic, serves any venue with a BookTix box
office at `https://{org}.booktix.com`. Two-step, **static HTML** (no JSON-LD, no
public JSON API, no JS rendering needed — curl_cffi suffices):

1. **Discovery** — the box office home `https://{org}.booktix.com/dept/main`
   lists each production as `/dept/main/e/{code}` links. `source_url` = that home
   URL. `extract_event_urls` regexes the codes (deduped) into production-page URLs.
2. **Detail** — each production page (`/dept/main/e/{code}`) is server-rendered:
   - **name**: the `<h3 class="text-2xl font-bold ...">` heading
   - **showtimes**: text like `Sat Jun 20 2026 - 7:00 PM` (a production page lists
     ALL its showtimes — one `Show` per showtime)
   - **price**: the `$N` token (lowest on the page = GA)

Production pages include **past** showtimes of a multi-weekend run, so
`BookTixEvent.to_show` filters showtimes earlier than now (there is no global
past-show filter). Onboarded: Makeshift Theater Akron (`makeshift.booktix.com`).

### Tix.com (`tix_com`)

`scraper_key = tix_com`, `platform = custom` (Tix.com has no dedicated
`ScrapingPlatform` enum value). Generic, serves any venue selling through Tix.com.
The public storefront `https://www.tix.com/ticket-sales/<slug>/<org_id>` is a
React SPA, but its on-sale events come from an **anonymous JSON API** (no auth, no
JS rendering — curl_cffi suffices):

  `https://www.tix.com/api_ots/onlinesales/events/organization/<org_id>`

- `source_url` (`scraping_url`) = the public storefront URL
  (e.g. `https://www.tix.com/ticket-sales/playhouseonpark/2704`). The scraper
  regexes the trailing numeric `<org_id>` (`2704`) out of it and builds the API URL.
- Response shape: `{payload: {groupedEvents: [[event, ...], ...]}}`. Each event has
  `EventId`, `ProductionName` (title), `EventDate` (naive local ISO), `MinPrice`
  (0 / `SuppressPrices` → price-unknown), `Category`/`SubCategory`, and venue fields.
- `show_page_url` = `<source_url>/event/<EventId>`.
- **Mixed-use venues** (community theaters running a recurring comedy series among
  musicals/plays) set `metadata.comedy_filter=true` to isolate comedy (same
  mechanism as etix/seatengine/academy_of_music). Onboarded: Playhouse on Park
  (`playhouseonpark/2704`, West Hartford CT) — note its Comedy Nights series is
  seasonal, so the feed has 0 comedy between seasons.

### Tessitura (WordPress REST integration)

`scraper_key = tessitura`, `platform = custom` (Tessitura has no dedicated
`ScrapingPlatform` enum value). Generic, serves Tessitura venue operators that
run the WordPress integration plugin which mirrors Tessitura productions into
`tessi_production` / `tessi_performance` custom post types.

**Spike finding (TASK-2924) — the box office is NOT the scrapable seam.** The
Tessitura box office itself (`tickets.{org}.com`) is bot/queue protected:
`tickets.capa.com/online/` 302-redirects into a **Queue-It** virtual waiting
room, and `tickets.playhousesquare.org/online/` returns **403**. There is no
usable public Tessitura ticketing JSON. The scrapable seam is instead the
operator's **WordPress site** (e.g. `www.capa.com`), which exposes the same
productions over the standard WP REST API.

`source_url` = the operator site root (e.g. `https://www.capa.com`); the scraper
derives `/wp-json/wp/v2` from it. Single API pass (no JS rendering — curl_cffi /
`fetch_json` suffices):

1. **Genre discovery** — `GET /wp-json/wp/v2/genre?per_page=100`; pick the term
   whose name matches "comedy" (case-insensitive, substring) with a non-zero
   `count`. CAPA: `Comedy` = id 71.
2. **Productions** — page through
   `GET /wp-json/wp/v2/tessi_production?genre={id}&per_page=100` (server-side
   genre filter = clean comedy slate, no per-show classification needed).
   - **title**: `title.rendered`
   - **showtime**: parsed from `content.rendered`, e.g.
     `Saturday, December 5, 2026 | 7 PM` (bare-hour and `7:30 PM` forms)
   - **venue/room**: the `VENUE … Plan Your Visit` block → `Show.room`
   - **ticket url**: the first `https://tickets.{org}.com/{prod}/{perf}/` link in
     `content.rendered`; falls back to the production page URL
   - **show page url**: the production `link` (drives traffic to the operator site)

`TessituraEvent.to_show` filters past showtimes (the genre feed includes
archived productions). Optional `scraping_sources.metadata` overrides:
`post_type` (default `tessi_production`), `genre_taxonomy` (default `genre`),
`comedy_genre_names` (comma-separated, default `comedy`).

Onboarded: **CAPA — Columbus Association for the Performing Arts** (`www.capa.com`),
modeled as ONE operator club (Ohio / Palace / Southern / Lincoln theatres + the
Davidson at the Riffe Center are carried in `Show.room`). Verified 18 future
comedy shows live (Whitney Cummings, Gary Gulman, Jo Koy, Daniel Sloss, …).

**Not on this seam:** Playhouse Square (Cleveland) is also a Tessitura operator
but its marketing site (`playhousesquare.org/events`) is **not** WordPress — it
is a custom CMS with no comedy genre tag, and its box office 403s. It has its own
dedicated `playhouse_square` scraper (see below), not this `tessitura` (WordPress)
scraper.

### Tessitura TNEW (production-seasons API)

| | |
|---|---|
| **Scraper key** | `tessitura_tnew` |
| **Platform** | `custom` |
| **DB field** | `scraping_sources.source_url` + optional `metadata.events_url` / `metadata.api_url` |
| **Value format** | TNEW listing page, usually `https://{boxoffice-host}/events?view=list` |
| **Generic?** | ✅ generic for TNEW storefront event-listing pages |

**Detection signals:**
- Box office host serves TNEW assets from `production.tnew-assets.com`.
- Listing page declares `listingStartDate`, `listingEndDate`, and
  `additionalApiData` in inline JS.
- Browser network shows `POST /api/products/productionseasons` with
  `content-type: application/x-www-form-urlencoded` and a
  `RequestVerificationToken` header.

**API/source pattern:**
- Prime the listing page (`source_url`) first. This establishes Incapsula /
  ASP.NET cookies and exposes the hidden `__RequestVerificationToken`.
- POST `{origin}/api/products/productionseasons` form data:
  `keywordIds=&startDate=<local-start>&endDate=<local-end>`.
- The empty `productionSeasonIdFilter: []` from page config serializes to no
  form field. Sending JSON or guessing array fields can produce HTTP 500.

**Key extraction notes:**
- Response root is a list of productions. Each production contains a
  `performances` array; create one show per performance.
- Prefer `performanceDate` because it carries the timezone offset; fall back to
  `iso8601DateString` localized with the club timezone.
- Title comes from `performanceTitle`, then `performanceSortTitle`, then the
  production title. Ticket/show URL is `performance.actionUrl`.
- Prices are not exposed on the list API; use a fallback ticket URL.

**DB setup:**
```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
VALUES (
    <club_id>, 'custom'::"ScrapingPlatform", 'tessitura_tnew',
    'https://purchase.example.com/events?view=list', 0, TRUE,
    '{"events_url":"https://purchase.example.com/events?view=list","api_url":"https://purchase.example.com/api/products/productionseasons"}'::jsonb
);
```

**Failure modes / gotchas:**
- Use the scraper HTTP stack. Plain `requests` can fail on the Incapsula-protected
  listing page and does not prove the scraper cannot fetch it.
- TNEW's browser form request is token-bearing even when no explicit anti-CSRF
  field is obvious in task notes; replay the hidden input as
  `RequestVerificationToken`.
- The form date range should use venue-local offsets. The listing end date is
  sent as end-of-day (`23:59:59`), not midnight.

**Reference implementation:**
- `apps/scraper/src/laughtrack/scrapers/implementations/api/tessitura_tnew/`
- `apps/scraper/src/laughtrack/core/entities/event/tessitura_tnew.py`
- Onboarded: The Groundlings Theatre & School (`purchase.groundlings.com`, org
  `GTAS`, TASK-2946).

### EventON (WordPress admin-ajax loader)

`scraper_key = eventon`, `platform = custom` (EventON has no dedicated
`ScrapingPlatform` enum value). Generic, serves venues running the EventON
WordPress events-calendar plugin (custom post type `ajde_events`).

**Spike finding (TASK-2926) — REST has no dates; the admin-ajax loader does.**
EventON keeps event start times in unexposed post meta (`evcal_srow`), so
`/wp-json/wp/v2/ajde_events` lists every event (id/title/link) but with **empty
meta** — no dates. `/wp-json/eventon/v1/data` 404s, `/events/` is AJAX-rendered
(no JSON-LD in initial HTML), and the homepage exposes only a 4-event rolling
JSON-LD widget. The scrapable seam is the frontend calendar loader:

1. **Loader (POST, required)** — `POST {root}/wp-admin/admin-ajax.php` with
   `action=eventon_init_load` and the **full default shortcode (`sc`) param set**
   serialized as `cals[<cal_id>][sc][<key>]=<value>` (see `extractor._DEFAULT_SC`;
   key tunables `event_past_future=future`, `hide_past=yes`, `event_count=300`,
   `number_of_months=12`). A *minimal* param set returns an empty `cals`, and GET
   returns empty — it must be POST with the full set. No nonce required. The
   response carries upcoming events under `cals.<cal_id>.json` as objects with
   `event_id`, `event_title`, and `event_start_unix`. Sent via `post_form`
   (curl_cffi), which clears the site's ModSecurity (plain curl → 406).
2. **Permalink + taxonomy join** — the loader payload has no per-event URLs or
   taxonomy, so `GET {root}/wp-json/wp/v2/ajde_events?include=<ids>&per_page=100&_fields=id,link,event_type`
   maps each `event_id` → `{link, event_type[term_ids]}`.
3. **Comedy filter** — `metadata.event_type_filter` (comma-separated names,
   e.g. `comedy`) discovers the matching `event_type` term id from
   `{root}/wp-json/wp/v2/event_type` (by name/slug) and keeps only events tagged
   with it. Omit to import all events. Use it for venues that host comedy
   *alongside* other programming.

**Timezone:** `event_start_unix` is the local wall-clock encoded as a UTC unix
timestamp — format it in UTC to read the wall-clock components, then localize to
the club timezone (`EventONEvent` does this; a 7 PM show stores as `…T19:00Z`).

`source_url` = the WordPress site root (e.g. `https://jillysmusicroom.com`).
Optional `metadata`: `cal_id` (default `MAIN`), `event_type_filter`. Onboarded:
**Jilly's Music Room** (Akron; `event_type_filter='comedy'` — verified 1 upcoming
comedy show out of 58 future events).

### AXS-skinned venue homepage (`axs`)

`scraper_key = axs`, `platform = custom` (AXS has no dedicated `ScrapingPlatform`
enum value). Generic, serves AXS/AEG venues that run the stock venue website
(royalSlider event slider) and link tickets to
`axs.com/events/<id>/...?skin=<venue>`.

**Spike finding (TASK-2929) — scrape the venue homepage, NOT axs.com.** The
`axs.com` event detail pages are DataDome-protected (403), but the venue's own
homepage is plain server-rendered HTML carrying the full event list. Parse the
`div.rsCaption` cards:
- **name**: `<h3><a href="<venue>/events/detail/<id>">NAME</a></h3>`
- **date**: a following `<h4>Tue, Jun 16, 2026</h4>` (`%a, %b %d, %Y`) — **date
  only, no time**
- **room**: `<h4 class="event_venue">`
- **ticket url**: `<a class="tickets" href="axs.com/events/<id>/...?skin=<venue>">`

`source_url` = the venue homepage. The homepage carries no show time, so each
Show uses `metadata.default_show_time` (`HH:MM`, default `19:00`) localized to
the club timezone. `show_page_url` is the venue detail page (drives traffic to
the venue); the ticket link is the AXS URL.

**No comedy filter — import-all.** The homepage has no genre/category tag, so the
scraper imports **every** event. There is no downstream comedy-relevance gate, so
only wire this scraper for venues whose programming is comedy-dedicated (or
accept concert noise). **Agora Theater (Cleveland)** was the originating venue
but was intentionally **NOT wired** (TASK-2929): it is a mostly-concerts venue
already carrying a `ticketmaster_comedy` source, and the all-events AXS import
would flood the comedy DB. The scraper is verified against Agora's homepage (19
live shows incl. comedy) and ready for comedy-dedicated AXS-skinned venues.

### Pabst Theater Group venue page (`pabst_axs`)

`scraper_key = pabst_axs`, `platform = custom`. **Pabst-group-specific, not the
generic `axs` scraper.** The Pabst Theater Group (pabsttheater.org) runs one
shared venue-page template across its rooms (Pabst Theater, Riverside Theater,
Turner Hall, …), all ticketed via AXS (`axs.com/events/<id>/...?skin=pabst`). The
generic `axs` scraper expects an AXS-skinned homepage with `rsCaption` slider
cards and returns 0 against this template — the Pabst pages use a different
`div.eventItem` card layout, carry **no** JSON-LD events (only `Organization`),
and the date lives in the thumbnail filename rather than a text node.

**Datasource (TASK-3033) — scrape the venue page, NOT axs.com.** The `axs.com`
detail pages are DataDome-protected; the venue page is plain server-rendered HTML
(plain curl gets 406 — use curl_cffi chrome impersonation, which `fetch_html`
does by default). Parse the `div.eventItem` cards:
- **name**: the `title` attribute of the info/ticket link — `More Info for <NAME>`
  (preferred) or `Buy Tickets for <NAME>` (the prefix is stripped)
- **date**: embedded in the thumbnail filename
  `<img src=".../assets/img/YYYY.MM.DD-<...>.png">` — **date only, no time**.
  Cards with no dated thumbnail (e.g. a TBA show) are skipped.
- **ticket url**: `<a href="axs.com/events/<id>/<slug>-tickets?skin=pabst">`
- **show_page_url**: the venue's own `…/events/detail/…` "More Info" link (drives
  traffic to the venue), falling back to the AXS ticket URL

`source_url` = the room's venue page (e.g.
`https://pabsttheater.org/venues/the-riverside-theater/`). The page carries no
show time, so each Show uses `metadata.default_show_time` (`HH:MM`, default
`19:00`) localized to the club timezone (Pabst rooms are `America/Chicago`).

**Comedy filter — mixed-use venue.** Each room is music-dominated (~5–7 comedy
acts among ~20 events), so wire the shared comedy filter via
`metadata.comedy_filter: true`. It keeps a title when it carries a comedy keyword
(`is_comedy_event`), names a known comedian above `metadata.min_comedian_popularity`
(default 0.30), **or** matches a per-source `metadata.comedy_title_allowlist`
substring. The allowlist is the escape hatch for comedian-name acts the keyword
filter misses (e.g. `"ben schwartz"`, `"anthony jeselnik"`, `"wait wait"` for
the NPR show, the Hasan Minhaj / Ronny Chieng wordplay title).

**Onboarding another Pabst-group room:** insert a `clubs` row + a
`scraping_sources` row (`scraper_key=pabst_axs`, `source_url`=the room's venue
page, `metadata` with `default_show_time` + `comedy_filter` +
`comedy_title_allowlist`) via an idempotent migration keyed on `google_place_id`.
See `migrations/20260620_onboard_riverside_theater_pabst_axs.sql` for the
template. Onboarded (all Milwaukee): **The Riverside Theater** (TASK-3033;
verified 7 dated comedy shows among 23 events), **Pabst Theater** (TASK-3035;
migrated off `ticketmaster_comedy`, 5 comedy shows), and **Turner Hall Ballroom**
(TASK-3035; 3 comedy shows).

### AEG/Goldenvoice Carbonhouse venue page (`aeg_axs`)

`scraper_key = aeg_axs`, `platform = custom`. **AEG-Carbonhouse-template-specific,
not the generic `axs` scraper.** Many AEG Presents / Goldenvoice venues (The
Warfield, The Regency Ballroom, Social Hall SF, …) run one shared
**Carbonhouse** venue-site template (`generatorAgent rdf:resource="http://carbonhouse.com/"`),
all ticketed via AXS (`axs.com/events/<id>/...?skin=<venue>`). The generic `axs`
scraper expects an `rsCaption` homepage slider and `pabst_axs` expects
`div.eventItem` cards; this template returns 0 against both — it lists shows as
`div.entry` cards on the venue's own `/events` page.

**Datasource (TASK-3209) — scrape the venue `/events` page, NOT axs.com.** The
`axs.com` detail pages are DataDome-protected; the venue `/events` page is plain
server-rendered HTML (curl_cffi chrome impersonation, which `fetch_html` does by
default). Parse the `div.entry` cards:
- **name**: `<h3 class="carousel_item_title_small"><a href="<venue>/events/detail/<id>">NAME</a></h3>`
- **date**: `<span class="date">Wed, Jun 24, 2026</span>` (`%a, %b %d, %Y`)
- **time**: `<span class="time">Show 8:00 PM</span>` — **a real show time**
  (unlike the date-only `axs`/`pabst_axs` templates); `default_show_time` is only
  a fallback for cards with no parseable time
- **ticket url**: `<a ... href="axs.com/events/<id>/...?skin=<venue>">`
- **show_page_url**: the venue's own `/events/detail/<id>` link (drives traffic to
  the venue), falling back to the AXS ticket URL

`source_url` = the venue `/events` page (e.g.
`https://www.thewarfieldtheatre.com/events`).

**Comedy filter — mixed-use concert venue.** These rooms are concert-dominated
(The Warfield: 19 of 20 upcoming shows are music), so wire the shared comedy
filter via `metadata.comedy_filter: true`. It keeps a title when it carries a
comedy keyword (`is_comedy_event`), names a known comedian above
`metadata.min_comedian_popularity` (default 0.30), **or** matches a per-source
`metadata.comedy_title_allowlist` substring. The allowlist is the escape hatch for
comedian-name acts the keyword filter misses whose stored popularity is below the
floor (e.g. `"kevin langue"` — popularity 0.188).

**Onboarding another AEG/Goldenvoice Carbonhouse room:** insert a `clubs` row + a
`scraping_sources` row (`scraper_key=aeg_axs`, `source_url`=the venue `/events`
page, `metadata` with `comedy_filter` + `comedy_title_allowlist`; add
`default_show_time` only for a venue whose cards omit a parseable `span.time` —
the Warfield's always carry one, so its metadata sets none) via an idempotent
migration keyed on `google_place_id`. See
`apps/web/prisma/migrations/20260623220000_onboard_warfield_aeg_axs/migration.sql`
for the template. Onboarded: **The Warfield** (San Francisco; TASK-3209; verified
1 comedy show — "The Kevin Langue Show: Live!" — kept among 20 events).

### NeonCRM / Neon One (`neoncrm`)

`scraper_key = neoncrm`, `platform = custom` (NeonCRM has no dedicated
`ScrapingPlatform` enum value). Generic, serves venues hosted on a NeonCRM
(Neon One) org.

**Datasource (TASK-2939):** the public event list at
`https://{org}.app.neoncrm.com/eventList.jsp?categoryId={N}` (canonical
`/np/clients/{org}/eventList.jsp`) is static server-rendered HTML — curl_cffi
chrome impersonation suffices. Each row is a `div.neoncrm-event-list-event` with:
- **name + detail URL**: `<h2 class="neoncrm-event-name"><a href="...event.jsp?event={id}">NAME</a></h2>`
- **date range**: `<div class="neoncrm-event-date">MM/DD/YYYY HH:MM PM - MM/DD/YYYY HH:MM PM ET</div>`
  — the scraper takes the range **start** as the show datetime (`%m/%d/%Y %I:%M %p`, localized to the club tz).

`show_page_url` = the absolute `event.jsp?event={id}` detail page; the list page
alone yields name + date + url (no per-event fetch needed).

**Config via `scraping_sources.metadata`:** `neon_org` (org slug) +
`category_ids` (list). When present the scraper builds one eventList URL per
category id; otherwise it falls back to the verbatim `scraping_url`. Use the
category filter to scope to the comedy-bearing category — NeonCRM categories mix
camps/classes/cinema with performances, so pick the venue's "Theater
Productions"-style category (it carries improv / stand-up / plays).

Onboarded: **Oglebay Institute Towngate Theatre** (Wheeling WV;
`neon_org=oionline`, `category_ids=[27]` Theater Productions — resident improv
troupes Left of Centre Players / Crazy 8s; verified 3 upcoming productions,
comedy/improv appear seasonally under the same category).

### Playhouse Square — Cleveland (`playhouse_square`)

`scraper_key = playhouse_square`, `platform = custom` (no dedicated
`ScrapingPlatform` enum value). **Venue-specific, not generic** — it targets the
carbonhouse "showtime" CMS that Playhouse Square runs. PHS is a Tessitura
operator but is NOT on the WordPress `tessi_production` seam (see the Tessitura
section), so it cannot use the `tessitura` scraper.

**Datasource (TASK-2942) — the load-more AJAX feed.** `playhousesquare.org/events`
server-renders only a curated subset behind a JS "Load More Events" button. The
full upcoming list is the button's AJAX feed:

```
GET {origin}/events/events_ajax/0?per_page=N&category=0&venue=0&team=0&came_from_page=event-list-page
```

- Requires curl_cffi's **default Chrome impersonation** — plain requests get a
  `406` from the WAF (the same 406 that blocks `/events/category/comedy`).
- The response is a **JSON-encoded string of HTML** (the same `m-eventItem` cards
  the page renders). `fetch_json` returns the decoded HTML string, which the
  extractor parses. `per_page=500` returns the whole feed in one fetch.

Per `div.m-eventItem` card:
- **name + detail URL**: `<h3 class="m-eventItem__title"><a href="/events/detail/<slug>">NAME</a></h3>`
- **date**: `<div class="m-eventItem__date">` as a single date
  (`m-date__singleDate`) or a range (`m-date__rangeFirst`/`m-date__rangeLast`) —
  **date only, no time**; the scraper takes the range START and combines it with
  `metadata.default_show_time` (`HH:MM`, default `19:00`) localized to the club tz.
  Months render mixed full ("June") and abbreviated ("Oct").
- **venue**: `<span class="venue_title">` (e.g. "Mimi Ohio Theatre") — PHS is a
  multi-theatre complex; this is how each source is scoped to one theatre.
- **ticket url**: `<a class="tickets" href="tickets.playhousesquare.org/...">` (the
  Tessitura box office). `show_page_url` is the venue's own `/events/detail/`
  page (drives traffic to the venue).

Cards whose title is prefixed `(Canceled)` are dropped.

**Comedy isolation — known-comedian heuristic (no genre tag anywhere).** Neither
the markup class tokens (`on_stage`/`home`/`Tri-CJazzFest`/…) nor the detail
pages carry a comedy/genre signal (the only "comedy" string is boilerplate meta
text). Since there is no downstream comedy-relevance gate, the scraper isolates
comedy itself (`comedy_filter.py`): keep an event only when its title contains a
credible whole-name match to a known comedian (the lineup-enrichment credibility
check) AND that comedian's STORED popularity clears
`metadata.min_comedian_popularity` (default `0.30`). The popularity floor drops
data-quality false positives — e.g. a junk "The Nutcracker" comedian row (ballet)
or a miscategorised "Professor Brian Cox" (science lecture), which score < 0.20,
vs. real touring acts at >= 0.40.

**Per-source `scraping_sources.metadata`:** `venue_titles` (REQUIRED — list of
feed `venue_title` strings this source covers; without it the source emits
nothing rather than the whole multi-venue feed), `per_page` (default 500),
`min_comedian_popularity` (default 0.30), `default_show_time` (default 19:00),
`comedy_title_allowlist` (optional — see below).
`source_url` = `https://www.playhousesquare.org/events` (origin is derived from it).

**`comedy_title_allowlist` — curated escape hatch (TASK-2943).** The known-comedian
name heuristic misses real comedy whose title contains no single matched full
name: multi-comedian bills (`HASAN HATES RONNY | RONNY HATES HASAN` = Hasan Minhaj
+ Ronny Chieng) and variety shows (`The Uncle Louie Variety Show`). Add the
title (or a distinctive substring, matched case-insensitively) to
`metadata.comedy_title_allowlist` and that title is force-included as comedy,
bypassing the heuristic. Because it is an explicit per-source opt-in it carries
no false-positive risk to other venues — a broader first-name-matching heuristic
was deliberately **deferred** for exactly that risk (common first names would
admit non-comedy events). Applied: Connor Palace (5058) carries
`["HASAN HATES RONNY"]`.

**Unwired-theatre coverage audit (2026-06-18, TASK-2943).** The full PHS feed
(78 events) was audited for comedy at theatres with no `playhouse_square` source.
The non-wired theatres (Hanna, Allen, Outcalt, E.J. Thomas, the Plaza, etc.) host
**no name-comedian stand-up** — only musicals, plays, dance, jazz, and magic. The
sole comedy-adjacent event is `The Uncle Louie Variety Show` at **Hanna Theatre**
(one borderline variety show). Wiring a dedicated Hanna club for a single event
was judged not worth it; if Hanna starts hosting recurring comedy, create the club
and add a `playhouse_square` source with `venue_titles=["Hanna Theatre"]` (and a
`comedy_title_allowlist` entry for the variety show if desired).

**Wiring — per theatre, preferred over the aggregator.** Comedy at PHS spans
multiple theatres, so one `playhouse_square` source is wired per comedy theatre
at **priority 0**, with the venue's existing `ticketmaster_comedy` source demoted
to priority 1 (kept as a fallback) — per project policy to prefer the venue's own
site over aggregators. Onboarded (TASK-2942): **Connor Palace** (club 5058),
**Mimi Ohio Theatre** (club 5394), **KeyBank State Theatre** (club 8901, created
during onboarding). Verified 10 upcoming comedy shows live across the three
(Nikki Glaser, Leanne Morgan, Kill Tony, Marc Maron, Zarna Garg, Daniel Sloss,
Rickey Smiley, Jo Koy, Ron White). The duplicate PHS venue clubs were merged
first (`dedupe_playhouse_square_clubs_2026_06_17.py`: 5071→5058, 5338/5392→5394).

### WooCommerce Store API

| | |
|---|---|
| **Scraper key** | `woocommerce_store_api` |
| **Platform** | `custom` |
| **DB field** | `source_url` (site root or the products endpoint) |
| **Generic?** | ✅ Generic — serves any WordPress + WooCommerce venue selling shows as products |

**Detection signals:**
- WordPress + WooCommerce site (`/wp-json/` reachable; footer/assets reference WooCommerce)
- `GET {site}/wp-json/wc/store/v1/products?per_page=100` returns a JSON **array** (HTTP 200)
- Products carry attributes "Show Dates" (MM/DD/YYYY) + "Show Times" and a `permalink`
- JSON-LD is `@type: Product` (not `Event`); `tribe_events` 404s

**Key implementation details:**
- Products are filtered to the comedy category (default `Comedy Events`; matched against each product's category name or slug)
- Each product fans out into one show per **(Show Date × Show Time)** — comedy clubs run uniform showtimes across a run, so the cartesian product is correct. A venue with genuinely per-date times would over-generate; revisit then.
- `permalink` is both the show URL and the ticket purchase URL; price comes from `prices.price` interpreted in `currency_minor_unit` (cents)
- Product names are HTML-unescaped; "Show Times" accept compact (`6:30pm`) and spaced (`6:30 pm`) meridiem forms

**Onboarding:**
1. Insert a `scraping_sources` row: `platform='custom'`, `scraper_key='woocommerce_store_api'`, `source_url=<site root or products endpoint>`, `enabled=true`. The scraper appends `/wp-json/wc/store/v1/products` and enforces `per_page=100` if the path is just the site root.
2. **Verify `clubs.timezone` is set** — a NULL timezone defaults to `America/New_York` and ships showtimes 1-3h off for non-Eastern venues (set it from the venue city/state).
3. `make scrape-club-id ID=<club>` and confirm N>0 shows before flipping `visible=true`.

First venue: Grand Comedy Club & Pizzeria (club 8897, grandcomedyclub.com).

---

## Implementation Patterns

### Playwright Network Inspection for JS-Heavy Sites

When a venue's show listing is powered by a JavaScript widget (e.g., embedded Crowdwork, SeatGeek, or Tixr), WebFetch may return misleading results (403, missing API calls, or JS-shell content). Use Playwright browser navigation + `browser_network_requests` instead:

1. Navigate to the venue homepage: `browser_navigate`
2. Wait 2–3 seconds for JS to execute: `browser_wait_for time: 3`
3. Capture: `browser_network_requests (includeStatic: false)`
4. Look for non-static, non-analytics API calls — the show-data API is usually a GET to a JSON endpoint

This pattern discovered the PHIT Crowdwork API: `https://crowdwork.com/api/v2/{theatre}/shows`

---

### JS-Rendered Pages Returning HTTP 200 with Shell Content

When a ticketing page returns HTTP 200 but only a JavaScript shell, `BaseScraper.fetch_html()` will NOT trigger the automatic Playwright fallback (that only activates on 403 / empty response / bot-block signatures). The scraper will silently extract zero events.

**Identification:** curl_cffi returns 200 with a large HTML payload (~100–200KB) but BeautifulSoup finds no event containers. Playwright shows event rows populated after DOMContentLoaded — injected by JS.

**Implementation pattern:** override `get_data()` and use the shared `_get_js_browser()` singleton — never instantiate `PlaywrightBrowser()` directly (it leaks a Chromium process per call):

```python
async def _fetch_html_with_js(self, url: str) -> Optional[str]:
    try:
        from laughtrack.foundation.infrastructure.http.client import _get_js_browser
        browser = _get_js_browser()
        if browser is None:
            return None
        return await browser.fetch_html(url)
    except Exception as e:
        Logger.warn(f"MyScraper: Playwright fetch failed for {url}: {e}")
        return None
```

`PlaywrightBrowser` uses `wait_until='domcontentloaded'`. Only use `networkidle` if events are loaded via a post-DOMContentLoaded XHR.

---

### curl_cffi + DataDome — Header Fingerprint Debugging

When a curl_cffi request with `impersonate='chrome124'` succeeds with no custom headers but returns 403 with application headers, DataDome is detecting a specific header combination (never a single header — commonly `Accept-Language + Cache-Control + Pragma` together).

**Diagnostic approach:**
1. Test with no headers → confirm 200
2. Binary search: split your header dict in half and test each half
3. Narrow down to the triggering combo (usually 2–3 headers)

**Fix pattern:** bypass `BaseApiClient.fetch_html` (which always sends `self.headers`) and use a bare `AsyncSession.get(url)`:
```python
async with AsyncSession(impersonate=self._get_impersonation_target(url)) as session:
    response = await session.get(url)  # no extra headers
```
Note: `BaseApiClient.fetch_html(headers=None)` falls back to `self.headers` — passing `None` or `{}` still sends API headers. A separate fetch method is needed to send zero application headers.

---

### Multi-Location Venues — Generalizing Extractor Regexes

When reusing an existing scraper for a second venue location (e.g., Comedy Store La Jolla reusing `comedy_store`), check the extractor's URL pattern regexes for hard-coded path prefixes that may differ between locations.

For example, `^/calendar/show/\d+/(.+)$` only matches West Hollywood hrefs — it must be generalized to `^(?:/[^/]+)?/calendar/show/\d+/(.+)$` before it can handle `/la-jolla/calendar/show/...`.

Before implementing a second location, fetch one day's HTML from the new location and verify every regex in the extractor matches the new URL structure.

---

### Comedy Store — ShowClix/Leap ticket pricing (TASK-2841)

The calendar day pages render no price element. The `comedy_store` scraper
resolves each distinct slug-style ticket page once per run (memoized,
failure-evicting, 10-request cap) to the numeric ShowClix id embedded in an
inline script — `var EVENT = {"event_id":"10341917", ...}` — then fetches
per-level prices via the same `ShowclixAPIClient.get_event_data` seated API
the Gotham scraper uses, taking `get_primary_price()` (0.00 levels are
placeholder/comp tiers and stay `None`).

**Leap host migration gotcha:** ShowClix migrated venue ticket hrefs from
`www.showclix.com/event/<slug>` to `events.leapevents.com/event/<slug>`
(observed live 2026-06-12). The extractor's anchor pattern
(`SHOWCLIX_EVENT_URL_RE`, shared with the scraper's enrichment eligibility
check) must match **both** hosts — when it only matched showclix.com, every
ticketed show's `ticket_url` silently degraded to the venue show page. If
Comedy Store prices/ticket links vanish again, re-check the calendar's anchor
host first.

---

### ShowSlinger

| | |
|---|---|
| **Scraper key** | `show_slinger` |
| **DB field** | `scraping_url` |
| **Value format** | Full combo widget URL: `https://app.showslinger.com/promo_widget_v3/combo_widget?id=<venue_id>&secure_code=<code>&origin_url=<club_website_url>` |
| **Generic?** | ✅ Already generic — no code needed for new venues (uses `the_comedy_shoppe` implementation) |

**Detection signals:**
- Buy links pointing to `app.showslinger.com/ticket_payment/...`
- Widget embed `<script>` tag referencing `showslinger.com` on the venue page
- "Powered by ShowSlinger" footer text

**⚠️ The `origin_url` parameter is REQUIRED.** Without it, the ShowSlinger widget returns a Cloudflare 403. The `origin_url` must match the club's actual website URL (the page where the widget is embedded).

**Finding the widget parameters:**
1. View the club's calendar/events page source
2. Look for a `<script>` or `<iframe>` embed referencing `app.showslinger.com`
3. Extract three parameters from the embed URL:
   - `id` — the venue's numeric ID (e.g., `238`)
   - `secure_code` — alphanumeric code (e.g., `ec8183215e`)
   - `origin_url` — the club's website URL where the widget is embedded

**HTML structure:** The widget is server-rendered (no JS execution needed). Events are in `div.signUP-admin` cards with:
- `h4.widget-name` — event title
- `span.widget-time` — showtime (two formats: full date "Sat, May 2, 3:00 pm" or time-only "7:30 PM" with date from `.widget-date-month` badge)
- `a.mrk_ticket_event_url` — ticket link (href contains `/ticket_payment/<id>`)
- `img.grid-img` — event image
- `.widget-price` / `.price` — ticket price

**DB setup:**
```sql
UPDATE clubs
SET scraper = 'show_slinger',
    scraping_url = 'https://app.showslinger.com/promo_widget_v3/combo_widget?id=238&secure_code=ec8183215e&origin_url=https://jjcomedy.com/calendar/'
WHERE name = 'My Club';
```

**Verify:**
```bash
cd apps/scraper && make scrape-club CLUB='My Club'
```

---

## Generic vs. Parameterized Summary

| Platform | Scraper Key | Needs Code? | Just set DB fields |
|---|---|---|---|
| Ticketmaster | `live_nation` | No | `ticketmaster_id` |
| Eventbrite | `eventbrite` | No | `eventbrite_id` |
| SeatEngine v1 | `seatengine` | No | `seatengine_id` (numeric) |
| SeatEngine Classic | `seatengine_classic` | No | `scraping_url` (calendar URL; `seatengine_id` metadata only) |
| SeatEngine v3 | `seatengine_v3` | No | `seatengine_id` (UUID) |
| Tribe Events (WordPress) | `the_events_calendar` | No | `source_url` |
| Modern Events Calendar (WordPress) | `modern_events_calendar` | No | `source_url` (`mec-events` REST endpoint + optional metadata) |
| WordPress category posts | venue-specific | **Yes** — parse venue title/date format | `source_url` (WP posts API category URL) |
| rhp-events (WordPress) | `comedy_magic_club` | No | `scraping_url` |
| JSON-LD (generic) | `json_ld` | No | `scraping_url` |
| Prekindle | `json_ld` | No | `scraping_url` |
| Humanitix | `json_ld` | No | `scraping_url` (Humanitix host URL) |
| Elfsight Event Calendar | `elfsight` | No | `source_url` (venue calendar page) + metadata `widget_pid` (+ optional `comedy_filter`) |
| Ninkashi | `ninkashi` | No | `scraping_url` (tickets subdomain URL) |
| Vivenu | `vivenu` | No | `scraping_url` |
| ShowSlinger | `show_slinger` | No | `scraping_url` (full combo_widget URL with id, secure_code, origin_url) |
| Tixr detail pages | `tixr` | No | `scraping_url` / `source_url` |
| Tixr public cards | `tixr_public_card` | No | `scraping_url` / `source_url` |
| Tixr Webflow day cards | `tixr_webflow_day_card` | No | `source_url` + metadata `tixr_group_fragment` |
| Tockify | venue-specific | **Yes** — replace calname | `scraping_url` |
| Tock | `tock` | No | `source_url` (business page URL; set `metadata.comedy_filter` for mixed calendars) |
| FareHarbor | `fareharbor` | No | `source_url` + metadata `shortname`, optional `exclude_item_pks` |
| Squarespace | `squarespace` | No | `scraping_url` (full GetItemsByMonth URL with `collectionId`) |
| Wix Events | venue-specific | **Yes** — replace compId | `scraping_url` |
| Crowdwork | `crowdwork` | No — slug lives in `source_url` | `source_url` (`/api/v2/<theatre>/shows`) |
| VBO Tickets (multi-event listing) | `vbo_tickets` | No | `source_url` (loadplugin URL with SiteID) |
| VBO Tickets (single recurring show) | venue-specific | **Yes** — replace SiteID/EID constants | `scraping_url` |
| SquadUP | venue-specific | **Yes** — replace user_id | `scraping_url` |
| Netlify Functions | venue-specific | **Yes** — new scraper dir | `scraping_url` (unused) |
| SimpleTix | `simpletix` | No | `scraping_url` (full SimpleTix event page URL) |
| ThunderTix | `thundertix` | No | `scraping_sources.source_url` (+ optional `metadata.title_skip_prefixes`) |
| TicketSource | venue-specific | **Yes** — new scraper dir (ref: `comedy_clubhouse`) | `scraping_url` |
| StageTime | venue-specific | **Yes** — new scraper dir | `scraping_url` |
| OvationTix (calendar) | `uncle_vinnies` | **Yes** — replace production IDs | `scraping_url` |
| OvationTix (direct) | `four_day_weekend` | **Yes** — replace production IDs | `scraping_url` |
| OvationTix (generic) | `ovationtix` | **No** — set `ovationtix_client_id` | `scraping_url` = `web.ovationtix.com/trs/cal/{clientId}` |
| OpenDate | venue-specific | **Yes** — ref: `sports_drink` | `scraping_url` |
| Square Online (Weebly) | venue-specific | **Yes** — ref: `coral_gables_comedy_club` | `scraping_url` (full products API URL) |
| Showpass | `showpass` | No | `scraping_url` (Showpass calendar API base URL) |
| TicketLeap | `ticketleap` | No | `scraping_url` (org listing URL: `events.ticketleap.com/events/{org_slug}`) |
| BrassTix | `brasstix` | No | `scraping_sources.source_url` (calendar.php URL with `Show=...`) |
| SellingTicket | `sellingticket` | No | `scraping_url` (list URL with OrganizationID) |
| Shopify | `shopify` | No | `scraping_url` (Shopify collection page URL) |
| BookTix | `booktix` | No | `source_url` or `scraping_url` (BookTix box-office home URL) |
| ShoWare | `showare` | No | `scraping_url` / `source_url` (ShoWare `default.asp` or venue root URL) |

---

## ShoWare

**Use when:** ticket links point to an accesso ShoWare host such as
`https://<venue>.showare.com/`, pages include an accesso ShoWare footer, or
network requests hit `/include/widgets/events/performancelist.asp`.

**DB setup:** use `platform='custom'`, `scraper_key='showare'`, and set
`source_url` to the ShoWare host's `default.asp` page or root URL. The generic
scraper derives the JSON endpoint from the host:

```sql
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
VALUES (
  <club_id>,
  'custom',
  'showare',
  'https://<venue>.showare.com/default.asp',
  0,
  TRUE,
  jsonb_build_object(
    'include_title_patterns', jsonb_build_array('Comedy', 'Known Comic Name'),
    'exclude_title_patterns', jsonb_build_array('screening', 'movie', 'film')
  )
);
```

**Multi-purpose venues:** ShoWare often powers concerts, fundraisers, recitals,
gift certificates, and live comedy on the same endpoint. Configure
`metadata.include_title_patterns` for the comedy-relevant titles and
`metadata.exclude_title_patterns` for film-only or movie screening rows. If the
official venue calendar also links to Veezi, keep `source_url` on the ShoWare
host so the live-performance scraper does not ingest movie ticketing pages.

## Onboarding Walkthrough: Tockify Venue

Here is a complete step-by-step example for a fictional new Tockify venue called "The Comedy Loft" with calname `thecomedyloft`.

**Step 1 — Confirm the platform**

Navigate to the venue's show listing page in Playwright:
```
browser_navigate → https://thecomedyloft.com/shows
browser_wait_for  → time: 3
browser_network_requests (includeStatic: false)
```
Look for a request to `tockify.com/api/tagoptions/thecomedyloft`. The `calname` is `thecomedyloft`.

**Step 2 — Test the API directly**
```bash
curl "https://tockify.com/api/ngevent?calname=thecomedyloft&max=200&startms=$(date +%s)000"
```
Confirm events are returned. Note the `customButtonLink` format for ticket URLs.

**Step 3 — Create the scraper**
```bash
cp -r apps/scraper/src/laughtrack/scrapers/implementations/venues/ice_house \
      apps/scraper/src/laughtrack/scrapers/implementations/venues/comedy_loft
```
In `comedy_loft/scraper.py`:
- Change `key = "comedy_loft"`
- Change `_TOCKIFY_BASE_URL` to use `calname=thecomedyloft`

In `comedy_loft/extractor.py`:
- Adjust any venue-specific ticket URL normalization if needed

Add `__init__.py` (empty) to the new directory.

**Step 4 — Add to the DB**
```sql
INSERT INTO clubs (name, scraper, scraping_url, ...)
VALUES ('The Comedy Loft', 'comedy_loft', 'https://thecomedyloft.com/shows', ...);
```

**Step 5 — Verify**
```bash
cd apps/scraper && make scrape-club CLUB='The Comedy Loft'
```
Confirm shows are scraped with correct dates (timestamps ÷ 1000 → seconds), ticket URLs, and comedian names.

---

## Maintenance Invariants

Repeatable database invariants live under `scripts/core/check_*.py` and are
exposed via `make check-*` targets. They are safe to run anytime and exit 2 on
violation so they can be wired into CI or a scheduled job. Notable checks:

### `check-scraping-source-invariants`

```bash
cd apps/scraper
make check-scraping-source-invariants                    # human report
make check-scraping-source-invariants ARGS='--json'      # machine-readable
```

Guards two invariants in one pass; trips exit 2 when either is violated:

1. **Orphan future inventory** — clubs with future shows but no enabled
   `scraping_sources` row. Usually means a stale writer, legacy pre-source
   data, or a hidden duplicate row is still emitting listings.
2. **Active clubs missing a scraper** — active visible clubs
   (`clubs.status = 'active'` AND `COALESCE(visible, TRUE) = TRUE`) with no
   enabled `scraping_sources` row at all. An active venue with no enabled
   source cannot ingest new inventory: either a dedicated scraper was never
   wired up after onboarding, or every previously enabled source has since
   been disabled without the club itself being deactivated. Invariant 1
   already covers the subset that still has future shows on the books; this
   invariant catches the quieter case where the club has no future inventory
   yet (or anymore) and would otherwise drift unscraped without a paging
   signal. Action: wire a dedicated `scraping_sources` row for the venue, or
   deactivate / hide the club if it is no longer running shows.

   **Scope:** Invariant 2 only looks at active visible clubs. A moderator
   hiding a club will silence the watchdog for that row — intentional,
   since hidden clubs are not shipped to users and don't accumulate
   user-visible rot. If a hidden club still needs onboarding attention,
   re-enable visibility or address it directly.

Other related checks:

- `check-scraping-priorities` — duplicate enabled `(club_id, priority)` rows
- `check-stale-scraper-keys` — enabled scraper keys with no recent writes
- `check-show-attribution` — `shows.last_scraped_by` values missing from `scrapers.key`

---

## Quick Reference: DB Fields by Scraper Key

| Scraper Key | Required DB Fields |
|---|---|
| `live_nation` | `ticketmaster_id` (alphanumeric Discovery API ID) |
| `eventbrite` | `eventbrite_id` (organizer or venue numeric ID) |
| `seatengine` | `seatengine_id` (numeric) |
| `seatengine_classic` | `scraping_url` (calendar URL; `seatengine_id` optional metadata only) |
| `seatengine_v3` | `seatengine_id` (UUID) |
| `the_events_calendar` | `source_url` (Tribe Events REST API base URL) |
| `modern_events_calendar` | `source_url` (WordPress `mec-events` REST endpoint, optionally filtered by `mec_category`) |
| `comedy_magic_club` | `scraping_url` (base `/events/` URL — no pagination) |
| `json_ld` | `scraping_url` (events page with JSON-LD markup, e.g. Prekindle, Humanitix) |
| `odoo_events` | `source_url` (Odoo website_event listing URL, usually `/event`) |
| `tixr` | `source_url` or `scraping_url` (server-rendered calendar page with Tixr event links) |
| `tixr_public_card` | `source_url` or `scraping_url` (venue-owned event cards with Tixr ticket URLs) |
| `tixr_webflow_day_card` | `source_url` + metadata `tixr_group_fragment` |
| `timely` | `source_url` + metadata `timely_calendar_id` |
| `squarespace` | `scraping_url` (full GetItemsByMonth URL with `collectionId`) |
| `vbo_tickets` | `source_url` (loadplugin URL with SiteID) |
| `ninkashi` | `scraping_url` (tickets subdomain, e.g. `tickets.myvenue.com`) |
| `vivenu` | `scraping_url` (Vivenu seller page root URL) |
| `simpletix` | `scraping_url` (full SimpleTix event page URL) |
| `thundertix` | `source_url` (+ optional metadata `title_skip_prefixes`) |
| `showpass` | `scraping_url` (Showpass calendar API base URL: `.../venues/{slug}/calendar/`) |
| `show_slinger` | `scraping_url` (full combo_widget URL with id, secure_code, origin_url) |
| `ticketleap` | `scraping_url` (org listing URL: `events.ticketleap.com/events/{org_slug}`) |
| `tock` | `source_url` (business page URL: `exploretock.com/{business_slug}`; optional `metadata.comedy_filter`) |
| `sellingticket` | `scraping_url` or `source_url` (list URL with OrganizationID) |
| `shopify` | `scraping_url` (Shopify collection page URL) |
| `booktix` | `source_url` or `scraping_url` (BookTix box-office home URL) |
| `east_austin_comedy` | `scraping_url` (homepage anchor; unused at runtime) |
| All venue-specific | `scraping_url` (venue calendar page or API URL) |
